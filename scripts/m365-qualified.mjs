#!/usr/bin/env node
// Project-owned Apache-2.0 code. Credentials stay in the installed CLI's store.
import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {execFileSync} from 'node:child_process';

const fail = message => { throw new Error(message); };
process.umask(0o077); // SDK response files and receipts remain owner-readable only.
let [mode, bindingPath, ...args] = process.argv.slice(2);
if (!['read','renew','change-log-read','documentation-sync','ardc-archive-read','outcome-store','relationship-store','project-link-schema','register-read','outcome-bootstrap'].includes(mode)) fail('MODE_UNAVAILABLE_BEFORE_AUTH: unsupported mode');
if (!bindingPath) fail('Private binding required');
const bindingFile = fs.realpathSync(bindingPath);
// A reader may use the native owner's retained binding from an isolated source
// worktree. Check its privacy in its own repository; retain its original lock.
execFileSync('git', ['-C', path.dirname(bindingFile), 'check-ignore', '-q', bindingFile]);
const pin = JSON.parse(fs.readFileSync(bindingFile, 'utf8'));
for (const key of ['sdkRoot','sdkVersion','connectionName','appId','tenantId','username']) if (!pin[key]) fail(`Missing private pin: ${key}`);
if (!Array.isArray(pin.resources) || !pin.resources.length) fail('Missing resource pins');
const pkg = JSON.parse(fs.readFileSync(path.join(pin.sdkRoot,'package.json'),'utf8'));
if (pkg.name !== '@pnp/cli-microsoft365' || pkg.version !== pin.sdkVersion) fail('SDK changed; requalify before login');
const {prepareRead}=await import('./m365_read_guard.mjs');
const assertPrivate=file=>execFileSync('git',['check-ignore','-q',path.resolve(file)]);
if(mode==='project-link-schema'){
  if(args.length!==3) fail('Private project target, initial pair and new receipts required');
  for(const file of args) assertPrivate(file);
  if(fs.existsSync(args[2])) fail('Never reuse a schema receipt directory');
  const selected=JSON.parse(fs.readFileSync(args[0],'utf8'));
  const {target}=await import('./bootstrap_outcome_register.mjs');target(pin,selected.listUrl?.split('/_api/')[0]);
  if(selected.journalField!=='ProjectLinkJournal'||selected.projectionField!=='ProjectLinkProjection') fail('Dedicated project fields required');
  pin.readUrlPrefixes=[...pin.readUrlPrefixes,selected.listUrl];
  const {validateTarget}=await import('./outcome_store.mjs');validateTarget({...pin,outcomeTarget:selected});
}
if(mode==='relationship-store'){
  if(args.length!==3) fail('Private relationship target, plan and new receipt directory required');
  for(const file of args) assertPrivate(file);
  if(fs.existsSync(args[2])) fail('Never reuse a relationship send journal');
  const {validateTarget}=await import('./relationship_store.mjs');
  validateTarget(pin,JSON.parse(fs.readFileSync(args[0],'utf8')));
  const plan=JSON.parse(fs.readFileSync(args[1],'utf8'));
  if(plan.operation==='apply') execFileSync(path.resolve('.venv/bin/python'),['-m','scripts.relationship_intake','--validate-plan',args[1]]);
  else if(plan.operation==='schema') {if(Object.keys(plan).join()!=='operation') fail('Exact schema operation required');}
  else if(plan.operation==='read') {if(Object.keys(plan).sort().join('|')!=='item_id|key|operation') fail('Exact relationship read required');}
  else fail('Unsupported relationship operation');
}
if(mode==='outcome-bootstrap'){
  if(args.length!==2) fail('Exact site and new private receipt directory required');
  assertPrivate(args[1]);if(fs.existsSync(args[1])) fail('Never reuse a bootstrap journal');
  const {target}=await import('./bootstrap_outcome_register.mjs');target(pin,args[0]);
}
if(mode==='outcome-store'){
  if(args.length===3){
    const targetPath=args.pop();assertPrivate(targetPath);
    const selected=JSON.parse(fs.readFileSync(targetPath,'utf8'));
    const site=selected.listUrl?.split('/_api/')[0];
    const {target}=await import('./bootstrap_outcome_register.mjs');target(pin,site);
    pin.outcomeTarget=selected;
    pin.readUrlPrefixes=[...pin.readUrlPrefixes,selected.listUrl];
  }
  if(args.length!==2) fail('Private outcome plan and new receipt directory required');
  for(const file of args) assertPrivate(file);
  if(fs.existsSync(args[1])) fail('New outcome receipt directory required; never replay a send journal');
  const {validateTarget,validatePlan}=await import('./outcome_store.mjs');
  validateTarget(pin);validatePlan(JSON.parse(fs.readFileSync(args[0],'utf8')));
}
if(mode==='documentation-sync'){
  const [operation,manifestPath,baselinePath,directory,libraryId]=args;
  if(args.length!==5 || !['plan','apply'].includes(operation)) fail('Exact documentation plan/apply arguments required');
  for(const file of [manifestPath,baselinePath,directory]) assertPrivate(file);
  const manifest=JSON.parse(fs.readFileSync(manifestPath,'utf8'));
  if(!pin.resources.includes(new URL(manifest.site_url).origin)) fail('Output resource is not pinned');
  if(!pin.documentationTarget || manifest.site_url!==pin.documentationTarget.site_url || manifest.folder!==pin.documentationTarget.folder || libraryId!==pin.documentationTarget.library_id) fail('Output target differs from private pins');
  const {manifestFiles}=await import('./sync_dataset_documentation.mjs');
  manifestFiles(manifest);
}
if(mode==='ardc-archive-read'){
  if(args.length!==2) fail('Accepted marker and existing checkpoint required');
  for(const file of args) assertPrivate(file);
  const {validateTarget}=await import('./ardc_bulk_archive_read.mjs');
  validateTarget(pin,fs.readFileSync(args[0]));
}
// Explicit register reconciliation reads only: derive the site from retained
// list pins; never persist broader pins or change authentication ownership.
if(mode==='register-read'){
  const index=args.indexOf('--url');
  if(index<0) fail('Exact register read URL required');
  const u=new URL(args[index+1]);
  const root=u.origin+u.pathname.split('/_api/')[0]+'/_api/web/lists';
  if(!(pin.readUrlPrefixes??[]).some(p=>p.startsWith(root+"(guid'"))) fail('Register site is not retained');
  const suffix=u.pathname.slice(new URL(root).pathname.length);
  if(suffix!=='' && !/^\(guid'[0-9a-f-]{36}'\)\/fields$/i.test(suffix)) fail('Only list inventory and field schema reads allowed');
  for(const key of u.searchParams.keys()) if(!['$select','$filter','$top'].includes(key)) fail('Unsupported register query');
  pin.readUrlPrefixes=[...pin.readUrlPrefixes,u.href];
  mode='read';
}
let rawReadUrl;
if(mode==='read') rawReadUrl=prepareRead(args,pin,assertPrivate).rawReadUrl;
if(mode==='renew'){
  if(args.length!==2 || !pin.resources.includes(args[0])) fail('Exact pinned renewal resource and new private receipt directory required');
  assertPrivate(args[1]);
  if(fs.existsSync(args[1])) fail('New renewal receipt directory required');
}
if(mode==='change-log-read'){
  if(args.length!==2) fail('Private query plan and new private directory required');
  for(const file of args) assertPrivate(file);
  if(fs.existsSync(args[1])) fail('New private change-log directory required');
  const {validatePlan}=await import('./sharepoint_change_log_read.mjs');
  const plan=JSON.parse(fs.readFileSync(args[0],'utf8'));
  validatePlan(plan,pin.readUrlPrefixes??[]);
  if(!pin.resources.includes(new URL(plan.listUrl).origin)) fail('Unpinned resource');
}
const lock = path.join(path.dirname(bindingFile), '.m365-qualified.lock');
const {acquireWorkloadLock}=await import('./m365_workload_lock.mjs');
await acquireWorkloadLock(lock); // Never remove an existing owner.
const lockIdentity=fs.statSync(lock);
process.once('exit',()=>{
  // An externally replaced lock belongs to its new owner, even on failure.
  let current;try{current=fs.lstatSync(lock);}catch{return;}
  if(current.dev!==lockIdentity.dev || current.ino!==lockIdentity.ino || current.isSymbolicLink()) return;
  fs.rmSync(lock,{recursive:true});
});
fs.writeFileSync(path.join(lock,'owner.json'), JSON.stringify({pid:process.pid,mode,started:new Date().toISOString()}),{mode:0o600});
const {default:auth} = await import(pathToFileURL(path.join(pin.sdkRoot,'dist/Auth.js')));
const {default:request} = await import(pathToFileURL(path.join(pin.sdkRoot,'dist/request.js')));
const quiet = {log:async()=>{},logToStderr:async()=>{}};
request.logger=quiet;request.debug=false;
if (mode==='read') {
  request.req.interceptors.request.use(config=>{
    if ((config.method??'get').toLowerCase()!=='get' || config.data!==undefined
        || (rawReadUrl && new URL(config.url).href!==rawReadUrl.href)) fail('Transport outside exact pinned GET');
    config.maxRedirects=0;config.timeout=15000;
    return config;
  });
  request.req.interceptors.response.use(undefined,error=>{
    // Installed SDK execute() recursively retries errors with these statuses.
    // Preserve the status without its response shape so it stops at one read.
    if([429,503].includes(error.response?.status)) {
      const stopped=Error('QUALIFIED_READ_THROTTLED: HTTP '+error.response.status+'; no automatic retry');
      stopped.status=error.response.status;throw stopped;
    }
    throw error;
  });
}
await auth.restoreAuth();
const same=(a,b)=>typeof a==='string' && typeof b==='string' && a.toLowerCase()===b.toLowerCase();
const guard=()=>{
  const c=auth.connection;
  if(c.name!==pin.connectionName || !same(c.appId,pin.appId) || !same(c.tenant,pin.tenantId) || c.authType!=='browser' || !c.active) fail('Existing active Toolkit connection differs from private pins');
};
guard();
// Verify the CLI-selected cached account even when its resource token is valid.
// This uses MSAL's normal account metadata API, never exports cache contents.
const publicClient=await auth.getPublicClient(quiet,false);
const selectedAccount=auth.connection.identityId
  ? await publicClient.getTokenCache().getAccountByLocalId(auth.connection.identityId) : null;
