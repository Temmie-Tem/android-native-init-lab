# A90 H30 Native ADB inventory pre-write failure

Date: 2026-08-21
Target: operator-owned Samsung Galaxy A90 5G
Disposition: `RECOVERY_REQUIRED_PREWRITE_ONLY_H30_UNPROVED`

## Result

The attended H30 run did not write the candidate or rollback. Both fixed flash
helpers inspected their exact local image, then stopped before ADB push and
before any boot write because the Native-side `adb devices -l` inventory wrote
the normal daemon-start banner to stderr. The strict owner correctly refused
that producer output.

Both machine receipts are exact `PRE_WRITE_FAILURE` with
`writeStarted=false`, `bootWrittenReadbackExact=false`,
`systemReturnAttempted=false`, and a quiescent helper. H30 therefore received no
boot opportunity and remains unproved, not refuted. Exact V2321 remained the
resident and the final bounded ACM observation was healthy.

The candidate-result record is 332 bytes at SHA-256
`42c41b678821958e2e5aed10d854c939b58d8db53b3dafe7119eb39b6821cfaf`.
The rollback-result record is 331 bytes at SHA-256
`dadb495602e6c49f494d23f0d21199bf1135fcf8865a4cb44948bbc226ac50b3`.
Terminal record 40 is 1,010 bytes at SHA-256
`6591783fbd0b950e7c59f8d32a149d3bfe1a8b26df0c83e47744521a715c9a63`
and records `RECOVERY_REQUIRED / ROLLBACK_HEALTH_UNPROVED`.

## Cause and next boundary

The failure is a host inventory ownership defect, not a kernel, TWRP, transfer,
or device-health result. The current Native pre-effect role check invokes ADB
even though ordinary Native observation is ACM-scoped. When no host ADB server
already exists, that check has the side effect of starting one and its stderr
banner becomes a deterministic pre-write rejection.

Candidate and active guards remain. No candidate or rollback replay is allowed
from this journal. Before another F1, a host-only reviewed repair must remove
the ambient Native ADB-server dependency or otherwise provide an explicitly
owned, policy-compatible inventory boundary, and a reviewed reconciliation
must close this exact pre-write run. This incident grants no D0, F1, retry, or
new candidate authority.
