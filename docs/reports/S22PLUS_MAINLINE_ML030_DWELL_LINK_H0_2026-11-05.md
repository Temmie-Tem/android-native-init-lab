# ML030 S22+ five-minute dwell and UFS link rehearsal

**H0 result.** The revised ARM64 kernel, fixed module, Debian witness, loader
and boot-only AP are built. A contended RPMh path could previously start a
power request after the deadline. The revised S22+ path tries one active slot,
keeps an ambiguous slot occupied, and binds a normal return to the authenticated
link result. ML028 remains the latest physical result. ML030 still requires
a separately adopted common/target scope and reviewed live owner. [ML028 closure](S22PLUS_MAINLINE_ML028_RUN_2026-11-05.md)
and [ML029 board study](S22PLUS_MAINLINE_ML029_UFS_H0_2026-11-05.md).

## Same-boot evidence

ML028's final device observation reported 49.300 seconds of uptime. Its
Download timeout did not measure time alive in Debian. For ML030 the operator
selected one boot with two observations and a link attempt only after the
second. The existing first-observation limit stays at 120 seconds. The host
waits at least 300 seconds from sealing the first response before generating
a new nonce. A single connection binds both nonces, the candidate, the boot ID
and both uptime samples. The guest measures PID 1, its observer, the FDT and
zero block devices again. A separately authenticated permit follows the
verified second response. The overall absolute VM window is 540 seconds.

| ARM64 VM case | Guest uptime, seconds | UIC commands | Result |
| --- | --- | ---: | --- |
| Correct late permit | 2.035 → 303.161 | 1 | Fresh command completion, result zero and device present |
| Early second challenge | 1.843 at first observation | 0 | Timeout before second receipt |
| Altered permit | 1.884 → 303.022 | 0 | Authentication failure before dispatch |

The positive trace contains one `DME_LINK_STARTUP` (0x16) and zero
SCSI executions. There were no emulated LUs or backing media. The first
emulated attempt stopped before the command because its expected PCI class
was wrong. A separate diagnostic measured `0x010901`, and a new fixture
passed the complete timed sequence. The failed fixture and raw captures
were retained. A second reader reverified the authenticated frames and
QEMU trace for all three cases. This measures the protocol and the QEMU
controller. The phone's five-minute survival and watchdog behavior remain
unmeasured. [VM producer and observer](../../workspace/public/src/mainline/s22plus_ufs_link_h0/dwell_vm.py).

## FYG8 cold initialization

The operator selected cold power, clock, device reset and PHY initialization
if needed, followed by one link attempt. SCSI and media commands are outside
this experiment. The FYG8 AOP configuration associates L9 with S12 and L7
with BOB. The empty L6 entry supplies no electrical-parent evidence. The
stock Linux driver sets a parent only for an explicit parent-supply or
vin-supply property, absent on these four resource declarations. The
proposed consumer uses existing USB L5 and separately registered L6, L7,
L9 and S12 resources. L9 has two consumer holds. S12's provider initial
vote is 1.256 V and its distinct UFS consumer requests load and enable.

All five Waipio tables compiled from the Samsung base header match the
corresponding symbols in the shipped FYG8 PHY module byte for byte.
Mainline's default tables differ at TX offsets on both lanes. The selected
v4 path uses the 80-entry Rate-A table, 48 second-lane entries and the
one-entry Rate-B override. The actual C trace issued 129 table writes.
The normal case, missing PCS readiness, unsupported hardware revision,
expired budget and failed reset readback took their expected paths.
[Table comparison](../../workspace/public/src/mainline/s22plus_ufs_link_h0/cold_phy_tables.py)
and [PHY component](../../workspace/public/src/mainline/s22plus_ufs_link_h0/waipio_phy.c).

