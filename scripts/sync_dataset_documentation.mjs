/** Operator-run versioned asset sync through the existing M365 CLI client.
 * No token export, sign-in, grants, deletion, settings changes or scheduling.
 */
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {pathToFileURL} from 'node:url';
export const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
export function classify(localHash,remoteHash,baselineHash){
 if(remoteHash===null)return 'create';
 if(localHash===remoteHash)return 'unchanged';
 if(!baselineHash||remoteHash!==baselineHash)throw Error('Native content differs from accepted baseline; preserve human edits');
 return 'update';
}
export function assertIdentity(recorded,native){
 if(recorded?.UniqueId&&(!native||native.UniqueId!==recorded.UniqueId))throw Error('Native identity changed or missing; preserve version history');
}
export function manifestFiles(manifest){
 const seen=new Set();
 for(const f of manifest.files){
  if(!/^[A-Za-z0-9_.-]+$/.test(f.name)||seen.has(f.name))throw Error('Unsafe or duplicate artifact name');
  seen.add(f.name);
  if(sha(fs.readFileSync(f.path))!==f.sha256)throw Error('Prepared artifact changed: '+f.name);
 }
 return manifest.files;
}
export async function main(){
 const [mode,manifestPath,baselinePath,outputPath,libraryId]=process.argv.slice(2);
 if(!['plan','apply'].includes(mode)||!outputPath||!libraryId)throw Error('Usage: node scripts/sync_dataset_documentation.mjs plan|apply manifest.json baseline.json private/output-dir library-guid');
 const m=JSON.parse(fs.readFileSync(manifestPath));manifestFiles(m);
 const baseline=JSON.parse(fs.readFileSync(baselinePath));
 const url=new URL(m.site_url);if(url.protocol!=='https:'||!url.hostname.endsWith('.sharepoint.com')||!m.folder.startsWith(url.pathname+'/')||!/^\w{8}(-\w{4}){3}-\w{12}$/.test(libraryId))throw Error('Exact SharePoint site/folder/library required');
 fs.mkdirSync(outputPath,{recursive:true});
 const journal=path.join(outputPath,'transport.jsonl');
 const dist=process.env.RIMS_M365_CLI_DIST||path.dirname(fs.realpathSync(execFileSync('which',['m365'],{encoding:'utf8'}).trim()));
 const request=(await import(pathToFileURL(path.join(dist,'request.js')))).default;
 const seen=new Set();
 request.req.interceptors.request.use(c=>{
  c.maxRedirects=0;
  if(!['get','head','options'].includes((c.method||'get').toLowerCase())){
   const target=new URL(c.url);if(target.origin!==url.origin||!target.pathname.toLowerCase().startsWith(url.pathname.toLowerCase()+'/_api/'))throw Error('Mutation outside exact site');
   const key=c.method+' '+c.url+' '+sha(Buffer.isBuffer(c.data)?c.data:Buffer.from(JSON.stringify(c.data??null)));
   if(seen.has(key))throw Error('Duplicate mutation transport blocked; reconcile native target');
   seen.add(key);fs.appendFileSync(journal,JSON.stringify({method:c.method,url:c.url,body_sha256:sha(Buffer.isBuffer(c.data)?c.data:Buffer.from(JSON.stringify(c.data??null))),submitted_utc:new Date().toISOString()})+'\n');
  }
  return c;
 });
 const {executeCommand}=await import(pathToFileURL(path.join(dist,'api.js')));
 const libraryUrl=m.site_url+"/_api/web/lists(guid'"+libraryId+"')?$select=Id,EnableVersioning,MajorVersionLimit,ForceCheckout,RootFolder/ServerRelativeUrl&$expand=RootFolder";
 await executeCommand('request',{url:libraryUrl,method:'get',output:'none'});
 request.logger={log:async()=>{},logToStderr:async()=>{}};
 const get=async p=>request.get({url:m.site_url+p,headers:{accept:'application/json;odata=nometadata'},responseType:'json'});
 const library=await request.get({url:libraryUrl,headers:{accept:'application/json;odata=nometadata'},responseType:'json'});
 if(!library.EnableVersioning||library.ForceCheckout||!m.folder.startsWith(library.RootFolder.ServerRelativeUrl+'/'))throw Error('Versioned non-forced-checkout library/folder not qualified');
 const parent=await get("/_api/web/GetFolderByServerRelativePath(decodedurl='"+m.folder.replaceAll("'","''")+"')/ListItemAllFields/ParentList?$select=Id");
 if(parent.Id.toLowerCase()!==libraryId.toLowerCase())throw Error('Folder parent identity differs');
 const folder="/_api/web/GetFolderByServerRelativePath(decodedurl='"+m.folder.replaceAll("'","''")+"')";
 const listing=await get(folder+'/Files?$select=Name,UniqueId,ETag,Length,CheckOutType,MajorVersion,MinorVersion&$top=5000');
 if(listing['odata.nextLink']||listing['@odata.nextLink'])throw Error('Incomplete native file inventory');
 const existing=new Map(listing.value.map(f=>[f.Name,{Name:f.Name,UniqueId:f.UniqueId,ETag:f.ETag,Length:String(f.Length),CheckOutType:f.CheckOutType,MajorVersion:f.MajorVersion,MinorVersion:f.MinorVersion}]));const old=new Map(baseline.files.map(f=>[f.name,f]));
 const bytes=async id=>Buffer.from(await request.get({url:m.site_url+"/_api/web/GetFileById('"+id+"')/$value",headers:{accept:'application/octet-stream'},responseType:'arraybuffer'}));
 const rows=[];
 for(const f of m.files){
  const native=existing.get(f.name);assertIdentity(old.get(f.name),native);if(native&&native.CheckOutType!==2)throw Error('Existing checkout: '+f.name);
  const raw=native?await bytes(native.UniqueId):null;const action=classify(f.sha256,raw?sha(raw):null,old.get(f.name)?.sha256);
  if(raw&&action==='update'){fs.mkdirSync(path.join(outputPath,'preimages'),{recursive:true});fs.writeFileSync(path.join(outputPath,'preimages',f.name),raw);}
  rows.push({name:f.name,action,sha256:f.sha256,native:native||null});
 }
 const plan={schema:1,site_url:m.site_url,folder:m.folder,library_id:libraryId,manifest_sha256:sha(fs.readFileSync(manifestPath)),library,files:rows};
 const planPath=path.join(outputPath,'plan.json');
 if(mode==='plan'){fs.writeFileSync(planPath,JSON.stringify(plan,null,2));console.log(JSON.stringify({planned:rows.length,counts:rows.reduce((r,x)=>(r[x.action]=(r[x.action]||0)+1,r),{})}));return;}
 // Apply requires the exact reviewed plan, with no material intervening drift.
 const accepted=JSON.parse(fs.readFileSync(planPath));
 if(accepted.manifest_sha256!==plan.manifest_sha256||accepted.site_url!==plan.site_url||accepted.folder!==plan.folder||accepted.library_id!==plan.library_id||JSON.stringify(accepted.files)!==JSON.stringify(plan.files))throw Error('Native/local plan drift; do not overwrite');
 const result=[];
 for(const row of rows){
  const f=m.files.find(f=>f.name===row.name);let native=row.native;
  if(row.action!=='unchanged'){
   const payload=fs.readFileSync(f.path);if(sha(payload)!==row.sha256)throw Error('Local bytes changed after preflight');
   if(native){
    const current=await get("/_api/web/GetFileById('"+native.UniqueId+"')?$select=UniqueId,ETag,CheckOutType");
    if(current.ETag!==native.ETag||current.CheckOutType!==2)throw Error('File changed after preflight: '+row.name);
    const endpoint=m.site_url+"/_api/web/GetFileById('"+native.UniqueId+"')";
    await request.post({url:endpoint+'/CheckOut()',headers:{accept:'application/json;odata=nometadata'},responseType:'json'});
    const locked=await get("/_api/web/GetFileById('"+native.UniqueId+"')?$select=UniqueId,ETag,CheckOutType");
    if(locked.CheckOutType===2||sha(await bytes(native.UniqueId))!==old.get(row.name)?.sha256)throw Error('Content changed before native checkout; preserve lock and reconcile');
    await request.put({url:endpoint+'/$value',headers:{'IF-MATCH':locked.ETag,'content-type':'application/octet-stream',accept:'application/json;odata=nometadata'},data:payload,responseType:'json'});
    if(sha(await bytes(native.UniqueId))!==row.sha256)throw Error('Saved checkout content mismatch; preserve lock');
    await request.post({url:endpoint+"/CheckIn(comment='RIMS documentation generation "+plan.manifest_sha256+"',checkintype=1)",headers:{accept:'application/json;odata=nometadata'},responseType:'json'});
   }else{
    native=await request.post({url:m.site_url+folder+"/Files/Add(url='"+encodeURIComponent(row.name)+"',overwrite=false)",headers:{accept:'application/json;odata=nometadata','content-type':'application/octet-stream'},data:payload,responseType:'json'});
   }
  }
  const saved=await get("/_api/web/GetFileById('"+native.UniqueId+"')?$select=UniqueId,Name,ETag,MajorVersion,MinorVersion,CheckOutType");
  const raw=await bytes(saved.UniqueId);if(sha(raw)!==row.sha256||saved.CheckOutType!==2||saved.Name!==row.name)throw Error('Native saved-byte/identity/checkout mismatch');
  if(row.native&&saved.UniqueId!==row.native.UniqueId)throw Error('Existing file identity replaced');
  if(row.action==='unchanged'&&saved.ETag!==row.native.ETag)throw Error('Unexpected unchanged-file version drift');
  let previousVersion=null;
  if(row.action==='update'){
   if(saved.MajorVersion<=row.native.MajorVersion)throw Error('Major version did not advance');
   const versions=await get("/_api/web/GetFileById('"+saved.UniqueId+"')/Versions?$select=ID,VersionLabel");
   const label=row.native.MajorVersion+'.'+row.native.MinorVersion;const previous=versions.value.find(v=>v.VersionLabel===label);
   if(!previous)throw Error('Previous version missing from native history');
   const oldBytes=Buffer.from(await request.get({url:m.site_url+"/_api/web/GetFileById('"+saved.UniqueId+"')/Versions("+previous.ID+")/$value",headers:{accept:'application/octet-stream'},responseType:'arraybuffer'}));
   if(sha(oldBytes)!==old.get(row.name)?.sha256)throw Error('Previous native version bytes differ');
   previousVersion={label,sha256:sha(oldBytes),retrieved:true};
  }
  const receipt={name:row.name,action:row.action,sha256:sha(raw),previousVersion,...saved};result.push(receipt);
  fs.writeFileSync(path.join(outputPath,'acceptance.json'),JSON.stringify({status:result.length===rows.length?'PASS_COMPLETE':'IN_PROGRESS',files:result},null,2));
  if(result.length%25===0)console.log('Verified '+result.length+'/'+rows.length);
 }
 console.log(JSON.stringify({status:'PASS_COMPLETE',files:result.length}));
}
if(process.argv[1]&&path.resolve(process.argv[1])===path.resolve(new URL(import.meta.url).pathname))main().catch(e=>{console.error(e.message||e.error?.message||String(e.error||e));process.exitCode=1;});
