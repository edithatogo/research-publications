"""Run an ARDC batch capture followed by a separate candidate projection.

Transport and persistence callbacks must be provided by the caller; this module
does not choose a native target, activate a flow or make external requests.
"""
from __future__ import annotations

try:
    from scripts.ardc_activity_batch import capture_batches
    from scripts.ardc_secondary_filter import filter_archived_batches, filter_responses
except ModuleNotFoundError:
    from ardc_activity_batch import capture_batches
    from ardc_secondary_filter import filter_archived_batches, filter_responses


def capture_and_filter(overlay, credential, aliases_raw, *, read_total, fetch_batch,
                       probe, put, read, save_receipt, save_projection, batch_size=32, save_partial=None,
                       cleanup_verified=None):
    """Capture source batches first, persist receipt, then derive candidates.

    Save callbacks must create new private artifacts; the receipt remains saved
    if filtering fails. This routine neither certifies source completeness nor
    makes an affiliation decision. Native read/write qualification remains the
    responsibility of the supplied callbacks.
    """
    def on_archived(name, raw):
        if save_partial is not None:
            save_partial(name, filter_responses([(name, raw)], aliases_raw))
        if cleanup_verified is not None:
            cleanup_verified(name, raw)

    receipt = capture_batches(overlay, read_total, fetch_batch, probe, put, read,
                              credential=credential, batch_size=batch_size, on_archived=on_archived)
    save_receipt(receipt)
    projection = filter_archived_batches(receipt, read, aliases_raw)
    save_projection(projection)
    return {'receipt': receipt, 'projection': projection,
            'native_target_qualified_by_pipeline': False,
            'current_provider_snapshot_verified': False}
