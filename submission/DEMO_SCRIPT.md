# LineageProof demo script

Target: a judge-readable English demo below three minutes. The generated video follows the
verified CLI and synthetic artifacts; it does not depend on an unfinished UI.

## Storyboard

1. **Problem** — A schema change can fail downstream; LineageProof brings DataHub evidence into
   the review before merge.
2. **Typed change** — Show the dataset and the rename, nullability change, and sensitive-field
   removal in the manifest.
3. **DataHub context** — Show entity, schema, lineage, and observed-query collection as one
   evidence chain.
4. **Actual CLI run** — Display the installed audit command and its real synthetic-fixture result.
5. **Decision** — Present one critical and three high issues with a clear request-remediation
   outcome.
6. **Provenance** — Show hash-only tool receipts and state what is deliberately not persisted.
7. **Remediation** — Convert findings into field-level migration, contract-test, owner, and
   classification actions.
8. **Safe default** — Show that audit produces a dry-run plan and invokes no mutation tool.
9. **Write-back gate** — Explain exact-plan validation, tool preflight, call limit, `--apply`, and
   change-ID acknowledgement.
10. **Truth boundary** — Prove five synthetic mutation calls while keeping
    `external_metadata_modified: false`.
11. **Release verification** — Show passing tests, receipt checks, privacy scan, and isolated
    package verification.
12. **Close** — Restate the review, evidence, and decision questions LineageProof answers.

The exact narration is stored in `scripts/build_demo_frames.py`. Scene timing is calculated from
the generated narration audio and written to `dist/demo-video/timeline.json`; sentence-level
captions are written to `dist/demo-video/LineageProof_Demo_en.srt`.

## Recording boundary

- Use only the generated 1920x1080 synthetic storyboard.
- Do not show a menu bar, notification, local username, browser account, or shell history.
- Do not show environment variables, credentials, customer data, or a production DataHub system.
- Use no third-party music, stock footage, or unverified external-state claim.
- Follow `VIDEO_BUILD.md` to reproduce the MP4 and verify the three-minute ceiling.
- Verify the hosted video and captions in a signed-out browser before submitting its URL.
