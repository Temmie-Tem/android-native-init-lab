# S22+ P407 pre-handoff observation — H0, 2026-09-26

## Selected unit

P407 `v0.4.0-rc.7` measures the installed-bootstrap preparation before a writable
mount or Debian init handoff. P406 proved a currently clean matching root and
closed healthy on original A; it did not locate P404/P405's earlier stop. This
candidate preserves P405's exact 81 module bytes, order and parameters, fixed
checker, two root verification passes, mdev scan and loader checks, then
returns its result through the existing native observer independently of Debian
NCM/SSH. The loader children now explicitly run unprivileged; that diagnostic
privilege difference is not a claim of byte-identical P405 execution.
The combined P407 ramdisk also lacks P405's `/etc/mdev.conf`, so the fixed
`mdev -s` uses BusyBox's default RAM device-node rules. This may change node
creation/permissions during measurement; partition protection and the later
complete `/dev` release remain mandatory. The result is not a byte-identical
reproduction of P405's whole preparation environment or proof of its old cause.

The [separate preflight capability](../operations/S22PLUS_NATIVE_PREFLIGHT_V1.md)
allows only one attended V3 `preflight`, at most 1800 seconds, and one original-A
return. Its automatic measurement is owned by the fresh N transfer intent;
the later result read cannot start or repeat it. This H0 result opens no grant
and performs no device effect. All previous consumed candidates remain consumed.

## Implementation and evidence boundary

`S22_DEBIAN_PREFLIGHT` selects a diagnostic variant of the actual `handoff.c` /
`target.inc.c` preparation. Entry-41 RAM block RO and ioctl/sysfs readback precede
both mounts; actual dev_t, ext4 and mount flags are verified. Root, installation
records and loader inputs remain bound to P401. There is no writable mount,
archive extraction, shutdown overlay, mount move or switch_root branch in the
resulting binary. The retained P405 BusyBox is an additional immutable `/busybox`;
the native observer's existing `/bin/busybox` stays byte-identical.

Child output, exec framing, actual wait, process-group settlement and ordinary
cleanup are separate checks. All borrowed descriptors and preparation mounts
are released; protected superblock/GPT readback must remain unchanged. A sealed
anonymous fd carries one fixed record and bounded log across `exec /init`.
The shared early gate binds intent, run, metadata/seals and current boot before
the observer can proceed. The observer adopts exactly the already-loaded 81
modules without reinsertion. Prior temporal module/provider witness calls are
omitted; checkpoint positions mean adopted availability only in this profile.
The existing authentication, fixed health, DETACH and CONTROL remain.

There is deliberately no observer until every module and all required cleanup
are proved. A partial module load, timeout, overflow or unsettled child parks
for attended physical original-A recovery. A complete record can locate a
synchronous preparation stop; missing output remains NO_PROOF. Even a complete
preflight proves neither the subsequent root transition nor Debian PID 1/SSH.

## Validation

- Actual ARM64 production init/reader and native observer compile; packaged A/B
  boot images/APs are byte-identical. Qualification parses the actual AP and
  joins every selected helper, module source and immutable ramdisk member.
- Recompiled P401 installer and P405 installed-only paths are byte-identical to
  their retained binaries. The conditional extension does not rewrite them.
- The independently parsed, hash-bound original P401 boot matches the retained
  metadata/content manifests, BusyBox and checker used by the new helper.
  Target-plan, root binding and filesystem seal regenerate from its artifact
  declarations without input drift.
- Real ARM64 Linux VM: completed preparation, dirty root rejection before
  mount, and directory-checksum rejection all produced their exact settled
  records. Complete preparation proved partition RO while whole disk and
  userdata remained writable. All three writable backing disks were unchanged.
- Actual shared child runner: exec failure, exit 23 and signal termination
  returned settled negative records; signal termination did not count as exec.
  Output overflow, a remaining descendant and timeout parked without admitting
  the observer. The shared gate was recompiled and matched its tested VM binary.
- 87 focused parser, actual C/PTY, task, owner, adapter and Android32 tests pass
  with no errors or skips. Faults cover lost result, no extra read effect,
  no admission/replay and health-only continuation without another A transfer.
- Selected Python compiles, tracked diff whitespace checks and repository
  boundary checks pass. A90/S20+ were not contacted by this work.

The VM substitutes virtual block discovery and omits physical module insertion;
it is not Samsung execution proof. The physical qualification helper is
byte-identical to the physical producer used to qualify the VM source variant.

## Retained private evidence

Evidence base: `workspace/private/outputs/s22plus-prehandoff-probe-p407-h0-20260926-1/`.
The selected package is under `s22plus-native-preflight-v1/p407/build-5/`.
Earlier failed H0 construction attempts remain separate and are not candidates.

| Evidence | SHA-256 |
| --- | --- |
| Actual selected AP | `4daa92eb76a69cb43b9351b48488638f62914f53b5bc392616509b781d1cc0d1` |
| `qualified-1/image.json` | `a3bddd5ba0b64588c98c7216eb2b8b1c90ebbbfad62966d831a946e4c152fc38` |
| `vm-qualification.json` | `d1e155f036f8c8cc2a70da85e55d51edb743e1636031fe0d6d5e50919165d66a` |
| `gate-join-1/result.json` | `620caff4d994310f5957147d96174382e1fce5d2ebd6b8dc2ae09ab0e955989c` |
| `final-review-request-1.json` | `45a9f41220f71ba7e184885039d0fdf2538954827c7fc3d1d3a4d2282a95b807` |
| Independent `PASS_GO` | `0a17228d3aba151607e491413abadd94a6904823e9b6fff602bd648f8304b790` |
| `prepared-1/ready.json` | `2d49fdc8927179e8ab2116a764184a76cc9772b3f16d799f44b0111642382431` |
| Prepared task | `20e6ab23b7000dc60bc933abb5d7c3ef911df0661658b634b7221f38018fe71f` |

The request binds 74 execution sources, 162 runtime sources and 226 unique
read-only saved source copies before any device effect. Raw logs, generated
bindings, filesystem identifiers and module/kernel artifacts remain private.
The [independent capability review](../../workspace/public/src/device-action/bindings/s22plus_native_preflight_v1_review.json)
is `PASS_GO`. Fresh fixed foreground D0 preparation rederived healthy original
Android root brackets, shell-v2, exact full GPT and 34,357,624,832-byte Android32
capacity. The concrete one-operation/1800-second task is ready; no grant or
P407 image transfer has started. Neither readiness nor this report supplies
the required returned finite attended start.
