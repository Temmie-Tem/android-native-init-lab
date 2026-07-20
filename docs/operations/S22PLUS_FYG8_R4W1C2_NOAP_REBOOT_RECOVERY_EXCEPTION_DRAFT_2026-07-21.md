BEGIN_S22PLUS_FYG8_R4W1C2_NOAP_REBOOT_RECOVERY_POLICY_V1
**Pending one-shot exception (S22+ FYG8 R4W1-C2 stock-intent no-AP reboot
recovery):** this clause applies only to the already consumed R4W1-C2 incident
at
`workspace/private/runs/s22plus-r4w1c2-measured-live-20260720T164444Z` on
Samsung S22+ `SM-S906N` / `g0q` / `S906NKSS7FYG8`. The exact policy state is
`S22PLUS_FYG8_R4W1C2_NOAP_REBOOT_RECOVERY_POLICY_STATE=ACTIVE`.

The only executable helper is
`workspace/public/src/scripts/revalidation/s22plus_fyg8_r4w1c2_noap_reboot_recovery.py`,
size `41971`, SHA256
`98bd04ae429ad44d841b7794c61243aab9744204be1367b963b7db99e1147543`.
Its focused test is
`tests/test_s22plus_fyg8_r4w1c2_noap_reboot_recovery.py`, size `17301`, SHA256
`233e0fefdef59ff87d81be575bb128e82d41ee04ec510df78b28d84345fa86d2`.
The fresh live acknowledgement is
`S22PLUS-FYG8-R4W1C2-NOAP-REBOOT-RECOVERY-LIVE`.
The helper must require that the policy block installed in `AGENTS.md` is
byte-for-byte equal to this complete draft, apart from the containing file's
following newline. Substring presence is not sufficient.

Before device contact and again immediately before one-shot consumption, the
helper must pin the complete runtime dependency graph:

- measured helper size `111396`, SHA256
  `22cba55a924e9c56e5d245114357921ebefc73460a673e40e22c7ecf2e145172`;
- connected helper size `54734`, SHA256
  `fa4e9b0a77032fbb8b17affb2ae985b80c990b6e4b07c0ee095328cfd80516b9`;
- Odin transition core size `58423`, SHA256
  `c9abb179158bb45039574465e743f1f5bee18f993cbddd2f0b40e9048d1ca6b3`;
- boot-only live core size `12524`, SHA256
  `9bcade2532e77d538112836ebe9903bab832c1f2250151d3635260b6fd013725`;
- USBFS identity observer size `18998`, SHA256
  `2d1310e129670e89862826bcacc3886820c60f2691f342720927e8e13bddfe10`;
- transport helper size `35401`, SHA256
  `f10a30735882bbd59453471fe901b1cef11fdf42bcf3560a8ae61b4af361c4f4`;
- birth-time `stat` executable size `11352352`, SHA256
  `48893b0fb21436b54619db80486e83ef39dfccaf1aefe83dfa00c02d6146e8c0`;
  and
- Odin executable size `3746744`, SHA256
  `6754aa54f2abe6e99ece32414cd34c8b23b28dbddde537a33203036813637c3b`.

Before device contact, the helper must rerun its host-only incident gate and
require all of the following exact evidence:

- consumed state size `2680`, SHA256
  `64d15cb2fab8dc7ea5ca0b569832cc15c32c7623e05cfbe6a60924cbf02ec477`;
- original live result size `108695`, SHA256
  `74aa8f0a03b033299b2af5a6c97d9cba819ce671b04666549be3da45b38d9728`;
- recovery-attempt-01 result size `190297`, SHA256
  `aabf8323dd4d78451c3378f968a2bb1900625a6705cba2122cb261b9aaab5456`;
- stock-cleanup intent size `1290`, SHA256
  `50d48adc1ad9710628d5282978ca8f984e2d1478192ccec2b75185628363f23c`;
- candidate, Magisk, and stock Odin logs SHA256
  `84523c1d488f51c936a1d62fa832b0640e30f92d8544cb5c41e1dc70cfbc4757`,
  `12eef1ec931c2052196ca64d5930a23fc25cbfceb19530565b36eefadeadcc1d`,
  and `175794cbe076165a41e171e6c5af8defb4c36158e651926af1871c44f810585d`;
- transaction index size `6971`, SHA256
  `2811364fada46d840e8787f8947491688df1f3065d6be75e670b0a923561e97b`;
- recovery timeline size `536`, SHA256
  `48226674518c975f3d9d866834222e6f4217593cffb25b0e6700d6308c7df239`;
