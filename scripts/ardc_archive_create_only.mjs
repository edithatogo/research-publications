// Project-owned Apache-2.0. One ARDC Activities binary create-only upload using the pinned Toolkit client.
// All native reads/readbacks remain through scripts/m365-qualified.mjs.
import fs from 'node:fs';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {pathToFileURL} from 'node:url';
import {createHash} from 'node:crypto';
const fail = message => {throw new Error(message);};
const [bindingPath, planPath, fileName, evidenceDir] = process.argv.slice(2);
if (!evidenceDir) fail('PRIVATE_BINDING PLAN EXACT_FILENAME NEW_PRIVATE_EVIDENCE_DIRECTORY required');
for (const file of [bindingPath,planPath,evidenceDir]) execFileSync('git',['check-ignore','-q',path.resolve(file)]);
const pin=JSON.parse(fs.readFileSync(bindingPath,'utf8'));
const plan=JSON.parse(fs.readFileSync(planPath,'utf8'));
const target=pin.ardcActivitiesArchiveTarget;
if (plan.format!=='rims-ardc-activities-upload-v1' || !target || plan.site!==target.site || plan.folder!==target.folder) fail('Archive target differs from exact private binding');
if (!/^https:\/\/[A-Za-z0-9-]+\.sharepoint\.com\/(?:personal|sites)\/[A-Za-z0-9_-]+$/.test(plan.site) || typeof plan.folder!=='string' || !plan.folder.startsWith('/Documents/') || /['?#%\\]/.test(plan.folder) || plan.folder.split('/').slice(1).some(p=>['','.','..'].includes(p))) fail('Unsafe source archive target');
if (!pin.resources.includes(new URL(plan.site).origin)) fail('Unpinned resource');
const file={name:plan.name,local:plan.local,bytes:plan.bytes,sha256:plan.sha256};
if (file.name!==fileName || !/^[a-f0-9]{64}$/.test(file.sha256 ?? '') || !/^activities-batch-[0-9]{9}\.json$/.test(file.name ?? '')) fail('Unqualified batch filename');
if (file.local!==file.name) fail('Local artifact must be the exact immutable filename');
const local=path.resolve(path.dirname(planPath),file.local);
if (!local.startsWith(path.resolve(path.dirname(planPath))+path.sep) || fs.lstatSync(local).isSymbolicLink()) fail('Local artifact escapes plan directory');
const bytes=fs.readFileSync(local);
if(bytes.length===0 || bytes.length!==file.bytes || bytes.length>20000000 || createHash('sha256').update(bytes).digest('hex')!==file.sha256) fail('Local artifact bytes differ');
if(typeof pin.ardcActivitiesCredentialFile!=='string' || typeof pin.ardcActivitiesJournalRoot!=='string') fail('Private credential and persistent journal bindings required');
for(const privatePath of [pin.ardcActivitiesCredentialFile,pin.ardcActivitiesJournalRoot]) execFileSync('git',['check-ignore','-q',path.resolve(privatePath)]);
const credential=fs.readFileSync(pin.ardcActivitiesCredentialFile,'utf8').trim();
if(!credential || /\s/.test(credential) || bytes.includes(Buffer.from(credential)) || bytes.includes(Buffer.from(encodeURIComponent(credential)))) fail('Invalid credential or credential present in payload');
let payload;
try { payload=JSON.parse(bytes.toString('utf8')); } catch { fail('Invalid Activities payload'); }
if(payload?.status!=='OK' || String(payload?.code)!=='200' || !Array.isArray(payload?.data?.records)) fail('Invalid Activities response');
// Reuse the same strict identity, source-key and credential checks as capture.
// Pass only private paths, never the credential or response, in argv.
try {
  execFileSync(path.resolve('.venv/bin/python'), ['-c',
    "import json,sys; from pathlib import Path; from scripts.ardc_activity_batch import validate_batch; p=json.loads(Path(sys.argv[1]).read_bytes()); validate_batch(Path(sys.argv[2]).read_bytes(),p['identities'],Path(sys.argv[3]).read_bytes().strip())",
    path.resolve(planPath), local, path.resolve(pin.ardcActivitiesCredentialFile)], {stdio:'pipe'});
} catch { fail('Activities batch validation failed'); }
const journalRoot=fs.realpathSync(pin.ardcActivitiesJournalRoot);
if(fs.lstatSync(pin.ardcActivitiesJournalRoot).isSymbolicLink() || !fs.statSync(journalRoot).isDirectory()) fail('Invalid journal directory');
const pkg=JSON.parse(fs.readFileSync(path.join(pin.sdkRoot,'package.json'),'utf8'));
if(pkg.name!=='@pnp/cli-microsoft365'||pkg.version!==pin.sdkVersion) fail('SDK drift');
fs.mkdirSync(evidenceDir,{mode:0o700});
const save=(n,x)=>fs.writeFileSync(path.join(evidenceDir,n),JSON.stringify(x,null,2)+'\n',{flag:'wx',mode:0o600});
const lock=path.join(path.dirname(fs.realpathSync(bindingPath)),'.m365-qualified.lock');
// Queue behind a live read without removing its lock or retrying a submission.
for(let attempt=0;;attempt++) {
 try { fs.mkdirSync(lock); break; }
 catch(error) {
  if(error.code!=='EEXIST' || attempt>=30) throw error;
  await new Promise(resolve=>setTimeout(resolve,1000));
 }
}
fs.writeFileSync(path.join(lock,'owner.json'),JSON.stringify({pid:process.pid,mode:'ardc-activities-create-only',started:new Date().toISOString()}));
process.once('exit',()=>fs.rmSync(lock,{recursive:true}));
const {default:auth}=await import(pathToFileURL(path.join(pin.sdkRoot,'dist/Auth.js')));
const {default:request}=await import(pathToFileURL(path.join(pin.sdkRoot,'dist/request.js')));
const quiet={log:async()=>{},logToStderr:async()=>{}};request.logger=quiet;request.debug=false;
const same=(a,b)=>typeof a==='string'&&typeof b==='string'&&a.toLowerCase()===b.toLowerCase();
await auth.restoreAuth();
const guard=()=>{const c=auth.connection;if(c.name!==pin.connectionName||!same(c.appId,pin.appId)||!same(c.tenant,pin.tenantId)||c.authType!=='browser'||!c.active)fail('Toolkit binding drift');};
guard();
const client=await auth.getPublicClient(quiet,false);
const account=auth.connection.identityId?await client.getTokenCache().getAccountByLocalId(auth.connection.identityId):null;
if(!account||!same(account.username,pin.username)||!same(account.tenantId,pin.tenantId)||(pin.objectId&&!same(account.localAccountId,pin.objectId)))fail('Selected identity drift');
for(const method of ['ensureAccessTokenWithBrowser','ensureAccessTokenWithDeviceCode','ensureAccessTokenWithPassword','retrieveAuthCodeWithBrowser'])auth[method]=async()=>fail('INTERACTIVE_AUTH_BLOCKED; use existing explicit resource renewal');
const silent=auth.ensureAccessTokenSilent.bind(auth);
auth.ensureAccessTokenSilent=async function(resource,...args){guard();if(resource!==new URL(plan.site).origin)fail('Wrong resource');const r=await silent(resource,...args);if(!r.accessToken||!(new Date(r.expiresOn)>new Date())||!same(r.account?.username,pin.username)||!same(r.account?.tenantId,pin.tenantId)||(r.idTokenClaims?.aud&&!same(r.idTokenClaims.aud,pin.appId)))fail('Renewed silent identity mismatch');return r;};
const token=await auth.ensureAccessToken(new URL(plan.site).origin,quiet,false);guard();
const fullFolder=new URL(plan.site).pathname+plan.folder;
const url=new URL(plan.site+"/_api/web/GetFolderByServerRelativePath(DecodedUrl='"+fullFolder+"')/Files/Add(url='"+file.name+"',overwrite=false)").href;
// A stable per-target intent prevents a second send even with a new evidence
// directory. Uncertain outcomes require exact native readback, not a retry.
const journalName=createHash('sha256').update(url).digest('hex')+'.json';
const journalFd=fs.openSync(path.join(journalRoot,journalName),'wx',0o600);
try { fs.writeFileSync(journalFd,JSON.stringify({url,file:file.name,sha256:file.sha256,bytes:bytes.length,at:new Date().toISOString()})+'\n'); fs.fsyncSync(journalFd); }
finally { fs.closeSync(journalFd); }
let sent=false;
request.req.interceptors.request.use(config=>{if(sent||config.url!==url||(config.method??'').toLowerCase()!=='post')fail('Duplicate/out-of-scope wire request');sent=true;config.maxRedirects=0;config.timeout=30000;save('submission.json',{url,file:file.name,bytes:bytes.length,sha256:file.sha256,overwrite:false,attempt:1,at:new Date().toISOString()});return config;});
try{
 const response=await request.req.post(url,bytes,{headers:{Authorization:'Bearer '+token,Accept:'application/json;odata=nometadata','Content-Type':'application/octet-stream'},maxRedirects:0,timeout:30000,responseType:'json'});
 save('response.json',{status:response.status,data:response.data});
 if(![200,201].includes(response.status))fail('Unexpected upload status; reconcile saved state');
 console.log(JSON.stringify({created:true,status:response.status,file:file.name,one_wire_submission:sent}));
}catch(error){save('error.json',{status:error.response?.status,message:error.message,uncertain:sent});throw Error('Upload failed/uncertain; inspect native state before another attempt');}
