# ML030 S22+ five-minute dwell and UFS link rehearsal

**H0 result.** Debian answered a fresh challenge on the same ARM64 VM boot,
301.000 seconds after the first response. One subsequent command brought up
QEMU's emulated UFS link. The proposed S22+ cold-init component builds for
the retained kernel. Integrated review found that a queued power command can
start after the component's deadline. **The physical candidate is blocked.**
ML028 remains the last physical result. [ML028 closure](S22PLUS_MAINLINE_ML028_RUN_2026-11-05.md)
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
to its nine source hashes and overlay bytes. The physical path has an open
finding. [Component producer](../../workspace/public/src/mainline/s22plus_ufs_link_h0/build_module.py).

## Why the phone was held

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
FYG8 cold-power requirements unmet. The present producer yields an H0 component
only. There is no ML030 AP, reviewed live owner, grant or transfer. A90 and
S20+ had no actions in this unit.

Private evidence is under
`workspace/private/outputs/s22plus-mainline-ml030-dwell-link-h0-20261105-1/`.
The principal records are `recheck-raw-1.json`, `power-source-1/result.json`,
`cold-phy-events-2/result.json`, `component-build-2/result.json`,
`module-guard-vm-1/serial.log`, `rpmh-contention-2/result.json` and
`rpmh-cache-negative-1/result.json`.
