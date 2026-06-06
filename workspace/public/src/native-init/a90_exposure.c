#include "a90_exposure.h"

#include <errno.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

#include "a90_config.h"
#include "a90_console.h"
#include "a90_helper.h"
#include "a90_netservice.h"
#include "a90_runtime.h"
#include "a90_service.h"

static const char *yesno(bool value) {
    return value ? "yes" : "no";
}

static bool path_exists(const char *path) {
    return path != NULL && path[0] != '\0' && access(path, F_OK) == 0;
}

static void runtime_state_path(char *out, size_t out_size, const char *name) {
    const char *state_dir = a90_runtime_state_dir();

    if (out == NULL || out_size == 0) {
        return;
    }
    if (state_dir == NULL || state_dir[0] == '\0') {
        snprintf(out, out_size, "%s", name != NULL ? name : "-");
        return;
    }
    snprintf(out, out_size, "%s/%s", state_dir, name != NULL ? name : "state");
}

static bool file_mode_summary(const char *path,
                              char *mode_out,
                              size_t mode_out_size,
                              bool *owner_only) {
    struct stat st;

    if (mode_out != NULL && mode_out_size > 0) {
        snprintf(mode_out, mode_out_size, "-");
    }
    if (owner_only != NULL) {
        *owner_only = false;
    }
    if (path == NULL || path[0] == '\0') {
        return false;
    }
    if (stat(path, &st) < 0) {
        return false;
    }
    if (mode_out != NULL && mode_out_size > 0) {
        snprintf(mode_out, mode_out_size, "%04o", (unsigned int)(st.st_mode & 0777));
    }
    if (owner_only != NULL) {
        *owner_only = (st.st_mode & 0077) == 0;
    }
    return true;
}

int a90_exposure_collect(struct a90_exposure_snapshot *out) {
    struct a90_netservice_status net_status;
    struct a90_service_info rshell_info;
    const char *rshell_helper;

    if (out == NULL) {
        return -EINVAL;
    }
    memset(out, 0, sizeof(*out));
    snprintf(out->tcpctl_token_mode, sizeof(out->tcpctl_token_mode), "-");
    snprintf(out->rshell_token_mode, sizeof(out->rshell_token_mode), "-");

    out->usb_acm_present = access("/dev/ttyGS0", F_OK) == 0;
    out->usb_acm_trusted_local = true;
    out->host_bridge_localhost_expected = true;
    out->host_bridge_identity_pinning_expected = true;

    memset(&net_status, 0, sizeof(net_status));
    (void)a90_netservice_status(&net_status);
    out->netservice_enabled = net_status.enabled;
    out->netservice_flag_present = path_exists(NETSERVICE_FLAG_PATH);
    out->ncm_present = net_status.ncm_present;
    out->ncm_ifname = net_status.ifname;
    out->ncm_device_ip = net_status.device_ip;
    out->ncm_netmask = net_status.netmask;
    out->tcpctl_helper_present = net_status.tcpctl_helper;
    out->tcpctl_running = net_status.tcpctl_running;
    out->tcpctl_pid = net_status.tcpctl_pid;
    out->tcpctl_bind_addr = net_status.tcp_bind_addr;
    out->tcpctl_port = net_status.tcp_port;
    out->tcpctl_token_path = net_status.tcp_token_path;
    out->tcpctl_token_present = file_mode_summary(net_status.tcp_token_path,
                                                  out->tcpctl_token_mode,
                                                  sizeof(out->tcpctl_token_mode),
                                                  &out->tcpctl_token_owner_only);
    out->tcpctl_auth_required = true;

    memset(&rshell_info, 0, sizeof(rshell_info));
    (void)a90_service_reap(A90_SERVICE_RSHELL, NULL);
    (void)a90_service_info(A90_SERVICE_RSHELL, &rshell_info);
    runtime_state_path(out->rshell_flag_path,
                       sizeof(out->rshell_flag_path),
                       A90_RSHELL_FLAG_NAME);
    runtime_state_path(out->rshell_token_path,
                       sizeof(out->rshell_token_path),
                       A90_RSHELL_TOKEN_NAME);
    out->rshell_enabled = rshell_info.enabled;
    out->rshell_flag_present = path_exists(out->rshell_flag_path);
    out->rshell_running = rshell_info.running;
    out->rshell_pid = rshell_info.pid;
    out->rshell_bind_addr = A90_RSHELL_BIND_ADDR;
    out->rshell_port = A90_RSHELL_PORT;
    out->rshell_token_present = file_mode_summary(out->rshell_token_path,
                                                 out->rshell_token_mode,
                                                 sizeof(out->rshell_token_mode),
                                                 &out->rshell_token_owner_only);
    rshell_helper = a90_helper_preferred_path("a90_rshell", A90_RSHELL_RAMDISK_HELPER);
    out->rshell_helper_present = rshell_helper != NULL && rshell_helper[0] != '\0' &&
                                 access(rshell_helper, X_OK) == 0;

    if (!out->usb_acm_present) {
        out->warn_count++;
    }
    if (!out->host_bridge_localhost_expected ||
        !out->host_bridge_identity_pinning_expected) {
        out->warn_count++;
    }
    if (strcmp(NETSERVICE_TCP_BIND_ADDR, NETSERVICE_DEVICE_IP) != 0) {
        out->fail_count++;
    }
    if (out->tcpctl_running && !out->ncm_present) {
        out->fail_count++;
    }
    if (out->tcpctl_running && !out->tcpctl_token_present) {
        out->fail_count++;
    }
    if (out->tcpctl_token_present && !out->tcpctl_token_owner_only) {
        out->fail_count++;
    }
    if (out->tcpctl_running && !out->tcpctl_auth_required) {
        out->fail_count++;
    }
    if (strcmp(A90_RSHELL_BIND_ADDR, NETSERVICE_DEVICE_IP) != 0) {
        out->fail_count++;
    }
    if (out->rshell_running && !out->ncm_present) {
        out->fail_count++;
    }
    if (out->rshell_running && !out->rshell_token_present) {
        out->fail_count++;
    }
    if (out->rshell_token_present && !out->rshell_token_owner_only) {
        out->fail_count++;
    }
    if (out->netservice_enabled && !out->tcpctl_running) {
        out->warn_count++;
    }
    if (out->rshell_enabled && !out->rshell_running) {
        out->warn_count++;
    }

    return 0;
}

