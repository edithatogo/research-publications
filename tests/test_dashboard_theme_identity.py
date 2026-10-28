"""Theme repair must preserve styling and reject ambiguous resource references."""
import json
from pathlib import Path
import tempfile
import unittest
from scripts.prepare_dashboard_readable_layout import bundle_digest
from scripts.prepare_dashboard_theme_identity import prepare_theme_identity


class ThemeIdentityTests(unittest.TestCase):
    def baseline(self, root):
        files={'definition/report.json':dict(themeCollection=dict(customTheme=dict(
            name='Exported.json',type='RegisteredResources')),
            resourcePackages=[dict(name='RegisteredResources',items=[dict(
                name='Exported.json',path='Exported.json',type='CustomTheme')])]),
            'definition/pages/pages.json':dict(pageOrder=['page'],activePageName='page'),
            'StaticResources/RegisteredResources/Exported.json':dict(
                name='Custom',dataColors=['#123456'],visualStyles={'*':{'*':{}}})}
        for name,value in files.items():
            p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(value))
        return files

    def test_only_theme_name_changes_and_source_is_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'source';output=Path(tmp)/'output';files=self.baseline(source)
            digest=bundle_digest(source)
            receipt=prepare_theme_identity(source,output,digest)
            name='StaticResources/RegisteredResources/Exported.json'
            result=json.loads((output/name).read_text())
            self.assertEqual(result,dict(files[name],name='Exported.json'))
            self.assertEqual(receipt['changed_files'],[name])
            self.assertEqual(bundle_digest(source),digest)

    def test_ambiguous_resource_fails_before_creating_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'source';output=Path(tmp)/'output';self.baseline(source)
            p=source/'definition/report.json';report=json.loads(p.read_text())
            report['resourcePackages'][0]['items']*=2;p.write_text(json.dumps(report))
            with self.assertRaisesRegex(ValueError,'unique'):
                prepare_theme_identity(source,output,bundle_digest(source))
            self.assertFalse(output.exists())


if __name__=='__main__':unittest.main()
