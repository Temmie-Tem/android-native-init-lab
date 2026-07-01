#ifndef A90_BOOT_WRITE_E1_H
#define A90_BOOT_WRITE_E1_H

/*
 * §0.2 write-probe rungs E1/E2 (self-dd fast-flash tool design §11.2).
 *
 * THIS FILE CARRIES A WRITE PRIMITIVE (pwrite to the boot block). It is a read-then-write-IDENTITY
 * probe confined to CONFIRMED-ZERO tail slack of the boot partition: it resolves boot from sysfs
 * PARTNAME=boot, picks one E1 target or four spread E2 targets in the tail slack (past the
 * boot-image content, 1 MiB before the partition end to avoid any AVB footer), REFUSES unless every
 * selected sector reads all-zero, writes the exact bytes it just read back to the same offset,
 * fsyncs, verifies via an O_DIRECT
 * cache-bypassed readback, and checks a full-partition SHA before/after to catch any cross-LBA
 * change. Any anomaly is reported as a STOP. Token-gated. Output lines are "A90BWE* key=value".
 * NOTE (design §11): on UFS an interrupted write is NOT guaranteed identity-safe; this rung is made
 * low-risk by writing only confirmed-zero padding, and requires an external recovery drill first.
 */
int a90_boot_write_e1_cmd(char **argv, int argc);
int a90_boot_write_e2_cmd(char **argv, int argc);

#endif /* A90_BOOT_WRITE_E1_H */
