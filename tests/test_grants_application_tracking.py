import unittest
from scripts.grants_application_tracking import build


class ApplicationTests(unittest.TestCase):
    def test_one_owner_one_application_and_terminal_stages(self):
        flow = build({'site':'https://example.invalid','registry_id':'00000000-0000-0000-0000-000000000001',
                      'operator_email':'fixture@example.invalid','sharepoint_connection':'fixture'})['definition']
        self.assertEqual(flow['triggers']['manual']['runtimeConfiguration']['concurrency']['runs'],1)
        actions = flow['actions']
        self.assertIn("body('Caller')?['Id']",actions['Key']['inputs'])
        paths = actions['Write']['actions']['NewOrExisting']
        self.assertEqual(paths['actions']['Create']['inputs']['parameters']['parameters/body']['Stage'],'Draft')
        writes = paths['else']['actions']
        self.assertEqual(writes['Save']['inputs']['parameters']['parameters/headers']['IF-MATCH'],
                         "@first(body('Existing')?['value'])?['odata.etag']")
        rules = writes['Current']['inputs']
        self.assertIn("['Stage'],'Draft'),contains(createArray('Submitted','Withdrawn')",rules)
        self.assertIn("['Stage'],'Submitted'),contains(createArray('Awarded','Unsuccessful','Withdrawn')",rules)
        for terminal in ('Awarded','Unsuccessful','Withdrawn'):
            self.assertNotIn("['Stage'],'"+terminal+"')",rules)
