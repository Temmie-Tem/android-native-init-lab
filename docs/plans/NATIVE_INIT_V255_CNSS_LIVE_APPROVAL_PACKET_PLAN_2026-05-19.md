# Native Init V255 CNSS Live Approval Packet Plan

## Summary

- V255 is a no-start approval packet for the first bounded CNSS live start-only attempt.
- It does not execute `cnss-daemon`.
- It freezes the exact proposed runner command, rollback checklist, prerequisite state, and helper no-allow evidence.
- If V255 passes, the next step is a human/operator approval decision for the first live start-only run.

## Goal

Create a host-side verifier that answers four questions before any live daemon start:

1. Are all required prerequisite manifests still present and matching?
2. Does the proposed start-only profile still use the latest private namespace shims?
3. Does the helper still fail closed without `--allow-cnss-start-only`?
4. Is there a concrete rollback checklist and exact manual command for the future approved run?

## Key Changes

- Add `scripts/revalidation/wifi_cnss_live_approval_packet.py`.
- The script will:
  - reuse `wifi_cnss_start_only_runner.py` profile construction;
  - build the exact approval command but not execute it;
  - verify prerequisite manifests through the runner's existing prerequisite checker;
  - run current read-only device captures;
  - run the helper once in no-allow mode to prove `exec_attempted=0`;
  - verify `pidof cnss-daemon` remains absent before and after;
  - write `manifest.json`, `approval-command.sh`, `rollback-checklist.md`, and `summary.md` under a private output directory.
- Keep all live start guardrails:
  - no Wi-Fi scan/connect/link-up/credential/DHCP/routing;
  - no `cnss_diag`;
  - no rfkill unblock;
  - no ICNSS bind/unbind;
  - no persistent Android partition write;
  - no automatic reboot.

## Validation

- Static:
  - `python3 -m py_compile scripts/revalidation/wifi_cnss_live_approval_packet.py scripts/revalidation/wifi_cnss_start_only_runner.py`
  - `git diff --check`
- Real-device no-start validation:
  - `python3 scripts/revalidation/wifi_cnss_live_approval_packet.py --out-dir tmp/wifi/v255-cnss-live-approval-packet`
- Expected decision:
  - `live-approval-packet-ready`
- Expected evidence:
  - exact manual command includes all approval flags and `--max-runtime-sec 10`;
  - approved helper argv includes `--allow-cnss-start-only` only in the generated future command profile;
  - helper no-allow run reports `cnss_start.result=start-only-blocked` and `exec_attempted=0`;
  - `pidof cnss-daemon` remains absent.

## Acceptance

- V255 is accepted if the approval packet passes and no daemon is executed.
- V255 does not authorize live daemon start by itself.
- The next live step requires an explicit operator instruction.

## Assumptions

- Latest device build remains `A90 Linux init 0.9.59 (v159)`.
- Latest helper remains `a90_android_execns_probe v9` with SHA-256 `80e8afb1b77fdba23dfbc71d6a8e17e5a2a095ed1de728474fd2855923c351a1`.
- V254 profile refresh has already passed.
