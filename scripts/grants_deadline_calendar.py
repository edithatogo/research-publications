"""Build a manual, snapshot-bound FlowAgent calendar application."""
from uuid import UUID

from scripts.grants_internal_deadlines import plan
from scripts.prepare_live_grants_calendar import compose, envelope, guard, manual, spo


def prepare(context, snapshot, **options):
    decisions = plan(snapshot, **options)
    actions = {}
    previous = ''
    # Detect added/removed rows as well as changed source, policy or review versions.
    for name, binding in [('policies','policy_id'),('overrides','override_id'),
                          ('registry','registry_id'),('calendar','calendar_id')]:
        uri = "_api/web/lists(guid'" + str(UUID(context[binding])) + "')/items"
        actions[name] = spo(context,'GET',uri+'?$select=Id&$orderby=Id&$top=5000',previous)
        rows = sorted(snapshot[name],key=lambda row: int(row['Id']))
        import re
        if len(rows)>5000 or any(not re.fullmatch(r'"[0-9]+"',r['odata.etag']) for r in rows):
            raise ValueError('Complete versioned snapshot required')
        expected = [str(r['Id']) + '/' + r['odata.etag'] for r in rows]
        select = name+'Versions'
        actions[select] = {'type':'Select','runAfter':{name:['Succeeded']},'inputs':{
            'from':"@body('"+name+"')?['value']", 'select':"@concat(string(item()?['Id']),'/',item()?['odata.etag'])"}}
        previous = name+'Current'
        actions[previous] = guard("and(empty(body('"+name+"')?['odata.nextLink']),empty(body('"+name+"')?['@odata.nextLink']),equals(join(body('"+select+"'),'|'),'"+'|'.join(expected)+"'))",select)
    root = "_api/web/lists(guid'" + str(UUID(context['calendar_id'])) + "')/items"
    existing = {r['DeadlineKey']:r for r in snapshot['calendar'] if str(r.get('DeadlineKey','')).startswith('INTERNAL:')}
    planned = {r['DeadlineKey']:r for r in decisions['rows']}
    keys = sorted(set(existing)|set(planned))
    if keys:
        actions['CurrentDay'] = guard("equals(convertTimeZone(utcNow(),'UTC','E. Australia Standard Time','yyyy-MM-dd'),'"+options['as_of']+"')",previous)
        previous = 'CurrentDay'
    mutations = 0
    for ordinal,key in enumerate(keys):
        old, row = existing.get(key), planned.get(key)
        if old and (old.get('Title') != 'RIMS internal deadline '+key or
                    old.get('ReviewStatus') not in ('Policy backed','Held by policy') or
                    (row and old.get('OpportunityKey') != row['OpportunityKey'])):
            raise ValueError('Internal calendar ownership conflict')
        day = row['EffectiveDate'] if row else None
        if not old and day is None:
            continue
        data = {'Title':'RIMS internal deadline '+key,'DeadlineKey':key,
                'OpportunityKey':row['OpportunityKey'] if row else old['OpportunityKey'],
                'CalculatedDate':day+'T00:00:00Z' if day else None,
                'Calendar_x0020_day':day,'Cancelled':day is None,'RevisionApplied':True,
                'ReviewStatus':'Policy backed' if day else 'Held by policy',
                'Revision':row['Revision'] if row else 'held','DeadlinePrecision':'day' if day else 'unknown'}
        if row: data['PolicyKey']=row['PolicyKey']
        if old and old.get('Revision')==data['Revision'] and old.get('Calendar_x0020_day')==day and old.get('Cancelled')==data['Cancelled']:
            continue
        import base64,json
        payload=base64.b64encode(json.dumps(data).encode()).decode()
        action='Apply'+str(ordinal)
        actions[action]=spo(context,'POST',root+'('+str(int(old['Id']))+')' if old else root,
                            previous,body="@json(base64ToString('"+payload+"'))",
                            etag=old['odata.etag'] if old else None)
        previous=action
        mutations+=1
    actions['Result']=compose({'PlannedWrites':mutations,'Held':len(decisions['held']),
                               'SnapshotDay':options['as_of']},previous)
    refs={'shared_sharepointonline':{'id':'/providers/Microsoft.PowerApps/apis/shared_sharepointonline',
          'connectionName':context['sharepoint_connection'],'source':'Embedded'}}
    return {'definition':envelope(actions,manual()),'connectionReferences':refs}
