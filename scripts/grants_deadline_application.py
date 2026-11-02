"""Prepare the reviewed override append and the dated internal deadline reader."""
import argparse
import base64
import copy
import json
import re
from pathlib import Path
from uuid import UUID

from scripts.grants_internal_deadlines import canonical, plan
from scripts.prepare_live_grants_calendar import branch, compose, envelope, guard, manual, spo
from scripts.deploy_report_definition import parts
from scripts.prepare_dashboard_overview import SCHEMA, projection
from scripts.prepare_grantconnect_history_reader import replace_part
from scripts.prepare_outcome_reader import emit

TABLE = 'GrantInternalDeadlines'
FIELDS = ('OpportunityTitle', 'OpportunityKey', 'AnchorDeadlineKey', 'SourceDate', 'CalculatedDate', 'EffectiveDate',
          'Disposition', 'PolicyVersionKey', 'OverrideKey', 'SourceVersion', 'Revision', 'AsOf')


def prepare_override(context, snapshot, row, **options):
    current = copy.deepcopy(snapshot)
    encoded = canonical(row)
    key = row['OverrideKey']
    existing = [item for item in current['overrides'] if item['OverrideKey'] == key]
    if existing and (len(existing) != 1 or json.loads(existing[0]['OverrideJson']) != row):
        raise ValueError('Conflicting immutable override version')
    if not existing:
        current['overrides'].append({'OverrideKey': key, 'OverrideJson': encoded})
    assessed = plan(current, **options)['override_assessments']
    if not any(item['OverrideKey'] == key and item['MatchesCurrentInputs'] for item in assessed):
        raise ValueError('Override requires a current policy and confirmed matching anchor')
    items = "_api/web/lists(guid'" + str(UUID(context['override_id'])) + "')/items"
    lookup = items + "?$select=OverrideKey,OverrideJson&$top=2&$filter=OverrideKey eq '" + key + "'"
    payload = canonical({'Title':key, 'OverrideKey':key, 'OverrideJson':encoded})
    actions = {'Payload':compose("@json(base64ToString('" + base64.b64encode(payload.encode()).decode() + "'))"),
               'Existing':spo(context,'GET',lookup,'Payload'),
               'Append':branch("@empty(body('Existing')?['value'])",
                   {'Create':spo(context,'POST',items,body="@outputs('Payload')")},previous='Existing'),
               'Saved':spo(context,'GET',lookup,'Append'),
               'Exact':guard("and(equals(length(body('Saved')?['value']),1),equals(first(body('Saved')?['value'])?['OverrideJson'],outputs('Payload')?['OverrideJson']))",'Saved')}
    projected = plan(current, **options)['rows']
    selected = next((entry for entry in projected if entry['AnchorDeadlineKey'] == row['AnchorDeadlineKey']
                     and entry['PolicyKey'] == row['PolicyKey'] and entry['PolicyVersion'] == row['PolicyVersion']), None)
    if selected is None:
        raise ValueError('An applicable approved policy is required')
    anchor = next(a for a in snapshot['calendar'] if a['DeadlineKey'] == row['AnchorDeadlineKey'])
    policy = next(a for a in snapshot['policies'] if a['PolicyVersionKey'] == selected['PolicyVersionKey'])
    previous = 'Payload'
    for label, list_id, item in [('Anchor', 'calendar_id', anchor), ('Policy', 'policy_id', policy)]:
        identity = int(item['Id'])
        version = item['odata.etag']
        if identity < 1 or not re.fullmatch(r'"[0-9]+"', version):
            raise ValueError('Versioned native item required')
        uri = "_api/web/lists(guid'" + str(UUID(context[list_id])) + "')/items(" + str(identity) + ")?$select=Id"
        actions[label] = spo(context, 'GET', uri, previous)
        previous = label + 'Matches'
        actions[previous] = guard("equals(body('" + label + "')?['odata.etag'],'" + version + "')",label)
    actions['Existing']['runAfter'] = {previous:['Succeeded']}
    return {'definition':envelope(actions,manual()),'connectionReferences':{'shared_sharepointonline':{
        'id':'/providers/Microsoft.PowerApps/apis/shared_sharepointonline',
        'connectionName':context['sharepoint_connection'],'source':'Embedded'}}}


