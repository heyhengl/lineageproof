# Release and submission checklist

This is the evidence ledger for a public hackathon release. A checked box must correspond to a reproducible artifact or public receipt.

## Local technical release

- [x] Python 3.12 package builds as a wheel.
- [x] Wheel installs in an isolated virtual environment.
- [x] Installed `lineageproof` CLI completes the synthetic audit.
- [x] Fourteen automated tests pass.
- [x] Ruff formatting and static checks pass.
- [x] Release verifier passes.
- [x] Expected output set contains exactly six files.
- [x] Synthetic decision is `request_remediation` with one critical and three high findings.
- [x] Eight receipts contain hashes rather than raw responses.
- [x] Write-back artifact states `dry_run: true` and `mutation_tools_invoked: false`.
- [x] Write-back plan is bound to the exact audit-report SHA-256.
- [x] Synthetic write-back requires `--apply` and an exact change-ID acknowledgement.
- [x] Synthetic write-back receipt records five mutation calls and `external_metadata_modified: false`.
- [x] Privacy scan reports zero findings across 34 release text files.
- [x] Deterministic source archive uses a public-file allowlist and excludes `design/`.
- [x] Source archive manifest records every included file's byte length and SHA-256.

## Build evidence

- Package: `dist/package/lineageproof-0.1.0-py3-none-any.whl`
- SHA-256: `d7d886a1540e270982aa43be437c374e9b44e165849cfef50ef37cf91a4f6f13`
- Source archive: `dist/release/lineageproof-0.1.0-source.zip`
- Source manifest: `dist/release/lineageproof-0.1.0-source-manifest.json`
- Local verification date: 2026-07-19 Asia/Shanghai

## Public release

- [x] Create public repository `https://github.com/heyhengl/lineageproof`.
- [x] Verify Apache-2.0 license is visible.
- [x] Record public commit `445ed51d9456ce4eb8a5d4ad1f1cdba0367f933c`.
- [x] Verify the current public branch head `bc2c6e6fcefd8df709aad1359e9d4881beba612a`.
- [x] Open the repository in a signed-out browser.
- [x] Confirm no credential, personal data, customer data, or private strategy content is present.
- [x] Add the public repository URL to the Devpost draft.

## Demo

- [x] Render the synthetic flow from `DEMO_SCRIPT.md` at 1920x1080.
- [x] Verify the local MP4 is 177.832 seconds with one video and one audio track.
- [x] Generate 30 sentence-level English subtitle cues with a 54-character line limit.
- [x] Verify the final decoded cover frame has no rotation or crop error.
- [x] Scan the MP4 for local path, username, and email-like strings with zero findings.
- [x] Publish a public preview at `https://heyhengl.github.io/lineageproof/`.
- [x] Verify preview playback and captions in a signed-out browser.
- [ ] Upload the final video publicly to YouTube, Vimeo, or Youku; GitHub Pages is not on the
  official host allowlist.
- [ ] Verify the allowed-host playback, duration, visibility, AI/synthetic disclosure, and captions
  in a signed-out browser.
- [ ] Add the rule-compliant video URL to the Devpost draft.

## Devpost

- [ ] Confirm account eligibility and current rules on the submission date.
- [x] Recheck the official rules on 2026-07-19: no purchase or payment is necessary; submission is
  a contract; the final video host must be YouTube, Vimeo, or Youku.
- [ ] Select `Agents That Do Real Work` and confirm the live category label is unchanged.
- [x] Confirm the project/testing URL opens without login or payment.
- [x] Confirm the public repository contains `examples/expected-output/` and full setup instructions.
- [ ] Disclose submission-period creation, AI coding assistance, code-generated visuals, and synthetic narration.
- [ ] Confirm every required field from the live submission form.
- [ ] Confirm the final submission creates no charge, deposit, purchase, or financial movement.
- [ ] Submit only verified public URLs and truthful claims.
- [ ] Record the Devpost project URL and submission receipt.

