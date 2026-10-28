# SPDX-License-Identifier: Apache-2.0
"""Fictional source/register/model/export journeys; no native transport."""
import copy
import tempfile
import unittest
from pathlib import Path

from scripts import prepare_publication_admission_packet as admission
from scripts import prepare_publication_consumer_parity as parity
from scripts import prepare_publication_registry_bootstrap as core
from scripts.export_publication_register import EXPORT_FIELDS, key_hash
from tests.test_prepare_publication_admission_packet import fixture as admission_fixture, pins, AS_OF


def capture(rows, context, role):
    return dict(kind='publication_consumer_capture_v1', complete=True, next_links=[],
                role=role, context=copy.deepcopy(context), row_count=len(rows),
                rows_sha256=core.sha(rows), pages=[dict(number=1, cursor_before=None,
                cursor_after='done', terminal=False, rows=rows), dict(number=2,
                cursor_before='done', cursor_after='done', terminal=True, rows=[])])


def export(rows, context, mode, month=None):
    return dict(context, complete=True, next_links=[], coverage_note='Fictional complete capture',
                scope=dict(mode=mode, reporting_month=month), expected_keys_generation_id=context['generation_id'],
                expected_canonical_keys=[r['CanonicalKey'] for r in rows],
                expected_canonical_count=len(rows), expected_key_sha256=key_hash(rows),
                pages=[dict(page_number=1, generation_id=context['generation_id'],has_more=False,records=rows)])


def fixture(*, richer=False, history_status="Excluded", long_title=None, noop=False):
    docs, raw = admission_fixture()
    if long_title is not None:
        from tests.test_prepare_publication_admission_packet import replace_pubmed_title
        replace_pubmed_title(docs,raw,long_title)
    # A year-only new publication, with no invented month. Change both raw and
    # independently typed fixture evidence before building the admission packet.
    raw['pubmed.xml'] = raw['pubmed.xml'].replace(b'<Month>Oct</Month>', b'')
    part = next(p for p in docs['acquisition']['parts'] if p['source']=='PubMed')
    part.update(bytes=len(raw['pubmed.xml']),sha256=core.bytes_sha(raw['pubmed.xml']))
    from scripts.capture_report_bound_source_union import project_current_pubmed_efetch
    from scripts.publication_xml_metadata import article_metadata
    import xml.etree.ElementTree as ET
    projected=project_current_pubmed_efetch(raw['pubmed.xml'])
    metadata={a.findtext('MedlineCitation/PMID'):core.decode_json(article_metadata(a)['MetadataJSON']) for a in ET.fromstring(raw['pubmed.xml'])}
    for r in docs['typed']['records']:
        if r['source']=='PubMed':r.update(record=projected[r['source_id']],metadata=metadata[r['source_id']])
    docs['typed']['pages'][0]['rows']=copy.deepcopy(docs['typed']['records'])
    s=docs['registry']
    s['items'][0].update(field_5=2026,field_7='2026 Sep',SourceFullTitle='Retained source title differs from human title')
    s['items'][1].update(field_8='unknown')
    # A keyed history row absent from this current source generation remains.
    history=copy.deepcopy(s['items'][1]);history.update(Id=4,field_1='pubmed:99',field_2='PUB:HISTORY',field_17=history_status)
    s['items'].append(history);s['counts']['items']=4;s['list']['ItemCount']=4
    if noop:
        for row in s['items'][:2]:row['field_20']=AS_OF
    if richer:
        from tests.test_prepare_publication_registry_bootstrap import field
        s['fields'].append(field('doi_value','DOI','Text',500))
        for row in s['items']:row['doi_value']='10.1234/retained' if row['Id']==1 else None
        s['counts']['fields']=len(s['fields']);docs['schema']['fields_sha256']=core.sha(s['fields'])
    packet=admission.prepare(docs,raw,expected_hashes=pins(docs),as_of=AS_OF)
    logical={**admission.MAPPING,'CHHHSAffiliatedAuthors':'field_15'}
    if richer:logical['DOI']='doi_value'
    fields={k:dict(internal_name=v,field_id=core.field_named(s,v)['Id'],missing_new='null') for k,v in logical.items()}
    mapping={k:dict(kind='null',reason='fixture:unavailable:'+k) for k in EXPORT_FIELDS}
    for k in ('CanonicalKey','Authors','Journal','PublicationDateRaw','PublicationDatePrecision','PublicationYear','PublicationMonth','PMID','CHHHSAffiliatedAuthors'):
        mapping[k]=dict(kind='registry',logical_field=k)
    if richer:mapping['DOI']=dict(kind='registry',logical_field='DOI')
    mapping['Title']=dict(kind='title',existing='Title',create='SourceFullTitle')
    mapping['SourceSet']=dict(kind='source',labels={'pubmed:':'PubMed','dora:':'DORA'})
    context=dict(generation_id='fixture:consumer-generation',source_snapshot_id='fixture:source-snapshot',
        query_version='fixture:query-v1',model_refresh_correlation='fixture:refresh',
        extraction_contract_sha256='e'*64,data_kind='synthetic',target=copy.deepcopy(packet['target']),
        source_generations=copy.deepcopy(packet['generations']),admission_packet_sha256=packet['packet_sha256'],
        registry_preimage_sha256=core.sha(s))
    contract=dict(kind='publication_consumer_contract_v1',version='fixture:v1',reference='fixture:contract',
        target=packet['target'],generations=packet['generations'],packet_sha256=packet['packet_sha256'],
        registry_sha256=core.sha(s),context=context,reporting_month='2026-09',registry_fields=fields,
        export_fields=mapping,filters=dict(model='all_registry_rows',placeholders='exclude_from_exports',
            excluded_statuses=['Excluded'],canonical_multiplicity='reject'))
    registry=[];model=[];bibliography=[]
    for old in s['items']:
        values={f['InternalName']:copy.deepcopy(old[f['InternalName']]) for f in s['fields']}
        if old['Id'] in (1,2):values['field_20']=AS_OF
        registry.append(dict(row_id='item:'+str(old['Id']),origin='existing',values=values))
    created=next(p for p in packet['proposals'] if p['kind']=='create')
    registry.append(dict(row_id='new:pubmed:2',origin='create',values={admission.MAPPING[k]:v for k,v in created['proposed_values'].items()}))
    for r in registry:
        values={k:r['values'].get(v) for k,v in logical.items()}
        model.append(dict(row_id=r['row_id'],values=values))
        if not values['SourceKey'] or values['ReviewStatus']=='Excluded':continue
        b={k:None for k in EXPORT_FIELDS}
        b.update({k:values[k] for k in ('CanonicalKey','Authors','Journal','PublicationDateRaw','PublicationDatePrecision','PublicationYear','PublicationMonth','PMID','CHHHSAffiliatedAuthors')})
        if richer:b['DOI']=values['DOI']
        b['Title']=values['Title'] if r['origin']=='existing' else values['SourceFullTitle']
        b['SourceSet']='PubMed' if values['SourceKey'].startswith('pubmed:') else 'DORA'
        bibliography.append(b)
    monthly=[r for r in bibliography if r['PublicationMonth']=='2026-09']
    captures=dict(registry=capture(registry,context,'registry'),model=capture(model,context,'model'),
        full=export(bibliography,context,'all'),monthly=export(monthly,context,'month','2026-09'))
    return docs,raw,packet,contract,captures