The HCI code first checks that the v4 controller, request lists and
interrupt state permit a cold start. The reset pulse uses only the dedicated
GPIO 210 output with existing output direction verified. Calibration must
complete before HCE. After enabling HCE the code waits the FYG8 1 ms before
polling. Six fixed local UniPro commands cover TX state, the two timer
attributes and TX line coding. Differing stock/mainline timer writes on the
observed register value stop setup. Only a new link command completion with
result zero and a transition from device absent to present can pass. The
component has no registered SCSI host, transfer descriptors, ICE/key
operation or retry. Thirteen register-model cases exercise the actual HCI
code. They include old completion, busy queues, expiry immediately before the
opcode write, missing device and lost link. [HCI code](../../workspace/public/src/mainline/s22plus_ufs_link_h0/waipio_hci.c)
and [cases](../../tests/test_s22plus_ml030_cold_hci.py).

A late overlay adds the four-rail provider and one consumer. It makes the
existing PHY node available with a clock-only compatible so GCC can resolve
its three symbol parents. No generic UFS or PHY driver binds to that node.
The first module could not resolve those parents through a disabled node.
The revised module also checks VRM resource type, checks the reset direction,
uses the shipped reference and lane clock order, and latches its sole probe.
It compiled and linked against an isolated copy of the ML028 Kbuild state
with ARM64 vermagic and an empty compiler log. The module hash is
`ba364da0f4a93790370c8ef86c60c9fe054185e528aad7f94bb5f67111fc5c45`.
A separate VM boot submitted exactly these bytes through `finit_module` after
its five-minute witness. The module returned `ENODEV` on QEMU's virt board
before creating a platform device. All thirteen HCI cases also ran as ARM64
executables. Independent review matched the corrected integrated H0 module
to its nine source hashes and overlay bytes. At that stage the shared RPMh path had an open finding. [Component producer](../../workspace/public/src/mainline/s22plus_ufs_link_h0/build_module.py).

## Why the initial module was held

The component checks time before requesting a resource through Linux.
Inside the retained kernel, `rpmh_rsc_send_data()` can then wait indefinitely
for a free transfer command set (TCS) and subsequently trigger hardware.
The ten-second RPMh completion wait starts only after that submission returns.
In a host fixture, the **actual retained send function** received a request
inside a 15-second budget. With a free slot its trigger followed immediately.
With the slot held, it returned success and reached the instrumented trigger
**15.251 seconds after entry**, 0.251 seconds past the deadline. The fixture
uses a real timed wait and substitutes the slot and hardware interfaces.
[Reproducer](../../workspace/public/src/mainline/s22plus_ufs_link_h0/rpmh_wait.py).

Merely making the slot claim return busy also leaves a concrete cache issue.
The retained `__rpmh_write()` updates the wake cache before it calls the
RSC. A separate fixture started with valid sleep/wake values of 3, rejected
an active request for 9 with `-EBUSY`, and then ran the retained flush logic.
Its instrumented wake submission carried 9. The fixture establishes a
conditional software path. It does not establish the phone's cache contents.
The active batch path also frees its completions after timeout even though
its source notes that late signaling is possible.

The stock interfaces expose no per-request deadline to the four-rail module.
A shared-transport repair would need to cover slot admission, the actual
trigger, cached votes and completion lifetime without disturbing ordinary USB
and original-A return. Skipping the real regulator holds would leave the known
FYG8 cold-power requirements unmet. This initial producer yielded an H0 component. No AP or grant had been
prepared at that point. A90 and S20+ had no actions in either ML030 unit.

Private evidence is under
`workspace/private/outputs/s22plus-mainline-ml030-dwell-link-h0-20261105-1/`.
The principal records are `recheck-raw-1.json`, `power-source-1/result.json`,
`cold-phy-events-2/result.json`, `component-build-2/result.json`,
`module-guard-vm-1/serial.log`, `rpmh-contention-2/result.json` and
`rpmh-cache-negative-1/result.json`.

## Revised shared power transport and boot-only AP

