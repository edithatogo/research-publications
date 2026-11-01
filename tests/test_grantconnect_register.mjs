import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import crypto from 'node:crypto';
import {createRegisterRows} from '../scripts/grantconnect_register.mjs';

test('bootstrap preserves existing rows, creates only missing keys, and refuses conflicts before writing', async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(),'grantconnect-'));
  try {
    const url='https://example.invalid/list';
    const rows=['existing','new'].map(key=>({OpportunityKey:key,Source:'GrantConnectRSS',ReviewStatus:'Needs Review',EvidenceHash:key,URL:'https://www.grants.gov.au/'}));
    const raw=JSON.stringify({kind:'grantconnect_xml_register_v1',rows,count:2});
    const input=path.join(root,'input'), receipt=path.join(root,'receipt');
    fs.writeFileSync(input,raw); fs.writeFileSync(receipt,JSON.stringify({status:'PASS_COMPLETE',files:[{sha256:crypto.createHash('sha256').update(raw).digest('hex')}]}));
    let hash='existing'; const writes=[];
    const run=dir=>createRegisterRows({args:[input,receipt,path.join(root,dir)],pin:{grantConnectListUrl:url,resources:['https://example.invalid'],readUrlPrefixes:[url]},auth:{ensureAccessToken:async()=>'fixture'},request:{req:async c=>{
      if(c.method==='post'){writes.push(c.data);return {status:201};}
      if(c.url.includes('/fields/'))return {data:{EnforceUniqueValues:true}};
      if(c.url.includes('/items?'))return {data:{value:[{OpportunityKey:'existing',EvidenceHash:hash}]}};
      return {data:{Title:'Grants Registry'}};
    }}});
    await run('first');assert.deepEqual(writes.map(x=>x.OpportunityKey),['new']);
    hash='changed';await assert.rejects(run('second'),/conflict/);assert.equal(writes.length,1);
  } finally {fs.rmSync(root,{recursive:true,force:true});}
});
