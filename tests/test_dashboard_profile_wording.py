"""Profile wording must retain queries, rich-text review and other pages."""
import json
from pathlib import Path
import tempfile
import unittest

from scripts.prepare_dashboard_profile_wording import TITLES, prepare_profile
from scripts.prepare_dashboard_readable_layout import bundle_digest


class ProfileWordingTests(unittest.TestCase):
    def baseline(self, root):
        def save(name,value):
            p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(value))
        save('definition/report.json',{})
        save('definition/pages/pages.json',{'pageOrder':['ReportSection4','Other'],'activePageName':'Other'})
        save('definition.pbir',{'binding':'fictional-retained'})
        save('definition/pages/Other/page.json',{'preserve':'other-page'})
        prefix='definition/pages/ReportSection4/'
        save(prefix+'page.json',{'name':'ReportSection4','displayName':'Clinical Analytics'})
        for n,label in enumerate(TITLES):
            save(prefix+f'visuals/v{n}/visual.json',{'name':f'v{n}','visual':{'visualType':'card',
                'query':{'retained':label},'visualContainerObjects':{'title':[{'properties':{'text':{'expr':{'Literal':{'Value':"'"+label+"'"}}}}}]}}})
        for name,words in [('heading','CHHHS Research Dashboard | Clinical Analytics'),
                           ('caption','Clinical directorate specialty mapping, retained'),
                           ('footer','Field of Research mapped using ANZSRC retained')]:
            save(prefix+f'visuals/{name}/visual.json',{'name':name,'visual':{'visualType':'textbox','objects':{
                'general':[{'properties':{'paragraphs':[{'textRuns':[{'value':words,'textStyle':{'retained':True}}]}]}}]}}})

    def test_wording_changes_without_binding_query_or_source_loss(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'source';output=root/'output';self.baseline(source)
            before=bundle_digest(source);result=prepare_profile(source,output,before)
            self.assertEqual(bundle_digest(source),before)
            self.assertEqual(result['native_writes'],0)
            for p in source.rglob('*.json'):
                a=json.loads(p.read_text());b=json.loads((output/p.relative_to(source)).read_text())
                if 'visual' in a and 'query' in a['visual']:
                    self.assertEqual(a['visual']['query'],b['visual']['query'])
                if 'ReportSection4' not in p.parts:self.assertEqual(a,b)
            self.assertIn('Known open share among assessed',(output/'definition/pages/ReportSection4/visuals/v0/visual.json').read_text())

    def test_incomplete_profile_and_digest_drift_create_no_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'source';output=root/'output';self.baseline(source)
            with self.assertRaisesRegex(ValueError,'baseline drift'):prepare_profile(source,output,'wrong')
            (source/'definition/pages/ReportSection4/visuals/v0/visual.json').unlink()
            with self.assertRaisesRegex(ValueError,'Incomplete profile'):prepare_profile(source,output,bundle_digest(source))
            self.assertFalse(output.exists())


if __name__=='__main__':unittest.main()
