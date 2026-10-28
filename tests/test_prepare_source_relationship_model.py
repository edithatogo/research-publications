import base64,copy,hashlib,json,unittest
from scripts.prepare_source_relationship_model import prepare,project_rows,TABLE,COLUMNS,document_hash,fingerprint

def part(path,text):return dict(path=path,payload=base64.b64encode(text.encode()).decode(),payloadType='InlineBase64')
def fixture():
    document={'definition':{'format':'TMDL','parts':[
        part('definition/model.tmdl','model Model\nref table Publication\n'),part('definition/relationships.tmdl',''),
        part('definition/expressions.tmdl','expression ExistingCandidateRows = ExistingQualifiedProducer\n'),
        part('definition/tables/Publication.tmdl','table Publication\n\tcolumn CanonicalKey\n\t\tdataType: string\n\tcolumn ReviewStatus\n\t\tdataType: string\n\tpartition Publication = m\n\t\tmode: import\n\t\tsource = ExistingAcceptedSource'),
        part('definition/tables/ExistingReview.tmdl','Reviewed and rejected records preserved'),part('unknown.txt','preserve')]}}
    publications=[dict(CanonicalKey='pub:1',ReviewStatus='Protected human decision')]
    rows=[dict(EvidenceKey='source|authorship|a',RelationshipKind='authorship',SourceWorkID='pubmed:13',PublicationPMID='13',PublicationDOI='',
        FromKey='pmid:13',ToKey='source-author:1',CanonicalKey='pub:1',CanonicalMatchCount=1,IdentityQualified=False,CanonicalAdmission=False,MutationAuthorized=False,
        CandidateEligible=True,SourceRetracted=None,ReviewState='Not reviewed',AuthenticationState='Not authenticated',GenerationID='fixture-source-generation',
        CanonicalSnapshotID='fixture-canonical',SourceSnapshotID='fixture-pubmed',SourceVersion='fixture-retained-version',RawSHA256='',StructuredMetadataSHA256='a'*64,
        SourcePaths=['/MedlineCitation/Article/AuthorList/Author/0'],ObservedUTC=None)]
    context=dict(projection_id='fixture-projection',producer_expression='ExistingCandidateRows',complete=True,next_links=[],
        publication_fields=['CanonicalKey','ReviewStatus'],publication_count=1,row_count=1,rows_sha256=fingerprint(rows),publications_sha256=fingerprint(publications),
        canonical_keys_sha256=fingerprint(['pub:1']),providers={rows[0]['EvidenceKey']:'PubMed'},eligibility={rows[0]['EvidenceKey']:True},
        model_sha256=document_hash(document),producer_expression_part_sha256=hashlib.sha256(base64.b64decode(document['definition']['parts'][2]['payload'])).hexdigest(),capabilities={})
    typed=project_rows(rows,publications,context)
    for name in ('native_typed_input','upstream_byte_hash_verification','canonical_source_parity'):
        context['capabilities'][name]=dict(status='qualified',evidence_ref='fictional://'+name,model_sha256=document_hash(document),typed_rows_sha256=fingerprint(typed),producer_expression_part_sha256=context['producer_expression_part_sha256'])
    args=dict(document=document,expected_sha256=document_hash(document),expected_parts=[p['path'] for p in document['definition']['parts']],rows=rows,publications=publications,producer_context=context,producer_context_sha256=fingerprint(context))
    return args

