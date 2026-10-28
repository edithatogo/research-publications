"""Fictional complete-model/source fixtures; no native records, calls or outcomes."""
import base64
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from scripts.dashboard_reader_source import digest, direct, model_contract
from scripts.prepare_dashboard_funding_layout import (CALENDAR, OPPORTUNITIES, REQUIRED as FUNDING,
                                                       funding_candidate)
from scripts.prepare_dashboard_relationship_summary import (MEASURES, REQUIRED as RELATIONSHIPS,
    prepare as relationships, qualified_links)
from scripts.prepare_dashboard_source_freshness import prepare as freshness


def sha(raw): return hashlib.sha256(raw).hexdigest()


def files(root):
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob('*') if p.is_file()}


def model_fixture(change=None):
    tables = {}
    for table, field, types in FUNDING+RELATIONSHIPS:
        tables.setdefault(table, {'columns': {}, 'measures': set()})['columns'][field] = sorted(types)[0]
    for table, field in MEASURES:
        tables[table]['measures'].add(field)
    for table, field, dtype in [
        ('Grants Registry', 'Deadline', 'string'), ('Grants Registry', 'Source', 'string'),
        ('Funding Calendar', 'Calendar day', 'dateTime'), ('Funding Calendar', 'Cancelled', 'boolean'),
        ('My Funding Watchlist', 'Active', 'boolean'), ('My Funding Watchlist', 'Scope', 'string'),
        ('DORA Activity Registry', 'DORAActivityKey', 'string'),
        ('DORA Activity Registry', 'DORAObservedUTC', 'dateTime'),
        ('DORA Activity Registry', 'DORAResourceLastModified', 'string'),
        ('FreshSearchAudit', 'RefreshedAtUTC', 'dateTime'),
        ('OpenAlexWorks', 'OpenAlexObservedUTC', 'dateTime'),
        ('ARCAwardContext', 'RetrievedUTC', 'string'),
        ('Study register', 'SourceObservedUTC', 'string'),
        ('ReportingWindow', 'RefreshedAtUTC', 'dateTime')]:
        tables.setdefault(table, {'columns': {}, 'measures': set()})['columns'][field] = dtype
    while len(tables) < 53:
        tables['Fictional'+str(len(tables))] = {'columns': {"Reader's source": 'string'}, 'measures': set()}
    if change: change(tables)
    parts = []
    def part(path, text):
        parts.append({'path': path, 'payloadType': 'InlineBase64',
                      'payload': base64.b64encode(text.encode()).decode()})
    def quoted(value): return "'"+value.replace("'", "''")+"'"
    for table, fields in tables.items():
        text = '/// Fictional retained consumer contract, not data.\ntable '+quoted(table)+'\n'
        for name, dtype in fields['columns'].items():
            text += '\tcolumn '+quoted(name)+'\n\t\tdataType: '+dtype+'\n'
        for name in sorted(fields['measures']):
            text += '\tmeasure '+quoted(name)+' = BLANK()\n'  # No outcome values fabricated.
        part('definition/tables/'+table+'.tmdl', text)
    part('definition/model.tmdl', 'model Fictional\n')
    for index in range(7): part('definition/fixture'+str(index)+'.tmdl', '// opaque metadata\n')
    return json.dumps({'definition': {'format': 'TMDL', 'parts': parts}}).encode()


