// Apache-2.0. Bounded read-only SharePoint change-log query; credentials stay client-owned.
import fs from 'node:fs';
import path from 'node:path';
import {execFileSync} from 'node:child_process';

export function validatePlan(plan, prefixes) {
  if (!plan || Object.keys(plan).some(k => !['listUrl','startToken','endToken'].includes(k))) throw Error('Exact change-log plan required');
  const u = new URL(plan.listUrl);
  const match = u.pathname.match(/\/_api\/web\/lists\(guid'([0-9a-f-]{36})'\)$/i);
  if (u.protocol !== 'https:' || u.username || u.password || u.search || u.hash || !match || /%(?:2f|5c|2e)/i.test(u.pathname)) throw Error('Exact HTTPS list root required');
  if (!prefixes.some(p => p === u.href)) throw Error('Exact list root must already be pinned');
  const tokenPattern = new RegExp('^1;3;' + match[1] + ';[0-9]+;[0-9]+$', 'i');
  if (![plan.startToken,plan.endToken].every(t => typeof t === 'string' && tokenPattern.test(t))) throw Error('Native same-list start/end tokens required');
  if (plan.startToken === plan.endToken) throw Error('Distinct native token bounds required');
  return {url:u.href+'/GetChanges',listId:match[1].toLowerCase()};
}

export function makeQuery(start, end) {
  // SharePoint verbose OData serializes Edm.Int64 values as strings.
  const query = {__metadata:{type:'SP.ChangeQuery'},ChangeTokenStart:{StringValue:start},ChangeTokenEnd:{StringValue:end},FetchLimit:'100',LatestFirst:false};
  for (const flag of ['Add','Update','SystemUpdate','DeleteObject','Rename','Move','Restore','Item','List','Field','ContentType','View','File','Folder','Alert','User','Group','GroupMembershipAdd','GroupMembershipDelete','Navigation','RoleAssignmentAdd','RoleAssignmentDelete','RoleDefinitionAdd','RoleDefinitionDelete','RoleDefinitionUpdate','SecurityPolicy','Site','Web']) query[flag]=true;
  return {query};
}

export async function runGuarded({args,auth,request,pin}) {
  if (args.length!==2) throw Error('Private query plan and new private directory required');
  const [planPath,directory]=args;
  for (const p of args) execFileSync('git',['check-ignore','-q',path.resolve(p)]);
  const plan=JSON.parse(fs.readFileSync(planPath,'utf8'));
  const target=validatePlan(plan,pin.readUrlPrefixes??[]);
  const resource=new URL(plan.listUrl).origin;
  if (!pin.resources.includes(resource)) throw Error('Unpinned resource');
  fs.mkdirSync(directory,{mode:0o700});
  const save=(name,data)=>fs.writeFileSync(path.join(directory,name),JSON.stringify(data,null,2)+'\n',{flag:'wx',mode:0o600});
  const token=await auth.ensureAccessToken(resource,{log:async()=>{},logToStderr:async()=>{}},false);
  let start=plan.startToken;const changes=[];const seen=new Set([start]);
  for(let page=0;page<20;page++) {
    const body=JSON.stringify(makeQuery(start,plan.endToken));
    save('query-'+page+'.json',{url:target.url,method:'POST',body:JSON.parse(body),semanticOperation:'GetChanges read only',retries:0,maxRedirects:0});
    let response;
    try {
      response=await request.req({url:target.url,method:'POST',headers:{Authorization:'Bearer '+token,Accept:'application/json;odata=verbose','Content-Type':'application/json;odata=verbose'},data:body,responseType:'text',maxRedirects:0,timeout:20000});
    } catch(e) {
      save('failure-'+page+'.json',{status:e.response?.status??null,message:e.message,body:e.response?.data??null,noRetry:true});throw Error('Exact read-only GetChanges query failed; see private receipt');
    }
    const raw=typeof response.data==='string'?response.data:JSON.stringify(response.data);
    fs.writeFileSync(path.join(directory,'response-'+page+'.json'),raw,{flag:'wx',mode:0o600});
    save('receipt-'+page+'.json',{status:response.status,atUtc:new Date().toISOString(),method:'POST',readOnly:true});
    const d=JSON.parse(raw);const rows=d.d?.results??d.value;
    if (response.status!==200 || !Array.isArray(rows) || rows.length>100
        || rows.some(row=>!row || typeof row!=='object' || Array.isArray(row))
        || d['@odata.nextLink'] || d['odata.nextLink'] || d.d?.__next) throw Error('Unexpected change-log response/paging; retain evidence and stop');
    for(const c of rows) if(c.ListId && c.ListId.toLowerCase()!==target.listId) throw Error('Change outside exact list');
    changes.push(...rows);
    if(rows.length<100) {save('complete.json',{complete:true,changes,startToken:plan.startToken,endToken:plan.endToken,pages:page+1,nativeMutations:0});console.log('Read-only change-log complete: '+changes.length+' events');return;}
    start=rows.at(-1)?.ChangeToken?.StringValue;
    validatePlan({...plan,startToken:start},pin.readUrlPrefixes??[]);
    if(seen.has(start)) throw Error('Nonprogressing change-log cursor');seen.add(start);
  }
  throw Error('Change-log page bound reached; incomplete, no inference permitted');
}
