# A90 resident-install v2 F1 pass — 2026-08-02

## Result

Run `a90-v3406-debian-display-f1-20260802-01` closed
`PASS_A90_RESIDENT_INSTALLED` with device safety state `RESIDENT_HEALTHY`.
The V3406 native candidate is now the resident A90 baseline.

The transaction performed:

- one boot-only candidate transfer;
- zero candidate replays;
- one candidate health check;
- zero resident reboots after that health check; and
- zero rollback transfers.

The separately connected S22+ received no command.

## Accepted health

The durable health record proves all of the resident-install v2 checks:

- exact candidate version and build;
- native selftest with `fail=0`;
- read-only pstore inspection with zero entries;
- exact immutable Debian source image size and SHA256 with the work path absent;
- one A90 NCM interface on the current ACM USB parent;
- successful host profile binding and activation; and
- direct USB-local route and device reachability.

The canonical timeline is `live_session_start`, `candidate_flash_start`,
`candidate_flash_done`, `candidate_boot_ready`, and `live_session_end`.
Eleven append-only journal records end at `RESIDENT_INSTALLED_CLOSED`.

## Host result-publication incident

After the terminal journal was durably written, publication of `result.json`
raised `resident-install rootfs health is not exact`. The device transition and
health proof were not repeated.

The receipt was valid. The command actually returned by the shared command
transport is:

```text
run /bin/busybox sh -c <exact manifest-bound preflight script>
```

The resident result validator and its synthetic fixture incorrectly expected
only `sh -c <script>`. The validator now compares the full real argv including
`run /bin/busybox`. It still requires exact list equality, exact script
equality, successful framed return, and exactly one success marker.

Focused tests pass `28/28`. Independent safety review found no issue and
returned PASS/GO. Candidate transfer, replay, rollback, and terminal-state
logic were unchanged.

The reviewed source correction does not retroactively change the consumed
manifest closure and grants no live authority. The original terminal journal
remains the authoritative result for this run; no candidate replay or rollback
was performed to repair a host reporting failure.

## Next boundary

There is no current A90 F1 or D1 authority. The next work is host-only: connect
the healthy resident baseline to the already designed D1 switch-root engine.
That work must not flash again or reinterpret the consumed F1 approval.
