# Native Init V683 cnss2/QMI Trigger Isolation Report

- date: `2026-05-24 KST`
- status: `host-only-pass`; Wi-Fi external ping is **not** complete
- script: `scripts/revalidation/native_wifi_cnss2_qmi_trigger_isolation_v683.py`
- plan evidence: `tmp/wifi/v683-cnss2-qmi-trigger-isolation-plan/`
- run evidence: `tmp/wifi/v683-cnss2-qmi-trigger-isolation/`
- decision: `v683-cnss-daemon-vndbinder-pre-wlfw-trigger-classified`

## Scope

V683 consumes existing evidence only. It does not contact the device, mount
filesystems, start daemons, start service-manager, start Wi-Fi HAL, scan/connect,
use credentials, run DHCP, change routes, write sysfs/debugfs, write boot
partitions, or ping externally.

## Result

| key | value |
| --- | --- |
| decision | `v683-cnss-daemon-vndbinder-pre-wlfw-trigger-classified` |
| pass | `True` |
| device_commands_executed | `False` |
| device_mutations | `False` |
| daemon_start_executed | `False` |
| wifi_hal_start_executed | `False` |
| scan_connect_executed | `False` |
| wifi_bringup_executed | `False` |
| external_ping_executed | `False` |

## Checks

| check | result |
| --- | --- |
| input evidence ready | pass |
| native lower path reaches CNSS before WLFW | finding |
| Android CNSS continuation proven | finding |
| native CNSS Binder precedes missing WLFW | finding |
| direct QCA power retry not yet justified | finding |

## Evidence Matrix

| source | marker | value |
| --- | --- | ---: |
| V682 live | service `74` | `1` |
| V682 live | CNSS netlink | `10` |
| V682 live | CNSS `cld80211` | `4` |
| V682 live | CNSS Binder transaction | `1` |
| V682 live | WLFW start | `0` |
| V682 live | QMI server connected | `0` |
| V682 live | BDF | `0` |
| V682 live | `wlan0` | `0` |
| V651 Android | WLFW start | `1` |
| V651 Android | QMI server connected | `1` |
| V651 Android | BDF `bdwlan` | `1` |
| V651 Android | `wlan0` | `3` |
| V651 Android | CNSS Binder transaction | `0` |
| V651 native | CNSS Binder transaction | `21` |
| V651 native | WLFW start | `0` |
| V654 | native CNSS Binder blocks WLFW | `True` |
| V654 | Android CNSS Binder transaction absent | `True` |

## Interpretation

V683 narrows the V682 “cnss2/QMI trigger” wording into a more concrete next
edge. The missing trigger is still before WLFW service publication, but current
evidence does not justify direct QCA/sysfs power manipulation yet.

The strongest causal edge is:

```text
Android: service 74 -> CNSS netlink -> WLFW -> QMI/BDF/wlan0
Native:  service 74 -> CNSS netlink -> cnss-daemon vndbinder transaction -22 -> no WLFW
```

That means the next live unit should capture or repair the native-only
`cnss-daemon` vndbinder transaction target before touching direct QCA power,
supplicant, scan/connect, DHCP, routes, credentials, or external ping.

## Next Gate

Plan V684 as a narrow `cnss-daemon` vndbinder transaction target capture/repair
gate:

- preserve the V682 service `74`/CNSS/focused sysfs path;
- identify which vendor Binder service/transaction `cnss-daemon` needs before
  `wlfw_start`;
- use private Binder debugfs only if it is the least invasive target-identifying
  primitive;
- otherwise prefer static service-name/string extraction or bounded helper-side
  child output/FD context;
- keep direct QCA/sysfs writes, supplicant, scan/connect, credentials, DHCP,
  routes, and external ping blocked.

## Validation

```sh
python3 -m py_compile \
  scripts/revalidation/native_wifi_cnss2_qmi_trigger_isolation_v683.py

python3 scripts/revalidation/native_wifi_cnss2_qmi_trigger_isolation_v683.py \
  --out-dir tmp/wifi/v683-cnss2-qmi-trigger-isolation-plan \
  plan

python3 scripts/revalidation/native_wifi_cnss2_qmi_trigger_isolation_v683.py \
  --out-dir tmp/wifi/v683-cnss2-qmi-trigger-isolation \
  run
```

The validation passed with
`v683-cnss-daemon-vndbinder-pre-wlfw-trigger-classified`.
