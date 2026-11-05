// SPDX-License-Identifier: Apache-2.0
// Read-only capture; native transport is exclusively the existing guarded wrapper.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {spawnSync} from 'node:child_process';
import {pathToFileURL} from 'node:url';
export const managed=['SourceKey','Source','ContextKind','SourceID','RelatedID','SourceURL','FullSummary','SourceProjectionJSON','SourceProvenanceJSON'];
const title='CHHHS RIMS | Data spaces | Source assertions - DEV';
const requireThat=(v,m)=>{if(!v)throw Error(m);};
export async function capture({base,read,save,maxPages=1000}) {
 const u=new URL(base);requireThat(u.protocol==='https:'&&!u.username&&!u.password&&!u.hash&&!u.search,'Exact HTTPS list URL required');
 const match=u.pathname.match(/\/_api\/web\/lists\(guid'([a-f0-9-]{36})'\)$/i);requireThat(match,'Exact list GUID required');
 const requests=[];
 const get=async(url,name)=>{const value=await read(url,name);requests.push({url,file:name,observedUTC:new Date().toISOString()});return value;};
 const metadataURL=base+'?$select=Id,Title,ItemCount,EnableVersioning';
 const before=await get(metadataURL,'metadata-before.json');
 requireThat(before.Id?.toLowerCase()===match[1].toLowerCase()&&before.Title===title&&before.EnableVersioning===true&&Number.isInteger(before.ItemCount)&&before.ItemCount>=0,'Exact versioned target metadata required');
 async function pages(kind,query) {
  let next=base+'/'+kind+query;const seen=new Set(),all=[];let count=0;
  while(next){
   const v=new URL(next);requireThat(v.origin===u.origin&&v.pathname===u.pathname+'/'+kind&&!v.username&&!v.password&&!v.hash&&!/%(?:2f|5c|2e)/i.test(v.pathname),'Continuation outside exact collection');
   for(const k of v.searchParams.keys())requireThat(['$top','$select','$skiptoken','$skip'].includes(k),'Unexpected continuation query');
   requireThat(!seen.has(v.href)&&count<maxPages,'Repeated or excessive continuation');seen.add(v.href);
   const page=await get(v.href,`${kind}-page-${count++}.json`);requireThat(Array.isArray(page.value),'Unknown page shape');
   requireThat(!Object.hasOwn(page,'__next')&&!Object.hasOwn(page,'d'),'Unsupported continuation envelope');
   const a=page['odata.nextLink'],b=page['@odata.nextLink'];requireThat(!(a&&b&&a!==b),'Conflicting continuation');
   all.push(...page.value);next=a??b??null;requireThat(next===null||typeof next==='string'&&next.length>0,'Malformed continuation');
  }
  return {all,count};
 }
 const schema=await pages('fields','?$top=5000');const items=await pages('items','?$select=*&$top=5000');
 const after=await get(metadataURL,'metadata-after.json');
 for(const k of ['Id','Title','ItemCount','EnableVersioning'])requireThat(before[k]===after[k],'Metadata drift');
 requireThat(items.all.length===before.ItemCount,'Incomplete item count');
 const ids=new Set(),keys=new Set();
 for(const r of items.all){
  requireThat(Number.isInteger(r.Id)&&r.Id>0&&!ids.has(r.Id),'Invalid or duplicate ID');ids.add(r.Id);
  requireThat(typeof r.SourceKey==='string'&&r.SourceKey.trim()===r.SourceKey&&r.SourceKey.length>0&&!keys.has(r.SourceKey),'Invalid or duplicate source key');keys.add(r.SourceKey);
  for(const k of managed)requireThat(Object.hasOwn(r,k)&&(r[k]===null||typeof r[k]==='string'),'Missing or non-text managed field');
  for(const k of ['Title','OperatorNotes','Modified','Created','OData__UIVersionString'])requireThat(Object.hasOwn(r,k),'Missing protected/system field: '+k);
  requireThat(/^(?:W\/)?"[^"\r\n]+"$/.test(r['odata.etag']??r['@odata.etag']??''),'Invalid or missing ETag');
 }
 const names=new Set();for(const f of schema.all){requireThat(typeof f.InternalName==='string'&&!names.has(f.InternalName),'Duplicate/missing schema identity');names.add(f.InternalName);}
 for(const k of [...managed,'Title','OperatorNotes'])requireThat(names.has(k),'Missing schema field: '+k);
 const result={capture:{metadata:before,response:{value:items.all}},schema:{value:schema.all},receipt:{status:'PASS_COMPLETE_READ_ONLY_CAPTURE',target:base,rows:items.all.length,fields:schema.all.length,itemPages:items.count,schemaPages:schema.count,metadataStable:true,atomicSnapshot:false,continuationsExhausted:true,mutations:0,provenance:requests}};
 // No consumable capture is emitted before every validation finishes.
 for(const [name,value] of Object.entries(result))await save(name+'.json',value);
 return result;
}
async function main(){
 const args=process.argv.slice(2);requireThat(args.length===5&&args[0]==='--live','Usage: --live GUARD_ROOT PRIVATE_BINDING EXACT_LIST_URL NEW_IGNORED_OUTPUT');
 const [,guardRoot,binding,base,output]=args;const root=path.resolve(guardRoot),out=path.resolve(output),pin=JSON.parse(fs.readFileSync(binding));
 requireThat(pin.readUrlPrefixes?.includes(base),'Binding must pin exact list');
 requireThat(spawnSync('git',['check-ignore','-q',out],{cwd:root}).status===0,'Ignored private output required');
 fs.mkdirSync(out,{mode:0o700});
 const save=async(n,x)=>fs.writeFileSync(path.join(out,n),JSON.stringify(x,null,2),{flag:'wx',mode:0o600});
 try{
  await capture({base,save,read:async(url,name)=>{
   const r=spawnSync('node',[path.join(root,'scripts/m365-qualified.mjs'),'read',path.resolve(binding),'request','--url',url,'--method','get','--filePath',path.join(out,name),'--output','json'],{cwd:root,stdio:['ignore','ignore','pipe'],timeout:120000});
   requireThat(r.status===0&&!r.error,'Guarded read failed: '+String(r.stderr??r.error));return JSON.parse(fs.readFileSync(path.join(out,name)));
  }});
 }catch(e){await save('failure.json',{status:'INCOMPLETE',message:e.message,at:new Date().toISOString()});throw e;}
 finally{const hashes={};for(const n of fs.readdirSync(out))hashes[n]=crypto.createHash('sha256').update(fs.readFileSync(path.join(out,n))).digest('hex');await save('hashes.json',hashes);}
}
if(process.argv[1]&&import.meta.url===pathToFileURL(path.resolve(process.argv[1])).href)main().catch(e=>{console.error(e.message);process.exitCode=1;});
