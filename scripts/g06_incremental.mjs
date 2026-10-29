// Apache-2.0. Incremental delivery of accepted G06 ARC candidate packets.
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {execFileSync,spawnSync} from 'node:child_process';
import {pathToFileURL} from 'node:url';
export const sha=x=>createHash('sha256').update(x).digest('hex');
const digest=x=>sha(JSON.stringify(x));
const hex=x=>typeof x==='string'&&/^[a-f0-9]{64}$/.test(x);
export function validatePacket(p){
 if(p?.kind!=='retained_arc_publication_relationship_candidates_v1'||!Array.isArray(p.relationships)||!Array.isArray(p.context)||!Array.isArray(p.unresolved)||p.coverage?.exact_candidates!==p.relationships.length||!p.input_hashes||!['registry','publications','awards'].every(k=>hex(p.input_hashes[k])))throw Error('Qualified retained ARC candidate packet required');
 const keys=new Set();
 for(const r of p.relationships){
  if(Object.keys(r).sort().join(',')!==['RelationshipKey','RelationshipType','FromKey','ToKey','AwardID','EvidenceURL','Confidence','ReviewStatus'].sort().join(','))throw Error('Exact typed candidate fields required');
  if(r.RelationshipType!=='candidate_award_match'||r.Confidence!=='candidate'||r.ReviewStatus!=='Needs Review'||!/^AWARD:arc:[^\s]+$/.test(r.FromKey)||!/^PUB:[^\s]+$/.test(r.ToKey)||typeof r.AwardID!=='string'||!r.AwardID||r.AwardID!==r.AwardID.trim()||!/^https:\/\/pubmed\.ncbi\.nlm\.nih\.gov\/[1-9][0-9]*\/$/.test(r.EvidenceURL))throw Error('Candidate source identity/admission mismatch');
  if(r.RelationshipKey!=='REL:'+sha(JSON.stringify([r.RelationshipType,r.FromKey,r.ToKey,r.AwardID,r.EvidenceURL])).slice(0,24)||keys.has(r.RelationshipKey))throw Error('Duplicate or forged relationship key');keys.add(r.RelationshipKey);
  const matches=p.context.filter(c=>c.RelationshipKey===r.RelationshipKey);
  if(matches.length!==1||Object.keys(r).some(k=>matches[0][k]!==r[k])||!['RegistryRowSHA256','AwardRowSHA256','CanonicalRowSHA256'].every(k=>hex(matches[0][k])))throw Error('Exact context and row provenance required');
  const c=matches[0],pmid=r.EvidenceURL.split('/')[3],award=r.FromKey.slice('AWARD:arc:'.length);
  if(c.RegistryPublicationKey!==r.ToKey||c.PublicationSourceKey!=='pubmed:'+pmid||c.PublicationURL!==r.EvidenceURL||c.AwardSourceID!==award||c.AwardCode!==r.AwardID||c.AwardURL!=='https://dataportal.arc.gov.au/NCGP/API/grants/'+award||!Number.isSafeInteger(c.RegistryItemID)||c.RegistryItemID<1||typeof c.PublicationCanonicalKey!=='string'||!c.PublicationCanonicalKey||c.PublicationCanonicalKey!==c.PublicationCanonicalKey.trim())throw Error('Source context crosswalk does not match relationship identity');
 }
 if(p.context.length!==p.relationships.length)throw Error('Unexpected context coverage');
 return p;
}
export function prepareIncremental(inputs,previous=null,ruleHash){
 if(!hex(ruleHash)||!Array.isArray(inputs)||!inputs.length)throw Error('Explicit inputs and rule hash required');
 if(previous&&(previous.kind!=='g06-incremental-delivered-v1'||previous.native_verified!==true||!previous.state?.sources))throw Error('Only a native-verified prior receipt can advance state');
 const sources={},combined=new Map(),changed=[],reused=[],removed=[],contextChanged=[];
 for(const input of inputs){
  if(typeof input.id!=='string'||!input.id||sources[input.id]||!Buffer.isBuffer(input.raw)||sha(input.raw)!==input.sha256)throw Error('Distinct hash-bound source inputs required');
  const old=previous?.state.sources[input.id];let p;
  if(old?.sha256===input.sha256&&previous.state.rule_sha256===ruleHash){p=old.packet;reused.push(input.id);}
  else{p=validatePacket(JSON.parse(input.raw));changed.push(input.id);}
  sources[input.id]={sha256:input.sha256,packet:p};
  for(const r of p.relationships){const c=p.context.find(c=>c.RelationshipKey===r.RelationshipKey);const prior=old?.packet.context.find(x=>x.RelationshipKey===r.RelationshipKey);if(prior&&digest(c)!==digest(prior))contextChanged.push(r.RelationshipKey);
   if(combined.has(r.RelationshipKey)&&digest(combined.get(r.RelationshipKey).row)!==digest(r))throw Error('Conflicting source assertions');
   const entry=combined.get(r.RelationshipKey)??{row:r,provenance:[]};entry.provenance.push({source:input.id,packet_sha256:input.sha256,context:c});combined.set(r.RelationshipKey,entry);
  }
  for(const r of old?.packet.relationships??[])if(!p.relationships.some(x=>x.RelationshipKey===r.RelationshipKey))removed.push(r.RelationshipKey);
 }
 for(const [id,old] of Object.entries(previous?.state.sources??{}))if(!sources[id])removed.push(...old.packet.relationships.map(r=>r.RelationshipKey));
 return {kind:'g06-incremental-prepared-v1',state:{rule_sha256:ruleHash,sources},relationships:[...combined.values()].map(x=>x.row),provenance:[...combined.values()].map(x=>({key:x.row.RelationshipKey,sources:x.provenance})),coverage:{changed_sources:changed,reused_sources:reused,absent_prior_sources:Object.keys(previous?.state.sources??{}).filter(k=>!sources[k]),removed_source_keys:[...new Set(removed)].sort(),changed_context_keys:[...new Set(contextChanged)].sort(),candidate_keys:combined.size,confirmed_funding:0,source_complete_claim:false},native_verified:false};
}
function save(p,x){const fd=fs.openSync(p,'wx',0o600);try{fs.writeFileSync(fd,JSON.stringify(x,null,2)+'\n');fs.fsyncSync(fd);}finally{fs.closeSync(fd);}const d=fs.openSync(path.dirname(p),'r');try{fs.fsyncSync(d);}finally{fs.closeSync(d);}}
export function verifyPythonRuntime(run=spawnSync){
 const python=new URL('../.venv/bin/python',import.meta.url).pathname;
 const result=run(python,['-c','import sys; print(".".join(map(str, sys.version_info[:3])))'],{encoding:'utf8',timeout:10000});
 if(result.status!==0||result.stdout?.trim()!=='3.15.1')throw Error('Repo-local Python 3.15.1 must be verified before native delivery');
 return python;
}
export function readRimsBaseline(reference){
 if(!reference)return null;
 if(typeof reference.path!=='string'||!hex(reference.sha256))throw Error('Hash-bound RIMS baseline required');
 const raw=fs.readFileSync(reference.path);if(sha(raw)!==reference.sha256)throw Error('RIMS baseline drift');
 const baseline=JSON.parse(raw);if(baseline.kind!=='current_native_funding_relationship_consumer_v1'||!Array.isArray(baseline.identity_material))throw Error('Accepted RIMS consumer baseline required');
 return raw;
}
export function main(argv){
 const [binding,jobPath,directory]=argv;if(!directory)throw Error('Private binding, job and exclusive result directory required');
 const owner=path.resolve(path.dirname(fs.realpathSync(binding)),'../../..');
 const ignored=p=>execFileSync('git',['check-ignore','-q',path.resolve(p)],{cwd:owner});
 [binding,jobPath,directory].forEach(ignored);const job=JSON.parse(fs.readFileSync(jobPath));
 if(job.kind!=='g06-incremental-job-v1'||!Array.isArray(job.sources))throw Error('Explicit incremental job required');
 const python=verifyPythonRuntime();
 if(job.rims_baseline)ignored(job.rims_baseline.path);
 const baseline=readRimsBaseline(job.rims_baseline);
 let previous=null;if(job.previous){ignored(job.previous.path);const bytes=fs.readFileSync(job.previous.path);if(sha(bytes)!==job.previous.sha256)throw Error('Prior receipt drift');previous=JSON.parse(bytes);}
 const inputs=job.sources.map(s=>{ignored(s.path);return {...s,raw:fs.readFileSync(s.path)};});
 const rule=digest(['g06_incremental.mjs','g06_candidate_writer.mjs','g06_native_qualification.mjs','connect_g06_rims.py','prepare_funding_relationship_context.py'].map(n=>[n,sha(fs.readFileSync(new URL(n,import.meta.url)))]));
 const prepared=prepareIncremental(inputs,previous,rule);
 ignored(job.scope);const scope=JSON.parse(fs.readFileSync(job.scope));
 if(!scope.list_url||!scope.journal_root)throw Error('Existing qualified list and persistent journal scope required');
 fs.mkdirSync(directory,{mode:0o700});save(path.join(directory,'prepared.json'),prepared);
 let baselinePath;
 if(baseline){baselinePath=path.resolve(directory,'rims-baseline.json');save(baselinePath,JSON.parse(baseline));}
 const scopePath=path.resolve(directory,'incremental-scope.json');save(scopePath,{...scope,incremental_packet:path.resolve(directory,'prepared.json'),incremental_sha256:sha(fs.readFileSync(path.join(directory,'prepared.json')))});
 const native=path.resolve(directory,'native');const result=spawnSync(process.execPath,[new URL('g06_native_qualification.mjs',import.meta.url).pathname,binding,scopePath,native,'apply'],{stdio:'inherit'});
 if(result.status!==0){save(path.join(directory,'delivery-failure.json'),{native_exit:result.status,checkpoint_advanced:false,previous_receipt_sha256:job.previous?.sha256??null,message:'Native delivery incomplete; inspect native evidence and persistent journal before another submission'});throw Error('Native delivery incomplete; preserve journal and reconcile before another submission');}
 const acceptance=JSON.parse(fs.readFileSync(path.join(native,'incremental-acceptance.json')));
 if(acceptance.native_verified!==true)throw Error('No native acceptance; checkpoint not advanced');
 const receipt={...prepared,kind:'g06-incremental-delivered-v1',native_verified:true,native:acceptance,previous_receipt_sha256:job.previous?.sha256??null,created_utc:new Date().toISOString()};
 const deliveryPath=path.resolve(directory,'native-delivery.json');save(deliveryPath,{...receipt,kind:'g06-native-delivery-verified-v1'});
 const consumerPath=path.resolve(directory,'rims-consumer.json');
 const consumerArgs=[new URL('connect_g06_rims.py',import.meta.url).pathname,'--processing-receipt',deliveryPath,'--output',consumerPath];
 if(baselinePath)consumerArgs.push('--baseline-consumer',baselinePath);
 const consumer=spawnSync(python,consumerArgs,{cwd:owner,stdio:'inherit'});
 if(consumer.status!==0){save(path.join(directory,'consumer-failure.json'),{consumer_exit:consumer.status,native_verified:true,checkpoint_advanced:false,native_delivery_sha256:sha(fs.readFileSync(deliveryPath))});throw Error('RIMS consumer preparation failed; native acceptance retained, processing checkpoint not advanced');}
 receipt.rims_consumer={path:consumerPath,sha256:sha(fs.readFileSync(consumerPath)),native_model_modified:false};
 save(path.join(directory,'receipt.json'),receipt);console.log(JSON.stringify({coverage:receipt.coverage,created:acceptance.created,preserved:acceptance.preserved,native_verified:true}));return receipt;
}
if(process.argv[1]&&import.meta.url===pathToFileURL(path.resolve(process.argv[1])).href)main(process.argv.slice(2));
