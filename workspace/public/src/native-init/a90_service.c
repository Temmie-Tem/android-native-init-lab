#include "a90_service.h"

#include "a90_config.h"
#include "a90_log.h"
#include "a90_reaper.h"
#include "a90_run.h"

#include <errno.h>
#include <stdbool.h>
#include <string.h>
#include <sys/wait.h>

static pid_t service_pids[A90_SERVICE_COUNT] = {
    -1,
    -1,
    -1,
    -1,
    -1,
};

static bool service_enabled[A90_SERVICE_COUNT] = {
    false,
    false,
    false,
    false,
    false,
};

struct a90_service_descriptor {
    enum a90_service_id id;
    const char *name;
    const char *description;
    enum a90_service_kind kind;
    unsigned int flags;
    const char *enable_path;
};

static const struct a90_service_descriptor service_descriptors[A90_SERVICE_COUNT] = {
    {
        A90_SERVICE_HUD,
        "autohud",
        "status HUD and menu background renderer",
        A90_SERVICE_KIND_DISPLAY,
        A90_SERVICE_FLAG_BOOT_OPTIONAL,
        NULL,
    },
    {
        A90_SERVICE_TCPCTL,
        "tcpctl",
        "USB NCM tcp control service",
        A90_SERVICE_KIND_NETWORK,
        A90_SERVICE_FLAG_BOOT_OPTIONAL |
            A90_SERVICE_FLAG_RAW_CONTROL |
            A90_SERVICE_FLAG_REQUIRES_NCM |
            A90_SERVICE_FLAG_DANGEROUS,
        NETSERVICE_FLAG_PATH,
    },
    {
        A90_SERVICE_ADBD,
        "adbd",
        "experimental Android adbd placeholder",
        A90_SERVICE_KIND_ANDROID,
        A90_SERVICE_FLAG_RAW_CONTROL |
            A90_SERVICE_FLAG_DANGEROUS,
        NULL,
    },
    {
        A90_SERVICE_RSHELL,
        "rshell",
        "token TCP remote shell over USB NCM",
        A90_SERVICE_KIND_REMOTE,
        A90_SERVICE_FLAG_BOOT_OPTIONAL |
            A90_SERVICE_FLAG_RAW_CONTROL |
            A90_SERVICE_FLAG_REQUIRES_NCM |
            A90_SERVICE_FLAG_DANGEROUS,
        A90_RSHELL_FLAG_NAME,
    },
    {
        A90_SERVICE_LONGSOAK,
        "longsoak",
        "device-side long soak recorder",
        A90_SERVICE_KIND_MONITOR,
        A90_SERVICE_FLAG_BOOT_OPTIONAL,
        NULL,
    },
};

static const struct a90_service_descriptor *service_descriptor(enum a90_service_id service) {
    if (service < 0 || service >= A90_SERVICE_COUNT) {
        return NULL;
    }
    if (service_descriptors[service].id != service) {
        return NULL;
    }
    return &service_descriptors[service];
}

const char *a90_service_name(enum a90_service_id service) {
    const struct a90_service_descriptor *descriptor = service_descriptor(service);

    if (descriptor == NULL) {
        return "unknown";
    }
    return descriptor->name;
}

const char *a90_service_kind_name(enum a90_service_kind kind) {
    switch (kind) {
    case A90_SERVICE_KIND_DISPLAY:
        return "display";
    case A90_SERVICE_KIND_NETWORK:
        return "network";
    case A90_SERVICE_KIND_REMOTE:
        return "remote";
    case A90_SERVICE_KIND_ANDROID:
        return "android";
    case A90_SERVICE_KIND_MONITOR:
        return "monitor";
    default:
        return "unknown";
    }
}

int a90_service_id_from_name(const char *name, enum a90_service_id *out) {
    int index;

    if (name == NULL || out == NULL) {
        return -EINVAL;
    }
    if (strcmp(name, "netservice") == 0) {
        *out = A90_SERVICE_TCPCTL;
        return 0;
    }
    for (index = 0; index < A90_SERVICE_COUNT; ++index) {
        if (strcmp(name, service_descriptors[index].name) == 0) {
            *out = service_descriptors[index].id;
            return 0;
        }
    }
    return -ENOENT;
}

