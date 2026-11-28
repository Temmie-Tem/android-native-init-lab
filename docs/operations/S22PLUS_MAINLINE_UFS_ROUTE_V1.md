# S22+ UFS V13 with the MAX77705 USB route

Status: **REVIEW_GATED_CAPABILITY** (code and contract review PASS_GO; the
capability record and candidate need their own owner review)

On 2026-11-27 the operator approved the common-contract delegation for this
scope ("그렇게 승인할게 진행해"). The approved summary listed four differing
inputs. The module turned out byte-identical, so the delegation lists three,
which is narrower. The code and contract are adopted (`c9c1b15ecb`); each
capability record and candidate still needs its own owner review.

This scope runs the adopted report-v13 late-UFS experiment
([capability V2](S22PLUS_MAINLINE_UFS_CAPABILITY_V2.md)) without a USB
replug. It adds the adopted Stage 2 MAX77705 route write
([route policy](S22PLUS_MAINLINE_MAX77705_ROUTE_V1.md)) to the V13 guest, so
that USB enumerates without physical action. The rest of V13 is unchanged.

## Why

ML051 and ML052 used V13 but never reached the module. Every mainline USB
first response since ML021 needed a physical replug:
- in ML051 the cue was refused as too late;
- in ML052 the replug worked, but the cue resolution was recorded after the
  window.

One gated `CONTROL1_W(COM_USB)` removed the replug in seven consecutive boots,
with the cable untouched. The seventh is
[route-timer run 6](../reports/S22PLUS_MAINLINE_MAX77705_ROUTE_TIMER_RUN6_2026-11-27.md).

## What differs from the adopted V13 capability

Only these three inputs differ. Each comes from an adopted artifact or the
adopted source with one stated change.

| Input | Adopted V13 | This scope |
| --- | --- | --- |
| Kernel Image | ML035 transport Image `c4f8d9b0…`, configuration `342fc571…` | `fb1fc155…`, configuration `881e450e…`: the same patched source and configuration with only `CONFIG_I2C_QCOM_GENI=y` (`m` before). No other configuration line changes. The exported symbol versions (`vmlinux.symvers` `fb83fba4…`) are byte-identical. |
| DT | Reduced no-display DT `f918d309…` | The same DT with QUP0 (`/soc@0/geniqup@9c0000`) and its SE5 I2C (`i2c@994000`) set to `okay`, and the SE5 `pinctrl-names` and `pinctrl-0` removed (`51b58a40…`). This is the DT of the adopted MAX77705 observation. TLMM and `gpi_dma0` stay disabled. |
| Guest observer | V13 observer | The V13 observer with the Stage 2 route observer's reads and gated write added, as described below. |

The fixed V13 module `5628f299…` is unchanged. Its rebuild from the V13
component inputs against the new kernel build is byte-identical, with the
same vermagic.

The four-package RAM userspace, the network template, the authenticated
protocol and response layout, the timer child and the producer toolchain are
unchanged.

## Guest composition

Both observers are built from the same canary `init.c`. The composition
applies the V13 insertions first:
- the result digest;
- the dwell and witness;
- the timer child arm before `G0Q_RAM_PID1_BEGIN`.

It then applies the route observer's three sampling insertions, unchanged:
- `mx_begin()` at `G0Q_RAM_PID1_BEGIN`, after the timer child is armed;
- `mx_tick()` every 200 ms while the gadget is bound and the first request is
  awaited, but only while at least one second of the 120-second window
  remains;
- the 200 ms bounded poll that replaces the single wait for the first
  connection.

The composition renders `max77705-usb-route.h` into the observer source. The
shared header file is unchanged. The rendered copy is the adopted header byte
for byte, plus two window checks:
- at the write's dispatch sample, before the payload is sent;
- directly before the mailbox start strobe, which is what starts the command.

