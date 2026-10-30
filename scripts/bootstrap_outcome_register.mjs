// SPDX-License-Identifier: Apache-2.0
// Fixed, user-authorized isolated register bootstrap using the retained client.
import fs from 'node:fs';
import path from 'node:path';
export function target(pin, site) {
  const u=new URL(site);
  if(u.protocol!=='https:' || u.username || u.password || u.search || u.hash || site.endsWith('/')) throw Error('Exact site required');
  const root=site+'/_api/web/lists';
  if(!pin.resources.includes(u.origin) || !pin.readUrlPrefixes.some(p=>p.startsWith(root+"(guid'"))) throw Error('Site must have retained list pins');
  return root;
}
export async function runGuarded({args,auth,request,pin}) {
  const [site,directory]=args,root=target(pin,site);
  fs.mkdirSync(directory,{mode:0o700});
  const save=(name,v)=>{const fd=fs.openSync(path.join(directory,name),'wx',0o600);try{fs.writeFileSync(fd,JSON.stringify(v,null,2));fs.fsyncSync(fd);}finally{fs.closeSync(fd);}};
  const token=await auth.ensureAccessToken(new URL(site).origin,{log:async()=>{},logToStderr:async()=>{}},false);
  let n=0;
  const call=async(method,url,data)=>{
    const id=++n;save(id+'-intent.json',{method,url,data,retries:0,redirects:0});
    try{const r=await request.req({method,url,data:data?JSON.stringify(data):undefined,headers:{Authorization:'Bearer '+token,Accept:'application/json;odata=verbose','Content-Type':'application/json;odata=verbose'},maxRedirects:0,timeout:20000,responseType:'text'});const body=r.data?typeof r.data==='string'?JSON.parse(r.data):r.data:{};save(id+'-response.json',{status:r.status,body});return body.d??body;}
    catch(e){save(id+'-failure.json',{status:e.response?.status??null,uncertain:method!=='GET',retry:false});throw Error('Bootstrap stopped; reconcile saved intent before another write');}
  };
  const inventory=await call('GET',root+'?$select=Id,Title&$top=100');
  if(inventory.__next || !Array.isArray(inventory.results)) throw Error('Complete inventory required');
  const name='RIMS Outcome Evidence';
  if(inventory.results.some(r=>r.Title.toLowerCase()===name.toLowerCase())) throw Error('Existing register requires reuse; no creation');
  const list=await call('POST',root,{__metadata:{type:'SP.List'},Title:name,Description:'Bounded RIMS outcome evidence revisions and derived projection; fictional qualification only until accepted.',BaseTemplate:100,EnableVersioning:true});
  if(!/^[0-9a-f-]{36}$/i.test(list.Id)) throw Error('Missing created list identity; stop');
  const listUrl=root+"(guid'"+list.Id+"')";
  for(const field of ['OutcomeJournal','OutcomeProjection']) await call('POST',listUrl+'/fields/createfieldasxml',{parameters:{__metadata:{type:'SP.XmlSchemaFieldCreationInformation'},SchemaXml:'<Field Type="Note" Name="'+field+'" StaticName="'+field+'" DisplayName="'+field+'" RichText="FALSE" AppendOnly="FALSE" NumLines="6" />',Options:0}});
  const meta=await call('GET',listUrl+'?$select=Id,EnableVersioning,ListItemEntityTypeFullName');
  if(meta.EnableVersioning!==true || !meta.ListItemEntityTypeFullName) throw Error('Versioned list metadata required');
  const item=await call('POST',listUrl+'/items',{__metadata:{type:meta.ListItemEntityTypeFullName},Title:'Fictional qualification journal',OutcomeJournal:'{"entries":[],"version":1}',OutcomeProjection:'{}'});
  if(!Number.isSafeInteger(item.Id)) throw Error('Created item identity missing; reconcile only');
  save('target.json',{listUrl,itemId:item.Id,journalField:'OutcomeJournal',projectionField:'OutcomeProjection'});
  save('result.json',{created:true,nativeAcceptance:false,recovery:'Retain exact created list/item identities. No automatic delete or retry.',operations:n});
  console.log('Outcome register bootstrap complete; no flow run or model change.');
}
