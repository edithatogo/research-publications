// Apache-2.0. Offline tests: no authentication or native requests.
import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {submitCandidate} from '../scripts/g06_candidate_writer.mjs';
const url="https://example.sharepoint.com/sites/dev/_api/web/lists(guid'11111111-1111-1111-1111-111111111111')";
const row={RelationshipKey:'REL:'+'a'.repeat(24),RelationshipType:'candidate_award_match',FromKey:'PUB:1',ToKey:'ARC:1',AwardID:'1',EvidenceURL:{Url:'https://example.org/evidence'},Confidence:'candidate',ReviewStatus:'Needs Review'};
function setup(t) {const journalRoot=fs.mkdtempSync(path.join(os.tmpdir(),'g06-'));t.after(()=>fs.rmSync(journalRoot,{recursive:true}));return {listUrl:url,pinnedListUrl:url,row,journalRoot};}
test('intent is durable before submission; saved readback and zero-write replay',async t=>{
  const p=setup(t);let rows=[],writes=0;
  const readByKey=async()=>rows;
  const createOnce=async r=>{assert.ok(fs.readdirSync(p.journalRoot).some(n=>n.endsWith('.intent.json')));writes++;rows=[{...r,Id:1}];return {status:201};};
  assert.equal((await submitCandidate({...p,readByKey,createOnce})).state,'created');
  rows[0].ReviewStatus='Reviewed';rows[0].Confidence='review';
  assert.equal((await submitCandidate({...p,readByKey,createOnce})).state,'preserved');assert.equal(writes,1);assert.equal(rows[0].ReviewStatus,'Reviewed');
});
test('uncertain submission refuses a second send even when exact key is absent',async t=>{
  const p=setup(t);let writes=0;const args={...p,readByKey:async()=>[],createOnce:async()=>{writes++;throw Error('timeout');}};
  await assert.rejects(submitCandidate(args),/timeout/);await assert.rejects(submitCandidate(args),/EEXIST/);assert.equal(writes,1);
});
test('changed target and noncandidate payload fail before read or submission',async t=>{
  const p=setup(t);let calls=0;const callbacks={readByKey:async()=>{calls++;return[];},createOnce:async()=>{calls++;}};
  await assert.rejects(submitCandidate({...p,...callbacks,pinnedListUrl:url+'x'}),/pinned/);
  await assert.rejects(submitCandidate({...p,...callbacks,row:{...row,Confidence:'confirmed'}}),/candidate/);assert.equal(calls,0);
});
test('failed post-create readback retains intent and cannot submit again',async t=>{
  const p=setup(t);let calls=0,writes=0;
  const args={...p,readByKey:async()=>{calls++;return [];},createOnce:async()=>{writes++;return {status:201};}};
  await assert.rejects(submitCandidate(args),/readback mismatch/);
  await assert.rejects(submitCandidate(args),/EEXIST/);
  assert.equal(writes,1);assert.ok(calls>=3);
});
test('an existing conflicting identity is never overwritten',async t=>{
  const p=setup(t);let writes=0;
  await assert.rejects(submitCandidate({...p,readByKey:async()=>[{...row,ToKey:'PUB:different'}],createOnce:async()=>{writes++;}}),/identity conflict/);
  assert.equal(writes,0);assert.equal(fs.readdirSync(p.journalRoot).length,0);
});
