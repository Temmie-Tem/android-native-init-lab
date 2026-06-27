# Stage C charter (delegated to the loop): confirm a patched-in direct `bl` executes under RKP_CFP

**Operator-delegated task.** RECON only: empirically confirm that a **new direct `bl` call**
injected into kernel `.text` boots AND executes under Samsung RKP_CFP — the last open Tier-2
gate. This is the grindy part (locate `printk` reliably, encode a ROPP-correct injection, iterate)
that suits the autonomous loop. **Not exploitation**: no grooming, no EL1, no UAF, no kernel write
beyond this one observable logging hook. Stays in the recoverable envelope, rollback `v2321`.

## What is already proven (don't redo)
- Tier-2 **Stage A** (a `.text` patch boots under RKP) and **Stage B** (patched code takes runtime
  effect: `kgsl_pwrctrl_num_pwrlevels_show` constant 5→99→5) are DONE. See
  `KERNEL_SECURITY_TIER2_TEXT_PATCH_RKP_VIABILITY_2026-06-28.md`.
- Analytical answer (favorable, the loop is confirming it): a **direct `bl`** is PC-relative, NOT an
  indirect branch, so JOPP (magic `0x00be7bad`, gates `blr`/`br`) does not apply; the callee
  self-handles ROPP. Only an indirect `blr` would need JOPP. Verified the ROPP prologue pattern on
  real functions: `eor x16, x30, x17 ; stp x29, x16, [sp,#-N]!` (key in reserved reg `x17`),
  epilogue `ldp x29, x16, [sp],#N ; eor x30, x16, x17 ; ret`.

## The blocker the loop must solve first: reliably locate `printk`
The in-image kallsyms map (extract with
`workspace/public/src/scripts/revalidation/a90_stock_kallsyms_extract.py --kernel <unpacked kernel>`)
gives `printk @ 0xffffff800813be60`, but its **address→file-offset calibration is unreliable** here:
two candidate constant DELTAs differ by exactly `text_offset` (`0x4ef4`), and neither maps the map's
`printk` address onto real `printk` code (one lands on a clean entry that takes an `int` first arg —
not `printk(const char *fmt, …)`; the other lands mid-function). **Do not trust the map address for
the `bl` target.** Locate `printk` by SIGNATURE and verify by disassembly:
- `printk(const char *fmt, ...)`: prologue must save `x0` as a 64-bit pointer (not `mov w*, w0`
  truncation), set up varargs, and the body must `bl vprintk`/`vprintk_func` and reference the log
  buffer. The map's `printk`→`vprintk` link offset is `+0x6f0` (DELTA-invariant), so the real `printk`
  is a function-entry that contains a `bl` to `entry+0x6f0`. Use that invariant to pin it.
- Cross-check: find an existing caller's `bl <printk>` and decode its PC-relative target (DELTA-free).
- Pin the file↔vaddr DELTA empirically from a KNOWN anchor: the num_pwrlevels display instruction
  `sub w3, w8, #1` (`51000503`) is at **kernel-file offset `0x8a6334`** (Stage B patched it to
  `mov w3,#99`=`52800c63` and `/sys/class/kgsl/kgsl-3d0/num_pwrlevels` read 99). Whatever DELTA places
  the chosen injection site and the verified `printk` in ONE consistent space is the correct one; the
  `bl` offset = `printk_vaddr - blsite_vaddr` in that space.

## Injection design (ROPP-correct, observable, benign)
Overwrite a **reachable, benign sysfs show** with a function that logs a marker, so reading the node
prints it. Recommended target: the num_pwrlevels display function (contains the `sub` at file
`0x8a6334`; triggered by reading `/sys/class/kgsl/kgsl-3d0/num_pwrlevels`). Confirm its entry (the
`eor x16,x30,x17` prologue, preceded by the `0x00be7bad` JOPP magic word) and its byte extent (to the
next magic/entry) so the injected body fits. Injected body (ROPP-correct so CFP is satisfied; keep
`x17` untouched; do NOT patch a `ret`/`blr`):
```
eor  x16, x30, x17           ; encrypt return addr (ROPP)
stp  x29, x16, [sp, #-16]!   ; save
mov  x29, sp
adrp x0,  <marker_str_page>  ; format string (NO % specifiers)
add  x0,  x0, #<off>
bl   <printk>                ; the test: a patched-in DIRECT call
ldp  x29, x16, [sp], #16     ; restore
eor  x30, x16, x17           ; decrypt return addr (ROPP)
mov  w0,  #5                 ; fake return length (benign)
ret
```
Marker string: reuse an existing distinctive no-`%` NUL-terminated rodata string (find one + its
vaddr), or overwrite a few bytes of unused rodata padding to spell a unique marker and point `x0` at
it. Pick something greppable like `A90TIER2C\n`.

## Boot image build (same method as Stage A/B — minimal diff)
Direct-patch the `v2321` boot image kernel bytes (kernel begins at boot-image offset `0x1000`; add the
kernel-file offset), then recompute the Android boot header v1 `id` at offset `0x240`:
`sha1(kernel || u32le(kernel_size) || ramdisk || u32le(ramdisk_size) || u32le(0) || u32le(0))`. Verify
the diff vs clean v2321 is only the intended kernel bytes + 20 id bytes. `chmod 600` the image.

## Test procedure (bounded, recoverable)
1. Flash via `native_init_flash.py <img> --from-native --expect-sha256 <sha> --expect-version v2321`.
2. Boot; `selftest fail=0` (proves the patched kernel boots).
3. `hide`/menu-settle; `echo 0 > /proc/sys/kernel/panic_on_oops` (safety net: a wrong `bl` oopses the
   reader task, NOT the device).
4. Read `/sys/class/kgsl/kgsl-3d0/num_pwrlevels` (triggers the injected show).
5. Capture `dmesg | tail` via serial `cmdv1x`. **Marker present → SUCCESS: a patched-in direct `bl`
   executed under RKP_CFP (Tier-2 code injection viable).** Oops with no marker → wrong `printk`
   address or CFP issue (device survives); fix and retry.
6. Restore `panic_on_oops=1`; rollback to clean `v2321`; confirm `fail=0`.

## Guardrails (hard)
- RECON only. No grooming/primitive/UAF/EL1. No `ret`/`blr`/CFP-site patches. Preserve `x17`.
- The injection runs on sysfs READ, not boot — worst case is a survivable oops under
  `panic_on_oops=0` or a recoverable bootloop; rollback `v2321` always.
- **Fails twice on the same approach → STOP** and leave a report (do not retry-loop flashes).
- Do not touch forbidden partitions; boot-partition-only via the checked helper with readback verify.
- This is a focused side-quest; it does not replace the SoftAP roadmap.
