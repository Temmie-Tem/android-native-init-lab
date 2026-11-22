# S22+ mainline replug dependency: Stage 0 and Stage 1 tooling (H0)

Date: 2026-11-22
Target: Galaxy S22+ `SM-S906N` / `g0q`, Linux 7.2.11 mainline + Debian RAM PID1.
Scope: host-only build and qualification. No device contact. This produces
a host-built boot package but no device authority or approved candidate.
Follows the [root-cause plan](S22PLUS_MAINLINE_REPLUG_DEPENDENCY_ROOT_CAUSE_H0_2026-11-22.md).

## Stage 0: host port watch (no phone change)

[`host_port_watch.py`](../../workspace/public/src/mainline/s22plus_canary_h0/host_port_watch.py)
watches selected host topologies during the untouched-cable window. By
default these are `3-1.3`, the candidate's USB2 lane, and `2-1.3`, the
SuperSpeed lane used by Download and Android.

What it records:
- the parent hub port's sysfs `state` (`not attached`, `powered`, ...
  `configured`), sampled every 0.1 s, transitions only;
- whether a device node exists at that topology;
- the host kernel log via `journalctl -k -f`, which this account can read
  even though `dmesg` is restricted;
- `udevadm monitor` USB events;
- the cable type the operator states.

It only reads sysfs and starts two read-only monitors. Its per-port label:

| Label | Reading |
|---|---|
| `PORT_STAYED_NOT_ATTACHED` | The phone's pull-up never reached the host port. H1/H3 survive. |
| `PORT_LEFT_NOT_ATTACHED_WITHOUT_DEVICE` | The pull-up crossed the connector but enumeration failed. H2 leads; the journal shows why. |
| `DEVICE_ENUMERATED` | The phone enumerated. |

Usage: `host_port_watch.py --output <fresh-private-dir> --duration 180
--cable c-to-a`, started alongside the next attended run. Six unit tests
cover topology mapping, transitions and labels on a fake sysfs. A 3-second
smoke run on this host read `2-1.3 configured` (Android) and
`3-1.3 not attached`.

## Stage 1a: read-only MAX77705 observer

The observer lives in
[`max77705-usb-observe.h`](../../workspace/public/src/mainline/s22plus_canary_h0/max77705-usb-observe.h).
It runs inside the Debian RAM observer.

**Adapter.** It locates the `i2c-dev` adapter whose parent is `994000.i2c` by
name, not by number, and uses `I2C_RDWR`.

**Identity gate.** It requires PMIC `0x66` ID `0x15` with revision low bits
`0x2`. On a mismatch it sends nothing more.

**First reads, before USB setup:**
- USBC hardware and firmware revision;
- `UIC_INT` and `CC_INT`, recorded and cleared. This handles a stale XBL
  `APCmdResI` and response latch;
- `BC_STATUS`, `CC_STATUS0` and `USBC_STATUS1`;
- FSA4480 `0x00`, `0x04` and `0x05`;
- one `CONTROL1_R` through the mailbox: `0x05` to `0x21`, strobe `0x41`, poll
  `APCmdResI` up to 100 times, read `0x51`/`0x52`, and require the opcode echo.

**While waiting for the request, every 200 ms:**
- read the interrupt and status bytes;
- on any change, read `CONTROL1` (at most once per second);
- otherwise read `CONTROL1` every 10 s;
- stop after 32 commands in total.

The first 24 events are kept from boot; the last 24 form a ring.

**Write allowlist.** The only bus writes that can reach the device are
`0x05 → 0x21` and `0x00 → 0x41` on `0x25`. `mx_write()` rejects everything
else before the bus. That excludes `CONTROL1_W` (`0x06`), any write to `0x66`
and any write to FSA4480. Any rejected attempt is counted in the record, and
the verifier fails the whole record if the count is nonzero.

**Host tests.** Eight tests run the real header against a simulated MAX77705.
They cover:
- an autonomous switch change after attach;
- the switch staying open;
- the stale latch;
- timeout and bad echo;
- an identity mismatch, where zero bus writes happen;
- the allowlist, where 5/5 disallowed writes are rejected with zero bus
  writes;
- the command budget and ring order under an interrupt flood;
- a source-level check that the only `mx_write` call sites are the two
  allowed pairs.

