# SPDX-License-Identifier: Apache-2.0
"""Add archive-bound DoRA admission to the existing collector; no network writes."""
import copy
from scripts.prepare_qgip_source_collection import compose, gate

BASE = 'https://dora.health.qld.gov.au/qldresearchjspui/handle/1/'


def build(collector, writer):
    result = copy.deepcopy(collector)
    a = result['properties']['definition']['actions']
    w = writer['properties']['definition']['actions']
    if 'Registry_Before' in a or 'Verify_complete_checkpoint' not in a:
        raise ValueError('Expected unbridged complete-checkpoint DoRA collector')
    before = copy.deepcopy(w['Get_Existing_Publication_Register'])
    before['runAfter'] = {'Verify_complete_checkpoint': ['Succeeded']}
    before['inputs']['parameters'].pop('$filter', None)
    before['inputs']['retryPolicy'] = {'type': 'none'}
    a['Registry_Before'] = before
    a['Registry_Complete'] = gate("and(less(length(body('Registry_Before')?['value']),5000),empty(body('Registry_Before')?['@odata.nextLink']),empty(body('Registry_Before')?['odata.nextLink']))", 'Registry_Before')
    for name, field in [('SourceKeys', 'field_1'), ('CanonicalKeys', 'field_2'), ('URLs', 'field_13'), ('IDs', 'ID')]:
        a['Registry_' + name] = {'type': 'Select', 'runAfter': {'Registry_Complete': ['Succeeded']}, 'inputs': {'from': "@body('Registry_Before')?['value']", 'select': "@string(item()?['" + field + "'])"}}
    url = "concat('" + BASE + "',string(item()?['key']))"
    absent = "and(not(contains(body('Registry_SourceKeys'),concat('dora:1/',string(item()?['key'])))),not(contains(body('Registry_SourceKeys'),concat('dora:'," + url + "))),not(contains(body('Registry_SourceKeys'),concat('dora:DORA:'," + url + "))),not(contains(body('Registry_CanonicalKeys'),concat('DORA:'," + url + "))),not(contains(body('Registry_URLs')," + url + ")),not(contains(body('Registry_URLs'),replace(" + url + ",'https://','http://'))))"
    a['Missing_DoRA_Records'] = {'type': 'Query', 'runAfter': {k: ['Succeeded'] for k in ['Registry_SourceKeys', 'Registry_CanonicalKeys', 'Registry_URLs']}, 'inputs': {'from': "@outputs('Manifest')?['record_files']", 'where': '@' + absent}}
    a['Initialize_DoRA_Admissions'] = {'type': 'InitializeVariable', 'runAfter': {}, 'inputs': {'variables': [{'name': 'DoRAAdmissions', 'type': 'array', 'value': []}]}}
    read = copy.deepcopy(a['For_each_record']['actions']['Read_record'])
    read['runAfter'] = {}
    read['inputs']['parameters']['path'] = "@concat(outputs('Manifest')?['archive_folder'],'/',items('Project_Missing_DoRA')?['name'])"
    read['inputs']['retryPolicy'] = {'type': 'none'}
    p = {'Read_Admission_HTML': read}
    p['Admission_HTML'] = compose("@base64ToString(body('Read_Admission_HTML')?['$content'])", 'Read_Admission_HTML')
    p['Admission_Table_Fragment'] = compose("@first(split(last(split(outputs('Admission_HTML'),'itemDisplayTable')),'</table>'))", 'Admission_HTML')
    # Only DC rows are XML-safe. The site's trailing navigation row contains
    # malformed HTML attributes and bare ampersands and is not record metadata.
    p['Admission_Table'] = compose("@xml(concat('<table>',substring(first(split(outputs('Admission_Table_Fragment'),'<tr><td class=\"metadataFieldLabel\">Appears in Sites:')),add(indexOf(outputs('Admission_Table_Fragment'),'>'),1)),'</table>'))", 'Admission_Table_Fragment')

    def field(name):
        return "xpath(outputs('Admission_Table'),'string(/table/tr[td[1]=\"" + name + "\"]/td[2])')"

    expected_url = "concat('" + BASE + "',string(items('Project_Missing_DoRA')?['key']))"
    p['Verify_Admission_Identity'] = gate("and(equals(length(split(outputs('Admission_HTML'),'itemDisplayTable')),2),equals(length(xpath(outputs('Admission_Table'),'/table/tr[td[1]=\"dc.identifier.uri\"]/td[2]')),1),equals(replace(" + field('dc.identifier.uri') + ",'http://','https://')," + expected_url + "),equals(length(xpath(outputs('Admission_Table'),'/table/tr[td[1]=\"dc.title\"]/td[2]')),1),not(empty(trim(" + field('dc.title') + "))))", 'Admission_Table')
    p['Admission_PMID'] = compose("@if(and(isInt(" + field('dc.identifier.pmid') + "),not(startsWith(" + field('dc.identifier.pmid') + ",'0')))," + field('dc.identifier.pmid') + ",'')", 'Verify_Admission_Identity')
    p['Admission_Date_Raw'] = compose('@' + field('dc.date.issued'), 'Admission_PMID')
    p['Admission_Year'] = compose("@if(and(greaterOrEquals(length(outputs('Admission_Date_Raw')),4),isInt(first(split(outputs('Admission_Date_Raw'),'-'))),equals(length(first(split(outputs('Admission_Date_Raw'),'-'))),4)),int(first(split(outputs('Admission_Date_Raw'),'-'))),null)", 'Admission_Date_Raw')
    p['Admission_Month_Number'] = compose("@if(greaterOrEquals(length(outputs('Admission_Date_Raw')),7),if(isInt(substring(outputs('Admission_Date_Raw'),5,2)),int(substring(outputs('Admission_Date_Raw'),5,2)),0),0)", 'Admission_Year')
    p['Admission_Month'] = compose("@if(and(not(equals(outputs('Admission_Year'),null)),greaterOrEquals(outputs('Admission_Month_Number'),1),lessOrEquals(outputs('Admission_Month_Number'),12),or(equals(length(outputs('Admission_Date_Raw')),7),equals(length(outputs('Admission_Date_Raw')),10))),substring(outputs('Admission_Date_Raw'),0,7),null)", 'Admission_Month_Number')
    row = {
        '[SourceKey]': "@concat('dora:1/',string(items('Project_Missing_DoRA')?['key']))",
        '[CanonicalKey]': "@concat('DORA:'," + expected_url + ')',
        '[DORAURL]': '@' + expected_url,
        '[PMID]': "@outputs('Admission_PMID')",
        '[PubMedURL]': "@if(empty(outputs('Admission_PMID')),null,concat('https://pubmed.ncbi.nlm.nih.gov/',outputs('Admission_PMID'),'/'))",
        '[Title]': '@' + field('dc.title'),
        '[Authors]': "@join(xpath(outputs('Admission_Table'),'/table/tr[td[1]=\"dc.contributor.author\"]/td[2]/text()'),'; ')",
        '[Journal]': '@' + field('dc.identifier.journaltitle'),
        '[DOI]': '@toLower(trim(' + field('dc.identifier.doi') + '))',
        '[SourceSet]': 'DORA',
        '[PublicationDateRaw]': "@outputs('Admission_Date_Raw')",
        '[PublicationYear]': "@outputs('Admission_Year')",
        '[PublicationMonth]': "@outputs('Admission_Month')",
        '[PublicationDatePrecision]': "@if(and(equals(length(outputs('Admission_Date_Raw')),4),not(equals(outputs('Admission_Year'),null))),'year',if(and(equals(length(outputs('Admission_Date_Raw')),7),not(equals(outputs('Admission_Month'),null))),'month','unknown'))",
        '[MatchedFacilities]': None,
        '[CHHHSAffiliatedAuthors]': None,
        '[AttributionEvidence]': "@concat('Configured DoRA collection; affiliation attribution not evaluated by this bridge. Source description: '," + field('dc.description') + ",'. Publication type: '," + field('dc.type') + ",'. Full source HTML: ',outputs('Manifest')?['archive_folder'],'/',items('Project_Missing_DoRA')?['name'])",
    }
    p['Append_DoRA_Admission'] = {'type': 'AppendToArrayVariable', 'runAfter': {'Admission_Month': ['Succeeded']}, 'inputs': {'name': 'DoRAAdmissions', 'value': row}}
    a['Project_Missing_DoRA'] = {'type': 'Foreach', 'foreach': "@body('Missing_DoRA_Records')", 'runAfter': {'Missing_DoRA_Records': ['Succeeded'], 'Initialize_DoRA_Admissions': ['Succeeded']}, 'runtimeConfiguration': {'concurrency': {'repetitions': 1}}, 'actions': p}
    loop = copy.deepcopy(w['Apply_to_each_Publication'])
    loop['foreach'] = "@variables('DoRAAdmissions')"
    loop['runAfter'] = {'Project_Missing_DoRA': ['Succeeded']}
    loop['runtimeConfiguration'] = {'concurrency': {'repetitions': 1}}
    loop['actions']['Filter_OpenAlex_Context']['inputs']['from'] = []
    loop['actions']['Condition_Is_New_Publication']['else'] = {'actions': {}}
    verified = copy.deepcopy(loop['actions']['SharePoint_Get_items'])
    verified['runAfter'] = {'Condition_Is_New_Publication': ['Succeeded']}
    verified['inputs']['retryPolicy'] = {'type': 'none'}
    loop['actions']['Read_Admission_After'] = verified
    loop['actions']['Verify_Admission_Present'] = gate(
        "greater(length(body('Read_Admission_After')?['value']),0)",
        'Read_Admission_After',
    )
    # A create has no safe automatic retry after an ambiguous response.
    loop['actions']['Condition_Is_New_Publication']['actions']['SharePoint_Create_item']['inputs']['retryPolicy'] = {'type': 'none'}
    a['Apply_to_each_Publication'] = loop
    after = copy.deepcopy(before)
    after['runAfter'] = {'Apply_to_each_Publication': ['Succeeded']}
    a['Registry_After'] = after
    a['Preserved_Registry_Rows'] = {'type': 'Query', 'runAfter': {'Registry_After': ['Succeeded'], 'Registry_IDs': ['Succeeded']}, 'inputs': {'from': "@body('Registry_After')?['value']", 'where': "@contains(body('Registry_IDs'),string(item()?['ID']))"}}
    a['Verify_DoRA_Register'] = gate("and(equals(length(outputs('Manifest')?['record_files']),outputs('Manifest')?['count']),equals(length(union(outputs('Manifest')?['keys'],outputs('Manifest')?['keys'])),outputs('Manifest')?['count']),equals(length(variables('DoRAAdmissions')),length(body('Missing_DoRA_Records'))),equals(body('Preserved_Registry_Rows'),body('Registry_Before')?['value']),less(length(body('Registry_After')?['value']),5000))", 'Preserved_Registry_Rows')
    return result
