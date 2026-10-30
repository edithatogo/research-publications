import unittest
from scripts.prepare_study_archive_path_fix import prepare,PATH
from scripts.prepare_outcome_reader import emit
from scripts.deploy_report_definition import fingerprint,parts

class StudyPathFixTests(unittest.TestCase):
    def test_only_lookup_changed_and_cardinality_preserved(self):
        model={'definition':{'parts':[]}}
        text='table SourceRelationshipEvidence\nReadStudy=(URL as text) as binary => let Folder=Table.SelectRows(T,each [Name]=N),Matches=Table.SelectRows(Folder,each [Name]=List.Last(Parts)) in if Table.RowCount(Matches)=1 then Matches{0}[Content] else error "missing",\nStudyEvidence=OriginalChecks\n'
        emit(model,PATH,text);emit(model,'definition/model.tmdl','model Existing\n')
        r=prepare(model,expected_sha256=fingerprint(model));after=parts(r['candidate'])
        self.assertEqual(after['definition/model.tmdl'],parts(model)['definition/model.tmdl'])
        new=after[PATH].decode();self.assertEqual(new.count('Uri.EscapeDataString([Name])'),2)
        self.assertIn('Table.RowCount(Matches)=1',new);self.assertTrue(new.endswith('StudyEvidence=OriginalChecks\n'))
        with self.assertRaises(ValueError):prepare(r['candidate'],expected_sha256=fingerprint(r['candidate']))
