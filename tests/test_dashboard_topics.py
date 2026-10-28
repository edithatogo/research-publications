"""Fictional taxonomy, lineage, conflict and canonical-domain qualification."""
import base64
import hashlib
import json
import unittest

from scripts.dashboard_topics import build_topics, mesh_catalogue


def observation(payload):
    raw=json.dumps(payload,sort_keys=True).encode()
    return dict(kind='openalex_retained_observation_v1',source='OpenAlex',http_status=200,
                work_id=payload['id'],observed_utc='2026-10-01T00:00:00Z',raw_byte_count=len(raw),
                raw_response_sha256=hashlib.sha256(raw).hexdigest(),
                raw_response_base64=base64.b64encode(raw).decode())


class TopicBridgeTests(unittest.TestCase):
    def setUp(self):
        self.topic=dict(id='https://openalex.org/T123',display_name='Fictional subject',
                        subfield=dict(id='https://openalex.org/subfields/1234',display_name='Fictional subfield'))
        self.payload=dict(id='https://openalex.org/W123',topics=[self.topic,self.topic],
                          primary_topic=self.topic,mesh=[dict(descriptor_ui='D123',descriptor_name='Source label')])
        self.catalog=[dict(descriptor_id='D123',label='Versioned label',edition='2026',
                           source_hash='a'*64,tree_positions=['A01.111.222','B02.333','A01.111.222'])]

    def build(self,payload=None,catalog=None):
        return build_topics(['p1','p2'],[observation(payload or self.payload)],
                            {'https://openalex.org/W123':['p1','p1']},
                            self.catalog if catalog is None else catalog,'2026')

    def test_membership_dedup_preserves_multiple_tree_positions_and_unknowns(self):
        result=self.build();self.assertEqual(len(result['memberships']),2)
        mesh=next(r for r in result['memberships'] if r['taxonomy']=='MeSH')
        self.assertEqual(mesh['hierarchy']['tree_positions'],['A01.111.222','B02.333'])
        self.assertEqual(mesh['hierarchy']['second_level_groups'],['A01','B02'])
        self.assertEqual(mesh['label'],'Versioned label')
        self.assertEqual(result['coverage']['OpenAlex'],dict(included=2,classified=1,unknown=1))
        self.assertTrue(next(r for r in result['memberships'] if r['taxonomy']=='OpenAlex')['primary'])

    def test_mesh_name_does_not_substitute_for_identifier_or_catalogue(self):
        result=self.build(catalog=[])
        self.assertEqual(result['coverage']['MeSH']['classified'],0)
        self.assertEqual(result['diagnostics'][0]['reason'],'mesh_descriptor_not_in_versioned_catalogue')

    def test_nlm_short_numeric_tree_segments_are_preserved_without_padding(self):
        record=dict(self.catalog[0],tree_positions=['B04.820.578.688.2','B03.300.390.400.80'])
        self.assertEqual(mesh_catalogue([record],'2026')['D123']['tree_positions'],
                         ['B03.300.390.400.80','B04.820.578.688.2'])

    def test_corrupt_bytes_and_multiple_snapshots_fail_closed(self):
        env=observation(self.payload);env['raw_response_sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'fingerprint'):
            build_topics(['p1'],[env],{'https://openalex.org/W123':['p1']},self.catalog,'2026')
        other=dict(self.payload,topics=[])
        with self.assertRaisesRegex(ValueError,'one dated'):
            build_topics(['p1'],[observation(self.payload),observation(other)],
                         {'https://openalex.org/W123':['p1']},self.catalog,'2026')

    def test_different_provider_assertions_cannot_overwrite_membership_provenance(self):
        second=dict(self.payload,id='https://openalex.org/W456')
        with self.assertRaisesRegex(ValueError,'membership assertions'):
            build_topics(['p1'],[observation(self.payload),observation(second)],
                         {self.payload['id']:['p1'],second['id']:['p1']},self.catalog,'2026')

    def test_conflicting_hierarchy_and_crosswalk_outside_canonical_domain_rejected(self):
        other=dict(self.topic,subfield=dict(id='different',display_name='Conflict'))
        with self.assertRaisesRegex(ValueError,'Conflicting topic'):
            self.build(dict(self.payload,topics=[self.topic,other]))
        with self.assertRaisesRegex(ValueError,'noncanonical'):
            build_topics(['p1'],[observation(self.payload)],
                         {'https://openalex.org/W123':['outside']},self.catalog,'2026')


if __name__=='__main__':unittest.main()
