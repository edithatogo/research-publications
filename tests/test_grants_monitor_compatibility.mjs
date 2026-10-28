// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {validateMonitorCompatibility} from '../scripts/grants_monitor_compatibility.mjs';

function fixture(){
  const parent=path.resolve('.venv/m365-offline-tests');fs.mkdirSync(parent,{recursive:true});
  const directory=fs.mkdtempSync(path.join(parent,'monitor-compatibility-'));
  const flow=(name)=>'https://api.flow.microsoft.com/providers/Microsoft.ProcessSimple/environments/offline/flows/'+name;
  const list="https://example.sharepoint.com/sites/offline/_api/web/lists(guid'11111111-1111-4111-8111-111111111111')";
  const config={environment:'offline',sources:{nhmrc:{flow_id:'offline-nhmrc'},mrff:{flow_id:'offline-mrff'}},stores:{registry:list}};
  const pin={sdkVersion:'synthetic-version',readUrlPrefixes:[flow('offline-nhmrc'),flow('offline-mrff'),list]};
  const archive=['spo','file','list','--webUrl','https://example.sharepoint.com/sites/offline','--folderUrl','/sites/offline/archive','--output','json'];
  const options={readOutputPath:path.join(directory,'never-created.json'),assertPrivate:()=>{},sdkPackage:{name:'@pnp/cli-microsoft365',version:pin.sdkVersion}};
  return {config,pin,options,archive,close:()=>fs.rmSync(directory,{recursive:true})};
}

test('static admissions cannot qualify missing dynamic archive commands',()=>{
  const f=fixture();try{
    const before=JSON.stringify([f.config,f.pin]);const result=validateMonitorCompatibility(f.config,f.pin,f.options);
    assert.equal(result.status,'incomplete');assert.equal(result.unknown,2);assert.equal(result.rejected,0);
    assert.equal(result.whole_monitor_qualified,false);assert.equal(result.native_calls,0);assert.equal(result.private_writes,0);
    assert.equal(fs.existsSync(f.options.readOutputPath),false);assert.equal(JSON.stringify([f.config,f.pin]),before);
  }finally{f.close();}
});
test('frozen named archive admission remains separate from future operational qualification',()=>{
  const f=fixture();try{
    f.pin.readCommandArguments=[f.archive];f.options.archiveCommands={nhmrc:[f.archive.slice(0,-2)],mrff:[f.archive.slice(0,-2)]};
    const result=validateMonitorCompatibility(f.config,f.pin,f.options);
    assert.equal(result.status,'compatible_frozen_commands');assert.equal(result.whole_monitor_qualified,false);
    assert.ok(result.unchecked.includes('future_archive_generations'));assert.equal(fs.existsSync(f.options.readOutputPath),false);
  }finally{f.close();}
});
test('missing flow roots, archive pins or SDK version are explicit incompatibilities without exposing targets',()=>{
  const f=fixture();try{
    f.pin.readUrlPrefixes=f.pin.readUrlPrefixes.slice(2);f.options.archiveCommands={nhmrc:[f.archive.slice(0,-2)],mrff:[f.archive.slice(0,-2)]};f.options.sdkPackage.version='changed';
    const result=validateMonitorCompatibility(f.config,f.pin,f.options);
    assert.equal(result.status,'incompatible');assert.equal(result.rejected,7);
    const output=JSON.stringify(result);assert.ok(!output.includes('example.sharepoint.com'));assert.ok(!output.includes('offline-nhmrc'));
  }finally{f.close();}
});
test('unsafe output admission and unrecognised commands cannot be treated as healthy',()=>{
  const f=fixture();try{
    f.options.assertPrivate=()=>{throw Error('not ignored');};const result=validateMonitorCompatibility(f.config,f.pin,f.options);
    assert.equal(result.status,'incompatible');assert.equal(result.checks.filter(c=>c.label.startsWith('registry-')&&c.admitted===false).length,3);
    f.options.archiveCommands={nhmrc:[['spo','list','remove']]};assert.throws(()=>validateMonitorCompatibility(f.config,f.pin,f.options));
  }finally{f.close();}
});
