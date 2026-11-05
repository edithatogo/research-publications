// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';import assert from 'node:assert/strict';
import {capture,managed} from '../scripts/capture_source_assertions.mjs';
import {spawnSync} from 'node:child_process';import fs from 'node:fs';import os from 'node:os';import path from 'node:path';
const base="https://example.sharepoint.com/sites/dev/_api/web/lists(guid'11111111-1111-1111-1111-111111111111')";
function fixture(){
 const meta={Id:'11111111-1111-1111-1111-111111111111',Title:'CHHHS RIMS | Data spaces | Source assertions - DEV',ItemCount:2,EnableVersioning:true};
 const schema=[...managed,'Title','OperatorNotes'].map(InternalName=>({InternalName,TypeAsString:['FullSummary','SourceProjectionJSON','SourceProvenanceJSON','OperatorNotes'].includes(InternalName)?'Note':'Text',ReadOnlyField:false,...(InternalName==='SourceKey'?{Indexed:true,EnforceUniqueValues:true}:{})}));
 const row=Id=>({...Object.fromEntries(managed.map(k=>[k,'synthetic'])),Id,SourceKey:'fixture:'+Id,Title:'Human title',OperatorNotes:'Human notes',Created:'2026-01-01T00:00:00Z',Modified:'2026-01-02T00:00:00Z',OData__UIVersionString:'2.0','odata.etag':'"2"'});
 const pages={'metadata-before.json':meta,'metadata-after.json':structuredClone(meta),'fields-page-0.json':{value:schema.slice(0,5),'odata.nextLink':base+'/fields?$skiptoken=next'},'fields-page-1.json':{value:schema.slice(5)},'items-page-0.json':{value:[row(1)],'@odata.nextLink':base+'/items?$skiptoken=next'},'items-page-1.json':{value:[row(2)]}};
 return {pages,run:async()=>{const saved={};const result=await capture({base,read:async(u,n)=>structuredClone(pages[n]),save:async(n,x)=>{saved[n]=x;}});return {result,saved};}};
}
test('all pages and all raw protected fields survive; unknown schema flags remain absent',async()=>{const f=fixture();const {result}=await f.run();assert.equal(result.receipt.itemPages,2);assert.equal(result.receipt.schemaPages,2);assert.equal(result.capture.response.value[0].OperatorNotes,'Human notes');assert.equal(result.capture.response.value[0]['odata.etag'],'"2"');assert.ok(!Object.hasOwn(result.schema.value[0],'RichText'));});
for(const [name,change] of [
 ['count mismatch',f=>f.pages['metadata-before.json'].ItemCount=3],
 ['metadata drift',f=>f.pages['metadata-after.json'].EnableVersioning=false],
 ['duplicate item',f=>f.pages['items-page-1.json'].value[0].Id=1],
 ['duplicate key',f=>f.pages['items-page-1.json'].value[0].SourceKey='fixture:1'],
 ['missing managed field',f=>delete f.pages['items-page-1.json'].value[0].SourceID],
 ['missing protected notes',f=>delete f.pages['items-page-1.json'].value[0].OperatorNotes],
 ['missing etag',f=>delete f.pages['items-page-1.json'].value[0]['odata.etag']],
 ['foreign continuation',f=>f.pages['items-page-0.json']['@odata.nextLink']='https://evil.example/items'],
 ['filtered continuation',f=>f.pages['items-page-0.json']['@odata.nextLink']=base+'/items?$filter=SourceKey'],
 ['loop continuation',f=>f.pages['items-page-1.json']['odata.nextLink']=base+'/items?$skiptoken=next'],
 ['unsupported envelope',f=>f.pages['items-page-1.json']={value:[],__next:'hidden'}],
 ['conflicting continuation',f=>f.pages['items-page-0.json']['odata.nextLink']=base+'/items?$skiptoken=other'],
 ['missing schema field',f=>f.pages['fields-page-1.json'].value.pop()],
 ['non-text managed field',f=>f.pages['items-page-1.json'].value[0].SourceID=9],
])test(name+' rejects without emitting capture',async()=>{const f=fixture();change(f);const saved=[];await assert.rejects(capture({base,read:async(u,n)=>structuredClone(f.pages[n]),save:async n=>saved.push(n)}));assert.deepEqual(saved,[]);});
test('actual empty list succeeds only with stable zero count and empty response',async()=>{const f=fixture();f.pages['metadata-before.json'].ItemCount=0;f.pages['metadata-after.json'].ItemCount=0;f.pages['items-page-0.json']={value:[]};assert.equal((await f.run()).result.receipt.rows,0);});
test('output consumed by integrator bind_inventory and schema_requirements', {skip:!process.env.SOURCE_CONTRACT_REPO?'Set SOURCE_CONTRACT_REPO to retained consumer checkout':false},async()=>{
 const f=fixture();const {result}=await f.run();const tmp=fs.mkdtempSync(path.join(os.tmpdir(),'assertion-contract-'));try{
 const file=path.join(tmp,'synthetic.json');fs.writeFileSync(file,JSON.stringify(result));
 const script="import json,sys;sys.path.insert(0,sys.argv[1]);from scripts.source_assertion_persistence import bind_inventory,schema_requirements;x=json.load(open(sys.argv[2]));r=bind_inventory(**x['capture'],expected_id=x['capture']['metadata']['Id']);s=schema_requirements(x['schema']['value']);print('PASS_CONSUMER_CONTRACT',len(s))";
 const r=spawnSync(path.join(process.env.SOURCE_CONTRACT_REPO,'.venv/bin/python'),['-c',script,process.env.SOURCE_CONTRACT_REPO,file],{encoding:'utf8'});assert.equal(r.status,0,r.stderr);assert.match(r.stdout,/PASS_CONSUMER_CONTRACT/);
 }finally{fs.rmSync(tmp,{recursive:true});}
});
