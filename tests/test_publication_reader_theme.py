import copy
import unittest

from scripts.prepare_publication_reader_theme import prepare_dark_theme


class PublicationReaderThemeTests(unittest.TestCase):
    def test_dark_palette_preserves_font_fallbacks_sizes_and_container_spacing(self):
        light = {'background': '#FFFFFF', 'foreground': '#242424',
                 'tableAccent': '#005A9E', 'dataColors': ['#005A9E'],
                 'textClasses': {'label': {'fontSize': 12, 'fontFace': 'Segoe UI, Arial, sans-serif', 'color': '#242424'}},
                 'visualStyles': {'*': {'*': {'padding': [{'top': 16}],
                     'title': [{'fontSize': 12, 'fontColor': {'solid': {'color': 'foreground'}}}]}}}}
        dark = {'name': 'RegisteredDark.json', 'background': '#252423', 'foreground': '#FFFFFF',
                'tableAccent': '#69AFE5', 'dataColors': ['#69AFE5']}
        before = copy.deepcopy(light)
        result = prepare_dark_theme(light, dark)
        self.assertEqual(light, before)
        self.assertEqual(result['textClasses']['label'],
                         {**light['textClasses']['label'], 'color': '#FFFFFF'})
        self.assertEqual(result['visualStyles'], light['visualStyles'])
        self.assertEqual(result['dataColors'], dark['dataColors'])
        self.assertEqual(result['name'], dark['name'])

    def test_different_palette_roles_are_not_silently_reassigned(self):
        with self.assertRaisesRegex(ValueError, 'Palette roles differ'):
            prepare_dark_theme({'dataColors': ['blue']}, {'dataColors': []})
