# S22+ Native-Init M17 Power-QMP Live Gate Preflight - 2026-07-08

## Verdict

PASS: M17 live gate is prepared and dry-run validated. No live flash was
executed.

This preflight adds the checked live helper and the SHA-pinned `AGENTS.md`
boot-only exception for exactly the M17 power-QMP candidate.

## Helper

- Helper: `workspace/public/src/scripts/revalidation/s22plus_m17_power_qmp_live_gate.py`
- Live ack: `S22PLUS-M17-POWER-QMP-LIVE-GATE`
- Rollback-only ack: `S22PLUS-M17-ROLLBACK-FROM-DOWNLOAD`
- Candidate AP: `workspace/private/outputs/s22plus_native_init/inplace_m17_power_qmp_v0_1/odin4/AP.tar.md5`
- Manifest: `workspace/private/outputs/s22plus_native_init/inplace_m17_power_qmp_v0_1/manifest.json`

M17 has no reboot beacon and no ACM-triggered download command. If it parks or
ACM appears, rollback requires operator manual download-mode entry followed by
the rollback-only helper mode.

## Pinned Artifact

- AP.tar.md5 SHA256: `78b2641788a1517f39bdbd50dc425dbaeab0683aa662bcd8bfe9c925a8a50274`
- boot.img SHA256: `090811c8f50aab753ef7f085c3cf5bd73e9d6d43e2ad629e95d2cfe48a0ecac2`
- Base Magisk boot SHA256: `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`
- Kernel SHA256: `bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff`
- M17 `/init` SHA256: `34389fc52cd74aa50b2ab2980075183bcde519ffc5d7f9dfb787e1e5b3e2bfe4`
- M17 module-list SHA256: `1e00da43ae2b22c56855a28967201733b66b65ec4e91086faa67a4d9b3177fb8`
- M17 source SHA256: `561099a8401ea6b5d5642614b6f6a73e225b239556de07c11cf2d99e1d0a6d2f`
- Rollback Magisk boot-only AP SHA256: `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`
- Stock boot-only fallback AP SHA256: `1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e`

AP tar members:

```text
boot.img.lz4
```

## Module Gate

The helper verifies the exact 21-module list and rejects drift:

```text
clk-rpmh.ko
gcc-waipio.ko
icc-rpmh.ko
qcom_ipc_logging.ko
rpmh-regulator.ko
clk-dummy.ko
clk-qcom.ko
cmd-db.ko
debug-regulator.ko
gdsc-regulator.ko
icc-bcm-voter.ko
icc-debug.ko
minidump.ko
qti-fixed-regulator.ko
proxy-consumer.ko
qcom_rpmh.ko
qcom-scm.ko
sec_debug.ko
smem.ko
socinfo.ko
phy-msm-ssusb-qmp.ko
```

It also requires `blocked_watchdogs_present_in_closure=[]` and
`blocked_from_closure=[]`.

## Validation

Commands run:

```bash
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/s22plus_m17_power_qmp_live_gate.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m17_power_qmp_live_gate.py --offline-check

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m17_power_qmp_live_gate.py
```

Results:

- `py_compile`: pass
- `--offline-check`: pass; candidate and rollback AP hashes verified; no device action
- dry-run: pass; `AGENTS.md` exception verified, current Android/Magisk
  baseline stable for 4 samples, current boot SHA matched the pinned Magisk
  boot hash, no live flash

Current rooted Android baseline at dry-run:

```text
boot_completed=1
bootanim=stopped
verifiedbootstate=orange
Magisk root available
```

## Next Live Command

Only run supervised:

```bash
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m17_power_qmp_live_gate.py \
  --live --ack S22PLUS-M17-POWER-QMP-LIVE-GATE
```

If M17 parks or ACM appears, manually enter download mode and run:

```bash
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m17_power_qmp_live_gate.py \
  --rollback-from-download --ack S22PLUS-M17-ROLLBACK-FROM-DOWNLOAD
```

## Interpretation

- Park or ACM: powered QMP no longer causes the loop; proceed to the next
  add-back rung.
- Bootloop: QMP still faults even with substrate; stop blind subset work and
  wait for UART-quality evidence.