## Financial evidence

- Settled or withdrawable net income: RMB 0.
- Startup spend: RMB 0.
- Prize pool, submission status, project URL, judging progress, and an award notice are not income.
- Only settled or withdrawable evidence may change the income total.
# Release and submission checklist

This is the evidence ledger for a public hackathon release. A checked box must correspond to a reproducible artifact or public receipt.

## Local technical release

- [x] Python 3.12 package builds as a wheel.
- [x] Wheel installs in an isolated virtual environment.
- [x] Installed `lineageproof` CLI completes the synthetic audit.
- [x] Fourteen automated tests pass.
- [x] Ruff formatting and static checks pass.
- [x] Release verifier passes.
- [x] Expected output set contains exactly six files.
- [x] Synthetic decision is `request_remediation` with one critical and three high findings.
- [x] Eight receipts contain hashes rather than raw responses.
- [x] Write-back artifact states `dry_run: true` and `mutation_tools_invoked: false`.
- [x] Write-back plan is bound to the exact audit-report SHA-256.
- [x] Synthetic write-back requires `--apply` and an exact change-ID acknowledgement.
- [x] Synthetic write-back receipt records five mutation calls and `external_metadata_modified: false`.
- [x] Privacy scan reports zero findings across 31 release text files.
- [x] Deterministic source archive uses a public-file allowlist and excludes `design/`.
- [x] Source archive manifest records every included file's byte length and SHA-256.

## Build evidence

- Package: `dist/package/lineageproof-0.1.0-py3-none-any.whl`
- SHA-256: `d7d886a1540e270982aa43be437c374e9b44e165849cfef50ef37cf91a4f6f13`
- Source archive: `dist/release/lineageproof-0.1.0-source.zip`
- Source manifest: `dist/release/lineageproof-0.1.0-source-manifest.json`
- Local verification date: 2026-07-18 Asia/Shanghai

## Public release

- [x] Create public repository `https://github.com/heyhengl/lineageproof`.
- [x] Verify Apache-2.0 license is visible.
- [x] Record public commit `445ed51d9456ce4eb8a5d4ad1f1cdba0367f933c`.
- [x] Open the repository in a signed-out browser.
- [x] Confirm no credential, personal data, customer data, or private strategy content is present.
- [x] Add the public repository URL to the Devpost draft.

## Demo

- [x] Render the synthetic flow from `DEMO_SCRIPT.md` at 1920x1080.
- [x] Verify the local MP4 is 177.832 seconds with one video and one audio track.
- [x] Generate 30 sentence-level English subtitle cues with a 54-character line limit.
- [x] Verify the final decoded cover frame has no rotation or crop error.
- [x] Scan the MP4 for local path, username, and email-like strings with zero findings.
- [x] Publish at `https://heyhengl.github.io/lineageproof/` with public judge-accessible visibility.
- [x] Verify playback and captions in a signed-out browser.
- [x] Add the video URL to the Devpost draft.

## Devpost

- [ ] Confirm account eligibility and current rules on the submission date.
- [ ] Select `Agents That Do Real Work` and confirm the live category label is unchanged.
- [x] Confirm the project/testing URL opens without login or payment.
- [x] Confirm the public repository contains `examples/expected-output/` and full setup instructions.
- [ ] Disclose submission-period creation, AI coding assistance, code-generated visuals, and synthetic narration.
- [ ] Confirm every required field from the live submission form.
- [ ] Confirm the final submission creates no charge, deposit, purchase, or financial movement.
- [ ] Submit only verified public URLs and truthful claims.
- [ ] Record the Devpost project URL and submission receipt.

## Financial evidence

- Settled or withdrawable net income: RMB 0.
- Startup spend: RMB 0.
- Prize pool, submission status, project URL, judging progress, and an award notice are not income.
- Only settled or withdrawable evidence may change the income total.
