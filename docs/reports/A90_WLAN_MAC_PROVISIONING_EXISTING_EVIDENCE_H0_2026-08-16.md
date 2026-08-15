# A90 WLAN MAC provisioning existing-evidence audit

Date: 2026-08-16
Target: operator-owned Samsung Galaxy A90 5G only
Tier: H0 host-only source and committed-evidence analysis
Device, `/dev`, USB, or network contact: none
Disposition: strong V3342 prior; effective and current values remain unproved

## Result

An exact vendor artifact is **not required for the next Option C H0
documentation unit**. `macloader` is not a role in the current H24 thirteen-role
ablation graph, so `WP2-4` may proceed without classifying the literal INI key.
The existing record also supplies a strong V3342 prior: that build did not
compile or enqueue its macloader path, the same bound live record fed the
mounted-vendor-first `WCNSS_qcom_cfg.ini`, and the run then created a working
`wlan0`. In this driver, an effective `enable_mac_provision=1` with no platform
MAC returns an error before default-vdev creation.

That chain does **not** prove the effective V3342 boolean false. The V3342
private root mounted procfs in the shared PID namespace, and the exact helper
itself used `/proc/1/root/...` as a source path. Two opaque children launched
before the WLAN trigger used the retained init-root identity. They could in
principle reach outer `/sys/wifi/mac_addr` or the cnss_utils debugfs writer;
the public V3342 record contains no same-run syscall or getter evidence that
excludes those writes. The debugfs writer also mutates the platform-MAC bytes
and count before its malformed loop eventually returns `-EINVAL`, so a caller
that ignores the return could still seed the getter.

The literal key, the effective V3342 value, and byte identity between the
2026-06-28 vendor file and the current H24 source root therefore remain
**unproved**. This audit narrows the next proof, but does not replace it.

## Why the earlier three-week comparison was insufficient

The archived V2092 classifier correctly records the V2091 observations:

- the real `/sys/wifi/mac_addr` node existed as sysfs mode `0220`;
- macloader was traced for fourteen focused records;
- `.mac.info` read, `mac_addr` open/write, write shape, and the kernel assignment
  line were all false.

But its own route matrix records `fw_ready=0` and `wlan0=0` for V2091. V2092
therefore proves that the observed macloader route did not write a platform MAC;
it does not, by itself, prove the effective INI value. Pairing that 2026-06-05
absence with V3342 three weeks later would leave an unbound build-generation
gap.

The audit below does not make that comparison. It combines the exact V3342
build topology with the exact V3342 live result, and uses V2092 only as
corroborating historical evidence that the earlier macloader branch was not a
working producer.

## Same-generation V3342 evidence and proof gap

### 1. The build and live record bind the same candidate

Both V3342 reports bind:

- boot SHA-256
  `836f76249d578ef42e25a2d0c7b43cc3ef1d8db9efe5dabc6ee5ce13b10e5502`;
- helper SHA-256
  `fa395d3ecb6944a57487f3966948a634596157e4de3fdc39575a2fc502d1ceef`;
- init `0.11.106`, build `v3342-softap-s3-fwsource-iftype-probe`.

The live report says the reviewed flash helper wrote and read back only that
boot image, then obtained the same version/build and clean self-test. This is a
fresh-kernel boot, so a platform-MAC list cannot be carried in RAM from an
earlier candidate.

### 2. The V3342 helper topology has no selected macloader

The V3342 builder is recorded by commit
`3e7eed10bb23193d5cb5e84eff9e4fa4637a7fa0`. Its V3341 parent takes the helper
flag set from `build_native_init_boot_v2237_supplicant_terminate_poll.py` and
adds the service-object firmware-class bridge. Reconstructing that frozen flag
chain produces twenty-five flags for the V3342 helper. It includes the
post-FW-ready boot-WLAN trigger and firmware-class feeder, but none of:

