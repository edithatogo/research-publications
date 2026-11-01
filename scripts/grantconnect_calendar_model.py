"""Add official confirmed GrantConnect dates to the existing calendar partition."""
from copy import deepcopy
from base64 import b64decode, b64encode

PATH = 'definition/tables/Funding Calendar.tmdl'
ORIGINAL = 'each [RevisionApplied] = true and [ReviewStatus] = "Reviewed"'
CONFIRMED = '''each [RevisionApplied] = true and ([ReviewStatus] = "Reviewed" or ([ReviewStatus] = "Source confirmed" and Text.StartsWith([DeadlineKey], "GC-CLOSE:") and [Calendar day] <> null and [Revision] <> null))'''


def prepare(before):
    result = deepcopy(before)
    part, = [p for p in result['definition']['parts'] if p['path'] == PATH]
    original = b64decode(part['payload'], validate=True).decode()
    if original.count(ORIGINAL) != 1:
        raise ValueError('Calendar partition preimage drift')
    part['payload'] = b64encode(original.replace(ORIGINAL, CONFIRMED).encode()).decode()
    return result
