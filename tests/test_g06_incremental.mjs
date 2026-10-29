// Apache-2.0. Offline incremental-source and checkpoint contract tests.
import {test} from 'node:test';import assert from 'node:assert/strict';
import fs from 'node:fs';import os from 'node:os';import path from 'node:path';
import {prepareIncremental,sha,validatePacket,verifyPythonRuntime,readRimsBaseline} from '../scripts/g06_incremental.mjs';
const rule='a'.repeat(64);
function packet(code='1'){
 const r={RelationshipType:'candidate_award_match',FromKey:'AWARD:arc:'+code,ToKey:'PUB:'+code,AwardID:code,EvidenceURL:'https://pubmed.ncbi.nlm.nih.gov/'+code+'/',Confidence:'candidate',ReviewStatus:'Needs Review'};
 r.RelationshipKey='REL:'+sha(JSON.stringify([r.RelationshipType,r.FromKey,r.ToKey,r.AwardID,r.EvidenceURL])).slice(0,24);
 return {kind:'retained_arc_publication_relationship_candidates_v1',relationships:[r],context:[{...r,RegistryItemID:Number(code),RegistryPublicationKey:r.ToKey,PublicationSourceKey:'pubmed:'+code,PublicationCanonicalKey:'PMID:'+code,PublicationURL:r.EvidenceURL,AwardSourceID:code,AwardCode:code,AwardURL:'https://dataportal.arc.gov.au/NCGP/API/grants/'+code,RegistryRowSHA256:'b'.repeat(64),AwardRowSHA256:'c'.repeat(64),CanonicalRowSHA256:'d'.repeat(64)}],unresolved:[],coverage:{exact_candidates:1},input_hashes:{registry:'e'.repeat(64),publications:'f'.repeat(64),awards:'0'.repeat(64)}};
}
const input=(p,id='arc')=>{const raw=Buffer.from(JSON.stringify(p));return {id,raw,sha256:sha(raw)};};
const delivered=p=>({...p,kind:'g06-incremental-delivered-v1',native_verified:true});
test('context source crosswalk must agree with the submitted relationship',()=>{
 for(const [field,value] of Object.entries({RegistryPublicationKey:'PUB:other',PublicationSourceKey:'pubmed:999',PublicationURL:'https://pubmed.ncbi.nlm.nih.gov/999/',AwardSourceID:'other',AwardCode:'other',AwardURL:'https://example.org/other',RegistryItemID:0,PublicationCanonicalKey:''})){
  const p=packet();p.context[0][field]=value;assert.throws(()=>validatePacket(p),/crosswalk/,field);
 }
});
test('native preflight requires the actual selected Python version',()=>{
 assert.ok(verifyPythonRuntime().endsWith('/.venv/bin/python'));
 for(const result of [{status:0,stdout:'3.14.6'},{status:0,stdout:'3.15.0'},{status:1,stdout:'3.15.1'},{status:null}]){
  assert.throws(()=>verifyPythonRuntime((exe,args)=>{assert.ok(exe.endsWith('/.venv/bin/python'));assert.equal(args[0],'-c');return result;}),/before native/);
 }
});
test('RIMS baseline is hash/type checked before delivery and freezes prior bytes',t=>{
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'g06-baseline-'));t.after(()=>fs.rmSync(dir,{recursive:true}));
 const file=path.join(dir,'baseline.json');const raw=Buffer.from(JSON.stringify({kind:'current_native_funding_relationship_consumer_v1',identity_material:[]}));fs.writeFileSync(file,raw);
 assert.equal(readRimsBaseline(null),null);
 const frozen=readRimsBaseline({path:file,sha256:sha(raw)});fs.writeFileSync(file,'{}');assert.deepEqual(frozen,raw);
 assert.throws(()=>readRimsBaseline({path:file,sha256:sha(raw)}),/drift/);
 assert.throws(()=>readRimsBaseline({path:file,sha256:sha('{}')}),/Accepted/);
});
test('bootstrap then unchanged input reuses checkpoint; no source parsing on replay',()=>{
 const i=input(packet());const first=prepareIncremental([i],null,rule);
 assert.deepEqual(first.coverage.changed_sources,['arc']);assert.equal(first.native_verified,false);
 const replay=prepareIncremental([i],delivered(first),rule);
 assert.deepEqual(replay.coverage.reused_sources,['arc']);assert.deepEqual(replay.coverage.changed_sources,[]);assert.equal(replay.relationships.length,1);
});
test('only changed source recomputes; new source appears; context changes retain key',()=>{
 const first=delivered(prepareIncremental([input(packet()),input(packet('2'),'other')],null,rule));
 const p=packet();p.context[0].RegistryRowSHA256='9'.repeat(64);
 const next=prepareIncremental([input(p),input(packet('2'),'other'),input(packet('3'),'new')],first,rule);
 assert.deepEqual(next.coverage.changed_sources,['arc','new']);assert.deepEqual(next.coverage.reused_sources,['other']);assert.deepEqual(next.coverage.changed_context_keys,[p.relationships[0].RelationshipKey]);assert.equal(next.relationships.length,3);
});
test('removed or absent source records are labelled, never native delete instructions',()=>{
 const first=delivered(prepareIncremental([input(packet()),input(packet('2'),'other')],null,rule));
 const next=prepareIncremental([input(packet('2'),'other')],first,rule);
 assert.deepEqual(next.coverage.absent_prior_sources,['arc']);assert.equal(next.coverage.removed_source_keys.length,1);assert.equal(next.delete,undefined);
});
test('unverified receipt, raw hash drift and rule change fail closed or revalidate',()=>{
 const i=input(packet());const first=prepareIncremental([i],null,rule);
 assert.throws(()=>prepareIncremental([i],first,rule),/native-verified/);
 assert.throws(()=>prepareIncremental([i],{...delivered(first),kind:'g06-native-delivery-verified-v1'},rule),/native-verified/);
 assert.throws(()=>prepareIncremental([{...i,sha256:'0'.repeat(64)}],null,rule),/hash-bound/);
 assert.deepEqual(prepareIncremental([i],delivered(first),'1'.repeat(64)).coverage.changed_sources,['arc']);
});
test('duplicate source IDs and unsupported or forged candidates are rejected',()=>{
 const i=input(packet());assert.throws(()=>prepareIncremental([i,i],null,rule),/Distinct/);
 const p=packet();p.relationships[0].Confidence='confirmed';assert.throws(()=>prepareIncremental([input(p)],null,rule),/admission/);
 const q=packet();q.relationships[0].RelationshipKey='REL:'+'0'.repeat(24);assert.throws(()=>prepareIncremental([input(q)],null,rule),/forged/);
});
