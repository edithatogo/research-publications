"""Run qualified grants checks, recovery snapshots and configured own-mail delivery.

The host must be awake with valid workload authentication. Default checks are
read-only. Explicit private delivery configuration permits the owned mail worker
to submit eligible notices and operational health alerts to the sole operator.
This command never renews auth, retries native writes or changes source facts.
"""
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
import argparse
from datetime import datetime,timedelta,timezone
import hashlib,json,os
from pathlib import Path
import re,subprocess,sys,time
from scripts.grants_source_health import evaluate,SOURCES,BRISBANE


def expected_slot(source,now):
    local=now.astimezone(BRISBANE)
    slot=(local-timedelta(days=local.weekday())).replace(hour=SOURCES[source][0],minute=0,second=0,microsecond=0)
    return slot-timedelta(days=7) if slot>local else slot


def archive_names(source):
    return {f'{source}-{i:02d}-original.xlsx' for i in range(1,SOURCES[source][1]+1)}|{'manifest.json','source-page.html','source-page-after.html'}


def checked_inventory(source,run,folder,listing):
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,128}',run):raise ValueError('Unsafe native run identity')
    if not isinstance(listing,list) or len(listing)!=len(archive_names(source)) or {r.get('Name') for r in listing}!=archive_names(source):raise ValueError('Archive inventory incomplete, duplicated or unexpected')
    if any(r.get('ServerRelativeUrl')!=folder+'/'+r['Name'] or int(r.get('Length',0))<1 for r in listing):raise ValueError('Native file path/length differs')
    return listing


def backup_counts(snapshots):
    """Missing/incomplete item reads must never become verified empty backups."""
    return {name:len(value['items']['value']) if all(k in value for k in ('metadata','fields','items')) else None
            for name,value in snapshots.items()}


