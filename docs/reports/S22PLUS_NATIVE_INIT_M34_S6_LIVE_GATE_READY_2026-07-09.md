# S22+ M34 S6 Stock-Softdep Live Gate Ready

Date: 2026-07-09 KST

Status: HOST-ONLY HELPER READY. No live flash is authorized by this report.

## Scope

This unit prepares the guarded live gate for the already-built M34 S6 native-init
candidate. It does not modify `AGENTS.md`, does not flash, does not reboot, and
does not touch a connected device.

## Helper

Added:

```text
workspace/public/src/scripts/revalidation/s22plus_m34_s6_stock_softdep_live_gate.py
tests/test_s22plus_m34_s6_stock_softdep_live_gate.py
```

The helper is dry-run by default and fails closed until a fresh SHA-pinned active
`AGENTS.md` exception exists. The live token it expects is:

```text
S22PLUS-M34-S6-STOCK-SOFTDEP-LIVE-GATE
```

The rollback-from-download token it expects is:

```text
S22PLUS-M34-S6-STOCK-SOFTDEP-ROLLBACK-FROM-DOWNLOAD
```

## Pinned S6 Contract

Candidate AP:

```text
workspace/private/outputs/s22plus_native_init/m34_runtime_gadget_split_v0_5/S6/odin4/AP.tar.md5
```

Pinned hashes:

```text
AP.tar.md5   f1ff77b7df434536029db417291689bff8b3a7dcdf4fda38fef5322475daad39
boot.img     b1bfc4ece7ece60af752bc570e0ae4ce76230d13b129b1c58d4e840cd92225f6
/init        ca3eb2b5a0fedff73cfb0aaa249d42f4b92fcb99b360e9ec5a041649dcd7dd8c
module list  51ba77aeed1966a2de8c78d307ca3d6fe5440daa2b96488679446f6056142515
source       ce023ba98006e49839433ce16ec8321bd9003b74151f39879fcecb682fef9ecc
kernel       bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff
base boot    2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
```

Runtime contract enforced from the manifest:

- stage is exactly `S6`
- AP contains exactly `boot.img.lz4`
- 55-module closure is exact
- QMP/EUD/ucsi softdep targets are present
- `sec_debug_region.ko` is absent
- `max_speed_high_speed=0`
- `ssusb_speed_high_speed=0`
- `ssusb_mode_peripheral=1`
- `soft_connect=0`
- `stock_softdep_parity=1`
- no required `high-speed`, `g1/max_speed`, `ssusb/speed`, `/sys/class/usb_role`,
  or `soft_connect` strings
- no reboot syscall in the compiled `/init` objdump

## Observation

The helper reuses the enhanced host-side USB observation path from the S5 result:

- `lsusb -d 04e8:6860 -v`
- `lsusb -t`
- `usb-devices`
- `/dev/ttyACM*` and `/dev/serial/by-*`
- udev properties
- host dmesg tail
- all Samsung `04e8:*` device summaries, including `685d` upload/download
  detection

This is required because S5 did not enumerate `04e8:6860` and later fell to
Samsung `04e8:685d`.

## Validation

Passed:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile workspace/public/src/scripts/revalidation/s22plus_m34_s6_stock_softdep_live_gate.py
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest tests.test_s22plus_m34_s6_stock_softdep_live_gate
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/s22plus_m34_s6_stock_softdep_live_gate.py --offline-check
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/s22plus_m34_s6_stock_softdep_live_gate.py --print-agents-exception-draft
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/s22plus_m34_s6_stock_softdep_live_gate.py
```

The default invocation failed closed before Android/device actions because
`AGENTS.md` has no active S6 authorization. That is the expected state.

## Next

Live is still not authorized. To run S6 live later, promote a fresh active
`AGENTS.md` exception using the helper's printed draft, run the default dry-run
again, and only then run live with the exact S6 ack token.
