// Apache-2.0. Append one reviewed documentation control; preserve every prior control.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {pathToFileURL} from 'node:url';
const sha=x=>crypto.createHash('sha256').update(x).digest('hex');
export function assertAppend(before,desired,scope='crossref-targeted-doi-replacement'){
 if(!['crossref-targeted-doi-replacement','crossref-incremental-doi','g07-notification-safe-operator-cycle','g04-workbook-timeout-recovery','anzctr-manual-archive-study-refresh','source-recovery-bootstrap','publication-digest-current-definition','publication-writer-conditional-observations','monthly-schedule-repair-20261102','publication-free-api-handoff-20261103'].includes(scope))throw Error('Unknown documentation scope');
 const old=JSON.parse(before.CanvasContent1);
 if(desired.length!==old.length+1 || JSON.stringify(desired.slice(0,-1))!==JSON.stringify(old))throw Error('Unselected catalogue controls changed');
 const added=desired.at(-1);
 if(added.controlType!==4 || old.some(c=>c.id===added.id) || typeof added.innerHTML!=='string' || !added.innerHTML.includes(scope))throw Error('Exact separate replacement control required');
}
export function assertSavedAppend(before,desired,after,site,scope='crossref-targeted-doi-replacement'){
 assertAppend(before,desired,scope);
 const actual=JSON.parse(after.CanvasContent1),expected=structuredClone(desired);
 // SharePoint canonicalizes same-site absolute hrefs on the newly appended control only.
 expected.at(-1).innerHTML=expected.at(-1).innerHTML.replace(/href="([^"]+)"/g,(match,value)=>{
  const url=new URL(value,site);return url.origin===new URL(site).origin?'href="'+url.pathname+url.search+url.hash+'"':match;
 });
 if(JSON.stringify(actual)!==JSON.stringify(desired)&&JSON.stringify(actual)!==JSON.stringify(expected))throw Error('Saved catalogue controls differ beyond exact new-control href canonicalization');
 for(const key of ['UniqueId','Title','Description','LayoutWebpartsContent'])if(after[key]!==before[key])throw Error('Saved catalogue identity/layout differs');
 if(after.IsPageCheckedOutToCurrentUser||!after.Version.endsWith('.0'))throw Error('Catalogue is not a checked-in major version');
}

