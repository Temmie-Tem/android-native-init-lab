# Native Init V631 Per-Node Sibling-SSCTL Proof Prep Report

- date: `2026-05-23 KST`
- status: `local-build-pass`; live flash not yet executed in this report
- native build: `A90 Linux init 0.9.66 (v631)`
- builder: `scripts/revalidation/build_native_init_boot_v631.py`
- local boot image: `stage3/boot_linux_v631.img`
- rollback image: `stage3/boot_linux_v319.img`

## Scope

This prep step implements and locally validates the V631 boot-image proof. It
does not flash the device, reboot the device, arm the proof flag, start Wi-Fi
daemons, start Wi-Fi HAL, scan/connect, use credentials, run DHCP, change
routes, or ping externally.

## Implementation

V631 adds a post-ACM, flag-gated, per-node sibling SSCTL proof to
`stage3/linux_init/v631/90_main.inc.c`.

Compared with V630:

- ADSP, CDSP, and SLPI are attempted in separate child processes.
- Each node gets an independent `5000ms` timeout.
- Parent PID1 logs per-node child status, timeout, and reap result.
- If a timed-out child cannot be reaped, V631 stops remaining nodes instead of
  stacking blocked children.

## Local Validation

```text
python3 -m py_compile scripts/revalidation/build_native_init_boot_v631.py
python3 scripts/revalidation/build_native_init_boot_v631.py
```

Result:

```text
markers: pass
init_sha256=f1db1df18ef40504bdc608c02287fd82cef779aa1993afbf442705d111521935
ramdisk_sha256=20edd5a583c26d47170f8d2ee9cf44c23f064bb1fa4ad353433ac3da9bd61c3f
boot_sha256=00a8a903ed9343f83a9a8166a446151a4be55dfaadd70f5626467dc83b865060
```

The builder verified these boot-image markers:

- `A90 Linux init 0.9.66 (v631)`
- `A90v631: sibling ssctl proof armed`
- `native-init-sibling-ssctl-v631`

## Next Step

Proceed to live V631 validation:

1. disabled-smoke flash with the V631 arm flag absent;
2. armed proof with exact flag content `run`;
3. rollback to V319;
4. classify the per-node ADSP/CDSP/SLPI map and decide whether any lower Wi-Fi
   marker advanced.

