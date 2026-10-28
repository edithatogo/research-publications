// SPDX-License-Identifier: Apache-2.0
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import test from 'node:test';
import {applyPaperLibraryMetadata} from '../scripts/apply_paper_library_metadata.mjs';
import {applyReportLibraryMetadata} from '../scripts/apply_report_library_metadata.mjs';

const sha = value => crypto.createHash('sha256').update(value).digest('hex');
const guid = n => `00000000-0000-4000-8000-${String(n).padStart(12, '0')}`;
const site = 'https://example.sharepoint.com/sites/research';
const library = guid(10), registry = guid(11);
const root = `${site}/_api/web/lists(guid'${library}')`;
const itemUrl = id => `${root}/items(${id})`;
const bytes = Buffer.from('%PDF-fictional accepted bytes');
const binding = {sdkRoot:'/fictional/sdk',sdkVersion:'12.fixture',connectionName:'fixture',appId:guid(12),tenantId:guid(13),username:'fictional@example.invalid',resources:['https://example.sharepoint.com']};

function fixture(t, kind = 'paper', count = 1) {
  const directory = fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), 'rims-library-')));
  t.after(() => fs.rmSync(directory, {recursive:true,force:true}));
  const target = {site_url:site,library_id:library,list_id:registry,folder:'/sites/research/Documents/papers'};
  const files = [], records = new Map(), requests = [];
  const fields = kind === 'paper' ? [
    {InternalName:'Title',TypeAsString:'Text',ReadOnlyField:false},
    {InternalName:'_ExtendedDescription',TypeAsString:'Note',ReadOnlyField:false,RichText:true},
  ] : [{InternalName:'RIMSGeneration',StaticName:'RIMSGeneration',EntityPropertyName:'RIMSGeneration',TypeAsString:'Text',ReadOnlyField:false,Required:false,Hidden:false}];
  for(let n = 1; n <= count; n++) {
    const file = {UniqueId:guid(n),Name:'paper.pdf',ServerRelativeUrl:`${target.folder}/paper-${n}-fixture/paper.pdf`,Length:String(bytes.length),ETag:'file-1',CheckOutType:2,UIVersionLabel:'1.0'};
    const item = {Id:n,'odata.etag':'"1"',Title:null,OData__ExtendedDescription:'<p>Human note</p>',Unrelated:'preserve'};
    const access = {Id:n,HasUniqueRoleAssignments:false};
    const versions = {value:[{ID:1,VersionLabel:'1.0',Created:'2030-01-01T00:00:00Z'}]};
    records.set(guid(n),{file:structuredClone(file),item:structuredClone(item),access,versions,bytes:Buffer.from(bytes)});
    files.push({file,item,access,versions,bytes:bytes.length,sha256:sha(bytes),accepted_sha256:sha(bytes),file_item_id:n,family:'report',count_scope:'monthly',role:'Monthly HTML'});
  }
  let evidence, plan;
  if(kind === 'paper') {
    const a = files[0];
    const manifest = {state:'linked',CanonicalKey:'fictional:1',DOI:'10.9999/fixture',verified_file_unique_id:a.file.UniqueId,sha256:sha(bytes),sha256_status:'verified_native_readback',file_url:'https://example.sharepoint.com'+a.file.ServerRelativeUrl,folder:path.posix.dirname(a.file.ServerRelativeUrl)};
    const parent = {Id:1,Title:'Fictional',field_2:manifest.CanonicalKey,field_11:manifest.DOI,OAArchiveState:'linked',OAArchiveURL:{Url:manifest.file_url},OAArchiveManifest:JSON.stringify(manifest)};
    evidence = {parent,manifest,...a,item_url:itemUrl(1)};
    plan = {file_id:a.file.UniqueId,item_id:1,parent_id:1,item_url:itemUrl(1),etag:'"1"',sha256:sha(bytes),file_url:manifest.file_url,file_preimage:a.file,before:{Title:null,OData__ExtendedDescription:a.item.OData__ExtendedDescription},changes:{Title:'Fictional | acceptedVersion',OData__ExtendedDescription:a.item.OData__ExtendedDescription+'<p>RIMS archive metadata v1</p><p>Canonical publication: fictional:1</p><p>End RIMS archive metadata</p>'},content_writes:false,manifest_writes:false};
  } else {
    evidence = {artifacts:files};
    plan = {format:'rims-report-library-metadata-v1',generation_id:'generation-1',fields:{RIMSGeneration:['Accepted generation','Text']},items:files.map(a=>({file_id:a.file.UniqueId,item_id:a.item.Id,etag:'"1"',file_preimage:a.file,sha256:a.sha256,properties:{RIMSGeneration:'generation-1'},changes:{RIMSGeneration:'generation-1'},before:{RIMSGeneration:null}})),content_writes:false,manifest_writes:false};
  }
  const sourcePath = path.join(directory,'source.json');
  const source = JSON.stringify(evidence);fs.writeFileSync(sourcePath,source);
  if(kind === 'paper') Object.assign(plan,{snapshot_path:sourcePath,snapshot_sha256:sha(source)});
  else Object.assign(plan,{evidence_path:sourcePath,evidence_sha256:sha(source)});
  const pin=structuredClone(binding);
  const qualification = {...pin,resource:'https://example.sharepoint.com',authType:'browser',active:true,interactiveAuth:false,sharedLockHeld:true,retries:0,maxRedirects:0,operation:`${kind}-library-metadata`,mutationQualified:true,mutationTargets:files.map(a=>itemUrl(a.item.Id))};
  const session = {qualification,assertQualified(){return this.qualification;},async request(request) {
    requests.push(structuredClone(request));
    assert.equal(request.retries,0);assert.equal(request.maxRedirects,0);assert.equal(request.interactiveAuth,false);
    if(request.method === 'POST') {
      const id = Number(request.url.match(/items\((\d+)\)$/)?.[1]);
      const record = records.get(guid(id));
      if(session.failBefore === id) throw Error('fictional uncertain transport failure');
      assert.equal(request.headers['IF-MATCH'],record.item['odata.etag']);
      Object.assign(record.item,request.data);record.item['odata.etag']='"2"';record.file.ETag='file-2';record.file.UIVersionLabel='2.0';
      record.versions.value.push({ID:2,VersionLabel:'2.0',Created:'2030-01-02T00:00:00Z'});
      if(session.damageAfter === 'access') record.access.HasUniqueRoleAssignments=true;
      if(session.damageAfter === 'field') record.item.Unrelated='unexpected';
      if(session.damageAfter === 'history') record.versions.value.shift();
      if(session.failAfter === id) throw Error('fictional response lost after save');
      return {};
    }
    if(request.url.includes('/fields?')) return {value:structuredClone(fields)};
    if(request.url.includes(`lists(guid'${registry}')`)) return structuredClone(evidence.parent);
    const record = records.get(request.url.match(/GetFileById\('([^']+)'\)/)?.[1]) || [...records.values()].find(r=>request.url.startsWith(itemUrl(r.item.Id)));
    assert.ok(record,`unexpected fictional endpoint ${request.url}`);
    if(request.url.includes('/$value')) return Buffer.from(session.badPrior && request.url.includes('/Versions(') ? 'wrong prior bytes' : record.bytes);
    if(request.url.includes('/Versions?')) return structuredClone(record.versions);
    if(request.url.includes('HasUniqueRoleAssignments')) return structuredClone(record.access);
    if(request.url.includes('/ListItemAllFields') || request.url.startsWith(itemUrl(record.item.Id))) return structuredClone(record.item);
    return structuredClone(record.file);
  }};
  const run = () => (kind === 'paper' ? applyPaperLibraryMetadata : applyReportLibraryMetadata)({target,plan,binding:pin,session,journalRoot:directory});
  return {directory,target,plan,binding:pin,session,records,requests,fields,sourcePath,evidence,run};
}

