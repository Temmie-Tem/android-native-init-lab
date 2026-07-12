# S22+ FYG8 R3C1 Artifact Reproduction

Date: 2026-07-12 KST

Target: `SM-S906N/g0q/S906NKSS7FYG8`

Verdict: `PASS_R3C1_ARTIFACT_REPRODUCED_HOST_ONLY`

This unit constructed and independently checked the R3C1 unpatched rebuilt-
kernel candidate. It performed no device contact, USB enumeration, Download
transition, reboot, transfer, or flash. It creates no live policy and grants no
live authorization.

## Construction Contract

The builder starts from exact live-proven R3C0 raw boot SHA256
`384efeb0f81534cbfaf3643f42e34fb6e01fe6f0b6bf80139a047a1f9a71f29f`
and replaces only byte interval `[4096, 41495040)` with exact R2 Full-LTO Image
SHA256
`9110a7722f28f075c5cb09789710341b44956147fa05867d05e5b3e7d024770d`,
size `41490944`.

The builder requires full ARM64 Image header equality with the R3C0 stock
kernel and proves:

- zero changed bytes outside the kernel interval;
- exact R3C0 boot header and all post-kernel bytes;
- exact stock ramdisk SHA256
  `0cb87ca46b876a8765fed95bb0ce047485a14d2ec76de95af4680423b3ed1443`;
- exact R3C0 signer SHA256
  `a1217a3a4409ffe17750dd15bc242732bca762c9313c45f8672deb400c0c9b94`;
- exact stock vbmeta SHA256
  `2128d4fa64fdbed386f8cf628e1df89b1161a60a59aec985bb28a5770873561d`;
- byte-identical R3C0 AVB footer;
- deterministic USTAR boot-only AP containing exactly `boot.img.lz4`;
- Odin parse gate restricted to fixed nonexistent path
  `/dev/bus/usb/999/999`, with failure before device open.

`PATCHVBMETAFLAG` is rejected. The stale AVB payload hash is intentional and is
required by the independent checker; the existing signed vbmeta bytes are
preserved and do not authenticate the replaced kernel.

## Reproducible Outputs

Reproductions A, B, and final-source C are byte-identical on all four generated
axes:

| Artifact | Size | SHA256 |
| --- | ---: | --- |
| raw `boot.img` | `100663296` | `e1f0be9933e9c76d881a2cc39c0431bf54930ee0f216f55de4d7a166a60d120c` |
| `boot.img.lz4` | `27714855` | `d00e12c6d9c2d1f4100d454ba9789dcb1d782da1d72a62caf9a7664402da9efd` |
| boot-only `AP.tar.md5` | `27719721` | `023d7780e11363bd152900e28279233a0fd66ce8dd8902417d23eb781f613fb4` |
| `manifest.json` | deterministic | `2596b5f1c6a8fa88d8ee75224c8a039764c67453875789744a7087db2fb97bb0` |

The actual R3C0-to-R3C1 delta contains `9098520` changed bytes. First changed
offset is `70520`, last is `41491833`, and outside-kernel changed byte count is
exactly zero.

## Independent Static Check

Static checker source SHA256:
`917b12f82dc5525b84cf2627379a80e49d921b6c33ca79fe3fc5c6a9ece6a514`.

Reproductions A, B, and C each returned `PASS_R3C1_STATIC_CONTRACT`. The checker
independently rebuilt the expected candidate from exact stock, R3C0, and R2
bytes; validated all boot geometry and AP/LZ4 round trips; required stale AVB;
and rehashed full FYG8 firmware plus Magisk and stock rollback chains. Final C
static-check JSON SHA256 is
`8897ae2f185f768b492108ef8b325aa4d2fb9631c96d70c43998ead4105b4acd`.

## Independent Review

Claude Opus usage was checked before and after review: current-session usage
`60% -> 76%`, reset 2026-07-13 01:50 KST. The review returned GO with no high or
critical finding. It independently measured zero outside-kernel changes,
verified all preservation hashes and A/B identity, and confirmed no live-
authorization or real-device Odin path.

Its one LOW finding was a builder input TOCTOU: the initial implementation
hashed R3C0/R2 files and then read them again. The final builder now reads each
artifact once, validates the exact in-memory bytes used for construction, and
final-source reproduction C remains byte-identical to A/B.

## Source And Tests

- builder:
  `workspace/public/src/scripts/revalidation/build_s22plus_fyg8_r3c1_candidate.py`
- builder SHA256:
  `11f6e270ba5c63b498b2072573bb8a870f6dd031b5fb407268b6d39c55577596`
- focused test SHA256:
  `229ce3766d898cc5b93448be84dbc18ab798fac0724969dc030992caa5edda5d`
- focused and related tests: `25/25` PASS
- `py_compile`: PASS

## Boundary

No generated boot image, AP, manifest, or raw static-check JSON is committed.
They remain private outputs. R3C1 is artifact-ready for a separately designed
and reviewed one-shot live helper, policy draft, connected read-only preflight,
and fresh attended approval. This report does not authorize any of those live
steps.
