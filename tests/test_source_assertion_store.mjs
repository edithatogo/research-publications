import test from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {execute,fields,policy,target as validateTarget} from '../scripts/source_assertion_store.mjs';
const plans=JSON.parse(execFileSync('.venv/bin/python',['-c',`import json,runpy
from scripts.source_assertion_persistence import prepare
r=runpy.run_path('tests/test_source_assertion_persistence.py')['revision']()
p=prepare(None,r)
r.update(revision_id='r2',supersedes='r1',state='withdrawn')
s={'item_id':7,'etag':'"1"','fields':p['after']}
print(json.dumps({'create':p,'update':prepare(s,r)}))`],{encoding:'utf8'}));
const id='11111111-1111-1111-1111-111111111111';
const target={listUrl:"https://example.invalid/sites/fixture/_api/web/lists(guid'"+id+"')",title:'CHHHS RIMS | Data spaces | Source assertions - DEV'};
function fixture({exists=false,lost=false,stale=false,unqualified=false,duplicate=false,noPostRead=false,intentFails=false}={}){
 let writes=0;let row=exists?{Id:7,__metadata:{etag:stale?'"2"':'"1"'},...structuredClone(plans.create.after),OperatorNotes:'Human notes',Title:'Human title'}:null;
 const saved={};
 const send=async c=>{
  assert.equal(c.maxRedirects,0);
  if(c.method==='POST'){
   assert.ok(saved['send-intent.json']);writes++;
   const body=JSON.parse(c.data);assert.equal(body.OperatorNotes,undefined);
   if(exists){assert.equal(c.headers['IF-MATCH'],'"1"');assert.equal(body.Title,undefined);assert.equal(c.headers['X-HTTP-Method'],'MERGE');}
   row={...row,...body,Id:7,__metadata:{etag:'"3"'}};
   if(lost){const e=Error('sensitive transport details');e.config={Authorization:'secret'};throw e;}
   return {status:204,data:''};
  }
  let d;
  if(c.url.endsWith('/fields'))d={results:fields.map(f=>({InternalName:f,TypeAsString:['FullSummary','SourceProjectionJSON','SourceProvenanceJSON'].includes(f)?'Note':'Text',ReadOnlyField:false,RichText:false,AppendOnly:false,Indexed:true,EnforceUniqueValues:!unqualified}))};
  else if(c.url.includes('/items')){
   if(writes&&noPostRead)throw Error('read unavailable');
   d=c.url.includes('/items(')?row:{results:row?(duplicate?[row,row]:[row]):[]};
  }else d={Id:id,Title:target.title,EnableVersioning:true};
  return {status:200,data:{d}};
 };
 return {send,save:(n,v)=>{if(n==='send-intent.json'&&intentFails)throw Error('disk failure');saved[n]=v;},writes:()=>writes,saved,row:()=>row};
}
test('create reconciles lost response once, retaining full provenance',async()=>{
 const io=fixture({lost:true});const r=await execute({target,plan:plans.create,...io});assert.equal(r.outcome,'candidate_present');assert.equal(io.writes(),1);assert.equal(r.retry_allowed,false);assert.deepEqual(r.current.fields,plans.create.after);
});
test('update preserves human fields and uses exact ETag',async()=>{
 const io=fixture({exists:true});const r=await execute({target,plan:plans.update,...io});assert.equal(r.outcome,'candidate_present');assert.equal(io.row().OperatorNotes,'Human notes');assert.equal(io.row().Title,'Human title');
});
test('replay, concurrency and duplicate identity do not write',async()=>{
 const replay=fixture({exists:true});assert.equal((await execute({target,plan:plans.create,...replay})).outcome,'unchanged_replay');assert.equal(replay.writes(),0);
 for(const [options,plan] of [[{exists:true,stale:true},plans.update],[{exists:true,duplicate:true},plans.create],[{unqualified:true},plans.create]]){
  const io=fixture(options);await assert.rejects(execute({target,plan,...io}));assert.equal(io.writes(),0);
 }
});
test('durable intent failure prevents send; uncertain postimage never resends',async()=>{
 const io=fixture({intentFails:true});await assert.rejects(execute({target,plan:plans.create,...io}));assert.equal(io.writes(),0);
 const unknown=fixture({lost:true,noPostRead:true});const r=await execute({target,plan:plans.create,...unknown});assert.equal(r.outcome,'unknown');assert.equal(r.retry_allowed,false);assert.equal(unknown.writes(),1);
});
test('target and domain checks reject before transport; duplicate JSON rejected',()=>{
 assert.throws(()=>validateTarget({resources:['https://example.invalid'],readUrlPrefixes:[]},target));
 assert.throws(()=>policy('validate','{"operation":"create","operation":"update"}'));
 const malformed=structuredClone(plans.create);malformed.after.Source='Other';assert.throws(()=>policy('validate',malformed));
});
