# S22+ FYG8 R4W1-B Live Binding Packet Preconnected Ready Host PASS

Date: 2026-07-19 KST

Target: `SM-S906N/g0q/S906NKSS7FYG8`

Scope: host-only implementation and validation of the deterministic promotion
step between connected PASS and independent live-policy binding review. No
device was enumerated or contacted. No ADB, Odin, reboot, Download transition,
policy activation, consumed state, transfer, rollback, or flash occurred.

## Result

`PASS_R4W1B_LIVE_BINDING_PACKET_PRECONNECTED_READY`

This is source readiness only. It grants no connected or live action.

## Implementation

The target-specific generator
`s22plus_fyg8_r4w1b_live_binding_packet.py` has two host-only modes:

- `--preconnected-check` proves the exact source/template pins, connected
  policy active, live policy inactive, connected PASS absent, and candidate
  unconsumed without writing a run directory;
- `--emit-after-connected` is unavailable until the exact connected PASS
  exists and validates. It reopens PASS and result evidence, renders the
  hash-pinned live clause template, and writes only a private review packet.

The generator cannot edit `AGENTS.md`, activate policy, enumerate a device,
invoke connected preflight, call Odin, consume candidate state, or transfer an
artifact. The rendered clause remains inert until independent review and a
separate committed `AGENTS.md` binding.

## Exact Pins

```text
generator  5834b0cc2113dc2fc7657a15a954d5b34dbfddefd37ce73a67fc61d4e72f53e6
test       831197ff7858b569eacac0458e8756a933abd57b8d36893ecdb73d1c5df8ed47
template   66b14fc1c87497346c4c6583f93d3e2c3bd4505c3a688837f91c540b2a7eb68f
```

The unchanged load-bearing helper/test/core/core-test identities remain
`734693c4...65a95d`, `87de8015...e42c1`, `9bcade25...3725`, and
`b55db857...2fd9d`.

## Evidence Hardening

- PASS and result are stable-read as direct files before validation;
- the canonical helper `validate_connected_pass()` must independently agree;
- both files are stable-read again and must remain byte-identical;
- they are reopened once more after clause files are written and must retain
  the same records, paths, sizes, and SHA256 identities;
- result paths must be canonical relative paths below
  `workspace/private/runs`, end in `result.json`, and contain no traversal,
  control character, or Markdown delimiter;
- timestamps, positive decimal sizes, and lowercase SHA256 values have exact
  lexical contracts;
- every known placeholder occurs exactly once, unknown or retained
  placeholders fail, and the exact clause contains one live sentinel;
- the template explicitly preserves the complete already-bound connected-only
  clause and adds no automatic activation.

## Review Status

An additional Claude Opus review was attempted in the existing conversation
after a `/usage` snapshot showed current session `52%` and weekly `11%`.
Claude returned only `session limit` with reset `10:20 KST`; no technical
verdict was produced. This is not approval. Codex's adversarial pass found and
closed the render-field injection, evidence-reopen TOCTOU, connected-clause
inheritance, and missing success-path test gaps before this checkpoint.

## Validation

```text
focused generator tests                  7 passed
all R4W1-B regression tests              107 passed, 3 skipped
py_compile                               PASS
git diff --check                         PASS
preconnected host check                  PASS
connected policy                         active
live policy                              inactive
connected PASS                           absent
candidate consumed                       false
device contact/write/flash               false/false/false
```

## Next Gate

The attending operator must provide the exact fresh connected acknowledgement
before any device contact. After connected PASS, run the pinned generator,
independently review its exact private packet, bind the exact live clause in a
separate commit, requalify offline, and only then request fresh live approval.