- `A90_WIFI_TEST_BOOT_MACLOADER_PRE_CNSS`;
- `A90_WIFI_TEST_BOOT_MACLOADER_MAC_SOURCE_BRIDGE`;
- `A90_WIFI_TEST_BOOT_MACLOADER_SYSCALL_TRACE`;
- `A90_WIFI_TEST_BOOT_MACLOADER_PROPERTY_SERVICE_ACK`.

In the helper source at that commit, all four macros default to zero.
`macloader_pre_cnss` is true only when the WLAN-PD firmware gate is active
**and** `A90_WIFI_TEST_BOOT_MACLOADER_PRE_CNSS` is nonzero; the composite graph
enqueues `/vendor/bin/hw/macloader` only inside that predicate. The V3342 route
therefore did not launch macloader.

The V2146 historical MAC assignment was a separate host-side experiment. It is
not part of the V3342 helper flag chain or the V3342 live procedure. Static
source search finds no explicit V3342 init/helper MAC write, but static absence
from the reviewed helper is not evidence about opaque vendor children.

### 3. Setter-call search does not close the alternative writer

The matching defconfig selects `CONFIG_CNSS_UTILS=y`. Consequently
`pld_get_wlan_mac_address()` and its derived-address counterpart call the
`cnss_utils` getters, rather than the disabled stubs or legacy CNSS PCI path.

`cnss_utils_init()` allocates its private state with `kzalloc()`. The selected
source has one external provisioned-MAC setter call: Samsung's
`store_mac_addr()` passes `/sys/wifi/mac_addr` input to
`cnss_utils_set_wlan_mac_address()`. The derived setter has no caller in this
kernel tree. This search is useful but not complete: the cnss_utils debugfs
writer directly selects `priv->wlan_mac_addr`, sets
`no_of_mac_addr_set = len / 12`, and writes the destination bytes without
calling the exported setter.

Its loop is malformed: for `12N` hexadecimal characters it iterates `12N`
times while consuming two characters per iteration. The first `6N` iterations
already write the complete `6N` MAC bytes, then a later iteration reaches the
string terminator and returns `-EINVAL`. The count and valid prefix are not
rolled back. A caller that treats the write as best-effort can therefore seed a
valid platform MAC even though the write syscall reports failure.

The V3342 `MAC_SOURCE_BRIDGE` flag was zero, so its private root did not receive
the helper's direct RW bind of `/sys/wifi`; that closes one path. It does not
close `/proc/1/root`: `setup_namespace()` mounted procfs without a fresh PID
namespace, the firmware feeder itself enumerated `/proc/1/root/vendor/firmware`
and `/proc/1/root/mnt/vendor/firmware`, and the selected root-identity fallback
applied to `rmt_storage` and `tftp_server`. Both were spawned before the
post-FW-ready WLAN trigger. The public record did not trace their complete file
writes, so neither outer sysfs nor outer debugfs seeding is excluded.

### 4. An enabled provisioning gate would prevent `wlan0`

`hdd_platform_wlan_mac()` returns `-EINVAL` when the platform getter returns no
address. `hdd_initialize_mac_address()` handles that result in two distinct
ways:

- if `mac_provision` is false, it continues through `wlan_mac.bin`, firmware
  `hw_macaddr`, serial-derived, and random fallback paths;
- if `mac_provision` is true, it returns the platform error immediately.

`hdd_wlan_startup()` propagates that error through `unregister_wiphy`.
`__hdd_soc_probe()` calls `hdd_psoc_create_vdevs()` only after
`hdd_wlan_startup()` succeeds. Therefore the failed enabled-provisioning branch
cannot create the default `wlan0` vdev.

### 5. V3342 records the successful outcome, not the missing cause

The bound V3342 live record contains, in one helper result:

```text
source_policy=qcacld-fwsource-mounted-vendor-first
request_0.firmware=wlan/qca_cld/WCNSS_qcom_cfg.ini
request_0.source_rc=0
request_0.source_bytes=13343
request_0.fed=1
wlan0_present=1
```