def consumer_pins(contract,captures):return {'contract':core.sha(contract),**{k:core.sha(v) for k,v in captures.items()}}


def run(f):
    d,r,p,c,cs=f
    return parity.prepare(d,r,p,input_pins=pins(d),packet_pin=p['packet_sha256'],
        contract=c,captures=cs,consumer_pins=consumer_pins(c,cs),as_of=AS_OF)


def reseal(capture):
    rows=[r for p in capture['pages'] for r in p['rows']]
    capture.update(row_count=len(rows),rows_sha256=core.sha(rows))


class ConsumerParityTests(unittest.TestCase):
    def test_complete_connected_journey_preserves_history_human_values_and_uncertainty(self):
        f=fixture();before=copy.deepcopy(f);receipt=run(f)
        self.assertEqual(f,before)
        self.assertEqual(receipt['counts'],dict(registry=5,existing=4,created=1,model=5,
            keyed=4,placeholders=1,excluded=1,historical_keyed=1,full=3,monthly=1,unknown_month=2))
        self.assertFalse(receipt['NativeAcceptance']);self.assertFalse(receipt['write_authorized'])
        self.assertEqual(receipt,run(f))
        self.assertEqual(receipt['status'],'VERIFIED_SUPPLIED_CANDIDATE_PARITY')

    def test_each_independent_consumer_pin_rejects_rebinding(self):
        for name in ('contract','registry','model','full','monthly'):
            f=fixture();d,r,p,c,cs=f;expected=consumer_pins(c,cs)
            (c if name=='contract' else cs[name])['injected']=True
            with self.subTest(name=name),self.assertRaises(ValueError):parity.prepare(d,r,p,input_pins=pins(d),packet_pin=p['packet_sha256'],contract=c,captures=cs,consumer_pins=expected,as_of=AS_OF)

    def test_admission_is_rebuilt_not_trusted_from_self_hash(self):
        f=list(fixture());f[2]['proposals'][0]['protected_values']['Title']='forged'
        f[2]['packet_sha256']=core.sha({k:v for k,v in f[2].items() if k!='packet_sha256'})
        f[3]['packet_sha256']=f[2]['packet_sha256']
        with self.assertRaises(ValueError):run(f)

    def test_raw_or_independently_pinned_input_changes_rejected(self):
        f=list(fixture());d,r,p,c,cs=f;ip=pins(d);r['pubmed.xml']+=b' '
        with self.assertRaises(ValueError):parity.prepare(d,r,p,input_pins=ip,packet_pin=p['packet_sha256'],contract=c,captures=cs,consumer_pins=consumer_pins(c,cs),as_of=AS_OF)

    def test_every_saved_registry_value_is_protected_beyond_selected_model_fields(self):
        for field in ('Title','SourceFullTitle','field_18','field_17','field_19','LinkTitle'):
            f=list(fixture());cs=f[4];cs['registry']['pages'][0]['rows'][0]['values'][field]='drift';reseal(cs['registry'])
            with self.subTest(field=field),self.assertRaises(ValueError):run(f)

    def test_model_protected_and_full_title_drift_fails(self):
        for field in ('Title','SourceFullTitle','ReviewNotes','FirstObservedUTC','ReviewStatus','LastObservedUTC'):
            f=list(fixture());cs=f[4];cs['model']['pages'][0]['rows'][0]['values'][field]='drift';reseal(cs['model'])
            with self.subTest(field=field),self.assertRaises(ValueError):run(f)

    def test_history_placeholder_new_or_excluded_rows_cannot_disappear_from_model(self):
        for index in (2,3,4):
            f=list(fixture());cs=f[4];cs['model']['pages'][0]['rows'].pop(index);reseal(cs['model'])
            with self.subTest(index=index),self.assertRaises(ValueError):run(f)

    def test_duplicate_registry_or_model_rows_rejected_even_with_resealed_counts(self):
        for role in ('registry','model'):
            f=list(fixture());cap=f[4][role];cap['pages'][0]['rows'].append(copy.deepcopy(cap['pages'][0]['rows'][0]));reseal(cap)
            with self.subTest(role=role),self.assertRaises(ValueError):run(f)

    def test_complete_pagination_requires_terminal_empty_cursor_chain_counts_and_no_errors(self):
        for role in ('registry','model'):
            for fault in ('terminal','cursor','count','error','partial','extra_terminal','hash','bool','rows'):
                f=list(fixture());cap=f[4][role]
                if fault=='terminal':cap['pages'].pop()
                elif fault=='cursor':cap['pages'][1]['cursor_before']='other'
                elif fault=='count':cap['row_count']+=1
                elif fault=='error':cap['pages'][0]['error']={}
                elif fault=='partial':cap['partial']=True
                elif fault=='extra_terminal':cap['pages'].append(copy.deepcopy(cap['pages'][1]))
                elif fault=='hash':cap['rows_sha256']='0'*64
                elif fault=='bool':cap['pages'][0]['number']=True
                else:cap['pages'][1]['rows']=[cap['pages'][0]['rows'][0]]
                with self.subTest(role=role,fault=fault),self.assertRaises(ValueError):run(f)

    def test_context_target_schema_generation_and_filter_rebinding_fail(self):
        for fault in ('generation','target','registry','field_id','meaning','alias','missing','filter','contract_extra'):
            f=list(fixture());c=f[3]
            if fault=='generation':c['generations'][0]['generation']='other'
            elif fault=='target':c['target']=dict(c['target'],model_id='00000000-0000-0000-0000-000000000000')
            elif fault=='registry':c['registry_sha256']='0'*64
            elif fault=='field_id':c['registry_fields']['Title']['field_id']='0'*36
            elif fault=='meaning':c['registry_fields']['Title']['internal_name']='field_18'
            elif fault=='alias':c['registry_fields']['Authors']=copy.deepcopy(c['registry_fields']['Title'])
            elif fault=='missing':c['registry_fields'].pop('ReviewNotes')
            elif fault=='filter':c['filters']['excluded_statuses']=[]
            else:c['native_qualified']=True
            with self.subTest(fault=fault),self.assertRaises(ValueError):run(f)

    def test_all_capture_context_fields_are_bound_including_export_generation(self):
        for role in ('registry','model','full','monthly'):
            for field in ('generation_id','source_snapshot_id','query_version','model_refresh_correlation','extraction_contract_sha256','data_kind'):
                f=list(fixture());cs=f[4];ctx=cs[role]['context'] if role in ('registry','model') else cs[role]
                ctx[field]='other'
                with self.subTest(role=role,field=field),self.assertRaises(ValueError):run(f)

    def test_full_export_missing_duplicate_extra_or_metadata_drift_rejected(self):
        for fault in ('missing','extra','duplicate','metadata','human_title','full_title'):
            f=list(fixture());cap=f[4]['full'];rows=cap['pages'][0]['records']
            if fault=='missing':rows.pop()
            elif fault=='extra':rows.append(dict(rows[0],CanonicalKey='PUB:EXTRA'))
            elif fault=='duplicate':rows.append(copy.deepcopy(rows[0]))
            elif fault=='metadata':rows[0]['Authors']='drift'
            elif fault=='human_title':rows[0]['Title']='Retained source title differs from human title'
            else:rows[-1]['Title']='truncated'
            cap.update(expected_canonical_keys=[r['CanonicalKey'] for r in rows],expected_canonical_count=len(rows),expected_key_sha256=key_hash(rows))
            with self.subTest(fault=fault),self.assertRaises(ValueError):run(f)

    def test_unknown_month_cannot_be_invented_and_monthly_cannot_omit_or_change_rows(self):
        for fault in ('unknown','omit','metadata','period','partial'):
            f=list(fixture());cs=f[4]
            if fault=='unknown':cs['full']['pages'][0]['records'][-1]['PublicationMonth']='2026-10'
            elif fault=='omit':cs['monthly']=export([],f[3]['context'],'month','2026-09')
            elif fault=='metadata':cs['monthly']['pages'][0]['records'][0]['Authors']='drift'
            elif fault=='period':cs['monthly']['scope']['reporting_month']='2026-10'
            else:cs['monthly']['pages'][0]['has_more']=True
            with self.subTest(fault=fault),self.assertRaises(ValueError):run(f)

    def test_export_mapping_cannot_suppress_required_metadata_or_replace_human_title(self):
        for field in ('CanonicalKey','Authors','Journal','PublicationYear','PublicationMonth','PublicationDateRaw','PublicationDatePrecision','PMID','Title'):
            f=list(fixture());f[3]['export_fields'][field]=dict(kind='null',reason='fixture:hide')
            with self.subTest(field=field),self.assertRaises(ValueError):run(f)

    def test_absent_required_create_field_fails_when_missing_policy_is_error(self):
        f=list(fixture());f[3]['registry_fields']['ReviewNotes']['missing_new']='error'
        with self.assertRaises(ValueError):run(f)

    def test_explicit_additional_bibliography_field_preserves_real_supplied_values(self):
        f=fixture(richer=True);receipt=run(f)
        self.assertEqual(receipt['counts']['full'],3)
        f[4]['full']['pages'][0]['records'][0]['DOI']=None
        with self.assertRaises(ValueError):run(f)

    def test_unresolved_export_page_continuation_and_implicit_next_links_fail(self):
        for role in ('full','monthly','registry','model'):
            f=fixture();cap=f[4][role]
            if role in ('full','monthly'):cap['pages'][0]['next_link']='fixture:unread-page'
            else:cap['next_links']=None
            with self.subTest(role=role),self.assertRaises(ValueError):run(f)

    def test_cli_private_atomic_output_replay_and_failed_input_preservation(self):
        from unittest.mock import patch
        from contextlib import redirect_stderr
        import io
        import json
        d,r,p,c,cs=fixture()
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve();private=root/'private';private.mkdir()
            docs=dict(inputs=d,files={},pins=pins(d),packet=dict(kind='publication_admission_local_result_v1',result=p),contract=c,captures=cs,consumer_pins=consumer_pins(c,cs))
            for name,raw in r.items():
                path=private/name;path.write_bytes(raw);docs['files'][name]=str(path)
            args=[]
            for name,value in docs.items():
                path=private/(name+'.json');path.write_text(json.dumps(value),encoding='utf-8')
                args.extend(['--'+name.replace('_','-'),str(path)])
            output=private/'result.json';args+=['--output',str(output),'--packet-sha256',p['packet_sha256'],'--as-of',AS_OF]
            with patch.object(parity,'ROOT',root),redirect_stderr(io.StringIO()):
                self.assertEqual(parity.main(args),0)
                original=output.read_bytes()
                self.assertEqual(parity.main(args),2);self.assertEqual(output.read_bytes(),original)
                result=core.decode_json(original)
                self.assertFalse(result['result']['NativeAcceptance'])
                self.assertIn('raw:pubmed.xml',result['source_files_sha256'])
                output.unlink()
                (private/'pubmed.xml').write_bytes(b'changed')
                self.assertEqual(parity.main(args),2);self.assertFalse(output.exists())

    def test_capture_identity_cannot_be_rebound_to_another_target_or_source_generation(self):
        for role in ('registry','model','full','monthly'):
            for field in ('target','source_generations','admission_packet_sha256','registry_preimage_sha256'):
                f=fixture();cap=f[4][role];ctx=cap['context'] if role in ('registry','model') else cap
                ctx[field]='other'
                with self.subTest(role=role,field=field),self.assertRaises(ValueError):run(f)

    def test_contract_context_cannot_claim_different_source_packet_target_or_preimage(self):
        for field in ('target','source_generations','admission_packet_sha256','registry_preimage_sha256'):
            f=fixture();c=f[3];c['context'][field]='other'
            # All consumers repeating a false context must not establish parity.
            for role,cap in f[4].items():
                (cap['context'] if role in ('registry','model') else cap)[field]='other'
            with self.subTest(field=field),self.assertRaises(ValueError):run(f)

    def test_included_history_absent_from_current_batch_remains_in_bibliography(self):
        f=fixture(history_status='Included');receipt=run(f)
        self.assertEqual(receipt['counts']['full'],4)
        self.assertEqual(receipt['counts']['historical_keyed'],1)
        self.assertEqual(receipt['counts']['excluded'],0)
        self.assertEqual(receipt['counts']['unknown_month'],3)

    def test_noop_existing_rows_are_not_given_an_extra_change(self):
        f=fixture(noop=True)
        self.assertEqual(f[2]['counts']['noops'],2)
        self.assertEqual(run(f)['counts']['created'],1)

    def test_new_unicode_full_title_survives_bounded_display_projection(self):
        title='Fictional '+('😀α' * 200)
        f=fixture(long_title=title);receipt=run(f)
        created=f[4]['model']['pages'][0]['rows'][-1]['values']
        self.assertLessEqual(len(created['Title'].encode('utf-16-le'))//2,255)
        self.assertEqual(created['SourceFullTitle'],title)
        self.assertEqual(f[4]['full']['pages'][0]['records'][-1]['Title'],title)
        self.assertEqual(receipt['counts']['full'],3)

    def test_ambiguous_mapping_and_fabricated_optional_facts_are_rejected(self):
        for fault in ('missing_binding','wrong_meaning','same_field','literal_fact','unknown_rule'):
            f=fixture(richer=True);c=f[3]
            if fault=='missing_binding':c['registry_fields'].pop('DOI')
            elif fault=='wrong_meaning':c['registry_fields']['DOI']['internal_name']='field_18'
            elif fault=='same_field':c['registry_fields']['DOI']=copy.deepcopy(c['registry_fields']['PMID'])
            elif fault=='literal_fact':c['export_fields']['AttributionStatus']=dict(kind='literal',value='Confirmed')
            else:c['export_fields']['DOI']=dict(kind='execute',code='arbitrary')
            with self.subTest(fault=fault),self.assertRaises(ValueError):run(f)

    def test_populated_optional_bibliography_values_cannot_be_declared_unavailable(self):
        for remove_binding in (False,True):
            f=fixture(richer=True);c=f[3]
            c['export_fields']['DOI']=dict(kind='null',reason='fixture:hide-populated')
            if remove_binding:
                c['registry_fields'].pop('DOI')
                for row in f[4]['model']['pages'][0]['rows']:row['values'].pop('DOI')
                reseal(f[4]['model'])
            for row in f[4]['full']['pages'][0]['records']:row['DOI']=None
            with self.subTest(remove_binding=remove_binding),self.assertRaises(ValueError):run(f)

    def test_receipt_reverification_rejects_changed_counts_or_scope(self):
        f=fixture();receipt=run(f);d,r,p,c,cs=f
        parity.verify(receipt,d,r,p,input_pins=pins(d),packet_pin=p['packet_sha256'],contract=c,captures=cs,consumer_pins=consumer_pins(c,cs),as_of=AS_OF,receipt_pin=receipt['receipt_sha256'])
        receipt['counts']['full']+=1
        with self.assertRaises(ValueError):parity.verify(receipt,d,r,p,input_pins=pins(d),packet_pin=p['packet_sha256'],contract=c,captures=cs,consumer_pins=consumer_pins(c,cs),as_of=AS_OF,receipt_pin=receipt['receipt_sha256'])


if __name__=='__main__':unittest.main()
