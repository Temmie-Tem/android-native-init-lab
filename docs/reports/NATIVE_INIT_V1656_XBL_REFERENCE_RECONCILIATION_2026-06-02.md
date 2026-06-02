# Native Init V1656 XBL Reference Reconciliation

## Summary

- Cycle: `V1656`
- Type: host-only XBL/reference reconciliation
- Decision: `v1656-xbl-reference-reconciliation-pass`
- Result: PASS
- Input: `tmp/wifi/v1655-xbl-context-interpretation/manifest.json`
- Source decision: `v1655-xbl-context-interpretation-pass`
- Device commands: `0`
- Raw string output: `0`
- Power / PCI / Wi-Fi mutation: `0`

## Checks

- `input_exists`: `True`
- `input_v1655_pass`: `True`
- `reference_files_exist`: `True`
- `reference_anchors_present`: `True`
- `xbl_has_sdx_pon_pmic_context`: `True`
- `xbl_has_pcie_context`: `True`
- `host_only_no_device_command`: `True`
- `no_raw_string_output`: `True`
- `no_wifi_or_power_mutation`: `True`

## XBL Signal Summary

- Total records: `326`
- Cross-slot duplicate groups: `96`
- Token totals: aop=98, gpio=7, pcie=2, pmic=48, pon=24, ps_hold=2, rpmh=132, sdx=6, vdd=15
- Class totals: generic-power-token-context=177, no-token-context=141, pcie-context=2, sdx-mdm-context=6
- Has SDX/PON/PMIC context: `True`
- Has PCIe context: `True`
- Has GPIO token: `True`

## Reference Matrix

| key | role | file | anchors |
|---|---|---|---|
| `android-v852-provider-positive` | Android-good lower Wi-Fi/provider positive control | `docs/reports/NATIVE_INIT_V852_ANDROID_EXT_MDM_PROVIDER_SURFACE_HANDOFF_2026-05-25.md` | mdm3 state=True, ONLINE=True, GPIO 142=True, BDF=True, wlan0=True |
| `native-v1461-provider-block` | native provider reaches sdx50m path but no endpoint response | `docs/reports/NATIVE_INIT_V1461_PROVIDER_THREAD_STATE_CLASSIFIER_2026-06-01.md` | sdx50m_toggle_soft_reset=True, mdm_subsys_powerup=True, GPIO135=True, GPIO142=True, wlan0=True |
| `android-v1559-pre-endpoint-order` | Android-good AP2MDM ordering before BDF | `docs/reports/NATIVE_INIT_V1559_ANDROID_PRE_ENDPOINT_ORDER_CLASSIFIER_2026-06-02.md` | GPIO135/AP2MDM=True, before BDF=True, native_endpoint_silent=True, scan/connect=True |
| `v1524-pcie-path-attribution` | PCIe/MHI resume path vs debugfs TEST path | `docs/reports/NATIVE_INIT_V1524_ENDPOINT_TRIGGER_ATTRIBUTION_CLASSIFIER_2026-06-02.md` | Android V852=True, RC1 L0=True, MSM_PCIE_RESUME=True, TEST:11=True, scan/connect=True |
| `esoc-pon-source-analysis` | exact provider PON source and polarity closure | `docs/reports/ESOC_PON_SOURCE_ANALYSIS_2026-06-02.md` | GPIO9 PON=True, GPIO135=True, GPIO142=True, ZERO power/regulator=True, not on disk=True |
| `esoc-dtb-parity` | native/Android DTB and bootloader/config parity closure | `docs/reports/ESOC_DTB_PARITY_2026-06-02.md` | DTB parity=True, bootloader=True, NO=True, only remaining unknown=True, GPIO142=True |
| `natural-path-contract` | next live natural-path observation contract | `docs/reports/ESOC_NATURAL_PATH_MDM2AP_OBSERVATION_CONTRACT_2026-06-02.md` | natural=True, GPIO142=True, errfatal=True, forced RC1=True, fake-ONLINE=True |

## Reconciliation