Either check refuses on a failed clock read, or at or after the end of the
120-second window by the observer's clock. A payload without its strobe
starts nothing. Candidate reproduction compares the whole
generated source, including the rendered header. The gate and bus effects
are otherwise those of the adopted route observer:
- MAX77705 status reads, which clear the read-to-clear `UIC_INT` and `CC_INT`
  latches;
- `CONTROL1_R` mailbox commands with their mailbox start strobes;
- at most one `CONTROL1_W(COM_USB)` with its strobe, after the gadget is
  bound, only when VBUS, a CC sink, an SDP or CDP charger type and a fresh
  open switch read all hold. It is never retried.

The read commands and the write share one budget of 32 mailbox commands.

No register value is written to the PMIC or FSA4480.

The route record is not appended to the response. The V13 response layout,
its authentication and the host's V13 parser stay exactly as adopted. Two
facts evidence the route:
- an authenticated V13 first response, which requires the enumerated gadget;
- the operator's statement that the cable was not touched.

The write gate code is the adopted one. No record shows whether the write ran
in a given boot. That limitation is accepted, because this scope's question
is the UFS link result, not the route.

## No attach cue

This scope has no attach cue. The cue tool refuses this image. USB must
enumerate without physical action. If no authenticated first response
arrives in the original 120-second window, the run issues no module permit.
The V13 timer child then attempts Download, and the original
owner transfers original A through the existing automatic or attended path.
The existing V13 attach closure already accepts an unissued cue.

## Unchanged

Everything else in V13 is unchanged:
- the one link attempt;
- the late-hardware predicates and the held-USB SH1/CN0 confirmation;
- the 256-byte report envelope;
- the 120/300/540/15-second limits;
- the timer child and its 555-to-570-second Download slot;
- the N-launch-plus-660-second original-owner return;
- one N and one original A;
- no replay;
- the physical fallback, the health-only continuation and final rooted
  Android health.

## Hazards specific to the composition

- **SE5 and QUP0 in the UFS boot.** The I2C GENI driver now probes SE5 at
  boot, and QUP0 votes on its own interconnect paths. In the retained SM8450
  topology, the SE5 configuration and memory paths do not include SH1 or CN0
  members. The voter is shared, though. Commits by other clients, including
  an already pending protected entry, can change the confirmation history.
  Before the overlay, the module requires:
  - the held USB path;
  - an empty commit list;
  - exactly confirmed SH1 and CN0 bucket values.

  A different commit history can change whether that gate passes. No
  predicate is bypassed: a failed gate is a pre-effect refusal, which means
  `NO_PROOF` and a normal return. The adopted MAX77705 observation ran this
  exact DT with USB enumerating normally.
- **Bus sharing.** SE5 serves only the MAX77705 PMIC, USBC and FSA4480. The
  route observer stops sampling once the first connection is accepted, before
  the request is read. It issues no I2C transfer during the dwell, witness or
  module stage.
- **Window end.** The boundary is a submission boundary:
  - no tick starts in the last second of the 120-second window;
  - the payload and the start strobe are each submitted only after an
    observer clock read that falls before the window's end;
  - each failed clock read refuses its own submission. The check after the
    payload can refuse only the strobe.

  The governing condition is the time of each clock read. Two latencies are
  not bounded: the gap between the clock read and the system call, and the
  kernel and bus path after submission (message copy, adapter lock, GENI
  setup). An admitted strobe can therefore reach the device after the
  window's end. It is still the same submitted command the window admits,
  not an additional effect.
- **Module.** The module is the adopted byte-identical V13 module. The new
  kernel exports the same symbol versions.

## Witness-floor variant

ML054 spent about 300 seconds in the witness dwell before the module permit.
On 2026-11-27 the operator approved shortening the wait as the first step of a
roadmap: shorter wait, then UFS read/write and persistence across a reboot,
then stability, then handover to the upstream driver. The candidate kernel
queues its regulator cleanup 30 seconds after late initcalls, at about 31 to
33 seconds of uptime. It sets the deferred-probe timeout to 10 seconds. A
60-second guest BOOTTIME floor is clear of both.

