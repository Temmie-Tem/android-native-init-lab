# Native Init V726 Wi-Fi Lifecycle Baseline Promotion

## Summary

- Cycle: `V726`
- Type: baseline promotion.
- Decision: `v726-wifi-lifecycle-baseline-promoted`
- Result: PASS
- Boot image: `stage3/boot_linux_v726_wifi_lifecycle.img`
- Boot SHA256: `2a8d3f946068d81b17882153058db06a6d795592a08ec2bd9057f0e6df2b501a`
- Init: `A90 Linux init 0.9.246 (v726-wifi-lifecycle)`

## Validation

- Source/build: `docs/reports/NATIVE_INIT_V726_WIFI_LIFECYCLE_SOURCE_BUILD_2026-06-07.md`
- Long hold evidence: `docs/reports/NATIVE_INIT_V2167_CONNECT_DHCP_GOOGLE_PING_HANDOFF_V726_5G_FWREADY_WAIT_5MIN_NO_HELPER_HOLDER_2026-06-05.md`
- Final SHA smoke evidence: `docs/reports/NATIVE_INIT_V2167_CONNECT_DHCP_GOOGLE_PING_HANDOFF_V726_FINAL_SHA_SMOKE_2026-06-05.md`
- Current boot was flashed to V726 and verified by `status` + `selftest fail=0`.
- Persistent boot summary now reports `wlan0_present=1`, `baseline_ready=1`, `helper_timeout_benign=1`, and `supervisor_result=wlan0-ready`.

## Final SHA Smoke

- Test image: `stage3/boot_linux_v726_wifi_lifecycle.img`
- Rollback image: `stage3/boot_linux_v726_wifi_lifecycle.img`
- Connect result: `connect-dhcp-google-ping-hold-pass`
- Hold: `60s`, `2/2` carrier samples, `2/2` gateway pings, `2/2` IP pings, `2/2` host pings.
- Link: 5 GHz, `5745 MHz`, `780-866 Mbps` sampled linkspeed.
- Secrets: `secret_values_logged=0`, archive secret hits `[]`.

## Notes

- The final SHA differs from the 5-minute hold image only by PID1 summary/UI status lines for benign helper timeout when `wlan0` is already present.
- Fast evidence upload still needs hardening: the final smoke received an archive with no secret hits, but `fast_upload_ok=false` due archive validation/upload status. This does not block Wi-Fi baseline behavior because the connect gate passed and artifacts were available.
- Country readback remains `US` after the `KR` driver command, but association, DHCP, gateway ping, and external ping all passed on the target 5 GHz AP.
