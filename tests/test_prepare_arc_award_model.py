import base64
import copy
import unittest
import tempfile
import json
import hashlib
from pathlib import Path
from scripts.prepare_arc_award_model import prepare as raw_prepare, NAME, FIELDS
from scripts.reconcile_arc_awards_snapshots import fingerprint


def archive(**args):
    return dict(complete=True,next_links=[],record_kind='awards_only',fields=list(FIELDS),manifest_sha256='a'*64,**args)


def snapshot(rows=2):
    records=[dict.fromkeys(FIELDS,'') for _ in range(rows)]
    for i,row in enumerate(records):
        row.update(RecordKind='Award',Source='arc',SourceID=str(i),AwardCode='CODE-'+str(i),Amount=None,RetrievedUTC=None)
    return dict(source='arc',record_kind='awards_only',snapshot_complete=True,next_links=[],
                source_total=rows,snapshot_hash=fingerprint(records),records=records)


def prepare(data, **args):
    # Invalid scalar counts are rejected by the model before they could be used
    # as native authority; fixture bytes remain an explicit separate input.
    saved=snapshot(args['rows'] if type(args['rows']) is int and args['rows']>0 else 2)
    with tempfile.TemporaryDirectory() as temp:
        path=Path(temp)/'snapshot.json';path.write_text(json.dumps(saved))
        sha=hashlib.sha256(path.read_bytes()).hexdigest()
        receipt=archive(**{k:args[k] for k in ('site','folder','export_run','source_run','rows')})
        receipt.update(snapshot_file_sha256=sha,snapshot_records_sha256=saved['snapshot_hash'])
        return raw_prepare(data,**args,expected_sha256=fingerprint(data),
                           expected_parts=[p['path'] for p in data['parts']],
                           archive_receipt=receipt,archive_sha256=fingerprint(receipt),
                           snapshot_path=path,snapshot_sha256=sha)

SITE = 'https://example.sharepoint.com/sites/research'


def fixture():
    return {'format': 'TMDL', 'parts': [
        {'path': 'definition/model.tmdl', 'payloadType': 'InlineBase64',
         'payload': base64.b64encode(b'model Model\nref table Publication\n').decode()},
        {'path': 'definition/expressions.tmdl', 'payloadType': 'InlineBase64',
         'payload': base64.b64encode(('expression Files = SharePoint.Files("' + SITE + '")\n').encode()).decode()},
        {'path': 'definition/tables/Publication.tmdl', 'payloadType': 'InlineBase64',
         'payload': base64.b64encode(b'table Publication\n').decode()}]}


def build(data, **kwargs):
    return prepare(data, **dict(site=SITE, folder=SITE+'/Shared Documents/accepted/',
                               export_run='export-run', source_run='source-run', rows=2, **kwargs))


