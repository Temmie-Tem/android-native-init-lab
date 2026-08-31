# S20+ G986N boot-slot recovery canary B0 H0 qualification

Date: 2026-08-31  
Target: `SM-G986N` / `y2q` / `y2qksx` / `G986NKSS8IYC2`  
Status: `PASS_GO_H0` for the fixed artifact closure only; live/F1 authority is false

## Decision

The proposed recovery-partition T0 is not eligible for execution. Independent
review returned `NO_GO` because the repository permanently permits ordinary
partition payloads only to `boot`, the recovery-only rollback path has not been
demonstrated live, and no reviewed live owner closes the proposed recovery
write. General operator consent cannot relax those boundaries.

The experiment was therefore reduced to a boot-only B0 carrier. It combines
the exact stock boot kernel, DTB, header, and image size with the already
qualified recovery-canary ramdisk. The recovery partition is neither read nor
written and no `recovery.img.lz4` member is present. The mandatory rollback is
the exact known-healthy resident Magisk boot AP already installed on the
device.

## Safety delta

The carrier builder makes one additional CPIO content edit: it inserts exactly
one `disabled` line into the fixed `service recovery /system/bin/recovery`
stanza. The source and output CPIOs contain the same 429 entries. All entry
metadata fields are unchanged; only `system/etc/init/hw/init.rc` grows from
6,427 to 6,440 bytes. A complete init/property search found no other recovery
service start, enable, or restart path.

This leaves the stock init PID 1, ueventd, the fixed recovery-banner root ADB
trigger, and `/init.s20plus_g986n_recovery_adb_canary` marker in place while
preventing the recovery binary from starting automatically. It therefore
reduces autonomous recovery-side BCB, log, and data effects without claiming
that the candidate will be accepted by the boot chain.

## Exact H0 closure

- builder: 27,216 bytes, SHA-256
  `3ef1eed83bf51e2725c0da62f31378d5505f89dc064fdd8e614bbfb02f7a131c`
- focused test: 10,246 bytes, SHA-256
  `804e4ebd2732e7787c2453073211ab2e3f6b6ac584e37ceff896024b2254a9a6`
- manifest: 8,090 bytes, SHA-256
  `a93b8175b1d20ab3ee53ec05420259e99d8434efd2ae8673fb635d928a9c1128`
- candidate AP: 36,198,441 bytes, SHA-256
  `a8ed52d314e3b0cf5820e99ecd55e97cacdbc8a943d2181886d52d42a1c177fa`
- candidate `boot.img.lz4`: 36,195,767 bytes, SHA-256
  `d06b3175dff1ebb0d9f47cc5f4e4787b6a2ee27fe2f740e2c048b586063a7f84`
- decoded candidate boot: 67,108,864 bytes, SHA-256
  `b42ba829a4a45728951f688b7b4ef07140686ce07f111a751bba948d1d934b4c`
- carrier ramdisk CPIO: 24,184,416 bytes, SHA-256
  `5924c2d34a62af356965cdcb40caade7e20969b7ddf03e7a2e5d3de6fc2a85f9`
- mandatory resident rollback AP: 25,835,561 bytes, SHA-256
  `1b33d098ea34b0396330cedf2e40c508704f1ba035b1f81e80a8526a637f1be2`
- decoded resident rollback boot: 67,108,864 bytes, SHA-256
  `d67d0af219d40d29f9e4d34da873e7aa33577d56fab68e2beccfe707418f7efc`

The candidate's embedded AVB signature remains structurally valid, but its
stock boot hash descriptor does not describe the modified ramdisk. Runtime
acceptance is therefore `UNKNOWN`, not proved.

## Validation and review

`python3 -m unittest -v
tests.test_s20plus_g986n_boot_recovery_canary_b0_h0` passed 10/10. Tests cover
exact common components, absence of recovery DTBO and recovery-partition
members, the sole service-disable delta, protected ADB/marker entries, archive
identity, rollback identity, reproducibility, hostile replacement, and the
explicit AVB/runtime-unknown boundary.

Independent exact-byte re-review returned `PASS_GO_H0` with high/medium/low
findings `0/0/0`. It independently parsed both newc archives and confirmed the
429-entry equality, the single content/size delta, zero metadata-field deltas,
and no alternate recovery start path.

## Remaining gate

No device command, ADB invocation, Odin invocation, reboot, or transfer was
performed by this unit. Before B0 can run, a separately reviewed and activated
exact boot-only F1 owner must bind the candidate, the mandatory resident
rollback, a short topology-bound recovery-ADB marker observation, intent-before-
effect journals, candidate and rollback no-replay, physical fallback, and
fresh resident-root terminal health. Only its connected prepare may emit the
fresh exact approval for one attended execution.
