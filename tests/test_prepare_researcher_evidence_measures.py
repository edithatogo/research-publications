"""Guard complete model preparation against drift, overwrite and global collisions."""
from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from prepare_researcher_evidence_measures import prepare
import prepare_researcher_evidence_measures as preparation


class PreparationGuards(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.preimage = self.root / 'preimage.json'
        self.output = self.root / 'candidate.json'
        self.model = {'definition': {'parts': [{
            'path': 'definition/tables/ResearcherPublicationMentions.tmdl',
            'payload': base64.b64encode((
                'table ResearcherPublicationMentions\n\n' +
                ''.join(f'\tcolumn {name}\n\t\tdataType: {"boolean" if name.startswith("Is") else "string"}\n\n' for name in
                        ('CanonicalKey', 'NameGroupKey', 'IsFirstListed', 'IsLastListed')) +
                '\tpartition ResearcherPublicationMentions = calculated\n'
                '\t\tmode: import\n\t\tsource = {1}\n').encode()).decode(),
            'payloadType': 'InlineBase64'}, {
            'path': 'definition/tables/Publication.tmdl',
            'payload': base64.b64encode(
                b'table Publication\n\n\tcolumn CanonicalKey\n\t\tdataType: string\n').decode(),
            'payloadType': 'InlineBase64'}]}}

    def save_preimage(self):
        self.preimage.write_text(json.dumps(self.model), encoding='utf-8')
        return hashlib.sha256(self.preimage.read_bytes()).hexdigest()

    def test_drift_cannot_create_candidate(self):
        self.save_preimage()
        with self.assertRaisesRegex(ValueError, 'fingerprint'):
            prepare(self.preimage, self.output, 'stale')
        self.assertFalse(self.output.exists())

    def test_existing_output_survives(self):
        digest = self.save_preimage()
        self.output.write_bytes(b'existing prepared input')
        with self.assertRaisesRegex(ValueError, 'New output'):
            prepare(self.preimage, self.output, digest)
        self.assertEqual(self.output.read_bytes(), b'existing prepared input')

    def test_case_insensitive_measure_collision_in_other_table_stops_preparation(self):
        self.model['definition']['parts'].append({
            'path': 'definition/tables/Other.tmdl',
            'payload': base64.b64encode(
                b"table Other\n\tmeasure 'AUTHOR-LABEL MENTIONS' = 1\n\t\tformatString: 0\n").decode(),
            'payloadType': 'InlineBase64'})
        digest = self.save_preimage()
        with self.assertRaisesRegex(ValueError, 'collision'):
            prepare(self.preimage, self.output, digest)
        self.assertFalse(self.output.exists())

    def test_position_flag_type_drift_cannot_create_candidate(self):
        part = self.model['definition']['parts'][0]
        source = base64.b64decode(part['payload']).decode()
        source = source.replace('column IsFirstListed\n\t\tdataType: boolean',
                                'column IsFirstListed\n\t\tdataType: string')
        part['payload'] = base64.b64encode(source.encode()).decode()
        digest = self.save_preimage()
        with self.assertRaisesRegex(ValueError, 'type drift: IsFirstListed'):
            prepare(self.preimage, self.output, digest)
        self.assertFalse(self.output.exists())

    def test_contract_cannot_add_case_variant_duplicate_measures(self):
        spec = json.loads(preparation.CONTRACT.read_text())
        duplicate = dict(spec['measures'][0])
        duplicate['name'] = duplicate['name'].upper()
        spec['measures'].append(duplicate)
        local_contract = self.root / 'contract.json'
        local_contract.write_text(json.dumps(spec))
        digest = self.save_preimage()
        with patch.object(preparation, 'CONTRACT', local_contract):
            with self.assertRaisesRegex(ValueError, 'Distinct measure names'):
                prepare(self.preimage, self.output, digest)
        self.assertFalse(self.output.exists())


if __name__ == '__main__':
    unittest.main()