def source_fixture(root):
    def write(path, doc):
        p = root/path; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(json.dumps(doc)+'\n')
    schema = 'https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.14.0/schema.json'
    pages = ['ReportSection3', 'ReportSection', 'ReportSection2', 'ReportSection4', OPPORTUNITIES, CALENDAR]
    write('definition/pages/pages.json', {'pageOrder': pages, 'activePageName': 'ReportSection2',
                                        'protected': 'Keep author default'})
    write('definition/report.json', {'linguisticSchemaSyncVersion': 2, 'filterConfig': {'untouched': True}})
    write('definition.pbir', {'datasetReference': {'protected': 'fictional original'}})
    (root/'opaque.bin').write_bytes(b'\x00\xffpreserve opaque resource')
    def add(page, name, kind, y, height, table=None, fields=()):
        item = {'$schema': schema, 'name': name,
                'position': {'x': 32, 'y': y, 'width': 1856, 'height': height, 'z': 7, 'tabOrder': 9},
                'filterConfig': {'protected': ['Do not discard source review state']},
                'visual': {'visualType': kind, 'objects': {'protected': 'source formatting'},
                           'visualContainerObjects': {'protected': 'source container'}}}
        if table:
            item['visual']['query'] = {'queryState': {'Values': {'projections': [direct(table, f) for f in fields]}},
                                       'sortDefinition': {'protected': 'source order'}}
        else:
            item['visual']['objects'] = {'general': [{'properties': {'paragraphs': [{'textRuns': [
                {'value': 'Protected source caveat', 'textStyle': {'fontSize': '22px'}}]}]}}]}
        write(f'definition/pages/{page}/visuals/{name}/visual.json', item)
    for page in pages:
        title = 'Funding Opportunities' if page == OPPORTUNITIES else 'Funding Calendar & Watchlist' if page == CALENDAR else page
        write(f'definition/pages/{page}/page.json', {'$schema': 'https://example.invalid/fictional-page-schema',
            'name': page, 'displayName': title, 'width': 1920, 'height': 1080,
            'filterConfig': {'protected': 'Keep page filters'}, 'pageBinding': {'name': 'KeepExistingBinding'}})
        add(page, 'heading', 'textbox', 16, 160 if page in (OPPORTUNITIES, CALENDAR) else 48)
    add(OPPORTUNITIES, '8dda39704411e961cda3', 'tableEx', 208, 808, 'Grants Registry',
        ('Funder', 'Deadline', 'Eligibility', 'OpportunityKey'))
    add(CALENDAR, '739383a647a9679c269d', 'tableEx', 208, 360, 'Funding Calendar',
        ('Title', 'Calendar day', 'Cancelled', 'DeadlineKey'))
    add(CALENDAR, '876392c7006b1020eeea', 'tableEx', 600, 360, 'My Funding Watchlist',
        ('Active', 'OpportunityKey', 'Scope', 'TargetKey'))
    # Title is an actual source field but not part of the minimal new consumer requirements.
    return root


class ReaderFixtureTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); self.source = source_fixture(self.root/'source')
        self.raw = model_fixture(lambda t: t['Funding Calendar']['columns'].update(Title='string'))
        self.original = files(self.source)

    def build(self, builder, name='output', raw=None, **kwargs):
        raw = self.raw if raw is None else raw
        return builder(self.source, self.root/name, expected_sha=digest(files(self.source)),
                       model_definition=raw, expected_model_sha=sha(raw), **kwargs)

    def new_docs(self, name):
        return {p: json.loads(raw) for p, raw in files(self.root/name).items()
                if p.endswith('/visual.json') and p not in self.original}

    def assert_preserved(self, name, allowed=()):
        current = files(self.root/name)
        for path, raw in self.original.items():
            if path not in allowed: self.assertEqual(current[path], raw, path)
        self.assertEqual(files(self.source), self.original)