for(const kind of ['paper','report']) {
  test(`${kind}: guarded save and unchanged replay preserve content, history and human fields`, async t=>{
    const f = fixture(t,kind);const original = structuredClone(f.plan);
    const first = await f.run();assert.equal(first.writes,1);
    const posts = f.requests.filter(r=>r.method==='POST');assert.equal(posts.length,1);
    assert.equal(posts[0].headers['X-HTTP-Method'],'MERGE');
    assert.equal(f.records.get(guid(1)).item.Unrelated,'preserve');
    assert.equal(f.records.get(guid(1)).bytes.toString(),bytes.toString());
    const replay = await f.run();assert.equal(replay.writes,0);
    assert.equal(f.requests.filter(r=>r.method==='POST').length,1);
    assert.deepEqual(f.plan,original);
    const journal = fs.readFileSync(first.journalPath,'utf8');assert.match(journal,/intent/);assert.match(journal,/verified/);
  });
  test(`${kind}: rejects SDK, identity, interactive auth, lock and read-only authority before requests`, async t=>{
    for(const [key,value] of [['sdkVersion','drift'],['appId',guid(99)],['username','other@example.invalid'],['resource','https://other.sharepoint.com'],['interactiveAuth',true],['sharedLockHeld',false],['mutationQualified',false],['retries',1],['maxRedirects',1],['operation','read']]) {
      const f = fixture(t,kind);f.session.qualification[key]=value;
      await assert.rejects(f.run());assert.equal(f.requests.length,0,key);
    }
  });
  test(`${kind}: rejects tampered pinned source and unexpected targets before requests`, async t=>{
    const f = fixture(t,kind);fs.appendFileSync(f.sourcePath,' ');
    await assert.rejects(f.run());assert.equal(f.requests.length,0);
    const g=fixture(t,kind);g.target.site_url='https://other.sharepoint.com/sites/research';
    await assert.rejects(g.run());assert.equal(g.requests.length,0);
    const h=fixture(t,kind);(kind==='paper'?h.plan:h.plan.items[0]).changes={Title:'out of scope'};
    if(kind==='paper') h.plan.item_url=itemUrl(99);
    await assert.rejects(h.run());assert.equal(h.requests.length,0);
  });
  test(`${kind}: preserves human edits and refuses ETag drift without writes`, async t=>{
    const f=fixture(t,kind);const r=f.records.get(guid(1));r.item[kind==='paper'?'Title':'RIMSGeneration']='Human edit';r.item['odata.etag']='"9"';
    await assert.rejects(f.run());assert.equal(f.requests.filter(r=>r.method==='POST').length,0);assert.equal(r.item[kind==='paper'?'Title':'RIMSGeneration'],'Human edit');
  });
  test(`${kind}: uncertain write is never resent; matching readback reconciles`, async t=>{
    const f=fixture(t,kind);f.session.failAfter=1;
    await assert.rejects(f.run(),/fictional response lost/);
    f.session.failAfter=undefined;const result=await f.run();assert.equal(result.writes,0);
    assert.equal(f.requests.filter(r=>r.method==='POST').length,1);
    assert.match(fs.readFileSync(result.journalPath,'utf8'),/reconciled/);
    const g=fixture(t,kind);g.session.failBefore=1;await assert.rejects(g.run());g.session.failBefore=undefined;
    await assert.rejects(g.run(),/UNCERTAIN/);assert.equal(g.requests.filter(r=>r.method==='POST').length,1);
  });
  test(`${kind}: corrupt bytes or incomplete versions stop before mutation`, async t=>{
    const f=fixture(t,kind);f.records.get(guid(1)).bytes=Buffer.from('changed');await assert.rejects(f.run());
    assert.equal(f.requests.filter(r=>r.method==='POST').length,0);
    const g=fixture(t,kind);g.records.get(guid(1)).versions['@odata.nextLink']='next';await assert.rejects(g.run());
    assert.equal(g.requests.filter(r=>r.method==='POST').length,0);
  });
  test(`${kind}: native CLI entry is disabled before any SDK import`, ()=>{
    const r=spawnSync(process.execPath,[`scripts/apply_${kind}_library_metadata.mjs`,'fictional'],{encoding:'utf8'});
    assert.notEqual(r.status,0);assert.match(r.stderr,/NATIVE_ENTRY_DISABLED/);
  });
  test(`${kind}: existing lock, journal symlink and truncated evidence cannot be replaced`,async t=>{
    const f=fixture(t,kind);const first=await f.run();const before=fs.readFileSync(first.journalPath);
    fs.mkdirSync(first.journalPath+'.lock');
    await assert.rejects(f.run());assert.deepEqual(fs.readFileSync(first.journalPath),before);
    assert.ok(fs.existsSync(first.journalPath+'.lock'));fs.rmdirSync(first.journalPath+'.lock');
    fs.appendFileSync(first.journalPath,'{"interrupted":');const calls=f.requests.length;
    await assert.rejects(f.run(),/Incomplete journal/);assert.equal(f.requests.length,calls);
    const g=fixture(t,kind);const saved=await g.run();const protectedFile=path.join(g.directory,'protected.jsonl');fs.renameSync(saved.journalPath,protectedFile);fs.symlinkSync(protectedFile,saved.journalPath);
    const protectedBytes=fs.readFileSync(protectedFile);await assert.rejects(g.run());assert.deepEqual(fs.readFileSync(protectedFile),protectedBytes);
  });
  test(`${kind}: post-save access, unrelated-field and history failures retain effect evidence`,async t=>{
    for(const damage of ['access','field','history']) {
      const f=fixture(t,kind);f.session.damageAfter=damage;await assert.rejects(f.run());
      assert.equal(f.requests.filter(r=>r.method==='POST').length,1);
      const log=fs.readFileSync(path.join(f.directory,fs.readdirSync(f.directory).find(n=>n.endsWith('.jsonl'))),'utf8');
      assert.match(log,/"event":"preimage"/);assert.match(log,/"event":"intent"/);assert.match(log,/"event":"stopped"/);
      assert.doesNotMatch(log,/"event":"verified"/);
      await assert.rejects(f.run());assert.equal(f.requests.filter(r=>r.method==='POST').length,1);
    }
  });
  test(`${kind}: source version bytes must qualify before the first write`,async t=>{
    const f=fixture(t,kind);f.session.badPrior=true;await assert.rejects(f.run());
    assert.equal(f.requests.filter(r=>r.method==='POST').length,0);
    const g=fixture(t,kind);const p=kind==='paper'?g.plan:g.plan.items[0];delete p.file_preimage.UIVersionLabel;
    await assert.rejects(g.run());assert.equal(g.requests.length,0);
  });
  test(`${kind}: session drift cannot move the saved binding after preflight starts`,async t=>{
    const f=fixture(t,kind);const request=f.session.request;
    f.session.request=async input=>{const response=await request(input);f.binding.sdkVersion='changed';f.session.qualification.sdkVersion='changed';return response;};
    await assert.rejects(f.run(),/identity drift/);assert.equal(f.requests.length,1);
  });
  test(`${kind}: metadata flags without an active qualification guard confer no transport authority`,async t=>{
    const f=fixture(t,kind);delete f.session.assertQualified;
    await assert.rejects(f.run());assert.equal(f.requests.length,0);
  });
  test(`${kind}: throttled mutation errors are not automatically retried`,async t=>{
    for(const status of [429,503]) {
      const f=fixture(t,kind);const request=f.session.request;
      f.session.request=async input=>{
        if(input.method==='POST'){f.requests.push(structuredClone(input));throw Object.assign(Error('fictional throttle'),{status});}
        return request(input);
      };
      await assert.rejects(f.run(),/fictional throttle/);
      await assert.rejects(f.run(),/UNCERTAIN/);
      assert.equal(f.requests.filter(r=>r.method==='POST').length,1);
    }
  });
  test(`${kind}: access response ETags may advance while access shape remains unchanged`,async t=>{
    const f=fixture(t,kind);const request=f.session.request;
    f.session.request=async input=>{const result=await request(input);
      if(input.method==='GET'&&Object.hasOwn(result,'HasUniqueRoleAssignments'))result['odata.etag']=f.records.get(guid(1)).item['odata.etag'];
      return result;};
    assert.equal((await f.run()).writes,1);assert.equal((await f.run()).writes,0);
    assert.equal(f.requests.filter(r=>r.method==='POST').length,1);
  });
}

