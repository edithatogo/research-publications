"""Plan and submit version-bound grants notices for the sole configured operator.

Only native-reviewed, classification-current records and active private rules can
reach the worker. Existing ledger identities always suppress automatic resend.
"""
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
import base64,copy,hashlib,html,json,re,subprocess,time,urllib.request
from datetime import datetime
from pathlib import Path
from uuid import UUID
from zoneinfo import ZoneInfo
from scripts.prepare_grants_delivery_worker import build


def preference(row):
    result=dict(row)
    for source,target in [('EventTypesJSON','EventTypes'),('ReminderOffsetsJSON','ReminderOffsets')]:
        result[target]=json.loads(row[source])
    if (not isinstance(result['EventTypes'],list) or not isinstance(result['ReminderOffsets'],list)
            or any(type(n) is not int or not 0<=n<=3660 for n in result['ReminderOffsets'])):raise ValueError('Invalid private preference lists')
    return result


def is_due(rule,now):
    local=now.astimezone(ZoneInfo(rule['Timezone']))
    cadence=rule['Cadence']
    if cadence=='immediate':return True
    if cadence=='daily':return local.hour==8
    if cadence=='weekly':return local.weekday()==0 and local.hour==8
    raise ValueError('Unsupported cadence')


def current_classification(source):
    try:
        evidence=json.loads(source.get('ClassificationEvidenceJSON') or '{}')
        return (source.get('ReviewStatus')=='Reviewed' and bool(source.get('EvidenceHash'))
                and evidence.get('source_evidence_hash')==source['EvidenceHash']
                and evidence.get('FunderKey')==source.get('FunderKey')
                and evidence.get('CategoryKeys')==json.loads(source.get('CategoryKeysJSON') or '[]'))
    except (TypeError,ValueError):return False


def candidates(registry,calendar,rules,ledger,*,now,recipient,user_key):
    if now.tzinfo is None:raise ValueError('Explicit current time offset required')
    if any(not isinstance(rows,list) for rows in [registry,calendar,rules,ledger]):raise ValueError('Complete native row arrays required')
    existing={r['Title'] for r in ledger if r.get('Title')};result={}
    for source in registry:
        if not current_classification(source):continue
        categories=set(json.loads(source.get('CategoryKeysJSON') or '[]'))
        for raw_rule in rules:
            if raw_rule.get('UserKey')!=user_key or raw_rule.get('Active') is not True or raw_rule.get('SubscriptionState')!='active' or raw_rule.get('Channel')!='email':continue
            rule=preference(raw_rule)
            if not is_due(rule,now):continue
            scope,target=rule['Scope'],rule['TargetKey']
            if not ((scope=='opportunity' and target==source['OpportunityKey']) or (scope=='funder' and target==source.get('FunderKey')) or (scope=='category' and target in categories)):continue
            events=[('opportunity_changed','OPPORTUNITY',source['EvidenceHash'],None,None)]
            for deadline in calendar:
                if deadline.get('OpportunityKey')!=source['OpportunityKey'] or deadline.get('ReviewStatus')!='Reviewed' or deadline.get('RevisionApplied') is not True:continue
                if not isinstance(deadline.get('Revision'),str) or not deadline['Revision']:raise ValueError('Reviewed deadline has no revision')
                event_type='deadline_cancelled' if deadline.get('Cancelled') is True else 'deadline_changed'
                events.append((event_type,deadline['DeadlineKey'],deadline['Revision'],None,deadline))
                if deadline.get('Cancelled') is not True and deadline.get('DeadlinePrecision')=='day':
                    day=deadline.get('Calendar_x0020_day')
                    if isinstance(day,str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}',day):
                        offset=(datetime.fromisoformat(day).date()-now.astimezone(ZoneInfo(rule['Timezone'])).date()).days
                        if offset in rule['ReminderOffsets']:events.append(('reminder',deadline['DeadlineKey'],deadline['Revision'],offset,deadline))
            for event_type,deadline_key,revision,offset,deadline in events:
                if event_type not in rule['EventTypes']:continue
                identity=json.dumps([user_key,source['OpportunityKey'],deadline_key,event_type,revision,offset,'email'],separators=(',',':'),ensure_ascii=False)
                key='EVENT:'+base64.b64encode(identity.encode()).decode()
                if len(key)>255:raise ValueError('Native event identity exceeds255 characters; never truncate or resend')
                if key in existing:continue
                title=str(source.get('Title') or source['OpportunityKey']);subject='RIMS grants: '+event_type.replace('_',' ')+' - '+title
                token=hashlib.sha256(key.encode()).hexdigest()[:12];subject=subject[:200]+' ['+token+']'
                url=source.get('URL');url=url.get('Url') if isinstance(url,dict) else url
                if not isinstance(url,str) or not url.startswith('https://'):raise ValueError('Reviewed source URL required')
                body='<p>'+html.escape(event_type.replace('_',' ').capitalize())+': '+html.escape(title)+'</p>'
                if deadline:body+='<p>Calendar date: '+html.escape(str(deadline.get('Calendar_x0020_day') or 'not precisely specified'))+'.</p>'
                body+='<p><a href="'+html.escape(url,quote=True)+'">Official source</a></p><p>This reflects a reviewed registry record and your private subscription. It does not determine applicant eligibility.</p>'
                item={'Scope':'grant','Recipient':recipient,'Channel':'email','UserKey':user_key,'EventIdentity':identity,'EventKey':key,'OpportunityKey':source['OpportunityKey'],'EventType':event_type,'DeadlineKey':deadline_key,'Revision':revision,'OffsetDays':offset,'Subject':subject,'BodyHtml':body,'SourceRowID':source['Id'],'SourceEvidenceHash':source['EvidenceHash'],'PreferenceRowID':rule['Id']}
                if deadline:item.update(DeadlineRowID=deadline['Id'])
                result.setdefault(key,item)
    return list(result.values())


