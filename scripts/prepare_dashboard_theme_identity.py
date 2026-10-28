"""Repair one exported custom-theme identity in a guarded local report clone.

Preserves all theme colours, fonts and overrides. No native calls or acceptance.
SPDX-License-Identifier: Apache-2.0
"""
import json
from pathlib import Path, PurePosixPath
from scripts.prepare_dashboard_readable_layout import bundle_digest
from scripts.prepare_dashboard_reader_increment import prepare, sha


def prepare_theme_identity(source, output, expected_sha):
    source=Path(source);output=Path(output)
    if bundle_digest(source)!=expected_sha:
        raise ValueError('Complete report baseline drift')
    report=json.loads((source/'definition/report.json').read_text())
    reference=report.get('themeCollection',{}).get('customTheme')
    if not reference or reference.get('type')!='RegisteredResources':
        raise ValueError('One registered custom theme required')
    resources=[item for package in report.get('resourcePackages',[])
               if package.get('name')=='RegisteredResources'
               for item in package.get('items',[])
               if item.get('type')=='CustomTheme' and item.get('name')==reference['name']]
    if len(resources)!=1:
        raise ValueError('Exact unique custom theme resource required')
    name=PurePosixPath(resources[0]['path'])
    if name.is_absolute() or '..' in name.parts:
        raise ValueError('Unsafe custom theme path')
    relative='StaticResources/RegisteredResources/'+name.as_posix()
    theme=json.loads((source/relative).read_text())
    if not isinstance(theme.get('name'),str) or theme['name']==reference['name']:
        raise ValueError('Mismatched named theme preimage required')
    original_name=theme['name'];theme['name']=reference['name']
    receipt=prepare(source,output,sha((source/'definition/report.json').read_bytes()))
    (output/relative).write_text(json.dumps(theme,indent=2)+'\n')
    receipt.update(status='LOCAL_THEME_IDENTITY_REPAIR_NOT_SAVED',
                   full_baseline_sha256=expected_sha, original_theme_name=original_name,
                   corrected_theme_name=reference['name'])
    receipt['output']={p.relative_to(output).as_posix():sha(p.read_bytes())
                       for p in output.rglob('*') if p.is_file()}
    receipt['changed_files']=sorted(n for n in receipt['output']
                                    if receipt['input'].get(n)!=receipt['output'][n])
    output.with_name(output.name+'.manifest.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return receipt
