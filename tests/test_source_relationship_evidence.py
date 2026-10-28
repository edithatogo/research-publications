import base64,copy,hashlib,json,sys,unittest
from scripts.source_relationship_evidence import (
 project as raw_project, study_references as raw_studies, pubmed_projection as raw_pubmed,
 orcid_status, fingerprint,
)


def generation(inputs,pubs,source):
 return dict(generation_id='fictional-generation',canonical_snapshot_id='fictional-canonical',
  source_snapshot_id='fictional-source',source=source,complete=True,next_links=[],
  source_count=len(inputs),publication_count=len(pubs),source_sha256=fingerprint(inputs),publications_sha256=fingerprint(pubs))


def project(inputs,pubs):return raw_project(inputs,pubs,generation=generation(inputs,pubs,'openalex'))
def study_references(inputs,pubs):
 inputs=copy.deepcopy(inputs)
 for item in inputs:item.update(complete=True,next_links=[],http_status=200,raw_response_sha256=hashlib.sha256(item['raw']).hexdigest())
 return raw_studies(inputs,pubs,generation=generation(inputs,pubs,'clinicaltrials.gov'))
def pubmed_projection(inputs,pubs):return raw_pubmed(inputs,pubs,generation=generation(inputs,pubs,'pubmed'))

def packet(authors=None,awards=None):
 w={'id':'https://openalex.org/W1','doi':'https://doi.org/10.1234/test','authorships':authors or [],'awards':awards or []};b=json.dumps(w).encode();return {'work_id':w['id'],'requested_doi':'10.1234/test','raw_response_base64':base64.b64encode(b).decode(),'raw_response_sha256':hashlib.sha256(b).hexdigest(),'observed_utc':'2026-10-20T00:00:00Z','complete':True,'next_links':[],'http_status':200}
def author(i,name='Same Name',institutions=None,orcid=None):return {'author':{'id':f'https://openalex.org/A{i}' if i else None,'display_name':name,'orcid':orcid},'institutions':institutions or []}
PUB=[{'DOI':'10.1234/test','CanonicalKey':'pub:1'}]
class SourceEvidenceTests(unittest.TestCase):
 def test_same_name_distinct_ids_and_unresolved_excluded_from_pairs(self):
  r=project([packet([author(1),author(2),author(None)])],PUB)
  self.assertEqual(sum(x['RelationshipKind']=='coauthorship' for x in r),1)
  self.assertEqual(sum(x['IdentityStatus']=='Unresolved identity' for x in r),1)
 def test_duplicate_identical_authorships_do_not_multiply_pairs(self):
  r=project([packet([author(1),author(1),author(2)])],PUB)
  self.assertEqual(sum(x['RelationshipKind']=='authorship' for x in r),2)
  self.assertEqual(sum(x['RelationshipKind']=='coauthorship' for x in r),1)
 def test_ambiguous_doi_retains_evidence_without_canonical_admission(self):
  r=project([packet([author(1)])],PUB+[{'DOI':'https://doi.org/10.1234/test','CanonicalKey':'pub:2'}])
  self.assertTrue(all(x['CanonicalKey']=='' and x['CanonicalMatchCount']==2 for x in r))
 def test_concurrent_affiliations_are_publication_specific(self):
  inst=[{'id':'https://openalex.org/I1','display_name':'One','ror':'https://ror.org/abc'},{'id':'https://openalex.org/I2','display_name':'Two'}]
  r=project([packet([author(1,institutions=inst)])],PUB)
  self.assertEqual(sum(x['RelationshipKind']=='publication_affiliation' for x in r),2)
  self.assertEqual(sum(x['RelationshipKind']=='institution_cooccurrence' for x in r),1)
  self.assertTrue(all(x['AuthenticationState']=='Not authenticated' and x['ReviewState']=='Not reviewed' for x in r))
 def test_multiple_awards_and_equal_numbers_different_funders_remain_distinct(self):
  awards=[{'funder_id':f'https://openalex.org/F{i}','funder_award_id':'123'} for i in [1,2]]
  r=project([packet(awards=awards)],PUB);self.assertEqual(sum(x['RelationshipKind']=='publication_award' for x in r),2)
 def test_hash_mismatch_rejected_and_source_immutable(self):
  e=packet();before=copy.deepcopy(e);project([e],PUB);self.assertEqual(e,before)
  e['raw_response_sha256']='0'*64
  with self.assertRaises(ValueError):project([e],PUB)
 def test_missing_projects_never_inferred_from_award_or_name(self):
  r=project([packet([author(1)],awards=[{'id':'https://openalex.org/G1'}])],PUB)
  self.assertFalse(any('project' in x['RelationshipKind'] for x in r))
 def test_orcid_checksum_is_not_authentication(self):
  self.assertEqual(orcid_status('0000-0002-1825-0097'),'Valid syntax; unauthenticated')
  self.assertEqual(orcid_status('0000-0002-1825-0098'),'Invalid')

