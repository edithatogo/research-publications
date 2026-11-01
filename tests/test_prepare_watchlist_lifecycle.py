"""Preference identity and native-effect boundaries of the lifecycle preparer."""
import copy
import json
import unittest
from scripts.prepare_watchlist_lifecycle import build


def preimage():
    return {'workflowid':'synthetic-existing','statecode':0,'statuscode':1,'clientdata':json.dumps({'properties':{
        'connectionReferences':{'shared_sharepointonline':{'runtimeSource':'invoker','connection':{'connectionReferenceLogicalName':'synthetic-existing'}}},
        'definition':{'triggers':{'manual':{'type':'Request','kind':'Button','inputs':{'schema':{'type':'object'}}}},'actions':{
            'Apply_to_each_Watchlist_Row':{'actions':{'SharePoint_Get_items':{'inputs':{
                'host':{'apiId':'/providers/Microsoft.PowerApps/apis/shared_sharepointonline','connectionName':'shared_sharepointonline','operationId':'GetItems'},
                'parameters':{'dataset':'https://example.sharepoint.com/sites/test','table':'synthetic-list'},
                'authentication':{'type':'Raw','value':'synthetic-existing-invoker-expression'}}}}}}}}})}


class WatchlistLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.original=preimage();self.result=build(self.original)
        self.props=json.loads(self.result['clientdata'])['properties'];self.actions=self.props['definition']['actions']

    def test_preserves_same_identity_state_invoker_and_original_preimage(self):
        self.assertEqual(self.original,preimage())
        self.assertEqual({k:v for k,v in self.result.items() if k!='clientdata'},
                         {k:v for k,v in self.original.items() if k!='clientdata'})
        self.assertEqual(self.props['connectionReferences'],json.loads(self.original['clientdata'])['properties']['connectionReferences'])
        altered=copy.deepcopy(self.original);data=json.loads(altered['clientdata'])
        data['properties']['connectionReferences']['shared_sharepointonline']['runtimeSource']='embedded'
        altered['clientdata']=json.dumps(data)
        with self.assertRaises(ValueError):build(altered)

    def test_identity_comes_from_invoker_and_input_cannot_supply_user_or_recipient(self):
        schema=self.props['definition']['triggers']['manual']['inputs']['schema']
        self.assertFalse(schema['additionalProperties'])
        self.assertNotIn('UserKey',schema['properties']);self.assertNotIn('Recipient',schema['properties'])
        self.assertIn('_api/web/currentuser',self.actions['Caller_identity']['inputs']['parameters']['parameters/uri'])
        self.assertIn("body('Caller_identity')",self.actions['Preference_key']['inputs'])

    def test_unsafe_backing_store_stops_before_read_or_write(self):
        self.assertEqual(self.actions['Read_preference']['runAfter'],{'Guard_store_boundary':['Succeeded']})
        guard=self.actions['Guard_store_boundary']['inputs']
        for field in ['ReadSecurity','WriteSecurity','EnableVersioning']:self.assertIn(field,guard)
        self.assertIn("json('WATCHLIST_LIFECYCLE_GUARD_FAILED')",guard)

    def test_mutation_requires_exact_version_and_unsubscribe_cannot_be_resumed(self):
        update=self.actions['Apply_transition']['else']['actions']
        self.assertEqual(update['Update_preference']['runAfter'],{'Guard_transition':['Succeeded']})
        self.assertEqual(update['Update_preference']['inputs']['parameters']['parameters/headers']['IF-MATCH'],"@triggerBody()?['ExpectedVersion']")
        self.assertIn("['@odata.etag']",update['Guard_owner_version']['inputs'])
        self.assertIn("['AuthorId']", update['Guard_owner_version']['inputs'])
        self.assertIn("['AuthorId']", self.actions['Guard_saved']['inputs'])
        self.assertIn("not(equals(triggerBody()?['ExpectedVersion'],'*'))", update['Guard_owner_version']['inputs'])
        self.assertIn("createArray('active','paused')",update['Guard_transition']['inputs'])
        self.assertIn("createArray('subscribe','unsubscribe')",update['Guard_transition']['inputs'])

    def test_no_delivery_effect_and_stored_state_readback_precedes_result(self):
        self.assertFalse(self.actions['Result']['inputs']['DeliveryEnabled'])
        self.assertEqual(self.actions['Result']['runAfter'],{'Guard_saved':['Succeeded']})
        def walk(actions):
            for a in actions.values():
                yield a
                if 'actions' in a:yield from walk(a['actions'])
                if 'else' in a:yield from walk(a['else']['actions'])
        for action in walk(self.actions):
            if action['type']=='OpenApiConnection':
                self.assertEqual(action['inputs']['host']['operationId'],'HttpRequest')
                self.assertEqual(action['inputs']['retryPolicy'],{'type':'none'})

    def test_editable_preferences_reject_forgery_duplicates_and_unknown_timezones(self):
        schema=self.actions['Configure_preferences']['actions']['Validate_preferences']['inputs']['schema']
        valid={'EventTypes':['reminder'],'ReminderOffsets':[7,1],'Cadence':'daily','Channel':'email','Timezone':'Australia/Brisbane'}
        self.assertFalse(schema['additionalProperties'])
        self.assertEqual(set(schema['required']),set(valid))
        self.assertNotIn('UserKey',schema['properties'])
        self.assertNotIn('invented/zone',schema['properties']['Timezone']['enum'])
        self.assertIn(valid['Timezone'],schema['properties']['Timezone']['enum'])
        self.assertTrue(schema['properties']['ReminderOffsets']['uniqueItems'])
        self.assertEqual(schema['properties']['ReminderOffsets']['items']['minimum'],0)
        self.assertNotIn('send_everything',schema['properties']['EventTypes']['items']['enum'])
        self.assertNotIn('sms',schema['properties']['Channel']['enum'])

    def test_lifecycle_saves_preferences_and_pause_preserves_them(self):
        create=self.actions['Apply_transition']['actions']['Create_preference']['inputs']['parameters']['parameters/body']
        update=self.actions['Apply_transition']['else']['actions']['Update_preference']['inputs']['parameters']['parameters/body']
        for field in ['EventTypesJSON','ReminderOffsetsJSON','Cadence','Channel','Timezone']:
            self.assertEqual(create[field],update[field])
            self.assertIn("first(body('Read_preference')?['value'])",update[field])
        self.assertEqual(self.actions['Caller_identity']['runAfter'],{'Configure_preferences':['Succeeded']})
        self.assertIn('Preferences',self.actions['Result']['inputs'])


if __name__=='__main__':unittest.main()
