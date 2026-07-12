# S22+ FYG8 R1/R2 Evidence Retention Audit

Date: 2026-07-12 KST  
Target: `SM-S906N/g0q/S906NKSS7FYG8`  
Scope: host-only evidence inventory; no build, package, device, or flash action

Status: historical R2 v1 retention snapshot, superseded by the clean R1 v3/R2
v2 reproduction and local Tier B return recorded in
`S22PLUS_FYG8_R1V3_R2V2_CLEAN_REPRODUCTION_2026-07-12.md`.

## Verdict

`PASS_METADATA_PINNED_R2_V1_SUPERSEDED_ARTIFACT_BYTES_REMOTE_ONLY`

The canonical R1/R2 result records are present locally and hash correctly. They
pin every required output, 2,397 generated modules, 15 symvers paths, and both
extra provider closures. The actual kernel outputs and symvers bytes remain on
the FX-8300 host and were not independently rehashed in this unit because
non-interactive SSH authentication was unavailable.

This is sufficient to preserve the historical R1/R2 result metadata. The R2 v1
PASS is superseded by the exact-banner miss documented in
`S22PLUS_FYG8_R1_R2_TIMESTAMP_GATE_POSTMORTEM_2026-07-12.md`. This is not yet a
complete local artifact escrow and does not replace a clean R1 v3/R2 v2 run.

## Local Canonical Records

| Record | Bytes | SHA256 |
|---|---:|---|
| R1 clean-compile result | 274,361 | `6bd78758a9285c3e898ef6a38d78222b2987c68ba74a893e6d9f9bf357a0a946` |
| R1 clean-compile timing | 849 | `4201495d50dc81b09b77262c0a9b3e40874ba6785351d453d655914cecec9ee3` |
| R1 final preflight | 5,265 | `bf863a8c070b26ccf9a8e5e44879f2b0f820ab8a93f3074f62058d80989e0ffa` |
| R1 final result | 647,397 | `027d0104ea0640b4d7faca1607dcaae4d0b1bb6af403725c9bd85e524f54b18f` |
| R1 final timing | 799 | `a8c76dd26dbd6c4a4cb1bda160cfd541115de2561828c62af88849bf8e2fd2bb` |
| R2 final result | 5,954 | `66c76073881752752c8a0eeddee03e8d6f8d63dc84109441616eda7386dea4cf` |

The records are under:

- `workspace/private/outputs/s22plus_fyg8_kernel_rebuild_r0/remote-fx8300-r1/`
- `workspace/private/outputs/s22plus_fyg8_kernel_rebuild_r0/remote-fx8300-r2/`

## Pinned Remote Outputs

| Output | Bytes | SHA256 |
|---|---:|---|
| `Image` | 41,490,944 | `e9b6717e6a25f4d65861da9771dcf49402ab0cb22ed3c3814c683d92b22ee161` |
| `Image.lz4` | 21,596,004 | `4956329693e2af27b3e5dbaf6250530c3f595098973185231154a334d65bcf02` |
| `vmlinux` | 476,910,592 | `89859ad9d6222ac52866a6bebeda23af214eff64dc25adb67705b1cfe5e904c4` |
| `System.map` | 5,072,294 | `ff24d80d62497e8eda0ee23e3a9d73c9e956ff48f1b215ed35eba4e75337087a` |
| `vmlinux.symvers` | 439,646 | `fd75413401617a427ddf6c264d0ae4f5452b46cde02b4575b9af09f19601ca19` |
| `modules.builtin` | 22,851 | `f9711ca3f001167eccec6a60924e23eecbd30f126a1a5b4121412ce4136399c4` |
| `modules.builtin.modinfo` | 144,002 | `632c673947987d480515fcf472ce152dcb97098555f7298108d0c341be5ab7a6` |
| generated `.config` | 185,325 | `6e5650226d8844fa9dd49b8f3f40d058da7e785fc357e8e5dd90eae33ebed0e9` |

The 15 recorded symvers paths collapse to ten unique byte identities. The
unique symvers payload is 1,172,615 bytes. The R3-operational retrieval set
(`Image`, `Image.lz4`, `System.map`, `.config`, and unique symvers bytes) is
69,517,182 bytes before filesystem or transfer overhead.

## Retention Tiers

### Tier A - Canonical Proof Metadata

Keep locally and remotely:

- all six records in the local table above;
- source overlay audit and transfer manifest;
- exact build wrapper and R2 auditor revisions;
- clean and final stdout/stderr/provider logs when remote access returns.

State: result/timing records local; detailed logs remain remote.

### Tier B - R3 Operational Set

Copy locally after remote authentication returns:

- `Image`, `Image.lz4`, `System.map`, and generated `.config`;
- all 15 symvers paths while retaining their path mapping, even though ten
  byte identities are sufficient for deduplicated storage;
- provider stdout/stderr for `dataipa` and `datarmnet-ext/shs`.

State: pinned by R1 result, byte retrieval pending.

### Tier C - Forensic And Rebuild Cache

Retain on the FX-8300 host unless storage pressure requires a separate review:

- `vmlinux` and built-in metadata;
- the generated `.ko` tree and intermediate Full-LTO output;
- complete build logs and dist staging.

The approximately 8 GiB `source/out` tree is a useful cache and Lane W module
source. It is reproducible, but it must not be deleted before Tier B is copied
and rehashed.

## Clean Reproduction Rule

The next clean one-shot run must not delete or rename the only canonical output
before Tier B is secured. Use a separate reconstructed work tree such as
`source-clean-final`, with its own `outputs/r1-clean-final` and
`outputs/r2-clean-final` directories. PASS requires a zero-return R1 v3 wrapper
without incremental repair and a zero-return R2 v2 audit. Whole result-JSON
hashes are not expected to match across work-tree paths or resource snapshots.
Compare normalized relative-path output/module/symvers/provider identities and
exact banner/config/CRC gates. Differences are evidence; they do not overwrite
historical records.

## Stop Conditions

- No remote deletion or cleanup before byte retrieval.
- No local claim that remote bytes were rehashed in this unit.
- No boot-image or AP construction from the pinned `Image`.
- No R1/R2 canonical replacement until the clean one-shot result is reviewed.