void a90_exposure_summary(const struct a90_exposure_snapshot *snapshot,
                          char *out,
                          size_t out_size) {
    if (out == NULL || out_size == 0) {
        return;
    }
    if (snapshot == NULL) {
        snprintf(out, out_size, "unavailable");
        return;
    }
    snprintf(out,
             out_size,
             "guard=%s warn=%d fail=%d ncm=%s tcpctl=%s rshell=%s boundary=usb-local",
             snapshot->fail_count == 0 ? "ok" : "fail",
             snapshot->warn_count,
             snapshot->fail_count,
             snapshot->ncm_present ? "present" : "absent",
             snapshot->tcpctl_running ? "running" : "stopped",
             snapshot->rshell_running ? "running" : "stopped");
}

bool a90_exposure_guardrail_ok(const struct a90_exposure_snapshot *snapshot) {
    return snapshot != NULL && snapshot->fail_count == 0;
}

void a90_exposure_print(const struct a90_exposure_snapshot *snapshot,
                        bool verbose) {
    char summary[192];

    if (snapshot == NULL) {
        a90_console_printf("exposure: unavailable\r\n");
        return;
    }
    a90_exposure_summary(snapshot, summary, sizeof(summary));
    a90_console_printf("exposure: %s\r\n", summary);
    a90_console_printf("exposure: acm=%s trusted_lab_only=%s bridge_host=127.0.0.1 bridge_identity_pin=expected\r\n",
            yesno(snapshot->usb_acm_present),
            yesno(snapshot->usb_acm_trusted_local));
    a90_console_printf("exposure: ncm=%s if=%s ip=%s/%s netservice=%s flag=%s\r\n",
            yesno(snapshot->ncm_present),
            snapshot->ncm_ifname != NULL ? snapshot->ncm_ifname : "-",
            snapshot->ncm_device_ip != NULL ? snapshot->ncm_device_ip : "-",
            snapshot->ncm_netmask != NULL ? snapshot->ncm_netmask : "-",
            snapshot->netservice_enabled ? "enabled" : "disabled",
            snapshot->netservice_flag_present ? "present" : "absent");
    a90_console_printf("exposure: tcpctl=%s pid=%ld bind=%s port=%s auth=required token=%s mode=%s owner_only=%s\r\n",
            snapshot->tcpctl_running ? "running" : "stopped",
            (long)snapshot->tcpctl_pid,
            snapshot->tcpctl_bind_addr != NULL ? snapshot->tcpctl_bind_addr : "-",
            snapshot->tcpctl_port != NULL ? snapshot->tcpctl_port : "-",
            snapshot->tcpctl_token_present ? "present" : "missing",
            snapshot->tcpctl_token_mode,
            yesno(snapshot->tcpctl_token_owner_only));
    a90_console_printf("exposure: rshell=%s pid=%ld bind=%s port=%s flag=%s token=%s mode=%s owner_only=%s\r\n",
            snapshot->rshell_running ? "running" : "stopped",
            (long)snapshot->rshell_pid,
            snapshot->rshell_bind_addr != NULL ? snapshot->rshell_bind_addr : "-",
            snapshot->rshell_port != NULL ? snapshot->rshell_port : "-",
            snapshot->rshell_flag_present ? "present" : "absent",
            snapshot->rshell_token_present ? "present" : "missing",
            snapshot->rshell_token_mode,
            yesno(snapshot->rshell_token_owner_only));
    if (verbose) {
        a90_console_printf("exposure: tcpctl_token_path=%s rshell_token_path=%s rshell_flag_path=%s\r\n",
                snapshot->tcpctl_token_path != NULL ? snapshot->tcpctl_token_path : "-",
                snapshot->rshell_token_path,
                snapshot->rshell_flag_path);
        a90_console_printf("exposure: accepted_boundary=F021/F030 while USB-local/localhost-only no_token_values=yes\r\n");
        a90_console_printf("exposure: guardrails bind_tcpctl=%s bind_rshell=%s tcpctl_helper=%s rshell_helper=%s\r\n",
                strcmp(NETSERVICE_TCP_BIND_ADDR, NETSERVICE_DEVICE_IP) == 0 ? "ok" : "fail",
                strcmp(A90_RSHELL_BIND_ADDR, NETSERVICE_DEVICE_IP) == 0 ? "ok" : "fail",
                yesno(snapshot->tcpctl_helper_present),
                yesno(snapshot->rshell_helper_present));
    }
}
