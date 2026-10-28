"""Ensure accessibility edits cannot change accepted report queries or identities."""
import base64
import copy
import json
import unittest
from scripts.prepare_dashboard_accessibility import prepare, contrast, HEIGHTS, METADATA_TABLES


def part(path, value):
    return {'path': path, 'payloadType': 'InlineBase64',
            'payload': base64.b64encode(json.dumps(value).encode()).decode()}


def decode(document):
    return {p['path']: json.loads(base64.b64decode(p['payload'])) for p in document['definition']['parts']}


def fixture():
    pages = ['ReportSection', 'ReportSection2', 'ReportSection4'] + [f'other{i}' for i in range(6)]
    parts = [part('definition/pages/pages.json', {'pageOrder': pages, 'activePageName': 'ReportSection2'}),
             part('definition.pbir', {'datasetReference': {'unchanged': 'model'}}),
             part('definition/report.json', {'themeCollection': {'baseTheme': {'name': 'theme', 'type': 'SharedResources'}},
                 'resourcePackages': [{'name': 'SharedResources', 'items': [{'name': 'theme', 'path': 'BaseThemes/theme.json'}]}]}),
             part('StaticResources/SharedResources/BaseThemes/theme.json', {'dataColors': ['#D9B300', '#12239E'], 'foreground': '#242424'})]
    for page in pages:
        parts.append(part(f'definition/pages/{page}/page.json', {'displayName': page, 'width': 1920, 'height': 1080}))
        for name, y in [('heading', 16), ('footer', 1016)]:
            parts.append(part(f'definition/pages/{page}/visuals/{name}/visual.json', {
                'name': name, 'position': {'x': 32, 'y': y, 'width': 1856, 'height': 48 if name == 'heading' else 32, 'z': 7, 'tabOrder': 2 if name == 'heading' else 1},
                'filterConfig': {'filters': ['accepted']},
                'visual': {'visualType': 'textbox', 'query': {'accepted': 'query'},
                    'objects': {'general': [{'properties': {'paragraphs': [{'textRuns': [{'value': "Source's caveat"}]}]}}]}}}))
    for page, (name, _, _) in METADATA_TABLES.items():
        parts.append(part(f'definition/pages/{page}/visuals/{name}/visual.json', {
            'name': name, 'position': {'x': 100, 'y': 100, 'width': 300, 'height': 300, 'z': 11000, 'tabOrder': 11000},
            'filterConfig': {'filters': ['accepted']},
            'visual': {'visualType': 'tableEx', 'objects': {}, 'query': {'queryState': {'Values': {'projections': [{'displayName': 'Release provenance'}]}}}}}))
    return {'definition': {'format': 'PBIR', 'parts': parts}}


class AccessibilityTests(unittest.TestCase):
    def test_preserves_queries_filters_visible_words_and_identity(self):
        source = fixture(); before = copy.deepcopy(source); result = prepare(source)
        self.assertEqual(source, before)
        old, new = decode(source), decode(result)
        self.assertEqual(set(new) - set(old), {p for p in new if "/RegisteredResources/" in p})
        for path, value in old.items():
            if not path.endswith('/visual.json') and '/BaseThemes/' not in path and path != 'definition/report.json' and not any(path == f'definition/pages/{p}/page.json' for p in METADATA_TABLES):
                self.assertEqual(value, new[path])
            if path.endswith('/visual.json'):
                for key in ['query', 'objects', 'visualType']:
                    self.assertEqual(value['visual'][key], new[path]['visual'][key])
                self.assertEqual(value['filterConfig'], new[path]['filterConfig'])
                for key in (['z'] if value['name'] in [v[0] for v in METADATA_TABLES.values()] else ['x', 'width', 'z']):
                    self.assertEqual(value['position'][key], new[path]['position'][key])
                self.assertEqual(value['name'], new[path]['name'])
                text = new[path]['visual']['visualContainerObjects']['general'][0]['properties']['altText']['expr']['Literal']['Value']
                self.assertIn("Source''s caveat" if value["visual"]["visualType"] == "textbox" else "Release provenance", text)
        self.assertEqual(new['definition/pages/ReportSection/visuals/heading/visual.json']['position']['tabOrder'], 1000)
        self.assertEqual(old['StaticResources/SharedResources/BaseThemes/theme.json'], new['StaticResources/SharedResources/BaseThemes/theme.json'])
        colors = next(v['dataColors'] for p, v in new.items() if '/RegisteredResources/' in p)
        self.assertTrue(all(contrast(c) >= 3 for c in colors))
        self.assertEqual(colors[1], '#12239E')
        self.assertEqual(prepare(result), result)  # Safe unchanged replay.

    def test_rejects_missing_expected_identity_and_duplicate_parts(self):
        doc = fixture(); doc['definition']['parts'].pop(6)
        with self.assertRaisesRegex(ValueError, 'five source textbox'):
            prepare(doc)
        doc = fixture(); doc['definition']['parts'].append(doc['definition']['parts'][0])
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            prepare(doc)


if __name__ == '__main__':
    unittest.main()
