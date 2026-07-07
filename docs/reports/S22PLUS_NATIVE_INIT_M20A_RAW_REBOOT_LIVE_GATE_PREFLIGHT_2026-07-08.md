# S22+ M20A Raw-Reboot Live Gate Preflight (2026-07-08)

## Verdict

PREFLIGHT PASS. No live flash was executed.

M20A is now the only authorized M20 live candidate. M20B, M20C, and wider M19
prefixes remain unauthorized.

## Candidate

Helper:

`workspace/public/src/scripts/revalidation/s22plus_m20a_raw_reboot_live_gate.py`

Live ack:

`S22PLUS-M20A-RAW-REBOOT-LIVE-GATE`

Rollback-only ack:

`S22PLUS-M20A-ROLLBACK-FROM-DOWNLOAD`

Candidate:

- Label: `M20A_RAW`
- AP.tar.md5 SHA256:
  `795e071107fdd7011a5acdc48ca7415273e5f2a3e19af45386702617292021fc`
- boot.img SHA256:
  `4fada63c986abc774e2a41eebc590f0635f1f1dcc8a207baa8d02cbfeb20eeb5`
- `/init` SHA256:
  `4b27b050b11a4f0f28f340172515a397f65e1d151507e149bc9cbe47c6beab17`
- Source SHA256:
  `ffce971408433acfb9bebb5bef236dab572fc8266d53a6c09e68419039f4abf1`
- Base boot SHA256:
  `2e541703951dc725bad35850faf7028c29967e`
- Kernel SHA256:
  `bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff`

Private AP path:

`workspace/private/outputs/s22plus_native_init/m20_floor_split_v0_1/M20A_RAW/odin4/AP.tar.md5`

## Scope

M20A is a direct raw-assembly PID1 candidate:

- first runtime action: raw arm64 `reboot(..., "download")`
- no libc startup
- no fs setup
- no `/dev/kmsg` marker write
- no module load
- no configfs/USB gadget/role force
- no Android/Magisk handoff
- no persistent partition mount or block write
- if the reboot syscall returns, park forever

Positive proof is narrow: host-observed Odin/download endpoint reappearance
after the original post-candidate Odin endpoint disconnects. A bootloop or
manual download-mode entry must not be counted as automatic self-download proof.

## Guarding

The helper verifies before live:

- exact SHA-pinned `AGENTS.md` M20A exception
- exact M20A AP hash and single `boot.img.lz4` tar member
- exact M20A manifest hashes and safety fields
- exact Magisk boot-only rollback AP SHA256
  `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`
- exact stock boot-only fallback AP SHA256
  `1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e`
- current Android identity and rooted Magisk baseline
- current boot SHA256
  `2e541703951dc725bad35850faf7028c29967e`

Rollback-only mode is available as:

```bash
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m20a_raw_reboot_live_gate.py \
  --rollback-from-download --ack S22PLUS-M20A-ROLLBACK-FROM-DOWNLOAD
```

## Validation

Commands:

```bash
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/s22plus_m20a_raw_reboot_live_gate.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m20a_raw_reboot_live_gate.py \
  --offline-check

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m20a_raw_reboot_live_gate.py
```

Results:

- `py_compile`: pass.
- `--offline-check`: pass; no device action.
- dry-run: pass; current Android/root/boot SHA baseline verified.

## Next

If live proceeds, run only M20A:

```bash
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m20a_raw_reboot_live_gate.py \
  --live --ack S22PLUS-M20A-RAW-REBOOT-LIVE-GATE
```

Do not run M20B/M20C until M20A is operator-clean under current timing.