## Stage 1b: kernel and DT

| Item | Value |
|---|---|
| Base | the selected ML053 Image `5a0b12b0…7406`, config `2a06feda…9113` |
| Config change | exactly one: `CONFIG_I2C_QCOM_GENI m → y` (after `olddefconfig`) |
| New Image | `d7df52a1…f609`, 43,969,024 B; embedded config equals `.config`; `geni_i2c_probe` present in System.map |
| Base DTB | ML053 `f918d309…46a0` |
| New DTB | `51b58a40…8235` |

The DTB diff is exactly four lines:
- `geniqup@9c0000` set to `okay`;
- `i2c@994000` set to `okay`;
- `pinctrl-names` deleted from `i2c@994000`;
- `pinctrl-0` deleted from `i2c@994000`.

TLMM (`pinctrl@f100000`) and `gpi_dma0` stay disabled, as the plan prefers.

Kernel and DT were built with the baseline's isolated `make` (bwrap, no
network) in a new private directory. No shared input was modified.

## Stage 1c: signed USB integration and VM qualification

[`max77705_usb_h0.py`](../../workspace/public/src/mainline/s22plus_canary_h0/max77705_usb_h0.py)
stages the profile from the reviewed Debian RAM observer, following the same
pattern as the SCM profile.

**Wire changes:**
- the body grows from 352 to 968 bytes: the base fields plus a 616-byte
  record;
- the VM and board profiles have separate domains and magics (`G0QM`,
  `G0QU`);
- a compile-time guard rejects a board build with the VM flag, and the
  reverse.

**Observer changes:**
- `mx_begin()` runs right after `G0Q_RAM_PID1_BEGIN`;
- the request wait loop polls in 200 ms slices and calls `mx_tick()`;
- the 120 s absolute deadline is unchanged.

**Board verifier.** Like SCM, it accepts only a sealed capture plus the
loader's exact FDT hash.

[`max77705_record.py`](../../workspace/public/src/mainline/s22plus_canary_h0/max77705_record.py)
decodes the record and gives a coarse verdict:
- `INITIAL_COM_USB`: the first CONTROL1 read is `0x09`;
- `OTHER_INITIAL_CONTROL1`: the first read is neither `0x09` nor `0x3f`;
- `OPEN_NO_ATTACH_SEEN`: the first read is `0x3f` and no VBUSDetI or CHGTypI
  was latched;
- `OPEN_NO_READ_AFTER_ATTACH`: an attach was latched but no CONTROL1 read
  followed it;
- `OPEN_THEN_COM_USB_AFTER_ATTACH`: the last read after attach is `0x09`;
- `OPEN_UNCHANGED_AFTER_ATTACH`: every read after attach is `0x3f`;
- `OPEN_THEN_OTHER_AFTER_ATTACH`: any other value after attach;
- `NO_PROOF_*`: adapter absent or failed to open, identity mismatch, or no
  CONTROL1 read.

Before any verdict, the decoder rejects records the observer cannot produce:
- more than 32 commands;
- an event count that disagrees with the total;
- events or commands without an identified adapter;
- anything other than exactly one leading `begin` event;
- event times out of order or past the elapsed time;
- more commanded events than commands;
- an event kind paired with a read status the producer never emits, for
  example a `begin` without an attempted command, or a `limit` status before
  32 commands.

The HMAC proves the record's origin, not its sanity, so the decoder checks
both.

Six wire tests cover:
- aarch64 compile of both profiles and rejection of the wrong mode flag;
- signed decode;
- HMAC tamper detection;
- the disallowed-write rejection;
- verdicts and ring order;
- the board-domain capture entry.

Artifacts (private, `s22plus-max77705-observe-h0.2QtaVD7S/`):

| | VM | Board |
|---|---|---|
| Observer (static aarch64) | `e9910f5b…0a40` | `a968179e…2ef2` (superseded) |
| RAM archive (ML022 with only the observer replaced, other 27 members byte-equal) | `390cd01b…b99f` | `e7ba1313…a8a3` (superseded) |

**Correction.** The board observer in this table was built with the VM
fixture's network seal (`dummy_udc.0`, fixed fixture MACs and serial). It
would never have enumerated on hardware. The board package below replaces it
with an observer built the way the SCM board build derives its seal.

