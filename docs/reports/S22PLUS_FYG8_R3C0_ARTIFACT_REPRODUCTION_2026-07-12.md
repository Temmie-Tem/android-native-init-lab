# S22+ FYG8 R3C0 Artifact Reproduction

Date: 2026-07-12 KST
Target: `SM-S906N/g0q/S906NKSS7FYG8`
Scope: host-only artifact construction and static validation; no device contact,
USB enumeration, transfer, flash, or live authorization

## Verdict

`PASS_R3C0_STATIC_CONTRACT` for two clean, byte-identical reproductions.

R3C0 is a **synthetic minimal signer-normalized control** built directly from
the exact FYG8 stock boot image. It preserves the complete stock header, kernel,
ramdisk, alignments, GKI signature, vbmeta, and padding. It changes only:

- bytes `[43483152,43483664)` to zero after the 16-byte
  `SEANDROIDENFORCE` marker; and
- AVB footer `original_image_size` from `43483664` to `43483152`.

This host PASS does not prove the synthetic carrier boots. It creates the exact
future R3C0 live discriminator. No R3C1 artifact was built.

## MagiskBoot Execution Correction

The first builder attempt intentionally required an actual pinned MagiskBoot
v30.7 no-change output to equal the two-field model. It failed closed. The
actual output:

| Field | Stock | MagiskBoot no-change output |
|---|---:|---:|
| ramdisk size | 1,978,967 | 1,653,775 |
| signature start | 43,479,040 | 43,151,360 |
| signer marker | 43,483,136 | 43,155,456 |
| footer original size | 43,483,664 | 43,155,472 |
| vbmeta offset | 43,487,232 | 43,159,552 |

Output SHA256 was
`f173500c9c9f2dcbe1272e1e4557c6d5818cbc06ab6484a4d235a4ef0b9dc81f`.
The kernel and relocated vbmeta bytes remained exact stock, but the ramdisk was
recompressed and the layout moved. This disproves the earlier source-only claim
that a real MagiskBoot no-change output differs only in signer/footer fields.

The final builder therefore pins MagiskBoot as provenance for marker behavior
but does not execute it. It directly constructs the two-field synthetic control
from exact stock bytes.

## Builder And Packaging

| Item | SHA256 |
|---|---|
| builder source | `2e9e7b9e07305fcc69e01a727f3c6405284530cea85fe184ca6f47e1fcb2806e` |
| builder tests | `4089cac44cd1156c0d2ad5e0c5f492f640cd63944b00ccba71aba4a1ac46441b` |
| independent R3 checker | `917b12f82dc5525b84cf2627379a80e49d921b6c33ca79fe3fc5c6a9ece6a514` |

The builder:

- pins stock boot, MagiskBoot provenance, LZ4, and Odin4 by exact size/SHA;
- refuses an existing output path and rejects `PATCHVBMETAFLAG`;
- writes into a private temporary directory and atomically promotes only a
  complete result;
- uses LZ4 `--content-size -B6`, matching FYG8 `FLG=0x6c`, `BD=0x60`;
- creates one deterministic USTAR member `boot.img.lz4` plus exact 41-byte MD5
  trailer;
- invokes pinned Odin4 only with `/dev/bus/usb/999/999`; PASS requires AP
  recognition followed by failure before device open.

Two intermediate package attempts failed closed before output promotion:

1. no LZ4 content size: `Contens size is not defined`;
2. default LZ4 B7 block: `Unsupported block size`.

The final B6/content-size AP reached only the fixed nonexistent device path and
returned the expected `No such file or directory` / `usb device Fail`. No
connected device was enumerated or contacted.

## Reproduction Pins

| Artifact | Size | SHA256 |
|---|---:|---|
| `boot.img` | 100,663,296 | `384efeb0f81534cbfaf3643f42e34fb6e01fe6f0b6bf80139a047a1f9a71f29f` |
| `boot.img.lz4` | 27,721,424 | `61f5d9f6bdf4ebba538234f8c0621c0a1219099cb213150ad3a0299c76e2212e` |
| `AP.tar.md5` | 27,729,961 | `8f2b16d3ee8932ff927e06fee8956f975ec3f9e5cc0ef16337e00ad5108d3c00` |
| `manifest.json` | 4,031 | `febffce465ea639d4d4751170bf280ae148ca3431f560aae6ecd8ea08f12ced0` |
| Odin parse record | 164 | `dfc0388f8bf05b6fb5f4391fe401ecf058fe947b98fac165bf46a7846a8f1d3a` |

Reproduction A and B match byte-for-byte for all five files. The AP tar-prefix
MD5 is `34bd084671b5492f17aaa0938df32a36`.

## Independent Static Validation

Both A and B independently rehashed the complete FYG8 six-file firmware set,
R1/R2 evidence, stock boot geometry, rollback AP chains, DTBO, recovery, and
tools. Both returned `PASS_R3C0_STATIC_CONTRACT`:

| Audit | Size | SHA256 |
|---|---:|---|
| reproduction A JSON | 16,051 | `2991391b2319cad52fe26febb03aaa0176f31c42a16d66a15eee3b1bdc344110` |
| reproduction B JSON | 16,051 | `6315d92b5c81cdbfceca0f9cdf1c6952994fa786c12eea91586c7229e983f85f` |

The audit JSONs are semantically identical after removing path fields. Each
proves exact stock kernel, ramdisk, and vbmeta; expected stale payload digest;
one strict LZ4 frame with no trailing data; and one canonical boot-only AP
member.

Related regression set: 31/31 PASS.

## Independent Review

Claude Opus received the builder, tests, checker, both audits, and corrected
MagiskBoot execution evidence under read-only tools. It returned GO for this
host-only source/reproduction unit with no code blocker. Its documentation
findings were applied here and in the design/roadmap: synthetic provenance is
now explicit, the known Magisk stale-vbmeta boot is not treated as proof that
this different shape boots, and stale artifact status was removed.

Usage before/after: current session 10% to 22%, current week 48% to 49%, cost
`$2.15`.

## Safety State And Next Gate

- generated images and APs remain private and uncommitted;
- no `AGENTS.md` R3C0 live exception exists;
- no device contact or flash occurred;
- R3C1 construction and all live work remain unauthorized;
- next bounded unit is R3C0 live-policy/helper design and independent review,
  followed by a fresh explicit attended approval before any device action.
