#ifndef A90_BOOT_WRITE_E1_H
#define A90_BOOT_WRITE_E1_H

/*
 * §0.2 write-probe rung E1 (self-dd fast-flash tool design §11.2) — the FIRST actual pwrite.
 *
 * THIS FILE CARRIES A WRITE PRIMITIVE (pwrite to the boot block). It is a read-then-write-IDENTITY
 * probe confined to CONFIRMED-ZERO tail slack of the boot partition: it resolves boot from sysfs
 * PARTNAME=boot, picks a 4096-byte target in the tail slack (past the boot-image content, 1 MiB
 * before the partition end to avoid any AVB footer), REFUSES unless that sector reads all-zero,
 * writes the exact bytes it just read back to the same offset, fsyncs, verifies via an O_DIRECT
 * cache-bypassed readback, and checks a full-partition SHA before/after to catch any cross-LBA
 * change. Any anomaly is reported as a STOP. Token-gated. Output lines are "A90BWE1 key=value".
 * NOTE (design §11): on UFS an interrupted write is NOT guaranteed identity-safe; this rung is made
 * low-risk by writing only confirmed-zero padding, and requires an external recovery drill first.
 */
int a90_boot_write_e1_cmd(char **argv, int argc);

#endif /* A90_BOOT_WRITE_E1_H */
