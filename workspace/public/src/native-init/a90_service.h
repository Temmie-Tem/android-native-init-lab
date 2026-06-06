#ifndef A90_SERVICE_H
#define A90_SERVICE_H

#include <stdbool.h>
#include <sys/types.h>

enum a90_service_id {
    A90_SERVICE_HUD = 0,
    A90_SERVICE_TCPCTL,
    A90_SERVICE_ADBD,
    A90_SERVICE_RSHELL,
    A90_SERVICE_LONGSOAK,
    A90_SERVICE_COUNT
};

enum a90_service_kind {
    A90_SERVICE_KIND_DISPLAY = 0,
    A90_SERVICE_KIND_NETWORK,
    A90_SERVICE_KIND_REMOTE,
    A90_SERVICE_KIND_ANDROID,
    A90_SERVICE_KIND_MONITOR,
};

enum a90_service_flag {
    A90_SERVICE_FLAG_NONE = 0,
    A90_SERVICE_FLAG_BOOT_OPTIONAL = 1u << 0,
    A90_SERVICE_FLAG_RAW_CONTROL = 1u << 1,
    A90_SERVICE_FLAG_REQUIRES_NCM = 1u << 2,
    A90_SERVICE_FLAG_DANGEROUS = 1u << 3,
};

struct a90_service_info {
    enum a90_service_id id;
    const char *name;
    const char *description;
    enum a90_service_kind kind;
    unsigned int flags;
    pid_t pid;
    bool running;
    bool enabled;
    const char *enable_path;
};

const char *a90_service_name(enum a90_service_id service);
const char *a90_service_kind_name(enum a90_service_kind kind);
int a90_service_id_from_name(const char *name, enum a90_service_id *out);
int a90_service_count(void);
enum a90_service_id a90_service_id_at(int index);
void a90_service_set_enabled_state(enum a90_service_id service, bool enabled);
bool a90_service_enabled_state(enum a90_service_id service);
int a90_service_info(enum a90_service_id service, struct a90_service_info *out);
void a90_service_reap_all(void);
pid_t a90_service_pid(enum a90_service_id service);
void a90_service_set_pid(enum a90_service_id service, pid_t pid);
void a90_service_clear(enum a90_service_id service);
int a90_service_reap(enum a90_service_id service, int *status_out);
int a90_service_stop(enum a90_service_id service, int timeout_ms);

#endif
