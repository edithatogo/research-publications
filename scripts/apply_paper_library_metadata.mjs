// SPDX-License-Identifier: Apache-2.0
// Injected, operation-qualified transport only. No CLI, SDK, authentication or network imports.
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';

const fail = message => { throw Error(message); };
const sha = value => crypto.createHash('sha256').update(value).digest('hex');
const canonical = value => JSON.stringify(value, (_key, v) => v && typeof v === 'object' && !Array.isArray(v)
  ? Object.fromEntries(Object.entries(v).sort(([a], [b]) => a.localeCompare(b))) : v);
const equal = (a, b) => canonical(a) === canonical(b);
const sameAccess = (a,b) => a?.Id===b?.Id && typeof a?.HasUniqueRoleAssignments==='boolean'
  && a.HasUniqueRoleAssignments===b?.HasUniqueRoleAssignments;
const text = value => typeof value === 'string' && value.length > 0 && value === value.trim();
const guid = value => typeof value === 'string' && /^[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$/i.test(value);
const positive = value => Number.isSafeInteger(value) && value > 0;
const etag = value => text(value) && value !== '*';
const itemTag = item => item['odata.etag'] ?? item['@odata.etag'];
const normal = (value, origin) => String(value ?? '').replace(/&#x([a-f0-9]+);/gi, (_, n) => String.fromCodePoint(parseInt(n, 16)))
  .replace(/&#([0-9]+);/g, (_, n) => String.fromCodePoint(Number(n)))
  .replace(/&(amp|lt|gt|quot|apos);/g, (_, n) => ({amp:'&',lt:'<',gt:'>',quot:'"',apos:"'"}[n]))
  .replace(/href="([^"]*)"/g, (whole, href) => {const u=new URL(href,origin+'/');return u.origin===origin?'href="'+u.href+'"':whole;})
  .replace(/<[^>]+>/g, tag => tag.replace(/\s+/g, ' '));

function pinned(file, digest) {
  if (!text(file) || !/^[a-f0-9]{64}$/.test(digest ?? '')) fail('Pinned source file/hash required');
  const fd = fs.openSync(file, fs.constants.O_RDONLY | fs.constants.O_NOFOLLOW);
  try {
    if (!fs.fstatSync(fd).isFile()) fail('Regular pinned evidence required');
    const bytes = fs.readFileSync(fd);
    if (sha(bytes) !== digest) fail('Pinned evidence changed');
    return JSON.parse(bytes);
  } finally { fs.closeSync(fd); }
}

function targetRoot(target) {
  const u = new URL(target.site_url);
  if (u.protocol !== 'https:' || !u.hostname.endsWith('.sharepoint.com') || u.username || u.password || u.search || u.hash
      || u.href !== target.site_url || u.pathname.endsWith('/') || !guid(target.library_id)) fail('Exact canonical SharePoint library required');
  return `${target.site_url}/_api/web/lists(guid'${target.library_id}')`;
}

function planItem(p) {
  if (!guid(p.file_id) || !positive(p.item_id) || !etag(p.etag) || !/^[a-f0-9]{64}$/.test(p.sha256 ?? '')
      || p.file_preimage?.UniqueId !== p.file_id || !etag(p.file_preimage.ETag)
      || !text(p.file_preimage.Name) || !text(p.file_preimage.UIVersionLabel)
      || !text(p.file_preimage.ServerRelativeUrl) || !p.file_preimage.ServerRelativeUrl.startsWith('/')) fail('Exact item/file preimage required');
  if (!p.before || !p.changes || Object.keys(p.before).sort().join() !== Object.keys(p.changes).sort().join()) fail('Complete exact field preimages required');
}

function context({target, plan, binding, session, journalRoot}, operation, items, reads) {
  binding = structuredClone(binding); // A caller cannot move both sides of a pin during a request.
  const root = targetRoot(target);
  const mutations = items.map(p => `${root}/items(${p.item_id})`);
  const guard = () => {
    // The owner supplies a synchronous, noninteractive assertion of the held
    // workload lock and operation qualification on every request. Flags alone
    // are not a session implementation and read-only authority is insufficient.
    const q = typeof session?.assertQualified === 'function' ? session.assertQualified() : null;
    if (!q || typeof session.request !== 'function' || q.operation !== operation || q.mutationQualified !== true
        || q.sharedLockHeld !== true || q.interactiveAuth !== false || q.retries !== 0 || q.maxRedirects !== 0
        || q.authType !== 'browser' || q.active !== true || q.resource !== new URL(target.site_url).origin
        || !binding?.resources?.includes(q.resource)) fail('Operation-qualified exclusive noninteractive zero-retry session required');
    for (const key of ['sdkRoot', 'sdkVersion', 'connectionName', 'appId', 'tenantId', 'username']) {
      if (!text(binding[key]) || !text(q[key]) || (['appId','tenantId','username'].includes(key)
        ? binding[key].toLowerCase() !== q[key].toLowerCase() : binding[key] !== q[key])) fail('Qualified workload/SDK identity drift');
    }
    if (binding.objectId && binding.objectId !== q.objectId) fail('Qualified object identity drift');
    if (binding.callbackOrigin && binding.callbackOrigin !== q.callbackOrigin) fail('Qualified callback drift');
    if (!Array.isArray(q.mutationTargets) || !equal([...q.mutationTargets].sort(), [...mutations].sort())) fail('Exact mutation targets not qualified');
  };
  guard(); // Before any service request or local journal admission.
  if (!text(journalRoot) || fs.realpathSync(journalRoot) !== path.resolve(journalRoot)) fail('Exclusive real journal root required');
  const scope = {operation,site:target.site_url,library:target.library_id,items:items.map(p=>({item:p.item_id,file:p.file_id})).sort((a,b)=>a.item-b.item)};
  const journalPath = path.join(journalRoot, `${operation}-${sha(canonical(scope))}.jsonl`);
  const lockPath = journalPath + '.lock';
  fs.mkdirSync(lockPath, {mode:0o700}); // Never wait for, remove or steal another owner.
  const owner = fs.lstatSync(lockPath);
  let fd;
  const close = () => {
    if (fd !== undefined) { fs.closeSync(fd); fd = undefined; }
    const current = fs.lstatSync(lockPath, {throwIfNoEntry:false});
    if (current?.dev === owner.dev && current?.ino === owner.ino && !current.isSymbolicLink()) fs.rmdirSync(lockPath);
  };
  try {
    fd = fs.openSync(journalPath, fs.constants.O_RDWR | fs.constants.O_APPEND | fs.constants.O_CREAT | fs.constants.O_NOFOLLOW, 0o600);
    const stat = fs.fstatSync(fd);
    if (!stat.isFile() || stat.nlink !== 1 || (stat.mode & 0o077)) fail('Private regular single-link journal required');
    const raw = fs.readFileSync(fd, 'utf8');
    if (raw && !raw.endsWith('\n')) fail('Incomplete journal; preserve and reconcile');
    const events = raw ? raw.trimEnd().split('\n').map(line=>JSON.parse(line)) : [];
    const header = {event:'scope',scope,plan_sha256:sha(canonical(plan)),binding_sha256:sha(canonical(binding))};
    const append = value => { fs.writeSync(fd, JSON.stringify(value)+'\n'); fs.fsyncSync(fd); events.push(value); };
    if (!events.length) {
      append(header);
      const directory = fs.openSync(journalRoot, fs.constants.O_RDONLY);
      try { fs.fsyncSync(directory); } finally { fs.closeSync(directory); }
    } else if (!equal(events[0], header)) fail('Journal source/plan/workload drift; reconcile original operation');
    const request = async (method, url, data, headers = {}) => {
      guard();
      if (method === 'GET' ? !reads.has(url) : method !== 'POST' || !mutations.includes(url)) fail('Unexpected transport target/method');
      return session.request({method,url,...(data === undefined ? {} : {data:structuredClone(data)}),headers:{accept:'application/json;odata=minimalmetadata',...headers},retries:0,maxRedirects:0,interactiveAuth:false});
    };
    return {journalPath,events,append,close,get:url=>request('GET',url),post:async(p,body)=>{
      if (events.some(e=>e.event==='intent' && e.item_id===p.item_id)) fail('UNCERTAIN_EFFECT_REQUIRES_READBACK; no mutation resend');
      append({event:'intent',item_id:p.item_id,etag:p.etag,body:structuredClone(body)});
      try { return await request('POST',`${root}/items(${p.item_id})`,body,{'IF-MATCH':p.etag,'X-HTTP-Method':'MERGE','content-type':'application/json;odata=nometadata'}); }
      catch (error) { append({event:'uncertain',item_id:p.item_id}); throw error; }
    }};
  } catch (error) { close(); throw error; }
}

function artifactUrls(site, p) {
  const base = `${site}/_api/web/GetFileById('${p.file_id}')`;
  return {base,file:base+'?$select=UniqueId,Name,ServerRelativeUrl,Length,ETag,CheckOutType,UIVersionLabel,MajorVersion,MinorVersion',item:base+'/ListItemAllFields?$select=*,OData__ExtendedDescription',access:base+'/ListItemAllFields?$select=Id,HasUniqueRoleAssignments',versions:base+'/Versions?$select=ID,VersionLabel,Created,IsCurrentVersion',bytes:base+'/$value'};
}
function versions(value) {
  if (!value || value['odata.nextLink'] || value['@odata.nextLink'] || !Array.isArray(value.value) || !value.value.length) fail('Complete version evidence required');
  const ids = new Set(), labels = new Set();
  for (const v of value.value) {
    if (!positive(v.ID) || !text(v.VersionLabel) || !text(v.Created) || ids.has(v.ID) || labels.has(v.VersionLabel)) fail('Unambiguous version history required');
    ids.add(v.ID); labels.add(v.VersionLabel);
  }
}
async function readArtifact(c, urls, p, pdf = false) {
  const result = {};
  for (const key of ['file','item','access','versions']) result[key] = await c.get(urls[key]);
  versions(result.versions);
  const bytes = await c.get(urls.bytes);
  if (!(bytes instanceof Uint8Array) || sha(bytes) !== p.sha256 || bytes.length !== Number(result.file.Length)
      || result.file.UniqueId !== p.file_id || result.item.Id !== p.item_id || result.access.Id !== p.item_id
      || typeof result.access.HasUniqueRoleAssignments !== 'boolean' || result.file.CheckOutType !== 2
      || result.file.ServerRelativeUrl !== p.file_preimage.ServerRelativeUrl || result.file.Length !== p.file_preimage.Length
      || result.file.Name !== p.file_preimage.Name
      || !etag(itemTag(result.item)) || !etag(result.file.ETag)
      || (pdf && !Buffer.from(bytes).subarray(0,5).equals(Buffer.from('%PDF-')))) fail('Content/identity/path/access/checkout drift');
  return result;
}
function compareHistory(before, after) {
  if (!before.value.every(old=>after.value.some(v=>v.ID===old.ID && v.VersionLabel===old.VersionLabel && v.Created===old.Created))) fail('Prior version history changed');
}
async function priorBytes(c, urls, history, p) {
  const label = p.file_preimage.UIVersionLabel;
  const v = history.value.find(v=>v.VersionLabel===label);
  if (!v) fail('Pinned source version missing');
  const url = `${urls.base}/Versions(${v.ID})/$value`;
  c.allowPrior(url); // Constructed only from complete exact file history.
  const bytes = await c.get(url);
  if (!(bytes instanceof Uint8Array) || sha(bytes) !== p.sha256) fail('Prior-version bytes differ');
}
function protectedFields(before, after, managed) {
  const ignored = new Set([...managed,'Modified','EditorId','EditorStringId','OData__UIVersionString','odata.etag','@odata.etag','odata.id']);
  for (const k of new Set([...Object.keys(before),...Object.keys(after)])) if (!ignored.has(k) && !equal(before[k],after[k])) fail('Unrelated human field changed');
}
function noChangeOrPreimage(c, p, current, properties, sameValue = equal) {
  const already = Object.entries(properties).every(([k,v])=>sameValue(current.item[k],v,k));
  if (already) return true;
  if (c.events.some(e=>e.event==='intent' && e.item_id===p.item_id)) fail('UNCERTAIN_EFFECT_REQUIRES_READBACK; no mutation resend');
  if (itemTag(current.item) !== p.etag || current.file.ETag !== p.file_preimage.ETag) fail('ETag drift; preserve human edits');
  for (const [key,value] of Object.entries(p.before)) if (!sameValue(current.item[key] ?? null,value ?? null,key)) fail('Human metadata drift');
  return false;
}
function reconcilePreimage(c, p, current, managed) {
  if (!c.events.some(e=>e.event==='intent' && e.item_id===p.item_id)) return;
  const original = c.events.find(e=>e.event==='preimage' && e.item_id===p.item_id);
  if (!original) fail('Intent has no durable preimage; reconcile');
  protectedFields(original.item,current.item,managed);
  if (!sameAccess(original.access,current.access)) fail('Journaled access shape changed');
  compareHistory(original.versions,current.versions);
}
function openContext(options, operation, items, reads) {
  const c = context(options,operation,items,reads);
  c.allowPrior = url => reads.add(url);
  return c;
}

export async function applyPaperLibraryMetadata(options) {
  const {target,session,binding,journalRoot} = options;
  const plan = structuredClone(options.plan);
  const root = targetRoot(target);planItem(plan);
  if (!guid(target.list_id) || !positive(plan.parent_id) || !text(target.folder) || !target.folder.startsWith('/')
      || plan.item_url !== `${root}/items(${plan.item_id})` || plan.content_writes !== false || plan.manifest_writes !== false
      || Object.keys(plan.changes).some(k=>!['Title','OData__ExtendedDescription'].includes(k))) fail('Exact paper two-field scope required');
  const snapshot = pinned(plan.snapshot_path,plan.snapshot_sha256);
  if (!equal(plan.file_preimage,snapshot.file) || snapshot.item?.Id !== plan.item_id || snapshot.parent?.Id !== plan.parent_id
      || snapshot.sha256 !== plan.sha256 || snapshot.manifest?.verified_file_unique_id !== plan.file_id
      || snapshot.manifest.file_url !== plan.file_url || snapshot.item_url !== plan.item_url) fail('Pinned paper plan/source identity drift');
  for (const [key,value] of Object.entries(plan.before)) if (!equal(value,snapshot.item[key] ?? null)) fail('Pinned field preimage differs');
  if (Object.hasOwn(plan.changes,'Title') && (snapshot.item.Title || !text(plan.changes.Title))) fail('Preserve existing human Title');
  if (Object.hasOwn(plan.changes,'OData__ExtendedDescription') && (typeof plan.changes.OData__ExtendedDescription !== 'string'
      || !plan.changes.OData__ExtendedDescription.startsWith(snapshot.item.OData__ExtendedDescription ?? ''))) fail('Preserve existing human Description');
  const urls = artifactUrls(target.site_url,plan);
  const parentUrl = `${target.site_url}/_api/web/lists(guid'${target.list_id}')/items(${plan.parent_id})?$select=Id,Title,field_2,field_11,OAArchiveState,OAArchiveURL,OAArchiveManifest`;
  const fieldsUrl = root+'/fields?$select=InternalName,TypeAsString,ReadOnlyField,RichText&$top=500';
  const reads = new Set([...Object.values(urls).filter(u=>u!==urls.base),parentUrl,fieldsUrl]);
  const c = openContext({target,plan,session,binding,journalRoot},'paper-library-metadata',[plan],reads);
  const same = (a,b,key) => key==='OData__ExtendedDescription' ? normal(a,new URL(target.site_url).origin)===normal(b,new URL(target.site_url).origin) : equal(a,b);
  try {
    const parent = await c.get(parentUrl), manifest = JSON.parse(parent.OAArchiveManifest);
    if (!equal(parent,snapshot.parent) || parent.OAArchiveState !== 'linked' || manifest.state !== 'linked'
        || manifest.verified_file_unique_id !== plan.file_id || manifest.sha256 !== plan.sha256 || manifest.file_url !== plan.file_url
        || parent.OAArchiveURL?.Url !== plan.file_url || manifest.CanonicalKey !== parent.field_2 || manifest.DOI !== parent.field_11
        || !manifest.folder.startsWith(`${target.folder}/paper-${plan.parent_id}-`) || plan.file_preimage.ServerRelativeUrl !== manifest.folder+'/paper.pdf') fail('Authoritative linked parent drift');
    const fields = await c.get(fieldsUrl);
    if (!Array.isArray(fields.value) || fields['odata.nextLink'] || fields['@odata.nextLink']) fail('Complete fields required');
    for (const [name,type] of [['Title','Text'],['_ExtendedDescription','Note']]) {
      const matches = fields.value.filter(f=>f.InternalName===name);
      if (matches.length!==1 || matches[0].TypeAsString!==type || matches[0].ReadOnlyField!==false || (type==='Note' && matches[0].RichText!==true)) fail('Exact existing paper field contract differs');
    }
    const before = await readArtifact(c,urls,plan,true);
    await priorBytes(c,urls,before.versions,plan);
    const already = noChangeOrPreimage(c,plan,before,plan.changes,same);
    if (already) {
      reconcilePreimage(c,plan,before,Object.keys(plan.changes));
      c.append({event:'reconciled',item_id:plan.item_id,writes:0});
      return {status:'UNCHANGED_INJECTED_TRANSPORT',writes:0,journalPath:c.journalPath,nativeAcceptance:false};
    }
    c.append({event:'preimage',item_id:plan.item_id,parent,...before});
    const immediate = await readArtifact(c,urls,plan,true);
    if (!equal(immediate,before) || !equal(await c.get(parentUrl),parent)) fail('Concurrent edit before effect');
    await c.post(plan,plan.changes);
    const after = await readArtifact(c,urls,plan,true);
    if (!Object.entries(plan.changes).every(([k,v])=>same(after.item[k],v,k)) || !equal(await c.get(parentUrl),parent)) fail('Saved metadata/parent differs; reconcile');
    protectedFields(before.item,after.item,Object.keys(plan.changes));compareHistory(before.versions,after.versions);
    if (!sameAccess(before.access,after.access)) fail('Access shape changed');
    await priorBytes(c,urls,after.versions,plan);
    c.append({event:'verified',item_id:plan.item_id,...after});
    return {status:'VERIFIED_INJECTED_TRANSPORT',writes:1,journalPath:c.journalPath,nativeAcceptance:false};
  } catch (error) { c.append({event:'stopped',requires_readback:c.events.some(e=>e.event==='intent')});throw error; }
  finally { c.close(); }
}

// Shared only by the two exact library operators; no native session implementation.
export const libraryMetadataInternals = {fail,sha,canonical,equal,sameAccess,text,guid,positive,etag,itemTag,pinned,targetRoot,planItem,artifactUrls,readArtifact,compareHistory,priorBytes,protectedFields,noChangeOrPreimage,reconcilePreimage,openContext};

if (process.argv[1] && pathToFileURL(path.resolve(process.argv[1])).href === import.meta.url) {
  console.error('NATIVE_ENTRY_DISABLED: metadata mutation session/transport is not qualified by the canonical read/renew wrapper. Inject an explicitly qualified exclusive session; no authentication was accessed.');
  process.exitCode = 1;
}
