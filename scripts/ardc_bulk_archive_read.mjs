// Apache-2.0. Prepared for invocation by the repository's guarded M365 entry point.
// This module alone does not establish authentication or authorize native reads.
import fs from 'node:fs';
import path from 'node:path';
import {createHash, randomUUID} from 'node:crypto';
import {execFileSync} from 'node:child_process';

const digest = bytes => createHash('sha256').update(bytes).digest('hex');
const fail = message => { throw Error(message); };

export function validateTarget(pin, markerBytes) {
  const t = pin?.ardcArchiveTarget;
  if (!t || !/^[a-f0-9]{64}$/.test(t.manifestSha256 ?? '') || digest(markerBytes) !== t.manifestSha256)
    fail('Accepted exact archive manifest hash required');
  let manifest;
  try { manifest = JSON.parse(markerBytes.toString('utf8')); } catch { fail('Invalid manifest JSON'); }
  if (manifest.source !== 'ardc' || manifest.format !== 'rims-ardc-public-registry-v1' || manifest.complete !== true
      || manifest.archive_folder !== t.folder || !Array.isArray(manifest.pages) || !manifest.pages.length)
    fail('Manifest does not match the pinned ARDC archive');
  const site = new URL(t.site);
  if (site.protocol !== 'https:' || site.username || site.password || site.search || site.hash
      || !/^\/personal\/[A-Za-z0-9_-]+$/.test(site.pathname)
      || !pin.resources?.includes(site.origin) || !t.folder.startsWith('/Documents/')
      || /['?#%\\]/.test(t.folder) || t.folder.split('/').some(s => s === '.' || s === '..'))
    fail('Unsafe or unpinned archive target');
  if (!(pin.readUrlPrefixes ?? []).some(prefix => {
    const u = new URL(prefix);
    return u.origin === site.origin && (u.pathname === site.pathname || u.pathname.startsWith(site.pathname + '/'));
  })) fail('Personal site is not in existing read pins');
  for (let i = 0; i < manifest.pages.length; i++) {
    const page = manifest.pages[i];
    if (page?.file !== `page-${i}.xml` || page.saved_content_equal !== true) fail('Invalid page inventory');
  }
  return {site: site.href.replace(/\/$/, ''), folder: t.folder, manifest};
}

export async function runGuarded({args, pin, auth, request}) {
  if (args.length !== 3) fail('Private binding, accepted marker and checkpoint required');
  const [bindingPath, markerPath, checkpointPath] = args.map(p => path.resolve(p));
  for (const p of [bindingPath, markerPath, checkpointPath]) execFileSync('git', ['check-ignore', '-q', p]);
  const marker = fs.readFileSync(markerPath);
  const target = validateTarget(pin, marker);
  const checkpoint = fs.realpathSync(checkpointPath);
  if (fs.lstatSync(checkpointPath).isSymbolicLink()) fail('Checkpoint must not be a symlink');
  const manifestAnchor = path.join(checkpoint, 'manifest-sha256.txt');
  const bindingAnchor = path.join(checkpoint, 'binding-sha256.txt');
  if (fs.lstatSync(manifestAnchor).isSymbolicLink() || fs.lstatSync(bindingAnchor).isSymbolicLink()
      || fs.readFileSync(manifestAnchor, 'utf8') !== digest(marker)
      || fs.readFileSync(bindingAnchor, 'utf8') !== digest(fs.readFileSync(bindingPath)))
    fail('Checkpoint manifest or binding differs');
  const lock = path.join(checkpoint, '.reader-lock');
  fs.mkdirSync(lock, {mode: 0o700});
  try {
    const token = await auth.ensureAccessToken(new URL(target.site).origin,
      {log: async () => {}, logToStderr: async () => {}}, false);
    if (typeof token !== 'string' || !token) fail('Missing qualified access token');
    let expectedUrl = '', sent = false;
    request.req.interceptors.request.use(config => {
      if (sent || config.method?.toLowerCase() !== 'get' || config.url !== expectedUrl || config.data !== undefined)
        fail('Out-of-scope or repeated archive request');
      sent = true; config.maxRedirects = 0; config.timeout = 30000;
      return config;
    });
    let created = 0, reused = 0;
    for (const page of target.manifest.pages) {
      const file = path.join(checkpoint, page.file), hashFile = file + '.sha256';
      if (fs.existsSync(file) || fs.existsSync(hashFile)) {
        if (!fs.existsSync(file) || !fs.existsSync(hashFile) || fs.lstatSync(file).isSymbolicLink()
            || fs.lstatSync(hashFile).isSymbolicLink() || digest(fs.readFileSync(file)) !== fs.readFileSync(hashFile, 'utf8'))
          fail('Incomplete or altered checkpoint page');
        reused++; continue;
      }
      const rel = new URL(target.site).pathname + target.folder + '/' + page.file;
      expectedUrl = target.site + "/_api/web/GetFileByServerRelativePath(DecodedUrl=@f)/$value?@f='" + encodeURIComponent(rel) + "'";
      sent = false;
      let response;
      try {
        response = await request.req({method: 'get', url: expectedUrl, headers: {Authorization: 'Bearer ' + token},
          responseType: 'arraybuffer', maxRedirects: 0, timeout: 30000, maxContentLength: 20000000});
      } catch (e) {
        const receipt = path.join(checkpoint, page.file + '.bulk-error-' + randomUUID() + '.json');
        fs.writeFileSync(receipt, JSON.stringify({status: e.response?.status ?? null, attempted: sent, retries: 0}) + '\n', {flag: 'wx', mode: 0o600});
        fail('Guarded archive read stopped; retain checkpoint and error receipt');
      }
      if (response.status !== 200 || !sent) fail('Unexpected archive read response');
      const raw = Buffer.from(response.data);
      if (raw.includes(Buffer.from(token))) fail('Response contains credential; page not retained');
      fs.writeFileSync(file, raw, {flag: 'wx', mode: 0o600});
      fs.writeFileSync(hashFile, digest(raw), {flag: 'wx', mode: 0o600});
      created++;
    }
    console.log(JSON.stringify({downloaded: created, reused, pageCount: target.manifest.pages.length,
      nativeWrites: 0, fullReconciliationPerformed: false}));
  } finally { fs.rmdirSync(lock); }
}