| topic | status | finding | basis | limit |
|---|---|---|---|---|
| `xbl-as-information-source` | `supported` | XBL contains SDX/PON/PMIC/RPMh/AOP/PCIe context and is useful for owner attribution. | records=326 cross_slot_dupes=96 has_sdx_pon_pmic=True | The records are redacted metadata; they do not expose a direct write target. |
| `xbl-as-native-vs-android-differential` | `not-supported` | XBL context does not currently explain a native-vs-Android differential. | dtb_and_bootloader_parity_reference_present=True; only boot partition changes between native and Android rollback flow. | XBL can identify historical ownership, but identical bootloader artifacts are not a mutation target without a concrete differential. |
| `provider-pon-path` | `closed-host-side` | The AP/provider PON sequence remains host-verified rather than the active defect. | pon_source_closure_present=True; native provider block present=True | Host evidence cannot prove whether the SDX50M main rail electrically responds to the correct PON pulse. |
| `lower-wifi-path` | `blocked-before-connect` | Wi-Fi HAL, scan/connect, DHCP, and external ping remain downstream. | android_positive_reference=True; native provider block=True | Native still lacks GPIO142/MDM2AP response, RC1 L0, MHI, WLFW, BDF, FW-ready, and wlan0. |
| `next-live-gate` | `natural-path-read-only` | The next aligned live gate is the one-run natural-path MDM2AP observation contract, not another forced RC1 or XBL mutation. | natural_contract_present=True; xbl_has_gpio_token=True xbl_has_pcie_context=True | If mdm2ap-silent-natural-path repeats, bounded rail/PMIC write remains a separate explicit gate. |

## Selected Reference Anchors

