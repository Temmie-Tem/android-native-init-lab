#include "a90_controller.h"

#include <errno.h>
#include <fcntl.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

#include "a90_config.h"
#include "a90_shell.h"
#include "a90_util.h"

#ifndef O_CLOEXEC
#define O_CLOEXEC 0
#endif

#ifndef O_NOFOLLOW
#define O_NOFOLLOW 0
#endif

#define A90_POLICY_MAX_ARGS 5
#define A90_POLICY_MAX_RESULTS 96

struct controller_policy_case {
    const char *label;
    int argc;
    const char *argv[A90_POLICY_MAX_ARGS];
    bool power_page;
    bool expected_allowed;
};

static struct a90_controller_policy_result policy_results[A90_POLICY_MAX_RESULTS];
static size_t policy_result_count = 0;
static size_t policy_pass_count = 0;
static size_t policy_fail_count = 0;
static size_t policy_allowed_count = 0;
static size_t policy_blocked_count = 0;

static void controller_write_file(const char *path, const char *value) {
    int fd = open(path, O_WRONLY | O_CREAT | O_TRUNC | O_CLOEXEC | O_NOFOLLOW, 0600);

    if (fd < 0) {
        return;
    }
    write_all(fd, value, strlen(value));
    close(fd);
}

bool a90_controller_is_hide_word(const char *name) {
    return name != NULL &&
           (strcmp(name, "q") == 0 ||
            strcmp(name, "Q") == 0 ||
            strcmp(name, "hide") == 0 ||
            strcmp(name, "hidemenu") == 0 ||
            strcmp(name, "resume") == 0);
}

static bool command_is_menu_control(const char *name) {
    return strcmp(name, "screenmenu") == 0 ||
           strcmp(name, "menu") == 0 ||
           strcmp(name, "hide") == 0 ||
           strcmp(name, "hidemenu") == 0 ||
           strcmp(name, "resume") == 0 ||
           strcmp(name, "stophud") == 0;
}

static bool command_waits_for_input(const char *name) {
    return strcmp(name, "blindmenu") == 0 ||
           strcmp(name, "waitkey") == 0 ||
           strcmp(name, "readinput") == 0 ||
           strcmp(name, "waitgesture") == 0;
}

static bool command_allowed_on_power_page(const char *name) {
    return strcmp(name, "help") == 0 ||
           strcmp(name, "version") == 0 ||
           strcmp(name, "status") == 0 ||
           strcmp(name, "bootstatus") == 0 ||
           strcmp(name, "exposure") == 0 ||
           strcmp(name, "policycheck") == 0 ||
           strcmp(name, "storage") == 0 ||
           strcmp(name, "timeline") == 0 ||
           strcmp(name, "last") == 0 ||
           strcmp(name, "logpath") == 0 ||
           strcmp(name, "logcat") == 0 ||
           strcmp(name, "inputlayout") == 0 ||
           strcmp(name, "inputmonitor") == 0 ||
           strcmp(name, "uname") == 0 ||
           strcmp(name, "pwd") == 0 ||
           strcmp(name, "mounts") == 0 ||
           strcmp(name, "reattach") == 0 ||
           strcmp(name, "stophud") == 0;
}

static bool command_allowed_during_menu(const char *name) {
    return strcmp(name, "help") == 0 ||
           strcmp(name, "cmdmeta") == 0 ||
           strcmp(name, "cmdgroups") == 0 ||
           strcmp(name, "version") == 0 ||
           strcmp(name, "status") == 0 ||
           strcmp(name, "bootstatus") == 0 ||
           strcmp(name, "exposure") == 0 ||
           strcmp(name, "policycheck") == 0 ||
           strcmp(name, "storage") == 0 ||
           strcmp(name, "runtime") == 0 ||
           strcmp(name, "timeline") == 0 ||
           strcmp(name, "last") == 0 ||
           strcmp(name, "logpath") == 0 ||
           strcmp(name, "logcat") == 0 ||
           strcmp(name, "inputlayout") == 0 ||
           strcmp(name, "uname") == 0 ||
           strcmp(name, "pwd") == 0 ||
           strcmp(name, "mounts") == 0 ||
           strcmp(name, "reattach") == 0;
}

