// SPDX-License-Identifier: Apache-2.0
// Every SDK, account, token and response below is synthetic. No live SDK loads.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {spawn,spawnSync} from 'node:child_process';
import {prepareRead} from '../scripts/m365_read_guard.mjs';
const base=path.resolve('.venv/m365-offline-tests');
const url='https://example.sharepoint.com/sites/offline/_api/web';
function fixture(){
  fs.mkdirSync(base,{recursive:true});
  const root=fs.mkdtempSync(path.join(base,'qualified-offline-'));
  const sdk=path.join(root,'fake-sdk');fs.mkdirSync(path.join(sdk,'dist'),{recursive:true});
  const pin={sdkRoot:sdk,sdkVersion:'synthetic-1',connectionName:'offline',appId:'11111111-1111-4111-8111-111111111111',tenantId:'22222222-2222-4222-8222-222222222222',username:'operator@example.invalid',objectId:'offline-user',resources:['https://example.sharepoint.com'],readUrlPrefixes:[url]};
  const binding=path.join(root,'binding.json');
  fs.writeFileSync(binding,JSON.stringify(pin));
  fs.writeFileSync(path.join(sdk,'package.json'),JSON.stringify({name:'@pnp/cli-microsoft365',version:pin.sdkVersion,type:'module'}));
  const common=`import fs from 'node:fs';
const pin=JSON.parse(fs.readFileSync(process.env.FAKE_BINDING));
const log=value=>fs.appendFileSync(process.env.FAKE_LOG,JSON.stringify(value)+'\\n');
`;
  fs.writeFileSync(path.join(sdk,'dist/Auth.js'),common+`
const account={username:pin.username,tenantId:pin.tenantId,localAccountId:pin.objectId};
const result=()=>({account,tenantId:pin.tenantId,idTokenClaims:{aud:pin.appId,tid:pin.tenantId,oid:pin.objectId,preferred_username:pin.username},accessToken:'synthetic-not-a-credential',expiresOn:new Date(Date.now()+3600000)});
const client={getTokenCache:()=>({getAccountByLocalId:async()=>process.env.FAKE_CASE==='wrong_account'?{...account,username:'other@example.invalid'}:account}),acquireTokenInteractive:async options=>{
 log({step:'interactive',scopes:options.scopes,responseMode:options.responseMode});
 const u=new URL('https://login.microsoftonline.com/'+pin.tenantId+'/oauth2/v2.0/authorize');
 u.searchParams.set('client_id',process.env.FAKE_CASE==='wrong_callback_client'?'wrong':pin.appId);
 u.searchParams.set('response_mode','form_post');u.searchParams.set('redirect_uri','http://localhost:54321');
 await options.openBrowser(u.href);return result();}};
const auth={connection:{name:pin.connectionName,appId:pin.appId,tenant:pin.tenantId,authType:'browser',active:true,identityId:pin.objectId},
 restoreAuth:async()=>{log({step:'restore'});if(process.env.FAKE_CASE==='wrong_connection')auth.connection.appId='other';},
 getPublicClient:async()=>client,
 ensureAccessTokenSilent:async()=>{log({step:'silent'});if(process.env.FAKE_CASE==='expired')return auth.ensureAccessTokenWithBrowser();if(process.env.FAKE_CASE==='wrong_result')return {...result(),account:{...account,username:'other@example.invalid'}};return result();},
 ensureAccessTokenWithBrowser:async()=>{log({step:'STOCK_LOGIN_FORBIDDEN'});throw Error('Stock login reached');},
 ensureAccessToken:async(resource,logger,debug,fetchNew)=>{log({step:'ensure',resource});auth.clientApplication=client;const r=await auth.ensureAccessTokenSilent(resource);return r.accessToken;}};
export default auth;
`);
  fs.writeFileSync(path.join(sdk,'dist/request.js'),common+`
const interceptors=[],failures=[];
const req=async config=>{for(const guard of interceptors)config=await guard(config);log({step:'transport',method:config.method,url:config.url,maxRedirects:config.maxRedirects});if(process.env.FAKE_CASE==='throttled'){let e={response:{status:429,headers:{'retry-after':'0'}}};for(const reject of failures){try{await reject(e);}catch(next){e=next;}}throw e;}return {status:200,data:'{\"d\":{\"results\":[]}}'};};
req.interceptors={request:{use:f=>interceptors.push(f)},response:{use:(accept,reject)=>failures.push(reject)}};
export default {req};
`);
  fs.writeFileSync(path.join(sdk,'dist/index.js'),common+`
import auth from './Auth.js';import request from './request.js';
const args=process.argv.slice(2);const value=name=>args[args.indexOf(name)+1];
await auth.ensureAccessToken(process.env.FAKE_CASE==='unpinned_resource'?'https://other.invalid':pin.resources[0]);
const send=async()=>{try{return await request.req({method:process.env.FAKE_CASE==='write_transport'?'POST':'GET',url:process.env.FAKE_CASE==='drift_transport'?pin.readUrlPrefixes[0]+'/other':value('--url')||pin.readUrlPrefixes[0]});}catch(e){if(e.response?.status===429){log({step:'SDK_RETRY_FORBIDDEN'});return send();}throw e;}};await send();
if(args.includes('--filePath'))fs.writeFileSync(value('--filePath'),'{}');
log({step:'complete'});
`);
  const log=path.join(root,'events.jsonl');
  function run(mode,args=[],fault=''){
    const r=spawnSync(process.execPath,[path.resolve('scripts/m365-qualified.mjs'),mode,binding,...args],{encoding:'utf8',timeout:5000,env:{...process.env,FAKE_BINDING:binding,FAKE_LOG:log,FAKE_CASE:fault}});
    assert.equal(r.error,undefined);return r;
  }
  return {root,pin,binding,sdk,log,run,args:()=>['request','--url',url,'--method','get','--filePath',path.join(root,'response.json'),'--output','json'],events:()=>fs.existsSync(log)?fs.readFileSync(log,'utf8').trim().split('\n').filter(Boolean).map(JSON.parse):[],close:()=>fs.rmSync(root,{recursive:true,force:true})};
}

