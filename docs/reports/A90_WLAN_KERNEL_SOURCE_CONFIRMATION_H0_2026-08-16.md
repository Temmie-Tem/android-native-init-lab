# A90 WLAN kernel source confirmation and correction of the pre-source prior

Date: 2026-08-16
Target: operator-owned Samsung Galaxy A90 5G only
Tier: H0 host-only source analysis
Device, `/dev`, USB, or network contact: none
Private input mutation: none
Disposition: source-backed partial closure; Option C remains research-only

## Result in one paragraph

The matching Samsung 4.14.190 source materially narrows the Option C WLAN
capsule. The base ICNSS path is a kernel QMI **client** for the remote WLFW
service, and this QRTR implementation explicitly requires a userspace service
listing daemon. The selected path therefore needs a QRTR name-service
implementation; the current implementation is `/vendor/bin/qrtr-ns`. In
contrast, ICNSS invokes the PD locator/notifier path as optional recovery setup
and ignores its return during probe, so the earlier suspicion that the PD group
was the primary bring-up dependency is weakened. The source does not prove
`pd_mapper`, the RFS roles, `cnss_daemon`, or `macloader` removable: recovery,
remote-firmware lifetime, proprietary userspace behaviour, and the deployed
`WCNSS_qcom_cfg.ini` remain unproved. No current H0 gate is retired by this
report.

## Relationship to the 2026-08-15 report

`A90_WLAN_KERNEL_SIDE_COMPOSITION_H0_2026-08-15.md` intentionally recorded a
prior before the source was available. It is not rewritten to make that prior
look more accurate. This report is the append-only correction layer.

| Pre-source statement | Matching-source result | Disposition |
|---|---|---|
| `qrtr_ns` is a near-certain requirement | QRTR Kconfig explicitly requires a userspace daemon for service lookups, and `qmi_add_lookup()` depends on name-server `NEW_SERVER`/`DEL_SERVER` replies | **confirmed for the service-name function**, not for one irreplaceable binary |
| suspicion moves toward the PD/RFS group for base bring-up | ICNSS calls service-location/notifier code from its recovery setup, and probe ignores the setup return | **PD bring-up prior partially refuted**; recovery value remains open |
| `cnss_diag` is diagnostic | its handler carries firmware-log and crash-injection traffic | **strengthened**, but removal remains unproved |
| `cnss_daemon` is a weaker bring-up suspect | no base ICNSS call to that process is present | **strengthened only as a prior**; proprietary behaviour remains opaque |
| eight `cnss_utils` symbols describe its whole surface | the PLD layer has eight wrappers, but `cnss_utils` exports additional interfaces and Samsung adds a separate sysfs MAC input | **corrected** |
| `cnss_genl` has only spectral-scan and OEM consumers | this tree contains OEM, CNSS diagnostic, PUMAC, PTT, and spectral-scan registrations under feature guards | **corrected** |
| the kernel has only MEM_SHARE and IPA QMI servers | the source has IPA v2, IPA v3, MEM_SHARE, and USB-audio call sites; this defconfig selects IPA3, MEM_SHARE, and USB audio | **corrected**, with no WLAN server added |

## Source identity and what it proves

The operator staged the private source package at:

```
workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource_13272/
```

The package manifest and independent host-side hashes agree:

| Object | SHA-256 |
|---|---|
| `SM-A908N_KOR_12_Opensource.zip` | `d0a6c9f29387a6ba9d5fe0ad8c1a1e79576f4d0c0bc463394f1cd70389897a3b` |
| `Kernel.tar.gz` | `403fdc49f086d238c01a796c390083c3c47c1754c218e228f29b55cc7c35d554` |
| `Platform.tar.gz` | `8bdbc5066ef95c3b823328fc6e8e30af2b0d827eeec7125c80ed8f162f475c27` |
| `r3q_kor_single_defconfig` | `3d90a83d61a7a1873249642f7657c572e06f91a61bc3e5b737758f08ec765216` |
| staged runtime `v3404.config` | `e4b7fa2f4fd6055eecfc7fd7b7546ab3e77ffdaf8ee77da27c9f341646f77f8b` |

