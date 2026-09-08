# S22+ bounded attended F1 session policy

Date: 2026-09-09

The operator requested a contract change that stops experimentation when an
unproved recovery situation occurs. The common contract now defines a finite
attended-session delegation: at most three reservations and two hours, exact
reviewed scope and fresh per-run bindings, with physical attendance retained.
The S22+ adoption is **DEFINED_NOT_ACTIVE**. Existing runner approvals remain
mandatory. This policy change opens no grant and performs no device action.

An unknown effect, unexplained session failure or recovery outside its proven
scope stops new experiments. Stopping does not prove recovery. Only previously
authorized recovery may proceed from durable journal state with its binding
intact; otherwise the run parks for physical intervention or separately reviewed
recovery authority. Expiry and withdrawal never cancel already authorized
rollback/final health. Consumed candidates and unresolved stops remain binding.

Implementation and activation are a separate bounded unit: integrate a distinct
session authorization path into the existing runner, durable reservations and
terminal reconciliation, and focused failure-path tests; independently review
that execution closure before activation. Do not bypass legacy token checks.
No new daemon, device probe or experimental candidate is part of this change.

Validation: documentation diff and local links, exact common-details SHA-256
pin, root loading budget, and unchanged permanent-boundary section. GOAL.md
remains below the 800-line history-review threshold. No image build or device
test is needed for this dormant policy-only change. Repository boundary check
passed. Independent reviewer `p352_usb_review` returned **PASS_GO** for the
policy-only scope: unchanged permanent and unattended boundaries, no runner
bypass or activation, and retained attendance/finite limits/no-replay/recovery
separation. Reviewed common-details SHA-256:
`78635cd38f94f2f62a491063b72a08faa0de7023a2f711565dcf8b7bf4c3351e`.
Unrelated S20+ changes were excluded. This verdict does not qualify a future
session runner or grant.
