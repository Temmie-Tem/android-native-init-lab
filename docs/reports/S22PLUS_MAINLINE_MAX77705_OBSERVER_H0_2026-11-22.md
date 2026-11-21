# S22+ mainline replug dependency: Stage 0 and Stage 1 tooling (H0)

Date: 2026-11-22
Target: Galaxy S22+ `SM-S906N` / `g0q`, Linux 7.2.11 mainline + Debian RAM PID1.
Scope: host-only build and qualification. No device contact. This produces
no device authority, approved candidate or boot package.
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
- `INITIAL_COM_USB`
- `OPEN_THEN_COM_USB_AFTER_ATTACH`
- `OPEN_UNCHANGED_AFTER_ATTACH`
- `OPEN_NO_ATTACH_SEEN`
- `NO_PROOF_*`

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
| Observer (static aarch64) | `e9910f5b…0a40` | `a968179e…2ef2` |
| RAM archive (ML022 with only the observer replaced, other 27 members byte-equal) | `390cd01b…b99f` | `e7ba1313…a8a3` |

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

## Not done / remaining

- **No board package or loader.** The board RAM archive, Image and DTB exist,
  but no uniLoader or boot AP was built and no qualified candidate exists.
  An attended run would need:
  - profile review and adoption;
  - review of the bus-sharing risk (`qcom,shared` SE5 without mainline
    arbitration);
  - a fresh candidate, D0 and approval.
- **Board behaviour is unknown:** FIFO versus GSI mode on SE5, whether XBL
  left the pins muxed, and whether `0x25` answers under mainline.
- **Stage 2** (one `CONTROL1_W(0x09)`) is not implemented, by design. It
  would be a separate profile, built only after Stage 1 reads `0x3f` on
  hardware.

## Incident

While checking the QEMU environment I ran the SCM harness in its own
directory. That overwrote its `unbound.json` receipt, so the receipt hash in
`recheck-zqgnc8p_/qualification.json` no longer matches. The qualified raw
response is intact. The details and the remedy for the owner are in
`s22plus-max77705-observe-h0.2QtaVD7S/INCIDENT-scm-receipt-overwrite.md`.
