# Retained publication field-description profile — 29 October 2026

The integrator preserved the exact project-owned `publication-field-meanings-v1`
configuration from the original source checkout as
[publication-field-meanings.json](../config/publication-field-meanings.json).
SHA256: `c6a26c218d50f2ac7f4e5b4b437af0eec7d89ab09b847b4a5ce37bfca2e65d65`.
All 14 names are unique and all descriptions fit the existing 255-character bound.
There are no tenant identities, credentials, records or bindings in this profile.

This is a retained description proposal, not current native schema or writer
qualification. Its internal names, field types, full-title destination and
processing-timestamp semantics must be checked against the selected current
list and writer before adoption. A mismatch is a qualification failure; it does
not authorize creating fields, changing types, renaming values, shortening source
text or changing the writer. In particular, the retained Authors and affiliation
Note-field assumptions and SourceFullTitle field are not evidence that another
target supports them.

The descriptions distinguish source keys from canonical publication/person
identities, author labels from resolved people, unknown dates from processing
stamps, and retained review text from correction authority. Their exact historical
wording is preserved for review; future amendments need their own version and
consumer comparison. No description has been saved to SharePoint by this import.

The related bootstrap/helper packet must bind its proposed descriptions to the
complete current preimage and preserve ETags, rows, versions, views, unrelated
field settings and recoverable previous descriptions. Capture, native mutation
and generated migration commands remain outside that offline source assignment.