test('exact pinned GET restores only synthetic auth and confines the transport',()=>{
  const f=fixture();try{const r=f.run('read',f.args());assert.equal(r.status,0,r.stderr);assert.deepEqual(f.events().find(e=>e.step==='transport'),{step:'transport',method:'GET',url,maxRedirects:0});assert.ok(!fs.existsSync(path.join(f.root,'.m365-qualified.lock')));assert.equal(fs.readFileSync(path.join(f.root,'response.json'),'utf8'),'{}');}finally{f.close();}
});
test('unavailable modes and invalid exact targets fail before SDK restore or lock',()=>{
  for(const mode of ['funding-apply','page-draft','documentation-sync','documentation-page','isolated-recovery','grants-downstream','grants-promotion','grants-preference-activation','unknown']){
    const f=fixture();try{const r=f.run(mode);assert.notEqual(r.status,0);assert.match(r.stderr,/MODE_UNAVAILABLE_BEFORE_AUTH/);assert.deepEqual(f.events(),[]);assert.ok(!fs.existsSync(path.join(f.root,'.m365-qualified.lock')));}finally{f.close();}
  }
  const f=fixture();try{const args=f.args();args[2]=url+'-other';const r=f.run('read',args);assert.notEqual(r.status,0);assert.match(r.stderr,/Unpinned native read target/);assert.deepEqual(f.events(),[]);}finally{f.close();}
});
test('SDK drift, existing output and debug/admin/auth overrides are rejected before auth',()=>{
  for(const fault of ['sdk','exists','debug','admin','auth']){
    const f=fixture();try{const args=f.args();if(fault==='sdk')fs.writeFileSync(path.join(f.sdk,'package.json'),'{"name":"@pnp/cli-microsoft365","version":"changed"}');if(fault==='exists')fs.writeFileSync(path.join(f.root,'response.json'),'preserve');if(fault==='debug')args.push('--debug','true');if(fault==='admin')args.push('--asAdmin','true');if(fault==='auth')args.push('--appId','other');const r=f.run('read',args);assert.notEqual(r.status,0);assert.deepEqual(f.events(),[]);}finally{f.close();}
  }
});
test('identity/resource drift and expired sessions never trigger stock login or transport',()=>{
  for(const fault of ['wrong_account','wrong_connection','wrong_result','expired','unpinned_resource']){
    const f=fixture();try{const r=f.run('read',f.args(),fault);assert.notEqual(r.status,0);assert.ok(!f.events().some(e=>['transport','STOCK_LOGIN_FORBIDDEN','interactive'].includes(e.step)));if(fault==='expired')assert.match(r.stderr,/INTERACTIVE_AUTH_BLOCKED/);assert.ok(!fs.existsSync(path.join(f.root,'.m365-qualified.lock')));}finally{f.close();}
  }
});
test('transport method or URL drift is blocked after SDK admission',()=>{
  for(const fault of ['write_transport','drift_transport']){const f=fixture();try{const r=f.run('read',f.args(),fault);assert.notEqual(r.status,0);assert.match(r.stderr,/Transport outside exact pinned GET/);assert.ok(!f.events().some(e=>e.step==='transport'));}finally{f.close();}}
});
test('named flow reads reuse the exact retained root pins and block alternate targets',()=>{
  const f=fixture();try{
    const args=['flow','get','--name','offline-flow','--environmentName','offline-environment','--output','json'];
    let r=f.run('read',args);assert.notEqual(r.status,0);assert.deepEqual(f.events(),[]);
    f.pin.readUrlPrefixes.push('https://api.flow.microsoft.com/providers/Microsoft.ProcessSimple/environments/offline-environment/flows/offline-flow');fs.writeFileSync(f.binding,JSON.stringify(f.pin));
    r=f.run('read',args);assert.equal(r.status,0,r.stderr);
    assert.throws(()=>prepareRead([...args,'--asAdmin','true'],f.pin,()=>{}));
    for(const variant of [ ['flow','run','list','--flowName','offline-flow','--environmentName','offline-environment','--output','json'],['flow','run','get','--flowName','offline-flow','--environmentName','offline-environment','--name','safe-run','--output','json']]) assert.deepEqual(prepareRead(variant,f.pin,()=>{}),{});
  }finally{f.close();}
});
test('SharePoint file commands require a separately qualified exact argument pin',()=>{
  const f=fixture();try{
    const args=['spo','file','list','--webUrl','https://example.sharepoint.com/sites/offline','--folderUrl','/sites/offline/archive','--output','json'];
    assert.throws(()=>prepareRead(args,f.pin,()=>{}));f.pin.readCommandArguments=[args];assert.deepEqual(prepareRead(args,f.pin,()=>{}),{});
    assert.throws(()=>prepareRead([...args,'--optionsFile','other'],f.pin,()=>{}));
  }finally{f.close();}
});
test('explicit renewal uses one exact resource and form_post without native reads',()=>{
  const f=fixture();try{const directory=path.join(f.root,'renew');const r=f.run('renew',[f.pin.resources[0],directory]);assert.equal(r.status,0,r.stderr);assert.equal(f.events().filter(e=>e.step==='interactive').length,1);assert.ok(!f.events().some(e=>e.step==='transport'));const result=JSON.parse(fs.readFileSync(path.join(directory,'result.json')));assert.equal(result.renewed,true);assert.equal(result.calls,1);assert.ok(!fs.readFileSync(path.join(directory,'identity-validation.json'),'utf8').includes('synthetic-not-a-credential'));}finally{f.close();}
});
test('renewal rejects unpinned resources before restore and incompatible callback before identity acceptance',()=>{
  const f=fixture();try{let r=f.run('renew',['https://other.invalid',path.join(f.root,'bad')]);assert.notEqual(r.status,0);assert.deepEqual(f.events(),[]);r=f.run('renew',[f.pin.resources[0],path.join(f.root,'callback')],'wrong_callback_client');assert.notEqual(r.status,0);assert.match(r.stderr,/Authorization request differs/);assert.ok(!fs.existsSync(path.join(f.root,'callback/identity-validation.json')));}finally{f.close();}
});
test('raw-read paths reject traversal encodings, prefix confusion, symlinks and mutable formats',()=>{
  const f=fixture();try{
    for(const changed of [url+'-other',url+'/%252foutside',url+'/%2foutside','http://example.sharepoint.com/sites/offline/_api/web',url+'#fragment']){const args=f.args();args[2]=changed;assert.throws(()=>prepareRead(args,f.pin,()=>{}));}
    fs.symlinkSync('missing-target',path.join(f.root,'response.json'));assert.throws(()=>prepareRead(f.args(),f.pin,()=>{}));fs.unlinkSync(path.join(f.root,'response.json'));
    assert.throws(()=>prepareRead([...f.args(),'--accept','text/html'],f.pin,()=>{}));
    assert.throws(()=>prepareRead([...f.args(),'--url',url],f.pin,()=>{}));
  }finally{f.close();}
});

