import unittest
from scripts.project_output_links import prepare,KINDS

class ProjectLinkTests(unittest.TestCase):
    def test_typed_links_exclude_candidates_and_withdrawals_without_fanout(self):
        inventory={'project':['FIC-P'],**{k:['FIC-'+k] for k in KINDS}}
        records=[dict(project_id='FIC-P',output_kind=k,output_id='FIC-'+k,evidence_id='FIC-E-'+k,evidence_revision='1',evidence_sha256='a'*64,status='reviewed' if k in {'publication','dataset'} else 'candidate') for k in sorted(KINDS)]
        result=prepare(records,inventory,complete=True)
        self.assertEqual(len(result['bridges']['publication']),1);self.assertEqual(result['bridges']['award'],[])
        self.assertEqual(len(result['records']),4);self.assertFalse(result['native_acceptance'])
        records[0]['status']='withdrawn'
        self.assertEqual(prepare(records,inventory,complete=True)['bridges']['award'],[])
    def test_unknown_and_duplicate_identity_refused(self):
        inventory={'project':['FIC-P'],**{k:['FIC-'+k] for k in KINDS}}
        r=dict(project_id='FIC-P',output_kind='publication',output_id='FIC-publication',evidence_id='FIC-E',evidence_revision='1',evidence_sha256='a'*64,status='reviewed')
        with self.assertRaises(ValueError):prepare([r,r],inventory,complete=True)
        with self.assertRaises(ValueError):prepare([dict(r,output_kind='dataset')],inventory,complete=True)

class ProjectLinkRevisionTests(unittest.TestCase):
    def setUp(self):
        self.inventory={'project':['FIC-P','FIC-P2'],**{k:['FIC-'+k,'FIC-'+k+'2'] for k in KINDS}}
        self.record=dict(project_id='FIC-P',output_kind='publication',output_id='FIC-publication',evidence_id='FIC-E',evidence_revision='1',evidence_sha256='a'*64,status='reviewed')

    def append(self,history,record,revision,supersedes=None):
        from scripts.project_output_links import append_revision
        return append_revision(history,record,self.inventory,complete=True,revision_id=revision,supersedes=supersedes,reason='Fictional correction')

    def test_correction_replay_and_withdrawal_preserve_history_and_remove_old_bridge(self):
        import copy
        from scripts.project_output_links import project_history
        first=self.append([],self.record,'R1');preimage=copy.deepcopy(first)
        corrected=dict(self.record,project_id='FIC-P2',output_id='FIC-publication2',evidence_revision='2',evidence_sha256='b'*64)
        second=self.append(first,corrected,'R2','R1')
        self.assertEqual(first,preimage)
        self.assertEqual(self.append(second,corrected,'R2','R1'),second)
        current=project_history(second,self.inventory,complete=True)
        self.assertEqual(current['bridges']['publication'],[{'project_id':'FIC-P2','output_id':'FIC-publication2'}])
        self.assertEqual(current['records'][0]['lineage_id'],first[0]['lineage_id'])
        withdrawn=self.append(second,dict(corrected,status='withdrawn'),'R3','R2')
        current=project_history(withdrawn,self.inventory,complete=True)
        self.assertEqual(current['bridges']['publication'],[])
        self.assertEqual(len(current['history']),3)
        self.assertEqual(current['history'][0]['record'],self.record)

    def test_stale_forks_conflicting_replays_and_cross_kind_corrections_are_refused(self):
        first=self.append([],self.record,'R1')
        second=self.append(first,dict(self.record,evidence_revision='2'),'R2','R1')
        with self.assertRaisesRegex(ValueError,'Stale'):self.append(second,self.record,'R3','R1')
        with self.assertRaisesRegex(ValueError,'identity conflict'):self.append(first,dict(self.record,status='candidate'),'R1')
        with self.assertRaisesRegex(ValueError,'output kind'):self.append(first,dict(self.record,output_kind='dataset',output_id='FIC-dataset'),'R2','R1')

    def test_retained_history_is_validated_before_projection(self):
        import copy
        from scripts.project_output_links import project_history,validate_history
        h=self.append([],self.record,'R1');changed=copy.deepcopy(h)
        changed[0]['record']['status']='withdrawn'
        with self.assertRaisesRegex(ValueError,'hash mismatch'):validate_history(changed)
        with self.assertRaisesRegex(ValueError,'Duplicate'):validate_history(h+h)
        reduced=copy.deepcopy(self.inventory);reduced['publication']=[]
        with self.assertRaisesRegex(ValueError,'Unresolved'):project_history(h,reduced,complete=True)
        self.assertEqual(h[0]['inventories'],self.inventory)

    def test_cli_operation_keeps_legacy_snapshot_contract_and_projects_current_heads(self):
        from scripts.project_output_links import process
        legacy=dict(records=[self.record],inventories=self.inventory,complete=True)
        self.assertEqual(process(legacy),prepare(**legacy))
        result=process(dict(operation='revise',history=[],record=self.record,inventories=self.inventory,complete=True,revision_id='R1',supersedes=None,reason='Fictional initial link'))
        projected=process(dict(operation='project-history',history=result['history'],inventories=self.inventory,complete=True))
        self.assertEqual(projected,result)
        self.assertFalse(result['native_acceptance'])

