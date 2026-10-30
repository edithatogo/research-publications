// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {execute,validateTarget} from '../scripts/outcome_store.mjs';

const url = "https://example.sharepoint.com/sites/fictional/_api/web/lists(guid'00000000-0000-0000-0000-000000000001')";
const target = {listUrl:url,itemId:1,journalField:'OutcomeJournal',projectionField:'OutcomeProjection',itemUrl:url+'/items(1)'};
function fixture(mode) {
  let writes=0; let etag='"1"'; let values={journal:'{}',projection:'{}'};
  const receipts = {};
  const send = async c => {
    assert.equal(c.maxRedirects,0);
    if(c.url.includes('/fields?')) return {status:200,data:{d:{results:['OutcomeJournal','OutcomeProjection'].map(InternalName=>({InternalName,TypeAsString:'Note',RichText:false,AppendOnly:false,ReadOnlyField:false}))}}};
    if(c.method==='GET') {
      if(mode==='lost_readback' && writes) throw Error('offline');
      return {status:200,data:{d:{Id:1,__metadata:{etag},OutcomeJournal:values.journal,OutcomeProjection:values.projection}}};
    }
    assert.equal(c.method,'POST'); assert.equal(c.url,target.itemUrl); ++writes;
    assert.equal(c.headers['X-HTTP-Method'],'MERGE');
    if(mode==='race') etag='"intervening"';
    if(c.headers['IF-MATCH']!==etag) throw Object.assign(Error('conflict'),{response:{status:412}});
    const body=JSON.parse(c.data);
    assert.deepEqual(Object.keys(body).sort(),['OutcomeJournal','OutcomeProjection']);
    if(mode==='throttle') throw Object.assign(Error('throttle'),{response:{status:429}});
    values={journal:body.OutcomeJournal,projection:body.OutcomeProjection}; etag='"2"';
    if(mode==='lost_response') throw Error('connection closed');
    return {status:204};
  };
  return {send,save:(name,value)=>{assert.ok(!receipts[name]);receipts[name]=value;},writes:()=>writes};
}
const plan={operation:'apply',etag:'"1"',before:{journal:'{}',projection:'{}'},after:{journal:'{"revision":1}',projection:'{"rows":[]}'}};
test('both fields commit once; exact replay is read-only',async()=>{
  const f=fixture(); const first=await execute({target,plan,...f});
  assert.equal(first.outcome,'candidate_present');assert.equal(f.writes(),1);
  const replay=await execute({target,plan,...f,save:()=>{}});
  assert.equal(replay.outcome,'unchanged_replay');assert.equal(f.writes(),1);
});
test('uncertain writes, races and throttling reconcile without resend',async()=>{
  for(const [mode,outcome] of [['lost_response','candidate_present'],['lost_readback','unknown'],['race','conflict'],['throttle','preimage_present']]) {
    const f=fixture(mode);const result=await execute({target,plan,...f});
    assert.equal(result.outcome,outcome);assert.equal(f.writes(),1);assert.equal(result.retry_allowed,false);
  }
});
test('target pins and current schema are enforced before a write',async()=>{
  assert.throws(()=>validateTarget({outcomeTarget:{...target},resources:[],readUrlPrefixes:[]}));
  const f=fixture();const send=async c=>c.url.includes('/fields?')?{status:200,data:{d:{results:[]}}}:f.send(c);
  await assert.rejects(execute({target,plan,...f,send}),/plain text/);assert.equal(f.writes(),0);
});
