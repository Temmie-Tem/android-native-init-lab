# V318 Private Property Transfer Primitive Preflight Report

## Summary

- Result: PASS.
- Decision: `private-property-transfer-primitive-preflight-ready`.
- Evidence: `tmp/wifi/v318-private-property-transfer-primitive-preflight/`.
- Device build: `A90 Linux init 0.9.60 (v261)`.
- Boot image change: none.

V318 verifies the command primitives needed before V317 performs a minimal private property namespace proof. It intentionally does not write files or start network daemons.

## Validation

```bash
python3 -m py_compile scripts/revalidation/wifi_private_property_transfer_primitive_preflight.py scripts/revalidation/a90ctl.py
python3 scripts/revalidation/a90ctl.py --json version
python3 scripts/revalidation/wifi_private_property_transfer_primitive_preflight.py \
  --out-dir tmp/wifi/v318-private-property-transfer-primitive-preflight \
  run
```

Observed:

```text
decision: private-property-transfer-primitive-preflight-ready
pass: True
reason: read-only transfer primitive checks passed
```

## Check Results

| check | status | severity | interpretation |
| --- | --- | --- | --- |
| `toybox-present` | PASS | blocker | `/cache/bin/toybox` executes. |
| `toybox-uudecode-output` | PASS | blocker | `uudecode [-o OUTFILE] [INFILE]` is available. |
| `toybox-base64-file-input` | PASS | blocker | `base64 [-di] [FILE...]` is available. |
| `toybox-touch` | PASS | blocker | `touch` exists for future approved ASCII staging file creation. |
| `writefile-command` | PASS | blocker | native `writefile <path> <value...>` exists. |
| `sha256sum-proc` | PASS | blocker | `sha256sum /proc/version` works. |
| `toybox-sh-unavailable` | WARN | info | `toybox sh` is not available, so V317 must not use shell pipelines/redirection. |
| `no-write-scope` | PASS | info | This preflight used no file creation/removal/write operation. |

## Important Finding

`toybox sh` is unavailable on the device:

```text
toybox: Unknown command sh
```

Therefore V317 should not use `sh -c`, pipes, or shell redirection for transfer. The viable path is redirection-free:

1. create versioned private workdir and ASCII staging files only after explicit V317 live approval;
2. write uuencoded text chunks through native `writefile`;
3. decode with `toybox uudecode -o <target> <encoded-file>`;
4. verify each decoded file with `toybox sha256sum`;
5. cleanup only `/mnt/sdext/a90/private-property-v317`.

## Safety

- `device_mutations=false` in the manifest.
- No generated property file was copied to the device.
- No global `/dev/__properties__` path was touched.
- No property service socket was created.
- No NCM/tcpctl daemon was started.
- No Wi-Fi bring-up action was attempted.

## Next Step

Patch the V317 namespace proof runner to use the `uudecode -o` transfer strategy instead of a shell pipeline. The V317 live run still requires the exact V317 approval phrase and should remain limited to the private workdir proof.
