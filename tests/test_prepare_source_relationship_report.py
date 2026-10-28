import base64,copy,hashlib,json,subprocess,sys,tempfile,unittest
from pathlib import Path
from test_prepare_source_relationship_model import fixture
from scripts.prepare_source_relationship_model import prepare as model_prepare,fingerprint,document_hash,ROOT
from scripts.prepare_source_relationship_report import prepare,PAGES,digest
MID='11111111-1111-4111-8111-111111111111';RID='22222222-2222-4222-8222-222222222222'

def report_fixture(root):
    def write(path,value):
        p=root/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(value))
    write('definition.pbir',{'datasetReference':{'byConnection':{'connectionString':'semanticmodelid='+MID+';'}}})
    write('definition/report.json',{'protected':'unchanged report settings'})
    write('definition/pages/pages.json',{'pageOrder':['ResearchRelationships','SourceFreshness'],'activePageName':'ResearchRelationships'})
    for page in ('ResearchRelationships','SourceFreshness'):write('definition/pages/'+page+'/page.json',dict(name=page,displayName=page,width=1920,height=1080))
    for name,kind in (('relationships-guidance','textbox'),('candidates','cardVisual'),('author-pattern','barChart')):
        write('definition/pages/ResearchRelationships/visuals/'+name+'/visual.json',dict(name=name,position=dict(x=0,y=0,width=100,height=100),visual=dict(visualType=kind,visualContainerObjects={'visualLink':[{'protected':'old action must not copy'}]},query={'original':'preserved'})))
    (root/'protected.bin').write_bytes(b'full untouched binary')

def files(root):return {p.relative_to(root).as_posix():p.read_bytes() for p in root.rglob('*') if p.is_file()}
def arguments(source,output):
    args=fixture();packet=model_prepare(**args);source_hash=digest(files(source))
    binding=dict(complete=True,report_id=RID,model_id=MID,report_capture_ref='fictional://report',model_capture_ref='fictional://model',observed_at_utc='2026-10-29T01:00:00Z',
        report_bundle_sha256=source_hash,source_model_sha256=packet['inputModelSHA256'],candidate_model_sha256=packet['outputModelSHA256'],
        report_binding_readback={'status_code':200,'text':{'id':RID,'datasetId':MID}})
    return dict(source=str(source),output=str(output),expected_sha256=source_hash,model_packet=packet,model_packet_sha256=fingerprint(packet),
        expected_model_parts=[p['path'] for p in packet['modelDefinition']['definition']['parts']],binding_evidence=binding,binding_sha256=fingerprint(binding))