VM runs used QEMU 10.2.1 virt, the guest NCM/dummy_hcd relay from the SCM
harness (copied, not run in place) and QEMU's own DTB:

| Case | Kernel | Result |
|---|---|---|
| ok | base `5a0b12b0` | `AUTHENTICATED_H0_MAX77705_USB_OBSERVATION`, adapter-absent (ENOENT), 0 commands, verdict `NO_PROOF_ADAPTER_ABSENT` |
| ok | new `d7df52a1` | same: the new kernel boots Debian and serves the signed response |
| bad-key | base | 0 bytes, observer parked with `EACCES` |

The VM has no `994000.i2c`, so these runs qualify the integration path, the
signing and the "absent adapter sends nothing" branch. The mailbox protocol is
covered only by the simulated-device tests.

**Harness finding.** Passing a QEMU-dumped DTB with `-dtb` stalled every
guest on this host for up to 300 s with no output, including the unchanged
SCM observer. The SCM harness passed with `-dtb` earlier the same day. This
profile needs no DT edits, so its runner boots with QEMU's internal DTB. The
cause is not investigated.

## Attended cue helper (fix for the ML051/ML052 cue loss)

[`s22plus_mainline_cue_dialog_v1.py`](../../workspace/public/src/scripts/host_tools/s22plus_mainline_cue_dialog_v1.py)
replaces the per-run `cue-watch.py`. It calls only the reviewed
`s22plus_mainline_attach_cue_v1.py` through its fixed self-capture CLI
(`issue`, `resolve`), so the reviewed interlock code and records are
unchanged.

Flow:
1. On the journal's `step-start mainline-evidence`, it starts the Stage 0
   host port watch.
2. At window+22 s it issues the cue, using the same retry and refusal rules
   as before.
3. On `CUE_RECORDED_DISPLAY_NOW` it plays a sound and shows a zenity dialog
   with **다시 꽂았음** and **취소**.
4. A click calls `resolve completed` or `resolve cancelled`. The operator
   statement names the button clicked and the time.

Timing:
- The dialog closes 8 s before the 120 s window ends.
- If it times out, nothing is resolved and the owner's interlock closes the
  attempt as before.
- Neither the assistant's turn nor typing is on the critical path any more.

Six tests run with a fake runner. They cover:
- button-to-resolution mapping;
- dialog timeout;
- refusals that never resolve;
- retry naming;
- no window;
- calling only the reviewed tool.

The operator accepted the click as their resolution on 2026-11-22. A review
of the helper is still needed before use.

## Board package (H0)

A boot AP for SM-S906N / g0q / FYG8 was built on the host. It follows the
SCM board-artifact build step for step (Codex's
`s22plus-scm-board-artifact.Z9b5Fre8`), with three substitutions:
- the I2C-enabled Image;
- the SE5 DT;
- the MAX77705 board observer.

The scripts were copied into a new private directory, not run in place.

| Item | Value |
|---|---|
| AP | `c3ce382a9f3cb27b32fd5d1eaa7a43fe2983c2f99ea7fd2a37a0c18579ab2ef9`, 25,497,641 B; two independent packagings are byte-identical |
| boot v4 (96 MiB) | `3b4f3039…2d86`; outer envelope, ramdisk, signature and AVB trailer retained from the original A |
| uniLoader | `6d89f7bd…0349`, 45,728,128 B; placement guard passed, no fixed-reservation overlap |
| Image / DT inside the loader | `d7df52a1…f609` / `51b58a40…8235` (Stage 1b) |
| Board observer | `6711b117…24b2`, 664,152 B. Built with `-std=c11 -Os -Wall -Wextra -Werror`. UDC `a600000.usb`; MACs and serial derived from the candidate identity |
| RAM archive | `4c39d880…c71b`; versus ML022, only the observer member differs |
| Loader-handed DT | 500,000 B, `67930f68…2ceb` (the verifier's expected FDT) |
| Board decoder | `c1974798…48cd`; the record decoder is embedded (see below) |
| Original A | `2e541703…967e`, equal to the target's final-health boot |

**Loader checks.**
- **Unicorn:** 20 cases pass (`PASS_H0_ACTUAL_ARM64_LOADER`), including 1,051
  aligned copy cases.
- **QEMU with the retained gdb-multiarch:** relocated entry at real EL1 and
  EL2, rejection at EL3. These are the same terminal PCs and CPSRs as the SCM
  candidate.

**Independent check** (`check_package.py`):
- Both AP copies unpack to the same boot image, and its kernel field is the
  loader.
- The Image, DT and ramdisk sliced from the loader's linker symbols match
  their sources.
- The observer, rebuilt from regenerated sources, is byte-identical.
- A board build with the VM flag fails at `#error`.
- The candidate identity re-derives from its pinned inputs.

**Loader-handed DT.** Compared with the SCM candidate's (same loader source,
same base DT), it differs in exactly five properties:
- the four SE5 lines from Stage 1b;
- `linux,initrd-end` on `/chosen`, which moves because the ramdisk size
  changed.

