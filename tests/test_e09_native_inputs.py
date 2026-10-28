# SPDX-License-Identifier: Apache-2.0
import copy
import unittest
from scripts.e09_native_inputs import qualify_rows, selection_packet
from scripts.e09_post_content import render_post_body


def native(**changes):
    value = {'Id': 1, 'odata.etag': '"1"', 'OData__UIVersionString': '1.0',
             'Title': 'Retained public title', 'field_1': 'pubmed:1',
             'field_2': 'PMID:1', 'field_17': 'Needs Review',
             'field_19': '2026-10-23T01:00:00Z', 'field_20': '10/24/2026 01:00:00',
             'field_6': None, 'field_7': '2026', 'field_8': 'year'}
    return {**value, **changes}


class NativeInputTests(unittest.TestCase):
    def test_legacy_identity_unknown_latest_and_raw_date_are_preserved(self):
        row = native(); before = copy.deepcopy(row)
        result = qualify_rows([row]); selected = result['qualified_rows'][0]
        self.assertEqual(selected['CanonicalKey'], 'PMID:1')
        self.assertIsNone(selected['LastObservedUTC'])
        self.assertEqual(result['accounting'][0]['raw_last_observed'], row['field_20'])
        self.assertEqual(row, before)
        self.assertEqual(qualify_rows([native(field_2='DORA:https://dora.health.qld.gov.au/qldresearchjspui/handle/1/10')])['tier_counts'], {'possible': 1})

    def test_unknown_first_rejected_and_placeholder_are_explicit(self):
        rows = [native(field_19='10/23/2026 01:00:00'),
                native(Id=2, field_1='pubmed:2', field_17='Excluded', field_19='unknown'),
                {'Id': 3, 'field_1': None}]
        result = qualify_rows(rows)
        self.assertEqual(result['disposition_counts'], {'unknown_first_observation': 1,
                         'excluded': 1, 'retained_placeholder': 1})
        self.assertEqual(len(result['accounting']), len(rows))

    def test_reordered_replay_and_exact_window_boundaries(self):
        rows = [native(), native(Id=2, field_1='pubmed:2', field_2='PUB:abcd',
                                field_17='Included', field_19='2026-10-24T01:00:00Z')]
        args = dict(baseline_utc='2026-10-23T01:00:00Z', through_utc='2026-10-24T01:00:00Z',
                    catch_up_from_utc='2026-10-01T00:00:00Z')
        a = selection_packet(rows, **args)
        self.assertEqual(a, selection_packet(list(reversed(rows)), **args))
        self.assertEqual(a['catch_up'][0]['tier'], 'possible')
        self.assertEqual(a['new']['new_threads'][0]['tier'], 'confirmed')
        self.assertEqual(a['catch_up'][0]['PublicationMonth'], None)
        self.assertIn('Retained public title', render_post_body(a['catch_up'][0])['plain_text'])

    def test_bad_identity_duplicate_and_qualified_reverse_time_fail_whole_batch(self):
        for rows in [[native(field_2='DORA:https://other.invalid/1/10')],
                     [native(), native(Id=2)],
                     [native(), native(field_1='pubmed:2')],
                     [native(**{'odata.etag': '*'})],
                     [native(field_1=False)],
                     [native(field_20='2026-10-22T00:00:00Z')]]:
            with self.assertRaises(ValueError):
                qualify_rows(rows)

    def test_renderer_rejects_mismatched_tier_or_invented_dates(self):
        record = dict(publication_key='pubmed:1', canonical_key='PMID:1', tier='possible',
                      review_status='Needs Review', discovered_on='2026-10-24',
                      suggested_trigger='first_discovery')
        for changes in [{'review_status': 'Included'}, {'discovered_on': '2026-02-30'},
                        {'canonical_key': 'unknown:1'}, {'PublicationMonth': '2026-13'}]:
            with self.assertRaises(ValueError):
                render_post_body({**record, **changes})

    def test_equal_canonical_keys_are_held_without_merging_tiers(self):
        rows = [native(field_2='PUB:abcd'), native(Id=2, field_1='dora:1/10',
                    field_2='PUB:abcd', field_17='Included')]
        result = selection_packet(rows, baseline_utc='2026-10-22T00:00:00Z',
                    through_utc='2026-10-24T00:00:00Z', catch_up_from_utc='2026-10-01T00:00:00Z')
        self.assertEqual(result['new']['new_threads'], [])
        group = result['canonical_aliases_held_for_mapping_reconciliation']['PUB:abcd']
        self.assertEqual({x['tier'] for x in group}, {'confirmed', 'possible'})