class AwardModelTests(unittest.TestCase):
    def test_pinned_preimage_inventory_and_archive_evidence_fail_closed(self):
        data=fixture();saved=snapshot()
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'snapshot';path.write_text(json.dumps(saved))
            sha=hashlib.sha256(path.read_bytes()).hexdigest()
            args=dict(site=SITE,folder=SITE+'/Shared Documents/accepted/',export_run='export-run',source_run='source-run',rows=2)
            receipt=archive(**args);receipt.update(snapshot_file_sha256=sha,snapshot_records_sha256=saved['snapshot_hash'])
            pins=dict(expected_sha256=fingerprint(data),expected_parts=[p['path'] for p in data['parts']],
                      archive_receipt=receipt,archive_sha256=fingerprint(receipt),snapshot_path=path,snapshot_sha256=sha)
            baseline=copy.deepcopy(data)
            for mode in ('digest','inventory','archive','snapshot','fields','run','count'):
                check=copy.deepcopy(pins)
                if mode=='digest':check['expected_sha256']='0'*64
                elif mode=='inventory':check['expected_parts'].pop()
                elif mode=='archive':check['archive_sha256']='0'*64
                elif mode=='snapshot':check['snapshot_sha256']='0'*64
                else:
                    if mode=='fields':check['archive_receipt']['fields'].pop()
                    elif mode=='run':check['archive_receipt']['source_run']='other'
                    else:check['archive_receipt']['rows']=True
                    check['archive_sha256']=fingerprint(check['archive_receipt'])
                with self.subTest(mode=mode),self.assertRaises(ValueError):raw_prepare(data,**args,**check)
            self.assertEqual(data,baseline)

    def test_all_source_fields_stay_text_unknown_and_never_summed(self):
        result=build(fixture())
        table=base64.b64decode(result['parts'][-1]['payload']).decode()
        self.assertEqual(table.count('dataType: string'),len(FIELDS))
        self.assertEqual(table.count('summarizeBy: none'),len(FIELDS))
        self.assertIn('dataCategory: WebUrl',table)
        self.assertNotIn('SUM(',table)

    def test_direct_stdlib_clis_connect_saved_snapshot_model_and_reader_and_preserve_failures(self):
        import subprocess,sys
        root=Path(__file__).resolve().parents[1];private=root/'private/ops';private.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=private) as temp:
            folder=Path(temp)
            def save(name,value):
                path=folder/name;path.write_text(json.dumps(value));return path
            def run(script,*args,ok=True):
                result=subprocess.run([sys.executable,'-S',str(root/'scripts'/script),*map(str,args)],
                                      cwd=folder,capture_output=True,text=True)
                self.assertEqual(result.returncode==0,ok,result.stderr)
                return result
            saved=snapshot();source=save('snapshot.json',saved)
            sha=hashlib.sha256(source.read_bytes()).hexdigest()
            compared=folder/'comparison.json'
            command=['reconcile_arc_awards_snapshots.py',source,source,'--baseline-sha256',sha,'--current-sha256',sha,'--output',compared]
            # Inputs must be distinct at the CLI boundary.
            run(*command,ok=False)
            old=save('baseline.json',saved);command[1]=old
            run(*command);self.assertFalse(json.loads(compared.read_text())['mutation_authorized'])
            before=compared.read_bytes();run(*command,ok=False);self.assertEqual(compared.read_bytes(),before)
            model=fixture();definition=save('model.json',model)
            inventory=save('model-parts.json',[p['path'] for p in model['parts']])
            args=dict(site=SITE,folder=SITE+'/Shared Documents/accepted/',export_run='export-run',source_run='source-run',rows=2)
            receipt=archive(**args);receipt.update(snapshot_file_sha256=sha,snapshot_records_sha256=saved['snapshot_hash'])
            evidence=save('archive-receipt.json',receipt);output=folder/'model-proposal.json'
            command=['prepare_arc_award_model.py','--definition',definition,'--output',output,
                     '--expected-sha256',fingerprint(model),'--expected-parts',inventory,
                     '--archive-receipt',evidence,'--archive-sha256',fingerprint(receipt),
                     '--snapshot',source,'--snapshot-sha256',sha]
            for key,value in args.items(): command.extend(['--'+key.replace('_','-'),value])
            run(*command)
            proposed=json.loads(output.read_text());self.assertEqual(len(proposed['parts']),4)
            self.assertEqual(proposed['parts'][2],model['parts'][2])
            before=output.read_bytes();run(*command,ok=False);self.assertEqual(output.read_bytes(),before)
            report={'sections':[{'name':str(i),'displayName':str(i),'ordinal':i,'visualContainers':[]} for i in range(8)]}
            reader={'definition':{'format':'PBIR-Legacy','parts':[
                {'path':'report.json','payloadType':'InlineBase64','payload':base64.b64encode(json.dumps(report).encode()).decode()},
                {'path':'definition.pbir','payloadType':'InlineBase64','payload':base64.b64encode(b'unchanged existing binding').decode()}]}}
            reportfile=save('report.json',reader);parts=save('report-parts.json',['report.json','definition.pbir']);out=folder/'reader-proposal.json'
            command=['prepare_arc_award_report_page.py','--definition',reportfile,'--output',out,
                     '--expected-sha256',fingerprint(reader),'--expected-parts',parts]
            run(*command);result=json.loads(out.read_text())
            self.assertEqual(result['definition']['parts'][1],reader['definition']['parts'][1])
            self.assertIn('ARCAwardContext',base64.b64decode(result['definition']['parts'][0]['payload']).decode())
            before=out.read_bytes();run(*command,ok=False);self.assertEqual(out.read_bytes(),before)
            # Even a caller-pinned outer duplicate key is ambiguous saved evidence.
            reportfile.write_bytes(b'{"definition":{},"definition":{}}')
            badout=folder/'bad.json';command[command.index(out)]=badout
            run(*command,ok=False);self.assertFalse(badout.exists())
            self.assertEqual(source.read_text(),json.dumps(saved))
            self.assertEqual(definition.read_text(),json.dumps(model))

    def test_additive_model_keeps_original_and_unrelated_part_bytes(self):
        data = fixture()
        baseline = copy.deepcopy(data)
        result = build(data)
        self.assertEqual(data, baseline)
        self.assertEqual(result['parts'][2], data['parts'][2])
        self.assertEqual(len(result['parts']), len(data['parts'])+1)
        self.assertEqual(result['parts'][-1]['path'], 'definition/tables/'+NAME+'.tmdl')
        with self.assertRaises(ValueError):
            build(result)

    def test_reject_duplicate_parts_before_any_preparation(self):
        data = fixture()
        data['parts'].append(copy.deepcopy(data['parts'][0]))
        with self.assertRaises(ValueError):
            build(data)

    def test_reject_unqualified_site_cross_site_folder_and_invalid_counts(self):
        for changes in [{'site':'https://other.sharepoint.com/sites/research'},
                        {'folder':'https://external.invalid/data/'},
                        {'folder':SITE+'/Documents/../accepted/'}, {'rows':True}, {'rows':0}]:
            args = dict(site=SITE, folder=SITE+'/Shared Documents/accepted/',
                        export_run='export-run', source_run='source-run', rows=2)
            args.update(changes)
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                prepare(fixture(), **args)