test('throttling stops after one transport call despite SDK retry behavior',()=>{
  const f=fixture();try{const r=f.run('read',f.args(),'throttled');assert.notEqual(r.status,0);assert.match(r.stderr,/QUALIFIED_READ_THROTTLED/);assert.equal(f.events().filter(e=>e.step==='transport').length,1);assert.ok(!f.events().some(e=>e.step==='SDK_RETRY_FORBIDDEN'));}finally{f.close();}
});
test('an existing shared workload owner blocks SDK restore until release',async()=>{
  const f=fixture();const lock=path.join(f.root,'.m365-qualified.lock');fs.mkdirSync(lock);fs.writeFileSync(path.join(lock,'owner.json'),'synthetic-existing-owner');
  let child;
  try{
    child=spawn(process.execPath,[path.resolve('scripts/m365-qualified.mjs'),'read',f.binding,...f.args()],{stdio:'ignore',env:{...process.env,FAKE_BINDING:f.binding,FAKE_LOG:f.log}});
    const done=new Promise((resolve,reject)=>{child.once('exit',resolve);child.once('error',reject);});
    await new Promise(resolve=>setTimeout(resolve,100));assert.equal(fs.readFileSync(path.join(lock,'owner.json'),'utf8'),'synthetic-existing-owner');assert.deepEqual(f.events(),[]);
    fs.rmSync(lock,{recursive:true});assert.equal(await done,0);assert.ok(f.events().some(e=>e.step==='restore'));
  }finally{if(child?.exitCode===null)child.kill();f.close();}
});
test('change-log mode keeps its fixed read-only POST dependency closed',()=>{
 const f=fixture();try{
  const list="https://example.sharepoint.com/sites/offline/_api/web/lists(guid'33333333-3333-4333-8333-333333333333')";
  f.pin.readUrlPrefixes.push(list);fs.writeFileSync(f.binding,JSON.stringify(f.pin));
  const plan=path.join(f.root,'changes.json'),directory=path.join(f.root,'changes');
  fs.writeFileSync(plan,JSON.stringify({listUrl:list,startToken:'1;3;33333333-3333-4333-8333-333333333333;1;1',endToken:'1;3;33333333-3333-4333-8333-333333333333;2;2'}));
  const r=f.run('change-log-read',[plan,directory]);assert.equal(r.status,0,r.stderr);
  assert.equal(f.events().filter(e=>e.step==='ensure').length,1);
  assert.equal(f.events().filter(e=>e.step==='transport').length,1);
  assert.equal(f.events().find(e=>e.step==='transport').method,'POST');
  assert.equal(JSON.parse(fs.readFileSync(path.join(directory,'complete.json'))).nativeMutations,0);
 }finally{f.close();}
});
