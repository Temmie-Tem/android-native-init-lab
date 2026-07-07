# S22+ SM8450 OpenOCD Target CFG Derivation (2026-07-08)

## Verdict

Host-only B1 EUD/OpenOCD staging advanced one gate: an SM8450/S22+ target cfg
now exists under the public OpenOCD script tree, and a DTB-backed auditor checks
that it matches the stock FYG8 CPU/CTI topology.

Live attach is still not executed. The host still has no current EUD USB
endpoint, and the cfg intentionally leaves per-core DBGBASE discovery to the
OpenOCD aarch64 ROM-table path because the stock DTB does not source-prove those
addresses.

## Scope

- Device action: no
- Flash/reboot/partition write: no
- Sysfs write/EUD enable: no
- Private payload committed: no

## Added

- `workspace/public/src/openocd/target/qualcomm/sm8450_s22plus_romtable.cfg`
- `workspace/public/src/scripts/revalidation/s22plus_sm8450_openocd_target_cfg_audit.py`
- `tests/test_s22plus_sm8450_openocd_target_cfg_audit.py`

## Source-Derived Facts

The auditor decompiled the stock FYG8 `vendor_boot` DTB with the private staged
`dtc` tool and extracted:

- CPU count: 8
- CPU CTI count: 8
- CTI bases: `0x12010000`, `0x12020000`, `0x12030000`, `0x12040000`,
  `0x12050000`, `0x12060000`, `0x12070000`, `0x12080000`
- The `cti@112060000` node name for CPU5 is a dtc-rendered node-name mismatch;
  its `reg = <0x12060000 0x1000>` is the value used by the cfg.
- ETE/funnel trace topology exists, but no per-core CPU debug-base / DBGBASE
  node was found.

Therefore the cfg hardcodes only the CTI bases and does **not** hardcode
`-dbgbase`.

## Validation

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/s22plus_sm8450_openocd_target_cfg_audit.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests/test_s22plus_sm8450_openocd_target_cfg_audit.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_sm8450_openocd_target_cfg_audit.py \
  --require-pass

S22+ SM8450 OpenOCD target cfg audit: sm8450_cfg_draft_ready_romtable_dbgbase; cpus=8 cpu_ctis=8 dbgbase_hints=0 cfg=1; log=workspace/private/runs/s22plus_sm8450_openocd_target_cfg_audit_20260707T225511Z/summary.json

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_eud_openocd_host_audit.py \
  --openocd workspace/private/tools/linux-msm-openocd-eud/install/bin/openocd \
  --script-dir workspace/private/tools/linux-msm-openocd-eud/install/share/openocd/scripts \
  --script-dir workspace/public/src/openocd

S22+ EUD OpenOCD host audit: waiting_for_eud_enumeration_or_hardware; openocd=1 eud_cfg=1 qcom_cfg=1 sm8450_cfg=1 host_eud_usb=0; log=workspace/private/runs/s22plus_eud_openocd_host_audit_20260707T225521Z/summary.json
```

Host-audit movement is now proven: `sm8450_cfg=1`, with the remaining blocker
being `host_eud_usb=0`.

## Next Gate

The next live-relevant gate is not another native-init flash. It is either:

1. make a real EUD USB/SWD endpoint appear, then run a bounded OpenOCD init
   probe with this cfg; or
2. if EUD never enumerates on this host/device state, switch to another
   observability path instead of repeating M18/sec_debug flashes.
