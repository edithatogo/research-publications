import test from 'node:test';import assert from 'node:assert/strict';import fs from 'node:fs';import os from 'node:os';import path from 'node:path';
import {acquireWorkloadLock} from '../scripts/m365_workload_lock.mjs';
test('a waiting operation never removes an existing owner and acquires only after release',async()=>{
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'rims-lock-')),lock=path.join(dir,'lock');fs.mkdirSync(lock);fs.writeFileSync(path.join(lock,'owner.json'),'original-owner');let acquired=false;
 try{const waiter=acquireWorkloadLock(lock,{timeoutMs:1000,intervalMs:5}).then(()=>{acquired=true;});await new Promise(r=>setTimeout(r,20));assert.equal(acquired,false);assert.equal(fs.readFileSync(path.join(lock,'owner.json'),'utf8'),'original-owner');fs.rmSync(lock,{recursive:true});await waiter;assert.equal(acquired,true);assert.equal(fs.existsSync(lock),true);assert.equal(fs.existsSync(path.join(lock,'owner.json')),false);}finally{fs.rmSync(dir,{recursive:true});}
});
test('timeout preserves the other owner and leaves the contender outside the lock',async()=>{
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'rims-lock-')),lock=path.join(dir,'lock');fs.mkdirSync(lock);fs.writeFileSync(path.join(lock,'owner.json'),'still-running');
 try{await assert.rejects(acquireWorkloadLock(lock,{timeoutMs:15,intervalMs:5}),/owner remains active/);assert.equal(fs.readFileSync(path.join(lock,'owner.json'),'utf8'),'still-running');}finally{fs.rmSync(dir,{recursive:true});}
});
test('invalid waits fail before filesystem acquisition',async()=>{
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'rims-lock-invalid-')),lock=path.join(dir,'lock');
 try{for(const options of [{timeoutMs:NaN},{timeoutMs:Infinity},{timeoutMs:-1},{intervalMs:0}])await assert.rejects(acquireWorkloadLock(lock,options),/bounded lock wait/);assert.equal(fs.existsSync(lock),false);}finally{fs.rmSync(dir,{recursive:true});}
});
