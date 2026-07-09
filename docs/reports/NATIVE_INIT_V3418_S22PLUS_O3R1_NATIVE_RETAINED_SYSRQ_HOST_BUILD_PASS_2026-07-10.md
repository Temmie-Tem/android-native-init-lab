# V3418 S22+ O3R1 Native Retained SysRq Host Build

## Verdict

`HOST BUILD PASS; LIVE NOT AUTHORIZED`.

O3R1 is the smallest direct-PID1 positive control for the observation channel
needed after the O3/O3F USB misses. It emits ordered phase and return-code
records to `/dev/kmsg`, mounts only procfs, writes exactly `c` to
`/proc/sysrq-trigger`, and deliberately falls back to global PID1
`exit_group` if any gated step fails or the SysRq write returns.

No device command, reboot, flash, module insertion, sysfs/configfs write, or
partition write occurred in this unit. The generated manifest says
`live_flash_authorized=false`; there is no active O3R1 exception.

## Named Discriminator

The previous O3F result left every internal phase unobservable because its
volatile kmsg marker was followed by an indefinite park and the later manual
Download reset did not retain that marker. O3R1 asks one narrower question:

> Can a direct native PID1 record a phase marker into the already proven
> Samsung sec_debug MID retained `/proc/last_kmsg` path when it immediately
> forces a kernel panic?

O3R1 does not configure USB, load modules, mount persistent storage, write
pmsg, hand off to Android, or attempt a reboot. It must not be interpreted as
an O3 USB candidate.

## M22 Non-Repetition

M22 attempted kmsg plus SysRq before Samsung sec_debug MID was the selected
retention path, ignored the relevant syscall return values, wrote the
unnecessary `kernel.sysrq` sysctl, and could fall through to an unreliable
Download reboot/park path. Its live run was a no-hit.

O3R1 has a different fail-closed discriminator:

1. Create or preserve `/dev/kmsg` as major 1, minor 11.
2. Emit `entry-pre-proc` with the node result.
3. Mount only procfs and emit `proc-mount` with its return code.
4. Open `/proc/sysrq-trigger` and emit `sysrq-open` with the returned fd/error.
5. Emit `before-sysrq-c`, then write exactly one byte `c`.
6. If any step fails or SysRq returns, call global PID1 `exit_group`, forcing
   the kernel's init-death panic path.

This produces four bounded interpretations after mandatory rollback:

- marker plus SysRq panic: retained native kmsg channel PASS;
- marker plus init-death panic: native kmsg retained, SysRq path failed;
- init-death panic without marker: candidate executed, kmsg path failed;
- no retained candidate panic: candidate/channel remains unproven; stop.

## Static Contract

The final `/init` is a 2,440-byte stripped static AArch64 ELF. It has no
`PT_INTERP`, no undefined symbols, and uses only these raw syscalls:

```text
mknodat=33 mkdirat=34 mount=40 openat=56 close=57 write=64 exit_group=94
```

The source contains no pmsg path, sysrq sysctl write, sysfs/configfs path,
module insertion, USB setup, block-device write, reboot syscall, clone, or
Android/Magisk handoff.

## Exact Artifact

Output:

```text
workspace/private/outputs/s22plus_native_init/o3r1_native_retained_sysrq_v0_1
```

```text
source_sha256=a51fd1d87732bbcc3fa4b6ea2c9ede7ff78d423736ce3e168c059cef50626968
init_sha256=44d70f3d7ee534b6701a5a912e07febdaf21b0b4d7fabf0368c4a6f942499fdc
base_boot_sha256=2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
kernel_sha256=bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff
ramdisk_after_sha256=bc40ff00d156ce27c0dba6453f426b42cda3438aadde26908cee0b78b2441d38
boot_img_sha256=fc0dce090f454b621ed90e63dd11cfe29dad8de0fe04d3c1f138a004d9d2f6aa
boot_img_lz4_sha256=3af2ec28c2048aee8aac632c815581ded688dae256e3522eb002464514ae84a9
ap_tar_sha256=eb3819730944e68cab7355d72f2372c2dc47e88de6cb5670e94c43fe1593cbb8
ap_tar_md5_sha256=2a92008b4632a8907fec96f0d8194a8461c16060cb1d919aeba7446020c4beda
tar_members=boot.img.lz4
```

MagiskBoot no-change repack is byte-identical to the known-booting base. The
candidate preserves the kernel, replaces only ramdisk `/init`, adds no ramdisk
entry, and packages exactly one Odin member: `boot.img.lz4`.

## Reproducibility And Tests

An independent build under `/tmp/s22plus_o3r1_repro` reproduced `init`,
`boot.img`, and `AP.tar.md5` byte-for-byte, and all pinned content hashes match.
The focused O3R1 suite passes four tests, including a real freestanding AArch64
link, empty undefined-symbol table, source safety contract, builder inertness,
and final manifest checks.

## Next Gate

Create an O3R1-specific checked live helper that pins every hash above, the
known rooted Android boot SHA, Samsung sec_debug MID/enabled preconditions, the
Magisk and stock boot-only rollback APs, continuous host observers, canonical
timeline events, mandatory attended rollback, and exact retained-log
classification. Run artifact-only and connected read-only dry-runs. Only then
may a fresh SHA-pinned one-shot `AGENTS.md` exception be added for one attended
intentional-crash boot-only run.
