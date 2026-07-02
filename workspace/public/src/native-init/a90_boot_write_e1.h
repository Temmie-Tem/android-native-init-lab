#ifndef A90_BOOT_WRITE_E1_H
#define A90_BOOT_WRITE_E1_H

/*
 * §0.2 write-probe rungs E1/E2/E3a/E3b/E4/E5 (self-dd fast-flash tool design §11.2)
 * plus the F0/F1 content-changing ladder preparation commands (design §12).
 *
 * THIS FILE CARRIES A WRITE PRIMITIVE (pwrite to the boot block). It is a read-then-write-IDENTITY
 * probe confined to boot partition identity writes: it resolves boot from sysfs PARTNAME=boot, picks
 * one confirmed-zero E1 tail-slack target, four confirmed-zero E2 tail-slack targets, sixteen
 * confirmed-zero E3a tail-slack targets spread across the observed all-zero sector population, or
 * one E3b contiguous 1 MiB non-zero slack block. E4 is the late 4 KiB header-sector identity rung at
 * offset 0. E5 streams the full 64 MiB boot partition back to itself in 1 MiB identity chunks. Each
 * rung writes the exact bytes it just read back to the same offset, fsyncs, verifies via an O_DIRECT
 * cache-bypassed readback, and checks a full-partition SHA before/after to catch any cross-LBA
 * change. F0 performs no write: it validates a staged candidate image and computes the target
 * full-partition SHA that a later content-changing rung would write. F1 is token-gated and performs
 * a paired content-changing roundtrip: write the planned target full image, verify it, then restore
 * the captured before.full image before any reboot. Any anomaly is reported as a STOP. E/F1 rungs
 * are token-gated. Output lines are "A90BWE*" / "A90BWF*" key=value.
 * NOTE (design §11): on UFS an interrupted write is NOT guaranteed identity-safe; these rungs stay
 * in boot-only externally-recoverable slack and require an external recovery drill first.
 */
int a90_boot_write_e1_cmd(char **argv, int argc);
int a90_boot_write_e2_cmd(char **argv, int argc);
int a90_boot_write_e3a_cmd(char **argv, int argc);
int a90_boot_write_e3b_cmd(char **argv, int argc);
int a90_boot_write_e4_cmd(char **argv, int argc);
int a90_boot_write_e5_cmd(char **argv, int argc);
int a90_boot_flash_plan_cmd(char **argv, int argc);
int a90_boot_flash_f1_cmd(char **argv, int argc);

#endif /* A90_BOOT_WRITE_E1_H */
