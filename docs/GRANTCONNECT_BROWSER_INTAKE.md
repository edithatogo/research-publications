# GrantConnect daily browser intake

The daily browser intake automation was paused on 2 November 2026 at track archival.

Use the public BrowserOS neo session and the previous accepted private generation. The initial register contains 120 opportunities. The SharePoint ready-file flow owns all GrantConnect list writes.

1. Capture the official RSS XML bytes with scripts/grantconnect_browser.js. Retain the final URL, UTC time, size, headers and SHA-256. Use the existing bootstrap-xml CLI with --previous-register. A missing record does not establish withdrawal. Preserve changed observations for reconciliation.
2. Capture the official opportunity pages in batches of up to ten. Match the GO ID and URL. Use scripts.grantconnect_closings to extract confirmed ACT closing dates. Leave ongoing opportunities undated. Preserve existing reviewed dates when the source becomes uncertain.
3. Archive the original bytes, parsed register and date evidence in the versioned SharePoint reporting folder using qualified documentation-sync. Run the repo-local Python module scripts.grantconnect_live_ready with the register JSON, closing-dates JSON and private output directory. Upload the register ready file first. After its successful receipt, upload the dates ready file. Use immutable filenames. An identical uploaded file or existing key and evidence hash is a replay.
4. Process the two existing funding model tables after changed rows have been accepted. Keep the prior baseline on failure. Record the occurrence and affected keys. Preserve institutional decisions separately. NIH remains inactive.

For history, run scripts/grantconnect_history_ready.py on a frozen database. Archive the original workbooks and detail captures. Upload data-upload.json through the qualified uploader before ready-upload.json. The flow routes closed opportunities, versioned awards and confirmed identifier pairs to separate lists. A failure within a SharePoint batch is detected by reading back the expected keys and hashes.