def delivery_healthy(result):
    """Check terminal execution; recipient receipt remains separate ledger evidence."""
    if result.get('error'):return False
    for submission in result.get('submissions',[]):
        if submission.get('error'):return False
        if submission.get('accepted_once') and submission.get('terminal_or_pending')!='Succeeded':return False
        if 'prior_one_send_journal' in submission.get('disposition',''):return False
    return True


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--config',type=Path,required=True);args=parser.parse_args(argv)
    config=json.loads(args.config.read_text());root=Path(config['repository']).resolve();state=Path(config['state']).resolve();state.mkdir(parents=True,exist_ok=True);os.umask(0o077)
    if sys.version_info[:3]!=(3,15,1):raise RuntimeError('Qualified repository Python3.15.1 required')
    if not config['node'].startswith('/') or not Path(config['node']).is_file():raise ValueError('Pinned absolute Node executable required')
    lock=state/'.run-lock';lock.mkdir();(lock/'owner.json').write_text(json.dumps({'pid':os.getpid()}))
    now=datetime.now(timezone.utc);stamp=now.strftime('%Y%m%dT%H%M%SZ')+'-'+str(os.getpid());out=state/'runs'/stamp;out.mkdir(parents=True)
    result={'observed_utc':now.isoformat(),'monitor':'grants-collector-health-v1','sources':[],'source_native_mutations':0,'mail_sends_measured':False,'authentication_renewal':False}
    unavailable_resources={}
    def command(label,options):
        resource='https://management.azure.com/' if options[0]=='flow' else config['site'].split('/personal/')[0]
        if resource in unavailable_resources:raise RuntimeError('Read workload stopped after authentication boundary at '+unavailable_resources[resource]+'; no repeated request')
        # Shared auth ownership remains with the established guarded entrypoint.
        binding=Path(config['binding']);shared=binding.parent/'.m365-qualified.lock';deadline=time.monotonic()+60
        while shared.exists():
            if time.monotonic()>deadline:raise RuntimeError('Shared workload remains owned; no request sent')
            time.sleep(.5)
        r=subprocess.run([config['node'],str(root/'scripts/m365-qualified.mjs'),'read',str(binding),*options,'--output','json'],cwd=root,capture_output=True,text=True,timeout=90)
        (out/(label+'-receipt.json')).write_text(json.dumps({'exit':r.returncode,'stderr':r.stderr,'args':options}))
        if r.returncode:
            if 'INTERACTIVE_AUTH_BLOCKED:' in r.stderr:
                audience=re.search(r'\[pinned resource: ([^\]]+)\]',r.stderr)
                unavailable_resources[resource]=audience.group(1) if audience else resource
            raise RuntimeError('Qualified read stopped: '+label+'; inspect private receipt; no login/retry')
        if '--asFile' in options:return None
        return json.loads(r.stdout) if r.stdout.strip() else None
    try:
        generations=[];cache=state/'archives';cache.mkdir(exist_ok=True)
        for source,settings in config['sources'].items():
            if source not in SOURCES:raise ValueError('Only qualified collectors allowed')
            try:
                flow=command(source+'-flow',['flow','get','--name',settings['flow_id'],'--environmentName',config['environment']])
                history=command(source+'-history',['flow','run','list','--flowName',settings['flow_id'],'--environmentName',config['environment']])
                (out/(source+'-flow.json')).write_text(json.dumps(flow));(out/(source+'-history.json')).write_text(json.dumps(history))
                slot=expected_slot(source,now);begin=slot-timedelta(days=1)
                kwargs=dict(as_of=now.isoformat(),history_from=begin.isoformat(),history_through=now.isoformat(),history_complete=True,reads_verified=True,archive_root=cache,due_by=(slot+timedelta(minutes=config['diagnostic_grace_minutes'])).isoformat())
                health=evaluate(source,flow,history,[],**kwargs);run=health.get('run_id')
                if run and health.get('terminal_status')=='Succeeded':
                    folder=settings['archive_prefix']+run;local=cache/(source+'-'+run);local.mkdir(exist_ok=True)
                    listing=command(source+'-inventory',['spo','file','list','--webUrl',config['site'],'--folderUrl',folder,'--fields','Name,ServerRelativeUrl,Length'])
                    checked_inventory(source,run,folder,listing);files=[]
                    for item in listing:
                        target=local/item['Name']
                        if not target.exists():command(source+'-'+item['Name'],['spo','file','get','--webUrl',config['site'],'--url',item['ServerRelativeUrl'],'--asFile','--path',str(target)])
                        raw=target.read_bytes()
                        if len(raw)!=int(item['Length']):raise ValueError('Downloaded length mismatch')
                        files.append({'name':item['Name'],'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
                    manifest=json.loads((local/'manifest.json').read_text())
                    if manifest.get('archive_folder')!=folder[len(config['site'].split('.com',1)[1]):]:raise ValueError('Manifest archive path mismatch')
                    generations.append({'source':source,'run':run,'manifest_exact_run':True,'files':files})
                    health=evaluate(source,flow,history,generations,**kwargs)
                result['sources'].append({'source':source,**health})
            except Exception as error:
                result['sources'].append({'source':source,'status':'UNKNOWN','reasons':[str(error)],'last_good_preserved':True})
        if config.get('nih_baseline'):
            from scripts.grants_nih_observer import observe
            try:result['sources'].append(observe(config['nih_baseline'],out))
            except Exception as error:result['sources'].append({'source':'nih-opportunity','status':'UNKNOWN','reasons':[str(error)],'last_good_preserved':True})
        snapshots={}
        try:
            for name,root_url in config.get('stores',{}).items():
                snapshots[name]={}
                for kind,suffix in [('metadata','?$select=Id,Title,ReadSecurity,WriteSecurity,EnableVersioning'),('fields','/fields?$top=5000'),('items','/items?$top=5000')]:
                    file=out/(name+'-'+kind+'.json')
                    command(name+'-'+kind,['request','--url',root_url+suffix,'--method','get','--filePath',str(file),'--accept','application/json;odata=minimalmetadata'])
                    value=json.loads(file.read_text())
                    if value.get('odata.nextLink') or value.get('@odata.nextLink'):raise ValueError('Incomplete recovery snapshot: '+name+' '+kind)
                    if name in ['watchlist','ledger'] and kind=='metadata' and (value.get('ReadSecurity')!=2 or value.get('WriteSecurity')!=2 or value.get('EnableVersioning') is not True):raise ValueError('Private versioned store boundary changed; no item read')
                    snapshots[name][kind]=value
        except Exception as error:result['sources'].append({'source':'recovery-backup','status':'UNKNOWN','reasons':[str(error)],'last_good_preserved':True})
        expected=2+bool(config.get('nih_baseline'))
        result['healthy']=len(result['sources'])==expected and all(s['status'] in ['VERIFIED_SAVED_OCCURRENCE','VERIFIED_UNCHANGED'] for s in result['sources'])
        result['backup_scope']='Current schema/settings/items; accepted attachment/model reconstruction evidence remains separate'
        result['backup_counts']=backup_counts(snapshots)
        if config.get('delivery'):
            from scripts.grants_live_delivery import dispatch_snapshot
            delivery=json.loads(Path(config['delivery']).read_text())
            rows={name:values.get('items',{}).get('value',[]) for name,values in snapshots.items()}
            def read_record(name,item_id):
                if type(item_id) is not int or item_id<1:raise ValueError('Exact native item ID required')
                file=out/(name+'-frozen-'+str(item_id)+'-'+str(time.time_ns())+'.json')
                command(name+'-frozen-'+str(item_id),['request','--url',config['stores'][name]+'/items('+str(item_id)+')','--method','get','--filePath',str(file),'--accept','application/json;odata=minimalmetadata'])
                value=json.loads(file.read_text())
                if not isinstance(value.get('odata.etag'),str) or value['odata.etag']=='*':raise ValueError('Native source/preference ETag missing')
                return value
            try:result['delivery']=dispatch_snapshot(delivery,rows,read_record,now=now,directory=out,health=result)
            except Exception as error:result['delivery']={'error':str(error),'automatic_retry':False}
        result['source_healthy']=result['healthy']
        result['delivery_healthy']=delivery_healthy(result.get('delivery',{}))
        result['delivery_health_scope']='Terminal execution only; actual recipient receipt/status is separate native ledger evidence'
        result['healthy']=result['source_healthy'] and result['delivery_healthy']
        (out/'generations.json').write_text(json.dumps(generations,indent=2));(out/'result.json').write_text(json.dumps(result,indent=2))
        temporary=state/('latest-'+stamp+'.tmp');temporary.write_text(json.dumps(result,indent=2));temporary.replace(state/'latest.json')
        if result['source_healthy']:
            temporary=state/('last-good-'+stamp+'.tmp');temporary.write_text(json.dumps(result,indent=2));temporary.replace(state/'last-good.json')
        with (state/'events.jsonl').open('a') as f:f.write(json.dumps({'observed_utc':now.isoformat(),'healthy':result['healthy'],'receipt':str(out/'result.json')})+'\n')
        print(json.dumps({'healthy':result['healthy'],'statuses':{s['source']:s['status'] for s in result['sources']},'receipt':str(out/'result.json')}))
        return 0 if result['healthy'] else 2
    finally:
        (lock/'owner.json').unlink();lock.rmdir()


if __name__=='__main__':raise SystemExit(main())
