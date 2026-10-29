// Apache-2.0. G06 candidate-only submission and durable uncertain-outcome guard.
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
const hash = s => createHash('sha256').update(s).digest('hex');
const fields = ['RelationshipKey','RelationshipType','FromKey','ToKey','AwardID','EvidenceURL','Confidence','ReviewStatus','Title'];
function equalIdentity(actual, desired) {
  return ['RelationshipKey','RelationshipType','FromKey','ToKey','AwardID'].every(k => actual[k] === desired[k]) && actual.EvidenceURL?.Url === desired.EvidenceURL.Url;
}
function save(file, value) {
  const fd = fs.openSync(file, 'wx', 0o600);
  try { fs.writeFileSync(fd, JSON.stringify(value, null, 2)+'\n'); fs.fsyncSync(fd); }
  finally { fs.closeSync(fd); }
  const dir = fs.openSync(path.dirname(file), 'r');
  try { fs.fsyncSync(dir); } finally { fs.closeSync(dir); }
}
export async function submitCandidate({listUrl, pinnedListUrl, row, journalRoot, readByKey, createOnce}) {
  if (listUrl !== pinnedListUrl || !/^https:\/\/[a-z0-9-]+\.sharepoint\.com\/[^?#]+\/_api\/web\/lists\(guid'[a-f0-9-]{36}'\)$/i.test(listUrl)) throw Error('Exact pinned list required');
  if (!row || Object.keys(row).some(k => !fields.includes(k)) || !/^REL:[a-f0-9]{24}$/.test(row.RelationshipKey) || row.RelationshipType !== 'candidate_award_match' || row.Confidence !== 'candidate' || row.ReviewStatus !== 'Needs Review' || !['FromKey','ToKey','AwardID'].every(k => typeof row[k] === 'string' && row[k] && row[k] === row[k].trim()) || typeof row.EvidenceURL?.Url !== 'string' || !row.EvidenceURL.Url.startsWith('https://')) throw Error('Explicit candidate identity and evidence required');
  if (fs.lstatSync(journalRoot).isSymbolicLink() || !fs.statSync(journalRoot).isDirectory()) throw Error('Existing private journal directory required');
  const prefix = path.join(journalRoot, hash(listUrl+'|'+row.RelationshipKey));
  const existing = await readByKey(row.RelationshipKey);
  if (!Array.isArray(existing) || existing.length > 1) throw Error('Complete unambiguous native key read required');
  if (existing.length) {
    if (!equalIdentity(existing[0],row)) throw Error('Existing candidate identity conflict');
    return {state:'preserved', item:existing[0], writes:0};
  }
  // Intent is stable across restarts and evidence directories. Absence after an
  // uncertain submission never permits a resend; reconciliation is required.
  save(prefix+'.intent.json', {listUrl,row,payloadSha256:hash(JSON.stringify(row)),at:new Date().toISOString()});
  let response;
  try { response = await createOnce(row); }
  catch (error) { save(prefix+'.uncertain.json', {at:new Date().toISOString(),message:'Submission failed or uncertain; reconcile exact key before any further action'}); throw error; }
  save(prefix+'.response.json', response);
  const saved = await readByKey(row.RelationshipKey);
  if (!Array.isArray(saved) || saved.length !== 1 || !equalIdentity(saved[0],row) || saved[0].Confidence !== row.Confidence || saved[0].ReviewStatus !== row.ReviewStatus || (row.Title !== undefined && saved[0].Title !== row.Title)) throw Error('Native saved candidate readback mismatch; reconcile before further action');
  save(prefix+'.saved.json',saved[0]);
  return {state:'created',item:saved[0],writes:1};
}
