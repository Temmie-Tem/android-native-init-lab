/* SPDX-License-Identifier: MIT
 *
 * Host fault-injection harness for the S20+ P1 direct-PID1 exec-handoff
 * witness.
 *
 * This does not reimplement the witness. It includes the production source with
 * S20PLUS_P1_WITNESS_FAULT_HARNESS defined, which swaps exactly one thing - the
 * `svc #0` primitive - for a call into this file. Every branch the device takes
 * is then taken here: the PID1 gate, the record builder, the /dev/kmsg write,
 * the rename, the exec, the park and the cleanup are the same statements.
 *
 * Each scenario names one injected failure. The harness prints a trace of the
 * calls the witness actually made, the record bytes it actually produced, and
 * how it actually terminated, and the Python tests assert on that rather than on
 * the shape of the source text.
 *
 * Termination is observable because both terminal states go through the seam:
 * the park loop calls nanosleep and a successful exec calls execve, so the
 * harness can longjmp out of either and name which one happened.
 */

#define S20PLUS_P1_WITNESS_FAULT_HARNESS 1

#include "s20plus_p1_pid1_witness_init.c"

#include <setjmp.h>
#include <stdio.h>
#include <string.h>

#define HARNESS_KMSG_FD 7
#define HARNESS_PROC_FD 8

#define END_PARK 1
#define END_EXEC 2

static jmp_buf harness_exit;

/* One scenario is one set of injected failures. Zero means "let it succeed". */
static struct {
    long getpid_result;
    long mount_result;
    long mkdir_result;
    long mknod_result;
    long kmsg_open_result;
    long write_result;      /* < 0 is an error; > 0 and short is a short write */
    long readlink_result;   /* < 0 makes every procfs link read fail */
    long bootid_open_result;
    long rename_result;
    long execve_result;
    long umount_result;     /* applied to both the plain and the MNT_DETACH call */
} fault;

static char written_record[512];
static long written_length = -1;
static long requested_length = -1;
static int proc_mounted;
static int kmsg_node_present;
static char **handoff_argv;
static char **handoff_envp;

static const char *syscall_name(long number) {
    switch (number) {
        case NR_MKNODAT: return "mknodat";
        case NR_MKDIRAT: return "mkdirat";
        case NR_UNLINKAT: return "unlinkat";
        case NR_RENAMEAT: return "renameat";
        case NR_UMOUNT2: return "umount2";
        case NR_MOUNT: return "mount";
        case NR_OPENAT: return "openat";
        case NR_CLOSE: return "close";
        case NR_READ: return "read";
        case NR_WRITE: return "write";
        case NR_READLINKAT: return "readlinkat";
        case NR_NANOSLEEP: return "nanosleep";
        case NR_GETPID: return "getpid";
        case NR_EXECVE: return "execve";
        case NR_EXIT_GROUP: return "exit_group";
        default: return "unknown";
    }
}

static long emit(long number, const char *detail, long result) {
    printf("CALL %s %s -> %ld\n", syscall_name(number), detail ? detail : "-", result);
    return result;
}

static size_t fill(char *destination, long limit, const char *value) {
    size_t length = strlen(value);
    if ((long)length > limit) {
        length = (size_t)limit;
    }
    memcpy(destination, value, length);
    return length;
}

long p1w_harness_syscall(long number, long a0, long a1, long a2, long a3, long a4) {
    const char *path = (const char *)(uintptr_t)a1;
    (void)a4;

    switch (number) {
        case NR_GETPID:
            return emit(number, "-", fault.getpid_result ? fault.getpid_result : 1);

        case NR_MKDIRAT:
            return emit(number, path, fault.mkdir_result);

        case NR_MOUNT: {
            long result = fault.mount_result;
            if (result == 0) {
                proc_mounted = 1;
            }
            return emit(number, (const char *)(uintptr_t)a1, result);
        }

        case NR_UMOUNT2: {
            long result = fault.umount_result;
            if (result == 0) {
                proc_mounted = 0;
            }
            return emit(number, (const char *)(uintptr_t)a0, result);
        }

        case NR_MKNODAT: {
            long result = fault.mknod_result;
            if (result == 0) {
                kmsg_node_present = 1;
            }
            return emit(number, path, result);
        }

        case NR_UNLINKAT: {
            kmsg_node_present = 0;
            return emit(number, path, 0);
        }

        case NR_READLINKAT: {
            char *buffer = (char *)(uintptr_t)a2;
            const char *value = NULL;
            if (fault.readlink_result < 0) {
                return emit(number, path, fault.readlink_result);
            }
            if (strcmp(path, P1W_PROC_SELF) == 0) {
                value = "1";
            } else if (strcmp(path, P1W_PROC_SELF_NS_PID) == 0) {
                value = "pid:[4026531836]";
            }
            if (value == NULL || !proc_mounted) {
                return emit(number, path, -2);
            }
            return emit(number, path, (long)fill(buffer, a3, value));
        }

        case NR_OPENAT:
            if (strcmp(path, P1W_KMSG_PATH) == 0) {
                if (fault.kmsg_open_result < 0) {
                    return emit(number, path, fault.kmsg_open_result);
                }
                if (!kmsg_node_present) {
                    return emit(number, path, -2);
                }
                return emit(number, path, HARNESS_KMSG_FD);
            }
            if (strcmp(path, P1W_BOOT_ID_PATH) == 0) {
                if (fault.bootid_open_result < 0 || !proc_mounted) {
                    return emit(number, path, fault.bootid_open_result ? fault.bootid_open_result : -2);
                }
                return emit(number, path, HARNESS_PROC_FD);
            }
            return emit(number, path, -2);

        case NR_READ: {
            char *buffer = (char *)(uintptr_t)a1;
            if (a0 != HARNESS_PROC_FD) {
                return emit(number, "-", -9);
            }
            return emit(number, P1W_BOOT_ID_PATH,
                        (long)fill(buffer, a2, "3f7a1b20-91cc-4d0e-8a55-1c9e77b40d31\n"));
        }

        case NR_WRITE: {
            long result;
            requested_length = a2;
            if (a0 != HARNESS_KMSG_FD) {
                return emit(number, "-", -9);
            }
            result = fault.write_result ? fault.write_result : a2;
            if (result > 0) {
                long copied = result < (long)sizeof(written_record) ? result : (long)sizeof(written_record) - 1;
                memcpy(written_record, (const char *)(uintptr_t)a1, (size_t)copied);
                written_record[copied] = '\0';
                written_length = result;
            }
            return emit(number, "kmsg", result);
        }

        case NR_CLOSE:
            return emit(number, "-", 0);

        case NR_RENAMEAT:
            printf("CALL renameat %s -> %s = %ld\n",
                   (const char *)(uintptr_t)a1, (const char *)(uintptr_t)a3, fault.rename_result);
            return fault.rename_result;

        case NR_EXECVE:
            handoff_argv = (char **)(uintptr_t)a1;
            handoff_envp = (char **)(uintptr_t)a2;
            emit(number, (const char *)(uintptr_t)a0, fault.execve_result);
            if (fault.execve_result == 0) {
                longjmp(harness_exit, END_EXEC);
            }
            return fault.execve_result;

        case NR_NANOSLEEP:
            longjmp(harness_exit, END_PARK);
            return 0;

        default:
            return emit(number, "-", -38);
    }
}

