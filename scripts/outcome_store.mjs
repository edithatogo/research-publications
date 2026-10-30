// SPDX-License-Identifier: Apache-2.0
// Same-client SharePoint transport. Imported only after the qualified wrapper's
// identity checks. Direct Axios requests avoid the SDK's recursive write retry.
import fs from 'node:fs';
import path from 'node:path';

const fail = message => { throw Error(message); };
const keys = (v, expected) => v && typeof v === 'object' && !Array.isArray(v)
  && Object.keys(v).sort().join('|') === [...expected].sort().join('|');
export function validateTarget(pin) {
  const t = pin.outcomeTarget;
  if (!keys(t, ['listUrl','itemId','journalField','projectionField'])) fail('Exact outcome target required');
  const u = new URL(t.listUrl);
  if (u.protocol !== 'https:' || u.username || u.password || u.search || u.hash
      || !/\/_api\/web\/lists\(guid'[0-9a-f-]{36}'\)$/.test(u.pathname)
      || /%(?:2f|5c|2e)/i.test(u.pathname) || !pin.resources.includes(u.origin)
      || !(pin.readUrlPrefixes ?? []).includes(u.href)) fail('Outcome list must already be pinned');
  if (!Number.isSafeInteger(t.itemId) || t.itemId < 1) fail('Existing positive item identity required');
  if (![t.journalField,t.projectionField].every(f => typeof f === 'string' && /^[A-Za-z][A-Za-z0-9_]{0,31}$/.test(f))
      || t.journalField === t.projectionField || [t.journalField,t.projectionField].some(f => ['Id','ID','Title','__metadata'].includes(f))) fail('Distinct dedicated text fields required');
  return {...t, resource:u.origin, itemUrl:u.href+'/items('+t.itemId+')'};
}
export function validatePlan(plan) {
  if (keys(plan,['operation']) && plan.operation === 'read') return;
  if (!keys(plan,['operation','etag','before','after']) || plan.operation !== 'apply'
      || typeof plan.etag !== 'string' || !/^(?:W\/)?"[^"\r\n]+"$/.test(plan.etag)) fail('Exact conditional update plan required');
  for (const value of [plan.before,plan.after]) {
    if (!keys(value,['journal','projection']) || !Object.values(value).every(v => typeof v === 'string' && v.length <= 60000)) fail('Bounded complete field preimages required');
  }
  // Domain validation is performed by outcome_intake.py before this transport.
  // Both fields are committed together; no partial projection publication.
  for (const name of ['journal','projection']) JSON.parse(plan.after[name]);
}
const equal = (snapshot, values) => snapshot.journal === values.journal && snapshot.projection === values.projection;

export async function execute({target, plan, send, save}) {
  validatePlan(plan);
  const schemaResponse = await send({url:target.listUrl+'/fields?$select=InternalName,TypeAsString,RichText,AppendOnly,ReadOnlyField',
    method:'GET',headers:{Accept:'application/json;odata=verbose'},maxRedirects:0,timeout:20000,responseType:'text'});
  const schema = typeof schemaResponse.data === 'string' ? JSON.parse(schemaResponse.data) : schemaResponse.data;
  if (schemaResponse.status !== 200 || !Array.isArray(schema.d?.results) || schema.d.__next) fail('Complete field schema required');
  for (const name of [target.journalField,target.projectionField]) {
    const rows = schema.d.results.filter(f => f.InternalName === name);
    if (rows.length !== 1 || rows[0].TypeAsString !== 'Note' || rows[0].RichText !== false
        || rows[0].AppendOnly !== false || rows[0].ReadOnlyField !== false) fail('Dedicated plain text writable fields required');
  }
  save('schema.json',schema);
  const read = async label => {
    const response = await send({url:target.itemUrl+'?$select=Id,'+target.journalField+','+target.projectionField,
      method:'GET',headers:{Accept:'application/json;odata=verbose'},maxRedirects:0,timeout:20000,responseType:'text'});
    if (response.status !== 200) fail('Unexpected item read status');
    const body = typeof response.data === 'string' ? JSON.parse(response.data) : response.data;
    const d = body.d;
    if (!d || d.Id !== target.itemId || typeof d[target.journalField] !== 'string'
        || typeof d[target.projectionField] !== 'string' || typeof d.__metadata?.etag !== 'string'
        || !/^(?:W\/)?"[^"\r\n]+"$/.test(d.__metadata.etag)) fail('Incomplete exact item readback');
    const snapshot = {item_id:d.Id,etag:d.__metadata.etag,journal:d[target.journalField],projection:d[target.projectionField]};
    save(label,snapshot); return snapshot;
  };
  const before = await read('preimage.json');
  if (plan.operation === 'read') return {outcome:'read',writes:0,snapshot:before};
  if (equal(before,plan.after)) return {outcome:'unchanged_replay',writes:0,snapshot:before};
  if (before.etag !== plan.etag || !equal(before,plan.before)) fail('Concurrent edit; no write sent');
  // Exclusive durable marker precedes the network call; a crash never permits
  // automatic resubmission in this directory. Recover by a fresh read only.
  save('send-intent.json',{at:new Date().toISOString(),target,plan,retries:0,redirects:0});
  let errorStatus = null;
  try {
    const response = await send({url:target.itemUrl,method:'POST',maxRedirects:0,timeout:20000,responseType:'text',
      headers:{Accept:'application/json;odata=verbose','Content-Type':'application/json;odata=nometadata','IF-MATCH':plan.etag,'X-HTTP-Method':'MERGE'},
      data:JSON.stringify({[target.journalField]:plan.after.journal,[target.projectionField]:plan.after.projection})});
    if (response.status !== 204) errorStatus = response.status;
  } catch (error) { errorStatus = error.response?.status ?? 'transport_error'; }
  let after;
  try { after = await read('postimage.json'); }
  catch { return {outcome:'unknown',writes:1,retry_allowed:false,error_status:errorStatus}; }
  const outcome = equal(after,plan.after) ? 'candidate_present'
    : equal(after,plan.before) && after.etag === plan.etag ? 'preimage_present' : 'conflict';
  return {outcome,writes:1,retry_allowed:false,error_status:errorStatus,snapshot:after};
}

export async function runGuarded({args,auth,request,pin}) {
  const [planPath,directory] = args;
  const target = validateTarget(pin), plan = JSON.parse(fs.readFileSync(planPath,'utf8'));
  validatePlan(plan);
  fs.mkdirSync(directory,{mode:0o700});
  const save = (name,value) => {
    const fd = fs.openSync(path.join(directory,name),'wx',0o600);
    try { fs.writeFileSync(fd,JSON.stringify(value,null,2)+'\n'); fs.fsyncSync(fd); }
    finally { fs.closeSync(fd); }
  };
  const token = await auth.ensureAccessToken(target.resource,{log:async()=>{},logToStderr:async()=>{}},false);
  const send = config => request.req({...config,headers:{...config.headers,Authorization:'Bearer '+token}});
  const result = await execute({target,plan,send,save});
  save('result.json',result);
  console.log(JSON.stringify({outcome:result.outcome,writes:result.writes}));
  if (!['read','candidate_present','unchanged_replay'].includes(result.outcome)) process.exitCode = 2;
}