test('report: partial-batch response loss preserves completed evidence and forbids resend',async t=>{
  const f=fixture(t,'report',2);f.session.failAfter=2;await assert.rejects(f.run());
  const journal=fs.readdirSync(f.directory).find(p=>p.endsWith('.jsonl'));const text=fs.readFileSync(path.join(f.directory,journal),'utf8');
  assert.match(text,/verified/);assert.match(text,/uncertain/);
  f.session.failAfter=undefined;assert.equal((await f.run()).writes,0);
  assert.equal(f.requests.filter(r=>r.method==='POST').length,2);
});

test('report: a later invalid artifact prevents every write in the selected batch',async t=>{
  const f=fixture(t,'report',2);f.records.get(guid(2)).bytes=Buffer.from('changed');await assert.rejects(f.run());
  assert.equal(f.requests.filter(r=>r.method==='POST').length,0);
});

test('report: omitted intended changes cannot cause an empty metadata write',async t=>{
  const f=fixture(t,'report');f.plan.items[0].changes={};f.plan.items[0].before={};
  await assert.rejects(f.run());assert.equal(f.requests.length,0);
});

test('paper: qualified rich-text href normalization permits unchanged replay',async t=>{
  const f=fixture(t,'paper');f.plan.changes.OData__ExtendedDescription += '<p><a href="https://example.sharepoint.com/sites/research/Source%20manifest">Source manifest</a></p>';
  await f.run();const record=f.records.get(guid(1));record.item.OData__ExtendedDescription=record.item.OData__ExtendedDescription.replace('href="https://example.sharepoint.com','href="');
  const replay=await f.run();assert.equal(replay.writes,0);assert.equal(f.requests.filter(r=>r.method==='POST').length,1);
});

test('report: native URL metadata wrappers preserve exact link values on save and replay',async t=>{
  const f=fixture(t,'report');f.plan.fields.RIMSGenerationManifest=['Accepted generation manifest','URL'];
  f.fields.push({InternalName:'RIMSGenerationManifest',TypeAsString:'URL',ReadOnlyField:false,Required:false,Hidden:false});
  const value={Url:'https://example.sharepoint.com/sites/research/manifest.json',Description:'Authoritative manifest'};
  const p=f.plan.items[0];p.properties.RIMSGenerationManifest=value;p.changes.RIMSGenerationManifest=value;p.before.RIMSGenerationManifest=null;
  const request=f.session.request;f.session.request=async input=>{const result=await request(input);
    if(input.method==='GET'&&result.RIMSGenerationManifest)result.RIMSGenerationManifest.__metadata={type:'SP.FieldUrlValue'};
    return result;};
  assert.equal((await f.run()).writes,1);assert.equal((await f.run()).writes,0);
  assert.equal(f.requests.filter(r=>r.method==='POST').length,1);
});