It then independently records `wlan0` link-up and successful AP-iftype
add/delete cleanup:

```text
ap_iftype_iface_created=1
ap_iftype_cleanup_ok=1
```

This is compatible with an effective false value and is strong evidence for
the compiled default. It is also compatible with an effective true value if an
unobserved pre-trigger writer seeded cnss_utils. Because the committed evidence
does not distinguish those cases, it cannot prove the runtime value of
`hdd_ctx->config->mac_provision`.

## What this closes and what it does not

| Claim | Disposition |
|---|---|
| V3342 selected or launched the helper's macloader role | **refuted** |
| no opaque V3342 child seeded cnss_utils through outer sysfs/debugfs | **unproved** |
| V3342 effective `mac_provision` boolean was false | **strong prior; unproved** |
| the INI literally contains `enable_mac_provision=0` | **unproved** |
| the current H24 vendor file is byte-identical to V3342 | **unproved** |
| a future configuration can never enable MAC provisioning | **unproved; must fail closed on drift** |
| the supplied INI may be replaced with a home-grown one | **not authorized and not recommended** |

The feeder makes native init the delivery intermediary, not the author of the
13,343-byte Samsung configuration. That file also carries regulatory, country,
firmware-offload, and radio tuning policy. Replacing it merely to control one
boolean would turn a bounded dependency question into a large unreviewed WLAN
configuration change. The correct rule is **read existing bytes when exact
current identity is later required; do not replace them**.

## Consequence for Option C and session accounting

The H24 selected dependency inventory already has no `macloader` role. Its
thirteen one-role ablations therefore do not contain a macloader session. This
finding does not change the projected program from thirty sessions to
twenty-nine. It prevents an additional macloader qualification/ablation unit
from being appended to that projection solely because the INI text was not
archived.

The current Option C H0 design keeps macloader outside the H24-derived capsule,
but this audit alone does not justify a V3342-equivalent necessity claim. Any
future promotion must bind the exact configuration and prove whether a trusted
MAC producer is required. This does not retire `H0D01-H0D10`, qualify `G0`, or
change the current ablation order.

The next useful Option C documentation unit may therefore remain the already
declared `WP2-4` property observation schema. A stock firmware download is not
a prerequisite for that H0 work.

The matching source exposes a narrower effect observation than reading the
whole INI, but the post-result debugfs state is corroboration rather than a
proof-bearing timestamp. `cnss_utils_mac_show()` reads the same persistent
`priv->wlan_mac_addr.no_of_mac_addr_set` and address array used by
`cnss_utils_get_wlan_mac_address()`; the getter does not consume or clear that
state. A pre-trigger absent read followed by an unobserved writer and then a
successful driver start is therefore unsafe to compose into a false-value
proof.

The proof-bearing false signature is emitted at the getter itself.
Provisioned=`type 0` and derived=`type 1`; the exact line
`WLAN MAC address is not set, type 0` is printed only while the provisioned
count is zero at that invocation. The driver returns from the platform path at
that point and never performs the derived lookup. The bounded matrix is:

| cnss_utils provisioned MAC | bound lookup signature | exact driver outcome | exact-run conclusion |
|---|---|---|---|
| present and valid | any | exact `wlan0` up | `MAC_PROVISION_VALUE_UNRESOLVED` |
| proved absent | exact type-0 absence once, no type-1, same bound driver-init epoch | exact `wlan0` up | `MAC_PROVISION_FALSE_PROVED_EXACT_RUN` |
| proved absent | not required | exact `getting MAC address from platform driver failed` branch | `MAC_PROVISION_TRUE_PROVED_EXACT_RUN` |
| absent without the bound type-0 signature, unreadable, malformed, stale, mixed-run, or any other combination | any | any | `NO_PROOF_OBSERVER` |