class BroaderRelationshipTests(unittest.TestCase):
    def test_new_types_review_correction_and_withdrawal_keep_legacy_history_exact(self):
        import copy
        from scripts.project_output_links import RELATIONSHIP_KINDS,append_revision,project_history
        legacy={'project':['PROJECT:1'],**{k:[] for k in KINDS}}
        legacy['publication']=['DOI:10.0000/example']
        record=dict(project_id='PROJECT:1',output_kind='publication',output_id=legacy['publication'][0],evidence_id='E:pub',evidence_revision='1',evidence_sha256='a'*64,status='candidate')
        h=append_revision([],record,legacy,complete=True,revision_id='pub1',reason='Fictional candidate')
        retained=copy.deepcopy(h)
        inventories={**legacy,**{k:['EXACT:'+k] for k in RELATIONSHIP_KINDS-KINDS}}
        for kind in sorted(RELATIONSHIP_KINDS-KINDS):
            row=dict(record,output_kind=kind,output_id='EXACT:'+kind,evidence_id='E:'+kind)
            h=append_revision(h,row,inventories,complete=True,revision_id=kind+'1',reason='Fictional candidate')
            self.assertEqual(project_history(h,inventories,complete=True)['bridges'][kind],[])
            h=append_revision(h,dict(row,status='reviewed'),inventories,complete=True,revision_id=kind+'2',supersedes=kind+'1',reason='Fictional explicit review')
            self.assertEqual(project_history(h,inventories,complete=True)['bridges'][kind],[{'project_id':'PROJECT:1','output_id':'EXACT:'+kind}])
            h=append_revision(h,dict(row,status='withdrawn'),inventories,complete=True,revision_id=kind+'3',supersedes=kind+'2',reason='Fictional withdrawal')
            self.assertEqual(project_history(h,inventories,complete=True)['bridges'][kind],[])
        self.assertEqual(h[:1],retained)
        self.assertEqual(set(project_history(retained,legacy,complete=True)['bridges']),KINDS)
        self.assertFalse(any(project_history(h,inventories,complete=True)['bridges'].values()))

    def test_typed_inventories_cannot_be_partial_or_resolve_from_another_namespace(self):
        from scripts.project_output_links import RELATIONSHIP_KINDS
        inventory={'project':['P'],**{k:[] for k in RELATIONSHIP_KINDS}}
        inventory['person']=['AUTH:1']
        r=dict(project_id='P',output_kind='ethics',output_id='AUTH:1',evidence_id='E',evidence_revision='1',evidence_sha256='a'*64,status='reviewed')
        with self.assertRaisesRegex(ValueError,'Unresolved'):prepare([r],inventory,complete=True)
        with self.assertRaisesRegex(ValueError,'Complete'):prepare([],{k:v for k,v in inventory.items() if k!='dora'},complete=True)
        with self.assertRaisesRegex(ValueError,'Complete'):prepare([],{**inventory,'names':['A Person']},complete=True)
