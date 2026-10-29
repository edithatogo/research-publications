// Apache-2.0. Exact G06 list inspection through the retained Toolkit workload.
import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
const [bindingPath, scopePath, directory, phase='inspect', recoveryEvidence] = process.argv.slice(2);
if(!['inspect','fixture','recover','apply'].includes(phase))throw Error('Inspection, candidate delivery or exact fixture qualification/recovery only');
if (!directory) throw Error('Private binding, exact scope and new evidence directory required');
const bindingFile=fs.realpathSync(bindingPath), ownerRoot=path.resolve(path.dirname(bindingFile),'../../..');
for (const p of [bindingFile,scopePath,directory]) execFileSync('git',['check-ignore','-q',path.resolve(p)],{cwd:ownerRoot});
const pin=JSON.parse(fs.readFileSync(bindingFile)), scope=JSON.parse(fs.readFileSync(scopePath));
const root=scope.list_url;
if (!pin.readUrlPrefixes?.includes(root) || !/^https:\/\/[a-z0-9-]+\.sharepoint\.com\/[^?#]+\/_api\/web\/lists\(guid'[a-f0-9-]{36}'\)$/i.test(root)) throw Error('Exact pinned G06 list required');
const resource=new URL(root).origin;
if (!pin.resources.includes(resource)) throw Error('Unpinned resource');
const pkg=JSON.parse(fs.readFileSync(path.join(pin.sdkRoot,'package.json')));
if(pkg.name!=='@pnp/cli-microsoft365'||pkg.version!==pin.sdkVersion)throw Error('SDK drift');
fs.mkdirSync(directory,{mode:0o700});
const save=(n,x)=>fs.writeFileSync(path.join(directory,n+'.json'),JSON.stringify(x,null,2)+'\n',{flag:'wx',mode:0o600});
const {acquireWorkloadLock}=await import(pathToFileURL(path.join(ownerRoot,'scripts/m365_workload_lock.mjs')));
const lock=path.join(path.dirname(bindingFile),'.m365-qualified.lock');await acquireWorkloadLock(lock);
fs.writeFileSync(path.join(lock,'owner.json'),JSON.stringify({pid:process.pid,mode:'g06-native-qualification',started:new Date().toISOString()}),{mode:0o600});
process.once('exit',()=>fs.rmSync(lock,{recursive:true}));
const {default:auth}=await import(pathToFileURL(path.join(pin.sdkRoot,'dist/Auth.js')));
const {default:request}=await import(pathToFileURL(path.join(pin.sdkRoot,'dist/request.js')));
const quiet={log:async()=>{},logToStderr:async()=>{}};request.logger=quiet;request.debug=false;
await auth.restoreAuth();const same=(a,b)=>typeof a==='string'&&typeof b==='string'&&a.toLowerCase()===b.toLowerCase();
const guard=()=>{const c=auth.connection;if(c.name!==pin.connectionName||!same(c.appId,pin.appId)||!same(c.tenant,pin.tenantId)||c.authType!=='browser'||!c.active)throw Error('Toolkit connection drift');};guard();
const client=await auth.getPublicClient(quiet,false), account=auth.connection.identityId?await client.getTokenCache().getAccountByLocalId(auth.connection.identityId):null;
if(!account||!same(account.username,pin.username)||!same(account.tenantId,pin.tenantId)||(pin.objectId&&!same(account.localAccountId,pin.objectId)))throw Error('Selected identity drift');
for(const m of ['ensureAccessTokenWithBrowser','ensureAccessTokenWithDeviceCode','ensureAccessTokenWithPassword','retrieveAuthCodeWithBrowser'])auth[m]=async()=>{throw Error('INTERACTIVE_AUTH_BLOCKED; use established explicit renewal');};
const silent=auth.ensureAccessTokenSilent.bind(auth);
auth.ensureAccessTokenSilent=async function(r,...args){guard();if(r!==resource)throw Error('Wrong resource');const t=await silent(r,...args);if(!t.accessToken||!(new Date(t.expiresOn)>new Date())||!same(t.account?.username,pin.username)||!same(t.account?.tenantId,pin.tenantId)||(t.idTokenClaims?.aud&&!same(t.idTokenClaims.aud,pin.appId)))throw Error('Silent identity mismatch');return t;};
const token=await auth.ensureAccessToken(resource,quiet,false);guard();
let active;
const bodyHash=x=>createHash('sha256').update(typeof x==='string'?x:JSON.stringify(x??null)).digest('hex');
request.req.interceptors.request.use(c=>{if(!active||active.sent||c.url!==active.url||(c.method??'get').toLowerCase()!==active.method||bodyHash(c.data)!==active.bodyHash)throw Error('Duplicate/out-of-scope transport');active.sent=true;c.maxRedirects=0;c.timeout=20000;return c;});
async function call(name,url,method='get',data){
 active={url,method,sent:false,bodyHash:bodyHash(data)};save(name+'-request',{url,method,body:data,semanticReadOnly:method==='get'||url.endsWith('/GetAllRules()'),automaticRetries:0});
 try{const r=await request.req({url,method,data,headers:{Authorization:'Bearer '+token,Accept:'application/json;odata=verbose','Content-Type':'application/json;odata=verbose'},responseType:'json',maxRedirects:0,timeout:20000});save(name,r.data);return r.data;}
 catch(e){save(name+'-failure',{status:e.response?.status,message:e.message,body:e.response?.data});throw Error('G06 exact operation failed; see private evidence');}
}
const meta=await call('metadata',root+'?$select=Id,Title,ItemCount,EnableVersioning,MajorVersionLimit,HasUniqueRoleAssignments,EffectiveBasePermissions,ListItemEntityTypeFullName');
const subscriptions=await call('subscriptions',root+'/subscriptions'),receivers=await call('receivers',root+'/EventReceivers');
const rules=await call('rules',root+'/GetAllRules()','post',{includeQuicksteps:true,includeAutomaticRules:true});
const site=root.split('/_api/')[0];
const alerts=await call('alerts',site+'/_api/web/alerts?$expand=List,User&$select=ID,Title,Status,DeliveryChannels,EventType,AlertFrequency,List/Id,List/Title,User/Id');
const roles=await call('roles',root+'/RoleAssignments?$expand=Member,RoleDefinitionBindings');
const user=await call('user',site+'/_api/web/currentuser?$select=Id');
const {notificationGate}=await import(pathToFileURL(path.join(ownerRoot,'scripts/grants_canonical_promotion.mjs')));
const collection=x=>({value:x.d?.results??x.value});
const effects=notificationGate({rules:{value:rules.d?.GetAllRules?.results??rules.value},subscriptions:collection(subscriptions),receivers:collection(receivers),alerts:collection(alerts),roles:collection(roles),userId:(user.d??user).Id,listId:(meta.d??meta).Id});
save('effects-accepted',effects);
if(phase==='apply'){
 const {submitCandidate}=await import('./g06_candidate_writer.mjs');
 const packetFile=scope.incremental_packet;execFileSync('git',['check-ignore','-q',path.resolve(packetFile)],{cwd:ownerRoot});
 const bytes=fs.readFileSync(packetFile);if(createHash('sha256').update(bytes).digest('hex')!==scope.incremental_sha256)throw Error('Incremental packet drift');
 const packet=JSON.parse(bytes);if(packet.kind!=='g06-incremental-prepared-v1'||packet.native_verified!==false||!Array.isArray(packet.relationships)||packet.coverage?.confirmed_funding!==0)throw Error('Prepared candidate-only packet required');
 const journal=scope.journal_root;execFileSync('git',['check-ignore','-q',path.resolve(journal)],{cwd:ownerRoot});if(!fs.existsSync(journal))throw Error('Reuse existing qualified persistent journal directory');
 const rows=d=>{const x=d.d??d;if(x.__next||x['odata.nextLink']||x['@odata.nextLink']||!Array.isArray(x.results??x.value))throw Error('Incomplete collection');return x.results??x.value;};
 const before=rows(await call('delivery-before',root+'/items?$top=1000'));
 const fields=rows(await call('delivery-fields',root+'/fields?$top=1000'));const key=fields.find(f=>f.InternalName==='RelationshipKey');
 if(!key?.Required||!key.Indexed||!key.EnforceUniqueValues)throw Error('Unique native key protection changed');
 if(new Set(before.map(r=>r.RelationshipKey)).size!==before.length||new Set(packet.relationships.map(r=>r.RelationshipKey)).size!==packet.relationships.length)throw Error('Duplicate relationship key');
 let readIndex=0,created=0,preserved=0;const results=[];
 const known=new Map(before.map(r=>[r.RelationshipKey,r]));
 const {validatePacket}=await import('./g06_incremental.mjs');
 for(const source of Object.values(packet.state.sources))validatePacket(source.packet);
 for(const r of packet.relationships){
  if(!known.has(r.RelationshipKey)){
   const pubRoot=scope.publication_list_url;
   if(!pin.readUrlPrefixes.includes(pubRoot)||!pubRoot.startsWith(site+"/_api/web/lists(guid'"))throw Error('Exact publication source read pin required before candidate creation');
   const provenance=packet.provenance.find(x=>x.key===r.RelationshipKey)?.sources;
   if(!provenance?.length)throw Error('Candidate source provenance missing');
   for(const [index,source] of provenance.entries()){
    const c=source.context;if(!Number.isSafeInteger(c.RegistryItemID)||c.RegistryItemID<1)throw Error('Exact source item identity required');
    const result=await call('source-guard-'+created+'-'+index,pubRoot+'/items('+c.RegistryItemID+')?$select=Id,field_1,field_2,field_17,GrantIDs,FunderNames');
    const current=result.d??result;
    if(current.field_1!==c.PublicationSourceKey||current.field_2!==c.RegistryPublicationKey||current.field_17==='Excluded'||current.GrantIDs!==c.RetainedGrantIDs||current.FunderNames!==c.RetainedFunderLabels)throw Error('Native publication source drift; preserve relationships and requalify source packet');
   }
  }
  const desired={...r,EvidenceURL:{Url:r.EvidenceURL}};
  let attempted=false;
  const result=await submitCandidate({listUrl:root,pinnedListUrl:root,row:desired,journalRoot:journal,
   readByKey:async k=>attempted?rows(await call('delivery-key-'+(++readIndex),root+"/items?$filter=RelationshipKey eq '"+k+"'")):(known.has(k)?[known.get(k)]:[]),
   createOnce:async value=>{attempted=true;return call('delivery-create-'+(++created),root+'/items','post',{__metadata:{type:(meta.d??meta).ListItemEntityTypeFullName},...value});}});
  if(result.state==='preserved')preserved++;results.push({key:r.RelationshipKey,state:result.state,item:result.item});
 }
 const after=rows(await call('delivery-after',root+'/items?$top=1000'));
 const clean=x=>Array.isArray(x)?x.map(clean):x&&typeof x==='object'?Object.fromEntries(Object.keys(x).sort().filter(k=>k!=='__metadata').map(k=>[k,clean(x[k])])):x;
 for(const original of before){const current=after.find(r=>r.Id===original.Id);if(!current||JSON.stringify(clean(current))!==JSON.stringify(clean(original))||current.__metadata?.etag!==original.__metadata?.etag)throw Error('Native review/history preservation failed');}
 if(after.length!==before.length+created)throw Error('Unexpected native row count delta');
 save('incremental-acceptance',{native_verified:true,created,preserved,original_rows_preserved:true,missing_source_retirements:0,results,current_rows:after,coverage:packet.coverage,at:new Date().toISOString()});
}
if(['fixture','recover'].includes(phase)){
 const {submitCandidate}=await import('./g06_candidate_writer.mjs');
 const f=scope.fixture;
 if(!f||f.Title!=='TEST_ONLY:G06:WRITER:20261029'||f.EvidenceURL?.Url!=='https://example.invalid/g06-writer-qualification-20261029'||scope.fixture_only!==true)throw Error('Exact fictional fixture scope required');
 const journal=scope.journal_root;execFileSync('git',['check-ignore','-q',path.resolve(journal)],{cwd:ownerRoot});
 if(!fs.existsSync(journal))fs.mkdirSync(journal,{mode:0o700});
 const basis=JSON.stringify([f.RelationshipType,f.FromKey,f.ToKey,f.AwardID,f.EvidenceURL.Url]);
 if(f.RelationshipKey!=='REL:'+createHash('sha256').update(basis).digest('hex').slice(0,24))throw Error('Typed fixture identity mismatch');
 const readRows=d=>{const x=d.d??d;if(x.__next||x['odata.nextLink']||x['@odata.nextLink']||!Array.isArray(x.results??x.value))throw Error('Incomplete collection');return x.results??x.value;};
 const recovering=phase==='recover';
 if(recovering)execFileSync('git',['check-ignore','-q',path.resolve(recoveryEvidence)],{cwd:ownerRoot});
 const prior=n=>JSON.parse(fs.readFileSync(path.join(recoveryEvidence,n+'.json')));
 const current=readRows(await call('items-before',root+'/items?$top=1000'));
 const before=recovering?readRows(prior('items-before')):current;
 if(before.some(r=>r.RelationshipKey===f.RelationshipKey))throw Error('Existing fixture requires reconciliation, never recreate');
 if(recovering && (current.length!==before.length+1||current.filter(r=>r.RelationshipKey===f.RelationshipKey).length!==1))throw Error('Exact existing fixture recovery required; no creates allowed');
 const fields=recovering?prior('fields-before'):await call('fields-before',root+'/fields?$top=1000');const fieldRows=readRows(fields);
 const key=fieldRows.find(r=>r.InternalName==='RelationshipKey');if(!key?.Required||!key.Indexed||!key.EnforceUniqueValues)throw Error('Native unique key protection required');
 const views=recovering?prior('views-before'):await call('views-before',root+'/views?$top=1000');
 let reads=0;
 const readByKey=async key=>readRows(await call('fixture-read-'+(++reads),root+"/items?$filter=RelationshipKey eq '"+key+"'"));
 const createOnce=async row=>(await call('fixture-create',root+'/items','post',{__metadata:{type:(meta.d??meta).ListItemEntityTypeFullName},...row}));
 const args={listUrl:root,pinnedListUrl:root,row:f,journalRoot:journal,readByKey,createOnce};
 const created=recovering?prior('created'):await submitCandidate(args);save('created',created);
 const replay=await submitCandidate(args);if(replay.writes!==0)throw Error('Replay wrote');save('replay',replay);
 const canonical=x=>Array.isArray(x)?x.map(canonical):x&&typeof x==='object'?Object.fromEntries(Object.keys(x).sort().filter(k=>k!=='__metadata').map(k=>[k,canonical(x[k])])):x;
 const sameData=(a,b)=>JSON.stringify(canonical(a))===JSON.stringify(canonical(b));
 const raw=await readByKey(f.RelationshipKey);if(raw.length!==1||raw[0].Id!==created.item.Id||!sameData(raw[0],created.item)||raw[0].__metadata?.etag!==created.item.__metadata?.etag)throw Error('Fixture changed; cleanup refused');
 const itemUrl=root+'/items('+created.item.Id+')';
 // Recovery operations have their own exclusive durable intent; an uncertain
 // recycle/restore is never retried by this command.
 const durable=(name,x)=>{const fd=fs.openSync(path.join(journal,f.RelationshipKey.replace(':','-')+'-'+name+'.json'),'wx',0o600);try{fs.writeFileSync(fd,JSON.stringify(x)+'\n');fs.fsyncSync(fd);}finally{fs.closeSync(fd);}const dir=fs.openSync(journal,'r');try{fs.fsyncSync(dir);}finally{fs.closeSync(dir);}};
 durable('recycle-intent',{itemUrl,postimage:raw[0]});
 const recycled=await call('fixture-recycle',itemUrl+'/recycle()','post',{});
 const recycleId=(recycled.d??recycled).Recycle;
 if(!/^[a-f0-9-]{36}$/i.test(recycleId))throw Error('No native recycle identity; reconcile');
 if((await readByKey(f.RelationshipKey)).length!==0)throw Error('Fixture remains after recycle');
 const recycleUrl=site+"/_api/site/RecycleBin(guid'"+recycleId+"')";
 await call('fixture-recycle-entry',recycleUrl);
 durable('restore-intent',{recycleUrl});await call('fixture-restore',recycleUrl+'/restore()','post',{});
 const restored=await readByKey(f.RelationshipKey);
 if(restored.length!==1||restored[0].Id!==created.item.Id||Object.keys(f).filter(k=>k!=='EvidenceURL').some(k=>JSON.stringify(restored[0][k])!==JSON.stringify(f[k]))||restored[0].EvidenceURL?.Url!==f.EvidenceURL.Url)throw Error('Restored fixture mismatch; preserve for inspection');
 save('recovered',restored[0]);
 durable('final-recycle-intent',{itemUrl,postimage:restored[0]});await call('fixture-final-recycle',itemUrl+'/recycle()','post',{});
 const after=readRows(await call('items-after',root+'/items?$top=1000'));
 if(!sameData(after,before)||after.some(r=>r.__metadata?.etag!==before.find(b=>b.Id===r.Id)?.__metadata?.etag))throw Error('Original relationship rows changed');
 const fieldAfter=await call('fields-after',root+'/fields?$top=1000'),viewAfter=await call('views-after',root+'/views?$top=1000');
 if(!sameData(fieldAfter,fields)||!sameData(viewAfter,views))throw Error('Original schema/views changed');
 save('writer-acceptance',{nativeCreate:true,exactReadback:true,replayWrites:0,recycleRestoreSameItem:true,fixtureCleaned:true,originalRowsPreserved:true,schemaViewsPreserved:true,automaticMutationRetries:0,at:new Date().toISOString()});
}
save('inspection-complete',{readOnly:phase==='inspect',at:new Date().toISOString()});
console.log('G06 exact list and downstream effects inspection saved');