static bool arg_equals(char **argv, int argc, int index, const char *value) {
    return argc > index && argv != NULL && argv[index] != NULL && strcmp(argv[index], value) == 0;
}

static bool subcmd_absent_or_one_of(int argc, char **argv, const char *const *allowed, size_t allowed_count) {
    size_t i;

    if (argc <= 1) {
        return true;
    }
    if (argc != 2) {
        return false;
    }
    if (argv == NULL || argv[1] == NULL) {
        return false;
    }
    for (i = 0; i < allowed_count; ++i) {
        if (strcmp(argv[1], allowed[i]) == 0) {
            return true;
        }
    }
    return false;
}

static bool subcmd_one_of(int argc, char **argv, const char *const *allowed, size_t allowed_count) {
    size_t i;

    if (argc != 2) {
        return false;
    }
    if (argv == NULL || argv[1] == NULL) {
        return false;
    }
    for (i = 0; i < allowed_count; ++i) {
        if (strcmp(argv[1], allowed[i]) == 0) {
            return true;
        }
    }
    return false;
}

static bool helpers_read_only(int argc, char **argv) {
    static const char *const safe_helpers[] = {
        "status",
        "verbose",
        "manifest",
        "plan",
    };

    if (subcmd_absent_or_one_of(argc, argv, safe_helpers, sizeof(safe_helpers) / sizeof(safe_helpers[0]))) {
        return true;
    }
    return argc == 3 && arg_equals(argv, argc, 1, "path");
}

static bool service_read_only(int argc, char **argv) {
    if (argc <= 1) {
        return true;
    }
    if (arg_equals(argv, argc, 1, "list")) {
        return argc == 2;
    }
    if (arg_equals(argv, argc, 1, "status")) {
        return argc == 2 || argc == 3;
    }
    return false;
}

static bool command_allowed_during_menu_ex(const char *name, int argc, char **argv) {
    static const char *const status_verbose[] = {
        "status",
        "verbose",
    };
    static const char *const status_only[] = {
        "status",
    };
    static const char *const diag_safe[] = {
        "summary",
        "paths",
    };
    static const char *const wififeas_safe[] = {
        "summary",
        "gate",
        "paths",
    };
    static const char *const rshell_safe[] = {
        "status",
        "audit",
    };
    static const char *const longsoak_safe[] = {
        "status",
        "start",
        "stop",
        "path",
        "tail",
    };

    if (name == NULL) {
        return false;
    }
    if (command_allowed_during_menu(name)) {
        return true;
    }
    if (strcmp(name, "selftest") == 0 ||
        strcmp(name, "pid1guard") == 0) {
        return subcmd_absent_or_one_of(argc, argv, status_verbose, sizeof(status_verbose) / sizeof(status_verbose[0]));
    }
    if (strcmp(name, "helpers") == 0) {
        return helpers_read_only(argc, argv);
    }
    if (strcmp(name, "mountsd") == 0) {
        return subcmd_one_of(argc, argv, status_only, sizeof(status_only) / sizeof(status_only[0]));
    }
    if (strcmp(name, "hudlog") == 0 ||
        strcmp(name, "netservice") == 0) {
        return subcmd_absent_or_one_of(argc, argv, status_only, sizeof(status_only) / sizeof(status_only[0]));
    }
    if (strcmp(name, "diag") == 0 ||
        strcmp(name, "wifiinv") == 0) {
        return subcmd_absent_or_one_of(argc, argv, diag_safe, sizeof(diag_safe) / sizeof(diag_safe[0]));
    }
    if (strcmp(name, "wififeas") == 0) {
        return subcmd_absent_or_one_of(argc, argv, wififeas_safe, sizeof(wififeas_safe) / sizeof(wififeas_safe[0]));
    }
    if (strcmp(name, "rshell") == 0) {
        return subcmd_absent_or_one_of(argc, argv, rshell_safe, sizeof(rshell_safe) / sizeof(rshell_safe[0]));
    }
    if (strcmp(name, "service") == 0) {
        return service_read_only(argc, argv);
    }
    if (strcmp(name, "longsoak") == 0) {
        return subcmd_absent_or_one_of(argc, argv, longsoak_safe, sizeof(longsoak_safe) / sizeof(longsoak_safe[0])) ||
               (argc == 3 && argv != NULL && argv[1] != NULL &&
                (strcmp(argv[1], "start") == 0 ||
                 strcmp(argv[1], "tail") == 0 ||
                 (strcmp(argv[1], "status") == 0 &&
                  argv[2] != NULL &&
                  strcmp(argv[2], "verbose") == 0)));
    }
    return false;
}

