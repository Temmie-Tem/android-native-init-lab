# S22+ M34 S10C0 Live Result + Stock Recovery

Date: 2026-07-10 00:57 KST / 2026-07-09 15:57 UTC

## 2026-07-11 Static-RE Correction

Retain the raw endpoint, timing, candidate, and rollback evidence below, but
withdraw the causal interpretation that `cmd-db.ko` acceptance deliberately
self-entered Download mode. Exact FYG8 source and shipped module metadata show
that S10C0's 89-module manifest omitted `qcom-dload-mode.ko`,
`sec_reboot_cmd.ko`, `sec_qc_rbcmd.ko`, and
`sec_qc_qcom_reboot_reason.ko`. Those modules implement the only identified
source-backed path from exact command string `download` to Samsung PON reason
`0x15`; FYG8 ABL then consumes `0x15` as Odin/Download. The present
`qcom-scm.ko` restart handler ignores the command pointer and can reset without
encoding `0x15`.

The host-visible Download endpoint therefore cannot distinguish a successful
candidate predicate from generic reset, boot failure, or bootloader fallback.
The internal `finit_module` result was not independently retained. Corrected
classification: `NO HARD PROOF OF FINIT_MODULE ACCEPTANCE OR SELF-DOWNLOAD`.
See
`docs/reports/S22PLUS_FYG8_BOOTLOADER_REBOOT_REASON_AND_RETAINED_MEMORY_STATIC_RE_2026-07-11.md`.

## Original Verdict (Superseded)

S10C0 produced the intended live signal:

```text
result=download-beacon-hit
module_load_probe=finit_cmd_db_accepted
probe_module=cmd-db.ko
probe_proc_name=cmd_db
```

Original interpretation: under native-init, the direct `cmd-db.ko`
`finit_module` probe reached
the accepted path and self-entered Download mode. That proves the S10A/S10B0
wall is not simply "cmd-db cannot be loaded at all"; the next technical unit
should distinguish load-loop skip/order/abort from `/proc/modules` observation
artifact.

However, the live run did not complete as a clean Magisk-baseline run. The
automatic Magisk boot rollback transferred successfully but Android did not
remain visible/stable long enough for `rollback_boot_ready`, so the analyzer
correctly keeps both advance gates closed:

```text
decision=s22plus-m34-s10c0-rollback-incomplete-recovery-required
ok_to_advance=false
ok_to_live_next_stage=false
missing_required_live_events=rollback_boot_ready
```

Recovery was then completed with the S10C0 stock boot-only fallback. The device
is back in Android stock-boot state:

```text
boot_completed=1
model=SM-S906N
device=g0q
bootloader=S906NKSS7FYG8
incremental=S906NKSS7FYG8
vbstate=orange
su=/system/bin/sh: su: inaccessible or not found
/debug_ramdisk/su=/system/bin/sh: /debug_ramdisk/su: inaccessible or not found
```

This is a recovery baseline, not the rooted Magisk measurement baseline. Do not
run another native-init live gate until the Magisk boot baseline is explicitly
restored and verified under a fresh bounded gate.

## Evidence

Live run directory:

```text
workspace/private/runs/s22plus_m34_s10c0_live_20260709T120611Z
```

Key live-log lines:

```text
line 166: s10c0_result=download-beacon-hit odin_device=/dev/bus/usb/002/127
line 167: beacon_hit_magisk_rollback_cmd=...
line 168: beacon_hit_magisk_rollback_odin_rc=0
line 572: result_json=.../result.json
line 573: result_summary={... "rc": 5, "result": "download-beacon-hit", "rollback_target": "magisk", ...}
```

Live result JSON:

```text
schema=s22plus_m34_s10c0_result_v1
stage=S10C0
target=SM-S906N/g0q/S906NKSS7FYG8
result=download-beacon-hit
rc=5
rollback_target=magisk
candidate_ap_sha256=9221cfa3ea3ce0776860a5041981e23a84d0be9b833203401dab771897266c6f
candidate_boot_sha256=8d77e1434cd47fe47f4723c948e4ff6db759cbe4bf75dd21e9e0c265d928c6df
candidate_init_sha256=cd80d5923c94f8a423821bc6dee4547f22763e177fbcc637d1bcb101c4b8c39b
base_boot_sha256=2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
module_load_probe=finit_cmd_db_accepted
probe_module=cmd-db.ko
probe_proc_name=cmd_db
```

Live timeline JSON used the canonical `events:[{name,timestamp_utc}]` shape but
missed `rollback_boot_ready`:

```text
live_session_start
candidate_flash_start
candidate_flash_done
candidate_boot_ready
rollback_flash_start
rollback_flash_done
live_session_end
```

Stock rollback-only run directory:

```text
workspace/private/runs/s22plus_m34_s10c0_stock_rollback_only_20260709T155407Z
```

Stock rollback evidence:

```text
line 17: rollback_only_stock_rollback_cmd=...
line 18: rollback_only_stock_rollback_odin_rc=0
line 98: boot_completed=1
line 105: su_root_rc=127
line 107: debug_ramdisk_su_root_rc=127
line 112: result_summary={... "rc": 0, "result": "rollback-only-no-s10c0-proof", "rollback_target": "stock", ...}
```

The rollback-only result is intentionally not S10C0 proof:

```text
decision=s22plus-m34-s10c0-rollback-only-no-direct-finit-proof
cmd_db_direct_finit_observed=false
ok_to_advance=false
```

## Host Commands

Live analyzer:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/analyze_s22plus_m34_s10c0_result.py \
  workspace/private/runs/s22plus_m34_s10c0_live_20260709T120611Z/result.json \
  --write-report --json
```

Stock rollback-only recovery:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m34_s10c0_direct_finit_loader_audit_live_gate.py \
  --rollback-from-download \
  --rollback-target stock \
  --ack S22PLUS-M34-S10C0-DIRECT-FINIT-LOADER-AUDIT-ROLLBACK-FROM-DOWNLOAD \
  --run-dir workspace/private/runs/s22plus_m34_s10c0_stock_rollback_only_20260709T155407Z
```

Analyzer fix validation:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/analyze_s22plus_m34_s10c0_result.py \
  tests/test_analyze_s22plus_m34_s10c0_result.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests/test_analyze_s22plus_m34_s10c0_result.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests/test_analyze_s22plus_m34_s10c0_result.py \
  tests/test_s22plus_m34_s10c0_direct_finit_loader_audit_live_gate.py \
  tests/test_s22plus_m34_s10b0_module_load_prefix_live_gate.py \
  tests/test_s22plus_m34_runtime_gadget_split_build.py
```

Result:

```text
Ran 23 tests in 0.036s
OK

Combined focused tests: Ran 40, OK, skipped=2
```

## Next

1. Restore the Magisk boot measurement baseline with a fresh bounded
   boot-only gate, or explicitly choose a stock-only path and update the live
   helpers accordingly.
2. After the rooted baseline is re-established, use the S10C0 HIT to design
   S11 host-only: per-module attempted/rc/errno plus a positive-control module,
   with the first question focused on why direct `cmd-db.ko` `finit_module`
   accepted while the earlier `/proc/modules` beacon missed `cmd_db`.
3. Do not reuse the consumed S10C0 live authorization for another candidate
   flash.
