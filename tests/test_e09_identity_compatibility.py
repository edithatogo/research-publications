# SPDX-License-Identifier: Apache-2.0
"""Synthetic E09 reference compatibility; no private rows or native execution."""
import copy
import hashlib
import json
import re
import unittest

from scripts.e09_first_discovery import _canonical_key, parse_registry_row, select_new_threads
from scripts.e09_thread_mapping import prepare_thread
from scripts.e09_storage import envelope, validate_envelope, transition
from scripts.e09_edition_storage import prepare_edition_snapshot
from scripts.build_e09_no_send_flow import definition, validate_no_send_definition
from tests.test_e09_first_discovery import registry_row
from tests.test_e09_thread_mapping import record
from tests import test_e09_edition_storage as edition_fixtures
from tests.test_e09_subscription_editions import preference

DORA = 'DORA:https://dora.health.qld.gov.au/qldresearchjspui/handle/'
VALID = ['PUB:0', 'PUB:abcd0123456789ef', 'PMID:1', 'PMID:' + '9' * 100,
         DORA + '1/2', DORA + '9' * 90 + '/' + '8' * 90]
INVALID = [':abcd', 'PUBPUB:abcd', 'PMIDPMID:1', 'PMID:1:2',
           DORA, DORA+'1/', DORA+'/2', '', 'PUB:', 'PUB:ABCD', 'pub:abcd', 'PUB:abcd\n', 'PMID:0',
           'PMID:01', 'PMID:+1', 'PMID:-1', 'PMID:1.0', 'PMID:1e3',
           'PMID:１', 'PMID:١', 'PMID:1 2', 'PMID:1\n', 'pmid:1',
           ' PMID:1', 'PMID:1 ', 'PMID:' + '9' * 100 + 'x',
           DORA + '0/1', DORA + '01/2', DORA + '1/02', DORA + '1/0',
           DORA + '1/2/', DORA + '1/2/3', DORA + '1/2?x=1', DORA + '1/2#f',
           DORA + '1/%32', DORA + '1/..', DORA + '１/2', DORA + '1/+2',
           DORA.replace('https:', 'http:') + '1/2',
           DORA.replace('DORA:', 'dora:') + '1/2',
           DORA.replace('dora.health', 'DORA.health') + '1/2',
           DORA.replace('gov.au/', 'gov.au:443/') + '1/2',
           DORA.replace('dora.health', 'user@dora.health') + '1/2',
           DORA.replace('gov.au/', 'gov.au.evil.invalid/') + '1/2',
           DORA.replace('/handle/', '/other/') + '1/2', 'OTHER:1']


def native_row(identity=1, canonical='PUB:abcd', **changes):
    return {**dict(Id=identity, Title='FICTIONAL retained candidate',
        field_1=f'qualification:row-{identity}', field_2=canonical,
        field_17='Needs Review', field_19='2026-10-20T04:00:00Z',
        field_20=None, field_6='2026-10', field_7='October 2026', field_8='month',
        OData__UIVersionString='2.0', **{'odata.etag':'"2"'}), **changes}


def packet(rows):
    from scripts.e09_native_inputs import selection_packet
    return selection_packet(rows, baseline_utc='2026-10-19T00:00:00Z',
        through_utc='2026-10-22T00:00:00Z', catch_up_from_utc='2026-10-01T00:00:00Z')


def evaluate_guard(expression, contexts):
    """Evaluate emitted string/boolean WDL subset locally, not a native engine.

    Strict token parsing fails for unknown functions; startsWith deliberately
    models WDL's case-insensitivity. No numeric identifier conversion is supplied.
    """
    source = expression.lstrip('@')
    pattern = r"'(?:[^']|'')*'|\?\[|[(),\]]|-?\d+|[A-Za-z_]\w*"
    tokens = []
    end = 0
    for match in re.finditer(pattern, source):
        assert not source[end:match.start()].strip(), 'Unsupported expression syntax'
        tokens.append(match.group()); end = match.end()
    assert not source[end:].strip(), 'Unparsed expression suffix'
    position = 0
    def parse():
        nonlocal position
        token = tokens[position]; position += 1
        if token.startswith("'"):
            value = token[1:-1].replace("''", "'")
        elif token in {'true','false','null'}:
            value = {'true':True,'false':False,'null':None}[token]
        elif re.fullmatch(r'-?\d+', token):
            value = int(token)
        else:
            assert tokens[position] == '('; position += 1
            args = []
            if tokens[position] != ')':
                args.append(parse())
                while tokens[position] == ',':
                    position += 1; args.append(parse())
            assert tokens[position] == ')'; position += 1
            def substring(s, start, length=None):
                if start < 0 or start > len(s) or (length is not None and start+length > len(s)):
                    raise ValueError('WDL substring bounds')
                return s[start:] if length is None else s[start:start+length]
            functions = dict(equals=lambda a,b: type(a) is type(b) and a==b,
                length=len, substring=substring, replace=lambda s,a,b:s.replace(a,b),
                startsWith=lambda s,p:s.casefold().startswith(p.casefold()),
                greater=lambda a,b:a>b, split=lambda s,d:s.split(d),
                first=lambda x:x[0], last=lambda x:x[-1], skip=lambda x,n:x[n:],
                take=lambda x,n:x[:n], join=lambda x,d:d.join(x),
                concat=lambda *x:''.join(x), outputs=lambda n:contexts['outputs'][n],
                body=lambda n:contexts['body'][n], triggerBody=lambda:contexts['trigger'],
                **{'and':lambda *x:all(x), 'or':lambda *x:any(x),
                   'if':lambda c,a,b:a if c else b})
            value = functions[token](*args)
        while position < len(tokens) and tokens[position]=='?[':
            position += 1; key=parse(); assert tokens[position]==']'; position += 1
            value = value.get(key) if value is not None else None
        return value
    result = parse(); assert position == len(tokens)
    return result


