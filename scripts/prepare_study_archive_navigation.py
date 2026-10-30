"""Prepare local-only reuse of study archive directory navigation.

No network, deployment or refresh. SPDX-License-Identifier: Apache-2.0
"""
import base64
import copy

from scripts.deploy_report_definition import fingerprint, parts
from scripts.prepare_study_archive_path_fix import PATH

OLD = 'ReadStudy=(URL as text) as binary => let Site=Text.BeforeDelimiter(URL,"/Documents/"),Parts=Text.Split(Text.AfterDelimiter(URL,Site&"/"),"/"),Root=if Site=StudySite then StudyRoot else error "Study archive site drift",Folder=List.Accumulate(List.RemoveLastN(Parts,1),Root,(T,N)=>let Matches=Table.SelectRows(T,each [Name]=N or Uri.EscapeDataString([Name])=N) in if Table.RowCount(Matches)=1 and Value.Is(Matches{0}[Content],type table) then Matches{0}[Content] else error "Study archive folder missing or duplicated"),Matches=Table.SelectRows(Folder,each [Name]=List.Last(Parts) or Uri.EscapeDataString([Name])=List.Last(Parts)) in if Table.RowCount(Matches)=1 and Value.Is(Matches{0}[Content],type binary) then Binary.Buffer(Matches{0}[Content]) else error "Study archive file missing or duplicated"'

# Buffer lists of records, not file binaries or entire SharePoint libraries.
# Cache only directories explicitly referenced by StudyRows. Other archive users
# retain the accepted reader unchanged. No URI normalization merges identities.
NEW = '''StudyArchiveDirectory=(URL as text) as text => Text.BeforeDelimiter(URL,"/",{0,RelativePosition.FromEnd}),
    StudyArchiveDirectories=List.Buffer(List.Distinct(List.Transform(StudyRows[ArchiveFileURL],StudyArchiveDirectory))),
    StudyArchiveEntries=(Directory as text) as list => let
        URL=Directory&"/__navigation_only__",
        Site=Text.BeforeDelimiter(URL,"/Documents/"),
        Parts=Text.Split(Text.AfterDelimiter(URL,Site&"/"),"/"),
        Root=if Site=StudySite then StudyRoot else error "Study archive site drift",
        Folder=List.Accumulate(List.RemoveLastN(Parts,1),Root,(T,N)=>let Matches=Table.SelectRows(T,each [Name]=N or Uri.EscapeDataString([Name])=N) in if Table.RowCount(Matches)=1 and Value.Is(Matches{0}[Content],type table) then Matches{0}[Content] else error "Study archive folder missing or duplicated")
        in List.Buffer(Table.ToRecords(Folder)),
    StudyArchiveDirectoryCache=Record.FromList(List.Transform(StudyArchiveDirectories,StudyArchiveEntries),StudyArchiveDirectories),
    ReadStudyUncached=UNCACHED,
    ReadStudy=(URL as text) as binary => let
        Site=Text.BeforeDelimiter(URL,"/Documents/"),
        Directory=StudyArchiveDirectory(URL),
        Name=List.Last(Text.Split(URL,"/")),
        Entries=if Site<>StudySite then error "Study archive site drift" else Record.FieldOrDefault(StudyArchiveDirectoryCache,Directory,null),
        Matches=if Entries=null then {} else List.Select(Entries,each [Name]=Name or Uri.EscapeDataString([Name])=Name)
        in if Entries=null then ReadStudyUncached(URL) else if List.Count(Matches)=1 and Value.Is(Matches{0}[Content],type binary) then Binary.Buffer(Matches{0}[Content]) else error "Study archive file missing or duplicated"'''.replace('UNCACHED', OLD.split('ReadStudy=', 1)[1])


def prepare(model, *, expected_sha256):
    if fingerprint(model) != expected_sha256:
        raise ValueError('Exact model preimage required')
    original = parts(model)
    text = original[PATH].decode()
    if text.count(NEW) == 1:
        return {'candidate': copy.deepcopy(model), 'recovery': model,
                'changed_paths': [], 'runtime_verified': False}
    if text.count(OLD) != 1 or any(x in text for x in (
            'StudyArchiveDirectoryCache', 'ReadStudyUncached=', 'StudyArchiveEntries=')):
        raise ValueError('Study reader drift; reconcile before editing')
    if 'StudyRows=' not in text or text.index('StudyRows=') > text.index(OLD):
        raise ValueError('Existing study rows must precede reader')
    updated = text.replace(OLD, NEW, 1)
    candidate = copy.deepcopy(model)
    for part in candidate['definition']['parts']:
        if part['path'] == PATH:
            part['payload'] = base64.b64encode(updated.encode()).decode()
    return {'candidate': candidate, 'recovery': model, 'changed_paths': [PATH],
            'runtime_verified': False}
