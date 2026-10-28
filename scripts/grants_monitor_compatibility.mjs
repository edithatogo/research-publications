// SPDX-License-Identifier: Apache-2.0
// Offline argument admission against the proposed wrapper; no SDK/auth import,
// native calls, lock, output-file creation or private binding edits.
import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {execFileSync} from 'node:child_process';
import {prepareRead} from './m365_read_guard.mjs';

export function validateMonitorCompatibility(config,pin,{readOutputPath,assertPrivate,sdkPackage,archiveCommands={}}={}){
  const checks=[];
  const probe=(label,args)=>{
    try{prepareRead([...args,'--output','json'],pin,assertPrivate);checks.push({label,admitted:true});}
    catch{checks.push({label,admitted:false,reason:'stricter_read_guard_rejected'});}
  };
  if(!config||!pin||typeof assertPrivate!=='function'||!readOutputPath||!sdkPackage
      ||Object.keys(config.sources??{}).length!==2||!['nhmrc','mrff'].every(s=>config.sources[s]))throw Error('Complete monitor snapshot and offline guard inputs required');
  checks.push({label:'sdk-package-pin',admitted:sdkPackage.name==='@pnp/cli-microsoft365'&&sdkPackage.version===pin.sdkVersion});
  for(const [source,settings] of Object.entries(config.sources)){
    probe(source+'-flow',['flow','get','--name',settings.flow_id,'--environmentName',config.environment]);
    probe(source+'-history',['flow','run','list','--flowName',settings.flow_id,'--environmentName',config.environment]);
    const commands=archiveCommands[source];
    // A frozen admission sample is not a policy for future generations.
    if(!Array.isArray(commands)||!commands.length)checks.push({label:source+'-archive',admitted:null,reason:'dynamic_archive_commands_not_supplied'});
    else for(const [index,args] of commands.entries()){
      if(!Array.isArray(args)||!['spo file get','spo file list'].includes(args.slice(0,3).join(' ')))throw Error('Only frozen archive read commands are accepted');
      probe(source+'-archive-'+index,args);
    }
  }
  for(const [store,root] of Object.entries(config.stores??{})){
    if(!['registry','calendar','watchlist','ledger','calendar-changes'].includes(store))throw Error('Unknown store label; no target inferred');
    for(const [kind,suffix] of [['metadata','?$select=Id,Title,ReadSecurity,WriteSecurity,EnableVersioning'],['fields','/fields?$top=5000'],['items','/items?$top=5000']]){
      probe(store+'-'+kind,['request','--url',root+suffix,'--method','get','--filePath',readOutputPath,'--accept','application/json;odata=minimalmetadata']);
    }
  }
  const rejected=checks.filter(c=>c.admitted===false).length,unknown=checks.filter(c=>c.admitted===null).length;
  return {status:rejected?'incompatible':unknown?'incomplete':'compatible_frozen_commands',checks,rejected,unknown,
    scope:'proposed_guarded_read_admission_only',whole_monitor_qualified:false,native_calls:0,private_writes:0,
    unchecked:['future_archive_generations','account_client_resource_authentication','notification_worker','host_schedule','active_wrapper_deployment']};
}

if(process.argv[1]&&import.meta.url===pathToFileURL(path.resolve(process.argv[1])).href){
  try{
    const [configFile,bindingFile,readOutputPath,archiveFile]=process.argv.slice(2);
    if(!configFile||!bindingFile||!readOutputPath)throw Error('Arguments required');
    const config=JSON.parse(fs.readFileSync(configFile)),pin=JSON.parse(fs.readFileSync(bindingFile));
    const sdkPackage=JSON.parse(fs.readFileSync(path.join(pin.sdkRoot,'package.json')));
    const assertPrivate=file=>execFileSync('git',['-C',config.repository,'check-ignore','-q',path.resolve(file)],{stdio:'ignore'});
    const result=validateMonitorCompatibility(config,pin,{readOutputPath,assertPrivate,sdkPackage,
      archiveCommands:archiveFile?JSON.parse(fs.readFileSync(archiveFile)):{} });
    console.log(JSON.stringify(result,null,2));process.exitCode=result.status==='compatible_frozen_commands'?0:2;
  }catch{console.error('Offline monitor compatibility input or admission check failed; no native call or configuration write occurred.');process.exitCode=2;}
}