static void select_scenario(const char *name) {
    memset(&fault, 0, sizeof(fault));
    if (strcmp(name, "happy") == 0) {
        return;
    }
    if (strcmp(name, "not-pid1") == 0) {
        fault.getpid_result = 2;
    } else if (strcmp(name, "mount-fail") == 0) {
        fault.mount_result = -1;
    } else if (strcmp(name, "readlink-fail") == 0) {
        fault.readlink_result = -13;
    } else if (strcmp(name, "bootid-open-fail") == 0) {
        fault.bootid_open_result = -13;
    } else if (strcmp(name, "kmsg-open-fail") == 0) {
        fault.kmsg_open_result = -13;
    } else if (strcmp(name, "mknod-fail") == 0) {
        fault.mknod_result = -1;
    } else if (strcmp(name, "mknod-exists") == 0) {
        fault.mknod_result = -17;
    } else if (strcmp(name, "write-fail") == 0) {
        fault.write_result = -5;
    } else if (strcmp(name, "short-write") == 0) {
        fault.write_result = 12;
    } else if (strcmp(name, "umount-fail") == 0) {
        fault.umount_result = -16;
    } else if (strcmp(name, "rename-fail") == 0) {
        fault.rename_result = -1;
    } else if (strcmp(name, "exec-fail") == 0) {
        fault.execve_result = -2;
    } else {
        fprintf(stderr, "unknown scenario %s\n", name);
    }
}

int main(int argc, char **argv) {
    /* The kernel's own PID1 entry stack: argc, argv[], NULL, envp[], NULL. The
     * witness must forward these two vectors untouched. */
    static char arg0[] = "/init";
    static char arg1[] = "selinux_setup";
    static char env0[] = "PATH=/sbin";
    unsigned long stack[6];
    int outcome;

    if (argc != 2) {
        fprintf(stderr, "usage: %s <scenario>\n", argv[0]);
        return 2;
    }
    select_scenario(argv[1]);

    stack[0] = 2;
    stack[1] = (unsigned long)(uintptr_t)arg0;
    stack[2] = (unsigned long)(uintptr_t)arg1;
    stack[3] = 0;
    stack[4] = (unsigned long)(uintptr_t)env0;
    stack[5] = 0;

    outcome = setjmp(harness_exit);
    if (outcome == 0) {
        p1w_main(stack);
        printf("END fallthrough\n");
        return 1;
    }

    if (written_length >= 0) {
        printf("RECORD %s\n", written_record);
        printf("RECORD_BYTES %ld of %ld\n", written_length, requested_length);
    } else {
        printf("RECORD none\n");
    }
    printf("STATE proc_mounted=%d kmsg_node_present=%d\n", proc_mounted, kmsg_node_present);
    if (handoff_argv != NULL) {
        printf("HANDOFF argv0=%s argv1=%s argv2=%s envp0=%s envp1=%s\n",
               handoff_argv[0] ? handoff_argv[0] : "(null)",
               handoff_argv[1] ? handoff_argv[1] : "(null)",
               handoff_argv[2] ? handoff_argv[2] : "(null)",
               handoff_envp[0] ? handoff_envp[0] : "(null)",
               handoff_envp[1] ? handoff_envp[1] : "(null)");
        printf("HANDOFF_VECTORS argv_is_stack1=%d envp_is_stack4=%d\n",
               handoff_argv == (char **)&stack[1], handoff_envp == (char **)&stack[4]);
    } else {
        printf("HANDOFF none\n");
    }
    printf("END %s\n", outcome == END_EXEC ? "exec" : "park");
    return 0;
}
