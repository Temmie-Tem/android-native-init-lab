# Native Init Wi-Fi Baseline QA Hold

## Summary

- Decision: `baseline-promotion-blocked-wifi-hold-failed`
- Scope: V2167 standalone `wpa_supplicant` connect/DHCP/google.com ping route with added hold QA.
- Baseline rollback: `v725-fasttransport`; post-run selftest verified `fail=0` after both live runs.
- Result: initial Wi-Fi function is reproducible on both tested bands, but sustained connectivity is not yet stable.

## Evidence

- 5 GHz run: `tmp/wifi/v2167-connect-dhcp-google-ping-handoff-qa-hold-v24-5g`
- 5 GHz report: `docs/reports/NATIVE_INIT_V2167_CONNECT_DHCP_GOOGLE_PING_HANDOFF_QA_HOLD_V24_5G_2026-06-05.md`
- 2.4 GHz run: `tmp/wifi/v2167-connect-dhcp-google-ping-handoff-qa-hold-v25-2g`
- 2.4 GHz report: `docs/reports/NATIVE_INIT_V2167_CONNECT_DHCP_GOOGLE_PING_HANDOFF_QA_HOLD_V25_2G_2026-06-05.md`

## Gate Results

- Initial association/DHCP/google.com ping: pass on 5 GHz and 2.4 GHz.
- Country side variable: `COUNTRY KR` ioctl returns rc 0 but `GETCOUNTRYREV` reads back `US`; both bands still associate and ping, so US readback is not a blocker for the tested AP/channels.
- 5 GHz hold: 180s requested, carrier stayed up for 5 samples, first sample ping passed, later hostname pings timed out.
- 2.4 GHz hold: 120s requested, carrier stayed up for 4 samples, first sample IP+hostname ping passed, later IP ping returned no reply and hostname ping timed out.
- Reconnect-on-drop: not exercised because carrier never dropped.
- Fast upload after rollback: failed NCM device-to-host probe in both QA runs, result fallback via serial-cat succeeded.

## Interpretation

- This is not an association-only or regulatory-only failure: both bands associate, DHCP, and pass the first external ping.
- This is not a carrier drop: `/sys/class/net/wlan0/carrier` remained up during the hold windows.
- The next blocker is sustained data-path stability after initial success: IP packets stop receiving replies while the link remains associated.
- Baseline promotion is blocked until the hold gate passes; UI polish should wait because the current test boot is not stable enough to present as the default Wi-Fi path.

## Next Work

- Add data-path hold diagnostics before fixing: route/default-gateway presence, ARP/neighbor state, interface counters, `wpa_cli status`, and driver power-save state at each hold sample.
- Test whether disabling WLAN power save or keeping a renewal/keepalive path changes the post-30s failure.
- Keep credential hygiene: no raw SSID/PSK/BSSID/MAC/IP/route/DNS/ping transcript in reports.
- Re-run both bands only after the data-path failure is named; baseline promotion requires at least two clean hold passes plus rollback selftest `fail=0`.