def norm(value):
    if isinstance(value,dict):
        result={k:norm(v) for k,v in value.items()}
        if value.get('type')=='OpenApiConnection' and result.get('inputs',{}).get('authentication')=="@parameters('$authentication')":result['inputs'].pop('authentication')
        return result
    if isinstance(value,list):return [norm(v) for v in value]
    return value


class MailWorker:
    def __init__(self,config,directory):
        self.config=config;self.directory=Path(directory);self.directory.mkdir();self.context=config['context']
        self.flow_id=str(UUID(config['flow_id']));self.base='https://api.flow.microsoft.com/providers/Microsoft.ProcessSimple/environments/'+config['environment']+'/flows/'+self.flow_id;self.qs='?api-version=2016-11-01'
        pin=json.loads(Path(config['auth_binding']).read_text());account=json.loads(subprocess.check_output(['az','account','show','-o','json']))
        if account['tenantId'].lower()!=pin['tenantId'].lower() or account['user']['name'].lower()!=pin['username'].lower():raise ValueError('Existing Azure identity drift')
        self.token=json.loads(subprocess.check_output(['az','account','get-access-token','--resource','https://service.flow.microsoft.com','-o','json']))['accessToken']
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self,*args,**kwargs):raise RuntimeError('Redirect refused')
        self.opener=urllib.request.build_opener(NoRedirect)
    def call(self,path,method='GET',body=None,label=None):
        url=self.base+path;data=None if body is None else json.dumps(body,separators=(',',':')).encode()
        if method!='GET':
            with (self.directory/(label+'-intent.json')).open('x') as f:json.dump({'method':method,'url':url,'one_send':True,'sha256':hashlib.sha256(data or b'').hexdigest()},f)
        with self.opener.open(urllib.request.Request(url,data=data,method=method,headers={'Authorization':'Bearer '+self.token,'Content-Type':'application/json'}),timeout=45) as r:
            raw=r.read();response={'status':r.status,'headers':dict(r.headers),'body':json.loads(raw) if raw else None}
        if label:(self.directory/(label+'-response.json')).write_text(json.dumps(response,indent=2))
        return response
    def submit(self,event):
        current=self.call(self.qs)['body'];properties=current['properties'];before_event=json.loads(properties['definition']['parameters']['EventJSON']['defaultValue'])
        if current['name']!=self.flow_id or properties['displayName']!='CHHHS RIMS | Grants | Live email worker' or properties['state']!='Started':raise ValueError('Exact owned live worker must be Started')
        expected=build(self.context,before_event)
        if norm(properties['definition'])!=norm(expected['properties']['definition']):raise ValueError('Live worker definition drift; preserve and stop')
        if set(properties['connectionReferences'])!=set(expected['properties']['connectionReferences']) or any(properties['connectionReferences'][k].get('connectionName')!=v['connectionName'] for k,v in expected['properties']['connectionReferences'].items()):raise ValueError('Existing worker connection binding drift')
        history=self.call('/runs'+self.qs)['body']
        if any(r['properties']['status'] in ['Running','Waiting','Resuming'] for r in history['value']):raise RuntimeError('Owned worker has an in-flight run; no mutation')
        candidate=build(self.context,event);(self.directory/'preimage.json').write_text(json.dumps(current,indent=2));(self.directory/'event.json').write_text(json.dumps(event,indent=2))
        self.call(self.qs,'PATCH',{'properties':{'definition':candidate['properties']['definition'],'connectionReferences':candidate['properties']['connectionReferences']}},'configure')
        after=self.call(self.qs)['body'];(self.directory/'saved.json').write_text(json.dumps(after,indent=2))
        if norm(after['properties']['definition'])!=norm(candidate['properties']['definition']) or after['properties']['state']!='Started':raise ValueError('Worker save/readback differs; no invocation')
        prior={r['name'] for r in history['value']};response=self.call('/triggers/manual/run'+self.qs,'POST',{},'invoke');run=next((v for k,v in response['headers'].items() if k.lower()=='x-ms-workflow-run-id'),None)
        if not run:
            for _ in range(10):
                rows=[r for r in self.call('/runs'+self.qs)['body']['value'] if r['name'] not in prior]
                if len(rows)>1:raise RuntimeError('Uncertain parallel submissions; no retry')
                if rows:run=rows[0]['name'];break
                time.sleep(1)
        if not run:raise RuntimeError('Accepted request has no unique run handle; reconcile without replay')
        result={'run_id':run,'event_key':event['EventKey'],'accepted_once':True,'automatic_retry':False};(self.directory/'submission.json').write_text(json.dumps(result,indent=2));return result
    def wait_readonly(self,run_id):
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,128}',run_id):raise ValueError('Exact native run handle required')
        deadline=time.monotonic()+50;status='Unknown'
        while time.monotonic()<deadline:
            row=self.call('/runs/'+run_id+self.qs)['body'];status=row['properties']['status']
            (self.directory/'terminal-or-pending.json').write_text(json.dumps(row,indent=2))
            if status in ['Succeeded','Failed','Cancelled','TimedOut']:break
            time.sleep(2)
        return status