The outer ZIP passes `unzip -t`. `MANIFEST.sha256` validates all five packaged
objects. The kernel Makefile is `4.14.190`. All 5,704 explicit defconfig
assignments are present with identical values in the staged runtime config;
there are zero mismatches.

That is strong evidence that this is the matching A908N KOR Android-12 kernel
source family and configuration. It is **not** a reproducible-build proof that
every installed kernel byte was produced from these exact source bytes. Toolchain,
generated inputs, vendor patches omitted from the release, and the installed
binary-to-source derivation remain unproved.

## Q1: what ICNSS requires from userspace

### The base control path

`drivers/soc/qcom/icnss_qmi.c:1265-1277` initializes one QMI handle for ICNSS
firmware control and registers one lookup:

```
WLFW_SERVICE_ID_V01 / WLFW_SERVICE_VERS_V01 / instance 0
```

`drivers/soc/qcom/icnss.c:4109-4115` makes failure to register that lookup fatal
to probe. When the service appears, the WLFW event path connects, powers the
device, registers indications, sets up MSA memory, and queries capabilities
(`icnss.c:963-1059`). A BDF request type exists in the generated protocol
definitions, but this selected ICNSS source contains no BDF request sender; the
report does not attribute board-data loading to that event path. The source
calls the endpoint the WLAN firmware service and implements no WLAN
`qmi_add_server()`.

This establishes a kernel-client/remote-service architecture. It does not, by
itself, identify the exact runtime QRTR node or prove that every WLFW server
byte resides in one firmware image. That exact endpoint attribution needs
runtime or firmware evidence and remains unproved.

### Why a QRTR name service is structural on this tree

The proof chain is direct:

1. `net/qrtr/Kconfig:12-13` says service lookups require a userspace daemon to
   maintain the service listing.
2. `net/qrtr/Makefile` contains the router and transports, but no built-in name
   service.
3. `drivers/soc/qcom/qmi_interface.c:207-238` registers a lookup with the name
   server and expects `NEW_SERVER` and `DEL_SERVER` control messages.
4. Without the controller replies, ICNSS can enqueue its lookup, but it cannot
   discover/connect to WLFW and advance through the server-arrival path using
   this architecture. `qmi_add_lookup()` returning zero is not proof that a
   service was found.

Therefore **some correct QRTR userspace name-service implementation is a hard
dependency of the selected 4.14 path**. The current H24 graph supplies it as
`/vendor/bin/qrtr-ns`. The source does not prove that this exact executable is
the only possible implementation; replacing it would require a separately
bound equivalent, not mere deletion.

This source also closes an Option C containment assumption. Kernel QMI sockets
are created with `sock_create_kern(&init_net, AF_QIPCRTR, ...)`
(`qmi_interface.c:604-627`), while `qrtr.c` keeps one global `qrtr_ports` IDR
and one global endpoint list (`:142-147`) and does not key lookup or assignment
by network namespace (`:1292-1309,1381-1417`). A fresh network namespace alone
is therefore **not a proved QRTR isolation boundary**. The trusted WLAN backend
needs the QRTR plane, but a remotely reachable Debian workload must be denied
`AF_QIPCRTR` rather than being assumed isolated from it by `CLONE_NEWNET`.

The privileged-port predicate is also exact in this source: a low QRTR port is
allowed by `CAP_NET_ADMIN`, group `AID_VENDOR_QRTR` (`2906`), or the global root
group (`qrtr.c:55,1381-1406`). H24's `2906:2906` QRTR identity satisfies the
kernel group branch. The separately retained `CAP_NET_BIND_SERVICE` is not this
kernel check; whether the proprietary executable needs that capability for
some other operation remains unproved.

### PD locator/notifier is a recovery path, not a fatal probe prerequisite

`icnss_pd_restart_enable()` asks the service locator for WLAN domains and then
registers service notifiers (`icnss.c:1967-2073`). It is reached only from
`icnss_enable_recovery()` (`:2076-2108`). The same function supports
`RECOVERY_DISABLE`, `SSR_ONLY`, and `PDR_ONLY` quirks. Most importantly, probe
calls `icnss_enable_recovery(priv)` at `:4115` without checking its return,
after the fatal WLFW registration check.

