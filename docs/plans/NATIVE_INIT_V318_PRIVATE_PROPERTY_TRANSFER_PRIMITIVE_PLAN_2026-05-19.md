# V318 Private Property Transfer Primitive Preflight Plan

## Summary

- V318 is a no-boot-image, read-only host/device preflight for the V317 private property namespace proof.
- Goal: verify the actual native v261 device has the primitive commands needed to transfer generated property layout files over the existing ACM bridge without starting NCM/tcpctl.
- Result target: decide whether V317 can use the current serial bridge path or needs a new transfer primitive before any private namespace materialization run.

## Scope

Allowed checks:

- `hide` to clear the auto-menu busy gate before command probes.
- `run /cache/bin/toybox` and read-only toybox help probes.
- `writefile` usage probe with no path/value, so no file is created or modified.
- `run /cache/bin/toybox sha256sum /proc/version` as a read-only hashing check.

Forbidden actions:

- No file creation, file write, directory creation, delete, move, or cleanup on the device.
- No global `/dev/__properties__` replacement or bind mount.
- No property service socket.
- No NCM/tcpctl/daemon start.
- No Wi-Fi scan/connect/link-up/credentials/DHCP/routing.

## Checks

- `toybox-present`: multicall toybox executes.
- `toybox-uudecode-output`: `uudecode` supports `-o OUTFILE` and file input.
- `toybox-base64-file-input`: `base64` supports `-d` and file input for diagnostics/readback.
- `toybox-touch`: `touch` exists so a future approved run can create ASCII staging files before `writefile`.
- `writefile-command`: native `writefile` command exists.
- `sha256sum-proc`: `sha256sum` can hash a read-only proc file.
- `toybox-sh-unavailable`: record whether shell pipelines are unavailable; this is not a blocker if `uudecode -o` exists.

## Expected Interpretation

- PASS means V317 should avoid `toybox sh` pipelines and use a redirection-free plan: create ASCII staging files, write uuencoded chunks with native `writefile`, decode with `toybox uudecode -o`, then verify with `toybox sha256sum`.
- BLOCKED means V317 cannot safely proceed over ACM without either a new native transfer command, a helper deploy path, or a separately approved NCM/tcpctl transfer.

## Validation

```bash
python3 -m py_compile scripts/revalidation/wifi_private_property_transfer_primitive_preflight.py
python3 scripts/revalidation/wifi_private_property_transfer_primitive_preflight.py \
  --out-dir tmp/wifi/v318-private-property-transfer-primitive-preflight \
  run
```

## Acceptance

- Manifest decision is `private-property-transfer-primitive-preflight-ready`.
- `device_mutations=false`.
- All blocker checks pass.
- Any missing `toybox sh` support is documented as a warning and not used by later V317 transfer logic.