- each of the three different AP attempts returned rc `1`, stdout size `51`,
  stdout SHA256
  `7f6162459d49213e9d36485eaa1e7748492b484f4538db45ef50ab4d9f31adb4`,
  empty stderr, and no completed rollback-transfer receipt; and
- that stdout digest must equal the exact bytes
  `Reboot into normal mode\nFail parse /proc/self/fd/7\n`, which contains no
  `Setup Connection` and therefore proves the sealed AP pathname failed parsing
  before the Odin device session or partition transfer began.

The exact Odin executable is `/usr/bin/odin4`, size `3746744`, SHA256
`6754aa54f2abe6e99ece32414cd34c8b23b28dbddde537a33203036813637c3b`.
It must be copied into a write-sealed executable memfd. No AP, BL, CP, CSC, UMS,
PIT, or partition payload may be opened, sealed, passed, or transferred.

Live entry requires the attending operator to keep the original handset on the
same cable, hub, and host port and to confirm that its screen remains normal
Samsung Download mode. Supplying the exact fresh acknowledgement is the
load-bearing attestation of those facts because Download exposes no serial and
same-handset continuity is not intrinsically host-verifiable. The consumed
state must preserve the acknowledgement and exact physical-continuity basis.
The helper must rediscover only topology `2-1.3`, exact
Samsung `04e8:685d`, product `SAMSUNG USB`, manufacturer `Samsung`, absent
Download serial, usbfs major/minor consistency, and three stable measured node
samples. It must execute one measured `odin4 -l`, bind the exact direct usbfs
node and immutable digest, and revalidate both immediately before action.

After the fresh acknowledgement and final host-only evidence recheck, but
before opening or observing any USB endpoint, the helper must durably and
exclusively create
`workspace/private/state/s22plus_fyg8_r4w1c2_noap_reboot_recovery_consumed.json`.
Creation consumes this recovery exception regardless of result. After final
endpoint revalidation, the helper must durably record the exact no-AP launch
attempt immediately before process creation. This action receipt is the only
permitted durable write between final revalidation and launch.

The only authorized device command shape is the sealed equivalent of:

`/usr/bin/odin4 --reboot -d /dev/bus/usb/BBB/DDD`

The argv must contain exactly the executable, `--reboot`, `-d`, and the bound
device path. `-a`, `-b`, `-c`, `-s`, `-u`, `-e`, `-V`, `--redownload`, and every
other payload or mode option are forbidden. stdin must be `/dev/null`; with
standard fds excluded, only the sealed Odin fd may be inherited through
`pass_fds`. stdout and stderr are bounded together to at most exactly 1 MiB and
60 seconds, persisted durably before interpretation, and must show rc `0`, empty stderr,
the exact bound node, and the ordered no-AP reboot success lines. Any timeout,
output overflow, nonzero rc, stderr, missing line, endpoint change, or ambiguous
USB state is non-PASS and authorizes no retry.

Every invocation, including failure before USB discovery, must produce a result
and canonical eight-event timeline. The durable launch-attempt and process-
outcome receipts must truthfully distinguish no attempt, attempted but no
return, returned nonzero, timeout, exact-cap overflow, and returned success.
Failure results may not state `reboot=false`; they must use an unknown reboot
outcome unless exact Android readiness is proven.

PASS is only
`PASS_R4W1C2_NOAP_REBOOT_RECOVERY_EXACT_MAGISK_ANDROID`. It requires exact
Android serial return on the original USB topology, exact FYG8 model/device/
incremental, completed boot, stopped boot animation, orange state, Magisk
`uid=0(root)`, exact known Magisk boot, stock vendor_boot/DTBO/recovery, and no
Odin endpoint. The result must state `device_writes=false`,
`partition_write=false`, `odin_transfer=false`, `flash=false`, and
`reboot=true`.

Timeline output must contain only `events:[{name,timestamp_utc}]` with the exact
canonical eight names on PASS and failure. Candidate fields are explicit zero-
action placeholders; rollback-flash fields bracket or truthfully close the no-
AP reboot attempt and are explicitly no-flash semantics in the result.

This exception authorizes no second invocation, AP/pathname-alias experiment,
candidate, Magisk or stock transfer, flash, partition write, raw host `dd`,
fastboot, Heimdall flash, RDX/S-Boot command, qdl/Sahara/Firehose, EUD/UART
action, panic, SysRq, format, cleanup, or A90 action. It authorizes no write to
boot, recovery, vendor_boot, DTBO, vbmeta, BL, CP, CSC, super, userdata,
persist, EFS, sec_efs, RPMB, keymaster, modem, bootloader, or any other
partition. The clause must be retired after the bounded invocation and may
never be reused.
END_S22PLUS_FYG8_R4W1C2_NOAP_REBOOT_RECOVERY_POLICY_V1