A capability selects the variant with the fixed field `witness_floor_ms = 60000`.
The field is allowed only in the route scope and only with that exact value.
- **Guest.** The candidate does not change the adopted `dwell.h` (sha256
  `6d523868…faad4590`). Instead the observer embeds a rendered copy of it. The
  copy differs only in its two 300-second comparisons. The dwell refuses a
  challenge that arrives before 60 seconds of BOOTTIME. The guest's fresh
  same-boot proof, whose uptime the witness reply reports, must show at least
  60 seconds and be later than the first response. The challenge itself still
  carries the first uptime and a zero second-uptime field. The 540-second
  ceiling check is unchanged.
- **Host.** The first response must report a BOOTTIME below 120 seconds. The
  host waits 60 seconds minus that BOOTTIME, plus a 2-second margin, and at
  least 1 second. It then re-derives the witness and requires a BOOTTIME of at
  least 60 seconds, later than the first.
- **Module and kernel.** Two fixed artifacts refuse to run below 300 seconds of
  boot time: the V13 module's `start()` (`g0q_stage.c`) and the transport
  kernel's `g0q_rpmh_begin()` (`transport/authority.inc.c`, built into
  `rpmh.c`). ML055 ran the first floor capability with both. The witness
  passed at 62.8 seconds, and the module refused before any effect
  ([run](../reports/S22PLUS_MAINLINE_ML055_UFS_FLOOR_RUN_2026-11-27.md)). A
  search of every module, transport and patched kernel source for an
  absolute boot-time bound found only these two; the other kernel checks are
  relative deadlines.
  The operator then approved a floor kernel and module. `boot_floor.py`
  renders both sha-pinned sources with that one comparison set to 60 seconds
  and nothing else changed:
  - the kernel is rebuilt from the route composition's kernel source and
    configuration, with the rendered authority substituted into the prepared
    `rpmh.c`;
  - the module is rebuilt from the rendered `g0q_stage.c` against that kernel.

  The module record carries `boot_floor_ms = 60000` and both rendered source
  digests. The candidate validator and the observer builder admit a floor
  capability only with that module, and an unfloored capability only with an
  unfloored module. For a floor record they also check the recorded build
  directories: the module directory's `g0q_stage.c` must be the rendering,
  and the kernel's transport record must pin a prepared `rpmh.c` that carries
  the rendered authority and not the adopted one. The step from those sources
  to the binaries rests on the H0 build records and the owner review, as for
  every earlier kernel and module. `boot_floor.py` and `authority.inc.c` are
  pinned in every V2 capability's source set.
- **Older records.** Capabilities and images without the field keep the
  300-second witness, the route kernel and the V13 module byte for byte.
  These include ML054's capability. ML055's capability-3, which paired the
  floor with the V13 kernel and module, no longer admits.

