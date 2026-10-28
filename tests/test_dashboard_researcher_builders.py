"""Source-only researcher preparation preserves name-label evidence and bindings."""
import base64
import copy
from contextlib import chdir
import json
from pathlib import Path
import tempfile
import unittest

from scripts.prepare_publication_outcome_reader import fingerprint, read, write
from scripts.prepare_researcher_summary_model import prepare as summary
from scripts.prepare_researcher_plot_reader import prepare as plots


class ResearcherBuildersTests(unittest.TestCase):
    def test_additive_name_summary_preserves_existing_parts_and_refuses_replay(self):
        def part(name,text):
            return {'path':name,'payloadType':'InlineBase64','payload':base64.b64encode(text.encode()).decode()}
        original={'format':'TMDL','parts':[
            part('definition/model.tmdl','model Model\nref table Publication\n'),
            part('definition/expressions.tmdl','expression CanonicalPublications = retained\n'),
            part('definition/tables/Publication.tmdl','table Publication\n\tpartition Publication = m\n')
        ]}
        frozen=copy.deepcopy(original);result=summary(original)
        self.assertEqual(original,frozen)
        self.assertEqual(result['parts'][1:3],original['parts'][1:])
        added={p['path']:base64.b64decode(p['payload']).decode() for p in result['parts'][3:]}
        self.assertEqual(len(added),2)
        self.assertTrue(all('IdentityStatus' in text and 'Unresolved' in text for text in added.values()))
        self.assertIn('name labels are not person identities',next(iter(added.values())))
        with self.assertRaisesRegex(ValueError,'already exists'):summary(result)

    def fixture(self,root):
        pages=root/'definition/pages';main=pages/'ResearcherEvidence'
        types={'researcher-heading':'textbox','researcher-guidance':'textbox','researcher-footer':'textbox',
               'researcher-label':'slicer','researcher-year':'slicer','researcher-source':'slicer',
               'researcher-groups':'tableEx','researcher-publications':'tableEx'}
        for name,kind in types.items():
            v={'name':name,'position':{},'visual':{'visualType':kind,'query':{'retained':name},'objects':{
                'general':[{'properties':{'paragraphs':[{'textRuns':[{'value':'Fictional evidence'}]}]}}]}}}
            write(main/'visuals'/name/'visual.json',v)
        write(main/'page.json',{'name':'ResearcherEvidence','width':1920,'height':1080})
        write(root/'definition.pbir',{'binding':'retained-fictional-binding'})
        write(pages/'pages.json',{'pageOrder':['ResearcherEvidence','DoraActivityCounts','DoraActivityEvidence','ARCAwardContextReader'],'activePageName':'ResearcherEvidence'})
        for name in ('activity-total','activity-years'):
            write(pages/'DoraActivityCounts/visuals'/name/'visual.json',{'name':name,'position':{},'visual':{'objects':{}}})
        control={'visual':{'objects':{'text':[{'selector':{'id':state},'properties':{'text':{}}} for state in ('default','disabled')]},
                'visualContainerObjects':{'visualLink':[{'properties':{'drillthroughSection':{}}}],
                                          'general':[{'properties':{}}]}}}
        write(pages/'DoraActivityCounts/visuals/e04-activity-drill/visual.json',control)
        write(pages/'DoraActivityEvidence/visuals/e04-activity-back/visual.json',control)
        write(pages/'DoraActivityEvidence/page.json',{'name':'DoraActivityEvidence'})
        write(pages/'ARCAwardContextReader/visuals/arc-code/visual.json',{'visual':{
            'objects':{'layout':[{'properties':{}}]},'visualContainerObjects':{'padding':[]}}})

    def test_plot_reader_from_another_cwd_preserves_evidence_and_binding(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'source';output=root/'candidate';self.fixture(source)
            digest=fingerprint(source)
            # Contract is resolved from the repository, not the caller's cwd.
            with chdir(root):
                result=plots(source,output,digest)
            self.assertEqual(fingerprint(source),digest)
            self.assertFalse(result['nativeSaveSubmitted'])
            self.assertEqual((source/'definition.pbir').read_bytes(),(output/'definition.pbir').read_bytes())
            for name in ('researcher-groups','researcher-publications'):
                old=read(source/'definition/pages/ResearcherEvidence/visuals'/name/'visual.json')
                new=read(output/'definition/pages/ResearcherLabelEvidence/visuals'/name/'visual.json')
                self.assertEqual(old['visual']['query'],new['visual']['query'])
            self.assertEqual(read(output/'definition/pages/pages.json')['activePageName'],'ResearcherEvidence')
            with self.assertRaises(ValueError):plots(source,output,digest)


if __name__=='__main__':unittest.main()
