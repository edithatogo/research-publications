# SPDX-License-Identifier: Apache-2.0
"""Add conditional source-owned metadata updates to the accepted DoRA collector."""
import copy
import json
from scripts.prepare_qgip_source_collection import compose, gate

FIELDS = ('Title', 'SourceFullTitle', 'field_3', 'field_4', 'field_5', 'field_6', 'field_7', 'field_8')


def build(collector):
    result = copy.deepcopy(collector)
    a = result['properties']['definition']['actions']
    if 'Verify_DoRA_Register' not in a or 'DoRA_Metadata_Before' in a:
        raise ValueError('Expected accepted admission bridge without metadata stage')
    before = copy.deepcopy(a['Registry_After'])
    before['runAfter'] = {'Verify_DoRA_Register': ['Succeeded']}
    a['DoRA_Metadata_Before'] = before
    a['DoRA_Metadata_Complete'] = gate("and(less(length(body('DoRA_Metadata_Before')?['value']),5000),empty(body('DoRA_Metadata_Before')?['@odata.nextLink']),equals(outputs('Manifest')?['complete'],true))", 'DoRA_Metadata_Before')
    a['DoRA_Metadata_Targets'] = {'type': 'Query', 'runAfter': {'DoRA_Metadata_Complete': ['Succeeded']}, 'inputs': {'from': "@body('DoRA_Metadata_Before')?['value']", 'where': "@and(startsWith(string(item()?['field_1']),'dora:'),contains(outputs('Manifest')?['keys'],last(split(string(item()?['field_1']),'/'))))"}}
    a['DoRA_Metadata_Initialize'] = {'type': 'InitializeVariable', 'runAfter': {}, 'inputs': {'variables': [{'name': 'DoRAMetadata', 'type': 'array', 'value': []}]}}
    loop = {'DoRA_Metadata_File': {'type': 'Query', 'runAfter': {}, 'inputs': {'from': "@outputs('Manifest')?['record_files']", 'where': "@equals(item()?['key'],last(split(items('DoRA_Metadata_Project')?['field_1'],'/')))"}}}
    loop['DoRA_Metadata_File_Guard'] = gate("and(equals(length(body('DoRA_Metadata_File')),1),equals(first(body('DoRA_Metadata_File'))?['saved_readback_equal'],true))", 'DoRA_Metadata_File')
    # Reuse the already-qualified XML parser and identity/date guards verbatim.
    parser = copy.deepcopy(a['Project_Missing_DoRA']['actions'])
    parser.pop('Append_DoRA_Admission')
    parser = json.loads(json.dumps(parser).replace("items('Project_Missing_DoRA')", "first(body('DoRA_Metadata_File'))"))
    parser['Read_Admission_HTML']['runAfter'] = {'DoRA_Metadata_File_Guard': ['Succeeded']}
    loop.update(parser)
    values = a['Project_Missing_DoRA']['actions']['Append_DoRA_Admission']['inputs']['value']
    mapping = {'SourceFullTitle': '[Title]', 'field_3': '[Authors]', 'field_4': '[Journal]', 'field_5': '[PublicationYear]', 'field_6': '[PublicationMonth]', 'field_7': '[PublicationDateRaw]', 'field_8': '[PublicationDatePrecision]'}
    after = {k: values[v] for k, v in mapping.items()}
    # Absence in an archive is not an instruction to erase existing metadata.
    for field in ('field_3', 'field_4'):
        expression = after[field][1:]
        after[field] = f"@if(empty(trim({expression})),items('DoRA_Metadata_Project')?['{field}'],{expression})"
    for field in ('field_5', 'field_6', 'field_7', 'field_8'):
        expression = after[field][1:]
        after[field] = f"@if(equals(outputs('Admission_Year'),null),items('DoRA_Metadata_Project')?['{field}'],{expression})"
    after['Title'] = "@take(xpath(outputs('Admission_Table'),'string(/table/tr[td[1]=\"dc.title\"]/td[2])'),255)"
    loop['DoRA_Metadata_Expected'] = compose(after, 'Admission_Month')
    # Canonicalise nullable connector strings for comparison; do not rewrite empty values.
    before_fields = {f: "@items('DoRA_Metadata_Project')?['" + f + "']" for f in FIELDS}
    loop['DoRA_Metadata_Preimage'] = compose(before_fields, 'DoRA_Metadata_Expected')
    comparisons = [f"equals(string(outputs('DoRA_Metadata_Preimage')?['{f}']),string(outputs('DoRA_Metadata_Expected')?['{f}']))" for f in FIELDS]
    loop['DoRA_Metadata_Append'] = {'type': 'If', 'runAfter': {'DoRA_Metadata_Preimage': ['Succeeded']}, 'expression': '@not(and(' + ','.join(comparisons) + '))', 'actions': {'DoRA_Metadata_Add': {'type': 'AppendToArrayVariable', 'runAfter': {}, 'inputs': {'name': 'DoRAMetadata', 'value': {'ID': "@items('DoRA_Metadata_Project')?['ID']", 'source_key': "@items('DoRA_Metadata_Project')?['field_1']", 'before': "@outputs('DoRA_Metadata_Preimage')", 'after': "@outputs('DoRA_Metadata_Expected')", 'source_file': "@first(body('DoRA_Metadata_File'))?['name']"}}}}, 'else': {'actions': {}}}
    loop = json.loads(json.dumps(loop).replace('Admission_', 'Metadata_').replace('Verify_Admission_Identity', 'Verify_Metadata_Identity'))
    a['DoRA_Metadata_Project'] = {'type': 'Foreach', 'foreach': "@body('DoRA_Metadata_Targets')", 'runAfter': {'DoRA_Metadata_Targets': ['Succeeded'], 'DoRA_Metadata_Initialize': ['Succeeded']}, 'runtimeConfiguration': {'concurrency': {'repetitions': 1}}, 'actions': loop}
    template = copy.deepcopy(a['List_previous_checkpoints'])
    dataset = before['inputs']['parameters']['dataset']
    table = before['inputs']['parameters']['table']
    uri = f"_api/web/lists(guid'{table}')/items(@{{items('DoRA_Metadata_Apply')?['ID']}})"
    def http(method, previous='', read=False):
        node = copy.deepcopy(template)
        node['runAfter'] = {previous: ['Succeeded']} if previous else {}
        node['inputs']['parameters'] = {'dataset': dataset, 'parameters/method': method, 'parameters/uri': uri + ('?$select=Id,field_1,' + ','.join(FIELDS) if read else ''), 'parameters/headers': {'Accept': 'application/json;odata=verbose'}}
        node['inputs']['retryPolicy'] = {'type': 'none'}
        return node
    w = {'DoRA_Metadata_Read': http('GET', read=True)}
    predicates = ["equals(body('DoRA_Metadata_Read')?['d']?['Id'],items('DoRA_Metadata_Apply')?['ID'])", "equals(body('DoRA_Metadata_Read')?['d']?['field_1'],items('DoRA_Metadata_Apply')?['source_key'])", "not(empty(body('DoRA_Metadata_Read')?['d']?['__metadata']?['etag']))"]
    predicates += [f"equals(string(body('DoRA_Metadata_Read')?['d']?['{f}']),string(items('DoRA_Metadata_Apply')?['before']?['{f}']))" for f in FIELDS]
    w['DoRA_Metadata_Guard'] = gate('and(' + ','.join(predicates) + ')', 'DoRA_Metadata_Read')
    patch = http('POST', 'DoRA_Metadata_Guard')
    patch['inputs']['parameters']['parameters/headers'].update({'Content-Type': 'application/json;odata=verbose', 'IF-MATCH': "@body('DoRA_Metadata_Read')?['d']?['__metadata']?['etag']", 'X-HTTP-Method': 'MERGE'})
    patch['inputs']['parameters']['parameters/body'] = "@string(setProperty(items('DoRA_Metadata_Apply')?['after'],'__metadata',setProperty(json('{}'),'type',body('DoRA_Metadata_Read')?['d']?['__metadata']?['type'])))"
    w['DoRA_Metadata_Update'] = patch
    w['DoRA_Metadata_Read_After'] = http('GET', 'DoRA_Metadata_Update', read=True)
    w['DoRA_Metadata_Verify'] = gate('and(' + ','.join(f"equals(string(body('DoRA_Metadata_Read_After')?['d']?['{f}']),string(items('DoRA_Metadata_Apply')?['after']?['{f}']))" for f in FIELDS) + ')', 'DoRA_Metadata_Read_After')
    a['DoRA_Metadata_Apply'] = {'type': 'Foreach', 'foreach': "@variables('DoRAMetadata')", 'runAfter': {'DoRA_Metadata_Project': ['Succeeded']}, 'runtimeConfiguration': {'concurrency': {'repetitions': 1}}, 'actions': w}
    a['DoRA_Metadata_Receipt'] = compose({'source': 'dora', 'source_run': "@outputs('Manifest')?['run']", 'list_update_run': "@workflow()?['run']?['name']", 'archive_count': "@outputs('Manifest')?['count']", 'eligible_rows': "@length(body('DoRA_Metadata_Targets'))", 'updates': "@variables('DoRAMetadata')", 'update_count': "@length(variables('DoRAMetadata'))", 'field_scope': list(FIELDS), 'verified': True, 'precedence': 'Existing PubMed source keys and all reviewed fields preserved'}, 'DoRA_Metadata_Apply')
    save = copy.deepcopy(a['Save_scope']); save['runAfter'] = {'DoRA_Metadata_Receipt': ['Succeeded']}
    save['inputs']['parameters'].update({'name': "@concat('metadata-update-',workflow()?['run']?['name'],'.json')", 'body': "@string(outputs('DoRA_Metadata_Receipt'))"})
    a['DoRA_Metadata_Save_Receipt'] = save
    read = copy.deepcopy(a['Read_scope']); read['runAfter'] = {'DoRA_Metadata_Save_Receipt': ['Succeeded']}
    read['inputs']['parameters']['path'] = "@concat(outputs('Run_folder'),'/metadata-update-',workflow()?['run']?['name'],'.json')"
    a['DoRA_Metadata_Read_Receipt'] = read
    a['DoRA_Metadata_Verify_Receipt'] = gate("equals(base64(string(outputs('DoRA_Metadata_Receipt'))),body('DoRA_Metadata_Read_Receipt')?['$content'])", 'DoRA_Metadata_Read_Receipt')
    return result
