import unittest

from scripts.rehearse_publication_stub_restore import rehearse
from scripts.plan_publication_stub_restore import schema_field_inventory_sha256


class RehearsalTests(unittest.TestCase):
    def fixtures(self):
        details = {"complete": True, "next_links": [], "items": [
            {"Id": 7, "fields": {"Title": "", "SourceKey": None}},
        ]}
        versions = {"complete": True, "next_links": [], "items": [
            {"Id": 7, "version_history_complete": True, "version_next_links": [],
             "versions": [{"VersionLabel":"1.0", "IsCurrentVersion": False, "Title": "Earlier title", "SourceKey":None},
                          {"VersionLabel":"2.0", "IsCurrentVersion": True, "Title": "", "SourceKey": None}]},
        ]}
        correlation = {"read_only": True, "candidate_count": 1,
                       "items": [{"id": 7, "grade": "direct_action_id_match"}]}
        schema = {"inventory_complete": True, "count": 2, "fields": [
            {"internal_name": "Title", "type": "Text"},
            {"internal_name": "SourceKey", "type": "Text"},
        ]}
        schema.update(source="fictional-schema", inventory_sha256=schema_field_inventory_sha256(schema["fields"]))
        return details, versions, correlation, schema

    def test_prior_only_and_never_authorizes_write(self):
        result = rehearse(*self.fixtures())
        row = result["items"][0]
        self.assertEqual(row["historical_value_field_names"], ["Title"])
        self.assertEqual(row["fields_without_historical_value"], ["SourceKey"])
        self.assertIsNone(row["write_payload"])
        self.assertEqual(result["restore_ready_count"], 0)
        self.assertNotIn("Earlier title", str(result))

    def test_incomplete_version_pagination_rejected(self):
        data = self.fixtures()
        data[1]["items"][0]["version_history_complete"] = False
        with self.assertRaisesRegex(ValueError, "pagination incomplete"):
            rehearse(*data)

    def test_conflicting_history_does_not_select_value(self):
        data = self.fixtures()
        data[1]["items"][0]["versions"].insert(
            0, {"VersionLabel":"0.5", "IsCurrentVersion": False, "Title": "Other title", "SourceKey":None})
        row = rehearse(*data)["items"][0]
        self.assertEqual(row["historical_value_field_names"], [])
        self.assertEqual(row["conflicting_history_field_names"], ["Title"])

    def test_single_first_version_without_marker_has_no_prior_values(self):
        data = self.fixtures()
        data[1]["items"][0]["versions"] = [{"VersionLabel": "1.0"}]
        with self.assertRaisesRegex(ValueError, 'version markers ambiguous'):
            rehearse(*data)

    def test_multiple_unmarked_versions_fail_closed(self):
        data = self.fixtures()
        data[1]["items"][0]["versions"] = [
            {"VersionLabel": "1.0", "Title": "Earlier title"},
            {"VersionLabel": "2.0"},
        ]
        with self.assertRaisesRegex(ValueError, "version markers ambiguous"):
            rehearse(*data)

    def test_no_current_version_fails_closed(self):
        data = self.fixtures()
        data[1]["items"][0]["versions"] = [
            {"VersionLabel":"1.0", "IsCurrentVersion": False, "Title": "Earlier title", "SourceKey":None},
            {"VersionLabel":"2.0", "IsCurrentVersion": False, "Title": "Later title"},
        ]
        with self.assertRaisesRegex(ValueError, "version markers ambiguous"):
            rehearse(*data)

    def test_schema_duplicates_missing_fields_and_boolean_markers_rejected(self):
        for mode in ('schema','missing','marker'):
            data=self.fixtures()
            if mode=='schema': data[3]['fields'].append(data[3]['fields'][0]);data[3]['count']=3
            elif mode=='missing':del data[0]['items'][0]['fields']['Title']
            else:data[1]['items'][0]['versions'][1]['IsCurrentVersion']=1
            with self.subTest(mode=mode),self.assertRaises(ValueError):rehearse(*data)

    def test_current_human_values_not_overwritten_and_incomplete_prior_is_not_chosen(self):
        data=self.fixtures();data[0]['items'][0]['fields']['Title']='Curated human title'
        data[1]['items'][0]['versions'][1]['Title']='Curated human title'
        report=rehearse(*data)
        self.assertEqual(report['items'][0]['historical_value_field_names'],[])
        self.assertNotIn('Curated human title',str(report))
        data=self.fixtures();data[1]['items'][0]['versions'].insert(0,{'VersionLabel':'0.5','IsCurrentVersion':False,'SourceKey':None})
        row=rehearse(*data)['items'][0]
        self.assertIn('Title',row['incomplete_history_field_names'])
        self.assertEqual(row['historical_value_field_names'],[])

    def test_typed_current_value_mismatch_and_partial_pagination_fail(self):
        data=self.fixtures();data[0]['items'][0]['fields']['SourceKey']=False;data[1]['items'][0]['versions'][1]['SourceKey']=0
        with self.assertRaisesRegex(ValueError,'Current version'):rehearse(*data)


if __name__ == "__main__":
    unittest.main()
