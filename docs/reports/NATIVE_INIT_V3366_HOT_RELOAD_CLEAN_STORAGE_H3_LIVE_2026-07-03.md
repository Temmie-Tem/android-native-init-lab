# Native Init V3366 Hot-Reload Clean Storage H3 Live

- Cycle: `V3366` (H3 live)
- Decision: `v3366-hot-reload-clean-storage-h3-pass`
- Scope: close the V3365 H2 residual where hot-reload returned through the new init but storage fell back with `BOOT ERR storage E16`.
- Device action: checked-helper flash V3364 resident, stage V3366 init ELF to SD, run `reload`, then checked-helper rollback to v2321.
- Final state: v2321 restored, `selftest fail=0`, staged V3366 ELF removed.

## Inputs

- Rollback baseline: `boot_linux_v2321_usb_clean_identity_rodata.img`
  - SHA256: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- Resident image flashed for H3: `boot_linux_v3364_init_hot_reload.img`
  - SHA256: `934f70384b3a470461666da8603620856219fdddf25cebff3d4378df04d8c8e7`
- Reload candidate init ELF: `workspace/private/builds/native-init/v3366-hot-reload-clean-storage/init_v3366_hot_reload_clean_storage`
  - SHA256: `2fed9a5aeee0142ff48613d517663ff56ae5ec45a5c5d28a07d2bbc17f72d951`
  - Size: `1723792` bytes
- V3366 source build commit: `5efb8fd8`

## Execution

1. Preflight on resident v2321 was clean:
   - `version`: `0.9.285 build=v2321-usb-clean-identity-rodata`
   - `selftest`: `pass=11 warn=1 fail=0`
2. Flashed V3364 through `native_init_flash.py --from-native`:
   - local image marker and SHA matched `0.11.125` / `934f7038...`
   - boot block readback SHA matched `934f7038...`
   - helper total: `64.580s`
   - post-boot verify: `0.11.125 build=v3364-hot-reload-fastpath`, `selftest fail=0`, SD/tcpctl ready
3. Staged V3366 init ELF:
   - one first staging attempt failed before transfer because the serial-side token query was corrupted (`cmdv1 ATATATAT`); bridge and tcpctl were immediately rechecked clean
   - retry with `--toybox /bin/toybox` succeeded
   - device path: `/mnt/sdext/a90/flash-staging/init_reload_h3_v3366`
   - device SHA: `2fed9a5aeee0142ff48613d517663ff56ae5ec45a5c5d28a07d2bbc17f72d951`
4. Sent reload at `2026-07-02T15:38:47Z`:

```text
reload INIT-RELOAD-EXECVE /mnt/sdext/a90/flash-staging/init_reload_h3_v3366 2fed9a5aeee0142ff48613d517663ff56ae5ec45a5c5d28a07d2bbc17f72d951
A90RELOAD begin path=/mnt/sdext/a90/flash-staging/init_reload_h3_v3366
A90RELOAD candidate=ok size=1723792 elf=1
A90RELOAD sha=2fed9a5aeee0142ff48613d517663ff56ae5ec45a5c5d28a07d2bbc17f72d951 expected_sha_match=1
A90RELOAD execve_now path=/mnt/sdext/a90/flash-staging/init_reload_h3_v3366 host_note=serial-persists-no-reboot

# A90 Linux init 0.11.127 (v3366-hot-reload-clean-storage)
# USB ACM serial console ready.
# Hot-reload: skipping autohud/netservice/rshell re-init (already live).
```

As in H2, `a90ctl` reports `A90P1 END marker not found`; this is expected because `reload` is `CMD_NO_DONE`.

## Result

H3 target proof passed:

- Post-reload `version`: `0.11.127 build=v3366-hot-reload-clean-storage`.
- Post-reload `status`: `boot: BOOT OK shell 98.0s`.
- Post-reload storage stayed on SD:
  - `storage: backend=sd root=/mnt/sdext/a90 fallback=no`
  - `runtime: backend=sd root=/mnt/sdext/a90 fallback=no writable=yes`
  - `mountsd: state=mounted mode=rw workspace=/mnt/sdext/a90`
- Post-reload `selftest`: `pass=12 warn=1 fail=0`.
- `pstore` stayed empty (`entries=0` in status).

This closes the V3365 H2 storage residual: the reloaded init now adopts the existing rw SD mount and no longer produces `BOOT ERR storage E16`.

## Residual

Hot-reload is still not a full service refresh:

- Post-reload `autohud: stopped`.
- Post-reload `tcpctl=stopped`, with transport showing `tcpctl=starting` and `upload=ncm-ready`.

This is consistent with the current fast-path policy that skips autohud/netservice/rshell re-init to avoid SETCRTC/NCM re-init errors. The next bounded unit should decide whether to add a narrow tcpctl health/adopt/restart path without reopening the expensive display/HUD re-init path.

## Rollback

Rolled back through `native_init_flash.py --from-native` to v2321:

- rollback image marker and SHA matched `0.9.285` / `ca978551...`
- boot block readback SHA matched `ca978551...`
- helper total: `63.452s`
- final `version`: `0.9.285 build=v2321-usb-clean-identity-rodata`
- final `status`: `BOOT OK`, SD mounted rw, tcpctl ready
- final `selftest`: `pass=11 warn=1 fail=0`
- staged file cleanup: `/mnt/sdext/a90/flash-staging/init_reload_h3_v3366` removed; follow-up `ls` returned `No such file or directory`

## Validation

- Source gate already committed in `5efb8fd8`:
  - `PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile workspace/public/src/scripts/revalidation/build_native_init_boot_v3366_hot_reload_clean_storage.py tests/test_native_hot_reload_clean_storage_source_v3366.py`
  - `PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest discover -s tests -p 'test_native_hot_reload_clean_storage_source_v3366.py'`
  - `PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest discover -s tests -p 'test_native_init_flash.py'`
- Live flash/reload/rollback path passed as described above.
