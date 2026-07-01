#ifndef A90_BOOT_WRITE_PROBE_H
#define A90_BOOT_WRITE_PROBE_H

/*
 * §0.2 write-probe rung E-open (self-dd fast-flash tool design §11).
 *
 * This is the FIRST command in the write-probe ladder, and it performs NO write. It answers half of
 * §0.2 — "does RKP/the kernel even permit opening the boot block O_WRONLY from normal-boot PID1?" —
 * with ZERO write risk: it resolves the boot partition from sysfs PARTNAME=boot, materializes the
 * node, calls open(O_WRONLY) then close() WITHOUT any write()/pwrite()/dd, confirms the fd identity,
 * and unlinks the node. It is token-gated (exact operator phrase). Output lines are
 * "A90BWOPEN key=value". There is deliberately NO write primitive compiled into this file.
 */
int a90_boot_write_open_probe_cmd(char **argv, int argc);

#endif /* A90_BOOT_WRITE_PROBE_H */
