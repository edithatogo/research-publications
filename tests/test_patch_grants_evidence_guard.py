# SPDX-License-Identifier: Apache-2.0
import copy
import json
from pathlib import Path
import unittest
from scripts.grants_order_guard import find
from scripts.patch_grants_evidence_guard import patch


class EvidenceGuardTests(unittest.TestCase):
    def test_only_predicate_changes_and_round_only_branch_is_retained(self):
        source = json.loads(Path('config/flows/grants-registry-reviewed-import.definition.json').read_text())['properties']['definition']
        before = copy.deepcopy(source)
        result = patch(source)
        lookup = find(result['actions'], 'SharePoint_Get_source_identity')
        query = lookup['inputs']['parameters']['$filter']
        self.assertIn("if(empty(item()?['SourceID']), if(empty(item()?['RoundID'])", query)
        self.assertIn(", 'SourceID ne null')", query)
        self.assertIn('EvidenceHash eq', query)
        self.assertIn('OpportunityKey ne', query)
        lookup['inputs']['parameters']['$filter'] = find(source['actions'], 'SharePoint_Get_source_identity')['inputs']['parameters']['$filter']
        guard = find(result['actions'], 'Condition_OpportunityKey_Present')['expression']['and']
        self.assertEqual(len(guard), 9)
        self.assertTrue(all('equals' in condition for condition in guard[4:]))
        del guard[4:]
        self.assertEqual(result, before)
        self.assertEqual(source, before)

    def test_changed_or_already_patched_preimage_is_rejected(self):
        source = json.loads(Path('config/flows/grants-registry-reviewed-import.definition.json').read_text())['properties']['definition']
        with self.assertRaises(ValueError):patch(patch(source))

    def test_padding_rejected_but_empty_optional_identifiers_stay_valid(self):
        source = json.loads(Path('config/flows/grants-registry-reviewed-import.definition.json').read_text())['properties']['definition']
        guard = find(patch(source)['actions'], 'Condition_OpportunityKey_Present')['expression']
        def evaluate(node, incoming, stored):
            if 'and' in node:return all(evaluate(x,incoming,stored) for x in node['and'])
            if 'or' in node:return any(evaluate(x,incoming,stored) for x in node['or'])
            if 'not' in node:return not evaluate(node['not'],incoming,stored)
            def value(text):
                import re
                match=re.search(r"item\(\)\?\['([^']+)'\]",text)
                if not match:return text
                result=str(incoming.get(match[1]) or '')
                return result.strip() if text.startswith('@trim(') else result
            left,right=node['equals'];return value(left)==value(right)
        valid = {'OpportunityKey':'GRANT:fixture','Source':'synthetic','SourceID':'fixture',
                 'RoundID':'round-a','EvidenceHash':'a'*64}
        self.assertTrue(evaluate(guard, valid, {}))
        self.assertTrue(evaluate(guard, {**valid, 'SourceID':''}, {}))
        self.assertTrue(evaluate(guard, {**valid, 'RoundID':''}, {}))
        for field in valid:
            for value in ['   ', ' '+valid[field], valid[field]+' ']:
                with self.subTest(field=field, value=value):
                    self.assertFalse(evaluate(guard, {**valid, field:value}, {}))
