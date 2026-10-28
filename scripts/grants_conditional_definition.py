"""Source-only conditional workflow definition adapter with injected transport.

No authentication, HTTP client, worker invocation or retry is provided here.
Caller-owned transports must honour max_redirects=0, retries=0 and the exact
request. Native row identity, concurrency support and ownership need separate
qualification; synthetic tests cannot establish those prerequisites.
"""
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import os
from pathlib import Path
import re
from urllib.parse import urlsplit
from uuid import UUID


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)


def _guid(value):
    if not isinstance(value, str) or value != str(UUID(value)):
        raise ValueError('Exact canonical native UUID required')
    return value


def _etag(row):
    value = row.get('@odata.etag')
    if not isinstance(value, str) or not re.fullmatch(r'(?:W/)?"[\x21\x23-\x7e]+"', value):
        raise ValueError('Exact non-wildcard row ETag required')
    return value


@dataclass(frozen=True)
class Binding:
    organization_url: str
    workflow_id: str
    flow_id: str
    environment: str

    def __post_init__(self):
        u = urlsplit(self.organization_url)
        if (u.scheme != 'https' or not u.hostname or u.username or u.password
                or u.path or u.query or u.fragment or self.organization_url != f'https://{u.netloc}'):
            raise ValueError('Exact canonical HTTPS organization origin required')
        _guid(self.workflow_id)
        _guid(self.flow_id)
        if not isinstance(self.environment, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', self.environment):
            raise ValueError('Exact environment identity required')

    @property
    def row_url(self):
        return self.organization_url + '/api/data/v9.2/workflows(' + self.workflow_id + ')'

    @property
    def metadata_url(self):
        return self.organization_url + "/api/data/v9.2/EntityDefinitions(LogicalName='workflow')?$select=LogicalName,IsOptimisticConcurrencyEnabled"

    @property
    def flow_url(self):
        return ('https://api.flow.microsoft.com/providers/Microsoft.ProcessSimple/environments/'
                + self.environment + '/flows/' + self.flow_id)


def _metadata(value):
    if (not isinstance(value, dict) or value.get('LogicalName') != 'workflow'
            or value.get('IsOptimisticConcurrencyEnabled') is not True):
        raise ValueError('Workflow optimistic concurrency remains an unqualified prerequisite')


def _client(row):
    if not isinstance(row, dict) or not isinstance(row.get('clientdata'), str):
        raise ValueError('Complete workflow row/clientdata required')
    value = json.loads(row['clientdata'])
    if (not isinstance(value, dict) or not isinstance(value.get('properties'), dict)
            or not isinstance(value['properties'].get('definition'), dict)
            or not isinstance(value['properties'].get('connectionReferences'), dict)):
        raise ValueError('Complete clientdata definition and connections required')
    return value


def _flow(binding, value):
    if (not isinstance(value, dict) or value.get('name') != binding.flow_id
            or value.get('id') != urlsplit(binding.flow_url).path):
        raise ValueError('Exact Flow management identity required')
    props = value.get('properties')
    if (not isinstance(props, dict) or props.get('workflowEntityId') != binding.workflow_id
            or not isinstance(props.get('definition'), dict)
            or not isinstance(props.get('connectionReferences'), dict)
            or not isinstance(props.get('state'), str) or not props['state']
            or type(props.get('flowFailureAlertSubscribed')) is not bool):
        raise ValueError('Exact workflow row binding and complete Flow boundaries required')
    return props


def _row(binding, value):
    if (not isinstance(value, dict) or value.get('workflowid') != binding.workflow_id
            or type(value.get('statecode')) is not int or type(value.get('statuscode')) is not int):
        raise ValueError('Exact workflow row identity/state required')
    _etag(value)
    return _client(value)


@dataclass(frozen=True)
class SavePlan:
    operation_id: str
    owner: str
    binding: Binding
    row_json: str
    flow_json: str
    candidate_clientdata: str

    @property
    def fingerprint(self):
        return sha256(_json(asdict(self)).encode()).hexdigest()

    @property
    def journal_key(self):
        return sha256((self.binding.row_url + '\n' + self.operation_id).encode()).hexdigest()


def prepare_save(*, operation_id, owner, binding, metadata, row, flow, definition):
    """Freeze only a definition change, preserving every other clientdata value."""
    if not isinstance(operation_id, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', operation_id):
        raise ValueError('Stable owned operation identity required')
    if not isinstance(owner, str) or not owner or owner != owner.strip():
        raise ValueError('Explicit exclusive native owner prerequisite required')
    _metadata(metadata)
    client = _row(binding, row)
    props = _flow(binding, flow)
    if (props['definition'] != client['properties']['definition']
            or props['connectionReferences'] != client['properties']['connectionReferences']):
        raise ValueError('Dataverse and Flow preimages disagree')
    if not isinstance(definition, dict) or definition == props['definition']:
        raise ValueError('A distinct frozen definition object is required')
    # JSON round trip prevents the caller retaining mutable references to a plan.
    candidate = json.loads(_json(client))
    candidate['properties']['definition'] = json.loads(_json(definition))
    return SavePlan(operation_id, owner, binding, _json(row), _json(flow), _json(candidate))


class FileJournal:
    """Exclusive durable local receipts. Supply an owned ignored private directory."""
    def __init__(self, directory):
        self.directory = Path(directory)
        self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)

    def write_once(self, key, label, value):
        if not re.fullmatch(r'[a-f0-9]{64}', key) or not re.fullmatch(r'[a-z-]+', label):
            raise ValueError('Safe journal key and label required')
        target = self.directory / (key + '-' + label + '.json')
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w') as stream:
            stream.write(_json(value) + '\n')
            stream.flush()
            os.fsync(stream.fileno())
        directory_fd = os.open(self.directory, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)

    def read(self, key, label):
        if not re.fullmatch(r'[a-f0-9]{64}', key) or not re.fullmatch(r'[a-z-]+', label):
            raise ValueError('Safe journal key and label required')
        return json.loads((self.directory / (key + '-' + label + '.json')).read_text())

    def contains(self, key, label):
        if not re.fullmatch(r'[a-f0-9]{64}', key) or not re.fullmatch(r'[a-z-]+', label):
            raise ValueError('Safe journal key and label required')
        try:
            (self.directory / (key + '-' + label + '.json')).lstat()
            return True
        except FileNotFoundError:
            return False


# Only service-owned row revision/time fields are excluded. Other changes,
# including connections, state and arbitrary clientdata, stop the operation.
_REVISION_FIELDS = {'@odata.etag', 'versionnumber', 'modifiedon'}


def _same_row(left, right):
    def business(row):
        result = {k: v for k, v in row.items() if k not in _REVISION_FIELDS}
        result['clientdata'] = _client(row)
        return result
    return business(left) == business(right)


def _request(transport, method, url, *, headers=None, body=None):
    return transport(method=method, url=url, headers=headers or {}, body=body,
                     max_redirects=0, retries=0, timeout_seconds=30)


def _get(transport, url):
    response = _request(transport, 'GET', url)
    if not isinstance(response, dict) or type(response.get('status')) is not int or response['status'] != 200:
        raise ValueError('Exact complete HTTP200 read required')
    if not isinstance(response.get('body'), dict):
        raise ValueError('Complete object response required')
    return response['body']


def _snapshot(plan, transport):
    _metadata(_get(transport, plan.binding.metadata_url))
    row = _get(transport, plan.binding.row_url)
    flow = _get(transport, plan.binding.flow_url + '?api-version=2016-11-01')
    _row(plan.binding, row)
    _flow(plan.binding, flow)
    return row, flow


def _matches(plan, row, flow, clientdata):
    before = json.loads(plan.row_json)
    expected = {**before, 'clientdata': clientdata}
    props = _flow(plan.binding, flow)
    original = json.loads(plan.flow_json)['properties']
    client = json.loads(clientdata)
    return (_same_row(row, expected)
            and props['definition'] == client['properties']['definition']
            and all(props[k] == original[k] for k in
                    ['state', 'workflowEntityId', 'connectionReferences', 'flowFailureAlertSubscribed']))


def _finish(plan, journal, label, status, reason, submitted, **details):
    result = {'status': status, 'reason': reason, 'patch_submitted': submitted,
              'plan_sha256': plan.fingerprint, 'invocation_allowed': False,
              'automatic_retry': False, **details}
    try:
        journal.write_once(plan.journal_key, label + '-outcome', result)
    except OSError:
        return {**result, 'status': 'quarantined', 'reason': 'receipt_write_failed'}
    return result


def _apply(plan, transport, journal, *, rollback):
    label = 'rollback' if rollback else 'save'
    original = json.loads(plan.row_json)
    # Validate a reconstructed plan, including preservation of all non-definition
    # clientdata. This also catches accidental dataclasses.replace() corruption.
    candidate = json.loads(plan.candidate_clientdata)
    props = candidate.get('properties', {}) if isinstance(candidate, dict) else {}
    verified = prepare_save(operation_id=plan.operation_id, owner=plan.owner, binding=plan.binding,
                            metadata={'LogicalName': 'workflow', 'IsOptimisticConcurrencyEnabled': True},
                            row=original, flow=json.loads(plan.flow_json), definition=props.get('definition'))
    if verified != plan:
        raise ValueError('Frozen plan altered outside definition scope')
    if any(journal.contains(plan.journal_key, label + suffix) for suffix in ['-intent', '-outcome']):
        return {'status': 'quarantined', 'reason': 'prior_intent_or_outcome_preserved',
                'patch_submitted': False, 'invocation_allowed': False, 'automatic_retry': False}
    if rollback:
        try:
            outcome = journal.read(plan.journal_key, 'save-outcome')
            intent = journal.read(plan.journal_key, 'save-intent')
        except (OSError, ValueError):
            return {'status': 'quarantined', 'reason': 'verified_owned_save_required', 'patch_submitted': False, 'invocation_allowed': False}
        if (outcome.get('status') != 'saved' or outcome.get('plan_sha256') != plan.fingerprint
                or intent.get('plan_sha256') != plan.fingerprint):
            return {'status': 'quarantined', 'reason': 'verified_owned_save_required', 'patch_submitted': False, 'invocation_allowed': False}
    try:
        current, flow = _snapshot(plan, transport)
        current_client = plan.candidate_clientdata if rollback else original['clientdata']
        if not _matches(plan, current, flow, current_client) or (not rollback and _etag(current) != _etag(original)):
            return _finish(plan, journal, label, 'quarantined', 'preimage_changed', False)
    except Exception:
        return _finish(plan, journal, label, 'quarantined', 'preflight_unqualified', False)
    desired = original['clientdata'] if rollback else plan.candidate_clientdata
    body = {'clientdata': desired}
    intent = {'plan_sha256': plan.fingerprint, 'plan': asdict(plan), 'method': 'PATCH',
              'url': plan.binding.row_url, 'etag': _etag(current), 'body': body,
              'one_send': True, 'rollback': rollback}
    try:
        journal.write_once(plan.journal_key, label + '-intent', intent)
    except FileExistsError:
        return {'status': 'quarantined', 'reason': 'prior_intent_preserved', 'patch_submitted': False, 'invocation_allowed': False}
    # If durable intent creation fails for another reason, propagate without a
    # request; a partial/existing intent still prevents replay on the next call.
    try:
        response = _request(transport, 'PATCH', plan.binding.row_url,
                            headers={'If-Match': _etag(current), 'Content-Type': 'application/json'}, body=body)
    except Exception:
        return _finish(plan, journal, label, 'quarantined', 'save_transport_uncertain', True)
    status = response.get('status') if isinstance(response, dict) else None
    if type(status) is not int or status not in [200, 204]:
        return _finish(plan, journal, label, 'quarantined', 'precondition_failed' if status == 412 else 'save_not_accepted', True)
    try:
        after, flow_after = _snapshot(plan, transport)
        if not _matches(plan, after, flow_after, desired) or _etag(after) == _etag(current):
            return _finish(plan, journal, label, 'quarantined', 'readback_mismatch', True)
    except Exception:
        return _finish(plan, journal, label, 'quarantined', 'readback_unqualified', True)
    return _finish(plan, journal, label, 'rolled_back' if rollback else 'saved', 'exact_readbacks_verified', True,
                   row_etag=_etag(after), row=after, flow=flow_after)


def save_definition(plan, *, transport, journal):
    return _apply(plan, transport, journal, rollback=False)


def rollback_definition(plan, *, transport, journal):
    """Only a verified owned candidate can be restored, under its fresh ETag."""
    return _apply(plan, transport, journal, rollback=True)
