# V1238 Late per_proxy-only Live Gate

- report: `docs/reports/NATIVE_INIT_V1238_LATE_PER_PROXY_ONLY_LIVE_2026-05-31.md`
- live runner: `scripts/revalidation/native_wifi_late_per_proxy_only_live_v1238.py`
- evidence: `tmp/wifi/v1238-late-per-proxy-only-live/manifest.json`

- decision: `v1238-late-per-proxy-reached-pm-service-esoc0-reboot-required`
- pass: `True`
- reason: late `per_proxy` started and `pm-service` Binder reached `/dev/subsys_esoc0` / `mdm_subsys_powerup`, but no WLFW or `wlan0` progress appeared and process cleanup was not proven safe.
- next_step: classify the `mdm_subsys_powerup` hardware response gap and the reboot-required cleanup boundary before Wi-Fi HAL/connect.

## Result

| field | value |
| --- | --- |
| helper | `a90_android_execns_probe v257` |
| direct helper trigger present | `false` |
| post-wait observer present | `false` |
| late `per_proxy` requested | `1` |
| late `per_proxy` begin | `true` |
| late `per_proxy` gate positive | `1` |
| late `per_proxy` started | `1` |
| late poll count | `12` |
| `pm-service` actor `/dev/subsys_esoc0` attempt | `true` |
| `pm-service` Binder wchan | `mdm_subsys_powerup` |
| `pm-service` path value | `/dev/subsys_esoc0` |
| `per_mgr` `/dev/subsys_modem` seen | `1` |
| `per_mgr` `/dev/subsys_esoc0` fd count | `0` |
| MHI pipe fd count | `0` |
| `ks` count | `0` |
| WLFW dmesg count | `0` |
| `wlan0` seen | `false` |
| `mdm3` state | `OFFLINING` |
| postflight safety | `all_postflight_safe=0` |

## Interpretation

V1238 removes the V1237 design conflict. The direct helper
`/dev/subsys_esoc0` trigger did not run, and the post-wait observer did not run.
The late `per_proxy` actor did run after `mdm_helper` held `/dev/esoc-0`.

This reaches the Android-positive PM actor contract identified by V1236:
`pm-service` Binder thread enters `openat("/dev/subsys_esoc0")` and blocks in
`mdm_subsys_powerup`. That closes the previous uncertainty about whether
`per_proxy` can deliver the request to `pm-service` in native init.

The remaining blocker moved lower: native now reaches `mdm_subsys_powerup`, but
SDX50M/MDM3 still does not respond. No MHI pipe, `ks`, WLFW service, BDF, or
`wlan0` appears; `mdm3` remains `OFFLINING`. This is now a hardware-response /
powerup-contract gap, not a missing `per_proxy`/Binder request gap.

## Safety

No Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, flash, boot
image write, or partition write occurred. The run did enter a reboot-required
cleanup boundary because the PM actor path was not proven stopped after
`mdm_subsys_powerup`. The device returned to native init `A90 Linux init 0.9.68
(v724)` and postflight remained clean: `selftest pass=11 warn=1 fail=0`,
`netservice enabled=no`, `ncm0=absent`, `tcpctl=stopped`.

## V1239 Gate

V1239 should be host-only first: classify what Android does after the
`pm-service` Binder thread enters `mdm_subsys_powerup` and before GPIO142,
PCIe RC1, MHI, `ks`, WLFW, BDF, and `wlan0` appear. The immediate comparison is:

- Android: `/dev/subsys_esoc0` open → GPIO142 IRQ → PCIe RC1 L0 → MHI/`ks` → WLFW/BDF/`wlan0`.
- Native V1238: `/dev/subsys_esoc0` open → `mdm_subsys_powerup` block → `mdm3=OFFLINING`, no MHI/`ks`/WLFW/`wlan0`, cleanup requires reboot.

No additional live Wi-Fi HAL or connect attempt is justified until this lower
powerup response gap is classified.