With the field, the closure records `same_boot_witness` and
`witness_floor_ms = 60000`, and omits `five_minute_same_boot`. The host wire
parser applies the same floor when it checks the witness and builds the
permit. All other parts of this composition are unchanged, as listed under
[Unchanged](#unchanged).

## Storage stage (phase 2a from report V14, phase 2b from V17)

Step 2 of the operator's roadmap is UFS read/write and persistence across a
reboot. The operator approved its [design](../reports/S22PLUS_MAINLINE_UFS_RW_DESIGN_H0_2026-11-27.md)
and the read-only phase 2a on 2026-11-27.

`ufs_storage.c` runs once after the completed link, inside the module's
budget, only in report V14 or later on the floor route kernel and module. It uses
one transfer slot with a polled doorbell and no interrupt. Crypto stays
disabled, the LUN is always 0, and every field is fixed:

1. NOP OUT, expecting NOP IN.
2. Query set flag `fDeviceInit`, then read the flag until it clears
   (1.5-second bound).
3. TEST UNIT READY; one repeat only after a UNIT ATTENTION (V15: or after a
   CHECK CONDITION whose sense was not located, see below).
4. READ CAPACITY(16): exactly 62,305,280 blocks of 4096 bytes.
5. READ(10) of LBAs 1–3. Their SHA-256 must equal the live Android32 table
   (`a0de4421…`), and a parse must show that no entry covers the test block.
6. READ(10) of LBA 62,305,152. The report carries its full SHA-256 and
   whether the block is all zeros.

Supporting changes:
- **SMMU.** The late overlay's link node gains `iommus = <&apps_smmu 0xe0 0>`
  and `dma-coherent` for V14 and later only. The kernel blocks unmatched SMMU
  streams, so UTP DMA needs the controller's own stream.
- **Report.** The V14 report appends 16 fields: the stage rc and step, flags,
  the `fDeviceInit` poll count, sense, the last transfer status, the capacity,
  a GPT digest word and the block digest. Its envelope is 512 bytes; older
  versions keep 256. V15 adds one field (below). The host decoder rejects inconsistent step and flag
  sets, and any storage field after a link that did not complete.
- **Return.** The stage's outcome never changes the return conditions.
- **Uncertain slot.** A slot that does not complete in time is never
  cleared or reused. At restart, the link driver's `.shutdown` runs before
  the SMMU's own shutdown. It stops the transfer list. With no slot
  outstanding, there is no DMA to stop. With one outstanding, it clears HCE
  and waits up to 1 second for HCE to read 0. The Qualcomm reset provider
  does not prove that a reset took effect. If HCE does not clear, the
  callback therefore asserts the block reset and parks the restart instead
  of letting the SMMU stop translating. The attended physical Download
  (a PMIC reset of the whole SoC) recovers from that state.
- **Guards.**
  - The stage requires `device_iommu_mapped()` before any DMA.
  - The module's budget check for the link runs before the stage. The
    stage ends 2 seconds before the module budget, so it can never change
    the link outcome.
  - Every command wait is an absolute deadline.
  - GOOD status counts only with no underflow, overflow or residual.
  - The GPT is parsed only after its exact digest matches, with an explicit
    entry-count bound.

The UTP sequence has a host device model (`tests/s22plus_ufs_storage_fixture.c`).
It drives the actual source and rejects any command outside the set above,
including any other write opcode or shape, another LUN or the crypto bit. Only
a V17 build (`G0Q_STORAGE_WRITE`) may send its one FUA write of the test block
(below), at most once per run.

### Response header (report V15)

V15 was built on a misdecoded ML057 status. ML058 showed that the Total EHS
Length was 0 and that the refused byte is the response field (see V16 below).
V15's handling of an extra header is harmless, and its header word is what
exposed the real cause.

V15 (`G0Q_STORAGE_HEADER`, cumulative on V14) changes only how a response
is read. The command set, the sequence and every other guard are unchanged.
- An extra header segment follows the 32-byte header. Every header field the
  stage reads keeps its offset: type, flags, response, status, residual, and
  the query echo and value. Data moves through the PRDT. So a nonzero EHS
  length no longer stops the stage.
- The one data segment the stage reads is sense. When a CHECK CONDITION
  declares an extra header segment, the sense bytes are not located and
  never guessed. The sense stays 0 and the flag `SENSE_UNPARSED` is set.
- TEST UNIT READY is repeated once after a UNIT ATTENTION or after such an
  unparsed CHECK CONDITION. The repeat attempt sets `TUR_REPEAT`. A parsed CHECK
  CONDITION with another sense key still stops the stage, and so does a
  second CHECK CONDITION.
- The report appends one field: header bytes 8–11 of the last response (Total
  EHS Length, Device Information, Data Segment Length). It has 55 fields in
  the same 512-byte envelope.

V14 still builds with the earlier behavior. ML057's V14 component keeps its
own retained stage rendering in `boot_floor.py`.

### Response byte (report V16)

ML057 and ML058 both stopped at TEST UNIT READY with `-EPROTO`, before any
media command. The status word was `0x21020100`: RESPONSE UPIU, OCS 0,
status CHECK CONDITION and response `0x01` (Target Failure). ML058's header
word was `0x00000014`: no extra header and a 20-byte data segment, the size
of a length field plus 18 bytes of fixed-format sense. That sense was not
parsed ([run](../reports/S22PLUS_MAINLINE_ML058_UFS_STORAGE_HEADER_RUN_2026-11-28.md)).
`scsi()` refuses any nonzero response byte. Upstream
`ufshcd_transfer_rsp_status()` takes only the status of a SCSI response.

V16 (`G0Q_STORAGE_RESPONSE`, cumulative on V15) accepts response `0x01`
only together with CHECK CONDITION, and sets the sticky flag
`TARGET_FAILURE`. The sense is parsed as before, so a UNIT ATTENTION takes
the one TEST UNIT READY repeat. A GOOD status with a nonzero response, or
any other response value, is still refused with `-EPROTO`. The report keeps
V15's 55 fields and envelope. Its tag is `0xf0100000`: tags through V15 are
`version << 28`, and later ones keep `0xf` and carry the excess in bits
20–27, clear of the site (bits 0–15) and the certificate (bit 16). V16 adds
no stage source change, so it shares V15's stage rendering.

### One-block write (report V17, phase 2b)

The operator approved the phase 2b exception, phase 2c and the storage
envelope in the common details on 2026-11-28 ("그렇게 하자, 2b 계약 승인하고
V17 진행해 나머지도 한번에 승인할게"). ML059 (V16) read the test block as 4096
zero bytes ([run](../reports/S22PLUS_MAINLINE_ML059_UFS_STORAGE_READ_PASS_2026-11-28.md)).

V17 (`G0Q_STORAGE_WRITE`, cumulative on V16) adds two steps after the block
read:
1. **Write decision.** If the block already holds the fixed pattern, the
   stage sets `PATTERN_PRESENT` and ends without a write. If it is not all
   zeros, the stage stops with `-EEXIST` before any write. If less than
   1 second of the stage budget remains, it stops with `-ETIMEDOUT` before
   any write.
2. **Write.** One WRITE(10) with FUA (`2a 08`, LBA 62,305,152, one block)
   carries the module-generated pattern (`S22UFS2B`, LBA and record index,
   256 records; SHA-256 `1155097a…0d18`). The status sample is cleared first,
   so a write that never completes leaves it 0. The doorbell rings only while
   a full second of the stage budget remains (checked last before the ring),
   so the write keeps its full 500 ms wait and the readback its own 500 ms; a
   later ring is refused (`-EBUSY`). On GOOD the stage sets `WRITTEN`.
3. **Readback.** One READ(10) of the block. The report carries the first
   SHA-256 word of the data read. A byte-exact match sets `READBACK_MATCH`;
   anything else stops with `-EILSEQ`.

Steps 11 (`WRITE`) and 12 (`READBACK`) name stops; a completed V17 stage
still ends at step 10 (`DONE`). The report appends the write's status word
and the readback word: 57 fields in the 512-byte envelope, tag `0xf0200000`.
The host decoder (`link_wire.storage_write`) checks the read-only fields with
the V16 rules and classifies the write as `WRITTEN`, `ALREADY_PRESENT`,
`FOREIGN_CONTENT`, `WRITE_BUDGET`, `WRITE_REFUSED`, `WRITE_LATE`,
`WRITE_UNCERTAIN`, `WRITE_FAILED`, `READBACK_MISMATCH` or `READBACK_FAILED`.
Each late stop is decoded against the exchange that produced it: an OCS
failure or another SCSI status (`-EIO`), a wrong reply type or response
(`-EPROTO`, possibly with a zero status word), a CHECK CONDITION (`-EAGAIN`,
response 0 or Target Failure, sense parsed or left unparsed with an extra
header), or a residual (`-ENODATA`). A refused or late readback keeps the
write's GOOD sample. Device-init polls are at most 1,499. A late or uncertain
write establishes neither media state: the block may hold zeros or the
pattern, and only a later block read decides. `READBACK_MISMATCH` and
`FOREIGN_CONTENT` stop the lane: once any closed run records either, or a
series block read finds `OTHER`, no V17 grant opens. The grant itself scans
every closure, whichever predecessor a task names; a V17 task must live at
`outputs/<run>/task-1` so its closure is in that scan. The device model sends at most one write per run and
refuses any other write shape.

### Android read (phase 2c)

`s22plus_mainline_ufs_android_block_v1.py` reads the test block once on the
healthy original Android that a V17 run returned to. It is in the storage
capability's source closure, so the run's capability binds its bytes. Its one
fixed root command checks the LU0 node (sysfs ancestry under `1d84000.ufshc`
LUN 0, device number, 4096-byte blocks, 498,442,240 sectors). It also checks
that every Android partition ends at or before sector 498,441,216, then
reads exactly one block at LBA 62,305,152 with Toybox `dd`. The read sits
between two rooted health brackets on the same boot. The read needs
`--attended`, the same host boot and the before-bracket boot ID equal to the
one that closure's final health proved. It is claimed and started within the
series step time after the V17 closure (decided once, at start); it then runs
under the ordinary 600-second D0 bound. A stopped read still records its
block class in `stopped.json`, and `OTHER` there stops the lane too. Its
output is fixed at `<series>/block-<step>`. Android's cold boot after the
transfer leaves no cached copy of a block that no partition covers. The outcome is `PATTERN`, `ZERO`,
`OTHER` or `NO_PROOF`.

### Series approval

`s22plus_mainline_series_v1.py` lets one exact returned approval cover a fixed
series. The planned persistence series is:
1. a V17 run of candidate 1 (write);
2. the Android read;
3. a V17 run of a second qualified candidate with its own AP (a consumed AP is
   never reused), which finds `ALREADY_PRESENT`.

Every mainline step must name a distinct V17-or-later UFS storage image
(distinct candidate and AP).

The approval text is
`APPROVE S22PLUS MAINLINE SERIES V1 <series sha256> <n>steps <seconds>s attended`.
Each mainline step is prepared as usual. Its `operator-approval.json` names
the series and step and carries the series approval text. The connector
binds the step's exact image and preceding closure. It claims the step once
before the grant opens. Expiry is decided once, by the claim: it records the
boot-clock time and host boot at which it was made and the approval text, and
the grant opens under a series text only with a claim made before expiry for
this task and image (the direct grant entry has none, so it refuses). A
claimed step runs and recovers under the single-step rules, and its recovery
needs neither later images nor the approval file. Later steps need every
earlier step closed healthy by its own claimed subject, and the claim itself
rechecks that order: the claimed task's `closed.json` with that task's grant, operation, terminal and the
final health inside that operation, or the claimed read's `terminal.json` naming the series and step, with
write outcome `WRITTEN` or `ALREADY_PRESENT` and Android read `PATTERN`.

## Evidence and claims

A completed run can claim:
- the V13 link result, with its usual classes;
- an authenticated USB first response with no physical action.

It does not claim:
- that the route write ran;
- that SE5 sharing had no effect on UFS beyond the module's own report;
- recovery from a hung kernel.

## Authority

This policy grants nothing by itself. The operator approved the
common-contract delegation, and the code, contract and target paragraph are
adopted (`c9c1b15ecb`, v67). Before any run:
- the exact capability record and its candidate need an independent owner
  review;
- the candidate must be fresh, qualified and key-only.

Each run then needs:
- current D0;
- one exact returned one-operation 1800-second approval, or one exact
  returned series approval that names it;
- the operator's attendance, with no action requested;
- usable physical Download;
- a validated prior healthy closure.

Conditional Autonomous F1 remains inactive.
