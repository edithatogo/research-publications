import copy
import unittest
from scripts.award_identifier_crosswalks import qualify_award_alias
from scripts.source_relationship_evidence import fingerprint


class AwardIdentifierCrosswalkTests(unittest.TestCase):
    authority = {'ror': 'https://ror.org/fixture', 'namespace': 'fixture', 'complete':True,
                 'fundref_dois':['10.13039/1'],'evidence_ref':'fixture://independent-authority','authority_raw_sha256':'a'*64}

    def record(self, number='123', record_id='1'):
        return {'type': 'grant', 'id': record_id,
                'purl': 'https://purl.org/au-research/grants/fixture/' + number,
                'identifiers': [number]}

    def qualify(self, records, ror='https://ror.org/fixture'):
        return qualify_award_alias({'funder_award_id': '123'}, ror,
                                   self.authority, records, authority_sha256=fingerprint(self.authority))

    def test_exact_namespace_and_identifier_admitted(self):
        self.assertEqual(self.qualify([self.record()])['state'], 'source_supported_alias')

    def test_number_collision_different_funder_rejected(self):
        self.assertEqual(self.qualify([self.record()], 'https://ror.org/other')['state'],
                         'unqualified_funder_namespace')

    def test_prefix_variants_and_title_similarity_do_not_establish_alias(self):
        record = self.record('GNT123')
        record['title'] = 'Same title'
        self.assertEqual(self.qualify([record])['state'], 'no_exact_identifier')

    def test_two_distinct_records_are_ambiguous(self):
        self.assertEqual(self.qualify([self.record(), self.record(record_id='2')])['state'],
                         'ambiguous_award_identifier')

    def test_search_result_without_explicit_identifier_rejected(self):
        record = self.record()
        record['identifiers'] = []
        self.assertEqual(self.qualify([record])['state'], 'no_exact_identifier')

    def test_untrusted_purl_host_rejected(self):
        record = self.record()
        record['purl'] = record['purl'].replace('purl.org', 'purl.org.invalid')
        self.assertEqual(self.qualify([record])['state'], 'no_exact_identifier')

    def test_alternate_ports_are_not_exact_grant_uris(self):
        for host in ['purl.org:443', 'purl.org:8443']:
            with self.subTest(host=host):
                record = self.record()
                record['purl'] = record['purl'].replace('purl.org', host)
                self.assertEqual(self.qualify([record])['state'], 'no_exact_identifier')

    def test_independent_pin_and_raw_fundref_namespace_binding_required(self):
        before=copy.deepcopy(self.authority)
        with self.assertRaises(ValueError):
            qualify_award_alias({'funder_award_id':'123'},None,self.authority,[self.record()],authority_sha256='0'*64,source_funder_doi='10.13039/1')
        result=qualify_award_alias({'funder_award_id':'123'},None,self.authority,[self.record()],authority_sha256=fingerprint(self.authority),source_funder_doi='10.13039/1')
        self.assertEqual(result['state'],'source_supported_alias')
        self.assertFalse(result['identity_qualified']);self.assertFalse(result['canonical_admission']);self.assertFalse(result['mutation_authorized'])
        wrong=qualify_award_alias({'funder_award_id':'123'},None,self.authority,[self.record()],authority_sha256=fingerprint(self.authority),source_funder_doi='10.13039/2')
        self.assertEqual(wrong['state'],'unqualified_funder_namespace');self.assertEqual(self.authority,before)

    def test_malformed_identifiers_duplicate_records_and_substrings_rejected(self):
        for mode in ('number','number-pad','number-path','id','id-pad','purl-pad','array','duplicates','duplicate-identifiers'):
            records=[self.record()];award={'funder_award_id':'123'}
            if mode=='number':award['funder_award_id']=True
            elif mode=='number-pad':award['funder_award_id']=' 123'
            elif mode=='number-path':award['funder_award_id']='../123'
            elif mode=='id':records[0]['id']=True
            elif mode=='id-pad':records[0]['id']=' 1'
            elif mode=='purl-pad':records[0]['purl']+=' '
            elif mode=='array':records[0]['identifiers']='X123X'
            elif mode=='duplicates':records.append(copy.deepcopy(records[0]))
            else:records[0]['identifiers']=['123','123']
            with self.subTest(mode=mode),self.assertRaises(ValueError):
                qualify_award_alias(award,self.authority['ror'],self.authority,records,authority_sha256=fingerprint(self.authority))

    def test_unknown_number_does_not_hide_partial_record_and_all_inputs_immutable(self):
        record=self.record();saved=copy.deepcopy(record)
        result=qualify_award_alias({},self.authority['ror'],self.authority,[record],authority_sha256=fingerprint(self.authority))
        self.assertEqual(result['state'],'missing_award_number');self.assertEqual(record,saved)
        with self.assertRaises(ValueError):qualify_award_alias({},None,self.authority,[{}],authority_sha256=fingerprint(self.authority))
