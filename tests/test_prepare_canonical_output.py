import ast
import copy
import csv
import io
import re
import unittest
from urllib.parse import unquote

from scripts.export_publication_register import EXPORT_FIELDS, safe_cell
from scripts.prepare_canonical_output import build, csv_cell, deployment_plan, html


def evaluate(expression, value):
    """Restricted field-expression oracle; not a native workflow interpreter."""
    expression = re.sub(r"item\(\)\?\['([^']+)'\]", lambda m: 'cell[' + repr(m.group(1)) + ']', expression.removeprefix('@'))
    expression = re.sub(r"body\('[^']+'\)", 'cell', expression).replace('?[' , '[')
    expression = expression.replace('if(', 'choose(').replace('or(', 'any_of(').replace('and(', 'all_of(').replace('not(', 'negate(')
    functions = {'choose': lambda c, y, n: y if c else n, 'any_of': lambda *v: any(v),
        'coalesce': lambda *v: next((x for x in v if x is not None), None),
        'all_of': lambda *v: all(v), 'negate': lambda v: not v,
        'equals': lambda a, b: type(a) is type(b) and a == b,
        'contains': lambda a, b: b in a, 'length': len, 'first': lambda v: v[0],
        'createArray': lambda *v: list(v), 'substring': lambda v, a, b: v[a:a+b],
        'string': lambda v: '' if v is None else str(v), 'trim': lambda v: v.strip(),
        'empty': lambda v: v is None or len(v) == 0,
        'replace': lambda v, old, new: v.replace(old, new), 'decodeUriComponent': unquote,
        'concat': lambda *v: ''.join(v), 'startsWith': lambda v, p: v.startswith(p)}
    def run(node):
        if isinstance(node, ast.Constant): return node.value
        if isinstance(node, ast.Name) and node.id == 'cell': return value
        if isinstance(node, ast.Name) and node.id in ('true', 'false', 'null'):
            return {'true': True, 'false': False, 'null': None}[node.id]
        if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name) and node.value.id == 'cell':
            return value.get(run(node.slice)) if isinstance(value, dict) else value
        if isinstance(node, ast.Subscript):
            parent = run(node.value)
            return parent.get(run(node.slice)) if isinstance(parent, dict) else parent[run(node.slice)]
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in functions and not node.keywords:
            return functions[node.func.id](*(run(arg) for arg in node.args))
        raise AssertionError('Unexpected field expression')
    return run(ast.parse(expression, mode='eval').body)


