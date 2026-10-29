"""Map verified bounded Activities capture into existing source-assertion fields.

No native writes, affiliation decisions or award/publication relationships.
"""
import hashlib
import json
import re
from urllib.parse import quote

from scripts.ardc_activity_batch import validate_batch
from scripts.ardc_secondary_filter import filter_responses
from scripts.filter_ardc_sharepoint_archive import archive_target


def build(raw, native, capture, reconciliation_raw, aliases, credential):
    reconciliation = json.loads(reconciliation_raw)
    digest = hashlib.sha256(raw).hexdigest()
    if (native.get('format') != 'ardc-bounded-increment-native-delivery-v1'
            or native.get('exact_bytes_verified') is not True
            or native.get('sha256') != digest or native.get('bytes') != len(raw)
            or capture.get('exact_ids_and_source_keys_verified') is not True
            or capture.get('response_sha256') != digest
            or capture.get('source_reconciliation_sha256') != hashlib.sha256(reconciliation_raw).hexdigest()
            or reconciliation.get('stored_generation_reconciled') is not True
            or capture.get('manifest_sha256') != reconciliation.get('manifest_sha256')):
        raise ValueError('Verified bounded native capture and lineage required')
    rows = validate_batch(raw, reconciliation['activities'], credential)
    if capture.get('records') != len(rows) or native.get('records') != len(rows):
        raise ValueError('Capture count differs')
    target = native['target']
    site, folder = archive_target({'ardcActivitiesArchiveTarget': target,
                                  'resources': [target['site'].split('/personal/')[0].split('/sites/')[0]]})
    name = native['name']
    if not isinstance(name, str) or re.fullmatch(r'activities-batch-[0-9]{9}\.json', name) is None:
        raise ValueError('Unsafe native filename')
    archive_url = site + quote(folder + '/' + name, safe='/')
    projection = filter_responses([(name, raw)], aliases)
    candidates = {r['activity_id']: r['matches'] for r in projection['candidates']}
    result = []
    for identity, record in rows.items():
        summary = record.get('title') or identity
        if not isinstance(summary, str):
            raise ValueError('Invalid activity title')
        context = {'activity': record, 'matches': candidates.get(identity, []),
                   'affiliation_confirmed': False, 'business_relationship_confirmed': False}
        provenance = {'archive_url': archive_url, 'raw_sha256': digest,
                      'registry_key': record['key'], 'observed_utc': capture['captured_at'],
                      'manifest_sha256': capture['manifest_sha256'],
                      'reconciliation_sha256': capture['source_reconciliation_sha256'],
                      'alias_sha256': projection['alias_sha256'],
                      'source_complete_verified': False, 'current_snapshot_verified': False,
                      'scope': 'reconciled_increment_exact_activity_ids'}
        result.append({'Title': summary[:255], 'FullSummary': summary,
                       'SourceKey': 'ardc-lookup:activity:' + identity, 'Source': 'ARDC',
                       'ContextKind': 'research_activity_candidate' if identity in candidates else 'research_activity_source_context',
                       'SourceID': identity, 'RelatedID': '', 'SourceURL': archive_url,
                       'SourceProjectionJSON': json.dumps(context, ensure_ascii=False),
                       'SourceProvenanceJSON': json.dumps(provenance, ensure_ascii=False)})
    return result
