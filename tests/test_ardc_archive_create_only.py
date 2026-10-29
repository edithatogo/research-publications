"""Offline one-send tests; the fake SDK never opens a network connection."""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/ardc_archive_create_only.mjs'


class CreateOnlyTests(unittest.TestCase):
    def test_persistent_journal_refuses_second_send(self):
        with tempfile.TemporaryDirectory(prefix='ardc-writer-test-', dir=ROOT / 'private/ops') as tmp:
            base = Path(tmp)
            sdk = base / 'sdk'
            (sdk / 'dist').mkdir(parents=True)
            (sdk / 'package.json').write_text(json.dumps({'name': '@pnp/cli-microsoft365', 'version': 'test', 'type': 'module'}))
            (sdk / 'dist/Auth.js').write_text('''
const auth={connection:{name:'test',appId:'app',tenant:'tenant',authType:'browser',active:true,identityId:'id'},
restoreAuth:async()=>{},getPublicClient:async()=>({getTokenCache:()=>({getAccountByLocalId:async()=>({username:'user',tenantId:'tenant'})})}),
ensureAccessTokenSilent:async()=>({}),ensureAccessToken:async()=> 'fake-token'};export default auth;
''')
            (sdk / 'dist/request.js').write_text('''
let intercept;const req={interceptors:{request:{use:f=>{intercept=f;}}},post:async(url,data,opts)=>{intercept({url,method:'post'});return {status:201,data:{}};}};
export default {req};
''')
            site = 'https://example.sharepoint.com/sites/Research'
            folder = '/Documents/Archive/Activities'
            journal = base / 'journal'
            journal.mkdir()
            credential = base / 'credential'
            credential.write_text('test-credential-value')
            binding = {'ardcActivitiesArchiveTarget': {'site': site, 'folder': folder}, 'resources': ['https://example.sharepoint.com'],
                       'sdkRoot': str(sdk), 'sdkVersion': 'test', 'connectionName': 'test', 'appId': 'app',
                       'tenantId': 'tenant', 'username': 'user', 'ardcActivitiesCredentialFile': str(credential),
                       'ardcActivitiesJournalRoot': str(journal)}
            binding_file = base / 'binding.json'
            binding_file.write_text(json.dumps(binding))
            data = b'{"status":"OK","code":200,"data":{"numFound":1,"offset":0,"records":[{"id":"10","key":"k"}]}}'
            name = 'activities-batch-000000000.json'
            (base / name).write_bytes(data)
            plan = {'format': 'rims-ardc-activities-upload-v1', 'site': site, 'folder': folder, 'name': name,
                    'local': name, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
                    'identities': [{'id': '10', 'key': 'k'}]}
            plan_file = base / 'plan.json'
            plan_file.write_text(json.dumps(plan))
            def invoke(evidence):
                return subprocess.run(['node', str(SCRIPT), str(binding_file), str(plan_file), name, str(base / evidence)],
                                      cwd=ROOT, capture_output=True, text=True)
            first = invoke('first')
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertTrue((base / 'first/submission.json').is_file())
            self.assertEqual(len(list(journal.iterdir())), 1)
            second = invoke('second')
            self.assertNotEqual(second.returncode, 0)
            self.assertFalse((base / 'second/submission.json').exists())
            self.assertEqual(len(list(journal.iterdir())), 1)
            leaked = b'{"status":"OK","code":200,"data":{"records":[]},"echo":"test-credential-value"}'
            (base / name).write_bytes(leaked)
            plan.update(bytes=len(leaked), sha256=hashlib.sha256(leaked).hexdigest())
            plan_file.write_text(json.dumps(plan))
            leaked_result = invoke('leaked')
            self.assertNotEqual(leaked_result.returncode, 0)
            self.assertFalse((base / 'leaked').exists())
            self.assertEqual(len(list(journal.iterdir())), 1)
