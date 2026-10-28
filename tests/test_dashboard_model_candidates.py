"""Adversarial local model composition; never author a native model in tests."""
import base64
import copy
import unittest
from scripts.prepare_dashboard_model_metrics import prepare_metrics
from scripts.prepare_dashboard_topic_model import prepare_topic_model


def part(path,text):return dict(path=path,payload=base64.b64encode(text.encode()).decode(),payloadType='InlineBase64')


def baseline():
    return {'definition':{'format':'TMDL','parts':[
        part('definition/model.tmdl','model Model\n\nref table Publication\n'),
        part('definition/relationships.tmdl',''),
        part('definition/tables/Publication.tmdl','table Publication\n\tmeasure Publications = COUNTROWS(Publication)\n\t\tformatString: #,0\n\n\tpartition Publication = m\n\t\tsource = ExistingSource\n'),
        part('definition/tables/Unrelated.tmdl','table Unrelated\n\tpartition Unrelated = m\n\t\tsource = ProtectedSource\n')
    ]}}


class ModelCandidateTests(unittest.TestCase):
    def test_year_measures_preserve_source_partition_and_all_other_parts(self):
        original=baseline();frozen=copy.deepcopy(original);result=prepare_metrics(original)
        self.assertEqual(original,frozen)
        before={p['path']:p['payload'] for p in original['definition']['parts']}
        after={p['path']:p['payload'] for p in result['definition']['parts']}
        self.assertEqual([k for k in before if before[k]!=after[k]],['definition/tables/Publication.tmdl'])
        text=base64.b64decode(after['definition/tables/Publication.tmdl']).decode()
        self.assertTrue(text.endswith('\tpartition Publication = m\n\t\tsource = ExistingSource\n'))
        with self.assertRaisesRegex(ValueError,'already exists'):prepare_metrics(result)

    def test_topic_candidate_cannot_admit_noncanonical_keys(self):
        row=dict(publication_key='outside',status='qualified')
        with self.assertRaisesRegex(ValueError,'noncanonical'):
            prepare_topic_model(baseline(),{'memberships':[row]},['p1'])

    def test_additive_empty_snapshot_preserves_original_table_parts(self):
        original=baseline();frozen=copy.deepcopy(original)
        result,receipt=prepare_topic_model(original,{'memberships':[]},['p1'])
        self.assertEqual(original,frozen)
        self.assertEqual(len(result['definition']['parts']),len(original['definition']['parts'])+2)
        after={p['path']:p for p in result['definition']['parts']}
        for p in original['definition']['parts']:
            if p['path'].startswith('definition/tables/'):
                self.assertEqual(after[p['path']],p)
        self.assertEqual(receipt['native_writes'],0)


if __name__=='__main__':unittest.main()
