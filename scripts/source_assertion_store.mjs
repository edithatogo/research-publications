// SPDX-License-Identifier: Apache-2.0
// Same-client transport; importing this module never initializes authentication.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
export const fields=['SourceKey','Source','ContextKind','SourceID','RelatedID','SourceURL','FullSummary','SourceProjectionJSON','SourceProvenanceJSON'];
export function policy(operation,payload){
 try{return JSON.parse(execFileSync(path.join(root,'.venv/bin/python'),['-m','scripts.source_assertion_executor_policy',operation],{cwd:root,input:typeof payload==='string'?payload:JSON.stringify(payload),encoding:'utf8',stdio:['pipe','pipe','pipe']}));}
 catch{throw Error('Source assertion policy refused '+operation);}
}
export function target(pin,t){
 const u=new URL(t.listUrl);
 if(Object.keys(t).sort().join('|')!=='listUrl|title'||t.title!=='CHHHS RIMS | Data spaces | Source assertions - DEV'
  ||u.protocol!=='https:'||u.username||u.password||u.search||u.hash||/%(?:2f|5c|2e|25)/i.test(u.pathname)
  ||!/\/_api\/web\/lists\(guid'[0-9a-f-]{36}'\)$/.test(u.pathname)||!pin.resources.includes(u.origin)
  ||!pin.readUrlPrefixes.some(p=>p.startsWith(u.href.split('/_api/')[0]+"/_api/web/lists(guid'")))throw Error('Exact existing Source Assertions target on retained site required');
 return t;
}
export async function execute({target,plan,send,save}){
 plan=policy('validate',plan);
 const call=async(method,url,data,headers={})=>{
  let r;try{r=await send({method,url,data:data?JSON.stringify(data):undefined,headers:{Accept:'application/json;odata=verbose','Content-Type':'application/json;odata=nometadata',...headers},timeout:20000,maxRedirects:0,responseType:'text'});}
  catch(e){const error=Error('Source assertion HTTP operation failed');error.status=e.response?.status??null;throw error;}
  if(r.status<200||r.status>=300)throw Error('Unexpected HTTP status');
  const value=r.data?typeof r.data==='string'?JSON.parse(r.data):r.data:{};return value.d??value;
 };
 const base=target.listUrl;
 const meta=await call('GET',base+'?$select=Id,Title,EnableVersioning');save('metadata.json',meta);
 if(meta.Title!==target.title||meta.EnableVersioning!==true||meta.Id?.toLowerCase()!==base.match(/guid'([^']+)'/)[1].toLowerCase())throw Error('Exact versioned register required');
 const schema=await call('GET',base+'/fields');save('schema.json',schema);
 if(schema.__next||!Array.isArray(schema.results))throw Error('Incomplete schema');
 policy('schema',schema.results);
 const item=plan.item_id;
 const url=base+'/items'+(item?'('+item+')':'?'+new URLSearchParams({'$filter':"SourceKey eq '"+plan.after.SourceKey+"'",'$top':'2'}));
 const read=async name=>{
  const value=await call('GET',url);
  if(value.__next)throw Error('Incomplete identity lookup');
  const rows=item?[value]:value.results;
  if(!Array.isArray(rows)||rows.length>1)throw Error('Duplicate identity');
  const row=rows[0];let current=null;
  if(row){
   if(!Number.isSafeInteger(row.Id)||row.Id<1||typeof row.__metadata?.etag!=='string'||!/^(?:W\/)?"[^"\r\n]+"$/.test(row.__metadata.etag))throw Error('Invalid item identity/ETag');
   current={item_id:row.Id,etag:row.__metadata.etag,fields:Object.fromEntries(fields.map(f=>[f,row[f]??'']))};
   if(!Object.values(current.fields).every(v=>typeof v==='string'))throw Error('Unexpected field types');
  }
  save(name,{current,raw:row??null});return current;
 };
 const current=await read('preimage.json');
 const prepared=policy('request',{plan,current});
 if(!prepared.write)return {outcome:'unchanged_replay',writes:0,current};
 const w=prepared.write;
 // Durable exclusive intent must succeed before the only mutation call.
 save('send-intent.json',{target,plan,request:w,retries:0,redirects:0});
 let status=null;
 try{await call(w.method,base+w.path,w.body,w.headers);}catch(e){status=e.status??'transport_error';}
 let after;try{after=await read('postimage.json');}catch{return {outcome:'unknown',writes:1,retry_allowed:false,status};}
 return {...policy('reconcile',{plan,current:after}),writes:1,status,current:after};
}
export async function runGuarded({args,auth,request,pin}){
 const [targetFile,planFile,directory]=args;
 const selected=target(pin,JSON.parse(fs.readFileSync(targetFile,'utf8')));
 const plan=policy('validate',fs.readFileSync(planFile,'utf8'));
 fs.mkdirSync(directory,{mode:0o700});
 const save=(name,value)=>{const fd=fs.openSync(path.join(directory,name),'wx',0o600);try{fs.writeFileSync(fd,JSON.stringify(value,null,2));fs.fsyncSync(fd);}finally{fs.closeSync(fd);}};
 let result;
 try{
  const token=await auth.ensureAccessToken(new URL(selected.listUrl).origin,{log:async()=>{},logToStderr:async()=>{}},false);
  result=await execute({target:selected,plan,save,send:c=>request.req({...c,headers:{...c.headers,Authorization:'Bearer '+token}})});
 }catch{result={outcome:'blocked',writes:fs.existsSync(path.join(directory,'send-intent.json'))?1:0,retry_allowed:false,message:'Guarded operation stopped; inspect private stage receipts, do not resend'};}
 save('result.json',result);console.log(JSON.stringify({outcome:result.outcome,writes:result.writes}));
 if(!['candidate_present','unchanged_replay'].includes(result.outcome))process.exitCode=2;
}