The operator authorized H0 changes to the S22+ shared RPMh path and checks
of ordinary USB and Download return. The new path admits only the issuing
task after the late witness. It checks that all four named VRM windows are
unique in the mapped command database before entering the issuing context.
The scan checks header offsets and entry counts against the mapping extent.
At most 32 requests have separate completion storage lasting until reboot.
An uncertain posted payload, command enable or control write keeps its slot
occupied. A verified preparation can be reclaimed before trigger. A final
deadline check precedes trigger submission under the slot lock. Late hardware
completion may settle an issued request. The command history preserves the
distinction between claimed, triggered, acknowledged and reclaimed slots.
[Transport source](../../workspace/public/src/mainline/s22plus_ufs_link_h0/transport/authority.inc.c)
and [TCS writer](../../workspace/public/src/mainline/s22plus_ufs_link_h0/transport/rsc-send.inc.c).

The late module takes a runtime-PM reference only on an already active g0q
DWC3 device. Under the interconnect and voter locks it checks the existing
four-node apps-USB path, bandwidth, node/provider identity and completed
SH1/CN0 active votes. Wake/sleep fields describe cached requests. They do
not establish that firmware later executed those requests. Ordinary transfers,
completion IRQs and the existing reboot-mode driver retain their original
implementations. An independent reviewer verified the observer against the
retained DWC3/BCM source and the actual ARM64 build. Twelve TCS submission,
timing, quarantine and reuse cases passed on both host and ARM64. Additional
cases covered database alias/extent failures and lost, duplicate, stale or
failed bus-vote confirmations. [Host fixtures](../../tests/test_s22plus_ml030_transport.py).

The first transport kernel still carried the consumed ML028 marker in its
early entry. It was confined to VM work. The prospective kernel restores
the exact original entry and its loader omits the marker. On the new kernel,
the original ML028 VM archive completed its UID 1000 SSH command, rc6 stop
and normal guest reset. A wrong-boot command parked without reset. QEMU
uses a virtio network device for this check. The actual DWC3, PMIC and
Download arrival remain physical observations.

The new fixed RAM root contains the four qualified Debian packages and one
40,992-byte g0q module. After the second challenge the witness checks the
same boot, DT, PID 1, kernel release and observer, then validates a separate
permit. It checks the fixed module's ownership, type, mode, link count,
size and bytes on the descriptor passed to its sole finit_module call.
The signed reply preserves the syscall errno and bounded raw status, including
a partial sysfs read failure. The host must verify the fresh UIC completion,
device-present transition, resolved RPMh records and released USB reference
before deriving the normal Download command from the SHA-256 of the entire
signed reply. Link evidence, normal Download, rollback and Android health
are separate findings. [Receiver](../../workspace/public/src/mainline/s22plus_ufs_link_h0/link-runtime.h)
and [result checks](../../workspace/public/src/mainline/s22plus_ufs_link_h0/link_wire.py).

| Final H0 artifact | SHA-256 |
| --- | --- |
| Unmarked ARM64 Image | `19fc260fc880731167d3612804e34a0ea64c48efb1a46bdf7aee803d35a2bc3c` |
| ARM64 module | `7859073e9abfef8cb93202683046bec2878b3210c4703fc36eb6a1474a6615f8` |
| Physical-mode RAM archive | `3c829b6137b10745ad1b0a3d16c227d498f96dbf0ca4c1495058033244a04631` |
| uniLoader | `6be55da7a4d53f18ad6c9129f66bcf24843117662a16b54dcfc03f5ae0b979ed` |
| Boot-only AP, both independent packs | `44ea04f4f7a9aaa09e3ad4e86e5162c08eb6aaba6d4bf5b94632feb95d9d7aba` |

Both observer binaries and archives were reproduced byte for byte from the
sealed inputs. The loader passed 20 placement/entry cases and 1,051 aligned
copy cases. QEMU separately exercised actual EL1, EL2 and rejected EL3 entry.
The AP has a single boot.img.lz4 member and retains the verified original-A
outer boot envelope. Raw inputs, outputs and superseded builds remain in the
private ML030 directory identified above, including `transport-build-4`,
`transport-component-4`, `producer-check-5`, `loader-tests-5`,
`loader-entry-vm-5` and `package-5`.