### `android-v852-provider-positive`
- `docs/reports/NATIVE_INIT_V852_ANDROID_EXT_MDM_PROVIDER_SURFACE_HANDOFF_2026-05-25.md:5` - decision: `v852-android-mdm3-online-provider-surface-captured`
- `docs/reports/NATIVE_INIT_V852_ANDROID_EXT_MDM_PROVIDER_SURFACE_HANDOFF_2026-05-25.md:26` | mdm3 state | `ONLINE` | `OFFLINING` |
- `docs/reports/NATIVE_INIT_V852_ANDROID_EXT_MDM_PROVIDER_SURFACE_HANDOFF_2026-05-25.md:27` | mss state | `ONLINE` | not active in idle surface |
- `docs/reports/NATIVE_INIT_V852_ANDROID_EXT_MDM_PROVIDER_SURFACE_HANDOFF_2026-05-25.md:32` | MDM2AP status IRQ | `mdm status` on GPIO 142, count `1` | not observable |
- `docs/reports/NATIVE_INIT_V852_ANDROID_EXT_MDM_PROVIDER_SURFACE_HANDOFF_2026-05-25.md:35` | BDF downloads | `regdb.bin`, `bdwlan.bin` | absent |
- `docs/reports/NATIVE_INIT_V852_ANDROID_EXT_MDM_PROVIDER_SURFACE_HANDOFF_2026-05-25.md:36` | `wlan0` | present in dmesg | absent |
- `docs/reports/NATIVE_INIT_V852_ANDROID_EXT_MDM_PROVIDER_SURFACE_HANDOFF_2026-05-25.md:48` - `wlfw_send_bdf_download_req: BDF file : regdb.bin`
- `docs/reports/NATIVE_INIT_V852_ANDROID_EXT_MDM_PROVIDER_SURFACE_HANDOFF_2026-05-25.md:49` - `wlfw_send_bdf_download_req: BDF file : bdwlan.bin`
### `native-v1461-provider-block`
- `docs/reports/NATIVE_INIT_V1461_PROVIDER_THREAD_STATE_CLASSIFIER_2026-06-01.md:9` - Reason: V1460 proves the exact provider Binder thread enters sdx50m_toggle_soft_reset, then msleep, then remains blocked in mdm_subsys_powerup while GPIO135/GPIO142, MDM status IRQ, pcie1 clocks/GDSC, RC1/MHI/WLFW, and wlan0 stay inactive
- `docs/reports/NATIVE_INIT_V1461_PROVIDER_THREAD_STATE_CLASSIFIER_2026-06-01.md:27` - late samples blocked in `mdm_subsys_powerup`: `True`
- `docs/reports/NATIVE_INIT_V1461_PROVIDER_THREAD_STATE_CLASSIFIER_2026-06-01.md:33` | `provider_micro_after_trigger_0ms` | `sdx50m_toggle_soft_reset` |
- `docs/reports/NATIVE_INIT_V1461_PROVIDER_THREAD_STATE_CLASSIFIER_2026-06-01.md:34` | `provider_micro_after_trigger_1ms` | `sdx50m_toggle_soft_reset` |
- `docs/reports/NATIVE_INIT_V1461_PROVIDER_THREAD_STATE_CLASSIFIER_2026-06-01.md:35` | `provider_micro_after_trigger_2ms` | `sdx50m_toggle_soft_reset` |
- `docs/reports/NATIVE_INIT_V1461_PROVIDER_THREAD_STATE_CLASSIFIER_2026-06-01.md:36` | `provider_micro_after_trigger_5ms` | `sdx50m_toggle_soft_reset` |
- `docs/reports/NATIVE_INIT_V1461_PROVIDER_THREAD_STATE_CLASSIFIER_2026-06-01.md:37` | `provider_micro_after_trigger_10ms` | `sdx50m_toggle_soft_reset` |
- `docs/reports/NATIVE_INIT_V1461_PROVIDER_THREAD_STATE_CLASSIFIER_2026-06-01.md:38` | `provider_micro_after_trigger_20ms` | `sdx50m_toggle_soft_reset` |
### `android-v1559-pre-endpoint-order`
- `docs/reports/NATIVE_INIT_V1559_ANDROID_PRE_ENDPOINT_ORDER_CLASSIFIER_2026-06-02.md:9` - Reason: Android-good shows GPIO135/AP2MDM before BDF while native has AP-side RC1 power/refclk/PERST but no AP2MDM/endpoint response; retained Android IRQ/L0 evidence is late and must not be treated as first-L0 ordering
- `docs/reports/NATIVE_INIT_V1559_ANDROID_PRE_ENDPOINT_ORDER_CLASSIFIER_2026-06-02.md:25` | GPIO135/AP2MDM | 43.891220 | 0 | Android GPIO135 occurs +0.343285s from esoc0 and -0.622807s before BDF; native count stays zero |
- `docs/reports/NATIVE_INIT_V1559_ANDROID_PRE_ENDPOINT_ORDER_CLASSIFIER_2026-06-02.md:39` | native_endpoint_silent | True |
- `docs/reports/NATIVE_INIT_V1559_ANDROID_PRE_ENDPOINT_ORDER_CLASSIFIER_2026-06-02.md:43` Existing evidence can order one important Android-good signal: GPIO135/AP2MDM is asserted after the esoc0 trigger and before BDF download. Native evidence already proves AP-side pcie1 power/refclk/pipe/PERST activity, but GPIO135/AP2MDM, GPIO104/WAKE, GPIO142/MDM2AP, IRQ252, IRQ290, L0, MHI, WLFW, BDF, FW-ready, and `wlan0` remain absent.
- `docs/reports/NATIVE_INIT_V1559_ANDROID_PRE_ENDPOINT_ORDER_CLASSIFIER_2026-06-02.md:51` - Focus: AP2MDM assertion/effective-level gap before BDF rather than late retained IRQ252/IRQ290 ordering
- `docs/reports/NATIVE_INIT_V1559_ANDROID_PRE_ENDPOINT_ORDER_CLASSIFIER_2026-06-02.md:55` - treat Android GPIO135/AP2MDM before BDF as the earliest currently proven discriminating signal
- `docs/reports/NATIVE_INIT_V1559_ANDROID_PRE_ENDPOINT_ORDER_CLASSIFIER_2026-06-02.md:57` - explain why native provider/RC1 path does not produce GPIO135/AP2MDM or endpoint wake/status despite AP-side pcie1 power/refclk/PERST
- `docs/reports/NATIVE_INIT_V1559_ANDROID_PRE_ENDPOINT_ORDER_CLASSIFIER_2026-06-02.md:58` - keep Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, PMIC/GPIO/GDSC direct writes, eSoC notify/BOOT_DONE spoof, global PCI rescan, and platform bind/unbind blocked
### `v1524-pcie-path-attribution`
- `docs/reports/NATIVE_INIT_V1524_ENDPOINT_TRIGGER_ATTRIBUTION_CLASSIFIER_2026-06-02.md:9` - Reason: Android-good initial RC1 is not a debugfs TEST:11 path, endpoint wake is not consistently attributable, and source shows an eSoC/MHI MSM_PCIE_RESUME path that must be modeled before the next mutation
- `docs/reports/NATIVE_INIT_V1524_ENDPOINT_TRIGGER_ATTRIBUTION_CLASSIFIER_2026-06-02.md:29` | v1523-fixed-point | pass | V1523 proves TEST:11 reaches the common enumerate/enable path but still leaves trigger/readiness attribution open |
- `docs/reports/NATIVE_INIT_V1524_ENDPOINT_TRIGGER_ATTRIBUTION_CLASSIFIER_2026-06-02.md:30` | android-v852-esoc-to-l0 | pass | Android V852 shows esoc0 followed by RC1 enable and LTSSM_L0 |
- `docs/reports/NATIVE_INIT_V1524_ENDPOINT_TRIGGER_ATTRIBUTION_CLASSIFIER_2026-06-02.md:31` | android-v852-not-debugfs-test11 | pass | Android V852 initial RC1 sequence has no pci-msm TEST/debugfs marker |
- `docs/reports/NATIVE_INIT_V1524_ENDPOINT_TRIGGER_ATTRIBUTION_CLASSIFIER_2026-06-02.md:32` | native-v1517-debugfs-test11-fails | pass | Native V1517 uses explicit TEST:11 and fails before L0 |
- `docs/reports/NATIVE_INIT_V1524_ENDPOINT_TRIGGER_ATTRIBUTION_CLASSIFIER_2026-06-02.md:33` | mhi-esoc-pm-resume-source-candidate | pass | Local MHI eSoC hook can request MSM_PCIE_RESUME, which dispatches to msm_pcie_enable via pm_resume |
- `docs/reports/NATIVE_INIT_V1524_ENDPOINT_TRIGGER_ATTRIBUTION_CLASSIFIER_2026-06-02.md:38` | field | Android V852 | Android V1521 | Native V1517 |
- `docs/reports/NATIVE_INIT_V1524_ENDPOINT_TRIGGER_ATTRIBUTION_CLASSIFIER_2026-06-02.md:42` | RC1 L0 / link fail | 8.820231 |  | 9.341767 |
### `esoc-pon-source-analysis`
- `docs/reports/ESOC_PON_SOURCE_ANALYSIS_2026-06-02.md:26` AP2MDM_STATUS = 1                          # TLMM GPIO135 high
- `docs/reports/ESOC_PON_SOURCE_ANALYSIS_2026-06-02.md:31` Modem readiness then arrives as the **MDM2AP_STATUS rising IRQ** (GPIO142),
- `docs/reports/ESOC_PON_SOURCE_ANALYSIS_2026-06-02.md:34` the GPIO142 IRQ.
- `docs/reports/ESOC_PON_SOURCE_ANALYSIS_2026-06-02.md:41` enter the real PON code and DOES drive GPIO9 assert/de-assert + GPIO135=1 +
- `docs/reports/ESOC_PON_SOURCE_ANALYSIS_2026-06-02.md:42` ESOC_REQ_IMG. It then waits for the GPIO142/MDM2AP IRQ that never comes.
- `docs/reports/ESOC_PON_SOURCE_ANALYSIS_2026-06-02.md:45` GPIO9 PON toggle (120ms assert) and GPIO135=1, but the SDX50M never raises
- `docs/reports/ESOC_PON_SOURCE_ANALYSIS_2026-06-02.md:46` MDM2AP. Either (a) the GPIO9 PON pulse is electrically ineffective on this boot
- `docs/reports/ESOC_PON_SOURCE_ANALYSIS_2026-06-02.md:54` GPIO9 PON / GPIO135 / ESOC_REQ_IMG never fire on that path — the endpoint is dead
### `esoc-dtb-parity`
- `docs/reports/ESOC_DTB_PARITY_2026-06-02.md:1` # DTB parity — native boot image vs stock/Android modem config (2026-06-02)
- `docs/reports/ESOC_DTB_PARITY_2026-06-02.md:3` **Host-only. No device command, no write.** Closes the "is the modem/PCIe/PMIC
- `docs/reports/ESOC_DTB_PARITY_2026-06-02.md:5` Verdict: **non-differential (parity).** This is the third and final static/config
- `docs/reports/ESOC_DTB_PARITY_2026-06-02.md:6` layer ruled out as the Android-vs-native differentiator, after bootloader and the
- `docs/reports/ESOC_DTB_PARITY_2026-06-02.md:11` correct and the provider carries no regulator. The remaining host-checkable
- `docs/reports/ESOC_DTB_PARITY_2026-06-02.md:14` bootloader is identical. If true, that WOULD be a real differential (the DTB is
- `docs/reports/ESOC_DTB_PARITY_2026-06-02.md:18` - Native boot image: `stage3/boot_linux_v724.img` (the device's known-good
- `docs/reports/ESOC_DTB_PARITY_2026-06-02.md:23` match, not a DTB). Carved both and parsed with a minimal Python FDT walker.
### `natural-path-contract`
- `docs/reports/ESOC_NATURAL_PATH_MDM2AP_OBSERVATION_CONTRACT_2026-06-02.md:1` # Live observation contract — natural ESOC_PWR_ON path, MDM2AP/GPIO142 response (2026-06-02)
- `docs/reports/ESOC_NATURAL_PATH_MDM2AP_OBSERVATION_CONTRACT_2026-06-02.md:25` SDX50M actually power up and answer on MDM2AP/GPIO142? That is not on disk.
- `docs/reports/ESOC_NATURAL_PATH_MDM2AP_OBSERVATION_CONTRACT_2026-06-02.md:29` ### Trigger — natural path ONLY
- `docs/reports/ESOC_NATURAL_PATH_MDM2AP_OBSERVATION_CONTRACT_2026-06-02.md:30` Drive the modem through the provider's natural
- `docs/reports/ESOC_NATURAL_PATH_MDM2AP_OBSERVATION_CONTRACT_2026-06-02.md:37` - forced RC1 enumerate (`rc_sel=2` + `case=11`, sysfs `debug/enumerate`, any
- `docs/reports/ESOC_NATURAL_PATH_MDM2AP_OBSERVATION_CONTRACT_2026-06-02.md:40` - fake-ONLINE / system-info spoof to advance pm-service (inverted causality,
- `docs/reports/ESOC_NATURAL_PATH_MDM2AP_OBSERVATION_CONTRACT_2026-06-02.md:46` Reuse the EXISTING clean natural-path observers; do NOT invent new write paths.
- `docs/reports/ESOC_NATURAL_PATH_MDM2AP_OBSERVATION_CONTRACT_2026-06-02.md:50` RC1 writer), plus the `mdm2ap_errfatal_pcie_timing` sampler

## Decision

V1656 narrows the role of XBL evidence: it is useful owner/context evidence, but not a direct native-vs-Android differential or write target. Existing references still place the active blocker below provider entry and before connect-side Wi-Fi: native lacks the SDX50M MDM2AP/GPIO142 response and downstream RC1 L0/MHI/WLFW/wlan0.

## Next

V1657 should return to the bounded natural-path MDM2AP observation contract: one read-only live run using natural `__subsystem_get(esoc0)`/`mdm_subsys_powerup`, with GPIO142 IRQ delta and errfatal IRQ delta as discriminators. Do not use forced RC1 enumerate, fake-ONLINE/system-info spoofing, PMIC/GPIO/GDSC writes, eSoC notify/`BOOT_DONE`, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.
