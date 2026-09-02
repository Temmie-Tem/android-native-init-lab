# S22+ FYG8 P3.28 authenticated command F1 no-proof

Date: 2026-09-03 KST

Target: `SM-S906N / g0q / S906NKSS7FYG8`

Tier: attended F1

Formal verdict: `NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK`

Outcome: `p328_authenticated_framed_exec_unproved_rollback_verified`

## Result

P3.28 is closed and consumed. The exact boot-only candidate and preapproved
Magisk rollback each transferred once. The journal reached `CLOSED` at 19
records, final rooted FYG8 Android health passed, and recovery is no longer
required. Candidate replay is forbidden.

P3.28 did not prove its authenticated command channel. The candidate enumerated
as the one exact `04e8:6861` CDC-ACM endpoint on the expected candidate lane,
with the same-run Type-C partner preserved, but the observer stopped before
opening the tty. Candidate RX and TX are both zero bytes; no banner, nonce,
HMAC, BusyBox command, framed close, or caller-selected command execution was
observed.

## Timeline

- live session start: `2026-09-02T15:27:07.351377Z`;
- candidate transfer: `15:27:24.673331Z` to `15:27:26.317439Z`;
- candidate endpoint ready: `15:27:36.078940Z`;
- rollback transfer: `15:29:56.639260Z` to `15:29:58.222888Z`;
- rooted Android health ready: `15:30:46.317465Z`;
- session closed: `15:30:46.338808Z`.

There was no candidate attempt 2.

## Observer failure

The retained candidate inventory has one exact candidate endpoint at
`usb:3-1.3`, zero exact endpoints at the Android source lane, zero foreign
candidate-like endpoints, and continuous Type-C partner identity. The guard
process remained armed and later released normally.

The pre-open tty property capture is 131 bytes and contains `DEVPATH`,
`DEVNAME`, major/minor and `SUBSYSTEM`, but neither
`ID_MM_DEVICE_IGNORE=1` nor `ID_MM_PORT_IGNORE=1`. The P3.28 read path probes
those properties once and maps a healthy guard with missing properties to
`identity-mismatch`; therefore it returned before opening `/dev/ttyACM0` and
before creating any authenticated protocol traffic.

The same-run udev trace resolves the apparent contradiction. Kernel `ttyACM0`
add occurred at monotonic timestamp `91466.152759`; the completed udev tty add
appeared at `91466.168553`, about 15.8 ms later, and includes both required
ignore flags. This supports a pre-open udev-property readiness race, not a
wrong device or wrong candidate identity. The classification name is broader
than the actual retained failure.

The proportional successor repair is to keep both ModemManager flags mandatory
but allow one short bounded settle loop after the exact endpoint is selected,
while continuously retaining the exact endpoint and guard identity. It does
not require a new wire protocol, key design, USB function, topology rule, or
recovery path.

## Durable evidence

Run directory:
`workspace/private/runs/device-action-f1-live-v2/p328-ready1-prepared-20260903-1`.

- candidate result: 2,079 bytes, SHA-256
  `f6105d95e5682346a8f19c40d2b793cb45f7a8013b2e62d156ba198327ff7973`;
- candidate receipt: 6,023 bytes, SHA-256
  `0080dbc71411861d27348f8c978073d96cf1e5a37e8739d5ababbd6dd0e24608`;
- candidate raw: 0 bytes, SHA-256
  `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`;
- P3.24 lane receipt: 3,141 bytes, SHA-256
  `a0104b4c5b45e59e915db5bd282f0c95d4d18688b4d9b56e5578aa1b570e02c8`;
- rollback result: 2,030 bytes, SHA-256
  `c40f18fc86f2620654aa25a5b47acc06eabad67dc230fac048859e1764ba4bd2`;
- final live state: 31,457 bytes, SHA-256
  `36f2f44ea6208a04182a65389801845a3d987123ac16ed4c5397bedcd5b0fb29`;
- final live result: 35,135 bytes, SHA-256
  `aed4dc0c50ec496276467256fec833a9b6be6a77cc21758bdd46e1d84fdc329a`.

The 35,135-byte result published normally through the new lifecycle-scoped
64 KiB final-result writer. Journals, state, receipts and all other ordinary
records remained under the unchanged 32 KiB bound. This closes the recurring
post-terminal publication defect without a run-specific finalizer.

## Claims

Proved:

- exact candidate and rollback transfers, 1/1;
- exact P3.28 CDC-ACM candidate enumeration and same-run Type-C continuity;
- mandatory rollback, final rooted Android health, and a closed 19-record
  journal;
- normal publication of the final result larger than 32 KiB.

Not proved:

- P3.28 banner, random challenge, HMAC authentication or framed session;
- BusyBox command execution or a caller-selected command;
- an interactive shell, PTY, resident service or standing command authority.

P3.28 is never replayable.
