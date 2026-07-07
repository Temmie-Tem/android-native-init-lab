# S22+ Ramoops Vendor Boot + M13 Capture Policy Activation (2026-07-08)

## Verdict

POLICY ACTIVE / DRY-RUN PASS / LIVE NOT EXECUTED.

Codex added the narrow `AGENTS.md` exception for one attended S22+ ramoops
positive-control sequence:

1. Flash the direct byte-preserving `vendor_boot` candidate.
2. Require Android/root to return.
3. Verify live DT `ramoops_region/status=okay`.
4. Flash the known parking M13 boot candidate.
5. Roll back `boot`.
6. Collect pstore if available.
7. Restore stock `vendor_boot`.

No live flash, Odin transfer, reboot command, rollback, or partition write was
performed in this activation step.

## Guarded Helper

```text
workspace/public/src/scripts/revalidation/s22plus_ramoops_vendor_boot_m13_capture_live_gate.py
```

Live ack token:

```text
S22PLUS-RAMOOPS-VENDORBOOT-M13-CAPTURE-LIVE-GATE
```

Rollback/restore tokens:

```text
S22PLUS-RAMOOPS-M13-ROLLBACK-BOOT-FROM-DOWNLOAD
S22PLUS-RAMOOPS-RESTORE-STOCK-VENDOR-BOOT
```

The exception does not authorize recovery, dtbo, vbmeta, vbmeta_system, BL, CP,
CSC, super, userdata, persist, EFS, sec_efs, RPMB, keymaster, modem,
bootloader, raw host `dd`, fastboot, Magisk modules, multidisabler, format
data, M15/M18/QMP candidates, additional boot candidates, additional
`vendor_boot` candidates, kernel rebuilds, or A90 action.

## Pinned Artifacts

```text
vendor_boot candidate AP.tar.md5
0af250628c7cd5d7062b53823162f55716d1758d31ff88f65ea1c61dd0da83c3

stock vendor_boot rollback AP.tar.md5
2f9075fe609e7aa66c2ec88a2bd0223d6a9d7ff23d8bab0f7c4eb44633f480bb

patched vendor_boot image
d62f2da241e1104db9e4b72aa0ba1927c0e85afd22fe380bff62c8df52bd3245

stock vendor_boot image
096e433e049fb088cd956e083d5a1039b33cdf0ca907e713bba7feaaf1b080b7

source DTB
2cd64d43a4f6b89a7c5523f3ef73fbb84dcad92c6d857e649cd1f0baa7c0080e

patched DTB
b862359dc65adb1eb9f5f17f1b8be637eb0135e88a681d779f9cbeda3ae5a3ec

M13 candidate AP.tar.md5
5e959f0dd7c55d8e6a9363cde0c0fcc72876639bdc46ccdc826186cfc43134fa

M13 padded boot.img
21808217d6cf698217e25cf35caf3a271a7f55451cad85ba576d54a40010441b

M13 base Magisk boot
2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e

M13 kernel
bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff

M13 /init
6b2d229217d83c7f36032c37291bebbebe7c8c5782d006fedcc538649d99f5d3

M13 source
4e3a88336c6a6e0b1ed6e25f572ed0ec26c2e8d177942598a6e32aa1b2a762e8

Magisk boot rollback AP.tar.md5
d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56

stock boot fallback AP.tar.md5
1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e
```

## Validation

Static validation:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/s22plus_ramoops_vendor_boot_m13_capture_live_gate.py
```

Result: pass.

Offline gate:

```text
PYTHONPATH=workspace/public/src/scripts/revalidation \
PYTHONPYCACHEPREFIX=/tmp/a90_pycache \
python3 workspace/public/src/scripts/revalidation/s22plus_ramoops_vendor_boot_m13_capture_live_gate.py \
  --offline-check
```

Result: pass. No device action.

Default dry-run:

```text
PYTHONPATH=workspace/public/src/scripts/revalidation \
PYTHONPYCACHEPREFIX=/tmp/a90_pycache \
python3 workspace/public/src/scripts/revalidation/s22plus_ramoops_vendor_boot_m13_capture_live_gate.py
```

Result:

```text
dry-run ok: vendor_boot/M13 candidates, rollback APs, AGENTS exception, Android stability, boot hash, and stock vendor_boot hash verified
```

Dry-run log:

```text
workspace/private/runs/s22plus_ramoops_vendor_boot_m13_capture_20260707T183204Z/s22plus_ramoops_vendor_boot_m13_capture_live_gate.txt
```

The dry-run verified `agents_exception_missing=[]`, Android stability, Magisk
root, current boot hash, and current stock `vendor_boot` hash. It did not run a
live flash path.

## Operator Bootloop Report Recheck

After the operator reported another bootloop observation followed by manual
download-mode entry, the host saw the device back in normal Android over ADB.
Read-only checks showed:

```text
model=SM-S906N
device=g0q
build=AP3A.240905.015.A2.S906NKSS7FYG8
sys.boot_completed=1
ro.boot.verifiedbootstate=orange
ro.boot.boot_recovery=0
```

The dry-run revalidated:

```text
boot        2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
vendor_boot 096e433e049fb088cd956e083d5a1039b33cdf0ca907e713bba7feaaf1b080b7
```

Interpretation: the device is currently recovered to the rooted Magisk boot +
stock FYG8 `vendor_boot` baseline. The bootloop/reset root cause is still not
explained because current Android has no useful retained kernel console.

## Next Step

The next live step is not another blind boot candidate. It is the attended
ramoops positive-control flow with the live ack token above. If it proceeds, the
run must restore `boot` and stock `vendor_boot` through the pinned rollback
paths and then report whether M13 produced retained pstore evidence.
