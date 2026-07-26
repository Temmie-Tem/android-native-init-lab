# S22+ FYG8 P2.76 E3 observation margin and ready2

Date: 2026-07-26 KST

Scope: H0 host-only. No D0, approval, transaction, Download request, Odin
session, transfer, reboot, device contact, or device write occurred.

## Verdict

`READY2_HOST_VALIDATED; CONNECTED_D0_NOT_YET_RUN`

The P2.72 ready1 manifest is retired before D0. Use only:

`workspace/public/src/device-action/manifests/s22plus_fyg8_p276_process_v2_ready_2.json`

The qualified candidate AP, rollback AP, observer identity, acceptance
contract, runner, and execution closure are unchanged. The only live-semantic
change is `observation.timeout_sec: 120 -> 180`.

## Why ready1 was retired

The candidate observation timeout starts after the Odin Download endpoint has
departed, not at flash start. P2.58A recorded `candidate_boot_ready` about 120
seconds after candidate flash completion because its observer deliberately
waited for the complete 120-second bound.

That elapsed host window is not a candidate terminal timestamp:

- the retained checkpoint format stores generation, stage, item, outcome,
  detail, and run identity, but no time;
- the retained checkpoint bytes sit in a fixed Samsung retained region and
  cannot be ordered against adjacent boot log timestamps; and
- P2.58A therefore proves only that E2 terminal stage `0x8f` was present by
  the end of the old observer window.

The current E3 runtime adds bounded waits after E2:

| Wait | Maximum |
|---|---:|
| `ttyGS0` class publication | 5 s |
| queued banner write under `EAGAIN` | 5 s |
| peripheral role plus exact UDC | 5 s |
| configured plus high-speed state | 30 s |
| Total E3 bounded waits | 45 s |

Configfs mount, gadget creation, node preparation, UDC bind, and checkpoint
writes are synchronous and add no explicit dwell, but they are not assumed to
be instantaneous. The generic-arm64 QEMU harness completed the E3 sequence in
about two seconds; that validates generic ordering and ABI behavior, not the
FYG8 vendor boot and provider timing.

Consequently, the old evidence cannot establish positive margin inside 120
seconds. This is an avoidable no-proof risk, not a device-safety defect.
Extending the bound to 180 seconds covers the conservative `120 + 45` model
with 15 seconds of additional margin and remains below the 300-second transient
guard lifetime under the previously measured short Download/flash departure.

## Preserved identities

- candidate AP SHA256:
  `a172448aaaab429591bfb31fb0ad57e635d6c362b27620eab2f528787eef3d66`;
- rollback AP SHA256:
  `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`;
- terminal stage: `0x90`;
- execution-closure SHA256:
  `950992db8cf69d610bfd787acdbea91a04dca11bfc96b01c441d3b06de79a764`;
- ready2 bundle SHA256:
  `05547ce58bf300575478e851cdc79dbaa8c23255ebf479c126d45d907c3aaf3f`.

No kernel, runtime, initramfs, AP archive, rollback, observer protocol, Odin
wrapper, transport, or recovery source changed.

## Attended execution note

The candidate calls `quiet_park()` after both terminal success and terminal
failure. It does not reboot itself. After bounded observation completes, the
operator must physically enter Download mode so the same Process v2
transaction can send the already-authorized exact rollback. Waiting for an
automatic reboot is incorrect.

The P2.74 USB sidecar remains diagnostic and should cover candidate flash,
observation, physical recovery Download, rollback, same-run recovery if
needed, and final health.

## Rollback inventory deviation

The repeated post-rollback inventory deviation remains unresolved at its exact
inner errno. A prior review correctly identified a plausible USBFS
re-enumeration race, but its named `_default_device_identity()` path is not the
active Process v2 observer. The active path is
`s22plus_odin_usbfs_identity.capture_inventory()`, where a node can disappear
or change between glob, two `stat` calls, and birth-time collection.

Do not modify frozen USBFS or recovery code before this transaction. If the
deviation recurs, preserve the sidecar and durable journal, then resume only
the state-allowed `--recover` branch. A later bounded fix must target the
measured inventory path and be based on the captured inner failure.

## Privacy correction

The E3 gadget serial is a synthetic value derived from the candidate run
identity, not the physical device serial. Private sidecar storage and public
redaction remain required because the same capture spans stock Android,
Download, and rollback enumeration, which can expose unrelated host-visible
identifiers.

## Next step

Run connected D0 against ready2. D0 grants no F1 authority. If D0 passes, one
new exact approval must bind the new ready2 manifest and bundle; no approval
or run directory from P2.72 may be reused.

```bash
MANIFEST=workspace/public/src/device-action/manifests/s22plus_fyg8_p276_process_v2_ready_2.json
LIVE=workspace/public/src/scripts/revalidation/device_action_f1_live_v2.py
PYTHONPYCACHEPREFIX=/tmp/p276_f1 python3 "$LIVE" --validate --manifest "$MANIFEST"
PYTHONPYCACHEPREFIX=/tmp/p276_f1 python3 "$LIVE" --prepare --manifest "$MANIFEST"
```

Stop after `--prepare` and return its exact fresh approval token to the
operator. Do not invoke `--execute` without that approval.
