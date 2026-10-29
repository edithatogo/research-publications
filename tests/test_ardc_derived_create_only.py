"""Offline one-send tests; the fake SDK never opens a network connection."""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/ardc_derived_create_only.mjs'


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
            binding = {'ardcDerivedArchiveTarget': {'site': site, 'folder': folder}, 'resources': ['https://example.sharepoint.com'],
                       'sdkRoot': str(sdk), 'sdkVersion': 'test', 'connectionName': 'test', 'appId': 'app',
                       'tenantId': 'tenant', 'username': 'user', 'ardcActivitiesCredentialFile': str(credential),
                       'ardcDerivedJournalRoot': str(journal)}
            binding_file = base / 'binding.json'
            binding_file.write_text(json.dumps(binding))
            data = json.dumps({'format':'rims-ardc-rifcs-checkpoint-candidates-v1', 'candidates':[], 'source_files':[{'source':'page-0.xml','sha256':'a'*64,'records':0}], 'input_records':0,'alias_sha256':'b'*64, 'source_complete_verified':False, 'current_snapshot_verified':False, 'affiliation_confirmed':False, 'source_is_checkpoint_copy':True}).encode()
            name = 'candidates.json'
            (base / name).write_bytes(data)
            plan = {'format': 'rims-ardc-derived-upload-v1', 'site': site, 'folder': folder, 'name': name,
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
            # A processing receipt is a different immutable target, retaining
            # false delivery status until independent native readback exists.
            name = 'processing-receipt.json'
            receipt = {'format':'ardc-provisional-checkpoint-processing-v1',
                       'source_complete_verified':False,
                       'current_activities_snapshot_verified':False,
                       'sharepoint_delivery_verified':False,
                       'processed_pages':2, 'remaining_pages':3, 'manifest_pages':5,
                       'candidate_projection_sha256':'a'*64}
            def stage_receipt():
                raw = json.dumps(receipt).encode()
                (base / name).write_bytes(raw)
                plan.update(name=name, local=name, bytes=len(raw),
                            sha256=hashlib.sha256(raw).hexdigest())
                plan_file.write_text(json.dumps(plan))
            stage_receipt()
            valid = invoke('receipt-valid')
            self.assertEqual(valid.returncode, 0, valid.stderr)
            self.assertEqual(len(list(journal.iterdir())), 2)
            receipt['remaining_pages'] = 4
            stage_receipt()
            invalid = invoke('receipt-invalid')
            self.assertNotEqual(invalid.returncode, 0)
            self.assertFalse((base / 'receipt-invalid').exists())
            self.assertEqual(len(list(journal.iterdir())), 2)
            receipt.update(remaining_pages=3, sharepoint_delivery_verified=True)
            stage_receipt()
            claimed = invoke('receipt-false-completion')
            self.assertNotEqual(claimed.returncode, 0)
            self.assertFalse((base / 'receipt-false-completion').exists())
