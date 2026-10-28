# SPDX-License-Identifier: Apache-2.0
"""Synthetic supplied registry metadata; no native fixtures or operators."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import xml.etree.ElementTree as ET
from scripts import prepare_publication_registry_bootstrap as core

SITE='https://example.sharepoint.com/sites/fictional'
LIST='10000000-0000-0000-0000-000000000001'
STAMP='2026-10-29T00:00:00Z'

def guid(i):return f'20000000-0000-0000-0000-{i:012d}'

def meanings():return json.loads((Path(__file__).parents[1]/'config/publication-field-meanings.json').read_text())

def field(name,title,kind,i):
    f=dict(Id=guid(i),InternalName=name,Title=title,TypeAsString=kind,Description='original description',
        Required=False,Indexed=False,EnforceUniqueValues=False,ReadOnlyField=False,Sealed=False,
        __metadata={'etag':'"1"','type':'SP.Field','uri':'fixture:field'})
    if kind=='Text':f['MaxLength']=255
    if kind=='Note':f.update(RichText=False,AppendOnly=False)
    attrs=dict(ID='{'+f['Id']+'}',Name=name,DisplayName=title,Type=kind,Description=f['Description'],Version='1',Indexed='FALSE')
    f['SchemaXml']=ET.tostring(ET.Element('Field',attrs),encoding='unicode')
    return f

def view(role,i,*,default=False):
    return dict(Id=guid(i),Title='existing '+role,DefaultView=default,PersonalView=False,Hidden=False,
        ViewType='HTML',Paged=True,RowLimit=100,ViewQuery='',CustomFormatter='',
        ServerRelativeUrl='/sites/fictional/Lists/Registry/'+role+'.aspx',
        resolvedFields={'Items':{'results':['LinkTitle','field_1']}},
        __metadata={'etag':'"1"','type':'SP.View','uri':'fixture:view'})

def metadata_snapshot():
    fs=[field(m['name'],m['title'],m['type'],i+1) for i,m in enumerate(meanings()['fields'])]
    fs += [field('field_10','PMID','Text',30),field('field_4','Journal','Text',31),field('field_14','MatchedFacilities','Text',32),field('LinkTitle','LinkTitle','Computed',33)]
    rows=[]
    for i,key in [(1,'pubmed:1'),(2,'dora:1/2'),(3,None)]:
        row={f['InternalName']:None for f in fs};row.update(Id=i,Title='Retained' if i==1 else 'Keep',
            field_1=key,field_2='PUB:'+str(i) if key else None,field_3='A; B',field_5=None,
            field_6='2026-09' if i==1 else None,field_8='month' if i==1 else 'year',
            field_10='1' if i==1 else None,field_17='Needs Review',field_18='Keep human note',
            OData__UIVersionString='1.0',__metadata={'etag':'"1"','type':'SP.Data.Item','uri':'fixture:item'},
            versions=[{'version':'1.0','evidence':'fixture:history'}])
        rows.append(row)
    vs=[view(role,100+i) for i,role in enumerate(['publications','month','uncertainty','placeholders'])]
    vs.append(view('default',110,default=True))
    return dict(complete=True,next_links=[],capture_reference='fixture:full-snapshot',observedAtUTC=STAMP,
        site_url=SITE,list_id=LIST,list={'Id':LIST,'ItemCount':3,'__metadata':{'etag':'"1"'}},
        counts={'items':3,'fields':len(fs),'views':len(vs)},items=rows,fields=fs,views=vs)

def selected(snapshot,name):return next(f for f in snapshot['fields'] if f['InternalName']==name)

def changed_field(f,**values):
    f=copy.deepcopy(f);xml=ET.fromstring(f['SchemaXml'])
    for key,value in values.items():
        f[key]=value
        if key in {'Description','Indexed'}:xml.set(key,str(value).upper() if isinstance(value,bool) else value)
    xml.set('Version',str(int(xml.get('Version'))+1));f['SchemaXml']=ET.tostring(xml,encoding='unicode')
    f['__metadata']['etag']='"2"';return f

def query_evidence(s,p,results):
    return dict(complete=True,site_url=s['site_url'],list_id=s['list_id'],observedAtUTC=STAMP,
        capture_reference='fixture:queries',plan_sha256=p['plan_sha256'],results=results,
        counts={k:len(v) for k,v in results.items()})

class MetadataUtilitiesTests(unittest.TestCase):
    def test_complete_snapshot_is_detached_and_retains_metadata_and_versions(self):
        s=metadata_snapshot();out=core.validate_snapshot(s);self.assertEqual(out,s)
        out['items'][0]['__metadata']['etag']='changed';self.assertEqual(s['items'][0]['__metadata']['etag'],'"1"')
        self.assertIn('versions',out['items'][0])

    def test_duplicate_partial_error_wrong_target_and_boolean_ids_fail_closed(self):
        for fault in ['partial','error','count','item','field','view','boolean','target','date']:
            s=metadata_snapshot()
            if fault=='partial':s['partial']={}
            elif fault=='error':s['error']={}
            elif fault=='count':s['counts']['fields']+=1
            elif fault in ['item','field','view']:
                key={'item':'items','field':'fields','view':'views'}[fault];s[key][1]['Id']=s[key][0]['Id']
            elif fault=='boolean':s['items'][0]['Id']=True
            elif fault=='target':s['list']['Id']=guid(999)
            else:s['observedAtUTC']='2026-10-29T00:00:00'
            with self.subTest(fault=fault),self.assertRaises(ValueError):core.validate_snapshot(s)

    def test_existing_note_qualifies_but_text_missing_modes_or_wrong_identity_does_not_migrate(self):
        s=metadata_snapshot();f=selected(s,'field_3')
        target=dict(site_url=SITE,list_id=LIST,field_id=f['Id'],internal_name='field_3',display_name='Authors')
        result=core.qualify_existing_note(target,s);self.assertFalse(result['write_authorized'])
        self.assertEqual(result['status'],'compatible_existing_note')
        for fault in ['text','rich','missing','identity']:
            b=copy.deepcopy(s);x=selected(b,'field_3')
            if fault=='text':x['TypeAsString']='Text';x['SchemaXml']=x['SchemaXml'].replace('Type="Note"','Type="Text"')
            elif fault=='rich':x['RichText']=True
            elif fault=='missing':x.pop('AppendOnly')
            else:x['Id']=guid(999)
            with self.subTest(fault=fault),self.assertRaises(ValueError):core.qualify_existing_note(target,b)

    def test_full_title_absence_never_creates_or_proposes_a_field(self):
        s=metadata_snapshot();self.assertEqual(core.qualify_full_title(s)['InternalName'],'SourceFullTitle')
        s['fields']=[f for f in s['fields'] if f['InternalName']!='SourceFullTitle'];s['counts']['fields']-=1
        with self.assertRaises(ValueError):core.qualify_full_title(s)

    def test_bound_plan_refuses_changed_preimage_plan_and_rehashed_tampering(self):
        s=metadata_snapshot();p=core.make_plan('fixture',s,{},[])
        core.check_plan(p,s,p['plan_sha256'])
        bad=copy.deepcopy(p);bad['changes'].append({'unsafe':True})
        with self.assertRaises(ValueError):core.check_plan(bad,s,p['plan_sha256'])
        bad['plan_sha256']=core.sha({k:v for k,v in bad.items() if k!='plan_sha256'})
        with self.assertRaises(ValueError):core.check_plan(bad,s,p['plan_sha256'])
        s['items'][0]['__metadata']['etag']='"7"'
        with self.assertRaises(ValueError):core.check_plan(p,s,p['plan_sha256'])

    def test_cli_strict_json_exclusive_result_and_byte_hashes(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory).resolve();private=root/'private';private.mkdir()
            source=private/'snapshot.json';out=private/'result.json';source.write_text(json.dumps(metadata_snapshot()))
            with mock.patch.object(core,'ROOT',root):
                self.assertEqual(core.main(['--snapshot',str(source),'--output',str(out)]),0)
                result=json.loads(out.read_text());self.assertEqual(result['source_files_sha256']['snapshot'],core.bytes_sha(source.read_bytes()))
                saved=out.read_bytes();self.assertNotEqual(core.main(['--snapshot',str(source),'--output',str(out)]),0);self.assertEqual(out.read_bytes(),saved)
                out.unlink();source.write_text('{"complete":true,"complete":false}')
                self.assertNotEqual(core.main(['--snapshot',str(source),'--output',str(out)]),0);self.assertFalse(out.exists())

    def test_malformed_columns_case_aliases_and_field_xml_are_rejected(self):
        for fault in ('columns','case_alias','xml_identity','wildcard','version'):
            s=metadata_snapshot()
            if fault=='columns':s['views'][0]['resolvedFields']['Items']['results']=[{}]
            elif fault=='case_alias':
                f=copy.deepcopy(s['fields'][0]);f['Id']=guid(999);f['InternalName']=f['InternalName'].upper();root=ET.fromstring(f['SchemaXml']);root.set('ID','{'+f['Id']+'}');root.set('Name',f['InternalName']);f['SchemaXml']=ET.tostring(root,encoding='unicode');s['fields'].append(f);s['counts']['fields']+=1
            elif fault=='xml_identity':s['fields'][0]['SchemaXml']=s['fields'][1]['SchemaXml']
            elif fault=='wildcard':s['items'][0]['__metadata']['etag']='*'
            else:s['items'][0]['OData__UIVersionString']='1'
            with self.subTest(fault=fault),self.assertRaises(ValueError):core.validate_snapshot(s)

    def test_field_readback_retains_xml_metadata_and_unselected_values(self):
        s=metadata_snapshot();f=s['fields'][0];p=core.make_plan('fixture',s,{},[dict(id=f['Id'],desired={'Description':'qualified'})]);after=copy.deepcopy(s);after['fields'][0]=changed_field(f,Description='qualified')
        core.field_readback(s,p,after)
        for fault in ('metadata','xml','constraint','unselected','removed','views'):
            a=copy.deepcopy(after)
            if fault=='metadata':a['fields'][0]['__metadata']['uri']='different'
            elif fault=='xml':a['fields'][0]['SchemaXml']=a['fields'][0]['SchemaXml'].replace('Version="2"','Version="5"')
            elif fault=='constraint':a['fields'][0]['Required']=True
            elif fault=='unselected':a['fields'][1]['Description']='other'
            elif fault=='removed':a['fields'][1].pop('__metadata')
            else:a['views'][0]['CustomFormatter']='changed'
            with self.subTest(fault=fault),self.assertRaises(ValueError):core.field_readback(s,p,a)

    def test_query_complete_counts_identity_and_time_binding(self):
        s=metadata_snapshot();p=core.make_plan('fixture',s,{},[]);e=query_evidence(s,p,{'fixture':[dict(Id=1,SourceKey='pubmed:1')]})
        core.check_queries(s,p,s,e,{'fixture':[1]})
        for fault in ('count','duplicate','bool','key','time','partial','plan','extra'):
            bad=copy.deepcopy(e)
            if fault=='count':bad['counts']['fixture']=0
            elif fault=='duplicate':bad['results']['fixture']*=2;bad['counts']['fixture']=2
            elif fault=='bool':bad['results']['fixture'][0]['Id']=True
            elif fault=='key':bad['results']['fixture'][0]['SourceKey']='other'
            elif fault=='time':bad['observedAtUTC']='2026-10-28T00:00:00Z'
            elif fault=='partial':bad['next_links']=['remaining']
            elif fault=='plan':bad['plan_sha256']='0'*64
            else:bad['results']['extra']=[];bad['counts']['extra']=0
            with self.subTest(fault=fault),self.assertRaises(ValueError):core.check_queries(s,p,s,bad,{'fixture':[1]})

    def test_cli_shared_private_guards_and_failures_leave_no_output(self):
        import contextlib,io
        with tempfile.TemporaryDirectory() as directory,contextlib.redirect_stderr(io.StringIO()):
            root=Path(directory).resolve();private=root/'private';private.mkdir();source=private/'input.json';source.write_text(json.dumps(metadata_snapshot()));outside=root/'outside.json';outside.write_text(source.read_text());alias=private/'alias.json';alias.symlink_to(outside)
            with mock.patch.object(core,'ROOT',root):
                for input_path in (outside,alias):
                    out=private/'result.json';self.assertEqual(core.main(['--snapshot',str(input_path),'--output',str(out)]),2);self.assertFalse(out.exists())
                source.write_text('{"complete": NaN}')
                self.assertEqual(core.main(['--snapshot',str(source),'--output',str(private/'result.json')]),2);self.assertFalse((private/'result.json').exists())

    def test_omitted_human_fields_are_not_treated_as_captured_nulls(self):
        s=metadata_snapshot();s['items'][0].pop('field_18')
        with self.assertRaises(ValueError):core.validate_snapshot(s)