def application(snapshot, *, require_applied=False, **options):
    result = plan(snapshot, **options)
    if require_applied:
        expected = {row['DeadlineKey']: row for row in result['rows'] if row['EffectiveDate']}
        saved = {row['DeadlineKey']: row for row in snapshot['calendar']
                 if str(row.get('DeadlineKey', '')).startswith('INTERNAL:') and row.get('Cancelled') is not True}
        if set(expected) != set(saved):
            raise ValueError('Reconcile applied calendar membership before publishing internal dates')
        for key, row in expected.items():
            actual = saved[key]
            if (actual.get('Revision') != row['Revision'] or actual.get('RevisionApplied') is not True
                    or actual.get('OpportunityKey') != row['OpportunityKey']
                    or actual.get('Calendar_x0020_day') != row['EffectiveDate']):
                raise ValueError('Reconcile applied calendar version and effective date')
    anchors = {row['DeadlineKey']: row for row in snapshot['calendar']}
    titles = {r['OpportunityKey']:r.get('Title') for r in snapshot['registry']}
    rows = []
    def add(anchor_key, disposition, values):
        anchor = anchors[anchor_key]
        rows.append(dict(OpportunityTitle=titles.get(anchor['OpportunityKey']), OpportunityKey=anchor['OpportunityKey'], AnchorDeadlineKey=anchor_key,
            SourceDate=anchor.get('Calendar_x0020_day'), Disposition=disposition, AsOf=result['as_of'],
            SourceVersion=anchor.get('odata.etag'), **{key:values.get(key) for key in
            ('CalculatedDate','EffectiveDate','PolicyVersionKey','OverrideKey','Revision')}))
    for row in result['rows']:
        add(row['AnchorDeadlineKey'], row['ReviewStatus'], row)
    for row in result['held']:
        add(row['DeadlineKey'], row['Reason'], {})
    return sorted(rows,key=lambda row:row['AnchorDeadlineKey'])


def reader(model, report, rows):
    model, report = copy.deepcopy(model), copy.deepcopy(report)
    mp, rp = parts(model), parts(report)
    path = 'definition/tables/' + TABLE + '.tmdl'
    page = 'definition/pages/' + TABLE + '/'
    if (path in mp) != (page+'page.json' in rp):
        raise ValueError('Incomplete existing deadline reader')
    payload = base64.b64encode(canonical(rows).encode()).decode()
    names = ', '.join(json.dumps(f) for f in FIELDS)
    tmdl = ['table '+TABLE]
    for f in FIELDS:
        tmdl.extend(['\tcolumn '+f,'\t\tdataType: string','\t\tsummarizeBy: none','\t\tsourceColumn: '+f])
    tmdl.extend(['\tpartition '+TABLE+' = m','\t\tmode: import','\t\tsource =',
        '\t\t\tTable.FromRecords(Json.Document(Binary.FromText("'+payload+'", BinaryEncoding.Base64)), {'+names+'}, MissingField.Error)'])
    if path in mp:
        replace_part(model,path,'\n'.join(tmdl)+'\n')
    else:
        emit(model,path,'\n'.join(tmdl)+'\n')
        root='definition/model.tmdl'
        replace_part(model,root,mp[root].decode()+'\nref table '+TABLE+'\n')
        order_path='definition/pages/pages.json'
        order=json.loads(rp[order_path]);order['pageOrder'].append(TABLE)
        replace_part(report,order_path,json.dumps(order))
        schema=json.loads(rp['definition/pages/'+order['pageOrder'][0]+'/page.json'])['$schema']
        emit(report,page+'page.json',json.dumps({'$schema':schema,'name':TABLE,'displayName':'Internal deadlines by snapshot date','height':1080,'width':1920,'displayOption':'FitToPage'}))
        emit(report,page+'visuals/deadlineRows/visual.json',json.dumps({'$schema':SCHEMA,'name':'deadlineRows',
            'position':{'x':24,'y':24,'width':1872,'height':1032,'z':0,'tabOrder':0},
            'visual':{'visualType':'tableEx','query':{'queryState':{'Values':{'projections':[projection(TABLE,f) for f in FIELDS]}}}}}))
    return model,report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('snapshot','evidence','organisation','as-of','output'):
        parser.add_argument('--'+name,required=True)
    for name in ('override','context','model','report'):
        parser.add_argument('--'+name)
    parser.add_argument('--apply-calendar',action='store_true')
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]/'private/ops'
    def private(value):
        path=Path(value).resolve()
        if not path.is_relative_to(root): raise ValueError('Private occurrence required')
        return path
    def read(value): return json.loads(private(value).read_bytes())
    snapshot=read(args.snapshot)
    options=dict(organisation=args.organisation,as_of=args.as_of,evidence_files=read(args.evidence))
    if args.apply_calendar:
        from scripts.grants_deadline_calendar import prepare
        packet=prepare(read(args.context),snapshot,**options)
    elif args.override:
        packet=prepare_override(read(args.context),snapshot,read(args.override),**options)
    else:
        rows=application(snapshot,require_applied=True,**options)
        model,report=reader(read(args.model),read(args.report),rows)
        packet={'rows':rows,'model':model,'report':report}
    with private(args.output).open('x') as handle: json.dump(packet,handle)


if __name__=='__main__': main()