class IdentityCompatibilityTests(unittest.TestCase):
    def test_strict_existing_and_candidate_references_preserve_exact_identity(self):
        for key in VALID:
            with self.subTest(key=key):
                self.assertEqual(_canonical_key(key), key)
                parsed=parse_registry_row(registry_row(CanonicalKey=key))
                self.assertEqual(parsed['canonical_key'], key)
        for key in INVALID + [None, 1, True, [], {}]:
            with self.subTest(key=key), self.assertRaises(ValueError): _canonical_key(key)

    def test_pub_envelopes_and_immutable_edition_snapshot_bytes_are_unchanged(self):
        # Golden SHA-256 recorded from pre-change 76fc710b synthetic fixtures.
        for kind, value, digest in [
            ('thread', record(), 'f41c39b40b0591cd53801a086cb88fdd5dad9aecb378eb18caf14a1c7468d25b'),
            ('edition', edition_fixtures.EditionStorageTests().snapshot(), '4ce497cce2d9ab36e3ffa498a03e963b7666c7e7c8120e6ab2208262bc6234b7')]:
            saved=envelope(kind,value,1)
            encoded=json.dumps(saved,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
            self.assertEqual(hashlib.sha256(encoded).hexdigest(),digest)
            self.assertEqual(validate_envelope(json.loads(json.dumps(saved))),saved)

    def test_candidate_discovery_render_mapping_storage_and_editions_keep_source_ids(self):
        for key in VALID:
            with self.subTest(key=key):
                selected=select_new_threads([registry_row(CanonicalKey=key,ReviewStatus='Needs Review')],
                    baseline_utc='2026-10-19T00:00:00Z',through_utc='2026-10-22T00:00:00Z')['new_threads']
                a=prepare_thread(selected[0],revision=1,recorded_at='2026-10-22T00:00:00Z',
                    native_input_reference='fixture:version-2',human_notes='Keep human text')
                saved=envelope('thread',a,1)
                self.assertEqual(saved['logical_id'],'thread:pubmed:39751157')
                self.assertEqual(json.loads(saved['payload_json'])['canonical_key'],key)
                self.assertIn(key,a['rendered_post']['plain_text'])
                self.assertEqual(a['render_input']['tier'],'possible')
                self.assertIsNone(a['delivery_receipt']['delivery_authority_reference'])
                self.assertIsNone(a['delivery_receipt']['post_reference'])
                self.assertEqual(transition(saved,copy.deepcopy(saved)),'unchanged')
                b=prepare_thread({**selected[0],'canonical_key':'PUB:ffff'},revision=2,
                    recorded_at='2026-10-22T00:00:00Z',native_input_reference='fixture:version-2',human_notes='Keep human text')
                with self.assertRaises(ValueError):transition(saved,envelope('thread',b,2))
                snap=prepare_edition_snapshot(preference(),selected,start_date='2026-10-19',end_date='2026-10-25')
                self.assertEqual(snap['result']['editions'][0]['publications'],[{'publication_key':'pubmed:39751157','tier':'possible'}])
                self.assertFalse(snap['delivered']); self.assertFalse(snap['authoritative'])
                self.assertEqual(transition(envelope('edition',snap,1),envelope('edition',snap,1)),'unchanged')

    def test_changed_candidate_reference_cannot_overwrite_prior_edition(self):
        from tests.test_e09_subscription_editions import discovered
        args=dict(subscription=preference(),start_date='2026-10-19',end_date='2026-10-25')
        a=prepare_edition_snapshot(discovered=[discovered(canonical_key='PMID:1')],**args)
        b=prepare_edition_snapshot(discovered=[discovered(canonical_key='PUB:abcd')],**args)
        self.assertEqual(a['result'],b['result'])
        self.assertNotEqual(a['edition_snapshot_id'],b['edition_snapshot_id'])
        saved=envelope('edition',a,1);before=copy.deepcopy(saved)
        with self.assertRaisesRegex(ValueError,'immutable'):
            transition(saved,envelope('edition',b,1))
        self.assertEqual(saved,before)

    def test_all_83_synthetic_candidate_rows_remain_temporally_held(self):
        rows=[native_row(i+1,DORA+f'1/{i+1}',field_19='10/20/2026 04:00:00') for i in range(67)]
        rows += [native_row(i+68,f'PMID:{i+1}',field_19='10/20/2026 04:00:00',
                    field_17='Included' if i<9 else 'Needs Review') for i in range(16)]
        original=copy.deepcopy(rows); result=packet(rows)
        self.assertEqual(result['disposition_counts'],{'unknown_first_observation':83})
        self.assertEqual(result['new']['new_threads'],[]);self.assertEqual(result['catch_up'],[])
        self.assertEqual(result['tier_counts'],{'possible':74,'confirmed':9})
        self.assertEqual(rows,original)
        self.assertEqual(result['accounting'][0]['native_etag'],'"2"')
        self.assertEqual(result['accounting'][0]['native_version'],'2.0')
        self.assertEqual(result['accounting'][0]['raw_first_observed'],'10/20/2026 04:00:00')

    def test_alias_unknown_time_and_placeholder_accounting_is_complete(self):
        rows=[native_row(1,'PMID:1'),native_row(2,'PMID:1',field_19=None),
              native_row(3,DORA+'1/2',field_20='10/21/2026 04:00:00'),
              native_row(4,field_1=None)]
        result=packet(rows)
        self.assertEqual(sum(result['disposition_counts'].values()),4)
        self.assertEqual([r['publication_key'] for r in result['new']['new_threads']],['qualification:row-3'])
        self.assertEqual(len(result['canonical_aliases_held_for_mapping_reconciliation']['PMID:1']),2)
        self.assertEqual(result['accounting'][2]['raw_last_observed'],'10/21/2026 04:00:00')
        self.assertIsNone(result['qualified_rows'][1]['LastObservedUTC'])

    def test_adapter_rejects_ambiguous_or_malformed_input_without_partial_selection(self):
        for rows in [[native_row(),native_row()], [native_row(),native_row(2,field_1='qualification:row-1')],
                     [native_row(field_2='PMID:01')], [native_row(**{'odata.etag':'*'})],
                     [native_row(OData__UIVersionString='1')], [native_row(field_17='Possible')],
                     [native_row(field_20='2026-10-19T00:00:00Z')],
                     [None], [native_row(Id=True)], [native_row(Id='1')],
                     [native_row(),{}]]:
            with self.subTest(rows=rows),self.assertRaises(ValueError): packet(rows)

    def test_emitted_graph_guard_accepts_only_strict_union_without_numeric_coercion(self):
        graph=definition('https://example.sharepoint.com/sites/qualification','aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa')
        expression=graph['actions']['Require_no_send_identity']['inputs']['content']['ok']
        # Build a valid PUB envelope, then substitute candidates at the guarded
        # input boundary to exercise the emitted graph independently of Python.
        a=record();e=envelope('thread',a,1)
        contexts={'body':{'Parse_thread':a,'Parse_envelope':e},'trigger':{'NoSendOnly':True},
                  'outputs':{'Native_rendered_post':a['rendered_post']}}
        for key in VALID+INVALID:
            a['canonical_key']=key;a['render_input']['canonical_key']=key
            try: accepted=evaluate_guard(expression,contexts)
            except (ValueError,IndexError): accepted=False
            with self.subTest(key=key):self.assertEqual(accepted,key in VALID)
        # Bypassing any part of the strict guard is not an admissible artifact.
        changed=copy.deepcopy(graph);changed['actions']['Require_no_send_identity']['inputs']['content']['ok']='@true'
        with self.assertRaises(ValueError):validate_no_send_definition(changed,
            'https://example.sharepoint.com/sites/qualification','aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa')

    def test_graph_guard_keeps_no_send_and_identity_checks_for_candidates(self):
        graph=definition('https://example.sharepoint.com/sites/qualification','aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa')
        expression=graph['actions']['Require_no_send_identity']['inputs']['content']['ok']
        for key in ['PMID:1',DORA+'1/2']:
            from tests.test_e09_thread_mapping import selection
            base=prepare_thread(selection(canonical_key=key),revision=1,
                recorded_at='2026-10-24T12:00:00Z',native_input_reference='fixture:v1')
            for change in ['none','send','authority','provider','identity','revision','render','qualification']:
                a=copy.deepcopy(base);e=envelope('thread',a,1)
                contexts={'body':{'Parse_thread':a,'Parse_envelope':e},
                    'trigger':{'NoSendOnly':True},'outputs':{'Native_rendered_post':copy.deepcopy(a['rendered_post'])}}
                if change=='send':contexts['trigger']['NoSendOnly']=False
                elif change=='authority':a['delivery_receipt']['delivery_authority_reference']='forged:authority'
                elif change=='provider':a['delivery_receipt']['post_reference']='forged:post'
                elif change=='identity':a['canonical_key']='PUB:abcd'
                elif change=='revision':a['revision']=2
                elif change=='render':a['rendered_post']['plain_text']='altered'
                elif change=='qualification':e['qualification_only']=False
                with self.subTest(key=key,change=change):
                    self.assertEqual(evaluate_guard(expression,contexts),change=='none')
