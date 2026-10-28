"""Observe the qualified public NIH opportunity without replacing accepted data."""
# SPDX-License-Identifier: Apache-2.0
import hashlib,json,urllib.request,urllib.error
from scripts.grants_us_gov_api import FON, OPPORTUNITY_ID, semantic_detail


def selected_detail(envelope):
    """Bind both observations to the same typed successful public opportunity."""
    if (not isinstance(envelope, dict)
            or type(envelope.get('errorcode')) is not int or envelope['errorcode'] != 0
            or not isinstance(envelope.get('data'), dict)):
        raise ValueError('Successful exact NIH opportunity envelope required')
    detail = envelope['data']
    if (type(detail.get('id')) is not int or detail['id'] != OPPORTUNITY_ID
            or detail.get('opportunityNumber') != FON):
        raise ValueError('Exact NIH opportunity identity required')
    return detail


def compare(status,raw,baseline):
    if status!=200:return {'source':'nih-opportunity','status':'SOURCE_HTTP_REJECTED','http_status':status,'last_good_preserved':True,'automatic_retry':False,'actual_changed_deadline_observed':False}
    body=json.loads(raw)
    old,new=semantic_detail(selected_detail(baseline)),semantic_detail(selected_detail(body));old_dates=old['synopsis'];new_dates=new['synopsis']
    dates={k:{'before':old_dates.get(k),'after':new_dates.get(k)} for k in ['responseDateStr','archiveDateStr'] if old_dates.get(k)!=new_dates.get(k)}
    return {'source':'nih-opportunity','status':'VERIFIED_UNCHANGED' if old==new else ('DEADLINE_CHANGED_REVIEW_REQUIRED' if dates else 'SOURCE_CHANGED_REVIEW_REQUIRED'),'http_status':200,'semantic_equal':old==new,'changed_date_fields':dates,'actual_changed_deadline_observed':bool(dates),'deadline_timezone_inferred':False,'last_good_preserved':True,'raw_sha256':hashlib.sha256(raw).hexdigest(),'automatic_retry':False}


def observe(baseline_path,directory):
    from pathlib import Path
    p=Path(directory)
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self,*args,**kwargs):raise RuntimeError('Unexpected provider redirect; stop')
    request=urllib.request.Request('https://api.grants.gov/v1/api/fetchOpportunity',data=b'{"opportunityId":357812}',method='POST',headers={'Content-Type':'application/json','Accept':'application/json'})
    try:
        with urllib.request.build_opener(NoRedirect).open(request,timeout=30) as response:status=response.status;raw=response.read();headers=dict(response.headers)
    except urllib.error.HTTPError as error:status=error.code;raw=error.read();headers=dict(error.headers)
    (p/'nih-provider-response.bin').write_bytes(raw);(p/'nih-provider-headers.json').write_text(json.dumps(headers,indent=2))
    result=compare(status,raw,json.loads(Path(baseline_path).read_text()));(p/'nih-observation.json').write_text(json.dumps(result,indent=2));return result