if(!selectedAccount || !same(selectedAccount.username,pin.username) || !same(selectedAccount.tenantId,pin.tenantId)) fail('Selected cached account differs from private pins');
if(pin.objectId && !same(selectedAccount.localAccountId,pin.objectId)) fail('Selected cached object differs from private pins');
const validate=result=>{
  const a=result?.account,c=result?.idTokenClaims;
  const users=[a?.username,c?.preferred_username,c?.upn].filter(v=>v!==undefined);
  const tenants=[result?.tenantId,a?.tenantId,c?.tid].filter(v=>v!==undefined && v!=='');
  if(!users.length || users.some(v=>!same(v,pin.username)) || !tenants.length || tenants.some(v=>!same(v,pin.tenantId))) fail('SDK identity mismatch');
  if(c?.aud!==undefined && !same(c.aud,pin.appId)) fail('SDK client mismatch');
  if(!a?.username && (!same(c?.aud,pin.appId)||!same(c?.tid,pin.tenantId)||!same(c?.preferred_username??c?.upn,pin.username))) fail('SDK identity incomplete');
  if(pin.objectId && (![a?.localAccountId,c?.oid].filter(Boolean).length || ![a?.localAccountId,c?.oid].filter(Boolean).every(v=>same(v,pin.objectId)))) fail('SDK object mismatch');
  if(!result.accessToken || !(new Date(result.expiresOn)>new Date())) fail('SDK token missing or expired');
  return result;
};
const deny=async()=>fail('INTERACTIVE_AUTH_BLOCKED: use explicit renew mode; stock login/device code forbidden');
for(const method of ['ensureAccessTokenWithBrowser','ensureAccessTokenWithDeviceCode','ensureAccessTokenWithPassword','retrieveAuthCodeWithBrowser']) auth[method]=deny;
const silent=auth.ensureAccessTokenSilent.bind(auth);
auth.ensureAccessTokenSilent=async function(resource,...rest){guard();return validate(await silent(resource,...rest));};
const ensure=auth.ensureAccessToken.bind(auth);
auth.ensureAccessToken=async function(resource,...rest){
  guard();if(!pin.resources.includes(resource))fail('Unpinned resource; stop');
  try{return await ensure(resource,...rest);}
  catch(error){
    // A command may first need Graph even when its target is SharePoint. Keep
    // the exact pinned audience on a blocked login; never infer target denial.
    if(error instanceof Error && error.message.startsWith('INTERACTIVE_AUTH_BLOCKED:'))
      error.message+=` [pinned resource: ${resource}]`;
    throw error;
  }
};
if(mode==='renew'){
  const [resource,directory]=args;
  if(args.length!==2 || !pin.resources.includes(resource)) fail('Exact pinned renewal resource and new private receipt directory required');
  fs.mkdirSync(directory,{recursive:false,mode:0o700});
  execFileSync('git',['check-ignore','-q',path.resolve(directory)]);
  let calls=0;
  const save=(name,value)=>fs.writeFileSync(path.join(directory,name),JSON.stringify(value,null,2)+'\n',{flag:'wx',mode:0o600});
  const interactive=async function(r){
    guard();if(r!==resource || calls++)fail('Only one exact-resource renewal allowed');
    const result=await this.clientApplication.acquireTokenInteractive({scopes:[resource+'/.default'],responseMode:'form_post',prompt:'select_account',loginHint:pin.username,openBrowser:async url=>{
      const u=new URL(url),callback=new URL(u.searchParams.get('redirect_uri'));
      if(u.origin!=='https://login.microsoftonline.com' || !u.pathname.startsWith('/'+pin.tenantId+'/') || !same(u.searchParams.get('client_id'),pin.appId) || u.searchParams.get('response_mode')!=='form_post' || callback.protocol!=='http:' || !['localhost','127.0.0.1'].includes(callback.hostname))fail('Authorization request differs from qualified client/callback');
      save('request-metadata.json',{appId:pin.appId,tenantId:pin.tenantId,resource,responseMode:'form_post',callbackOrigin:callback.origin});
      fs.writeFileSync(path.join(directory,'sign-in-url.txt'),url,{flag:'wx',mode:0o600});
      console.error('Qualified Toolkit form_post URL retained privately; waiting for owner browser sign-in.');
    }});
    validate(result);save('identity-validation.json',{identityVerified:true,resource,clientPinned:true,expiresOn:result.expiresOn});return result;
  };
  auth.ensureAccessTokenSilent=interactive;auth.ensureAccessTokenWithBrowser=interactive;
  try{await auth.ensureAccessToken(resource,quiet,false,true);guard();save('result.json',{renewed:true,calls,at:new Date().toISOString()});console.log('Qualified same-client resource renewal complete; exact-target readback still required.');}
  catch(e){save('failure.json',{message:e.message??String(e),at:new Date().toISOString()});throw e;}
}else if(mode==='outcome-bootstrap'){
  const {runGuarded}=await import('./bootstrap_outcome_register.mjs');
  await runGuarded({args,auth,request,pin});
}else if(mode==='project-link-schema'){
  const {runGuarded}=await import('./project_link_schema.mjs');
  await runGuarded({args,auth,request,pin});
}else if(mode==='relationship-store'){
  const {runGuarded}=await import('./relationship_store.mjs');
  await runGuarded({args,auth,request,pin});
}else if(mode==='outcome-store'){
  const {runGuarded}=await import('./outcome_store.mjs');
  await runGuarded({args,auth,request,pin});
}else if(mode==='documentation-sync'){
  process.env.RIMS_M365_CLI_DIST=path.join(pin.sdkRoot,'dist');
  process.argv=[process.argv[0],process.argv[1],...args];
  const {main}=await import('./sync_dataset_documentation.mjs');
  await main();
}else if(mode==='ardc-archive-read'){
  const {runGuarded}=await import('./ardc_bulk_archive_read.mjs');
  await runGuarded({args:[bindingFile,...args],auth,request,pin});
}else if(mode==='change-log-read'){
  const {runGuarded}=await import('./sharepoint_change_log_read.mjs');
  await runGuarded({args,auth,request,pin});
}else{
  process.argv=[process.argv[0],process.argv[1],...args];
  process.env.CLIMICROSOFT365_NOUPDATE='1';
  await import(pathToFileURL(path.join(pin.sdkRoot,'dist/index.js')));
}
