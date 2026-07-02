# Native Init V3365 Hot-Reload Delta H2 Live

- Cycle: `V3365` (H2 live)
- Decision: `v3365-hot-reload-delta-h2-changed-init-proven`
- Scope: prove a genuinely changed native-init ELF can be staged onto a V3364 resident and take effect through `reload` without a reboot.
- Device action: checked-helper flash V3364 resident, stage V3365 init ELF to SD, run `reload`, then checked-helper rollback to v2321.
- Final state: v2321 restored, `selftest fail=0`, staged V3365 ELF removed.

## Inputs

- Rollback baseline: `boot_linux_v2321_usb_clean_identity_rodata.img`
  - SHA256: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- Resident image flashed for H2: `boot_linux_v3364_init_hot_reload.img`
  - SHA256: `934f70384b3a470461666da8603620856219fdddf25cebff3d4378df04d8c8e7`
- Reload candidate init ELF: `workspace/private/builds/native-init/v3365-hot-reload-delta/init_v3365_hot_reload_delta`
  - SHA256: `bb105b55f399e9ada9670ca886ad1746653a6beaf1632a6b588c21fa63e01194`
  - Size: `1789328` bytes
- V3365 source build commit: `64916022`

## Execution

1. Preflight on resident v2321 was clean:
   - `version`: `0.9.285 build=v2321-usb-clean-identity-rodata`
   - `status`: `BOOT OK`, SD mounted rw, tcpctl ready
   - `selftest`: `pass=11 warn=1 fail=0`
2. Flashed V3364 through `native_init_flash.py --from-native`:
   - local image marker and SHA matched `0.11.125` / `934f7038...`
   - boot block readback SHA matched `934f7038...`
   - helper total: `66.803s`
   - post-boot verify: `0.11.125 build=v3364-hot-reload-fastpath`, `selftest fail=0`
3. Staged V3365 init ELF:
   - first tcpctl install attempt failed because default `/cache/bin/toybox` was absent
   - retried with `--toybox /bin/toybox`
   - device path: `/mnt/sdext/a90/flash-staging/init_reload_h2_v3365`
   - device SHA: `bb105b55f399e9ada9670ca886ad1746653a6beaf1632a6b588c21fa63e01194`
   - mode/owner: `-rwxr-xr-x 1 0 0`
4. Sent reload at `2026-07-02T15:21:48Z`:

```text
reload INIT-RELOAD-EXECVE /mnt/sdext/a90/flash-staging/init_reload_h2_v3365 bb105b55f399e9ada9670ca886ad1746653a6beaf1632a6b588c21fa63e01194
A90RELOAD begin path=/mnt/sdext/a90/flash-staging/init_reload_h2_v3365
A90RELOAD candidate=ok size=1789328 elf=1
A90RELOAD sha=bb105b55f399e9ada9670ca886ad1746653a6beaf1632a6b588c21fa63e01194 expected_sha_match=1
A90RELOAD execve_now path=/mnt/sdext/a90/flash-staging/init_reload_h2_v3365 host_note=serial-persists-no-reboot

# A90 Linux init 0.11.126 (v3365-hot-reload-delta)
# USB ACM serial console ready.
# Hot-reload: skipping autohud/netservice/rshell re-init (already live).
```

`a90ctl` returned `A90P1 END marker not found`, which is expected for `reload` because it is registered `CMD_NO_DONE` and the old PID1 image is replaced before it can emit an END marker.

## Result

H2 target proof passed:

- Post-reload `version` reported `0.11.126 build=v3365-hot-reload-delta`.
- The shell returned over the same USB ACM bridge without a kernel reboot or TWRP roundtrip.
- The post-reload banner came from the staged V3365 ELF, not the boot-partition resident.
- Post-reload `selftest` remained `fail=0`.
- `pstore` stayed empty (`entries=0` in status).

This closes the narrow H2 question: **a changed native-init binary can be loaded into PID1 by `reload` and immediately change the running command surface/version identity without reflashing or rebooting.**

## Residual

This was not a fully clean reload state:

- Post-reload `status` showed `boot: BOOT ERR storage E16`.
- Storage status fell back to `/tmp` / `/cache/a90-runtime` even though `mountsd` still showed `/mnt/sdext` mounted rw.
- `autohud` and `tcpctl` were stopped in the reloaded image. This matches the current V3364 fast-path design for autohud/netservice/rshell re-init avoidance, but it means a hot-reloaded init is currently serial-control-focused rather than a full service refresh.

Likely next fix: extend the `A90_RELOADED` fast-path over storage initialization, or treat already-mounted SD `EBUSY` as a successful mounted state before selecting fallback storage.

## Rollback

Rolled back through `native_init_flash.py --from-native` to v2321:

- rollback image marker and SHA matched `0.9.285` / `ca978551...`
- boot block readback SHA matched `ca978551...`
- helper total: `64.568s`
- final `version`: `0.9.285 build=v2321-usb-clean-identity-rodata`
- final `status`: `BOOT OK`, SD mounted rw, tcpctl ready
- final `selftest`: `pass=11 warn=1 fail=0`
- staged file cleanup: `/mnt/sdext/a90/flash-staging/init_reload_h2_v3365` removed; follow-up `ls` returned `No such file or directory`

## Validation

- Source gate already committed in `64916022`:
  - `PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile workspace/public/src/scripts/revalidation/build_native_init_boot_v3365_hot_reload_delta.py tests/test_native_hot_reload_delta_source_v3365.py`
  - `PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest discover -s tests -p 'test_native_hot_reload_delta_source_v3365.py'`
  - `PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest discover -s tests -p 'test_native_init_flash.py'`
- Live flash/reload/rollback path passed as described above.
