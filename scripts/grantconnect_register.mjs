import fs from 'node:fs';
import crypto from 'node:crypto';

export async function createRegisterRows({args,pin,auth,request}) {
  const [input,receipt,dir] = args;
  const raw = fs.readFileSync(input);
  const acceptance = JSON.parse(fs.readFileSync(receipt));
  const artifact = acceptance.files?.[0];
  const hash = crypto.createHash('sha256').update(raw).digest('hex');
  if (acceptance.status !== 'PASS_COMPLETE' || hash !== artifact?.sha256) throw Error('Cloud capture mismatch');
  const {rows,kind,count} = JSON.parse(raw);
  if (kind !== 'grantconnect_xml_register_v1' || !rows.length || rows.length !== count ||
      new Set(rows.map(r=>r.OpportunityKey)).size !== count ||
      rows.some(r=>r.Source !== 'GrantConnectRSS' || r.ReviewStatus !== 'Needs Review' || r.DeadlineRaw || !r.OpportunityKey))
    throw Error('Invalid undated GrantConnect bootstrap');
  const url = pin.grantConnectListUrl;
  if (!pin.readUrlPrefixes.includes(url) || !pin.resources.includes(new URL(url).origin)) throw Error('Unpinned register');
  const token = await auth.ensureAccessToken(new URL(url).origin,{log:async()=>{},logToStderr:async()=>{}},false);
  const send = (method,suffix,data)=>request.req({method,url:url+suffix,data,timeout:20000,maxRedirects:0,responseType:'json',transformResponse:[v=>typeof v==='string' && v ? JSON.parse(v) : v],
    headers:{Authorization:'Bearer '+token,Accept:'application/json;odata=nometadata','Content-Type':'application/json;odata=nometadata'}});
  const info=(await send('get','?$select=Title')).data;
  if(info.Title!=='Grants Registry') throw Error('Register identity drift');
  const field=(await send('get',"/fields/getbyinternalnameortitle('OpportunityKey')?$select=EnforceUniqueValues")).data;
  if(!field.EnforceUniqueValues) throw Error('Unique register key required');
  const current=(await send('get','/items?$select=OpportunityKey,EvidenceHash&$top=5000')).data;
  if(!Array.isArray(current.value) || Object.keys(current).some(k=>k.endsWith('nextLink'))) throw Error('Incomplete register snapshot');
  const existing=new Map(current.value.map(r=>[r.OpportunityKey,r.EvidenceHash]));
  for(const r of rows) if(existing.has(r.OpportunityKey) && existing.get(r.OpportunityKey)!==r.EvidenceHash) throw Error('Existing row conflict');
  fs.mkdirSync(dir);
  for(const r of rows){
    if(existing.has(r.OpportunityKey)) continue;
    const data=Object.fromEntries(['Title','OpportunityKey','Source','SourceID','Description','ReviewStatus','Status','EvidenceHash','RetrievedUTC','RetrievedTimestampStatus','DeadlinePrecision','DeadlineTemporalStatus'].map(k=>[k,r[k]]));
    data.URL={Url:r.URL,Description:'GrantConnect'};
    fs.appendFileSync(dir+'/intents.jsonl',JSON.stringify(r.OpportunityKey)+'\n');
    try {const result=await send('post','/items',data);fs.appendFileSync(dir+'/results.jsonl',JSON.stringify([r.OpportunityKey,result.status])+'\n');}
    catch(e){throw Error('Register create failed: '+e.response?.status+' '+JSON.stringify(e.response?.data?.error?.message));}
  }
}
