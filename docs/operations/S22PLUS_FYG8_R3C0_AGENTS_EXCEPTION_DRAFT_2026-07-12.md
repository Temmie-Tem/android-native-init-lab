# S22+ FYG8 R3C0 AGENTS Exception Draft

State: `RETIRED_AFTER_PASS`

This is the historical pre-live policy source. The exact approved helper ran
once, R3C0 passed with verified Magisk rollback, and the binding exception is
retired. This document does not authorize another device write.

## Proposed Narrow Exception

After independent source review, the consumed exception authorized one
bounded attended `S22+ FYG8 R3C0 synthetic carrier boot-only live gate` on
Samsung S22+ `SM-S906N` / `g0q` / `S906NKSS7FYG8`, using only checked helper
`workspace/public/src/scripts/revalidation/s22plus_fyg8_r3c0_live_gate.py`
SHA256
`921800725fa73b7d37fd8d3c46369d0015ab4a8e366111e079b5f7ce674246e3`.
The consumed active clause contained sentinel
`S22PLUS_FYG8_R3C0_POLICY_STATE=ACTIVE`. The live acknowledgement would be
`S22PLUS-FYG8-R3C0-SYNTHETIC-CARRIER-LIVE`; an interrupted already-started run
requiring rollback from an attended Download endpoint would use
`S22PLUS-FYG8-R3C0-MAGISK-ROLLBACK-FROM-DOWNLOAD`.

Before any candidate transfer, the helper must pass the exact R3 static checker
SHA256
`917b12f82dc5525b84cf2627379a80e49d921b6c33ca79fe3fc5c6a9ece6a514`
with verdict `PASS_R3C0_STATIC_CONTRACT`, verify full FYG8 stock-firmware
evidence through that checker, and verify the exact artifacts below:

- candidate raw boot SHA256
  `384efeb0f81534cbfaf3643f42e34fb6e01fe6f0b6bf80139a047a1f9a71f29f`,
  size `100663296`;
- candidate boot-only AP SHA256
  `8f2b16d3ee8932ff927e06fee8956f975ec3f9e5cc0ef16337e00ad5108d3c00`,
  containing exactly `boot.img.lz4`;
- candidate manifest SHA256
  `febffce465ea639d4d4751170bf280ae148ca3431f560aae6ecd8ea08f12ced0`;
- Magisk boot-only rollback AP SHA256
  `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`;
- cleanup-only stock boot AP SHA256
  `2f6a8ac093587a0f03c423d8e21f65c6fe3a8d2ce9915297170cdaa2cac37c94`;
- Odin 4 SHA256
  `6754aa54f2abe6e99ece32414cd34c8b23b28dbddde537a33203036813637c3b`,
  size `3746744`.

Live preflight must prove exactly one normal Android ADB target, exact target
identity, FYG8 incremental, completed boot with stopped boot animation, orange
verified-boot state, Magisk `uid=0(root)`, known Magisk boot SHA256
`2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`,
stock DTBO SHA256
`97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c`,
and stock recovery SHA256
`93fac06ca79bf4b365b25a8d49902bc41aba112ea253c30880c90e314d7895d4`.

The helper may request Download mode from that exact Android target and flash
the exact candidate AP once to boot only. Candidate flash start consumes the
future exception regardless of result. A candidate PASS milestone requires one
authorized ADB target, exact model/device/bootloader/incremental, completed boot,
stopped boot animation, exact kernel release and `/proc/version`, recorded
orange verified-boot state, and three bounded stable samples. Root is not a
candidate requirement. If no valid candidate milestone appears, the result is
no-proof and rollback remains mandatory.

After candidate observation, the helper must restore the exact Magisk boot AP.
If candidate Android exposes ADB, it may request Download mode; otherwise the
operator physically enters Download mode. If the Magisk transfer fails while
exactly one Odin endpoint remains, only the exact stock boot AP above may be
used as cleanup. Final PASS requires normal Android, Magisk root, exact Magisk
boot, stock DTBO and recovery identities, and no Odin endpoint. A candidate
milestone without verified Magisk rollback is not PASS.

The run is one-shot in code as well as policy. Before live entry the helper
must reject an existing
`workspace/private/state/s22plus_fyg8_r3c0_live_exception_consumed.json`, then
durably create it at `candidate_flash_start` before invoking Odin. That state
blocks later candidate runs but does not block the emergency rollback-only
entrypoint. The active `AGENTS.md` clause must still be retired after the run.

The helper must write `timeline.json` only as
`events:[{name,timestamp_utc}]` with exactly one occurrence, in order, of
`live_session_start`, `candidate_flash_start`, `candidate_flash_done`,
`candidate_boot_ready`, `rollback_flash_start`, `rollback_flash_done`,
`rollback_boot_ready`, and `live_session_end`. If no candidate milestone is
reached, `candidate_boot_ready` is only the bounded observation close and must
carry explicit no-proof semantics in `result.json`.

This consumed exception authorized no R3C1 artifact or transfer, native PID1,
Debian transition, partition-table action, raw host `dd`, fastboot, Magisk
module, panic, SysRq, RDX/S-Boot command, RAM dump, EUD/UART write, format data,
or write to recovery, vendor_boot, DTBO, vbmeta, BL, CP, CSC, super, userdata,
persist, EFS, sec_efs, RPMB, keymaster, modem, bootloader, or any partition other
than boot. It granted no A90 action. The binding state is now
`S22PLUS_FYG8_R3C0_POLICY_STATE=RETIRED`; the ACTIVE state must not be restored.
See `docs/reports/S22PLUS_FYG8_R3C0_LIVE_RESULT_2026-07-12.md`.
