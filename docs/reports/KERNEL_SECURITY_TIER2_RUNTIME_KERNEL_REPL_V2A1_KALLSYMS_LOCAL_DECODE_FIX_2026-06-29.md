# Kernel Security Tier-2 Runtime Kernel REPL v2a1 Kallsyms Local Decode Fix

- Cycle: `TIER2_REPL_V2A1`
- Date: `2026-06-29`
- Scope: host-only tooling fix; no device action, no flash
- Base boot image: `workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img`
- Base SHA256: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`

## Problem

Gate-2 caught that v2a0 only made the known semantic overrides look correct. The pure
BASE_RELATIVE decode kept globals correct, but KGSL local sysfs functions still resolved to wrong
post-transform entries:

- `kgsl_pwrctrl_num_pwrlevels_show` decoded to `0xffffff800892b1e4`, which is inside the previous
  function tail.
- `kgsl_pwrctrl_gpu_busy_percentage_show` decoded to `0xffffff800892cf34`, a different function.

## Fix

Updated `workspace/public/src/scripts/revalidation/a90_stock_kallsyms_extract.py` to:

- keep Android boot and `UNCOMPRESSED_IMG` unwrap plus BASE_RELATIVE raw-Image decoding;
- parse kallsyms compressed-name lengths as one- or two-byte ULEB128 records;
- stop using semantic overrides in `render_system_map`;
- convert semantic overrides into cross-checks: decoded address must already equal the force_no_nap
  function-pointer locator and the plain-printk signature locator, or extraction raises;
- repair the KGSL local sysfs run by anchoring the legacy local slot for
  `kgsl_pwrctrl_num_pwrlevels_show` to the live RKP/ROPP entry stream, checking the
  `sub w3,w8,#1` marker, then walking the contiguous KGSL local run by ROPP entry ordinal.

## Final Resolved Symbols

| Symbol | Address | Decode source |
| --- | --- | --- |
| `kgsl_pwrctrl_force_no_nap_show` | `0xffffff8008927344` | pure decode, `rkp-ropp-local-run`; semantic cross-check agreed |
| `kgsl_pwrctrl_force_no_nap_store` | `0xffffff80089273b4` | pure decode, `rkp-ropp-local-run`; semantic cross-check agreed |
| `printk` | `0xffffff800813d8cc` | plain-printk variadic-wrapper signature decode; semantic cross-check agreed |
| `kgsl_pwrctrl_num_pwrlevels_show` | `0xffffff80089262dc` | pure decode, `rkp-ropp-local-run` |
| `kgsl_pwrctrl_gpu_busy_percentage_show` | `0xffffff800892790c` | pure decode, `rkp-ropp-local-run` |
| `__kmalloc` | `0xffffff80082724bc` | pure decode, `base-relative` |
| `kfree` | `0xffffff800827276c` | pure decode, `base-relative` |
| `kallsyms_lookup_name` | `0xffffff800818452c` | pure decode, `base-relative` |

## Disassembly Checks

- `kgsl_pwrctrl_num_pwrlevels_show`: entry `0xffffff80089262dc`; contains
  `ldr w8,[x8,#1528]`, `mov w1,#0x1000`, and `sub w3,w8,#1` (`0x51000503`) at raw offset `0x8a6320`.
- `kgsl_pwrctrl_gpu_busy_percentage_show`: entry `0xffffff800892790c`; contains
  `mov w10,#0x64`, `mul w9,w9,w10` (`0x1b0a7d29`), `udiv w3,w9,w8` (`0x1ac80923`), and
  `mov w1,#0x1000`.
- `kgsl_pwrctrl_force_no_nap_store`: entry `0xffffff80089273b4`; first words are
  `sub sp,sp,#0x40` (`0xd10103ff`) then ROPP `eor x16,x30,x17` (`0xca1103d0`).
- `printk`: entry `0xffffff800813d8cc`; varargs prologue spills `x1..x7` and `q0..q7`, builds the
  `va_list`, and directly calls the printk va-list helper.

## Validation

- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile workspace/public/src/scripts/revalidation/a90_stock_kallsyms_extract.py tests/test_a90_stock_kallsyms_extract.py`
- `PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest tests.test_a90_stock_kallsyms_extract`
- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/a90_stock_kallsyms_extract.py --kernel workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img --out-map /tmp/a90_v2321_v2a1.System.map --out-json /tmp/a90_v2321_v2a1.json`

Extractor summary for v2321:

```json
{
  "decode_sources": {
    "base-relative": 147241,
    "plain-printk-variadic-wrapper-signature": 1,
    "rkp-ropp-local-run": 53
  },
  "semantic_cross_checks": {
    "kgsl_pwrctrl_force_no_nap_show": "0xffffff8008927344",
    "kgsl_pwrctrl_force_no_nap_store": "0xffffff80089273b4",
    "printk": "0xffffff800813d8cc"
  }
}
```
