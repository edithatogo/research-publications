# SPDX-License-Identifier: Apache-2.0
import copy
import unittest
from pathlib import Path
import tempfile
from unittest.mock import patch
from scripts.grants_calendar import build_native_calendar_export, write_native_calendar_export

ROW={'DeadlineKey':'fixture:1','Title':'Fictional call','ReviewStatus':'Reviewed','RevisionApplied':True,'DeadlinePrecision':'day','Calendar_x0020_day':'2026-11-30','CalculatedDate':'2026-11-29T14:00:00Z','Cancelled':False,'SourceURL':{'Url':'https://example.invalid/grant'},'odata.etag':'"2"'}

class NativeCalendarExportTests(unittest.TestCase):
    def export(self,rows):return build_native_calendar_export(rows,generated_utc='2026-10-27T05:00:00Z')

    def test_uses_source_day_and_filters_uncommitted_or_unreviewed_rows(self):
        result=self.export([ROW,{**ROW,'DeadlineKey':'pending','RevisionApplied':False},{**ROW,'DeadlineKey':'unreviewed','ReviewStatus':'Needs Review'}])
        self.assertEqual(result.count('BEGIN:VEVENT'),1)
        self.assertIn('DTSTART;VALUE=DATE:20261130',result)
        self.assertNotIn('20261129',result)
        self.assertIn('CLASS:PRIVATE',result)
        self.assertIn('TRANSP:TRANSPARENT',result)
        self.assertNotIn('VALARM',result)
        self.assertNotIn('ATTENDEE',result)

    def test_changed_day_and_cancellation_preserve_uid_and_advance_sequence(self):
        initial=self.export([ROW])
        changed=self.export([{**ROW,'Calendar_x0020_day':'2026-12-01','odata.etag':'"3"'}])
        cancelled=self.export([{**ROW,'Cancelled':True,'odata.etag':'"4"'}])
        uid=lambda text:next(line for line in text.splitlines() if line.startswith('UID:'))
        self.assertEqual(uid(initial),uid(changed));self.assertEqual(uid(changed),uid(cancelled))
        self.assertIn('SEQUENCE:3',changed);self.assertIn('SEQUENCE:4',cancelled)
        self.assertIn('STATUS:CANCELLED',cancelled)
        self.assertIn('SUMMARY:CANCELLED: Fictional call',cancelled)
        self.assertIn('TRANSP:TRANSPARENT',cancelled)

    def test_ambiguous_days_duplicate_keys_and_url_injection_fail_closed(self):
        for update in [{'Calendar_x0020_day':None},{'odata.etag':'"guid,2"'},{'SourceURL':'https://example.invalid/\r\nATTENDEE:evil'}]:
            with self.subTest(update=update),self.assertRaises(ValueError):self.export([{**ROW,**update}])
        with self.assertRaises(ValueError):self.export([ROW,copy.deepcopy(ROW)])

    def test_padded_source_url_and_conflicting_versions_are_not_normalized_into_events(self):
        for update in [{'SourceURL':' https://example.invalid/grant'},
                       {'@odata.etag':'"3"'},
                       {'DeadlineKey':False}, {'Cancelled':'false'}]:
            with self.subTest(update=update),self.assertRaises(ValueError):self.export([{**ROW,**update}])

    def test_month_precision_is_withheld_and_unicode_lines_remain_folded(self):
        self.assertEqual(self.export([{**ROW,'DeadlinePrecision':'month','Calendar_x0020_day':None}]).count('BEGIN:VEVENT'),0)
        result=self.export([{**ROW,'Title':'研究'*90+'; line\r\nATTENDEE:untrusted'}])
        self.assertTrue(all(len(line.encode('utf-8'))<=75 for line in result.split('\r\n')))
        self.assertNotIn('\r\nATTENDEE:',result)
        self.assertIn('\\nATTENDEE:',result.replace('\r\n ',''))

    def test_native_snapshot_output_is_private_exclusive_and_cannot_escape(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory).resolve();folder=root/'private'/'ops';folder.mkdir(parents=True)
            output=self.export([ROW]);target=folder/'snapshot.ics'
            with patch('scripts.grants_calendar._ROOT',root), patch('scripts.grants_calendar.subprocess.run') as ignored:
                write_native_calendar_export(target,output)
                ignored.assert_called_once()
                self.assertEqual(target.read_bytes(),output.encode('utf-8'))
                self.assertEqual(target.stat().st_mode & 0o777,0o600)
                with self.assertRaises(FileExistsError):write_native_calendar_export(target,'replacement')
                self.assertEqual(target.read_bytes(),output.encode('utf-8'))
                with self.assertRaises(ValueError):write_native_calendar_export(root/'public.ics',output)
                link=folder/'redirect.ics';link.symlink_to(folder/'missing.ics')
                with self.assertRaises(ValueError):write_native_calendar_export(link,output)
                self.assertFalse((folder/'missing.ics').exists())

if __name__=='__main__':unittest.main()
