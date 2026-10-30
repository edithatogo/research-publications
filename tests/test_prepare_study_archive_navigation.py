import unittest

from scripts.deploy_report_definition import fingerprint, parts
from scripts.prepare_outcome_reader import emit
from scripts.prepare_study_archive_navigation import OLD, NEW, PATH, prepare


class ArchiveNavigationTests(unittest.TestCase):
    def model(self):
        model = {'definition': {'parts': []}}
        emit(model, PATH, 'table SourceRelationshipEvidence\nStudyRows=AcceptedRows,\n'
             + OLD + ',\nStudyEvidence=AcceptedIdentityAndProjectionChecks\n')
        emit(model, 'definition/model.tmdl', 'model Existing\n')
        model['definition']['parts'][0]['payloadType'] = 'InlineBase64'
        return model

    def test_exact_delta_recovery_and_unrelated_preservation(self):
        model = self.model()
        before = parts(model)
        result = prepare(model, expected_sha256=fingerprint(model))
        after = parts(result['candidate'])
        self.assertEqual(parts(model), before)
        self.assertEqual(result['recovery'], model)
        self.assertEqual(after[PATH].decode().replace(NEW, OLD), before[PATH].decode())
        self.assertEqual(after['definition/model.tmdl'], before['definition/model.tmdl'])
        self.assertEqual(result['changed_paths'], [PATH])
        self.assertFalse(result['runtime_verified'])

    def test_determinism_and_idempotent_rerun(self):
        model = self.model()
        first = prepare(model, expected_sha256=fingerprint(model))
        self.assertEqual(first, prepare(model, expected_sha256=fingerprint(model)))
        second = prepare(first['candidate'], expected_sha256=fingerprint(first['candidate']))
        self.assertEqual(second['candidate'], first['candidate'])
        self.assertEqual(second['changed_paths'], [])

    def test_wrong_preimage_or_reader_drift_refused(self):
        model = self.model()
        with self.assertRaises(ValueError):
            prepare(model, expected_sha256='wrong')
        for replacement in (OLD.replace('Table.RowCount(Matches)=1', 'Table.RowCount(Matches)>0'),
                            OLD + ',\n' + OLD):
            changed = self.model()
            changed['definition']['parts'] = [p for p in changed['definition']['parts'] if p['path'] != PATH]
            emit(changed, PATH, 'StudyRows=AcceptedRows,\n' + replacement)
            with self.assertRaises(ValueError):
                prepare(changed, expected_sha256=fingerprint(changed))

    def test_multiline_m_retains_tmdl_expression_indentation(self):
        model = self.model()
        prefix = '\t\t\t\t    '
        model['definition']['parts'] = [p for p in model['definition']['parts'] if p['path'] != PATH]
        emit(model, PATH, 'table SourceRelationshipEvidence\n'
             '\tpartition SourceRelationshipEvidence = m\n\t\tsource =\n'
             + prefix + 'StudyRows=AcceptedRows,\n' + prefix + OLD
             + ',\n' + prefix + 'StudyEvidence=AcceptedChecks\n')
        result = prepare(model, expected_sha256=fingerprint(model))
        text = parts(result['candidate'])[PATH].decode()
        replacement = NEW.replace('\n', '\n' + prefix)
        self.assertIn(prefix + replacement, text)
        self.assertEqual(text.replace(replacement, OLD), parts(model)[PATH].decode())
        again = prepare(result['candidate'], expected_sha256=fingerprint(result['candidate']))
        self.assertEqual(again['changed_paths'], [])
