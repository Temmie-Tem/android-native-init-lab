# Native Init V726 Wi-Fi Lifecycle Baseline Promotion

## Summary

- Baseline tag: `v726-wifi-lifecycle`
- Type: baseline promotion.
- Decision: `v726-wifi-lifecycle-baseline-promoted`
- Result: PASS
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v726_wifi_lifecycle.img`
- Boot SHA256: `6b34aac93d4fa6d5b40355b9e13b2c1ae847c24a3685d84b0d1cd78751351d40`
- Init: `A90 Linux init 0.9.246 (v726-wifi-lifecycle)`
- Version axes: `v726-wifi-lifecycle` is the boot/init baseline tag; `helper-v427` is the embedded helper marker; `V2167`/`V2168` are the validation-route/report identifiers that support this artifact.

## Validation

- Source/build: `docs/reports/NATIVE_INIT_V726_WIFI_LIFECYCLE_SOURCE_BUILD_2026-06-07.md`
- Long hold evidence: `docs/reports/NATIVE_INIT_V2167_CONNECT_DHCP_GOOGLE_PING_HANDOFF_V726_5G_FWREADY_WAIT_5MIN_NO_HELPER_HOLDER_2026-06-05.md`
- Final SHA smoke evidence: `docs/reports/NATIVE_INIT_V2167_CONNECT_DHCP_GOOGLE_PING_HANDOFF_V726_FINAL_SHA_SMOKE_2026-06-05.md`
- Autoconnect/config plan: `docs/reports/NATIVE_INIT_WIFI_AUTOCONNECT_CONFIG_PLAN_2026-06-07.md`
- Current boot was flashed to V726 and verified by `status` + `selftest fail=0`.
- Rebuilt reproducible V726 image was flashed from native via TWRP handoff; local, remote, and boot readback SHA256 all matched `6b34aac93d4fa6d5b40355b9e13b2c1ae847c24a3685d84b0d1cd78751351d40`.
- Native flash timing: total `63.754s`, recovery wait `27.138s`, adb push `0.833s`, boot write `0.454s`, native verify `32.438s`.
- Post-flash status: `A90 Linux init 0.9.246 (v726-wifi-lifecycle)`, `selftest: pass=11 warn=1 fail=0`, `ncm=present`, `tcpctl=stopped`, SD workspace mounted rw.
- Persistent boot summary now reports `wlan0_present=1`, `baseline_ready=1`, `helper_timeout_benign=1`, and `supervisor_result=wlan0-ready`.
- Runtime summary after post-flash boot reports `wlan0_present=1`, `operstate=down`, `mac_label=xx:7f:3a`, `ip4_label=none`, and `rx_mbps=0.0`/`tx_mbps=0.0` while idle.
- HUD now shows Wi-Fi state (`WIFI WAIT`/`IFACE`/`READY`/`UP`) above the existing SD/storage line and consumes `/cache/native-init-wifi-runtime.summary` for runtime MAC/IP/RX/TX details.

## Final SHA Smoke

- Test image: `workspace/private/inputs/boot_images/boot_linux_v726_wifi_lifecycle.img`
- Rollback image: `workspace/private/inputs/boot_images/boot_linux_v726_wifi_lifecycle.img`
- Connect result: `connect-dhcp-google-ping-hold-pass`
- Hold: `60s`, `2/2` carrier samples, `2/2` gateway pings, `2/2` IP pings, `2/2` host pings.
- Link: 5 GHz, `5745 MHz`, `780-866 Mbps` sampled linkspeed.
- Secrets: `secret_values_logged=0`, archive secret hits `[]`.

## Notes

- The final SHA differs from the 5-minute hold image only by PID1 summary/UI status lines for benign helper timeout when `wlan0` is already present.
- Fast evidence upload still needs hardening: the final smoke received an archive with no secret hits, but `fast_upload_ok=false` due archive validation/upload status. This does not block Wi-Fi baseline behavior because the connect gate passed and artifacts were available.
- Country readback remains `US` after the `KR` driver command, but association, DHCP, gateway ping, and external ping all passed on the target 5 GHz AP.
