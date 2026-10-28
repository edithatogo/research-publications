# SPDX-License-Identifier: Apache-2.0
import copy
import json
from pathlib import Path
import tempfile
import unittest
from scripts import prepare_publication_collector_admission_inputs as adapter
from scripts import prepare_publication_admission_packet as admission
from scripts import prepare_publication_registry_bootstrap as core
from scripts.reconcile_pubmed_source_cycle import prepare_offline_typed_candidate
from scripts.publication_source_metadata_contract import reconstruct_metadata_rows
from scripts.publication_retained_cycle import retain
from tests.test_pubmed_offline_typed_candidate import inputs as pubmed_inputs
from tests.test_prepare_publication_admission_packet import literal_dora_fixture,AS_OF
from tests import test_prepare_dora_metadata_cycle as dora_fixture


def encoded(value):return (core.canonical(value)+'\n').encode()


def bridge_for(source,artifacts,bindings,content_hash,raw_reference,role):
    commit=core.decode_json(artifacts['commit']);g=next(g for g in bindings['generations'] if g['source']==source)
    return dict(kind='publication_collector_generation_bridge_v1',complete=True,source=source,reference='fixture:independent-generation-authority',artifact_inventory_sha256=core.sha(adapter.inventory(artifacts)),binding_inventory_sha256=core.sha(bindings),generation=copy.deepcopy(g),raw_generation_reference=raw_reference,candidate_generation_sha256=content_hash,commit_sha256=core.bytes_sha(artifacts['commit']),binding_role=role)


def setup_artifacts(*,http=False):
    docs,_=literal_dora_fixture(http_own_uri=http);bindings=docs['bindings']
    args=list(pubmed_inputs());args[0].update(run='fixture:raw-run',downstream_selection_applied=False,fidelity='saved HTTP XML text; not wire bytes')
    candidate,comparison,differences=prepare_offline_typed_candidate(*args)
    pub=dict(manifest=encoded(args[0]),readback=encoded(args[1]),commit=encoded(args[2]),raw_files=args[3],typed_receipt=encoded(args[4]),source_pages=args[5],typed_files=args[6],candidate=encoded(candidate),comparison=encoded(comparison),differences=encoded(differences))
    source_names=('manifest','readback','commit','source_pages','typed_receipt');receipt=dict(counts=comparison['counts'],input_paths={n:'fixture:original/'+n for n in source_names},input_sha256={n:core.bytes_sha(pub[n]) for n in source_names},native_invoked=False,output_path='fixture:original-output',output_sha256={label:core.bytes_sha(pub[name]) for name,label in [('candidate','candidate.json'),('comparison','comparison.json'),('differences','differences-private.json')]});pub['receipt']=encoded(receipt)
    for g in bindings['generations']:
        if g['source']=='PubMed':g.update(generation=candidate['generation_sha256'],request_id='fixture:offline-candidate-consumer-request')
    case=dora_fixture.DoraMetadataCycleTests();case.setUp();url=admission.OFFICIAL+'1/2';metadata=dora_fixture.fields(url)
    metadata.extend([dict(Field='dc.contributor.author',Value='Author',Language='en',Unknown={'kept':True}),dict(Field='unknown.term',Value='literal',Language='fr')])
    if http:metadata[0]['Value']='http://'+url[8:]
    pages,validation=case.inputs(metadata=[metadata]);g=next(g for g in bindings['generations'] if g['source']=='DORA')
    key='DORA:'+url
    for source in pages['sources'].values():
        for page in source['pages']:
            for row in page['body']['results'][0]['tables'][0]['rows']:
                row['[DORAKey]']=key
                if '[DORAURL]' in row:row['[DORAURL]']=url
    values=validation['body']['results'][0]['tables'][0]['rows'][0];values['[CurrentKeysJSON]']=json.dumps([key],separators=(',',':'))
    # For this single-record fixture both terminal query cursors must use the
    # literal verified URL, including when the raw own URI is historical HTTP.
    from scripts.publication_source_metadata_contract import page_query
    for table,source in pages['sources'].items():
        cursor=[key] if table=='DoraPublications' else [key,0];query=page_query(table,cursor);source['pages'][1].update(query=query,query_sha256=core.bytes_sha(query.encode()))
    native=copy.deepcopy(case.generation);native.update(generation=g['generation'],modelId=g['model_id'],refreshRequestId=g['request_id'],refreshCompletedAtUTC=g['observed_at_utc'])
    pages.update(model_id=g['model_id'],request_id=g['request_id'],generation=g['generation'],latest_request_before=g['request_id'],latest_request_after=g['request_id']);validation.update(model_id=g['model_id'],request_id=g['request_id'])
    chunks=pages['sources']['DoraMetadataChunks']['pages'][0]['body']['results'][0]['tables'][0]['rows'];documents,payloads,characters=reconstruct_metadata_rows(chunks,'DORAKey')
    commit=dict(SchemaVersion=1,Status='committed',Generation=g['generation'],ModelID=g['model_id'],RefreshRequestID=g['request_id'],RefreshCompletedAtUTC=g['observed_at_utc'],Sources=[dict(Source='DORA',MetadataProfile='dora_complete_metadata_v1',ExpectedKeys=[key],ExpectedRecords=1)],SourceExtraction=dict(Generation=g['generation'],ModelID=g['model_id'],RefreshRequestID=g['request_id'],MetadataTerminalPageVerified=True,PublicationTerminalPageVerified=True,MetadataPayloadSHA256=core.sha(payloads),MetadataPayloadCharacters=characters,MetadataChunkCount=len(chunks),PublicationKeySHA256=core.sha([key]),MetadataKeySHA256=core.sha([key])))
    dora={name:encoded(value) for name,value in dict(pages=pages,generation=native,validation=validation,commit=commit).items()}
    pub_bridge=bridge_for('PubMed',pub,bindings,candidate['generation_sha256'],'fixture:raw-run','offline_candidate_for_consumer_validation');dora_bridge=bridge_for('DORA',dora,bindings,core.sha(payloads),g['generation'],'retained_union_candidate_for_consumer_validation')
    return docs,pub,pub_bridge,dora,dora_bridge