class CanonicalOutputTests(unittest.TestCase):
    def inputs(self):
        def operation(name, params, connector='shared_sharepointonline'):
            return {'type': 'OpenApiConnection', 'inputs': {
                'host': {'apiId': '/providers/Microsoft.PowerApps/apis/' + connector,
                         'connectionName': connector, 'operationId': name},
                'parameters': params}, 'runAfter': {}}
        exporter = {'properties': {'connectionReferences': {'shared_sharepointonline': {'pin': 'sp'}},
            'definition': {'triggers': {'Recurrence': {'type': 'Recurrence', 'recurrence': {'frequency': 'Month', 'interval': 1}}},
            'actions': {'Export_Run': {'type': 'Scope', 'runAfter': {}, 'actions': {
                'Save_Registered_Publications_CSV': operation('CreateFile', {'dataset': 'https://example.sharepoint.com/sites/dev', 'folderPath': '/reporting', 'name': 'old.csv', 'body': 'old'}),
                'Printable_Read_manifest': operation('GetFileContentByPath', {'dataset': 'https://example.sharepoint.com/sites/dev', 'path': '/reporting/old.json', 'inferContentType': False}),
                'Printable_Verify_manifest': {'type': 'Compose', 'inputs': True, 'runAfter': {}}}},
                'Monitor_Success_receipt': {'type': 'Compose', 'inputs': 'success', 'runAfter': {'Export_Run': ['Succeeded']}},
                'Monitor_Retain_failed_status': {'type': 'Terminate', 'inputs': {'runStatus': 'Failed'}, 'runAfter': {'Export_Run': ['Failed']}}}}}}
        writer = {'properties': {'connectionReferences': {'shared_sharepointonline': {'pin': 'sp'}, 'shared_powerbi': {'pin': 'pbi'}},
            'definition': {'actions': {'Query': operation('ExecuteDatasetQuery', {'groupid': 'group', 'datasetid': 'model', 'specification/query': 'old'}, 'shared_powerbi')}}}}
        return exporter, writer

    def test_existing_actions_schedule_and_references_preserved(self):
        exporter, writer = self.inputs()
        frozen = copy.deepcopy(exporter)
        after = build(exporter, writer, reporting_month='2026-09')
        self.assertEqual(exporter, frozen)
        original = exporter['properties']['definition']
        actual = after['properties']['definition']
        self.assertEqual(actual['triggers'], original['triggers'])
        for name, action in original['actions'].items():
            if name == 'Export_Run':
                for key, value in action['actions'].items():
                    self.assertEqual(actual['actions'][name]['actions'][key], value)
            else:
                self.assertEqual(actual['actions'][name], action)
        self.assertEqual(after['properties']['connectionReferences'], writer['properties']['connectionReferences'])

    def test_all_added_actions_form_one_checked_chain_and_manifest_is_last(self):
        exporter, writer = self.inputs()
        actions = build(exporter, writer, reporting_month='2026-09')['properties']['definition']['actions']['Export_Run']['actions']
        seen = set(exporter['properties']['definition']['actions']['Export_Run']['actions'])
        for name, action in actions.items():
            if not name.startswith('Canonical_'):
                continue
            self.assertEqual(len(action['runAfter']), 1)
            dependency, statuses = next(iter(action['runAfter'].items()))
            self.assertIn(dependency, seen)
            self.assertIn('Succeeded', statuses)
            self.assertNotIn(action['type'], {'Http', 'Terminate'})
            seen.add(name)
        self.assertEqual(list(actions)[-1], 'Canonical_Store_manifest')
        self.assertEqual(len(actions['Canonical_Manifest']['inputs']['verified_files']), 4)
        self.assertIn('Canonical_Verify_keys', actions['Canonical_Full_safe_cells']['runAfter'])
        self.assertIn('COALESCE(COUNTROWS', actions['Canonical_Query_Counts']['inputs']['parameters']['specification/query'])
        self.assertNotIn('1344', str(actions))

    def test_period_policy_and_revision_are_explicit(self):
        exporter, writer = self.inputs()
        a = build(exporter, writer, period_policy='previous-completed-month-brisbane')['properties']['definition']['actions']['Export_Run']['actions']
        period = a['Canonical_Period']['inputs']
        self.assertIn('E. Australia Standard Time', period)
        self.assertIn("1,'Month','yyyy-MM'", period)
        self.assertIn("outputs('Canonical_Period')", a['Canonical_Query_Month_keys']['inputs']['parameters']['specification/query'])
        for kwargs in ({'reporting_month': '0000-01'}, {'period_policy': 'guess'},
                       {'reporting_month': '2026-09', 'period_policy': 'previous-completed-month-brisbane'},
                       {'reporting_month': '2026-09', 'revision': "x')"}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                build(exporter, writer, **kwargs)

    def test_replay_is_read_only_and_atomic_creation_is_only_after_404(self):
        exporter, writer = self.inputs()
        a = build(exporter, writer, reporting_month='2026-09')['properties']['definition']['actions']['Export_Run']['actions']
        for name, action in a.items():
            if not name.startswith('Canonical_Store_') or action['type'] != 'If':
                continue
            self.assertEqual(len(action['actions']), 1)
            self.assertEqual(next(iter(action['actions'].values()))['type'], 'Compose')
            branch = action['else']['actions']
            self.assertIn('404', branch[name + '_Require404']['inputs'])
            create = branch[name + '_Create']
            self.assertEqual(create['runAfter'], {name + '_Require404': ['Succeeded']})
            params = create['inputs']['parameters']
            self.assertIn('overwrite=false', params['parameters/uri'])
            self.assertEqual(create['inputs']['retryPolicy'], {'type': 'none'})
            self.assertEqual(branch[name + '_Readback']['runAfter'], {name + '_Create': ['Succeeded', 'Failed', 'TimedOut']})
            self.assertNotIn("workflow()?['run']", str(action))
        self.assertNotIn('run_id', a['Canonical_Manifest']['inputs'])

    def test_csv_safety_and_html_roundtrip_expressions(self):
        from html import unescape
        values = [None, '', 'plain', '001', 0, 2026, '=cmd', '  +SUM(A1)', '@x',
                  '-1', '\ttext', '\rline', '\nline', '\ufeff=cmd', '  \ufeff@x',
                  "O'Brien & <research> \"quoted\"", 'Maori Māori 日本語', 'line\r\nnext']
        for value in values:
            with self.subTest(value=value):
                self.assertEqual(evaluate(csv_cell('Title'), value), safe_cell(value))
                self.assertEqual(unescape(evaluate('@' + html('Title'), value)), '' if value is None else str(value))
        # Native trim additionally protects Unicode-whitespace-prefixed formulas.
        self.assertEqual(evaluate(csv_cell('Title'), '\u00a0=cmd'), "'\u00a0=cmd")

    def test_empty_month_has_headers_without_inventing_rows(self):
        exporter, writer = self.inputs()
        actions = build(exporter, writer, reporting_month='2026-09')['properties']['definition']['actions']['Export_Run']['actions']
        expression = actions['Canonical_Month_CSV_complete']['inputs']
        expression = expression.replace("body('Canonical_Month')", 'cell').replace("body('Canonical_Month_CSV')", "''")
        result = list(csv.reader(io.StringIO(evaluate(expression, []))))
        self.assertEqual(result, [EXPORT_FIELDS])
        self.assertIn('COALESCE(COUNTROWS', actions['Canonical_Query_Counts']['inputs']['parameters']['specification/query'])

    def test_nested_connector_errors_cannot_be_hidden_by_matching_totals(self):
        exporter, writer = self.inputs()
        a = build(exporter, writer, reporting_month='2026-09')['properties']['definition']['actions']['Export_Run']['actions']
        guard = a['Canonical_Check_Rows']['inputs']
        condition = guard.removeprefix('@if(').removesuffix(",true,int('CANONICAL_QUERY_ERROR'))")
        for rows in ([], [{'[CanonicalKey]': 'PMID:1'}]):
            valid = {'results': [{'tables': [{'rows': rows}]}], 'firstTableRows': rows}
            self.assertTrue(evaluate(condition, valid))
            for location in ('top', 'result', 'table'):
                for flag, failure in [('error', {'code': 'PartialResult'}), ('errors', ['failed']), ('partial', True), ('truncated', True)]:
                    value = copy.deepcopy(valid)
                    node = value if location == 'top' else value['results'][0]
                    if location == 'table': node = node['tables'][0]
                    node[flag] = failure
                    with self.subTest(location=location, flag=flag):
                        self.assertFalse(evaluate(condition, value))
            mismatch = copy.deepcopy(valid)
            mismatch['firstTableRows'] = [{'[CanonicalKey]': 'different'}]
            self.assertFalse(evaluate(condition, mismatch))

    def test_source_key_and_date_invariants_reject_malformed_records(self):
        exporter, writer = self.inputs()
        a = build(exporter, writer, reporting_month='2026-09')['properties']['definition']['actions']['Export_Run']['actions']
        schema = a['Canonical_Parse_rows']['inputs']['schema']['items']['properties']
        predicate = a['Canonical_Invalid_rows']['inputs']['where']
        row = {f: None for f in EXPORT_FIELDS}
        row.update(CanonicalKey='PMID:123', Title='Paper', SourceSet='PubMed', PublicationDatePrecision='day', PublicationMonth='2026-09', PublicationYear=2026)
        def allowed(value):
            for field, data in value.items():
                rules = schema['[' + field + ']']
                if 'enum' in rules and data not in rules['enum']: return False
                if data is not None and 'pattern' in rules and not re.search(rules['pattern'], data): return False
            return not evaluate(predicate, value)
        self.assertTrue(allowed(row))
        for patch in [{'CanonicalKey': '   '}, {'CanonicalKey': ' PMID:123'}, {'CanonicalKey': 'PMID:123 '},
                      {'CanonicalKey': 'PMID:123\n'}, {'Title': '  '}, {'SourceSet': 'unqualified'},
                      {'PublicationMonth': '2026-13'}, {'PublicationMonth': '0000-01', 'PublicationYear': 0},
                      {'PublicationYear': 2025}, {'PublicationMonth': None}, {'PublicationDatePrecision': 'invented'},
                      {'CanonicalKey': 'TEST:1'}, {'Title': '[SYNTHETIC] paper'}]:
            with self.subTest(patch=patch): self.assertFalse(allowed(dict(row, **patch)))
        for precision in ('year', 'range', 'unknown', 'rss_unverified'):
            self.assertFalse(allowed(dict(row, PublicationDatePrecision=precision)))
            self.assertTrue(allowed(dict(row, PublicationDatePrecision=precision, PublicationMonth=None)))
        self.assertEqual(a['Canonical_Month']['runAfter'], {'Canonical_Verify_row_invariants': ['Succeeded']})

    def test_plan_pins_only_additive_changes_and_rejects_original_edits(self):
        exporter, writer = self.inputs()
        candidate = build(exporter, writer, reporting_month='2026-09')
        plan = deployment_plan(exporter, candidate)
        self.assertEqual(plan['required_target_statecode'], 0)
        self.assertFalse(plan['native_preflight_performed'])
        self.assertEqual(plan['added_connection_names'], ['shared_powerbi'])
        candidate['properties']['definition']['triggers'] = {}
        with self.assertRaises(ValueError):
            deployment_plan(exporter, candidate)

    def test_rejects_changed_connection_missing_readback_and_duplicate_scope(self):
        for mutation in ('connection', 'readback', 'query', 'duplicate'):
            exporter, writer = self.inputs()
            if mutation == 'connection':
                writer['properties']['connectionReferences']['shared_sharepointonline']['pin'] = 'other'
            elif mutation == 'readback':
                del exporter['properties']['definition']['actions']['Export_Run']['actions']['Printable_Verify_manifest']
            elif mutation == 'query':
                writer['properties']['definition']['actions'] = {}
            else:
                exporter = build(exporter, writer, reporting_month='2026-09')
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                build(exporter, writer, reporting_month='2026-09')

    def test_rejects_ambiguous_model_and_implicit_period(self):
        exporter, writer = self.inputs()
        for period in (None, '', '2026-9', '2026-13', '@utcNow()'):
            with self.subTest(period=period), self.assertRaises(ValueError):
                build(exporter, writer, reporting_month=period)
        query = writer['properties']['definition']['actions']['Query']
        other = copy.deepcopy(query)
        other['inputs']['parameters']['datasetid'] = 'other'
        writer['properties']['definition']['actions']['Other'] = other
        with self.assertRaises(ValueError):
            build(exporter, writer, reporting_month='2026-09')


if __name__ == '__main__':
    unittest.main()
