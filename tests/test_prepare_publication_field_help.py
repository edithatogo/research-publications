# SPDX-License-Identifier: Apache-2.0
import copy
import unittest
from scripts import prepare_publication_field_help as help
from scripts.prepare_publication_registry_bootstrap import sha
from tests.test_prepare_publication_registry_bootstrap import metadata_snapshot,meanings,changed_field

def qualification(s,m):return dict(field_semantics_confirmed=True,profile_sha256=sha(m),preimage_sha256=sha(s),reference='fixture:field-policy',writer_semantics_reference='fixture:writer-policy')

class FieldHelpTests(unittest.TestCase):
    def test_fourteen_bounded_descriptions_only_and_complete_reconciliation(self):
        s=metadata_snapshot();original=copy.deepcopy(s);m=meanings();p=help.prepare(s,m,qualification=qualification(s,m))
        self.assertEqual(len(p['changes']),14);self.assertEqual(s,original)
        after=copy.deepcopy(s)
        for c in p['changes']:
            i=next(i for i,f in enumerate(after['fields']) if f['Id']==c['id'])
            after['fields'][i]=changed_field(after['fields'][i],**c['desired'])
        result=help.reconcile(s,p,after,expected_plan_sha256=p['plan_sha256'])
        self.assertEqual(result['status'],'verified_supplied_readback');self.assertFalse(result['native_acceptance'])
        self.assertEqual(help.prepare(after,m,qualification=qualification(after,m))['changes'],[])

    def test_wrong_type_missing_note_capacity_changed_plan_or_human_data_fail(self):
        for fault in ['type','note','plan','row','etag']:
            s=metadata_snapshot();m=meanings()
            if fault=='type':m['fields'][0]['type']='Choice'
            elif fault=='note':next(f for f in s['fields'] if f['InternalName']=='field_3').pop('RichText')
            if fault in ['type','note']:
                with self.assertRaises(ValueError):help.prepare(s,m,qualification=qualification(s,m))
                continue
            p=help.prepare(s,m,qualification=qualification(s,m));after=copy.deepcopy(s)
            if fault=='plan':p['changes'][0]['desired']['Description']='forged'
            elif fault=='row':after['items'][0]['field_18']='overwrite'
            else:after['items'][0]['__metadata']['etag']='"2"'
            with self.subTest(fault=fault),self.assertRaises(ValueError):help.reconcile(s,p,after,expected_plan_sha256=p['plan_sha256'])

    def test_duplicate_names_unknown_fields_and_unicode_capacity_are_rejected(self):
        for changes in ['duplicate','missing','length']:
            m=meanings()
            if changes=='duplicate':m['fields'].append(copy.deepcopy(m['fields'][0]))
            elif changes=='missing':m['fields'][0]['name']='missing'
            else:m['fields'][0]['description']='😀'*128
            with self.subTest(changes=changes),self.assertRaises(ValueError):help.prepare(metadata_snapshot(),m,qualification=qualification(metadata_snapshot(),m))

    def test_config_is_not_policy_qualification_or_timestamp_writer_proof(self):
        s=metadata_snapshot();m=meanings()
        for fault in ('missing','flag','profile','snapshot','reference','writer'):
            q=qualification(s,m)
            if fault=='missing':q=None
            elif fault=='flag':q['field_semantics_confirmed']='true'
            elif fault=='profile':q['profile_sha256']='a'*64
            elif fault=='snapshot':q['preimage_sha256']='a'*64
            elif fault=='reference':q['reference']=''
            else:q['writer_semantics_reference']=''
            with self.subTest(fault=fault),self.assertRaises(ValueError):help.prepare(s,m,qualification=q)

    def test_rehashed_plan_with_pinned_hash_still_cannot_change_selected_scope(self):
        s=metadata_snapshot();m=meanings();p=help.prepare(s,m,qualification=qualification(s,m));p['changes']=[]
        p['plan_sha256']=sha({k:v for k,v in p.items() if k!='plan_sha256'})
        with self.assertRaises(ValueError):help.reconcile(s,p,s,expected_plan_sha256=p['plan_sha256'])

    def test_cli_same_read_hashes_exclusive_output_and_duplicate_policy(self):
        import contextlib,io,json,tempfile
        from pathlib import Path
        from unittest.mock import patch
        from scripts.prepare_publication_registry_bootstrap import bytes_sha
        s=metadata_snapshot();m=meanings()
        with tempfile.TemporaryDirectory() as directory,contextlib.redirect_stderr(io.StringIO()):
            root=Path(directory).resolve();private=root/'private';private.mkdir()
            for name,value in dict(snapshot=s,meanings=m,qualification=qualification(s,m)).items():(private/(name+'.json')).write_text(json.dumps(value))
            args=[value for name in ('snapshot','meanings','qualification') for value in ('--'+name,str(private/(name+'.json')))]+['--output',str(private/'plan.json')]
            with patch.object(help,'ROOT',root):
                self.assertEqual(help.main(args),0);raw=(private/'plan.json').read_bytes()
                self.assertEqual(json.loads(raw)['source_files_sha256']['meanings'],bytes_sha((private/'meanings.json').read_bytes()))
                self.assertEqual(help.main(args),2);self.assertEqual((private/'plan.json').read_bytes(),raw)
                args[-1]=str(private/'other.json');(private/'qualification.json').write_text('{"field_semantics_confirmed":true,"field_semantics_confirmed":false}')
                self.assertEqual(help.main(args),2);self.assertFalse((private/'other.json').exists())
