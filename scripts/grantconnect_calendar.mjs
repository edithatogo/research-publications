// SPDX-License-Identifier: Apache-2.0
import fs from 'node:fs';
import crypto from 'node:crypto';
const hash = s => crypto.createHash('sha256').update(s).digest('hex');

export async function publishClosingDates({args,pin,auth,request}) {
  const [registerPath, datesPath, journal] = args;
  const rows = JSON.parse(fs.readFileSync(registerPath)).rows;
  const byKey = new Map(rows.map(row=>[row.OpportunityKey,row]));
  const {dates,unresolved} = JSON.parse(fs.readFileSync(datesPath));
  const keys = [...dates.map(d=>d.OpportunityKey),...unresolved];
  if(keys.length!==byKey.size || new Set(keys).size!==keys.length || keys.some(k=>!byKey.has(k))) throw Error('Source coverage mismatch');
  const lists=[pin.grantConnectListUrl,pin.grantConnectCalendarUrl];
  if(lists.some(u=>!pin.readUrlPrefixes.includes(u)) || lists[0]===lists[1]) throw Error('Unqualified lists');
  const origin=new URL(lists[0]).origin;
  if(!pin.resources.includes(origin)||new URL(lists[1]).origin!==origin) throw Error('Invalid audience');
  const token=await auth.ensureAccessToken(origin,{log:async()=>{},logToStderr:async()=>{}},false);
  const send=async(method,url,data,headers={})=>(await request.req({method,url,data,maxRedirects:0,timeout:20000,
    responseType:'json',transformResponse:[v=>typeof v==='string' && v?JSON.parse(v):v],
    headers:{Authorization:'Bearer '+token,Accept:'application/json;odata=minimalmetadata','Content-Type':'application/json;odata=nometadata',...headers}})).data;
  async function inventory(url,fields,key){
    const d=await send('get',url+'/items?$top=5000&$select='+fields);
    if(!Array.isArray(d.value)||Object.keys(d).some(k=>k.endsWith('nextLink')))throw Error('Incomplete list');
    const m=new Map(d.value.map(r=>[r[key],r]));if(m.size!==d.value.length)throw Error('Duplicate list key');return m;
  }
  const register=await inventory(lists[0],'Id,OpportunityKey,SourceID,DeadlineRaw,DeadlineUTCInstant,ReviewStatus','OpportunityKey');
  const calendar=await inventory(lists[1],'Id,DeadlineKey,OpportunityKey,Revision,ReviewStatus','DeadlineKey');
  fs.mkdirSync(journal);
  async function write(url,record,body,key){
    const tag=record?.['odata.etag']??record?.['@odata.etag'];
    if(record && (!tag||tag==='*'))throw Error('Missing item version');
    fs.appendFileSync(journal+'/intent.jsonl',JSON.stringify([key,hash(JSON.stringify(body))])+'\n');
    await send('post',url+'/items'+(record?'('+record.Id+')':''),body,record?{'IF-MATCH':tag,'X-HTTP-Method':'MERGE'}:{});
  }
  for(const d of dates){
    const row=byKey.get(d.OpportunityKey), saved=register.get(d.OpportunityKey);
    if(!saved || saved.SourceID!==row.SourceID || row.URL!==d.SourceURL || !d.DeadlineUTCInstant)throw Error('Register identity drift');
    const key='GC-CLOSE:'+hash(row.OpportunityKey).slice(0,32);
    const revision=hash(JSON.stringify([key,d.DeadlineUTCInstant,d.SourceURL]));
    const prior=calendar.get(key);
    if(prior && (prior.OpportunityKey!==row.OpportunityKey||prior.ReviewStatus!=='Source confirmed'))throw Error('Calendar ownership drift');
    if(saved.DeadlineUTCInstant!==d.DeadlineUTCInstant){
      if(saved.ReviewStatus!=='Needs Review'||(saved.DeadlineRaw && !prior))throw Error('Existing date requires reconciliation');
      await write(lists[0],saved,{Deadline:d.DeadlineUTCInstant,DeadlineRaw:d.DeadlineRaw,DeadlineTimezone:'Australia/Sydney',
        DeadlineUTCInstant:d.DeadlineUTCInstant,DeadlineBrisbaneDate:d.DeadlineBrisbaneDate,DeadlinePrecision:'day'},row.OpportunityKey);
    }
    if(prior?.Revision!==revision)await write(lists[1],prior,{Title:row.Title,OpportunityKey:row.OpportunityKey,DeadlineKey:key,
      SourceURL:{Url:row.URL,Description:'Official closing date'},CalculatedDate:d.DeadlineUTCInstant,Calendar_x0020_day:d.DeadlineSourceDate,
      DeadlinePrecision:'day',ReviewStatus:'Source confirmed',Revision:revision,RevisionApplied:true,Cancelled:false},key);
  }
}