def adapt_pub(pub,bridge,docs):return adapter.adapt_pubmed(pub,bridge,docs['bindings'],artifact_sha256=core.sha(adapter.inventory(pub)),bridge_sha256=core.sha(bridge),bindings_sha256=core.sha(docs['bindings']),page_records=1)


def adapt_dora(dora,bridge,docs):return adapter.adapt_dora(dora,bridge,docs['bindings'],artifact_sha256=core.sha(adapter.inventory(dora)),bridge_sha256=core.sha(bridge),bindings_sha256=core.sha(docs['bindings']),state=docs['state'],state_sha256=core.sha(docs['state']),representation_profile=docs['schema']['dora_representation_profile'],profile_sha256=core.sha(docs['schema']['dora_representation_profile']),page_records=1)


class CollectorAdapterTests(unittest.TestCase):
    def test_pubmed_original_receipt_full_rebuild_and_same_raw_bytes(self):
        docs,pub,bridge,_,_=setup_artifacts();original=copy.deepcopy((docs,pub,bridge));result=adapt_pub(pub,bridge,docs)
        self.assertEqual(result['status'],'PREPARED_LOCAL_INPUTS');self.assertEqual(result['files'],pub['raw_files']);self.assertEqual(len(result['typed']['records']),2);self.assertEqual(result['typed']['pages'][-1]['rows'],[]);self.assertFalse(result['native_admission_accepted']);self.assertEqual((docs,pub,bridge),original)
        self.assertIn('Unknown',core.canonical(result['typed']['records'][0]['metadata']));self.assertTrue(result['provenance']['richer_candidate_and_author_evidence_retained'])

    def test_url_union_preserves_literal_http_duplicate_metadata_language_and_dates(self):
        docs,_,_,dora,bridge=setup_artifacts(http=True);original=copy.deepcopy((docs,dora));result=adapt_dora(dora,bridge,docs);row=result['typed']['records'][0]
        self.assertEqual(row['source_id'],'DORA:'+admission.OFFICIAL+'1/2');self.assertEqual(row['metadata'][0]['Value'],'http://'+admission.OFFICIAL[8:]+'1/2');self.assertEqual(row['record']['PublicationDateRaw'],'2020')
        self.assertEqual(sum(n['Field']=='dc.contributor.author' for n in row['metadata']),2);self.assertIn(dict(Field='unknown.term',Value='literal',Language='fr'),row['metadata']);self.assertEqual((docs,dora),original)

    def test_current_pubmed_cannot_inherit_prior_native_generation_or_request(self):
        for field in ('generation','request_id'):
            docs,pub,bridge,_,_=setup_artifacts();old=core.decode_json(pub['commit']);g=next(g for g in docs['bindings']['generations'] if g['source']=='PubMed');g[field]=old['Generation' if field=='generation' else 'RefreshRequestID'];bridge['generation']=copy.deepcopy(g);bridge['binding_inventory_sha256']=core.sha(docs['bindings'])
            with self.subTest(field=field),self.assertRaises(ValueError):adapt_pub(pub,bridge,docs)

    def test_external_artifact_and_bridge_pins_are_required(self):
        docs,pub,bridge,_,_=setup_artifacts();expected=core.sha(adapter.inventory(pub));pub['raw_files']['raw.xml']+=b' '
        with self.assertRaises(ValueError):adapter.adapt_pubmed(pub,bridge,docs['bindings'],artifact_sha256=expected,bridge_sha256=core.sha(bridge),bindings_sha256=core.sha(docs['bindings']),page_records=1)
        docs,pub,bridge,_,_=setup_artifacts();pin=core.sha(bridge);bridge['reference']='different'
        with self.assertRaises(ValueError):adapter.adapt_pubmed(pub,bridge,docs['bindings'],artifact_sha256=core.sha(adapter.inventory(pub)),bridge_sha256=pin,bindings_sha256=core.sha(docs['bindings']),page_records=1)

    def test_saved_candidate_comparison_receipt_or_file_substitution_fails(self):
        for role in ('candidate','comparison','receipt','typed_files'):
            docs,pub,bridge,_,_=setup_artifacts()
            if role=='typed_files':pub[role][next(iter(pub[role]))]+=b' '
            else:
                value=core.decode_json(pub[role]);value['changed']='not original';pub[role]=encoded(value)
            bridge['artifact_inventory_sha256']=core.sha(adapter.inventory(pub))
            with self.subTest(role=role),self.assertRaises(ValueError):adapt_pub(pub,bridge,docs)

    def test_books_and_html_are_retained_blocked_without_partial_projection(self):
        docs,pub,bridge,_,_=setup_artifacts();pub['raw_files']['raw.xml']=b'<PubmedArticleSet><PubmedBookArticle><BookDocument><PMID>9</PMID></BookDocument></PubmedBookArticle></PubmedArticleSet>';proofs=adapter.inventory(pub);result=adapt_pub(pub,bridge,docs)
        self.assertEqual(result['status'],'BLOCKED_RETAINED_INPUT');self.assertEqual(result['files'],{});self.assertEqual(result['provenance']['original_artifacts'],proofs)
        html=dict(manifest=encoded(dict(format='rims-dora-publication-raw-commit-v1',complete=True)),record_files={'full.html':b'<table>retain all</table>'});result=adapter.adapt_dora(html,{},docs['bindings'],artifact_sha256=core.sha(adapter.inventory(html)),bridge_sha256='0'*64,bindings_sha256=core.sha(docs['bindings']),state=docs['state'],state_sha256=core.sha(docs['state']),representation_profile=docs['schema']['dora_representation_profile'],profile_sha256=core.sha(docs['schema']['dora_representation_profile']),page_records=1)
        self.assertEqual(result['status'],'BLOCKED_RETAINED_INPUT');self.assertIn('HTML',result['blockers'][0]);self.assertEqual(result['files'],{})

    def test_union_partial_chunks_hashes_generation_and_parity_fail_closed(self):
        for fault in ('terminal','chunk','marker_hash','generation','parity'):
            docs,_,_,dora,bridge=setup_artifacts();pages=core.decode_json(dora['pages'])
            if fault=='terminal':pages['sources']['DoraMetadataChunks']['pages'].pop()
            elif fault=='chunk':pages['sources']['DoraMetadataChunks']['pages'][0]['body']['results'][0]['tables'][0]['rows'][0]['[ChunkCount]']=2
            elif fault=='marker_hash':
                marker=core.decode_json(dora['commit']);marker['SourceExtraction']['MetadataPayloadSHA256']='0'*64;dora['commit']=encoded(marker)
            elif fault=='generation':pages['latest_request_after']='other'
            else:pages['sources']['DoraPublications']['pages'][0]['body']['results'][0]['tables'][0]['rows'][0]['[Title]']='contradictory'
            dora['pages']=encoded(pages);bridge['artifact_inventory_sha256']=core.sha(adapter.inventory(dora));bridge['commit_sha256']=core.bytes_sha(dora['commit'])
            with self.subTest(fault=fault),self.assertRaises(ValueError):adapt_dora(dora,bridge,docs)

    def test_representation_authority_and_prior_state_are_independently_pinned(self):
        docs,_,_,dora,bridge=setup_artifacts();profile=copy.deepcopy(docs['schema']['dora_representation_profile']);profile['reference']='different'
        with self.assertRaises(ValueError):adapter.adapt_dora(dora,bridge,docs['bindings'],artifact_sha256=core.sha(adapter.inventory(dora)),bridge_sha256=core.sha(bridge),bindings_sha256=core.sha(docs['bindings']),state=docs['state'],state_sha256=core.sha(docs['state']),representation_profile=profile,profile_sha256=core.sha(docs['schema']['dora_representation_profile']),page_records=1)

    def test_complete_combination_uses_external_values_and_downstream_feed(self):
        from tests.test_prepare_publication_guarded_writer import declarations,CLOCK
        from scripts import prepare_publication_writer_feed as feed
        from scripts import prepare_publication_guarded_writer as writer
        docs,pub,pb,dora,db=setup_artifacts(http=True);results={'PubMed':adapt_pub(pub,pb,docs),'DORA':adapt_dora(dora,db,docs)};external={k:docs[k] for k in ('registry','schema','writer','bindings','state','ledger')};original=copy.deepcopy(external)
        external_pins={k:core.sha(v) for k,v in {**external,'policy':admission.load_policy(),'reference':admission.load_reference()}.items()};combined=adapter.combine(results,external,result_pins={s:r['result_sha256'] for s,r in results.items()},external_pins=external_pins,as_of=AS_OF,page_records=1)
        self.assertEqual(external,original);self.assertFalse(combined['packet']['native_acceptance']);self.assertEqual(combined['packet']['counts']['source_records'],3)
        packet=combined['packet'];m,parts=feed.build(combined['inputs'],combined['files'],packet,input_pins=combined['input_pins'],packet_pin=packet['packet_sha256'],as_of=AS_OF,max_part_records=1,max_part_bytes=80000,max_manifest_bytes=1000000);profiles,profile_pins=declarations(m,docs['writer']);transport=writer.MemoryTransport(docs['registry']['items'],[CLOCK]*3)
        result=writer.simulate(docs['writer'],m,parts,profiles,transport,expected_writer_sha256=core.sha(docs['writer']),expected_manifest_sha256=m['manifest_sha256'],profile_pins=profile_pins);self.assertEqual(result['status'],'SIMULATED_COMPLETE');self.assertFalse(result['native_runtime_verified'])

    def test_blocked_or_missing_source_cannot_be_silently_dropped(self):
        docs,pub,pb,_,_=setup_artifacts();result=adapt_pub(pub,pb,docs);external={k:docs[k] for k in ('registry','schema','writer','bindings','state','ledger')};p={k:core.sha(v) for k,v in {**external,'policy':admission.load_policy(),'reference':admission.load_reference()}.items()}
        with self.assertRaises(ValueError):adapter.combine({'PubMed':result},external,result_pins={'PubMed':result['result_sha256']},external_pins=p,as_of=AS_OF,page_records=1)

    def test_literal_prior_history_and_unknown_metadata_are_not_rekeyed(self):
        docs,_,_,dora,bridge=setup_artifacts();url=admission.OFFICIAL+'1/2';metadata=dora_fixture.fields(url);docs['state']=retain(docs['state'],[('DORA:'+url,dora_fixture.record(metadata))],generation='prior',observed_at='2020-01-01T00:00:00Z',source='DORA',complete=True);before=copy.deepcopy(docs['state']);result=adapt_dora(dora,bridge,docs)
        self.assertEqual(docs['state'],before);self.assertEqual(result['typed']['records'][0]['SourceKey'],'dora:'+url)

    def test_cli_exclusive_same_read_evidence_and_direct_minus_s(self):
        import subprocess,sys,contextlib,io
        docs,pub,bridge,_,_=setup_artifacts();root=Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory(prefix='collector-adapter-test-',dir=root/'private') as directory,contextlib.redirect_stderr(io.StringIO()):
            private=Path(directory);paths={}
            for role,value in pub.items():
                if isinstance(value,bytes):path=private/(role+'.json');path.write_bytes(value);paths[role]=str(path)
                else:
                    paths[role]={}
                    for i,(name,raw) in enumerate(value.items()):path=private/(role+str(i)+'.bin');path.write_bytes(raw);paths[role][name]=str(path)
            request=dict(source='PubMed',artifacts=paths,bridge=bridge,bindings=docs['bindings'],artifact_sha256=core.sha(adapter.inventory(pub)),bridge_sha256=core.sha(bridge),bindings_sha256=core.sha(docs['bindings']),page_records=1);req=private/'request.json';req.write_bytes(encoded(request));out=private/'result.json';args=['--request',str(req),'--output',str(out)]
            run=subprocess.run([sys.executable,'-S',str(root/'scripts/prepare_publication_collector_admission_inputs.py'),*args],cwd=root,capture_output=True,text=True,timeout=20);self.assertEqual(run.returncode,0,run.stderr);raw=out.read_bytes();result=json.loads(raw);self.assertEqual(result['source_files_sha256']['manifest'],core.bytes_sha(pub['manifest']));self.assertEqual(result['result']['status'],'PREPARED_LOCAL_INPUTS')
            self.assertEqual(adapter.main(args),2);self.assertEqual(out.read_bytes(),raw)

    def test_malformed_documents_and_duplicate_json_fail_without_output(self):
        for fault in ('document','duplicate','typed_rows'):
            docs,pub,bridge,_,_=setup_artifacts()
            if fault=='document':pub['readback']=b'[]'
            elif fault=='duplicate':pub['manifest']=b'{"complete":true,"complete":false}'
            else:pub['typed_files'][next(iter(pub['typed_files']))]=b'{}'
            bridge['artifact_inventory_sha256']=core.sha(adapter.inventory(pub))
            with self.subTest(fault=fault),self.assertRaises(ValueError):adapt_pub(pub,bridge,docs)

    def test_combiner_rejects_changed_external_schema_or_claimed_authority(self):
        for fault in ('external','authority','representation'):
            docs,pub,pb,dora,db=setup_artifacts();results={'PubMed':adapt_pub(pub,pb,docs),'DORA':adapt_dora(dora,db,docs)};external={k:copy.deepcopy(docs[k]) for k in ('registry','schema','writer','bindings','state','ledger')};p={k:core.sha(v) for k,v in {**external,'policy':admission.load_policy(),'reference':admission.load_reference()}.items()}
            if fault=='external':external['registry']['items'][0]['field_18']='changed'
            elif fault=='authority':results['PubMed']['native_admission_accepted']=True;results['PubMed']['result_sha256']=adapter.result_hash(results['PubMed'])
            else:external['schema']['dora_representation_profile']['reference']='different';p['schema']=core.sha(external['schema'])
            with self.subTest(fault=fault),self.assertRaises(ValueError):adapter.combine(results,external,result_pins={s:r['result_sha256'] for s,r in results.items()},external_pins=p,as_of=AS_OF,page_records=1)

    def test_committed_extraction_lineage_and_terminal_proofs_cannot_contradict_pages(self):
        for field,value in (('Generation','other'),('ModelID','other'),('RefreshRequestID','other'),('MetadataTerminalPageVerified',False),('PublicationTerminalPageVerified',1)):
            docs,_,_,dora,bridge=setup_artifacts();commit=core.decode_json(dora['commit']);commit['SourceExtraction'][field]=value;dora['commit']=encoded(commit);bridge['commit_sha256']=core.bytes_sha(dora['commit']);bridge['artifact_inventory_sha256']=core.sha(adapter.inventory(dora))
            with self.subTest(field=field),self.assertRaises(ValueError):adapt_dora(dora,bridge,docs)

    def test_combined_retention_keeps_literal_prior_version_prefix_and_source_dates(self):
        docs,pub,pb,dora,db=setup_artifacts(http=True);url=admission.OFFICIAL+'1/2';docs['state']=retain(docs['state'],[('DORA:'+url,dora_fixture.record(dora_fixture.fields(url)))],generation='prior-literal',observed_at='2020-01-01T00:00:00Z',source='DORA',complete=True);before=copy.deepcopy(docs['state'])
        results={'PubMed':adapt_pub(pub,pb,docs),'DORA':adapt_dora(dora,db,docs)};external={k:docs[k] for k in ('registry','schema','writer','bindings','state','ledger')};p={k:core.sha(v) for k,v in {**external,'policy':admission.load_policy(),'reference':admission.load_reference()}.items()};combined=adapter.combine(results,external,result_pins={s:r['result_sha256'] for s,r in results.items()},external_pins=p,as_of=AS_OF,page_records=1)
        state=combined['packet']['retained_state_candidate'];self.assertEqual(state['versions'][:len(before['versions'])],before['versions']);self.assertIn('dora:'+url,state['latest']);self.assertNotIn('dora:1/2',state['latest']);self.assertEqual(docs['state'],before)
