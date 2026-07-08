# S22+ M32 Watchdog-Managed HS ACM Live Result (2026-07-09 KST)

## Verdict

LIVE CONSUMED. FAIL / NO ACM. ROLLBACK CLEAN.

The M32 candidate was flashed exactly once under the approved one-shot
exception. It left the original Download endpoint, but no M32 ACM endpoint
appeared. The operator reported bootloop during the observation window. The host
then saw an unexpected Odin/Download endpoint at ~35.6 seconds, and the helper
immediately rolled back with the pinned Magisk boot-only AP.

No active M32 authorization remains.

## Run

Helper:

`workspace/public/src/scripts/revalidation/s22plus_m32_wdt_hs_acm_live_gate.py`

Command:

```bash
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m32_wdt_hs_acm_live_gate.py \
  --live \
  --ack S22PLUS-M32-WDT-HS-ACM-LIVE-GATE
```

Run directory:

`workspace/private/runs/s22plus_m32_wdt_hs_acm_live_gate_20260708T170344Z`

Candidate:

```text
AP.tar.md5  b2dee88862cbbfa8e9da799978c10134a07f41e4d144c23b2db1d0b8e00adbd4
boot.img    8001809f9f0d7b2d6615bdec97843680a0c20721d679dde74a76bbe6d95bb9ca
/init       0595a0e932fa0ca7240192e2438d134ca8e4338a48e68a17edb8d9b023dc8f77
modules     2291dc1c72add131c42d0b4ed6649880c20316d0598e0a2af942cc774949062c
```

Rollback:

```text
Magisk boot-only AP d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56
```

## Timeline

Canonical `timeline.json` events:

```text
2026-07-08T17:03:55.880040Z live_session_start
2026-07-08T17:04:07.456478Z candidate_flash_start
2026-07-08T17:04:08.954573Z candidate_flash_done
2026-07-08T17:04:10.242773Z candidate_boot_ready
2026-07-08T17:04:46.034233Z unexpected_endpoint_rollback_flash_start
2026-07-08T17:04:46.034485Z rollback_flash_start
2026-07-08T17:04:47.383932Z rollback_flash_done
2026-07-08T17:04:47.384089Z unexpected_endpoint_rollback_flash_done
2026-07-08T17:05:32.615173Z rollback_boot_ready
2026-07-08T17:05:32.615319Z unexpected_endpoint_rollback_boot_ready
2026-07-08T17:05:32.942723Z live_session_end
```

Important elapsed points:

```text
candidate left original Download endpoint: 2026-07-08T17:04:10Z
ACM checks 0.000s..35.629s: []
unexpected Odin endpoint: elapsed_sec=35.629 device=/dev/bus/usb/002/055
```

## Evidence

Candidate flash succeeded:

```text
candidate_odin_rc=0
Upload Binaries
boot.img.lz4
(31%)
(62%)
(93%)
(100%)
Close Connection
post-candidate-disconnect_odin_absent=1
```

No ACM was observed:

```text
m32_transport_observe_001_acm_devices=[]
m32_transport_observe_002_acm_devices=[]
m32_transport_observe_003_acm_devices=[]
m32_transport_observe_004_acm_devices=[]
m32_transport_observe_005_acm_devices=[]
m32_transport_observe_006_acm_devices=[]
m32_transport_observe_007_acm_devices=[]
m32_transport_observe_008_acm_devices=[]
```

Failure condition:

```text
m32_result=unexpected_odin_before_window elapsed_sec=35.629 device=/dev/bus/usb/002/055
```

Operator observation:

```text
bootloop observed during M32 candidate window
```

Rollback succeeded:

```text
unexpected_endpoint_magisk_boot_rollback_odin_rc=0
Upload Binaries
boot.img.lz4
(31%)
(62%)
(93%)
(100%)
Close Connection
```

Final Android/Magisk baseline:

```text
sys.boot_completed=1
init.svc.bootanim=stopped
ro.boot.verifiedbootstate=orange
su_id=uid=0(root) gid=0(root) groups=0(root) context=u:r:magisk:s0
boot_sha256=2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
```

Retained evidence:

```text
post_m32_unexpected_endpoint_rollback_pstore_files=[]
post_m32_unexpected_endpoint_rollback_last_kmsg_bytes=2097136
post_m32_unexpected_endpoint_rollback_last_kmsg_marker_found=0
post_m32_unexpected_endpoint_rollback_retained_marker_found=0
```

## Interpretation

M31B showed that loading `smem -> minidump -> qcom-scm -> qcom_wdt_core ->
gh_virt_wdt` removes the prior un-managed watchdog park ceiling. M32 preserved
that watchdog closure, then added the dependency-complete HS-only USB/ACM stack
while keeping QMP/EUD excluded.

The result means the failure is no longer explained by simply starving the
watchdog, but the full HS ACM add-back still does not create a usable ACM path.
It returned to Download/loop around ~35 seconds without a single host-visible
M32 ACM endpoint.

Likely next host-only direction:

- Split the M32-added closure into smaller watchdog-managed prefixes rather than
  replaying all 45 modules at once.
- Compare M31B vs M32 at the exact added module boundary; highest-value split is
  providers before DWC3/function binding, then `dwc3-msm`, then `usb_f_ss_acm`.
- Consider a link-only or marker-only USB substrate that avoids the full ACM
  configfs path until the module boundary is localized.

## Policy

`AGENTS.md` now marks the M32 one-shot exception consumed/retired and omits the
live ack tokens as active authorization. Do not repeat M32 under the consumed
gate. Any next live candidate needs a fresh narrow exception, exact SHA pins,
and a fail-closed helper.
