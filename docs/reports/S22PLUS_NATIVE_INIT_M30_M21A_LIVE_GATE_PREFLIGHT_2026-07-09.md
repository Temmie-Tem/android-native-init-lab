# S22+ M30/M21A Raw Nanosleep-Download Live Gate Preflight (2026-07-09 KST)

## Verdict

PREFLIGHT PASS / POLICY ACTIVE / LIVE NOT EXECUTED.

Codex promoted a fresh one-shot `AGENTS.md` exception for the M30/M21A
floor-reanchor run and verified the checked helper in both host-only
`--offline-check` mode and non-flashing Android dry-run mode. No reboot, Odin
flash, partition write, or rollback was performed in this preflight.

The live candidate is intentionally small:

```text
raw PID1 -> nanosleep(90s) -> reboot(..., "download") -> park if reboot returns
```

It exists to answer the floor question M29 left open: can direct native `/init`
execute one raw syscall, remain in a time-distinct state, and self-enter
Download mode without module loading, filesystem setup, kmsg writes, configfs,
or Android handoff?

## Active Policy Scope

Active helper:

```text
workspace/public/src/scripts/revalidation/s22plus_m21a_raw_nanosleep_download_live_gate.py
```

Live ack token:

```text
S22PLUS-M21A-RAW-NANOSLEEP-DOWNLOAD-LIVE-GATE
```

Rollback-only ack token:

```text
S22PLUS-M21A-ROLLBACK-FROM-DOWNLOAD
```

Candidate hashes:

```text
AP.tar.md5        d1949a56c60c71498d68753d2ffd6064719fafce1ad0e3959ebb8a4255bb6c79
boot.img          61d7dc9818b79c810b30370edfe4df2b55ec451588defb48458fefae9c6c00a5
/init             10f525760b170cba4ec55d7fd4955c466601253258371cb571eb45515bd9cf30
source            300ed990c8ea476c3744e18327ae08277c0d27dc443e99245aeecba457968c4f
base Magisk boot  2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
kernel            bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff
```

Rollback AP hashes:

```text
Magisk boot rollback  d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56
stock boot fallback   1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e
```

The APs are single-member `boot.img.lz4` packages. No DTBO, vendor_boot,
recovery, vbmeta, BL, CP, CSC, super, userdata, EFS, RPMB, keymaster, modem, or
bootloader payload is authorized.

## Offline Check

Command:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m21a_raw_nanosleep_download_live_gate.py \
  --offline-check
```

Result:

```text
offline-check ok: M21A candidate and rollback APs verified; no device action
```

Run log:

```text
workspace/private/runs/s22plus_m21a_raw_nanosleep_download_live_gate_20260708T153303Z/
```

## Android Dry-Run

Command:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m21a_raw_nanosleep_download_live_gate.py \
  --serial <S22_SERIAL_REDACTED>
```

Result:

```text
dry-run ok: M21A candidate, rollback APs, AGENTS exception, current boot hash,
Android preflight, and dwell policy verified
```

Run log:

```text
workspace/private/runs/s22plus_m21a_raw_nanosleep_download_live_gate_20260708T153311Z/
```

Android baseline observed by the helper:

```text
model=SM-S906N
device=g0q
bootloader=S906NKSS7FYG8
incremental=S906NKSS7FYG8
vbstate=orange
boot_recovery=0
boot_completed=1
su_id=uid=0(root) gid=0(root) groups=0(root) context=u:r:magisk:s0
current_boot_hash=2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
```

## Live Interpretation

PASS requires all of:

- Original Odin endpoint disconnects after candidate flash.
- No operator key intervention before helper decision.
- No Odin endpoint before the 90 second dwell threshold.
- Host-observed Download mode appears only after dwell and within grace.
- Rollback restores Android/Magisk baseline.

NO PROOF / FAIL:

- Odin appears before dwell.
- Android returns unexpectedly.
- Device visibly loops before dwell.
- No Download appears after dwell plus grace.
- Operator enters Download manually before helper asks for rollback.

## Next

The next action can be the live gate, but only with the explicit live ack token:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m21a_raw_nanosleep_download_live_gate.py \
  --serial <S22_SERIAL_REDACTED> \
  --live \
  --ack S22PLUS-M21A-RAW-NANOSLEEP-DOWNLOAD-LIVE-GATE
```

During the live run, do not manually press Download/Recovery keys until the
helper reaches the dwell+grace decision or explicitly asks for manual rollback.
