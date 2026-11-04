"""Add archive-bound PubMed admission to the existing collector; no native writes.

Uses the accepted registry writer's exact lookup/create contract. Existing rows
are never changed. Original XML remains the full-fidelity source of record.
"""
import copy


def compose(value, after):
    return {'type': 'Compose', 'runAfter': {after: ['Succeeded']}, 'inputs': value}


def gate(condition, after):
    return compose("@if(" + condition + ",true,int('PUBMED_REGISTER_BRIDGE_REJECTED'))", after)


def build(collector, writer):
    result = copy.deepcopy(collector)
    a = result['properties']['definition']['actions']
    w = writer['properties']['definition']['actions']
    if 'Registry_Before' in a or 'Verify_complete_checkpoint' not in a:
        raise ValueError('Expected an unbridged verified PubMed collector')
    # Acquire a complete ordered snapshot. Refuse the cap rather than accept
    # a truncated inventory. The native readback is retained in run history.
    before = copy.deepcopy(w['Get_Existing_Publication_Register'])
    before['runAfter'] = {'Verify_complete_checkpoint': ['Succeeded']}
    before['inputs']['parameters'].pop('$filter', None)
    before['inputs']['retryPolicy'] = {'type': 'none'}
    a['Registry_Before'] = before
    a['Registry_Inventory_Complete'] = gate("and(less(length(body('Registry_Before')?['value']),5000),empty(body('Registry_Before')?['@odata.nextLink']),empty(body('Registry_Before')?['odata.nextLink']))", 'Registry_Before')
    a['Registry_PMIDs_Before'] = {'type': 'Select', 'runAfter': {'Registry_Inventory_Complete': ['Succeeded']}, 'inputs': {'from': "@body('Registry_Before')?['value']", 'select': "@string(item()?['field_10'])"}}
    a['Registry_IDs_Before'] = {'type': 'Select', 'runAfter': {'Registry_Inventory_Complete': ['Succeeded']}, 'inputs': {'from': "@body('Registry_Before')?['value']", 'select': "@item()?['ID']"}}
    # Initialization is top-level. Parsing and writes depend on a complete
    # acquisition, including both provider searches and every stored XML readback.
    a['Initialize_Admission_Rows'] = {'type': 'InitializeVariable', 'runAfter': {}, 'inputs': {'variables': [{'name': 'AdmissionRows', 'type': 'array', 'value': []}]}}
    read = copy.deepcopy(a['For_each_batch']['actions']['Read_xml'])
    read['runAfter'] = {}
    read['inputs']['parameters']['path'] = "@concat(outputs('Manifest')?['archive_folder'],'/',items('Read_Completed_PubMed_Files')?['file'])"
    read['inputs']['retryPolicy'] = {'type': 'none'}
    # Resolve each manifest member beneath its completed archive folder.
    page = {'Read_Admission_XML': read}
    page['Admission_XML_Text'] = compose("@base64ToString(body('Read_Admission_XML')?['$content'])", 'Read_Admission_XML')
    old = a['For_each_batch']['actions']['XML_for_identity']['inputs']
    page['Admission_XML'] = compose(old.replace("outputs('Raw_xml')", "outputs('Admission_XML_Text')").replace("string(body('Fetch_xml'))", "outputs('Admission_XML_Text')"), 'Admission_XML_Text')
    page['Admission_Page_IDs'] = compose("@xpath(xml(outputs('Admission_XML')),'/PubmedArticleSet/PubmedArticle/MedlineCitation/PMID/text() | /PubmedArticleSet/PubmedBookArticle/BookDocument/PMID/text()')", 'Admission_XML')
    page['Verify_Admission_Page'] = gate("equals(sort(outputs('Admission_Page_IDs')),sort(items('Read_Completed_PubMed_Files')?['ids']))", 'Admission_Page_IDs')
    page['Admission_Articles'] = compose("@xpath(xml(outputs('Admission_XML')),'/PubmedArticleSet/PubmedArticle | /PubmedArticleSet/PubmedBookArticle')", 'Verify_Admission_Page')
    pmid = "xpath(xml(item()),'string((/PubmedArticle/MedlineCitation/PMID | /PubmedBookArticle/BookDocument/PMID)[1])')"
    page['New_Admission_Articles'] = {'type': 'Query', 'runAfter': {'Admission_Articles': ['Succeeded']}, 'inputs': {'from': "@outputs('Admission_Articles')", 'where': "@not(contains(body('Registry_PMIDs_Before')," + pmid + '))'}}
    def xp(path):
        return "xpath(xml(items('Project_Admission_Articles')),'string((" + path + ")[1])')"
    article = '/PubmedArticle/MedlineCitation/Article'
    book = '/PubmedBookArticle/BookDocument'
    pid = xp('/PubmedArticle/MedlineCitation/PMID | ' + book + '/PMID')
    title = xp(article + '/ArticleTitle | ' + book + '/ArticleTitle | ' + book + '/Book/BookTitle')
    journal = xp(article + '/Journal/Title | ' + book + '/Book/BookTitle')
    doi = xp('/PubmedArticle/PubmedData/ArticleIdList/ArticleId[@IdType="doi"] | /PubmedBookArticle/PubmedBookData/ArticleIdList/ArticleId[@IdType="doi"]')
    date = article + '/Journal/JournalIssue/PubDate'
    year = xp(date + '/Year | ' + book + '/Book/PubDate/Year')
    month = xp(date + '/Month | ' + book + '/Book/PubDate/Month')
    day = xp(date + '/Day | ' + book + '/Book/PubDate/Day')
    medline = xp(date + '/MedlineDate | ' + book + '/Book/PubDate/MedlineDate')
    project = {}
    project['Admission_Authors'] = compose("@xpath(xml(items('Project_Admission_Articles')),'" + article + '/AuthorList/Author | ' + book + "/AuthorList/Author')", 'placeholder')
    project['Admission_Authors']['runAfter'] = {}
    project['Admission_Author_Names'] = {'type': 'Select', 'runAfter': {'Admission_Authors': ['Succeeded']}, 'inputs': {'from': "@outputs('Admission_Authors')", 'select': "@if(not(empty(xpath(xml(item()),'string(/Author/CollectiveName)'))),xpath(xml(item()),'string(/Author/CollectiveName)'),trim(concat(xpath(xml(item()),'string(/Author/LastName)'),' ',xpath(xml(item()),'string(/Author/Initials)'))))"}}
    # Preserve uncertain dates verbatim; resolve only unambiguous year/month.
    project['Admission_Date_Parts'] = compose({'year': '@' + year, 'month': '@' + month, 'day': '@' + day, 'medline': '@' + medline}, 'Admission_Author_Names')
    months = {'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04', 'may': '05', 'jun': '06', 'jul': '07', 'aug': '08', 'sep': '09', 'oct': '10', 'nov': '11', 'dec': '12'}
    import json
    project['Admission_Month'] = compose("@coalesce(json('" + json.dumps(months, separators=(',', ':')) + "')?[toLower(outputs('Admission_Date_Parts')?['month'])],if(and(isInt(outputs('Admission_Date_Parts')?['month']),greaterOrEquals(int(if(isInt(outputs('Admission_Date_Parts')?['month']),outputs('Admission_Date_Parts')?['month'],'0')),1),lessOrEquals(int(if(isInt(outputs('Admission_Date_Parts')?['month']),outputs('Admission_Date_Parts')?['month'],'0')),12)),formatNumber(int(outputs('Admission_Date_Parts')?['month']),'00'),''))", 'Admission_Date_Parts')
    project['Admission_Year'] = compose("@if(and(isInt(outputs('Admission_Date_Parts')?['year']),equals(length(outputs('Admission_Date_Parts')?['year']),4)),int(outputs('Admission_Date_Parts')?['year']),null)", 'Admission_Month')
    row = {'[SourceKey]': "@concat('pubmed:'," + pid + ')', '[CanonicalKey]': "@concat('PMID:'," + pid + ')', '[PMID]': '@' + pid, '[Title]': '@' + title, '[Journal]': '@' + journal, '[Authors]': "@join(body('Admission_Author_Names'),'; ')", '[DOI]': '@toLower(trim(' + doi + '))', '[PubMedURL]': "@concat('https://pubmed.ncbi.nlm.nih.gov/'," + pid + ",'/')", '[DORAURL]': None, '[SourceSet]': 'PubMed', '[PublicationYear]': "@outputs('Admission_Year')", '[PublicationMonth]': "@if(and(not(equals(outputs('Admission_Year'),null)),not(empty(outputs('Admission_Month')))),concat(string(outputs('Admission_Year')),'-',outputs('Admission_Month')),null)", '[PublicationDateRaw]': "@if(not(empty(outputs('Admission_Date_Parts')?['medline'])),outputs('Admission_Date_Parts')?['medline'],trim(concat(outputs('Admission_Date_Parts')?['year'],' ',outputs('Admission_Date_Parts')?['month'],' ',outputs('Admission_Date_Parts')?['day'])))", '[PublicationDatePrecision]': "@if(not(empty(outputs('Admission_Date_Parts')?['medline'])),'unknown',if(equals(outputs('Admission_Year'),null),'unknown',if(empty(outputs('Admission_Month')),'year',if(empty(outputs('Admission_Date_Parts')?['day']),'month','day'))))", '[MatchedFacilities]': None, '[CHHHSAffiliatedAuthors]': None, '[AttributionEvidence]': "@concat('Configured PubMed source; affiliation attribution not evaluated. Complete original XML: ',items('Read_Completed_PubMed_Files')?['file'])"}
    row['[AttributionEvidence]'] = "@concat('Configured PubMed source; affiliation attribution not evaluated. Publication types: ',join(xpath(xml(items('Project_Admission_Articles')),'/PubmedArticle/MedlineCitation/Article/PublicationTypeList/PublicationType/text() | /PubmedBookArticle/BookDocument/PublicationType/text()'),'; '),'. Full source XML: ',outputs('Manifest')?['archive_folder'],'/',items('Read_Completed_PubMed_Files')?['file'])"
    project['Append_Admission_Row'] = {'type': 'AppendToArrayVariable', 'runAfter': {'Admission_Year': ['Succeeded']}, 'inputs': {'name': 'AdmissionRows', 'value': row}}
    page['Project_Admission_Articles'] = {'type': 'Foreach', 'foreach': "@body('New_Admission_Articles')", 'runAfter': {'New_Admission_Articles': ['Succeeded']}, 'runtimeConfiguration': {'concurrency': {'repetitions': 1}}, 'actions': project}
    a['Read_Completed_PubMed_Files'] = {'type': 'Foreach', 'foreach': "@outputs('Manifest')?['files']", 'runAfter': {'Registry_PMIDs_Before': ['Succeeded'], 'Initialize_Admission_Rows': ['Succeeded']}, 'runtimeConfiguration': {'concurrency': {'repetitions': 1}}, 'actions': page}
    # Reuse the qualified exact-key/PMID lookup and create mapping. A race that
    # finds an existing record leaves it unchanged rather than updating it.
    loop = copy.deepcopy(w['Apply_to_each_Publication'])
    loop['runAfter'] = {'Read_Completed_PubMed_Files': ['Succeeded']}
    loop['foreach'] = "@variables('AdmissionRows')"
    loop['runtimeConfiguration'] = {'concurrency': {'repetitions': 1}}
    la = loop['actions']
    la['Filter_OpenAlex_Context']['inputs']['from'] = []
    la['Condition_Is_New_Publication']['else'] = {'actions': {}}
    a['Apply_to_each_Publication'] = loop
    after = copy.deepcopy(before)
    after['runAfter'] = {'Apply_to_each_Publication': ['Succeeded']}
    a['Registry_After'] = after
    a['Registry_PMIDs_After'] = {'type': 'Select', 'runAfter': {'Registry_After': ['Succeeded']}, 'inputs': {'from': "@body('Registry_After')?['value']", 'select': "@string(item()?['field_10'])"}}
    a['Registry_Preserved_Rows'] = {'type': 'Query', 'runAfter': {'Registry_After': ['Succeeded'], 'Registry_IDs_Before': ['Succeeded']}, 'inputs': {'from': "@body('Registry_After')?['value']", 'where': "@contains(body('Registry_IDs_Before'),item()?['ID'])"}}
    a['Verify_Automatic_PubMed_Register'] = gate("and(equals(length(intersection(outputs('Manifest')?['pmids'],body('Registry_PMIDs_After'))),outputs('Manifest')?['count']),equals(body('Registry_Preserved_Rows'),body('Registry_Before')?['value']),less(length(body('Registry_After')?['value']),5000))", 'Registry_PMIDs_After')
    a['Verify_Automatic_PubMed_Register']['runAfter']['Registry_Preserved_Rows'] = ['Succeeded']
    return result
