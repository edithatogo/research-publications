import test from 'node:test';
import assert from 'node:assert/strict';
import {execute,fields} from '../scripts/relationship_store.mjs';
const target={listUrl:"https://example.invalid/_api/web/lists(guid'11111111-1111-1111-1111-111111111111')",title:'Grant Relationships'};
const values=Object.fromEntries(fields.map(f=>[f,f==='EvidenceURL'?{Url:'https://example.invalid',Description:'evidence'}:f==='RelationshipKey'?'REL:'+'a'.repeat(24):f==='Confidence'?'candidate':f==='RelationshipType'?'candidate_award_match':'value']));
function setup({existing=false,uncertain=false,concurrent=false}={}){
 let row=existing?{Id:1,__metadata:{etag:'"2"'},...structuredClone(values)}:null;
 if(concurrent)row.ReviewStatus='human edit';
 let writes=0;const receipts={};
 const send=async c=>{
  assert.equal(c.maxRedirects,0);
  if(c.method==='POST'){writes++;row={Id:1,__metadata:{etag:'"3"'},...JSON.parse(c.data)};if(uncertain)throw Error('Lost response');return {data:'',status:201};}
  let d;if(c.url.endsWith('/fields'))d={results:fields.map(f=>({InternalName:f,TypeAsString:f==='RelationshipHistory'?'Note':f==='EvidenceURL'?'URL':['Confidence','RelationshipType'].includes(f)?'Choice':'Text',ReadOnlyField:false,RichText:false,AppendOnly:false,EnforceUniqueValues:true,Indexed:true,Choices:{results:['candidate','candidate_award_match']}}))};
  else if(c.url.includes('/items'))d=c.url.includes('/items(')?row:{results:row?[row]:[]};
  else d={Title:target.title,EnableVersioning:true};
  return {status:200,data:{d}};
 };
 return {send,save:(n,v)=>{receipts[n]=v;},writes:()=>writes,receipts};
}
test('create reconciles a lost response without resending',async()=>{
 const io=setup({uncertain:true});const r=await execute({target,plan:{operation:'apply',item_id:null,etag:null,before:null,after:values},...io});
 assert.equal(r.outcome,'candidate_present');assert.equal(io.writes(),1);assert.ok(io.receipts['send-intent.json']);
});
test('identical replay sends nothing',async()=>{
 const io=setup({existing:true});const r=await execute({target,plan:{operation:'apply',item_id:null,before:null,after:values},...io});
 assert.equal(r.outcome,'unchanged_replay');assert.equal(io.writes(),0);
});
test('human edit and stale ETag refuse updates',async()=>{
 for(const concurrent of [true,false]){
  const io=setup({existing:true,concurrent});await assert.rejects(execute({target,plan:{operation:'apply',item_id:1,etag:'"1"',before:values,after:{...values,ReviewStatus:'Withdrawn'}},...io}),/no write sent/);assert.equal(io.writes(),0);
 }
});
test('update uses exact conditional headers and preserves unrelated fields',async()=>{
 const io=setup({existing:true});const send=async c=>{if(c.method==='POST'){assert.equal(c.headers['IF-MATCH'],'"2"');assert.equal(c.headers['X-HTTP-Method'],'MERGE');assert.equal(JSON.parse(c.data).Title,undefined);}return io.send(c);};
 const r=await execute({target,plan:{operation:'apply',item_id:1,etag:'"2"',before:values,after:{...values,ReviewStatus:'Withdrawn'}},...io,send});assert.equal(r.outcome,'candidate_present');assert.equal(io.writes(),1);
});
test('throttled prerequisite read stops before writes and strips transport secrets',async()=>{
 let writes=0;
 await assert.rejects(execute({target,plan:{operation:'schema'},save:()=>{},send:async c=>{
  if(c.method==='POST')writes++;
  const e=Error('sensitive transport details');e.response={status:429};e.config={headers:{Authorization:'secret'}};throw e;
 }}),e=>e.message==='Relationship request stopped: 429'&&e.status===429&&e.config===undefined);
 assert.equal(writes,0);
});
