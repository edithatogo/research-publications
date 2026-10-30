// SPDX-License-Identifier: Apache-2.0
// Typed existing-register adapter; same retained client, no automatic write retry.
import fs from 'node:fs';
import path from 'node:path';
import {isDeepStrictEqual as equal} from 'node:util';
export const fields=['AwardID','Confidence','EvidenceURL','FromKey','RelationshipKey','RelationshipType','ReviewStatus','ToKey','RelationshipHistory'];
const fail=m=>{throw Error(m);};
export function validateTarget(pin,t){
  const u=new URL(t.listUrl);
  if(Object.keys(t).sort().join('|')!=='listUrl|title' || t.title!=='Grant Relationships'
    ||u.protocol!=='https:'||u.username||u.password||u.search||u.hash
    ||!/^.*\/_api\/web\/lists\(guid'[0-9a-f-]{36}'\)$/.test(u.pathname)
    ||!pin.resources.includes(u.origin)||!(pin.readUrlPrefixes??[]).includes(u.href)) fail('Existing pinned Grant Relationships list required');
  return t;
}
export async function execute({target,plan,send,save}){
  const base=target.listUrl;
  const call=async(method,url,data,headers={})=>{
    let r;try{r=await send({method,url,data:data?JSON.stringify(data):undefined,headers:{Accept:'application/json;odata=verbose','Content-Type':'application/json;odata=nometadata',...headers},timeout:20000,maxRedirects:0,responseType:'text'});}
    catch(e){const error=Error('Relationship request stopped: '+(e.response?.status??'transport_error'));error.status=e.response?.status??null;throw error;}
    const body=r.data?typeof r.data==='string'?JSON.parse(r.data):r.data:{};
    return body.d??body;
  };
  const meta=await call('GET',base+'?$select=Id,Title,EnableVersioning');save('metadata.json',meta);
  if(meta.Title!==target.title||meta.EnableVersioning!==true)fail('Versioned existing relationship register required');
  const schema=await call('GET',base+'/fields');save('schema.json',schema);
  if(schema.__next||!Array.isArray(schema.results))fail('Complete schema required');
  const byName=Object.fromEntries(schema.results.map(f=>[f.InternalName,f]));
  for(const name of fields.filter(n=>n!=='RelationshipHistory')){
    const f=byName[name];const type=name==='EvidenceURL'?'URL':['Confidence','RelationshipType'].includes(name)?'Choice':'Text';
    if(!f||f.TypeAsString!==type||f.ReadOnlyField!==false)fail('Typed relationship schema mismatch: '+name);
  }
  if(byName.RelationshipKey.EnforceUniqueValues!==true||byName.RelationshipKey.Indexed!==true)fail('Unique indexed relationship identity required');
  const journal=byName.RelationshipHistory;
  const validJournal=f=>f?.TypeAsString==='Note'&&f.RichText===false&&f.AppendOnly===false&&f.ReadOnlyField===false;
  if(journal&&!validJournal(journal))fail('Existing history field incompatible; no overwrite');
  if(plan.operation==='schema'){
    if(journal)return {outcome:'schema_present',writes:0};
    const data={parameters:{__metadata:{type:'SP.XmlSchemaFieldCreationInformation'},SchemaXml:'<Field Type="Note" Name="RelationshipHistory" StaticName="RelationshipHistory" DisplayName="RelationshipHistory" RichText="FALSE" AppendOnly="FALSE" NumLines="6" />',Options:0}};
    save('send-intent.json',{target,plan,data,retries:0,redirects:0});
    let error=null;try{await call('POST',base+'/fields/createfieldasxml',data,{'Content-Type':'application/json;odata=verbose'});}catch(e){error=e.status??'transport_error';}
    let after;try{after=await call('GET',base+"/fields/getbyinternalnameortitle('RelationshipHistory')");save('postimage.json',after);}catch{return {outcome:'unknown',writes:1,retry_allowed:false,error};}
    return {outcome:validJournal(after)?'schema_present':'conflict',writes:1,retry_allowed:false,error};
  }
  if(!journal)fail('Prepare the additive history field first');
  if(!['read','apply'].includes(plan.operation))fail('Unsupported relationship operation');
  const key=plan.operation==='apply'?plan.after.RelationshipKey:plan.key;
  if(!/^REL:[0-9a-f]{24}$/.test(key))fail('Exact normalized relationship key required');
  for(const name of ['Confidence','RelationshipType'])if(plan.operation==='apply'&&!(byName[name].Choices?.results??byName[name].Choices).includes(plan.after[name]))fail('Unsupported native choice');
  const itemId=plan.item_id;
  if(itemId!==null&&(!Number.isSafeInteger(itemId)||itemId<1))fail('Exact item identity required');
  const read=async label=>{
    const result=await call('GET',base+'/items'+(itemId?'('+itemId+')':'?'+new URLSearchParams({'$filter':"RelationshipKey eq '"+key+"'",'$top':'2'})));
    if(result.__next)fail('Incomplete identity lookup');
    const rows=itemId?[result]:result.results;
    if(!Array.isArray(rows)||rows.length>1)fail('Ambiguous relationship identity');
    const row=rows[0];const snapshot=row?{item_id:row.Id,etag:row.__metadata?.etag,fields:Object.fromEntries(fields.map(f=>[f,row[f]??'']))}:null;
    if(snapshot&&(!Number.isSafeInteger(snapshot.item_id)||typeof snapshot.etag!=='string'))fail('Incomplete native item identity');
    if(snapshot?.fields.EvidenceURL) snapshot.fields.EvidenceURL={Url:snapshot.fields.EvidenceURL.Url,Description:snapshot.fields.EvidenceURL.Description};
    save(label,{snapshot,raw:row??null});return snapshot;
  };
  const before=await read('preimage.json');
  if(plan.operation==='read')return {outcome:'read',writes:0,snapshot:before};
  if(before&&equal(before.fields,plan.after))return {outcome:'unchanged_replay',writes:0,snapshot:before};
  if(plan.before===null?before!==null:!before||before.etag!==plan.etag||!equal(before.fields,plan.before))fail('Existing or human-edited relationship differs; no write sent');
  save('send-intent.json',{target,plan,retries:0,redirects:0});
  const data={...plan.after};if(!itemId)data.Title='RIMS relationship revision';
  let error=null;try{await call('POST',base+'/items'+(itemId?'('+itemId+')':''),data,itemId?{'IF-MATCH':plan.etag,'X-HTTP-Method':'MERGE'}:{});}catch(e){error=e.status??'transport_error';}
  let after;try{after=await read('postimage.json');}catch{return {outcome:'unknown',writes:1,retry_allowed:false,error};}
  return {outcome:after&&equal(after.fields,plan.after)?'candidate_present':'conflict',writes:1,retry_allowed:false,error,snapshot:after};
}
export async function runGuarded({args,auth,request,pin}){
  const [targetPath,planPath,directory]=args;const target=validateTarget(pin,JSON.parse(fs.readFileSync(targetPath,'utf8'))),plan=JSON.parse(fs.readFileSync(planPath,'utf8'));
  fs.mkdirSync(directory,{mode:0o700});
  const save=(name,v)=>{const fd=fs.openSync(path.join(directory,name),'wx',0o600);try{fs.writeFileSync(fd,JSON.stringify(v,null,2));fs.fsyncSync(fd);}finally{fs.closeSync(fd);}};
  const token=await auth.ensureAccessToken(new URL(target.listUrl).origin,{log:async()=>{},logToStderr:async()=>{}},false);
  let result;
  try{result=await execute({target,plan,save,send:c=>request.req({...c,headers:{...c.headers,Authorization:'Bearer '+token}})});}
  catch(e){result={outcome:'blocked',writes:fs.existsSync(path.join(directory,'send-intent.json'))?1:0,retry_allowed:false,status:e.status??null,message:e.message};}
  save('result.json',result);console.log(JSON.stringify({outcome:result.outcome,writes:result.writes}));
  if(!['read','schema_present','candidate_present','unchanged_replay'].includes(result.outcome))process.exitCode=2;
}
