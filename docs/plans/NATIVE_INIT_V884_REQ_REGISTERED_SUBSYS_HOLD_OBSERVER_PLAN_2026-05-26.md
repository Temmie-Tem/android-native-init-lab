# V884 REQ-registered Subsystem-hold Observer Plan

## Goal

Run the first bounded live `/dev/subsys_esoc0` hold window with helper `v139`.
The gate holds a successful `REG_REQ_ENG` fd, attempts `/dev/subsys_esoc0` in a
bounded child, and records passive `ESOC_WAIT_FOR_REQ` observer output. This is
not a daemon start and not a Wi-Fi bring-up attempt.

## Inputs

- V883 deployed helper:
  `/cache/bin/a90_android_execns_probe`
- helper sha256:
  `077ced65ae5b0b546ecdf3b1bb0c808d3ec34bfa2462516e6ceba170b18f23c5`
- helper mode:
  `wifi-companion-esoc-req-registered-subsys-hold-preflight`
- runner:
  `scripts/revalidation/native_wifi_esoc_req_registered_subsys_hold_v884.py`
- eSoC research:
  `docs/overview/ESOC_PERIPHERAL_MANAGER_BRINGUP_RESEARCH_2026-05-25.md`

## Method

1. Verify native health and helper `v139` remote parity.
2. Mount system read-only if needed for private helper namespace setup.
3. Materialize only Android-equivalent private eSoC/subsys nodes.
4. Execute helper mode with `REG_REQ_ENG` and bounded `/dev/subsys_esoc0`
   child open.
5. Record passive `ESOC_WAIT_FOR_REQ` observer fields.
6. Clean up created nodes and verify postflight native health plus actor and
   Wi-Fi surfaces.

## Hard Gates

- Allowed eSoC registration ioctl: `REG_REQ_ENG` only.
- Allowed subsystem action: bounded `/dev/subsys_esoc0` open attempt only.
- `ESOC_WAIT_FOR_REQ` is passive observation only.
- No `REG_CMD_ENG` dependency.
- No direct userspace `CMD_EXE`, explicit userspace `PWR_ON`, or
  `ESOC_NOTIFY`.
- No `mdm_helper`, `ks`, `pm_proxy_helper`, CNSS, service-manager, Wi-Fi HAL,
  scan/connect, credentials, DHCP/routes, or external ping.
- No module load/unload, boot image write, partition write, firmware mutation,
  GPIO/sysfs/debugfs write, or Wi-Fi link-up.

## Success Criteria

- Decision is `v884-req-registered-subsys-hold-window-pass`.
- Remote helper sha, marker, and mode token match V883.
- `REG_REQ_ENG` returns rc `0`.
- `/dev/subsys_esoc0` child is reaped or otherwise proven safe.
- Passive `ESOC_WAIT_FOR_REQ` observer fields are recorded.
- Postflight selftest stays `fail=0`.
- Service-manager actor hits and Wi-Fi netdev hits remain `0`.

`ESOC_REQ_IMG` absence is diagnostic data, not an immediate failure, because
SDX50M may boot from PCIe/self flash rather than the older request-image loop.

## Failure Classification

- `v884-reg-req-eng-review`: the REQ engine precondition failed.
- `v884-subsys-esoc0-open-failed`: `REG_REQ_ENG` worked but subsystem open did
  not.
- `v884-reboot-required`: the child or observer was not proven stopped and a
  recovery reboot is required before the next live gate.
- `v884-req-registered-subsys-hold-review`: evidence exists but does not match
  a known terminal label.

## Next

If V884 passes, classify mdm3/SSCTL/WLFW deltas from the hold window before
starting any Android actor or Wi-Fi HAL. If V884 requires reboot cleanup, recover
native health first and treat the open/wchan behavior as the next blocker.
