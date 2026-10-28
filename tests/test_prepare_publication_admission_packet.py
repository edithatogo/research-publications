# SPDX-License-Identifier: Apache-2.0
"""Synthetic frozen source journey; no requests, native calls or mutation."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET
from scripts import prepare_publication_admission_packet as admission
from scripts import prepare_publication_registry_bootstrap as core
from scripts.capture_report_bound_source_union import project_current_pubmed_efetch
from scripts.publication_xml_metadata import article_metadata
from scripts.verify_retained_canary_metadata_values import _dora
from scripts.publication_policy import load_policy
from scripts.organisation_enrichment import load_reference
from tests.test_pubmed_offline_typed_candidate import article
from tests.test_prepare_publication_registry_bootstrap import metadata_snapshot
from tests.test_preflight_publication_flow_activation import writer_fixture,target
AS_OF='2026-10-29T02:00:00Z'
OBSERVED='2026-10-29T01:00:00Z'


def pins(docs):return {k:core.sha(v) for k,v in {**docs,'policy':load_policy(),'reference':load_reference()}.items()}


def fixture():
    s=metadata_snapshot();t=target();generations=[dict(source=source,generation=source+':fixture:v1',model_id=t['model_id'],workspace_id=t['workspace_id'],request_id='fixture:request:'+source,observed_at_utc=OBSERVED) for source in ('DORA','PubMed')]
    xml=('<PubmedArticleSet>'+article('1',title='Source changes stay separate')+article('2',title='New source')+'</PubmedArticleSet>').encode()
    metadata=[dict(Field='dc.identifier.uri',Value=admission.OFFICIAL+'1/2'),dict(Field='dc.title',Value='Source DoRA title'),dict(Field='dc.contributor.author',Value='Raw Author'),dict(Field='dc.date.issued',Value='not known'),dict(Field='unknown.provider.field',Value='preserve')]
    dora=dict(kind='dora_metadata_records_v1',complete=True,records=[dict(source_id='DORA:1/2',metadata=metadata)])
    files={'pubmed.xml':xml,'dora.json':json.dumps(dora).encode()};parts=[];records=[]
    for source,name,profile,ids in [('PubMed','pubmed.xml','pubmed_efetch_xml_v1',['1','2']),('DORA','dora.json','dora_metadata_records_v1',['DORA:1/2'])]:
        generation=next(g for g in generations if g['source']==source)['generation']
        parts.append(dict(name=name,source=source,generation=generation,format=profile,bytes=len(files[name]),sha256=core.bytes_sha(files[name]),source_ids=ids))
        if source=='PubMed':
            projected=project_current_pubmed_efetch(xml);meta={a.findtext('MedlineCitation/PMID'):core.decode_json(article_metadata(a)['MetadataJSON']) for a in ET.fromstring(xml)}
        else:projected={'DORA:1/2':_dora(metadata)};meta={'DORA:1/2':metadata}
        for source_id in ids:
            key=admission.identity(source,source_id);canonical={'pubmed:1':'PUB:1','pubmed:2':'PUB:NEW','dora:1/2':'PUB:2'}[key]
            records.append(dict(source=source,source_id=source_id,SourceKey=key,CanonicalKey=canonical,generation=generation,part=name,record=projected[source_id],metadata=meta[source_id]))
    records.sort(key=lambda r:r['SourceKey']);bindings=[{k:r[k] for k in ('source','source_id','SourceKey','CanonicalKey')} for r in records]
    schema=dict(kind='publication_admission_schema_v1',complete=True,fields_sha256=core.sha(s['fields']),policy_sha256=core.sha(load_policy()),reference_sha256=core.sha(load_reference()),timestamp_profile='registry_processing_utc',timestamp_semantics_reference='fixture:writer-semantics',full_title_semantics_reference='fixture:full-title',capacities={})
    for f in s['fields']:
        if f['InternalName'] in admission.MAPPING.values() and f['TypeAsString'] in ('Text','Note'):
            schema['capacities'][f['InternalName']]=dict(field_id=f['Id'],utf16_units=255 if f['TypeAsString']=='Text' else 8000)
    docs=dict(acquisition=dict(kind='publication_frozen_acquisition_v1',complete=True,unfiltered=True,capture_reference='fixture:acquisition',scope_reference='fixture:scope',generations=generations,parts=parts),
        typed=dict(kind='publication_typed_admission_input_v1',complete=True,capture_reference='fixture:typed',generations=copy.deepcopy(generations),records=records,pages=[dict(rows=copy.deepcopy(records),cursor_before=None,cursor_after='terminal'),dict(rows=[],cursor_before='terminal',cursor_after='terminal')]),
        registry=s,writer=writer_fixture(),bindings=dict(kind='publication_source_bindings_v1',complete=True,target=t,generations=copy.deepcopy(generations),records=bindings,item_count=len(bindings)),
        state=dict(kind='publication_retained_versions_v1',cycles=[],versions=[],latest={}),ledger=dict(kind='publication_admission_ledger_v1',complete=True,entries=[],item_count=0),schema=schema)
    return docs,files


def replace_pubmed_title(docs,files,title):
    xml=('<PubmedArticleSet>'+article('1',title='Source changes stay separate')+article('2',title=title)+'</PubmedArticleSet>').encode();files['pubmed.xml']=xml
    part=next(p for p in docs['acquisition']['parts'] if p['source']=='PubMed');part.update(bytes=len(xml),sha256=core.bytes_sha(xml))
    projected=project_current_pubmed_efetch(xml);meta={a.findtext('MedlineCitation/PMID'):core.decode_json(article_metadata(a)['MetadataJSON']) for a in ET.fromstring(xml)}
    for r in docs['typed']['records']:
        if r['source']=='PubMed':r.update(record=projected[r['source_id']],metadata=meta[r['source_id']])
    docs['typed']['pages'][0]['rows']=copy.deepcopy(docs['typed']['records'])


class AdmissionTests(unittest.TestCase):
    def prepare(self,docs=None,files=None):
        if docs is None:docs,files=fixture()
        return admission.prepare(docs,files,expected_hashes=pins(docs),as_of=AS_OF)

    def test_complete_raw_to_typed_to_logical_proposals_preserves_all_inputs(self):
        docs,files=fixture();original=copy.deepcopy((docs,files));packet=self.prepare(docs,files)
        proposals={r['SourceKey']:r for r in packet['proposals']}
        self.assertEqual(proposals['pubmed:2']['proposed_values']['ReviewStatus'],'Included')
        self.assertEqual(proposals['pubmed:1']['proposed_observation'],{'LastObservedUTC':AS_OF})
        self.assertEqual(proposals['pubmed:1']['retained_current'],docs['registry']['items'][0])
        self.assertEqual(proposals['pubmed:1']['protected_values']['ReviewNotes'],'Keep human note')
        self.assertEqual(proposals['dora:1/2']['source_record']['record']['PublicationDatePrecision'],'unknown')
        self.assertEqual((docs,files),original);self.assertEqual(packet['allowed_existing_internal_fields'],['field_20']);self.assertFalse(packet['writer_ready']);self.assertFalse(packet['native_acceptance'])
        self.assertEqual(len(packet['retained_state_candidate']['versions']),3)
        self.assertEqual(self.prepare(docs,files),packet)

    def test_independent_pins_reject_every_rebound_document_and_policy(self):
        for name in admission.DOCUMENTS:
            docs,files=fixture();expected=pins(docs);docs[name]['injected']='changed'
            with self.subTest(name=name),self.assertRaises(ValueError):admission.prepare(docs,files,expected_hashes=expected,as_of=AS_OF)
        docs,files=fixture();expected=pins(docs);expected['policy']='0'*64
        with self.assertRaises(ValueError):admission.prepare(docs,files,expected_hashes=expected,as_of=AS_OF)

    def test_raw_bytes_complete_parts_and_typed_projection_cannot_be_substituted(self):
        for fault in ('bytes','missing','extra','count','keys','typed','metadata','generation','model','partial','unfiltered'):
            docs,files=fixture()
            if fault=='bytes':files['pubmed.xml']+=b' '
            elif fault=='missing':files.pop('pubmed.xml')
            elif fault=='extra':files['extra.xml']=files['pubmed.xml']
            elif fault=='count':docs['acquisition']['parts'][0]['bytes']=True
            elif fault=='keys':docs['acquisition']['parts'][0]['source_ids']=['1']
            elif fault=='typed':docs['typed']['records'][0]['record']['Title']='forged'
            elif fault=='metadata':docs['typed']['records'][0]['metadata']=[]
            elif fault=='generation':docs['typed']['generations'][0]['generation']='another'
            elif fault=='model':docs['bindings']['generations'][0]['model_id']=target()['flow_id']
            elif fault=='partial':docs['acquisition']['complete']=False
            else:docs['acquisition']['unfiltered']=False
            with self.subTest(fault=fault),self.assertRaises(ValueError):self.prepare(docs,files)

    def test_duplicated_ambiguous_or_inferred_source_bindings_fail(self):
        for fault in ('canonical','sourcekey','sourceid','duplicate','unknown_source','count'):
            docs,files=fixture();rows=docs['bindings']['records']
            if fault=='canonical':rows[1]['CanonicalKey']=rows[0]['CanonicalKey']
            elif fault=='sourcekey':rows[0]['SourceKey']='dora:'+rows[0]['CanonicalKey']
            elif fault=='sourceid':rows[1]['source_id']='01'
            elif fault=='duplicate':rows.append(copy.deepcopy(rows[0]));docs['bindings']['item_count']+=1
            elif fault=='unknown_source':rows[0]['source']='Other'
            else:docs['bindings']['item_count']=False
            with self.subTest(fault=fault),self.assertRaises(ValueError):self.prepare(docs,files)

    def test_paging_errors_duplicates_and_lost_terminal_page_fail(self):
        for fault in ('terminal','duplicate','value','cursor','error','partial'):
            docs,files=fixture();pages=docs['typed']['pages']
            if fault=='terminal':pages.pop()
            elif fault=='duplicate':pages[0]['rows'].append(copy.deepcopy(pages[0]['rows'][0]))
            elif fault=='value':pages[0]['rows'][0]['record']['Title']='changed'
            elif fault=='cursor':pages[1]['cursor_before']='different'
            elif fault=='error':pages[0]['error']={}
            else:pages[0]['partial']=True
            with self.subTest(fault=fault),self.assertRaises(ValueError):self.prepare(docs,files)

    def test_history_and_packet_ledger_refuse_identical_or_changed_replay(self):
        docs,files=fixture();packet=self.prepare(docs,files)
        for history in ('state','ledger'):
            d=copy.deepcopy(docs)
            if history=='state':d['state']=packet['retained_state_candidate']
            else:d['ledger'].update(item_count=1,entries=[dict(packet_sha256=packet['packet_sha256'],generations=d['bindings']['generations'])])
            with self.subTest(history=history),self.assertRaises(ValueError):self.prepare(d,files)

    def test_schema_writability_type_identity_capacity_and_semantics_are_required(self):
        for fault in ('type','capacity','id','readonly','note','semantics','fields_pin','missing'):
            docs,files=fixture();schema=docs['schema'];s=docs['registry']
            if fault=='type':core.field_named(s,'field_5')['TypeAsString']='Text'
            elif fault=='capacity':schema['capacities']['Title']['utf16_units']=256
            elif fault=='id':schema['capacities']['Title']['field_id']=target()['flow_id']
            elif fault=='readonly':core.field_named(s,'field_3')['ReadOnlyField']=True
            elif fault=='note':core.field_named(s,'SourceFullTitle')['RichText']=True
            elif fault=='semantics':schema['timestamp_semantics_reference']=''
            elif fault=='fields_pin':schema['fields_sha256']='0'*64
            else:schema['capacities'].pop('field_3')
            with self.subTest(fault=fault),self.assertRaises(ValueError):self.prepare(docs,files)

    def test_long_unicode_display_is_bounded_and_full_source_is_lossless(self):
        docs,files=fixture();title='X'+'😀'*150;replace_pubmed_title(docs,files,title);packet=self.prepare(docs,files)
        new=next(p for p in packet['proposals'] if p['kind']=='create')['proposed_values']
        self.assertEqual(new['SourceFullTitle'],title);self.assertLessEqual(len(new['Title'].encode('utf-16-le'))//2,255)
        docs['schema']['capacities']['SourceFullTitle']['utf16_units']=100
        with self.assertRaises(ValueError):self.prepare(docs,files)

    def test_unknown_dates_and_existing_exclusion_human_versions_remain_unchanged(self):
        docs,files=fixture();old=docs['registry']['items'][0];old.update(field_17='Excluded',field_5=None,field_6=None,field_18='Human decision');old['versions'].append(dict(version='2.0',evidence='fixture:human'))
        packet=self.prepare(docs,files);proposal=next(p for p in packet['proposals'] if p['SourceKey']=='pubmed:1')
        self.assertEqual(proposal['retained_current'],old);self.assertEqual(proposal['protected_values']['ReviewStatus'],'Excluded');self.assertNotIn('ReviewStatus',proposal['proposed_observation'])

    def test_unknown_dora_metadata_survives_and_conflicting_own_identity_fails(self):
        docs,files=fixture();packet=self.prepare(docs,files)
        self.assertIn(dict(Field='unknown.provider.field',Value='preserve'),packet['proposals'][0]['source_record']['metadata'])
        dora=json.loads(files['dora.json']);dora['records'][0]['metadata'][0]['Value']=admission.OFFICIAL+'1/999';files['dora.json']=json.dumps(dora).encode();part=docs['acquisition']['parts'][1];part.update(bytes=len(files['dora.json']),sha256=core.bytes_sha(files['dora.json']))
        with self.assertRaises(ValueError):self.prepare(docs,files)

    def test_existing_alias_or_canonical_conflict_never_merges_rows(self):
        for fault in ('case','alias','canonical','duplicate'):
            docs,files=fixture();rows=docs['registry']['items']
            if fault=='case':rows[0]['field_1']='PUBMED:1'
            elif fault=='alias':rows[1]['field_1']='dora:'+admission.OFFICIAL+'1/2'
            elif fault=='canonical':rows[0]['field_2']='PUB:NEW'
            else:rows[1]['field_1']=rows[0]['field_1']
            with self.subTest(fault=fault),self.assertRaises(ValueError):self.prepare(docs,files)

    def test_observation_noop_regression_and_future_evidence(self):
        docs,files=fixture();docs['registry']['items'][0]['field_20']=AS_OF;packet=self.prepare(docs,files)
        p=next(p for p in packet['proposals'] if p['SourceKey']=='pubmed:1');self.assertEqual(p['kind'],'noop');self.assertEqual(p['proposed_observation'],{})
        docs['registry']['items'][0]['field_20']='2026-10-29T03:00:00Z'
        with self.assertRaises(ValueError):self.prepare(docs,files)
        docs,files=fixture()
        with self.assertRaises(ValueError):admission.prepare(docs,files,expected_hashes=pins(docs),as_of='2026-10-28T00:00:00Z')

    def test_packet_tampering_independent_pin_and_rebuilding_scope(self):
        docs,files=fixture();p=self.prepare(docs,files);pin=p['packet_sha256'];expected=pins(docs)
        self.assertFalse(admission.verify(p,docs,files,expected_hashes=expected,expected_packet_sha256=pin,as_of=AS_OF)['writer_ready'])
        p['proposals'][0]['proposed_observation']['ReviewNotes']='forged'
        with self.assertRaises(ValueError):admission.verify(p,docs,files,expected_hashes=expected,expected_packet_sha256=pin,as_of=AS_OF)
        p['packet_sha256']=core.sha({k:v for k,v in p.items() if k!='packet_sha256'})
        with self.assertRaises(ValueError):admission.verify(p,docs,files,expected_hashes=expected,expected_packet_sha256=p['packet_sha256'],as_of=AS_OF)

    def test_cli_roundtrip_same_read_hashes_and_exclusive_output(self):
        import contextlib,io
        docs,files=fixture()
        with tempfile.TemporaryDirectory() as directory,contextlib.redirect_stderr(io.StringIO()):
            root=Path(directory).resolve();private=root/'private';private.mkdir()
            mapping={}
            for name,raw in files.items():path=private/name;path.write_bytes(raw);mapping[name]=str(path)
            for name,value in dict(inputs=docs,pins=pins(docs),files=mapping).items():(private/(name+'.json')).write_text(json.dumps(value))
            args=[v for name in ('inputs','files','pins') for v in ('--'+name,str(private/(name+'.json')))]+['--as-of',AS_OF,'--output',str(private/'packet.json')]
            with patch.object(admission,'ROOT',root):
                self.assertEqual(admission.main(args),0);raw=(private/'packet.json').read_bytes();envelope=json.loads(raw);p=envelope['result']
                self.assertEqual(envelope['source_files_sha256']['raw:pubmed.xml'],core.bytes_sha(files['pubmed.xml']))
                self.assertEqual(admission.main(args),2);self.assertEqual((private/'packet.json').read_bytes(),raw)
                args[-1]=str(private/'comparison.json');self.assertEqual(admission.main(args+['--packet',str(private/'packet.json'),'--expected-packet-sha256',p['packet_sha256']]),0)

    def test_more_than_one_hundred_records_and_variable_raw_part_count(self):
        docs,files=fixture();ids=[str(i) for i in range(3,104)];xml=('<PubmedArticleSet>'+''.join(article(i,title='Additional '+i) for i in ids)+'</PubmedArticleSet>').encode();name='additional.xml';files[name]=xml;g=next(g for g in docs['bindings']['generations'] if g['source']=='PubMed')
        docs['acquisition']['parts'].append(dict(name=name,source='PubMed',generation=g['generation'],format='pubmed_efetch_xml_v1',bytes=len(xml),sha256=core.bytes_sha(xml),source_ids=sorted(ids)))
        projected=project_current_pubmed_efetch(xml);meta={a.findtext('MedlineCitation/PMID'):core.decode_json(article_metadata(a)['MetadataJSON']) for a in ET.fromstring(xml)}
        for source_id in ids:
            binding=dict(source='PubMed',source_id=source_id,SourceKey='pubmed:'+source_id,CanonicalKey='EXPLICIT:'+source_id);docs['bindings']['records'].append(binding)
            docs['typed']['records'].append(dict(**binding,generation=g['generation'],part=name,record=projected[source_id],metadata=meta[source_id]))
        docs['bindings']['item_count']=len(docs['bindings']['records']);docs['typed']['records'].sort(key=lambda r:r['SourceKey']);docs['typed']['pages'][0]['rows']=copy.deepcopy(docs['typed']['records'])
        packet=self.prepare(docs,files);self.assertEqual(len(packet['proposals']),104);self.assertEqual(len(packet['raw_files']),3);self.assertIn('pilot_topn_100',packet['writer_preflight']['blockers'])

    def test_source_disappearance_preserves_last_good_state_and_all_history(self):
        from scripts.publication_retained_cycle import retain,latest_projection
        docs,files=fixture();docs['state']=retain(docs['state'],[('9',{'Title':'Prior retained source','PublicationDatePrecision':'unknown'})],generation='prior',observed_at='2026-10-28T00:00:00Z',source='PubMed',complete=True)
        previous=copy.deepcopy(docs['state']);packet=self.prepare(docs,files);candidate=packet['retained_state_candidate']
        self.assertEqual(candidate['versions'][:len(previous['versions'])],previous['versions']);self.assertEqual(candidate['cycles'][:len(previous['cycles'])],previous['cycles'])
        missing=next(r for r in latest_projection(candidate) if r['SourceKey']=='pubmed:9');self.assertFalse(missing['PresentInLatestSourceCycle']);self.assertEqual(missing['Record']['Title'],'Prior retained source')

    def test_rehashed_raw_xml_cannot_conceal_unknown_metadata_loss(self):
        docs,files=fixture();old=files['pubmed.xml'];new=old.replace(b'<ArticleTitle>',b'<UnknownProviderField>Retain this</UnknownProviderField><ArticleTitle>',1);files['pubmed.xml']=new;p=docs['acquisition']['parts'][0];p.update(bytes=len(new),sha256=core.bytes_sha(new))
        with self.assertRaises(ValueError):self.prepare(docs,files)

    def test_raw_json_duplicates_and_nested_page_error_envelopes_are_rejected(self):
        docs,files=fixture();files['dora.json']=files['dora.json'].replace(b'"complete": true',b'"complete": true, "complete": true');part=docs['acquisition']['parts'][1];part.update(bytes=len(files['dora.json']),sha256=core.bytes_sha(files['dora.json']))
        with self.assertRaises(ValueError):self.prepare(docs,files)
        docs,files=fixture();docs['typed']['pages'][0]['errors']={}
        with self.assertRaises(ValueError):self.prepare(docs,files)

    def test_cli_malformed_json_symlinks_and_incomplete_comparison_preserve_files(self):
        import contextlib,io
        docs,files=fixture()
        with tempfile.TemporaryDirectory() as directory,contextlib.redirect_stderr(io.StringIO()):
            root=Path(directory).resolve();private=root/'private';private.mkdir();mapping={}
            for name,raw in files.items():path=private/name;path.write_bytes(raw);mapping[name]=str(path)
            for name,value in dict(inputs=docs,pins=pins(docs),files=mapping).items():(private/(name+'.json')).write_text(json.dumps(value))
            out=private/'result.json';args=[v for name in ('inputs','files','pins') for v in ('--'+name,str(private/(name+'.json')))]+['--as-of',AS_OF,'--output',str(out)]
            with patch.object(admission,'ROOT',root):
                self.assertEqual(admission.main(args+['--expected-packet-sha256','0'*64]),2);self.assertFalse(out.exists())
                (private/'pins.json').write_text('{"bad":NaN}');self.assertEqual(admission.main(args),2);self.assertFalse(out.exists());(private/'pins.json').write_text(json.dumps(pins(docs)))
                original=private/'pubmed.xml';alias=private/'alias.xml';alias.symlink_to(original);mapping['pubmed.xml']=str(alias);(private/'files.json').write_text(json.dumps(mapping))
                self.assertEqual(admission.main(args),2);self.assertFalse(out.exists());self.assertEqual(original.read_bytes(),files['pubmed.xml'])

    def test_direct_scripts_under_selected_python_without_site_packages(self):
        import subprocess,sys
        docs,files=fixture();root=Path(__file__).resolve().parents[1]
        self.assertTrue((root/'private').is_dir());self.assertFalse((root/'private').is_symlink())
        with tempfile.TemporaryDirectory(prefix='admission-cli-test-',dir=root/'private') as directory:
            private=Path(directory);mapping={}
            for name,raw in files.items():path=private/name;path.write_bytes(raw);mapping[name]=str(path)
            for name,value in dict(inputs=docs,pins=pins(docs),files=mapping,writer=docs['writer'],registry=docs['registry'],target=docs['bindings']['target']).items():(private/(name+'.json')).write_text(json.dumps(value))
            args=[v for name in ('inputs','files','pins') for v in ('--'+name,str(private/(name+'.json')))]+['--as-of',AS_OF,'--output',str(private/'packet.json')]
            result=subprocess.run([sys.executable,'-S',str(root/'scripts/prepare_publication_admission_packet.py'),*args],cwd=root,capture_output=True,text=True,timeout=20)
            self.assertEqual(result.returncode,0,result.stderr);self.assertFalse(json.loads((private/'packet.json').read_bytes())['result']['writer_ready'])
            args=[v for name in ('writer','registry','target') for v in ('--'+name,str(private/(name+'.json')))]+['--expected-writer-sha256',core.sha(docs['writer']),'--output',str(private/'preflight.json')]
            result=subprocess.run([sys.executable,'-S',str(root/'scripts/preflight_publication_flow_activation.py'),*args],cwd=root,capture_output=True,text=True,timeout=20)
            self.assertEqual(result.returncode,0,result.stderr);self.assertFalse(json.loads((private/'preflight.json').read_bytes())['result']['activation_permitted'])

    def test_new_retained_versions_carry_complete_source_evidence_without_enriching_values(self):
        docs,files=fixture();p=self.prepare(docs,files)
        for version in p['retained_state_candidate']['versions']:
            evidence=version['SourceEvidence'];record=evidence['typed_record']
            self.assertEqual(version['Record'],record['record']);self.assertEqual(evidence['raw_part']['sha256'],core.bytes_sha(files[record['part']]))
        dora=next(v for v in p['retained_state_candidate']['versions'] if v['SourceKey']=='dora:1/2')
        self.assertIn(dict(Field='unknown.provider.field',Value='preserve'),dora['SourceEvidence']['typed_record']['metadata'])

    def test_sparse_rss_cannot_replace_full_dora_metadata_even_with_matching_typed_values(self):
        docs,files=fixture();raw=json.loads(files['dora.json']);metadata=raw['records'][0]['metadata'];metadata.append(dict(Field='rims.source.format',Value='dora_rss_v1'));files['dora.json']=json.dumps(raw).encode();part=docs['acquisition']['parts'][1];part.update(bytes=len(files['dora.json']),sha256=core.bytes_sha(files['dora.json']))
        record=next(r for r in docs['typed']['records'] if r['source']=='DORA');record.update(record=_dora(metadata),metadata=metadata);docs['typed']['pages'][0]['rows']=copy.deepcopy(docs['typed']['records'])
        with self.assertRaisesRegex(ValueError,'Sparse RSS'):self.prepare(docs,files)

    def test_configuration_change_during_preparation_cannot_rebind_retention(self):
        docs,files=fixture();expected=pins(docs);reference=load_reference()
        with patch.object(admission,'load_reference',side_effect=[reference,{}]),self.assertRaisesRegex(ValueError,'changed during'):
            admission.prepare(docs,files,expected_hashes=expected,as_of=AS_OF)

    def test_processing_timestamps_and_source_observations_keep_distinct_meanings(self):
        docs,files=fixture();p=self.prepare(docs,files)
        create=next(p for p in p['proposals'] if p['kind']=='create')
        self.assertEqual(create['proposed_values']['FirstObservedUTC'],AS_OF);self.assertEqual(create['proposed_values']['LastObservedUTC'],AS_OF)
        source=next(v for v in p['retained_state_candidate']['versions'] if v['SourceKey']==create['SourceKey']);self.assertEqual(source['ObservedAtUTC'],OBSERVED)
        docs['schema']['timestamp_profile']='source_observation_utc'
        with self.assertRaises(ValueError):self.prepare(docs,files)

    def test_own_pmid_cardinality_rejects_duplicate_same_and_conflicting_ids(self):
        for value in ('1','2'):
            raw=('<PubmedArticleSet>'+article('1')+'</PubmedArticleSet>').encode();root=ET.fromstring(raw);citation=root[0].find('MedlineCitation');duplicate=ET.Element('PMID');duplicate.text=value;citation.insert(1,duplicate);raw=ET.tostring(root)
            with self.subTest(value=value),self.assertRaises(ValueError):admission.project_part(dict(source='PubMed',format='pubmed_efetch_xml_v1',source_ids=['1']),raw)

    def test_own_citation_article_and_title_cardinality_is_checked_before_projection(self):
        for name in ('MedlineCitation','Article','ArticleTitle'):
            root=ET.fromstring('<PubmedArticleSet>'+article('1')+'</PubmedArticleSet>')
            parent={'MedlineCitation':root[0],'Article':root[0].find('MedlineCitation'),'ArticleTitle':root[0].find('MedlineCitation/Article')}[name];parent.append(copy.deepcopy(parent.find(name)))
            with self.subTest(name=name),self.assertRaises(ValueError):admission.project_part(dict(source='PubMed',format='pubmed_efetch_xml_v1',source_ids=['1']),ET.tostring(root))

    def test_identity_and_title_scalar_structure_cannot_hide_nested_own_fields(self):
        for fault in ('pmid_child','nested_title','empty_title','duplicate_journal_title'):
            root=ET.fromstring('<PubmedArticleSet>'+article('1')+'</PubmedArticleSet>');own=root[0].find('MedlineCitation/Article');title=own.find('ArticleTitle')
            if fault=='pmid_child':root[0].find('MedlineCitation/PMID').append(ET.Element('i'))
            elif fault=='nested_title':ET.SubElement(title,'ArticleTitle').text='other'
            elif fault=='empty_title':title.text=' '
            else:own.find('Journal').append(copy.deepcopy(own.find('Journal/Title')))
            with self.subTest(fault=fault),self.assertRaises(ValueError):admission.project_part(dict(source='PubMed',format='pubmed_efetch_xml_v1',source_ids=['1']),ET.tostring(root))

    def test_utf16_and_other_encoding_profiles_cannot_bypass_entity_refusal(self):
        body='<!DOCTYPE PubmedArticleSet [<!ENTITY own "Expanded">]><PubmedArticleSet>'+article('1',title='&own;')+'</PubmedArticleSet>'
        for encoding in ('utf-8','utf-16','utf-16-le','utf-16-be','utf-32'):
            declared='UTF-8' if encoding=='utf-8' else 'UTF-16' if encoding.startswith('utf-16') else 'UTF-32'
            raw=('<?xml version="1.0" encoding="'+declared+'"?>'+body).encode(encoding)
            with self.subTest(encoding=encoding),self.assertRaises(ValueError):admission.project_part(dict(source='PubMed',format='pubmed_efetch_xml_v1',source_ids=['1']),raw)
        raw=('<?xml version="1.0" encoding="ISO-8859-1"?><PubmedArticleSet>'+article('1')+'</PubmedArticleSet>').encode('ascii')
        with self.assertRaises(ValueError):admission.project_part(dict(source='PubMed',format='pubmed_efetch_xml_v1',source_ids=['1']),raw)

    def test_cited_pmids_mixed_title_markup_and_escaped_entities_are_preserved(self):
        title='Café &amp; <i>mixed</i> H<sub>2</sub>O &lt; 3'
        xml='<?xml version="1.0" encoding="UTF-8" standalone="yes"?><PubmedArticleSet>'+article('1',title=title)+'<PubmedArticle><MedlineCitation><PMID>2</PMID><Article><ArticleTitle>Second</ArticleTitle></Article></MedlineCitation></PubmedArticle></PubmedArticleSet>'
        root=ET.fromstring(xml);references=ET.SubElement(root[0],'ReferenceList')
        for value in ('1','2','999'):
            reference=ET.SubElement(references,'Reference');ET.SubElement(reference,'PMID').text=value
        raw=b'\xef\xbb\xbf'+b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'+ET.tostring(root,encoding='utf-8');saved=raw
        projected=admission.project_part(dict(source='PubMed',format='pubmed_efetch_xml_v1',source_ids=['1','2']),raw)
        self.assertEqual(projected['1'][0]['Title'],'Café & mixed H2O < 3');self.assertEqual(set(projected),{'1','2'});self.assertEqual(raw,saved)
        self.assertEqual(projected['1'][1],core.decode_json(article_metadata(ET.fromstring(raw)[0])['MetadataJSON']))