class FrozenContractTests(ReaderFixtureTest):
    def test_complete_quoted_commented_model_and_hash_guard(self):
        contract = model_contract(self.raw, sha(self.raw))
        self.assertEqual(len(contract['tables']), 53)
        dummy = next(v for k, v in contract['tables'].items() if k.startswith('Fictional'))
        self.assertIn("Reader's source", dummy['columns'])
        with self.assertRaisesRegex(ValueError, 'hash drift'):
            model_contract(self.raw+b' ', sha(self.raw))

    def test_partial_duplicate_and_wrong_table_identity_refused(self):
        for mutation, message in [('partial', '61-part'), ('duplicate', 'Duplicate'), ('identity', 'identity drift')]:
            with self.subTest(mutation=mutation):
                doc = json.loads(self.raw)
                if mutation == 'partial': doc['definition']['parts'].pop()
                elif mutation == 'duplicate': doc['definition']['parts'][-1] = doc['definition']['parts'][0]
                else: doc['definition']['parts'][0]['payload'] = base64.b64encode(b'table WrongIdentity\n').decode()
                raw = json.dumps(doc).encode()
                with self.assertRaisesRegex(ValueError, message): model_contract(raw, sha(raw))

    def test_report_hash_drift_and_exclusive_output_for_each_builder(self):
        for builder in (relationships, freshness):
            with self.assertRaisesRegex(ValueError, 'baseline drift'):
                builder(self.source, self.root/'none', expected_sha='0'*64,
                        model_definition=self.raw, expected_model_sha=sha(self.raw))
            self.assertFalse((self.root/'none').exists())
        output = self.root/'existing'; output.mkdir(); (output/'human.txt').write_text('Keep human work')
        with self.assertRaisesRegex(ValueError, 'Exclusive output'):
            self.build(freshness, 'existing')
        self.assertEqual((output/'human.txt').read_text(), 'Keep human work')
        manifest = self.root/'receipt.manifest.json'; manifest.write_text('Keep prior receipt')
        with self.assertRaisesRegex(ValueError, 'Exclusive output'):
            self.build(freshness, 'receipt')
        self.assertEqual(manifest.read_text(), 'Keep prior receipt')
        self.assertFalse((self.root/'receipt').exists())
        with self.assertRaisesRegex(ValueError, 'outside source'):
            freshness(self.source, self.source/'nested', expected_sha=digest(files(self.source)),
                      model_definition=self.raw, expected_model_sha=sha(self.raw))
        self.assertFalse((self.source/'nested').exists())


class FundingReaderTests(ReaderFixtureTest):
    def build_funding(self, name='funding', raw=None):
        raw = self.raw if raw is None else raw
        return funding_candidate(self.source, self.root/name, digest(files(self.source)), raw, sha(raw))

    def test_all_keyed_queries_filters_words_and_opaque_parts_preserved(self):
        receipt = self.build_funding()
        table = f'definition/pages/{OPPORTUNITIES}/visuals/8dda39704411e961cda3/visual.json'
        changed = [table, f'definition/pages/{OPPORTUNITIES}/page.json', f'definition/pages/{CALENDAR}/page.json']
        self.assert_preserved('funding', changed)
        old = json.loads(self.original[table]); new = json.loads((self.root/'funding'/table).read_bytes())
        new['position'] = old['position']; self.assertEqual(new, old)
        for page in (OPPORTUNITIES, CALENDAR):
            path = f'definition/pages/{page}/page.json'
            old = json.loads(self.original[path]); new = json.loads((self.root/'funding'/path).read_bytes())
            new['height'] = old['height']; self.assertEqual(new, old)
        self.assertEqual(len(receipt['new_parts']), 3)
        detail = next(v for p, v in self.new_docs('funding').items() if 'opportunity-details' in p)
        refs = [p['queryRef'] for p in detail['visual']['query']['queryState']['Values']['projections']]
        self.assertIn('Grants Registry.OpportunityKey', refs); self.assertIn('Grants Registry.ReviewStatus', refs)
        self.assertFalse(receipt['model_changed'])

    def test_missing_model_key_or_table_key_refused_before_output(self):
        raw = model_fixture(lambda t: t['Grants Registry']['columns'].pop('OpportunityKey'))
        with self.assertRaisesRegex(ValueError, 'consumer contract'): self.build_funding(raw=raw)
        self.assertFalse((self.root/'funding').exists())
        path = self.source/f'definition/pages/{OPPORTUNITIES}/visuals/8dda39704411e961cda3/visual.json'
        doc = json.loads(path.read_bytes()); doc['visual']['query']['queryState']['Values']['projections'].pop()
        path.write_text(json.dumps(doc))
        with self.assertRaisesRegex(ValueError, 'table key'): self.build_funding()
        self.assertFalse((self.root/'funding').exists())

    def test_preoutput_geometry_collision_and_missing_detail_field_refused(self):
        raw = model_fixture(lambda t: t['Grants Registry']['columns'].pop('Eligibility'))
        with self.assertRaisesRegex(ValueError, 'Eligibility'): self.build_funding(raw=raw)
        path = self.source/f'definition/pages/{OPPORTUNITIES}/visuals/heading/visual.json'
        doc = json.loads(path.read_bytes()); doc['position']['height'] = 400; path.write_text(json.dumps(doc))
        with self.assertRaisesRegex(ValueError, 'overlaps'): self.build_funding()
        self.assertFalse((self.root/'funding').exists())

    def test_watchlist_scope_is_required_without_inferring_target_identity(self):
        path = self.source/f'definition/pages/{CALENDAR}/visuals/876392c7006b1020eeea/visual.json'
        doc = json.loads(path.read_bytes())
        values = doc['visual']['query']['queryState']['Values']['projections']
        values[:] = [item for item in values if item['queryRef'] != 'My Funding Watchlist.Scope']
        path.write_text(json.dumps(doc))
        with self.assertRaisesRegex(ValueError, 'table key'): self.build_funding()
        self.assertFalse((self.root/'funding').exists())