The locator itself defaults to `LOCATOR_NOT_PRESENT` and exposes an `enable`
module parameter (`service-locator.c:39-45,245-257`). `get_service_location()`
schedules asynchronous work and normally returns before the service lookup
result is known (`:306-345`); a later locator failure calls the ICNSS notifier
with `LOCATOR_DOWN`, which ICNSS ignores at `icnss.c:1981-1982`. The exact boot
parameter remains unproved, but the source default and error flow reinforce
that this is not the fatal base-lookup gate.

This refutes the narrow prior that successful PD lookup is required for the
initial ICNSS probe. It does **not** prove the PD roles removable from a 24/7
server. Firmware-crash notification, PDR restart, and recovery-quality
requirements are part of the steady-state acceptance boundary, so their exact
necessity remains unproved until independently observed or ablated.

### RFS remains unresolved

There is no direct `rmt_storage`, `rmtfs`, or `tftp_server` call in the ICNSS
driver. That absence is not proof of irrelevance. Those roles may make firmware
or calibration data available to the remote subsystem before WLFW becomes
discoverable. The kernel source does not describe that remote boot dependency,
so the RFS roles remain unproved rather than classified removable.

## Q2: kernel QMI client and server roles

| Service or family | Kernel role in this source | Source-backed placement conclusion |
|---|---|---|
| WLFW (`0x45`, version `0x01`) | client lookup from ICNSS | remote WLAN firmware service; exact runtime endpoint unproved |
| SERVREG_LOC (`0x40`) | client lookup from service locator | server placement unproved by this source |
| SERVREG_NOTIF (`0x42`) | client lookup from service notifier | server placement unproved by this source |
| IPA v3 | server in the selected defconfig | compiled kernel service, not a WLAN bring-up server |
| MEM_SHARE | server in the selected defconfig | compiled kernel service, not a WLAN bring-up server |
| USB audio QMI | server in the selected defconfig | compiled kernel service, not a WLAN bring-up server |

There are four source call sites outside the QMI implementation itself: IPA
v2, IPA v3, MEM_SHARE, and USB audio. The exact defconfig selects `IPA3=y`,
leaves legacy `IPA` unset, and selects both `MEM_SHARE_QMI_SERVICE=y` and
`SND_USB_AUDIO_QMI=y`. Thus the compiled server families are three, not two.
None is a WLAN `qmi_add_server()`, so the correction does not change the ICNSS
client-side conclusion.

The source also does not prove that `pd_mapper` is the sole SERVREG_LOC server
or that every SERVREG_NOTIF server sits in one named remote PD. Those are
current-Android topology hypotheses and must not be promoted to source facts.

## Q3: `cnss_utils`, `cnss_genl`, and the opaque userspace roles

### `cnss_utils`

The qcacld PLD layer exposes eight wrappers for unsafe-channel set/get, DFS NOL
set/get, provisioned/derived MAC retrieval, and driver-load count increment/get
(`core/pld/inc/pld_common.h:452-575`). They are eight PLD wrappers, not the
entire exported `cnss_utils` ABI.

MAC provisioning has two visible kernel input surfaces:

- `drivers/net/wireless/cnss_utils/cnss_utils.c:477-603` provides a mode-0600
  debugfs `mac_address` file;
- Samsung ICNSS creates `/sys/wifi/mac_addr` mode 0220 and passes it to
  `cnss_utils_set_wlan_mac_address()` (`icnss.c:3706-3729,3842-3885`).

The public H24 helper also explicitly targets `/sys/wifi/mac_addr`
(`a90_android_execns_probe.c:17669-17733`). Therefore the Samsung macloader
path is not merely a debugfs convention.

The driver parameter `enable_mac_provision` defaults to `0`
(`core/hdd/inc/hdd_config.h:702-720`). `hdd_initialize_mac_address()` then uses
this fallback chain (`wlan_hdd_main.c:12234-12280`): platform/cnss-utils MAC,
`wlan_mac.bin`, firmware `hw_macaddr`, serial-derived MAC, and finally a random
MAC. If `enable_mac_provision=1`, absence of the provisioned platform MAC is a
fatal error; its caller propagates that failure (`:13959-13963`).

