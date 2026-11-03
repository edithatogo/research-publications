import test from 'node:test';
import assert from 'node:assert/strict';
import {assertAppend,assertSavedAppend} from '../scripts/publish_documentation_catalogue.mjs';
const controls=[{id:'human',controlType:4,innerHTML:'Retained operator content'}];
const before={CanvasContent1:JSON.stringify(controls)};
const added={id:'replacement',controlType:4,innerHTML:'crossref-targeted-doi-replacement'};
test('incremental Crossref supplement has an explicit isolated scope',()=>{
 const control={...added,id:'crossref-incremental',innerHTML:'crossref-incremental-doi'};
 assert.doesNotThrow(()=>assertAppend(before,[...controls,control],'crossref-incremental-doi'));
 assert.throws(()=>assertAppend(before,[...controls,control]),/separate/);
 assert.throws(()=>assertAppend(before,[{...controls[0],innerHTML:'changed'},control],'crossref-incremental-doi'),/Unselected/);
});
test('replacement supplement preserves the complete native control prefix',()=>{
 assert.doesNotThrow(()=>assertAppend(before,[...controls,added]));
 assert.throws(()=>assertAppend(before,[{...controls[0],innerHTML:'lost human edit'},added]),/Unselected/);
 assert.throws(()=>assertAppend(before,[added]),/Unselected/);
});
test('duplicate identities and unrelated added components are refused',()=>{
 assert.throws(()=>assertAppend(before,[...controls,{...added,id:'human'}]),/separate/);
 assert.throws(()=>assertAppend(before,[...controls,{...added,controlType:3}]),/separate/);
 assert.throws(()=>assertAppend(before,[...controls,{...added,innerHTML:'unrelated'}]),/separate/);
});

test('G07 append is explicitly scoped and preserves every existing control',()=>{
 const control={...added,id:'g07',innerHTML:'g07-notification-safe-operator-cycle'};
 assert.doesNotThrow(()=>assertAppend(before,[...controls,control],'g07-notification-safe-operator-cycle'));
 assert.throws(()=>assertAppend(before,[...controls,control]),/separate/);
 assert.throws(()=>assertAppend(before,[{...controls[0],innerHTML:'changed'},control],'g07-notification-safe-operator-cycle'),/Unselected/);
 assert.throws(()=>assertAppend(before,[...controls,control],'arbitrary'),/Unknown/);
});

test('workbook recovery append cannot replace controls or use another scope',()=>{
 const scope='g04-workbook-timeout-recovery';
 const control={...added,id:'g04',innerHTML:scope};
 assert.doesNotThrow(()=>assertAppend(before,[...controls,control],scope));
 assert.throws(()=>assertAppend(before,[{...controls[0],innerHTML:'lost human edit'},control],scope),/Unselected/);
 assert.throws(()=>assertAppend(before,[...controls,control],'g07-notification-safe-operator-cycle'),/separate/);
});

test('native href canonicalization is limited to the new control',()=>{
 const b={...before,UniqueId:'same',Title:'Existing',Description:'preserve',LayoutWebpartsContent:'layout'};
 const c={...added,id:'g07',innerHTML:'g07-notification-safe-operator-cycle <a href="https://example.invalid/site/Shared Documents/guide.md">Guide</a>'};
 const desired=[...controls,c];const a={...b,Version:'2.0',IsPageCheckedOutToCurrentUser:false,CanvasContent1:JSON.stringify([...controls,{...c,innerHTML:'g07-notification-safe-operator-cycle <a href="/site/Shared%20Documents/guide.md">Guide</a>'}])};
 assert.doesNotThrow(()=>assertSavedAppend(b,desired,a,'https://example.invalid/site','g07-notification-safe-operator-cycle'));
 const drift=structuredClone(a);const rows=JSON.parse(drift.CanvasContent1);rows[0].innerHTML='changed';drift.CanvasContent1=JSON.stringify(rows);
 assert.throws(()=>assertSavedAppend(b,desired,drift,'https://example.invalid/site','g07-notification-safe-operator-cycle'),/differ/);
 assert.throws(()=>assertSavedAppend(b,desired,{...a,Title:'changed'},'https://example.invalid/site','g07-notification-safe-operator-cycle'),/identity/);
});

