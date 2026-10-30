// SPDX-License-Identifier: Apache-2.0
// Add only dedicated project-link fields on the existing outcome evidence item.
import fs from 'node:fs';
import path from 'node:path';
import {isDeepStrictEqual as equal} from 'node:util';
import {validateTarget} from './outcome_store.mjs';
export async function runGuarded({args,auth,request,pin}){
 const [targetFile,initialFile,directory]=args;
 const selected=JSON.parse(fs.readFileSync(targetFile,'utf8'));
 const t=validateTarget({...pin,outcomeTarget:selected});
 if(t.journalField!=='ProjectLinkJournal'||t.projectionField!=='ProjectLinkProjection')throw Error('Dedicated project-link pair required');
 const initial=JSON.parse(fs.readFileSync(initialFile,'utf8'));
 if(Object.keys(initial).sort().join('|')!=='journal|projection'||!Object.values(initial).every(v=>typeof v==='string'&&v.length<60000))throw Error('Bounded initial pair required');
 fs.mkdirSync(directory,{mode:0o700});
 const save=(n,v)=>{const f=fs.openSync(path.join(directory,n),'wx',0o600);try{fs.writeFileSync(f,JSON.stringify(v,null,2));fs.fsyncSync(f);}finally{fs.closeSync(f);}};
 let writes=0,ordinal=0;
 const token=await auth.ensureAccessToken(t.resource,{log:async()=>{},logToStderr:async()=>{}},false);
 const call=async(method,url,data,headers={})=>{
  const number=++ordinal;
  if(method!=='GET'){save(number+'-send-intent.json',{method,url,data,headers,retries:0});writes++;}
  try{
   const r=await request.req({method,url,data:data?JSON.stringify(data):undefined,headers:{Authorization:'Bearer '+token,Accept:'application/json;odata=verbose','Content-Type':'application/json;odata=verbose',...headers},timeout:20000,maxRedirects:0,responseType:'text'});
   const body=r.data?typeof r.data==='string'?JSON.parse(r.data):r.data:{};save(number+'-response.json',{status:r.status,body});return body.d??body;
  }catch(e){save(number+'-failure.json',{status:e.response?.status??null,uncertain:method!=='GET',retry:false});throw Error('Project schema operation stopped; reconcile receipts before any resend');}
 };
 try{
  const meta=await call('GET',t.listUrl+'?$select=Id,Title,EnableVersioning');
  if(meta.Title!=='RIMS Outcome Evidence'||meta.EnableVersioning!==true)throw Error('Existing versioned outcome evidence register required');
  const preimage=await call('GET',t.itemUrl);save('preimage.json',preimage);
  if(preimage.Id!==t.itemId)throw Error('Exact existing item required');
  const schema=await call('GET',t.listUrl+'/fields');
  if(schema.__next||!Array.isArray(schema.results))throw Error('Complete schema required');
  const valid=f=>f?.TypeAsString==='Note'&&f.RichText===false&&f.AppendOnly===false&&f.ReadOnlyField===false;
  for(const name of [t.journalField,t.projectionField]){
   const existing=schema.results.find(f=>f.InternalName===name);
   if(existing){if(!valid(existing))throw Error('Incompatible existing field');continue;}
   await call('POST',t.listUrl+'/fields/createfieldasxml',{parameters:{__metadata:{type:'SP.XmlSchemaFieldCreationInformation'},SchemaXml:'<Field Type="Note" Name="'+name+'" StaticName="'+name+'" DisplayName="'+name+'" RichText="FALSE" AppendOnly="FALSE" NumLines="6" />',Options:0}});
   const actual=await call('GET',t.listUrl+"/fields/getbyinternalnameortitle('"+name+"')");if(!valid(actual))throw Error('Field readback mismatch');
  }
  const current=await call('GET',t.itemUrl);
  const pair={[t.journalField]:initial.journal,[t.projectionField]:initial.projection};
  if(!Object.keys(pair).every(k=>current[k]===pair[k])){
   if(!Object.keys(pair).every(k=>current[k]===null||current[k]===undefined))throw Error('Existing project data preserved; bootstrap refused');
   const etag=current.__metadata?.etag;if(typeof etag!=='string'||!/^(?:W\/)?"[^"\r\n]+"$/.test(etag))throw Error('Exact ETag required');
   await call('POST',t.itemUrl,pair,{'IF-MATCH':etag,'X-HTTP-Method':'MERGE','Content-Type':'application/json;odata=nometadata'});
  }
  const after=await call('GET',t.itemUrl);save('postimage.json',after);
  if(!Object.keys(pair).every(k=>after[k]===pair[k]))throw Error('Initialization readback mismatch');
  const excluded=new Set(['__metadata','Modified','EditorId','OData__UIVersionString',t.journalField,t.projectionField]);
  if(Object.keys(preimage).some(k=>!excluded.has(k)&&!equal(preimage[k],after[k])))throw Error('Unexpected existing item change');
  save('result.json',{outcome:'schema_initialized',writes,existing_fields_preserved:true});console.log(JSON.stringify({outcome:'schema_initialized',writes}));
 }catch(e){save('result.json',{outcome:'blocked',writes,message:e.message,retry_allowed:false});console.log(JSON.stringify({outcome:'blocked',writes}));process.exitCode=2;}
}
