# S22+ FYG8 R4W1-D connected D0 and preparation pass

Date: 2026-07-21 KST
Scope: CONNECTED READ-ONLY
Status: exact F1 binding prepared; fresh operator approval pending

## Draft connected D0

The draft bundle SHA256
`3a068ce78d045e943b878fa841593baad81c6e92c3153cf06e88bc15001aa498`
passed one connected read-only D0 run. The strict validator reopened the result
and raw observer from
`workspace/private/runs/device-action-d0-v2/d0-20260721T100128-1784628088792726672`.

Load-bearing evidence:

- verdict: `PASS_DEVICE_ACTION_D0_V2_CONNECTED_READ_ONLY`;
- result: 2,945 bytes, SHA256
  `e15f4fe905e475939e670fb8dac0b34484456fddcf35e88efb06299bfa16a03a`;
- `/proc/last_kmsg`: 2,097,136 bytes read to EOF, empty stderr, SHA256
  `bbc7c88c42fbaeaf478075df63e5a839384d4d482c22fb2365ccee0389d9497b`;
- D exact marker count zero and D family count zero;
- exact FYG8 Android boot complete, stopped boot animation, Magisk root, known
  boot, stock vendor_boot/DTBO/recovery, orange verified boot; and
- no Download endpoint before or after collection.

## Readiness promotion

The ready manifest is a data-only derivative of the reviewed draft. Exactly
three top-level fields changed: `manifest_id`, `run_id`, and `status`. Candidate
AP, rollback AP, target profile, timeout, marker, family, source, and health
contract are identical.

- ready manifest: 1,120 bytes, SHA256
  `5ec7e479715ffdaa1f8853a10e31b70599e6bd12c93122d33c3a2de22c478cf2`;
- ready bundle SHA256:
  `872da8ec972a230d928779cc78ba52cfc4d2a12f07013559baa7dae93614eb4e`;
- status: `ready-for-f1-approval`;
- H0, D0 offline, and F1 live offline validators: PASS.

## F1 preparation

Process v2 `--prepare` repeated the complete connected read-only D0 and created
the private run at
`workspace/private/runs/device-action-f1-live-v2/f1-2026-07-21T100308522934Z-1784628188522972001`.
Strict `load_prepared` reopening passed.

- preparation D0 result: 2,969 bytes, SHA256
  `f75dd43f532f9245b7eff46b193c678ee18a8d6ad5c3d20ec692ce65f9f3eff9`;
- observer: same 2,097,136-byte clean baseline and SHA256 as the draft D0;
- `prepared.json`: 5,454 bytes, SHA256
  `80459c3afce6ad8ce0d110fecd399d9d7a1ebe7d960316970802362b7b28f3ec`;
- execution closure SHA256:
  `92298ec1c84adac5c235d7a2ca54328b00305a39966599166da95075899763d4`;
- approval binding SHA256:
  `16640f551d082dd89e8de57da7572c42e235abd30d0733fa050c76aa46530392`.

## Boundary

Both connected actions were read-only. Device writes, reboot requests, Download
transitions, Odin invocations, and partition transfers were all false. The
prepared result itself sets both `f1_authorized=false` and
`live_authorized=false`.

The next action is not implicit. The operator must freshly provide the exact
approval token emitted by this prepared binding. Only then may Process v2
execute one candidate attempt. That approval preauthorizes the mandatory exact
Magisk rollback so recovery cannot be blocked by a second acknowledgement.
