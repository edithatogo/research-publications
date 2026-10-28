// SPDX-License-Identifier: Apache-2.0
// Existing-column metadata only. Field creation and native CLI execution remain disabled.
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {libraryMetadataInternals as h} from './apply_paper_library_metadata.mjs';

// Native URL-field wrappers are transport metadata, not a changed link/label.
const sameValue = (actual, expected) => expected && typeof expected === 'object' && Object.hasOwn(expected,'Url')
  ? h.equal({Url:actual?.Url,Description:actual?.Description},expected) : h.equal(actual,expected);

export async function applyReportLibraryMetadata(options) {
  const {target,session,binding,journalRoot} = options;
  const plan = structuredClone(options.plan), root = h.targetRoot(target);
  if (plan.format!=='rims-report-library-metadata-v1' || plan.content_writes!==false || plan.manifest_writes!==false
      || !h.text(plan.generation_id) || !Array.isArray(plan.items) || !plan.items.length || !plan.fields) h.fail('Complete report metadata-only plan required');
  const evidence = h.pinned(plan.evidence_path,plan.evidence_sha256);
  if (!Array.isArray(evidence.artifacts) || evidence.artifacts.length!==plan.items.length) h.fail('Complete pinned artifact batch required');
  const known = new Map([['RIMSPeriod','Text'],['RIMSGeneration','Text'],['RIMSQueryVersion','Text'],['RIMSTemplateVersion','Text'],['RIMSRecordCount','Number'],['RIMSOutputRevision','Text'],['RIMSReconciliation','Text'],['RIMSArtifactRole','Text'],['RIMSGenerationManifest','URL'],['RIMSArtifactManifest','URL']]);
  for (const [key,field] of Object.entries(plan.fields)) if (!known.has(key) || !Array.isArray(field) || field.length!==2 || !h.text(field[0]) || field[1]!==known.get(key)) h.fail('Unexpected report column contract');
  const ids = new Set(), files = new Set();
  for (let i=0;i<plan.items.length;i++) {
    const p=plan.items[i], old=evidence.artifacts[i];h.planItem(p);
    if (ids.has(p.item_id) || files.has(p.file_id) || p.file_id!==old.file?.UniqueId || p.item_id!==old.item?.Id
        || p.sha256!==old.sha256 || p.sha256!==old.accepted_sha256 || !h.equal(p.file_preimage,old.file)
        || !p.properties || !Object.keys(p.properties).length || Object.keys(p.properties).some(k=>!Object.hasOwn(plan.fields,k))
        || Object.keys(p.changes).some(k=>!Object.hasOwn(p.properties,k) || !h.equal(p.changes[k],p.properties[k]))) h.fail('Plan outside pinned artifact/field scope');
    for (const [key,value] of Object.entries(p.properties)) {
      const type=known.get(key);
      if (type==='Text' ? !h.text(value) || Buffer.byteLength(value,'utf16le')>510 : type==='Number' ? !Number.isSafeInteger(value) || value<0
        : !value || Object.keys(value).sort().join()!=='Description,Url' || !h.text(value.Description)) h.fail('Invalid native property value');
      if (type==='URL') { const u=new URL(value.Url);if(u.protocol!=='https:'||u.username||u.password||u.search||u.hash||u.href!==value.Url)h.fail('Unsafe provenance link'); }
      const native=evidence.field_bindings?.[key] ?? key;
      if(!sameValue(old.item[native],value) && !Object.hasOwn(p.changes,key))h.fail('Missing intended metadata change');
      if (Object.hasOwn(p.changes,key)) {
        if ((old.item[native] ?? null)!==null && old.item[native]!=='') h.fail('Preserve conflicting existing report property');
        if (!h.equal(p.before[key],old.item[native] ?? null)) h.fail('Pinned metadata preimage differs');
      }
    }
    ids.add(p.item_id);files.add(p.file_id);
  }
  const fieldsUrl=root+'/fields?$select=Id,InternalName,StaticName,EntityPropertyName,TypeAsString,ReadOnlyField,Required,Hidden&$top=500';
  const urls=plan.items.map(p=>h.artifactUrls(target.site_url,p));
  const reads=new Set([fieldsUrl,...urls.flatMap(u=>Object.values(u).filter(v=>v!==u.base))]);
  const c=h.openContext({target,plan,session,binding,journalRoot},'report-library-metadata',plan.items,reads);
  try {
    const fields=await c.get(fieldsUrl), bindings={};
    if (!Array.isArray(fields.value)||fields['odata.nextLink']||fields['@odata.nextLink'])h.fail('Complete native fields required');
    for (const [name,[,type]] of Object.entries(plan.fields)) {
      const matches=fields.value.filter(f=>f.InternalName===name||f.StaticName===name);
      const f=matches[0];
      if(matches.length!==1||f.TypeAsString!==type||f.ReadOnlyField!==false||f.Required!==false||f.Hidden!==false)h.fail('Exact existing field contract differs');
      bindings[name]=f.EntityPropertyName||f.InternalName;
      if(bindings[name] !== (evidence.field_bindings?.[name]??name))h.fail('Pinned native binding drift');
    }
    if(new Set(Object.values(bindings)).size!==Object.keys(bindings).length)h.fail('Ambiguous native property aliases');
    const native=props=>Object.fromEntries(Object.entries(props).map(([k,v])=>[bindings[k],v]));
    const snapshots=[];
    // Entire selected batch must qualify before its first intended effect.
    for(let i=0;i<plan.items.length;i++) {
      const p=plan.items[i],s=await h.readArtifact(c,urls[i],p),old=evidence.artifacts[i];
      if(!h.sameAccess(s.access,old.access))h.fail('Access shape drift');
      if(old.versions)h.compareHistory(old.versions,s.versions);
      const nativePlan={...p,before:native(p.before)};
      await h.priorBytes(c,urls[i],s.versions,p);
      const already=h.noChangeOrPreimage(c,nativePlan,s,native(p.properties),sameValue);
      if(already)h.reconcilePreimage(c,p,s,Object.keys(native(p.changes)));
      snapshots.push({s,already});
    }
    let writes=0;
    for(let i=0;i<plan.items.length;i++) {
      const p=plan.items[i],{s,already}=snapshots[i];
      if(already){c.append({event:'reconciled',item_id:p.item_id,writes:0});continue;}
      c.append({event:'preimage',item_id:p.item_id,...s});
      const fresh=await h.readArtifact(c,urls[i],p);
      if(!h.equal(fresh,s))h.fail('Concurrent edit before effect');
      await c.post(p,native(p.changes));writes++;
      const after=await h.readArtifact(c,urls[i],p);
      if(!Object.entries(native(p.properties)).every(([k,v])=>sameValue(after.item[k],v)))h.fail('Saved metadata differs; reconcile');
      h.protectedFields(s.item,after.item,Object.keys(native(p.changes)));h.compareHistory(s.versions,after.versions);
      if(!h.sameAccess(s.access,after.access))h.fail('Access shape changed');
      await h.priorBytes(c,urls[i],after.versions,p);
      c.append({event:'verified',item_id:p.item_id,...after});
    }
    return {status:'VERIFIED_INJECTED_TRANSPORT',writes,journalPath:c.journalPath,nativeAcceptance:false};
  }catch(error){c.append({event:'stopped',requires_readback:c.events.some(e=>e.event==='intent')});throw error;}
  finally{c.close();}
}

if(process.argv[1]&&pathToFileURL(path.resolve(process.argv[1])).href===import.meta.url){
  console.error('NATIVE_ENTRY_DISABLED: existing-column metadata requires an injected operation-qualified session. Field creation, CLI/authentication and read-only authority promotion are unavailable.');
  process.exitCode=1;
}
