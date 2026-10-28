// Apache-2.0. Offline change-log admission and transport checks.
import test, {after} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import {execFileSync} from 'node:child_process';
import {validatePlan,makeQuery,runGuarded} from '../scripts/sharepoint_change_log_read.mjs';
// This test file runs in its own Node test process. Preserve the real Git
// ignore guard inside a disposable checkout, including in clean source archives.
const previousCwd=process.cwd();
const testRoot=fs.mkdtempSync(path.join(os.tmpdir(),'rims-change-log-fixture-'));
execFileSync('git',['init','--quiet',testRoot]);
fs.writeFileSync(path.join(testRoot,'.gitignore'),'*\n');
process.chdir(testRoot);
after(()=>{process.chdir(previousCwd);fs.rmSync(testRoot,{recursive:true,force:true});});
const root="https://example.sharepoint.com/sites/test/_api/web/lists(guid'11111111-1111-1111-1111-111111111111')";
const plan={listUrl:root,startToken:'1;3;11111111-1111-1111-1111-111111111111;1;1',endToken:'1;3;11111111-1111-1111-1111-111111111111;2;2'};
test('only an already pinned exact list and native same-list token bounds are admitted',()=>{
  assert.equal(validatePlan(plan,[root]).url,root+'/GetChanges');
  for(const bad of [{...plan,listUrl:root+'/items'},{...plan,listUrl:root+'?x=1'},{...plan,startToken:plan.startToken.replace('11111111','22222222')},{...plan,startToken:plan.endToken},{...plan,method:'PATCH'}]) assert.throws(()=>validatePlan(bad,[root]));
  assert.throws(()=>validatePlan(plan,[root.split('/_api')[0]]));
});
test('fixed query covers system updates and deletion without caller-controlled write payloads',()=>{
  const q=makeQuery(plan.startToken,plan.endToken).query;
  for(const k of ['Item','List','Field','View','ContentType','Update','SystemUpdate','DeleteObject','Restore','RoleAssignmentAdd','RoleAssignmentDelete']) assert.equal(q[k],true);
  assert.equal(q.FetchLimit,'100');assert.equal(q.LatestFirst,false);assert.deepEqual(q.ChangeTokenStart,{StringValue:plan.startToken});
});
test('isolated transport sends only exact read-only POST, uses one pinned resource, and retains empty proof',async()=>{
  const parent=fs.mkdtempSync(path.join(testRoot,'change-log-offline-test-'));const file=path.join(parent,'plan.json');fs.writeFileSync(file,JSON.stringify(plan));
  let calls=0,authCalls=0;
  try {
    await runGuarded({args:[file,path.join(parent,'receipt')],pin:{readUrlPrefixes:[root],resources:['https://example.sharepoint.com']},auth:{ensureAccessToken:async resource=>{assert.equal(resource,'https://example.sharepoint.com');authCalls++;return 'synthetic-offline-only';}},request:{req:async config=>{calls++;assert.equal(config.url,root+'/GetChanges');assert.equal(config.method,'POST');assert.equal(config.maxRedirects,0);assert.deepEqual(JSON.parse(config.data),makeQuery(plan.startToken,plan.endToken));return {status:200,data:'{"d":{"results":[]}}'};}}});
    assert.equal(calls,1);assert.equal(authCalls,1);const r=JSON.parse(fs.readFileSync(path.join(parent,'receipt/complete.json')));assert.equal(r.complete,true);assert.deepEqual(r.changes,[]);assert.equal(r.nativeMutations,0);
  } finally {fs.rmSync(parent,{recursive:true});}
});
test('partial responses and malformed or incomplete rows cannot certify empty history',async()=>{
  for(const response of [{status:206,data:'{"d":{"results":[]}}'},{status:200,data:'{"value":[],"odata.nextLink":"untrusted"}'},{status:200,data:'{"value":[null]}'},{status:200,data:JSON.stringify({value:Array(101).fill({})})}]){
    const parent=fs.mkdtempSync(path.join(testRoot,'change-log-rejected-'));const file=path.join(parent,'plan.json');fs.writeFileSync(file,JSON.stringify(plan));let calls=0;
    try{
      await assert.rejects(runGuarded({args:[file,path.join(parent,'receipt')],pin:{readUrlPrefixes:[root],resources:['https://example.sharepoint.com']},auth:{ensureAccessToken:async()=> 'synthetic-only'},request:{req:async()=>{calls++;return response;}}}),/Unexpected change-log response/);
      assert.equal(calls,1);assert.ok(!fs.existsSync(path.join(parent,'receipt/complete.json')));
    }finally{fs.rmSync(parent,{recursive:true});}
  }
});
