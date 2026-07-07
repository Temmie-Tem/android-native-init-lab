# S22+ Ramoops Vendor-Boot + M13 Capture Gate Source (2026-07-08)

## Scope

Host-only source/gate work. No device action, no reboot, no flash, and no
partition write.

This follows the byte-preserving direct `vendor_boot` ramoops build and prepares
the positive-control capture run without authorizing it. The live target is M13
first, not M15/M18, because the current steer requires proving the ramoops
channel on a known parking native-init before pointing it at the QMP PHY fault.

## Added Helper

`workspace/public/src/scripts/revalidation/s22plus_ramoops_vendor_boot_m13_capture_live_gate.py`

Modes:

- `--offline-check`: verify all AP packages and manifests; no device action; does
  not require an `AGENTS.md` live exception.
- default dry-run: verify packages, then require a future SHA-pinned
  `AGENTS.md` exception before touching Android state.
- `--live`: once separately authorized, intended flow is patched vendor_boot
  flash, Android/root return, live DT `ramoops_region/status=okay` check, M13
  boot flash, host observation, Magisk boot rollback, pstore collection, and
  stock vendor_boot restore.
- `--rollback-boot-from-download`: attended recovery mode if M13 parks and the
  operator manually enters download mode.
- `--restore-vendor-boot-from-download` / `--restore-vendor-boot-from-android`:
  explicit stock vendor_boot restore paths.

## Required Pinned Artifacts

```text
vendor_boot candidate AP.tar.md5 0af250628c7cd5d7062b53823162f55716d1758d31ff88f65ea1c61dd0da83c3
vendor_boot rollback AP.tar.md5  2f9075fe609e7aa66c2ec88a2bd0223d6a9d7ff23d8bab0f7c4eb44633f480bb
patched vendor_boot              d62f2da241e1104db9e4b72aa0ba1927c0e85afd22fe380bff62c8df52bd3245
stock vendor_boot                096e433e049fb088cd956e083d5a1039b33cdf0ca907e713bba7feaaf1b080b7
source DTB                       2cd64d43a4f6b89a7c5523f3ef73fbb84dcad92c6d857e649cd1f0baa7c0080e
patched DTB                      b862359dc65adb1eb9f5f17f1b8be637eb0135e88a681d779f9cbeda3ae5a3ec
M13 AP.tar.md5                   5e959f0dd7c55d8e6a9363cde0c0fcc72876639bdc46ccdc826186cfc43134fa
M13 boot.img                     21808217d6cf698217e25cf35caf3a271a7f55451cad85ba576d54a40010441b
M13 base Magisk boot             2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
M13 /init                        6b2d229217d83c7f36032c37291bebbebe7c8c5782d006fedcc538649d99f5d3
M13 source                       4e3a88336c6a6e0b1ed6e25f572ed0ec26c2e8d177942598a6e32aa1b2a762e8
Magisk rollback AP               d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56
stock boot fallback AP           1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e
```

Required tar members:

```text
vendor_boot APs: vendor_boot.img.lz4
M13/boot rollback APs: boot.img.lz4
```

Ack tokens reserved by the helper:

```text
S22PLUS-RAMOOPS-VENDORBOOT-M13-CAPTURE-LIVE-GATE
S22PLUS-RAMOOPS-M13-ROLLBACK-BOOT-FROM-DOWNLOAD
S22PLUS-RAMOOPS-RESTORE-STOCK-VENDOR-BOOT
```

## Validation

```bash
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/s22plus_ramoops_vendor_boot_m13_capture_live_gate.py

PYTHONPATH=workspace/public/src/scripts/revalidation \
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_ramoops_vendor_boot_m13_capture_live_gate.py \
  --offline-check

PYTHONPATH=workspace/public/src/scripts/revalidation \
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_ramoops_vendor_boot_m13_capture_live_gate.py
```

Results:

```text
py_compile: pass
offline-check: pass; verified vendor_boot/M13 candidates and rollback APs; no device action
default dry-run: blocked before Android/device action because AGENTS.md has no
  ramoops vendor_boot + M13 authorization markers; rc=1
```

Private offline-check log:

`workspace/private/runs/s22plus_ramoops_vendor_boot_m13_capture_20260707T182525Z/s22plus_ramoops_vendor_boot_m13_capture_live_gate.txt`

## Next Gate

Before any live capture attempt, add a narrow SHA-pinned `AGENTS.md` exception
covering exactly this helper and the hashes/tokens above.

Do not run `--live`, `--rollback-boot-from-download`, or any vendor_boot restore
mode until that exception exists and the operator is actively attending the
device.