### Final protocol cases and independent review

| ARM64 guest case | Result |
| --- | --- |
| Early challenge | Parked with ETIMEDOUT before a permit |
| Altered late permit | Parked with EACCES after 301.000 seconds, without dispatch |
| Real module on QEMU virt | After 301.000 seconds the fixed module returned ENODEV, the sealed result recorded zero report bytes and the guest parked |
| Modeled power, QEMU UFS, final-result-bound Download | Same boot at 1.594 and 302.737 seconds, one emulated link command, zero SCSI commands, one authenticated ACK and one guest reset |
| Same model with the original base nonce | Same boot at 1.641 and 302.771 seconds, one emulated link command, zero SCSI commands, EACCES and zero resets |

The last two cases use the real late protocol and reboot code with a QEMU UFS
controller and explicit fixture values for g0q power status. Only the
unmodified-module case exercises the real candidate module on QEMU. It
correctly rejects that board. A bounded sysfs read fixture also retained the
exact prefix and errno on short read, overflow and close failure. The selected
Python suite passed nine tests, including thirteen HCI scenarios. All four new
C fixtures were cross-built, checked as ARM64 ELFs and executed under QEMU.

The independent reviewer returned **PASS_GO for revision 5's prospective
guest and loader at H0**, with zero open H0 findings. Review covered rederived
raw frames and QMP events, the outer boot payload and ELF/CPIO joins.
`final-evidence-check-5.json` has SHA-256
`58ace1c8e7afc1ab43150282857e757996d5451816fc658240be3bbec93b1a5a`.
The current RAM validator rejects both new manifests. This H0 review covers
neither the future live owner nor a physical operation.

The [proposed common scope](../plans/S22PLUS_ML030_LINK_ONLY_SCOPE_2026-11-05.md)
was independently reviewed as a proposal. It limits the experiment to one
S22+ boot, the 300-second witness, fixed cold initialization, one link command
and an attended return. The current revision 64 exception names the eight
FYG8 stock drivers and V3 owner. The new AP has no live execution authority
from packaging, H0 review or ML028's consumed grant.

## Policy adoption on 2026-11-06

The operator approved incorporating the independently reviewed proposal into
common and S22+ target rules. Contract revision 65 adds that closed ML030
hardware delegation. The new policy pins the already-qualified Image,
module, RAM archive, loader and boot-only AP. It keeps the 1800-second
single-operation attended task, initial 120-second observation, five-minute
same-boot witness, 540-second late ceilings, 15-second module budget,
one link attempt, result-bound normal Download and original-A consumption.

Independent policy review returned PASS_GO with no open findings. Its
source-bound review covers the root, common details, target, risk tiers,
RAM cross-link, new policy and current goal. Review clarified that generic
driver disablement concerns the UFS-device binding/discovery path, while
common SCSI code may remain compiled in the retained kernel. The witness
verifies the module file before finit_module. No effect was added by either
clarification. The unchanged proposal remains the adopted reference.

The common details digest is
`eb28a7b006969e866b3a1625e7c0ab76ea0a01f8b1acc8eaecde5de3033a0068`.
Removing only the new ML030 clause reproduces the previous common details
byte for byte. Diff, links, anchors and the root digest passed focused checks.
The existing successful artifact and VM checks were reused because their
inputs were unchanged. The current owner still requires explicit ML030
implementation and review before an exact returned approval, fresh health
and attendance can authorize a device effect. Device actions in this policy
unit were zero. [Adopted policy](../operations/S22PLUS_MAINLINE_UFS_LINK_V1.md).

Private policy-review and checks are retained under
`workspace/private/outputs/s22plus-ml030-policy-adoption-h0-20261106-1/`.
