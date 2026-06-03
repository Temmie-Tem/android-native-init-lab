# V1909 Android Service-locator Domain-list Handoff

- generated: `2026-06-03T12:37:48.519307+00:00`
- command: `run`
- decision: `v1909-android-servloc-180-only-service74-published-elsewhere-pass`
- label: `android-servloc-180-only-service74-published-elsewhere`
- pass: `True`
- reason: Android-good direct service-locator query also sees only instance 180, yet service-notifier 74 publishes during normal state-up; source inference must move to the kernel/servreg publication path rather than locator response content
- evidence: `tmp/wifi/v1909-android-servloc-domain-handoff-live-20260603-213346`

## Android Direct Query

| field | value |
| --- | --- |
| android_dir | tmp/wifi/v1909-android-servloc-domain-handoff-live-20260603-213346/android-postfs-evidence/a90-v1909-servloc-domain |
| query success/count/instances/names | 1/3/[180]/["msm/modem/wlan_pd"] |
| domain74/domain180 | False/True |
| service74/service180/wlan_pd/wlanmdsp/wlan0 | 1/1/2/10/14.904181 |
| contamination pcie-mhi/esoc/degraded257 | 0/0/False |
| first service74 | [    7.185228]  [2:  kworker/u16:8:  292] service-notifier: service_notifier_new_server: Connection established between QMI handle and 74 service |
| first wlan_pd | [    9.558609]  [5:  kworker/u16:1:   75] service-notifier: root_service_service_ind_cb: Indication received from msm/modem/wlan_pd, state: 0x1fffffff, trans-id: 1 |

## Native Baseline

| field | value |
| --- | --- |
| manifest | tmp/wifi/v1908-servloc-domain-list-live-handoff/manifest.json |
| decision/pass/label | v1908-servloc-domain-list-180-only-service74-missing-rollback-pass/True/servloc-domain-list-180-only-service74-missing |
| servloc result/count/name/instance | domain-list-response-success/1/msm/modem/wlan_pd/180 |
| service74/wlan_pd counts | 0,0,0/0,0,0 |

## Query Example

```text
a90_servloc_query.version=1
a90_servloc_query.service=64
a90_servloc_query.instance=257
a90_servloc_query.service_name=wlan/fw
a90_servloc_query.wifi_hal=0
a90_servloc_query.scan_connect_linkup=0
a90_servloc_query.credentials=0
a90_servloc_query.dhcp_routing=0
a90_servloc_query.external_ping=0
a90_servloc_query.request_hex=00010021001100010700776c616e2f667710040000000000
a90_servloc_query.lookup_socket.rc=0
a90_servloc_query.lookup_new.rc=0
a90_servloc_query.lookup_new.bytes=20
a90_servloc_query.lookup_event.0.bytes=20
a90_servloc_query.lookup_event.0.cmd=4
a90_servloc_query.lookup_event.0.service=64
a90_servloc_query.lookup_event.0.instance=257
a90_servloc_query.lookup_event.0.node=1
a90_servloc_query.lookup_event.0.port=16484
a90_servloc_query.lookup_del.rc=0
a90_servloc_query.lookup_del.bytes=20
a90_servloc_query.lookup.events=1
a90_servloc_query.endpoint.found=1
a90_servloc_query.endpoint.node=1
a90_servloc_query.endpoint.port=16484
a90_servloc_query.socket.rc=0
a90_servloc_query.send_attempted=1
a90_servloc_query.send.rc=0
a90_servloc_query.send.bytes=24
a90_servloc_query.send.node=1
a90_servloc_query.send.port=16484
a90_servloc_query.packet.0.bytes=55
a90_servloc_query.packet.0.from.node=1
a90_servloc_query.packet.0.from.port=16484
a90_servloc_query.packet.0.type=2
a90_servloc_query.packet.0.txn_id=1
a90_servloc_query.packet.0.msg_id=33
a90_servloc_query.packet.0.hex=020100210030000204000000000010020001001102000100121c0001116d736d2f6d6f64656d2f776c616e5f7064b40000000000000000
a90_servloc_query.response.type=2
a90_servloc_query.response.txn_id=1
a90_servloc_query.response.msg_id=33
a90_servloc_query.response.msg_len=48
a90_servloc_query.response.body_available=48
a90_servloc_query.tlv.0.type=0x02
a90_servloc_query.tlv.0.len=4
a90_servloc_query.tlv.0.status=parsed
a90_servloc_query.tlv.0.hex=00000000
a90_servloc_query.tlv.1.type=0x10
a90_servloc_query.tlv.1.len=2
a90_servloc_query.tlv.1.status=parsed
a90_servloc_query.tlv.1.hex=0100
a90_servloc_query.tlv.2.type=0x11
a90_servloc_query.tlv.2.len=2
a90_servloc_query.tlv.2.status=parsed
a90_servloc_query.tlv.2.hex=0100
a90_servloc_query.tlv.3.type=0x12
a90_servloc_query.tlv.3.len=28
a90_servloc_query.tlv.3.status=parsed
a90_servloc_query.tlv.3.hex=01116d736d2f6d6f64656d2f776c616e5f7064b40000000000000000
a90_servloc_query.domain_list.wire_count=1
a90_servloc_query.domain.0.name_len=17
a90_servloc_query.domain.0.name=msm/modem/wlan_pd
a90_servloc_query.domain.0.instance_id=180
a90_servloc_query.domain.0.service_data_valid=0
a90_servloc_query.domain.0.service_data=0
a90_servloc_query.domain.0.contains_wlan=1
a90_servloc_query.domain.0.status=parsed
a90_servloc_query.domain_list.bytes_consumed=28
a90_servloc_query.response_parse=complete
a90_servloc_query.tlv_count=4
a90_servloc_query.qmi_result_valid=1
a90_servloc_query.qmi_result=0
a90_servloc_query.qmi_error=0
a90_servloc_query.total_domains_valid=1
a90_servloc_query.total_domains=1
a90_servloc_query.db_rev_count_valid=1
a90_servloc_query.db_rev_count=1
a90_servloc_query.domain_list_valid=1
a90_servloc_query.domain_count=1
a90_servloc_query.wlan_like_domains=1
```

## Rollback Gate

- native rollback selftest fail=0: `True`
- base handoff decision/pass: `v1521-magisk-postfs-partial-android-lower-no-pre-window-rollback-pass` / `True`

## Safety

Rollbackable Android-handoff to native v724 only. Android-side writes are limited to the temporary Magisk module and bounded evidence directory. The module runs only a read-only AF_QIPCRTR service-locator get-domain-list query for `wlan/fw` plus log capture. No Wi-Fi HAL start, scan/connect, credential handling, DHCP/routes, external ping, PMIC/GPIO/GDSC/regulator write, forced RC1/case write, `/dev/subsys_esoc0` open, fake ONLINE, eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, restart-PD request, or partition write beyond the declared boot-image handoff/rollback.

## Next

- Use the selected label to choose the next native action; do not attempt Wi-Fi connect/ping until native init proves WLFW service69 and `wlan0`.
