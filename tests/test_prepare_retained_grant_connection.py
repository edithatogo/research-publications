"""New preparation boundaries only; existing reader/consumer checks are reused."""
import base64
import copy
import json
import unittest

from scripts.prepare_retained_grant_connection import prepare, fingerprint, sha, TABLE_PATH


def inputs():
    site = 'https://example.sharepoint.com/sites/fixture'
    texts = {'definition/model.tmdl': 'model Model\n',
             'definition/relationships.tmdl': '',
             'definition/expressions.tmdl': 'expression Existing = SharePoint.Contents("' + site + '")\n',
             'definition/tables/Publication.tmdl': 'table Publication\n\tcolumn CanonicalKey\n',
             'definition/unknown.json': '{"preserve":true}'}
    model = {'unknown': 'preserve', 'definition': {'format': 'TMDL', 'parts': [
        dict(path=p, payloadType='InlineBase64', payload=base64.b64encode(t.encode()).decode())
        for p, t in texts.items()]}}
    artifact = dict(kind='retained_pubmed_grant_references_v1', edge_count=1,
                    publication_count=1, confirmed_relationship_count=0,
                    edges=[dict(EvidenceKey='pubmed:1|grant:123', CanonicalKey='pub:1',
                                RelationshipKind='publication_grant_reference',
                                CanonicalAdmission=False, MutationAuthorized=False,
                                IdentityQualified=False, SourcePaths=['/Grant/0'])])
    content = json.dumps(artifact)
    digest = sha(content.encode())
    return dict(model=model, artifact_content=content,
                upload=dict(status='PASS_COMPLETE', files=[dict(name='fixture.json', action='create',
                            sha256=digest, UniqueId='fixture-id', ETag='fixture-version')]),
                target=dict(site_url=site, folder='/sites/fixture/Documents/Reporting'),
                model_sha256=fingerprint(model), artifact_sha256=digest,
                artifact_bytes=len(content.encode()))


class NativePreparationTests(unittest.TestCase):
    def test_additive_candidate_exact_inverse_and_honest_blockers(self):
        data = inputs()
        before = copy.deepcopy(data)
        result = prepare(**data)
        self.assertEqual(result['inverse'], before['model'])
        self.assertEqual(data, before)
        old = {p['path']: p for p in data['model']['definition']['parts']}
        new = {p['path']: p for p in result['modelDefinition']['definition']['parts']}
        self.assertEqual(set(new)-set(old), {TABLE_PATH})
        for path in set(old)-{'definition/model.tmdl', 'definition/relationships.tmdl'}:
            self.assertEqual(old[path], new[path])
        self.assertFalse(result['nativeDeploymentReady'])
        self.assertFalse(result['nativeSaveSubmitted'])
        self.assertEqual(len(result['blockers']), 4)

    def test_rejects_artifact_model_receipt_and_scope_drift(self):
        for kind in ['artifact', 'model', 'receipt', 'scope']:
            with self.subTest(kind=kind):
                data = inputs()
                if kind == 'artifact':
                    data['artifact_content'] += ' '
                elif kind == 'model':
                    data['model']['unknown'] = 'changed'
                elif kind == 'receipt':
                    data['upload']['files'][0]['sha256'] = '0' * 64
                else:
                    data['target']['site_url'] = 'https://other.sharepoint.com/sites/other'
                with self.assertRaises(ValueError):
                    prepare(**data)