enum a90_controller_busy_reason a90_controller_command_busy_reason(const char *name,
                                                                   unsigned int flags,
                                                                   bool menu_active,
                                                                   bool power_page_active) {
    if (name == NULL || !menu_active) {
        return A90_CONTROLLER_BUSY_NONE;
    }
    if (command_is_menu_control(name)) {
        return A90_CONTROLLER_BUSY_NONE;
    }
    if (!power_page_active) {
        if ((flags & CMD_DANGEROUS) != 0) {
            return A90_CONTROLLER_BUSY_DANGEROUS;
        }
        if (command_waits_for_input(name)) {
            return A90_CONTROLLER_BUSY_AUTO_MENU;
        }
        if (command_allowed_during_menu(name)) {
            return A90_CONTROLLER_BUSY_NONE;
        }
        return A90_CONTROLLER_BUSY_AUTO_MENU;
    }
    if (command_allowed_on_power_page(name)) {
        return A90_CONTROLLER_BUSY_NONE;
    }
    return A90_CONTROLLER_BUSY_POWER;
}

enum a90_controller_busy_reason a90_controller_command_busy_reason_ex(const char *name,
                                                                      unsigned int flags,
                                                                      int argc,
                                                                      char **argv,
                                                                      bool menu_active,
                                                                      bool power_page_active) {
    if (name == NULL || !menu_active) {
        return A90_CONTROLLER_BUSY_NONE;
    }
    if (command_is_menu_control(name)) {
        return A90_CONTROLLER_BUSY_NONE;
    }
    if (!power_page_active) {
        if (command_waits_for_input(name)) {
            return A90_CONTROLLER_BUSY_AUTO_MENU;
        }
        if (command_allowed_during_menu_ex(name, argc, argv)) {
            return A90_CONTROLLER_BUSY_NONE;
        }
        if ((flags & CMD_DANGEROUS) != 0) {
            return A90_CONTROLLER_BUSY_DANGEROUS;
        }
        return A90_CONTROLLER_BUSY_AUTO_MENU;
    }
    if (command_allowed_on_power_page(name)) {
        return A90_CONTROLLER_BUSY_NONE;
    }
    return A90_CONTROLLER_BUSY_POWER;
}

const char *a90_controller_busy_message(enum a90_controller_busy_reason reason) {
    switch (reason) {
    case A90_CONTROLLER_BUSY_POWER:
        return "[busy] power menu active; send hide/q before commands";
    case A90_CONTROLLER_BUSY_DANGEROUS:
        return "[busy] auto menu active; hide/q before dangerous command";
    case A90_CONTROLLER_BUSY_AUTO_MENU:
        return "[busy] auto menu active; send hide/q before command";
    case A90_CONTROLLER_BUSY_NONE:
    default:
        return "";
    }
}

