# Native Init V772 Boot Incompatibility Classifier Report

## Result

- decision: `v772-boot-fail-likely-missing-appended-dtb`
- pass: `true`
- runner: `scripts/revalidation/native_wifi_boot_incompat_classifier_v772.py`
- evidence: `tmp/wifi/v772-boot-incompat-classifier/`

## What Ran

```bash
python3 -m py_compile scripts/revalidation/native_wifi_boot_incompat_classifier_v772.py
python3 scripts/revalidation/native_wifi_boot_incompat_classifier_v772.py plan
python3 scripts/revalidation/native_wifi_boot_incompat_classifier_v772.py run
```

## Evidence Summary

| Signal | Known-good v724 payload | V770 diagnostic payload |
| --- | --- | --- |
| kernel size | `49827613` | `48830516` |
| FDT/DTB magic count | `3` | `0` |
| FDT offsets | `48830500`, `49327831`, `49827440` | none |
| stock DTB tail size | `997113` | absent |
| `A90V765` marker count | `0` | `19` |
| embedded config hash | matches diagnostic | matches stock |

Version strings also differ:

- v724 stock: `Linux version 4.14.190-25818860-abA908NKSU5EWA3 ... clang version 10.0.7 ... Thu Jan 12 18:53:40 KST 2023`
- diagnostic: `Linux version 4.14.190 ... clang version 10.0.6 ... Mon May 25 01:27:22 KST 2026`

## Interpretation

The strongest host-only explanation for the V771 boot failure is that V770
packaged a diagnostic kernel payload with no appended FDT/DTB payload, while the
known-good v724 kernel payload contains three appended FDT blobs. The diagnostic
payload still contains all 19 `A90V765` instrumentation markers, and the
embedded kernel config matches the stock payload, so the immediate structural
gap is DTB packaging rather than config mismatch.

This explains why TWRP write/readback succeeded but reboot dropped to Download
mode: the boot image was syntactically writable, but the kernel payload was not
boot-compatible for this device.

## Safety

- device command: not executed
- partition write/flash/reboot: not executed
- Wi-Fi HAL/scan/connect/credential use: not executed
- DHCP/routes/external ping: not executed

## Next

V773 should be local-only:

1. split the known-good v724 kernel payload at the first FDT offset;
2. append the stock v724 DTB tail to the V769 instrumented Image payload;
3. repack a local diagnostic boot image;
4. verify FDT count, kernel roundtrip hash, native-init marker, and `A90V765` markers;
5. keep live flash blocked until V773 staging passes.

Do not retry the V770 image or the same bare OSRC-built kernel payload as-is.
