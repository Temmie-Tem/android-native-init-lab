# S22+ Native-Init M31 Post-M30 Short-Dwell Design (2026-07-09)

## Verdict

HOST-ONLY POSTMORTEM / DESIGN ONLY. No build, flash, reboot, Odin action, or
device write was run in this unit.

Superseded on 2026-07-09 by
`S22PLUS_PMIC_PON_ABNORMAL_RESET_IS_THE_WALL_2026-07-09.md`. The short-dwell
download discriminator remains a possible narrow measurement, but it is no
longer the primary next step. The stronger current direction is to prove or
disprove the PMIC/PON watchdog-ceiling model by managing the stock watchdog
modules first.

The M30/M21A photo closes the main ambiguity in the previous result: the
candidate did not present a clean timed Download endpoint. The observed device
state was Samsung RDX with `PMIC abnormal reset`.

That means the next discriminator must not repeat a 75-90 second sleep. On this
device, earlier native-init work has repeatedly shown an about-30-second reset
shape when bare PID1 fails to make normal boot progress. A 90 second dwell is
therefore too long to distinguish "reboot(download) maps badly" from "PID1 was
reset before it reached the reboot syscall."

## New Evidence From M30

Operator photo artifact:

```text
workspace/private/runs/s22plus_m21a_raw_nanosleep_download_live_result_20260708T154424Z/operator_photo_phic_abnormal_reset.png
SHA256 7c03abfeecd36619c2939392467747487d231987c6c173ced5b337d6a9ab942e
```

Visible screen text:

```text
RDX (without Token)
PMIC abnormal reset
... print_summary_to_lcd...
pMic init.. Done for RDX
[To PC] Connect a USB cable or
[RDX AGAIN] Press VOL_UP + POWERKEY 3 sec
[RDX EXIT] Press VOL_DOWN + POWERKEY 3 sec
```

Host facts from the same run:

```text
m21a_download_seen=0
m21a_result=no-download-after-dwell-grace
host ADB/Odin snapshots through elapsed 119.525s: empty
post-rollback /proc/last_kmsg: 2097136 bytes
S22_NATIVE=0
M21A=0
operator_photo_PMIC_abnormal_reset=1
RDX=16
abnormal=32
watchdog=72
```

Final baseline after rollback remained clean:

```text
Android boot complete
verified boot state orange
Magisk root available
boot SHA256        2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
dtbo SHA256        97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c
vendor_boot SHA256 096e433e049fb088cd956e083d5a1039b33cdf0ca907e713bba7feaaf1b080b7
```

## Reclassified Prior Evidence

M4T2 remains the strongest positive floor proof.

- Raw AArch64 `/init` replaced PID1.
- It had no libc, filesystem setup, marker, modules, configfs, USB, or reboot
  path.
- It immediately entered an infinite `wfe; b` park.
- The operator observed the device park rather than fast-loop.

M4T3 and M20A are not hard proof of raw self-Download.

- Both used a raw first-action `reboot(..., "download")` shape.
- Later Odin visibility was observed by the helper.
- Operator-visible loop/manual intervention contaminated the inference,
  especially after M20A.
- They remain useful evidence that the raw reboot path may transition the device
  toward a recoverable mode, but not enough to prove instruction-level success.

M25/M30 strengthen the watchdog/boot-progress hypothesis.

- M25 returned through Odin/Download about 30.3 seconds after boot flash even
  though the candidate had no `download` string and no reboot syscall.
- M30/M21A slept for 90 seconds, produced no host transport, and then surfaced
  as `PMIC abnormal reset`.
- Together, these results make a long bare-PID1 dwell a poor proof separator.

## Current Failure Tree

M30/M21A narrows the fault to these cases:

1. Raw PID1 reached `nanosleep(90s)`, but the platform reset it for lack of boot
   progress before the sleep completed.
2. Raw PID1 reached `reboot(..., "download")`, but Samsung's early direct-PID1
   reboot target mapped to PMIC/RDX abnormal reset rather than normal Odin
   Download.
3. Raw PID1 never reached the intended instruction sequence after kernel handoff
   in this specific boot construction, despite M4T2 suggesting the floor can
   execute.
4. A retained evidence channel is still missing, so the host sees only rollback
   and Android-side retained logs.

The photo mainly rejects a clean case:

```text
90s sleep completed -> raw reboot(download) succeeded -> Odin appeared
```

It does not by itself distinguish cases 1, 2, and 3.

## M31 Direction

The next host-only candidate family should use a short dwell ladder below the
observed watchdog/boot-progress window.

Preferred shape:

```text
M31A_RAW_SHORT_DWELL_DOWNLOAD

_start:
  raw nanosleep(5s or 10s; first live candidate chooses one)
  raw reboot(LINUX_REBOOT_MAGIC1, LINUX_REBOOT_MAGIC2,
             LINUX_REBOOT_CMD_RESTART2, "download")
  infinite wfe park if the syscall returns
```

Candidate selection:

- Start with one short dwell, not a large batch in the first live gate.
- Prefer 10 seconds: long enough for operator/host time separation, still well
  below the about-30-second reset shape.
- If 10 seconds returns clean Download, build a later 20 second candidate to
  bracket the watchdog window.
- If 10 seconds still lands in PMIC/RDX or no transport, treat raw
  `reboot(download)` as suspect and stop the download-beacon line.

## Interpretation Policy For A Future M31A Live Gate

PASS:

- candidate flash succeeds;
- original Odin endpoint disconnects;
- no operator key intervention occurs;
- Odin Download appears after the short dwell and before the 30 second
  watchdog-like window;
- rollback restores the pinned Magisk boot baseline.

FAIL / REBOOT PATH SUSPECT:

- PMIC/RDX appears before or around the expected short dwell;
- no Odin endpoint appears before the 30 second watchdog-like window;
- host sees repeated bootloop behavior;
- retained evidence still lacks any candidate marker.

RECOVERY ONLY / NO PROOF:

- operator manually enters Download before the helper declares timeout or asks
  for rollback;
- the host only sees a later endpoint that could be manual Download.

## Guardrails

No active S22+ native-init live authorization exists after M30/M21A. M31A must
remain host-only until all of the following exist:

- source and build manifest for the exact short-dwell candidate;
- AP.tar.md5 SHA256, contained boot.img SHA256, and raw `/init` SHA256;
- helper with canonical `timeline.json` events;
- explicit fail-closed `AGENTS.md` authorization for one SHA-pinned candidate;
- dry-run proof against the current Android/Magisk baseline;
- rollback proof using the pinned Magisk boot AP, with stock boot fallback.

Do not add modules, configfs, USB, Android handoff, watchdog pokes, or broad
observability changes to M31A. This unit exists only to separate short-dwell
raw `reboot(download)` behavior from the long-dwell PMIC/watchdog reset shape.