static const struct controller_policy_case policy_cases[] = {
    { "menu allow version", 1, { "version" }, false, true },
    { "menu allow status", 1, { "status" }, false, true },
    { "menu allow bootstatus", 1, { "bootstatus" }, false, true },
    { "menu allow exposure status", 2, { "exposure", "status" }, false, true },
    { "menu allow exposure verbose", 2, { "exposure", "verbose" }, false, true },
    { "menu allow policycheck", 1, { "policycheck" }, false, true },
    { "menu allow policycheck run", 2, { "policycheck", "run" }, false, true },
    { "menu allow storage", 1, { "storage" }, false, true },
    { "menu allow runtime", 1, { "runtime" }, false, true },
    { "menu allow timeline", 1, { "timeline" }, false, true },
    { "menu allow logpath", 1, { "logpath" }, false, true },
    { "menu allow helpers status", 2, { "helpers", "status" }, false, true },
    { "menu allow helpers verbose", 2, { "helpers", "verbose" }, false, true },
    { "menu allow helpers manifest", 2, { "helpers", "manifest" }, false, true },
    { "menu allow helpers plan", 2, { "helpers", "plan" }, false, true },
    { "menu allow helpers path", 3, { "helpers", "path", "a90_cpustress" }, false, true },
    { "menu allow selftest status", 2, { "selftest", "status" }, false, true },
    { "menu allow selftest verbose", 2, { "selftest", "verbose" }, false, true },
    { "menu allow pid1guard status", 2, { "pid1guard", "status" }, false, true },
    { "menu allow pid1guard verbose", 2, { "pid1guard", "verbose" }, false, true },
    { "menu allow mountsd status", 2, { "mountsd", "status" }, false, true },
    { "menu allow netservice status", 2, { "netservice", "status" }, false, true },
    { "menu allow rshell status", 2, { "rshell", "status" }, false, true },
    { "menu allow rshell audit", 2, { "rshell", "audit" }, false, true },
    { "menu allow service list", 2, { "service", "list" }, false, true },
    { "menu allow service status", 2, { "service", "status" }, false, true },
    { "menu allow service status tcpctl", 3, { "service", "status", "tcpctl" }, false, true },
    { "menu allow longsoak status", 2, { "longsoak", "status" }, false, true },
    { "menu allow longsoak status verbose", 3, { "longsoak", "status", "verbose" }, false, true },
    { "menu allow longsoak start", 3, { "longsoak", "start", "2" }, false, true },
    { "menu allow longsoak tail", 3, { "longsoak", "tail", "3" }, false, true },
    { "menu allow longsoak stop", 2, { "longsoak", "stop" }, false, true },
    { "menu allow diag summary", 2, { "diag", "summary" }, false, true },
    { "menu allow diag paths", 2, { "diag", "paths" }, false, true },
    { "menu allow wifiinv summary", 2, { "wifiinv", "summary" }, false, true },
    { "menu allow wifiinv paths", 2, { "wifiinv", "paths" }, false, true },
    { "menu allow wififeas summary", 2, { "wififeas", "summary" }, false, true },
    { "menu allow wififeas gate", 2, { "wififeas", "gate" }, false, true },
    { "menu allow hide", 1, { "hide" }, false, true },
    { "menu block bare mountsd", 1, { "mountsd" }, false, false },
    { "menu block mountsd ro", 2, { "mountsd", "ro" }, false, false },
    { "menu block mountsd rw", 2, { "mountsd", "rw" }, false, false },
    { "menu block mountsd off", 2, { "mountsd", "off" }, false, false },
    { "menu block mountsd init", 2, { "mountsd", "init" }, false, false },
    { "menu block netservice start", 2, { "netservice", "start" }, false, false },
    { "menu block netservice stop", 2, { "netservice", "stop" }, false, false },
    { "menu block netservice enable", 2, { "netservice", "enable" }, false, false },
    { "menu block netservice disable", 2, { "netservice", "disable" }, false, false },
    { "menu block rshell start", 2, { "rshell", "start" }, false, false },
    { "menu block rshell stop", 2, { "rshell", "stop" }, false, false },
    { "menu block rshell enable", 2, { "rshell", "enable" }, false, false },
    { "menu block rshell disable", 2, { "rshell", "disable" }, false, false },
    { "menu block rshell token show", 3, { "rshell", "token", "show" }, false, false },
    { "menu block rshell rotate-token", 2, { "rshell", "rotate-token" }, false, false },
    { "menu block service start tcpctl", 3, { "service", "start", "tcpctl" }, false, false },
    { "menu block service stop tcpctl", 3, { "service", "stop", "tcpctl" }, false, false },
    { "menu block service enable tcpctl", 3, { "service", "enable", "tcpctl" }, false, false },
    { "menu block service disable tcpctl", 3, { "service", "disable", "tcpctl" }, false, false },
    { "menu block service start rshell", 3, { "service", "start", "rshell" }, false, false },
    { "menu block hudlog on", 2, { "hudlog", "on" }, false, false },
    { "menu block hudlog off", 2, { "hudlog", "off" }, false, false },
    { "menu block diag full", 2, { "diag", "full" }, false, false },
    { "menu block diag bundle", 2, { "diag", "bundle" }, false, false },
    { "menu block wifiinv refresh", 2, { "wifiinv", "refresh" }, false, false },
    { "menu block wififeas refresh", 2, { "wififeas", "refresh" }, false, false },
    { "menu block userland test all", 3, { "userland", "test", "all" }, false, false },
    { "menu block busybox sh", 2, { "busybox", "sh" }, false, false },
    { "menu block toybox sh", 2, { "toybox", "sh" }, false, false },
    { "menu block run", 3, { "run", "/bin/a90sleep", "1" }, false, false },
    { "menu block runandroid", 3, { "runandroid", "/system/bin/toybox", "true" }, false, false },
    { "menu block writefile", 4, { "writefile", "/tmp/x", "y" }, false, false },
    { "menu block mountfs", 4, { "mountfs", "tmpfs", "/tmp/x", "tmpfs" }, false, false },
    { "menu block mknodc", 4, { "mknodc", "/tmp/x", "1", "3" }, false, false },
    { "menu block umount", 2, { "umount", "/mnt/sdext" }, false, false },
    { "menu block reboot", 1, { "reboot" }, false, false },
    { "menu block recovery", 1, { "recovery" }, false, false },
    { "menu block poweroff", 1, { "poweroff" }, false, false },
    { "power allow help", 1, { "help" }, true, true },
    { "power allow status", 1, { "status" }, true, true },
    { "power allow exposure status", 2, { "exposure", "status" }, true, true },
    { "power allow policycheck", 1, { "policycheck" }, true, true },
    { "power allow storage", 1, { "storage" }, true, true },
    { "power allow timeline", 1, { "timeline" }, true, true },
    { "power allow logpath", 1, { "logpath" }, true, true },
    { "power allow inputlayout", 1, { "inputlayout" }, true, true },
    { "power allow reattach", 1, { "reattach" }, true, true },
    { "power allow stophud", 1, { "stophud" }, true, true },
    { "power allow hide", 1, { "hide" }, true, true },
    { "power block netservice start", 2, { "netservice", "start" }, true, false },
    { "power block rshell start", 2, { "rshell", "start" }, true, false },
    { "power block service start tcpctl", 3, { "service", "start", "tcpctl" }, true, false },
    { "power block writefile", 4, { "writefile", "/tmp/x", "y" }, true, false },
    { "power block run", 3, { "run", "/bin/a90sleep", "1" }, true, false },
    { "power block reboot", 1, { "reboot" }, true, false },
    { "power block recovery", 1, { "recovery" }, true, false },
    { "power block poweroff", 1, { "poweroff" }, true, false },
};

