// SPDX-License-Identifier: Apache-2.0
// Pure admission guards. No auth imports, service I/O or private binding writes.
import fs from 'node:fs';
import path from 'node:path';

const fail=message=>{throw Error(message);};
export function prepareRead(args,pin,assertPrivate){
  if(args[0]!=='request'){
    const allowed=['spo file get','spo file list','flow get','flow run get','flow run list'];
    if(!allowed.some(command=>args.slice(0,command.split(' ').length).join(' ')===command)) fail('Only qualified read commands allowed');
    if(args.some(a=>['-d','-v'].includes(a)||/^--?(debug|verbose|appId|tenant|authType|connectionName|asAdmin|optionsFile)(=|$)/i.test(a))) fail('Authentication/admin/debug overrides forbidden');
    if(args[0]==='flow'){
      const run=args[1]==='run',get=run&&args[2]==='get';
      const values=new Map(),offset=run?3:2;
      const fields=run?['--flowName','--environmentName','--output',...(get?['--name']:[])]:['--name','--environmentName','--output'];
      for(let i=offset;i<args.length;i+=2){
        if(!fields.includes(args[i])||!args[i+1]||values.has(args[i])) fail('Exact flow read options required');
        values.set(args[i],args[i+1]);
      }
      if(values.size!==fields.length||values.get('--output')!=='json') fail('Complete exact flow read and JSON output required');
      for(const field of fields.filter(f=>f!=='--output')) if(!/^[A-Za-z0-9_-]{1,128}$/.test(values.get(field))) fail('Exact safe native identity required');
      const target='https://api.flow.microsoft.com/providers/Microsoft.ProcessSimple/environments/'+values.get('--environmentName')+'/flows/'+values.get(run?'--flowName':'--name');
      if(!(pin.readUrlPrefixes??[]).some(prefix=>prefix===target)) fail('Exact native flow root is not pinned');
      return {};
    }
    if(!Array.isArray(pin.readCommandArguments) || !pin.readCommandArguments.some(p=>Array.isArray(p)&&p.length===args.length&&p.every((v,i)=>typeof v==='string'&&v===args[i]))) fail('Exact read command arguments not pinned; qualify under the existing native owner');
    return {};
  }
  const values=new Map();
  for(let i=1;i<args.length;i+=2){
    if(!['--url','--method','--filePath','--output','--accept'].includes(args[i])||!args[i+1]||values.has(args[i])) fail('Pinned GET accepts only unique explicit URL/method/filePath/output and fixed Accept');
    values.set(args[i],args[i+1]);
  }
  if(values.get('--method')!=='get'||values.get('--output')!=='json') fail('Pinned request requires GET and JSON output');
  if(values.has('--accept')&&values.get('--accept')!=='application/json;odata=minimalmetadata') fail('Only fixed minimal-metadata Accept allowed');
  const rawReadUrl=new URL(values.get('--url'));
  if(rawReadUrl.protocol!=='https:'||rawReadUrl.username||rawReadUrl.password||rawReadUrl.hash||rawReadUrl.href!==values.get('--url')) fail('Exact canonical HTTPS read URL required');
  if(/%(?:25|2f|5c|2e)/i.test(rawReadUrl.pathname)) fail('Encoded read-path separators or traversal forbidden');
  const targets=pin.readUrlPrefixes??[];
  if(!targets.some(prefix=>typeof prefix==='string'&&rawReadUrl.href.startsWith(prefix)&&['','/','?'].includes(rawReadUrl.href.slice(prefix.length,prefix.length+1)))) fail('Unpinned native read target');
  const file=values.get('--filePath');
  if(!file) fail('New ignored raw-response file required');
  try{fs.lstatSync(file);fail('New ignored raw-response file required');}catch(e){if(e.code!=='ENOENT')throw e;}
  // Resolve the parent before Git admission so a symlink cannot redirect output
  // from an ignored path into a tracked file or another checkout.
  const resolved=path.join(fs.realpathSync(path.dirname(path.resolve(file))),path.basename(file));
  assertPrivate(path.resolve(file));assertPrivate(resolved);
  return {rawReadUrl};
}