class RelationshipReaderTests(ReaderFixtureTest):
    def test_current_six_pages_preserved_without_historical_dataset_page(self):
        receipt = self.build(relationships, 'relationships')
        self.assert_preserved('relationships', ['definition/pages/pages.json'])
        old = json.loads(self.original['definition/pages/pages.json'])
        new = json.loads((self.root/'relationships/definition/pages/pages.json').read_bytes())
        self.assertEqual(new['pageOrder'][:-1], old['pageOrder'])
        new['pageOrder'] = old['pageOrder']; self.assertEqual(new, old)
        docs = self.new_docs('relationships')
        self.assertTrue(all(d['visual']['visualType'] != 'actionButton' for d in docs.values()))
        text = json.dumps(docs)
        self.assertIn('no qualified view supplied', text)
        self.assertIn('no review decision', text)
        self.assertIn('No name match, funded-publication inference', text)
        self.assertEqual(receipt['changed_existing'], ['definition/pages/pages.json'])
        self.assertEqual(receipt['native_writes'], 0)

    def test_incomplete_typed_keys_evidence_and_review_contracts_refused(self):
        for table, field in [('Funding Relationship Context', 'EvidenceURL'),
                             ('Funding Relationship Context', 'ReviewStatusRaw'),
                             ('Funding Relationship Context', 'TypedBindingCount'),
                             ('Publication', 'CanonicalKey'), ('ARCAwardContext', 'SourceID')]:
            with self.subTest(table=table, field=field):
                raw = model_fixture(lambda t: t[table]['columns'].pop(field))
                with self.assertRaisesRegex(ValueError, field): self.build(relationships, raw=raw)
                self.assertFalse((self.root/'output').exists())

    def test_no_count_substitute_for_missing_governed_measure(self):
        raw = model_fixture(lambda t: t['Funding Relationship Context']['measures'].remove('Confirmed reviewed links'))
        with self.assertRaisesRegex(ValueError, 'Confirmed reviewed links'): self.build(relationships, raw=raw)
        self.assertFalse((self.root/'output').exists())

    def test_optional_activity_missing_stays_visibly_unavailable(self):
        raw = model_fixture(lambda t: t['DORA Activity Registry']['columns'].pop('DORAActivityKey'))
        receipt = self.build(relationships, 'relationships', raw=raw)
        doc = next(d for d in self.new_docs('relationships').values() if d['name'] == 'source-activities')
        self.assertNotIn('query', doc['visual']); self.assertIn('unavailable', json.dumps(doc))
        self.assertEqual(receipt['unavailable_dependencies'][0]['field'], 'DORAActivityKey')

    def test_link_keys_and_exact_host_scope(self):
        good = {key: 'https://example.sharepoint.com/sites/reader/Lists/Records/AllItems.aspx'
                for key in ('publications', 'candidate_links', 'confirmed_links')}
        for links, hosts, message in [(dict(publications=good['publications']), ['example.sharepoint.com'], 'three-link'),
                                      (good, [], 'allowlist'),
                                      ({**good, 'publications': good['publications']+'\nignored'}, ['example.sharepoint.com'], 'Invalid view URL'),
                                      ({**good, 'publications': good['publications'].replace('example.', 'other.')}, ['example.sharepoint.com'], 'exact-host'),
                                      ({**good, 'publications': 'https://user@example.sharepoint.com/view.aspx'}, ['example.sharepoint.com'], 'exact-host')]:
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message): qualified_links(links, hosts)
        receipt = self.build(relationships, 'links', links=good, allowed_hosts=['example.sharepoint.com'])
        self.assertEqual(sum(d['visual']['visualType'] == 'actionButton' for d in self.new_docs('links').values()), 3)
        self.assertFalse(receipt['model_changed'])