test('ANZCTR catalogue append preserves existing controls and is scope bound',()=>{
 const scope='anzctr-manual-archive-study-refresh';
 const control={...added,id:'anzctr',innerHTML:scope};
 assert.doesNotThrow(()=>assertAppend(before,[...controls,control],scope));
 assert.throws(()=>assertAppend(before,[{...controls[0],innerHTML:'lost edit'},control],scope),/Unselected/);
 assert.throws(()=>assertAppend(before,[...controls,control],'crossref-incremental-doi'),/separate/);
});

test('source recovery bootstrap appends without changing accepted prior evidence',()=>{
 const scope='source-recovery-bootstrap';
 const retained=[...controls,{id:'prior-source-proof',controlType:4,innerHTML:'Accepted baseline and retained source provenance'}];
 const page={...before,CanvasContent1:JSON.stringify(retained),UniqueId:'stable',Title:'Catalogue',Description:'retained',LayoutWebpartsContent:'layout'};
 const control={id:'source-recovery-addendum',controlType:4,innerHTML:scope+' PubMed, DataCite and ClinicalTrials saved definitions; changed-path runtime unaccepted.'};
 const desired=[...retained,control];
 assert.doesNotThrow(()=>assertAppend(page,desired,scope));
 assert.throws(()=>assertAppend(page,[{...retained[0],innerHTML:'lost operator text'},retained[1],control],scope),/Unselected/);
 assert.throws(()=>assertAppend(page,[...retained,{...control,id:'prior-source-proof'}],scope),/separate/);
 assert.throws(()=>assertAppend(page,desired,'source-recovery-unreviewed'),/Unknown/);
 const after={...page,CanvasContent1:JSON.stringify(desired),Version:'26.0',IsPageCheckedOutToCurrentUser:false};
 assert.doesNotThrow(()=>assertSavedAppend(page,desired,after,'https://example.invalid/site',scope));
 const altered=structuredClone(after);const native=JSON.parse(altered.CanvasContent1);native[1].innerHTML='reclassified baseline';altered.CanvasContent1=JSON.stringify(native);
 assert.throws(()=>assertSavedAppend(page,desired,altered,'https://example.invalid/site',scope),/differ/);
});

test('current digest documentation preserves the historical no-send control',()=>{
 const scope='publication-digest-current-definition';
 const control={id:'digest-current',controlType:4,innerHTML:scope+' Stopped; Outlook action present; delivery and native Loop parity unaccepted.'};
 const desired=[...controls,control];
 assert.doesNotThrow(()=>assertAppend(before,desired,scope));
 assert.throws(()=>assertAppend(before,[{...controls[0],innerHTML:'rewritten acceptance'},control],scope),/Unselected/);
 assert.throws(()=>assertAppend(before,[...controls,{...control,id:controls[0].id}],scope),/separate/);
 assert.throws(()=>assertAppend(before,desired,'crossref-incremental-doi'),/separate/);
});

test('publication conditional update remains a scoped append, not a process-count increment',()=>{
 const scope='publication-writer-conditional-observations';
 const control={...added,id:'publication-conditional',innerHTML:scope+' Existing capability; runtime pending'};
 assert.doesNotThrow(()=>assertAppend(before,[...controls,control],scope));
 assert.throws(()=>assertAppend(before,[{...controls[0],innerHTML:'lost human edit'},control],scope),/Unselected/);
 assert.throws(()=>assertAppend(before,[...controls,control],'publication-digest-current-definition'),/separate/);
});

test('monthly repair append preserves every earlier control and requires exact marker',()=>{const scope='monthly-schedule-repair-20261102',control={...added,id:'monthly',innerHTML:scope};assert.doesNotThrow(()=>assertAppend(before,[...controls,control],scope));assert.throws(()=>assertAppend(before,[{...controls[0],innerHTML:'changed'},control],scope),/Unselected/);assert.throws(()=>assertAppend(before,[...controls,added],scope),/separate/);});

test('free API handoff appends one scoped control without losing human content',()=>{const scope='publication-free-api-handoff-20261103';const control={...added,id:'free-api',innerHTML:scope+' Accepted source coverage and explicit deferrals'};assert.doesNotThrow(()=>assertAppend(before,[...controls,control],scope));assert.throws(()=>assertAppend(before,[{...controls[0],innerHTML:'lost human edit'},control],scope),/Unselected/);assert.throws(()=>assertAppend(before,[...controls,{...control,id:'human'}],scope),/separate/);assert.throws(()=>assertAppend(before,[...controls,added],scope),/separate/);});
