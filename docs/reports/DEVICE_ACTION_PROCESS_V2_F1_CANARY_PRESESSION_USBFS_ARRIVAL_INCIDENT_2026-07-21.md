# Process v2 F1 Canary Pre-session USBFS Arrival Incident

Date: 2026-07-21 KST

Verdict: `FAIL_F1_V2_PRE_CANDIDATE_DOWNLOAD`

The first approved Process v2 canary invocation stopped before candidate
attempt or partition transfer. Execution-time D0 passed, Android requested
Download, and the journal reached `APPROVED`. Endpoint polling then recorded 11
empty Odin snapshots before raising `OdinTransitionError`. The device appeared
as Samsung Download `04e8:685d` immediately afterward and `odin4 -l` returned
its usbfs path.

The persisted result proves:

- `candidate_classification=not-attempted`;
- `candidate_completed=false`;
- `rollback_completed=false`;
- `recovery_required=false`; and
- no `candidate_flash_start` event or Odin transfer attempt exists.

The race occurred when a Download node arrived after an empty snapshot receipt
was published but before its post-receipt inventory revalidation. The shared
code treated this expected arrival as endpoint replacement.

The remediation keeps strict revalidation as the default. Only
`wait_for_single_live_endpoint()` may carry an empty receipt to the next poll;
live endpoint tickets, terminal absence checks, and ticket revalidation remain
strict. Regression coverage proves expected arrival succeeds on the next poll,
terminal absence rejects the same race, and live endpoint replacement remains
rejected.

Validation passed:

- USBFS/Odin tests: 77;
- Process v2 F1/D0/document tests: 69;
- Python compilation and `git diff --check`; and
- independent `gpt-5.6-sol` xhigh delta review:
  `GO_HOST_ONLY_COMMIT`, no findings.

The aborted binding and approval cannot be reused. The changed execution
closure requires Android return, a new connected D0 preparation, and a fresh
exact-binding approval before any later F1 attempt. This report grants no
device authority.