class StudyReferenceTests(unittest.TestCase):
 def test_reference_types_and_missing_identity_are_preserved(self):
  s={'protocolSection':{'identificationModule':{'nctId':'NCT00000001'},'referencesModule':{'references':[{'pmid':'12','type':'BACKGROUND'},{'pmid':'13','type':'DERIVED'},{'pmid':'14','type':'RESULT'}]}}}
  r=study_references([{'record':s,'raw':json.dumps(s).encode(),'observed_utc':'2026-10-20T00:00:00Z'}],[{'PMID':'13','CanonicalKey':'pub:13'}])
  self.assertEqual(len(r),2);self.assertEqual({x['ReferenceType'] for x in r},{'DERIVED','RESULT'})
  self.assertEqual(sum(bool(x['CanonicalKey']) for x in r),1)
  self.assertTrue(all(x['ToKey']=='clinicaltrials.gov:NCT00000001' for x in r))
 def test_repeated_project_reference_deduplicates_without_project_award_inference(self):
  ref={'pmid':'13','type':'RESULT'};s={'protocolSection':{'identificationModule':{'nctId':'NCT00000001','orgStudyIdInfo':{'id':'NHMRC123'}},'referencesModule':{'references':[ref,ref]}}}
  r=study_references([{'record':s,'raw':json.dumps(s).encode(),'observed_utc':'2026-10-20T00:00:00Z'}],[{'PMID':'13','CanonicalKey':'pub:13'}])
  self.assertEqual(len(r),1);self.assertEqual(r[0]['RelationshipKind'],'publication_study_reference');self.assertEqual(len(r[0]['SourcePaths']),2)

class ConflictingIdentityTests(unittest.TestCase):
 def test_conflicting_valid_orcids_exclude_author_from_pairs(self):
  a=packet([author(1,orcid='0000-0002-1825-0097'),author(2)])
  b=packet([author(1,orcid='0000-0001-5109-3700'),author(3)])
  w=json.loads(base64.b64decode(b['raw_response_base64']));w['id']='https://openalex.org/W2';w['doi']='https://doi.org/10.1234/other';raw=json.dumps(w).encode();b.update(work_id=w['id'],requested_doi='10.1234/other',raw_response_base64=base64.b64encode(raw).decode(),raw_response_sha256=hashlib.sha256(raw).hexdigest())
  self.assertTrue(orcid_status('0000-0001-5109-3700').startswith('Valid'))
  r=project([a,b],PUB+[{'DOI':'10.1234/other','CanonicalKey':'pub:2'}]);self.assertFalse(any(x['RelationshipKind']=='coauthorship' for x in r));self.assertEqual(sum(x['IdentityStatus']=='Conflicting identifiers' for x in r),2)

def node(name,value,attrs=None):return {'Name':name,'Value':value,'Attributes':attrs or []}
def pm_record(authors,grants=None,dbs=None):
 tree=[node('MedlineCitation',[node('PMID','13'),node('Article',[node('AuthorList',authors),node('GrantList',grants or []),node('DataBankList',dbs or [])])])]
 return {'pmid':'13','metadata':tree,'metadata_sha256':fingerprint(tree),'source_version':'batch-accepted','observed_utc':'2026-10-20T00:00:00Z','complete':True,'next_links':[],'http_status':200}
def pm_author(orcid=None,affs=None,name='Same Label'):
 return node('Author',[node('LastName',name)]+([node('Identifier',orcid,[{'Name':'Source','Value':'ORCID'}])] if orcid else [])+(affs or []))