def dispatch_snapshot(config,rows,read_record,*,now,directory,health):
    """Use the existing monitor's guarded reads and a persistent one-send outbox."""
    state=Path(config['outbox']);state.mkdir(parents=True,exist_ok=True);results=[]
    recipient=config['context']['operator_email'];own=config['operator_user_key']
    planned=candidates(rows['registry'],rows['calendar'],rows['watchlist'],rows['ledger'],now=now,recipient=recipient,user_key=own) if health['healthy'] else []
    summary=[{'source':s['source'],'status':s['status'],'reasons':s.get('reasons',[])} for s in health['sources']]
    fingerprint=hashlib.sha256(json.dumps(summary,sort_keys=True).encode()).hexdigest()[:24]
    previous_path=state/'health-observation.json';previous=json.loads(previous_path.read_text()) if previous_path.exists() else None
    operational=[]
    if (not health['healthy'] and previous is None) or (previous and previous['fingerprint']!=fingerprint and (not health['healthy'] or previous['healthy'] is False)):
        identity=json.dumps(['SYSTEM:G07','source_health',fingerprint,'email'],separators=(',',':'))
        operational=[{'Scope':'operational','Recipient':recipient,'Channel':'email','EventIdentity':identity,'EventKey':'EVENT:'+base64.b64encode(identity.encode()).decode(),'OpportunityKey':'SYSTEM:G07','EventType':'source_health','Revision':fingerprint,'Subject':'RIMS grants: source health changed ['+fingerprint[:12]+']','BodyHtml':'<p>Grants monitoring detected a health change.</p><ul>'+''.join('<li>'+html.escape(s['source']+': '+s['status'])+'</li>' for s in summary)+'</ul><p>Last good data is retained. No grant approval or automatic retry occurred. Inspect the private CLI monitoring receipt for the exact cause.</p>'}]
    # Reconcile an existing attempt by explicit receipt-only invocation. The
    # native graph forbids both claiming and sending in this mode, even if a
    # malformed caller supplies an event that has no ledger row.
    for row in rows.get('ledger',[]):
        if row.get('UserKey')!=own or row.get('DryRun') is not False or row.get('Status') not in ['unknown','submitted','pending_attempt'] or row.get('Attempt')!=1:continue
        key=row.get('Title','');target=state/hashlib.sha256(key.encode()).hexdigest()
        frozen=sorted(target.glob('qualification-*/event.json'))
        if not frozen:continue
        event=json.loads(frozen[-1].read_text())
        if event.get('EventKey')!=key or event.get('EventIdentity')!=row.get('EventIdentity'):raise ValueError('Stored receipt identity differs')
        event['ReceiptOnly']=True;receipt_root=target/'receipt-checks';receipt_root.mkdir(exist_ok=True);attempt=receipt_root/now.strftime('%Y%m%dT%H')
        if attempt.exists():continue
        try:
            client=MailWorker(config,attempt);accepted=client.submit(event);accepted['operation']='receipt_only';accepted['terminal_or_pending']=client.wait_readonly(accepted['run_id']);results.append(accepted)
            if accepted['terminal_or_pending'] not in ['Succeeded','Failed','Cancelled','TimedOut']:break
        except Exception as error:results.append({'event_key':key,'operation':'receipt_only','error':str(error),'automatic_retry':False});break
    for event in operational+planned:
        key_hash=hashlib.sha256(event['EventKey'].encode()).hexdigest();target=state/key_hash;target.mkdir(exist_ok=True)
        if any(target.rglob('*-intent.json')):
            results.append({'event_key':event['EventKey'],'disposition':'prior_one_send_journal_preserved; reconcile rather than retry'});continue
        if event['Scope']=='grant':
            source=read_record('registry',event['SourceRowID']);rule=read_record('watchlist',event['PreferenceRowID']);deadlines=[]
            if event.get('DeadlineRowID'):deadlines=[read_record('calendar',event['DeadlineRowID'])]
            refreshed=candidates([source],deadlines,[rule],rows['ledger'],now=now,recipient=recipient,user_key=own)
            matched=[r for r in refreshed if r['EventKey']==event['EventKey']]
            if len(matched)!=1:
                results.append({'event_key':event['EventKey'],'disposition':'current_source_or_preference_no_longer_matches; no submission'});continue
            event=matched[0];event['SourceVersion']=source['odata.etag'];event['PreferenceVersion']=rule['odata.etag']
            if deadlines:event['DeadlineVersion']=deadlines[0]['odata.etag']
        attempt=target/('qualification-'+str(time.time_ns()))
        try:
            client=MailWorker(config,attempt);accepted=client.submit(event);accepted['terminal_or_pending']=client.wait_readonly(accepted['run_id']);results.append(accepted)
            if accepted['terminal_or_pending'] not in ['Succeeded','Failed','Cancelled','TimedOut']:break
        except Exception as error:
            (target/('error-'+str(time.time_ns())+'.json')).write_text(json.dumps({'error':str(error),'automatic_retry':False}))
            results.append({'event_key':event['EventKey'],'disposition':'stopped_or_uncertain; no automatic retry','error':str(error)})
    # A failure before any native intent may be qualified again later. A native
    # intent remains quarantined; never advance an alert as though it was sent.
    advance=not operational or any(r.get('accepted_once') is True and r.get('event_key')==operational[0]['EventKey'] for r in results)
    if advance:
        temp=state/('health-'+str(time.time_ns())+'.tmp');temp.write_text(json.dumps({'fingerprint':fingerprint,'healthy':health['healthy']}));temp.replace(previous_path)
    output={'eligible_grant_notices':len(planned),'operational_health_events':len(operational),'submissions':results,'recipient_scope':'fixed sole operator','review_and_private_preference_guards':True}
    Path(directory,'delivery-result.json').write_text(json.dumps(output,indent=2));return output
