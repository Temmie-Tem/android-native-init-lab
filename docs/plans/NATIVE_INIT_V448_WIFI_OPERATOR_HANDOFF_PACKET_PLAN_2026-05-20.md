# Native Init V448 Wi-Fi Operator Handoff Packet Plan

Date: 2026-05-20

## Goal

V448 closes the remaining operator sequencing gap before the first real V447
host preflight and live explicit Wi-Fi connect run.  The repo can now prepare
private, ignored handoff scripts that prompt for Wi-Fi values at execution time
instead of asking the operator to paste secrets into chat or tracked files.

## Scope

Allowed:

- run V446 secret guard;
- run V447 plan;
- generate private scripts under ignored `tmp/`;
- prompt for Wi-Fi values only at script execution time;
- unset Wi-Fi env values on script exit;
- require an exact live confirmation string before V445 live handoff.

Not allowed:

- write raw Wi-Fi values to tracked files or V448 evidence;
- run V443/V444/V445 during V448 packet generation;
- boot/flash Android or enable Wi-Fi from V448;
- expose any server listener.

## Implementation

- Packet generator: `scripts/revalidation/wifi_operator_handoff_packet_v448.py`
  - `plan`: records the packet plan without generating scripts;
  - `run`: runs V446, runs V447 plan, then writes:
    - `run-v447-host-preflight.sh`
    - `run-v447-live.sh`
  - both scripts prompt locally, export env values only inside the process, and
    clean them up on exit.

## Validation Plan

```text
python3 -m py_compile scripts/revalidation/wifi_operator_handoff_packet_v448.py

python3 scripts/revalidation/wifi_operator_handoff_packet_v448.py \
  --out-dir tmp/wifi/v448-operator-handoff-packet-plan-<ts> \
  plan

python3 scripts/revalidation/wifi_operator_handoff_packet_v448.py \
  --out-dir tmp/wifi/v448-operator-handoff-packet-run-<ts> \
  run

git diff --check
```

The generated script evidence must not contain raw Wi-Fi values.

## Expected Decisions

- `v448-operator-handoff-packet-plan-ready`
- `v448-operator-handoff-secret-guard-blocked`
- `v448-operator-handoff-v447-plan-blocked`
- `v448-operator-handoff-packet-ready`
- `v448-operator-handoff-packet-missing`

## Pass Criteria

V448 passes only when:

- V446 secret guard passes;
- V447 plan passes;
- host preflight and live handoff scripts are generated privately under ignored
  `tmp/`;
- V448 does not execute device commands or Wi-Fi bring-up;
- generated scripts contain prompts and cleanup logic, not Wi-Fi values.

## Next Gate

Run the generated host preflight script.  If V447 returns preflight-ready, run
the generated live script to perform the bounded explicit scan/connect test.

Server exposure remains blocked.