class FreshnessReaderTests(ReaderFixtureTest):
    def test_event_types_distinct_string_dates_unavailable_and_max_refs_correct(self):
        receipt = self.build(freshness, 'freshness'); self.assert_preserved('freshness', ['definition/pages/pages.json'])
        docs = list(self.new_docs('freshness').values()); cards = [d for d in docs if d['visual']['visualType'] == 'card']
        self.assertEqual(len(cards), 4)  # Three typed source events and separate materialization context.
        for card in cards:
            item = card['visual']['query']['queryState']['Values']['projections'][0]
            self.assertEqual(item['field']['Aggregation']['Function'], 4)
            self.assertTrue(item['queryRef'].startswith('Max('))
        unsupported = {('ARCAwardContext', 'RetrievedUTC'), ('Study register', 'SourceObservedUTC'),
                       ('DORA Activity Registry', 'DORAResourceLastModified')}
        gaps = {(d['table'], d['field']) for d in receipt['unavailable_dependencies']}
        self.assertTrue(unsupported <= gaps)
        for doc in docs:
            if doc['name'] in ('timestamp-4', 'timestamp-5', 'provider-dora'):
                self.assertNotIn('query', doc['visual']); self.assertIn('Unavailable', json.dumps(doc))
        text = json.dumps(docs)
        for meaning in ('Observation', 'Acquisition', 'Processing completion', 'Publication date', 'Provider modification'):
            self.assertIn(meaning, text)
        self.assertIn('Blank cards mean unavailable', text)
        self.assertIn('not proof that the whole model processed successfully', text)
        self.assertEqual(receipt['changed_existing'], ['definition/pages/pages.json'])

    def test_absent_observation_field_never_uses_publication_date_or_other_provider(self):
        raw = model_fixture(lambda t: t['OpenAlexWorks']['columns'].pop('OpenAlexObservedUTC'))
        receipt = self.build(freshness, 'freshness', raw=raw)
        doc = next(d for d in self.new_docs('freshness').values() if d['name'] == 'timestamp-3')
        self.assertNotIn('query', doc['visual']); self.assertIn('Unavailable', json.dumps(doc))
        self.assertTrue(any(d['field'] == 'OpenAlexObservedUTC' and d['actual_type'] is None
                            for d in receipt['unavailable_dependencies']))

    def test_reapplication_refused_instead_of_replacing_new_page(self):
        self.build(freshness, 'freshness')
        source = self.root/'freshness'
        with self.assertRaisesRegex(ValueError, 'Page already exists'):
            freshness(source, self.root/'second', expected_sha=digest(files(source)),
                      model_definition=self.raw, expected_model_sha=sha(self.raw))
        self.assertFalse((self.root/'second').exists())


class ReaderCompositionTests(ReaderFixtureTest):
    def test_each_increment_preserves_previously_added_reader_parts(self):
        funding_candidate(self.source, self.root/'funding', digest(files(self.source)), self.raw, sha(self.raw))
        source = self.root/'funding'; funding_files = files(source)
        relationships(source, self.root/'relationships', expected_sha=digest(funding_files),
                      model_definition=self.raw, expected_model_sha=sha(self.raw))
        source = self.root/'relationships'; relationship_files = files(source)
        freshness(source, self.root/'freshness', expected_sha=digest(relationship_files),
                  model_definition=self.raw, expected_model_sha=sha(self.raw))
        final = files(self.root/'freshness')
        for path, raw in relationship_files.items():
            if path != 'definition/pages/pages.json': self.assertEqual(final[path], raw, path)
        order = json.loads(final['definition/pages/pages.json'])
        self.assertEqual(order['pageOrder'][-2:], ['ResearchRelationships', 'SourceFreshness'])
        self.assertEqual(order['activePageName'], 'ReportSection2')
        self.assertEqual(files(self.source), self.original)


if __name__ == '__main__': unittest.main()
