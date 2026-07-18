# S22+ FYG8 R4W1-B Connected-Only Binding Clause Draft

Date: 2026-07-19 KST

State: `DRAFT_INACTIVE`

Scope: exact proposed `AGENTS.md` clause for one connected read-only
qualification. This file is inert. It grants no device contact, and its text
must be independently reviewed before the block below is copied into
`AGENTS.md` in a separate commit.

The one-shot live policy remains inactive. This connected clause cannot request
Download mode, create the consumed state, transfer a candidate, run rollback,
or flash.

## Exact Proposed Clause

```text
**Pending exception (2026-07-19, S22+ FYG8 R4W1-B connected read-only
qualification):** after exact host source commit `c744abb3` passed an
independent delta review with verdict
`GO_TO_SEPARATE_CONNECTED_POLICY_BINDING_REVIEW`, Codex may perform one bounded
connected read-only qualification on Samsung S22+ `SM-S906N` / `g0q` /
`S906NKSS7FYG8` only after the attending operator supplies the exact fresh
acknowledgement below. Policy marker:
`S22+ FYG8 R4W1-B direct-PID1 retained witness boot-only live gate`.

`S22PLUS_FYG8_R4W1B_CONNECTED_POLICY_STATE=ACTIVE`

The only executable helper is
`workspace/public/src/scripts/revalidation/s22plus_fyg8_r4w1b_live_gate.py`
SHA256
`734693c456d482e6a09360129ba74e9123017b5c42829518a23870d07465a95d`.
Its focused test SHA256 is
`87de80150d1962c5804471a8037657144a4c394cd8cba5c596947c0723be42c1`.
The reusable core is
`workspace/public/src/scripts/revalidation/s22plus_boot_only_live_core.py`
SHA256
`9bcade2532e77d538112836ebe9903bab832c1f2250151d3635260b6fd013725`;
its focused test SHA256 is
`b55db8579115ec437e7fe63b6a3b6ecef0d8cbcac54110599e85f310f3b2fd9d`.
The reviewed inactive full exception draft SHA256 is
`a757eb46d5adb9e77e42fc6290656f9b56e1d6c33ec5e0cba6930bcf8fb557e2`.

Before device contact, the helper must rerun its complete offline artifact gate
and fresh deterministic static checker. It must require candidate raw boot
SHA256
`69690e6832bab2a422979054b51ad279222c14cbc369517433b55a785ed3d44d`,
size `100663296`; candidate LZ4 SHA256
`be2265ae72c584553945a82cdabc1ce36cc59cf6ee065c9675b97df9fc209c9a`,
size `27055052`; candidate boot-only AP SHA256
`ae26340d69f7208ae3a8c0d135e3f65317b4d16b539d4e19c1613b7f15f0f2c5`,
size `27064361`; manifest SHA256
`46c29171bfe640fb81b4dc36b8f342364c73055274145f413f29e0c8e36c65b0`,
size `4150`; and static result SHA256
`969b4a5d94660fb07abba95fe2386cb9327c2a0e97167e153a895619c4385d47`,
size `30004`, schema
`s22plus_fyg8_r4w1b_candidate_static_checker_v1`, verdict
`PASS_R4W1B_CANDIDATE_THREE_REPRO_STATIC_CONTRACT`, and empty blockers.

It must also require static-checker SHA256
`922b05eaffd1b17d33f69376564cbeab008c0e84b8cb2a34464aad8f5896d0b4`,
builder SHA256
`3d7b0cdcf5584c034589b713a85e15eb302932093b3721e8e65ee42242edf388`,
Magisk boot-only rollback AP SHA256
`d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`,
stock boot-only cleanup AP SHA256
`2f6a8ac093587a0f03c423d8e21f65c6fe3a8d2ce9915297170cdaa2cac37c94`,
full FYG8 stock firmware SHA256
`f831e5fb8abe1c7a9d8c38fe9c033a3fce7e77651776383641c385c2bb85a2c8`,
and Odin4 size `3746744`, SHA256
`6754aa54f2abe6e99ece32414cd34c8b23b28dbddde537a33203036813637c3b`.
The candidate and both rollback APs must each contain exactly one regular
`boot.img.lz4` member and no other member. These are qualification pins only;
this connected exception authorizes no transfer.

Fresh acknowledgement:
`S22PLUS-FYG8-R4W1B-CONNECTED-READ-ONLY-DRY-RUN`.
The live and recovery acknowledgement strings
`S22PLUS-FYG8-R4W1B-DIRECT-PID1-LIVE` and
`S22PLUS-FYG8-R4W1B-MAGISK-ROLLBACK-FROM-DOWNLOAD`, and the temporal string
`S22PLUS-FYG8-R4W1B-NORMAL-DOWNLOAD-CONFIRMED`, are identity pins only in this
stage and authorize no corresponding action.

Connected preflight must start from exactly one normal rooted FYG8 Android
target with completed boot, stopped boot animation, orange verified-boot state,
Magisk `uid=0(root)`, exact known Magisk boot SHA256
`2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`,
stock `vendor_boot` SHA256
`096e433e049fb088cd956e083d5a1039b33cdf0ca907e713bba7feaaf1b080b7`,
stock DTBO SHA256
`97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c`,
stock recovery SHA256
`93fac06ca79bf4b365b25a8d49902bc41aba112ea253c30880c90e314d7895d4`,
and no Odin endpoint.

It must prove live `sec_log_buf`, exact platform bind
`/sys/bus/platform/drivers/samsung,kernel_log_buf/8.samsung,kernel_log_buf`,
and absence of both `/sys/fs/pstore/console-ramoops` and
`/sys/fs/pstore/console-ramoops-0`. It must stream `/proc/ap_klog` once and
`/proc/last_kmsg` twice through true EOF with a `64 MiB` bound, rc=0, empty
stderr, and nonempty bytes. The two `last_kmsg` reads must be byte-identical.
Every observer must have no exact, foreign, malformed, unterminated,
delimiter-mismatched, or boundary-partial `[[S22R4W1B|` record. Historical
`[[S22R4W1|` records are a disjoint namespace: their count may be reported but
they neither contaminate nor satisfy R4W1-B.

The helper may write only a new host-side private run directory and one
exclusive host PASS record at
`workspace/private/state/s22plus_fyg8_r4w1b_connected_read_only_pass.json`.
PASS is only `PASS_R4W1B_CONNECTED_BASELINE_READ_ONLY` and must bind target,
exact helper/test/core/core-test identities, result path and result SHA256,
full observer receipts, pstore absence, `device_writes=false`, `reboot=false`,
`download_transition=false`, `odin_transfer=false`, and `flash=false`.

This connected-only exception does not activate the one-shot live policy and
authorizes no candidate run, consumed-state creation, reboot, Download
transition, Odin transfer, rollback transfer, flash, raw host `dd`, fastboot,
Magisk module, panic, SysRq, RDX/S-Boot command, RAM dump, qdl, Sahara,
Firehose, EUD/UART write, format, cleanup, or A90 action. It authorizes no write
to boot, recovery, vendor_boot, DTBO, vbmeta, BL, CP, CSC, super, userdata,
persist, EFS, sec_efs, RPMB, keymaster, modem, bootloader, or any partition.
Any mismatch fails closed before the host PASS record. A later live stage
requires a separate exact connected PASS, independent policy-binding review,
separate `AGENTS.md` commit, and fresh live approval.
```