int a90_service_count(void) {
    return A90_SERVICE_COUNT;
}

enum a90_service_id a90_service_id_at(int index) {
    if (index < 0 || index >= A90_SERVICE_COUNT) {
        return A90_SERVICE_COUNT;
    }
    return service_descriptors[index].id;
}

void a90_service_set_enabled_state(enum a90_service_id service, bool enabled) {
    if (service_descriptor(service) == NULL) {
        return;
    }
    service_enabled[service] = enabled;
}

bool a90_service_enabled_state(enum a90_service_id service) {
    if (service_descriptor(service) == NULL) {
        return false;
    }
    return service_enabled[service];
}

int a90_service_info(enum a90_service_id service, struct a90_service_info *out) {
    const struct a90_service_descriptor *descriptor = service_descriptor(service);

    if (descriptor == NULL || out == NULL) {
        return -EINVAL;
    }
    out->id = descriptor->id;
    out->name = descriptor->name;
    out->description = descriptor->description;
    out->kind = descriptor->kind;
    out->flags = descriptor->flags;
    out->pid = service_pids[service];
    out->running = out->pid > 0;
    out->enabled = service_enabled[service];
    out->enable_path = descriptor->enable_path;
    return 0;
}

void a90_service_reap_all(void) {
    int index;

    for (index = 0; index < A90_SERVICE_COUNT; ++index) {
        (void)a90_service_reap(service_descriptors[index].id, NULL);
    }
    (void)a90_reaper_reap_orphans("service-reap-all");
}

static const char *service_name_for_log(enum a90_service_id service) {
    switch (service) {
    case A90_SERVICE_HUD:
        return "autohud";
    case A90_SERVICE_TCPCTL:
        return "tcpctl";
    case A90_SERVICE_ADBD:
        return "adbd";
    case A90_SERVICE_RSHELL:
        return "rshell";
    case A90_SERVICE_LONGSOAK:
        return "longsoak";
    default:
        return "unknown";
    }
}

static int valid_service(enum a90_service_id service) {
    return service_descriptor(service) != NULL;
}

pid_t a90_service_pid(enum a90_service_id service) {
    if (!valid_service(service)) {
        return -1;
    }
    return service_pids[service];
}

void a90_service_set_pid(enum a90_service_id service, pid_t pid) {
    if (!valid_service(service)) {
        return;
    }
    service_pids[service] = pid;
    a90_logf("service", "%s pid=%ld", service_name_for_log(service), (long)pid);
}

void a90_service_clear(enum a90_service_id service) {
    if (!valid_service(service)) {
        return;
    }
    if (service_pids[service] > 0) {
        a90_logf("service", "%s clear pid=%ld",
                    service_name_for_log(service), (long)service_pids[service]);
    }
    service_pids[service] = -1;
}

int a90_service_reap(enum a90_service_id service, int *status_out) {
    pid_t pid;
    int status = 0;
    int rc;

    if (!valid_service(service)) {
        return -EINVAL;
    }

    pid = service_pids[service];
    if (pid <= 0) {
        return 0;
    }

    rc = a90_run_reap_pid(pid, &status);
    if (rc == 1) {
        if (status_out != NULL) {
            *status_out = status;
        }
        a90_logf("service", "%s reaped pid=%ld status=0x%x",
                    service_name_for_log(service), (long)pid, status);
        service_pids[service] = -1;
        return 1;
    }
    if (rc < 0) {
        a90_logf("service", "%s reap failed pid=%ld rc=%d error=%s",
                    service_name_for_log(service), (long)pid, rc, strerror(-rc));
    }
    return rc;
}

int a90_service_stop(enum a90_service_id service, int timeout_ms) {
    pid_t pid;
    int status = 0;
    int rc;

    if (!valid_service(service)) {
        return -EINVAL;
    }

    pid = service_pids[service];
    if (pid <= 0) {
        return 0;
    }

    rc = a90_run_stop_pid(pid, service_name_for_log(service), timeout_ms, &status);
    service_pids[service] = -1;
    a90_logf("service", "%s stopped pid=%ld rc=%d status=0x%x",
                service_name_for_log(service), (long)pid, rc, status);
    return rc;
}
