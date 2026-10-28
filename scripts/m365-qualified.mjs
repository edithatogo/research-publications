#!/usr/bin/env node
// Project-owned Apache-2.0 code. Credentials stay in the installed CLI's store.
import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {execFileSync} from 'node:child_process';

const fail = message => { throw new Error(message); };
process.umask(0o077); // SDK response files and receipts remain owner-readable only.
const [mode, bindingPath, ...args] = process.argv.slice(2);
if (!['read','renew','change-log-read'].includes(mode)) fail('MODE_UNAVAILABLE_BEFORE_AUTH: this source packet implements only read, renew and change-log-read');
if (!bindingPath) fail('Private binding required');
const bindingFile = fs.realpathSync(bindingPath);
execFileSync('git', ['check-ignore', '-q', bindingFile]);
const pin = JSON.parse(fs.readFileSync(bindingFile, 'utf8'));
for (const key of ['sdkRoot','sdkVersion','connectionName','appId','tenantId','username']) if (!pin[key]) fail(`Missing private pin: ${key}`);
if (!Array.isArray(pin.resources) || !pin.resources.length) fail('Missing resource pins');
const pkg = JSON.parse(fs.readFileSync(path.join(pin.sdkRoot,'package.json'),'utf8'));
if (pkg.name !== '@pnp/cli-microsoft365' || pkg.version !== pin.sdkVersion) fail('SDK changed; requalify before login');
const {prepareRead}=await import('./m365_read_guard.mjs');
const assertPrivate=file=>execFileSync('git',['check-ignore','-q',path.resolve(file)]);
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
}else if(mode==='change-log-read'){
  const {runGuarded}=await import('./sharepoint_change_log_read.mjs');
  await runGuarded({args,auth,request,pin});
}else{
  process.argv=[process.argv[0],process.argv[1],...args];
  process.env.CLIMICROSOFT365_NOUPDATE='1';
  await import(pathToFileURL(path.join(pin.sdkRoot,'dist/index.js')));
}
