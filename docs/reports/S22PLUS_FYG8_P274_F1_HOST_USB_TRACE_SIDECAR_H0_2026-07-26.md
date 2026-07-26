# S22+ FYG8 P2.74 F1 host USB trace sidecar

Date: 2026-07-26 KST

Scope: H0 host-only implementation and synthetic validation. No connected D0,
approval, transaction, Download request, Odin session, transfer, reboot, device
contact, or device write occurred.

## Result

A bounded, non-authoritative host USB trace sidecar is ready for the next
attended P2.72 transaction:

`workspace/public/src/scripts/revalidation/device_action_usb_trace_sidecar_v1.py`

It captures:

- host kernel USB messages through `journalctl --dmesg --follow`;
- kernel and udev events for the `usb` and `tty` subsystems;
- one `lsusb` snapshot before and after the capture window; and
- UTC receive timestamps, bounded private logs, and a durable result receipt.

The sidecar never opens `/dev/ttyACM*`, does not poll `lsusb`, does not invoke
ADB or Odin, and is not an F1 acceptance gate. The existing Process v2
candidate-bound ACM observer remains the only reader of candidate ACM bytes.

## Execution boundary

The P2.72 candidate line remains frozen. This unit changes none of:

- the candidate or rollback artifacts;
- ready manifest or observation contract;
- P2.60 runtime, source contract, decoder, or checker;
- Process v2 runner, live adapter, CDC-ACM observer, or USBFS identity code; or
- Odin wrapper, recovery state machine, target profile, or transport.

The frozen bundle and execution-closure hashes remain:

```text
bundle: 52e2e95c3d346a1e2936f3ec2a7a7f6efd5e3ed080ceacb7803b250cdca70347
execution closure: 950992db8cf69d610bfd787acdbea91a04dca11bfc96b01c441d3b06de79a764
```

Sidecar failure, truncation, or absence cannot change the canonical F1 verdict,
journal, recovery authority, or stop rules.

## Attended use

Run connected D0 exactly as rehearsed by P2.73. After it emits the exact
`RUN_DIR` and before invoking `--execute`, start the sidecar in a separate
terminal:

```bash
TRACE=workspace/public/src/scripts/revalidation/device_action_usb_trace_sidecar_v1.py
PYTHONPYCACHEPREFIX=/tmp/p274_usb_trace python3 "$TRACE" \
  --output-dir "$RUN_DIR/host-usb-trace" \
  --duration-sec 2700
```

The foreground process prints one start record. Leave it running across:

```text
candidate Download -> candidate flash -> candidate boot/observation
-> recovery Download -> rollback flash -> Android return -> final health
```

If the first runner invocation stops at durable `ROLLBACK_FLASHED` with the
same previously localized `measured USB endpoint inventory failed`, leave the
sidecar running while invoking the exact P2.73 `--recover` command against the
same run directory. Do not repeat the candidate or rollback.

Stop the sidecar with `Ctrl-C` only after the journal reaches `CLOSED` or an
operator stop has reached a known stable state. Its 45-minute absolute bound
prevents an orphaned capture. A duration expiry is diagnostic loss, not an F1
failure.

## Physical preconditions

- Use the same direct data cable and USB topology established by D0.
- Do not insert or remove a hub, change ports, or reconnect during the run.
- Keep the cable connected throughout candidate boot, rollback, recovery, and
  final health.
- Do not start a second ACM reader, serial terminal, `screen`, `minicom`, or
  repeated `lsusb` scanner.

A rear motherboard port is a useful preference, not proof of a direct root
port. The D0-bound stable topology is authoritative.

## Interpretation

| Retained/host result | Supported interpretation | Next coordinate |
|---|---|---|
| stage `0x8f`, `ETIMEDOUT`, no host connect | no configured state and no observed pull-up/connect | VBUS, Type-C, pull-up, notifier path |
| stage `0x8f`, `ETIMEDOUT`, connect/reset errors | pull-up occurred; enumeration negotiation failed | descriptor/reset/PHY/host trace |
| stage `0x8f`, `EPROTO` | configured but `current_speed` was not exact `high-speed` | cable/port first, then speed/PHY contract |
| stage `0x8d` or `0x8e`, errno | E3 role/UDC preparation or bind failed | exact stage and errno |
| E3 stage, `0x8xx`/`0x9xx` detail | an earlier E2 gate regressed or became unreadable | decoded gate index |
| stage `0x88..0x8c`, errno | real-kernel E3 path diverged from generic QEMU | exact syscall/errno and harness boundary |
| terminal `0x90`, ACM observer rejected | device queued the banner and reached high-speed configured; host receipt failed | observer classification plus host trace |
| terminal `0x90`, exact ACM banner | E3 live path proven | mandatory rollback and final health |

`ETIMEDOUT` alone never proves that the host saw no connect. `EPROTO` does not
by itself exonerate candidate or PHY code. Terminal `0x90` with no exact banner
is diagnostic proof of the device-side terminal path, not E3 PASS.

## Private evidence and redaction

The output directory contains raw host identifiers and is private evidence.
Kernel, udev, and `lsusb` output may expose:

- physical Android or Download serials;
- the synthetic candidate serial;
- `ID_SERIAL`, `ID_SERIAL_SHORT`, bus/device numbers; and
- `DEVPATH` or physical USB topology.

Never commit or paste these raw logs into a public report. Public reporting
must summarize only the event sequence and error class, with serials removed
and topology replaced by an approved digest. The sidecar writes
`contains_private_usb_identifiers=true` and
`public_raw_export_forbidden=true` into both start and result receipts.

## Validation

- Python compilation passed.
- Five focused unit tests passed with `ResourceWarning` promoted to error.
- Tests cover private-path confinement, exclusive output creation, bounded
  duration, durable source receipts, non-authoritative flags, command failure,
  and absence of ACM opens or periodic `lsusb` in the continuous sources.
- The installed host provides `journalctl`, `udevadm`, and `lsusb`.
- A synthetic capture completed without device contact under
  `workspace/private/outputs/s22plus_fyg8_p274_usb_trace_sidecar_dry_run/`.
- The pinned P2.72 ready-manifest regression still reopens the exact bundle,
  and live `--validate` returns the frozen bundle and execution-closure hashes.

Verdict: `PASS_P274_F1_HOST_USB_TRACE_SIDECAR_H0`.