**Fixture responses.** These used a disjoint key and identity, signed by an
AArch64 codec built from the shipped `protocol.h`; the C and Python HMACs
agree.
- The board verifier read four verdicts: `OPEN_THEN_COM_USB_AFTER_ATTACH`,
  `OPEN_UNCHANGED_AFTER_ATTACH`, `INITIAL_COM_USB` and
  `NO_PROOF_ADAPTER_ABSENT`.
- It rejected nine cases:
  - a non-handle input;
  - a failed capture;
  - the real candidate key;
  - an old challenge;
  - a VM claim;
  - CONTROL1 changed after signing;
  - a nonzero rejected-write count;
  - an added empty DT leaf (FDT hash);
  - SE5 set back to `disabled` (DT property check).

The setup needed two harness inputs on this host: the retained
`gdb-multiarch` and unicorn 2.1.4 from
`s22plus-mainline-loader-h0-20261028-1`. The first attempts, using the host
gdb (no aarch64) and lacking unicorn, are kept as failed logs.

**Rebuild for a self-contained decoder.** The first package (AP `680ad421…`,
private `s22plus-max77705-board-artifact.G06Ao4bm/`) had a board decoder that
loaded `max77705_record.py` from its own directory at verify time. The
attended session runs a decoder only from hash-checked bytes, with no
`__file__`, so that second read would have been unpinned. The generator now
embeds the record decoder, and a wire test runs the decoder from bytes with
the sibling file deleted. Because the candidate identity commits to the
generated sources, the whole package was rebuilt (AP `f3f5cec7…`).

**Second rebuild for decoder sanity checks.** An independent Codex review
(`gpt-6.2-sol`) showed that the decoder accepted a signed record with 255
commands and out-of-order times, and still returned an observed verdict. It
also showed that any first CONTROL1 value other than `0x09` counted as
"open". The record checks and verdict split above were added, and the package
was rebuilt again. Every check above passed, plus one more rejection (a
command count of 255).

A second review round found that a `begin` event marked `skipped` still
passed. The kind/status checks were added and the package was rebuilt a third
time; all checks passed again.

Artifacts: private `s22plus-max77705-board-artifact.64Mdgw1G/`. The manifest
is `final-w_6mo8ll/qualified-artifact.json` (`eeebf904…4569`). APs
`680ad421…`, `f3f5cec7…` and `a3fd5a78…` are superseded.

## SE5 sharing review

Stock FYG8 marks SE5 `qcom,shared`. It is the only SE with that flag in the
base DT. Stock wraps every GSI transfer in lock/unlock so another execution
environment can use the engine between transfers. Mainline has no such
handling.

**Peer.** The peer is still unidentified, but the trusted VM is excluded:
- The FYG8 `vm-bootsys` partition holds Gunyah trusted-VM segments
  `trustedvm.b00`–`b05`.
- Its DT segment carries 10 board DTs (Waipio, Cape and Diwali; MTP, QRD,
  CDP and RUMI).
- They assign only SE1, SE4 and SE8 to the VM. None names SE5 or
  `i2c@994000`.

The mainline candidate starts no trusted VM and no remote processor:
- SLPI, ADSP, CDSP and MPSS are all `disabled` in the DT;
- `QCOM_Q6V5_PAS` is a module that the RAM archive does not carry.

That leaves TZ or the hypervisor as possible concurrent users, and neither is
known to use SE5.

**Mainline driver behaviour** (7.2.11 `i2c-qcom-geni.c`, `qcom-geni-se.c`):

