# Native Init V724 QRTR/Service-Locator Boot Proof Plan

- date: `2026-05-24 KST`
- cycle: `v724`
- boot artifact: `A90 Linux init 0.9.68 (v724)`
- builder: `scripts/revalidation/build_native_init_boot_v724.py`
- boot image: `stage3/boot_linux_v724.img`
- gate: post-ACM boot-window lower companion proof

## Goal

V723 proved that late lower companion startup can reconnect service-locator but
does not recover service `180/74` after the kernel `servloc` timeout has already
fired.

V724 moves the same lower-only action into the boot window:

```text
USB ACM ready -> console attached -> one-shot flag check
  -> mount /mnt/system read-only if needed
  -> ensure selinuxfs surface
  -> spawn helper out-of-line
  -> PID1 immediately continues to shell
```

The helper mode remains:

```text
qrtr-ns -> pd-mapper -> rmt_storage -> tftp_server
```

## Scope

Allowed:

- flash a rollback-ready native init boot image;
- consume `/cache/native-init-qrtr-servloc-boot-v724` only when it contains
  `run`;
- start only `qrtr-ns`, `pd-mapper`, `rmt_storage`, and `tftp_server`;
- record kmsg, timeline, `/cache/native-init-qrtr-servloc-boot-v724.log`, and
  helper PID evidence;
- collect read-only dmesg/QRTR/CNSS2 markers after boot.

Blocked:

- pre-ACM PID1 blocking work;
- CNSS daemon start;
- Android service-manager start;
- Wi-Fi HAL or `wificond` start;
- scan/connect/link-up;
- credential use;
- DHCP, route changes, and external ping.

## Safety Design

V572 showed that pre-ACM helper execution can remove host recovery visibility.
V724 avoids that failure mode:

1. the hook runs only after USB ACM and console attach have completed;
2. the flag is one-shot and consumed before execution;
3. helper execution is `a90_run_spawn()` only, not a PID1 foreground wait;
4. helper stdout/stderr is appended to a private no-follow cache log;
5. PID1 proceeds to normal shell even if the helper later hangs or exits;
6. known-good rollback remains `stage3/boot_linux_v319.img`.

## Success Criteria

Primary positive:

- device boots `0.9.68 (v724)` with the disabled flag absent;
- armed boot returns to serial shell;
- V724 kmsg/timeline/log show helper spawn before the kernel `servloc` timeout;
- dmesg shows service-locator and service `180` or `74` before timeout;
- no CNSS/HAL/connect/credential/external ping guardrail is crossed.

Partial positive:

- service-locator reconnects before timeout but service `180/74` remains absent.

Failure labels:

- `v724-disabled-smoke-fail`: new image fails with flag absent;
- `v724-helper-missing`: helper absent or non-regular;
- `v724-android-layout-fail`: `/mnt/system/system` setup failed;
- `v724-selinuxfs-fail`: selinuxfs surface unavailable;
- `v724-spawn-fail`: helper fork/exec setup failed;
- `v724-boot-window-no-wlanpd`: helper ran before timeout but service `180/74`
  stayed absent;
- `v724-guardrail-crossed`: CNSS/HAL/connect/ping path was used unexpectedly.

## Validation Plan

Static:

```bash
python3 -m py_compile scripts/revalidation/build_native_init_boot_v724.py
python3 scripts/revalidation/build_native_init_boot_v724.py
strings stage3/boot_linux_v724.img | rg \
  'A90 Linux init 0\.9\.68 \(v724\)|A90v724|native-init-qrtr-servloc-boot-v724'
git diff --check
```

Disabled live smoke:

```bash
python3 scripts/revalidation/native_init_flash.py \
  stage3/boot_linux_v724.img \
  --expect-version "A90 Linux init 0.9.68 (v724)" \
  --verify-protocol auto \
  --from-native
```

Armed live proof:

```text
write /cache/native-init-qrtr-servloc-boot-v724 = run
reboot native init
collect status, bootstatus, dmesg, QRTR table, V724 cache log, and helper PID
```

## Next Gate

If V724 produces service `180/74` before `servloc` timeout, move to a same-boot
CNSS2 callback/WLFW progression observer. If it does not, the blocker is below
the lower companion user services and the next gate should compare Android's
earliest QRTR/SERVREG bring-up sequence against native boot-time kernel state.