export async function publishCatalogueAppend({args,pin,request}){
 const [directory,scope='crossref-targeted-doi-replacement',pageId='7']=args;if(args.length<1||args.length>3)throw Error('Exact private publication directory required');
 execFileSync('git',['check-ignore','-q',path.resolve(directory)]);
 if(pageId!=='7' && !(pageId==='6' && ['monthly-schedule-repair-20261102','publication-free-api-handoff-20261103'].includes(scope)))throw Error('Unqualified documentation page');
 const pageName=pageId==='6'?'RIMS-Dataset-Field-Guide.aspx':'RIMS-Flow-Diagrams.aspx';
 const root=path.resolve(directory),read=n=>JSON.parse(fs.readFileSync(path.join(root,n)));
 const before=read('catalogue-before.json'),desired=read('catalogue-desired-canvas.json');assertAppend(before,desired,scope);
 const message=scope==='publication-free-api-handoff-20261103'?'Document verified free-API publication source coverage; preserve explicit source limits and all prior content.':scope==='monthly-schedule-repair-20261102'?'Document verified existing monthly repair and pending natural-run acceptance.':scope==='publication-writer-conditional-observations'?'Document current Stopped publication conditional-update definition; runtime acceptance and native Loop parity remain separate.':scope==='publication-digest-current-definition'?'Document current Stopped digest definition; retain historical no-send acceptance and pending native Loop parity.':scope==='source-recovery-bootstrap'?'Document CLI-saved PubMed, DataCite and ClinicalTrials recovery definitions; changed-path runtime remains separately unaccepted.':scope==='anzctr-manual-archive-study-refresh'?'Document accepted manual ANZCTR archive, study refresh and reconciled flow catalogue; preserve existing documentation.':scope==='g04-workbook-timeout-recovery'?'Document qualified MRFF timeout recovery and bounded workbook integration; preserve historical diagrams.':scope==='g07-notification-safe-operator-cycle'?'Document notification-safe grants source cycle and scoped recovery; preserve existing documentation.':scope==='crossref-incremental-doi'?'Document verified Crossref incremental coverage and daily03:30 collector; preserve dated baseline and historical diagrams.':'Document the independently verified Crossref targeted replacement; preserve historical diagrams.';
 const target=pin.documentationTarget;if(!target || !pin.resources.includes(new URL(target.site_url).origin))throw Error('Documentation resource unpinned');
 const journal=path.join(root,'catalogue-transport.jsonl');
 const prior=fs.existsSync(journal)?fs.readFileSync(journal,'utf8').trim().split('\n').map(JSON.parse):[];
 const resume=prior.length===2 && prior.some(x=>x.url.endsWith('/checkoutpage')) && prior.every(x=>x.url.endsWith('/checkoutpage')||x.url.endsWith('/contextinfo'));
 if(prior.length&&!resume)throw Error('Prior publication journal exists; reconcile, never resend');
 const url=target.site_url+'/_api/sitepages/pages('+pageId+')';
 const get=()=>request.get({url,headers:{accept:'application/json;odata=nometadata'},responseType:'json'});
 const equal=(current,owned=false)=>{for(const k of ['UniqueId','CanvasContent1','LayoutWebpartsContent','Title','Description'])if(current[k]!==before[k])throw Error('Native page drift '+k);if(!owned&&current.Version!==before.Version)throw Error('Native page drift Version');if(current.IsPageCheckedOutToCurrentUser&&!owned)throw Error('Existing draft; preserve');};
 const current=await get();equal(current,resume);if(resume&&(!current.IsPageCheckedOutToCurrentUser||current.Version!==before.Version.replace(/\.0$/,'.1')))throw Error('Owned checkout state differs; preserve');
 const seen=new Set();let saved=false;
 request.req.interceptors.request.use(async c=>{
  c.maxRedirects=0;
  if(['get','head','options'].includes((c.method??'get').toLowerCase()))return c;
  const u=new URL(c.url);if(u.origin!==new URL(target.site_url).origin||!u.pathname.toLowerCase().startsWith(new URL(target.site_url).pathname.toLowerCase()+'/_api/'))throw Error('Mutation outside documentation site');
  const key=c.method+' '+c.url+' '+sha(Buffer.isBuffer(c.data)?c.data:Buffer.from(JSON.stringify(c.data??null)));if(seen.has(key))throw Error('Duplicate publication transport; reconcile');seen.add(key);
  if(/\/savepage(?:asdraft)?(?:\?|$)/i.test(u.pathname)){
   if(saved)throw Error('Duplicate SavePage');equal(await get(),true);const body=typeof c.data==='string'?JSON.parse(c.data):c.data;
   if(JSON.stringify(JSON.parse(body.CanvasContent1))!==JSON.stringify(desired))throw Error('Unreviewed canvas');saved=true;
  }
  fs.appendFileSync(journal,JSON.stringify({method:c.method,url:c.url,body_sha256:key.slice(-64),at:new Date().toISOString()})+'\n',{mode:0o600});return c;
 });
 if(resume){
  // Continue the recorded checkout at the installed CLI's supported SavePage/CheckIn boundary.
  const data={CanvasContent1:JSON.stringify(desired)};for(const k of ['Title','Description','BannerImageUrl','LayoutWebpartsContent','TopicHeader','AuthorByline'])if(current[k])data[k]=current[k];
  await request.post({url:target.site_url+'/_api/SitePages/Pages('+pageId+')/SavePage',headers:{'X-HTTP-Method':'MERGE','IF-MATCH':'*','content-type':'application/json;odata=nometadata',accept:'application/json;odata=nometadata'},data,responseType:'json'});
  const savedDraft=await get();if(JSON.stringify(JSON.parse(savedDraft.CanvasContent1))!==JSON.stringify(desired)||!savedDraft.IsPageCheckedOutToCurrentUser)throw Error('Owned saved draft differs; preserve');
  await request.post({url:target.site_url+"/_api/web/GetFileByServerRelativePath(DecodedUrl='"+new URL(target.site_url).pathname+"/SitePages/"+pageName+"')/CheckIn(comment='RIMS qualified documentation update',checkintype=1)",headers:{accept:'application/json;odata=nometadata'},responseType:'json'});
 }else{
  const {executeCommand}=await import(pathToFileURL(path.join(pin.sdkRoot,'dist/api.js')));
  await executeCommand('spo page set',{webUrl:target.site_url,name:pageName,content:JSON.stringify(desired),description:before.Description,publish:true,publishMessage:message,output:'none'});
 }
 const after=await get();fs.writeFileSync(path.join(root,'catalogue-after.json'),JSON.stringify(after,null,2)+'\n',{flag:'wx',mode:0o600});
 assertSavedAppend(before,desired,after,target.site_url,scope);
 console.log(JSON.stringify({status:'PASS_NATIVE_CATALOGUE_APPEND',version:after.Version,unselected_controls_preserved:desired.length-1}));
}
