"""Fictional ledger safety cases; these do not establish native provenance."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from scripts.build_publication_stub_preservation_ledger import (
    build, fingerprint, verify_action_references, verify_native_files,
)


def fixture():
    stamp = '2026-09-13T00:00:00Z'
    rows = [{'Id': i, 'GUID': 'fictional-' + str(i), 'odata.etag': '"1"',
             'OData__UIVersionString': '1.0', 'Created': stamp, 'Modified': stamp,
             'field_1': None, 'field_2': None, 'Title': None,
             'field_17': 'Needs Review', 'field_19':None, 'field_20':None, 'Attachments': False} for i in [1, 2]]
    original = {'candidate_count': 2, 'list_id': 'fictional-list',
                'items': [{'id': i, 'created': stamp} for i in [1, 2]]}
    native = {'complete':True, 'next_links':[], 'status':'fictional-capture',
              'candidate_count': 2, 'registry_metadata_stable': True, 'native_writes': 0,
              'items': [{'Id': i, 'GUID': 'fictional-' + str(i), 'ETag': '"1"',
                         'version': '1.0', 'version_history_complete': True, 'version_count': 1,
                         'version_pages': [{'file': f'versions-{i}-0.json', 'sha256': 'a' * 64}],
                         'current_core_fields_equal_snapshot': True,
                         'attachment_export_complete': True, 'attachments': []} for i in [1, 2]]}
    correlation = {'schema_version': 'publication-stub-action-correlation/v1', 'read_only': True,
                   'candidate_count': 2, 'candidate_snapshot_sha256': fingerprint(original),
                   'exact_match_count': 1, 'unmatched_candidate_count': 1,
                   'items': [{'id': 1, 'grade': 'direct_action_id_match',
                              'action': {'run_id': 'fictional-run', 'action_id': 'fictional-action',
                                         'evidence_ref': 'fictional-only.json'}},
                             {'id': 2, 'grade': 'unmatched', 'action': None}]}
    shapes = {'schema_version': 'publication-create-field-shape-inventory/v1', 'read_only': True,
              'item_count': 1, 'run_id': 'fictional-run', 'items': [
                  {'created_item_id': 1, 'output_version_populated_parity': True,
                   'input_nonblank_fields': ['field_17', 'field_19', 'field_20'],
                   'output_nonblank_fields': ['field_17', 'field_19', 'field_20']}]}
    fields = [{'InternalName': name, 'ReadOnlyField': False, 'Hidden': False,
               'TypeAsString': 'Text'} for name in ['field_1','field_2', 'Title', 'field_17','field_19','field_20']]
    context = {'list_id': 'fictional-list', 'native_data_writes': 0,
               'effective_retention_qualified': False,
               'preservation_reviewed_at_utc': '2026-10-28T00:00:00Z',
               'field_inventory':{'complete':True,'next_links':[],'field_count':len(fields),
                                  'fields_sha256':fingerprint(fields),'artifact_sha256':'f'*64,'source':'fictional-fields'}}
    return [rows, native, original, correlation, shapes, fields, context]


class PreservationLedgerTests(unittest.TestCase):
    def native_fixture(self, root):
        args=fixture(); rows,cohort=args[:2]
        args[5].append({'InternalName':'field_59','ReadOnlyField':False,'Hidden':False,'TypeAsString':'Note'})
        args[6]['field_inventory'].update(field_count=len(args[5]),fields_sha256=fingerprint(args[5]))
        mapping={f['InternalName']:'saved_'+f['InternalName'] for f in args[5]}
        for row,evidence in zip(rows,cohort['items']):
            row['field_59']='Fictional protected human review'
            row['OData__UIVersionString']='2.0';evidence.update(version='2.0',version_count=2)
            current={mapping[k]:row[k] for k in mapping};current.update(GUID=row['GUID'],IsCurrentVersion=True,VersionLabel='2.0')
            prior={**current,'IsCurrentVersion':False,'VersionLabel':'1.0'}
            path=root/evidence['version_pages'][0]['file'];path.write_text(json.dumps({'value':[prior,current]}))
            evidence['version_pages'][0]['sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
        attachment=root/'fictional-attachment.bin';attachment.write_bytes(b'fictional attachment bytes')
        rows[0]['Attachments']=True
        cohort['items'][0]['attachments']=[{'name':'fictional.txt','file':attachment.name,'sha256':hashlib.sha256(attachment.read_bytes()).hexdigest()}]
        return args,mapping

    def test_all_rows_retained_without_restoration_or_cleanup_authority(self):
        args = fixture(); before = copy.deepcopy(args)
        result = build(*args)
        self.assertEqual(args, before)
        self.assertEqual(result['counts']['retain_in_place'], 2)
        self.assertEqual(result['counts']['exact_create_matches'], 1)
        self.assertEqual(result['counts']['unresolved_create_provenance'], 1)
        self.assertEqual(result['restore_ready_count'], 0)
        self.assertFalse(result['mutation_authorized'])
        self.assertFalse(result['cleanup_authorized'])
        self.assertTrue(all(row['write_payload'] is None for row in result['items']))
        self.assertTrue(all(row['preservation_review']['decision'] == 'retain' for row in result['items']))
        self.assertNotEqual(result['items'][0]['preservation_review']['rationale'],
                            result['items'][1]['preservation_review']['rationale'])

    def test_missing_candidate_or_duplicate_id_does_not_drop_a_row(self):
        for change in ['missing', 'duplicate', 'bool']:
            args = fixture()
            if change == 'missing': args[1]['items'].pop()
            elif change == 'duplicate': args[0][1]['Id'] = 1
            else: args[0][0]['Id'] = True
            with self.subTest(change=change), self.assertRaises(ValueError): build(*args)

    def test_stale_candidate_binding_or_item_identity_fails_closed(self):
        for change in ['hash', 'guid', 'created', 'etag']:
            args = fixture()
            if change == 'hash': args[3]['candidate_snapshot_sha256'] = 'wrong'
            elif change == 'guid': args[1]['items'][0]['GUID'] = 'other'
            elif change == 'created': args[0][0]['Created'] = '2026-09-14T00:00:00Z'
            else: args[1]['items'][0]['ETag'] = '"2"'
            with self.subTest(change=change), self.assertRaises(ValueError): build(*args)

    def test_incomplete_history_or_attachments_cannot_pass_as_complete(self):
        for field, value in [('version_history_complete', False), ('version_count', 0),
                             ('attachments', [{'name': 'not-exported'}]),
                             ('attachment_export_complete', False)]:
            args = fixture(); args[1]['items'][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError): build(*args)

    def test_timestamp_cohort_cannot_replace_exact_create_action_evidence(self):
        args = fixture(); args[3]['items'][1].update(grade='same_timestamp_cohort')
        with self.assertRaisesRegex(ValueError, 'provenance'): build(*args)
        args = fixture(); args[3]['items'][0]['action']['action_id'] = ''
        with self.assertRaisesRegex(ValueError, 'provenance'): build(*args)

    def test_missing_visible_field_and_unqualified_retention_cannot_be_blessed(self):
        args = fixture(); del args[0][0]['field_17']
        with self.assertRaisesRegex(ValueError, 'writable'): build(*args)
        args = fixture(); args[6]['effective_retention_qualified'] = True
        with self.assertRaisesRegex(ValueError, 'retention'): build(*args)

    def test_shape_proof_requires_exact_run_and_does_not_expand_to_other_rows(self):
        args = fixture(); args[4]['run_id'] = 'other'
        with self.assertRaisesRegex(ValueError, 'run-bound'): build(*args)
        result = build(*fixture())
        self.assertTrue(result['items'][0]['retained_blank_create_input_output_proven'])
        self.assertFalse(result['items'][1]['retained_blank_create_input_output_proven'])

    def test_aggregate_or_list_mismatch_is_not_preservation_proof(self):
        for change in ['count', 'list']:
            args = fixture()
            if change == 'count': args[3]['exact_match_count'] = 2
            else: args[6]['list_id'] = 'other-list'
            with self.subTest(change=change), self.assertRaises(ValueError): build(*args)

    def test_boolean_write_counters_or_missing_history_references_are_rejected(self):
        for change in ['cohort', 'context', 'references']:
            args = fixture()
            if change == 'cohort': args[1]['native_writes'] = False
            elif change == 'context': args[6]['native_data_writes'] = False
            else: args[1]['items'][0]['version_pages'] = []
            with self.subTest(change=change), self.assertRaises(ValueError): build(*args)

    def test_native_action_reference_requires_exact_return_not_nearby_id(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); path = root / 'fictional-capture.json'
            capture = {'schema_version': 'publication-create-repetition-ids/v1',
                       'read_only': True, 'complete_repetition_index_set': True,
                       'run_id': 'fictional-run', 'action': 'SharePoint_Create_item',
                       'items': [{'iteration_zero_based': 0, 'action_status': 'Succeeded',
                                  'response_status': 201, 'created_item_id': 1}]}
            path.write_text(json.dumps(capture))
            correlation = fixture()[3]
            action = correlation['items'][0]['action']
            action.update(evidence_ref=str(path)+'#items[0]',
                          action_id='Apply_to_each_Publication/iteration_1/SharePoint_Create_item')
            self.assertEqual(verify_action_references(correlation, root)['exact_returns_rechecked'], 1)
            capture['items'][0]['created_item_id'] = 2; path.write_text(json.dumps(capture))
            with self.assertRaisesRegex(ValueError, 'exact candidate'): verify_action_references(correlation, root)
            action['evidence_ref'] = str(path)+'#items[9]'
            with self.assertRaisesRegex(ValueError, 'out of bounds'): verify_action_references(correlation, root)

    def test_native_version_files_are_value_and_hash_bound(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); rows = fixture()[0]
            for row in rows:
                for i in range(1, 21): row.setdefault('field_'+str(i), None)
            cohort = fixture()[1]
            for row, evidence in zip(rows, cohort['items']):
                version = {key.replace('_', '_x005f_'): value for key, value in row.items()
                           if key == 'Title' or key.startswith('field_')}
                version.update(GUID=row['GUID'], IsCurrentVersion=True, VersionLabel='1.0')
                path = root / evidence['version_pages'][0]['file']
                path.write_text(json.dumps({'value': [version]}))
                evidence['version_pages'][0]['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertEqual(verify_native_files(cohort, rows, root, fixture()[5], version_field_map={f['InternalName']:f['InternalName'].replace('_','_x005f_') for f in fixture()[5]}, inventory_receipt=fixture()[6]['field_inventory'])['native_history_files_value_bound'], 2)
            path.write_text('{}')
            with self.assertRaisesRegex(ValueError, 'bytes changed'): verify_native_files(cohort, rows, root, fixture()[5], version_field_map={f['InternalName']:f['InternalName'].replace('_','_x005f_') for f in fixture()[5]}, inventory_receipt=fixture()[6]['field_inventory'])

    def test_inventory_beyond_old_twenty_fields_versions_attachments_and_human_values(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);args,mapping=self.native_fixture(root)
            receipt=verify_native_files(args[1],args[0],root,args[5],version_field_map=mapping, inventory_receipt=args[6]['field_inventory'])
            self.assertEqual(receipt['visible_field_value_comparisons'],len(mapping)*2)
            self.assertEqual(receipt['attachment_files_hash_bound'],1)
            result=build(*args)
            self.assertEqual(result['items'][0]['older_saved_versions'],1)
            self.assertIsNone(result['counts']['older_saved_content_recoverable'])
            self.assertEqual(result['counts']['no_attachments'],1)
            self.assertEqual(result['items'][0]['current_record']['field_59'],'Fictional protected human review')
            result['items'][0]['current_record']['field_59']='overwrite'
            self.assertEqual(args[0][0]['field_59'],'Fictional protected human review')
            self.assertFalse(result['mutation_authorized']);self.assertIsNone(result['items'][0]['write_payload'])

    def test_dynamic_value_drift_missing_map_and_incomplete_native_page_rejected(self):
        for mode in ('value','map','next','marker','attachment'):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as temp:
                root=Path(temp);args,mapping=self.native_fixture(root)
                evidence=args[1]['items'][0];path=root/evidence['version_pages'][0]['file']
                payload=json.loads(path.read_bytes())
                if mode=='value':payload['value'][1][mapping['field_59']]='changed human value'
                elif mode=='map':mapping.pop('field_59')
                elif mode=='next':payload['@odata.nextLink']='https://example.invalid/unretained'
                elif mode=='marker':payload['value'][1]['IsCurrentVersion']=1
                else:(root/'fictional-attachment.bin').write_bytes(b'changed')
                path.write_text(json.dumps(payload));evidence['version_pages'][0]['sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
                with self.assertRaises(ValueError):verify_native_files(args[1],args[0],root,args[5],version_field_map=mapping, inventory_receipt=args[6]['field_inventory'])

    def test_unresolved_all_origins_and_no_shape_capture_are_preserved(self):
        args=fixture();args[3].update(exact_match_count=0,unmatched_candidate_count=2)
        for item in args[3]['items']:item.update(grade='unmatched',action=None)
        args[4].update(items=[],item_count=0)
        result=build(*args)
        self.assertEqual(result['counts']['unresolved_create_provenance'],2)
        self.assertEqual(result['counts']['retained_blank_create_input_output_proven'],0)
        self.assertTrue(all(item['disposition']=='retain_in_place' for item in result['items']))

    def test_duplicate_field_flags_and_padded_native_identity_fail(self):
        for mode in ('duplicate','flag','guid','list','count'):
            args=fixture()
            if mode=='duplicate':args[5].append(copy.deepcopy(args[5][0]))
            elif mode=='flag':args[5][0]['ReadOnlyField']=0
            elif mode=='guid':args[0][0]['GUID']=' fictional-1'
            elif mode=='list':args[6]['list_id']=args[2]['list_id']=' fictional-list'
            else:args[4]['item_count']=True
            with self.subTest(mode=mode),self.assertRaises(ValueError):build(*args)

    def test_complete_inventory_receipt_cannot_be_replaced_by_a_short_field_list(self):
        for mode in ('missing','partial','next','hash','bool'):
            args=fixture()
            if mode=='missing':args[6].pop('field_inventory')
            elif mode=='partial':args[5].pop()
            elif mode=='next':args[6]['field_inventory']['next_links']=['unretained-page']
            elif mode=='hash':args[6]['field_inventory']['fields_sha256']='0'*64
            else:args[6]['field_inventory']['field_count']=True
            with self.subTest(mode=mode),self.assertRaises(ValueError):build(*args)


if __name__ == '__main__':
    unittest.main()