| SE5 state at handoff | Mainline action | Outcome for the run |
|---|---|---|
| Protocol not programmed | `geni_load_se_firmware` reads `firmware-name` from the wrapper. Our DT has none, so it returns `-EINVAL` before any firmware request | Probe fails; observer reports adapter absent |
| I2C, FIFO disabled (GSI only) | `geni_se_select_mode(GPI)` clears the SE interrupt state and writes several mode registers, then `dma_request_chan` fails because `gpi_dma0` is disabled | Probe fails after those writes; adapter absent |
| I2C, FIFO enabled (r0q case) | FIFO init and packing configuration; 100 kHz (no `clock-frequency` in the node) | Adapter present; observer runs |
| Another protocol | `-ENXIO` | Adapter absent |

**Correction.** An earlier version of this table said the unprogrammed case
makes no SE register write. That is wrong. Runtime resume runs before
protocol detection in every row, turns the SE clocks and resources on, and
enables the SE interrupt (`i2c-qcom-geni.c:1210-1222`). If an interrupt is
pending, the ISR can clear interrupt state or write the TX watermark with no
transfer in flight (`:300-380`). So every state can produce some SE5 register
writes before the probe outcome. None of them reaches the I2C bus.

**Bus load and limits.**
- Each 200 ms tick reads five registers. That is about 3,000 reads over the
  120 s window.
- On top of that, at most 32 mailbox commands, each with two writes, up to
  100 polls and two reads.
- The only register values written on the bus are the two allowlisted USBC
  mailbox bytes. Every read is a combined transfer that first sends the
  register address in write direction, to `0x66`, `0x25` and `0x42` alike.
  FSA4480 sees three reads. No register value is written to the PMIC or
  FSA4480.

**Risk if a peer exists.** A collision would show up as I2C errors or wrong
values in our reads. The risk to the peer is a corrupted transfer of its own,
and the mailbox writes are the only bytes we put on the bus. The read-to-clear
`UIC_INT` and `CC_INT` are consumed by nobody else under mainline. Android's
driver re-reads status at its own probe after the original A is restored.

**Recommendation.** Keep the profile as is. If the run shows bus errors on
`0x25` while the adapter probed, treat it as possible sharing interference
rather than retrying blindly.

## Not done / remaining

- **No device authority.** The AP is a host artifact only. An attended run
  needs:
  - the session draft on the isolated branch `claude/s22-max77705-attended-h0`
    (`fbfc48e75f`, `DRAFT_H0`, rebased on the SCM adoption). It binds this
    candidate, the board decoder and the expected FDT in the existing
    mainline RAM owner. It also extends the attach cue to this image's
    ordinary evidence route. An offline binding check against the real
    artifact passed, and seven identity substitutions were rejected;
  - two Codex review rounds returned NO_GO. Their findings in the draft and
    decoder are fixed. The remaining findings sit in the shared cue and
    recovery code (the policy draft lists them). Merging the draft would
    invalidate eight review records that pin the shared files;
  - independent review and target adoption of that draft.
- **SCM run and the replug.** The adopted SCM run (2026-11-22) authenticated
  about 98 s after the Download device left the host. The operator confirmed
  that they replugged the phone end during that window. The cue tool refuses
  the ordinary route, so no cue, resolution or closure records that action.
  The run therefore supports the replug dependency rather than weakening it.
  It also shows the ordinary-route cue gap in practice: a physical action in
  the window went unrecorded.
  - D0, current Download recovery and approval.
- **Board behaviour is unknown:** FIFO versus GSI mode on SE5, whether XBL
  left the pins muxed, and whether `0x25` answers under mainline. The table
  above lists what each case produces.
- **Stage 2** (one `CONTROL1_W(0x09)`) is not implemented, by design. It
  would be a separate profile, built only after Stage 1 reads `0x3f` on
  hardware.

## Incident

While checking the QEMU environment I ran the SCM harness in its own
directory. That overwrote its `unbound.json` receipt, so the receipt hash in
`recheck-zqgnc8p_/qualification.json` no longer matches. The qualified raw
response is intact. The details and the remedy for the owner are in
`s22plus-max77705-observe-h0.2QtaVD7S/INCIDENT-scm-receipt-overwrite.md`.
