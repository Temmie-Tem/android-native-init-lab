#ifndef A90_EXPOSURE_H
#define A90_EXPOSURE_H

#include <stdbool.h>
#include <stddef.h>
#include <sys/types.h>

struct a90_exposure_snapshot {
    bool usb_acm_present;
    bool usb_acm_trusted_local;
    bool host_bridge_localhost_expected;
    bool host_bridge_identity_pinning_expected;

    bool netservice_enabled;
    bool netservice_flag_present;
    bool ncm_present;
    const char *ncm_ifname;
    const char *ncm_device_ip;
    const char *ncm_netmask;

    bool tcpctl_helper_present;
    bool tcpctl_running;
    pid_t tcpctl_pid;
    const char *tcpctl_bind_addr;
    const char *tcpctl_port;
    bool tcpctl_token_present;
    bool tcpctl_token_owner_only;
    char tcpctl_token_mode[16];
    const char *tcpctl_token_path;
    bool tcpctl_auth_required;

    bool rshell_enabled;
    bool rshell_flag_present;
    bool rshell_helper_present;
    bool rshell_running;
    pid_t rshell_pid;
    const char *rshell_bind_addr;
    const char *rshell_port;
    bool rshell_token_present;
    bool rshell_token_owner_only;
    char rshell_token_mode[16];
    char rshell_token_path[256];
    char rshell_flag_path[256];

    int warn_count;
    int fail_count;
};

int a90_exposure_collect(struct a90_exposure_snapshot *out);
void a90_exposure_summary(const struct a90_exposure_snapshot *snapshot,
                          char *out,
                          size_t out_size);
bool a90_exposure_guardrail_ok(const struct a90_exposure_snapshot *snapshot);
void a90_exposure_print(const struct a90_exposure_snapshot *snapshot,
                        bool verbose);

#endif
