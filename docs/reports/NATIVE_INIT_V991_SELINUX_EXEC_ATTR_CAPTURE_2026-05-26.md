# V991 SELinux Exec Attr Capture

- generated: `2026-05-26`
- scope: source/build-only helper observability patch
- decision: `v991-selinux-exec-attr-capture-pass`
- evidence: `tmp/wifi/v991-selinux-exec-attr-capture/manifest.json`
- artifact: `tmp/wifi/v991-execns-helper-v168-build/a90_android_execns_probe`
- artifact sha256: `4407766d01d816e03bc81bde6ea994112cb59fb66bf9444900929db862889fa0`

## Summary

V991 bumps `a90_android_execns_probe` to helper `v168` and adds compact
`/proc/<pid>/attr/current` plus `/proc/<pid>/attr/exec` capture to traced
`exec` and `crash` stops.

This is targeted at the V990 blocker: `setexeccon` reports success for Android
service domains, but child processes remain in SELinux `kernel` context.

## Guardrails

- source/build-only before deploy
- no actor start in V991
- no `qcwlanstate`
- no `IWifi.start`
- no `/dev/subsys_esoc0` open
- no eSoC ioctl
- no scan/connect/link-up
- no credential use
- no DHCP/route/external ping

## Validation

```bash
python3 -m py_compile scripts/revalidation/native_wifi_selinux_exec_attr_capture_v991.py
python3 scripts/revalidation/native_wifi_selinux_exec_attr_capture_v991.py
```

Result:

```text
decision: v991-selinux-exec-attr-capture-pass
pass: True
```

## Next

Deploy helper `v168`, then rerun the bounded Android service-window proof to
confirm the post-`execv` SELinux attr values directly.
