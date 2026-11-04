# SPDX-License-Identifier: Apache-2.0
"""Compile an archive-bound Crossref citation writer; no service operations."""
import copy
from scripts.prepare_qgip_source_collection import compose, gate


def build(collector):
    result = copy.deepcopy(collector)
    a = result['properties']['definition']['actions']
    if 'Crossref_Register_Before' in a or 'Verify_incremental_checkpoint' not in a:
        raise ValueError('Expected unbridged incremental collector')
    before = copy.deepcopy(a['Get_publication_dois'])
    before['runAfter'] = {'Verify_incremental_checkpoint': ['Succeeded']}
    before['inputs']['parameters'].update({'$top': 5000, '$orderby': 'ID asc'})
    a['Crossref_Register_Before'] = before
    a['Crossref_Register_Complete'] = gate("and(less(length(body('Crossref_Register_Before')?['value']),5000),empty(body('Crossref_Register_Before')?['@odata.nextLink']))", 'Crossref_Register_Before')
    a['Crossref_Successful_Entries'] = {'type': 'Query', 'runAfter': {'Crossref_Register_Complete': ['Succeeded']}, 'inputs': {'from': "@outputs('Coverage')?['doi_lookups']", 'where': "@equals(item()?['http_status'],200)"}}
    a['Crossref_Successful_DOIs'] = {'type': 'Select', 'runAfter': {'Crossref_Successful_Entries': ['Succeeded']}, 'inputs': {'from': "@body('Crossref_Successful_Entries')", 'select': "@toLower(item()?['doi'])"}}
    a['Crossref_Target_Rows'] = {'type': 'Query', 'runAfter': {'Crossref_Successful_DOIs': ['Succeeded']}, 'inputs': {'from': "@body('Crossref_Register_Before')?['value']", 'where': "@and(contains(body('Crossref_Successful_DOIs'),toLower(trim(string(item()?['field_11'])))),or(equals(item()?['CitationCount_Crossref'],null),contains(outputs('Batch_DOIs'),toLower(trim(string(item()?['field_11']))))))"}}
    a['Crossref_Initialize_Updates'] = {'type': 'InitializeVariable', 'runAfter': {}, 'inputs': {'variables': [{'name': 'CrossrefUpdates', 'type': 'array', 'value': []}]}}
    loop = {}
    loop['Crossref_Find_Entry'] = {'type': 'Query', 'runAfter': {}, 'inputs': {'from': "@body('Crossref_Successful_Entries')", 'where': "@equals(toLower(item()?['doi']),toLower(trim(string(items('Crossref_Project_Updates')?['field_11']))))"}}
    loop['Crossref_Require_Entry'] = gate("equals(length(body('Crossref_Find_Entry')),1)", 'Crossref_Find_Entry')
    read = copy.deepcopy(a['Read_coverage']);read['runAfter'] = {'Crossref_Require_Entry': ['Succeeded']}
    read['inputs']['parameters']['path'] = "@concat(first(body('Crossref_Find_Entry'))?['archive_folder'],'/',first(body('Crossref_Find_Entry'))?['file'])"
    read['inputs']['retryPolicy'] = {'type': 'none'}
    loop['Crossref_Read_Raw'] = read
    loop['Crossref_Raw'] = compose("@json(base64ToString(body('Crossref_Read_Raw')?['$content']))", 'Crossref_Read_Raw')
    loop['Crossref_Verify_Raw'] = gate("and(equals(outputs('Crossref_Raw')?['status_code'],200),equals(toLower(outputs('Crossref_Raw')?['requested_doi']),toLower(first(body('Crossref_Find_Entry'))?['doi'])),equals(toLower(outputs('Crossref_Raw')?['body']?['message']?['DOI']),toLower(first(body('Crossref_Find_Entry'))?['doi'])),isInt(string(outputs('Crossref_Raw')?['body']?['message']?['is-referenced-by-count'])))", 'Crossref_Raw')
    loop['Crossref_Count'] = compose("@int(outputs('Crossref_Raw')?['body']?['message']?['is-referenced-by-count'])", 'Crossref_Verify_Raw')
    loop['Crossref_Verify_Count'] = gate("greaterOrEquals(outputs('Crossref_Count'),0)", 'Crossref_Count')
    loop['Crossref_Append_Update'] = {'type': 'AppendToArrayVariable', 'runAfter': {'Crossref_Verify_Count': ['Succeeded']}, 'inputs': {'name': 'CrossrefUpdates', 'value': {'ID': "@items('Crossref_Project_Updates')?['ID']", 'doi': "@toLower(trim(string(items('Crossref_Project_Updates')?['field_11'])))", 'before': "@items('Crossref_Project_Updates')?['CitationCount_Crossref']", 'count': "@outputs('Crossref_Count')", 'source_file': "@concat(first(body('Crossref_Find_Entry'))?['archive_folder'],'/',first(body('Crossref_Find_Entry'))?['file'])", 'source_run': "@first(body('Crossref_Find_Entry'))?['capture_run']"}}}
    a['Crossref_Project_Updates'] = {'type': 'Foreach', 'foreach': "@body('Crossref_Target_Rows')", 'runAfter': {'Crossref_Target_Rows': ['Succeeded'], 'Crossref_Initialize_Updates': ['Succeeded']}, 'runtimeConfiguration': {'concurrency': {'repetitions': 1}}, 'actions': loop}
    # Reuse the exact qualified site and list, with conditional single-field MERGE.
    template = copy.deepcopy(a['Read_publication_count'])
    uri = template['inputs']['parameters']['parameters/uri'].split('?$')[0]
    def http(method, suffix, previous):
        node = copy.deepcopy(template);node['runAfter'] = {previous: ['Succeeded']} if previous else {}
        node['inputs']['parameters'].update({'parameters/method': method, 'parameters/uri': uri + suffix, 'parameters/headers': {'Accept': 'application/json;odata=verbose'}})
        node['inputs']['retryPolicy'] = {'type': 'none'}
        return node
    w = {}
    suffix = "/items(@{items('Crossref_Apply_Updates')?['ID']})"
    w['Crossref_Read_Target'] = http('GET', suffix + '?$select=Id,field_11,CitationCount_Crossref', '')
    w['Crossref_Verify_Target'] = gate("and(equals(body('Crossref_Read_Target')?['d']?['Id'],items('Crossref_Apply_Updates')?['ID']),equals(toLower(trim(string(body('Crossref_Read_Target')?['d']?['field_11']))),items('Crossref_Apply_Updates')?['doi']),equals(body('Crossref_Read_Target')?['d']?['CitationCount_Crossref'],items('Crossref_Apply_Updates')?['before']),not(empty(body('Crossref_Read_Target')?['d']?['__metadata']?['etag'])))", 'Crossref_Read_Target')
    patch = http('POST', suffix, '')
    patch['inputs']['parameters']['parameters/headers'].update({'Content-Type': 'application/json;odata=verbose', 'IF-MATCH': "@body('Crossref_Read_Target')?['d']?['__metadata']?['etag']", 'X-HTTP-Method': 'MERGE'})
    patch['inputs']['parameters']['parameters/body'] = "@string(setProperty(setProperty(json('{}'),'__metadata',setProperty(json('{}'),'type',body('Crossref_Read_Target')?['d']?['__metadata']?['type'])),'CitationCount_Crossref',items('Crossref_Apply_Updates')?['count']))"
    w['Crossref_If_Changed'] = {'type': 'If', 'runAfter': {'Crossref_Verify_Target': ['Succeeded']}, 'expression': "@not(equals(items('Crossref_Apply_Updates')?['before'],items('Crossref_Apply_Updates')?['count']))", 'actions': {'Crossref_Update_Count': patch}, 'else': {'actions': {}}}
    w['Crossref_Read_After'] = http('GET', suffix + '?$select=Id,field_11,CitationCount_Crossref', 'Crossref_If_Changed')
    w['Crossref_Verify_After'] = gate("and(equals(body('Crossref_Read_After')?['d']?['Id'],items('Crossref_Apply_Updates')?['ID']),equals(toLower(trim(string(body('Crossref_Read_After')?['d']?['field_11']))),items('Crossref_Apply_Updates')?['doi']),equals(body('Crossref_Read_After')?['d']?['CitationCount_Crossref'],items('Crossref_Apply_Updates')?['count']))", 'Crossref_Read_After')
    a['Crossref_Apply_Updates'] = {'type': 'Foreach', 'foreach': "@variables('CrossrefUpdates')", 'runAfter': {'Crossref_Project_Updates': ['Succeeded']}, 'runtimeConfiguration': {'concurrency': {'repetitions': 1}}, 'actions': w}
    receipt = {'source': 'crossref', 'source_run': "@outputs('Coverage')?['capture_run']", 'list_update_run': "@workflow()?['run']?['name']", 'source_doi_count': "@outputs('Coverage')?['source_doi_count']", 'updates': "@variables('CrossrefUpdates')", 'update_count': "@length(variables('CrossrefUpdates'))", 'verified': True, 'field_scope': ['CitationCount_Crossref']}
    a['Crossref_List_Receipt'] = compose(receipt, 'Crossref_Apply_Updates')
    filename = "@concat('register-update-',workflow()?['run']?['name'],'.json')"
    save = copy.deepcopy(a['Save_scope'])
    save['runAfter'] = {'Crossref_List_Receipt': ['Succeeded']}
    save['inputs']['parameters'].update({'name': filename, 'body': "@string(outputs('Crossref_List_Receipt'))"})
    a['Crossref_Save_List_Receipt'] = save
    read = copy.deepcopy(a['Read_scope'])
    read['runAfter'] = {'Crossref_Save_List_Receipt': ['Succeeded']}
    read['inputs']['parameters']['path'] = "@concat(outputs('Run_folder'),'/register-update-',workflow()?['run']?['name'],'.json')"
    a['Crossref_Read_List_Receipt'] = read
    a['Crossref_Verify_List_Receipt'] = gate("equals(base64(string(outputs('Crossref_List_Receipt'))),body('Crossref_Read_List_Receipt')?['$content'])", 'Crossref_Read_List_Receipt')
    return result
