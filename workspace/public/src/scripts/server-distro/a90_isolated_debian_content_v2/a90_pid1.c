/*
 * Consoleless, non-privileged PID 1 for the isolated A90 appliance.
 *
 * This is intentionally not a SysV init replacement.  It owns one exact
 * workload child, forwards the attended stop signals, and reaps only that
 * child.  The native bootstrap supplies the namespace, root, writable tmpfs,
 * identity, and final capability/filter envelope before this binary runs.
 */
#define _GNU_SOURCE

#include <errno.h>
#include <signal.h>
#include <sys/prctl.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

enum {
    A90_SERVICE_UID = 3301,
    A90_SERVICE_GID = 3301,
};

static volatile sig_atomic_t stop_requested;

static void request_stop(int signal_number) {
    (void)signal_number;
    stop_requested = 1;
}

static int exact_identity(void) {
    return getuid() == A90_SERVICE_UID &&
           geteuid() == A90_SERVICE_UID &&
           getgid() == A90_SERVICE_GID &&
           getegid() == A90_SERVICE_GID;
}

static int install_signal_policy(void) {
    struct sigaction action = {
        .sa_handler = request_stop,
        .sa_flags = 0,
    };
    if (sigemptyset(&action.sa_mask) != 0) {
        return -1;
    }
    if (sigaction(SIGTERM, &action, NULL) != 0 ||
        sigaction(SIGINT, &action, NULL) != 0 ||
        sigaction(SIGHUP, &action, NULL) != 0) {
        return -1;
    }
    return 0;
}

int main(void) {
    static char workload_path[] = "/usr/local/libexec/a90-workload";
    static char workload_arg[] = "--serve";
    static char path_env[] = "PATH=/usr/local/libexec";
    static char home_env[] = "HOME=/srv/a90-service";
    static char lang_env[] = "LANG=C";
    char *const workload_argv[] = {workload_path, workload_arg, NULL};
    char *const workload_envp[] = {path_env, home_env, lang_env, NULL};
    int status;
    pid_t workload;

    if (getpid() != 1 || !exact_identity() || prctl(PR_SET_DUMPABLE, 0) != 0) {
        return 111;
    }
    if (install_signal_policy() != 0) {
        return 112;
    }

    workload = fork();
    if (workload < 0) {
        return 113;
    }
    if (workload == 0) {
        execve(workload_path, workload_argv, workload_envp);
        _exit(114);
    }

    for (;;) {
        pid_t waited = waitpid(workload, &status, 0);
        if (waited == workload) {
            if (WIFEXITED(status) && WEXITSTATUS(status) == 0) {
                return 0;
            }
            return 115;
        }
        if (waited < 0 && errno == EINTR) {
            if (stop_requested) {
                (void)kill(workload, SIGTERM);
            }
            continue;
        }
        return 116;
    }
}
