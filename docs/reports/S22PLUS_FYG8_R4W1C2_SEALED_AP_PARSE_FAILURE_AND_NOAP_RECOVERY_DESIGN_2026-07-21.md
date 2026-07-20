# S22+ FYG8 R4W1-C2 Sealed AP Parse Failure And No-AP Recovery Design

Date: 2026-07-21 KST

## Verdict

`HOST_ROOT_CAUSE_PROVEN_NO_DEVICE_WRITE_NOAP_RECOVERY_SOURCE_PASS`

The R4W1-C2 one-shot was consumed, but candidate, Magisk rollback, and stock
cleanup each failed before an Odin device session began. The handset remains in
normal Samsung Download mode and the built-in helper is correctly blocked by
the durable stock-cleanup intent.

## Exact Failure

All three different APs produced the same record:

- return code `1`;
- stdout size `51` and SHA256
  `7f6162459d49213e9d36485eaa1e7748492b484f4538db45ef50ab4d9f31adb4`;
- empty stderr; and
- no `rollback_transfer_finished` receipt.

The digest is the exact preimage:

```text
Reboot into normal mode
Fail parse /proc/self/fd/7
```

The helper copied each AP into a sealed memfd and passed
`-a /proc/self/fd/7`. A USB-hidden Bubblewrap reproduction showed that an
extensionless AP pathname immediately returns `Fail parse`, while an otherwise
identical `.tar.md5` pathname reaches Odin's file-check path. The live output
contains no `Setup Connection`, so no Odin device session or partition transfer
started. This is a host invocation bug, not a candidate-kernel result.

## External Cross-Check

- Samsung describes Download mode as a technician diagnosis/repair state and
  documents exiting it with Volume Down plus Side/Power for about seven seconds:
  <https://www.samsung.com/us/support/troubleshooting/TSG01212623/>.
- Samsung Knox calls Download mode the ODIN firmware-recovery path:
  <https://docs.samsungknox.com/dev/knox-sdk/faq/standard-features/>.
- Heimdall documents that Download mode exposes Samsung's Loke implementation
  of the Odin 3 protocol over USB:
  <https://github.com/Benjamin-Dobell/Heimdall>.
- The Linux Odin4 distribution README shows `-a AP_XXXX.tar.md5`, `-d` for an
  exact device path, and `--reboot` as a separate reboot operation:
  <https://github.com/Adrilaw/OdinV4>.

The Odin4 repository is a community distribution mirror, not an official
Samsung source. Its CLI description nevertheless matches the exact local
binary help and the host-isolated behavior.

## Recovery Design

The safest recovery does not attempt another AP alias or partition transfer.
It executes only sealed Odin `--reboot -d <measured-node>` after reopening the
exact incident and binding the same topology and usbfs identity. The helper:

1. pins the consumed state, both results, stock intent, three failed Odin logs,
   transaction index, and timeline;
2. reconstructs and verifies the exact 51-byte parse-failure stdout;
3. measures the same `2-1.3` Download endpoint and immutable usbfs node;
4. consumes a separate one-shot recovery state;
5. revalidates the endpoint after consumption;
6. launches argv with no AP or payload option and only the Odin fd inherited;
7. bounds and durably saves stdout/stderr before interpretation; and
8. requires exact FYG8 Android, Magisk root, known boot, stock vendor_boot/
   DTBO/recovery, original USB binding, and no Odin endpoint.

The command performs a bootloader reboot only. It does not write a partition.

## Static Qualification

- focused tests: `13/13` PASS;
- actual offline verdict:
  `PASS_R4W1C2_NOAP_REBOOT_RECOVERY_SOURCE_HOST_ONLY`;
- policy inactive during qualification;
- recovery one-shot unconsumed;
- device contact, device write, reboot, Odin transfer, and flash all false.

The exact policy draft is
`docs/operations/S22PLUS_FYG8_R4W1C2_NOAP_REBOOT_RECOVERY_EXCEPTION_DRAFT_2026-07-21.md`.
It is not live authority until independently reviewed and installed exactly in
`AGENTS.md` with a new operator acknowledgement.

## Later Disposition

The policy was never installed. After eight repair rounds, the ninth review was
intentionally stopped before verdict and the no-AP branch was closed as
disproportionate to a transient no-payload reboot. The final implementation is
preserved in commit `eea4c23c`; its helper, test, and draft were removed from
the active tree. This design is historical evidence and grants no authority.
