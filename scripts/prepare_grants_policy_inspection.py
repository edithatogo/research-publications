"""Bounded read-only qualification of the retained policy/override storage.

No policy creation/approval, deadline mutation, email or scheduled trigger.
SPDX-License-Identifier: Apache-2.0
"""
from uuid import UUID

from scripts.prepare_live_grants_calendar import after, compose, envelope, guard, manual, query, spo


def build(value):
    c = dict(value)
    for k in ['policy_id', 'override_id', 'calendar_id', 'registry_id']:
        c[k] = str(UUID(c[k]))
    a = {'Operator': spo(c, 'GET', '_api/web/currentuser?$select=Id,Email'),
         'Owner': guard("equals(toLower(body('Operator')?['Email']),'" + c['operator_email'].lower() + "')", 'Operator')}
    prev = 'Owner'
    for name, key, fields in [('Policies', 'policy_id', 'Id,Title,PolicyVersionKey,PolicyJson'),
                              ('Overrides', 'override_id', 'Id,Title,OverrideKey,OverrideJson'),
                              ('Calendar', 'calendar_id', 'Id,DeadlineKey,OpportunityKey,Title,Calendar_x0020_day,RevisionApplied,ReviewStatus,DeadlinePrecision,Cancelled,SourceURL,Revision'),
                              ('Registry', 'registry_id', 'Id,OpportunityKey,Source,URL,EvidenceHash')]:
        root = "_api/web/lists(guid'" + c[key] + "')"
        if name in ['Policies', 'Overrides']:
            a[name + '_metadata'] = spo(c, 'GET', root + '?$select=Id,Title,EnableVersioning,ItemCount', prev)
            a[name + '_versioned'] = guard("equals(body('" + name + "_metadata')?['EnableVersioning'],true)", name + '_metadata')
            a[name + '_fields'] = spo(c, 'GET', root + '/fields?$select=InternalName,TypeAsString,Required,EnforceUniqueValues&$top=500', name + '_versioned')
            prev = name + '_fields'
        a[name] = spo(c, 'GET', root + '/items?$select=' + fields + '&$top=5000', prev)
        a[name + '_complete'] = guard("and(empty(body('" + name + "')?['odata.nextLink']),empty(body('" + name + "')?['@odata.nextLink']))", name)
        prev = name + '_complete'
    a['Bound_policies'] = query("@body('Policies')?['value']", "@and(startsWith(coalesce(item()?['PolicyVersionKey'],''),'POLICY:'),equals(json(item()?['PolicyJson'])?['SchemaVersion'],'rims-approved-policy-v1'),equals(json(item()?['PolicyJson'])?['Authority']?['Status'],'Approved'))", prev)
    a['Snapshot'] = compose({name.lower(): "@body('" + name + "')?['value']" for name in ['Policies', 'Overrides', 'Calendar', 'Registry']}, 'Bound_policies')
    a['Summary'] = compose({'PolicyRows': "@length(body('Policies')?['value'])", 'AuthorityBoundPolicies': "@length(body('Bound_policies'))", 'OverrideRows': "@length(body('Overrides')?['value'])", 'SourceCalendarRows': "@length(body('Calendar')?['value'])", 'NativeWrites': 0}, 'Snapshot')
    refs = {'shared_sharepointonline': {'id': '/providers/Microsoft.PowerApps/apis/shared_sharepointonline',
              'connectionName': c['sharepoint_connection'], 'source': 'Embedded'}}
    return {'definition': envelope(a, manual()), 'connectionReferences': refs}