class ModelPreservationTests(unittest.TestCase):
    def test_preserves_source_review_and_unknown_parts_and_rejects_reapplication(self):
        args=fixture();before=copy.deepcopy(args);result=prepare(**args)
        self.assertEqual(args,before);self.assertEqual(result['status'],'prepared');self.assertFalse(result['nativeSaveSubmitted'])
        original={p['path']:p for p in args['document']['definition']['parts']};after={p['path']:p for p in result['modelDefinition']['definition']['parts']}
        for path in ('definition/model.tmdl','definition/relationships.tmdl'):
            self.assertTrue(base64.b64decode(after[path]['payload']).startswith(base64.b64decode(original[path]['payload'])))
        for path in original:
            if path not in {'definition/model.tmdl','definition/relationships.tmdl'}:self.assertEqual(original[path],after[path])
        table=base64.b64decode(after['definition/tables/'+TABLE+'.tmdl']['payload']).decode()
        self.assertNotIn('LOWER(TRIM(',table);self.assertNotIn('+ 0',table);self.assertIn('BLANK()',table)
        rel=base64.b64decode(after['definition/relationships.tmdl']['payload']).decode();self.assertIn('oneDirection',rel);self.assertNotIn('bothDirections',rel)
        args['document']=result['modelDefinition'];args['expected_sha256']=document_hash(args['document']);args['expected_parts']=list(after)
        with self.assertRaises(ValueError):prepare(**args)

    def test_unqualified_native_capabilities_return_blocked_without_model_candidate(self):
        args=fixture();args['producer_context']['capabilities']={};args['producer_context_sha256']=fingerprint(args['producer_context'])
        result=prepare(**args);self.assertEqual(result['status'],'blocked');self.assertIsNone(result['modelDefinition']);self.assertEqual(len(result['blockers']),3)

    def test_generation_types_provider_and_human_state_are_not_inferred(self):
        for mode in ('context-pin','model-pin','field-inventory','provider','eligible','review','raw-hash','canonical','duplicate','count','partial'):
            args=fixture();ctx=args['producer_context'];r=args['rows'][0]
            if mode=='context-pin':args['producer_context_sha256']='0'*64
            elif mode=='model-pin':args['expected_sha256']='0'*64
            elif mode=='field-inventory':ctx['publication_fields']=['CanonicalKey']
            elif mode=='provider':ctx['providers']={}
            elif mode=='eligible':ctx['eligibility'][r['EvidenceKey']]=False
            elif mode=='review':r['ReviewState']='Human reviewed'
            elif mode=='raw-hash':r['StructuredMetadataSHA256']=''
            elif mode=='canonical':r['CanonicalKey']='pub:other'
            elif mode=='duplicate':args['rows'].append(copy.deepcopy(r));ctx['row_count']=2
            elif mode=='count':ctx['row_count']=True
            else:ctx['partial']=True
            if mode!='context-pin':
                if mode in ('review','raw-hash','canonical','duplicate'):ctx['rows_sha256']=fingerprint(args['rows'])
                args['producer_context_sha256']=fingerprint(ctx)
            with self.subTest(mode=mode),self.assertRaises(ValueError):prepare(**args)

    def test_retraction_unknowns_occurrences_and_versions_survive_typed_projection(self):
        args=fixture();r=args['rows'][0];r['CandidateEligible']=False;r['SourceRetracted']=True;r['SourcePaths'].append('/another/occurrence')
        ctx=args['producer_context'];ctx['eligibility'][r['EvidenceKey']]=False;ctx['rows_sha256']=fingerprint(args['rows'])
        rows=project_rows(args['rows'],args['publications'],ctx)
        self.assertTrue(rows[0]['SourceRetracted']);self.assertIsNone(rows[0]['ObservedUTC']);self.assertEqual(len(json.loads(rows[0]['SourcePathsJSON'])),2)
        self.assertEqual(json.loads(rows[0]['RawAssertionJSON']),r);self.assertEqual(len({x['CanonicalKey'] for x in rows}),1)

    def test_m_templates_are_typed_consumers_not_unqualified_acquisition_or_crypto(self):
        from pathlib import Path
        root=Path(__file__).resolve().parents[1]
        core=(root/'config/source-relationship-evidence.m').read_text();pub=(root/'config/pubmed-relationship-evidence.m').read_text()
        self.assertIn('CanonicalValid',core);self.assertIn('Expected[RowCount]',core);self.assertIn('SourceRetracted',core)
        self.assertIn('StructuredMetadataSHA256',pub);self.assertIn('RawSHA256',pub)
        for forbidden in ('Web.Contents','SharePoint.Contents','Binary.Hash','Crypto.','RetainedSourceObservations('):self.assertNotIn(forbidden,core+pub)

    def test_missing_typed_producer_is_a_named_blocker_not_an_invented_source(self):
        args=fixture();part=args['document']['definition']['parts'][2];part['payload']=base64.b64encode(b'expression OtherSource = ExistingAcceptedSource\n').decode()
        args['expected_sha256']=document_hash(args['document']);ctx=args['producer_context'];ctx['model_sha256']=args['expected_sha256'];ctx['producer_expression_part_sha256']=hashlib.sha256(base64.b64decode(part['payload'])).hexdigest();ctx['capabilities']={};args['producer_context_sha256']=fingerprint(ctx)
        result=prepare(**args);self.assertEqual(result['status'],'blocked');self.assertIn('existing_typed_producer_expression',result['blockers']);self.assertIsNone(result['modelDefinition'])

    def test_typed_m_interface_and_candidate_bridge_count_share_one_contract(self):
        import re
        from scripts.prepare_source_relationship_model import ROOT,TEXT,LOGICAL
        core=(ROOT/'config/source-relationship-evidence.m').read_text()
        text=json.loads('['+re.search(r'TextFields = \{([^}]+)\}',core)[1]+']')
        logical=json.loads('['+re.search(r'LogicalFields = \{([^}]+)\}',core)[1]+']')
        self.assertEqual(text,TEXT);self.assertEqual(logical,LOGICAL);self.assertEqual(set(text+logical+['CanonicalMatchCount']),set(COLUMNS))
        args=fixture();row=copy.deepcopy(args['rows'][0]);row.update(EvidenceKey='source|study|b',RelationshipKind='publication_study_reference',ToKey='clinicaltrials.gov:NCT00000001')
        args['rows'].append(row);ctx=args['producer_context'];ctx.update(row_count=2,rows_sha256=fingerprint(args['rows']));ctx['providers'][row['EvidenceKey']]='PubMed';ctx['eligibility'][row['EvidenceKey']]=True
        projected=project_rows(args['rows'],args['publications'],ctx)
        self.assertEqual(len(projected),2);self.assertEqual(len({r['CanonicalKey'] for r in projected}),1)
        self.assertTrue(all(not r['CanonicalAdmission'] and not r['IdentityQualified'] for r in projected))

    def test_casefold_equivalent_canonical_keys_are_rejected_without_rekeying(self):
        args=fixture();pubs=args['publications'];pubs.append(dict(pubs[0],CanonicalKey='PUB:1'))
        ctx=args['producer_context'];ctx.update(publication_count=2,publications_sha256=fingerprint(pubs),canonical_keys_sha256=fingerprint(sorted(p['CanonicalKey'] for p in pubs)))
        before=copy.deepcopy(pubs)
        with self.assertRaises(ValueError):project_rows(args['rows'],pubs,ctx)
        self.assertEqual(pubs,before)
        args=fixture();args['publications'][0]['CanonicalKey']='Pub:Literal';args['rows'][0]['CanonicalKey']='Pub:Literal'
        ctx=args['producer_context'];ctx.update(publications_sha256=fingerprint(args['publications']),rows_sha256=fingerprint(args['rows']),canonical_keys_sha256=fingerprint(['Pub:Literal']))
        projected=project_rows(args['rows'],args['publications'],ctx)
        self.assertEqual(projected[0]['CanonicalKey'],'Pub:Literal')

    def test_new_provider_consumers_are_not_implicitly_connected(self):
        for provider in ('NIH RePORTER','DataCite','Protocol','Unknown'):
            args=fixture();ctx=args['producer_context'];ctx['providers'][args['rows'][0]['EvidenceKey']]=provider
            with self.subTest(provider=provider),self.assertRaises(ValueError):project_rows(args['rows'],args['publications'],ctx)
