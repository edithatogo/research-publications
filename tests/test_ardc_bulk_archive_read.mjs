import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import {runGuarded, validateTarget} from '../scripts/ardc_bulk_archive_read.mjs';

function fixture() {
  const site = 'https://example.sharepoint.com/personal/example';
  const folder = '/Documents/Archive/source-run';
  const marker = Buffer.from(JSON.stringify({source: 'ardc', format: 'rims-ardc-public-registry-v1',
    complete: true, archive_folder: folder, pages: [{file: 'page-0.xml', saved_content_equal: true}]}));
  const pin = {resources: ['https://example.sharepoint.com'],
    readUrlPrefixes: [site + '/_api/web'],
    ardcArchiveTarget: {site, folder, manifestSha256: createHash('sha256').update(marker).digest('hex')}};
  return {marker, pin};
}

test('accepts only a pinned manifest, personal site and exact page inventory', () => {
  const {marker, pin} = fixture();
  const result = validateTarget(pin, marker);
  assert.equal(result.manifest.pages.length, 1);
  assert.throws(() => validateTarget(pin, Buffer.from(marker.toString() + ' ')), /manifest hash/);
  assert.throws(() => validateTarget({...pin, ardcArchiveTarget: {...pin.ardcArchiveTarget, folder: '/Documents/Other'}}, marker), /pinned ARDC archive/);
  assert.throws(() => validateTarget({...pin, readUrlPrefixes: []}, marker), /read pins/);
});

test('rejects unsafe or out-of-sequence paths even with a matching marker hash', () => {
  const {pin} = fixture();
  const raw = Buffer.from(JSON.stringify({source: 'ardc', format: 'rims-ardc-public-registry-v1',
    complete: true, archive_folder: pin.ardcArchiveTarget.folder, pages: [{file: '../page-0.xml', saved_content_equal: true}]}));
  pin.ardcArchiveTarget.manifestSha256 = createHash('sha256').update(raw).digest('hex');
  assert.throws(() => validateTarget(pin, raw), /page inventory/);
});

test('guarded helper uses one GET per missing page and resumes without another request', async () => {
  const {marker, pin} = fixture();
  const root = fs.mkdtempSync(path.resolve('private/ops/ardc-bulk-test-'));
  try {
    const binding = path.join(root, 'binding.json'), source = path.join(root, 'marker.json'), checkpoint = path.join(root, 'checkpoint');
    fs.mkdirSync(checkpoint);
    fs.writeFileSync(binding, '{}'); fs.writeFileSync(source, marker);
    fs.writeFileSync(path.join(checkpoint, 'manifest-sha256.txt'), createHash('sha256').update(marker).digest('hex'));
    fs.writeFileSync(path.join(checkpoint, 'binding-sha256.txt'), createHash('sha256').update('{}').digest('hex'));
    let calls = 0;
    const makeRequest = () => {
      let guard;
      const req = async config => {
        calls++;
        assert.equal(config.headers.Authorization, 'Bearer test-token-very-long');
        guard(config);
        return {status: 200, data: Buffer.from('synthetic page')};
      };
      req.interceptors = {request: {use: fn => { guard = fn; }}};
      return {req};
    };
    const auth = {ensureAccessToken: async () => 'test-token-very-long'};
    await runGuarded({args: [binding, source, checkpoint], pin, auth, request: makeRequest()});
    assert.equal(calls, 1);
    assert.equal(fs.readFileSync(path.join(checkpoint, 'page-0.xml'), 'utf8'), 'synthetic page');
    await runGuarded({args: [binding, source, checkpoint], pin, auth, request: makeRequest()});
    assert.equal(calls, 1);
    assert.equal(fs.existsSync(path.join(checkpoint, '.reader-lock')), false);
  } finally { fs.rmSync(root, {recursive: true, force: true}); }
});

test('denied request is sent once, recorded and leaves no accepted page', async () => {
  const {marker, pin} = fixture();
  const root = fs.mkdtempSync(path.resolve('private/ops/ardc-bulk-test-'));
  try {
    const binding = path.join(root, 'binding.json'), source = path.join(root, 'marker.json'), checkpoint = path.join(root, 'checkpoint');
    fs.mkdirSync(checkpoint); fs.writeFileSync(binding, '{}'); fs.writeFileSync(source, marker);
    fs.writeFileSync(path.join(checkpoint, 'manifest-sha256.txt'), createHash('sha256').update(marker).digest('hex'));
    fs.writeFileSync(path.join(checkpoint, 'binding-sha256.txt'), createHash('sha256').update('{}').digest('hex'));
    let calls = 0, guard;
    const req = async config => { calls++; guard(config); throw {response: {status: 403}}; };
    req.interceptors = {request: {use: fn => { guard = fn; }}};
    await assert.rejects(runGuarded({args: [binding, source, checkpoint], pin,
      auth: {ensureAccessToken: async () => 'synthetic'}, request: {req}}), /stopped/);
    assert.equal(calls, 1);
    assert.equal(fs.existsSync(path.join(checkpoint, 'page-0.xml')), false);
    assert.equal(fs.readdirSync(checkpoint).filter(n => n.includes('.bulk-error-')).length, 1);
  } finally { fs.rmSync(root, {recursive: true, force: true}); }
});

test('checkpoint anchors cannot be symlinks', async () => {
  const {marker, pin} = fixture();
  const root = fs.mkdtempSync(path.resolve('private/ops/ardc-bulk-test-'));
  try {
    const binding = path.join(root, 'binding.json'), source = path.join(root, 'marker.json'), checkpoint = path.join(root, 'checkpoint');
    fs.mkdirSync(checkpoint); fs.writeFileSync(binding, '{}'); fs.writeFileSync(source, marker);
    const target = path.join(root, 'target.txt');
    fs.writeFileSync(target, createHash('sha256').update(marker).digest('hex'));
    fs.symlinkSync(target, path.join(checkpoint, 'manifest-sha256.txt'));
    fs.writeFileSync(path.join(checkpoint, 'binding-sha256.txt'), createHash('sha256').update('{}').digest('hex'));
    let called = false;
    await assert.rejects(runGuarded({args: [binding, source, checkpoint], pin,
      auth: {ensureAccessToken: async () => { called = true; return 'synthetic'; }}, request: {}}), /Checkpoint/);
    assert.equal(called, false);
  } finally { fs.rmSync(root, {recursive: true, force: true}); }
});
