# SPDX-License-Identifier: Apache-2.0
"""Synthetic complete captures only; no tenant data or private fixture gates."""
import copy
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from scripts import verify_publication_protected_fields as module
from scripts.publication_batch_contract import PROTECTED_MANUAL_FIELDS

NOW=datetime(2026,10,29,0,0,tzinfo=timezone.utc)
TARGET={'site_url':'https://example.sharepoint.com/sites/fictional','list_id':'10000000-0000-0000-0000-000000000001'}


def snapshot(rows, key='value', *, minutes=0):
    return {'complete':True,'item_count':len(rows),'history_complete':True,
            'observed_at_utc':(NOW-timedelta(minutes=minutes)).isoformat(),
            'capture_reference':'fixture:complete-snapshot','target':copy.deepcopy(TARGET),key:copy.deepcopy(rows)}


def versioned(row):
    return {**row,'version':'1.0','etag':'"1"','versions':[{'version':'1.0','etag':'"1"','capture_reference':'fixture:version-1'}]}


def advance(row):
    row['version']='2.0';row['etag']='"2"'
    row['versions'].append({'version':'2.0','etag':'"2"','capture_reference':'fixture:version-2'})


def native_row(number=1, key='PUB:abcd'):
    values={'FirstObservedUTC':'unknown locale source stamp','ReviewStatus':'Needs Review','ReviewNotes':'Keep human edit',
            'Title':'FICTIONAL source title','Authors':'A; B','Journal':'Fixture','PublicationYear':None,
            'PublicationMonth':None,'SourceKey':f'qualification:{number}','CanonicalKey':key}
    return versioned({'Id':f'20000000-0000-0000-0000-{number:012d}','ID':number,
                      **{module.FIELD_MAP[k]:v for k,v in values.items()}})


class ProtectedFieldsTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory();self.addCleanup(self.directory.cleanup)
        self.base=Path(self.directory.name).resolve();self.before=snapshot([native_row()],minutes=1)
        self.after=copy.deepcopy(self.before);self.after['observed_at_utc']=NOW.isoformat()
        new=native_row(2,'PUB:ef');new['field_1']='pubmed:123';new['field_17']='Included'
        self.after['value'].append(new);self.after['item_count']=2

    def compare(self,**changes):
        before=self.base/'before.json';after=self.base/'after.json'
        before.write_text(json.dumps(self.before));after.write_text(json.dumps(self.after))
        return module.compare(before,after,['pubmed:123'],'Included',now=NOW,expected_canonical_keys={'pubmed:123':'PUB:ef'},**changes)

    def test_complete_intake_preserves_every_policy_field_versions_and_unknown_dates(self):
        original=copy.deepcopy((self.before,self.after));r=self.compare()
        self.assertEqual(r['status'],'verified');self.assertEqual(r['protected_fields_checked'],sorted(PROTECTED_MANUAL_FIELDS))
        self.assertEqual(r['preserved_prior_item_count'],1);self.assertEqual(r['new_item_count'],1)
        self.assertFalse(r['native_acceptance']);self.assertFalse(r['write_authorized'])
        self.assertEqual((self.before,self.after),original)
        self.assertEqual(r['after_export_sha256'],hashlib.sha256((self.base/'after.json').read_bytes()).hexdigest())

    def test_changed_human_fields_or_typed_values_fail_without_echoing_raw_values(self):
        for logical in PROTECTED_MANUAL_FIELDS:
            old=copy.deepcopy(self.after)
            self.after['value'][0][module.FIELD_MAP[logical]]='PRIVATE FICTIONAL CHANGE'
            with self.subTest(field=logical),self.assertRaisesRegex(ValueError,'protected') as caught:self.compare()
            self.assertNotIn('PRIVATE FICTIONAL CHANGE',str(caught.exception));self.after=old
        self.after['value'][0]['field_5']=False
        with self.assertRaises(ValueError):self.compare()

    def test_duplicate_missing_padded_or_coerced_item_identity_rejected(self):
        for change in ['duplicate','missing','boolean','padded-guid','reassigned-integer']:
            old=copy.deepcopy(self.after)
            if change=='duplicate':self.after['value'][1]['Id']=self.after['value'][0]['Id']
            elif change=='missing':self.after['value'].pop(0);self.after['item_count']=1
            elif change=='boolean':self.after['value'][0]['ID']=True
            elif change=='padded-guid':self.after['value'][0]['Id']=' '+self.after['value'][0]['Id']
            else:self.after['value'][0]['ID']=7
            with self.subTest(change=change),self.assertRaises(ValueError):self.compare()
            self.after=old

    def test_every_selected_field_and_complete_version_history_are_required(self):
        for field in list(module.FIELD_MAP.values())+['version','etag','versions']:
            old=copy.deepcopy(self.after);self.after['value'][0].pop(field)
            with self.subTest(field=field),self.assertRaises(ValueError):self.compare()
            self.after=old
        self.after['value'][0]['versions'][0]['capture_reference']='changed old evidence'
        with self.assertRaisesRegex(ValueError,'history'):self.compare()

    def test_incomplete_stale_future_wrong_scope_or_wrong_count_is_not_accepted(self):
        changes=[{'complete':False},{'history_complete':False},{'item_count':True},{'item_count':99},
                 {'error':{}},{'partial':[]},{'odata.nextLink':'next'},
                 {'observed_at_utc':(NOW-timedelta(minutes=16)).isoformat()},
                 {'observed_at_utc':(NOW+timedelta(seconds=1)).isoformat()},
                 {'observed_at_utc':'2026-10-29T00:00:00'},
                 {'target':{**TARGET,'list_id':'30000000-0000-0000-0000-000000000003'}}]
        for change in changes:
            old=copy.deepcopy(self.after);self.after.update(change)
            with self.subTest(change=change),self.assertRaises(ValueError):self.compare()
            self.after=old

    def test_expected_keys_and_new_review_status_are_exact(self):
        for key in ['pubmed:0','pubmed:01','pubmed:١',' pubmed:123']:
            (self.base/'a').write_text(json.dumps(self.before));(self.base/'b').write_text(json.dumps(self.after))
            with self.subTest(key=key),self.assertRaises(ValueError):module.compare(self.base/'a',self.base/'b',[key],'Included',now=NOW)
        self.after['value'][1]['field_17']='Needs Review'
        with self.assertRaises(ValueError):self.compare()

    def test_cli_output_is_exclusive_and_failures_preserve_preexisting_files(self):
        from contextlib import redirect_stderr
        import io
        root=self.base/'repo';private=root/'private';private.mkdir(parents=True)
        paths=[private/n for n in ['before.json','after.json','keys.json','report.json']]
        canonical=private/'canonical.json';canonical.write_text(json.dumps({'pubmed:123':'PUB:ef'}))
        for p,v in zip(paths,[self.before,self.after,['pubmed:123']]):p.write_text(json.dumps(v))
        args=['--before',str(paths[0]),'--after',str(paths[1]),'--expected-keys',str(paths[2]),'--new-review-status','Included','--expected-canonical-keys',str(canonical),'--output',str(paths[3]),'--as-of',NOW.isoformat()]
        with mock.patch.object(module,'ROOT',root),redirect_stderr(io.StringIO()):
            self.assertEqual(module.main(args),0);saved=paths[3].read_bytes()
            self.assertNotEqual(module.main(args),0);self.assertEqual(paths[3].read_bytes(),saved)
            paths[3].unlink();paths[1].write_text('{')
            self.assertNotEqual(module.main(args),0);self.assertFalse(paths[3].exists())
            paths[3].symlink_to(paths[0]);original=paths[0].read_bytes()
            self.assertNotEqual(module.main(args),0);self.assertEqual(paths[0].read_bytes(),original)

    def test_portable_direct_cli_imports_without_site_packages(self):
        script=Path(module.__file__).resolve()
        run=subprocess.run([sys.executable,'-S','-B',str(script),'--help'],cwd=self.base,capture_output=True,text=True)
        self.assertEqual(run.returncode,0,run.stderr)

    def test_export_hashes_bind_the_single_read_used_for_comparison(self):
        reads={};original=Path.read_bytes
        def read(path):
            reads[path]=reads.get(path,0)+1
            return original(path)
        with mock.patch.object(Path,'read_bytes',read):self.compare()
        self.assertEqual(reads[self.base/'before.json'],1)
        self.assertEqual(reads[self.base/'after.json'],1)

    def test_duplicate_json_names_and_failed_serialization_never_create_output(self):
        path=self.base/'duplicate.json';path.write_text('{"complete":true,"complete":false}')
        with self.assertRaises(ValueError):module.read_json(path)
        output=self.base/'report.json'
        with self.assertRaises(ValueError):module.exclusive_json(output,{'bad':float('nan')})
        self.assertFalse(output.exists())

    def test_canonical_identity_must_match_independent_supplied_map(self):
        a=self.base/'a';b=self.base/'b'
        a.write_text(json.dumps(self.before));b.write_text(json.dumps(self.after))
        with self.assertRaisesRegex(ValueError,'canonical'):
            module.compare(a,b,['pubmed:123'],'Included',now=NOW)
        self.after['value'][1]['field_2']='pubmed:123'
        with self.assertRaisesRegex(ValueError,'canonical'):self.compare()
