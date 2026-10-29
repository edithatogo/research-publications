import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {classify,manifestFiles,sha,assertIdentity} from '../scripts/sync_dataset_documentation.mjs';
test('same bytes cause no version bump; accepted baseline permits changed source',()=>{
 assert.equal(classify('new','new','old'),'unchanged');assert.equal(classify('new',null,null),'create');assert.equal(classify('new','old','old'),'update');
});
test('human drift or unowned different content never gets overwritten',()=>{
 assert.throws(()=>classify('generated','human','old'),/preserve human edits/);assert.throws(()=>classify('generated','unowned',undefined),/preserve human edits/);
});
test('manifest refuses traversal, duplicate names and changed local payload',()=>{
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'rims-docs-'));try{
 const file=path.join(dir,'source.txt');fs.writeFileSync(file,'a');const f={name:'source.txt',path:file,sha256:sha(Buffer.from('a'))};
 assert.equal(manifestFiles({files:[f]}).length,1);assert.throws(()=>manifestFiles({files:[f,f]}),/duplicate/);assert.throws(()=>manifestFiles({files:[{...f,name:'../other'}]}),/Unsafe/);
 fs.writeFileSync(file,'changed');assert.throws(()=>manifestFiles({files:[f]}),/changed/);
 }finally{fs.rmSync(dir,{recursive:true});}
});

test("accepted native identity cannot be replaced or recreated",()=>{assertIdentity({UniqueId:"old"},{UniqueId:"old"});assert.throws(()=>assertIdentity({UniqueId:"old"},{UniqueId:"replacement"}),/version history/);assert.throws(()=>assertIdentity({UniqueId:"old"},undefined),/version history/);});
