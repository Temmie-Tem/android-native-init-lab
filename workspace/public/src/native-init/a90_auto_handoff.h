#ifndef A90_AUTO_HANDOFF_H
#define A90_AUTO_HANDOFF_H

/*
 * Run a profile-bound automatic D3 switch_root at most once and only after a
 * separate durable enable intent was created on a healthy resident boot.
 * Success replaces PID1 and never returns.  A positive result means the first
 * boot is unarmed or the no-replay latch already exists; a negative result
 * remains fail-closed against automatic replay.
 */
int a90_auto_handoff_status_cmd(char **argv, int argc);
int a90_auto_handoff_arm_cmd(char **argv, int argc);
int a90_auto_handoff_arm_reboot_cmd(char **argv, int argc);
int a90_auto_handoff_run_once(void);

#endif /* A90_AUTO_HANDOFF_H */