class PubMedExplicitEvidenceTests(unittest.TestCase):
 def test_only_author_bound_valid_orcids_create_people_pairs(self):
  rec=pm_record([pm_author('0000-0002-1825-0097'),pm_author('https://orcid.org/0000-0001-5109-3700'),pm_author('0000-0002-1825-0098'),pm_author()]);before=copy.deepcopy(rec)
  r=pubmed_projection([rec],[{'PMID':'13','CanonicalKey':'pub:13'}]);self.assertEqual(rec,before)
  self.assertEqual(sum(x['RelationshipKind']=='coauthorship' for x in r),1)
  self.assertEqual(sum(x['RelationshipKind']=='authorship' and x['IdentityStatus']=='Source-supported' for x in r),2)
  self.assertTrue(all(x['AuthenticationState']=='Not authenticated' and x['SourceVersion']=='batch-accepted' for x in r))
 def test_affiliation_variants_same_explicit_ringgold_id_remain_evidence(self):
  def af(label):return node('AffiliationInfo',[node('Affiliation',label),node('Identifier','123',[{'Name':'Source','Value':'RINGGOLD'}])])
  r=pubmed_projection([pm_record([pm_author('0000-0002-1825-0097',[af('Department One'),af('Department Two')])])],[{'PMID':'13','CanonicalKey':'pub:13'}])
  self.assertEqual(sum(x['RelationshipKind']=='publication_affiliation' for x in r),2)
  self.assertFalse(any(x['RelationshipKind']=='institution_cooccurrence' for x in r))
 def test_grants_are_explicit_source_scoped_and_unqualified_agency_is_unresolved(self):
  grants=[node('Grant',[node('GrantID','123'),node('Agency',agency),node('Country','AU')]) for agency in ['Funder A','Funder B','']]
  r=pubmed_projection([pm_record([],grants)],[{'PMID':'13','CanonicalKey':'pub:13'}]);g=[x for x in r if x['RelationshipKind']=='publication_grant_reference'];self.assertEqual(len(g),3);self.assertEqual(len({x['ToKey'] for x in g}),3);self.assertEqual(sum(x['IdentityStatus']=='Unresolved award namespace' for x in g),1)
 def test_trial_registry_ids_only_and_no_background_or_sequence_database_join(self):
  dbs=[node('DataBank',[node('DataBankName',name),node('AccessionNumberList',[node('AccessionNumber',value)])]) for name,value in [('ClinicalTrials.gov','NCT00000001'),('ANZCTR','ACTRN12605000411673'),('GENBANK','NCT00000002')]]
  r=pubmed_projection([pm_record([],dbs=dbs)],[{'PMID':'13','CanonicalKey':'pub:13'}]);links=[x for x in r if x['RelationshipKind']=='publication_study_reference'];self.assertEqual(len(links),2);self.assertEqual({x['ToKey'] for x in links},{'clinicaltrials.gov:NCT00000001','anzctr:ACTRN12605000411673'})
 def test_explicit_orcid_crosswalk_deduplicates_same_pair_across_providers(self):
  pubs=[{'PMID':'13','DOI':'10.1234/test','CanonicalKey':'pub:13'}]
  oa=project([packet([author(1,orcid='0000-0002-1825-0097'),author(2,orcid='0000-0001-5109-3700')])],pubs)
  pm=pubmed_projection([pm_record([pm_author('0000-0002-1825-0097',name='Other Display Label'),pm_author('0000-0001-5109-3700')])],pubs)
  pairs=[x for x in oa+pm if x['RelationshipKind']=='coauthorship'];self.assertEqual(len(pairs),2);self.assertEqual(len({(x['FromKey'],x['ToKey']) for x in pairs}),1)

