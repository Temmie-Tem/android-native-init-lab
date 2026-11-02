# S22+ LA002: LOGM write/read positive control

Result: **PASS_LOADER_FYG8_ANDROID / READBACK_AND_SNAPSHOT_OBSERVED /
ANDROID_CLOSED_HEALTHY**.

The operator returned the exact 1800-second, one-operation attended approval
for the [qualified LA002 control](S22PLUS_LOADER_LOGM_LA002_H0_2026-11-03.md).
The earlier readiness had become stale, so one fresh invocation of the named
preapproval D0 re-established complete original-A health before the grant.
The reviewed capability, backend V23 and stable worker were unchanged.

One candidate N and one original Android A transferred. Candidate Android
proved the unique loader marker, exact FYG8 kernel, candidate boot digest,
original supporting partitions and numeric root. Its fixed report/log capture
and three complete candidate health brackets belong to one observed Android
boot and the required USB generations. Fresh proof preceded the normal
candidate Download command inside the original observation window.

## LOGM observations

The FDT report and complete 2,097,136-byte snapshot were acquired successfully
with empty stderr. Production decoding and an independent wire/HMAC
reconstruction agree:

| Observation | Result |
| --- | --- |
| Current loader exception level | EL1 |
| Sampled memory state | MMU off, data cache off, little-endian |
| Live FDT/log-region and header eligibility | Passed |
| Before, precommit and final four-word header samples | Identical |
| Complete 128-byte readback | Zero mismatches |
| Exact candidate-HMAC frames in the snapshot | 1 |
| Damaged or foreign frame candidates | 0 |
| Snapshot position versus the sampled-index prediction | Consistent |

The sampled index selects the wrapped-ring reader branch. Position agreement
is an additional observation, not an acceptance gate or an attempt identity.
The current FDT establishes this observed boot's writer outcome; the static
frame establishes candidate occurrence in its acquired snapshot. Together they
provide a positive write/read control on the healthy vendor path. They do not
prove that a particular snapshot frame came from the same attempt, exclude
earlier unseen boots or intervening writes, explain ML012–ML015's absent
markers, or demonstrate retention across a failed mainline boot and Download/
original-A restoration. Mainline RAM PID1 and USB remain unproved.

## Original-A return and health

Normal candidate Download and original-A transfer completed inside the same
owner. The initial final-health attempt then stopped: `03-health` returned
code 1, empty stdout and the fixed same-target ADB-not-found diagnostic. Its
preceding `02-health` properties command returned code 0 but **zero stdout
bytes**, so it supplies neither a boot ID nor health. The failed raw captures
remain intact; no prefix was combined with later evidence.

One original-owner health-only continuation acquired a fresh complete
seven-read bracket and closed healthy. Final Android proves numeric root,
boot completion, stopped boot animation and all exact original-A/supporting
partition digests. Its boot differs from the proved candidate boot. The first
failed bracket provides no identity continuity across the ADB disappearance;
its cause and an intervening unobserved boot are not resolved here.

The terminal's `recovered=true` denotes this health continuation. There was
no physical Download request, second A transfer, candidate replay or additional
control after the stop. Normal Download return is proved; automatic recovery
from an unresponsive experimental component remains unproved.

## Canonical timeline

Times are seconds from the original grant opening, rounded to three decimals.

| Event | Seconds |
| --- | ---: |
| Initial Android Download intent | 25.919 |
| N transfer intent / completion | 38.205 / 39.673 |
| Candidate health and LOGM observation complete | 159.124 |
| Candidate Download intent / departure complete | 160.953 / 162.762 |
| Original-A transfer intent / completion | 174.264 / 175.796 |
| Initial final-health failure; owner stopped | 216.950 |
| Health-only continuation began | 279.627 |
| Final health and durable close | 281.226 |

There are exactly two Download controls, one N intent and one A intent.
The operation and grant are consumed; no replay or successor is authorized.

## Evidence closure

The H0 closer rederived the terminal, released-owner state, raw index and
canonical timeline. An offline audit checked all **981 raw captures**, the
**56-record source snapshot**, both independent decodings and the complete
candidate/return health joins. Device acquisition, subprocess and socket
creation were blocked during closure rederivation. All **31 protected
approval/task/grant/terminal/journal records** remained byte-identical.

The private approval, task/source snapshot, append-only journals, raw failures,
candidate FDT/snapshot, terminal, timeline and `run-audit.json` remain under
`workspace/private/outputs/s22plus-loader-logm-control-h0-20261103-1/`.
The connector reports `CLOSED_BY_ORIGINAL_OWNER`; no F1 owner remains.

No native_data reader, mount, repair or writer was invoked. Android health
does not establish native_data consistency. A90 and S20+ were untouched, and
the initial unrelated files remain unchanged.