static unsigned int controller_command_flags(const struct shell_command *commands,
                                             size_t count,
                                             const char *name) {
    const struct shell_command *command = a90_shell_find_command(commands, count, name);

    if (command == NULL) {
        return CMD_NONE;
    }
    return command->flags;
}

int a90_controller_policy_matrix_run(const struct shell_command *commands, size_t count) {
    size_t index;

    policy_result_count = 0;
    policy_pass_count = 0;
    policy_fail_count = 0;
    policy_allowed_count = 0;
    policy_blocked_count = 0;

    for (index = 0;
         index < sizeof(policy_cases) / sizeof(policy_cases[0]) &&
         index < A90_POLICY_MAX_RESULTS;
         ++index) {
        const struct controller_policy_case *policy_case = &policy_cases[index];
        struct a90_controller_policy_result *result = &policy_results[policy_result_count];
        char *argv[A90_POLICY_MAX_ARGS];
        enum a90_controller_busy_reason reason;
        unsigned int flags;
        int arg_index;

        memset(argv, 0, sizeof(argv));
        for (arg_index = 0; arg_index < policy_case->argc && arg_index < A90_POLICY_MAX_ARGS; ++arg_index) {
            argv[arg_index] = (char *)policy_case->argv[arg_index];
        }

        flags = controller_command_flags(commands, count, policy_case->argv[0]);
        reason = a90_controller_command_busy_reason_ex(policy_case->argv[0],
                                                       flags,
                                                       policy_case->argc,
                                                       argv,
                                                       true,
                                                       policy_case->power_page);
        result->label = policy_case->label;
        result->command = policy_case->argv[0];
        result->power_page = policy_case->power_page;
        result->expected_allowed = policy_case->expected_allowed;
        result->actual_allowed = reason == A90_CONTROLLER_BUSY_NONE;
        result->reason = reason;
        result->flags = flags;

        if (result->actual_allowed) {
            policy_allowed_count++;
        } else {
            policy_blocked_count++;
        }
        if (result->expected_allowed == result->actual_allowed) {
            policy_pass_count++;
        } else {
            policy_fail_count++;
        }
        policy_result_count++;
    }

    return policy_fail_count == 0 ? 0 : -EIO;
}

