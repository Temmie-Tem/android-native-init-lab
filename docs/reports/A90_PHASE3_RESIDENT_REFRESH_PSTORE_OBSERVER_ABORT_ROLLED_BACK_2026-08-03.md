# A90 Phase 3 resident refresh pstore observer abort and rollback

## Result

Run `a90-v3406-debian-display-f1-20260803-02` is closed
`NO_PROOF_A90_F1_RP_CANDIDATE_ROLLED_BACK`.

- Rootfs staging and candidate preflight passed.
- One exact boot-only candidate transfer completed; candidate replay is false.
- Exact candidate version/build, `selftest fail=0`, and the bounded control
  response passed.
- The pre-handoff pstore observer stopped before resident installation because
  it required an empty directory after reboot.
- One exact V2321 rollback transfer completed from durable journal state.
- Final V2321 version/build, `selftest fail=0`, empty pstore, and exact control
  health passed. S22+ and the other Samsung endpoint received no command.

The device terminal is `HEALTHY`; the Phase 3 resident installation has no
proof and D1 was not started.

## Incident classification

This is `HOST_OBSERVER_FAILURE`, not a proved candidate crash. The read-only
pstore listing contained only `console-ramoops-0` and `pmsg-ramoops-0` after
the candidate reboot. It contained no `dmesg`, `ftrace`, or unknown entry.
Those two boot-record classes can be materialized by an ordinary reboot and do
not by themselves refute the already exact native health response.

The runner nevertheless implemented `entries == 0` as a fatal condition. It
therefore converted an expected post-reboot observation into a resident-install
failure. The old transaction remains closed and its candidate is never
replayed.

## H0 correction boundary

The pre-handoff pstore observer remains read-only and always unmounts. It now:

- records an empty pstore as `empty`;
- records only `console-ramoops-*` and `pmsg-ramoops-*` as
  `expected-boot-records` with a warning and continues; and
- stops on `dmesg`, `ftrace`, any unknown entry, or any malformed nonempty
  listing line as a crash-class, unknown, or unresolved health signal.

One shared exact validator accepts the new nine-key classified receipt. Its
compatibility mode also accepts the historical six-key receipt only when both
the bound entry list and the reparsed listing are truly empty. This preserves
the existing resident baseline for F1 ancestry and D1 replay without allowing
legacy nonempty evidence to bypass the new classifier.

No pstore entry is cleared, no device command is retried, and transfer,
rollback, target isolation, boot-only scope, and physical recovery semantics
are unchanged. Focused and related F1/D1 regressions pass `353/353` and
`135/135`. Source mutation probes reject allowlist expansion, a disabled
classifier, malformed-line fail-open, and injected pstore cleanup. Because
this incident changes execution-critical F1 classification and its D1
consumer, it received a fresh independent capability review before any new
manifest or live attempt.

## Independent review

The subagent review closed one High schema-consumer finding and two Medium
parser/self-audit findings, then returned `PASS_GO` with no unresolved finding.
The combined 33-file execution-critical closure digest is
`8ed89ab95829c38b6a8cfa4f6cbc72df6a363982d667e332cb7255710d6c69ea`.
This qualification is reusable across manifests, campaigns, and ordinals until
that closure or its named semantics changes, or another hazard or incident
occurs.

## Evidence identities

- Manifest SHA256:
  `a083fcb2a142a493b1c836b494110fecd2cddec0927840524487adc15e429c4f`.
- Structured result SHA256:
  `ca45fe30a40d4de4fc6c1fd893ead39313bdc35ee93f08049342085840131c20`.
- Timeline SHA256:
  `cd451fb188389f01bada871293524f0b2aa5d05faf4f019ae05426e9ccda1da1`.
- Candidate-boot-ready journal SHA256:
  `7636a8040269b8e33ecad3eb98df31964aee0e9244fe1ecce589c27f6bfe82ac`.
- Rollback-flashed journal SHA256:
  `9150af8c9031694f0e37d72e8f8303c9ce8d3ac7ec391962252dffd7431ea449`.
- Final-health journal SHA256:
  `242b8dda5e47fc06bf717ba5911a4a7da2e6e708a6601e56c3f1948231ec7330`.
- Closed journal SHA256:
  `3aedfb21a8e007f869f8c7fae4c1c52fd532dbc5390bf4c9e2302f75553fa72c`.

Raw flash, serial, pstore, and target evidence remains private. No payload,
credential, device serial, or recovery identifier is committed.
