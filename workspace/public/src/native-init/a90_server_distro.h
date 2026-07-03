#ifndef A90_SERVER_DISTRO_H
#define A90_SERVER_DISTRO_H

/*
 * Server-distro D3 handoff.
 *
 * `switch-root-to-distro <token> <image> <sha256>` is a PID1-only handoff command for
 * the SD-backed Debian sysvinit proof.  It validates that the requested image lives under
 * the approved SD runtime root, verifies a caller-pinned SHA-256, loop-mounts the ext4
 * image, moves the live /proc /sys /dev mounts into the distro root, then execve()s
 * BusyBox switch_root so Debian /sbin/init becomes PID1.
 *
 * On success the command intentionally does not return a normal shell END marker because
 * PID1 has been replaced.  The D3A rootfs must schedule the mandatory bounded auto-reboot
 * before starting dropbear.
 */
int a90_server_distro_switch_root_cmd(char **argv, int argc);

/*
 * Server-distro D4 userdata appliance surfaces.
 *
 * D4 mutates Android userdata, so every command is token gated.  Mutating
 * commands re-derive PARTNAME=userdata from sysfs and compare host-pinned
 * identity before materializing or touching the block node.
 */
int a90_server_distro_cmd(char **argv, int argc);
int a90_server_distro_userdata_preflight_cmd(char **argv, int argc);
int a90_server_distro_userdata_formatter_probe_cmd(char **argv, int argc);
int a90_server_distro_userdata_format_cmd(char **argv, int argc);
int a90_server_distro_userdata_populate_cmd(char **argv, int argc);
int a90_server_distro_switch_root_userdata_cmd(char **argv, int argc);

#endif /* A90_SERVER_DISTRO_H */