The exact deployed value is therefore decisive. It is not in the kernel
source: `WCNSS_qcom_cfg.ini` is a runtime vendor input. The same driver treats
failure to parse that INI as fatal (`wlan_hdd_main.c:11416-11422`), and the
source fixes its path in `wlan_hdd_misc.h:44-50`. Neither that INI nor
`wlan_mac.bin` is present in the staged OSRC package or public repository.
Consequently `macloader` necessity remains **unproved**, not disproved.

### `cnss_genl`

The source contains registrations for these message IDs under their respective
feature guards:

- `WLAN_NL_MSG_OEM`;
- `WLAN_NL_MSG_CNSS_DIAG`;
- `ANI_NL_MSG_PUMAC`;
- `ANI_NL_MSG_PTT`;
- `WLAN_NL_MSG_SPECTRAL_SCAN`.

`CONFIG_CNSS_GENL=y` selects the generic-netlink transport, but the staged
defconfig alone does not prove which additional WLAN feature guards were in
the exact installed build. The earlier two-message enumeration was therefore
too narrow.

The CNSS diagnostic handler does support firmware-log delivery and crash
injection (`dbglog_host.c:4161-4260`). This is strong static support for keeping
`cnss_diag` first among removal candidates. It still does not prove the
userspace process has no acceptance-critical side effect.

OEM is likewise broader than “RTT”: source paths include generic OEM data and
positioning/capability traffic. A diagnostic label must not be generalized to
all OEM traffic.

### What source cannot say about `cnss-daemon`

No ICNSS base-bring-up call names `cnss-daemon`. The qcacld source does name
four classes of interaction with it: applying RX-queue RPS CPU maps, forwarding
core-minimum-frequency requests to `perfd`, changing TCP throughput sysctls,
and restoring the interop-issues AP list after driver reload
(`wlan_nlink_common.h:184-243`, `wlan_hdd_napi.c:263-324`,
`hdd_dp_cfg.h:472-491,620-646`, and
`wlan_cfg80211_interop_issues_ap.c:242-267`). These are performance/policy and
compatibility paths, not the fatal WLFW lookup.

That strengthens the prior that `cnss-daemon` is an early ablation candidate,
but does not close it. Its proprietary executable may perform transactions not
named by kernel comments, and its exact runtime behaviour is not present in
this source release. Removability remains unproved.

## Additional source defect: Samsung MAC sysfs parser

`icnss.c:3717-3723` parses six MAC octets by casting the address of each byte in
a six-byte array to `unsigned int *` for six `%02X` conversions. Each conversion
writes an `unsigned int`, so the writes overlap and the final conversions write
beyond the array. The code also ignores the conversion count and returns `0`
instead of the consumed sysfs byte count.

This is a static correctness and hardening defect in the source path. No live
trigger, installed-byte identity, or exploit impact is claimed here. A future
Option C implementation must not copy this parser: it should parse into six
properly sized temporaries (or a bounded hex decoder), validate exactly six
octets, and return `count` only on success.

The alternative debugfs parser has a separate defect
(`cnss_utils.c:477-540`). After validating that the string contains a multiple
of 12 hexadecimal characters, it executes `while (len--)` but consumes **two**
characters and emits one byte per iteration. A one-MAC input therefore attempts
12 byte conversions instead of six, reads beyond the terminated MAC string,
and can partially mutate the destination before returning an error. The
debugfs path is not a sound replacement for the Samsung sysfs path without its
own fix and validation.

## Consequence for Option C and WP-H0-2

The source changes the research program, but does not silently rewrite its
authority model:

1. A future reviewed design may classify the **QRTR name-service function** as
   structurally retained and remove a pointless deletion experiment. That
   requires an exact candidate implementation and an independent update to the
   WP-H0-2 design; this report alone does not do it.
2. PD roles move from “base bring-up suspects” to “recovery-quality suspects.”
   Their experiment must measure firmware crash/restart and sustained service,
   not merely first scan or association.
3. `cnss_diag` remains the best first deletion candidate, with stronger static
   support.
