"""Add outcome evidence tables and one reader page to complete supplied definitions.

Requires an existing caller-reviewed OutcomeProjection M expression containing
JSON from the outcome persistence projection. No source URL, credential, binding,
refresh, real impact claim or native acceptance is inferred.
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations
import base64
import copy
import json
import sys
from pathlib import Path
if not __package__: sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.deploy_report_definition import parts, fingerprint
from scripts.prepare_publication_outcome_reader import projection

TABLES = {
    'TranslationEvent': [('event_id', 'string'), ('revision_id', 'string'), ('event_type', 'string')],
    'OutcomeObservation': [('observation_id', 'string'), ('revision_id', 'string'), ('unit', 'string'), ('population_id', 'string'), ('setting_id', 'string'), ('indicator_id', 'string'), ('indicator_version', 'string'), ('estimate', 'double'), ('numerator', 'double'), ('denominator', 'double'), ('estimate_state', 'string'), ('numerator_state', 'string'), ('denominator_state', 'string')],
    'EventProject': [('event_id', 'string'), ('project_id', 'string')],
    'ObservationProject': [('observation_id', 'string'), ('project_id', 'string')],
    'OutcomeEvidenceDetail': [('kind', 'string'), ('id', 'string'), ('revision_id', 'string'), ('verification_status', 'string'), ('eligible', 'boolean'), ('selected_as_of_cutoff', 'boolean'), ('source_sha256', 'string')],
}


def table_definition(name):
    fields = TABLES[name]
    lines = ['/// Eligibility/redaction supplied by the validated outcome projection.', 'table '+name]
    for field, kind in fields:
        lines.extend([f'\tcolumn {field}', f'\t\tdataType: {kind}', '\t\tsummarizeBy: none', '\t\tsourceColumn: '+field])
    if name in ('TranslationEvent', 'OutcomeObservation'):
        key = fields[0][0]
        lines.extend([f'\tmeasure \'Eligible records\' = DISTINCTCOUNT({name}[{key}])', '\t\tformatString: 0'])
    if name == 'OutcomeObservation':
        lines.extend(["\tmeasure 'Selected observation estimate' = IF(HASONEVALUE(OutcomeObservation[observation_id]), SELECTEDVALUE(OutcomeObservation[estimate]), BLANK())", '\t\tformatString: 0.00'])
    columns = ', '.join(json.dumps(f) for f, _ in fields)
    lines.extend([f'\tpartition {name} = m', '\t\tmode: import', '\t\tsource =',
                  '\t\t\tlet', '\t\t\t    Payload = Json.Document(OutcomeProjection),',
                  f'\t\t\t    Rows = Record.Field(Payload, "{name}"),',
                  f'\t\t\t    Selected = Table.FromRecords(Rows, {{{columns}}}, MissingField.Error)',
                  '\t\t\tin Selected'])
    return '\n'.join(lines)+'\n'


def emit(document, path, content):
    document['definition']['parts'].append({'path': path, 'payloadType': 'InlineBase64',
        'payload': base64.b64encode(content if isinstance(content, bytes) else content.encode()).decode()})


def prepare(model, report, *, model_sha256, report_sha256, source_expression_sha256, card_template_path, table_template_path):
    if fingerprint(model) != model_sha256 or fingerprint(report) != report_sha256:
        raise ValueError('Complete supplied preimage hashes required')
    model_parts, report_parts = parts(model), parts(report)
    expressions = model_parts.get('definition/expressions.tmdl', b'')
    import hashlib, re
    if (hashlib.sha256(expressions).hexdigest() != source_expression_sha256
            or not re.search(rb"(?m)^expression (?:OutcomeProjection|'OutcomeProjection')\s*=", expressions)):
        raise ValueError('Existing reviewed OutcomeProjection expression required')
    paths = ['definition/tables/'+name+'.tmdl' for name in TABLES]
    if any(p.casefold() in {key.casefold() for key in model_parts} for p in paths):
        raise ValueError('Existing outcome tables require an explicit update candidate')
    result_model, result_report = copy.deepcopy(model), copy.deepcopy(report)
    # Preserve model references and add the new tables to the existing model.
    model_path = 'definition/model.tmdl'
    if model_path not in model_parts: raise ValueError('Complete TMDL model required')
    text = model_parts[model_path].decode()
    for name in TABLES:
        if re.search(r"(?m)^\s*ref table '?"+name+r"'?(?:\s|$)", text):
            raise ValueError('Existing table reference collision')
        text += '\nref table '+name+'\n'
        emit(result_model, 'definition/tables/'+name+'.tmdl', table_definition(name))
    for part in result_model['definition']['parts']:
        if part['path'] == model_path: part['payload'] = base64.b64encode(text.encode()).decode()
    page_id = 'OutcomeEvidence'
    page_prefix = 'definition/pages/'+page_id+'/'
    if any(p.startswith(page_prefix) for p in report_parts): raise ValueError('Existing page must not be overwritten')
    order_path = 'definition/pages/pages.json'
    order = json.loads(report_parts[order_path])
    if page_id in order['pageOrder']: raise ValueError('Duplicate page identity')
    card, table = (json.loads(report_parts[p]) for p in (card_template_path, table_template_path))
    if card['visual']['visualType'] != 'cardVisual' or table['visual']['visualType'] != 'tableEx':
        raise ValueError('Accepted card/table visual templates required')
    emit(result_report, page_prefix+'page.json', json.dumps({'name': page_id, 'displayName': 'Translation and outcome evidence', 'width': 1920, 'height': 1080, 'displayOption': 'FitToPage'}))
    for ordinal, (name, template, roles, rect) in enumerate([
        ('events', card, {'Data': [projection('TranslationEvent', 'Eligible records', measure=True)]}, (24,24,900,180)),
        ('observations', card, {'Data': [projection('OutcomeObservation', 'Eligible records', measure=True)]}, (960,24,900,180)),
        ('evidence', table, {'Values': [projection('OutcomeEvidenceDetail', field) for field in ('kind','id','revision_id','verification_status','eligible','source_sha256')]}, (24,240,1836,360)),
        ('observation-values', table, {'Values': [projection('OutcomeObservation', field) for field in ('observation_id','indicator_id','indicator_version','unit','population_id','estimate','numerator','denominator')]}, (24,624,1836,420)),
    ]):
        visual = copy.deepcopy(template); visual['name'] = name
        visual['position'] = dict(zip(('x','y','width','height'), rect), z=ordinal, tabOrder=ordinal)
        for key in ('filterConfig','drillthrough'): visual.pop(key, None)
        # Keep only the accepted schema/style, never template queries or selectors.
        schema = visual.get('$schema')
        visual = {'name': name, 'position': visual['position'], 'visual': {
            'visualType': template['visual']['visualType'],
            'query': {'queryState': {role: {'projections': values} for role, values in roles.items()}}}}
        if schema: visual['$schema'] = schema
        emit(result_report, page_prefix+'visuals/'+name+'/visual.json', json.dumps(visual))
    order['pageOrder'].append(page_id)
    for part in result_report['definition']['parts']:
        if part['path'] == order_path: part['payload'] = base64.b64encode(json.dumps(order).encode()).decode()
    return {'model': result_model, 'report': result_report, 'native_ready': False,
            'limitations': ['Counts, individual quantitative observations and evidence detail; no causal impact or pooled effect.',
                           'Project-filter propagation and quantitative outcome plots are not implemented.',
                           'Native query, rendering and source binding remain unverified.']}


def main(argv=None):
    import argparse, os, subprocess
    from scripts.deploy_report_definition import strict
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('model', 'report', 'model-sha256', 'report-sha256', 'source-expression-sha256',
                 'card-template-path', 'table-template-path', 'output'):
        parser.add_argument('--'+name, required=True)
    args = parser.parse_args(argv)
    result = prepare(strict(Path(args.model).read_bytes()), strict(Path(args.report).read_bytes()),
        model_sha256=args.model_sha256, report_sha256=args.report_sha256,
        source_expression_sha256=args.source_expression_sha256,
        card_template_path=args.card_template_path, table_template_path=args.table_template_path)
    root = Path(__file__).resolve().parents[1]; output = Path(args.output).resolve()
    if not output.is_relative_to(root / 'private' / 'ops'):
        raise ValueError('Output must remain in checkout private/ops')
    subprocess.run(['git', 'check-ignore', '-q', str(output)], cwd=root, check=True)
    with os.fdopen(os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w') as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
    print('PASS_LOCAL_ONLY; native acceptance not evaluated')


if __name__ == '__main__': main()
