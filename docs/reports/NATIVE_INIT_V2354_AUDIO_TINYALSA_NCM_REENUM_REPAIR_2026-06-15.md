# NATIVE_INIT V2354 — repair AUD-3C tinyalsa runner for NCM re-enumeration

Date: 2026-06-15

## Scope

Host-only runner repair after V2353. No flash, no ADSP command, no `/dev/snd` command, no tinyalsa execution, no mixer write, and no playback.

V2353 proved the audio side reached the safe pre-inventory point again, then blocked before inventory because the host could no longer reach the candidate boot over NCM/tcpctl after USB re-enumeration.

## Root Cause

The V2351 runner had two transport weaknesses:

1. It only probed host ping and `tcpctl` after materialization. If the V2334 candidate re-enumerated as a new host `enx*` interface/MAC, the host NetworkManager profile might still be bound to the previous interface, leaving `192.168.7.1/24` absent on the current A90 NCM link.
2. The readiness predicate used `int(step.get("rc") or 1) == 0`, which treats `rc=0` as false and converts it to `1`. That can misclassify successful ping/tcpctl steps as failed.

## Change

Updated `workspace/public/src/scripts/revalidation/native_audio_tinyalsa_inventory_live_handoff_v2349.py`:

- Added a pre-transfer repair command using the existing `ncm_host_setup.py setup` helper.
- The repair command is only invoked when the initial host ping/tcpctl probes cannot satisfy the requested inventory transport.
- The repair path uses the device-reported NCM host MAC with `--allow-auto-interface`, configures `192.168.7.1/24`, and uses `--sudo "sudo -n"` so it fails closed instead of blocking for a password.
- After repair, the runner re-runs host ping and `tcpctl ping` once, then selects `tcpctl` or serial transport from the post-repair evidence.
- Fixed the `rc=0` readiness predicate to compare `step.get("rc") == 0` directly.
- Added `--repair-host-ncm/--no-repair-host-ncm`, `--host-ip`, `--host-prefix`, `--ncm-setup-timeout`, `--ncm-interface-timeout`, and `--ncm-setup-sudo` runner options.

Updated `tests/test_native_audio_tinyalsa_inventory_live_handoff_v2349.py`:

- Dry-run now asserts the NCM repair plan is visible.
- Added a regression for initial transfer failure -> one `ncm_host_setup.py setup` -> post-repair `tcpctl` selection.
- Added a regression proving `--no-repair-host-ncm` fails closed without invoking setup.

Updated state docs:

- `GOAL.md` latest AUD-3C block now records V2353 and V2354.
- `CLAUDE.md` audio state now records V2353 and V2354.

## Dry-Run Evidence

```text
native_audio_tinyalsa_inventory_live_handoff_v2349.py --dry-run
# decision v2349-audio-tinyalsa-inventory-live-dry-run ok True
# repair_policy if initial host ping/tcpctl probes cannot satisfy the requested transport, run one ncm_host_setup.py setup repair, then re-probe once
# repair_cmd python3 workspace/public/src/scripts/revalidation/ncm_host_setup.py setup ... --allow-auto-interface ... --sudo sudo -n
```

Resident V2321 read-only NCM status path was also checked without running setup:

```text
ncm_host_setup.py status --device-protocol cmdv1 --sudo 'sudo -n'
# host interface: enx964ea8cb1e7b (...)
# host readiness: a90_ncm=True ipv4_192.168.7.1/24=True ipv6_link_local=False
```

## Validation

```text
python3 -m py_compile \
  workspace/public/src/scripts/revalidation/native_audio_tinyalsa_inventory_live_handoff_v2349.py \
  tests/test_native_audio_tinyalsa_inventory_live_handoff_v2349.py
# pass

PYTHONPATH=tests python3 -m unittest tests.test_native_audio_tinyalsa_inventory_live_handoff_v2349 -v
# Ran 9 tests — OK

python3 -m unittest discover -s tests -p 'test_*.py'
# Ran 1025 tests — OK

git diff --check
# pass
```

## Next Gate

The next safe unit is a fresh exact-gated AUD-3C live inventory attempt using the repaired runner.

Required phrase remains:

```text
AUD-3C-tinyalsa-inventory go: read-only tinyalsa mixer/PCM inventory on materialized V2334, no mixer set, no tinyplay/playback, rollback to V2321
```

Expected behavior on the next live attempt:

1. Flash V2334 and reproduce ADSP + `/dev/snd` materialization.
2. Probe host ping/tcpctl.
3. If NCM was re-enumerated and unreachable, run one `ncm_host_setup.py setup` repair.
4. Re-probe ping/tcpctl.
5. Stage `tinymix` and `tinypcminfo` over `tcpctl` if ready, otherwise serial over ACM if host NCM ping is ready.
6. Run read-only `tinymix`/`tinypcminfo` inventory only.
7. Roll back to V2321 and verify `selftest fail=0`.

Do not proceed to `tinyplay`, PCM playback/write, or mixer writes until read-only inventory succeeds and is reviewed.