The first row remains unresolved because a writer may have supplied or
overwritten the MAC under either boolean. The second row now depends on the
self-timestamping getter line, not on observation order inferred around an
untracked writer window. It requires exactly one type-0 line, zero type-1
lines, complete bounded kernel-log capture, and `wlan0` up from the same exact
driver initialization epoch. The third row binds the source-unique fatal
branch rather than inferring the boolean from a generic probe failure; the
debugfs absence is only corroboration there as well. Module/source, boot/run,
driver-init epoch, driver identity, debugfs file identity, parse completeness,
log completeness, and the exact outcome must all match; an empty string caused
by a read error is never “absent.”

Within one boot the provisioned count has no zero-clear path: the built-in
`CONFIG_CNSS_UTILS=y` exit routine is not a runtime reset. This supports only a
**non-reversion** invariant (present does not later become absent), not a
set-once invariant. The ordinary setter returns success without copying when a
count already exists, while the debugfs writer bypasses that guard and can
overwrite the count and bytes.

`WP2-4` may encode that matrix as an observation field for a future separately
reviewed execution. Doing so avoids making a standalone INI read a prerequisite
for the H0 schema, but it is not a current D0 action and grants no D0 or live
authority. More explicitly, WP2-4 grants no D0 authority and no live authority.
A future execution still needs its own exact tier, observer,
qualification, recovery, and approval. Matching stock-firmware extraction or
an exact current-generation INI read remains fallback evidence if the effect
observation cannot be made complete. Reading never authorizes replacing the
Samsung file.

## Source anchors

Public, committed evidence:

- `docs/archive/legacy/reports/NATIVE_INIT_V2092_MAC_FALSIFIER_TFTP_REDIRECT_2026-06-05.md:13-46`
- `docs/reports/NATIVE_INIT_V3342_SOFTAP_S3_FWSOURCE_IFTYPE_PROBE_SOURCE_BUILD_2026-06-28.md:1-32`
- `docs/reports/NATIVE_INIT_V3342_SOFTAP_S3_FWSOURCE_IFTYPE_PROBE_LIVE_2026-06-28.md:1-55,57-118`
- `workspace/public/src/scripts/revalidation/build_native_init_boot_v3341_softap_s3_iftype_probe.py:15,71,328-389`
- `workspace/public/src/scripts/revalidation/build_native_init_boot_v3342_softap_s3_fwsource_iftype_probe.py:15-28,327-379`
- `workspace/public/src/scripts/revalidation/build_native_init_boot_v2237_supplicant_terminate_poll.py:43-77`
- frozen helper at commit `3e7eed10...`:
  `a90_android_execns_probe.c:328-342,6788-6889,56266-56310,58094-58099,58316-58324,59040-59546,68554-68670`

Matching private source, read only:

- `arch/arm64/configs/r3q_kor_single_defconfig:2186`
- `drivers/net/wireless/qualcomm/wcn39xx/qcacld-3.0/core/pld/inc/pld_common.h:519-615`
- `drivers/net/wireless/cnss_utils/cnss_utils.c:265-365,477-603,625-657`
- `drivers/soc/qcom/icnss.c:3706-3729,3842-3885`
- `drivers/net/wireless/qualcomm/wcn39xx/qcacld-3.0/core/hdd/src/wlan_hdd_main.c:12120-12280,13911-14011`
- `drivers/net/wireless/qualcomm/wcn39xx/qcacld-3.0/core/hdd/src/wlan_hdd_driver_ops.c:453-505`

## Boundary and authority

This report read only the public A90 repository and the operator-staged named
A90 kernel source already used by the source-confirmation report. It did not
read any other private path. Device, `/dev`, USB, network, S22+, and S20+
contacts are zero. No INI, source, private evidence, or device state was
modified.

This is H0 research evidence only. It grants no D0, D1, F1, candidate,
installation, handoff, UFS-content, property, live-ablation, recovery, or INI
replacement authority. Option C remains research-only.
