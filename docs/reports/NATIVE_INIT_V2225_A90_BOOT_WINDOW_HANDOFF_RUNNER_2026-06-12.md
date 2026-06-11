# Native Init V2225 A90 Boot-Window Handoff Runner

## Summary

- Cycle: `V2225`
- Type: rollbackable boot-window handoff runner; default execution is host-only dry-run.
- Decision: `v2225-boot-window-helper-parse-incomplete-rollback-pass`
- Result: `FAIL`
- Reason: rollback passed, but helper artifacts did not parse cleanly
- Execute mode: `True`
- Evidence: `workspace/private/runs/kernel/v2225-live-20260612-071624`

## Images

- Test image: `workspace/private/inputs/boot_images/boot_linux_v2224_a90_boot_window_observer.img`
- Test SHA256: `ad177a775e7c1952e1dba8120066ec9bc3f8814a6f2d6360f83f314bd2c513df`
- Test version: `A90 Linux init 0.9.262 (v2224-a90-boot-window-observer)`
- Rollback image: `workspace/private/inputs/boot_images/boot_linux_v2189_security_p0_stage_fix.img`
- Rollback SHA256: `f54becb2b720ad198413c2a0089912626ca295c79a96f13e0921cf4f05b39f51`
- Rollback version: `A90 Linux init 0.9.261 (v2189-security-p0-stage-fix)`

## Live Contract

- Live mode requires `--execute` plus the exact confirmation token.
- Live sequence: V2222 preflight -> flash V2224 -> collect `/cache/native-init-wifi-test-boot-v2224-*` -> V2220 parser -> rollback V2189 -> selftest fail=0.
- Collection is read-only after boot; it uses `cat` over the native bridge and the helper-owned trace output.

## Live Evidence

- V2222 preflight before flash: PASS.
- V2224 test boot flash: PASS; boot verified `A90 Linux init 0.9.262 (v2224-a90-boot-window-observer)`.
- V2224 test boot selftest: PASS, `fail=0`.
- Initial artifact collection hit serial/UI contention:
  - helper result: `A90P1 END marker not found`;
  - summary/log: `status=busy` from the active auto menu.
- Post-rollback read-only recollection with `--hide-on-busy` recovered the V2224 artifacts from `/cache`.
- V2189 rollback: PASS; post-rollback status verified `A90 Linux init 0.9.261 (v2189-security-p0-stage-fix)`.
- Post-rollback selftest: PASS, `fail=0`.

## Live Diagnosis

- The V2224 helper did not reach WLFW/CNSS trace collection.
- Recovered helper result:
  - `helper_status=setup-error`;
  - `setup_error=lstat property root: No such file or directory`;
  - `child_exit_code=20`.
- Recovered summary:
  - `helper_exit_code=20`;
  - `supervisor_result=helper-complete-no-wlan0`;
  - `helper_result_path=/cache/native-init-wifi-test-boot-v2224-helper.result`.
- Recovered log shows firmware-class path and debugfs preparation succeeded before the helper setup error.
- Root cause: V2224 configured `wifi_test.property_root=/mnt/sdext/a90/private-property-v317/v2224/dev/__properties__`, but that property root was not present on the device. The existing reusable property root `/mnt/sdext/a90/private-property-v317/v726/dev/__properties__` is present.
- Next unit: build V2226 with the same observer route but a present/staged property root, and keep `--hide-on-busy` on all bridge artifact collection commands.

## Safety Scope

- Dry-run does not flash, reboot, write device partitions, scan/connect Wi-Fi, use credentials, configure DHCP/routes, ping, attach BPF, execute `probe_write_user`, or write tracefs controls.
- Live mode flashes only the approved rollbackable V2224 test boot and V2189 rollback image.
- It does not use Wi-Fi HAL scan/connect, credentials, DHCP/routes, external ping, PMIC/GPIO/GDSC/eSoC/PCI paths, platform bind/unbind, or `sda29` writes.
