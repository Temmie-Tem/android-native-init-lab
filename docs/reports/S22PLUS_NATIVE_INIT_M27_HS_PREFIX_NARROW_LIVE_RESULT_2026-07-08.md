# S22+ Native-Init M27 HS Prefix-Narrow Live Result (2026-07-08)

## Verdict

M27 LIVE CONSUMED / P08 NOT A CLEAN HIT: the M27 batch was started, but it was
stopped after `P08`. Because the operator reported bootloop observation and
manual Download-mode entry before/while Odin appeared, the helper's automatic
`m27_P08_result=self-download` line is treated as manual-download contaminated
and must not be used as a clean checkpoint proof.

Operational conclusion: the fault is now narrowed below `P08`, between known
`P00` hit and operator-corrected `P08` no-hit/manual-download. Next unit should
bisect modules `1..8`, not proceed to `P12+`.

## Live Run

Command started:

```bash
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m27_hs_prefix_narrow_live_gate.py \
  --serial RFCT519XWGK \
  --live \
  --ack S22PLUS-M27-HS-PREFIX-NARROW-LIVE-GATE
```

Primary log:

```text
workspace/private/runs/s22plus_m27_hs_prefix_narrow_live_gate_20260708T134030Z/s22plus_m27_hs_prefix_narrow_live_gate.txt
```

DTBO restore log:

```text
workspace/private/runs/s22plus_m27_hs_prefix_narrow_live_gate_20260708T134404Z/s22plus_m27_hs_prefix_narrow_live_gate.txt
```

## Timeline

Primary run:

- `13:40:53Z`: M25 DTBO high-speed cap flash start.
- `13:40:54Z`: M25 DTBO high-speed cap flash done.
- `13:41:27Z`: Android boot ready under patched DTBO.
- `13:41:39Z`: `P08` boot candidate flash start.
- `13:41:40Z`: `P08` boot candidate flash done.
- `13:41:42Z` through `13:42:20Z`: host saw no ADB and no Odin.
- `13:42:21Z`: host saw Odin and helper logged `m27_P08_result=self-download`.
- Operator correction: the Odin appearance is contaminated by manual Download
  entry after bootloop observation, so it is not a clean candidate self-download.
- `13:42:21Z`: Magisk boot rollback flash start.
- `13:42:23Z`: Magisk boot rollback flash done.
- The helper was interrupted while polling Android to prevent the contaminated
  Odin event from advancing to later prefixes.

DTBO restore:

- `13:44:27Z`: stock DTBO rollback flash start.
- `13:44:28Z`: stock DTBO rollback flash done.
- `13:45:13Z`: Android boot ready and stock DTBO hash verified.

## Evidence

Primary run excerpts:

```text
m27_P08_self_download_seen=1 device=/dev/bus/usb/002/030
m27_P08_result=self-download
P08_magisk_boot_rollback_odin_rc=0
```

These lines are not sufficient as proof because the operator reported:

```text
부트루프 관측됨 다운로드 모드 수동진입
```

Host samples before the Odin appearance showed no transport:

```text
m27_P08_self_download_001..036: odin devices=[]; adb devices empty
```

DTBO restore evidence:

```text
stock_dtbo_rollback_odin_rc=0
stock_restore_dtbo_hash_rc=0
97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c  /dev/block/by-name/dtbo
```

## Final Baseline

Final host verification after restore:

- ADB device: `RFCT519XWGK`
- `boot_completed=1`
- `bootanim=stopped`
- verified boot state: `orange`
- Magisk root: `uid=0(root)`
- boot SHA256:
  `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`
- stock DTBO SHA256:
  `97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c`
- vendor_boot SHA256:
  `096e433e049fb088cd956e083d5a1039b33cdf0ca907e713bba7feaaf1b080b7`

## Next

Do not continue M27 to `P12+`; the first M27 point is already contaminated/no-hit.
Build a fresh host-only discriminator inside modules `1..8`, for example
`P01/P02/P04/P06/P07/P08`, with the same DTBO high-speed context and the same
prefix/download proof shape. The next live unit needs a fresh SHA-pinned
`AGENTS.md` exception and should make manual Download contamination explicit in
the runbook.