void a90_controller_policy_matrix_summary(char *out, size_t out_size) {
    if (out == NULL || out_size == 0) {
        return;
    }
    snprintf(out,
             out_size,
             "cases=%zu pass=%zu fail=%zu allowed=%zu blocked=%zu",
             policy_result_count,
             policy_pass_count,
             policy_fail_count,
             policy_allowed_count,
             policy_blocked_count);
}

size_t a90_controller_policy_matrix_count(void) {
    return policy_result_count;
}

const struct a90_controller_policy_result *a90_controller_policy_matrix_entry_at(size_t index) {
    if (index >= policy_result_count) {
        return NULL;
    }
    return &policy_results[index];
}

void a90_controller_clear_menu_ipc(void) {
    unlink(AUTO_MENU_STATE_PATH);
    unlink(AUTO_MENU_REQUEST_PATH);
}

void a90_controller_clear_menu_request(void) {
    unlink(AUTO_MENU_REQUEST_PATH);
}

void a90_controller_set_menu_active(bool active) {
    controller_write_file(AUTO_MENU_STATE_PATH, active ? "1\n" : "0\n");
}

void a90_controller_set_menu_state(bool active, bool power_page) {
    if (!active) {
        controller_write_file(AUTO_MENU_STATE_PATH, "0\n");
    } else if (power_page) {
        controller_write_file(AUTO_MENU_STATE_PATH, "power\n");
    } else {
        controller_write_file(AUTO_MENU_STATE_PATH, "1\n");
    }
}

bool a90_controller_menu_is_active(void) {
    char state[16];

    if (read_text_file(AUTO_MENU_STATE_PATH, state, sizeof(state)) < 0) {
        return false;
    }
    trim_newline(state);
    return strcmp(state, "1") == 0 ||
           strcmp(state, "active") == 0 ||
           strcmp(state, "menu") == 0 ||
           strcmp(state, "power") == 0;
}

bool a90_controller_menu_power_is_active(void) {
    char state[16];

    if (read_text_file(AUTO_MENU_STATE_PATH, state, sizeof(state)) < 0) {
        return false;
    }
    trim_newline(state);
    return strcmp(state, "power") == 0;
}

void a90_controller_request_menu_show(void) {
    controller_write_file(AUTO_MENU_REQUEST_PATH, "show\n");
}

void a90_controller_request_menu_hide(void) {
    controller_write_file(AUTO_MENU_REQUEST_PATH, "hide\n");
}

enum a90_controller_menu_request a90_controller_consume_menu_request(void) {
    char request[32];

    if (read_text_file(AUTO_MENU_REQUEST_PATH, request, sizeof(request)) < 0) {
        return A90_CONTROLLER_MENU_REQUEST_NONE;
    }
    unlink(AUTO_MENU_REQUEST_PATH);
    trim_newline(request);
    if (strcmp(request, "hide") == 0 ||
        strcmp(request, "hidemenu") == 0 ||
        strcmp(request, "resume") == 0 ||
        strcmp(request, "q") == 0 ||
        strcmp(request, "Q") == 0 ||
        strcmp(request, "0") == 0) {
        return A90_CONTROLLER_MENU_REQUEST_HIDE;
    }
    if (strcmp(request, "show") == 0 ||
        strcmp(request, "menu") == 0 ||
        strcmp(request, "screenmenu") == 0 ||
        strcmp(request, "1") == 0) {
        return A90_CONTROLLER_MENU_REQUEST_SHOW;
    }
    return A90_CONTROLLER_MENU_REQUEST_NONE;
}
