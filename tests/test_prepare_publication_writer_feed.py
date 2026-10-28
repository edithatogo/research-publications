# SPDX-License-Identifier: Apache-2.0
import copy
import json
from pathlib import Path
import tempfile
import unittest
from scripts import prepare_publication_admission_packet as admission
from scripts import prepare_publication_writer_feed as feed
from scripts import prepare_publication_registry_bootstrap as core
from tests.test_prepare_publication_admission_packet import fixture,pins,AS_OF,replace_pubmed_title


def make_feed(*,max_part_records=1,max_part_bytes=80000,max_manifest_bytes=1000000,docs=None,files=None):
    if docs is None:docs,files=fixture()
    packet=admission.prepare(docs,files,expected_hashes=pins(docs),as_of=AS_OF)
    manifest,parts=feed.build(docs,files,packet,input_pins=pins(docs),packet_pin=packet['packet_sha256'],as_of=AS_OF,max_part_records=max_part_records,max_part_bytes=max_part_bytes,max_manifest_bytes=max_manifest_bytes)
    return docs,files,packet,manifest,parts


def repin(manifest):manifest['manifest_sha256']=core.sha({k:v for k,v in manifest.items() if k!='manifest_sha256'});return manifest['manifest_sha256']


class FeedTests(unittest.TestCase):
    def test_rebuilt_feed_is_complete_bounded_deterministic_and_unpublished(self):
        docs,files,packet,m,parts=make_feed();original=copy.deepcopy((docs,files,packet));rows=feed.validate(m,parts,expected_manifest_sha256=m['manifest_sha256'])
        self.assertEqual(len(rows),3);self.assertEqual(m['part_count'],4);self.assertTrue(m['parts'][-1]['terminal']);self.assertEqual(m['parts'][-1]['records'],0)
        self.assertTrue(all(len(raw)<=80000 for raw in parts.values()));self.assertEqual((docs,files,packet),original)
        self.assertEqual((m,parts),make_feed()[3:]);self.assertFalse(m['publishing_authorized']);self.assertFalse(m['source_authority_qualified']);self.assertFalse(m['native_acceptance'])
        self.assertEqual(m['context']['input_pins'],pins(docs));self.assertEqual(m['context']['schema'],docs['schema'])

    def test_source_full_metadata_human_values_and_versions_remain_lossless(self):
        docs,files,p,m,parts=make_feed();rows=feed.validate(m,parts,expected_manifest_sha256=m['manifest_sha256'])
        self.assertEqual([r['proposal'] for r in rows],p['proposals'])
        existing=next(r for r in rows if r['SourceKey']=='pubmed:1')['proposal'];self.assertEqual(existing['retained_current'],docs['registry']['items'][0]);self.assertEqual(existing['proposed_observation'],{'LastObservedUTC':AS_OF})

    def test_admission_pin_and_full_rebuild_are_required(self):
        docs,files,p,m,parts=make_feed();p['proposals'][0]['proposed_observation']['ReviewNotes']='forged';p['packet_sha256']=core.sha({k:v for k,v in p.items() if k!='packet_sha256'})
        with self.assertRaises(ValueError):feed.build(docs,files,p,input_pins=pins(docs),packet_pin=p['packet_sha256'],as_of=AS_OF,max_part_records=1,max_part_bytes=80000,max_manifest_bytes=1000000)

    def test_atomic_record_bounds_never_truncate_or_split_values(self):
        docs,files=fixture();replace_pubmed_title(docs,files,'Long '+'😀'*300);_,_,p,m,parts=make_feed(docs=docs,files=files)
        rows=feed.validate(m,parts,expected_manifest_sha256=m['manifest_sha256']);self.assertEqual(next(r for r in rows if r['SourceKey']=='pubmed:2')['proposal']['proposed_values']['SourceFullTitle'],'Long '+'😀'*300)
        for records,limit in ((True,80000),(0,80000),(1,10),(1,False)):
            with self.subTest(records=records,limit=limit),self.assertRaises(ValueError):feed.build(docs,files,p,input_pins=pins(docs),packet_pin=p['packet_sha256'],as_of=AS_OF,max_part_records=records,max_part_bytes=limit,max_manifest_bytes=1000000)

    def test_changed_parts_counts_cursors_terminal_and_identities_fail(self):
        for fault in ('missing','extra','bytes','count','terminal','cursor','reorder','hash'):
            _,_,_,m,parts=make_feed();d=m['parts'][0];name=d['name']
            if fault=='missing':parts.pop(name)
            elif fault=='extra':parts['other']=parts[name]
            elif fault=='bytes':parts[name]+=b' '
            elif fault=='count':d['records']=False
            elif fault=='terminal':m['parts'].pop();parts.pop(next(reversed(parts)));m['part_count']-=1
            elif fault=='cursor':d['cursor_before']='not-start'
            elif fault=='reorder':m['parts'][0],m['parts'][1]=m['parts'][1],m['parts'][0]
            else:d['sha256']='0'*64
            with self.subTest(fault=fault),self.assertRaises(ValueError):feed.validate(m,parts,expected_manifest_sha256=repin(m))

    def test_rehashed_widened_update_is_not_a_valid_feed(self):
        _,_,_,m,parts=make_feed();d=m['parts'][0];part=core.decode_json(parts[d['name']]);row=part['rows'][0];row['proposal']['proposed_observation']['ReviewStatus']='Included';row['operation_id']=feed.operation(m['feed_id'],row['proposal'])['operation_id']
        parts[d['name']]=feed.wire(part);d.update(bytes=len(parts[d['name']]),sha256=core.bytes_sha(parts[d['name']]));all_rows=[r for desc in m['parts'] for r in core.decode_json(parts[desc['name']])['rows']];m['records_sha256']=core.sha(all_rows)
        with self.assertRaises(ValueError):feed.validate(m,parts,expected_manifest_sha256=repin(m))

    def test_manifest_pins_and_authority_flags_cannot_be_rebound(self):
        for fault in ('pin','context','writer','authority'):
            _,_,_,m,parts=make_feed();pin=m['manifest_sha256']
            if fault=='pin':m['record_count']+=1
            elif fault=='context':m['context']['target']['flow_id']='changed'
            elif fault=='writer':m['writer_capture_sha256']='0'*64
            else:m['publishing_authorized']=True
            if fault!='pin':pin=repin(m)
            with self.subTest(fault=fault),self.assertRaises(ValueError):feed.validate(m,parts,expected_manifest_sha256=pin)

    def test_part_encoding_is_exact_canonical_utf8(self):
        _,_,_,m,parts=make_feed();d=m['parts'][0];value=core.decode_json(parts[d['name']]);parts[d['name']]=json.dumps(value).encode('utf-16');d.update(bytes=len(parts[d['name']]),sha256=core.bytes_sha(parts[d['name']]))
        with self.assertRaises(ValueError):feed.validate(m,parts,expected_manifest_sha256=repin(m))

    def test_cli_same_read_hashes_exclusive_outputs_and_direct_minus_s(self):
        import contextlib,io,subprocess,sys
        docs,files,p,m,parts=make_feed();root=Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory(prefix='writer-feed-test-',dir=root/'private') as directory,contextlib.redirect_stderr(io.StringIO()):
            private=Path(directory);mapping={}
            for name,raw in files.items():path=private/name;path.write_bytes(raw);mapping[name]=str(path)
            for name,value in dict(inputs=docs,files=mapping,pins=pins(docs),packet={'kind':'publication_admission_local_result_v1','result':p}).items():(private/(name+'.json')).write_text(json.dumps(value))
            args=[v for name in ('inputs','files','pins','packet') for v in ('--'+name,str(private/(name+'.json')))]+['--packet-sha256',p['packet_sha256'],'--as-of',AS_OF,'--max-part-records','1','--max-part-bytes','80000','--max-manifest-bytes','1000000','--output',str(private/'feed.json')]
            result=subprocess.run([sys.executable,'-S',str(root/'scripts/prepare_publication_writer_feed.py'),*args],cwd=root,capture_output=True,text=True,timeout=20);self.assertEqual(result.returncode,0,result.stderr)
            out=private/'feed.json';raw=out.read_bytes();envelope=json.loads(raw);self.assertEqual(envelope['manifest'],m);self.assertEqual(envelope['source_files_sha256']['raw:pubmed.xml'],core.bytes_sha(files['pubmed.xml']))
            self.assertEqual(feed.main(args),2);self.assertEqual(out.read_bytes(),raw)
            args[-1]=str(private/'other.json');(private/'pins.json').write_text('{"bad":NaN}')
            self.assertEqual(feed.main(args),2);self.assertFalse((private/'other.json').exists())

    def test_manifest_has_an_explicit_byte_budget_and_independent_binding_inventory(self):
        docs,files,p,m,parts=make_feed()
        with self.assertRaises(ValueError):feed.build(docs,files,p,input_pins=pins(docs),packet_pin=p['packet_sha256'],as_of=AS_OF,max_part_records=1,max_part_bytes=80000,max_manifest_bytes=10)
        self.assertLessEqual(len(feed.wire(m)),m['context']['max_manifest_bytes'])
        m['bindings'].pop()
        with self.assertRaises(ValueError):feed.validate(m,parts,expected_manifest_sha256=repin(m))

    def test_error_envelopes_and_forged_committed_status_are_not_candidate_feeds(self):
        for fault in ('errors','committed'):
            _,_,_,m,parts=make_feed()
            if fault=='errors':m['errors']={}
            else:m['status']='COMMITTED'
            with self.subTest(fault=fault),self.assertRaises(ValueError):feed.validate(m,parts,expected_manifest_sha256=repin(m))
