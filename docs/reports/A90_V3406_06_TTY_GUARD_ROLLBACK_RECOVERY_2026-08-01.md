# A90 V3406-06 tty guard rollback recovery

Date: 2026-08-01

Status: `NO_PROOF_A90_F1_RP_CANDIDATE_ROLLED_BACK`

## Closed result

Run `a90-v3406-debian-display-f1-20260801-06` completed one exact boot-only
candidate transfer, no candidate replay, one exact V2321 rollback transfer,
and final V2321 health verification. The canonical timeline is closed. The
separately connected S22+ received no command and no non-boot partition was
written.

The private structured result SHA256 is:

```text
5a161a5c189da8aee8da28e2a52eff8d6f5dae94adb4053cbf3dcbdc7f391f4f
```

The candidate flash log proves local-image validation, native recovery,
manifest-bound recovery endpoint selection, payload transfer, boot write,
exact readback, and native selftest. Its returned native output identifies
version `0.11.161`, build `phase2-display-v1-native-handoff`, and selftest
`fail=0`. The resident experiment stopped before Debian handoff, so it produced
no Debian or display proof.

## Host guard defect

The transient udev rule correctly put `ID_MM_DEVICE_IGNORE=1` and
`ID_MM_PORT_IGNORE=1` on the exact `/sys/class/tty/ttyACM*` node. The runner
resolved that tty correctly but called `guard.matches_node()` with
`endpoint.device_path`, the USB-interface sysfs node. That node does not own
the tty properties, so the validator reported a false guard failure before
candidate health.

The first rollback invocation then selected `adb-recovery` even though the
device was still at the healthy native prompt. Its durable raw-log
classification is exact: local image validation passed, while native recovery
request, recovery endpoint selection, payload transfer, boot write, boot
write completion, and readback are all false. It therefore consumed no
rollback transfer and changed no device state.

## Bounded recovery deviation

Before recovery, the host durably recorded the deviation intent, revalidated
the unchanged V2321 image and canonical flash runner, selected the exact A90
bridge, and proved the candidate version and selftest. A new transient guard
was armed and privileged udev replay proved both ignore properties on the
actual tty node.

The canonical `native_init_flash.py --from-native` path then requested recovery
from native-init and performed the already-authorized exact rollback once. Its
raw classification proves all seven phases, including boot write and exact
readback. Returned V2321 version `0.9.285`, build
`v2321-usb-clean-identity-rodata`, and selftest `fail=0` passed. A second
short-lived guard protected final health and both transient rules were removed
cleanly.

The recovery-deviation closure and final-health receipt SHA256 values are:

```text
71c6cfc88f340d092bc58feaeabb1a84f798badfa1679305296b06b66bcc6dae
5e6f0bf0d04b4238c102fd4e747dee85ece87369a5adcf6914b3291b604ca44b
```

The journal records candidate transfer count `1`, rollback transfer count `1`,
candidate replay `false`, restored final health, and a closed canonical event
timeline. Reporting recovery reconstructed `candidate-boot-ready` from the
already-durable exact candidate flash log; it did not repeat a device command
or transition.

## Next H0 gate

The next unit is deliberately small:

1. validate ModemManager properties on `endpoint.tty_class`, not
   `endpoint.device_path`;
2. exercise the installed rule on the exact tty node before proceeding;
3. add a regression that keeps interface properties absent while tty
   properties are present; and
4. independently review the changed execution-critical closure before another
   F1 manifest is prepared.

No A90 live authority remains, and this run, candidate, approval, and rollback
transition are non-reusable.
