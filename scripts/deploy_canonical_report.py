"""Compatibility entrypoint: prepare an isolated packet, never deploy canonical state."""
from __future__ import annotations
if __package__:
    from scripts.deploy_report_definition import main
else:
    from deploy_report_definition import main


def validate_deployment_target(workspace_id, report_id, target_scope):
    from uuid import UUID
    if target_scope != 'isolated':
        raise ValueError('canonical/shared report deployment is disabled')
    UUID(workspace_id); UUID(report_id)


if __name__ == '__main__': main()
