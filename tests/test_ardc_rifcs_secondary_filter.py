import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from scripts.ardc_rifcs_secondary_filter import filter_cached_pages


class RifcsFilterTests(unittest.TestCase):
    def test_records_reference_original_page_and_position(self):
        raw = b'''<OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/" xmlns:r="http://ands.org.au/standards/rif-cs/registryObjects"><ListRecords>
        <record><header><identifier>oai:ands.org.au::1</identifier></header><metadata><r:registryObjects><r:registryObject><r:key>k1</r:key><r:collection/></r:registryObject></r:registryObjects></metadata></record>
        <record><header><identifier>oai:ands.org.au::2</identifier></header><metadata><r:registryObjects><r:registryObject><r:key>k2</r:key><r:activity><r:name>CHHHS project</r:name></r:activity></r:registryObject></r:registryObjects></metadata></record>
        </ListRecords></OAI-PMH>'''
        aliases = json.dumps({'units': [{'OrganisationKey': 'chhhs', 'Aliases': ['CHHHS']}]}).encode()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'page-0.xml').write_bytes(raw)
            sidecar = root / 'page-0.xml.sha256'
            sidecar.write_text(hashlib.sha256(raw).hexdigest())
            result = filter_cached_pages(root, [0], aliases)
            self.assertEqual(result['candidates'][0]['record_index'], 1)
            self.assertEqual(result['candidates'][0]['source_sha256'], hashlib.sha256(raw).hexdigest())
            self.assertFalse(result['source_complete_verified'])
            sidecar.write_text('wrong')
            with self.assertRaisesRegex(ValueError, 'hash mismatch'):
                filter_cached_pages(root, [0], aliases)