class BoundGenerationTests(unittest.TestCase):
 def test_partial_duplicate_and_unbound_generations_fail_closed(self):
  original=packet([author(1)]);pubs=copy.deepcopy(PUB)
  for mode in ('missing','source-hash','canonical-hash','count','bool','next','incomplete','source','duplicate-canonical','duplicate-source','drift','capture'):
   inputs=[copy.deepcopy(original)];p=copy.deepcopy(pubs)
   if mode=='duplicate-canonical':p.append(copy.deepcopy(p[0]))
   if mode=='duplicate-source':inputs.append(copy.deepcopy(inputs[0]))
   g=generation(inputs,p,'openalex')
   if mode=='missing':g.pop('generation_id')
   elif mode=='source-hash':g['source_sha256']='0'*64
   elif mode=='canonical-hash':g['publications_sha256']='0'*64
   elif mode=='count':g['source_count']=2
   elif mode=='bool':g['source_count']=True
   elif mode=='next':g['next_links']=['more']
   elif mode=='incomplete':g['complete']=False
   elif mode=='source':g['source']='pubmed'
   elif mode=='drift':p[0]['ReviewStatus']='human edit after capture'
   elif mode=='capture':inputs[0]['complete']=False;g=generation(inputs,p,'openalex')
   with self.subTest(mode=mode),self.assertRaises(ValueError):raw_project(inputs,p,generation=g)
  self.assertEqual(original,packet([author(1)]));self.assertEqual(pubs,PUB)

 def test_strict_raw_json_failure_and_partial_payloads_rejected_even_when_rehashed(self):
  for raw in (b'{"id":1,"id":2}',b'{"x":NaN}',b'{"x":1e999}',b'{"error":"failed"}',b'{"id":"https://openalex.org/W1","doi":"10.1234/test"}'):
   e=packet();e.update(raw_response_base64=base64.b64encode(raw).decode(),raw_response_sha256=hashlib.sha256(raw).hexdigest())
   with self.subTest(raw=raw),self.assertRaises(ValueError):project([e],PUB)

 def test_occurrences_and_revision_withdrawal_are_retained_not_applied(self):
  e=packet([author(1),author(1),author(2)]);e['observed_utc']=None
  pubs=copy.deepcopy(PUB);pubs[0].update(ReviewStatus='Reviewed',HumanCorrection='Preserve',PublicationDate=None)
  before=copy.deepcopy((e,pubs));rows=project([e],pubs)
  a=next(r for r in rows if r['RelationshipKind']=='authorship' and r['ToKey']=='https://openalex.org/A1')
  self.assertEqual(a['SourcePaths'],['/authorships/0','/authorships/1'])
  self.assertTrue(all(r['ObservedUTC'] is None for r in rows))
  revised=copy.deepcopy(e);w=json.loads(base64.b64decode(revised['raw_response_base64']));w['is_retracted']=True;raw=json.dumps(w).encode()
  revised.update(raw_response_base64=base64.b64encode(raw).decode(),raw_response_sha256=hashlib.sha256(raw).hexdigest())
  g=generation([revised],pubs,'openalex');g.update(generation_id='fictional-revision',source_snapshot_id='fictional-revised-source')
  current=raw_project([revised],pubs,generation=g)
  self.assertEqual({r['EvidenceKey'] for r in rows},{r['EvidenceKey'] for r in current})
  self.assertNotEqual(rows[0]['SourceVersion'],current[0]['SourceVersion'])
  self.assertTrue(all(not r['CandidateEligible'] and r['EvidenceState']=='source_marked_retracted' for r in current))
  self.assertTrue(all(r['ReviewState']=='Not reviewed' and not r['MutationAuthorized'] and not r['CanonicalAdmission'] for r in current))
  self.assertEqual((e,pubs),before)

 def test_candidate_bridge_filter_counts_do_not_multiply_publication_grain(self):
  inst=[{'id':'https://openalex.org/I1','display_name':'One'},{'id':'https://openalex.org/I2','display_name':'Two'}]
  rows=project([packet([author(1,institutions=inst),author(2,institutions=inst)],awards=[{'funder_id':'https://openalex.org/F1','funder_award_id':'123'},{'funder_id':'https://openalex.org/F2','funder_award_id':'123'}])],PUB)
  selected=[r for r in rows if r['RelationshipKind'] in {'authorship','publication_affiliation','publication_award'}]
  self.assertGreater(len(selected),1)
  self.assertEqual({r['CanonicalKey'] for r in selected},{'pub:1'})
  self.assertEqual({r['CanonicalKey'] for r in selected if r['ToKey']=='https://openalex.org/I1'},{'pub:1'})
  self.assertEqual(sum(r['RelationshipKind']=='publication_award' for r in selected),2)
  self.assertTrue(all(r['Confidence']=='candidate' and not r['IdentityQualified'] for r in selected))
  from scripts.grants_relationships import normalize_relationship
  with self.assertRaises(ValueError):normalize_relationship(selected[0])

 def test_unknown_award_namespace_and_same_names_do_not_create_funding_fact(self):
  r=project([packet([author(None,name='Same Name'),author(None,name='Same Name')],awards=[{'funder_display_name':'A name','funder_award_id':'123'}])],PUB)
  self.assertFalse(any(x['RelationshipKind'] in {'coauthorship','funded_by_award','publication_award'} for x in r))
  self.assertEqual(sum(x['RelationshipKind']=='unresolved_award_reference' for x in r),1)
  self.assertEqual(sum(x['IdentityStatus']=='Unresolved identity' for x in r),2)

 def test_study_raw_record_mismatch_and_duplicate_capture_rejected(self):
  s={'protocolSection':{'identificationModule':{'nctId':'NCT00000001'},'referencesModule':{'references':[{'pmid':'13','type':'RESULT'}]},'statusModule':{'overallStatus':'WITHDRAWN'}}}
  item=dict(record=s,raw=json.dumps(s).encode(),complete=True,next_links=[],http_status=200,observed_utc=None)
  item['raw_response_sha256']=hashlib.sha256(item['raw']).hexdigest();pubs=[{'PMID':'13','CanonicalKey':'pub:13'}]
  r=raw_studies([item],pubs,generation=generation([item],pubs,'clinicaltrials.gov'))
  self.assertEqual(r[0]['SourceStatusRaw'],'WITHDRAWN')
  self.assertTrue(r[0]['CandidateEligible']) # Study status does not retract a publication reference.
  for mode in ('parsed','raw','duplicate'):
   items=[copy.deepcopy(item)]
   if mode=='parsed':items[0]['record']['protocolSection']['identificationModule']['nctId']='NCT00000002'
   elif mode=='raw':items[0]['raw']=b'{"x":1,"x":2}';items[0]['raw_response_sha256']=hashlib.sha256(items[0]['raw']).hexdigest()
   else:items.append(copy.deepcopy(item))
   with self.subTest(mode=mode),self.assertRaises(ValueError):raw_studies(items,pubs,generation=generation(items,pubs,'clinicaltrials.gov'))

 def test_pubmed_metadata_hash_duplicate_identity_and_singletons_rejected(self):
  pubs=[{'PMID':'13','CanonicalKey':'pub:13'}]
  for mode in ('hash','identity','duplicate','singleton','attributes','partial'):
   rec=pm_record([pm_author()]);items=[rec]
   if mode=='hash':rec['metadata_sha256']='0'*64
   elif mode=='identity':rec['pmid']=True
   elif mode=='duplicate':items.append(copy.deepcopy(rec))
   else:
    if mode=='singleton':rec['metadata'][0]['Value'].append(copy.deepcopy(rec['metadata'][0]['Value'][0]))
    elif mode=='attributes':rec['metadata'][0]['Attributes']=[{'Name':'X','Value':'a'},{'Name':'X','Value':'b'}]
    else:rec['metadata']=[]
    rec['metadata_sha256']=fingerprint(rec['metadata'])
   with self.subTest(mode=mode),self.assertRaises(ValueError):raw_pubmed(items,pubs,generation=generation(items,pubs,'pubmed'))

 def test_pubmed_retraction_and_structured_provenance_remain_distinct_from_raw_xml(self):
  rec=pm_record([pm_author()]);article=rec['metadata'][0]['Value'][1]
  article['Value'].append(node('PublicationTypeList',[node('PublicationType','Retracted Publication')]))
  rec['metadata_sha256']=fingerprint(rec['metadata']);before=copy.deepcopy(rec)
  rows=pubmed_projection([rec],[{'PMID':'13','CanonicalKey':'pub:13'}])
  self.assertTrue(all(not r['CandidateEligible'] and r['RawSHA256']=='' and r['StructuredMetadataSHA256']==rec['metadata_sha256'] for r in rows))
  self.assertEqual(rec,before)
