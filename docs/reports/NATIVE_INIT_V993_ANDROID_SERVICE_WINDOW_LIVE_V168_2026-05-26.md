# V993 Android Service-Window Live v168

- generated: `2026-05-26`
- scope: bounded Android service-window start-only proof
- decision: `v970-android-service-window-runtime-gap`
- evidence: `tmp/wifi/v993-android-service-window-live-v168/manifest.json`
- transcript: `tmp/wifi/v993-android-service-window-live-v168/native/mdm-helper-cnss-before-esoc.txt`
- helper: `a90_android_execns_probe v168`

## Summary

V993 reran the Android service-window proof with helper `v168`. The new attr
capture confirms the V990 SELinux transition blocker after `execv`, not just
before it:

```text
wifi_hal_composite_child.wificond.selinux_exec.target_context=u:r:wificond:s0
wifi_hal_composite_child.wificond.selinux_exec.ok=1
wifi_hal_composite_start.child.wificond.trace.exec_stop=1
capture.exec.attr/current.value=kernel\x00
capture.exec.attr/exec.value=
wifi_hal_composite_start.child.wificond.trace.crash_stop=1
capture.crash.attr/current.value=kernel\x00
capture.crash.attr/exec.value=
```

The same run preserved safety guards:

```text
android_wifi_service_window.qcwlanstate_write=0
android_wifi_service_window.iwifi_start=0
android_wifi_service_window.subsys_esoc0_open_attempted=0
android_wifi_service_window.esoc_ioctl_attempted=0
android_wifi_service_window.scan_connect_linkup=0
android_wifi_service_window.credentials=0
android_wifi_service_window.dhcp_routing=0
android_wifi_service_window.external_ping=0
```

## Interpretation

The remaining blocker is now sharper:

1. `setexeccon`/`attr/exec` write is accepted before `execv`.
2. At the traced `exec` stop, `wificond` is still `kernel`.
3. At the crash stop, `wificond` is still `kernel`.
4. `wificond` then aborts in the service registration path classified by V989.

Therefore another full service-window retry is not useful until the SELinux
transition mechanism is changed or the service-manager registration path is
made compatible with the current native `kernel` context.

## Device Health

Post-run serial health check:

```text
boot: BOOT OK shell 4.6s
selftest: pass=11 warn=1 fail=0
exposure: ncm=absent tcpctl=stopped rshell=stopped boundary=usb-local
```

Cleanup reboot was not required.

## Guardrails

- no scan/connect/link-up
- no credential use
- no DHCP/route/external ping
- no `qcwlanstate`
- no `IWifi.start`
- no `/dev/subsys_esoc0` open
- no eSoC ioctl

## Validation

```bash
python3 scripts/revalidation/native_wifi_android_service_window_live_v970.py \
  --out-dir tmp/wifi/v993-android-service-window-live-v168 \
  --local-helper tmp/wifi/v991-execns-helper-v168-build/a90_android_execns_probe \
  --helper-sha256 4407766d01d816e03bc81bde6ea994112cb59fb66bf9444900929db862889fa0 \
  --helper-marker "a90_android_execns_probe v168" \
  --allow-mountsystem-ro \
  --allow-selinuxfs-mount \
  --allow-android-wifi-service-window \
  --allow-cleanup-reboot \
  --assume-yes run
python3 scripts/revalidation/a90ctl.py bootstatus
```

## Next

V994 should be host-only/source-first and choose between:

1. implementing a real native Android SELinux setup/reexec path, or
2. proving a narrow service-manager registration bypass/compatibility route for
   the private service-window without scan/connect.