class SourceReaderTests(unittest.TestCase):
    def temp(self):
        base=ROOT/'private/ops';base.mkdir(parents=True,exist_ok=True)
        return tempfile.TemporaryDirectory(dir=base)

    def test_connected_projection_model_reader_preserves_originals_and_limits(self):
        with self.temp() as temp:
            root=Path(temp);source=root/'source';source.mkdir();report_fixture(source);before=files(source)
            args=arguments(source,root/'candidate');saved=copy.deepcopy(args);receipt=prepare(**args)
            self.assertEqual(args,saved);self.assertEqual(files(source),before);self.assertFalse(receipt['nativeSaveSubmitted'])
            result=files(root/'candidate')
            for path,raw in before.items():
                if path!='definition/pages/pages.json':self.assertEqual(result[path],raw)
            for page in PAGES:
                for path,raw in result.items():
                    if path.startswith('definition/pages/'+page+'/visuals/'):
                        v=json.loads(raw);self.assertNotIn('visualLink',v['visual'].get('visualContainerObjects',{}))
                        p=v['position'];self.assertLessEqual(p['x']+p['width'],1920);self.assertLessEqual(p['y']+p['height'],1080)
            text='\n'.join(raw.decode() for p,raw in result.items() if p.endswith('.json') and any(page in p for page in PAGES))
            self.assertIn('Candidate source assertions only',text);self.assertIn('unavailable',text)
            self.assertNotIn('Qualified author IDs',text)
            with self.assertRaises(ValueError):prepare(**args)
            self.assertEqual(result,files(root/'candidate'))

    def test_missing_or_conflicting_identity_and_model_dependencies_fail_before_output(self):
        for mode in ('binding-pin','dataset','report-hash','model-hash','capability','type','measure','inventory'):
            with self.subTest(mode=mode),self.temp() as temp:
                root=Path(temp);source=root/'source';source.mkdir();report_fixture(source);args=arguments(source,root/'out')
                if mode=='binding-pin':args['binding_sha256']='0'*64
                elif mode=='dataset':args['binding_evidence']['report_binding_readback']['text']['datasetId']=RID
                elif mode=='report-hash':args['binding_evidence']['report_bundle_sha256']='0'*64
                elif mode=='model-hash':args['binding_evidence']['candidate_model_sha256']='0'*64
                elif mode=='capability':args['model_packet']['status']='blocked';args['model_packet']['blockers']=['native_typed_input']
                elif mode=='inventory':args['expected_model_parts'].pop()
                else:
                    packet=args['model_packet'];part=packet['modelDefinition']['definition']['parts'][-1];text=base64.b64decode(part['payload']).decode()
                    text=text.replace('dataType: boolean','dataType: string',1) if mode=='type' else text.replace('BLANK()','0',1)
                    part['payload']=base64.b64encode(text.encode()).decode();packet['outputModelSHA256']=document_hash(packet['modelDefinition']);args['binding_evidence']['candidate_model_sha256']=packet['outputModelSHA256']
                if mode!='binding-pin':args['binding_sha256']=fingerprint(args['binding_evidence'])
                args['model_packet_sha256']=fingerprint(args['model_packet'])
                with self.assertRaises(ValueError):prepare(**args)
                self.assertFalse((root/'out').exists())

    def test_drift_strict_json_symlinks_and_template_failures_preserve_existing_files(self):
        for mode in ('drift','json','symlink','template'):
            with self.subTest(mode=mode),self.temp() as temp:
                root=Path(temp);source=root/'source';source.mkdir();report_fixture(source);args=arguments(source,root/'out')
                if mode=='drift':(source/'protected.bin').write_bytes(b'changed')
                elif mode=='json':(source/'definition/report.json').write_bytes(b'{"x":1,"x":2}')
                elif mode=='symlink':(source/'alias').symlink_to(source/'protected.bin')
                else:(source/'definition/pages/ResearchRelationships/visuals/candidates/visual.json').unlink()
                if mode in ('json','template'):
                    args['expected_sha256']=digest(files(source));args['binding_evidence']['report_bundle_sha256']=args['expected_sha256'];args['binding_sha256']=fingerprint(args['binding_evidence'])
                with self.assertRaises(ValueError):prepare(**args)
                self.assertFalse((root/'out').exists())

    def test_failed_install_cleans_only_new_candidate_and_staging(self):
        from unittest.mock import patch
        with self.temp() as temp:
            root=Path(temp);source=root/'source';source.mkdir();report_fixture(source);args=arguments(source,root/'out');before=files(source)
            with patch('scripts.prepare_source_relationship_report.os.rename',side_effect=OSError('fictional install failure')):
                with self.assertRaises(OSError):prepare(**args)
            self.assertFalse((root/'out').exists());self.assertEqual(files(source),before)
            self.assertEqual([p.name for p in root.iterdir()],['source'])

    def test_private_direct_clis_close_under_stdlib_and_keep_blocked_capabilities_visible(self):
        with self.temp() as temp:
            root=Path(temp);model_args=fixture();input=root/'model-input.json';input.write_text(json.dumps(model_args));out=root/'model-output.json'
            command=[sys.executable,'-B','-S',str(ROOT/'scripts/prepare_source_relationship_model.py'),'--input',str(input),'--output',str(out)]
            result=subprocess.run(command,cwd=root,capture_output=True,text=True);self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(json.loads(out.read_text())['status'],'prepared')
            source=root/'source';source.mkdir();report_fixture(source);args=arguments(source,root/'reader');args['model_packet']=json.loads(out.read_text());args['model_packet_sha256']=fingerprint(args['model_packet'])
            path=root/'reader-input.json';path.write_text(json.dumps(args))
            result=subprocess.run([sys.executable,'-B','-S',str(ROOT/'scripts/prepare_source_relationship_report.py'),'--input',str(path)],cwd=root,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr);self.assertTrue((root/'reader').exists())
            model_args['producer_context']['capabilities']={};model_args['producer_context_sha256']=fingerprint(model_args['producer_context']);input.write_text(json.dumps(model_args));blocked=root/'blocked.json';command[-1]=str(blocked)
            result=subprocess.run(command,cwd=root,capture_output=True,text=True);self.assertEqual(result.returncode,0,result.stderr)
            self.assertIsNone(json.loads(blocked.read_text())['modelDefinition'])

    def test_nested_output_cannot_change_source_capture(self):
        with self.temp() as temp:
            source=Path(temp)/'source';source.mkdir();report_fixture(source);before=files(source)
            with self.assertRaises(ValueError):prepare(**arguments(source,source/'nested'))
            self.assertEqual(files(source),before)