4. `macloader` cannot be classified until the exact deployed
   `WCNSS_qcom_cfg.ini` is known.
5. RFS and proprietary-daemon necessity cannot be settled from this kernel
   tree; their upstream remote-subsystem and userspace evidence is still
   missing.

`H0D01` through `H0D10` remain in their current declared states. No component
is retired, no generation is qualified, and no candidate or execution consumer
is created by this report.

## Next bounded H0 unit

The highest-value next input is the exact matching vendor firmware/config
content, acquired and staged host-only from an operator-provided matching
artifact. Read only:

- `/mnt/vendor/firmware/wlan/qca_cld/WCNSS_qcom_cfg.ini`, the current H24
  source root plus the exact firmware request name, or its independently bound
  matching-artifact equivalent;
- `wlan_mac.bin`, if present;
- the board-data/regulatory files selected by the current H24 helper;
- the init/service declarations that launch `qrtr-ns`, PD/RFS roles,
  `cnss-daemon`, `cnss_diag`, and macloader.

The immediate question is the exact `enable_mac_provision` value and whether
any other configuration key turns an auxiliary kernel interface into a fatal
requirement. This can save an attended ablation only after the exact artifact
is pinned and its consumer semantics are reviewed. No device read or live
session is authorized by this next-unit description.

## Source anchors

Private source root (not tracked):
`workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource_13272/Kernel/`

- `drivers/soc/qcom/icnss_qmi.c:1265-1277`
- `drivers/soc/qcom/icnss.c:963-1059,1967-2108,3706-3729,3842-3885,4109-4115`
- `drivers/soc/qcom/qmi_interface.c:207-238`
- `drivers/soc/qcom/service-locator.c:269-280`
- `drivers/soc/qcom/service-notifier.c:536-548`
- `net/qrtr/Kconfig:4-25`
- `net/qrtr/Makefile:1-22`
- `net/qrtr/qrtr.c:55,142-147,1292-1309,1381-1417`
- `drivers/net/wireless/cnss_utils/cnss_utils.c:477-603`
- `drivers/net/wireless/qualcomm/wcn39xx/qcacld-3.0/core/pld/inc/pld_common.h:452-575`
- `drivers/net/wireless/qualcomm/wcn39xx/qcacld-3.0/core/hdd/inc/hdd_config.h:702-720`
- `drivers/net/wireless/qualcomm/wcn39xx/qcacld-3.0/core/hdd/inc/wlan_hdd_misc.h:44-50`
- `drivers/net/wireless/qualcomm/wcn39xx/qcacld-3.0/core/hdd/src/wlan_hdd_main.c:11416-11422,12234-12280,13959-13963`
- `drivers/net/wireless/qualcomm/wcn39xx/qca-wifi-host-cmn/utils/fwlog/dbglog_host.c:4161-4260`
- `drivers/net/wireless/qualcomm/wcn39xx/qca-wifi-host-cmn/utils/nlink/inc/wlan_nlink_common.h:184-243`
- `drivers/net/wireless/qualcomm/wcn39xx/qcacld-3.0/core/hdd/src/wlan_hdd_napi.c:263-324`
- `drivers/net/wireless/qualcomm/wcn39xx/qcacld-3.0/core/hdd/inc/hdd_dp_cfg.h:472-491,620-646`
- `drivers/net/wireless/qualcomm/wcn39xx/qcacld-3.0/os_if/interop_issues_ap/src/wlan_cfg80211_interop_issues_ap.c:242-267`
- `arch/arm64/configs/r3q_kor_single_defconfig`
- public H24 companion source:
  `workspace/public/src/native-init/helpers/a90_android_execns_probe.c:17669-17733`

## Boundary and authority

This report was produced from the operator-staged named A90 source package,
the already-staged A90 runtime configuration, and public A90 repository files.
It did not read any other private path. Device, `/dev`, USB, network, S22+, and
S20+ contacts are zero. No source or private evidence was modified.

This is H0 research evidence only. It grants no D0, D1, F1, candidate,
installation, handoff, property, UFS-content, live-ablation, or recovery
authority. Option C remains research-only and implementation-blocked by its
declared gates and independent reviews.
