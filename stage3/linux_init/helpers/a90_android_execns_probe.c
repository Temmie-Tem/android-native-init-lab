#define _GNU_SOURCE

#include <errno.h>
#include <endian.h>
#include <fcntl.h>
#include <poll.h>
#include <stddef.h>
#include <stdint.h>
#include <signal.h>
#include <stdbool.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mount.h>
#include <sys/mman.h>
#include <sys/ioctl.h>
#include <sys/ptrace.h>
#include <sys/stat.h>
#include <sys/sysmacros.h>
#include <sys/types.h>
#include <sys/uio.h>
#include <sys/wait.h>
#include <sys/prctl.h>
#include <sys/syscall.h>
#include <sys/socket.h>
#include <time.h>
#include <unistd.h>
#include <sched.h>
#include <elf.h>
#include <dirent.h>
#include <grp.h>
#include <linux/capability.h>
#include <linux/android/binder.h>
#include <linux/genetlink.h>
#include <linux/netlink.h>
#include <linux/nl80211.h>
#include <linux/qrtr.h>
#include <linux/rtnetlink.h>
#include <sys/un.h>

#ifndef MNT_DETACH
#define MNT_DETACH 2
#endif
#ifndef PTRACE_O_EXITKILL
#define PTRACE_O_EXITKILL 0x00100000
#endif
#ifndef NT_PRSTATUS
#define NT_PRSTATUS 1
#endif
#ifndef PR_CAP_AMBIENT
#define PR_CAP_AMBIENT 47
#endif
#ifndef PR_CAP_AMBIENT_RAISE
#define PR_CAP_AMBIENT_RAISE 2
#endif
#ifndef CAP_BLOCK_SUSPEND
#define CAP_BLOCK_SUSPEND 36
#endif
#ifndef BINDER_BUFFER_FLAG_REF
#define BINDER_BUFFER_FLAG_REF 0x02
#endif
#ifndef NLA_ALIGNTO
#define NLA_ALIGNTO 4
#endif
#ifndef NLA_ALIGN
#define NLA_ALIGN(len) (((len) + NLA_ALIGNTO - 1) & ~(NLA_ALIGNTO - 1))
#endif
#ifndef NLA_HDRLEN
#define NLA_HDRLEN ((int)NLA_ALIGN(sizeof(struct nlattr)))
#endif
#ifndef NLA_TYPE_MASK
#define NLA_TYPE_MASK ~(NLA_F_NESTED | NLA_F_NET_BYTEORDER)
#endif
#ifndef AF_QIPCRTR
#define AF_QIPCRTR 42
#endif
#ifndef IOPRIO_WHO_PROCESS
#define IOPRIO_WHO_PROCESS 1
#endif
#ifndef IOPRIO_CLASS_SHIFT
#define IOPRIO_CLASS_SHIFT 13
#endif
#ifndef IOPRIO_CLASS_RT
#define IOPRIO_CLASS_RT 1
#endif
#ifndef IOPRIO_PRIO_VALUE
#define IOPRIO_PRIO_VALUE(class_value, data) (((class_value) << IOPRIO_CLASS_SHIFT) | (data))
#endif

#define EXECNS_VERSION "a90_android_execns_probe v139"
#define MAX_PATH_LEN 512
#define MAX_CAPTURE_SIZE (1024 * 1024)
#define MAX_LINKERCONFIG_SIZE (256 * 1024)
#define MAX_SEPOLICY_LOAD_SIZE (16 * 1024 * 1024)
#define DEFAULT_QRTR_READBACK_MATRIX "wlfw:69:0,1"
#define MAX_QRTR_READBACK_CASES 16
#define MAX_QRTR_READBACK_LABEL 32
#define A90_SERVLOC_SERVICE 64U
#define A90_SERVLOC_INSTANCE_ENCODED 257U
#define A90_SERVLOC_GET_DOMAIN_LIST_MSG_ID 0x0021U
#define A90_SERVLOC_TXN_ID 1U
#define A90_SERVLOC_READBACK_MS 1000U
#define A90_SERVLOC_RESPONSE_MS 2000U
#define A90_SERVNOTIF_SERVICE 66U
#define A90_SERVNOTIF_INSTANCE_ENCODED 46081U
#define A90_SERVNOTIF_REGISTER_LISTENER_MSG_ID 0x0020U
#define A90_SERVNOTIF_STATE_UPDATED_IND_MSG_ID 0x0022U
#define A90_SERVNOTIF_ACK_MSG_ID 0x0023U
#define A90_SERVNOTIF_TXN_ID 1U
#define A90_SERVNOTIF_ACK_TXN_ID 2U
#define A90_SERVNOTIF_READBACK_MS 10000U
#define A90_SERVNOTIF_RESPONSE_MS 15000U
#define A90_WLAN_PD_SERVICE_NAME "msm/modem/wlan_pd"
#define A90_PROP_NAME_MAX 512
#define A90_PROP_VALUE_MAX 1024
#define A90_PROP_LEGACY_NAME_MAX 32
#define A90_PROP_LEGACY_VALUE_MAX 92
#define A90_PROP_MSG_SETPROP 0x00000001u
#define A90_PROP_MSG_SETPROP2 0x00020001u
#define A90_PROP_SUCCESS 0u
#define A90_PROP_ERROR_READ_CMD 0x0004u
#define A90_PROP_ERROR_READ_DATA 0x0008u
#define A90_PROP_ERROR_PERMISSION_DENIED 0x0018u
#define A90_PROP_ERROR_INVALID_CMD 0x001bu
#define A90_AID_SYSTEM 1000
#define A90_AID_SDCARD_RW 1015
#define A90_AID_WIFI 1010
#define A90_AID_GPS 1021
#define A90_AID_MEDIA_RW 1023
#define A90_AID_DIAG 2002
#define A90_AID_SHELL 2000
#define A90_AID_VENDOR_RFS 2903
#define A90_AID_VENDOR_RFS_SHARED 2904
#define A90_AID_VENDOR_QRTR 2906
#define A90_AID_INET 3003
#define A90_AID_NET_RAW 3004
#define A90_AID_NET_ADMIN 3005
#define A90_AID_READPROC 3009
#define A90_AID_WAKELOCK 3010
#define A90_AID_NOBODY 9999
#define A90_WIFI_HAL_COMPOSITE_CHILD_COUNT 3
#define A90_WIFI_SURFACE_COMPOSITE_CHILD_COUNT 5
#define A90_COMPOSITE_CHILD_MAX 14
#define A90_WIFI_HAL_WAIT_TARGET_COUNT 3
#define A90_HWBINDER_DATA_MAX 2048
#define A90_HWBINDER_OBJECT_MAX 16
#define A90_HWBINDER_READ_MAX 8192
#define A90_HWBINDER_VM_SIZE ((1024 * 1024) - (4096 * 2))
#define A90_STRICT_MODE_PENALTY_GATHER (0x40 << 16)
#define A90_NL80211_RECV_BUF_SIZE 65536
#define A90_NL80211_IFNAME_MAX 64
#define A90_SYSLOG_ACTION_READ_ALL 3
#define A90_SERVICE74_GATE_KLOG_BYTES (256 * 1024)
#define A90_SERVICE74_GATE_WAIT_MS 12000L
#define A90_VNDSERVICEMANAGER_READY_SETTLE_MS 1000L
#ifndef SYS_syslog
#ifdef __NR_syslog
#define SYS_syslog __NR_syslog
#endif
#endif
#define A90_ESOC_CODE 0xCC
#define A90_ESOC_CMD_EXE _IOW(A90_ESOC_CODE, 1, unsigned int)
#define A90_ESOC_WAIT_FOR_REQ _IOR(A90_ESOC_CODE, 2, unsigned int)
#define A90_ESOC_NOTIFY _IOW(A90_ESOC_CODE, 3, unsigned int)
#define A90_ESOC_GET_STATUS _IOR(A90_ESOC_CODE, 4, unsigned int)
#define A90_ESOC_GET_ERR_FATAL _IOR(A90_ESOC_CODE, 5, unsigned int)
#define A90_ESOC_WAIT_FOR_CRASH _IOR(A90_ESOC_CODE, 6, unsigned int)
#define A90_ESOC_REG_REQ_ENG _IO(A90_ESOC_CODE, 7)
#define A90_ESOC_REG_CMD_ENG _IO(A90_ESOC_CODE, 8)
#define A90_ESOC_GET_LINK_ID _IOWR(A90_ESOC_CODE, 9, uint64_t)
#define A90_ESOC_PWR_ON 1U
#define A90_ESOC_IMG_XFER_DONE 1U
#define A90_ESOC_BOOT_DONE 2U

struct config {
    const char *system_root;
    const char *vendor_block;
    const char *vendor_fstype;
    const char *target;
    const char *target_profile;
    const char *linker;
    const char *env_mode;
    const char *mode;
    const char *capture_mode;
    const char *null_device_mode;
    const char *data_wifi_mode;
    const char *vndk_apex_alias_mode;
    const char *linkerconfig_mode;
    const char *linkerconfig_source;
    const char *apex_libraries_source;
    const char *property_root;
    const char *property_key;
    const char *selinux_context;
    const char *selinux_attr_mode;
    const char *android_selinux_context_mode;
    const char *connect_config;
    const char *connect_iface;
    const char *ping_target;
    const char *qrtr_readback_matrix;
    int timeout_sec;
    bool allow_cnss_start_only;
    bool allow_wifi_companion_start_only;
    bool allow_service_manager_start_only;
    bool allow_wifi_hal_start_only;
    bool allow_hal_service_query;
    bool allow_iwifi_start_only;
    bool allow_wlan_driver_state_on;
    bool allow_cnss_userspace_readiness;
    bool allow_qrtr_ns_readback;
    bool allow_servloc_domain_list_probe;
    bool allow_service_notifier_listener_probe;
    bool allow_scan_only;
    bool allow_connect_dhcp_ping;
    bool allow_policy_load_proof;
    bool allow_esoc_control_preflight;
    bool allow_esoc_engine_register_preflight;
    bool allow_esoc_req_registered_subsys_hold_preflight;
};

struct a90_hidl_string_wire {
    binder_uintptr_t buffer;
    uint32_t size;
    bool owns_buffer;
    uint8_t pad[3];
};

struct a90_wifi_status_wire {
    uint32_t code;
    uint32_t pad;
    struct a90_hidl_string_wire description;
};

struct a90_hwbinder_parcel {
    uint8_t data[A90_HWBINDER_DATA_MAX];
    binder_size_t offsets[A90_HWBINDER_OBJECT_MAX];
    struct a90_hidl_string_wire strings[4];
    size_t data_size;
    size_t offsets_count;
    size_t buffers_size;
    size_t string_count;
};

struct a90_hwbinder_reply {
    uint8_t *data;
    binder_size_t *offsets;
    size_t data_size;
    size_t offsets_count;
    binder_uintptr_t free_buffer;
    bool has_free_buffer;
    bool failed_reply;
    bool dead_reply;
    bool frozen_reply;
    bool status_code;
    int32_t status_value;
};

enum a90_hwbinder_token_wire {
    A90_HWBINDER_TOKEN_STRING16_STRICTMODE = 0,
    A90_HWBINDER_TOKEN_CSTRING = 1,
};

struct buffer {
    char *data;
    size_t len;
    size_t cap;
    bool truncated;
};

struct paths {
    char base[MAX_PATH_LEN];
    char root[MAX_PATH_LEN];
    char system[MAX_PATH_LEN];
    char vendor[MAX_PATH_LEN];
    char vendor_source[MAX_PATH_LEN];
    char vendor_firmware_mnt[MAX_PATH_LEN];
    char vendor_firmware_modem[MAX_PATH_LEN];
    char firmware_mnt_source[MAX_PATH_LEN];
    char firmware_modem_source[MAX_PATH_LEN];
    char dev[MAX_PATH_LEN];
    char dev_null[MAX_PATH_LEN];
    char dev_wlan[MAX_PATH_LEN];
    char dev_block[MAX_PATH_LEN];
    char dev_block_by_name[MAX_PATH_LEN];
    char dev_block_bootdevice[MAX_PATH_LEN];
    char dev_block_bootdevice_by_name[MAX_PATH_LEN];
    char dev_uio0[MAX_PATH_LEN];
    char dev_kmsg[MAX_PATH_LEN];
    char dev_binder[MAX_PATH_LEN];
    char dev_hwbinder[MAX_PATH_LEN];
    char dev_vndbinder[MAX_PATH_LEN];
    char dev_properties[MAX_PATH_LEN];
    char dev_socket[MAX_PATH_LEN];
    char property_service_socket[MAX_PATH_LEN];
    char sys[MAX_PATH_LEN];
    char sys_bus[MAX_PATH_LEN];
    char sys_bus_esoc[MAX_PATH_LEN];
    char sys_bus_msm_subsys[MAX_PATH_LEN];
    char sys_class[MAX_PATH_LEN];
    char sys_class_uio[MAX_PATH_LEN];
    char sys_devices[MAX_PATH_LEN];
    char sys_devices_platform[MAX_PATH_LEN];
    char sys_devices_platform_soc[MAX_PATH_LEN];
    char sys_devices_platform_soc_mdm3[MAX_PATH_LEN];
    char sys_devices_platform_soc_mss[MAX_PATH_LEN];
    char sys_power[MAX_PATH_LEN];
    char sys_power_wake_lock[MAX_PATH_LEN];
    char sys_power_wake_unlock[MAX_PATH_LEN];
    char sys_fs[MAX_PATH_LEN];
    char sys_fs_selinux[MAX_PATH_LEN];
    char sys_fs_selinux_null[MAX_PATH_LEN];
    char sys_fs_selinux_status[MAX_PATH_LEN];
    char sys_fs_selinux_enforce[MAX_PATH_LEN];
    char sys_fs_selinux_load[MAX_PATH_LEN];
    char data[MAX_PATH_LEN];
    char data_vendor[MAX_PATH_LEN];
    char data_vendor_wifi[MAX_PATH_LEN];
    char data_vendor_wifi_sockets[MAX_PATH_LEN];
    char proc[MAX_PATH_LEN];
    char apex[MAX_PATH_LEN];
    char linkerconfig[MAX_PATH_LEN];
    bool apex_synthetic;
};

static void usage(FILE *out) {
    fprintf(out, "%s\n", EXECNS_VERSION);
    fprintf(out,
            "usage: a90_android_execns_probe "
            "--system-root /mnt/system/system "
            "--vendor-block /dev/block/sda29 "
            "--vendor-fstype ext4 "
            "[--target-profile cnss-daemon|system-toybox|system-sh|linker64-self|apex-linker64-self|system-getprop|system-servicemanager|system-hwservicemanager|vendor-wifi-hal-ext|vendor-wifi-hal-legacy] "
            "[--target /vendor/bin/cnss-daemon] "
            "[--linker /system/bin/linker64|/apex/com.android.runtime/bin/linker64] "
            "[--env-mode clean|ld-debug-1|ld-debug-2|auxv] "
            "[--capture-mode none|ptrace-lite] "
            "[--null-device-mode none|dev-null|dev-null-selinux] "
            "[--data-wifi-mode none|private-empty] "
            "[--vndk-apex-alias-mode none|v30-to-current|v30-to-system-ext-v30] "
            "[--linkerconfig-mode none|copy-real|minimal-vendor] "
            "[--linkerconfig-source /cache/path/to/ld.config.txt] "
            "[--apex-libraries-source /cache/path/to/apex.libraries.config.txt] "
            "[--property-root /mnt/sdext/a90/private-property-v317/.../dev/__properties__] "
            "[--property-key ro.build.version.sdk] "
            "[--selinux-context u:r:hal_wifi_default:s0] "
            "[--selinux-attr-mode current|exec|both] "
            "[--android-selinux-context-mode auto|none|service-defaults] "
            "[internal --selinux-print-current static postexec proof] "
            "[--allow-cnss-start-only] "
            "[--allow-wifi-companion-start-only] "
            "[--allow-service-manager-start-only] "
            "[--allow-wifi-hal-start-only] "
            "[--allow-hal-service-query] "
            "[--allow-iwifi-start-only] "
            "[--allow-wlan-driver-state-on] "
            "[--allow-cnss-userspace-readiness] "
            "[--allow-qrtr-ns-readback] "
            "[--allow-servloc-domain-list-probe] "
            "[--allow-service-notifier-listener-probe] "
            "[--allow-scan-only] "
            "[--allow-connect-dhcp-ping] "
            "[--allow-policy-load-proof] "
            "[--allow-esoc-control-preflight] "
            "[--allow-esoc-engine-register-preflight] "
            "[--allow-esoc-req-registered-subsys-hold-preflight] "
            "[--qrtr-readback-matrix label:service:instance[,instance][;...]] "
            "[--connect-config /cache/a90-wifi/...] "
            "[--connect-iface auto|wlan0] "
            "[--ping-target 1.1.1.1] "
            "--mode linker-list|identity-probe|sepolicy-inventory|sepolicy-compile-proof|sepolicy-load-proof|selinux-domain-proof|cnss-start-only|cnss-userspace-readiness|wifi-companion-start-only|wifi-companion-post-sysmon-observer-start-only|wifi-companion-android-order-post-sysmon-observer-start-only|wifi-companion-service-manager-start-only|wifi-companion-vnd-service-manager-start-only|wifi-companion-qrtr-first-vnd-service-manager-start-only|wifi-companion-cnss-first-delayed-vnd-service-manager-start-only|wifi-companion-service74-gated-vnd-service-manager-start-only|wifi-companion-service74-gated-vnd-service-manager-readiness-start-only|wifi-companion-service74-gated-vnd-service-manager-cnss-retry-start-only|wifi-companion-peripheral-manager-node-parity-start-only|wifi-companion-peripheral-manager-property-contract-start-only|wifi-companion-peripheral-manager-init-contract-start-only|wifi-companion-esoc-control-preflight|wifi-companion-esoc-engine-register-preflight|wifi-companion-esoc-req-registered-subsys-hold-preflight|wifi-companion-service74-gated-peripheral-manager-cnss-retry-start-only|wifi-companion-service74-gated-peripheral-manager-cnss-retry-registry-snapshot-start-only|wifi-companion-service74-gated-peripheral-manager-vndservice-query-start-only|wifi-companion-service74-gated-peripheral-manager-vndservice-query-cnss-retry-start-only|wifi-companion-service74-gated-peripheral-manager-vndservice-query-provider-first-cnss-start-only|wifi-companion-service74-gated-android-userspace-cnss-retry-start-only|wifi-companion-service74-gated-android-userspace-cnss-retry-registry-snapshot-start-only|wifi-companion-service74-gated-vnd-service-manager-registry-snapshot-start-only|wifi-companion-service74-gated-mdm-helper-start-only|wifi-companion-service180-gated-mdm-helper-start-only|wifi-companion-sysmon-gated-mdm-helper-start-only|wifi-companion-hal-order-start-only|wifi-companion-hal-wificond-order-start-only|wifi-companion-hal-wificond-lshal-wait-samsung|wifi-companion-hal-wificond-lshal-wait-iwifi|wifi-companion-dual-hal-wificond-lshal-wait-iwifi|wifi-companion-dual-hal-wificond-iwifi-start|wifi-companion-dual-hal-wificond-lshal-then-iwifi-start|rmt-storage-start-only|property-lookup|service-manager-start-only|private-selinux-proof|wifi-hal-lshal-vintf-status-list|wifi-hal-composite-start-only|wifi-hal-composite-lshal-list|wifi-hal-composite-lshal-binderized-list|wifi-hal-composite-lshal-wait-target|wifi-surface-composite-lshal-wait-iwifi|wifi-surface-composite-lshal-wait-samsung|wifi-surface-composite-lshal-wait-samsung-ptrace|wifi-hal-composite-lshal-status-list|wifi-hal-composite-lshal-binderized-status-list|wifi-surface-composite-start-only|wifi-dual-hal-lshal-wait-iwifi|wifi-dual-hal-iwifi-start-surface|wifi-iwifi-start-surface|wifi-active-session-surface|wifi-active-session-scan-only|wifi-active-session-connect-ping|wifi-connect-tool-surface|subsys-hold-open-proof|service-notifier-listener-only "
            "[v27 binderized query runs: /system/bin/lshal list --types=binderized --neat] "
            "[v28 target query runs: /system/bin/lshal wait <fqinstance>] "
            "[v29 status query runs: /system/bin/lshal list --types=binderized,vintf --neat -V -S -i -p -e -c] "
            "[v29 VINTF control runs: /system/bin/lshal list --types=vintf --neat -V -S -i] "
            "[v30 binderized status query runs: /system/bin/lshal list --types=binderized --neat -S] "
            "--timeout-sec <1..30>\n");
}

static bool streq(const char *a, const char *b) {
    return a != NULL && b != NULL && strcmp(a, b) == 0;
}

static bool is_wifi_hal_composite_mode(const char *mode) {
    return streq(mode, "wifi-hal-composite-start-only") ||
           streq(mode, "wifi-hal-composite-lshal-list") ||
           streq(mode, "wifi-hal-composite-lshal-binderized-list") ||
           streq(mode, "wifi-hal-composite-lshal-wait-target") ||
           streq(mode, "wifi-surface-composite-lshal-wait-iwifi") ||
           streq(mode, "wifi-surface-composite-lshal-wait-samsung") ||
           streq(mode, "wifi-surface-composite-lshal-wait-samsung-ptrace") ||
           streq(mode, "wifi-hal-composite-lshal-status-list") ||
           streq(mode, "wifi-hal-composite-lshal-binderized-status-list") ||
           streq(mode, "wifi-surface-composite-start-only") ||
           streq(mode, "wifi-dual-hal-lshal-wait-iwifi") ||
           streq(mode, "wifi-dual-hal-iwifi-start-surface") ||
           streq(mode, "wifi-iwifi-start-surface") ||
           streq(mode, "wifi-active-session-surface") ||
           streq(mode, "wifi-active-session-scan-only") ||
           streq(mode, "wifi-active-session-connect-ping");
}

static bool is_wifi_surface_composite_mode(const char *mode) {
    return streq(mode, "wifi-surface-composite-start-only") ||
           streq(mode, "wifi-surface-composite-lshal-wait-iwifi") ||
           streq(mode, "wifi-surface-composite-lshal-wait-samsung") ||
           streq(mode, "wifi-surface-composite-lshal-wait-samsung-ptrace") ||
           streq(mode, "wifi-dual-hal-lshal-wait-iwifi") ||
           streq(mode, "wifi-dual-hal-iwifi-start-surface") ||
           streq(mode, "wifi-iwifi-start-surface") ||
           streq(mode, "wifi-active-session-surface") ||
           streq(mode, "wifi-active-session-scan-only") ||
           streq(mode, "wifi-active-session-connect-ping");
}

static bool is_wifi_dual_hal_iwifi_start_mode(const char *mode) {
    return streq(mode, "wifi-dual-hal-iwifi-start-surface");
}

static bool is_wifi_dual_hal_composite_mode(const char *mode) {
    return streq(mode, "wifi-dual-hal-lshal-wait-iwifi") ||
           is_wifi_dual_hal_iwifi_start_mode(mode);
}

static bool is_wifi_active_session_surface_mode(const char *mode) {
    return streq(mode, "wifi-active-session-surface") ||
           streq(mode, "wifi-active-session-scan-only") ||
           streq(mode, "wifi-active-session-connect-ping");
}

static bool is_wifi_active_session_scan_only_mode(const char *mode) {
    return streq(mode, "wifi-active-session-scan-only");
}

static bool is_wifi_active_session_connect_ping_mode(const char *mode) {
    return streq(mode, "wifi-active-session-connect-ping");
}

static bool is_wifi_connect_tool_surface_mode(const char *mode) {
    return streq(mode, "wifi-connect-tool-surface");
}

static bool is_subsys_hold_open_proof_mode(const char *mode) {
    return streq(mode, "subsys-hold-open-proof");
}

static bool is_service_notifier_listener_only_mode(const char *mode) {
    return streq(mode, "service-notifier-listener-only");
}

static bool is_cnss_userspace_readiness_mode(const char *mode) {
    return streq(mode, "cnss-userspace-readiness");
}

static bool is_wifi_companion_start_only_mode(const char *mode) {
    return streq(mode, "wifi-companion-start-only");
}

static bool is_wifi_companion_post_sysmon_observer_start_only_mode(const char *mode) {
    return streq(mode, "wifi-companion-post-sysmon-observer-start-only");
}

static bool is_wifi_companion_android_order_post_sysmon_observer_start_only_mode(const char *mode) {
    return streq(mode, "wifi-companion-android-order-post-sysmon-observer-start-only");
}

static bool is_wifi_companion_service_manager_start_only_mode(const char *mode) {
    return streq(mode, "wifi-companion-service-manager-start-only");
}

static bool is_wifi_companion_vnd_service_manager_start_only_mode(const char *mode) {
    return streq(mode, "wifi-companion-vnd-service-manager-start-only");
}

static bool is_wifi_companion_qrtr_first_vnd_service_manager_start_only_mode(const char *mode) {
    return streq(mode, "wifi-companion-qrtr-first-vnd-service-manager-start-only");
}

static bool is_wifi_companion_cnss_first_delayed_vnd_service_manager_start_only_mode(const char *mode) {
    return streq(mode, "wifi-companion-cnss-first-delayed-vnd-service-manager-start-only");
}

static bool is_wifi_companion_service74_gated_vnd_service_manager_start_only_mode(const char *mode) {
    return streq(mode, "wifi-companion-service74-gated-vnd-service-manager-start-only");
}

static bool is_wifi_companion_service74_gated_vnd_service_manager_readiness_start_only_mode(const char *mode) {
    return streq(mode, "wifi-companion-service74-gated-vnd-service-manager-readiness-start-only");
}

static bool is_wifi_companion_service74_gated_vnd_service_manager_cnss_retry_start_only_mode(const char *mode) {
    return streq(mode, "wifi-companion-service74-gated-vnd-service-manager-cnss-retry-start-only");
}

static bool is_wifi_companion_peripheral_manager_node_parity_start_only_mode(const char *mode) {
    return streq(mode, "wifi-companion-peripheral-manager-node-parity-start-only");
}

static bool is_wifi_companion_peripheral_manager_property_contract_start_only_mode(const char *mode) {
    return streq(mode, "wifi-companion-peripheral-manager-property-contract-start-only");
}

static bool is_wifi_companion_peripheral_manager_init_contract_start_only_mode(const char *mode) {
    return streq(mode, "wifi-companion-peripheral-manager-init-contract-start-only");
}

static bool is_wifi_companion_esoc_control_preflight_mode(const char *mode) {
    return streq(mode, "wifi-companion-esoc-control-preflight");
}

static bool is_wifi_companion_esoc_engine_register_preflight_mode(const char *mode) {
    return streq(mode, "wifi-companion-esoc-engine-register-preflight");
}

static bool is_wifi_companion_esoc_req_registered_subsys_hold_preflight_mode(const char *mode) {
    return streq(mode, "wifi-companion-esoc-req-registered-subsys-hold-preflight");
}

static bool is_wifi_companion_peripheral_manager_service_node_materialization_mode(const char *mode) {
    return is_wifi_companion_peripheral_manager_node_parity_start_only_mode(mode) ||
           is_wifi_companion_peripheral_manager_property_contract_start_only_mode(mode) ||
           is_wifi_companion_peripheral_manager_init_contract_start_only_mode(mode);
}

static bool is_wifi_companion_peripheral_manager_node_materialization_mode(const char *mode) {
    return is_wifi_companion_peripheral_manager_service_node_materialization_mode(mode) ||
           is_wifi_companion_esoc_control_preflight_mode(mode) ||
           is_wifi_companion_esoc_engine_register_preflight_mode(mode) ||
           is_wifi_companion_esoc_req_registered_subsys_hold_preflight_mode(mode);
}

static bool is_wifi_companion_service74_gated_peripheral_manager_cnss_retry_start_only_mode(const char *mode) {
    return streq(mode, "wifi-companion-service74-gated-peripheral-manager-cnss-retry-start-only");
}

static bool is_wifi_companion_service74_gated_peripheral_manager_cnss_retry_registry_snapshot_start_only_mode(const char *mode) {
    return streq(mode, "wifi-companion-service74-gated-peripheral-manager-cnss-retry-registry-snapshot-start-only");
}

static bool is_wifi_companion_service74_gated_peripheral_manager_vndservice_query_start_only_mode(const char *mode) {
    return streq(mode, "wifi-companion-service74-gated-peripheral-manager-vndservice-query-start-only");
}

static bool is_wifi_companion_service74_gated_peripheral_manager_vndservice_query_cnss_retry_start_only_mode(const char *mode) {
    return streq(mode, "wifi-companion-service74-gated-peripheral-manager-vndservice-query-cnss-retry-start-only");
}

static bool is_wifi_companion_service74_gated_peripheral_manager_vndservice_query_provider_first_cnss_start_only_mode(const char *mode) {
    return streq(mode, "wifi-companion-service74-gated-peripheral-manager-vndservice-query-provider-first-cnss-start-only");
}

static bool is_wifi_companion_service74_gated_android_userspace_cnss_retry_start_only_mode(const char *mode) {
    return streq(mode, "wifi-companion-service74-gated-android-userspace-cnss-retry-start-only");
}

static bool is_wifi_companion_service74_gated_android_userspace_cnss_retry_registry_snapshot_start_only_mode(const char *mode) {
    return streq(mode, "wifi-companion-service74-gated-android-userspace-cnss-retry-registry-snapshot-start-only");
}

static bool is_wifi_companion_service74_gated_vnd_service_manager_registry_snapshot_start_only_mode(const char *mode) {
    return streq(mode, "wifi-companion-service74-gated-vnd-service-manager-registry-snapshot-start-only");
}

static bool is_wifi_companion_service74_gated_mdm_helper_start_only_mode(const char *mode) {
    return streq(mode, "wifi-companion-service74-gated-mdm-helper-start-only");
}

static bool is_wifi_companion_service180_gated_mdm_helper_start_only_mode(const char *mode) {
    return streq(mode, "wifi-companion-service180-gated-mdm-helper-start-only");
}

static bool is_wifi_companion_sysmon_gated_mdm_helper_start_only_mode(const char *mode) {
    return streq(mode, "wifi-companion-sysmon-gated-mdm-helper-start-only");
}

static bool is_wifi_companion_with_service_manager_start_only_mode(const char *mode) {
    return is_wifi_companion_service_manager_start_only_mode(mode) ||
           is_wifi_companion_vnd_service_manager_start_only_mode(mode) ||
           is_wifi_companion_qrtr_first_vnd_service_manager_start_only_mode(mode) ||
           is_wifi_companion_cnss_first_delayed_vnd_service_manager_start_only_mode(mode) ||
           is_wifi_companion_service74_gated_vnd_service_manager_start_only_mode(mode) ||
           is_wifi_companion_service74_gated_vnd_service_manager_readiness_start_only_mode(mode) ||
           is_wifi_companion_service74_gated_vnd_service_manager_cnss_retry_start_only_mode(mode) ||
           is_wifi_companion_peripheral_manager_service_node_materialization_mode(mode) ||
           is_wifi_companion_service74_gated_peripheral_manager_cnss_retry_start_only_mode(mode) ||
           is_wifi_companion_service74_gated_peripheral_manager_cnss_retry_registry_snapshot_start_only_mode(mode) ||
           is_wifi_companion_service74_gated_peripheral_manager_vndservice_query_start_only_mode(mode) ||
           is_wifi_companion_service74_gated_peripheral_manager_vndservice_query_cnss_retry_start_only_mode(mode) ||
           is_wifi_companion_service74_gated_peripheral_manager_vndservice_query_provider_first_cnss_start_only_mode(mode) ||
           is_wifi_companion_service74_gated_android_userspace_cnss_retry_start_only_mode(mode) ||
           is_wifi_companion_service74_gated_android_userspace_cnss_retry_registry_snapshot_start_only_mode(mode) ||
           is_wifi_companion_service74_gated_vnd_service_manager_registry_snapshot_start_only_mode(mode);
}

static bool is_wifi_companion_any_start_only_mode(const char *mode) {
    return is_wifi_companion_start_only_mode(mode) ||
           is_wifi_companion_post_sysmon_observer_start_only_mode(mode) ||
           is_wifi_companion_android_order_post_sysmon_observer_start_only_mode(mode) ||
           is_wifi_companion_service74_gated_mdm_helper_start_only_mode(mode) ||
           is_wifi_companion_service180_gated_mdm_helper_start_only_mode(mode) ||
           is_wifi_companion_sysmon_gated_mdm_helper_start_only_mode(mode) ||
           is_wifi_companion_with_service_manager_start_only_mode(mode);
}

static bool is_wifi_companion_hal_order_start_only_mode(const char *mode) {
    return streq(mode, "wifi-companion-hal-order-start-only") ||
           streq(mode, "wifi-companion-hal-wificond-order-start-only") ||
           streq(mode, "wifi-companion-hal-wificond-lshal-wait-samsung") ||
           streq(mode, "wifi-companion-hal-wificond-lshal-wait-iwifi") ||
           streq(mode, "wifi-companion-dual-hal-wificond-lshal-wait-iwifi") ||
           streq(mode, "wifi-companion-dual-hal-wificond-iwifi-start") ||
           streq(mode, "wifi-companion-dual-hal-wificond-lshal-then-iwifi-start");
}

static bool is_wifi_companion_hal_wificond_order_start_only_mode(const char *mode) {
    return streq(mode, "wifi-companion-hal-wificond-order-start-only") ||
           streq(mode, "wifi-companion-hal-wificond-lshal-wait-samsung") ||
           streq(mode, "wifi-companion-hal-wificond-lshal-wait-iwifi") ||
           streq(mode, "wifi-companion-dual-hal-wificond-lshal-wait-iwifi") ||
           streq(mode, "wifi-companion-dual-hal-wificond-iwifi-start") ||
           streq(mode, "wifi-companion-dual-hal-wificond-lshal-then-iwifi-start");
}

static bool is_wifi_companion_hal_wificond_lshal_wait_samsung_mode(const char *mode) {
    return streq(mode, "wifi-companion-hal-wificond-lshal-wait-samsung");
}

static bool is_wifi_companion_hal_wificond_lshal_wait_iwifi_mode(const char *mode) {
    return streq(mode, "wifi-companion-hal-wificond-lshal-wait-iwifi");
}

static bool is_wifi_companion_dual_hal_wificond_lshal_wait_iwifi_mode(const char *mode) {
    return streq(mode, "wifi-companion-dual-hal-wificond-lshal-wait-iwifi");
}

static bool is_wifi_companion_dual_hal_wificond_iwifi_start_mode(const char *mode) {
    return streq(mode, "wifi-companion-dual-hal-wificond-iwifi-start");
}

static bool is_wifi_companion_dual_hal_wificond_lshal_then_iwifi_start_mode(const char *mode) {
    return streq(mode, "wifi-companion-dual-hal-wificond-lshal-then-iwifi-start");
}

static bool is_rmt_storage_start_only_mode(const char *mode) {
    return streq(mode, "rmt-storage-start-only");
}

static bool is_wifi_iwifi_start_surface_mode(const char *mode) {
    return streq(mode, "wifi-iwifi-start-surface") ||
           is_wifi_dual_hal_iwifi_start_mode(mode) ||
           is_wifi_active_session_surface_mode(mode);
}

static bool is_wifi_hal_service_query_mode(const char *mode) {
    return streq(mode, "wifi-hal-composite-lshal-list") ||
           streq(mode, "wifi-hal-composite-lshal-binderized-list") ||
           streq(mode, "wifi-hal-composite-lshal-wait-target") ||
           streq(mode, "wifi-surface-composite-lshal-wait-iwifi") ||
           streq(mode, "wifi-surface-composite-lshal-wait-samsung") ||
           streq(mode, "wifi-surface-composite-lshal-wait-samsung-ptrace") ||
           streq(mode, "wifi-hal-composite-lshal-status-list") ||
           streq(mode, "wifi-hal-composite-lshal-binderized-status-list") ||
           streq(mode, "wifi-dual-hal-lshal-wait-iwifi");
}

static bool is_wifi_hal_lshal_wait_target_mode(const char *mode) {
    return streq(mode, "wifi-hal-composite-lshal-wait-target") ||
           streq(mode, "wifi-surface-composite-lshal-wait-iwifi") ||
           streq(mode, "wifi-surface-composite-lshal-wait-samsung") ||
           streq(mode, "wifi-surface-composite-lshal-wait-samsung-ptrace") ||
           streq(mode, "wifi-dual-hal-lshal-wait-iwifi");
}

static bool is_wifi_hal_composite_ptrace_mode(const char *mode) {
    return streq(mode, "wifi-surface-composite-lshal-wait-samsung-ptrace");
}

static bool is_wifi_companion_ptrace_capture(const struct config *cfg) {
    return is_wifi_companion_any_start_only_mode(cfg->mode) &&
           streq(cfg->capture_mode, "ptrace-lite");
}

static bool is_wifi_hal_lshal_wait_iwifi_mode(const char *mode) {
    return streq(mode, "wifi-surface-composite-lshal-wait-iwifi") ||
           streq(mode, "wifi-dual-hal-lshal-wait-iwifi") ||
           streq(mode, "wifi-companion-hal-wificond-lshal-wait-iwifi") ||
           streq(mode, "wifi-companion-dual-hal-wificond-lshal-wait-iwifi") ||
           streq(mode, "wifi-companion-dual-hal-wificond-lshal-then-iwifi-start");
}

static bool is_lshal_readonly_query_mode(const char *mode) {
    return streq(mode, "wifi-hal-lshal-vintf-status-list");
}

static bool selinux_context_allowed(const char *context) {
    return streq(context, "u:r:init:s0") ||
           streq(context, "u:r:hal_wifi_default:s0") ||
           streq(context, "u:r:hwservicemanager:s0") ||
           streq(context, "u:r:servicemanager:s0") ||
           streq(context, "u:r:vendor_wcnss_service:s0") ||
           streq(context, "u:r:vendor_qrtr:s0") ||
           streq(context, "u:r:vendor_rmt_storage:s0") ||
           streq(context, "u:r:vendor_rfs_access:s0") ||
           streq(context, "u:r:vendor_pd_mapper:s0");
}

static const char *const A90_WIFI_HAL_WAIT_TARGETS[A90_WIFI_HAL_WAIT_TARGET_COUNT] = {
    "vendor.samsung.hardware.wifi@2.0::ISehWifi/default",
    "vendor.samsung.hardware.wifi@2.1::ISehWifi/default",
    "vendor.samsung.hardware.wifi@2.2::ISehWifi/default",
};

static const char *const A90_IWIFI_WAIT_TARGETS[] = {
    "android.hardware.wifi@1.0::IWifi/default",
};

static bool parse_int_range(const char *value, int min_value, int max_value, int *out) {
    char *end = NULL;
    long parsed;

    if (value == NULL || value[0] == '\0') {
        return false;
    }
    errno = 0;
    parsed = strtol(value, &end, 10);
    if (errno != 0 || end == value || *end != '\0') {
        return false;
    }
    if (parsed < min_value || parsed > max_value) {
        return false;
    }
    *out = (int)parsed;
    return true;
}

static bool path_has_prefix_component(const char *path, const char *prefix) {
    size_t prefix_len;

    if (path == NULL || prefix == NULL) {
        return false;
    }
    prefix_len = strlen(prefix);
    return strncmp(path, prefix, prefix_len) == 0 &&
           (path[prefix_len] == '\0' || path[prefix_len] == '/');
}

static bool property_root_allowed(const char *path) {
    const char *suffix = "/dev/__properties__";
    size_t path_len;
    size_t suffix_len;

    if (path == NULL) {
        return false;
    }
    path_len = strlen(path);
    suffix_len = strlen(suffix);
    return path_has_prefix_component(path, "/mnt/sdext/a90/private-property-v317") &&
           strstr(path, "..") == NULL &&
           path_len >= suffix_len &&
           strcmp(path + path_len - suffix_len, suffix) == 0;
}

static bool connect_config_allowed(const char *path) {
    return path_has_prefix_component(path, "/cache/a90-wifi") &&
           strstr(path, "..") == NULL &&
           strstr(path, "\n") == NULL &&
           strstr(path, "\r") == NULL;
}

static bool connect_iface_allowed(const char *ifname) {
    if (streq(ifname, "auto")) {
        return true;
    }
    if (ifname == NULL || ifname[0] == '\0' || strlen(ifname) >= A90_NL80211_IFNAME_MAX) {
        return false;
    }
    for (size_t i = 0; ifname[i] != '\0'; i++) {
        char ch = ifname[i];

        if (!((ch >= 'A' && ch <= 'Z') ||
              (ch >= 'a' && ch <= 'z') ||
              (ch >= '0' && ch <= '9') ||
              ch == '_' ||
              ch == '-' ||
              ch == '.')) {
            return false;
        }
    }
    return true;
}

static bool ping_target_allowed(const char *target) {
    if (target == NULL || target[0] == '\0' || strlen(target) > 63U) {
        return false;
    }
    for (size_t i = 0; target[i] != '\0'; i++) {
        char ch = target[i];

        if (!((ch >= '0' && ch <= '9') || ch == '.')) {
            return false;
        }
    }
    return true;
}

static bool property_key_allowed(const char *key) {
    return streq(key, "ro.build.version.sdk") ||
           streq(key, "ro.build.version.release") ||
           streq(key, "ro.product.vendor.device") ||
           streq(key, "ro.board.platform") ||
           streq(key, "ro.product.name") ||
           streq(key, "ro.hardware") ||
           streq(key, "ro.vendor.build.version.sdk") ||
           streq(key, "ro.property_service.version") ||
           streq(key, "sys.boot_completed") ||
           streq(key, "dev.bootcomplete") ||
           streq(key, "wifi.interface") ||
           streq(key, "wlan.driver.status") ||
           streq(key, "init.svc.servicemanager") ||
           streq(key, "init.svc.hwservicemanager") ||
           streq(key, "init.svc.vendor.wifi_hal_ext") ||
           streq(key, "init.svc.vendor.wifi_hal_legacy") ||
           streq(key, "init.svc.vendor.wifi_hal") ||
           streq(key, "init.svc.wificond") ||
           streq(key, "init.svc.wpa_supplicant") ||
           streq(key, "init.svc.cnss-daemon") ||
           streq(key, "init.svc.cnss_diag") ||
           streq(key, "debug.ld.app.qrtr-ns") ||
           streq(key, "arm64.memtag.process.qrtr-ns") ||
           streq(key, "debug.ld.app.tftp_server") ||
           streq(key, "arm64.memtag.process.tftp_server") ||
           streq(key, "persist.log.tag.tftp_server") ||
           streq(key, "log.tag.tftp_server") ||
           streq(key, "debug.ld.app.pd-mapper") ||
           streq(key, "arm64.memtag.process.pd-mapper") ||
           streq(key, "persist.log.tag.pd-mapper-svc") ||
           streq(key, "log.tag.pd-mapper-svc") ||
           streq(key, "persist.vendor.pd_locater_debug") ||
           streq(key, "debug.ld.app.cnss_diag") ||
           streq(key, "arm64.memtag.process.cnss_diag") ||
           streq(key, "persist.log.tag.CNSS") ||
           streq(key, "log.tag.CNSS") ||
           streq(key, "debug.ld.app.cnss-daemon") ||
           streq(key, "arm64.memtag.process.cnss-daemon") ||
           streq(key, "persist.log.tag.cnss-daemon") ||
           streq(key, "log.tag.cnss-daemon") ||
           streq(key, "persist.vendor.cnss-daemon.debug_level") ||
           streq(key, "persist.vendor.cnss-daemon.hw_trc_disable_override") ||
           streq(key, "persist.vendor.cnss-daemon.kmsg_logging") ||
           streq(key, "debug.ld.app.rmt_storage") ||
           streq(key, "arm64.memtag.process.rmt_storage") ||
           streq(key, "persist.log.tag.vendor.rmt_storage") ||
           streq(key, "log.tag.vendor.rmt_storage") ||
           streq(key, "persist.log.semlevel") ||
           streq(key, "ro.baseband") ||
           streq(key, "init.svc.vendor.rmt_storage");
}

static int parse_args(int argc, char **argv, struct config *cfg) {
    memset(cfg, 0, sizeof(*cfg));
    cfg->timeout_sec = 10;
    cfg->linkerconfig_mode = "none";
    cfg->target_profile = "cnss-daemon";
    cfg->target = "/vendor/bin/cnss-daemon";
    cfg->env_mode = "clean";
    cfg->capture_mode = "none";
    cfg->null_device_mode = "none";
    cfg->data_wifi_mode = "none";
    cfg->vndk_apex_alias_mode = "none";
    cfg->selinux_attr_mode = "exec";
    cfg->android_selinux_context_mode = "auto";
    cfg->connect_iface = "auto";
    cfg->ping_target = "1.1.1.1";
    cfg->qrtr_readback_matrix = DEFAULT_QRTR_READBACK_MATRIX;

    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--help") == 0) {
            usage(stdout);
            exit(0);
        }
        if (strcmp(argv[i], "--allow-cnss-start-only") == 0) {
            cfg->allow_cnss_start_only = true;
            continue;
        }
        if (strcmp(argv[i], "--allow-wifi-companion-start-only") == 0) {
            cfg->allow_wifi_companion_start_only = true;
            continue;
        }
        if (strcmp(argv[i], "--allow-service-manager-start-only") == 0) {
            cfg->allow_service_manager_start_only = true;
            continue;
        }
        if (strcmp(argv[i], "--allow-wifi-hal-start-only") == 0) {
            cfg->allow_wifi_hal_start_only = true;
            continue;
        }
        if (strcmp(argv[i], "--allow-hal-service-query") == 0) {
            cfg->allow_hal_service_query = true;
            continue;
        }
        if (strcmp(argv[i], "--allow-iwifi-start-only") == 0) {
            cfg->allow_iwifi_start_only = true;
            continue;
        }
        if (strcmp(argv[i], "--allow-wlan-driver-state-on") == 0) {
            cfg->allow_wlan_driver_state_on = true;
            continue;
        }
        if (strcmp(argv[i], "--allow-cnss-userspace-readiness") == 0) {
            cfg->allow_cnss_userspace_readiness = true;
            continue;
        }
        if (strcmp(argv[i], "--allow-qrtr-ns-readback") == 0) {
            cfg->allow_qrtr_ns_readback = true;
            continue;
        }
        if (strcmp(argv[i], "--allow-servloc-domain-list-probe") == 0) {
            cfg->allow_servloc_domain_list_probe = true;
            continue;
        }
        if (strcmp(argv[i], "--allow-service-notifier-listener-probe") == 0) {
            cfg->allow_service_notifier_listener_probe = true;
            continue;
        }
        if (strcmp(argv[i], "--allow-scan-only") == 0) {
            cfg->allow_scan_only = true;
            continue;
        }
        if (strcmp(argv[i], "--allow-connect-dhcp-ping") == 0) {
            cfg->allow_connect_dhcp_ping = true;
            continue;
        }
        if (strcmp(argv[i], "--allow-policy-load-proof") == 0) {
            cfg->allow_policy_load_proof = true;
            continue;
        }
        if (strcmp(argv[i], "--allow-esoc-control-preflight") == 0) {
            cfg->allow_esoc_control_preflight = true;
            continue;
        }
        if (strcmp(argv[i], "--allow-esoc-engine-register-preflight") == 0) {
            cfg->allow_esoc_engine_register_preflight = true;
            continue;
        }
        if (strcmp(argv[i], "--allow-esoc-req-registered-subsys-hold-preflight") == 0) {
            cfg->allow_esoc_req_registered_subsys_hold_preflight = true;
            continue;
        }
        if (i + 1 >= argc) {
            fprintf(stderr, "missing value for %s\n", argv[i]);
            return 2;
        }
        if (strcmp(argv[i], "--system-root") == 0) {
            cfg->system_root = argv[++i];
        } else if (strcmp(argv[i], "--vendor-block") == 0) {
            cfg->vendor_block = argv[++i];
        } else if (strcmp(argv[i], "--vendor-fstype") == 0) {
            cfg->vendor_fstype = argv[++i];
        } else if (strcmp(argv[i], "--target") == 0) {
            cfg->target = argv[++i];
            cfg->target_profile = "custom-allowlisted";
        } else if (strcmp(argv[i], "--target-profile") == 0) {
            cfg->target_profile = argv[++i];
        } else if (strcmp(argv[i], "--linker") == 0) {
            cfg->linker = argv[++i];
        } else if (strcmp(argv[i], "--env-mode") == 0) {
            cfg->env_mode = argv[++i];
        } else if (strcmp(argv[i], "--mode") == 0) {
            cfg->mode = argv[++i];
        } else if (strcmp(argv[i], "--capture-mode") == 0) {
            cfg->capture_mode = argv[++i];
        } else if (strcmp(argv[i], "--null-device-mode") == 0) {
            cfg->null_device_mode = argv[++i];
        } else if (strcmp(argv[i], "--data-wifi-mode") == 0) {
            cfg->data_wifi_mode = argv[++i];
        } else if (strcmp(argv[i], "--vndk-apex-alias-mode") == 0) {
            cfg->vndk_apex_alias_mode = argv[++i];
        } else if (strcmp(argv[i], "--linkerconfig-mode") == 0) {
            cfg->linkerconfig_mode = argv[++i];
        } else if (strcmp(argv[i], "--linkerconfig-source") == 0) {
            cfg->linkerconfig_source = argv[++i];
        } else if (strcmp(argv[i], "--apex-libraries-source") == 0) {
            cfg->apex_libraries_source = argv[++i];
        } else if (strcmp(argv[i], "--property-root") == 0) {
            cfg->property_root = argv[++i];
        } else if (strcmp(argv[i], "--property-key") == 0) {
            cfg->property_key = argv[++i];
        } else if (strcmp(argv[i], "--selinux-context") == 0) {
            cfg->selinux_context = argv[++i];
        } else if (strcmp(argv[i], "--selinux-attr-mode") == 0) {
            cfg->selinux_attr_mode = argv[++i];
        } else if (strcmp(argv[i], "--android-selinux-context-mode") == 0) {
            cfg->android_selinux_context_mode = argv[++i];
        } else if (strcmp(argv[i], "--connect-config") == 0) {
            cfg->connect_config = argv[++i];
        } else if (strcmp(argv[i], "--connect-iface") == 0) {
            cfg->connect_iface = argv[++i];
        } else if (strcmp(argv[i], "--ping-target") == 0) {
            cfg->ping_target = argv[++i];
        } else if (strcmp(argv[i], "--qrtr-readback-matrix") == 0) {
            cfg->qrtr_readback_matrix = argv[++i];
        } else if (strcmp(argv[i], "--timeout-sec") == 0) {
            if (!parse_int_range(argv[++i], 1, 30, &cfg->timeout_sec)) {
                fprintf(stderr, "invalid --timeout-sec\n");
                return 2;
            }
        } else {
            fprintf(stderr, "unknown option: %s\n", argv[i]);
            return 2;
        }
    }

    if (streq(cfg->target_profile, "cnss-daemon")) {
        cfg->target = "/vendor/bin/cnss-daemon";
    } else if (streq(cfg->target_profile, "system-toybox")) {
        cfg->target = "/system/bin/toybox";
    } else if (streq(cfg->target_profile, "system-sh")) {
        cfg->target = "/system/bin/sh";
    } else if (streq(cfg->target_profile, "linker64-self")) {
        cfg->target = "/system/bin/linker64";
    } else if (streq(cfg->target_profile, "apex-linker64-self")) {
        cfg->target = "/apex/com.android.runtime/bin/linker64";
    } else if (streq(cfg->target_profile, "system-getprop")) {
        cfg->target = "/system/bin/getprop";
    } else if (streq(cfg->target_profile, "system-servicemanager")) {
        cfg->target = "/system/bin/servicemanager";
    } else if (streq(cfg->target_profile, "system-hwservicemanager")) {
        cfg->target = "/system/bin/hwservicemanager";
    } else if (streq(cfg->target_profile, "vendor-wifi-hal-ext")) {
        cfg->target = "/vendor/bin/hw/vendor.samsung.hardware.wifi@2.0-service";
    } else if (streq(cfg->target_profile, "vendor-wifi-hal-legacy")) {
        cfg->target = "/vendor/bin/hw/android.hardware.wifi@1.0-service";
    } else if (streq(cfg->target_profile, "custom-allowlisted")) {
        if (!(streq(cfg->target, "/vendor/bin/cnss-daemon") ||
              streq(cfg->target, "/system/bin/toybox") ||
              streq(cfg->target, "/system/bin/sh") ||
              streq(cfg->target, "/system/bin/linker64") ||
              streq(cfg->target, "/apex/com.android.runtime/bin/linker64") ||
              streq(cfg->target, "/system/bin/getprop") ||
              streq(cfg->target, "/system/bin/servicemanager") ||
              streq(cfg->target, "/system/bin/hwservicemanager") ||
              streq(cfg->target, "/vendor/bin/hw/vendor.samsung.hardware.wifi@2.0-service") ||
              streq(cfg->target, "/vendor/bin/hw/android.hardware.wifi@1.0-service"))) {
            fprintf(stderr, "--target must match a v235 allowlisted profile path\n");
            return 2;
        }
    } else {
        fprintf(stderr, "unknown --target-profile\n");
        return 2;
    }

    if ((is_wifi_hal_service_query_mode(cfg->mode) ||
         is_wifi_surface_composite_mode(cfg->mode) ||
         is_rmt_storage_start_only_mode(cfg->mode) ||
         is_subsys_hold_open_proof_mode(cfg->mode) ||
         is_wifi_companion_any_start_only_mode(cfg->mode) ||
         is_wifi_companion_hal_order_start_only_mode(cfg->mode)) &&
        streq(cfg->data_wifi_mode, "none")) {
        cfg->data_wifi_mode = "private-empty";
    }
    if (is_rmt_storage_start_only_mode(cfg->mode)) {
        cfg->target = "/vendor/bin/rmt_storage";
        cfg->target_profile = "vendor-rmt-storage";
    }
    if (is_wifi_companion_hal_order_start_only_mode(cfg->mode) &&
        streq(cfg->target_profile, "cnss-daemon")) {
        cfg->target = "/vendor/bin/hw/vendor.samsung.hardware.wifi@2.0-service";
        cfg->target_profile = "vendor-wifi-hal-ext";
    }
    if (is_wifi_companion_hal_order_start_only_mode(cfg->mode)) {
        if (streq(cfg->null_device_mode, "none")) {
            cfg->null_device_mode = "dev-null";
        }
        if (streq(cfg->vndk_apex_alias_mode, "none")) {
            cfg->vndk_apex_alias_mode = "v30-to-system-ext-v30";
        }
        if (streq(cfg->linkerconfig_mode, "none")) {
            cfg->linkerconfig_mode = "copy-real";
            cfg->linkerconfig_source = "/cache/bin/a90_real_ld.config.txt";
            cfg->apex_libraries_source = "/cache/bin/a90_real_apex.libraries.config.txt";
        }
        if (streq(cfg->android_selinux_context_mode, "auto")) {
            cfg->android_selinux_context_mode = "service-defaults";
        }
    }
    if (is_wifi_companion_service74_gated_android_userspace_cnss_retry_start_only_mode(cfg->mode)) {
        if (streq(cfg->null_device_mode, "none")) {
            cfg->null_device_mode = "dev-null";
        }
        if (streq(cfg->vndk_apex_alias_mode, "none")) {
            cfg->vndk_apex_alias_mode = "v30-to-system-ext-v30";
        }
        if (streq(cfg->linkerconfig_mode, "none")) {
            cfg->linkerconfig_mode = "copy-real";
            cfg->linkerconfig_source = "/cache/bin/a90_real_ld.config.txt";
            cfg->apex_libraries_source = "/cache/bin/a90_real_apex.libraries.config.txt";
        }
        if (streq(cfg->android_selinux_context_mode, "auto")) {
            cfg->android_selinux_context_mode = "service-defaults";
        }
    }
    if (is_wifi_hal_composite_ptrace_mode(cfg->mode) &&
        streq(cfg->capture_mode, "none")) {
        cfg->capture_mode = "ptrace-lite";
    }

    if (!streq(cfg->system_root, "/mnt/system/system") ||
        !streq(cfg->vendor_block, "/dev/block/sda29") ||
        !streq(cfg->vendor_fstype, "ext4") ||
        !(streq(cfg->mode, "linker-list") ||
          streq(cfg->mode, "identity-probe") ||
          streq(cfg->mode, "sepolicy-inventory") ||
          streq(cfg->mode, "sepolicy-compile-proof") ||
          streq(cfg->mode, "sepolicy-load-proof") ||
          streq(cfg->mode, "selinux-domain-proof") ||
          streq(cfg->mode, "cnss-start-only") ||
          is_cnss_userspace_readiness_mode(cfg->mode) ||
          is_rmt_storage_start_only_mode(cfg->mode) ||
          is_subsys_hold_open_proof_mode(cfg->mode) ||
          is_wifi_companion_esoc_control_preflight_mode(cfg->mode) ||
          is_wifi_companion_esoc_engine_register_preflight_mode(cfg->mode) ||
          is_wifi_companion_esoc_req_registered_subsys_hold_preflight_mode(cfg->mode) ||
          is_wifi_companion_any_start_only_mode(cfg->mode) ||
          is_wifi_companion_hal_order_start_only_mode(cfg->mode) ||
          streq(cfg->mode, "property-lookup") ||
          streq(cfg->mode, "private-selinux-proof") ||
          streq(cfg->mode, "service-manager-start-only") ||
          is_wifi_connect_tool_surface_mode(cfg->mode) ||
          is_service_notifier_listener_only_mode(cfg->mode) ||
          is_lshal_readonly_query_mode(cfg->mode) ||
          is_wifi_hal_composite_mode(cfg->mode)) ||
        !(streq(cfg->capture_mode, "none") ||
          streq(cfg->capture_mode, "ptrace-lite")) ||
        !(streq(cfg->null_device_mode, "none") ||
          streq(cfg->null_device_mode, "dev-null") ||
          streq(cfg->null_device_mode, "dev-null-selinux")) ||
        !(streq(cfg->data_wifi_mode, "none") ||
          streq(cfg->data_wifi_mode, "private-empty")) ||
        !(streq(cfg->vndk_apex_alias_mode, "none") ||
          streq(cfg->vndk_apex_alias_mode, "v30-to-current") ||
          streq(cfg->vndk_apex_alias_mode, "v30-to-system-ext-v30")) ||
        !(streq(cfg->env_mode, "clean") ||
          streq(cfg->env_mode, "ld-debug-1") ||
          streq(cfg->env_mode, "ld-debug-2") ||
          streq(cfg->env_mode, "auxv")) ||
        !(streq(cfg->selinux_attr_mode, "current") ||
          streq(cfg->selinux_attr_mode, "exec") ||
          streq(cfg->selinux_attr_mode, "both")) ||
        !(streq(cfg->android_selinux_context_mode, "auto") ||
          streq(cfg->android_selinux_context_mode, "none") ||
          streq(cfg->android_selinux_context_mode, "service-defaults")) ||
        !(streq(cfg->linkerconfig_mode, "none") ||
          streq(cfg->linkerconfig_mode, "copy-real") ||
          streq(cfg->linkerconfig_mode, "minimal-vendor"))) {
        fprintf(stderr, "arguments do not match v235 allowlist\n");
        return 2;
    }
    if (streq(cfg->mode, "linker-list") &&
        !(streq(cfg->linker, "/system/bin/linker64") ||
          streq(cfg->linker, "/apex/com.android.runtime/bin/linker64"))) {
        fprintf(stderr, "--linker is required for linker-list mode\n");
        return 2;
    }
    if (streq(cfg->mode, "identity-probe") && cfg->linker != NULL) {
        fprintf(stderr, "--linker is not used by identity-probe mode\n");
        return 2;
    }
    if (streq(cfg->mode, "identity-probe") && !streq(cfg->capture_mode, "none")) {
        fprintf(stderr, "--capture-mode must be none for identity-probe mode\n");
        return 2;
    }
    if (streq(cfg->mode, "sepolicy-inventory")) {
        if (cfg->linker != NULL) {
            fprintf(stderr, "--linker is not used by sepolicy-inventory mode\n");
            return 2;
        }
        if (!streq(cfg->capture_mode, "none")) {
            fprintf(stderr, "--capture-mode must be none for sepolicy-inventory mode\n");
            return 2;
        }
        if (!streq(cfg->target, "/system/bin/toybox")) {
            fprintf(stderr, "sepolicy-inventory target-profile must be system-toybox\n");
            return 2;
        }
        if (cfg->allow_cnss_start_only ||
            cfg->allow_wifi_companion_start_only ||
            cfg->allow_service_manager_start_only ||
            cfg->allow_wifi_hal_start_only ||
            cfg->allow_hal_service_query ||
            cfg->allow_iwifi_start_only ||
            cfg->allow_wlan_driver_state_on ||
            cfg->allow_cnss_userspace_readiness ||
            cfg->allow_qrtr_ns_readback ||
            cfg->allow_servloc_domain_list_probe ||
            cfg->allow_service_notifier_listener_probe ||
            cfg->allow_policy_load_proof) {
            fprintf(stderr, "sepolicy-inventory does not accept daemon/HAL allow flags\n");
            return 2;
        }
    }
    if (streq(cfg->mode, "sepolicy-compile-proof")) {
        if (cfg->linker != NULL) {
            fprintf(stderr, "--linker is not used by sepolicy-compile-proof mode\n");
            return 2;
        }
        if (!streq(cfg->capture_mode, "none")) {
            fprintf(stderr, "--capture-mode must be none for sepolicy-compile-proof mode\n");
            return 2;
        }
        if (!streq(cfg->target, "/system/bin/toybox")) {
            fprintf(stderr, "sepolicy-compile-proof target-profile must be system-toybox\n");
            return 2;
        }
        if (cfg->allow_cnss_start_only ||
            cfg->allow_wifi_companion_start_only ||
            cfg->allow_service_manager_start_only ||
            cfg->allow_wifi_hal_start_only ||
            cfg->allow_hal_service_query ||
            cfg->allow_iwifi_start_only ||
            cfg->allow_wlan_driver_state_on ||
            cfg->allow_cnss_userspace_readiness ||
            cfg->allow_policy_load_proof) {
            fprintf(stderr, "sepolicy-compile-proof does not accept daemon/HAL allow flags\n");
            return 2;
        }
    }
    if (streq(cfg->mode, "sepolicy-load-proof")) {
        if (cfg->linker != NULL) {
            fprintf(stderr, "--linker is not used by sepolicy-load-proof mode\n");
            return 2;
        }
        if (!streq(cfg->capture_mode, "none")) {
            fprintf(stderr, "--capture-mode must be none for sepolicy-load-proof mode\n");
            return 2;
        }
        if (!streq(cfg->target, "/system/bin/toybox")) {
            fprintf(stderr, "sepolicy-load-proof target-profile must be system-toybox\n");
            return 2;
        }
        if (!cfg->allow_policy_load_proof) {
            fprintf(stderr, "sepolicy-load-proof requires --allow-policy-load-proof\n");
            return 2;
        }
        if (cfg->allow_cnss_start_only ||
            cfg->allow_wifi_companion_start_only ||
            cfg->allow_service_manager_start_only ||
            cfg->allow_wifi_hal_start_only ||
            cfg->allow_hal_service_query ||
            cfg->allow_iwifi_start_only ||
            cfg->allow_cnss_userspace_readiness) {
            fprintf(stderr, "sepolicy-load-proof does not accept daemon/HAL allow flags\n");
            return 2;
        }
    } else if (cfg->allow_policy_load_proof) {
        fprintf(stderr, "--allow-policy-load-proof is only valid with sepolicy-load-proof mode\n");
        return 2;
    }
    if (cfg->allow_esoc_control_preflight &&
        !is_wifi_companion_esoc_control_preflight_mode(cfg->mode)) {
        fprintf(stderr, "--allow-esoc-control-preflight is only valid with wifi-companion-esoc-control-preflight mode\n");
        return 2;
    }
    if (cfg->allow_esoc_engine_register_preflight &&
        !is_wifi_companion_esoc_engine_register_preflight_mode(cfg->mode)) {
        fprintf(stderr, "--allow-esoc-engine-register-preflight is only valid with wifi-companion-esoc-engine-register-preflight mode\n");
        return 2;
    }
    if (cfg->allow_esoc_req_registered_subsys_hold_preflight &&
        !is_wifi_companion_esoc_req_registered_subsys_hold_preflight_mode(cfg->mode)) {
        fprintf(stderr, "--allow-esoc-req-registered-subsys-hold-preflight is only valid with wifi-companion-esoc-req-registered-subsys-hold-preflight mode\n");
        return 2;
    }
    if (is_wifi_companion_esoc_engine_register_preflight_mode(cfg->mode)) {
        if (cfg->linker != NULL) {
            fprintf(stderr, "--linker is not used by wifi-companion-esoc-engine-register-preflight mode\n");
            return 2;
        }
        if (!streq(cfg->capture_mode, "none")) {
            fprintf(stderr, "--capture-mode must be none for wifi-companion-esoc-engine-register-preflight mode\n");
            return 2;
        }
        if (cfg->allow_cnss_start_only ||
            cfg->allow_wifi_companion_start_only ||
            cfg->allow_service_manager_start_only ||
            cfg->allow_wifi_hal_start_only ||
            cfg->allow_hal_service_query ||
            cfg->allow_iwifi_start_only ||
            cfg->allow_wlan_driver_state_on ||
            cfg->allow_cnss_userspace_readiness ||
            cfg->allow_qrtr_ns_readback ||
            cfg->allow_servloc_domain_list_probe ||
            cfg->allow_service_notifier_listener_probe ||
            cfg->allow_scan_only ||
            cfg->allow_connect_dhcp_ping ||
            cfg->allow_policy_load_proof ||
            cfg->allow_esoc_control_preflight ||
            cfg->allow_esoc_req_registered_subsys_hold_preflight) {
            fprintf(stderr, "wifi-companion-esoc-engine-register-preflight does not accept actor/HAL/scan/connect or other proof allow flags\n");
            return 2;
        }
    }
    if (is_wifi_companion_esoc_req_registered_subsys_hold_preflight_mode(cfg->mode)) {
        if (cfg->linker != NULL) {
            fprintf(stderr, "--linker is not used by wifi-companion-esoc-req-registered-subsys-hold-preflight mode\n");
            return 2;
        }
        if (!streq(cfg->capture_mode, "none")) {
            fprintf(stderr, "--capture-mode must be none for wifi-companion-esoc-req-registered-subsys-hold-preflight mode\n");
            return 2;
        }
        if (cfg->allow_cnss_start_only ||
            cfg->allow_wifi_companion_start_only ||
            cfg->allow_service_manager_start_only ||
            cfg->allow_wifi_hal_start_only ||
            cfg->allow_hal_service_query ||
            cfg->allow_iwifi_start_only ||
            cfg->allow_wlan_driver_state_on ||
            cfg->allow_cnss_userspace_readiness ||
            cfg->allow_qrtr_ns_readback ||
            cfg->allow_servloc_domain_list_probe ||
            cfg->allow_service_notifier_listener_probe ||
            cfg->allow_scan_only ||
            cfg->allow_connect_dhcp_ping ||
            cfg->allow_policy_load_proof ||
            cfg->allow_esoc_control_preflight ||
            cfg->allow_esoc_engine_register_preflight) {
            fprintf(stderr, "wifi-companion-esoc-req-registered-subsys-hold-preflight does not accept actor/HAL/scan/connect or other proof allow flags\n");
            return 2;
        }
    }
    if (streq(cfg->mode, "selinux-domain-proof")) {
        if (cfg->linker != NULL) {
            fprintf(stderr, "--linker is not used by selinux-domain-proof mode\n");
            return 2;
        }
        if (!streq(cfg->capture_mode, "none")) {
            fprintf(stderr, "--capture-mode must be none for selinux-domain-proof mode\n");
            return 2;
        }
        if (cfg->selinux_context == NULL || !selinux_context_allowed(cfg->selinux_context)) {
            fprintf(stderr, "--selinux-context must match the v37 allowlist\n");
            return 2;
        }
        if (cfg->allow_cnss_start_only ||
            cfg->allow_wifi_companion_start_only ||
            cfg->allow_service_manager_start_only ||
            cfg->allow_wifi_hal_start_only ||
            cfg->allow_hal_service_query ||
            cfg->allow_iwifi_start_only ||
            cfg->allow_cnss_userspace_readiness) {
            fprintf(stderr, "selinux-domain-proof does not accept daemon/HAL allow flags\n");
            return 2;
        }
    } else if (cfg->selinux_context != NULL || !streq(cfg->selinux_attr_mode, "exec")) {
        fprintf(stderr, "--selinux-context and --selinux-attr-mode are only valid with selinux-domain-proof mode\n");
        return 2;
    }
    if (streq(cfg->android_selinux_context_mode, "service-defaults") &&
        !(streq(cfg->mode, "service-manager-start-only") ||
          is_wifi_hal_composite_mode(cfg->mode) ||
          is_cnss_userspace_readiness_mode(cfg->mode) ||
          is_rmt_storage_start_only_mode(cfg->mode) ||
          is_wifi_companion_any_start_only_mode(cfg->mode) ||
          is_wifi_companion_hal_order_start_only_mode(cfg->mode))) {
        fprintf(stderr, "--android-selinux-context-mode is only valid with service-manager, Wi-Fi HAL composite, CNSS userspace readiness, or Wi-Fi companion modes\n");
        return 2;
    }
    if (streq(cfg->mode, "cnss-start-only") && cfg->linker != NULL) {
        fprintf(stderr, "--linker is not used by cnss-start-only mode\n");
        return 2;
    }
    if (streq(cfg->mode, "cnss-start-only") && !streq(cfg->capture_mode, "none")) {
        fprintf(stderr, "--capture-mode must be none for cnss-start-only mode\n");
        return 2;
    }
    if (streq(cfg->mode, "cnss-start-only") && !streq(cfg->target, "/vendor/bin/cnss-daemon")) {
        fprintf(stderr, "cnss-start-only target is fixed to /vendor/bin/cnss-daemon\n");
        return 2;
    }
    if (is_cnss_userspace_readiness_mode(cfg->mode)) {
        if (cfg->linker != NULL) {
            fprintf(stderr, "--linker is not used by cnss-userspace-readiness mode\n");
            return 2;
        }
        if (!streq(cfg->capture_mode, "none")) {
            fprintf(stderr, "--capture-mode must be none for cnss-userspace-readiness mode\n");
            return 2;
        }
        if (!cfg->allow_cnss_start_only || !cfg->allow_cnss_userspace_readiness) {
            fprintf(stderr, "cnss-userspace-readiness requires --allow-cnss-start-only and --allow-cnss-userspace-readiness\n");
            return 2;
        }
        if (cfg->allow_service_manager_start_only ||
            cfg->allow_wifi_companion_start_only ||
            cfg->allow_wifi_hal_start_only ||
            cfg->allow_hal_service_query ||
            cfg->allow_iwifi_start_only ||
            cfg->allow_wlan_driver_state_on ||
            cfg->allow_scan_only ||
            cfg->allow_connect_dhcp_ping) {
            fprintf(stderr, "cnss-userspace-readiness does not accept HAL/scan/connect allow flags\n");
            return 2;
        }
    } else if (cfg->allow_cnss_userspace_readiness) {
        fprintf(stderr, "--allow-cnss-userspace-readiness is only valid with cnss-userspace-readiness mode\n");
        return 2;
    }
    if (is_wifi_companion_any_start_only_mode(cfg->mode)) {
        const bool post_sysmon_observer =
            is_wifi_companion_post_sysmon_observer_start_only_mode(cfg->mode) ||
            is_wifi_companion_android_order_post_sysmon_observer_start_only_mode(cfg->mode);
        const bool peripheral_manager_node_parity =
            is_wifi_companion_peripheral_manager_node_materialization_mode(cfg->mode);
        const bool with_service_manager =
            is_wifi_companion_with_service_manager_start_only_mode(cfg->mode);
        const bool service74_gated_android_userspace_retry =
            is_wifi_companion_service74_gated_android_userspace_cnss_retry_start_only_mode(cfg->mode) ||
            is_wifi_companion_service74_gated_android_userspace_cnss_retry_registry_snapshot_start_only_mode(cfg->mode);

        if (cfg->linker != NULL) {
            fprintf(stderr, "--linker is not used by Wi-Fi companion modes\n");
            return 2;
        }
        if (!(streq(cfg->capture_mode, "none") ||
              streq(cfg->capture_mode, "ptrace-lite"))) {
            fprintf(stderr, "--capture-mode must be none or ptrace-lite for Wi-Fi companion modes\n");
            return 2;
        }
        if (!cfg->allow_wifi_companion_start_only ||
            (!post_sysmon_observer &&
             !peripheral_manager_node_parity &&
             !cfg->allow_cnss_start_only)) {
            fprintf(stderr, "Wi-Fi companion modes require --allow-wifi-companion-start-only%s\n",
                    (post_sysmon_observer || peripheral_manager_node_parity) ? "" : " and --allow-cnss-start-only");
            return 2;
        }
        if (peripheral_manager_node_parity && cfg->allow_cnss_start_only) {
            fprintf(stderr, "wifi-companion-peripheral-manager node-only modes must not use --allow-cnss-start-only\n");
            return 2;
        }
        if (post_sysmon_observer && cfg->allow_cnss_start_only) {
            fprintf(stderr, "Wi-Fi post-sysmon observer modes must not use --allow-cnss-start-only\n");
            return 2;
        }
        if (with_service_manager && !cfg->allow_service_manager_start_only) {
            fprintf(stderr, "wifi-companion-service-manager-start-only requires --allow-service-manager-start-only\n");
            return 2;
        }
        if (!with_service_manager && cfg->allow_service_manager_start_only) {
            fprintf(stderr, "wifi-companion-start-only does not accept --allow-service-manager-start-only\n");
            return 2;
        }
        if (service74_gated_android_userspace_retry && !cfg->allow_wifi_hal_start_only) {
            fprintf(stderr, "wifi-companion-service74-gated-android-userspace-cnss-retry-start-only requires --allow-wifi-hal-start-only\n");
            return 2;
        }
        if ((!service74_gated_android_userspace_retry && cfg->allow_wifi_hal_start_only) ||
            cfg->allow_hal_service_query ||
            cfg->allow_iwifi_start_only ||
            cfg->allow_wlan_driver_state_on ||
            cfg->allow_scan_only ||
            cfg->allow_connect_dhcp_ping ||
            cfg->allow_cnss_userspace_readiness) {
            fprintf(stderr, "Wi-Fi companion modes do not accept HAL/scan/connect allow flags\n");
            return 2;
        }
    } else if (is_wifi_companion_hal_order_start_only_mode(cfg->mode)) {
        const bool registration_query_mode =
            is_wifi_companion_hal_wificond_lshal_wait_samsung_mode(cfg->mode) ||
            is_wifi_companion_hal_wificond_lshal_wait_iwifi_mode(cfg->mode) ||
            is_wifi_companion_dual_hal_wificond_lshal_wait_iwifi_mode(cfg->mode) ||
            is_wifi_companion_dual_hal_wificond_lshal_then_iwifi_start_mode(cfg->mode);
        const bool iwifi_start_mode =
            is_wifi_companion_dual_hal_wificond_iwifi_start_mode(cfg->mode) ||
            is_wifi_companion_dual_hal_wificond_lshal_then_iwifi_start_mode(cfg->mode);

        if (cfg->linker != NULL) {
            fprintf(stderr, "--linker is not used by Wi-Fi companion HAL order mode\n");
            return 2;
        }
        if (!streq(cfg->capture_mode, "none")) {
            fprintf(stderr, "--capture-mode must be none for Wi-Fi companion HAL order mode\n");
            return 2;
        }
        if (!cfg->allow_wifi_companion_start_only ||
            !cfg->allow_cnss_start_only ||
            !cfg->allow_service_manager_start_only ||
            !cfg->allow_wifi_hal_start_only) {
            fprintf(stderr, "wifi-companion-hal-order-start-only requires companion, CNSS, service-manager, and Wi-Fi HAL allow flags\n");
            return 2;
        }
        if (registration_query_mode && !cfg->allow_hal_service_query) {
            fprintf(stderr, "wifi-companion-hal-wificond-lshal-wait modes require --allow-hal-service-query\n");
            return 2;
        }
        if (iwifi_start_mode && !cfg->allow_iwifi_start_only) {
            fprintf(stderr, "wifi-companion-dual-hal-wificond-iwifi-start requires --allow-iwifi-start-only\n");
            return 2;
        }
        if ((!registration_query_mode && cfg->allow_hal_service_query) ||
            (!iwifi_start_mode && cfg->allow_iwifi_start_only) ||
            cfg->allow_scan_only ||
            cfg->allow_connect_dhcp_ping ||
            cfg->allow_cnss_userspace_readiness) {
            fprintf(stderr, "Wi-Fi companion HAL order mode does not accept query/IWifi/scan/connect allow flags\n");
            return 2;
        }
        if (cfg->allow_wlan_driver_state_on &&
            !is_wifi_companion_dual_hal_wificond_lshal_then_iwifi_start_mode(cfg->mode)) {
            fprintf(stderr, "--allow-wlan-driver-state-on is only valid with companion dual-HAL lshal-then-IWifi.start mode\n");
            return 2;
        }
        if (!(streq(cfg->target, "/vendor/bin/hw/vendor.samsung.hardware.wifi@2.0-service") ||
              streq(cfg->target, "/vendor/bin/hw/android.hardware.wifi@1.0-service"))) {
            fprintf(stderr, "wifi-companion-hal-order-start-only target is fixed to Wi-Fi HAL binaries\n");
            return 2;
        }
    } else if (cfg->allow_wifi_companion_start_only) {
        if (!is_rmt_storage_start_only_mode(cfg->mode) &&
            !is_subsys_hold_open_proof_mode(cfg->mode)) {
            fprintf(stderr, "--allow-wifi-companion-start-only is only valid with Wi-Fi companion, companion HAL order, or rmt-storage-start-only modes\n");
            return 2;
        }
    }
    if (is_rmt_storage_start_only_mode(cfg->mode)) {
        if (cfg->linker != NULL) {
            fprintf(stderr, "--linker is not used by rmt-storage-start-only mode\n");
            return 2;
        }
        if (!streq(cfg->capture_mode, "none")) {
            fprintf(stderr, "--capture-mode must be none for rmt-storage-start-only mode\n");
            return 2;
        }
        if (!cfg->allow_wifi_companion_start_only) {
            fprintf(stderr, "rmt-storage-start-only requires --allow-wifi-companion-start-only\n");
            return 2;
        }
        if (cfg->allow_cnss_start_only ||
            cfg->allow_service_manager_start_only ||
            cfg->allow_wifi_hal_start_only ||
            cfg->allow_hal_service_query ||
            cfg->allow_iwifi_start_only ||
            cfg->allow_wlan_driver_state_on ||
            cfg->allow_scan_only ||
            cfg->allow_connect_dhcp_ping ||
            cfg->allow_cnss_userspace_readiness) {
            fprintf(stderr, "rmt-storage-start-only does not accept CNSS/service-manager/HAL/scan/connect allow flags\n");
            return 2;
        }
    } else if (cfg->allow_wifi_companion_start_only &&
               !is_wifi_companion_any_start_only_mode(cfg->mode) &&
               !is_wifi_companion_hal_order_start_only_mode(cfg->mode) &&
               !is_subsys_hold_open_proof_mode(cfg->mode)) {
        fprintf(stderr, "--allow-wifi-companion-start-only is only valid with Wi-Fi companion, companion HAL order, or rmt-storage-start-only modes\n");
        return 2;
    }
    if (cfg->allow_qrtr_ns_readback &&
        !is_wifi_companion_any_start_only_mode(cfg->mode) &&
        !is_wifi_companion_hal_order_start_only_mode(cfg->mode)) {
        fprintf(stderr, "--allow-qrtr-ns-readback is only valid with Wi-Fi companion modes\n");
        return 2;
    }
    if (cfg->allow_servloc_domain_list_probe &&
        !is_wifi_companion_any_start_only_mode(cfg->mode)) {
        fprintf(stderr, "--allow-servloc-domain-list-probe is only valid with Wi-Fi companion start-only modes\n");
        return 2;
    }
    if (cfg->allow_service_notifier_listener_probe &&
        !is_wifi_companion_any_start_only_mode(cfg->mode) &&
        !is_service_notifier_listener_only_mode(cfg->mode)) {
        fprintf(stderr, "--allow-service-notifier-listener-probe is only valid with Wi-Fi companion start-only or service-notifier-listener-only modes\n");
        return 2;
    }
    if (is_service_notifier_listener_only_mode(cfg->mode)) {
        if (cfg->linker != NULL) {
            fprintf(stderr, "--linker is not used by service-notifier-listener-only mode\n");
            return 2;
        }
        if (!streq(cfg->capture_mode, "none")) {
            fprintf(stderr, "--capture-mode must be none for service-notifier-listener-only mode\n");
            return 2;
        }
        if (!cfg->allow_service_notifier_listener_probe) {
            fprintf(stderr, "service-notifier-listener-only requires --allow-service-notifier-listener-probe\n");
            return 2;
        }
        if (cfg->allow_cnss_start_only ||
            cfg->allow_wifi_companion_start_only ||
            cfg->allow_service_manager_start_only ||
            cfg->allow_wifi_hal_start_only ||
            cfg->allow_hal_service_query ||
            cfg->allow_iwifi_start_only ||
            cfg->allow_wlan_driver_state_on ||
            cfg->allow_scan_only ||
            cfg->allow_connect_dhcp_ping ||
            cfg->allow_cnss_userspace_readiness ||
            cfg->allow_qrtr_ns_readback ||
            cfg->allow_servloc_domain_list_probe ||
            cfg->allow_policy_load_proof) {
            fprintf(stderr, "service-notifier-listener-only accepts only --allow-service-notifier-listener-probe\n");
            return 2;
        }
    }
    if (streq(cfg->mode, "service-manager-start-only")) {
        if (cfg->linker != NULL) {
            fprintf(stderr, "--linker is not used by service-manager-start-only mode\n");
            return 2;
        }
        if (!(streq(cfg->capture_mode, "none") ||
              streq(cfg->capture_mode, "ptrace-lite"))) {
            fprintf(stderr, "--capture-mode must be none or ptrace-lite for service-manager-start-only mode\n");
            return 2;
        }
        if (!(streq(cfg->target, "/system/bin/servicemanager") ||
              streq(cfg->target, "/system/bin/hwservicemanager"))) {
            fprintf(stderr, "service-manager-start-only target is fixed to system service-manager binaries\n");
            return 2;
        }
        if (streq(cfg->capture_mode, "ptrace-lite") &&
            !cfg->allow_service_manager_start_only) {
            fprintf(stderr, "--capture-mode ptrace-lite requires --allow-service-manager-start-only\n");
            return 2;
        }
    }
    if (is_wifi_hal_composite_mode(cfg->mode)) {
        if (cfg->linker != NULL) {
            fprintf(stderr, "--linker is not used by wifi-hal-composite modes\n");
            return 2;
        }
        if (!(streq(cfg->capture_mode, "none") ||
              (is_wifi_hal_composite_ptrace_mode(cfg->mode) &&
               streq(cfg->capture_mode, "ptrace-lite")))) {
            fprintf(stderr, "--capture-mode ptrace-lite is only valid for wifi-surface-composite-lshal-wait-samsung-ptrace\n");
            return 2;
        }
        if (!(streq(cfg->target, "/vendor/bin/hw/vendor.samsung.hardware.wifi@2.0-service") ||
              streq(cfg->target, "/vendor/bin/hw/android.hardware.wifi@1.0-service"))) {
            fprintf(stderr, "wifi-hal-composite target is fixed to Wi-Fi HAL binaries\n");
            return 2;
        }
        if (cfg->allow_wifi_hal_start_only && !cfg->allow_service_manager_start_only) {
            fprintf(stderr, "--allow-wifi-hal-start-only requires --allow-service-manager-start-only\n");
            return 2;
        }
        if (cfg->allow_hal_service_query &&
            (!cfg->allow_service_manager_start_only || !cfg->allow_wifi_hal_start_only)) {
            fprintf(stderr, "--allow-hal-service-query requires service-manager and Wi-Fi HAL allow flags\n");
            return 2;
        }
        if (cfg->allow_iwifi_start_only &&
            (!cfg->allow_service_manager_start_only ||
             !cfg->allow_wifi_hal_start_only ||
             !cfg->allow_cnss_start_only)) {
            fprintf(stderr, "--allow-iwifi-start-only requires service-manager, Wi-Fi HAL, and CNSS allow flags\n");
            return 2;
        }
        if (cfg->allow_wlan_driver_state_on &&
            (!cfg->allow_service_manager_start_only ||
             !cfg->allow_wifi_hal_start_only ||
             !cfg->allow_cnss_start_only)) {
            fprintf(stderr, "--allow-wlan-driver-state-on requires service-manager, Wi-Fi HAL, and CNSS allow flags\n");
            return 2;
        }
        if (cfg->allow_scan_only &&
            (!cfg->allow_service_manager_start_only ||
             !cfg->allow_wifi_hal_start_only ||
             !cfg->allow_cnss_start_only ||
             !cfg->allow_iwifi_start_only)) {
            fprintf(stderr, "--allow-scan-only requires service-manager, Wi-Fi HAL, CNSS, and IWifi.start allow flags\n");
            return 2;
        }
        if (cfg->allow_connect_dhcp_ping &&
            (!cfg->allow_service_manager_start_only ||
             !cfg->allow_wifi_hal_start_only ||
             !cfg->allow_cnss_start_only ||
             !cfg->allow_iwifi_start_only)) {
            fprintf(stderr, "--allow-connect-dhcp-ping requires service-manager, Wi-Fi HAL, CNSS, and IWifi.start allow flags\n");
            return 2;
        }
        if (is_wifi_surface_composite_mode(cfg->mode) &&
            (!cfg->allow_service_manager_start_only ||
             !cfg->allow_wifi_hal_start_only ||
             !cfg->allow_cnss_start_only ||
             (is_wifi_iwifi_start_surface_mode(cfg->mode) && !cfg->allow_iwifi_start_only) ||
             (is_wifi_active_session_scan_only_mode(cfg->mode) && !cfg->allow_scan_only) ||
             (is_wifi_active_session_connect_ping_mode(cfg->mode) && !cfg->allow_connect_dhcp_ping))) {
            fprintf(stderr, "wifi surface modes require service-manager, Wi-Fi HAL, CNSS, and mode-specific allow flags\n");
            return 2;
        }
    }
    if (cfg->allow_iwifi_start_only &&
        !is_wifi_iwifi_start_surface_mode(cfg->mode) &&
        !is_wifi_companion_dual_hal_wificond_iwifi_start_mode(cfg->mode) &&
        !is_wifi_companion_dual_hal_wificond_lshal_then_iwifi_start_mode(cfg->mode)) {
        fprintf(stderr, "--allow-iwifi-start-only is only valid with wifi-iwifi-start-surface, wifi-dual-hal-iwifi-start-surface, active-session, or companion dual-HAL IWifi.start modes\n");
        return 2;
    }
    if (cfg->allow_wlan_driver_state_on &&
        !is_wifi_surface_composite_mode(cfg->mode) &&
        !is_wifi_companion_dual_hal_wificond_lshal_then_iwifi_start_mode(cfg->mode)) {
        fprintf(stderr, "--allow-wlan-driver-state-on is only valid with Wi-Fi surface composite or companion dual-HAL lshal-then-IWifi.start modes\n");
        return 2;
    }
    if (cfg->allow_scan_only && !is_wifi_active_session_scan_only_mode(cfg->mode)) {
        fprintf(stderr, "--allow-scan-only is only valid with wifi-active-session-scan-only mode\n");
        return 2;
    }
    if (cfg->allow_connect_dhcp_ping && !is_wifi_active_session_connect_ping_mode(cfg->mode)) {
        fprintf(stderr, "--allow-connect-dhcp-ping is only valid with wifi-active-session-connect-ping mode\n");
        return 2;
    }
    if (is_wifi_active_session_connect_ping_mode(cfg->mode)) {
        if (cfg->connect_config == NULL || !connect_config_allowed(cfg->connect_config)) {
            fprintf(stderr, "wifi-active-session-connect-ping requires --connect-config under /cache/a90-wifi\n");
            return 2;
        }
        if (!connect_iface_allowed(cfg->connect_iface)) {
            fprintf(stderr, "--connect-iface must be auto or a simple interface name\n");
            return 2;
        }
        if (!ping_target_allowed(cfg->ping_target)) {
            fprintf(stderr, "--ping-target must be an IPv4 literal\n");
            return 2;
        }
    } else if (cfg->connect_config != NULL) {
        fprintf(stderr, "--connect-config is only valid with wifi-active-session-connect-ping mode\n");
        return 2;
    }
    if (is_lshal_readonly_query_mode(cfg->mode)) {
        if (cfg->linker != NULL) {
            fprintf(stderr, "--linker is not used by lshal read-only query modes\n");
            return 2;
        }
        if (!streq(cfg->capture_mode, "none")) {
            fprintf(stderr, "--capture-mode must be none for lshal read-only query modes\n");
            return 2;
        }
        if (!streq(cfg->target, "/system/bin/toybox")) {
            fprintf(stderr, "lshal read-only query target-profile must be system-toybox\n");
            return 2;
        }
        if (cfg->allow_cnss_start_only ||
            cfg->allow_wifi_companion_start_only ||
            cfg->allow_service_manager_start_only ||
            cfg->allow_wifi_hal_start_only ||
            cfg->allow_hal_service_query ||
            cfg->allow_iwifi_start_only ||
            cfg->allow_cnss_userspace_readiness) {
            fprintf(stderr, "lshal read-only query modes do not accept daemon/HAL allow flags\n");
            return 2;
        }
    }
    if (streq(cfg->mode, "private-selinux-proof")) {
        if (cfg->linker != NULL) {
            fprintf(stderr, "--linker is not used by private-selinux-proof mode\n");
            return 2;
        }
        if (!streq(cfg->capture_mode, "none")) {
            fprintf(stderr, "--capture-mode must be none for private-selinux-proof mode\n");
            return 2;
        }
        if (!(streq(cfg->target, "/system/bin/servicemanager") ||
              streq(cfg->target, "/system/bin/hwservicemanager"))) {
            fprintf(stderr, "private-selinux-proof target is fixed to system service-manager binaries\n");
            return 2;
        }
        if (cfg->property_key != NULL) {
            fprintf(stderr, "--property-key is only valid with property-lookup mode\n");
            return 2;
        }
        if (cfg->property_root != NULL && !property_root_allowed(cfg->property_root)) {
            fprintf(stderr, "--property-root must be under /mnt/sdext/a90/private-property-v317 and point at dev/__properties__\n");
            return 2;
        }
    }
    if (streq(cfg->mode, "property-lookup")) {
        if (cfg->linker != NULL) {
            fprintf(stderr, "--linker is not used by property-lookup mode\n");
            return 2;
        }
        if (!streq(cfg->capture_mode, "none")) {
            fprintf(stderr, "--capture-mode must be none for property-lookup mode\n");
            return 2;
        }
        if (!streq(cfg->target, "/system/bin/getprop")) {
            fprintf(stderr, "property-lookup target is fixed to /system/bin/getprop\n");
            return 2;
        }
        if (!property_root_allowed(cfg->property_root)) {
            fprintf(stderr, "--property-root must be under /mnt/sdext/a90/private-property-v317 and point at dev/__properties__\n");
            return 2;
        }
        if (!property_key_allowed(cfg->property_key)) {
            fprintf(stderr, "--property-key is not in the v321 read-only allowlist\n");
            return 2;
        }
    } else if (streq(cfg->mode, "private-selinux-proof")) {
        if (cfg->property_key != NULL) {
            fprintf(stderr, "--property-key is only valid with property-lookup mode\n");
            return 2;
        }
        if (cfg->property_root != NULL && !property_root_allowed(cfg->property_root)) {
            fprintf(stderr, "--property-root must be under /mnt/sdext/a90/private-property-v317 and point at dev/__properties__\n");
            return 2;
        }
    } else if (streq(cfg->mode, "service-manager-start-only") ||
               is_lshal_readonly_query_mode(cfg->mode) ||
               is_rmt_storage_start_only_mode(cfg->mode) ||
               is_wifi_companion_any_start_only_mode(cfg->mode) ||
               is_wifi_companion_hal_order_start_only_mode(cfg->mode) ||
               is_wifi_hal_composite_mode(cfg->mode)) {
        if (cfg->property_key != NULL) {
            fprintf(stderr, "--property-key is only valid with property-lookup mode\n");
            return 2;
        }
        if (cfg->property_root != NULL && !property_root_allowed(cfg->property_root)) {
            fprintf(stderr, "--property-root must be under /mnt/sdext/a90/private-property-v317 and point at dev/__properties__\n");
            return 2;
        }
    } else if (cfg->property_root != NULL || cfg->property_key != NULL) {
        fprintf(stderr, "--property-root is only valid with property-lookup, private-selinux-proof, service-manager-start-only, rmt-storage-start-only, Wi-Fi companion, companion HAL order, or wifi-hal-composite modes; --property-key is only valid with property-lookup mode\n");
        return 2;
    }
    if (streq(cfg->linkerconfig_mode, "copy-real")) {
        if (cfg->linkerconfig_source == NULL ||
            strncmp(cfg->linkerconfig_source, "/cache/", 7) != 0 ||
            strstr(cfg->linkerconfig_source, "..") != NULL) {
            fprintf(stderr, "--linkerconfig-source must be an absolute /cache path for copy-real\n");
            return 2;
        }
        if (cfg->apex_libraries_source != NULL &&
            (strncmp(cfg->apex_libraries_source, "/cache/", 7) != 0 ||
             strstr(cfg->apex_libraries_source, "..") != NULL)) {
            fprintf(stderr, "--apex-libraries-source must be an absolute /cache path for copy-real\n");
            return 2;
        }
    } else if (cfg->linkerconfig_source != NULL || cfg->apex_libraries_source != NULL) {
        fprintf(stderr, "--linkerconfig-source and --apex-libraries-source are only valid with --linkerconfig-mode copy-real\n");
        return 2;
    }
    return 0;
}

static int append_path(char *out, size_t out_size, const char *a, const char *b) {
    int rc = snprintf(out, out_size, "%s/%s", a, b);

    if (rc < 0 || (size_t)rc >= out_size) {
        errno = ENAMETOOLONG;
        return -1;
    }
    return 0;
}

static int mkdir_one(const char *path, mode_t mode) {
    if (mkdir(path, mode) < 0 && errno != EEXIST) {
        return -1;
    }
    return 0;
}

static int mkdir_p(const char *path, mode_t mode) {
    char tmp[MAX_PATH_LEN];
    size_t len;

    len = strlen(path);
    if (len == 0 || len >= sizeof(tmp)) {
        errno = ENAMETOOLONG;
        return -1;
    }
    memcpy(tmp, path, len + 1);
    for (char *p = tmp + 1; *p != '\0'; p++) {
        if (*p == '/') {
            *p = '\0';
            if (mkdir_one(tmp, mode) < 0) {
                return -1;
            }
            *p = '/';
        }
    }
    return mkdir_one(tmp, mode);
}

static int init_paths(struct paths *paths) {
    int rc;

    rc = snprintf(paths->base, sizeof(paths->base), "/tmp/a90-v231-%ld", (long)getpid());
    if (rc < 0 || (size_t)rc >= sizeof(paths->base)) {
        errno = ENAMETOOLONG;
        return -1;
    }
    if (append_path(paths->root, sizeof(paths->root), paths->base, "root") < 0 ||
        append_path(paths->system, sizeof(paths->system), paths->root, "system") < 0 ||
        append_path(paths->vendor, sizeof(paths->vendor), paths->root, "vendor") < 0 ||
        append_path(paths->vendor_source, sizeof(paths->vendor_source), paths->base, "vendor-block-sda29") < 0 ||
        append_path(paths->vendor_firmware_mnt,
                    sizeof(paths->vendor_firmware_mnt),
                    paths->vendor,
                    "firmware_mnt") < 0 ||
        append_path(paths->vendor_firmware_modem,
                    sizeof(paths->vendor_firmware_modem),
                    paths->vendor,
                    "firmware-modem") < 0 ||
        append_path(paths->firmware_mnt_source,
                    sizeof(paths->firmware_mnt_source),
                    paths->base,
                    "firmware-block-apnhlos") < 0 ||
        append_path(paths->firmware_modem_source,
                    sizeof(paths->firmware_modem_source),
                    paths->base,
                    "firmware-block-modem") < 0 ||
        append_path(paths->dev, sizeof(paths->dev), paths->root, "dev") < 0 ||
        append_path(paths->dev_null, sizeof(paths->dev_null), paths->dev, "null") < 0 ||
        append_path(paths->dev_wlan, sizeof(paths->dev_wlan), paths->dev, "wlan") < 0 ||
        append_path(paths->dev_block, sizeof(paths->dev_block), paths->dev, "block") < 0 ||
        append_path(paths->dev_block_by_name,
                    sizeof(paths->dev_block_by_name),
                    paths->dev_block,
                    "by-name") < 0 ||
        append_path(paths->dev_block_bootdevice,
                    sizeof(paths->dev_block_bootdevice),
                    paths->dev_block,
                    "bootdevice") < 0 ||
        append_path(paths->dev_block_bootdevice_by_name,
                    sizeof(paths->dev_block_bootdevice_by_name),
                    paths->dev_block_bootdevice,
                    "by-name") < 0 ||
        append_path(paths->dev_uio0, sizeof(paths->dev_uio0), paths->dev, "uio0") < 0 ||
        append_path(paths->dev_kmsg, sizeof(paths->dev_kmsg), paths->dev, "kmsg") < 0 ||
        append_path(paths->dev_binder, sizeof(paths->dev_binder), paths->dev, "binder") < 0 ||
        append_path(paths->dev_hwbinder, sizeof(paths->dev_hwbinder), paths->dev, "hwbinder") < 0 ||
        append_path(paths->dev_vndbinder, sizeof(paths->dev_vndbinder), paths->dev, "vndbinder") < 0 ||
        append_path(paths->dev_properties,
                    sizeof(paths->dev_properties),
                    paths->dev,
                    "__properties__") < 0 ||
        append_path(paths->dev_socket, sizeof(paths->dev_socket), paths->dev, "socket") < 0 ||
        append_path(paths->property_service_socket,
                    sizeof(paths->property_service_socket),
                    paths->dev_socket,
                    "property_service") < 0 ||
        append_path(paths->sys, sizeof(paths->sys), paths->root, "sys") < 0 ||
        append_path(paths->sys_bus, sizeof(paths->sys_bus), paths->sys, "bus") < 0 ||
        append_path(paths->sys_bus_esoc, sizeof(paths->sys_bus_esoc), paths->sys_bus, "esoc") < 0 ||
        append_path(paths->sys_bus_msm_subsys,
                    sizeof(paths->sys_bus_msm_subsys),
                    paths->sys_bus,
                    "msm_subsys") < 0 ||
        append_path(paths->sys_class, sizeof(paths->sys_class), paths->sys, "class") < 0 ||
        append_path(paths->sys_class_uio, sizeof(paths->sys_class_uio), paths->sys_class, "uio") < 0 ||
        append_path(paths->sys_devices, sizeof(paths->sys_devices), paths->sys, "devices") < 0 ||
        append_path(paths->sys_devices_platform,
                    sizeof(paths->sys_devices_platform),
                    paths->sys_devices,
                    "platform") < 0 ||
        append_path(paths->sys_devices_platform_soc,
                    sizeof(paths->sys_devices_platform_soc),
                    paths->sys_devices_platform,
                    "soc") < 0 ||
        append_path(paths->sys_devices_platform_soc_mdm3,
                    sizeof(paths->sys_devices_platform_soc_mdm3),
                    paths->sys_devices_platform_soc,
                    "soc:qcom,mdm3") < 0 ||
        append_path(paths->sys_devices_platform_soc_mss,
                    sizeof(paths->sys_devices_platform_soc_mss),
                    paths->sys_devices_platform_soc,
                    "4080000.qcom,mss") < 0 ||
        append_path(paths->sys_power, sizeof(paths->sys_power), paths->sys, "power") < 0 ||
        append_path(paths->sys_power_wake_lock,
                    sizeof(paths->sys_power_wake_lock),
                    paths->sys_power,
                    "wake_lock") < 0 ||
        append_path(paths->sys_power_wake_unlock,
                    sizeof(paths->sys_power_wake_unlock),
                    paths->sys_power,
                    "wake_unlock") < 0 ||
        append_path(paths->sys_fs, sizeof(paths->sys_fs), paths->sys, "fs") < 0 ||
        append_path(paths->sys_fs_selinux, sizeof(paths->sys_fs_selinux), paths->sys_fs, "selinux") < 0 ||
        append_path(paths->sys_fs_selinux_null,
                    sizeof(paths->sys_fs_selinux_null),
                    paths->sys_fs_selinux,
                    "null") < 0 ||
        append_path(paths->sys_fs_selinux_status,
                    sizeof(paths->sys_fs_selinux_status),
                    paths->sys_fs_selinux,
                    "status") < 0 ||
        append_path(paths->sys_fs_selinux_enforce,
                    sizeof(paths->sys_fs_selinux_enforce),
                    paths->sys_fs_selinux,
                    "enforce") < 0 ||
        append_path(paths->sys_fs_selinux_load,
                    sizeof(paths->sys_fs_selinux_load),
                    paths->sys_fs_selinux,
                    "load") < 0 ||
        append_path(paths->data, sizeof(paths->data), paths->root, "data") < 0 ||
        append_path(paths->data_vendor, sizeof(paths->data_vendor), paths->data, "vendor") < 0 ||
        append_path(paths->data_vendor_wifi,
                    sizeof(paths->data_vendor_wifi),
                    paths->data_vendor,
                    "wifi") < 0 ||
        append_path(paths->data_vendor_wifi_sockets,
                    sizeof(paths->data_vendor_wifi_sockets),
                    paths->data_vendor_wifi,
                    "sockets") < 0 ||
        append_path(paths->proc, sizeof(paths->proc), paths->root, "proc") < 0 ||
        append_path(paths->apex, sizeof(paths->apex), paths->root, "apex") < 0 ||
        append_path(paths->linkerconfig, sizeof(paths->linkerconfig), paths->root, "linkerconfig") < 0) {
        return -1;
    }
    if (mkdir_p(paths->base, 0700) < 0 ||
        mkdir_p(paths->root, 0755) < 0 ||
        mkdir_p(paths->system, 0755) < 0 ||
        mkdir_p(paths->vendor, 0755) < 0 ||
        mkdir_p(paths->proc, 0755) < 0 ||
        mkdir_p(paths->apex, 0755) < 0 ||
        mkdir_p(paths->linkerconfig, 0755) < 0) {
        return -1;
    }
    return 0;
}

static int bind_ro(const char *source, const char *target) {
    if (mount(source, target, NULL, MS_BIND | MS_REC, NULL) < 0) {
        return -1;
    }
    if (mount(NULL, target, NULL, MS_BIND | MS_REMOUNT | MS_RDONLY | MS_NOSUID | MS_NODEV, NULL) < 0) {
        return -1;
    }
    return 0;
}

static int bind_rw(const char *source, const char *target) {
    return mount(source, target, NULL, MS_BIND | MS_REC, NULL);
}

static int materialize_private_properties(const struct config *cfg,
                                          const struct paths *paths,
                                          char *error_buf,
                                          size_t error_size) {
    struct stat st;
    bool wants_private_properties =
        streq(cfg->mode, "property-lookup") ||
        (streq(cfg->mode, "private-selinux-proof") &&
         cfg->property_root != NULL) ||
        (streq(cfg->mode, "service-manager-start-only") &&
         cfg->allow_service_manager_start_only &&
         cfg->property_root != NULL) ||
        ((is_rmt_storage_start_only_mode(cfg->mode) ||
          is_wifi_companion_any_start_only_mode(cfg->mode) ||
          is_wifi_companion_hal_order_start_only_mode(cfg->mode)) &&
         cfg->allow_wifi_companion_start_only &&
         cfg->property_root != NULL) ||
        (is_wifi_hal_composite_mode(cfg->mode) &&
         cfg->allow_service_manager_start_only &&
         cfg->allow_wifi_hal_start_only &&
         cfg->property_root != NULL);

    if (!wants_private_properties) {
        return 0;
    }
    if (lstat(cfg->property_root, &st) < 0) {
        snprintf(error_buf, error_size, "lstat property root: %s", strerror(errno));
        return -1;
    }
    if (S_ISLNK(st.st_mode)) {
        snprintf(error_buf, error_size, "property root is symlink");
        errno = ELOOP;
        return -1;
    }
    if (stat(cfg->property_root, &st) < 0) {
        snprintf(error_buf, error_size, "stat property root: %s", strerror(errno));
        return -1;
    }
    if (!S_ISDIR(st.st_mode)) {
        snprintf(error_buf, error_size, "property root is not directory");
        errno = ENOTDIR;
        return -1;
    }
    if (mkdir_p(paths->dev, 0755) < 0) {
        snprintf(error_buf, error_size, "mkdir dev for properties: %s", strerror(errno));
        return -1;
    }
    if (mkdir_p(paths->dev_properties, 0755) < 0) {
        snprintf(error_buf, error_size, "mkdir dev properties: %s", strerror(errno));
        return -1;
    }
    if (bind_ro(cfg->property_root, paths->dev_properties) < 0) {
        snprintf(error_buf, error_size, "bind private properties: %s", strerror(errno));
        return -1;
    }
    return 0;
}

static int materialize_selinuxfs_surface(const struct config *cfg,
                                         const struct paths *paths,
                                         char *error_buf,
                                         size_t error_size) {
    struct stat st;

    if (!streq(cfg->mode, "private-selinux-proof") &&
        !streq(cfg->mode, "sepolicy-inventory") &&
        !streq(cfg->mode, "sepolicy-compile-proof") &&
        !streq(cfg->mode, "sepolicy-load-proof") &&
        !streq(cfg->mode, "selinux-domain-proof") &&
        !streq(cfg->mode, "service-manager-start-only") &&
        !is_rmt_storage_start_only_mode(cfg->mode) &&
        !is_wifi_companion_any_start_only_mode(cfg->mode) &&
        !is_wifi_companion_hal_order_start_only_mode(cfg->mode) &&
        !(is_wifi_hal_composite_mode(cfg->mode) &&
          cfg->allow_service_manager_start_only &&
          cfg->allow_wifi_hal_start_only)) {
        return 0;
    }
    if (stat("/sys/fs/selinux/status", &st) < 0) {
        snprintf(error_buf, error_size, "stat host selinux status: %s", strerror(errno));
        return -1;
    }
    if (mkdir_p(paths->sys_fs_selinux, 0755) < 0) {
        snprintf(error_buf, error_size, "mkdir private selinuxfs target: %s", strerror(errno));
        return -1;
    }
    if (bind_rw("/sys/fs/selinux", paths->sys_fs_selinux) < 0) {
        snprintf(error_buf, error_size, "bind selinuxfs surface: %s", strerror(errno));
        return -1;
    }
    return 0;
}

static uint64_t fnv1a64_update(uint64_t hash, const void *data, size_t len) {
    const unsigned char *bytes = data;

    for (size_t i = 0; i < len; i++) {
        hash ^= bytes[i];
        hash *= UINT64_C(1099511628211);
    }
    return hash;
}

static int write_all_fd(int fd, const void *data, size_t len) {
    const unsigned char *bytes = data;
    size_t done = 0;

    while (done < len) {
        ssize_t nwritten = write(fd, bytes + done, len - done);

        if (nwritten < 0) {
            if (errno == EINTR) {
                continue;
            }
            return -1;
        }
        if (nwritten == 0) {
            errno = EIO;
            return -1;
        }
        done += (size_t)nwritten;
    }
    return 0;
}

static int read_exact_fd(int fd, unsigned char *data, size_t len) {
    size_t done = 0;

    while (done < len) {
        ssize_t nread = read(fd, data + done, len - done);

        if (nread < 0) {
            if (errno == EINTR) {
                continue;
            }
            return -1;
        }
        if (nread == 0) {
            errno = EIO;
            return -1;
        }
        done += (size_t)nread;
    }
    return 0;
}

static int write_file_once_to_fd(const char *path, int out_fd, size_t *bytes_out, uint64_t *hash_out) {
    struct stat st;
    unsigned char *data;
    size_t total = 0;
    uint64_t hash;
    int in_fd = open(path, O_RDONLY | O_CLOEXEC);
    ssize_t nwritten;

    if (in_fd < 0) {
        return -1;
    }
    if (fstat(in_fd, &st) < 0) {
        close(in_fd);
        return -1;
    }
    if (!S_ISREG(st.st_mode) || st.st_size <= 0 || st.st_size > MAX_SEPOLICY_LOAD_SIZE) {
        close(in_fd);
        errno = EFBIG;
        return -1;
    }
    total = (size_t)st.st_size;
    data = malloc(total);
    if (data == NULL) {
        close(in_fd);
        return -1;
    }
    if (read_exact_fd(in_fd, data, total) < 0) {
        int saved_errno = errno;

        free(data);
        close(in_fd);
        errno = saved_errno;
        return -1;
    }
    close(in_fd);
    hash = fnv1a64_update(UINT64_C(1469598103934665603), data, total);
    do {
        nwritten = write(out_fd, data, total);
    } while (nwritten < 0 && errno == EINTR);
    if (nwritten < 0 || (size_t)nwritten != total) {
        int saved_errno = nwritten < 0 ? errno : EIO;

        free(data);
        errno = saved_errno;
        return -1;
    }
    free(data);
    if (bytes_out != NULL) {
        *bytes_out = total;
    }
    if (hash_out != NULL) {
        *hash_out = hash;
    }
    return 0;
}

static const char minimal_vendor_linkerconfig[] =
    "# A90 v232 synthetic private linkerconfig for linker64 --list only\n"
    "dir.vendor = /vendor/bin/\n"
    "\n"
    "[vendor]\n"
    "namespace.default.isolated = false\n"
    "namespace.default.search.paths = /vendor/${LIB}\n"
    "namespace.default.search.paths += /system/${LIB}\n"
    "namespace.default.search.paths += /apex/com.android.runtime/${LIB}/bionic\n"
    "namespace.default.permitted.paths = /vendor/${LIB}\n"
    "namespace.default.permitted.paths += /system/${LIB}\n"
    "namespace.default.permitted.paths += /apex/com.android.runtime/${LIB}/bionic\n";

static int append_linkerconfig_file(const char *dest,
                                    const char *data,
                                    size_t len,
                                    size_t *total_bytes,
                                    uint64_t *hash) {
    int fd = open(dest, O_WRONLY | O_CREAT | O_APPEND | O_CLOEXEC, 0644);

    if (fd < 0) {
        return -1;
    }
    if (write_all_fd(fd, data, len) < 0) {
        int saved_errno = errno;
        close(fd);
        errno = saved_errno;
        return -1;
    }
    close(fd);
    *hash = fnv1a64_update(*hash, data, len);
    *total_bytes += len;
    return 0;
}

static int copy_linkerconfig_file(const char *source,
                                  const char *dest,
                                  size_t *total_bytes,
                                  uint64_t *hash) {
    char tmp[4096];
    int in_fd = open(source, O_RDONLY | O_CLOEXEC);
    int out_fd;

    if (in_fd < 0) {
        return -1;
    }
    out_fd = open(dest, O_WRONLY | O_CREAT | O_TRUNC | O_CLOEXEC, 0644);
    if (out_fd < 0) {
        int saved_errno = errno;
        close(in_fd);
        errno = saved_errno;
        return -1;
    }
    for (;;) {
        ssize_t nread = read(in_fd, tmp, sizeof(tmp));

        if (nread < 0) {
            if (errno == EINTR) {
                continue;
            }
            goto fail;
        }
        if (nread == 0) {
            break;
        }
        if (*total_bytes + (size_t)nread > MAX_LINKERCONFIG_SIZE) {
            errno = EFBIG;
            goto fail;
        }
        if (write_all_fd(out_fd, tmp, (size_t)nread) < 0) {
            goto fail;
        }
        *hash = fnv1a64_update(*hash, tmp, (size_t)nread);
        *total_bytes += (size_t)nread;
    }
    close(out_fd);
    close(in_fd);
    return 0;

fail:
    {
        int saved_errno = errno;
        close(out_fd);
        close(in_fd);
        errno = saved_errno;
        return -1;
    }
}

static int materialize_linkerconfig(const struct config *cfg,
                                    const struct paths *paths,
                                    size_t *total_bytes,
                                    uint64_t *hash,
                                    char *error_buf,
                                    size_t error_size) {
    char dest[MAX_PATH_LEN];

    *total_bytes = 0;
    *hash = UINT64_C(1469598103934665603);
    if (append_path(dest, sizeof(dest), paths->linkerconfig, "ld.config.txt") < 0) {
        snprintf(error_buf, error_size, "linkerconfig path: %s", strerror(errno));
        return -1;
    }
    if (unlink(dest) < 0 && errno != ENOENT) {
        snprintf(error_buf, error_size, "unlink linkerconfig: %s", strerror(errno));
        return -1;
    }
    if (streq(cfg->linkerconfig_mode, "minimal-vendor")) {
        if (append_linkerconfig_file(dest,
                                     minimal_vendor_linkerconfig,
                                     strlen(minimal_vendor_linkerconfig),
                                     total_bytes,
                                     hash) < 0) {
            snprintf(error_buf, error_size, "write minimal linkerconfig: %s", strerror(errno));
            return -1;
        }
        return 0;
    }
    if (streq(cfg->linkerconfig_mode, "copy-real")) {
        if (copy_linkerconfig_file(cfg->linkerconfig_source, dest, total_bytes, hash) < 0) {
            snprintf(error_buf, error_size, "copy linkerconfig: %s", strerror(errno));
            return -1;
        }
        if (cfg->apex_libraries_source != NULL) {
            if (append_path(dest, sizeof(dest), paths->linkerconfig, "apex.libraries.config.txt") < 0) {
                snprintf(error_buf, error_size, "apex libraries path: %s", strerror(errno));
                return -1;
            }
            if (unlink(dest) < 0 && errno != ENOENT) {
                snprintf(error_buf, error_size, "unlink apex libraries: %s", strerror(errno));
                return -1;
            }
            if (copy_linkerconfig_file(cfg->apex_libraries_source, dest, total_bytes, hash) < 0) {
                snprintf(error_buf, error_size, "copy apex libraries: %s", strerror(errno));
                return -1;
            }
        }
        return 0;
    }
    errno = EINVAL;
    snprintf(error_buf, error_size, "invalid linkerconfig mode");
    return -1;
}

static int materialize_null_devices(const struct config *cfg,
                                    const struct paths *paths,
                                    char *error_buf,
                                    size_t error_size) {
    if (streq(cfg->null_device_mode, "none")) {
        return 0;
    }
    if (mkdir_p(paths->dev, 0755) < 0) {
        snprintf(error_buf, error_size, "mkdir dev: %s", strerror(errno));
        return -1;
    }
    if (unlink(paths->dev_null) < 0 && errno != ENOENT) {
        snprintf(error_buf, error_size, "unlink dev null: %s", strerror(errno));
        return -1;
    }
    if (mknod(paths->dev_null, S_IFCHR | 0666, makedev(1, 3)) < 0) {
        snprintf(error_buf, error_size, "mknod dev null: %s", strerror(errno));
        return -1;
    }
    if (chmod(paths->dev_null, 0666) < 0) {
        snprintf(error_buf, error_size, "chmod dev null: %s", strerror(errno));
        return -1;
    }
    if (!streq(cfg->null_device_mode, "dev-null-selinux")) {
        return 0;
    }
    if (mkdir_p(paths->sys_fs_selinux, 0755) < 0) {
        snprintf(error_buf, error_size, "mkdir sys fs selinux: %s", strerror(errno));
        return -1;
    }
    if (unlink(paths->sys_fs_selinux_null) < 0 && errno != ENOENT) {
        snprintf(error_buf, error_size, "unlink selinux null: %s", strerror(errno));
        return -1;
    }
    if (mknod(paths->sys_fs_selinux_null, S_IFCHR | 0666, makedev(1, 3)) < 0) {
        snprintf(error_buf, error_size, "mknod selinux null: %s", strerror(errno));
        return -1;
    }
    if (chmod(paths->sys_fs_selinux_null, 0666) < 0) {
        snprintf(error_buf, error_size, "chmod selinux null: %s", strerror(errno));
        return -1;
    }
    return 0;
}

static int materialize_one_binder_device(const char *path,
                                         unsigned int minor_no,
                                         const char *name,
                                         char *error_buf,
                                         size_t error_size) {
    if (unlink(path) < 0 && errno != ENOENT) {
        snprintf(error_buf, error_size, "unlink %s: %s", name, strerror(errno));
        return -1;
    }
    if (mknod(path, S_IFCHR | 0666, makedev(10, minor_no)) < 0) {
        snprintf(error_buf, error_size, "mknod %s: %s", name, strerror(errno));
        return -1;
    }
    if (chmod(path, 0666) < 0) {
        snprintf(error_buf, error_size, "chmod %s: %s", name, strerror(errno));
        return -1;
    }
    return 0;
}

static int materialize_service_manager_binder_devices(const struct config *cfg,
                                                      const struct paths *paths,
                                                      char *error_buf,
                                                      size_t error_size) {
    if (!(streq(cfg->mode, "private-selinux-proof") ||
          (is_rmt_storage_start_only_mode(cfg->mode) &&
           cfg->allow_wifi_companion_start_only &&
           cfg->property_root != NULL) ||
          (is_wifi_companion_any_start_only_mode(cfg->mode) &&
           cfg->allow_wifi_companion_start_only &&
           cfg->allow_cnss_start_only) ||
          (is_wifi_companion_peripheral_manager_node_materialization_mode(cfg->mode) &&
           cfg->allow_wifi_companion_start_only &&
           cfg->allow_service_manager_start_only) ||
          (is_wifi_companion_hal_order_start_only_mode(cfg->mode) &&
           cfg->allow_wifi_companion_start_only &&
           cfg->allow_cnss_start_only &&
           cfg->allow_service_manager_start_only &&
           cfg->allow_wifi_hal_start_only) ||
          (streq(cfg->mode, "service-manager-start-only") &&
           cfg->allow_service_manager_start_only) ||
          (is_wifi_hal_composite_mode(cfg->mode) &&
           cfg->allow_service_manager_start_only &&
           cfg->allow_wifi_hal_start_only))) {
        return 0;
    }
    if (mkdir_p(paths->dev, 0755) < 0) {
        snprintf(error_buf, error_size, "mkdir dev for binder: %s", strerror(errno));
        return -1;
    }
    if (materialize_one_binder_device(paths->dev_binder, 81, "binder", error_buf, error_size) < 0 ||
        materialize_one_binder_device(paths->dev_hwbinder, 80, "hwbinder", error_buf, error_size) < 0 ||
        materialize_one_binder_device(paths->dev_vndbinder, 79, "vndbinder", error_buf, error_size) < 0) {
        return -1;
    }
    return 0;
}

static int materialize_wifi_wlan_device(const struct config *cfg,
                                        const struct paths *paths,
                                        char *error_buf,
                                        size_t error_size) {
    struct stat st;

    if (!((is_wifi_hal_composite_mode(cfg->mode) ||
           is_wifi_companion_hal_order_start_only_mode(cfg->mode) ||
           is_wifi_companion_service74_gated_android_userspace_cnss_retry_start_only_mode(cfg->mode)) &&
          cfg->allow_service_manager_start_only &&
          cfg->allow_wifi_hal_start_only)) {
        return 0;
    }
    if (lstat("/dev/wlan", &st) < 0) {
        if (errno == ENOENT) {
            return 0;
        }
        snprintf(error_buf, error_size, "stat host dev wlan: %s", strerror(errno));
        return -1;
    }
    if (!S_ISCHR(st.st_mode)) {
        snprintf(error_buf, error_size, "host dev wlan is not a char device");
        errno = ENODEV;
        return -1;
    }
    if (mkdir_p(paths->dev, 0755) < 0) {
        snprintf(error_buf, error_size, "mkdir dev for wlan: %s", strerror(errno));
        return -1;
    }
    if (unlink(paths->dev_wlan) < 0 && errno != ENOENT) {
        snprintf(error_buf, error_size, "unlink dev wlan: %s", strerror(errno));
        return -1;
    }
    if (mknod(paths->dev_wlan, S_IFCHR | 0660, st.st_rdev) < 0) {
        snprintf(error_buf, error_size, "mknod dev wlan: %s", strerror(errno));
        return -1;
    }
    if (chown(paths->dev_wlan, A90_AID_WIFI, A90_AID_WIFI) < 0) {
        snprintf(error_buf, error_size, "chown dev wlan: %s", strerror(errno));
        return -1;
    }
    if (chmod(paths->dev_wlan, 0660) < 0) {
        snprintf(error_buf, error_size, "chmod dev wlan: %s", strerror(errno));
        return -1;
    }
    return 0;
}

static int materialize_data_wifi(const struct config *cfg,
                                 const struct paths *paths,
                                 char *error_buf,
                                 size_t error_size) {
    if (streq(cfg->data_wifi_mode, "none")) {
        return 0;
    }
    if (!streq(cfg->data_wifi_mode, "private-empty")) {
        snprintf(error_buf, error_size, "invalid data wifi mode");
        errno = EINVAL;
        return -1;
    }
    if (mkdir_p(paths->data_vendor_wifi_sockets, 0770) < 0) {
        snprintf(error_buf, error_size, "mkdir data vendor wifi sockets: %s", strerror(errno));
        return -1;
    }
    (void)chmod(paths->data, 0771);
    (void)chmod(paths->data_vendor, 0771);
    (void)chmod(paths->data_vendor_wifi, 0770);
    (void)chmod(paths->data_vendor_wifi_sockets, 0770);
    if (chown(paths->data_vendor_wifi, A90_AID_SYSTEM, A90_AID_WIFI) < 0) {
        snprintf(error_buf, error_size, "chown data vendor wifi: %s", strerror(errno));
        return -1;
    }
    if (chown(paths->data_vendor_wifi_sockets, A90_AID_SYSTEM, A90_AID_WIFI) < 0) {
        snprintf(error_buf, error_size, "chown data vendor wifi sockets: %s", strerror(errno));
        return -1;
    }
    return 0;
}

static bool safe_apex_name(const char *name) {
    return name != NULL &&
           name[0] != '\0' &&
           strcmp(name, ".") != 0 &&
           strcmp(name, "..") != 0 &&
           strchr(name, '/') == NULL;
}

static int bind_apex_entry(const struct paths *paths,
                           const char *system_apex,
                           const char *name,
                           const char *target_name,
                           char *error_buf,
                           size_t error_size) {
    char mount_path[MAX_PATH_LEN];
    char source_path[MAX_PATH_LEN];
    struct stat st;

    if (!safe_apex_name(name) || !safe_apex_name(target_name)) {
        errno = EINVAL;
        snprintf(error_buf, error_size, "unsafe apex name");
        return -1;
    }
    if (append_path(mount_path, sizeof(mount_path), paths->apex, name) < 0) {
        snprintf(error_buf, error_size, "apex mount path: %s", strerror(errno));
        return -1;
    }
    if (append_path(source_path, sizeof(source_path), system_apex, target_name) < 0) {
        snprintf(error_buf, error_size, "apex source path: %s", strerror(errno));
        return -1;
    }
    if (stat(source_path, &st) < 0) {
        snprintf(error_buf, error_size, "stat apex %s: %s", target_name, strerror(errno));
        return -1;
    }
    if (!S_ISDIR(st.st_mode)) {
        snprintf(error_buf, error_size, "apex %s is not a directory", target_name);
        errno = ENOTDIR;
        return -1;
    }
    if (mkdir_p(mount_path, 0755) < 0) {
        snprintf(error_buf, error_size, "mkdir apex %s: %s", name, strerror(errno));
        return -1;
    }
    if (bind_ro(source_path, mount_path) < 0) {
        snprintf(error_buf, error_size, "bind apex %s: %s", name, strerror(errno));
        return -1;
    }
    return 0;
}

static int materialize_apex_bind_farm(const struct config *cfg,
                                      struct paths *paths,
                                      const char *system_apex,
                                      char *error_buf,
                                      size_t error_size) {
    DIR *dir;
    struct dirent *entry;
    char current_source[MAX_PATH_LEN];
    char system_ext_apex[MAX_PATH_LEN];
    char system_ext_source[MAX_PATH_LEN];
    char v30_mount[MAX_PATH_LEN];

    paths->apex_synthetic = true;
    dir = opendir(system_apex);
    if (dir == NULL) {
        snprintf(error_buf, error_size, "opendir system apex: %s", strerror(errno));
        return -1;
    }
    while ((entry = readdir(dir)) != NULL) {
        if (!safe_apex_name(entry->d_name)) {
            continue;
        }
        if (bind_apex_entry(paths,
                            system_apex,
                            entry->d_name,
                            entry->d_name,
                            error_buf,
                            error_size) < 0) {
            closedir(dir);
            return -1;
        }
    }
    closedir(dir);

    if (streq(cfg->vndk_apex_alias_mode, "none")) {
        return 0;
    }
    if (append_path(v30_mount, sizeof(v30_mount), paths->apex, "com.android.vndk.v30") < 0) {
        snprintf(error_buf, error_size, "vndk v30 mount path: %s", strerror(errno));
        return -1;
    }
    if (access(v30_mount, F_OK) == 0) {
        return 0;
    }
    if (errno != ENOENT) {
        snprintf(error_buf, error_size, "stat vndk v30 mount: %s", strerror(errno));
        return -1;
    }
    if (streq(cfg->vndk_apex_alias_mode, "v30-to-system-ext-v30")) {
        if (append_path(system_ext_apex, sizeof(system_ext_apex), cfg->system_root, "system_ext/apex") < 0) {
            snprintf(error_buf, error_size, "system_ext apex path: %s", strerror(errno));
            return -1;
        }
        if (append_path(system_ext_source,
                        sizeof(system_ext_source),
                        system_ext_apex,
                        "com.android.vndk.v30") < 0) {
            snprintf(error_buf, error_size, "system_ext vndk v30 path: %s", strerror(errno));
            return -1;
        }
        if (access(system_ext_source, R_OK | X_OK) < 0) {
            snprintf(error_buf, error_size, "system_ext vndk v30 missing: %s", strerror(errno));
            return -1;
        }
        return bind_apex_entry(paths,
                               system_ext_apex,
                               "com.android.vndk.v30",
                               "com.android.vndk.v30",
                               error_buf,
                               error_size);
    }
    if (append_path(current_source,
                    sizeof(current_source),
                    system_apex,
                    "com.android.vndk.current") < 0) {
        snprintf(error_buf, error_size, "vndk current path: %s", strerror(errno));
        return -1;
    }
    if (access(current_source, R_OK | X_OK) < 0) {
        snprintf(error_buf, error_size, "vndk current missing: %s", strerror(errno));
        return -1;
    }
    return bind_apex_entry(paths,
                           system_apex,
                           "com.android.vndk.v30",
                           "com.android.vndk.current",
                           error_buf,
                           error_size);
}

static void cleanup_dir_entries(const char *path) {
    DIR *dir = opendir(path);
    struct dirent *entry;

    if (dir == NULL) {
        return;
    }
    while ((entry = readdir(dir)) != NULL) {
        char child[MAX_PATH_LEN];

        if (!safe_apex_name(entry->d_name)) {
            continue;
        }
        if (append_path(child, sizeof(child), path, entry->d_name) == 0) {
            umount2(child, MNT_DETACH);
            if (rmdir(child) < 0) {
                unlink(child);
            }
        }
    }
    closedir(dir);
}

static void cleanup_paths(const struct paths *paths) {
    char linkerconfig_file[MAX_PATH_LEN];

    if (paths->apex[0] != '\0') {
        umount2(paths->apex, MNT_DETACH);
        if (paths->apex_synthetic) {
            cleanup_dir_entries(paths->apex);
        }
    }
    if (paths->linkerconfig[0] != '\0') {
        umount2(paths->linkerconfig, MNT_DETACH);
        if (append_path(linkerconfig_file,
                        sizeof(linkerconfig_file),
                        paths->linkerconfig,
                        "ld.config.txt") == 0) {
            unlink(linkerconfig_file);
        }
        if (append_path(linkerconfig_file,
                        sizeof(linkerconfig_file),
                        paths->linkerconfig,
                        "apex.libraries.config.txt") == 0) {
            unlink(linkerconfig_file);
        }
    }
    umount2(paths->proc, MNT_DETACH);
    umount2(paths->vendor_firmware_modem, MNT_DETACH);
    umount2(paths->vendor_firmware_mnt, MNT_DETACH);
    umount2(paths->vendor, MNT_DETACH);
    umount2(paths->system, MNT_DETACH);
    if (paths->sys_fs_selinux[0] != '\0') {
        umount2(paths->sys_fs_selinux, MNT_DETACH);
    }
    if (paths->sys_class_uio[0] != '\0') {
        umount2(paths->sys_class_uio, MNT_DETACH);
    }
    if (paths->sys_bus_esoc[0] != '\0') {
        umount2(paths->sys_bus_esoc, MNT_DETACH);
    }
    if (paths->sys_bus_msm_subsys[0] != '\0') {
        umount2(paths->sys_bus_msm_subsys, MNT_DETACH);
    }
    if (paths->sys_devices_platform_soc_mdm3[0] != '\0') {
        umount2(paths->sys_devices_platform_soc_mdm3, MNT_DETACH);
    }
    if (paths->sys_devices_platform_soc_mss[0] != '\0') {
        umount2(paths->sys_devices_platform_soc_mss, MNT_DETACH);
    }
    if (paths->sys_fs_selinux_null[0] != '\0') {
        unlink(paths->sys_fs_selinux_null);
    }
    if (paths->dev_properties[0] != '\0') {
        umount2(paths->dev_properties, MNT_DETACH);
        rmdir(paths->dev_properties);
    }
    if (paths->property_service_socket[0] != '\0') {
        unlink(paths->property_service_socket);
    }
    if (paths->dev_socket[0] != '\0') {
        rmdir(paths->dev_socket);
    }
    if (paths->dev_wlan[0] != '\0') {
        unlink(paths->dev_wlan);
    }
    if (paths->dev_uio0[0] != '\0') {
        unlink(paths->dev_uio0);
    }
    if (paths->dev_kmsg[0] != '\0') {
        unlink(paths->dev_kmsg);
    }
    if (paths->dev_binder[0] != '\0') {
        unlink(paths->dev_binder);
    }
    if (paths->dev_hwbinder[0] != '\0') {
        unlink(paths->dev_hwbinder);
    }
    if (paths->dev_vndbinder[0] != '\0') {
        unlink(paths->dev_vndbinder);
    }
    if (paths->dev_block_by_name[0] != '\0') {
        cleanup_dir_entries(paths->dev_block_by_name);
        rmdir(paths->dev_block_by_name);
    }
    if (paths->dev_block_bootdevice_by_name[0] != '\0') {
        cleanup_dir_entries(paths->dev_block_bootdevice_by_name);
        rmdir(paths->dev_block_bootdevice_by_name);
    }
    if (paths->dev_block_bootdevice[0] != '\0') {
        rmdir(paths->dev_block_bootdevice);
    }
    if (paths->dev_block[0] != '\0') {
        cleanup_dir_entries(paths->dev_block);
        rmdir(paths->dev_block);
    }
    if (paths->dev_null[0] != '\0') {
        unlink(paths->dev_null);
    }
    if (paths->sys_power_wake_lock[0] != '\0') {
        unlink(paths->sys_power_wake_lock);
    }
    if (paths->sys_power_wake_unlock[0] != '\0') {
        unlink(paths->sys_power_wake_unlock);
    }
    if (paths->sys_power[0] != '\0') {
        rmdir(paths->sys_power);
    }
    if (paths->sys_class_uio[0] != '\0') {
        char child[MAX_PATH_LEN];

        if (append_path(child, sizeof(child), paths->sys_class_uio, "uio0/name") == 0) unlink(child);
        if (append_path(child, sizeof(child), paths->sys_class_uio, "uio0/version") == 0) unlink(child);
        if (append_path(child, sizeof(child), paths->sys_class_uio, "uio0/dev") == 0) unlink(child);
        if (append_path(child, sizeof(child), paths->sys_class_uio, "uio0/maps/map0/addr") == 0) unlink(child);
        if (append_path(child, sizeof(child), paths->sys_class_uio, "uio0/maps/map0/size") == 0) unlink(child);
        if (append_path(child, sizeof(child), paths->sys_class_uio, "uio0/maps/map0/name") == 0) unlink(child);
        if (append_path(child, sizeof(child), paths->sys_class_uio, "uio0/maps/map0/offset") == 0) unlink(child);
        if (append_path(child, sizeof(child), paths->sys_class_uio, "uio0/maps/map0") == 0) rmdir(child);
        if (append_path(child, sizeof(child), paths->sys_class_uio, "uio0/maps") == 0) rmdir(child);
        if (append_path(child, sizeof(child), paths->sys_class_uio, "uio0") == 0) rmdir(child);
        rmdir(paths->sys_class_uio);
    }
    if (paths->sys_class[0] != '\0') {
        rmdir(paths->sys_class);
    }
    if (paths->sys_bus_esoc[0] != '\0') {
        rmdir(paths->sys_bus_esoc);
    }
    if (paths->sys_bus_msm_subsys[0] != '\0') {
        rmdir(paths->sys_bus_msm_subsys);
    }
    if (paths->sys_bus[0] != '\0') {
        rmdir(paths->sys_bus);
    }
    if (paths->sys_devices_platform_soc_mdm3[0] != '\0') {
        rmdir(paths->sys_devices_platform_soc_mdm3);
    }
    if (paths->sys_devices_platform_soc_mss[0] != '\0') {
        rmdir(paths->sys_devices_platform_soc_mss);
    }
    if (paths->sys_devices_platform_soc[0] != '\0') {
        rmdir(paths->sys_devices_platform_soc);
    }
    if (paths->sys_devices_platform[0] != '\0') {
        rmdir(paths->sys_devices_platform);
    }
    if (paths->sys_devices[0] != '\0') {
        rmdir(paths->sys_devices);
    }
    if (paths->sys_fs_selinux[0] != '\0') {
        rmdir(paths->sys_fs_selinux);
    }
    if (paths->sys_fs[0] != '\0') {
        rmdir(paths->sys_fs);
    }
    if (paths->sys[0] != '\0') {
        rmdir(paths->sys);
    }
    if (paths->dev[0] != '\0') {
        rmdir(paths->dev);
    }
    if (paths->data_vendor_wifi_sockets[0] != '\0') {
        rmdir(paths->data_vendor_wifi_sockets);
    }
    if (paths->data_vendor_wifi[0] != '\0') {
        rmdir(paths->data_vendor_wifi);
    }
    if (paths->data_vendor[0] != '\0') {
        rmdir(paths->data_vendor);
    }
    if (paths->data[0] != '\0') {
        rmdir(paths->data);
    }
    if (paths->apex[0] != '\0') {
        rmdir(paths->apex);
    }
    if (paths->linkerconfig[0] != '\0') {
        rmdir(paths->linkerconfig);
    }
    rmdir(paths->proc);
    rmdir(paths->vendor);
    rmdir(paths->system);
    rmdir(paths->root);
    unlink(paths->firmware_modem_source);
    unlink(paths->firmware_mnt_source);
    unlink(paths->vendor_source);
    rmdir(paths->base);
}

static int buffer_init(struct buffer *buf) {
    buf->data = calloc(1, 1);
    if (buf->data == NULL) {
        return -1;
    }
    buf->len = 0;
    buf->cap = 1;
    buf->truncated = false;
    return 0;
}

static void buffer_free(struct buffer *buf) {
    free(buf->data);
    buf->data = NULL;
    buf->len = 0;
    buf->cap = 0;
}

static int buffer_append(struct buffer *buf, const char *data, size_t len) {
    size_t allowed = len;

    if (buf->len >= MAX_CAPTURE_SIZE) {
        buf->truncated = true;
        return 0;
    }
    if (buf->len + allowed > MAX_CAPTURE_SIZE) {
        allowed = MAX_CAPTURE_SIZE - buf->len;
        buf->truncated = true;
    }
    if (buf->len + allowed + 1 > buf->cap) {
        size_t new_cap = buf->cap;
        char *new_data;

        while (new_cap < buf->len + allowed + 1) {
            new_cap *= 2;
        }
        new_data = realloc(buf->data, new_cap);
        if (new_data == NULL) {
            return -1;
        }
        buf->data = new_data;
        buf->cap = new_cap;
    }
    memcpy(buf->data + buf->len, data, allowed);
    buf->len += allowed;
    buf->data[buf->len] = '\0';
    return 0;
}

static int set_nonblock(int fd) {
    int flags = fcntl(fd, F_GETFL, 0);

    if (flags < 0) {
        return -1;
    }
    return fcntl(fd, F_SETFL, flags | O_NONBLOCK);
}

static int drain_fd(int fd, struct buffer *buf, bool *open_flag) {
    char tmp[4096];

    for (;;) {
        ssize_t nread = read(fd, tmp, sizeof(tmp));

        if (nread > 0) {
            if (buffer_append(buf, tmp, (size_t)nread) < 0) {
                return -1;
            }
            continue;
        }
        if (nread == 0) {
            close(fd);
            *open_flag = false;
            return 0;
        }
        if (errno == EINTR) {
            continue;
        }
        if (errno == EAGAIN || errno == EWOULDBLOCK) {
            return 0;
        }
        close(fd);
        *open_flag = false;
        return -1;
    }
}

static long monotonic_ms(void) {
    struct timespec ts;

    if (clock_gettime(CLOCK_MONOTONIC, &ts) < 0) {
        return 0;
    }
    return ts.tv_sec * 1000L + ts.tv_nsec / 1000000L;
}

static pid_t wait_for_child_session_pgid(pid_t pid, long timeout_ms);
static int read_small_file_trim(const char *path, char *out, size_t out_size);
static int parse_dev_major_minor(const char *path,
                                 unsigned int *major_no,
                                 unsigned int *minor_no,
                                 char *text,
                                 size_t text_size);

static int path_in_root(char *out, size_t out_size, const struct paths *paths, const char *absolute_path) {
    const char *relative = absolute_path;
    int rc;

    if (absolute_path == NULL || absolute_path[0] != '/') {
        errno = EINVAL;
        return -1;
    }
    while (*relative == '/') {
        relative++;
    }
    rc = snprintf(out, out_size, "%s/%s", paths->root, relative);
    if (rc < 0 || (size_t)rc >= out_size) {
        errno = ENAMETOOLONG;
        return -1;
    }
    return 0;
}

static int fnv1a64_file(const char *path, uint64_t *hash, size_t *bytes) {
    char tmp[4096];
    int fd = open(path, O_RDONLY | O_CLOEXEC);

    *hash = UINT64_C(1469598103934665603);
    *bytes = 0;
    if (fd < 0) {
        return -1;
    }
    for (;;) {
        ssize_t nread = read(fd, tmp, sizeof(tmp));

        if (nread < 0) {
            if (errno == EINTR) {
                continue;
            }
            close(fd);
            return -1;
        }
        if (nread == 0) {
            break;
        }
        *hash = fnv1a64_update(*hash, tmp, (size_t)nread);
        *bytes += (size_t)nread;
        if (*bytes > MAX_LINKERCONFIG_SIZE * 4U) {
            break;
        }
    }
    close(fd);
    return 0;
}

static void print_context_path(const struct paths *paths, const char *label, const char *absolute_path) {
    char host_path[MAX_PATH_LEN];
    char link_target[MAX_PATH_LEN];
    struct stat st;
    ssize_t nreadlink;
    uint64_t hash;
    size_t bytes;

    if (path_in_root(host_path, sizeof(host_path), paths, absolute_path) < 0) {
        printf("context.%s.path=%s\n", label, absolute_path);
        printf("context.%s.error=path-too-long\n", label);
        return;
    }
    printf("context.%s.path=%s\n", label, absolute_path);
    printf("context.%s.host_path=%s\n", label, host_path);
    if (lstat(host_path, &st) < 0) {
        printf("context.%s.exists=0\n", label);
        printf("context.%s.errno=%d\n", label, errno);
        return;
    }
    printf("context.%s.exists=1\n", label);
    printf("context.%s.uid=%u\n", label, (unsigned int)st.st_uid);
    printf("context.%s.gid=%u\n", label, (unsigned int)st.st_gid);
    printf("context.%s.mode=%o\n", label, st.st_mode & 07777);
    printf("context.%s.type=%s\n", label,
           S_ISREG(st.st_mode) ? "regular" :
           S_ISDIR(st.st_mode) ? "directory" :
           S_ISLNK(st.st_mode) ? "symlink" :
           S_ISCHR(st.st_mode) ? "char" :
           S_ISBLK(st.st_mode) ? "block" : "other");
    if (S_ISCHR(st.st_mode) || S_ISBLK(st.st_mode)) {
        printf("context.%s.rdev=%u:%u\n",
               label,
               major(st.st_rdev),
               minor(st.st_rdev));
    }
    printf("context.%s.size=%lld\n", label, (long long)st.st_size);
    nreadlink = readlink(host_path, link_target, sizeof(link_target) - 1);
    if (nreadlink >= 0) {
        link_target[nreadlink] = '\0';
        printf("context.%s.readlink=%s\n", label, link_target);
    }
    printf("context.%s.access_r=%d\n", label, access(host_path, R_OK) == 0 ? 1 : 0);
    printf("context.%s.access_x=%d\n", label, access(host_path, X_OK) == 0 ? 1 : 0);
    if (S_ISREG(st.st_mode) && fnv1a64_file(host_path, &hash, &bytes) == 0) {
        printf("context.%s.bytes=%zu\n", label, bytes);
        printf("context.%s.hash=0x%016llx\n", label, (unsigned long long)hash);
    }
}

static void print_preexec_context(const struct config *cfg, const struct paths *paths) {
    if (cfg->linker != NULL) {
        print_context_path(paths, "linker", cfg->linker);
    }
    if (cfg->target != NULL) {
    print_context_path(paths, "target", cfg->target);
    }
    print_context_path(paths, "dev_null", "/dev/null");
    print_context_path(paths, "dev_wlan", "/dev/wlan");
    print_context_path(paths, "dev_block", "/dev/block");
    print_context_path(paths, "dev_block_by_name", "/dev/block/by-name");
    print_context_path(paths, "dev_block_bootdevice_by_name", "/dev/block/bootdevice/by-name");
    print_context_path(paths, "dev_block_modemst1", "/dev/block/bootdevice/by-name/modemst1");
    print_context_path(paths, "dev_block_modemst2", "/dev/block/bootdevice/by-name/modemst2");
    print_context_path(paths, "dev_block_fsc", "/dev/block/bootdevice/by-name/fsc");
    print_context_path(paths, "dev_block_fsg", "/dev/block/bootdevice/by-name/fsg");
    print_context_path(paths, "dev_uio0", "/dev/uio0");
    print_context_path(paths, "dev_kmsg", "/dev/kmsg");
    print_context_path(paths, "dev_binder", "/dev/binder");
    print_context_path(paths, "dev_hwbinder", "/dev/hwbinder");
    print_context_path(paths, "dev_vndbinder", "/dev/vndbinder");
    print_context_path(paths, "dev_properties", "/dev/__properties__");
    print_context_path(paths, "selinux_null", "/sys/fs/selinux/null");
    print_context_path(paths, "sys_class_uio", "/sys/class/uio");
    print_context_path(paths, "sys_class_uio0_name", "/sys/class/uio/uio0/name");
    print_context_path(paths, "sys_class_uio0_dev", "/sys/class/uio/uio0/dev");
    print_context_path(paths, "sys_class_uio0_version", "/sys/class/uio/uio0/version");
    print_context_path(paths, "sys_class_uio0_map0_addr", "/sys/class/uio/uio0/maps/map0/addr");
    print_context_path(paths, "sys_class_uio0_map0_size", "/sys/class/uio/uio0/maps/map0/size");
    print_context_path(paths, "sys_class_uio0_map0_offset", "/sys/class/uio/uio0/maps/map0/offset");
    print_context_path(paths, "sys_bus_esoc", "/sys/bus/esoc");
    print_context_path(paths, "sys_bus_esoc_device_esoc0", "/sys/bus/esoc/devices/esoc0");
    print_context_path(paths, "sys_bus_msm_subsys", "/sys/bus/msm_subsys");
    print_context_path(paths, "sys_bus_msm_subsys_device_subsys9", "/sys/bus/msm_subsys/devices/subsys9");
    print_context_path(paths, "sys_mdm3_esoc0_esoc_name", "/sys/devices/platform/soc/soc:qcom,mdm3/esoc0/esoc_name");
    print_context_path(paths, "sys_mdm3_esoc0_esoc_link", "/sys/devices/platform/soc/soc:qcom,mdm3/esoc0/esoc_link");
    print_context_path(paths, "sys_mdm3_esoc0_esoc_link_info", "/sys/devices/platform/soc/soc:qcom,mdm3/esoc0/esoc_link_info");
    print_context_path(paths, "sys_mdm3_subsys9_name", "/sys/devices/platform/soc/soc:qcom,mdm3/subsys9/name");
    print_context_path(paths, "sys_mss_subsys0_name", "/sys/devices/platform/soc/4080000.qcom,mss/subsys0/name");
    print_context_path(paths, "sys_power_wake_lock", "/sys/power/wake_lock");
    print_context_path(paths, "sys_power_wake_unlock", "/sys/power/wake_unlock");
    print_context_path(paths, "selinux_status", "/sys/fs/selinux/status");
    print_context_path(paths, "selinux_enforce", "/sys/fs/selinux/enforce");
    print_context_path(paths, "selinux_policy", "/sys/fs/selinux/policy");
    print_context_path(paths, "selinux_service_manager_class", "/sys/fs/selinux/class/service_manager");
    print_context_path(paths, "selinux_service_manager_list", "/sys/fs/selinux/class/service_manager/perms/list");
    print_context_path(paths, "selinux_service_manager_add", "/sys/fs/selinux/class/service_manager/perms/add");
    print_context_path(paths, "selinux_service_manager_find", "/sys/fs/selinux/class/service_manager/perms/find");
    print_context_path(paths, "data", "/data");
    print_context_path(paths, "data_vendor", "/data/vendor");
    print_context_path(paths, "data_vendor_wifi", "/data/vendor/wifi");
    print_context_path(paths, "data_vendor_wifi_sockets", "/data/vendor/wifi/sockets");
    print_context_path(paths, "ld_config", "/linkerconfig/ld.config.txt");
    print_context_path(paths, "apex_libraries", "/linkerconfig/apex.libraries.config.txt");
    print_context_path(paths, "apex_runtime", "/apex/com.android.runtime");
    print_context_path(paths, "apex_vndk_v30", "/apex/com.android.vndk.v30");
    print_context_path(paths, "apex_vndk_v30_libcutils", "/apex/com.android.vndk.v30/lib64/libcutils.so");
    print_context_path(paths, "apex_vndk_v30_wifi_1_0", "/apex/com.android.vndk.v30/lib64/android.hardware.wifi@1.0.so");
    print_context_path(paths, "apex_vndk_current", "/apex/com.android.vndk.current");
    print_context_path(paths, "apex_vndk_current_libcutils", "/apex/com.android.vndk.current/lib64/libcutils.so");
    print_context_path(paths, "system_lib64", "/system/lib64");
    print_context_path(paths, "vendor_lib64", "/vendor/lib64");
    print_context_path(paths, "system_ext_apex_vndk_v30", "/system/system_ext/apex/com.android.vndk.v30");
    print_context_path(paths, "plat_service_contexts", "/system/etc/selinux/plat_service_contexts");
    print_context_path(paths, "plat_hwservice_contexts", "/system/etc/selinux/plat_hwservice_contexts");
    print_context_path(paths, "system_ext_service_contexts", "/system/system_ext/etc/selinux/system_ext_service_contexts");
    print_context_path(paths, "system_ext_hwservice_contexts", "/system/system_ext/etc/selinux/system_ext_hwservice_contexts");
    print_context_path(paths, "vendor_service_contexts", "/vendor/etc/selinux/vendor_service_contexts");
    print_context_path(paths, "vendor_hwservice_contexts", "/vendor/etc/selinux/vendor_hwservice_contexts");
    print_context_path(paths, "proc_self_exe", "/proc/self/exe");
}

static void apply_child_env(const struct config *cfg) {
    clearenv();
    setenv("PATH", "/system/bin:/vendor/bin:/bin", 1);
    setenv("ANDROID_ROOT", "/system", 1);
    setenv("ANDROID_DATA", "/data", 1);
    if (streq(cfg->env_mode, "ld-debug-1")) {
        setenv("LD_DEBUG", "1", 1);
    } else if (streq(cfg->env_mode, "ld-debug-2")) {
        setenv("LD_DEBUG", "2", 1);
    } else if (streq(cfg->env_mode, "auxv")) {
        setenv("LD_SHOW_AUXV", "1", 1);
    }
}

static unsigned int cap_word(int cap) {
    return (unsigned int)cap / 32U;
}

static unsigned int cap_bit(int cap) {
    return 1U << ((unsigned int)cap % 32U);
}

static int capget_current(struct __user_cap_data_struct data[2]) {
    struct __user_cap_header_struct header;

    memset(&header, 0, sizeof(header));
    memset(data, 0, sizeof(struct __user_cap_data_struct) * 2U);
    header.version = _LINUX_CAPABILITY_VERSION_3;
    header.pid = 0;
    return (int)syscall(SYS_capget, &header, data);
}

static int capset_current(const struct __user_cap_data_struct data[2]) {
    struct __user_cap_header_struct header;

    memset(&header, 0, sizeof(header));
    header.version = _LINUX_CAPABILITY_VERSION_3;
    header.pid = 0;
    return (int)syscall(SYS_capset, &header, data);
}

static bool cap_data_has(const struct __user_cap_data_struct data[2],
                         const char *field,
                         int cap) {
    unsigned int word = cap_word(cap);
    unsigned int bit = cap_bit(cap);

    if (word >= 2U) {
        return false;
    }
    if (strcmp(field, "effective") == 0) {
        return (data[word].effective & bit) != 0;
    }
    if (strcmp(field, "permitted") == 0) {
        return (data[word].permitted & bit) != 0;
    }
    if (strcmp(field, "inheritable") == 0) {
        return (data[word].inheritable & bit) != 0;
    }
    return false;
}

static void print_cap_net_admin(const char *prefix) {
    struct __user_cap_data_struct data[2];

    if (capget_current(data) < 0) {
        printf("%s.capget.error=%s\n", prefix, strerror(errno));
        return;
    }
    printf("%s.cap.net_admin.effective=%d\n",
           prefix,
           cap_data_has(data, "effective", CAP_NET_ADMIN) ? 1 : 0);
    printf("%s.cap.net_admin.permitted=%d\n",
           prefix,
           cap_data_has(data, "permitted", CAP_NET_ADMIN) ? 1 : 0);
    printf("%s.cap.net_admin.inheritable=%d\n",
           prefix,
           cap_data_has(data, "inheritable", CAP_NET_ADMIN) ? 1 : 0);
}

static bool groups_contain(const gid_t *groups, int count, gid_t expected) {
    for (int i = 0; i < count; i++) {
        if (groups[i] == expected) {
            return true;
        }
    }
    return false;
}

static void sanitize_selinux_attr_value(char *value) {
    for (size_t i = 0; value[i] != '\0'; i++) {
        unsigned char ch = (unsigned char)value[i];

        if (ch == '\n' || ch == '\r') {
            value[i] = '\0';
            return;
        }
        if (ch < 0x20 || ch > 0x7e) {
            value[i] = '?';
        }
    }
}

static int self_selinux_attr_path(char *path, size_t path_size, const char *attr) {
    long tid = (long)syscall(SYS_gettid);

    if (snprintf(path, path_size, "/proc/self/task/%ld/attr/%s", tid, attr) >= (int)path_size) {
        errno = ENAMETOOLONG;
        return -1;
    }
    return 0;
}

static int read_selinux_attr(const char *attr, char *out, size_t out_size) {
    char path[96];
    int fd;
    ssize_t nread;

    if (self_selinux_attr_path(path, sizeof(path), attr) < 0) {
        return -1;
    }
    fd = open(path, O_RDONLY | O_CLOEXEC);
    if (fd < 0) {
        return -1;
    }
    nread = read(fd, out, out_size - 1);
    close(fd);
    if (nread < 0) {
        return -1;
    }
    out[nread] = '\0';
    sanitize_selinux_attr_value(out);
    return 0;
}

static void print_selinux_attr_snapshot(const char *prefix) {
    char value[256];

    if (read_selinux_attr("current", value, sizeof(value)) < 0) {
        printf("%s.selinux.current.error=%s\n", prefix, strerror(errno));
    } else {
        printf("%s.selinux.current=%s\n", prefix, value);
    }
    if (read_selinux_attr("exec", value, sizeof(value)) < 0) {
        printf("%s.selinux.exec.error=%s\n", prefix, strerror(errno));
    } else {
        printf("%s.selinux.exec=%s\n", prefix, value);
    }
}

static int run_selinux_print_current_early(void) {
    char value[256];

    if (read_selinux_attr("current", value, sizeof(value)) < 0) {
        printf("selinux_postexec_static.current.error=%s\n", strerror(errno));
        return 126;
    }
    printf("selinux_postexec_static.current=%s\n", value);
    return 0;
}

static int write_selinux_attr(const char *attr, const char *context) {
    char path[96];
    int fd;
    size_t len = strlen(context) + 1U;
    ssize_t nwritten;

    if (self_selinux_attr_path(path, sizeof(path), attr) < 0) {
        return -1;
    }
    fd = open(path, O_WRONLY | O_CLOEXEC);
    if (fd < 0) {
        return -1;
    }
    nwritten = write(fd, context, len);
    if (nwritten < 0 || (size_t)nwritten != len) {
        int saved_errno = nwritten < 0 ? errno : EIO;

        close(fd);
        errno = saved_errno;
        return -1;
    }
    if (close(fd) < 0) {
        return -1;
    }
    return 0;
}

static const char *android_default_selinux_context_for_target(const char *target) {
    if (streq(target, "/system/bin/servicemanager")) {
        return "u:r:servicemanager:s0";
    }
    if (streq(target, "/system/bin/hwservicemanager")) {
        return "u:r:hwservicemanager:s0";
    }
    if (streq(target, "/system/bin/wificond")) {
        return "u:r:wificond:s0";
    }
    if (streq(target, "/vendor/bin/vndservicemanager")) {
        return "u:r:vndservicemanager:s0";
    }
    if (streq(target, "/vendor/bin/hw/vendor.samsung.hardware.wifi@2.0-service") ||
        streq(target, "/vendor/bin/hw/android.hardware.wifi@1.0-service")) {
        return "u:r:hal_wifi_default:s0";
    }
    if (streq(target, "/vendor/bin/cnss-daemon") ||
        streq(target, "/vendor/bin/cnss_diag")) {
        return "u:r:vendor_wcnss_service:s0";
    }
    if (streq(target, "/vendor/bin/qrtr-ns")) {
        return "u:r:vendor_qrtr:s0";
    }
    if (streq(target, "/vendor/bin/rmt_storage")) {
        return "u:r:vendor_rmt_storage:s0";
    }
    if (streq(target, "/vendor/bin/tftp_server")) {
        return "u:r:vendor_rfs_access:s0";
    }
    if (streq(target, "/vendor/bin/pd-mapper")) {
        return "u:r:vendor_pd_mapper:s0";
    }
    if (streq(target, "/vendor/bin/pm-service") ||
        streq(target, "/vendor/bin/pm-proxy")) {
        return "u:r:vendor_per_mgr:s0";
    }
    if (streq(target, "/vendor/bin/pm_proxy_helper")) {
        return "u:r:per_proxy_helper:s0";
    }
    return NULL;
}

static int apply_android_exec_selinux_context_if_requested(const struct config *cfg,
                                                          const char *prefix,
                                                          const char *target) {
    const char *context;

    printf("%s.selinux_context_mode=%s\n", prefix, cfg->android_selinux_context_mode);
    if (streq(cfg->android_selinux_context_mode, "none")) {
        printf("%s.selinux_exec.skipped=1\n", prefix);
        printf("%s.selinux_exec.reason=context-mode-none\n", prefix);
        return 0;
    }
    context = android_default_selinux_context_for_target(target);
    if (context == NULL) {
        printf("%s.selinux_exec.skipped=1\n", prefix);
        printf("%s.selinux_exec.reason=no-default-context-for-target\n", prefix);
        return 0;
    }
    printf("%s.selinux_exec.target_context=%s\n", prefix, context);
    errno = 0;
    if (write_selinux_attr("exec", context) < 0) {
        printf("%s.selinux_exec.ok=0\n", prefix);
        printf("%s.selinux_exec.errno=%d\n", prefix, errno);
        printf("%s.selinux_exec.error=%s\n", prefix, strerror(errno));
        return -1;
    }
    printf("%s.selinux_exec.ok=1\n", prefix);
    printf("%s.selinux_exec.errno=0\n", prefix);
    print_selinux_attr_snapshot(prefix);
    return 0;
}

static bool run_selinux_postexec_current_probe(const char *prefix, const char *context) {
    int pipefd[2] = {-1, -1};
    char value[256];
    size_t len = 0;
    pid_t pid;
    int status = 0;
    bool match = false;

    memset(value, 0, sizeof(value));
    if (pipe2(pipefd, O_CLOEXEC) < 0) {
        printf("%s.postexec.pipe.error=%s\n", prefix, strerror(errno));
        return false;
    }
    pid = fork();
    if (pid < 0) {
        printf("%s.postexec.fork.error=%s\n", prefix, strerror(errno));
        close(pipefd[0]);
        close(pipefd[1]);
        return false;
    }
    if (pid == 0) {
        char *const print_argv[] = {
            (char *)"/proc/self/exe",
            (char *)"--selinux-print-current",
            NULL,
        };

        close(pipefd[0]);
        dup2(pipefd[1], STDOUT_FILENO);
        close(pipefd[1]);
        if (write_selinux_attr("exec", context) < 0) {
            printf("setexec_error=%s\n", strerror(errno));
            fflush(stdout);
            _exit(126);
        }
        execv("/proc/self/exe", print_argv);
        printf("exec_error=%s\n", strerror(errno));
        fflush(stdout);
        _exit(127);
    }
    close(pipefd[1]);
    pipefd[1] = -1;
    while (len + 1U < sizeof(value)) {
        ssize_t nread = read(pipefd[0], value + len, sizeof(value) - len - 1U);

        if (nread < 0) {
            if (errno == EINTR) {
                continue;
            }
            printf("%s.postexec.read.error=%s\n", prefix, strerror(errno));
            break;
        }
        if (nread == 0) {
            break;
        }
        len += (size_t)nread;
    }
    close(pipefd[0]);
    value[len] = '\0';
    sanitize_selinux_attr_value(value);
    printf("%s.postexec.raw=%s\n", prefix, value);
    {
        const char *current_key = "selinux_postexec_static.current=";
        char *current = strstr(value, current_key);

        if (current != NULL) {
            current += strlen(current_key);
            memmove(value, current, strlen(current) + 1U);
        }
    }
    if (waitpid(pid, &status, 0) < 0) {
        printf("%s.postexec.wait.error=%s\n", prefix, strerror(errno));
    }
    printf("%s.postexec.current=%s\n", prefix, value);
    if (WIFEXITED(status)) {
        printf("%s.postexec.exit_code=%d\n", prefix, WEXITSTATUS(status));
    } else if (WIFSIGNALED(status)) {
        printf("%s.postexec.signal=%d\n", prefix, WTERMSIG(status));
    }
    match = streq(value, context) && WIFEXITED(status) && WEXITSTATUS(status) == 0;
    printf("%s.postexec.match=%d\n", prefix, match ? 1 : 0);
    return match;
}

static int print_identity_snapshot(const char *prefix) {
    uid_t ruid = (uid_t)-1;
    uid_t euid = (uid_t)-1;
    uid_t suid = (uid_t)-1;
    gid_t rgid = (gid_t)-1;
    gid_t egid = (gid_t)-1;
    gid_t sgid = (gid_t)-1;
    gid_t groups[32];
    int group_count;

    if (getresuid(&ruid, &euid, &suid) < 0) {
        printf("%s.getresuid.error=%s\n", prefix, strerror(errno));
        return -1;
    }
    if (getresgid(&rgid, &egid, &sgid) < 0) {
        printf("%s.getresgid.error=%s\n", prefix, strerror(errno));
        return -1;
    }
    group_count = getgroups((int)(sizeof(groups) / sizeof(groups[0])), groups);
    if (group_count < 0) {
        printf("%s.getgroups.error=%s\n", prefix, strerror(errno));
        return -1;
    }
    printf("%s.uid.real=%ld\n", prefix, (long)ruid);
    printf("%s.uid.effective=%ld\n", prefix, (long)euid);
    printf("%s.uid.saved=%ld\n", prefix, (long)suid);
    printf("%s.gid.real=%ld\n", prefix, (long)rgid);
    printf("%s.gid.effective=%ld\n", prefix, (long)egid);
    printf("%s.gid.saved=%ld\n", prefix, (long)sgid);
    printf("%s.groups.count=%d\n", prefix, group_count);
    printf("%s.groups.values=", prefix);
    for (int i = 0; i < group_count; i++) {
        printf("%s%ld", i == 0 ? "" : ",", (long)groups[i]);
    }
    printf("\n");
    printf("%s.groups.has_inet=%d\n",
           prefix,
           groups_contain(groups, group_count, A90_AID_INET) ? 1 : 0);
    printf("%s.groups.has_net_admin=%d\n",
           prefix,
           groups_contain(groups, group_count, A90_AID_NET_ADMIN) ? 1 : 0);
    printf("%s.groups.has_wifi=%d\n",
           prefix,
           groups_contain(groups, group_count, A90_AID_WIFI) ? 1 : 0);
    printf("%s.groups.has_readproc=%d\n",
           prefix,
           groups_contain(groups, group_count, A90_AID_READPROC) ? 1 : 0);
    print_selinux_attr_snapshot(prefix);
    print_cap_net_admin(prefix);
    return 0;
}

static int ensure_net_admin_inheritable_before_drop(void) {
    struct __user_cap_data_struct data[2];
    unsigned int word = cap_word(CAP_NET_ADMIN);
    unsigned int bit = cap_bit(CAP_NET_ADMIN);

    if (capget_current(data) < 0) {
        return -1;
    }
    if (word >= 2U) {
        errno = EINVAL;
        return -1;
    }
    data[word].inheritable |= bit;
    return capset_current(data);
}

static int restrict_to_net_admin_capability(void) {
    struct __user_cap_data_struct data[2];
    unsigned int word = cap_word(CAP_NET_ADMIN);
    unsigned int bit = cap_bit(CAP_NET_ADMIN);

    memset(data, 0, sizeof(data));
    if (word >= 2U) {
        errno = EINVAL;
        return -1;
    }
    data[word].effective = bit;
    data[word].permitted = bit;
    data[word].inheritable = bit;
    return capset_current(data);
}

static int ensure_capabilities_inheritable_before_drop(const int *caps, size_t cap_count) {
    struct __user_cap_data_struct data[2];

    if (capget_current(data) < 0) {
        return -1;
    }
    for (size_t i = 0; i < cap_count; i++) {
        unsigned int word = cap_word(caps[i]);
        unsigned int bit = cap_bit(caps[i]);

        if (word >= 2U) {
            errno = EINVAL;
            return -1;
        }
        data[word].inheritable |= bit;
    }
    return capset_current(data);
}

static int restrict_to_capabilities(const int *caps, size_t cap_count) {
    struct __user_cap_data_struct data[2];

    memset(data, 0, sizeof(data));
    for (size_t i = 0; i < cap_count; i++) {
        unsigned int word = cap_word(caps[i]);
        unsigned int bit = cap_bit(caps[i]);

        if (word >= 2U) {
            errno = EINVAL;
            return -1;
        }
        data[word].effective |= bit;
        data[word].permitted |= bit;
        data[word].inheritable |= bit;
    }
    return capset_current(data);
}

static int raise_ambient_capability_report(const char *prefix, int cap, const char *name) {
    int rc;

    errno = 0;
    rc = prctl(PR_CAP_AMBIENT, PR_CAP_AMBIENT_RAISE, cap, 0, 0);
    if (rc < 0) {
        printf("%s.ambient_raise.%s.error=%s\n", prefix, name, strerror(errno));
    } else {
        printf("%s.ambient_raise.%s.ok=1\n", prefix, name);
    }
    printf("%s.ambient_raise.%s.rc=%d\n", prefix, name, rc);
    printf("%s.ambient_raise.%s.errno=%d\n", prefix, name, rc < 0 ? errno : 0);
    return rc;
}

static int apply_android_identity_contract(const char *prefix) {
    gid_t groups[] = {A90_AID_INET, A90_AID_NET_ADMIN, A90_AID_WIFI};
    int ambient_rc;
    bool pass = true;

    printf("%s.expected.uid=%d\n", prefix, A90_AID_SYSTEM);
    printf("%s.expected.gid=%d\n", prefix, A90_AID_SYSTEM);
    printf("%s.expected.groups=%d,%d,%d\n",
           prefix,
           A90_AID_INET,
           A90_AID_NET_ADMIN,
           A90_AID_WIFI);
    printf("%s.expected.cap=CAP_NET_ADMIN\n", prefix);
    if (print_identity_snapshot("cnss.identity.before") < 0) {
        pass = false;
    }
    if (setgroups((int)(sizeof(groups) / sizeof(groups[0])), groups) < 0) {
        printf("%s.setgroups.error=%s\n", prefix, strerror(errno));
        pass = false;
    } else {
        printf("%s.setgroups.ok=1\n", prefix);
    }
    if (prctl(PR_SET_KEEPCAPS, 1, 0, 0, 0) < 0) {
        printf("%s.pr_set_keepcaps.error=%s\n", prefix, strerror(errno));
        pass = false;
    } else {
        printf("%s.pr_set_keepcaps.ok=1\n", prefix);
    }
    if (ensure_net_admin_inheritable_before_drop() < 0) {
        printf("%s.pre_drop_inheritable.error=%s\n", prefix, strerror(errno));
        pass = false;
    } else {
        printf("%s.pre_drop_inheritable.ok=1\n", prefix);
    }
    if (setresgid(A90_AID_SYSTEM, A90_AID_SYSTEM, A90_AID_SYSTEM) < 0) {
        printf("%s.setresgid.error=%s\n", prefix, strerror(errno));
        pass = false;
    } else {
        printf("%s.setresgid.ok=1\n", prefix);
    }
    if (setresuid(A90_AID_SYSTEM, A90_AID_SYSTEM, A90_AID_SYSTEM) < 0) {
        printf("%s.setresuid.error=%s\n", prefix, strerror(errno));
        pass = false;
    } else {
        printf("%s.setresuid.ok=1\n", prefix);
    }
    if (restrict_to_net_admin_capability() < 0) {
        printf("%s.capset_net_admin.error=%s\n", prefix, strerror(errno));
        pass = false;
    } else {
        printf("%s.capset_net_admin.ok=1\n", prefix);
    }
    errno = 0;
    ambient_rc = prctl(PR_CAP_AMBIENT, PR_CAP_AMBIENT_RAISE, CAP_NET_ADMIN, 0, 0);
    if (ambient_rc < 0) {
        printf("%s.ambient_raise.error=%s\n", prefix, strerror(errno));
        pass = false;
    } else {
        printf("%s.ambient_raise.ok=1\n", prefix);
    }
    printf("%s.ambient_raise.rc=%d\n", prefix, ambient_rc);
    printf("%s.ambient_raise.errno=%d\n", prefix, ambient_rc < 0 ? errno : 0);
    if (print_identity_snapshot("cnss.identity.after") < 0) {
        pass = false;
    }
    printf("%s.preexec_status=%s\n", prefix, pass ? "pass" : "fail");
    return pass ? 0 : -1;
}

static int apply_cnss_diag_identity_contract(const char *prefix) {
    gid_t groups[] = {
        A90_AID_SYSTEM,
        A90_AID_WIFI,
        A90_AID_INET,
        A90_AID_SDCARD_RW,
        A90_AID_MEDIA_RW,
        A90_AID_DIAG,
    };
    bool pass = true;

    printf("%s.expected.uid=%d\n", prefix, A90_AID_SYSTEM);
    printf("%s.expected.gid=%d\n", prefix, A90_AID_SYSTEM);
    printf("%s.expected.groups=%d,%d,%d,%d,%d,%d\n",
           prefix,
           A90_AID_SYSTEM,
           A90_AID_WIFI,
           A90_AID_INET,
           A90_AID_SDCARD_RW,
           A90_AID_MEDIA_RW,
           A90_AID_DIAG);
    printf("%s.expected.cap=none\n", prefix);
    if (print_identity_snapshot("cnss_diag.identity.before") < 0) {
        pass = false;
    }
    if (setgroups((int)(sizeof(groups) / sizeof(groups[0])), groups) < 0) {
        printf("%s.setgroups.error=%s\n", prefix, strerror(errno));
        pass = false;
    } else {
        printf("%s.setgroups.ok=1\n", prefix);
    }
    if (setresgid(A90_AID_SYSTEM, A90_AID_SYSTEM, A90_AID_SYSTEM) < 0) {
        printf("%s.setresgid.error=%s\n", prefix, strerror(errno));
        pass = false;
    } else {
        printf("%s.setresgid.ok=1\n", prefix);
    }
    if (setresuid(A90_AID_SYSTEM, A90_AID_SYSTEM, A90_AID_SYSTEM) < 0) {
        printf("%s.setresuid.error=%s\n", prefix, strerror(errno));
        pass = false;
    } else {
        printf("%s.setresuid.ok=1\n", prefix);
    }
    if (restrict_to_capabilities(NULL, 0) < 0) {
        printf("%s.capset_empty.error=%s\n", prefix, strerror(errno));
        pass = false;
    } else {
        printf("%s.capset_empty.ok=1\n", prefix);
    }
    if (print_identity_snapshot("cnss_diag.identity.after") < 0) {
        pass = false;
    }
    printf("%s.preexec_status=%s\n", prefix, pass ? "pass" : "fail");
    return pass ? 0 : -1;
}

static int apply_companion_identity_contract(const char *prefix,
                                             const char *label,
                                             uid_t uid,
                                             gid_t gid,
                                             const gid_t *groups,
                                             size_t group_count,
                                             const int *caps,
                                             size_t cap_count,
                                             bool raise_ambient) {
    bool pass = true;

    printf("%s.expected.contract=%s\n", prefix, label);
    printf("%s.expected.uid=%ld\n", prefix, (long)uid);
    printf("%s.expected.gid=%ld\n", prefix, (long)gid);
    printf("%s.expected.groups=", prefix);
    for (size_t group_index = 0; group_index < group_count; group_index++) {
        printf("%s%ld", group_index == 0 ? "" : ",", (long)groups[group_index]);
    }
    printf("\n");
    printf("%s.expected.cap_count=%zu\n", prefix, cap_count);
    printf("%s.expected.ambient=%d\n", prefix, raise_ambient ? 1 : 0);
    if (print_identity_snapshot("companion.identity.before") < 0) {
        pass = false;
    }
    if (setgroups((int)group_count, group_count == 0 ? NULL : groups) < 0) {
        printf("%s.setgroups.error=%s\n", prefix, strerror(errno));
        pass = false;
    } else {
        printf("%s.setgroups.ok=1\n", prefix);
    }
    if (cap_count > 0) {
        if (prctl(PR_SET_KEEPCAPS, 1, 0, 0, 0) < 0) {
            printf("%s.pr_set_keepcaps.error=%s\n", prefix, strerror(errno));
            pass = false;
        } else {
            printf("%s.pr_set_keepcaps.ok=1\n", prefix);
        }
        if (ensure_capabilities_inheritable_before_drop(caps, cap_count) < 0) {
            printf("%s.pre_drop_inheritable.error=%s\n", prefix, strerror(errno));
            pass = false;
        } else {
            printf("%s.pre_drop_inheritable.ok=1\n", prefix);
        }
    }
    if (setresgid(gid, gid, gid) < 0) {
        printf("%s.setresgid.error=%s\n", prefix, strerror(errno));
        pass = false;
    } else {
        printf("%s.setresgid.ok=1\n", prefix);
    }
    if (setresuid(uid, uid, uid) < 0) {
        printf("%s.setresuid.error=%s\n", prefix, strerror(errno));
        pass = false;
    } else {
        printf("%s.setresuid.ok=1\n", prefix);
    }
    if (restrict_to_capabilities(caps, cap_count) < 0) {
        printf("%s.capset.error=%s\n", prefix, strerror(errno));
        pass = false;
    } else {
        printf("%s.capset.ok=1\n", prefix);
    }
    if (raise_ambient) {
        for (size_t cap_index = 0; cap_index < cap_count; cap_index++) {
            char cap_name[32];

            snprintf(cap_name, sizeof(cap_name), "cap%d", caps[cap_index]);
            if (raise_ambient_capability_report(prefix, caps[cap_index], cap_name) < 0) {
                pass = false;
            }
        }
    }
    if (print_identity_snapshot("companion.identity.after") < 0) {
        pass = false;
    }
    printf("%s.preexec_status=%s\n", prefix, pass ? "pass" : "fail");
    return pass ? 0 : -1;
}

static int apply_qrtr_ns_identity_contract(const char *prefix) {
    int caps[] = {CAP_NET_BIND_SERVICE};

    return apply_companion_identity_contract(prefix,
                                             "qrtr-ns",
                                             A90_AID_VENDOR_QRTR,
                                             A90_AID_VENDOR_QRTR,
                                             NULL,
                                             0,
                                             caps,
                                             sizeof(caps) / sizeof(caps[0]),
                                             true);
}

static int apply_android_init_root_identity_contract(const char *prefix,
                                                     const char *label) {
    bool pass = true;

    printf("%s.expected.contract=%s\n", prefix, label);
    printf("%s.expected.init_rc_user=root\n", prefix);
    printf("%s.expected.uid=0\n", prefix);
    printf("%s.expected.gid=0\n", prefix);
    printf("%s.expected.groups=\n", prefix);
    printf("%s.expected.capability_mode=android-init-root\n", prefix);
    if (print_identity_snapshot("companion.identity.before") < 0) {
        pass = false;
    }
    if (setgroups(0, NULL) < 0) {
        printf("%s.setgroups.error=%s\n", prefix, strerror(errno));
        pass = false;
    } else {
        printf("%s.setgroups.ok=1\n", prefix);
    }
    if (setresgid(0, 0, 0) < 0) {
        printf("%s.setresgid.error=%s\n", prefix, strerror(errno));
        pass = false;
    } else {
        printf("%s.setresgid.ok=1\n", prefix);
    }
    if (setresuid(0, 0, 0) < 0) {
        printf("%s.setresuid.error=%s\n", prefix, strerror(errno));
        pass = false;
    } else {
        printf("%s.setresuid.ok=1\n", prefix);
    }
    if (print_identity_snapshot("companion.identity.after") < 0) {
        pass = false;
    }
    printf("%s.preexec_status=%s\n", prefix, pass ? "pass" : "fail");
    return pass ? 0 : -1;
}

static int apply_rmt_storage_identity_contract(const char *prefix) {
    return apply_android_init_root_identity_contract(prefix, "rmt_storage-init-root");
}

static int apply_tftp_server_identity_contract(const char *prefix) {
    return apply_android_init_root_identity_contract(prefix, "tftp_server-init-root");
}

static int apply_pd_mapper_identity_contract(const char *prefix) {
    int caps[] = {CAP_NET_BIND_SERVICE};

    return apply_companion_identity_contract(prefix,
                                             "pd-mapper",
                                             A90_AID_SYSTEM,
                                             A90_AID_SYSTEM,
                                             NULL,
                                             0,
                                             caps,
                                             sizeof(caps) / sizeof(caps[0]),
                                             true);
}

static int apply_mdm_helper_identity_contract(const char *prefix) {
    gid_t groups[] = {A90_AID_SYSTEM, A90_AID_WAKELOCK, A90_AID_SHELL};

    return apply_companion_identity_contract(prefix,
                                             "mdm-helper",
                                             0,
                                             A90_AID_SYSTEM,
                                             groups,
                                             sizeof(groups) / sizeof(groups[0]),
                                             NULL,
                                             0,
                                             false);
}

static int apply_peripheral_manager_identity_contract(const char *prefix) {
    return apply_companion_identity_contract(prefix,
                                             "peripheral-manager",
                                             A90_AID_SYSTEM,
                                             A90_AID_SYSTEM,
                                             NULL,
                                             0,
                                             NULL,
                                             0,
                                             false);
}

static int apply_peripheral_manager_ioprio_rt4_contract(const char *prefix) {
#ifdef SYS_ioprio_set
    const int priority = IOPRIO_PRIO_VALUE(IOPRIO_CLASS_RT, 4);
    long rc;

    errno = 0;
    rc = syscall(SYS_ioprio_set, IOPRIO_WHO_PROCESS, 0, priority);
    printf("%s.ioprio.class=rt\n", prefix);
    printf("%s.ioprio.priority=4\n", prefix);
    printf("%s.ioprio.ok=%d\n", prefix, rc == 0 ? 1 : 0);
    printf("%s.ioprio.errno=%d\n", prefix, rc == 0 ? 0 : errno);
    if (rc != 0) {
        printf("%s.ioprio.error=%s\n", prefix, strerror(errno));
    }
#else
    printf("%s.ioprio.class=rt\n", prefix);
    printf("%s.ioprio.priority=4\n", prefix);
    printf("%s.ioprio.ok=0\n", prefix);
    printf("%s.ioprio.errno=%d\n", prefix, ENOSYS);
    printf("%s.ioprio.error=%s\n", prefix, strerror(ENOSYS));
#endif
    return 0;
}

static int apply_wifi_hal_identity_contract(const char *prefix) {
    gid_t groups[] = {A90_AID_WIFI, A90_AID_GPS, A90_AID_NET_RAW, A90_AID_NET_ADMIN};
    int caps[] = {CAP_NET_ADMIN, CAP_NET_RAW};
    bool pass = true;

    printf("%s.expected.uid=%d\n", prefix, A90_AID_WIFI);
    printf("%s.expected.gid=%d\n", prefix, A90_AID_WIFI);
    printf("%s.expected.groups=%d,%d,%d,%d\n",
           prefix,
           A90_AID_WIFI,
           A90_AID_GPS,
           A90_AID_NET_RAW,
           A90_AID_NET_ADMIN);
    printf("%s.expected.cap=CAP_NET_ADMIN,CAP_NET_RAW\n", prefix);
    if (print_identity_snapshot("wifi_hal.identity.before") < 0) {
        pass = false;
    }
    if (setgroups((int)(sizeof(groups) / sizeof(groups[0])), groups) < 0) {
        printf("%s.setgroups.error=%s\n", prefix, strerror(errno));
        pass = false;
    } else {
        printf("%s.setgroups.ok=1\n", prefix);
    }
    if (prctl(PR_SET_KEEPCAPS, 1, 0, 0, 0) < 0) {
        printf("%s.pr_set_keepcaps.error=%s\n", prefix, strerror(errno));
        pass = false;
    } else {
        printf("%s.pr_set_keepcaps.ok=1\n", prefix);
    }
    if (ensure_capabilities_inheritable_before_drop(caps, sizeof(caps) / sizeof(caps[0])) < 0) {
        printf("%s.pre_drop_inheritable.error=%s\n", prefix, strerror(errno));
        pass = false;
    } else {
        printf("%s.pre_drop_inheritable.ok=1\n", prefix);
    }
    if (setresgid(A90_AID_WIFI, A90_AID_WIFI, A90_AID_WIFI) < 0) {
        printf("%s.setresgid.error=%s\n", prefix, strerror(errno));
        pass = false;
    } else {
        printf("%s.setresgid.ok=1\n", prefix);
    }
    if (setresuid(A90_AID_WIFI, A90_AID_WIFI, A90_AID_WIFI) < 0) {
        printf("%s.setresuid.error=%s\n", prefix, strerror(errno));
        pass = false;
    } else {
        printf("%s.setresuid.ok=1\n", prefix);
    }
    if (restrict_to_capabilities(caps, sizeof(caps) / sizeof(caps[0])) < 0) {
        printf("%s.capset_wifi_hal.error=%s\n", prefix, strerror(errno));
        pass = false;
    } else {
        printf("%s.capset_wifi_hal.ok=1\n", prefix);
    }
    if (raise_ambient_capability_report(prefix, CAP_NET_ADMIN, "net_admin") < 0) {
        pass = false;
    }
    if (raise_ambient_capability_report(prefix, CAP_NET_RAW, "net_raw") < 0) {
        pass = false;
    }
    if (print_identity_snapshot("wifi_hal.identity.after") < 0) {
        pass = false;
    }
    printf("%s.preexec_status=%s\n", prefix, pass ? "pass" : "fail");
    return pass ? 0 : -1;
}

static int apply_wificond_identity_contract(const char *prefix) {
    gid_t groups[] = {A90_AID_WIFI, A90_AID_NET_RAW, A90_AID_NET_ADMIN};
    int caps[] = {CAP_NET_RAW, CAP_NET_ADMIN};
    bool pass = true;

    printf("%s.expected.uid=%d\n", prefix, A90_AID_WIFI);
    printf("%s.expected.gid=%d\n", prefix, A90_AID_WIFI);
    printf("%s.expected.groups=%d,%d,%d\n",
           prefix,
           A90_AID_WIFI,
           A90_AID_NET_RAW,
           A90_AID_NET_ADMIN);
    printf("%s.expected.cap=CAP_NET_RAW,CAP_NET_ADMIN\n", prefix);
    if (print_identity_snapshot("wificond.identity.before") < 0) {
        pass = false;
    }
    if (setgroups((int)(sizeof(groups) / sizeof(groups[0])), groups) < 0) {
        printf("%s.setgroups.error=%s\n", prefix, strerror(errno));
        pass = false;
    } else {
        printf("%s.setgroups.ok=1\n", prefix);
    }
    if (prctl(PR_SET_KEEPCAPS, 1, 0, 0, 0) < 0) {
        printf("%s.pr_set_keepcaps.error=%s\n", prefix, strerror(errno));
        pass = false;
    } else {
        printf("%s.pr_set_keepcaps.ok=1\n", prefix);
    }
    if (ensure_capabilities_inheritable_before_drop(caps, sizeof(caps) / sizeof(caps[0])) < 0) {
        printf("%s.pre_drop_inheritable.error=%s\n", prefix, strerror(errno));
        pass = false;
    } else {
        printf("%s.pre_drop_inheritable.ok=1\n", prefix);
    }
    if (setresgid(A90_AID_WIFI, A90_AID_WIFI, A90_AID_WIFI) < 0) {
        printf("%s.setresgid.error=%s\n", prefix, strerror(errno));
        pass = false;
    } else {
        printf("%s.setresgid.ok=1\n", prefix);
    }
    if (setresuid(A90_AID_WIFI, A90_AID_WIFI, A90_AID_WIFI) < 0) {
        printf("%s.setresuid.error=%s\n", prefix, strerror(errno));
        pass = false;
    } else {
        printf("%s.setresuid.ok=1\n", prefix);
    }
    if (restrict_to_capabilities(caps, sizeof(caps) / sizeof(caps[0])) < 0) {
        printf("%s.capset_wificond.error=%s\n", prefix, strerror(errno));
        pass = false;
    } else {
        printf("%s.capset_wificond.ok=1\n", prefix);
    }
    if (raise_ambient_capability_report(prefix, CAP_NET_RAW, "net_raw") < 0) {
        pass = false;
    }
    if (raise_ambient_capability_report(prefix, CAP_NET_ADMIN, "net_admin") < 0) {
        pass = false;
    }
    if (print_identity_snapshot("wificond.identity.after") < 0) {
        pass = false;
    }
    printf("%s.preexec_status=%s\n", prefix, pass ? "pass" : "fail");
    return pass ? 0 : -1;
}

static int apply_service_manager_identity_contract(const char *prefix) {
    gid_t groups[] = {A90_AID_SYSTEM, A90_AID_READPROC};
    bool pass = true;

    printf("%s.expected.uid=%d\n", prefix, A90_AID_SYSTEM);
    printf("%s.expected.gid=%d\n", prefix, A90_AID_SYSTEM);
    printf("%s.expected.groups=%d,%d\n",
           prefix,
           A90_AID_SYSTEM,
           A90_AID_READPROC);
    printf("%s.expected.cap=none\n", prefix);
    if (print_identity_snapshot("service_manager.identity.before") < 0) {
        pass = false;
    }
    if (setgroups((int)(sizeof(groups) / sizeof(groups[0])), groups) < 0) {
        printf("%s.setgroups.error=%s\n", prefix, strerror(errno));
        pass = false;
    } else {
        printf("%s.setgroups.ok=1\n", prefix);
    }
    if (setresgid(A90_AID_SYSTEM, A90_AID_SYSTEM, A90_AID_SYSTEM) < 0) {
        printf("%s.setresgid.error=%s\n", prefix, strerror(errno));
        pass = false;
    } else {
        printf("%s.setresgid.ok=1\n", prefix);
    }
    if (setresuid(A90_AID_SYSTEM, A90_AID_SYSTEM, A90_AID_SYSTEM) < 0) {
        printf("%s.setresuid.error=%s\n", prefix, strerror(errno));
        pass = false;
    } else {
        printf("%s.setresuid.ok=1\n", prefix);
    }
    if (print_identity_snapshot("service_manager.identity.after") < 0) {
        pass = false;
    }
    printf("%s.preexec_status=%s\n", prefix, pass ? "pass" : "fail");
    return pass ? 0 : -1;
}

static int run_identity_probe_child(const struct config *cfg, const struct paths *paths) {
    gid_t groups[] = {A90_AID_INET, A90_AID_NET_ADMIN, A90_AID_WIFI};
    int ambient_rc;
    int ambient_errno = 0;
    bool pass = true;

    if (chroot(paths->root) < 0) {
        perror("chroot");
        return 120;
    }
    if (chdir("/") < 0) {
        perror("chdir");
        return 121;
    }
    apply_child_env(cfg);

    printf("identity_probe.begin=1\n");
    printf("identity_probe.expected.uid=%d\n", A90_AID_SYSTEM);
    printf("identity_probe.expected.gid=%d\n", A90_AID_SYSTEM);
    printf("identity_probe.expected.groups=%d,%d,%d\n",
           A90_AID_INET,
           A90_AID_NET_ADMIN,
           A90_AID_WIFI);
    printf("identity_probe.expected.cap=CAP_NET_ADMIN\n");
    if (print_identity_snapshot("identity.before") < 0) {
        pass = false;
    }
    if (setgroups((int)(sizeof(groups) / sizeof(groups[0])), groups) < 0) {
        printf("identity_probe.setgroups.error=%s\n", strerror(errno));
        pass = false;
    } else {
        printf("identity_probe.setgroups.ok=1\n");
    }
    if (prctl(PR_SET_KEEPCAPS, 1, 0, 0, 0) < 0) {
        printf("identity_probe.pr_set_keepcaps.error=%s\n", strerror(errno));
        pass = false;
    } else {
        printf("identity_probe.pr_set_keepcaps.ok=1\n");
    }
    if (ensure_net_admin_inheritable_before_drop() < 0) {
        printf("identity_probe.pre_drop_inheritable.error=%s\n", strerror(errno));
        pass = false;
    } else {
        printf("identity_probe.pre_drop_inheritable.ok=1\n");
    }
    if (setresgid(A90_AID_SYSTEM, A90_AID_SYSTEM, A90_AID_SYSTEM) < 0) {
        printf("identity_probe.setresgid.error=%s\n", strerror(errno));
        pass = false;
    } else {
        printf("identity_probe.setresgid.ok=1\n");
    }
    if (setresuid(A90_AID_SYSTEM, A90_AID_SYSTEM, A90_AID_SYSTEM) < 0) {
        printf("identity_probe.setresuid.error=%s\n", strerror(errno));
        pass = false;
    } else {
        printf("identity_probe.setresuid.ok=1\n");
    }
    if (restrict_to_net_admin_capability() < 0) {
        printf("identity_probe.capset_net_admin.error=%s\n", strerror(errno));
        pass = false;
    } else {
        printf("identity_probe.capset_net_admin.ok=1\n");
    }
    errno = 0;
    ambient_rc = prctl(PR_CAP_AMBIENT, PR_CAP_AMBIENT_RAISE, CAP_NET_ADMIN, 0, 0);
    if (ambient_rc < 0) {
        ambient_errno = errno;
        printf("identity_probe.ambient_raise.error=%s\n", strerror(errno));
        pass = false;
    } else {
        printf("identity_probe.ambient_raise.ok=1\n");
    }
    printf("identity_probe.ambient_raise.rc=%d\n", ambient_rc);
    printf("identity_probe.ambient_raise.errno=%d\n", ambient_errno);
    if (print_identity_snapshot("identity.after") < 0) {
        pass = false;
    }
    printf("identity_probe.preexec_status=%s\n", pass ? "pass" : "fail");
    printf("identity_probe.exec_target=/system/bin/toybox cat /proc/self/status\n");
    fflush(stdout);
    if (!pass) {
        printf("identity_probe.end=1\n");
        fflush(stdout);
        return 1;
    }
    {
        char *const child_argv[] = {
            (char *)"/system/bin/toybox",
            (char *)"cat",
            (char *)"/proc/self/status",
            NULL,
        };

        execv("/system/bin/toybox", child_argv);
    }
    printf("identity_probe.exec_error=%s\n", strerror(errno));
    printf("identity_probe.end=1\n");
    fflush(stdout);
    return 127;
}

static void proc_path(char *out, size_t out_size, pid_t pid, const char *name) {
    snprintf(out, out_size, "/proc/%ld/%s", (long)pid, name);
}

static void print_proc_link(pid_t pid, const char *label, const char *name) {
    char path[MAX_PATH_LEN];
    char target[MAX_PATH_LEN];
    ssize_t nread;

    proc_path(path, sizeof(path), pid, name);
    nread = readlink(path, target, sizeof(target) - 1);
    if (nread < 0) {
        printf("capture.%s.%s.error=%s\n", label, name, strerror(errno));
        return;
    }
    target[nread] = '\0';
    printf("capture.%s.%s=%s\n", label, name, target);
}

static void print_proc_text(pid_t pid, const char *label, const char *name, size_t limit) {
    char path[MAX_PATH_LEN];
    char buf[4096];
    size_t total = 0;
    bool truncated = false;
    char last_char = '\0';
    int fd;

    proc_path(path, sizeof(path), pid, name);
    printf("A90_EXECNS_CAPTURE_%s_%s_BEGIN path=%s limit=%zu\n", label, name, path, limit);
    fd = open(path, O_RDONLY | O_CLOEXEC);
    if (fd < 0) {
        printf("open-error=%s\n", strerror(errno));
        printf("A90_EXECNS_CAPTURE_%s_%s_END bytes=0 truncated=0\n", label, name);
        return;
    }
    while (total < limit) {
        size_t room = limit - total;
        ssize_t nread = read(fd, buf, room < sizeof(buf) ? room : sizeof(buf));

        if (nread < 0) {
            if (errno == EINTR) {
                continue;
            }
            printf("\nread-error=%s\n", strerror(errno));
            break;
        }
        if (nread == 0) {
            break;
        }
        fwrite(buf, 1, (size_t)nread, stdout);
        last_char = buf[nread - 1];
        total += (size_t)nread;
    }
    if (total >= limit) {
        truncated = true;
    }
    close(fd);
    if (total == 0 || last_char != '\n') {
        putchar('\n');
    }
    printf("A90_EXECNS_CAPTURE_%s_%s_END bytes=%zu truncated=%d\n",
           label,
           name,
           total,
           truncated ? 1 : 0);
}

static void print_proc_auxv(pid_t pid, const char *label) {
    char path[MAX_PATH_LEN];
    struct {
        unsigned long key;
        unsigned long value;
    } item;
    int fd;
    int index = 0;

    proc_path(path, sizeof(path), pid, "auxv");
    fd = open(path, O_RDONLY | O_CLOEXEC);
    if (fd < 0) {
        printf("capture.%s.auxv.error=%s\n", label, strerror(errno));
        return;
    }
    while (read(fd, &item, sizeof(item)) == (ssize_t)sizeof(item)) {
        printf("capture.%s.auxv.%d.type=%lu\n", label, index, item.key);
        printf("capture.%s.auxv.%d.value=0x%lx\n", label, index, item.value);
        index++;
        if (item.key == 0 || index >= 96) {
            break;
        }
    }
    close(fd);
    printf("capture.%s.auxv.count=%d\n", label, index);
}

static void print_ptrace_siginfo(pid_t pid, const char *label) {
    siginfo_t info;

    memset(&info, 0, sizeof(info));
    if (ptrace(PTRACE_GETSIGINFO, pid, NULL, &info) < 0) {
        printf("capture.%s.siginfo.error=%s\n", label, strerror(errno));
        return;
    }
    printf("capture.%s.siginfo.signo=%d\n", label, info.si_signo);
    printf("capture.%s.siginfo.code=%d\n", label, info.si_code);
    printf("capture.%s.siginfo.errno=%d\n", label, info.si_errno);
    printf("capture.%s.siginfo.addr=%p\n", label, info.si_addr);
}

static void print_ptrace_regs(pid_t pid, const char *label) {
    unsigned long long regs[96];
    struct iovec iov;
    size_t words;

    memset(regs, 0, sizeof(regs));
    iov.iov_base = regs;
    iov.iov_len = sizeof(regs);
    if (ptrace(PTRACE_GETREGSET, pid, (void *)(long)NT_PRSTATUS, &iov) < 0) {
        printf("capture.%s.regset.nt_prstatus.error=%s\n", label, strerror(errno));
        return;
    }
    printf("capture.%s.regset.nt_prstatus.bytes=%zu\n", label, iov.iov_len);
    words = iov.iov_len / sizeof(regs[0]);
    if (words > 40) {
        words = 40;
    }
    for (size_t i = 0; i < words; i++) {
        printf("capture.%s.regset.word%02zu=0x%016llx\n", label, i, regs[i]);
    }
}

static void print_capture_snapshot(pid_t pid, const char *label, bool include_maps) {
    printf("capture.%s.pid=%ld\n", label, (long)pid);
    print_proc_link(pid, label, "exe");
    print_proc_link(pid, label, "cwd");
    print_proc_auxv(pid, label);
    print_ptrace_regs(pid, label);
    print_proc_text(pid, label, "status", 8192);
    if (include_maps) {
        print_proc_text(pid, label, "maps", 65536);
        print_proc_text(pid, label, "mountinfo", 65536);
    }
}

static int run_linker_list_ptrace(const struct config *cfg,
                                  const struct paths *paths,
                                  struct buffer *stdout_buf,
                                  struct buffer *stderr_buf,
                                  int *child_exit_code,
                                  int *child_signal,
                                  bool *timed_out);

static int run_linker_list(const struct config *cfg,
                           const struct paths *paths,
                           struct buffer *stdout_buf,
                           struct buffer *stderr_buf,
                           int *child_exit_code,
                           int *child_signal,
                           bool *timed_out) {
    int stdout_pipe[2] = {-1, -1};
    int stderr_pipe[2] = {-1, -1};
    bool stdout_open = true;
    bool stderr_open = true;
    long deadline;
    pid_t pid;
    int status = 0;
    bool child_done = false;

    if (streq(cfg->capture_mode, "ptrace-lite")) {
        return run_linker_list_ptrace(cfg,
                                      paths,
                                      stdout_buf,
                                      stderr_buf,
                                      child_exit_code,
                                      child_signal,
                                      timed_out);
    }

    *child_exit_code = -1;
    *child_signal = 0;
    *timed_out = false;

    if (pipe2(stdout_pipe, O_CLOEXEC) < 0 || pipe2(stderr_pipe, O_CLOEXEC) < 0) {
        perror("pipe2");
        goto fail;
    }
    pid = fork();
    if (pid < 0) {
        perror("fork");
        goto fail;
    }
    if (pid == 0) {
        char *const child_argv[] = {
            (char *)cfg->linker,
            (char *)"--list",
            (char *)cfg->target,
            NULL,
        };

        setpgid(0, 0);
        close(stdout_pipe[0]);
        close(stderr_pipe[0]);
        dup2(stdout_pipe[1], STDOUT_FILENO);
        dup2(stderr_pipe[1], STDERR_FILENO);
        close(stdout_pipe[1]);
        close(stderr_pipe[1]);
        if (chroot(paths->root) < 0) {
            perror("chroot");
            _exit(120);
        }
        if (chdir("/") < 0) {
            perror("chdir");
            _exit(121);
        }
        apply_child_env(cfg);
        execv(cfg->linker, child_argv);
        perror("execv linker");
        _exit(127);
    }

    close(stdout_pipe[1]);
    close(stderr_pipe[1]);
    stdout_pipe[1] = -1;
    stderr_pipe[1] = -1;
    set_nonblock(stdout_pipe[0]);
    set_nonblock(stderr_pipe[0]);
    deadline = monotonic_ms() + cfg->timeout_sec * 1000L;

    while (stdout_open || stderr_open || !child_done) {
        struct pollfd fds[2];
        int nfds = 0;
        int poll_timeout = 100;
        long now = monotonic_ms();

        if (!child_done && now >= deadline) {
            *timed_out = true;
            kill(-pid, SIGKILL);
            kill(pid, SIGKILL);
        }
        if (stdout_open) {
            fds[nfds].fd = stdout_pipe[0];
            fds[nfds].events = POLLIN | POLLHUP | POLLERR;
            nfds++;
        }
        if (stderr_open) {
            fds[nfds].fd = stderr_pipe[0];
            fds[nfds].events = POLLIN | POLLHUP | POLLERR;
            nfds++;
        }
        if (nfds > 0) {
            int rc = poll(fds, nfds, poll_timeout);

            if (rc > 0) {
                int idx = 0;

                if (stdout_open) {
                    if (fds[idx].revents != 0) {
                        drain_fd(stdout_pipe[0], stdout_buf, &stdout_open);
                    }
                    idx++;
                }
                if (stderr_open) {
                    if (fds[idx].revents != 0) {
                        drain_fd(stderr_pipe[0], stderr_buf, &stderr_open);
                    }
                }
            }
        } else {
            usleep(100000);
        }

        if (!child_done) {
            pid_t wait_rc = waitpid(pid, &status, WNOHANG);

            if (wait_rc == pid) {
                child_done = true;
                if (WIFEXITED(status)) {
                    *child_exit_code = WEXITSTATUS(status);
                } else if (WIFSIGNALED(status)) {
                    *child_signal = WTERMSIG(status);
                }
            }
        }
    }
    return 0;

fail:
    if (stdout_pipe[0] >= 0) close(stdout_pipe[0]);
    if (stdout_pipe[1] >= 0) close(stdout_pipe[1]);
    if (stderr_pipe[0] >= 0) close(stderr_pipe[0]);
    if (stderr_pipe[1] >= 0) close(stderr_pipe[1]);
    return -1;
}

static int run_linker_list_ptrace(const struct config *cfg,
                                  const struct paths *paths,
                                  struct buffer *stdout_buf,
                                  struct buffer *stderr_buf,
                                  int *child_exit_code,
                                  int *child_signal,
                                  bool *timed_out) {
    int stdout_pipe[2] = {-1, -1};
    int stderr_pipe[2] = {-1, -1};
    bool stdout_open = true;
    bool stderr_open = true;
    bool child_done = false;
    bool exec_captured = false;
    bool crash_captured = false;
    long deadline;
    pid_t pid;
    int status = 0;

    *child_exit_code = -1;
    *child_signal = 0;
    *timed_out = false;
    printf("capture.mode=ptrace-lite\n");

    if (pipe2(stdout_pipe, O_CLOEXEC) < 0 || pipe2(stderr_pipe, O_CLOEXEC) < 0) {
        perror("pipe2");
        goto fail;
    }
    pid = fork();
    if (pid < 0) {
        perror("fork");
        goto fail;
    }
    if (pid == 0) {
        char *const child_argv[] = {
            (char *)cfg->linker,
            (char *)"--list",
            (char *)cfg->target,
            NULL,
        };

        setpgid(0, 0);
        close(stdout_pipe[0]);
        close(stderr_pipe[0]);
        dup2(stdout_pipe[1], STDOUT_FILENO);
        dup2(stderr_pipe[1], STDERR_FILENO);
        close(stdout_pipe[1]);
        close(stderr_pipe[1]);
        if (ptrace(PTRACE_TRACEME, 0, NULL, NULL) < 0) {
            perror("ptrace-traceme");
            _exit(122);
        }
        raise(SIGSTOP);
        if (chroot(paths->root) < 0) {
            perror("chroot");
            _exit(120);
        }
        if (chdir("/") < 0) {
            perror("chdir");
            _exit(121);
        }
        apply_child_env(cfg);
        execv(cfg->linker, child_argv);
        perror("execv linker");
        _exit(127);
    }

    close(stdout_pipe[1]);
    close(stderr_pipe[1]);
    stdout_pipe[1] = -1;
    stderr_pipe[1] = -1;
    set_nonblock(stdout_pipe[0]);
    set_nonblock(stderr_pipe[0]);

    if (waitpid(pid, &status, 0) != pid) {
        printf("capture.initial_wait.error=%s\n", strerror(errno));
        goto fail;
    }
    if (!WIFSTOPPED(status)) {
        printf("capture.initial_stop.unexpected_status=0x%x\n", status);
        if (WIFEXITED(status)) {
            *child_exit_code = WEXITSTATUS(status);
        } else if (WIFSIGNALED(status)) {
            *child_signal = WTERMSIG(status);
        }
        child_done = true;
    } else {
        printf("capture.initial_stop.signal=%d\n", WSTOPSIG(status));
        if (ptrace(PTRACE_SETOPTIONS,
                   pid,
                   NULL,
                   (void *)(long)(PTRACE_O_TRACEEXEC | PTRACE_O_EXITKILL)) < 0) {
            printf("capture.setoptions.error=%s\n", strerror(errno));
        }
        if (ptrace(PTRACE_CONT, pid, NULL, NULL) < 0) {
            printf("capture.initial_cont.error=%s\n", strerror(errno));
            goto fail;
        }
    }
    deadline = monotonic_ms() + cfg->timeout_sec * 1000L;

    while (stdout_open || stderr_open || !child_done) {
        struct pollfd fds[2];
        int nfds = 0;
        int poll_timeout = 50;
        long now = monotonic_ms();

        if (!child_done && now >= deadline) {
            *timed_out = true;
            printf("capture.timeout.kill=1\n");
            kill(-pid, SIGKILL);
            kill(pid, SIGKILL);
        }
        if (stdout_open) {
            fds[nfds].fd = stdout_pipe[0];
            fds[nfds].events = POLLIN | POLLHUP | POLLERR;
            nfds++;
        }
        if (stderr_open) {
            fds[nfds].fd = stderr_pipe[0];
            fds[nfds].events = POLLIN | POLLHUP | POLLERR;
            nfds++;
        }
        if (nfds > 0) {
            int rc = poll(fds, nfds, poll_timeout);

            if (rc > 0) {
                int idx = 0;

                if (stdout_open) {
                    if (fds[idx].revents != 0) {
                        drain_fd(stdout_pipe[0], stdout_buf, &stdout_open);
                    }
                    idx++;
                }
                if (stderr_open) {
                    if (fds[idx].revents != 0) {
                        drain_fd(stderr_pipe[0], stderr_buf, &stderr_open);
                    }
                }
            }
        } else {
            usleep(50000);
        }

        if (!child_done) {
            pid_t wait_rc = waitpid(pid, &status, WNOHANG);

            if (wait_rc == pid) {
                if (WIFEXITED(status)) {
                    child_done = true;
                    *child_exit_code = WEXITSTATUS(status);
                    printf("capture.child.exit=%d\n", *child_exit_code);
                } else if (WIFSIGNALED(status)) {
                    child_done = true;
                    *child_signal = WTERMSIG(status);
                    printf("capture.child.signal=%d\n", *child_signal);
                } else if (WIFSTOPPED(status)) {
                    int sig = WSTOPSIG(status);
                    unsigned int event = (unsigned int)status >> 16;
                    int deliver_sig = 0;

                    printf("capture.stop.signal=%d\n", sig);
                    printf("capture.stop.event=%u\n", event);
                    if (sig == SIGTRAP && !exec_captured) {
                        exec_captured = true;
                        printf("capture.exec_stop=1\n");
                        print_capture_snapshot(pid, "exec", true);
                    } else if (sig == SIGSEGV || sig == SIGBUS || sig == SIGILL || sig == SIGABRT) {
                        crash_captured = true;
                        printf("capture.crash_stop=1\n");
                        print_ptrace_siginfo(pid, "crash");
                        print_capture_snapshot(pid, "crash", true);
                        deliver_sig = sig;
                    } else if (sig != SIGTRAP) {
                        deliver_sig = sig;
                    }
                    if (ptrace(PTRACE_CONT, pid, NULL, (void *)(long)deliver_sig) < 0) {
                        printf("capture.cont.error=%s\n", strerror(errno));
                        kill(-pid, SIGKILL);
                        kill(pid, SIGKILL);
                    }
                }
            } else if (wait_rc < 0 && errno != EINTR && errno != ECHILD) {
                printf("capture.wait.error=%s\n", strerror(errno));
            }
        }
    }
    printf("capture.exec_captured=%d\n", exec_captured ? 1 : 0);
    printf("capture.crash_captured=%d\n", crash_captured ? 1 : 0);
    return 0;

fail:
    if (stdout_pipe[0] >= 0) close(stdout_pipe[0]);
    if (stdout_pipe[1] >= 0) close(stdout_pipe[1]);
    if (stderr_pipe[0] >= 0) close(stderr_pipe[0]);
    if (stderr_pipe[1] >= 0) close(stderr_pipe[1]);
    return -1;
}

static int run_identity_probe(const struct config *cfg,
                              const struct paths *paths,
                              struct buffer *stdout_buf,
                              struct buffer *stderr_buf,
                              int *child_exit_code,
                              int *child_signal,
                              bool *timed_out) {
    int stdout_pipe[2] = {-1, -1};
    int stderr_pipe[2] = {-1, -1};
    bool stdout_open = true;
    bool stderr_open = true;
    bool child_done = false;
    long deadline;
    pid_t pid;
    int status = 0;

    *child_exit_code = -1;
    *child_signal = 0;
    *timed_out = false;

    if (pipe2(stdout_pipe, O_CLOEXEC) < 0 || pipe2(stderr_pipe, O_CLOEXEC) < 0) {
        perror("pipe2");
        goto fail;
    }
    pid = fork();
    if (pid < 0) {
        perror("fork");
        goto fail;
    }
    if (pid == 0) {
        int rc;

        setpgid(0, 0);
        close(stdout_pipe[0]);
        close(stderr_pipe[0]);
        dup2(stdout_pipe[1], STDOUT_FILENO);
        dup2(stderr_pipe[1], STDERR_FILENO);
        close(stdout_pipe[1]);
        close(stderr_pipe[1]);
        rc = run_identity_probe_child(cfg, paths);
        _exit(rc);
    }

    close(stdout_pipe[1]);
    close(stderr_pipe[1]);
    stdout_pipe[1] = -1;
    stderr_pipe[1] = -1;
    set_nonblock(stdout_pipe[0]);
    set_nonblock(stderr_pipe[0]);
    deadline = monotonic_ms() + cfg->timeout_sec * 1000L;

    while (stdout_open || stderr_open || !child_done) {
        struct pollfd fds[2];
        int nfds = 0;
        int poll_timeout = 50;
        long now = monotonic_ms();

        if (!child_done && now >= deadline) {
            *timed_out = true;
            kill(-pid, SIGKILL);
            kill(pid, SIGKILL);
        }
        if (stdout_open) {
            fds[nfds].fd = stdout_pipe[0];
            fds[nfds].events = POLLIN | POLLHUP | POLLERR;
            nfds++;
        }
        if (stderr_open) {
            fds[nfds].fd = stderr_pipe[0];
            fds[nfds].events = POLLIN | POLLHUP | POLLERR;
            nfds++;
        }
        if (nfds > 0) {
            int rc = poll(fds, nfds, poll_timeout);

            if (rc > 0) {
                int idx = 0;

                if (stdout_open) {
                    if (fds[idx].revents != 0) {
                        drain_fd(stdout_pipe[0], stdout_buf, &stdout_open);
                    }
                    idx++;
                }
                if (stderr_open) {
                    if (fds[idx].revents != 0) {
                        drain_fd(stderr_pipe[0], stderr_buf, &stderr_open);
                    }
                }
            }
        } else {
            usleep(50000);
        }
        if (!child_done) {
            pid_t wait_rc = waitpid(pid, &status, WNOHANG);

            if (wait_rc == pid) {
                child_done = true;
                if (WIFEXITED(status)) {
                    *child_exit_code = WEXITSTATUS(status);
                } else if (WIFSIGNALED(status)) {
                    *child_signal = WTERMSIG(status);
                }
            } else if (wait_rc < 0 && errno != EINTR && errno != ECHILD) {
                printf("identity_probe.wait.error=%s\n", strerror(errno));
                child_done = true;
            }
        }
    }
    return 0;

fail:
    if (stdout_pipe[0] >= 0) close(stdout_pipe[0]);
    if (stdout_pipe[1] >= 0) close(stdout_pipe[1]);
    if (stderr_pipe[0] >= 0) close(stderr_pipe[0]);
    if (stderr_pipe[1] >= 0) close(stderr_pipe[1]);
    return -1;
}

static int run_selinux_domain_proof_child(const struct config *cfg, const struct paths *paths) {
    bool want_current = streq(cfg->selinux_attr_mode, "current") ||
                        streq(cfg->selinux_attr_mode, "both");
    bool want_exec = streq(cfg->selinux_attr_mode, "exec") ||
                     streq(cfg->selinux_attr_mode, "both");
    bool current_ok = !want_current;
    bool exec_ok = !want_exec;
    bool pass;

    if (chroot(paths->root) < 0) {
        printf("selinux_domain_proof.chdir_root.error=%s\n", strerror(errno));
        printf("selinux_domain_proof.end=1\n");
        return 120;
    }
    if (chdir("/") < 0) {
        printf("selinux_domain_proof.chdir.error=%s\n", strerror(errno));
        printf("selinux_domain_proof.end=1\n");
        return 121;
    }
    apply_child_env(cfg);
    printf("selinux_domain_proof.begin=1\n");
    printf("selinux_domain_proof.target_context=%s\n", cfg->selinux_context);
    printf("selinux_domain_proof.attr_mode=%s\n", cfg->selinux_attr_mode);
    printf("selinux_domain_proof.daemon_start_executed=0\n");
    printf("selinux_domain_proof.wifi_hal_start_executed=0\n");
    printf("selinux_domain_proof.scan_connect_linkup=0\n");
    printf("selinux_domain_proof.credentials=0\n");
    print_selinux_attr_snapshot("selinux_domain_proof.before");

    if (want_current) {
        char verify_current[256] = "";

        errno = 0;
        if (write_selinux_attr("current", cfg->selinux_context) < 0) {
            printf("selinux_domain_proof.write_current.ok=0\n");
            printf("selinux_domain_proof.write_current.errno=%d\n", errno);
            printf("selinux_domain_proof.write_current.error=%s\n", strerror(errno));
        } else {
            printf("selinux_domain_proof.write_current.ok=1\n");
            printf("selinux_domain_proof.write_current.errno=0\n");
            if (read_selinux_attr("current", verify_current, sizeof(verify_current)) == 0 &&
                streq(verify_current, cfg->selinux_context)) {
                current_ok = true;
                printf("selinux_domain_proof.verify_current.match=1\n");
            } else {
                printf("selinux_domain_proof.verify_current.match=0\n");
                printf("selinux_domain_proof.verify_current.value=%s\n", verify_current);
            }
        }
        print_selinux_attr_snapshot("selinux_domain_proof.after_current");
    }
    if (want_exec) {
        char verify_exec[256] = "";

        errno = 0;
        if (write_selinux_attr("exec", cfg->selinux_context) < 0) {
            printf("selinux_domain_proof.write_exec.ok=0\n");
            printf("selinux_domain_proof.write_exec.errno=%d\n", errno);
            printf("selinux_domain_proof.write_exec.error=%s\n", strerror(errno));
        } else {
            printf("selinux_domain_proof.write_exec.ok=1\n");
            printf("selinux_domain_proof.write_exec.errno=0\n");
            if (read_selinux_attr("exec", verify_exec, sizeof(verify_exec)) == 0 &&
                streq(verify_exec, cfg->selinux_context)) {
                printf("selinux_domain_proof.verify_exec.match=1\n");
            } else {
                printf("selinux_domain_proof.verify_exec.match=0\n");
                printf("selinux_domain_proof.verify_exec.value=%s\n", verify_exec);
            }
            exec_ok = run_selinux_postexec_current_probe("selinux_domain_proof", cfg->selinux_context);
        }
        print_selinux_attr_snapshot("selinux_domain_proof.after_exec");
    }

    pass = current_ok && exec_ok;
    printf("selinux_domain_proof.result=%s\n",
           pass ? "selinux-domain-setcon-proof-pass" : "selinux-domain-setcon-proof-blocked");
    printf("selinux_domain_proof.reason=%s\n",
           pass ? "requested-selinux-attr-write-and-readback-succeeded" : "requested-selinux-attr-write-or-readback-failed");
    printf("selinux_domain_proof.end=1\n");
    fflush(stdout);
    return pass ? 0 : 1;
}

static int run_selinux_domain_proof(const struct config *cfg,
                                    const struct paths *paths,
                                    struct buffer *stdout_buf,
                                    struct buffer *stderr_buf,
                                    int *child_exit_code,
                                    int *child_signal,
                                    bool *timed_out) {
    int stdout_pipe[2] = {-1, -1};
    int stderr_pipe[2] = {-1, -1};
    bool stdout_open = true;
    bool stderr_open = true;
    bool child_done = false;
    long deadline;
    pid_t pid;
    int status = 0;

    *child_exit_code = -1;
    *child_signal = 0;
    *timed_out = false;

    if (pipe2(stdout_pipe, O_CLOEXEC) < 0 || pipe2(stderr_pipe, O_CLOEXEC) < 0) {
        perror("pipe2");
        goto fail;
    }
    pid = fork();
    if (pid < 0) {
        perror("fork");
        goto fail;
    }
    if (pid == 0) {
        int rc;

        setpgid(0, 0);
        close(stdout_pipe[0]);
        close(stderr_pipe[0]);
        dup2(stdout_pipe[1], STDOUT_FILENO);
        dup2(stderr_pipe[1], STDERR_FILENO);
        close(stdout_pipe[1]);
        close(stderr_pipe[1]);
        rc = run_selinux_domain_proof_child(cfg, paths);
        _exit(rc);
    }

    close(stdout_pipe[1]);
    close(stderr_pipe[1]);
    stdout_pipe[1] = -1;
    stderr_pipe[1] = -1;
    set_nonblock(stdout_pipe[0]);
    set_nonblock(stderr_pipe[0]);
    deadline = monotonic_ms() + cfg->timeout_sec * 1000L;

    while (stdout_open || stderr_open || !child_done) {
        struct pollfd fds[2];
        int nfds = 0;
        long now = monotonic_ms();

        if (!child_done && now >= deadline) {
            *timed_out = true;
            kill(-pid, SIGKILL);
            kill(pid, SIGKILL);
        }
        if (stdout_open) {
            fds[nfds].fd = stdout_pipe[0];
            fds[nfds].events = POLLIN | POLLHUP | POLLERR;
            nfds++;
        }
        if (stderr_open) {
            fds[nfds].fd = stderr_pipe[0];
            fds[nfds].events = POLLIN | POLLHUP | POLLERR;
            nfds++;
        }
        if (nfds > 0) {
            int poll_rc = poll(fds, nfds, 50);

            if (poll_rc > 0) {
                int idx = 0;

                if (stdout_open) {
                    if (fds[idx].revents != 0) {
                        drain_fd(stdout_pipe[0], stdout_buf, &stdout_open);
                    }
                    idx++;
                }
                if (stderr_open && fds[idx].revents != 0) {
                    drain_fd(stderr_pipe[0], stderr_buf, &stderr_open);
                }
            }
        } else {
            usleep(50000);
        }
        if (!child_done) {
            pid_t wait_rc = waitpid(pid, &status, WNOHANG);

            if (wait_rc == pid) {
                child_done = true;
                if (WIFEXITED(status)) {
                    *child_exit_code = WEXITSTATUS(status);
                } else if (WIFSIGNALED(status)) {
                    *child_signal = WTERMSIG(status);
                }
            } else if (wait_rc < 0 && errno != EINTR && errno != ECHILD) {
                fprintf(stderr, "selinux_domain_proof.wait.error=%s\n", strerror(errno));
                child_done = true;
            }
        }
    }
    if (stdout_pipe[0] >= 0) close(stdout_pipe[0]);
    if (stderr_pipe[0] >= 0) close(stderr_pipe[0]);
    return *child_exit_code == 0 && *child_signal == 0 && !*timed_out ? 0 : 1;

fail:
    if (stdout_pipe[0] >= 0) close(stdout_pipe[0]);
    if (stdout_pipe[1] >= 0) close(stdout_pipe[1]);
    if (stderr_pipe[0] >= 0) close(stderr_pipe[0]);
    if (stderr_pipe[1] >= 0) close(stderr_pipe[1]);
    return -1;
}

static int run_property_lookup(const struct config *cfg,
                               const struct paths *paths,
                               struct buffer *stdout_buf,
                               struct buffer *stderr_buf,
                               int *child_exit_code,
                               int *child_signal,
                               bool *timed_out) {
    int stdout_pipe[2] = {-1, -1};
    int stderr_pipe[2] = {-1, -1};
    bool stdout_open = true;
    bool stderr_open = true;
    bool child_done = false;
    long deadline;
    pid_t pid;
    int status = 0;

    *child_exit_code = -1;
    *child_signal = 0;
    *timed_out = false;

    if (pipe2(stdout_pipe, O_CLOEXEC) < 0 || pipe2(stderr_pipe, O_CLOEXEC) < 0) {
        perror("pipe2");
        goto fail;
    }
    pid = fork();
    if (pid < 0) {
        perror("fork");
        goto fail;
    }
    if (pid == 0) {
        char *const child_argv[] = {
            (char *)"/system/bin/getprop",
            (char *)cfg->property_key,
            NULL,
        };

        setpgid(0, 0);
        close(stdout_pipe[0]);
        close(stderr_pipe[0]);
        dup2(stdout_pipe[1], STDOUT_FILENO);
        dup2(stderr_pipe[1], STDERR_FILENO);
        close(stdout_pipe[1]);
        close(stderr_pipe[1]);
        if (chroot(paths->root) < 0) {
            perror("chroot");
            _exit(120);
        }
        if (chdir("/") < 0) {
            perror("chdir");
            _exit(121);
        }
        apply_child_env(cfg);
        execv("/system/bin/getprop", child_argv);
        perror("execv getprop");
        _exit(127);
    }

    close(stdout_pipe[1]);
    close(stderr_pipe[1]);
    stdout_pipe[1] = -1;
    stderr_pipe[1] = -1;
    set_nonblock(stdout_pipe[0]);
    set_nonblock(stderr_pipe[0]);
    deadline = monotonic_ms() + cfg->timeout_sec * 1000L;

    while (stdout_open || stderr_open || !child_done) {
        struct pollfd fds[2];
        int nfds = 0;
        int poll_timeout = 50;
        long now = monotonic_ms();

        if (!child_done && now >= deadline) {
            *timed_out = true;
            kill(-pid, SIGKILL);
            kill(pid, SIGKILL);
        }
        if (stdout_open) {
            fds[nfds].fd = stdout_pipe[0];
            fds[nfds].events = POLLIN | POLLHUP | POLLERR;
            nfds++;
        }
        if (stderr_open) {
            fds[nfds].fd = stderr_pipe[0];
            fds[nfds].events = POLLIN | POLLHUP | POLLERR;
            nfds++;
        }
        if (nfds > 0) {
            int rc = poll(fds, nfds, poll_timeout);

            if (rc > 0) {
                int idx = 0;

                if (stdout_open) {
                    if (fds[idx].revents != 0) {
                        drain_fd(stdout_pipe[0], stdout_buf, &stdout_open);
                    }
                    idx++;
                }
                if (stderr_open) {
                    if (fds[idx].revents != 0) {
                        drain_fd(stderr_pipe[0], stderr_buf, &stderr_open);
                    }
                }
            }
        } else {
            usleep(50000);
        }
        if (!child_done) {
            pid_t wait_rc = waitpid(pid, &status, WNOHANG);

            if (wait_rc == pid) {
                child_done = true;
                if (WIFEXITED(status)) {
                    *child_exit_code = WEXITSTATUS(status);
                } else if (WIFSIGNALED(status)) {
                    *child_signal = WTERMSIG(status);
                }
            } else if (wait_rc < 0 && errno != EINTR && errno != ECHILD) {
                printf("property_lookup.wait.error=%s\n", strerror(errno));
                child_done = true;
            }
        }
    }
    return 0;

fail:
    if (stdout_pipe[0] >= 0) close(stdout_pipe[0]);
    if (stdout_pipe[1] >= 0) close(stdout_pipe[1]);
    if (stderr_pipe[0] >= 0) close(stderr_pipe[0]);
    if (stderr_pipe[1] >= 0) close(stderr_pipe[1]);
    return -1;
}

static int append_literal(struct buffer *buf, const char *text) {
    return buffer_append(buf, text, strlen(text));
}

static int append_format(struct buffer *buf, const char *fmt, ...) {
    char small[1024];
    char *dynamic_buf = NULL;
    va_list ap;
    va_list copy;
    int needed;
    int rc;

    va_start(ap, fmt);
    va_copy(copy, ap);
    needed = vsnprintf(small, sizeof(small), fmt, ap);
    va_end(ap);
    if (needed < 0) {
        va_end(copy);
        return -1;
    }
    if ((size_t)needed < sizeof(small)) {
        va_end(copy);
        return buffer_append(buf, small, (size_t)needed);
    }
    dynamic_buf = malloc((size_t)needed + 1U);
    if (dynamic_buf == NULL) {
        va_end(copy);
        return -1;
    }
    rc = vsnprintf(dynamic_buf, (size_t)needed + 1U, fmt, copy);
    va_end(copy);
    if (rc < 0) {
        free(dynamic_buf);
        return -1;
    }
    rc = buffer_append(buf, dynamic_buf, (size_t)rc);
    free(dynamic_buf);
    return rc;
}

struct sepolicy_inventory_path {
    const char *label;
    const char *path;
};

static void sanitize_one_line(char *value) {
    for (size_t i = 0; value[i] != '\0'; i++) {
        unsigned char ch = (unsigned char)value[i];

        if (ch == '\n' || ch == '\r') {
            value[i] = '\0';
            return;
        }
        if (ch < 0x20 || ch > 0x7e) {
            value[i] = '?';
        }
    }
}

static int read_root_first_line(const struct paths *paths,
                                const char *absolute_path,
                                char *out,
                                size_t out_size,
                                bool *present) {
    char host_path[MAX_PATH_LEN];
    int fd;
    ssize_t nread;

    *present = false;
    if (out_size == 0) {
        errno = EINVAL;
        return -1;
    }
    out[0] = '\0';
    if (path_in_root(host_path, sizeof(host_path), paths, absolute_path) < 0) {
        return -1;
    }
    fd = open(host_path, O_RDONLY | O_CLOEXEC);
    if (fd < 0) {
        if (errno == ENOENT || errno == ENOTDIR) {
            return 0;
        }
        return -1;
    }
    *present = true;
    nread = read(fd, out, out_size - 1U);
    close(fd);
    if (nread < 0) {
        out[0] = '\0';
        return -1;
    }
    out[nread] = '\0';
    sanitize_one_line(out);
    return 0;
}

static int append_sepolicy_path_info(struct buffer *buf,
                                     const struct paths *paths,
                                     const char *label,
                                     const char *absolute_path) {
    char host_path[MAX_PATH_LEN];
    char line[256];
    struct stat st;
    uint64_t hash;
    size_t bytes;
    bool present = false;

    if (path_in_root(host_path, sizeof(host_path), paths, absolute_path) < 0) {
        return append_format(buf, "sepolicy.path.%s.error=path-too-long\n", label);
    }
    if (append_format(buf, "sepolicy.path.%s.path=%s\n", label, absolute_path) < 0 ||
        append_format(buf, "sepolicy.path.%s.host_path=%s\n", label, host_path) < 0) {
        return -1;
    }
    if (lstat(host_path, &st) < 0) {
        return append_format(buf,
                             "sepolicy.path.%s.exists=0\n"
                             "sepolicy.path.%s.errno=%d\n",
                             label,
                             label,
                             errno);
    }
    if (append_format(buf,
                      "sepolicy.path.%s.exists=1\n"
                      "sepolicy.path.%s.mode=%o\n"
                      "sepolicy.path.%s.type=%s\n"
                      "sepolicy.path.%s.size=%lld\n"
                      "sepolicy.path.%s.access_r=%d\n"
                      "sepolicy.path.%s.access_x=%d\n",
                      label,
                      label,
                      st.st_mode & 07777,
                      label,
                      S_ISREG(st.st_mode) ? "regular" :
                      S_ISDIR(st.st_mode) ? "directory" :
                      S_ISLNK(st.st_mode) ? "symlink" :
                      S_ISCHR(st.st_mode) ? "char" :
                      S_ISBLK(st.st_mode) ? "block" : "other",
                      label,
                      (long long)st.st_size,
                      label,
                      access(host_path, R_OK) == 0 ? 1 : 0,
                      label,
                      access(host_path, X_OK) == 0 ? 1 : 0) < 0) {
        return -1;
    }
    if (S_ISREG(st.st_mode) && fnv1a64_file(host_path, &hash, &bytes) == 0) {
        if (append_format(buf,
                          "sepolicy.path.%s.bytes=%zu\n"
                          "sepolicy.path.%s.hash=0x%016llx\n",
                          label,
                          bytes,
                          label,
                          (unsigned long long)hash) < 0) {
            return -1;
        }
    }
    if (S_ISREG(st.st_mode) &&
        read_root_first_line(paths, absolute_path, line, sizeof(line), &present) == 0 &&
        present && line[0] != '\0') {
        if (append_format(buf, "sepolicy.path.%s.first_line=%s\n", label, line) < 0) {
            return -1;
        }
    }
    return 0;
}

static int append_sepolicy_hash_compare(struct buffer *buf,
                                        const struct paths *paths,
                                        const char *label,
                                        const char *actual_path,
                                        const char *precompiled_path) {
    char actual[256];
    char precompiled[256];
    bool actual_present = false;
    bool precompiled_present = false;
    int actual_rc;
    int precompiled_rc;
    bool match = false;

    actual_rc = read_root_first_line(paths, actual_path, actual, sizeof(actual), &actual_present);
    precompiled_rc = read_root_first_line(paths,
                                          precompiled_path,
                                          precompiled,
                                          sizeof(precompiled),
                                          &precompiled_present);
    if (actual_rc < 0 || precompiled_rc < 0) {
        return append_format(buf,
                             "sepolicy.hash.%s.error=read-failed\n"
                             "sepolicy.hash.%s.actual_rc=%d\n"
                             "sepolicy.hash.%s.precompiled_rc=%d\n",
                             label,
                             label,
                             actual_rc,
                             label,
                             precompiled_rc);
    }
    match = actual_present && precompiled_present && actual[0] != '\0' && streq(actual, precompiled);
    return append_format(buf,
                         "sepolicy.hash.%s.actual_present=%d\n"
                         "sepolicy.hash.%s.precompiled_present=%d\n"
                         "sepolicy.hash.%s.match=%d\n"
                         "sepolicy.hash.%s.actual=%s\n"
                         "sepolicy.hash.%s.precompiled=%s\n",
                         label,
                         actual_present ? 1 : 0,
                         label,
                         precompiled_present ? 1 : 0,
                         label,
                         match ? 1 : 0,
                         label,
                         actual_present ? actual : "<missing>",
                         label,
                         precompiled_present ? precompiled : "<missing>");
}

static bool root_path_exists(const struct paths *paths, const char *absolute_path) {
    char host_path[MAX_PATH_LEN];

    if (path_in_root(host_path, sizeof(host_path), paths, absolute_path) < 0) {
        return false;
    }
    return access(host_path, F_OK) == 0;
}

static int append_stat_line(struct buffer *stdout_buf,
                            const char *prefix,
                            const char *label,
                            const char *path,
                            const struct stat *st,
                            int err_no) {
    return append_format(stdout_buf,
                         "%s.%s.path=%s\n"
                         "%s.%s.present=%d\n"
                         "%s.%s.executable=%d\n"
                         "%s.%s.mode=%o\n"
                         "%s.%s.size=%lld\n"
                         "%s.%s.errno=%d\n",
                         prefix,
                         label,
                         path,
                         prefix,
                         label,
                         err_no == 0 ? 1 : 0,
                         prefix,
                         label,
                         (err_no == 0 && (st->st_mode & 0111) != 0) ? 1 : 0,
                         prefix,
                         label,
                         err_no == 0 ? (unsigned int)(st->st_mode & 07777) : 0,
                         prefix,
                         label,
                         err_no == 0 ? (long long)st->st_size : 0LL,
                         prefix,
                         label,
                         err_no);
}

static int append_root_stat_line(const struct paths *paths,
                                 struct buffer *stdout_buf,
                                 const char *prefix,
                                 const char *label,
                                 const char *absolute_path,
                                 bool *present,
                                 bool *executable) {
    char host_path[MAX_PATH_LEN];
    struct stat st;
    int err_no = 0;

    *present = false;
    *executable = false;
    if (path_in_root(host_path, sizeof(host_path), paths, absolute_path) < 0) {
        err_no = errno;
        memset(&st, 0, sizeof(st));
    } else if (stat(host_path, &st) < 0) {
        err_no = errno;
        memset(&st, 0, sizeof(st));
    } else {
        *present = true;
        *executable = (st.st_mode & 0111) != 0;
    }
    return append_stat_line(stdout_buf, prefix, label, absolute_path, &st, err_no);
}

static int append_host_stat_line(struct buffer *stdout_buf,
                                 const char *prefix,
                                 const char *label,
                                 const char *path,
                                 bool *present,
                                 bool *executable) {
    struct stat st;
    int err_no = 0;

    *present = false;
    *executable = false;
    if (stat(path, &st) < 0) {
        err_no = errno;
        memset(&st, 0, sizeof(st));
    } else {
        *present = true;
        *executable = (st.st_mode & 0111) != 0;
    }
    return append_stat_line(stdout_buf, prefix, label, path, &st, err_no);
}

static int run_wifi_connect_tool_surface(const struct config *cfg,
                                         const struct paths *paths,
                                         struct buffer *stdout_buf) {
    bool vendor_wpa_hw_present = false;
    bool vendor_wpa_hw_executable = false;
    bool vendor_wpa_present = false;
    bool vendor_wpa_executable = false;
    bool system_wificond_present = false;
    bool system_wificond_executable = false;
    bool system_ip_present = false;
    bool system_ip_executable = false;
    bool system_ping_present = false;
    bool system_ping_executable = false;
    bool system_dhcpcd_present = false;
    bool system_dhcpcd_executable = false;
    bool system_udhcpc_present = false;
    bool system_udhcpc_executable = false;
    bool cache_busybox_present = false;
    bool cache_busybox_executable = false;
    bool cache_toybox_present = false;
    bool cache_toybox_executable = false;
    bool supplicant_ready;
    bool dhcp_ready;
    bool ping_ready;

    (void)cfg;
    if (append_literal(stdout_buf,
                       "wifi_connect_tool_surface.begin=1\n"
                       "wifi_connect_tool_surface.device_commands_executed=0\n"
                       "wifi_connect_tool_surface.device_mutations=0\n"
                       "wifi_connect_tool_surface.credentials_read=0\n"
                       "wifi_connect_tool_surface.scan_connect_executed=0\n"
                       "wifi_connect_tool_surface.external_ping_executed=0\n"
                       "wifi_connect_tool_surface.strategy=wpa-supplicant-plus-dhcp-plus-ping\n") < 0) {
        return -1;
    }
    if (append_root_stat_line(paths,
                              stdout_buf,
                              "wifi_connect_tool_surface",
                              "vendor_wpa_supplicant_hw",
                              "/vendor/bin/hw/wpa_supplicant",
                              &vendor_wpa_hw_present,
                              &vendor_wpa_hw_executable) < 0 ||
        append_root_stat_line(paths,
                              stdout_buf,
                              "wifi_connect_tool_surface",
                              "vendor_wpa_supplicant",
                              "/vendor/bin/wpa_supplicant",
                              &vendor_wpa_present,
                              &vendor_wpa_executable) < 0 ||
        append_root_stat_line(paths,
                              stdout_buf,
                              "wifi_connect_tool_surface",
                              "system_wificond",
                              "/system/bin/wificond",
                              &system_wificond_present,
                              &system_wificond_executable) < 0 ||
        append_root_stat_line(paths,
                              stdout_buf,
                              "wifi_connect_tool_surface",
                              "system_ip",
                              "/system/bin/ip",
                              &system_ip_present,
                              &system_ip_executable) < 0 ||
        append_root_stat_line(paths,
                              stdout_buf,
                              "wifi_connect_tool_surface",
                              "system_ping",
                              "/system/bin/ping",
                              &system_ping_present,
                              &system_ping_executable) < 0 ||
        append_root_stat_line(paths,
                              stdout_buf,
                              "wifi_connect_tool_surface",
                              "system_dhcpcd",
                              "/system/bin/dhcpcd",
                              &system_dhcpcd_present,
                              &system_dhcpcd_executable) < 0 ||
        append_root_stat_line(paths,
                              stdout_buf,
                              "wifi_connect_tool_surface",
                              "system_udhcpc",
                              "/system/bin/udhcpc",
                              &system_udhcpc_present,
                              &system_udhcpc_executable) < 0 ||
        append_host_stat_line(stdout_buf,
                              "wifi_connect_tool_surface",
                              "cache_busybox",
                              "/cache/bin/busybox",
                              &cache_busybox_present,
                              &cache_busybox_executable) < 0 ||
        append_host_stat_line(stdout_buf,
                              "wifi_connect_tool_surface",
                              "cache_toybox",
                              "/cache/bin/toybox",
                              &cache_toybox_present,
                              &cache_toybox_executable) < 0) {
        return -1;
    }
    supplicant_ready = (vendor_wpa_hw_present && vendor_wpa_hw_executable) ||
                       (vendor_wpa_present && vendor_wpa_executable);
    dhcp_ready = (system_dhcpcd_present && system_dhcpcd_executable) ||
                 (system_udhcpc_present && system_udhcpc_executable) ||
                 (cache_busybox_present && cache_busybox_executable);
    ping_ready = system_ip_present && system_ip_executable &&
                 system_ping_present && system_ping_executable;
    if (append_format(stdout_buf,
                      "wifi_connect_tool_surface.supplicant_ready=%d\n"
                      "wifi_connect_tool_surface.dhcp_ready=%d\n"
                      "wifi_connect_tool_surface.ping_ready=%d\n",
                      supplicant_ready ? 1 : 0,
                      dhcp_ready ? 1 : 0,
                      ping_ready ? 1 : 0) < 0) {
        return -1;
    }
    if (supplicant_ready && dhcp_ready && ping_ready) {
        return append_literal(stdout_buf,
                              "wifi_connect_tool_surface.result=connect-tools-ready\n"
                              "wifi_connect_tool_surface.reason=supplicant-dhcp-ping-tools-present\n"
                              "wifi_connect_tool_surface.end=1\n");
    }
    return append_literal(stdout_buf,
                          "wifi_connect_tool_surface.result=connect-tools-missing\n"
                          "wifi_connect_tool_surface.reason=supplicant-dhcp-or-ping-tool-missing\n"
                          "wifi_connect_tool_surface.end=1\n");
}

static int run_wifi_connect_ping_scaffold(const struct config *cfg,
                                          const struct paths *paths,
                                          struct buffer *stdout_buf) {
    struct stat config_st;
    int config_errno = 0;
    int config_fd = -1;
    int config_flags = O_RDONLY | O_CLOEXEC;
    bool vendor_wpa_hw_present = false;
    bool vendor_wpa_hw_executable = false;
    bool vendor_wpa_present = false;
    bool vendor_wpa_executable = false;
    bool system_ip_present = false;
    bool system_ip_executable = false;
    bool system_ping_present = false;
    bool system_ping_executable = false;
    bool system_dhcpcd_present = false;
    bool system_dhcpcd_executable = false;
    bool system_udhcpc_present = false;
    bool system_udhcpc_executable = false;
    bool cache_busybox_present = false;
    bool cache_busybox_executable = false;
    bool supplicant_ready;
    bool dhcp_ready;
    bool ping_ready;

#ifdef O_NOFOLLOW
    config_flags |= O_NOFOLLOW;
#endif

    memset(&config_st, 0, sizeof(config_st));
    if (lstat(cfg->connect_config, &config_st) < 0) {
        config_errno = errno;
    } else if (!S_ISREG(config_st.st_mode)) {
        config_errno = EINVAL;
    } else {
        config_fd = open(cfg->connect_config, config_flags);
        if (config_fd < 0) {
            config_errno = errno;
        } else {
            close(config_fd);
            config_fd = -1;
        }
    }

    if (append_literal(stdout_buf,
                       "wifi_connect_ping.begin=1\n"
                       "wifi_connect_ping.helper_version=" EXECNS_VERSION "\n"
                       "wifi_connect_ping.mode=v52-scaffold\n"
                       "wifi_connect_ping.allowed=1\n"
                       "wifi_connect_ping.credentials_read=0\n"
                       "wifi_connect_ping.secret_values_logged=0\n"
                       "wifi_connect_ping.exec_attempted=0\n"
                       "wifi_connect_ping.supplicant_started=0\n"
                       "wifi_connect_ping.dhcp_executed=0\n"
                       "wifi_connect_ping.external_ping_executed=0\n") < 0 ||
        append_format(stdout_buf,
                      "wifi_connect_ping.connect_config.path=%s\n"
                      "wifi_connect_ping.connect_config.present=%d\n"
                      "wifi_connect_ping.connect_config.mode=%o\n"
                      "wifi_connect_ping.connect_config.size=%lld\n"
                      "wifi_connect_ping.connect_config.private_mode=%d\n"
                      "wifi_connect_ping.connect_config.errno=%d\n"
                      "wifi_connect_ping.iface=%s\n"
                      "wifi_connect_ping.ping_target=%s\n",
                      cfg->connect_config,
                      config_errno == 0 ? 1 : 0,
                      config_errno == 0 ? (unsigned int)(config_st.st_mode & 07777) : 0,
                      config_errno == 0 ? (long long)config_st.st_size : 0LL,
                      (config_errno == 0 &&
                       S_ISREG(config_st.st_mode) &&
                       (config_st.st_mode & 0077) == 0 &&
                       config_st.st_size > 0 &&
                       config_st.st_size <= 8192) ? 1 : 0,
                      config_errno,
                      cfg->connect_iface,
                      cfg->ping_target) < 0) {
        return -1;
    }

    if (append_root_stat_line(paths,
                              stdout_buf,
                              "wifi_connect_ping",
                              "vendor_wpa_supplicant_hw",
                              "/vendor/bin/hw/wpa_supplicant",
                              &vendor_wpa_hw_present,
                              &vendor_wpa_hw_executable) < 0 ||
        append_root_stat_line(paths,
                              stdout_buf,
                              "wifi_connect_ping",
                              "vendor_wpa_supplicant",
                              "/vendor/bin/wpa_supplicant",
                              &vendor_wpa_present,
                              &vendor_wpa_executable) < 0 ||
        append_root_stat_line(paths,
                              stdout_buf,
                              "wifi_connect_ping",
                              "system_ip",
                              "/system/bin/ip",
                              &system_ip_present,
                              &system_ip_executable) < 0 ||
        append_root_stat_line(paths,
                              stdout_buf,
                              "wifi_connect_ping",
                              "system_ping",
                              "/system/bin/ping",
                              &system_ping_present,
                              &system_ping_executable) < 0 ||
        append_root_stat_line(paths,
                              stdout_buf,
                              "wifi_connect_ping",
                              "system_dhcpcd",
                              "/system/bin/dhcpcd",
                              &system_dhcpcd_present,
                              &system_dhcpcd_executable) < 0 ||
        append_root_stat_line(paths,
                              stdout_buf,
                              "wifi_connect_ping",
                              "system_udhcpc",
                              "/system/bin/udhcpc",
                              &system_udhcpc_present,
                              &system_udhcpc_executable) < 0 ||
        append_host_stat_line(stdout_buf,
                              "wifi_connect_ping",
                              "cache_busybox",
                              "/cache/bin/busybox",
                              &cache_busybox_present,
                              &cache_busybox_executable) < 0) {
        return -1;
    }

    supplicant_ready = (vendor_wpa_hw_present && vendor_wpa_hw_executable) ||
                       (vendor_wpa_present && vendor_wpa_executable);
    dhcp_ready = (system_dhcpcd_present && system_dhcpcd_executable) ||
                 (system_udhcpc_present && system_udhcpc_executable) ||
                 (cache_busybox_present && cache_busybox_executable);
    ping_ready = system_ip_present && system_ip_executable &&
                 system_ping_present && system_ping_executable;
    if (append_format(stdout_buf,
                      "wifi_connect_ping.supplicant_ready=%d\n"
                      "wifi_connect_ping.dhcp_ready=%d\n"
                      "wifi_connect_ping.ping_ready=%d\n"
                      "wifi_connect_ping.executor_implemented=0\n"
                      "wifi_connect_ping.result=executor-scaffold-only\n"
                      "wifi_connect_ping.reason=v52-contract-present-live-execution-deferred-to-v53\n"
                      "wifi_connect_ping.end=1\n",
                      supplicant_ready ? 1 : 0,
                      dhcp_ready ? 1 : 0,
                      ping_ready ? 1 : 0) < 0) {
        return -1;
    }
    return 40;
}

static int run_sepolicy_inventory(const struct config *cfg,
                                  const struct paths *paths,
                                  struct buffer *stdout_buf) {
    static const struct sepolicy_inventory_path inventory_paths[] = {
        {"system_plat_cil", "/system/etc/selinux/plat_sepolicy.cil"},
        {"system_plat_mapping_sha", "/system/etc/selinux/plat_sepolicy_and_mapping.sha256"},
        {"system_mapping_dir", "/system/etc/selinux/mapping"},
        {"system_secilc", "/system/bin/secilc"},
        {"system_plat_pub_versioned", "/system/etc/selinux/plat_pub_versioned.cil"},
        {"system_ext_cil", "/system/system_ext/etc/selinux/system_ext_sepolicy.cil"},
        {"system_ext_hash", "/system/system_ext/etc/selinux/system_ext_sepolicy_and_mapping.sha256"},
        {"system_ext_mapping_dir", "/system/system_ext/etc/selinux/mapping"},
        {"system_ext_root_cil", "/system_ext/etc/selinux/system_ext_sepolicy.cil"},
        {"product_cil", "/system/product/etc/selinux/product_sepolicy.cil"},
        {"product_hash", "/system/product/etc/selinux/product_sepolicy_and_mapping.sha256"},
        {"product_mapping_dir", "/system/product/etc/selinux/mapping"},
        {"product_root_cil", "/product/etc/selinux/product_sepolicy.cil"},
        {"vendor_precompiled", "/vendor/etc/selinux/precompiled_sepolicy"},
        {"vendor_precompiled_plat_hash", "/vendor/etc/selinux/precompiled_sepolicy.plat_sepolicy_and_mapping.sha256"},
        {"vendor_precompiled_system_ext_hash", "/vendor/etc/selinux/precompiled_sepolicy.system_ext_sepolicy_and_mapping.sha256"},
        {"vendor_precompiled_product_hash", "/vendor/etc/selinux/precompiled_sepolicy.product_sepolicy_and_mapping.sha256"},
        {"vendor_plat_pub_versioned", "/vendor/etc/selinux/plat_pub_versioned.cil"},
        {"vendor_policy_cil", "/vendor/etc/selinux/vendor_sepolicy.cil"},
        {"vendor_plat_sepolicy_vers", "/vendor/etc/selinux/plat_sepolicy_vers.txt"},
        {"vendor_file_contexts", "/vendor/etc/selinux/vendor_file_contexts"},
        {"vendor_service_contexts", "/vendor/etc/selinux/vendor_service_contexts"},
        {"vendor_hwservice_contexts", "/vendor/etc/selinux/vendor_hwservice_contexts"},
        {"odm_precompiled", "/odm/etc/selinux/precompiled_sepolicy"},
        {"odm_policy_cil", "/odm/etc/selinux/odm_sepolicy.cil"},
    };
    bool split_policy;
    bool vendor_precompiled;
    bool secilc;
    bool vendor_policy;
    bool vendor_plat_pub;
    int hash_match_count = 0;
    int hash_required_count = 0;

    (void)cfg;
    if (append_literal(stdout_buf,
                       "sepolicy_inventory.begin=1\n"
                       "sepolicy_inventory.daemon_start_executed=0\n"
                       "sepolicy_inventory.wifi_hal_start_executed=0\n"
                       "sepolicy_inventory.wifi_bringup_executed=0\n") < 0) {
        return -1;
    }
    for (size_t i = 0; i < sizeof(inventory_paths) / sizeof(inventory_paths[0]); i++) {
        if (append_sepolicy_path_info(stdout_buf,
                                      paths,
                                      inventory_paths[i].label,
                                      inventory_paths[i].path) < 0) {
            return -1;
        }
    }
    if (append_sepolicy_hash_compare(stdout_buf,
                                     paths,
                                     "plat",
                                     "/system/etc/selinux/plat_sepolicy_and_mapping.sha256",
                                     "/vendor/etc/selinux/precompiled_sepolicy.plat_sepolicy_and_mapping.sha256") < 0 ||
        append_sepolicy_hash_compare(stdout_buf,
                                     paths,
                                     "system_ext",
                                     "/system/system_ext/etc/selinux/system_ext_sepolicy_and_mapping.sha256",
                                     "/vendor/etc/selinux/precompiled_sepolicy.system_ext_sepolicy_and_mapping.sha256") < 0 ||
        append_sepolicy_hash_compare(stdout_buf,
                                     paths,
                                     "product",
                                     "/system/product/etc/selinux/product_sepolicy_and_mapping.sha256",
                                     "/vendor/etc/selinux/precompiled_sepolicy.product_sepolicy_and_mapping.sha256") < 0) {
        return -1;
    }
    split_policy = root_path_exists(paths, "/system/etc/selinux/plat_sepolicy.cil");
    vendor_precompiled = root_path_exists(paths, "/vendor/etc/selinux/precompiled_sepolicy");
    secilc = root_path_exists(paths, "/system/bin/secilc");
    vendor_policy = root_path_exists(paths, "/vendor/etc/selinux/vendor_sepolicy.cil");
    vendor_plat_pub = root_path_exists(paths, "/vendor/etc/selinux/plat_pub_versioned.cil");
    if (root_path_exists(paths, "/system/etc/selinux/plat_sepolicy_and_mapping.sha256")) {
        hash_required_count++;
        if (root_path_exists(paths, "/vendor/etc/selinux/precompiled_sepolicy.plat_sepolicy_and_mapping.sha256")) {
            char actual[256];
            char precompiled[256];
            bool actual_present = false;
            bool precompiled_present = false;

            if (read_root_first_line(paths,
                                     "/system/etc/selinux/plat_sepolicy_and_mapping.sha256",
                                     actual,
                                     sizeof(actual),
                                     &actual_present) == 0 &&
                read_root_first_line(paths,
                                     "/vendor/etc/selinux/precompiled_sepolicy.plat_sepolicy_and_mapping.sha256",
                                     precompiled,
                                     sizeof(precompiled),
                                     &precompiled_present) == 0 &&
                actual_present &&
                precompiled_present &&
                streq(actual, precompiled)) {
                hash_match_count++;
            }
        }
    }
    if (root_path_exists(paths, "/system/system_ext/etc/selinux/system_ext_sepolicy_and_mapping.sha256")) {
        hash_required_count++;
        if (root_path_exists(paths, "/vendor/etc/selinux/precompiled_sepolicy.system_ext_sepolicy_and_mapping.sha256")) {
            char actual[256];
            char precompiled[256];
            bool actual_present = false;
            bool precompiled_present = false;

            if (read_root_first_line(paths,
                                     "/system/system_ext/etc/selinux/system_ext_sepolicy_and_mapping.sha256",
                                     actual,
                                     sizeof(actual),
                                     &actual_present) == 0 &&
                read_root_first_line(paths,
                                     "/vendor/etc/selinux/precompiled_sepolicy.system_ext_sepolicy_and_mapping.sha256",
                                     precompiled,
                                     sizeof(precompiled),
                                     &precompiled_present) == 0 &&
                actual_present &&
                precompiled_present &&
                streq(actual, precompiled)) {
                hash_match_count++;
            }
        }
    }
    if (root_path_exists(paths, "/system/product/etc/selinux/product_sepolicy_and_mapping.sha256")) {
        hash_required_count++;
        if (root_path_exists(paths, "/vendor/etc/selinux/precompiled_sepolicy.product_sepolicy_and_mapping.sha256")) {
            char actual[256];
            char precompiled[256];
            bool actual_present = false;
            bool precompiled_present = false;

            if (read_root_first_line(paths,
                                     "/system/product/etc/selinux/product_sepolicy_and_mapping.sha256",
                                     actual,
                                     sizeof(actual),
                                     &actual_present) == 0 &&
                read_root_first_line(paths,
                                     "/vendor/etc/selinux/precompiled_sepolicy.product_sepolicy_and_mapping.sha256",
                                     precompiled,
                                     sizeof(precompiled),
                                     &precompiled_present) == 0 &&
                actual_present &&
                precompiled_present &&
                streq(actual, precompiled)) {
                hash_match_count++;
            }
        }
    }
    if (append_format(stdout_buf,
                      "sepolicy_inventory.split_policy_device=%d\n"
                      "sepolicy_inventory.vendor_precompiled_present=%d\n"
                      "sepolicy_inventory.precompiled_hash_required_count=%d\n"
                      "sepolicy_inventory.precompiled_hash_match_count=%d\n"
                      "sepolicy_inventory.precompiled_usable=%d\n"
                      "sepolicy_inventory.secilc_present=%d\n"
                      "sepolicy_inventory.vendor_policy_cil_present=%d\n"
                      "sepolicy_inventory.vendor_plat_pub_versioned_present=%d\n"
                      "sepolicy_inventory.compile_inputs_present=%d\n"
                      "sepolicy_inventory.result=%s\n"
                      "sepolicy_inventory.end=1\n",
                      split_policy ? 1 : 0,
                      vendor_precompiled ? 1 : 0,
                      hash_required_count,
                      hash_match_count,
                      vendor_precompiled && hash_required_count > 0 && hash_match_count == hash_required_count ? 1 : 0,
                      secilc ? 1 : 0,
                      vendor_policy ? 1 : 0,
                      vendor_plat_pub ? 1 : 0,
                      split_policy && secilc && vendor_policy && vendor_plat_pub ? 1 : 0,
                      split_policy ? "split-policy-inventory-pass" : "split-policy-inventory-missing") < 0) {
        return -1;
    }
    return 0;
}

static int add_sepolicy_compile_input(struct buffer *stdout_buf,
                                      const struct paths *paths,
                                      const char *attempt,
                                      const char *label,
                                      const char *absolute_path,
                                      bool required,
                                      char **argv,
                                      size_t *argc,
                                      size_t max_argc,
                                      int *required_missing) {
    char host_path[MAX_PATH_LEN];
    struct stat st;
    bool present = false;
    bool readable = false;

    if (path_in_root(host_path, sizeof(host_path), paths, absolute_path) < 0) {
        if (required) {
            (*required_missing)++;
        }
        return append_format(stdout_buf,
                             "sepolicy_compile.attempt_%s.input.%s.path=%s\n"
                             "sepolicy_compile.attempt_%s.input.%s.required=%d\n"
                             "sepolicy_compile.attempt_%s.input.%s.present=0\n"
                             "sepolicy_compile.attempt_%s.input.%s.error=path-too-long\n",
                             attempt,
                             label,
                             absolute_path,
                             attempt,
                             label,
                             required ? 1 : 0,
                             attempt,
                             label,
                             attempt,
                             label);
    }
    if (stat(host_path, &st) == 0 && S_ISREG(st.st_mode)) {
        present = true;
        readable = access(host_path, R_OK) == 0;
    }
    if (append_format(stdout_buf,
                      "sepolicy_compile.attempt_%s.input.%s.path=%s\n"
                      "sepolicy_compile.attempt_%s.input.%s.host_path=%s\n"
                      "sepolicy_compile.attempt_%s.input.%s.required=%d\n"
                      "sepolicy_compile.attempt_%s.input.%s.present=%d\n"
                      "sepolicy_compile.attempt_%s.input.%s.readable=%d\n",
                      attempt,
                      label,
                      absolute_path,
                      attempt,
                      label,
                      host_path,
                      attempt,
                      label,
                      required ? 1 : 0,
                      attempt,
                      label,
                      present ? 1 : 0,
                      attempt,
                      label,
                      readable ? 1 : 0) < 0) {
        return -1;
    }
    if (!present || !readable) {
        if (required) {
            (*required_missing)++;
        }
        return 0;
    }
    if (*argc + 1 >= max_argc) {
        return append_format(stdout_buf,
                             "sepolicy_compile.attempt_%s.input.%s.error=argv-overflow\n",
                             attempt,
                             label);
    }
    argv[(*argc)++] = (char *)absolute_path;
    return 0;
}

static int append_sepolicy_compile_output_info(struct buffer *stdout_buf,
                                               const struct paths *paths,
                                               const char *attempt,
                                               const char *output_path,
                                               bool remove_output) {
    char host_path[MAX_PATH_LEN];
    struct stat st;
    uint64_t hash = 0;
    size_t bytes = 0;

    if (path_in_root(host_path, sizeof(host_path), paths, output_path) < 0) {
        return append_format(stdout_buf,
                             "sepolicy_compile.attempt_%s.output.path=%s\n"
                             "sepolicy_compile.attempt_%s.output.exists=0\n"
                             "sepolicy_compile.attempt_%s.output.error=path-too-long\n",
                             attempt,
                             output_path,
                             attempt,
                             attempt);
    }
    if (lstat(host_path, &st) < 0) {
        return append_format(stdout_buf,
                             "sepolicy_compile.attempt_%s.output.path=%s\n"
                             "sepolicy_compile.attempt_%s.output.host_path=%s\n"
                             "sepolicy_compile.attempt_%s.output.exists=0\n"
                             "sepolicy_compile.attempt_%s.output.errno=%d\n",
                             attempt,
                             output_path,
                             attempt,
                             host_path,
                             attempt,
                             attempt,
                             errno);
    }
    if (S_ISREG(st.st_mode) && fnv1a64_file(host_path, &hash, &bytes) == 0) {
        if (append_format(stdout_buf,
                          "sepolicy_compile.attempt_%s.output.path=%s\n"
                          "sepolicy_compile.attempt_%s.output.host_path=%s\n"
                          "sepolicy_compile.attempt_%s.output.exists=1\n"
                          "sepolicy_compile.attempt_%s.output.size=%lld\n"
                          "sepolicy_compile.attempt_%s.output.bytes=%zu\n"
                          "sepolicy_compile.attempt_%s.output.hash=0x%016llx\n",
                          attempt,
                          output_path,
                          attempt,
                          host_path,
                          attempt,
                          attempt,
                          (long long)st.st_size,
                          attempt,
                          bytes,
                          attempt,
                          (unsigned long long)hash) < 0) {
            return -1;
        }
    } else if (append_format(stdout_buf,
                             "sepolicy_compile.attempt_%s.output.path=%s\n"
                             "sepolicy_compile.attempt_%s.output.host_path=%s\n"
                             "sepolicy_compile.attempt_%s.output.exists=1\n"
                             "sepolicy_compile.attempt_%s.output.size=%lld\n"
                             "sepolicy_compile.attempt_%s.output.hash=<unavailable>\n",
                             attempt,
                             output_path,
                             attempt,
                             host_path,
                             attempt,
                             attempt,
                             (long long)st.st_size,
                             attempt) < 0) {
        return -1;
    }
    if (remove_output) {
        unlink(host_path);
    }
    return 0;
}

static bool sepolicy_mapping_version_safe(const char *version) {
    if (version == NULL || version[0] == '\0') {
        return false;
    }
    return strspn(version, "0123456789.") == strlen(version);
}

static int run_sepolicy_compile_attempt(const struct config *cfg,
                                        const struct paths *paths,
                                        struct buffer *stdout_buf,
                                        struct buffer *stderr_buf,
                                        const char *policy_version,
                                        const char *vendor_mapping_version,
                                        int timeout_ms,
                                        bool keep_output,
                                        char *output_host_path,
                                        size_t output_host_path_size,
                                        char *output_chroot_path,
                                        size_t output_chroot_path_size) {
    char secilc_host_path[MAX_PATH_LEN];
    char plat_mapping[128];
    char plat_compat[128];
    char system_ext_mapping[160];
    char system_ext_compat[160];
    char product_mapping[160];
    char output_path[64];
    char *child_argv[64];
    size_t argc = 0;
    int required_missing = 0;
    int stdout_pipe[2] = {-1, -1};
    int stderr_pipe[2] = {-1, -1};
    pid_t pid;
    pid_t pgid;
    bool stdout_open = false;
    bool stderr_open = false;
    bool child_done = false;
    bool timed_out = false;
    int exit_code = -1;
    int signal_no = 0;
    long deadline;

    if (output_host_path != NULL && output_host_path_size > 0) {
        output_host_path[0] = '\0';
    }
    if (output_chroot_path != NULL && output_chroot_path_size > 0) {
        output_chroot_path[0] = '\0';
    }

    if (snprintf(plat_mapping,
                 sizeof(plat_mapping),
                 "/system/etc/selinux/mapping/%s.cil",
                 vendor_mapping_version) < 0 ||
        strlen(plat_mapping) >= sizeof(plat_mapping) ||
        snprintf(plat_compat,
                 sizeof(plat_compat),
                 "/system/etc/selinux/mapping/%s.compat.cil",
                 vendor_mapping_version) < 0 ||
        strlen(plat_compat) >= sizeof(plat_compat) ||
        snprintf(system_ext_mapping,
                 sizeof(system_ext_mapping),
                 "/system/system_ext/etc/selinux/mapping/%s.cil",
                 vendor_mapping_version) < 0 ||
        strlen(system_ext_mapping) >= sizeof(system_ext_mapping) ||
        snprintf(system_ext_compat,
                 sizeof(system_ext_compat),
                 "/system/system_ext/etc/selinux/mapping/%s.compat.cil",
                 vendor_mapping_version) < 0 ||
        strlen(system_ext_compat) >= sizeof(system_ext_compat) ||
        snprintf(product_mapping,
                 sizeof(product_mapping),
                 "/system/product/etc/selinux/mapping/%s.cil",
                 vendor_mapping_version) < 0 ||
        strlen(product_mapping) >= sizeof(product_mapping) ||
        snprintf(output_path,
                 sizeof(output_path),
                 "/sepolicy-compile-proof-%s.compiled",
                 policy_version) < 0 ||
        strlen(output_path) >= sizeof(output_path)) {
        append_format(stdout_buf,
                      "sepolicy_compile.attempt_%s.result=manual-review-required\n"
                      "sepolicy_compile.attempt_%s.reason=path-format-overflow\n",
                      policy_version,
                      policy_version);
        return -1;
    }
    if (output_chroot_path != NULL && output_chroot_path_size > 0) {
        int rc = snprintf(output_chroot_path, output_chroot_path_size, "%s", output_path);

        if (rc < 0 || (size_t)rc >= output_chroot_path_size) {
            errno = ENAMETOOLONG;
            return -1;
        }
    }
    if (output_host_path != NULL && output_host_path_size > 0 &&
        path_in_root(output_host_path, output_host_path_size, paths, output_path) < 0) {
        return -1;
    }

    if (path_in_root(secilc_host_path, sizeof(secilc_host_path), paths, "/system/bin/secilc") < 0) {
        append_format(stdout_buf,
                      "sepolicy_compile.attempt_%s.result=compile-tool-missing\n"
                      "sepolicy_compile.attempt_%s.reason=secilc-path-too-long\n",
                      policy_version,
                      policy_version);
        return 10;
    }
    append_format(stdout_buf,
                  "sepolicy_compile.attempt_%s.begin=1\n"
                  "sepolicy_compile.attempt_%s.tool=/system/bin/secilc\n"
                  "sepolicy_compile.attempt_%s.tool_host_path=%s\n"
                  "sepolicy_compile.attempt_%s.tool_exists=%d\n"
                  "sepolicy_compile.attempt_%s.tool_executable=%d\n"
                  "sepolicy_compile.attempt_%s.policy_version=%s\n"
                  "sepolicy_compile.attempt_%s.vendor_mapping_version=%s\n"
                  "sepolicy_compile.attempt_%s.output=%s\n"
                  "sepolicy_compile.attempt_%s.policy_load_executed=0\n"
                  "sepolicy_compile.attempt_%s.init_reexec_executed=0\n"
                  "sepolicy_compile.attempt_%s.daemon_start_executed=0\n"
                  "sepolicy_compile.attempt_%s.wifi_hal_start_executed=0\n"
                  "sepolicy_compile.attempt_%s.wifi_bringup_executed=0\n",
                  policy_version,
                  policy_version,
                  policy_version,
                  secilc_host_path,
                  policy_version,
                  access(secilc_host_path, F_OK) == 0 ? 1 : 0,
                  policy_version,
                  access(secilc_host_path, X_OK) == 0 ? 1 : 0,
                  policy_version,
                  policy_version,
                  policy_version,
                  vendor_mapping_version,
                  policy_version,
                  output_path,
                  policy_version,
                  policy_version,
                  policy_version,
                  policy_version,
                  policy_version);
    if (access(secilc_host_path, X_OK) < 0) {
        append_format(stdout_buf,
                      "sepolicy_compile.attempt_%s.exec_attempted=0\n"
                      "sepolicy_compile.attempt_%s.result=compile-tool-missing\n"
                      "sepolicy_compile.attempt_%s.reason=system-bin-secilc-unavailable-%s\n"
                      "sepolicy_compile.attempt_%s.end=1\n",
                      policy_version,
                      policy_version,
                      policy_version,
                      strerror(errno),
                      policy_version);
        return 10;
    }

    child_argv[argc++] = (char *)"/system/bin/secilc";
    if (add_sepolicy_compile_input(stdout_buf,
                                   paths,
                                   policy_version,
                                   "plat",
                                   "/system/etc/selinux/plat_sepolicy.cil",
                                   true,
                                   child_argv,
                                   &argc,
                                   sizeof(child_argv) / sizeof(child_argv[0]),
                                   &required_missing) < 0) {
        return -1;
    }
    child_argv[argc++] = (char *)"-m";
    child_argv[argc++] = (char *)"-M";
    child_argv[argc++] = (char *)"true";
    child_argv[argc++] = (char *)"-G";
    child_argv[argc++] = (char *)"-N";
    child_argv[argc++] = (char *)"-c";
    child_argv[argc++] = (char *)policy_version;
    if (add_sepolicy_compile_input(stdout_buf,
                                   paths,
                                   policy_version,
                                   "plat_mapping",
                                   plat_mapping,
                                   true,
                                   child_argv,
                                   &argc,
                                   sizeof(child_argv) / sizeof(child_argv[0]),
                                   &required_missing) < 0) {
        return -1;
    }
    child_argv[argc++] = (char *)"-o";
    child_argv[argc++] = output_path;
    child_argv[argc++] = (char *)"-f";
    child_argv[argc++] = (char *)"/sys/fs/selinux/null";
    if (add_sepolicy_compile_input(stdout_buf,
                                   paths,
                                   policy_version,
                                   "plat_compat",
                                   plat_compat,
                                   false,
                                   child_argv,
                                   &argc,
                                   sizeof(child_argv) / sizeof(child_argv[0]),
                                   &required_missing) < 0 ||
        add_sepolicy_compile_input(stdout_buf,
                                   paths,
                                   policy_version,
                                   "system_ext",
                                   "/system/system_ext/etc/selinux/system_ext_sepolicy.cil",
                                   false,
                                   child_argv,
                                   &argc,
                                   sizeof(child_argv) / sizeof(child_argv[0]),
                                   &required_missing) < 0 ||
        add_sepolicy_compile_input(stdout_buf,
                                   paths,
                                   policy_version,
                                   "system_ext_mapping",
                                   system_ext_mapping,
                                   false,
                                   child_argv,
                                   &argc,
                                   sizeof(child_argv) / sizeof(child_argv[0]),
                                   &required_missing) < 0 ||
        add_sepolicy_compile_input(stdout_buf,
                                   paths,
                                   policy_version,
                                   "system_ext_compat",
                                   system_ext_compat,
                                   false,
                                   child_argv,
                                   &argc,
                                   sizeof(child_argv) / sizeof(child_argv[0]),
                                   &required_missing) < 0 ||
        add_sepolicy_compile_input(stdout_buf,
                                   paths,
                                   policy_version,
                                   "product",
                                   "/system/product/etc/selinux/product_sepolicy.cil",
                                   false,
                                   child_argv,
                                   &argc,
                                   sizeof(child_argv) / sizeof(child_argv[0]),
                                   &required_missing) < 0 ||
        add_sepolicy_compile_input(stdout_buf,
                                   paths,
                                   policy_version,
                                   "product_mapping",
                                   product_mapping,
                                   false,
                                   child_argv,
                                   &argc,
                                   sizeof(child_argv) / sizeof(child_argv[0]),
                                   &required_missing) < 0 ||
        add_sepolicy_compile_input(stdout_buf,
                                   paths,
                                   policy_version,
                                   "plat_pub_versioned",
                                   "/vendor/etc/selinux/plat_pub_versioned.cil",
                                   true,
                                   child_argv,
                                   &argc,
                                   sizeof(child_argv) / sizeof(child_argv[0]),
                                   &required_missing) < 0 ||
        add_sepolicy_compile_input(stdout_buf,
                                   paths,
                                   policy_version,
                                   "vendor",
                                   "/vendor/etc/selinux/vendor_sepolicy.cil",
                                   true,
                                   child_argv,
                                   &argc,
                                   sizeof(child_argv) / sizeof(child_argv[0]),
                                   &required_missing) < 0 ||
        add_sepolicy_compile_input(stdout_buf,
                                   paths,
                                   policy_version,
                                   "odm",
                                   "/odm/etc/selinux/odm_sepolicy.cil",
                                   false,
                                   child_argv,
                                   &argc,
                                   sizeof(child_argv) / sizeof(child_argv[0]),
                                   &required_missing) < 0) {
        return -1;
    }
    child_argv[argc] = NULL;
    append_format(stdout_buf,
                  "sepolicy_compile.attempt_%s.argc=%zu\n"
                  "sepolicy_compile.attempt_%s.required_missing=%d\n",
                  policy_version,
                  argc,
                  policy_version,
                  required_missing);
    for (size_t i = 0; i < argc; i++) {
        append_format(stdout_buf,
                      "sepolicy_compile.attempt_%s.argv.%zu=%s\n",
                      policy_version,
                      i,
                      child_argv[i]);
    }
    if (required_missing > 0) {
        append_format(stdout_buf,
                      "sepolicy_compile.attempt_%s.exec_attempted=0\n"
                      "sepolicy_compile.attempt_%s.result=compile-input-gap\n"
                      "sepolicy_compile.attempt_%s.reason=required-input-missing\n"
                      "sepolicy_compile.attempt_%s.end=1\n",
                      policy_version,
                      policy_version,
                      policy_version,
                      policy_version);
        return 11;
    }

    if (pipe2(stdout_pipe, O_CLOEXEC) < 0 || pipe2(stderr_pipe, O_CLOEXEC) < 0) {
        append_format(stdout_buf,
                      "sepolicy_compile.attempt_%s.result=manual-review-required\n"
                      "sepolicy_compile.attempt_%s.reason=pipe-failed-%s\n"
                      "sepolicy_compile.attempt_%s.end=1\n",
                      policy_version,
                      policy_version,
                      strerror(errno),
                      policy_version);
        if (stdout_pipe[0] >= 0) close(stdout_pipe[0]);
        if (stdout_pipe[1] >= 0) close(stdout_pipe[1]);
        if (stderr_pipe[0] >= 0) close(stderr_pipe[0]);
        if (stderr_pipe[1] >= 0) close(stderr_pipe[1]);
        return -1;
    }
    pid = fork();
    if (pid < 0) {
        append_format(stdout_buf,
                      "sepolicy_compile.attempt_%s.result=manual-review-required\n"
                      "sepolicy_compile.attempt_%s.reason=fork-failed-%s\n"
                      "sepolicy_compile.attempt_%s.end=1\n",
                      policy_version,
                      policy_version,
                      strerror(errno),
                      policy_version);
        close(stdout_pipe[0]);
        close(stdout_pipe[1]);
        close(stderr_pipe[0]);
        close(stderr_pipe[1]);
        return -1;
    }
    if (pid == 0) {
        close(stdout_pipe[0]);
        close(stderr_pipe[0]);
        dup2(stdout_pipe[1], STDOUT_FILENO);
        dup2(stderr_pipe[1], STDERR_FILENO);
        close(stdout_pipe[1]);
        close(stderr_pipe[1]);
        if (setsid() < 0) {
            perror("setsid");
            _exit(123);
        }
        if (chroot(paths->root) < 0) {
            perror("chroot");
            _exit(120);
        }
        if (chdir("/") < 0) {
            perror("chdir");
            _exit(121);
        }
        apply_child_env(cfg);
        printf("sepolicy_compile.attempt_%s.child.begin=1\n", policy_version);
        printf("sepolicy_compile.attempt_%s.child.exec_target=/system/bin/secilc\n", policy_version);
        printf("sepolicy_compile.attempt_%s.child.policy_load_executed=0\n", policy_version);
        fflush(stdout);
        execv("/system/bin/secilc", child_argv);
        printf("sepolicy_compile.attempt_%s.child.exec_error=%s\n", policy_version, strerror(errno));
        printf("sepolicy_compile.attempt_%s.child.end=1\n", policy_version);
        fflush(stdout);
        _exit(127);
    }
    close(stdout_pipe[1]);
    close(stderr_pipe[1]);
    stdout_open = true;
    stderr_open = true;
    set_nonblock(stdout_pipe[0]);
    set_nonblock(stderr_pipe[0]);
    pgid = wait_for_child_session_pgid(pid, 1000);
    append_format(stdout_buf,
                  "sepolicy_compile.attempt_%s.exec_attempted=1\n"
                  "sepolicy_compile.attempt_%s.child_started=1\n"
                  "sepolicy_compile.attempt_%s.pid=%ld\n"
                  "sepolicy_compile.attempt_%s.pgid=%ld\n",
                  policy_version,
                  policy_version,
                  policy_version,
                  (long)pid,
                  policy_version,
                  (long)pgid);
    deadline = monotonic_ms() + timeout_ms;
    while (stdout_open || stderr_open || !child_done) {
        struct pollfd fds[2];
        int nfds = 0;

        if (!child_done && monotonic_ms() >= deadline) {
            timed_out = true;
            if (pgid > 1) {
                kill(-pgid, SIGTERM);
            }
            kill(pid, SIGTERM);
        }
        if (stdout_open) {
            fds[nfds].fd = stdout_pipe[0];
            fds[nfds].events = POLLIN | POLLHUP | POLLERR;
            nfds++;
        }
        if (stderr_open) {
            fds[nfds].fd = stderr_pipe[0];
            fds[nfds].events = POLLIN | POLLHUP | POLLERR;
            nfds++;
        }
        if (nfds > 0) {
            int rc = poll(fds, nfds, 50);

            if (rc > 0) {
                int idx = 0;

                if (stdout_open) {
                    if (fds[idx].revents != 0) {
                        drain_fd(stdout_pipe[0], stdout_buf, &stdout_open);
                    }
                    idx++;
                }
                if (stderr_open && fds[idx].revents != 0) {
                    drain_fd(stderr_pipe[0], stderr_buf, &stderr_open);
                }
            }
        } else {
            usleep(50000);
        }
        if (!child_done) {
            int status = 0;
            pid_t wait_rc = waitpid(pid, &status, WNOHANG);

            if (wait_rc == pid) {
                child_done = true;
                if (WIFEXITED(status)) {
                    exit_code = WEXITSTATUS(status);
                } else if (WIFSIGNALED(status)) {
                    signal_no = WTERMSIG(status);
                }
            } else if (wait_rc < 0) {
                if (errno == ECHILD) {
                    child_done = true;
                } else if (errno != EINTR) {
                    append_format(stdout_buf,
                                  "sepolicy_compile.attempt_%s.wait.error=%s\n",
                                  policy_version,
                                  strerror(errno));
                    child_done = true;
                }
            }
        }
        if (timed_out && !child_done && monotonic_ms() >= deadline + 1000L) {
            if (pgid > 1) {
                kill(-pgid, SIGKILL);
            }
            kill(pid, SIGKILL);
        }
    }
    if (stdout_pipe[0] >= 0) close(stdout_pipe[0]);
    if (stderr_pipe[0] >= 0) close(stderr_pipe[0]);
    append_format(stdout_buf,
                  "sepolicy_compile.attempt_%s.exit_code=%d\n"
                  "sepolicy_compile.attempt_%s.signal=%d\n"
                  "sepolicy_compile.attempt_%s.timed_out=%d\n",
                  policy_version,
                  exit_code,
                  policy_version,
                  signal_no,
                  policy_version,
                  timed_out ? 1 : 0);
    append_sepolicy_compile_output_info(stdout_buf,
                                        paths,
                                        policy_version,
                                        output_path,
                                        !keep_output);
    if (timed_out) {
        append_format(stdout_buf,
                      "sepolicy_compile.attempt_%s.result=compile-timeout\n"
                      "sepolicy_compile.attempt_%s.reason=secilc-timeout\n"
                      "sepolicy_compile.attempt_%s.end=1\n",
                      policy_version,
                      policy_version,
                      policy_version);
        return 12;
    }
    if (exit_code == 0 && signal_no == 0) {
        append_format(stdout_buf,
                      "sepolicy_compile.attempt_%s.result=compile-pass\n"
                      "sepolicy_compile.attempt_%s.reason=secilc-exit-zero\n"
                      "sepolicy_compile.attempt_%s.end=1\n",
                      policy_version,
                      policy_version,
                      policy_version);
        return 0;
    }
    append_format(stdout_buf,
                  "sepolicy_compile.attempt_%s.result=compile-runtime-gap\n"
                  "sepolicy_compile.attempt_%s.reason=secilc-nonzero\n"
                  "sepolicy_compile.attempt_%s.end=1\n",
                  policy_version,
                  policy_version,
                  policy_version);
    return 11;
}

static int run_sepolicy_compile_proof(const struct config *cfg,
                                      const struct paths *paths,
                                      struct buffer *stdout_buf,
                                      struct buffer *stderr_buf) {
    char vendor_mapping_version[64];
    char kernel_policy_version[64];
    bool vendor_mapping_present = false;
    bool kernel_policy_present = false;
    int rc31;
    int rc30 = 99;

    if (append_literal(stdout_buf,
                       "sepolicy_compile.begin=1\n"
                       "sepolicy_compile.policy_load_executed=0\n"
                       "sepolicy_compile.init_reexec_executed=0\n"
                       "sepolicy_compile.daemon_start_executed=0\n"
                       "sepolicy_compile.wifi_hal_start_executed=0\n"
                       "sepolicy_compile.wifi_bringup_executed=0\n") < 0) {
        return -1;
    }
    if (append_sepolicy_path_info(stdout_buf, paths, "compile_system_secilc", "/system/bin/secilc") < 0 ||
        append_sepolicy_path_info(stdout_buf, paths, "compile_system_plat_cil", "/system/etc/selinux/plat_sepolicy.cil") < 0 ||
        append_sepolicy_path_info(stdout_buf, paths, "compile_vendor_policy_cil", "/vendor/etc/selinux/vendor_sepolicy.cil") < 0 ||
        append_sepolicy_path_info(stdout_buf, paths, "compile_vendor_plat_pub_versioned", "/vendor/etc/selinux/plat_pub_versioned.cil") < 0 ||
        append_sepolicy_path_info(stdout_buf, paths, "compile_vendor_plat_sepolicy_vers", "/vendor/etc/selinux/plat_sepolicy_vers.txt") < 0 ||
        append_sepolicy_path_info(stdout_buf, paths, "compile_selinux_null", "/sys/fs/selinux/null") < 0) {
        return -1;
    }
    if (read_root_first_line(paths,
                             "/vendor/etc/selinux/plat_sepolicy_vers.txt",
                             vendor_mapping_version,
                             sizeof(vendor_mapping_version),
                             &vendor_mapping_present) < 0) {
        append_literal(stdout_buf,
                       "sepolicy_compile.result=compile-input-gap\n"
                       "sepolicy_compile.reason=vendor-mapping-version-read-failed\n"
                       "sepolicy_compile.end=1\n");
        return 11;
    }
    if (read_root_first_line(paths,
                             "/sys/fs/selinux/policyvers",
                             kernel_policy_version,
                             sizeof(kernel_policy_version),
                             &kernel_policy_present) < 0) {
        kernel_policy_version[0] = '\0';
    }
    append_format(stdout_buf,
                  "sepolicy_compile.vendor_mapping_version.present=%d\n"
                  "sepolicy_compile.vendor_mapping_version=%s\n"
                  "sepolicy_compile.kernel_policy_version.present=%d\n"
                  "sepolicy_compile.kernel_policy_version=%s\n",
                  vendor_mapping_present ? 1 : 0,
                  vendor_mapping_present ? vendor_mapping_version : "<missing>",
                  kernel_policy_present ? 1 : 0,
                  kernel_policy_present ? kernel_policy_version : "<missing>");
    if (!vendor_mapping_present || !sepolicy_mapping_version_safe(vendor_mapping_version)) {
        append_literal(stdout_buf,
                       "sepolicy_compile.result=compile-input-gap\n"
                       "sepolicy_compile.reason=vendor-mapping-version-missing-or-unsafe\n"
                       "sepolicy_compile.end=1\n");
        return 11;
    }

    rc31 = run_sepolicy_compile_attempt(cfg,
                                        paths,
                                        stdout_buf,
                                        stderr_buf,
                                        "31",
                                        vendor_mapping_version,
                                        cfg->timeout_sec * 1000,
                                        false,
                                        NULL,
                                        0,
                                        NULL,
                                        0);
    if (rc31 == 0) {
        append_literal(stdout_buf,
                       "sepolicy_compile.attempts=1\n"
                       "sepolicy_compile.pass_version=31\n"
                       "sepolicy_compile.result=compile-pass\n"
                       "sepolicy_compile.reason=policy-version-31-pass\n"
                       "sepolicy_compile.end=1\n");
        return 0;
    }
    rc30 = run_sepolicy_compile_attempt(cfg,
                                        paths,
                                        stdout_buf,
                                        stderr_buf,
                                        "30",
                                        vendor_mapping_version,
                                        cfg->timeout_sec * 1000,
                                        false,
                                        NULL,
                                        0,
                                        NULL,
                                        0);
    if (rc30 == 0) {
        append_literal(stdout_buf,
                       "sepolicy_compile.attempts=2\n"
                       "sepolicy_compile.pass_version=30\n"
                       "sepolicy_compile.result=compile-pass\n"
                       "sepolicy_compile.reason=policy-version-30-pass\n"
                       "sepolicy_compile.end=1\n");
        return 0;
    }
    append_format(stdout_buf,
                  "sepolicy_compile.attempts=2\n"
                  "sepolicy_compile.result=compile-runtime-gap\n"
                  "sepolicy_compile.reason=all-compile-attempts-failed\n"
                  "sepolicy_compile.rc31=%d\n"
                  "sepolicy_compile.rc30=%d\n"
                  "sepolicy_compile.end=1\n",
                  rc31,
                  rc30);
    return 11;
}

static int append_sepolicy_load_state(struct buffer *stdout_buf,
                                      const struct paths *paths,
                                      const char *phase) {
    char current[256] = "<read-failed>";
    char enforce[64] = "<read-failed>";
    char policyvers[64] = "<read-failed>";
    bool enforce_present = false;
    bool policyvers_present = false;

    read_small_file_trim("/proc/self/attr/current", current, sizeof(current));
    read_root_first_line(paths, "/sys/fs/selinux/enforce", enforce, sizeof(enforce), &enforce_present);
    read_root_first_line(paths, "/sys/fs/selinux/policyvers", policyvers, sizeof(policyvers), &policyvers_present);
    return append_format(stdout_buf,
                         "sepolicy_load.%s.current=%s\n"
                         "sepolicy_load.%s.enforce.present=%d\n"
                         "sepolicy_load.%s.enforce=%s\n"
                         "sepolicy_load.%s.policyvers.present=%d\n"
                         "sepolicy_load.%s.policyvers=%s\n"
                         "sepolicy_load.%s.load_path=%s\n"
                         "sepolicy_load.%s.load_writable=%d\n",
                         phase,
                         current,
                         phase,
                         enforce_present ? 1 : 0,
                         phase,
                         enforce_present ? enforce : "<missing>",
                         phase,
                         policyvers_present ? 1 : 0,
                         phase,
                         policyvers_present ? policyvers : "<missing>",
                         phase,
                         paths->sys_fs_selinux_load,
                         phase,
                         access(paths->sys_fs_selinux_load, W_OK) == 0 ? 1 : 0);
}

static int run_sepolicy_load_proof(const struct config *cfg,
                                   const struct paths *paths,
                                   struct buffer *stdout_buf,
                                   struct buffer *stderr_buf) {
    char vendor_mapping_version[64];
    char kernel_policy_version[64];
    char output_host_path[MAX_PATH_LEN];
    char output_chroot_path[MAX_PATH_LEN];
    bool vendor_mapping_present = false;
    bool kernel_policy_present = false;
    int compile_rc;
    const char *compiled_policy_version = "31";
    int load_fd;
    size_t load_bytes = 0;
    uint64_t load_hash = 0;

    if (append_literal(stdout_buf,
                       "sepolicy_load.begin=1\n"
                       "sepolicy_load.policy_load_attempted=0\n"
                       "sepolicy_load.policy_load_executed=0\n"
                       "sepolicy_load.init_reexec_executed=0\n"
                       "sepolicy_load.daemon_start_executed=0\n"
                       "sepolicy_load.wifi_hal_start_executed=0\n"
                       "sepolicy_load.wifi_bringup_executed=0\n") < 0) {
        return -1;
    }
    if (!cfg->allow_policy_load_proof) {
        append_literal(stdout_buf,
                       "sepolicy_load.result=approval-missing\n"
                       "sepolicy_load.reason=missing-allow-policy-load-proof\n"
                       "sepolicy_load.end=1\n");
        return 13;
    }
    if (append_sepolicy_path_info(stdout_buf, paths, "load_system_secilc", "/system/bin/secilc") < 0 ||
        append_sepolicy_path_info(stdout_buf, paths, "load_system_plat_cil", "/system/etc/selinux/plat_sepolicy.cil") < 0 ||
        append_sepolicy_path_info(stdout_buf, paths, "load_vendor_policy_cil", "/vendor/etc/selinux/vendor_sepolicy.cil") < 0 ||
        append_sepolicy_path_info(stdout_buf, paths, "load_vendor_plat_pub_versioned", "/vendor/etc/selinux/plat_pub_versioned.cil") < 0 ||
        append_sepolicy_path_info(stdout_buf, paths, "load_selinux_load", "/sys/fs/selinux/load") < 0 ||
        append_sepolicy_load_state(stdout_buf, paths, "pre") < 0) {
        return -1;
    }
    if (read_root_first_line(paths,
                             "/vendor/etc/selinux/plat_sepolicy_vers.txt",
                             vendor_mapping_version,
                             sizeof(vendor_mapping_version),
                             &vendor_mapping_present) < 0) {
        append_literal(stdout_buf,
                       "sepolicy_load.result=compile-input-gap\n"
                       "sepolicy_load.reason=vendor-mapping-version-read-failed\n"
                       "sepolicy_load.end=1\n");
        return 11;
    }
    if (read_root_first_line(paths,
                             "/sys/fs/selinux/policyvers",
                             kernel_policy_version,
                             sizeof(kernel_policy_version),
                             &kernel_policy_present) < 0) {
        kernel_policy_version[0] = '\0';
    }
    append_format(stdout_buf,
                  "sepolicy_load.vendor_mapping_version.present=%d\n"
                  "sepolicy_load.vendor_mapping_version=%s\n"
                  "sepolicy_load.kernel_policy_version.present=%d\n"
                  "sepolicy_load.kernel_policy_version=%s\n",
                  vendor_mapping_present ? 1 : 0,
                  vendor_mapping_present ? vendor_mapping_version : "<missing>",
                  kernel_policy_present ? 1 : 0,
                  kernel_policy_present ? kernel_policy_version : "<missing>");
    if (!vendor_mapping_present || !sepolicy_mapping_version_safe(vendor_mapping_version)) {
        append_literal(stdout_buf,
                       "sepolicy_load.result=compile-input-gap\n"
                       "sepolicy_load.reason=vendor-mapping-version-missing-or-unsafe\n"
                       "sepolicy_load.end=1\n");
        return 11;
    }

    compile_rc = run_sepolicy_compile_attempt(cfg,
                                              paths,
                                              stdout_buf,
                                              stderr_buf,
                                              "31",
                                              vendor_mapping_version,
                                              cfg->timeout_sec * 1000,
                                              true,
                                              output_host_path,
                                              sizeof(output_host_path),
                                              output_chroot_path,
                                              sizeof(output_chroot_path));
    if (compile_rc != 0) {
        compiled_policy_version = "30";
        compile_rc = run_sepolicy_compile_attempt(cfg,
                                                  paths,
                                                  stdout_buf,
                                                  stderr_buf,
                                                  "30",
                                                  vendor_mapping_version,
                                                  cfg->timeout_sec * 1000,
                                                  true,
                                                  output_host_path,
                                                  sizeof(output_host_path),
                                                  output_chroot_path,
                                                  sizeof(output_chroot_path));
    }
    if (compile_rc != 0) {
        append_format(stdout_buf,
                      "sepolicy_load.result=compile-runtime-gap\n"
                      "sepolicy_load.reason=compile-before-load-failed\n"
                      "sepolicy_load.compile_rc=%d\n"
                      "sepolicy_load.end=1\n",
                      compile_rc);
        return 11;
    }
    append_format(stdout_buf,
                  "sepolicy_load.compiled_policy.version=%s\n"
                  "sepolicy_load.compiled_policy.host_path=%s\n"
                  "sepolicy_load.compiled_policy.chroot_path=%s\n",
                  compiled_policy_version,
                  output_host_path,
                  output_chroot_path);
    load_fd = open(paths->sys_fs_selinux_load, O_WRONLY | O_CLOEXEC);
    append_literal(stdout_buf, "sepolicy_load.policy_load_attempted=1\n");
    if (load_fd < 0) {
        append_format(stdout_buf,
                      "sepolicy_load.result=policy-load-open-failed\n"
                      "sepolicy_load.reason=open-selinux-load-failed-%s\n"
                      "sepolicy_load.end=1\n",
                      strerror(errno));
        unlink(output_host_path);
        return 12;
    }
    if (write_file_once_to_fd(output_host_path, load_fd, &load_bytes, &load_hash) < 0) {
        int saved_errno = errno;

        close(load_fd);
        append_format(stdout_buf,
                      "sepolicy_load.result=policy-load-write-failed\n"
                      "sepolicy_load.reason=write-selinux-load-failed-%s\n"
                      "sepolicy_load.bytes=%zu\n"
                      "sepolicy_load.hash=0x%016llx\n"
                      "sepolicy_load.end=1\n",
                      strerror(saved_errno),
                      load_bytes,
                      (unsigned long long)load_hash);
        unlink(output_host_path);
        return 12;
    }
    close(load_fd);
    append_format(stdout_buf,
                  "sepolicy_load.policy_load_executed=1\n"
                  "sepolicy_load.bytes=%zu\n"
                  "sepolicy_load.hash=0x%016llx\n",
                  load_bytes,
                  (unsigned long long)load_hash);
    append_sepolicy_load_state(stdout_buf, paths, "post");
    unlink(output_host_path);
    append_literal(stdout_buf,
                   "sepolicy_load.result=policy-load-pass\n"
                   "sepolicy_load.reason=selinux-load-write-success\n"
                   "sepolicy_load.end=1\n");
    return 0;
}

static bool wifi_surface_iface_name(const char *name) {
    return name != NULL &&
           (strncmp(name, "wlan", 4) == 0 ||
            strncmp(name, "swlan", 5) == 0 ||
            strncmp(name, "p2p", 3) == 0 ||
            strncmp(name, "wifi-aware", 10) == 0);
}

static int append_limited_csv(struct buffer *buf,
                              const char *prefix,
                              const char *field,
                              char names[][64],
                              size_t count) {
    if (append_format(buf, "%s.%s=", prefix, field) < 0) {
        return -1;
    }
    for (size_t i = 0; i < count; i++) {
        if (i > 0 && append_literal(buf, ",") < 0) {
            return -1;
        }
        if (append_literal(buf, names[i]) < 0) {
            return -1;
        }
    }
    return append_literal(buf, "\n");
}

static int collect_matching_dir_names(const char *path,
                                      bool (*predicate)(const char *),
                                      char names[][64],
                                      size_t max_names,
                                      size_t *count_out) {
    DIR *dir = opendir(path);
    struct dirent *entry;
    size_t count = 0;

    *count_out = 0;
    if (dir == NULL) {
        return -1;
    }
    while ((entry = readdir(dir)) != NULL) {
        if (entry->d_name[0] == '.') {
            continue;
        }
        if (!predicate(entry->d_name)) {
            continue;
        }
        if (count < max_names) {
            strncpy(names[count], entry->d_name, 63);
            names[count][63] = '\0';
        }
        count++;
    }
    closedir(dir);
    *count_out = count;
    return 0;
}

static bool phy_name(const char *name) {
    return name != NULL && strncmp(name, "phy", 3) == 0;
}

static int read_small_file_trim(const char *path, char *out, size_t out_size) {
    FILE *file;
    size_t nread;

    if (out_size == 0) {
        errno = EINVAL;
        return -1;
    }
    out[0] = '\0';
    file = fopen(path, "re");
    if (file == NULL) {
        return -1;
    }
    nread = fread(out, 1, out_size - 1, file);
    fclose(file);
    out[nread] = '\0';
    while (nread > 0 && (out[nread - 1] == '\n' || out[nread - 1] == '\r' || out[nread - 1] == ' ' || out[nread - 1] == '\t')) {
        out[nread - 1] = '\0';
        nread--;
    }
    return 0;
}

static int parse_proc_devices_major(const char *name, unsigned int *major_no) {
    FILE *file;
    char line[256];

    file = fopen("/proc/devices", "re");
    if (file == NULL) {
        return -1;
    }
    while (fgets(line, sizeof(line), file) != NULL) {
        unsigned int current_major = 0;
        char current_name[128];

        if (sscanf(line, " %u %127s", &current_major, current_name) == 2 &&
            strcmp(current_name, name) == 0) {
            *major_no = current_major;
            fclose(file);
            return 0;
        }
    }
    fclose(file);
    errno = ENOENT;
    return -1;
}

static int materialize_private_android_char_node(const char *dev_dir,
                                                 const char *name,
                                                 mode_t mode,
                                                 uid_t uid,
                                                 gid_t gid,
                                                 unsigned int major_no,
                                                 unsigned int minor_no,
                                                 char *error_buf,
                                                 size_t error_size) {
    char path[MAX_PATH_LEN];

    if (append_path(path, sizeof(path), dev_dir, name) < 0) {
        snprintf(error_buf, error_size, "private node path too long: %s", name);
        errno = ENAMETOOLONG;
        return -1;
    }
    if (unlink(path) < 0 && errno != ENOENT) {
        snprintf(error_buf, error_size, "unlink private node %s: %s", name, strerror(errno));
        return -1;
    }
    if (mknod(path, S_IFCHR | mode, makedev(major_no, minor_no)) < 0) {
        snprintf(error_buf, error_size, "mknod private node %s: %s", name, strerror(errno));
        return -1;
    }
    if (chown(path, uid, gid) < 0) {
        snprintf(error_buf, error_size, "chown private node %s: %s", name, strerror(errno));
        return -1;
    }
    if (chmod(path, mode) < 0) {
        snprintf(error_buf, error_size, "chmod private node %s: %s", name, strerror(errno));
        return -1;
    }
    return 0;
}

static int materialize_peripheral_manager_node_parity(const struct config *cfg,
                                                      const struct paths *paths,
                                                      char *error_buf,
                                                      size_t error_size) {
    char dev_text[64];
    unsigned int major_no = 0;
    unsigned int minor_no = 0;

    if (!is_wifi_companion_peripheral_manager_node_materialization_mode(cfg->mode)) {
        return 0;
    }
    if (mkdir_p(paths->dev, 0755) < 0) {
        snprintf(error_buf, error_size, "mkdir dev for peripheral nodes: %s", strerror(errno));
        return -1;
    }
    if (parse_dev_major_minor("/sys/class/subsys/subsys_modem/dev",
                              &major_no,
                              &minor_no,
                              dev_text,
                              sizeof(dev_text)) < 0) {
        snprintf(error_buf, error_size, "parse subsys_modem dev: %s", strerror(errno));
        return -1;
    }
    if (materialize_private_android_char_node(paths->dev,
                                              "subsys_modem",
                                              0640,
                                              A90_AID_SYSTEM,
                                              A90_AID_SYSTEM,
                                              major_no,
                                              minor_no,
                                              error_buf,
                                              error_size) < 0) {
        return -1;
    }
    if (parse_dev_major_minor("/sys/class/subsys/subsys_esoc0/dev",
                              &major_no,
                              &minor_no,
                              dev_text,
                              sizeof(dev_text)) < 0) {
        snprintf(error_buf, error_size, "parse subsys_esoc0 dev: %s", strerror(errno));
        return -1;
    }
    if (materialize_private_android_char_node(paths->dev,
                                              "subsys_esoc0",
                                              0640,
                                              A90_AID_SYSTEM,
                                              A90_AID_SYSTEM,
                                              major_no,
                                              minor_no,
                                              error_buf,
                                              error_size) < 0) {
        return -1;
    }
    if (parse_proc_devices_major("esoc", &major_no) < 0) {
        snprintf(error_buf, error_size, "parse esoc char major: %s", strerror(errno));
        return -1;
    }
    return materialize_private_android_char_node(paths->dev,
                                                 "esoc-0",
                                                 0660,
                                                 0,
                                                 1001,
                                                 major_no,
                                                 0,
                                                 error_buf,
                                                 error_size);
}

static int append_private_android_node_status(struct buffer *buf,
                                              const struct paths *paths,
                                              const char *name,
                                              const char *label) {
    char path[MAX_PATH_LEN];
    struct stat st;

    if (append_path(path, sizeof(path), paths->dev, name) < 0) {
        return append_format(buf,
                             "wifi_companion_start.private_node.%s.exists=0\n"
                             "wifi_companion_start.private_node.%s.error=path-too-long\n",
                             label,
                             label);
    }
    if (lstat(path, &st) < 0) {
        return append_format(buf,
                             "wifi_companion_start.private_node.%s.exists=0\n"
                             "wifi_companion_start.private_node.%s.error=%s\n",
                             label,
                             label,
                             strerror(errno));
    }
    return append_format(buf,
                         "wifi_companion_start.private_node.%s.exists=1\n"
                         "wifi_companion_start.private_node.%s.char_device=%d\n"
                         "wifi_companion_start.private_node.%s.major=%u\n"
                         "wifi_companion_start.private_node.%s.minor=%u\n"
                         "wifi_companion_start.private_node.%s.mode=%04o\n"
                         "wifi_companion_start.private_node.%s.uid=%ld\n"
                         "wifi_companion_start.private_node.%s.gid=%ld\n"
                         "wifi_companion_start.private_node.%s.path=%s\n",
                         label,
                         label,
                         S_ISCHR(st.st_mode) ? 1 : 0,
                         label,
                         S_ISCHR(st.st_mode) ? major(st.st_rdev) : 0,
                         label,
                         S_ISCHR(st.st_mode) ? minor(st.st_rdev) : 0,
                         label,
                         (unsigned int)(st.st_mode & 07777),
                         label,
                         (long)st.st_uid,
                         label,
                         (long)st.st_gid,
                         label,
                         path);
}

static int append_esoc_ioctl_probe_result(struct buffer *buf,
                                          int fd,
                                          const char *name,
                                          unsigned long request,
                                          unsigned long long *value) {
    int saved_errno;
    unsigned int value32 = 0;
    uint64_t value64 = 0;
    int rc;

    errno = 0;
    if (streq(name, "GET_LINK_ID")) {
        rc = ioctl(fd, request, &value64);
        *value = value64;
    } else {
        rc = ioctl(fd, request, &value32);
        *value = value32;
    }
    saved_errno = errno;
    return append_format(buf,
                         "esoc_control_preflight.ioctl.%s.request=0x%lx\n"
                         "esoc_control_preflight.ioctl.%s.rc=%d\n"
                         "esoc_control_preflight.ioctl.%s.errno=%d\n"
                         "esoc_control_preflight.ioctl.%s.value=%llu\n",
                         name,
                         request,
                         name,
                         rc,
                         name,
                         saved_errno,
                         name,
                         *value);
}

static int append_esoc_noarg_ioctl_result(struct buffer *buf,
                                          int fd,
                                          const char *name,
                                          unsigned long request) {
    int rc;
    int saved_errno;

    errno = 0;
    rc = ioctl(fd, request);
    saved_errno = errno;
    return append_format(buf,
                         "esoc_engine_register_preflight.ioctl.%s.request=0x%lx\n"
                         "esoc_engine_register_preflight.ioctl.%s.rc=%d\n"
                         "esoc_engine_register_preflight.ioctl.%s.errno=%d\n",
                         name,
                         request,
                         name,
                         rc,
                         name,
                         saved_errno);
}

static int run_wifi_companion_esoc_control_preflight_guarded(const struct config *cfg,
                                                            const struct paths *paths,
                                                            struct buffer *stdout_buf,
                                                            struct buffer *stderr_buf,
                                                            int *child_exit_code,
                                                            int *child_signal,
                                                            bool *timed_out) {
    char esoc_path[MAX_PATH_LEN];
    int fd = -1;
    int saved_errno = 0;
    unsigned long long value = 0;

    (void)stderr_buf;
    *child_signal = 0;
    *timed_out = false;
    if (append_literal(stdout_buf,
                       "esoc_control_preflight.begin=1\n"
                       "esoc_control_preflight.mode=guarded\n"
                       "esoc_control_preflight.device=/dev/esoc-0\n"
                       "esoc_control_preflight.daemon_start_executed=0\n"
                       "esoc_control_preflight.mdm_helper_start_executed=0\n"
                       "esoc_control_preflight.ks_start_executed=0\n"
                       "esoc_control_preflight.wifi_hal_start_executed=0\n"
                       "esoc_control_preflight.scan_connect_linkup=0\n"
                       "esoc_control_preflight.credentials=0\n"
                       "esoc_control_preflight.dhcp_routing=0\n"
                       "esoc_control_preflight.external_ping=0\n"
                       "esoc_control_preflight.reg_req_eng_attempted=0\n"
                       "esoc_control_preflight.reg_cmd_eng_attempted=0\n"
                       "esoc_control_preflight.cmd_exe_attempted=0\n"
                       "esoc_control_preflight.wait_for_req_attempted=0\n"
                       "esoc_control_preflight.notify_attempted=0\n"
                       "esoc_control_preflight.pwr_on_attempted=0\n") < 0 ||
        append_format(stdout_buf,
                      "esoc_control_preflight.uapi.ESOC_CODE=0x%x\n"
                      "esoc_control_preflight.uapi.ESOC_CMD_EXE.nr=1\n"
                      "esoc_control_preflight.uapi.ESOC_WAIT_FOR_REQ.nr=2\n"
                      "esoc_control_preflight.uapi.ESOC_NOTIFY.nr=3\n"
                      "esoc_control_preflight.uapi.ESOC_GET_STATUS.nr=4\n"
                      "esoc_control_preflight.uapi.ESOC_GET_ERR_FATAL.nr=5\n"
                      "esoc_control_preflight.uapi.ESOC_WAIT_FOR_CRASH.nr=6\n"
                      "esoc_control_preflight.uapi.ESOC_REG_REQ_ENG.nr=7\n"
                      "esoc_control_preflight.uapi.ESOC_REG_CMD_ENG.nr=8\n"
                      "esoc_control_preflight.uapi.ESOC_GET_LINK_ID.nr=9\n"
                      "esoc_control_preflight.uapi.ESOC_PWR_ON.value=%u\n"
                      "esoc_control_preflight.uapi.ESOC_IMG_XFER_DONE.value=%u\n"
                      "esoc_control_preflight.uapi.ESOC_BOOT_DONE.value=%u\n",
                      A90_ESOC_CODE,
                      A90_ESOC_PWR_ON,
                      A90_ESOC_IMG_XFER_DONE,
                      A90_ESOC_BOOT_DONE) < 0 ||
        append_private_android_node_status(stdout_buf, paths, "esoc-0", "esoc_0") < 0 ||
        append_private_android_node_status(stdout_buf, paths, "subsys_esoc0", "subsys_esoc0") < 0 ||
        append_private_android_node_status(stdout_buf, paths, "subsys_modem", "subsys_modem") < 0) {
        return -1;
    }
    if (!cfg->allow_esoc_control_preflight) {
        if (append_literal(stdout_buf,
                           "esoc_control_preflight.allowed=0\n"
                           "esoc_control_preflight.open_attempted=0\n"
                           "esoc_control_preflight.result=blocked\n"
                           "esoc_control_preflight.reason=missing-esoc-control-preflight-allow-flag\n"
                           "esoc_control_preflight.end=1\n") < 0) {
            return -1;
        }
        *child_exit_code = 0;
        return 0;
    }
    if (append_literal(stdout_buf,
                       "esoc_control_preflight.allowed=1\n"
                       "esoc_control_preflight.open_attempted=1\n") < 0) {
        return -1;
    }
    if (append_path(esoc_path, sizeof(esoc_path), paths->dev, "esoc-0") < 0) {
        if (append_literal(stdout_buf,
                           "esoc_control_preflight.result=path-too-long\n"
                           "esoc_control_preflight.end=1\n") < 0) {
            return -1;
        }
        *child_exit_code = 0;
        return 0;
    }
    errno = 0;
    fd = open(esoc_path, O_RDONLY | O_CLOEXEC);
    saved_errno = fd < 0 ? errno : 0;
    if (append_format(stdout_buf,
                      "esoc_control_preflight.open.path=%s\n"
                      "esoc_control_preflight.open.fd=%d\n"
                      "esoc_control_preflight.open.errno=%d\n",
                      esoc_path,
                      fd,
                      saved_errno) < 0) {
        if (fd >= 0) {
            close(fd);
        }
        return -1;
    }
    if (fd < 0) {
        if (append_literal(stdout_buf,
                           "esoc_control_preflight.result=open-failed\n"
                           "esoc_control_preflight.end=1\n") < 0) {
            return -1;
        }
        *child_exit_code = 0;
        return 0;
    }
    if (append_esoc_ioctl_probe_result(stdout_buf, fd, "GET_STATUS", A90_ESOC_GET_STATUS, &value) < 0 ||
        append_esoc_ioctl_probe_result(stdout_buf, fd, "GET_ERR_FATAL", A90_ESOC_GET_ERR_FATAL, &value) < 0 ||
        append_esoc_ioctl_probe_result(stdout_buf, fd, "GET_LINK_ID", A90_ESOC_GET_LINK_ID, &value) < 0) {
        close(fd);
        return -1;
    }
    close(fd);
    if (append_literal(stdout_buf,
                       "esoc_control_preflight.close_attempted=1\n"
                       "esoc_control_preflight.result=read-only-ioctl-probe-complete\n"
                       "esoc_control_preflight.end=1\n") < 0) {
        return -1;
    }
    *child_exit_code = 0;
    return 0;
}

static int run_wifi_companion_esoc_engine_register_preflight_guarded(const struct config *cfg,
                                                                    const struct paths *paths,
                                                                    struct buffer *stdout_buf,
                                                                    struct buffer *stderr_buf,
                                                                    int *child_exit_code,
                                                                    int *child_signal,
                                                                    bool *timed_out) {
    char esoc_path[MAX_PATH_LEN];
    int cmd_fd = -1;
    int req_fd = -1;
    int saved_errno = 0;
    int hold_sec = cfg->timeout_sec > 3 ? cfg->timeout_sec - 2 : 1;

    (void)stderr_buf;
    *child_signal = 0;
    *timed_out = false;
    if (append_literal(stdout_buf,
                       "esoc_engine_register_preflight.begin=1\n"
                       "esoc_engine_register_preflight.mode=guarded\n"
                       "esoc_engine_register_preflight.device=/dev/esoc-0\n"
                       "esoc_engine_register_preflight.daemon_start_executed=0\n"
                       "esoc_engine_register_preflight.mdm_helper_start_executed=0\n"
                       "esoc_engine_register_preflight.ks_start_executed=0\n"
                       "esoc_engine_register_preflight.pm_proxy_helper_start_executed=0\n"
                       "esoc_engine_register_preflight.cnss_start_executed=0\n"
                       "esoc_engine_register_preflight.service_manager_start_executed=0\n"
                       "esoc_engine_register_preflight.wifi_hal_start_executed=0\n"
                       "esoc_engine_register_preflight.scan_connect_linkup=0\n"
                       "esoc_engine_register_preflight.credentials=0\n"
                       "esoc_engine_register_preflight.dhcp_routing=0\n"
                       "esoc_engine_register_preflight.external_ping=0\n"
                       "esoc_engine_register_preflight.cmd_exe_attempted=0\n"
                       "esoc_engine_register_preflight.pwr_on_attempted=0\n"
                       "esoc_engine_register_preflight.wait_for_req_attempted=0\n"
                       "esoc_engine_register_preflight.notify_attempted=0\n"
                       "esoc_engine_register_preflight.subsys_esoc0_open_attempted=0\n") < 0 ||
        append_format(stdout_buf,
                      "esoc_engine_register_preflight.uapi.ESOC_CODE=0x%x\n"
                      "esoc_engine_register_preflight.uapi.ESOC_REG_CMD_ENG.request=0x%lx\n"
                      "esoc_engine_register_preflight.uapi.ESOC_REG_REQ_ENG.request=0x%lx\n"
                      "esoc_engine_register_preflight.uapi.ESOC_CMD_EXE.request=0x%lx\n"
                      "esoc_engine_register_preflight.uapi.ESOC_PWR_ON.value=%u\n"
                      "esoc_engine_register_preflight.uapi.ESOC_WAIT_FOR_REQ.request=0x%lx\n"
                      "esoc_engine_register_preflight.uapi.ESOC_NOTIFY.request=0x%lx\n",
                      A90_ESOC_CODE,
                      (unsigned long)A90_ESOC_REG_CMD_ENG,
                      (unsigned long)A90_ESOC_REG_REQ_ENG,
                      (unsigned long)A90_ESOC_CMD_EXE,
                      A90_ESOC_PWR_ON,
                      (unsigned long)A90_ESOC_WAIT_FOR_REQ,
                      (unsigned long)A90_ESOC_NOTIFY) < 0 ||
        append_private_android_node_status(stdout_buf, paths, "esoc-0", "esoc_0") < 0 ||
        append_private_android_node_status(stdout_buf, paths, "subsys_esoc0", "subsys_esoc0") < 0 ||
        append_private_android_node_status(stdout_buf, paths, "subsys_modem", "subsys_modem") < 0) {
        return -1;
    }
    if (!cfg->allow_esoc_engine_register_preflight) {
        if (append_literal(stdout_buf,
                           "esoc_engine_register_preflight.allowed=0\n"
                           "esoc_engine_register_preflight.open_cmd_attempted=0\n"
                           "esoc_engine_register_preflight.open_req_attempted=0\n"
                           "esoc_engine_register_preflight.reg_cmd_eng_attempted=0\n"
                           "esoc_engine_register_preflight.reg_req_eng_attempted=0\n"
                           "esoc_engine_register_preflight.result=blocked\n"
                           "esoc_engine_register_preflight.reason=missing-esoc-engine-register-preflight-allow-flag\n"
                           "esoc_engine_register_preflight.end=1\n") < 0) {
            return -1;
        }
        *child_exit_code = 0;
        return 0;
    }
    if (append_literal(stdout_buf,
                       "esoc_engine_register_preflight.allowed=1\n"
                       "esoc_engine_register_preflight.open_cmd_attempted=1\n"
                       "esoc_engine_register_preflight.open_req_attempted=1\n") < 0) {
        return -1;
    }
    if (append_path(esoc_path, sizeof(esoc_path), paths->dev, "esoc-0") < 0) {
        if (append_literal(stdout_buf,
                           "esoc_engine_register_preflight.result=path-too-long\n"
                           "esoc_engine_register_preflight.end=1\n") < 0) {
            return -1;
        }
        *child_exit_code = 0;
        return 0;
    }
    errno = 0;
    cmd_fd = open(esoc_path, O_RDONLY | O_CLOEXEC);
    saved_errno = cmd_fd < 0 ? errno : 0;
    if (append_format(stdout_buf,
                      "esoc_engine_register_preflight.open_cmd.path=%s\n"
                      "esoc_engine_register_preflight.open_cmd.fd=%d\n"
                      "esoc_engine_register_preflight.open_cmd.errno=%d\n",
                      esoc_path,
                      cmd_fd,
                      saved_errno) < 0) {
        if (cmd_fd >= 0) {
            close(cmd_fd);
        }
        return -1;
    }
    errno = 0;
    req_fd = open(esoc_path, O_RDONLY | O_CLOEXEC);
    saved_errno = req_fd < 0 ? errno : 0;
    if (append_format(stdout_buf,
                      "esoc_engine_register_preflight.open_req.path=%s\n"
                      "esoc_engine_register_preflight.open_req.fd=%d\n"
                      "esoc_engine_register_preflight.open_req.errno=%d\n",
                      esoc_path,
                      req_fd,
                      saved_errno) < 0) {
        if (cmd_fd >= 0) {
            close(cmd_fd);
        }
        if (req_fd >= 0) {
            close(req_fd);
        }
        return -1;
    }
    if (cmd_fd < 0 || req_fd < 0) {
        if (append_literal(stdout_buf,
                           "esoc_engine_register_preflight.reg_cmd_eng_attempted=0\n"
                           "esoc_engine_register_preflight.reg_req_eng_attempted=0\n"
                           "esoc_engine_register_preflight.result=open-failed\n"
                           "esoc_engine_register_preflight.end=1\n") < 0) {
            return -1;
        }
        if (cmd_fd >= 0) {
            close(cmd_fd);
        }
        if (req_fd >= 0) {
            close(req_fd);
        }
        *child_exit_code = 0;
        return 0;
    }
    if (append_literal(stdout_buf, "esoc_engine_register_preflight.reg_cmd_eng_attempted=1\n") < 0 ||
        append_esoc_noarg_ioctl_result(stdout_buf, cmd_fd, "REG_CMD_ENG", A90_ESOC_REG_CMD_ENG) < 0 ||
        append_literal(stdout_buf, "esoc_engine_register_preflight.reg_req_eng_attempted=1\n") < 0 ||
        append_esoc_noarg_ioctl_result(stdout_buf, req_fd, "REG_REQ_ENG", A90_ESOC_REG_REQ_ENG) < 0 ||
        append_format(stdout_buf,
                      "esoc_engine_register_preflight.hold_sec=%d\n",
                      hold_sec) < 0) {
        close(cmd_fd);
        close(req_fd);
        return -1;
    }
    if (hold_sec > 0) {
        sleep((unsigned int)hold_sec);
    }
    close(req_fd);
    close(cmd_fd);
    if (append_literal(stdout_buf,
                       "esoc_engine_register_preflight.close_req_attempted=1\n"
                       "esoc_engine_register_preflight.close_cmd_attempted=1\n"
                       "esoc_engine_register_preflight.result=engine-register-preflight-complete\n"
                       "esoc_engine_register_preflight.end=1\n") < 0) {
        return -1;
    }
    *child_exit_code = 0;
    return 0;
}

struct rmt_block_partition {
    const char *partname;
    bool required;
};

static int parse_key_value_line(const char *line, const char *key, char *out, size_t out_size) {
    size_t key_len = strlen(key);

    if (strncmp(line, key, key_len) != 0 || line[key_len] != '=') {
        return 0;
    }
    snprintf(out, out_size, "%s", line + key_len + 1);
    return 1;
}

static int find_block_partition(const char *partname,
                                char *devname,
                                size_t devname_size,
                                unsigned int *major_no,
                                unsigned int *minor_no) {
    DIR *dir;
    struct dirent *entry;
    int found = 0;

    dir = opendir("/sys/class/block");
    if (dir == NULL) {
        return -1;
    }
    while ((entry = readdir(dir)) != NULL) {
        char uevent_path[MAX_PATH_LEN];
        char uevent[4096];
        char *saveptr = NULL;
        char *line;
        char current_partname[128] = "";
        char current_devname[128] = "";
        unsigned int current_major = 0;
        unsigned int current_minor = 0;
        bool have_major = false;
        bool have_minor = false;

        if (!safe_apex_name(entry->d_name)) {
            continue;
        }
        if (snprintf(uevent_path,
                     sizeof(uevent_path),
                     "/sys/class/block/%s/uevent",
                     entry->d_name) >= (int)sizeof(uevent_path)) {
            continue;
        }
        if (read_small_file_trim(uevent_path, uevent, sizeof(uevent)) < 0) {
            continue;
        }
        for (line = strtok_r(uevent, "\n", &saveptr);
             line != NULL;
             line = strtok_r(NULL, "\n", &saveptr)) {
            char value[128];

            if (parse_key_value_line(line, "PARTNAME", value, sizeof(value))) {
                snprintf(current_partname, sizeof(current_partname), "%s", value);
            } else if (parse_key_value_line(line, "DEVNAME", value, sizeof(value))) {
                snprintf(current_devname, sizeof(current_devname), "%s", value);
            } else if (parse_key_value_line(line, "MAJOR", value, sizeof(value))) {
                if (sscanf(value, "%u", &current_major) == 1) {
                    have_major = true;
                }
            } else if (parse_key_value_line(line, "MINOR", value, sizeof(value))) {
                if (sscanf(value, "%u", &current_minor) == 1) {
                    have_minor = true;
                }
            }
        }
        if (streq(current_partname, partname) &&
            current_devname[0] != '\0' &&
            have_major &&
            have_minor) {
            snprintf(devname, devname_size, "%s", current_devname);
            *major_no = current_major;
            *minor_no = current_minor;
            found = 1;
            break;
        }
    }
    closedir(dir);
    if (!found) {
        errno = ENOENT;
        return -1;
    }
    return 0;
}

static int write_empty_private_file(const char *path, mode_t mode) {
    int fd;

    fd = open(path, O_WRONLY | O_CREAT | O_TRUNC | O_CLOEXEC, mode);
    if (fd < 0) {
        return -1;
    }
    if (fchmod(fd, mode) < 0) {
        int saved_errno = errno;

        close(fd);
        errno = saved_errno;
        return -1;
    }
    close(fd);
    return 0;
}

static int write_private_text_file(const char *path, const char *text, mode_t mode) {
    int fd;
    size_t len = strlen(text);

    fd = open(path, O_WRONLY | O_CREAT | O_TRUNC | O_CLOEXEC, mode);
    if (fd < 0) {
        return -1;
    }
    if (fchmod(fd, mode) < 0) {
        int saved_errno = errno;

        close(fd);
        errno = saved_errno;
        return -1;
    }
    while (len > 0) {
        ssize_t written = write(fd, text, len);

        if (written < 0) {
            if (errno == EINTR) {
                continue;
            }
            {
                int saved_errno = errno;

                close(fd);
                errno = saved_errno;
                return -1;
            }
        }
        text += written;
        len -= (size_t)written;
    }
    close(fd);
    return 0;
}

static int copy_sysfs_text_file(const char *source,
                                const char *dest,
                                char *error_buf,
                                size_t error_size) {
    char value[256];
    char content[320];
    int rc;

    if (read_small_file_trim(source, value, sizeof(value)) < 0) {
        snprintf(error_buf, error_size, "read %s: %s", source, strerror(errno));
        return -1;
    }
    rc = snprintf(content, sizeof(content), "%s\n", value);
    if (rc < 0 || (size_t)rc >= sizeof(content)) {
        snprintf(error_buf, error_size, "sysfs value too long for %s", source);
        return -1;
    }
    if (write_private_text_file(dest, content, 0444) < 0) {
        snprintf(error_buf, error_size, "write private %s: %s", dest, strerror(errno));
        return -1;
    }
    return 0;
}

static int symlink_replace(const char *target, const char *linkpath) {
    if (unlink(linkpath) < 0 && errno != ENOENT) {
        return -1;
    }
    return symlink(target, linkpath);
}

static int materialize_one_rmt_block_alias(const struct paths *paths,
                                           const char *partname,
                                           bool required,
                                           char *error_buf,
                                           size_t error_size) {
    char devname[128];
    char node_path[MAX_PATH_LEN];
    char by_name_path[MAX_PATH_LEN];
    char bootdevice_by_name_path[MAX_PATH_LEN];
    char by_name_target[160];
    char bootdevice_target[160];
    unsigned int major_no = 0;
    unsigned int minor_no = 0;

    if (find_block_partition(partname, devname, sizeof(devname), &major_no, &minor_no) < 0) {
        if (!required && errno == ENOENT) {
            return 0;
        }
        snprintf(error_buf, error_size, "find block partition %s: %s", partname, strerror(errno));
        return -1;
    }
    if (append_path(node_path, sizeof(node_path), paths->dev_block, devname) < 0 ||
        append_path(by_name_path, sizeof(by_name_path), paths->dev_block_by_name, partname) < 0 ||
        append_path(bootdevice_by_name_path,
                    sizeof(bootdevice_by_name_path),
                    paths->dev_block_bootdevice_by_name,
                    partname) < 0) {
        snprintf(error_buf, error_size, "rmt block alias path too long");
        return -1;
    }
    if (unlink(node_path) < 0 && errno != ENOENT) {
        snprintf(error_buf, error_size, "unlink rmt block node %s: %s", partname, strerror(errno));
        return -1;
    }
    if (mknod(node_path, S_IFBLK | 0600, makedev(major_no, minor_no)) < 0) {
        snprintf(error_buf, error_size, "mknod rmt block node %s: %s", partname, strerror(errno));
        return -1;
    }
    snprintf(by_name_target, sizeof(by_name_target), "../%s", devname);
    snprintf(bootdevice_target, sizeof(bootdevice_target), "../../%s", devname);
    if (symlink_replace(by_name_target, by_name_path) < 0 ||
        symlink_replace(bootdevice_target, bootdevice_by_name_path) < 0) {
        snprintf(error_buf, error_size, "symlink rmt block alias %s: %s", partname, strerror(errno));
        return -1;
    }
    return 0;
}

static int mount_one_wifi_firmware_partition(const char *partname,
                                             const char *source,
                                             const char *target,
                                             char *error_buf,
                                             size_t error_size) {
    struct stat st;
    char devname[128];
    unsigned int major_no = 0;
    unsigned int minor_no = 0;

    if (stat(target, &st) < 0) {
        snprintf(error_buf, error_size, "stat firmware mount target %s: %s", partname, strerror(errno));
        return -1;
    }
    if (!S_ISDIR(st.st_mode)) {
        snprintf(error_buf, error_size, "firmware mount target %s is not a directory", partname);
        errno = ENOTDIR;
        return -1;
    }
    if (find_block_partition(partname, devname, sizeof(devname), &major_no, &minor_no) < 0) {
        snprintf(error_buf, error_size, "find firmware partition %s: %s", partname, strerror(errno));
        return -1;
    }
    if (unlink(source) < 0 && errno != ENOENT) {
        snprintf(error_buf, error_size, "unlink firmware source %s: %s", partname, strerror(errno));
        return -1;
    }
    if (mknod(source, S_IFBLK | 0600, makedev(major_no, minor_no)) < 0) {
        snprintf(error_buf, error_size, "mknod firmware source %s: %s", partname, strerror(errno));
        return -1;
    }
    if (mount(source,
              target,
              "vfat",
              MS_RDONLY | MS_NOSUID | MS_NODEV,
              "shortname=lower,uid=0,gid=1000,dmask=227,fmask=337") < 0) {
        snprintf(error_buf, error_size, "mount firmware partition %s: %s", partname, strerror(errno));
        return -1;
    }
    return 0;
}

static int materialize_wifi_firmware_mounts(const struct config *cfg,
                                            const struct paths *paths,
                                            char *error_buf,
                                            size_t error_size) {
    if (!is_wifi_companion_any_start_only_mode(cfg->mode) &&
        !is_wifi_companion_hal_order_start_only_mode(cfg->mode) &&
        !is_subsys_hold_open_proof_mode(cfg->mode) &&
        !is_wifi_hal_composite_mode(cfg->mode)) {
        return 0;
    }
    if (mount_one_wifi_firmware_partition("apnhlos",
                                          paths->firmware_mnt_source,
                                          paths->vendor_firmware_mnt,
                                          error_buf,
                                          error_size) < 0) {
        return -1;
    }
    if (mount_one_wifi_firmware_partition("modem",
                                          paths->firmware_modem_source,
                                          paths->vendor_firmware_modem,
                                          error_buf,
                                          error_size) < 0) {
        return -1;
    }
    return 0;
}

static int materialize_rmt_uio_surface(const struct paths *paths,
                                       char *error_buf,
                                       size_t error_size) {
    char dev_text[64];
    char uio0_dir[MAX_PATH_LEN];
    char maps_dir[MAX_PATH_LEN];
    char map0_dir[MAX_PATH_LEN];
    char dest[MAX_PATH_LEN];
    unsigned int major_no = 0;
    unsigned int minor_no = 0;

    if (mkdir_p(paths->sys_class, 0755) < 0 ||
        mkdir_p(paths->sys_class_uio, 0755) < 0) {
        snprintf(error_buf, error_size, "mkdir sys class uio: %s", strerror(errno));
        return -1;
    }
    if (append_path(uio0_dir, sizeof(uio0_dir), paths->sys_class_uio, "uio0") < 0 ||
        append_path(maps_dir, sizeof(maps_dir), uio0_dir, "maps") < 0 ||
        append_path(map0_dir, sizeof(map0_dir), maps_dir, "map0") < 0) {
        snprintf(error_buf, error_size, "uio sysfs private path too long");
        return -1;
    }
    if (mkdir_p(map0_dir, 0755) < 0) {
        snprintf(error_buf, error_size, "mkdir private uio0 map0: %s", strerror(errno));
        return -1;
    }
    if (read_small_file_trim("/sys/class/uio/uio0/dev", dev_text, sizeof(dev_text)) < 0 ||
        sscanf(dev_text, "%u:%u", &major_no, &minor_no) != 2) {
        snprintf(error_buf, error_size, "parse uio0 dev: %s", strerror(errno));
        return -1;
    }
    if (append_path(dest, sizeof(dest), uio0_dir, "name") < 0 ||
        copy_sysfs_text_file("/sys/class/uio/uio0/name", dest, error_buf, error_size) < 0) {
        return -1;
    }
    if (append_path(dest, sizeof(dest), uio0_dir, "version") < 0 ||
        copy_sysfs_text_file("/sys/class/uio/uio0/version", dest, error_buf, error_size) < 0) {
        return -1;
    }
    if (append_path(dest, sizeof(dest), uio0_dir, "dev") < 0 ||
        copy_sysfs_text_file("/sys/class/uio/uio0/dev", dest, error_buf, error_size) < 0) {
        return -1;
    }
    if (append_path(dest, sizeof(dest), map0_dir, "addr") < 0 ||
        copy_sysfs_text_file("/sys/class/uio/uio0/maps/map0/addr", dest, error_buf, error_size) < 0) {
        return -1;
    }
    if (append_path(dest, sizeof(dest), map0_dir, "size") < 0 ||
        copy_sysfs_text_file("/sys/class/uio/uio0/maps/map0/size", dest, error_buf, error_size) < 0) {
        return -1;
    }
    if (append_path(dest, sizeof(dest), map0_dir, "name") < 0 ||
        copy_sysfs_text_file("/sys/class/uio/uio0/maps/map0/name", dest, error_buf, error_size) < 0) {
        return -1;
    }
    if (append_path(dest, sizeof(dest), map0_dir, "offset") < 0 ||
        copy_sysfs_text_file("/sys/class/uio/uio0/maps/map0/offset", dest, error_buf, error_size) < 0) {
        return -1;
    }
    if (unlink(paths->dev_uio0) < 0 && errno != ENOENT) {
        snprintf(error_buf, error_size, "unlink dev uio0: %s", strerror(errno));
        return -1;
    }
    if (mknod(paths->dev_uio0, S_IFCHR | 0660, makedev(major_no, minor_no)) < 0) {
        snprintf(error_buf, error_size, "mknod dev uio0: %s", strerror(errno));
        return -1;
    }
    if (chmod(paths->dev_uio0, 0660) < 0) {
        snprintf(error_buf, error_size, "chmod dev uio0: %s", strerror(errno));
        return -1;
    }
    return 0;
}

static int bind_optional_ro_dir(const char *source,
                                const char *target,
                                const char *label,
                                char *error_buf,
                                size_t error_size) {
    struct stat st;

    if (stat(source, &st) < 0) {
        if (errno == ENOENT || errno == ENOTDIR) {
            return 0;
        }
        snprintf(error_buf, error_size, "stat %s: %s", label, strerror(errno));
        return -1;
    }
    if (!S_ISDIR(st.st_mode)) {
        snprintf(error_buf, error_size, "%s is not a directory", label);
        errno = ENOTDIR;
        return -1;
    }
    if (mkdir_p(target, 0755) < 0) {
        snprintf(error_buf, error_size, "mkdir private %s: %s", label, strerror(errno));
        return -1;
    }
    if (bind_ro(source, target) < 0) {
        snprintf(error_buf, error_size, "bind private %s: %s", label, strerror(errno));
        return -1;
    }
    return 0;
}

static int materialize_rmt_modem_detect_surface(const struct paths *paths,
                                                char *error_buf,
                                                size_t error_size) {
    if (bind_optional_ro_dir("/sys/devices/platform/soc/soc:qcom,mdm3",
                             paths->sys_devices_platform_soc_mdm3,
                             "mdm3 sysfs",
                             error_buf,
                             error_size) < 0) {
        return -1;
    }
    if (bind_optional_ro_dir("/sys/devices/platform/soc/4080000.qcom,mss",
                             paths->sys_devices_platform_soc_mss,
                             "mss sysfs",
                             error_buf,
                             error_size) < 0) {
        return -1;
    }
    if (bind_optional_ro_dir("/sys/bus/esoc",
                             paths->sys_bus_esoc,
                             "esoc bus sysfs",
                             error_buf,
                             error_size) < 0) {
        return -1;
    }
    if (bind_optional_ro_dir("/sys/bus/msm_subsys",
                             paths->sys_bus_msm_subsys,
                             "msm_subsys bus sysfs",
                             error_buf,
                             error_size) < 0) {
        return -1;
    }
    return 0;
}

static int materialize_rmt_storage_runtime_surface(const struct config *cfg,
                                                   const struct paths *paths,
                                                   char *error_buf,
                                                   size_t error_size) {
    static const struct rmt_block_partition partitions[] = {
        {"modemst1", true},
        {"modemst2", true},
        {"fsc", true},
        {"fsg", true},
        {"ssd", false},
    };

    if (!is_rmt_storage_start_only_mode(cfg->mode) &&
        !is_wifi_companion_any_start_only_mode(cfg->mode) &&
        !is_wifi_companion_hal_order_start_only_mode(cfg->mode)) {
        return 0;
    }
    if (mkdir_p(paths->dev_block, 0755) < 0 ||
        mkdir_p(paths->dev_block_by_name, 0755) < 0 ||
        mkdir_p(paths->dev_block_bootdevice_by_name, 0755) < 0) {
        snprintf(error_buf, error_size, "mkdir rmt dev block surface: %s", strerror(errno));
        return -1;
    }
    for (size_t i = 0; i < sizeof(partitions) / sizeof(partitions[0]); i++) {
        if (materialize_one_rmt_block_alias(paths,
                                            partitions[i].partname,
                                            partitions[i].required,
                                            error_buf,
                                            error_size) < 0) {
            return -1;
        }
    }
    if (materialize_rmt_uio_surface(paths, error_buf, error_size) < 0) {
        return -1;
    }
    if (materialize_rmt_modem_detect_surface(paths, error_buf, error_size) < 0) {
        return -1;
    }
    if (unlink(paths->dev_kmsg) < 0 && errno != ENOENT) {
        snprintf(error_buf, error_size, "unlink dev kmsg: %s", strerror(errno));
        return -1;
    }
    if (mknod(paths->dev_kmsg, S_IFCHR | 0600, makedev(1, 11)) < 0) {
        snprintf(error_buf, error_size, "mknod dev kmsg: %s", strerror(errno));
        return -1;
    }
    if (mkdir_p(paths->sys_power, 0755) < 0) {
        snprintf(error_buf, error_size, "mkdir sys power: %s", strerror(errno));
        return -1;
    }
    if (write_empty_private_file(paths->sys_power_wake_lock, 0666) < 0 ||
        write_empty_private_file(paths->sys_power_wake_unlock, 0666) < 0) {
        snprintf(error_buf, error_size, "create private wakelock files: %s", strerror(errno));
        return -1;
    }
    return 0;
}

static bool rfkill_wifi_like(const char *name) {
    char type_path[MAX_PATH_LEN];
    char type_value[64];
    int rc;

    if (name == NULL || snprintf(type_path, sizeof(type_path), "/sys/class/rfkill/%s/type", name) < 0) {
        return false;
    }
    if (strlen(type_path) >= sizeof(type_path) - 1) {
        return false;
    }
    rc = read_small_file_trim(type_path, type_value, sizeof(type_value));
    if (rc < 0) {
        return false;
    }
    return strstr(type_value, "wlan") != NULL ||
           strstr(type_value, "wifi") != NULL ||
           strstr(type_value, "wireless") != NULL;
}

static int count_proc_net_wireless(char names[][64], size_t max_names, size_t *count_out) {
    FILE *file = fopen("/proc/net/wireless", "re");
    char line[256];
    size_t count = 0;

    *count_out = 0;
    if (file == NULL) {
        return -1;
    }
    while (fgets(line, sizeof(line), file) != NULL) {
        char *colon = strchr(line, ':');
        char *start = line;
        size_t len;

        if (colon == NULL) {
            continue;
        }
        while (*start == ' ' || *start == '\t') {
            start++;
        }
        len = (size_t)(colon - start);
        if (len == 0 || len >= 64) {
            continue;
        }
        if (count < max_names) {
            memcpy(names[count], start, len);
            names[count][len] = '\0';
        }
        count++;
    }
    fclose(file);
    *count_out = count;
    return 0;
}

static int append_wifi_surface_snapshot(struct buffer *buf, const char *prefix) {
    char wlan_names[16][64];
    char phy_names_buf[16][64];
    char wireless_names[16][64];
    char rfkill_names[16][64];
    size_t wlan_count = 0;
    size_t phy_count = 0;
    size_t wireless_count = 0;
    size_t rfkill_count = 0;
    int wlan_rc = collect_matching_dir_names("/sys/class/net", wifi_surface_iface_name, wlan_names, 16, &wlan_count);
    int phy_rc = collect_matching_dir_names("/sys/class/ieee80211", phy_name, phy_names_buf, 16, &phy_count);
    int wireless_rc = count_proc_net_wireless(wireless_names, 16, &wireless_count);
    int rfkill_rc = collect_matching_dir_names("/sys/class/rfkill", rfkill_wifi_like, rfkill_names, 16, &rfkill_count);

    if (append_format(buf, "%s.wlan_count=%zu\n", prefix, wlan_rc == 0 ? wlan_count : 0) < 0 ||
        append_format(buf, "%s.wlan_rc=%d\n", prefix, wlan_rc) < 0 ||
        append_limited_csv(buf, prefix, "wlan_names", wlan_names, wlan_rc == 0 && wlan_count < 16 ? wlan_count : 16) < 0 ||
        append_format(buf, "%s.phy_count=%zu\n", prefix, phy_rc == 0 ? phy_count : 0) < 0 ||
        append_format(buf, "%s.phy_rc=%d\n", prefix, phy_rc) < 0 ||
        append_limited_csv(buf, prefix, "phy_names", phy_names_buf, phy_rc == 0 && phy_count < 16 ? phy_count : 16) < 0 ||
        append_format(buf, "%s.proc_wireless_count=%zu\n", prefix, wireless_rc == 0 ? wireless_count : 0) < 0 ||
        append_format(buf, "%s.proc_wireless_rc=%d\n", prefix, wireless_rc) < 0 ||
        append_limited_csv(buf, prefix, "proc_wireless_names", wireless_names, wireless_rc == 0 && wireless_count < 16 ? wireless_count : 16) < 0 ||
        append_format(buf, "%s.wifi_rfkill_count=%zu\n", prefix, rfkill_rc == 0 ? rfkill_count : 0) < 0 ||
        append_format(buf, "%s.wifi_rfkill_rc=%d\n", prefix, rfkill_rc) < 0 ||
        append_limited_csv(buf, prefix, "wifi_rfkill_names", rfkill_names, rfkill_rc == 0 && rfkill_count < 16 ? rfkill_count : 16) < 0) {
        return -1;
    }
    return 0;
}

static const char *runtime_path_type(mode_t mode) {
    if (S_ISREG(mode)) return "regular";
    if (S_ISDIR(mode)) return "directory";
    if (S_ISLNK(mode)) return "symlink";
    if (S_ISCHR(mode)) return "char";
    if (S_ISBLK(mode)) return "block";
    if (S_ISSOCK(mode)) return "socket";
    if (S_ISFIFO(mode)) return "fifo";
    return "other";
}

static int append_runtime_path_status(struct buffer *buf,
                                      const char *prefix,
                                      const char *scope,
                                      const char *label,
                                      const char *path) {
    char link_target[MAX_PATH_LEN];
    struct stat st;
    ssize_t nreadlink;

    if (append_format(buf,
                      "%s.%s.%s.path=%s\n",
                      prefix,
                      scope,
                      label,
                      path) < 0) {
        return -1;
    }
    if (lstat(path, &st) < 0) {
        return append_format(buf,
                             "%s.%s.%s.exists=0\n"
                             "%s.%s.%s.errno=%d\n",
                             prefix,
                             scope,
                             label,
                             prefix,
                             scope,
                             label,
                             errno);
    }
    if (append_format(buf,
                      "%s.%s.%s.exists=1\n"
                      "%s.%s.%s.uid=%u\n"
                      "%s.%s.%s.gid=%u\n"
                      "%s.%s.%s.mode=%o\n"
                      "%s.%s.%s.type=%s\n"
                      "%s.%s.%s.size=%lld\n"
                      "%s.%s.%s.access_r=%d\n"
                      "%s.%s.%s.access_w=%d\n"
                      "%s.%s.%s.access_x=%d\n",
                      prefix, scope, label,
                      prefix, scope, label, (unsigned int)st.st_uid,
                      prefix, scope, label, (unsigned int)st.st_gid,
                      prefix, scope, label, st.st_mode & 07777,
                      prefix, scope, label, runtime_path_type(st.st_mode),
                      prefix, scope, label, (long long)st.st_size,
                      prefix, scope, label, access(path, R_OK) == 0 ? 1 : 0,
                      prefix, scope, label, access(path, W_OK) == 0 ? 1 : 0,
                      prefix, scope, label, access(path, X_OK) == 0 ? 1 : 0) < 0) {
        return -1;
    }
    if (S_ISCHR(st.st_mode) || S_ISBLK(st.st_mode)) {
        if (append_format(buf,
                          "%s.%s.%s.rdev=%u:%u\n",
                          prefix,
                          scope,
                          label,
                          major(st.st_rdev),
                          minor(st.st_rdev)) < 0) {
            return -1;
        }
    }
    nreadlink = readlink(path, link_target, sizeof(link_target) - 1);
    if (nreadlink >= 0) {
        link_target[nreadlink] = '\0';
        if (append_format(buf,
                          "%s.%s.%s.readlink=%s\n",
                          prefix,
                          scope,
                          label,
                          link_target) < 0) {
            return -1;
        }
    }
    return 0;
}

static int append_private_runtime_path_status(struct buffer *buf,
                                              const struct paths *paths,
                                              const char *prefix,
                                              const char *label,
                                              const char *absolute_path) {
    char host_path[MAX_PATH_LEN];

    if (path_in_root(host_path, sizeof(host_path), paths, absolute_path) < 0) {
        return append_format(buf,
                             "%s.private.%s.absolute=%s\n"
                             "%s.private.%s.error=path-too-long\n",
                             prefix,
                             label,
                             absolute_path,
                             prefix,
                             label);
    }
    if (append_format(buf,
                      "%s.private.%s.absolute=%s\n"
                      "%s.private.%s.host_path=%s\n",
                      prefix,
                      label,
                      absolute_path,
                      prefix,
                      label,
                      host_path) < 0) {
        return -1;
    }
    return append_runtime_path_status(buf, prefix, "private", label, host_path);
}

static int append_wifi_runtime_surface_snapshot(struct buffer *buf,
                                                const struct paths *paths,
                                                const char *prefix) {
    static const struct {
        const char *label;
        const char *path;
    } runtime_paths[] = {
        { "dev_socket_wifihal", "/dev/socket/wifihal" },
        { "dev_socket_wifihal_ctrlsock", "/dev/socket/wifihal/wifihal_ctrlsock" },
        { "dev_socket_wpa_wlan0", "/dev/socket/wpa_wlan0" },
        { "dev_wlan", "/dev/wlan" },
        { "data_vendor_wifi", "/data/vendor/wifi" },
        { "data_vendor_wifi_sockets", "/data/vendor/wifi/sockets" },
        { "data_vendor_wifi_sockets_wlan0", "/data/vendor/wifi/sockets/wlan0" },
        { "sys_class_net_wlan0", "/sys/class/net/wlan0" },
    };

    if (append_format(buf,
                      "%s.begin=1\n"
                      "%s.path_count=%zu\n",
                      prefix,
                      prefix,
                      sizeof(runtime_paths) / sizeof(runtime_paths[0])) < 0) {
        return -1;
    }
    for (size_t i = 0; i < sizeof(runtime_paths) / sizeof(runtime_paths[0]); i++) {
        if (append_runtime_path_status(buf,
                                       prefix,
                                       "host",
                                       runtime_paths[i].label,
                                       runtime_paths[i].path) < 0 ||
            append_private_runtime_path_status(buf,
                                               paths,
                                               prefix,
                                               runtime_paths[i].label,
                                               runtime_paths[i].path) < 0) {
            return -1;
        }
    }
    return append_format(buf, "%s.end=1\n", prefix);
}

static size_t align_up_size(size_t value, size_t alignment) {
    return (value + alignment - 1U) & ~(alignment - 1U);
}

static int hwbinder_parcel_write(struct a90_hwbinder_parcel *parcel,
                                 const void *data,
                                 size_t len,
                                 size_t align) {
    size_t padded = align_up_size(len, align);

    if (parcel->data_size + padded > sizeof(parcel->data)) {
        errno = ENOSPC;
        return -1;
    }
    memcpy(parcel->data + parcel->data_size, data, len);
    if (padded > len) {
        memset(parcel->data + parcel->data_size + len, 0, padded - len);
    }
    parcel->data_size += padded;
    return 0;
}

static int hwbinder_parcel_write_int32(struct a90_hwbinder_parcel *parcel,
                                       int32_t value) {
    return hwbinder_parcel_write(parcel, &value, sizeof(value), 4U);
}

static int hwbinder_parcel_write_string16_ascii(struct a90_hwbinder_parcel *parcel,
                                                const char *text) {
    uint32_t len = (uint32_t)strlen(text);
    uint16_t chars[256];

    if ((size_t)len >= sizeof(chars) / sizeof(chars[0])) {
        errno = ENAMETOOLONG;
        return -1;
    }
    if (hwbinder_parcel_write_int32(parcel, (int32_t)len) < 0) {
        return -1;
    }
    for (uint32_t i = 0; i < len; i++) {
        chars[i] = (uint16_t)(uint8_t)text[i];
    }
    chars[len] = 0;
    return hwbinder_parcel_write(parcel, chars, ((size_t)len + 1U) * sizeof(chars[0]), 4U);
}

static int hwbinder_parcel_write_cstring(struct a90_hwbinder_parcel *parcel,
                                         const char *text) {
    return hwbinder_parcel_write(parcel, text, strlen(text) + 1U, 4U);
}

static const char *hwbinder_token_wire_name(enum a90_hwbinder_token_wire token_wire) {
    switch (token_wire) {
    case A90_HWBINDER_TOKEN_STRING16_STRICTMODE:
        return "string16-strictmode";
    case A90_HWBINDER_TOKEN_CSTRING:
        return "cstring";
    }
    return "unknown";
}

static int hwbinder_parcel_write_interface_token(struct a90_hwbinder_parcel *parcel,
                                                 const char *descriptor,
                                                 enum a90_hwbinder_token_wire token_wire) {
    switch (token_wire) {
    case A90_HWBINDER_TOKEN_STRING16_STRICTMODE:
        if (hwbinder_parcel_write_int32(parcel, A90_STRICT_MODE_PENALTY_GATHER) < 0) {
            return -1;
        }
        return hwbinder_parcel_write_string16_ascii(parcel, descriptor);
    case A90_HWBINDER_TOKEN_CSTRING:
        return hwbinder_parcel_write_cstring(parcel, descriptor);
    }
    errno = EINVAL;
    return -1;
}

static int hwbinder_parcel_write_buffer_object(struct a90_hwbinder_parcel *parcel,
                                               struct binder_buffer_object *object,
                                               size_t *handle_out) {
    size_t offset;
    size_t aligned_len;

    if (parcel->offsets_count >= A90_HWBINDER_OBJECT_MAX) {
        errno = ENOSPC;
        return -1;
    }
    offset = parcel->data_size;
    parcel->offsets[parcel->offsets_count] = (binder_size_t)offset;
    if (handle_out != NULL) {
        *handle_out = parcel->offsets_count;
    }
    parcel->offsets_count++;
    if (hwbinder_parcel_write(parcel, object, sizeof(*object), 8U) < 0) {
        return -1;
    }
    if ((object->flags & BINDER_BUFFER_FLAG_REF) == 0 && object->buffer != 0) {
        aligned_len = align_up_size((size_t)object->length, 8U);
        if (aligned_len > SIZE_MAX - parcel->buffers_size) {
            errno = EOVERFLOW;
            return -1;
        }
        parcel->buffers_size += aligned_len;
    }
    return 0;
}

static int hwbinder_parcel_write_hidl_string(struct a90_hwbinder_parcel *parcel,
                                             const char *text) {
    struct a90_hidl_string_wire *wire;
    struct binder_buffer_object parent;
    struct binder_buffer_object child;
    size_t parent_handle = 0;

    if (parcel->string_count >= sizeof(parcel->strings) / sizeof(parcel->strings[0])) {
        errno = ENOSPC;
        return -1;
    }
    wire = &parcel->strings[parcel->string_count++];
    memset(wire, 0, sizeof(*wire));
    wire->buffer = (binder_uintptr_t)(uintptr_t)text;
    wire->size = (uint32_t)strlen(text);

    memset(&parent, 0, sizeof(parent));
    parent.hdr.type = BINDER_TYPE_PTR;
    parent.buffer = (binder_uintptr_t)(uintptr_t)wire;
    parent.length = sizeof(*wire);
    parent.flags = 0;
    if (hwbinder_parcel_write_buffer_object(parcel, &parent, &parent_handle) < 0) {
        return -1;
    }

    memset(&child, 0, sizeof(child));
    child.hdr.type = BINDER_TYPE_PTR;
    child.buffer = (binder_uintptr_t)(uintptr_t)text;
    child.length = strlen(text) + 1U;
    child.flags = BINDER_BUFFER_FLAG_HAS_PARENT;
    child.parent = parent_handle;
    child.parent_offset = 0;
    return hwbinder_parcel_write_buffer_object(parcel, &child, NULL);
}

static int hwbinder_build_get_iwifi_parcel(struct a90_hwbinder_parcel *parcel,
                                           const char *manager_descriptor,
                                           enum a90_hwbinder_token_wire token_wire) {
    memset(parcel, 0, sizeof(*parcel));
    if (hwbinder_parcel_write_interface_token(parcel, manager_descriptor, token_wire) < 0 ||
        hwbinder_parcel_write_hidl_string(parcel, "android.hardware.wifi@1.0::IWifi") < 0 ||
        hwbinder_parcel_write_hidl_string(parcel, "default") < 0) {
        return -1;
    }
    return 0;
}

static int hwbinder_build_iwifi_start_parcel(struct a90_hwbinder_parcel *parcel,
                                             enum a90_hwbinder_token_wire token_wire) {
    memset(parcel, 0, sizeof(*parcel));
    return hwbinder_parcel_write_interface_token(parcel, "android.hardware.wifi@1.0::IWifi", token_wire);
}

static int hwbinder_write_read(int fd,
                               const void *write_data,
                               size_t write_size,
                               void *read_data,
                               size_t read_size) {
    struct binder_write_read bwr;

    memset(&bwr, 0, sizeof(bwr));
    bwr.write_size = write_size;
    bwr.write_buffer = (binder_uintptr_t)(uintptr_t)write_data;
    bwr.read_size = read_size;
    bwr.read_buffer = (binder_uintptr_t)(uintptr_t)read_data;
    do {
        if (ioctl(fd, BINDER_WRITE_READ, &bwr) == 0) {
            return (int)bwr.read_consumed;
        }
    } while (errno == EINTR);
    return -1;
}

static int hwbinder_write_command_payload(int fd,
                                          uint32_t command,
                                          const void *payload,
                                          size_t payload_size) {
    uint8_t write_data[sizeof(uint32_t) + sizeof(struct binder_transaction_data_sg)];

    if (payload_size > sizeof(write_data) - sizeof(command)) {
        errno = EMSGSIZE;
        return -1;
    }
    memcpy(write_data, &command, sizeof(command));
    if (payload_size > 0) {
        memcpy(write_data + sizeof(command), payload, payload_size);
    }
    return hwbinder_write_read(fd, write_data, sizeof(command) + payload_size, NULL, 0);
}

static int hwbinder_send_transaction(int fd,
                                     uint32_t handle,
                                     uint32_t code,
                                     const struct a90_hwbinder_parcel *parcel) {
    struct binder_transaction_data_sg txn;

    memset(&txn, 0, sizeof(txn));
    txn.transaction_data.target.handle = handle;
    txn.transaction_data.code = code;
    txn.transaction_data.flags = TF_ACCEPT_FDS;
    txn.transaction_data.data_size = parcel->data_size;
    txn.transaction_data.offsets_size = parcel->offsets_count * sizeof(parcel->offsets[0]);
    txn.transaction_data.data.ptr.buffer = (binder_uintptr_t)(uintptr_t)parcel->data;
    txn.transaction_data.data.ptr.offsets = (binder_uintptr_t)(uintptr_t)parcel->offsets;
    txn.buffers_size = parcel->buffers_size;
    return hwbinder_write_command_payload(fd, BC_TRANSACTION_SG, &txn, sizeof(txn));
}

static int hwbinder_write_handle_command(int fd, uint32_t command, uint32_t handle) {
    return hwbinder_write_command_payload(fd, command, &handle, sizeof(handle));
}

static int hwbinder_acquire_handle(int fd, uint32_t handle, struct buffer *stdout_buf, const char *prefix) {
    int weak_rc = hwbinder_write_handle_command(fd, BC_INCREFS, handle);
    int strong_rc = hwbinder_write_handle_command(fd, BC_ACQUIRE, handle);

    append_format(stdout_buf,
                  "%s.acquire.handle=%u\n"
                  "%s.acquire.weak_rc=%d\n"
                  "%s.acquire.strong_rc=%d\n",
                  prefix,
                  handle,
                  prefix,
                  weak_rc,
                  prefix,
                  strong_rc);
    return weak_rc < 0 || strong_rc < 0 ? -1 : 0;
}

static const char *hwbinder_status_name(int32_t status_value) {
    switch (status_value) {
    case 0:
        return "OK";
    case -2147483647:
        return "BAD_TYPE";
    case -2147483646:
        return "FAILED_TRANSACTION";
    case -74:
        return "UNKNOWN_TRANSACTION";
    case -22:
        return "BAD_VALUE";
    case -1:
        return "PERMISSION_DENIED";
    default:
        return "UNKNOWN";
    }
}

static void hwbinder_reply_clear(struct a90_hwbinder_reply *reply) {
    memset(reply, 0, sizeof(*reply));
}

static int hwbinder_read_reply(int fd,
                               struct a90_hwbinder_reply *reply,
                               int timeout_ms,
                               struct buffer *stdout_buf,
                               const char *prefix) {
    uint8_t read_buf[A90_HWBINDER_READ_MAX];
    long deadline = monotonic_ms() + timeout_ms;

    hwbinder_reply_clear(reply);
    while (monotonic_ms() < deadline) {
        struct pollfd pfd;
        int poll_rc;
        int consumed;
        uint8_t *cursor;
        uint8_t *end;
        int remaining = (int)(deadline - monotonic_ms());

        if (remaining < 1) {
            remaining = 1;
        }
        memset(&pfd, 0, sizeof(pfd));
        pfd.fd = fd;
        pfd.events = POLLIN;
        poll_rc = poll(&pfd, 1, remaining > 250 ? 250 : remaining);
        if (poll_rc < 0) {
            if (errno == EINTR) {
                continue;
            }
            append_format(stdout_buf, "%s.poll.error=%s\n", prefix, strerror(errno));
            return -1;
        }
        if (poll_rc == 0) {
            continue;
        }
        memset(read_buf, 0, sizeof(read_buf));
        consumed = hwbinder_write_read(fd, NULL, 0, read_buf, sizeof(read_buf));
        if (consumed < 0) {
            append_format(stdout_buf, "%s.read.error=%s\n", prefix, strerror(errno));
            return -1;
        }
        cursor = read_buf;
        end = read_buf + consumed;
        while (cursor + sizeof(uint32_t) <= end) {
            uint32_t command;

            memcpy(&command, cursor, sizeof(command));
            cursor += sizeof(command);
            if (command == BR_NOOP || command == BR_TRANSACTION_COMPLETE) {
                append_format(stdout_buf, "%s.driver_command=0x%08x\n", prefix, command);
                continue;
            }
            if (command == BR_REPLY) {
                struct binder_transaction_data txn;

                if (cursor + sizeof(txn) > end) {
                    append_format(stdout_buf, "%s.reply.truncated=1\n", prefix);
                    return -1;
                }
                memcpy(&txn, cursor, sizeof(txn));
                reply->data = (uint8_t *)(uintptr_t)txn.data.ptr.buffer;
                reply->offsets = (binder_size_t *)(uintptr_t)txn.data.ptr.offsets;
                reply->data_size = (size_t)txn.data_size;
                reply->offsets_count = (size_t)(txn.offsets_size / sizeof(binder_size_t));
                reply->free_buffer = txn.data.ptr.buffer;
                reply->has_free_buffer = txn.data.ptr.buffer != 0;
                reply->status_code = (txn.flags & TF_STATUS_CODE) != 0;
                if (reply->status_code && reply->data != NULL && reply->data_size >= sizeof(int32_t)) {
                    memcpy(&reply->status_value, reply->data, sizeof(reply->status_value));
                }
                append_format(stdout_buf,
                              "%s.reply.data_size=%zu\n"
                              "%s.reply.offsets_count=%zu\n"
                              "%s.reply.status_code=%d\n"
                              "%s.reply.status_value=%d\n"
                              "%s.reply.status_name=%s\n",
                              prefix,
                              reply->data_size,
                              prefix,
                              reply->offsets_count,
                              prefix,
                              reply->status_code ? 1 : 0,
                              prefix,
                              reply->status_value,
                              prefix,
                              hwbinder_status_name(reply->status_value));
                return 0;
            }
            if (command == BR_FAILED_REPLY) {
                reply->failed_reply = true;
                append_format(stdout_buf, "%s.failed_reply=1\n", prefix);
                return 0;
            }
            if (command == BR_DEAD_REPLY) {
                reply->dead_reply = true;
                append_format(stdout_buf, "%s.dead_reply=1\n", prefix);
                return 0;
            }
            if (command == BR_FROZEN_REPLY) {
                reply->frozen_reply = true;
                append_format(stdout_buf, "%s.frozen_reply=1\n", prefix);
                return 0;
            }
            if (command == BR_ERROR && cursor + sizeof(int32_t) <= end) {
                int32_t error_value;

                memcpy(&error_value, cursor, sizeof(error_value));
                append_format(stdout_buf, "%s.br_error=%d\n", prefix, error_value);
                return -1;
            }
            append_format(stdout_buf, "%s.unhandled_driver_command=0x%08x\n", prefix, command);
            return -1;
        }
    }
    append_format(stdout_buf, "%s.timeout=1\n", prefix);
    return 12;
}

static int hwbinder_free_reply_buffer(int fd, const struct a90_hwbinder_reply *reply) {
    binder_uintptr_t buffer;

    if (!reply->has_free_buffer) {
        return 0;
    }
    buffer = reply->free_buffer;
    return hwbinder_write_command_payload(fd, BC_FREE_BUFFER, &buffer, sizeof(buffer));
}

static bool hwbinder_reply_find_handle(const struct a90_hwbinder_reply *reply,
                                       uint32_t *handle_out,
                                       bool *null_out) {
    if (reply->data == NULL || reply->status_code) {
        return false;
    }
    for (size_t i = 0; i < reply->offsets_count; i++) {
        binder_size_t offset = reply->offsets[i];
        struct flat_binder_object object;

        if ((size_t)offset + sizeof(object) > reply->data_size) {
            continue;
        }
        memcpy(&object, reply->data + offset, sizeof(object));
        if (object.hdr.type == BINDER_TYPE_HANDLE) {
            *handle_out = object.handle;
            *null_out = false;
            return true;
        }
        if (object.hdr.type == BINDER_TYPE_BINDER && object.binder == 0 && object.cookie == 0) {
            *handle_out = 0;
            *null_out = true;
            return true;
        }
    }
    for (size_t offset = 0; offset + sizeof(struct flat_binder_object) <= reply->data_size; offset += 4U) {
        struct flat_binder_object object;

        memcpy(&object, reply->data + offset, sizeof(object));
        if (object.hdr.type == BINDER_TYPE_BINDER && object.binder == 0 && object.cookie == 0) {
            *handle_out = 0;
            *null_out = true;
            return true;
        }
    }
    return false;
}

static const char *wifi_status_code_name(uint32_t code) {
    switch (code) {
    case 0:
        return "SUCCESS";
    case 1:
        return "ERROR_WIFI_CHIP_INVALID";
    case 2:
        return "ERROR_WIFI_IFACE_INVALID";
    case 3:
        return "ERROR_WIFI_RTT_CONTROLLER_INVALID";
    case 4:
        return "ERROR_NOT_SUPPORTED";
    case 5:
        return "ERROR_NOT_AVAILABLE";
    case 6:
        return "ERROR_NOT_STARTED";
    case 7:
        return "ERROR_INVALID_ARGS";
    case 8:
        return "ERROR_BUSY";
    case 9:
        return "ERROR_UNKNOWN";
    default:
        return "UNKNOWN";
    }
}

static bool hwbinder_reply_decode_wifi_status(const struct a90_hwbinder_reply *reply,
                                              struct buffer *stdout_buf,
                                              const char *prefix,
                                              uint32_t *code_out) {
    bool decoded = false;

    if (reply->data == NULL || reply->status_code) {
        append_format(stdout_buf, "%s.wifi_status.decoded=0\n", prefix);
        return false;
    }
    for (size_t i = 0; i < reply->offsets_count; i++) {
        binder_size_t offset = reply->offsets[i];
        struct binder_buffer_object object;

        if ((size_t)offset + sizeof(object) > reply->data_size) {
            append_format(stdout_buf, "%s.object.%zu.truncated=1\n", prefix, i);
            continue;
        }
        memcpy(&object, reply->data + offset, sizeof(object));
        append_format(stdout_buf,
                      "%s.object.%zu.offset=%zu\n"
                      "%s.object.%zu.type=0x%08x\n"
                      "%s.object.%zu.buffer=0x%llx\n"
                      "%s.object.%zu.length=%llu\n"
                      "%s.object.%zu.flags=0x%08x\n",
                      prefix,
                      i,
                      (size_t)offset,
                      prefix,
                      i,
                      object.hdr.type,
                      prefix,
                      i,
                      (unsigned long long)object.buffer,
                      prefix,
                      i,
                      (unsigned long long)object.length,
                      prefix,
                      i,
                      object.flags);
        if (!decoded &&
            object.hdr.type == BINDER_TYPE_PTR &&
            object.buffer != 0 &&
            object.length >= sizeof(struct a90_wifi_status_wire)) {
            struct a90_wifi_status_wire status_wire;

            memcpy(&status_wire, (const void *)(uintptr_t)object.buffer, sizeof(status_wire));
            *code_out = status_wire.code;
            decoded = true;
            append_format(stdout_buf,
                          "%s.wifi_status.decoded=1\n"
                          "%s.wifi_status.code=%u\n"
                          "%s.wifi_status.name=%s\n"
                          "%s.wifi_status.description_size=%u\n",
                          prefix,
                          prefix,
                          status_wire.code,
                          prefix,
                          wifi_status_code_name(status_wire.code),
                          prefix,
                          status_wire.description.size);
            if (status_wire.description.buffer != 0 && status_wire.description.size > 0) {
                char desc[129];
                size_t desc_len = status_wire.description.size;

                if (desc_len >= sizeof(desc)) {
                    desc_len = sizeof(desc) - 1U;
                }
                memcpy(desc, (const void *)(uintptr_t)status_wire.description.buffer, desc_len);
                desc[desc_len] = '\0';
                append_format(stdout_buf, "%s.wifi_status.description=%s\n", prefix, desc);
            }
        }
    }
    if (!decoded) {
        append_format(stdout_buf, "%s.wifi_status.decoded=0\n", prefix);
    }
    return decoded;
}

static int run_iwifi_start_hwbinder_probe(const struct paths *paths,
                                          struct buffer *stdout_buf) {
    static const char *const manager_descriptors[] = {
        "android.hidl.manager@1.2::IServiceManager",
        "android.hidl.manager@1.1::IServiceManager",
        "android.hidl.manager@1.0::IServiceManager",
    };
    static const enum a90_hwbinder_token_wire token_wires[] = {
        A90_HWBINDER_TOKEN_STRING16_STRICTMODE,
        A90_HWBINDER_TOKEN_CSTRING,
    };
    const int get_timeout_ms = 500;
    int fd;
    void *binder_vm = MAP_FAILED;
    struct binder_version version;
    uint32_t service_handle = 0;
    bool service_null = false;
    bool service_found = false;
    bool service_retained = false;
    bool start_transaction_ok = false;
    enum a90_hwbinder_token_wire service_token_wire = A90_HWBINDER_TOKEN_STRING16_STRICTMODE;

    append_literal(stdout_buf,
                   "iwifi_start.begin=1\n"
                   "iwifi_start.descriptor=android.hardware.wifi@1.0::IWifi\n"
                   "iwifi_start.instance=default\n"
                   "iwifi_start.get_transaction_code=1\n"
                   "iwifi_start.start_transaction_code=3\n"
                   "iwifi_start.manager_descriptor_order=1.2,1.1,1.0\n"
                   "iwifi_start.interface_token_wire_order=string16-strictmode,cstring\n"
                   "iwifi_start.scan_connect_linkup=0\n"
                   "iwifi_start.credentials=0\n"
                   "iwifi_start.dhcp_routing=0\n");
    fd = open(paths->dev_hwbinder, O_RDWR | O_CLOEXEC);
    if (fd < 0) {
        append_format(stdout_buf,
                      "iwifi_start.open_hwbinder.error=%s\n"
                      "iwifi_start.result=hwbinder-open-failed\n"
                      "iwifi_start.end=1\n",
                      strerror(errno));
        return 10;
    }
    memset(&version, 0, sizeof(version));
    if (ioctl(fd, BINDER_VERSION, &version) == 0) {
        append_format(stdout_buf, "iwifi_start.binder_protocol=%d\n", version.protocol_version);
    } else {
        append_format(stdout_buf, "iwifi_start.binder_version.error=%s\n", strerror(errno));
    }
    binder_vm = mmap(NULL,
                     A90_HWBINDER_VM_SIZE,
                     PROT_READ,
                     MAP_PRIVATE | MAP_NORESERVE,
                     fd,
                     0);
    if (binder_vm == MAP_FAILED) {
        append_format(stdout_buf,
                      "iwifi_start.mmap.ok=0\n"
                      "iwifi_start.mmap.error=%s\n"
                      "iwifi_start.result=hwbinder-mmap-failed\n"
                      "iwifi_start.end=1\n",
                      strerror(errno));
        close(fd);
        return 13;
    }
    append_format(stdout_buf,
                  "iwifi_start.mmap.ok=1\n"
                  "iwifi_start.mmap.size=%d\n",
                  A90_HWBINDER_VM_SIZE);
    hwbinder_acquire_handle(fd, 0, stdout_buf, "iwifi_start.context");
    for (int attempt = 1; attempt <= 5 && !service_found; attempt++) {
        struct a90_hwbinder_parcel parcel;
        struct a90_hwbinder_reply reply;
        int send_rc;
        int read_rc;
        bool null_handle = false;

        for (size_t token_index = 0;
             token_index < sizeof(token_wires) / sizeof(token_wires[0]) && !service_found;
             token_index++) {
            enum a90_hwbinder_token_wire token_wire = token_wires[token_index];

            for (size_t desc_index = 0;
                 desc_index < sizeof(manager_descriptors) / sizeof(manager_descriptors[0]) && !service_found;
                 desc_index++) {
                const char *manager_descriptor = manager_descriptors[desc_index];

                if (hwbinder_build_get_iwifi_parcel(&parcel, manager_descriptor, token_wire) < 0) {
                    append_format(stdout_buf,
                                  "iwifi_start.get.%d.%zu.%zu.build.error=%s\n",
                                  attempt,
                                  token_index,
                                  desc_index,
                                  strerror(errno));
                    munmap(binder_vm, A90_HWBINDER_VM_SIZE);
                    close(fd);
                    return -1;
                }
                append_format(stdout_buf,
                              "iwifi_start.get.%d.%zu.%zu.token_wire=%s\n"
                              "iwifi_start.get.%d.%zu.%zu.manager_descriptor=%s\n"
                              "iwifi_start.get.%d.%zu.%zu.data_size=%zu\n"
                              "iwifi_start.get.%d.%zu.%zu.offsets_count=%zu\n"
                              "iwifi_start.get.%d.%zu.%zu.buffers_size=%zu\n",
                              attempt,
                              token_index,
                              desc_index,
                              hwbinder_token_wire_name(token_wire),
                              attempt,
                              token_index,
                              desc_index,
                              manager_descriptor,
                              attempt,
                              token_index,
                              desc_index,
                              parcel.data_size,
                              attempt,
                              token_index,
                              desc_index,
                              parcel.offsets_count,
                              attempt,
                              token_index,
                              desc_index,
                              parcel.buffers_size);
                send_rc = hwbinder_send_transaction(fd, 0, 1, &parcel);
                append_format(stdout_buf,
                              "iwifi_start.get.%d.%zu.%zu.send_rc=%d\n",
                              attempt,
                              token_index,
                              desc_index,
                              send_rc);
                if (send_rc < 0) {
                    append_format(stdout_buf,
                                  "iwifi_start.get.%d.%zu.%zu.send.error=%s\n",
                                  attempt,
                                  token_index,
                                  desc_index,
                                  strerror(errno));
                    munmap(binder_vm, A90_HWBINDER_VM_SIZE);
                    close(fd);
                    return 11;
                }
                read_rc = hwbinder_read_reply(fd, &reply, get_timeout_ms, stdout_buf, "iwifi_start.get");
                append_format(stdout_buf,
                              "iwifi_start.get.%d.%zu.%zu.read_rc=%d\n",
                              attempt,
                              token_index,
                              desc_index,
                              read_rc);
                if (read_rc == 0 &&
                    !reply.failed_reply &&
                    !reply.dead_reply &&
                    !reply.frozen_reply &&
                    hwbinder_reply_find_handle(&reply, &service_handle, &null_handle)) {
                    bool non_null_handle = !null_handle;

                    service_found = non_null_handle;
                    service_null = null_handle;
                    service_token_wire = token_wire;
                    append_format(stdout_buf,
                                  "iwifi_start.get.%d.%zu.%zu.service_handle_found=%d\n"
                                  "iwifi_start.get.%d.%zu.%zu.service_handle=%u\n"
                                  "iwifi_start.get.%d.%zu.%zu.service_null=%d\n",
                                  attempt,
                                  token_index,
                                  desc_index,
                                  service_found ? 1 : 0,
                                  attempt,
                                  token_index,
                                  desc_index,
                                  service_handle,
                                  attempt,
                                  token_index,
                                  desc_index,
                                  service_null ? 1 : 0);
                    if (non_null_handle) {
                        char retain_prefix[96];
                        int retain_rc;

                        snprintf(retain_prefix,
                                 sizeof(retain_prefix),
                                 "iwifi_start.get.%d.%zu.%zu.service_retain",
                                 attempt,
                                 token_index,
                                 desc_index);
                        retain_rc = hwbinder_acquire_handle(fd, service_handle, stdout_buf, retain_prefix);
                        append_format(stdout_buf,
                                      "iwifi_start.get.%d.%zu.%zu.service_retain_rc=%d\n",
                                      attempt,
                                      token_index,
                                      desc_index,
                                      retain_rc);
                        service_retained = retain_rc == 0;
                        if (!service_retained) {
                            service_found = false;
                            service_handle = 0;
                        }
                    }
                }
                hwbinder_free_reply_buffer(fd, &reply);
            }
        }
        if (!service_found) {
            usleep(200000);
        }
    }
    append_format(stdout_buf,
                  "iwifi_start.service_handle_found=%d\n"
                  "iwifi_start.service_handle=%u\n"
                  "iwifi_start.service_null=%d\n"
                  "iwifi_start.service_token_wire=%s\n"
                  "iwifi_start.service_retained=%d\n",
                  service_found ? 1 : 0,
                  service_handle,
                  service_null ? 1 : 0,
                  hwbinder_token_wire_name(service_token_wire),
                  service_retained ? 1 : 0);
    if (!service_found) {
        append_literal(stdout_buf,
                       "iwifi_start.transaction_executed=0\n"
                       "iwifi_start.result=service-null\n"
                       "iwifi_start.reason=IWifi-default-handle-not-returned\n"
                       "iwifi_start.end=1\n");
        munmap(binder_vm, A90_HWBINDER_VM_SIZE);
        close(fd);
        return 20;
    }
    if (!service_retained &&
        hwbinder_acquire_handle(fd, service_handle, stdout_buf, "iwifi_start.service") == 0) {
        service_retained = true;
    }
    {
        struct a90_hwbinder_parcel parcel;
        struct a90_hwbinder_reply reply;
        int send_rc;
        int read_rc;
        bool start_wifi_status_decoded = false;
        uint32_t start_wifi_status_code = UINT32_MAX;

        if (hwbinder_build_iwifi_start_parcel(&parcel, service_token_wire) < 0) {
            append_format(stdout_buf, "iwifi_start.start.build.error=%s\n", strerror(errno));
            munmap(binder_vm, A90_HWBINDER_VM_SIZE);
            close(fd);
            return -1;
        }
        append_format(stdout_buf,
                      "iwifi_start.start.token_wire=%s\n"
                      "iwifi_start.start.data_size=%zu\n"
                      "iwifi_start.start.offsets_count=%zu\n"
                      "iwifi_start.start.buffers_size=%zu\n",
                      hwbinder_token_wire_name(service_token_wire),
                      parcel.data_size,
                      parcel.offsets_count,
                      parcel.buffers_size);
        send_rc = hwbinder_send_transaction(fd, service_handle, 3, &parcel);
        append_format(stdout_buf,
                      "iwifi_start.transaction_executed=1\n"
                      "iwifi_start.start.send_rc=%d\n",
                      send_rc);
        if (send_rc < 0) {
            append_format(stdout_buf,
                          "iwifi_start.start.send.error=%s\n"
                          "iwifi_start.result=transaction-failed\n"
                          "iwifi_start.reason=start-send-failed\n"
                          "iwifi_start.end=1\n",
                          strerror(errno));
            munmap(binder_vm, A90_HWBINDER_VM_SIZE);
            close(fd);
            return 21;
        }
        read_rc = hwbinder_read_reply(fd, &reply, 1500, stdout_buf, "iwifi_start.start");
        append_format(stdout_buf, "iwifi_start.start.read_rc=%d\n", read_rc);
        if (read_rc == 0 && !reply.failed_reply && !reply.dead_reply && !reply.frozen_reply) {
            if (!reply.status_code || reply.status_value == 0) {
                start_wifi_status_decoded = hwbinder_reply_decode_wifi_status(&reply,
                                                                               stdout_buf,
                                                                               "iwifi_start.start",
                                                                               &start_wifi_status_code);
                start_transaction_ok = !start_wifi_status_decoded || start_wifi_status_code == 0;
            }
        }
        append_format(stdout_buf,
                      "iwifi_start.start.wifi_status_decoded=%d\n"
                      "iwifi_start.start.wifi_status_code=%u\n"
                      "iwifi_start.start.wifi_status_name=%s\n",
                      start_wifi_status_decoded ? 1 : 0,
                      start_wifi_status_decoded ? start_wifi_status_code : UINT32_MAX,
                      start_wifi_status_decoded ? wifi_status_code_name(start_wifi_status_code) : "UNDECODED");
        hwbinder_free_reply_buffer(fd, &reply);
    }
    munmap(binder_vm, A90_HWBINDER_VM_SIZE);
    close(fd);
    append_format(stdout_buf,
                  "iwifi_start.start_transaction_ok=%d\n"
                  "iwifi_start.result=%s\n"
                  "iwifi_start.reason=%s\n"
                  "iwifi_start.end=1\n",
                  start_transaction_ok ? 1 : 0,
                  start_transaction_ok ? "transaction-ok" : "transaction-failed",
                  start_transaction_ok ? "IWifi-start-reply-observed" : "IWifi-start-reply-not-clean");
    return start_transaction_ok ? 0 : 22;
}

static int append_proc_file_capture_named(struct buffer *buf,
                                          pid_t pid,
                                          const char *name,
                                          const char *label,
                                          size_t limit,
                                          bool *captured) {
    char path[MAX_PATH_LEN];
    char tmp[4096];
    size_t total = 0;
    bool truncated = false;
    int fd;

    *captured = false;
    proc_path(path, sizeof(path), pid, name);
    if (append_format(buf, "A90_EXECNS_CNSS_PROC_%s_BEGIN path=%s name=%s limit=%zu\n", label, path, name, limit) < 0) {
        return -1;
    }
    fd = open(path, O_RDONLY | O_CLOEXEC);
    if (fd < 0) {
        if (append_format(buf,
                          "open-error=%s\nA90_EXECNS_CNSS_PROC_%s_END bytes=0 truncated=0\n",
                          strerror(errno),
                          label) < 0) {
            return -1;
        }
        return 0;
    }
    *captured = true;
    while (total < limit) {
        size_t room = limit - total;
        ssize_t nread = read(fd, tmp, room < sizeof(tmp) ? room : sizeof(tmp));

        if (nread < 0) {
            if (errno == EINTR) {
                continue;
            }
            append_format(buf, "\nread-error=%s\n", strerror(errno));
            break;
        }
        if (nread == 0) {
            break;
        }
        if (buffer_append(buf, tmp, (size_t)nread) < 0) {
            close(fd);
            return -1;
        }
        total += (size_t)nread;
    }
    if (total >= limit) {
        truncated = true;
    }
    close(fd);
    if (total == 0 || buf->data[buf->len - 1] != '\n') {
        if (append_literal(buf, "\n") < 0) {
            return -1;
        }
    }
    return append_format(buf,
                         "A90_EXECNS_CNSS_PROC_%s_END bytes=%zu truncated=%d\n",
                         label,
                         total,
                         truncated ? 1 : 0);
}

static int append_proc_file_capture(struct buffer *buf,
                                    pid_t pid,
                                    const char *name,
                                    size_t limit,
                                    bool *captured) {
    return append_proc_file_capture_named(buf, pid, name, name, limit, captured);
}

static int append_path_file_capture_named(struct buffer *buf,
                                          const char *path,
                                          const char *label,
                                          size_t limit,
                                          bool *captured) {
    char tmp[4096];
    size_t total = 0;
    bool truncated = false;
    int fd;

    *captured = false;
    if (append_format(buf, "A90_EXECNS_PATH_%s_BEGIN path=%s limit=%zu\n", label, path, limit) < 0) {
        return -1;
    }
    fd = open(path, O_RDONLY | O_CLOEXEC);
    if (fd < 0) {
        return append_format(buf,
                             "open-error=%s\nA90_EXECNS_PATH_%s_END bytes=0 truncated=0\n",
                             strerror(errno),
                             label);
    }
    while (total < limit) {
        size_t room = limit - total;
        ssize_t nread = read(fd, tmp, room < sizeof(tmp) ? room : sizeof(tmp));

        if (nread < 0) {
            if (errno == EINTR) {
                continue;
            }
            {
                int saved_errno = errno;

                close(fd);
                return append_format(buf,
                                     "read-error=%s\nA90_EXECNS_PATH_%s_END bytes=%zu truncated=0\n",
                                     strerror(saved_errno),
                                     label,
                                     total);
            }
        }
        if (nread == 0) {
            break;
        }
        if (buffer_append(buf, tmp, (size_t)nread) < 0) {
            close(fd);
            return -1;
        }
        total += (size_t)nread;
    }
    if (total >= limit) {
        truncated = true;
    }
    close(fd);
    if (total == 0 || buf->data[buf->len - 1] != '\n') {
        if (append_literal(buf, "\n") < 0) {
            return -1;
        }
    }
    *captured = true;
    return append_format(buf,
                         "A90_EXECNS_PATH_%s_END bytes=%zu truncated=%d\n",
                         label,
                         total,
                         truncated ? 1 : 0);
}

static bool window_surface_entry_interesting(const char *name) {
    return strcasestr(name, "qrtr") != NULL ||
           strcasestr(name, "qmi") != NULL ||
           strcasestr(name, "cnss") != NULL ||
           strcasestr(name, "diag") != NULL ||
           strcasestr(name, "wlan") != NULL ||
           strcasestr(name, "icnss") != NULL ||
           strcasestr(name, "rpmsg") != NULL ||
           strcasestr(name, "subsys") != NULL ||
           strcasestr(name, "modem") != NULL ||
           strcasestr(name, "sysmon") != NULL ||
           strcasestr(name, "service") != NULL;
}

static int append_dir_capture_named(struct buffer *buf,
                                    const char *path,
                                    const char *label,
                                    bool filter_interesting,
                                    int max_entries,
                                    bool *captured) {
    DIR *dir;
    struct dirent *entry;
    int count = 0;
    int shown = 0;
    bool truncated = false;

    *captured = false;
    if (append_format(buf,
                      "A90_EXECNS_DIR_%s_BEGIN path=%s filter=%d max_entries=%d\n",
                      label,
                      path,
                      filter_interesting ? 1 : 0,
                      max_entries) < 0) {
        return -1;
    }
    dir = opendir(path);
    if (dir == NULL) {
        return append_format(buf,
                             "open-error=%s\nA90_EXECNS_DIR_%s_END count=0 shown=0 truncated=0\n",
                             strerror(errno),
                             label);
    }
    while ((entry = readdir(dir)) != NULL) {
        if (strcmp(entry->d_name, ".") == 0 || strcmp(entry->d_name, "..") == 0) {
            continue;
        }
        count++;
        if (filter_interesting && !window_surface_entry_interesting(entry->d_name)) {
            continue;
        }
        if (shown >= max_entries) {
            truncated = true;
            continue;
        }
        if (append_format(buf,
                          "entry.%03d=%s\n",
                          shown,
                          entry->d_name) < 0) {
            closedir(dir);
            return -1;
        }
        shown++;
    }
    closedir(dir);
    *captured = true;
    return append_format(buf,
                         "A90_EXECNS_DIR_%s_END count=%d shown=%d truncated=%d\n",
                         label,
                         count,
                         shown,
                         truncated ? 1 : 0);
}

static int append_wifi_window_surface_capture(struct buffer *buf, const char *phase) {
    bool proc_qrtr_captured = false;
    bool dev_filtered_captured = false;
    bool msm_subsys_captured = false;
    bool rpmsg_captured = false;
    bool rpmsg_drivers_captured = false;
    bool rpmsg_autoprobe_captured = false;
    bool remoteproc_captured = false;
    bool service_notifier_captured = false;
    bool mdm3_captured = false;
    bool mss_captured = false;
    bool mss_subsys0_uevent_captured = false;
    bool mss_subsys0_name_captured = false;
    bool mss_subsys0_state_captured = false;
    bool mss_subsys0_restart_level_captured = false;
    bool mss_subsys0_firmware_name_captured = false;
    bool mss_subsys0_crash_count_captured = false;
    bool mdm3_subsys9_uevent_captured = false;
    bool mdm3_subsys9_name_captured = false;
    bool mdm3_subsys9_state_captured = false;
    bool mdm3_subsys9_restart_level_captured = false;
    bool mdm3_subsys9_firmware_name_captured = false;
    bool mdm3_subsys9_crash_count_captured = false;
    int subsys_value_captures = 0;

    if (append_format(buf, "wifi_companion_start.surface_%s.begin=1\n", phase) < 0 ||
        append_path_file_capture_named(buf,
                                       "/proc/net/qrtr",
                                       "wifi_window_proc_net_qrtr",
                                       8192,
                                       &proc_qrtr_captured) < 0 ||
        append_dir_capture_named(buf,
                                 "/dev",
                                 "wifi_window_dev_filtered",
                                 true,
                                 96,
                                 &dev_filtered_captured) < 0 ||
        append_dir_capture_named(buf,
                                 "/sys/bus/msm_subsys/devices",
                                 "wifi_window_msm_subsys_devices",
                                 false,
                                 96,
                                 &msm_subsys_captured) < 0 ||
        append_dir_capture_named(buf,
                                 "/sys/bus/rpmsg/devices",
                                 "wifi_window_rpmsg_devices",
                                 false,
                                 128,
                                 &rpmsg_captured) < 0 ||
        append_dir_capture_named(buf,
                                 "/sys/bus/rpmsg/drivers",
                                 "wifi_window_rpmsg_drivers",
                                 false,
                                 128,
                                 &rpmsg_drivers_captured) < 0 ||
        append_path_file_capture_named(buf,
                                       "/sys/bus/rpmsg/drivers_autoprobe",
                                       "wifi_window_rpmsg_drivers_autoprobe",
                                       1024,
                                       &rpmsg_autoprobe_captured) < 0 ||
        append_dir_capture_named(buf,
                                 "/sys/class/remoteproc",
                                 "wifi_window_remoteproc",
                                 false,
                                 96,
                                 &remoteproc_captured) < 0 ||
        append_dir_capture_named(buf,
                                 "/sys/kernel/debug/service_notifier",
                                 "wifi_window_service_notifier",
                                 false,
                                 96,
                                 &service_notifier_captured) < 0 ||
        append_dir_capture_named(buf,
                                 "/sys/devices/platform/soc/soc:qcom,mdm3",
                                 "wifi_window_soc_mdm3",
                                 false,
                                 96,
                                 &mdm3_captured) < 0 ||
        append_dir_capture_named(buf,
                                 "/sys/devices/platform/soc/4080000.qcom,mss",
                                 "wifi_window_soc_mss",
                                 false,
                                 96,
                                 &mss_captured) < 0 ||
        append_path_file_capture_named(buf,
                                       "/sys/devices/platform/soc/4080000.qcom,mss/subsys0/uevent",
                                       "wifi_window_soc_mss_subsys0_uevent",
                                       2048,
                                       &mss_subsys0_uevent_captured) < 0 ||
        append_path_file_capture_named(buf,
                                       "/sys/devices/platform/soc/4080000.qcom,mss/subsys0/name",
                                       "wifi_window_soc_mss_subsys0_name",
                                       1024,
                                       &mss_subsys0_name_captured) < 0 ||
        append_path_file_capture_named(buf,
                                       "/sys/devices/platform/soc/4080000.qcom,mss/subsys0/state",
                                       "wifi_window_soc_mss_subsys0_state",
                                       1024,
                                       &mss_subsys0_state_captured) < 0 ||
        append_path_file_capture_named(buf,
                                       "/sys/devices/platform/soc/4080000.qcom,mss/subsys0/restart_level",
                                       "wifi_window_soc_mss_subsys0_restart_level",
                                       1024,
                                       &mss_subsys0_restart_level_captured) < 0 ||
        append_path_file_capture_named(buf,
                                       "/sys/devices/platform/soc/4080000.qcom,mss/subsys0/firmware_name",
                                       "wifi_window_soc_mss_subsys0_firmware_name",
                                       1024,
                                       &mss_subsys0_firmware_name_captured) < 0 ||
        append_path_file_capture_named(buf,
                                       "/sys/devices/platform/soc/4080000.qcom,mss/subsys0/crash_count",
                                       "wifi_window_soc_mss_subsys0_crash_count",
                                       1024,
                                       &mss_subsys0_crash_count_captured) < 0 ||
        append_path_file_capture_named(buf,
                                       "/sys/devices/platform/soc/soc:qcom,mdm3/subsys9/uevent",
                                       "wifi_window_soc_mdm3_subsys9_uevent",
                                       2048,
                                       &mdm3_subsys9_uevent_captured) < 0 ||
        append_path_file_capture_named(buf,
                                       "/sys/devices/platform/soc/soc:qcom,mdm3/subsys9/name",
                                       "wifi_window_soc_mdm3_subsys9_name",
                                       1024,
                                       &mdm3_subsys9_name_captured) < 0 ||
        append_path_file_capture_named(buf,
                                       "/sys/devices/platform/soc/soc:qcom,mdm3/subsys9/state",
                                       "wifi_window_soc_mdm3_subsys9_state",
                                       1024,
                                       &mdm3_subsys9_state_captured) < 0 ||
        append_path_file_capture_named(buf,
                                       "/sys/devices/platform/soc/soc:qcom,mdm3/subsys9/restart_level",
                                       "wifi_window_soc_mdm3_subsys9_restart_level",
                                       1024,
                                       &mdm3_subsys9_restart_level_captured) < 0 ||
        append_path_file_capture_named(buf,
                                       "/sys/devices/platform/soc/soc:qcom,mdm3/subsys9/firmware_name",
                                       "wifi_window_soc_mdm3_subsys9_firmware_name",
                                       1024,
                                       &mdm3_subsys9_firmware_name_captured) < 0 ||
        append_path_file_capture_named(buf,
                                       "/sys/devices/platform/soc/soc:qcom,mdm3/subsys9/crash_count",
                                       "wifi_window_soc_mdm3_subsys9_crash_count",
                                       1024,
                                       &mdm3_subsys9_crash_count_captured) < 0) {
        return -1;
    }
    subsys_value_captures += mss_subsys0_uevent_captured ? 1 : 0;
    subsys_value_captures += mss_subsys0_name_captured ? 1 : 0;
    subsys_value_captures += mss_subsys0_state_captured ? 1 : 0;
    subsys_value_captures += mss_subsys0_restart_level_captured ? 1 : 0;
    subsys_value_captures += mss_subsys0_firmware_name_captured ? 1 : 0;
    subsys_value_captures += mss_subsys0_crash_count_captured ? 1 : 0;
    subsys_value_captures += mdm3_subsys9_uevent_captured ? 1 : 0;
    subsys_value_captures += mdm3_subsys9_name_captured ? 1 : 0;
    subsys_value_captures += mdm3_subsys9_state_captured ? 1 : 0;
    subsys_value_captures += mdm3_subsys9_restart_level_captured ? 1 : 0;
    subsys_value_captures += mdm3_subsys9_firmware_name_captured ? 1 : 0;
    subsys_value_captures += mdm3_subsys9_crash_count_captured ? 1 : 0;
    if (append_format(buf,
                      "wifi_companion_start.surface_%s.proc_qrtr_captured=%d\n"
                      "wifi_companion_start.surface_%s.dev_filtered_captured=%d\n"
                      "wifi_companion_start.surface_%s.msm_subsys_captured=%d\n"
                      "wifi_companion_start.surface_%s.rpmsg_captured=%d\n"
                      "wifi_companion_start.surface_%s.rpmsg_drivers_captured=%d\n"
                      "wifi_companion_start.surface_%s.rpmsg_autoprobe_captured=%d\n"
                      "wifi_companion_start.surface_%s.remoteproc_captured=%d\n"
                      "wifi_companion_start.surface_%s.service_notifier_captured=%d\n"
                      "wifi_companion_start.surface_%s.mdm3_captured=%d\n"
                      "wifi_companion_start.surface_%s.mss_captured=%d\n"
                      "wifi_companion_start.surface_%s.mss_subsys0_state_captured=%d\n"
                      "wifi_companion_start.surface_%s.mdm3_subsys9_state_captured=%d\n"
                      "wifi_companion_start.surface_%s.subsys_value_captures=%d\n"
                      "wifi_companion_start.surface_%s.end=1\n",
                      phase,
                      proc_qrtr_captured ? 1 : 0,
                      phase,
                      dev_filtered_captured ? 1 : 0,
                      phase,
                      msm_subsys_captured ? 1 : 0,
                      phase,
                      rpmsg_captured ? 1 : 0,
                      phase,
                      rpmsg_drivers_captured ? 1 : 0,
                      phase,
                      rpmsg_autoprobe_captured ? 1 : 0,
                      phase,
                      remoteproc_captured ? 1 : 0,
                      phase,
                      service_notifier_captured ? 1 : 0,
                      phase,
                      mdm3_captured ? 1 : 0,
                      phase,
                      mss_captured ? 1 : 0,
                      phase,
                      mss_subsys0_state_captured ? 1 : 0,
                      phase,
                      mdm3_subsys9_state_captured ? 1 : 0,
                      phase,
                      subsys_value_captures,
                      phase) < 0) {
        return -1;
    }
    return 0;
}

static int build_phase_label(char *out, size_t out_size, const char *phase, const char *suffix) {
    int rc = snprintf(out, out_size, "wifi_icnss_edge_%s_%s", phase, suffix);

    if (rc < 0 || (size_t)rc >= out_size) {
        errno = ENAMETOOLONG;
        return -1;
    }
    return 0;
}

static int append_wifi_icnss_edge_capture(struct buffer *buf, const char *phase) {
    bool mhi_devices_captured = false;
    bool mhi_drivers_captured = false;
    bool pci_devices_captured = false;
    bool pci_drivers_captured = false;
    bool rpmsg_devices_captured = false;
    bool rpmsg_drivers_captured = false;
    bool icnss_params_captured = false;
    bool wlan_params_captured = false;
    bool icnss_power_captured = false;
    bool qca6390_power_captured = false;
    bool interrupts_captured = false;
    bool icnss_quirks_captured = false;
    bool icnss_dynamic_feature_mask_captured = false;
    bool wlan_fwpath_captured = false;
    bool wlan_con_mode_captured = false;
    bool wlan_country_code_captured = false;
    bool wlan_prealloc_disabled_captured = false;
    int value_captures = 0;
    char label[128];

    if (append_format(buf, "wifi_companion_start.icnss_edge_%s.begin=1\n", phase) < 0 ||
        append_runtime_path_status(buf,
                                   "wifi_icnss_edge",
                                   phase,
                                   "icnss_driver_link",
                                   "/sys/bus/platform/devices/18800000.qcom,icnss/driver") < 0 ||
        append_runtime_path_status(buf,
                                   "wifi_icnss_edge",
                                   phase,
                                   "qca6390_driver_link",
                                   "/sys/bus/platform/devices/a0000000.qcom,cnss-qca6390/driver") < 0 ||
        append_runtime_path_status(buf,
                                   "wifi_icnss_edge",
                                   phase,
                                   "wlan0_netdev",
                                   "/sys/class/net/wlan0") < 0 ||
        append_runtime_path_status(buf,
                                   "wifi_icnss_edge",
                                   phase,
                                   "shutdown_wlan",
                                   "/sys/kernel/shutdown_wlan") < 0) {
        return -1;
    }

    if (build_phase_label(label, sizeof(label), phase, "mhi_devices") < 0 ||
        append_dir_capture_named(buf,
                                 "/sys/bus/mhi/devices",
                                 label,
                                 false,
                                 96,
                                 &mhi_devices_captured) < 0 ||
        build_phase_label(label, sizeof(label), phase, "mhi_drivers") < 0 ||
        append_dir_capture_named(buf,
                                 "/sys/bus/mhi/drivers",
                                 label,
                                 false,
                                 96,
                                 &mhi_drivers_captured) < 0 ||
        build_phase_label(label, sizeof(label), phase, "pci_devices") < 0 ||
        append_dir_capture_named(buf,
                                 "/sys/bus/pci/devices",
                                 label,
                                 false,
                                 96,
                                 &pci_devices_captured) < 0 ||
        build_phase_label(label, sizeof(label), phase, "pci_drivers") < 0 ||
        append_dir_capture_named(buf,
                                 "/sys/bus/pci/drivers",
                                 label,
                                 false,
                                 128,
                                 &pci_drivers_captured) < 0 ||
        build_phase_label(label, sizeof(label), phase, "rpmsg_devices") < 0 ||
        append_dir_capture_named(buf,
                                 "/sys/bus/rpmsg/devices",
                                 label,
                                 false,
                                 128,
                                 &rpmsg_devices_captured) < 0 ||
        build_phase_label(label, sizeof(label), phase, "rpmsg_drivers") < 0 ||
        append_dir_capture_named(buf,
                                 "/sys/bus/rpmsg/drivers",
                                 label,
                                 false,
                                 128,
                                 &rpmsg_drivers_captured) < 0 ||
        build_phase_label(label, sizeof(label), phase, "icnss_params") < 0 ||
        append_dir_capture_named(buf,
                                 "/sys/module/icnss/parameters",
                                 label,
                                 false,
                                 96,
                                 &icnss_params_captured) < 0 ||
        build_phase_label(label, sizeof(label), phase, "wlan_params") < 0 ||
        append_dir_capture_named(buf,
                                 "/sys/module/wlan/parameters",
                                 label,
                                 false,
                                 128,
                                 &wlan_params_captured) < 0 ||
        build_phase_label(label, sizeof(label), phase, "icnss_power") < 0 ||
        append_dir_capture_named(buf,
                                 "/sys/bus/platform/devices/18800000.qcom,icnss/power",
                                 label,
                                 false,
                                 96,
                                 &icnss_power_captured) < 0 ||
        build_phase_label(label, sizeof(label), phase, "qca6390_power") < 0 ||
        append_dir_capture_named(buf,
                                 "/sys/bus/platform/devices/a0000000.qcom,cnss-qca6390/power",
                                 label,
                                 false,
                                 96,
                                 &qca6390_power_captured) < 0 ||
        build_phase_label(label, sizeof(label), phase, "proc_interrupts") < 0 ||
        append_path_file_capture_named(buf,
                                       "/proc/interrupts",
                                       label,
                                       16384,
                                       &interrupts_captured) < 0) {
        return -1;
    }

    if (append_path_file_capture_named(buf,
                                       "/sys/module/icnss/parameters/quirks",
                                       "wifi_icnss_edge_icnss_quirks",
                                       1024,
                                       &icnss_quirks_captured) < 0 ||
        append_path_file_capture_named(buf,
                                       "/sys/module/icnss/parameters/dynamic_feature_mask",
                                       "wifi_icnss_edge_icnss_dynamic_feature_mask",
                                       1024,
                                       &icnss_dynamic_feature_mask_captured) < 0 ||
        append_path_file_capture_named(buf,
                                       "/sys/module/wlan/parameters/fwpath",
                                       "wifi_icnss_edge_wlan_fwpath",
                                       1024,
                                       &wlan_fwpath_captured) < 0 ||
        append_path_file_capture_named(buf,
                                       "/sys/module/wlan/parameters/con_mode",
                                       "wifi_icnss_edge_wlan_con_mode",
                                       1024,
                                       &wlan_con_mode_captured) < 0 ||
        append_path_file_capture_named(buf,
                                       "/sys/module/wlan/parameters/country_code",
                                       "wifi_icnss_edge_wlan_country_code",
                                       1024,
                                       &wlan_country_code_captured) < 0 ||
        append_path_file_capture_named(buf,
                                       "/sys/module/wlan/parameters/prealloc_disabled",
                                       "wifi_icnss_edge_wlan_prealloc_disabled",
                                       1024,
                                       &wlan_prealloc_disabled_captured) < 0) {
        return -1;
    }

    value_captures += icnss_quirks_captured ? 1 : 0;
    value_captures += icnss_dynamic_feature_mask_captured ? 1 : 0;
    value_captures += wlan_fwpath_captured ? 1 : 0;
    value_captures += wlan_con_mode_captured ? 1 : 0;
    value_captures += wlan_country_code_captured ? 1 : 0;
    value_captures += wlan_prealloc_disabled_captured ? 1 : 0;
    return append_format(buf,
                         "wifi_companion_start.icnss_edge_%s.mhi_devices_captured=%d\n"
                         "wifi_companion_start.icnss_edge_%s.mhi_drivers_captured=%d\n"
                         "wifi_companion_start.icnss_edge_%s.pci_devices_captured=%d\n"
                         "wifi_companion_start.icnss_edge_%s.pci_drivers_captured=%d\n"
                         "wifi_companion_start.icnss_edge_%s.rpmsg_devices_captured=%d\n"
                         "wifi_companion_start.icnss_edge_%s.rpmsg_drivers_captured=%d\n"
                         "wifi_companion_start.icnss_edge_%s.icnss_params_captured=%d\n"
                         "wifi_companion_start.icnss_edge_%s.wlan_params_captured=%d\n"
                         "wifi_companion_start.icnss_edge_%s.icnss_power_captured=%d\n"
                         "wifi_companion_start.icnss_edge_%s.qca6390_power_captured=%d\n"
                         "wifi_companion_start.icnss_edge_%s.interrupts_captured=%d\n"
                         "wifi_companion_start.icnss_edge_%s.value_captures=%d\n"
                         "wifi_companion_start.icnss_edge_%s.end=1\n",
                         phase, mhi_devices_captured ? 1 : 0,
                         phase, mhi_drivers_captured ? 1 : 0,
                         phase, pci_devices_captured ? 1 : 0,
                         phase, pci_drivers_captured ? 1 : 0,
                         phase, rpmsg_devices_captured ? 1 : 0,
                         phase, rpmsg_drivers_captured ? 1 : 0,
                         phase, icnss_params_captured ? 1 : 0,
                         phase, wlan_params_captured ? 1 : 0,
                         phase, icnss_power_captured ? 1 : 0,
                         phase, qca6390_power_captured ? 1 : 0,
                         phase, interrupts_captured ? 1 : 0,
                         phase, value_captures,
                         phase);
}

static int append_wifi_cnss2_focus_capture(struct buffer *buf, const char *phase) {
    bool icnss_driver_captured = false;
    bool icnss_device_captured = false;
    bool qca6390_device_captured = false;
    bool net_class_captured = false;
    bool wlan0_captured = false;
    bool icnss_uevent_captured = false;
    bool icnss_modalias_captured = false;
    bool icnss_power_control_captured = false;
    bool icnss_power_runtime_status_captured = false;
    bool qca6390_uevent_captured = false;
    bool qca6390_modalias_captured = false;
    bool qca6390_power_control_captured = false;
    bool qca6390_power_runtime_status_captured = false;
    bool debug_icnss_captured = false;
    int value_captures = 0;

    if (append_format(buf, "wifi_companion_start.cnss2_focus_%s.begin=1\n", phase) < 0 ||
        append_dir_capture_named(buf,
                                 "/sys/bus/platform/drivers/icnss",
                                 "wifi_cnss2_focus_icnss_driver",
                                 false,
                                 96,
                                 &icnss_driver_captured) < 0 ||
        append_dir_capture_named(buf,
                                 "/sys/bus/platform/devices/18800000.qcom,icnss",
                                 "wifi_cnss2_focus_icnss_device",
                                 false,
                                 128,
                                 &icnss_device_captured) < 0 ||
        append_dir_capture_named(buf,
                                 "/sys/bus/platform/devices/a0000000.qcom,cnss-qca6390",
                                 "wifi_cnss2_focus_qca6390_device",
                                 false,
                                 128,
                                 &qca6390_device_captured) < 0 ||
        append_dir_capture_named(buf,
                                 "/sys/class/net",
                                 "wifi_cnss2_focus_net_class",
                                 false,
                                 128,
                                 &net_class_captured) < 0 ||
        append_dir_capture_named(buf,
                                 "/sys/class/net/wlan0",
                                 "wifi_cnss2_focus_wlan0",
                                 false,
                                 128,
                                 &wlan0_captured) < 0 ||
        append_path_file_capture_named(buf,
                                       "/sys/bus/platform/devices/18800000.qcom,icnss/uevent",
                                       "wifi_cnss2_focus_icnss_uevent",
                                       4096,
                                       &icnss_uevent_captured) < 0 ||
        append_path_file_capture_named(buf,
                                       "/sys/bus/platform/devices/18800000.qcom,icnss/modalias",
                                       "wifi_cnss2_focus_icnss_modalias",
                                       4096,
                                       &icnss_modalias_captured) < 0 ||
        append_path_file_capture_named(buf,
                                       "/sys/bus/platform/devices/18800000.qcom,icnss/power/control",
                                       "wifi_cnss2_focus_icnss_power_control",
                                       1024,
                                       &icnss_power_control_captured) < 0 ||
        append_path_file_capture_named(buf,
                                       "/sys/bus/platform/devices/18800000.qcom,icnss/power/runtime_status",
                                       "wifi_cnss2_focus_icnss_power_runtime_status",
                                       1024,
                                       &icnss_power_runtime_status_captured) < 0 ||
        append_path_file_capture_named(buf,
                                       "/sys/bus/platform/devices/a0000000.qcom,cnss-qca6390/uevent",
                                       "wifi_cnss2_focus_qca6390_uevent",
                                       4096,
                                       &qca6390_uevent_captured) < 0 ||
        append_path_file_capture_named(buf,
                                       "/sys/bus/platform/devices/a0000000.qcom,cnss-qca6390/modalias",
                                       "wifi_cnss2_focus_qca6390_modalias",
                                       4096,
                                       &qca6390_modalias_captured) < 0 ||
        append_path_file_capture_named(buf,
                                       "/sys/bus/platform/devices/a0000000.qcom,cnss-qca6390/power/control",
                                       "wifi_cnss2_focus_qca6390_power_control",
                                       1024,
                                       &qca6390_power_control_captured) < 0 ||
        append_path_file_capture_named(buf,
                                       "/sys/bus/platform/devices/a0000000.qcom,cnss-qca6390/power/runtime_status",
                                       "wifi_cnss2_focus_qca6390_power_runtime_status",
                                       1024,
                                       &qca6390_power_runtime_status_captured) < 0 ||
        append_dir_capture_named(buf,
                                 "/sys/kernel/debug/icnss",
                                 "wifi_cnss2_focus_debug_icnss",
                                 false,
                                 128,
                                 &debug_icnss_captured) < 0) {
        return -1;
    }
    value_captures += icnss_uevent_captured ? 1 : 0;
    value_captures += icnss_modalias_captured ? 1 : 0;
    value_captures += icnss_power_control_captured ? 1 : 0;
    value_captures += icnss_power_runtime_status_captured ? 1 : 0;
    value_captures += qca6390_uevent_captured ? 1 : 0;
    value_captures += qca6390_modalias_captured ? 1 : 0;
    value_captures += qca6390_power_control_captured ? 1 : 0;
    value_captures += qca6390_power_runtime_status_captured ? 1 : 0;
    if (append_format(buf,
                      "wifi_companion_start.cnss2_focus_%s.icnss_driver_captured=%d\n"
                      "wifi_companion_start.cnss2_focus_%s.icnss_device_captured=%d\n"
                      "wifi_companion_start.cnss2_focus_%s.qca6390_device_captured=%d\n"
                      "wifi_companion_start.cnss2_focus_%s.net_class_captured=%d\n"
                      "wifi_companion_start.cnss2_focus_%s.wlan0_captured=%d\n"
                      "wifi_companion_start.cnss2_focus_%s.debug_icnss_captured=%d\n"
                      "wifi_companion_start.cnss2_focus_%s.value_captures=%d\n",
                      phase,
                      icnss_driver_captured ? 1 : 0,
                      phase,
                      icnss_device_captured ? 1 : 0,
                      phase,
                      qca6390_device_captured ? 1 : 0,
                      phase,
                      net_class_captured ? 1 : 0,
                      phase,
                      wlan0_captured ? 1 : 0,
                      phase,
                      debug_icnss_captured ? 1 : 0,
                      phase,
                      value_captures) < 0 ||
        append_wifi_icnss_edge_capture(buf, phase) < 0 ||
        append_format(buf, "wifi_companion_start.cnss2_focus_%s.icnss_edge_captured=1\n"
                           "wifi_companion_start.cnss2_focus_%s.end=1\n",
                      phase,
                      phase) < 0) {
        return -1;
    }
    return 0;
}


static int count_dir_entries_matching(const char *path,
                                      const char *needle,
                                      int *count,
                                      bool *matched) {
    DIR *dir;
    struct dirent *entry;

    *count = 0;
    *matched = false;
    dir = opendir(path);
    if (dir == NULL) {
        return -1;
    }
    while ((entry = readdir(dir)) != NULL) {
        if (strcmp(entry->d_name, ".") == 0 || strcmp(entry->d_name, "..") == 0) {
            continue;
        }
        (*count)++;
        if (needle != NULL && strstr(entry->d_name, needle) != NULL) {
            *matched = true;
        }
    }
    closedir(dir);
    return 0;
}

static void read_state_or_error(const char *path, char *out, size_t out_size) {
    int saved_errno;

    if (read_small_file_trim(path, out, out_size) == 0) {
        return;
    }
    saved_errno = errno;
    snprintf(out, out_size, "error:%s", strerror(saved_errno));
}

static int append_subsys_hold_snapshot(struct buffer *buf, const char *phase) {
    char mss_state[128];
    char mdm3_state[128];
    int rpmsg_count = -1;
    bool rpmsg_ipcrtr_present = false;
    bool rpmsg_error = false;

    read_state_or_error("/sys/devices/platform/soc/4080000.qcom,mss/subsys0/state",
                        mss_state,
                        sizeof(mss_state));
    read_state_or_error("/sys/devices/platform/soc/soc:qcom,mdm3/subsys9/state",
                        mdm3_state,
                        sizeof(mdm3_state));
    if (count_dir_entries_matching("/sys/bus/rpmsg/devices",
                                   "IPCRTR",
                                   &rpmsg_count,
                                   &rpmsg_ipcrtr_present) < 0) {
        rpmsg_error = true;
    }
    return append_format(buf,
                         "wifi_companion_start.subsys_hold.%s.mss_state=%s\n"
                         "wifi_companion_start.subsys_hold.%s.mdm3_state=%s\n"
                         "wifi_companion_start.subsys_hold.%s.rpmsg_count=%d\n"
                         "wifi_companion_start.subsys_hold.%s.rpmsg_ipcrtr_present=%d\n"
                         "wifi_companion_start.subsys_hold.%s.rpmsg_error=%d\n",
                         phase,
                         mss_state,
                         phase,
                         mdm3_state,
                         phase,
                         rpmsg_count,
                         phase,
                         rpmsg_ipcrtr_present ? 1 : 0,
                         phase,
                         rpmsg_error ? 1 : 0);
}

static int append_esoc_req_subsys_hold_snapshot(struct buffer *buf, const char *phase) {
    char mss_state[128];
    char mdm3_state[128];
    int rpmsg_count = -1;
    bool rpmsg_ipcrtr_present = false;
    bool rpmsg_error = false;

    read_state_or_error("/sys/devices/platform/soc/4080000.qcom,mss/subsys0/state",
                        mss_state,
                        sizeof(mss_state));
    read_state_or_error("/sys/devices/platform/soc/soc:qcom,mdm3/subsys9/state",
                        mdm3_state,
                        sizeof(mdm3_state));
    if (count_dir_entries_matching("/sys/bus/rpmsg/devices",
                                   "IPCRTR",
                                   &rpmsg_count,
                                   &rpmsg_ipcrtr_present) < 0) {
        rpmsg_error = true;
    }
    return append_format(buf,
                         "esoc_req_registered_subsys_hold_preflight.snapshot.%s.mss_state=%s\n"
                         "esoc_req_registered_subsys_hold_preflight.snapshot.%s.mdm3_state=%s\n"
                         "esoc_req_registered_subsys_hold_preflight.snapshot.%s.rpmsg_count=%d\n"
                         "esoc_req_registered_subsys_hold_preflight.snapshot.%s.rpmsg_ipcrtr_present=%d\n"
                         "esoc_req_registered_subsys_hold_preflight.snapshot.%s.rpmsg_error=%d\n",
                         phase,
                         mss_state,
                         phase,
                         mdm3_state,
                         phase,
                         rpmsg_count,
                         phase,
                         rpmsg_ipcrtr_present ? 1 : 0,
                         phase,
                         rpmsg_error ? 1 : 0);
}

static int parse_dev_major_minor(const char *path,
                                 unsigned int *major_no,
                                 unsigned int *minor_no,
                                 char *text,
                                 size_t text_size) {
    if (read_small_file_trim(path, text, text_size) < 0) {
        return -1;
    }
    if (sscanf(text, "%u:%u", major_no, minor_no) != 2) {
        errno = EINVAL;
        return -1;
    }
    return 0;
}

static int materialize_subsys_hold_node(const char *sys_dev_path,
                                        const char *node_path,
                                        const char *label,
                                        struct buffer *stdout_buf) {
    char dev_text[64];
    unsigned int major_no = 0;
    unsigned int minor_no = 0;
    int saved_errno;

    if (parse_dev_major_minor(sys_dev_path, &major_no, &minor_no, dev_text, sizeof(dev_text)) < 0) {
        saved_errno = errno;
        return append_format(stdout_buf,
                             "wifi_companion_start.subsys_hold.%s_node_ready=0\n"
                             "wifi_companion_start.subsys_hold.%s_dev_path=%s\n"
                             "wifi_companion_start.subsys_hold.%s_dev_error=%s\n",
                             label,
                             label,
                             sys_dev_path,
                             label,
                             strerror(saved_errno));
    }
    if (unlink(node_path) < 0 && errno != ENOENT) {
        saved_errno = errno;
        return append_format(stdout_buf,
                             "wifi_companion_start.subsys_hold.%s_node_ready=0\n"
                             "wifi_companion_start.subsys_hold.%s_node_error=unlink-%s\n",
                             label,
                             label,
                             strerror(saved_errno));
    }
    if (mknod(node_path, S_IFCHR | 0600, makedev(major_no, minor_no)) < 0) {
        saved_errno = errno;
        return append_format(stdout_buf,
                             "wifi_companion_start.subsys_hold.%s_node_ready=0\n"
                             "wifi_companion_start.subsys_hold.%s_node_error=mknod-%s\n",
                             label,
                             label,
                             strerror(saved_errno));
    }
    if (chmod(node_path, 0600) < 0) {
        saved_errno = errno;
        return append_format(stdout_buf,
                             "wifi_companion_start.subsys_hold.%s_node_ready=0\n"
                             "wifi_companion_start.subsys_hold.%s_node_error=chmod-%s\n",
                             label,
                             label,
                             strerror(saved_errno));
    }
    return append_format(stdout_buf,
                         "wifi_companion_start.subsys_hold.%s_node_ready=1\n"
                         "wifi_companion_start.subsys_hold.%s_dev_path=%s\n"
                         "wifi_companion_start.subsys_hold.%s_dev=%s\n"
                         "wifi_companion_start.subsys_hold.%s_node=%s\n",
                         label,
                         label,
                         sys_dev_path,
                         label,
                         dev_text,
                         label,
                         node_path);
}

static int open_subsys_hold_child_node(int out_fd, const char *path, const char *label) {
    int fd;
    int saved_errno = 0;

    fd = open(path, O_RDONLY | O_NONBLOCK | O_CLOEXEC);
    if (fd < 0 && errno == EINVAL) {
        fd = open(path, O_RDONLY | O_CLOEXEC);
    }
    if (fd < 0) {
        saved_errno = errno;
        dprintf(out_fd,
                "wifi_companion_start.subsys_hold.%s_opened=0\n"
                "wifi_companion_start.subsys_hold.%s_open_errno=%d\n"
                "wifi_companion_start.subsys_hold.%s_open_error=%s\n",
                label,
                label,
                saved_errno,
                label,
                strerror(saved_errno));
        return -1;
    }
    dprintf(out_fd,
            "wifi_companion_start.subsys_hold.%s_opened=1\n"
            "wifi_companion_start.subsys_hold.%s_fd=%d\n",
            label,
            label,
            fd);
    return fd;
}

static int open_esoc_req_registered_subsys_child_node(int out_fd) {
    int fd;
    int saved_errno = 0;

    dprintf(out_fd,
            "esoc_req_registered_subsys_hold_preflight.subsys_esoc0_open_attempting=1\n");
    errno = 0;
    fd = open("/dev/subsys_esoc0", O_RDONLY | O_NONBLOCK | O_CLOEXEC);
    if (fd < 0 && errno == EINVAL) {
        errno = 0;
        fd = open("/dev/subsys_esoc0", O_RDONLY | O_CLOEXEC);
    }
    saved_errno = fd < 0 ? errno : 0;
    if (fd < 0) {
        dprintf(out_fd,
                "esoc_req_registered_subsys_hold_preflight.subsys_esoc0_opened=0\n"
                "esoc_req_registered_subsys_hold_preflight.subsys_esoc0_open_errno=%d\n"
                "esoc_req_registered_subsys_hold_preflight.subsys_esoc0_open_error=%s\n",
                saved_errno,
                strerror(saved_errno));
        return -1;
    }
    dprintf(out_fd,
            "esoc_req_registered_subsys_hold_preflight.subsys_esoc0_opened=1\n"
            "esoc_req_registered_subsys_hold_preflight.subsys_esoc0_fd=%d\n",
            fd);
    return fd;
}

static int run_esoc_wait_for_req_observer_child(int out_fd, int req_fd, int hold_sec) {
    unsigned int request_value = 0;
    int rc;
    int saved_errno;
    long started_ms = monotonic_ms();

    dprintf(out_fd,
            "esoc_req_registered_subsys_hold_preflight.wait_for_req_observer.begin=1\n"
            "esoc_req_registered_subsys_hold_preflight.wait_for_req_observer.mode=passive\n"
            "esoc_req_registered_subsys_hold_preflight.wait_for_req_observer.hold_sec=%d\n"
            "esoc_req_registered_subsys_hold_preflight.wait_for_req_observer.ioctl.request=0x%lx\n",
            hold_sec,
            (unsigned long)A90_ESOC_WAIT_FOR_REQ);
    errno = 0;
    rc = ioctl(req_fd, A90_ESOC_WAIT_FOR_REQ, &request_value);
    saved_errno = rc < 0 ? errno : 0;
    dprintf(out_fd,
            "esoc_req_registered_subsys_hold_preflight.wait_for_req_observer.ioctl.rc=%d\n"
            "esoc_req_registered_subsys_hold_preflight.wait_for_req_observer.ioctl.errno=%d\n"
            "esoc_req_registered_subsys_hold_preflight.wait_for_req_observer.ioctl.value=%u\n"
            "esoc_req_registered_subsys_hold_preflight.wait_for_req_observer.elapsed_ms=%ld\n"
            "esoc_req_registered_subsys_hold_preflight.wait_for_req_observer.result=%s\n"
            "esoc_req_registered_subsys_hold_preflight.wait_for_req_observer.end=1\n",
            rc,
            saved_errno,
            request_value,
            monotonic_ms() - started_ms,
            rc == 0 ? "request-observed" : "ioctl-error");
    return rc == 0 ? 0 : 32;
}

static pid_t wait_for_child_session_pgid(pid_t pid, long timeout_ms);

static int run_subsys_hold_open_proof(const struct config *cfg,
                                      const struct paths *paths,
                                      struct buffer *stdout_buf,
                                      struct buffer *stderr_buf,
                                      int *child_exit_code,
                                      int *child_signal,
                                      bool *timed_out) {
    int stdout_pipe[2] = {-1, -1};
    bool stdout_open = true;
    bool child_done = false;
    bool child_started = false;
    bool term_sent = false;
    bool kill_sent = false;
    bool reaped = false;
    bool postflight_safe = true;
    char modem_node[MAX_PATH_LEN];
    char esoc_node[MAX_PATH_LEN];
    long deadline;
    pid_t pid = -1;
    pid_t pgid = -1;
    int status = 0;
    int hold_sec = cfg->timeout_sec > 3 ? cfg->timeout_sec - 2 : 1;

    (void)stderr_buf;
    *child_exit_code = -1;
    *child_signal = 0;
    *timed_out = false;

    if (append_literal(stdout_buf,
                       "wifi_companion_start.begin=1\n"
                       "wifi_companion_start.mode=subsys-hold-open-proof\n"
                       "wifi_companion_start.service_manager=0\n"
                       "wifi_companion_start.wifi_hal=0\n"
                       "wifi_companion_start.scan_connect_linkup=0\n"
                       "wifi_companion_start.external_ping=0\n"
                       "wifi_companion_start.subsys_hold.qcwlanstate_write=0\n"
                       "wifi_companion_start.subsys_hold.scan_connect_linkup=0\n"
                       "wifi_companion_start.subsys_hold.external_ping=0\n") < 0) {
        return -1;
    }
    if (!cfg->allow_wifi_companion_start_only) {
        return append_literal(stdout_buf,
                              "wifi_companion_start.allowed=0\n"
                              "wifi_companion_start.exec_attempted=0\n"
                              "wifi_companion_start.child_started=0\n"
                              "wifi_companion_start.all_observable=0\n"
                              "wifi_companion_start.all_postflight_safe=1\n"
                              "wifi_companion_start.result=subsys-hold-blocked\n"
                              "wifi_companion_start.reason=missing-allow-wifi-companion-start-only\n"
                              "wifi_companion_start.end=1\n");
    }
    if (append_literal(stdout_buf, "wifi_companion_start.allowed=1\n") < 0 ||
        append_subsys_hold_snapshot(stdout_buf, "before") < 0 ||
        append_wifi_window_surface_capture(stdout_buf, "subsys_before") < 0) {
        return -1;
    }
    if (append_path(modem_node, sizeof(modem_node), paths->dev, "subsys_modem") < 0 ||
        append_path(esoc_node, sizeof(esoc_node), paths->dev, "subsys_esoc0") < 0) {
        return -1;
    }
    if (materialize_subsys_hold_node("/sys/class/subsys/subsys_modem/dev",
                                     modem_node,
                                     "modem",
                                     stdout_buf) < 0 ||
        materialize_subsys_hold_node("/sys/class/subsys/subsys_esoc0/dev",
                                     esoc_node,
                                     "esoc0",
                                     stdout_buf) < 0) {
        return -1;
    }
    if (strstr(stdout_buf->data != NULL ? stdout_buf->data : "", "node_ready=0") != NULL) {
        append_literal(stdout_buf,
                       "wifi_companion_start.exec_attempted=0\n"
                       "wifi_companion_start.child_started=0\n"
                       "wifi_companion_start.all_observable=0\n"
                       "wifi_companion_start.all_postflight_safe=1\n"
                       "wifi_companion_start.result=subsys-hold-setup-failed\n"
                       "wifi_companion_start.reason=subsys-cdev-node-unavailable\n"
                       "wifi_companion_start.end=1\n");
        unlink(modem_node);
        unlink(esoc_node);
        return 0;
    }
    if (pipe2(stdout_pipe, O_CLOEXEC) < 0) {
        return append_format(stdout_buf,
                             "wifi_companion_start.exec_attempted=0\n"
                             "wifi_companion_start.child_started=0\n"
                             "wifi_companion_start.all_observable=0\n"
                             "wifi_companion_start.all_postflight_safe=0\n"
                             "wifi_companion_start.result=manual-review-required\n"
                             "wifi_companion_start.reason=pipe-failed-%s\n"
                             "wifi_companion_start.end=1\n",
                             strerror(errno));
    }
    pid = fork();
    if (pid < 0) {
        int saved_errno = errno;

        close(stdout_pipe[0]);
        close(stdout_pipe[1]);
        unlink(modem_node);
        unlink(esoc_node);
        return append_format(stdout_buf,
                             "wifi_companion_start.exec_attempted=0\n"
                             "wifi_companion_start.child_started=0\n"
                             "wifi_companion_start.all_observable=0\n"
                             "wifi_companion_start.all_postflight_safe=0\n"
                             "wifi_companion_start.result=manual-review-required\n"
                             "wifi_companion_start.reason=fork-failed-%s\n"
                             "wifi_companion_start.end=1\n",
                             strerror(saved_errno));
    }
    if (pid == 0) {
        int modem_fd;
        int esoc_fd;
        int any_open;

        close(stdout_pipe[0]);
        if (setsid() < 0) {
            dprintf(stdout_pipe[1], "wifi_companion_start.subsys_hold.child_setsid_error=%s\n", strerror(errno));
            _exit(120);
        }
        if (chroot(paths->root) < 0) {
            dprintf(stdout_pipe[1], "wifi_companion_start.subsys_hold.child_chroot_error=%s\n", strerror(errno));
            _exit(121);
        }
        if (chdir("/") < 0) {
            dprintf(stdout_pipe[1], "wifi_companion_start.subsys_hold.child_chdir_error=%s\n", strerror(errno));
            _exit(122);
        }
        dprintf(stdout_pipe[1],
                "wifi_companion_start.subsys_hold.child_chroot=1\n"
                "wifi_companion_start.subsys_hold.hold_sec=%d\n",
                hold_sec);
        modem_fd = open_subsys_hold_child_node(stdout_pipe[1], "/dev/subsys_modem", "modem");
        esoc_fd = open_subsys_hold_child_node(stdout_pipe[1], "/dev/subsys_esoc0", "esoc0");
        any_open = modem_fd >= 0 || esoc_fd >= 0;
        dprintf(stdout_pipe[1], "wifi_companion_start.subsys_hold.any_open=%d\n", any_open ? 1 : 0);
        if (any_open) {
            for (int i = 0; i < hold_sec * 10; i++) {
                usleep(100000);
            }
        }
        if (modem_fd >= 0) {
            close(modem_fd);
        }
        if (esoc_fd >= 0) {
            close(esoc_fd);
        }
        dprintf(stdout_pipe[1], "wifi_companion_start.subsys_hold.child_done=1\n");
        close(stdout_pipe[1]);
        _exit(any_open ? 0 : 31);
    }

    child_started = true;
    close(stdout_pipe[1]);
    stdout_pipe[1] = -1;
    set_nonblock(stdout_pipe[0]);
    pgid = wait_for_child_session_pgid(pid, 1000);
    if (append_format(stdout_buf,
                      "wifi_companion_start.exec_attempted=1\n"
                      "wifi_companion_start.child_started=1\n"
                      "wifi_companion_start.pid=%ld\n"
                      "wifi_companion_start.pgid=%ld\n",
                      (long)pid,
                      (long)pgid) < 0) {
        goto fail;
    }
    usleep(500000);
    drain_fd(stdout_pipe[0], stdout_buf, &stdout_open);
    if (append_subsys_hold_snapshot(stdout_buf, "hold") < 0 ||
        append_wifi_window_surface_capture(stdout_buf, "subsys_hold") < 0) {
        goto fail;
    }
    deadline = monotonic_ms() + cfg->timeout_sec * 1000L;
    while (stdout_open || !child_done) {
        struct pollfd fds[1];
        int nfds = 0;

        if (monotonic_ms() >= deadline) {
            *timed_out = true;
            break;
        }
        if (stdout_open) {
            fds[nfds].fd = stdout_pipe[0];
            fds[nfds].events = POLLIN | POLLHUP | POLLERR;
            nfds++;
        }
        if (nfds > 0 && poll(fds, nfds, 50) > 0 && fds[0].revents != 0) {
            drain_fd(stdout_pipe[0], stdout_buf, &stdout_open);
        } else {
            usleep(50000);
        }
        if (!child_done) {
            pid_t wait_rc = waitpid(pid, &status, WNOHANG);

            if (wait_rc == pid) {
                child_done = true;
                reaped = true;
                if (WIFEXITED(status)) {
                    *child_exit_code = WEXITSTATUS(status);
                } else if (WIFSIGNALED(status)) {
                    *child_signal = WTERMSIG(status);
                }
            } else if (wait_rc < 0 && errno != EINTR && errno != ECHILD) {
                append_format(stdout_buf, "wifi_companion_start.subsys_hold.wait_error=%s\n", strerror(errno));
                break;
            }
        }
    }
    if (!child_done || stdout_open) {
        if (kill(-pgid, SIGTERM) == 0 || errno == ESRCH) {
            term_sent = true;
        }
        deadline = monotonic_ms() + 1000L;
        while ((!child_done || stdout_open) && monotonic_ms() < deadline) {
            if (!child_done) {
                if (waitpid(pid, &status, WNOHANG) == pid) {
                    child_done = true;
                    reaped = true;
                    if (WIFEXITED(status)) {
                        *child_exit_code = WEXITSTATUS(status);
                    } else if (WIFSIGNALED(status)) {
                        *child_signal = WTERMSIG(status);
                    }
                }
            }
            if (stdout_open) {
                drain_fd(stdout_pipe[0], stdout_buf, &stdout_open);
            }
            usleep(50000);
        }
    }
    if (!child_done || stdout_open) {
        if (kill(-pgid, SIGKILL) == 0 || errno == ESRCH) {
            kill_sent = true;
        }
        deadline = monotonic_ms() + 1000L;
        while ((!child_done || stdout_open) && monotonic_ms() < deadline) {
            if (!child_done) {
                if (waitpid(pid, &status, WNOHANG) == pid) {
                    child_done = true;
                    reaped = true;
                    if (WIFEXITED(status)) {
                        *child_exit_code = WEXITSTATUS(status);
                    } else if (WIFSIGNALED(status)) {
                        *child_signal = WTERMSIG(status);
                    }
                }
            }
            if (stdout_open) {
                drain_fd(stdout_pipe[0], stdout_buf, &stdout_open);
            }
            usleep(50000);
        }
    }
    if (stdout_open) {
        drain_fd(stdout_pipe[0], stdout_buf, &stdout_open);
    }
    postflight_safe = reaped && (kill(-pgid, 0) < 0 && errno == ESRCH);
    if (append_subsys_hold_snapshot(stdout_buf, "after") < 0 ||
        append_wifi_window_surface_capture(stdout_buf, "subsys_after") < 0 ||
        append_format(stdout_buf,
                      "wifi_companion_start.exited=%d\n"
                      "wifi_companion_start.exit_code=%d\n"
                      "wifi_companion_start.signal=%d\n"
                      "wifi_companion_start.timed_out=%d\n"
                      "wifi_companion_start.term_sent=%d\n"
                      "wifi_companion_start.kill_sent=%d\n"
                      "wifi_companion_start.reaped=%d\n"
                      "wifi_companion_start.all_observable=%d\n"
                      "wifi_companion_start.all_postflight_safe=%d\n",
                      child_done ? 1 : 0,
                      *child_exit_code,
                      *child_signal,
                      *timed_out ? 1 : 0,
                      term_sent ? 1 : 0,
                      kill_sent ? 1 : 0,
                      reaped ? 1 : 0,
                      child_started ? 1 : 0,
                      postflight_safe ? 1 : 0) < 0) {
        goto fail;
    }
    if (!postflight_safe) {
        append_literal(stdout_buf,
                       "wifi_companion_start.result=subsys-hold-reboot-required\n"
                       "wifi_companion_start.reason=child-not-proven-stopped\n");
    } else if (*child_exit_code == 0) {
        append_literal(stdout_buf,
                       "wifi_companion_start.result=subsys-hold-window-pass\n"
                       "wifi_companion_start.reason=temporary-subsys-cdev-open-held-and-cleaned\n");
    } else {
        append_literal(stdout_buf,
                       "wifi_companion_start.result=subsys-hold-open-failed\n"
                       "wifi_companion_start.reason=no-subsys-cdev-open-succeeded\n");
    }
    append_literal(stdout_buf, "wifi_companion_start.end=1\n");
    if (stdout_pipe[0] >= 0) close(stdout_pipe[0]);
    unlink(modem_node);
    unlink(esoc_node);
    return 0;

fail:
    if (pid > 0) {
        kill(-pid, SIGKILL);
        kill(pid, SIGKILL);
        waitpid(pid, NULL, WNOHANG);
    }
    if (stdout_pipe[0] >= 0) close(stdout_pipe[0]);
    if (stdout_pipe[1] >= 0) close(stdout_pipe[1]);
    unlink(modem_node);
    unlink(esoc_node);
    return -1;
}

static int run_wifi_companion_esoc_req_registered_subsys_hold_preflight_guarded(const struct config *cfg,
                                                                               const struct paths *paths,
                                                                               struct buffer *stdout_buf,
                                                                               struct buffer *stderr_buf,
                                                                               int *child_exit_code,
                                                                               int *child_signal,
                                                                               bool *timed_out) {
    char esoc_path[MAX_PATH_LEN];
    int req_fd = -1;
    int req_rc = -1;
    int saved_errno = 0;
    int stdout_pipe[2] = {-1, -1};
    bool stdout_open = true;
    bool child_done = false;
    bool term_sent = false;
    bool kill_sent = false;
    bool reaped = false;
    bool postflight_safe = true;
    long deadline;
    pid_t pid = -1;
    pid_t pgid = -1;
    int status = 0;
    int hold_sec = cfg->timeout_sec > 3 ? cfg->timeout_sec - 2 : 1;

    (void)stderr_buf;
    *child_exit_code = -1;
    *child_signal = 0;
    *timed_out = false;
    if (append_literal(stdout_buf,
                       "esoc_req_registered_subsys_hold_preflight.begin=1\n"
                       "esoc_req_registered_subsys_hold_preflight.mode=guarded\n"
                       "esoc_req_registered_subsys_hold_preflight.device=/dev/esoc-0\n"
                       "esoc_req_registered_subsys_hold_preflight.subsys_device=/dev/subsys_esoc0\n"
                       "esoc_req_registered_subsys_hold_preflight.daemon_start_executed=0\n"
                       "esoc_req_registered_subsys_hold_preflight.mdm_helper_start_executed=0\n"
                       "esoc_req_registered_subsys_hold_preflight.ks_start_executed=0\n"
                       "esoc_req_registered_subsys_hold_preflight.pm_proxy_helper_start_executed=0\n"
                       "esoc_req_registered_subsys_hold_preflight.cnss_start_executed=0\n"
                       "esoc_req_registered_subsys_hold_preflight.service_manager_start_executed=0\n"
                       "esoc_req_registered_subsys_hold_preflight.wifi_hal_start_executed=0\n"
                       "esoc_req_registered_subsys_hold_preflight.scan_connect_linkup=0\n"
                       "esoc_req_registered_subsys_hold_preflight.credentials=0\n"
                       "esoc_req_registered_subsys_hold_preflight.dhcp_routing=0\n"
                       "esoc_req_registered_subsys_hold_preflight.external_ping=0\n"
                       "esoc_req_registered_subsys_hold_preflight.reg_cmd_eng_attempted=0\n"
                       "esoc_req_registered_subsys_hold_preflight.cmd_exe_attempted=0\n"
                       "esoc_req_registered_subsys_hold_preflight.pwr_on_attempted=0\n"
                       "esoc_req_registered_subsys_hold_preflight.wait_for_req_loop_implemented=0\n"
                       "esoc_req_registered_subsys_hold_preflight.wait_for_req_passive_observer_supported=1\n"
                       "esoc_req_registered_subsys_hold_preflight.wait_for_req_passive_observer_attempted=0\n"
                       "esoc_req_registered_subsys_hold_preflight.wait_for_req_attempted=0\n"
                       "esoc_req_registered_subsys_hold_preflight.notify_attempted=0\n") < 0 ||
        append_format(stdout_buf,
                      "esoc_req_registered_subsys_hold_preflight.uapi.ESOC_CODE=0x%x\n"
                      "esoc_req_registered_subsys_hold_preflight.uapi.ESOC_REG_REQ_ENG.request=0x%lx\n"
                      "esoc_req_registered_subsys_hold_preflight.uapi.ESOC_REG_CMD_ENG.request=0x%lx\n"
                      "esoc_req_registered_subsys_hold_preflight.uapi.ESOC_CMD_EXE.request=0x%lx\n"
                      "esoc_req_registered_subsys_hold_preflight.uapi.ESOC_PWR_ON.value=%u\n"
                      "esoc_req_registered_subsys_hold_preflight.uapi.ESOC_WAIT_FOR_REQ.request=0x%lx\n"
                      "esoc_req_registered_subsys_hold_preflight.uapi.ESOC_NOTIFY.request=0x%lx\n",
                      A90_ESOC_CODE,
                      (unsigned long)A90_ESOC_REG_REQ_ENG,
                      (unsigned long)A90_ESOC_REG_CMD_ENG,
                      (unsigned long)A90_ESOC_CMD_EXE,
                      A90_ESOC_PWR_ON,
                      (unsigned long)A90_ESOC_WAIT_FOR_REQ,
                      (unsigned long)A90_ESOC_NOTIFY) < 0 ||
        append_private_android_node_status(stdout_buf, paths, "esoc-0", "esoc_0") < 0 ||
        append_private_android_node_status(stdout_buf, paths, "subsys_esoc0", "subsys_esoc0") < 0 ||
        append_private_android_node_status(stdout_buf, paths, "subsys_modem", "subsys_modem") < 0) {
        return -1;
    }
    if (!cfg->allow_esoc_req_registered_subsys_hold_preflight) {
        if (append_literal(stdout_buf,
                           "esoc_req_registered_subsys_hold_preflight.allowed=0\n"
                           "esoc_req_registered_subsys_hold_preflight.open_req_attempted=0\n"
                           "esoc_req_registered_subsys_hold_preflight.reg_req_eng_attempted=0\n"
                           "esoc_req_registered_subsys_hold_preflight.subsys_esoc0_open_attempted=0\n"
                           "esoc_req_registered_subsys_hold_preflight.wait_for_req_passive_observer_attempted=0\n"
                           "esoc_req_registered_subsys_hold_preflight.child_started=0\n"
                           "esoc_req_registered_subsys_hold_preflight.result=blocked\n"
                           "esoc_req_registered_subsys_hold_preflight.reason=missing-esoc-req-registered-subsys-hold-preflight-allow-flag\n"
                           "esoc_req_registered_subsys_hold_preflight.end=1\n") < 0) {
            return -1;
        }
        *child_exit_code = 0;
        return 0;
    }
    if (append_literal(stdout_buf,
                       "esoc_req_registered_subsys_hold_preflight.allowed=1\n"
                       "esoc_req_registered_subsys_hold_preflight.open_req_attempted=1\n") < 0) {
        return -1;
    }
    if (append_path(esoc_path, sizeof(esoc_path), paths->dev, "esoc-0") < 0) {
        if (append_literal(stdout_buf,
                           "esoc_req_registered_subsys_hold_preflight.result=path-too-long\n"
                           "esoc_req_registered_subsys_hold_preflight.end=1\n") < 0) {
            return -1;
        }
        *child_exit_code = 0;
        return 0;
    }
    errno = 0;
    req_fd = open(esoc_path, O_RDONLY | O_CLOEXEC);
    saved_errno = req_fd < 0 ? errno : 0;
    if (append_format(stdout_buf,
                      "esoc_req_registered_subsys_hold_preflight.open_req.path=%s\n"
                      "esoc_req_registered_subsys_hold_preflight.open_req.fd=%d\n"
                      "esoc_req_registered_subsys_hold_preflight.open_req.errno=%d\n",
                      esoc_path,
                      req_fd,
                      saved_errno) < 0) {
        if (req_fd >= 0) {
            close(req_fd);
        }
        return -1;
    }
    if (req_fd < 0) {
        if (append_literal(stdout_buf,
                           "esoc_req_registered_subsys_hold_preflight.reg_req_eng_attempted=0\n"
                           "esoc_req_registered_subsys_hold_preflight.subsys_esoc0_open_attempted=0\n"
                           "esoc_req_registered_subsys_hold_preflight.child_started=0\n"
                           "esoc_req_registered_subsys_hold_preflight.result=open-req-failed\n"
                           "esoc_req_registered_subsys_hold_preflight.end=1\n") < 0) {
            return -1;
        }
        *child_exit_code = 0;
        return 0;
    }
    errno = 0;
    req_rc = ioctl(req_fd, A90_ESOC_REG_REQ_ENG);
    saved_errno = req_rc < 0 ? errno : 0;
    if (append_format(stdout_buf,
                      "esoc_req_registered_subsys_hold_preflight.reg_req_eng_attempted=1\n"
                      "esoc_req_registered_subsys_hold_preflight.ioctl.REG_REQ_ENG.request=0x%lx\n"
                      "esoc_req_registered_subsys_hold_preflight.ioctl.REG_REQ_ENG.rc=%d\n"
                      "esoc_req_registered_subsys_hold_preflight.ioctl.REG_REQ_ENG.errno=%d\n",
                      (unsigned long)A90_ESOC_REG_REQ_ENG,
                      req_rc,
                      saved_errno) < 0) {
        close(req_fd);
        return -1;
    }
    if (req_rc < 0) {
        close(req_fd);
        if (append_literal(stdout_buf,
                           "esoc_req_registered_subsys_hold_preflight.close_req_attempted=1\n"
                           "esoc_req_registered_subsys_hold_preflight.subsys_esoc0_open_attempted=0\n"
                           "esoc_req_registered_subsys_hold_preflight.child_started=0\n"
                           "esoc_req_registered_subsys_hold_preflight.result=reg-req-eng-failed\n"
                           "esoc_req_registered_subsys_hold_preflight.end=1\n") < 0) {
            return -1;
        }
        *child_exit_code = 0;
        return 0;
    }
    if (append_esoc_req_subsys_hold_snapshot(stdout_buf, "before") < 0 ||
        append_format(stdout_buf,
                      "esoc_req_registered_subsys_hold_preflight.req_fd_held=1\n"
                      "esoc_req_registered_subsys_hold_preflight.subsys_esoc0_open_attempted=1\n"
                      "esoc_req_registered_subsys_hold_preflight.wait_for_req_passive_observer_attempted=1\n"
                      "esoc_req_registered_subsys_hold_preflight.wait_for_req_attempted=1\n"
                      "esoc_req_registered_subsys_hold_preflight.hold_sec=%d\n",
                      hold_sec) < 0) {
        close(req_fd);
        return -1;
    }
    if (pipe2(stdout_pipe, O_CLOEXEC) < 0) {
        saved_errno = errno;
        close(req_fd);
        return append_format(stdout_buf,
                             "esoc_req_registered_subsys_hold_preflight.child_started=0\n"
                             "esoc_req_registered_subsys_hold_preflight.close_req_attempted=1\n"
                             "esoc_req_registered_subsys_hold_preflight.result=manual-review-required\n"
                             "esoc_req_registered_subsys_hold_preflight.reason=pipe-failed-%s\n"
                             "esoc_req_registered_subsys_hold_preflight.end=1\n",
                             strerror(saved_errno));
    }
    pid = fork();
    if (pid < 0) {
        saved_errno = errno;
        close(stdout_pipe[0]);
        close(stdout_pipe[1]);
        close(req_fd);
        return append_format(stdout_buf,
                             "esoc_req_registered_subsys_hold_preflight.child_started=0\n"
                             "esoc_req_registered_subsys_hold_preflight.close_req_attempted=1\n"
                             "esoc_req_registered_subsys_hold_preflight.result=manual-review-required\n"
                             "esoc_req_registered_subsys_hold_preflight.reason=fork-failed-%s\n"
                             "esoc_req_registered_subsys_hold_preflight.end=1\n",
                             strerror(saved_errno));
    }
    if (pid == 0) {
        int esoc_fd;
        pid_t observer_pid = -1;
        int observer_status = 0;
        int observer_exit_code = -1;
        int observer_signal = 0;
        bool observer_term_sent = false;
        bool observer_kill_sent = false;
        bool observer_reaped = false;

        close(stdout_pipe[0]);
        if (setsid() < 0) {
            dprintf(stdout_pipe[1], "esoc_req_registered_subsys_hold_preflight.child_setsid_error=%s\n", strerror(errno));
            _exit(120);
        }
        if (chroot(paths->root) < 0) {
            dprintf(stdout_pipe[1], "esoc_req_registered_subsys_hold_preflight.child_chroot_error=%s\n", strerror(errno));
            _exit(121);
        }
        if (chdir("/") < 0) {
            dprintf(stdout_pipe[1], "esoc_req_registered_subsys_hold_preflight.child_chdir_error=%s\n", strerror(errno));
            _exit(122);
        }
        dprintf(stdout_pipe[1],
                "esoc_req_registered_subsys_hold_preflight.child_chroot=1\n"
                "esoc_req_registered_subsys_hold_preflight.child_hold_sec=%d\n",
                hold_sec);
        observer_pid = fork();
        if (observer_pid < 0) {
            dprintf(stdout_pipe[1],
                    "esoc_req_registered_subsys_hold_preflight.wait_for_req_observer.child_started=0\n"
                    "esoc_req_registered_subsys_hold_preflight.wait_for_req_observer.fork_errno=%d\n"
                    "esoc_req_registered_subsys_hold_preflight.wait_for_req_observer.fork_error=%s\n",
                    errno,
                    strerror(errno));
        } else if (observer_pid == 0) {
            int observer_rc = run_esoc_wait_for_req_observer_child(stdout_pipe[1], req_fd, hold_sec);

            _exit(observer_rc);
        } else {
            dprintf(stdout_pipe[1],
                    "esoc_req_registered_subsys_hold_preflight.wait_for_req_observer.child_started=1\n"
                    "esoc_req_registered_subsys_hold_preflight.wait_for_req_observer.pid=%ld\n",
                    (long)observer_pid);
        }
        esoc_fd = open_esoc_req_registered_subsys_child_node(stdout_pipe[1]);
        if (esoc_fd >= 0) {
            for (int i = 0; i < hold_sec * 10; i++) {
                usleep(100000);
            }
            close(esoc_fd);
        }
        if (observer_pid > 0) {
            pid_t wait_rc = waitpid(observer_pid, &observer_status, WNOHANG);

            if (wait_rc == observer_pid) {
                observer_reaped = true;
            } else if (wait_rc == 0) {
                if (kill(observer_pid, SIGTERM) == 0 || errno == ESRCH) {
                    observer_term_sent = true;
                }
                for (int i = 0; i < 10 && !observer_reaped; i++) {
                    wait_rc = waitpid(observer_pid, &observer_status, WNOHANG);
                    if (wait_rc == observer_pid) {
                        observer_reaped = true;
                        break;
                    }
                    usleep(100000);
                }
                if (!observer_reaped && (kill(observer_pid, SIGKILL) == 0 || errno == ESRCH)) {
                    observer_kill_sent = true;
                }
                for (int i = 0; i < 10 && !observer_reaped; i++) {
                    wait_rc = waitpid(observer_pid, &observer_status, WNOHANG);
                    if (wait_rc == observer_pid) {
                        observer_reaped = true;
                        break;
                    }
                    usleep(100000);
                }
            }
            if (observer_reaped) {
                if (WIFEXITED(observer_status)) {
                    observer_exit_code = WEXITSTATUS(observer_status);
                } else if (WIFSIGNALED(observer_status)) {
                    observer_signal = WTERMSIG(observer_status);
                }
            }
            dprintf(stdout_pipe[1],
                    "esoc_req_registered_subsys_hold_preflight.wait_for_req_observer.term_sent=%d\n"
                    "esoc_req_registered_subsys_hold_preflight.wait_for_req_observer.kill_sent=%d\n"
                    "esoc_req_registered_subsys_hold_preflight.wait_for_req_observer.reaped=%d\n"
                    "esoc_req_registered_subsys_hold_preflight.wait_for_req_observer.exit_code=%d\n"
                    "esoc_req_registered_subsys_hold_preflight.wait_for_req_observer.signal=%d\n",
                    observer_term_sent ? 1 : 0,
                    observer_kill_sent ? 1 : 0,
                    observer_reaped ? 1 : 0,
                    observer_exit_code,
                    observer_signal);
        }
        dprintf(stdout_pipe[1],
                "esoc_req_registered_subsys_hold_preflight.child_done=1\n");
        close(stdout_pipe[1]);
        _exit(esoc_fd >= 0 ? 0 : 31);
    }

    close(stdout_pipe[1]);
    stdout_pipe[1] = -1;
    set_nonblock(stdout_pipe[0]);
    pgid = wait_for_child_session_pgid(pid, 1000);
    if (append_format(stdout_buf,
                      "esoc_req_registered_subsys_hold_preflight.child_started=1\n"
                      "esoc_req_registered_subsys_hold_preflight.pid=%ld\n"
                      "esoc_req_registered_subsys_hold_preflight.pgid=%ld\n",
                      (long)pid,
                      (long)pgid) < 0) {
        goto fail;
    }
    usleep(500000);
    drain_fd(stdout_pipe[0], stdout_buf, &stdout_open);
    if (append_esoc_req_subsys_hold_snapshot(stdout_buf, "hold") < 0) {
        goto fail;
    }
    deadline = monotonic_ms() + cfg->timeout_sec * 1000L;
    while (stdout_open || !child_done) {
        struct pollfd fds[1];
        int nfds = 0;

        if (!child_done && monotonic_ms() >= deadline) {
            *timed_out = true;
            break;
        }
        if (stdout_open) {
            fds[nfds].fd = stdout_pipe[0];
            fds[nfds].events = POLLIN | POLLHUP | POLLERR;
            nfds++;
        }
        if (nfds > 0 && poll(fds, nfds, 50) > 0 && fds[0].revents != 0) {
            drain_fd(stdout_pipe[0], stdout_buf, &stdout_open);
        } else {
            usleep(50000);
        }
        if (!child_done) {
            pid_t wait_rc = waitpid(pid, &status, WNOHANG);

            if (wait_rc == pid) {
                child_done = true;
                reaped = true;
                if (WIFEXITED(status)) {
                    *child_exit_code = WEXITSTATUS(status);
                } else if (WIFSIGNALED(status)) {
                    *child_signal = WTERMSIG(status);
                }
            } else if (wait_rc < 0 && errno != EINTR && errno != ECHILD) {
                append_format(stdout_buf,
                              "esoc_req_registered_subsys_hold_preflight.wait_error=%s\n",
                              strerror(errno));
                break;
            }
        }
    }
    if (!child_done) {
        if (kill(-pgid, SIGTERM) == 0 || errno == ESRCH) {
            term_sent = true;
        }
        deadline = monotonic_ms() + 1000L;
        while (!child_done && monotonic_ms() < deadline) {
            if (waitpid(pid, &status, WNOHANG) == pid) {
                child_done = true;
                reaped = true;
                if (WIFEXITED(status)) {
                    *child_exit_code = WEXITSTATUS(status);
                } else if (WIFSIGNALED(status)) {
                    *child_signal = WTERMSIG(status);
                }
                break;
            }
            if (stdout_open) {
                drain_fd(stdout_pipe[0], stdout_buf, &stdout_open);
            }
            usleep(50000);
        }
    }
    if (!child_done) {
        if (kill(-pgid, SIGKILL) == 0 || errno == ESRCH) {
            kill_sent = true;
        }
        deadline = monotonic_ms() + 1000L;
        while (!child_done && monotonic_ms() < deadline) {
            if (waitpid(pid, &status, WNOHANG) == pid) {
                child_done = true;
                reaped = true;
                if (WIFEXITED(status)) {
                    *child_exit_code = WEXITSTATUS(status);
                } else if (WIFSIGNALED(status)) {
                    *child_signal = WTERMSIG(status);
                }
                break;
            }
            usleep(50000);
        }
    }
    if (stdout_open) {
        drain_fd(stdout_pipe[0], stdout_buf, &stdout_open);
    }
    close(req_fd);
    req_fd = -1;
    postflight_safe = reaped && (kill(-pgid, 0) < 0 && errno == ESRCH);
    if (append_esoc_req_subsys_hold_snapshot(stdout_buf, "after") < 0 ||
        append_format(stdout_buf,
                      "esoc_req_registered_subsys_hold_preflight.close_req_attempted=1\n"
                      "esoc_req_registered_subsys_hold_preflight.exited=%d\n"
                      "esoc_req_registered_subsys_hold_preflight.exit_code=%d\n"
                      "esoc_req_registered_subsys_hold_preflight.signal=%d\n"
                      "esoc_req_registered_subsys_hold_preflight.timed_out=%d\n"
                      "esoc_req_registered_subsys_hold_preflight.term_sent=%d\n"
                      "esoc_req_registered_subsys_hold_preflight.kill_sent=%d\n"
                      "esoc_req_registered_subsys_hold_preflight.reaped=%d\n"
                      "esoc_req_registered_subsys_hold_preflight.all_postflight_safe=%d\n",
                      child_done ? 1 : 0,
                      *child_exit_code,
                      *child_signal,
                      *timed_out ? 1 : 0,
                      term_sent ? 1 : 0,
                      kill_sent ? 1 : 0,
                      reaped ? 1 : 0,
                      postflight_safe ? 1 : 0) < 0) {
        goto fail;
    }
    if (!postflight_safe) {
        append_literal(stdout_buf,
                       "esoc_req_registered_subsys_hold_preflight.result=reboot-required\n"
                       "esoc_req_registered_subsys_hold_preflight.reason=child-not-proven-stopped\n");
    } else if (*child_exit_code == 0) {
        append_literal(stdout_buf,
                       "esoc_req_registered_subsys_hold_preflight.result=req-registered-subsys-hold-window-pass\n"
                       "esoc_req_registered_subsys_hold_preflight.reason=req-engine-held-while-subsys-esoc0-opened-and-cleaned\n");
    } else {
        append_literal(stdout_buf,
                       "esoc_req_registered_subsys_hold_preflight.result=subsys-esoc0-open-failed\n"
                       "esoc_req_registered_subsys_hold_preflight.reason=subsys-cdev-open-did-not-succeed\n");
    }
    append_literal(stdout_buf, "esoc_req_registered_subsys_hold_preflight.end=1\n");
    if (stdout_pipe[0] >= 0) close(stdout_pipe[0]);
    return 0;

fail:
    if (pid > 0) {
        kill(-pid, SIGKILL);
        kill(pid, SIGKILL);
        waitpid(pid, NULL, WNOHANG);
    }
    if (req_fd >= 0) close(req_fd);
    if (stdout_pipe[0] >= 0) close(stdout_pipe[0]);
    if (stdout_pipe[1] >= 0) close(stdout_pipe[1]);
    return -1;
}


static pid_t wait_for_child_session_pgid(pid_t pid, long timeout_ms) {
    long deadline = monotonic_ms() + timeout_ms;

    while (monotonic_ms() < deadline) {
        pid_t pgid = getpgid(pid);

        if (pgid == pid) {
            return pgid;
        }
        if (pgid < 0 && errno == ESRCH) {
            break;
        }
        usleep(10000);
    }
    return pid;
}

static int append_proc_fd_summary(struct buffer *buf, pid_t pid, bool *captured) {
    char path[MAX_PATH_LEN];
    DIR *dir;
    struct dirent *entry;
    int count = 0;

    *captured = false;
    proc_path(path, sizeof(path), pid, "fd");
    dir = opendir(path);
    if (dir == NULL) {
        return append_format(buf, "cnss_start.fd_summary.error=%s\n", strerror(errno));
    }
    while ((entry = readdir(dir)) != NULL) {
        if (strcmp(entry->d_name, ".") == 0 || strcmp(entry->d_name, "..") == 0) {
            continue;
        }
        count++;
    }
    closedir(dir);
    *captured = true;
    return append_format(buf, "cnss_start.fd_summary.count=%d\n", count);
}

static int append_proc_fdinfo_compact(struct buffer *buf,
                                      pid_t pid,
                                      const char *label,
                                      int entry_index,
                                      const char *fd_name) {
    char path[MAX_PATH_LEN];
    FILE *file;
    char line[256];
    int line_count = 0;
    bool truncated = false;

    if (snprintf(path,
                 sizeof(path),
                 "/proc/%ld/fdinfo/%s",
                 (long)pid,
                 fd_name) >= (int)sizeof(path)) {
        return append_format(buf,
                             "capture.%s.fd_links.entry_%02d.fdinfo.error=path-too-long\n",
                             label,
                             entry_index);
    }
    if (append_format(buf,
                      "capture.%s.fd_links.entry_%02d.fdinfo.begin=1\n"
                      "capture.%s.fd_links.entry_%02d.fdinfo.path=%s\n",
                      label,
                      entry_index,
                      label,
                      entry_index,
                      path) < 0) {
        return -1;
    }
    file = fopen(path, "re");
    if (file == NULL) {
        return append_format(buf,
                             "capture.%s.fd_links.entry_%02d.fdinfo.error=%s\n"
                             "capture.%s.fd_links.entry_%02d.fdinfo.end=1\n",
                             label,
                             entry_index,
                             strerror(errno),
                             label,
                             entry_index);
    }
    while (fgets(line, sizeof(line), file) != NULL) {
        char key[64];
        char value[160];
        int parsed;

        sanitize_one_line(line);
        if (line_count < 16) {
            if (append_format(buf,
                              "capture.%s.fd_links.entry_%02d.fdinfo.line_%02d=%s\n",
                              label,
                              entry_index,
                              line_count,
                              line) < 0) {
                fclose(file);
                return -1;
            }
        } else {
            truncated = true;
        }
        parsed = sscanf(line, "%63[^:]:%159s", key, value);
        if (parsed == 2 &&
            (strcmp(key, "pos") == 0 ||
             strcmp(key, "flags") == 0 ||
             strcmp(key, "mnt_id") == 0 ||
             strcmp(key, "ino") == 0)) {
            if (append_format(buf,
                              "capture.%s.fd_links.entry_%02d.fdinfo.%s=%s\n",
                              label,
                              entry_index,
                              key,
                              value) < 0) {
                fclose(file);
                return -1;
            }
        }
        line_count++;
    }
    fclose(file);
    return append_format(buf,
                         "capture.%s.fd_links.entry_%02d.fdinfo.lines=%d\n"
                         "capture.%s.fd_links.entry_%02d.fdinfo.truncated=%d\n"
                         "capture.%s.fd_links.entry_%02d.fdinfo.end=1\n",
                         label,
                         entry_index,
                         line_count < 16 ? line_count : 16,
                         label,
                         entry_index,
                         truncated ? 1 : 0,
                         label,
                         entry_index);
}

static int append_proc_fd_links_compact(struct buffer *buf, pid_t pid, const char *label) {
    char dir_path[MAX_PATH_LEN];
    DIR *dir;
    struct dirent *entry;
    int count = 0;
    int shown = 0;
    int socket_count = 0;
    int anon_inode_count = 0;
    bool truncated = false;

    proc_path(dir_path, sizeof(dir_path), pid, "fd");
    if (append_format(buf,
                      "capture.%s.fd_links.begin=1\n"
                      "capture.%s.fd_links.path=%s\n",
                      label,
                      label,
                      dir_path) < 0) {
        return -1;
    }
    dir = opendir(dir_path);
    if (dir == NULL) {
        return append_format(buf,
                             "capture.%s.fd_links.error=%s\n"
                             "capture.%s.fd_links.end=1\n",
                             label,
                             strerror(errno),
                             label);
    }
    while ((entry = readdir(dir)) != NULL) {
        char fd_path[MAX_PATH_LEN];
        char target[MAX_PATH_LEN];
        ssize_t nread;

        if (strcmp(entry->d_name, ".") == 0 || strcmp(entry->d_name, "..") == 0) {
            continue;
        }
        count++;
        if (snprintf(fd_path, sizeof(fd_path), "%s/%s", dir_path, entry->d_name) >= (int)sizeof(fd_path)) {
            truncated = true;
            continue;
        }
        nread = readlink(fd_path, target, sizeof(target) - 1);
        if (nread < 0) {
            if (shown < 64 &&
                append_format(buf,
                              "capture.%s.fd_links.entry_%02d.fd=%s\n"
                              "capture.%s.fd_links.entry_%02d.error=%s\n",
                              label,
                              shown,
                              entry->d_name,
                              label,
                              shown,
                              strerror(errno)) < 0) {
                closedir(dir);
                return -1;
            }
            shown++;
            continue;
        }
        target[nread] = '\0';
        if (strncmp(target, "socket:", 7) == 0) {
            socket_count++;
        }
        if (strncmp(target, "anon_inode:", 11) == 0) {
            anon_inode_count++;
        }
        if (shown < 64) {
            if (append_format(buf,
                              "capture.%s.fd_links.entry_%02d.fd=%s\n"
                              "capture.%s.fd_links.entry_%02d.target=%s\n",
                              label,
                              shown,
                              entry->d_name,
                              label,
                              shown,
                              target) < 0) {
                closedir(dir);
                return -1;
            }
            if (strncmp(target, "socket:", 7) == 0 &&
                append_proc_fdinfo_compact(buf, pid, label, shown, entry->d_name) < 0) {
                closedir(dir);
                return -1;
            }
        } else {
            truncated = true;
        }
        shown++;
    }
    closedir(dir);
    return append_format(buf,
                         "capture.%s.fd_links.count=%d\n"
                         "capture.%s.fd_links.socket_count=%d\n"
                         "capture.%s.fd_links.anon_inode_count=%d\n"
                         "capture.%s.fd_links.shown=%d\n"
                         "capture.%s.fd_links.truncated=%d\n"
                         "capture.%s.fd_links.end=1\n",
                         label,
                         count,
                         label,
                         socket_count,
                         label,
                         anon_inode_count,
                         label,
                         shown < 64 ? shown : 64,
                         label,
                         truncated ? 1 : 0,
                         label);
}

static bool decimal_name(const char *name) {
    if (name == NULL || *name == '\0') {
        return false;
    }
    for (const char *ptr = name; *ptr != '\0'; ptr++) {
        if (*ptr < '0' || *ptr > '9') {
            return false;
        }
    }
    return true;
}

static int append_proc_task_stall_capture(struct buffer *buf, pid_t pid, const char *label) {
    char task_path[MAX_PATH_LEN];
    DIR *dir;
    struct dirent *entry;
    int count = 0;
    int shown = 0;
    bool truncated = false;

    if (snprintf(task_path, sizeof(task_path), "/proc/%ld/task", (long)pid) >= (int)sizeof(task_path)) {
        return append_format(buf,
                             "capture.%s.stall_tasks.begin=1\n"
                             "capture.%s.stall_tasks.error=path-too-long\n"
                             "capture.%s.stall_tasks.end=1\n",
                             label,
                             label,
                             label);
    }
    if (append_format(buf,
                      "capture.%s.stall_tasks.begin=1\n"
                      "capture.%s.stall_tasks.path=%s\n",
                      label,
                      label,
                      task_path) < 0) {
        return -1;
    }
    dir = opendir(task_path);
    if (dir == NULL) {
        return append_format(buf,
                             "capture.%s.stall_tasks.error=%s\n"
                             "capture.%s.stall_tasks.end=1\n",
                             label,
                             strerror(errno),
                             label);
    }
    while ((entry = readdir(dir)) != NULL) {
        char path[MAX_PATH_LEN];
        char capture_label[160];
        bool captured = false;

        if (!decimal_name(entry->d_name)) {
            continue;
        }
        count++;
        if (shown >= 16) {
            truncated = true;
            continue;
        }
        if (append_format(buf,
                          "capture.%s.stall_tasks.entry_%02d.tid=%s\n",
                          label,
                          shown,
                          entry->d_name) < 0) {
            closedir(dir);
            return -1;
        }
        if (snprintf(path, sizeof(path), "%s/%s/status", task_path, entry->d_name) < (int)sizeof(path) &&
            snprintf(capture_label, sizeof(capture_label), "%s_stall_task_%s_status", label, entry->d_name) < (int)sizeof(capture_label) &&
            append_path_file_capture_named(buf, path, capture_label, 4096, &captured) < 0) {
            closedir(dir);
            return -1;
        }
        if (snprintf(path, sizeof(path), "%s/%s/stat", task_path, entry->d_name) < (int)sizeof(path) &&
            snprintf(capture_label, sizeof(capture_label), "%s_stall_task_%s_stat", label, entry->d_name) < (int)sizeof(capture_label) &&
            append_path_file_capture_named(buf, path, capture_label, 2048, &captured) < 0) {
            closedir(dir);
            return -1;
        }
        if (snprintf(path, sizeof(path), "%s/%s/wchan", task_path, entry->d_name) < (int)sizeof(path) &&
            snprintf(capture_label, sizeof(capture_label), "%s_stall_task_%s_wchan", label, entry->d_name) < (int)sizeof(capture_label) &&
            append_path_file_capture_named(buf, path, capture_label, 1024, &captured) < 0) {
            closedir(dir);
            return -1;
        }
        if (snprintf(path, sizeof(path), "%s/%s/syscall", task_path, entry->d_name) < (int)sizeof(path) &&
            snprintf(capture_label, sizeof(capture_label), "%s_stall_task_%s_syscall", label, entry->d_name) < (int)sizeof(capture_label) &&
            append_path_file_capture_named(buf, path, capture_label, 1024, &captured) < 0) {
            closedir(dir);
            return -1;
        }
        shown++;
    }
    closedir(dir);
    return append_format(buf,
                         "capture.%s.stall_tasks.count=%d\n"
                         "capture.%s.stall_tasks.shown=%d\n"
                         "capture.%s.stall_tasks.truncated=%d\n"
                         "capture.%s.stall_tasks.end=1\n",
                         label,
                         count,
                         label,
                         shown,
                         label,
                         truncated ? 1 : 0,
                         label);
}

static int append_cnss_stall_snapshot_capture(struct buffer *buf, pid_t pid, const char *label) {
    bool wchan_captured = false;
    bool syscall_captured = false;
    bool stack_captured = false;
    bool stat_captured = false;
    bool sched_captured = false;
    bool netlink_captured = false;
    bool unix_captured = false;
    bool qrtr_captured = false;
    bool protocols_captured = false;
    bool task_captured = false;

    if (append_format(buf,
                      "capture.%s.stall_snapshot.begin=1\n"
                      "capture.%s.stall_snapshot.pid=%ld\n",
                      label,
                      label,
                      (long)pid) < 0 ||
        append_proc_file_capture_named(buf, pid, "wchan", "wifi_stall_cnss_wchan", 1024, &wchan_captured) < 0 ||
        append_proc_file_capture_named(buf, pid, "syscall", "wifi_stall_cnss_syscall", 1024, &syscall_captured) < 0 ||
        append_proc_file_capture_named(buf, pid, "stack", "wifi_stall_cnss_stack", 8192, &stack_captured) < 0 ||
        append_proc_file_capture_named(buf, pid, "stat", "wifi_stall_cnss_stat", 2048, &stat_captured) < 0 ||
        append_proc_file_capture_named(buf, pid, "sched", "wifi_stall_cnss_sched", 8192, &sched_captured) < 0 ||
        append_path_file_capture_named(buf, "/proc/net/netlink", "wifi_stall_proc_net_netlink", 32768, &netlink_captured) < 0 ||
        append_path_file_capture_named(buf, "/proc/net/unix", "wifi_stall_proc_net_unix", 32768, &unix_captured) < 0 ||
        append_path_file_capture_named(buf, "/proc/net/qrtr", "wifi_stall_proc_net_qrtr", 32768, &qrtr_captured) < 0 ||
        append_path_file_capture_named(buf, "/proc/net/protocols", "wifi_stall_proc_net_protocols", 32768, &protocols_captured) < 0 ||
        append_proc_task_stall_capture(buf, pid, label) < 0) {
        return -1;
    }
    task_captured = true;
    return append_format(buf,
                         "capture.%s.stall_snapshot.wchan_captured=%d\n"
                         "capture.%s.stall_snapshot.syscall_captured=%d\n"
                         "capture.%s.stall_snapshot.stack_captured=%d\n"
                         "capture.%s.stall_snapshot.stat_captured=%d\n"
                         "capture.%s.stall_snapshot.sched_captured=%d\n"
                         "capture.%s.stall_snapshot.netlink_captured=%d\n"
                         "capture.%s.stall_snapshot.unix_captured=%d\n"
                         "capture.%s.stall_snapshot.qrtr_captured=%d\n"
                         "capture.%s.stall_snapshot.protocols_captured=%d\n"
                         "capture.%s.stall_snapshot.task_captured=%d\n"
                         "capture.%s.stall_snapshot.end=1\n",
                         label,
                         wchan_captured ? 1 : 0,
                         label,
                         syscall_captured ? 1 : 0,
                         label,
                         stack_captured ? 1 : 0,
                         label,
                         stat_captured ? 1 : 0,
                         label,
                         sched_captured ? 1 : 0,
                         label,
                         netlink_captured ? 1 : 0,
                         label,
                         unix_captured ? 1 : 0,
                         label,
                         qrtr_captured ? 1 : 0,
                         label,
                         protocols_captured ? 1 : 0,
                         label,
                         task_captured ? 1 : 0,
                         label);
}

static int append_qipcrtr_protocol_summary(struct buffer *buf, const char *prefix) {
    FILE *file;
    char line[512];
    bool found = false;
    int sockets = -1;
    long size = -1;

    if (append_format(buf, "%s.begin=1\n", prefix) < 0) {
        return -1;
    }
    file = fopen("/proc/net/protocols", "re");
    if (file == NULL) {
        return append_format(buf,
                             "%s.protocols_open=0\n"
                             "%s.protocols_error=%s\n"
                             "%s.qipcrtr_present=0\n"
                             "%s.qipcrtr_sockets=-1\n"
                             "%s.end=1\n",
                             prefix,
                             prefix,
                             strerror(errno),
                             prefix,
                             prefix,
                             prefix);
    }
    while (fgets(line, sizeof(line), file) != NULL) {
        char name[64];
        long parsed_size;
        int parsed_sockets;
        size_t len = strlen(line);

        while (len > 0 && (line[len - 1] == '\n' || line[len - 1] == '\r')) {
            line[--len] = '\0';
        }
        if (sscanf(line, "%63s %ld %d", name, &parsed_size, &parsed_sockets) == 3 &&
            strcmp(name, "QIPCRTR") == 0) {
            found = true;
            size = parsed_size;
            sockets = parsed_sockets;
            if (append_format(buf, "%s.qipcrtr_line=%s\n", prefix, line) < 0) {
                fclose(file);
                return -1;
            }
            break;
        }
    }
    fclose(file);
    return append_format(buf,
                         "%s.protocols_open=1\n"
                         "%s.qipcrtr_present=%d\n"
                         "%s.qipcrtr_size=%ld\n"
                         "%s.qipcrtr_sockets=%d\n"
                         "%s.end=1\n",
                         prefix,
                         prefix,
                         found ? 1 : 0,
                         prefix,
                         size,
                         prefix,
                         sockets,
                         prefix);
}

static bool parse_pid_name(const char *text, pid_t *pid) {
    char *end = NULL;
    long value;

    if (text == NULL || *text == '\0') {
        return false;
    }
    errno = 0;
    value = strtol(text, &end, 10);
    if (errno != 0 || end == text || *end != '\0' || value <= 0) {
        return false;
    }
    *pid = (pid_t)value;
    return true;
}

static void read_proc_comm(pid_t pid, char *out, size_t out_size) {
    char path[MAX_PATH_LEN];
    FILE *file;

    if (out_size == 0) {
        return;
    }
    out[0] = '\0';
    proc_path(path, sizeof(path), pid, "comm");
    file = fopen(path, "re");
    if (file == NULL) {
        snprintf(out, out_size, "unknown");
        return;
    }
    if (fgets(out, (int)out_size, file) == NULL) {
        snprintf(out, out_size, "unknown");
    } else {
        size_t len = strlen(out);

        while (len > 0 && (out[len - 1] == '\n' || out[len - 1] == '\r')) {
            out[--len] = '\0';
        }
    }
    fclose(file);
}

static char read_proc_state(pid_t pid) {
    char path[MAX_PATH_LEN];
    char line[512];
    FILE *file;
    char *close_paren;

    proc_path(path, sizeof(path), pid, "stat");
    file = fopen(path, "re");
    if (file == NULL) {
        return '?';
    }
    if (fgets(line, sizeof(line), file) == NULL) {
        fclose(file);
        return '?';
    }
    fclose(file);
    close_paren = strrchr(line, ')');
    if (close_paren == NULL || close_paren[1] != ' ' || close_paren[2] == '\0') {
        return '?';
    }
    return close_paren[2];
}

static int append_pgid_scan_summary(struct buffer *buf,
                                    const char *prefix,
                                    const char *phase,
                                    pid_t pgid,
                                    int *match_count) {
    DIR *dir;
    struct dirent *entry;
    int count = 0;

    *match_count = -1;
    dir = opendir("/proc");
    if (dir == NULL) {
        return append_format(buf,
                             "%s.pgid_scan.%s.error=%s\n",
                             prefix,
                             phase,
                             strerror(errno));
    }
    while ((entry = readdir(dir)) != NULL) {
        pid_t pid;
        pid_t candidate_pgid;
        char comm[128];
        char state;

        if (!parse_pid_name(entry->d_name, &pid)) {
            continue;
        }
        candidate_pgid = getpgid(pid);
        if (candidate_pgid < 0 || candidate_pgid != pgid) {
            continue;
        }
        read_proc_comm(pid, comm, sizeof(comm));
        state = read_proc_state(pid);
        if (append_format(buf,
                          "%s.pgid_scan.%s.entry.%d=pid:%ld state:%c comm:%s\n",
                          prefix,
                          phase,
                          count,
                          (long)pid,
                          state,
                          comm) < 0) {
            closedir(dir);
            return -1;
        }
        count++;
    }
    closedir(dir);
    *match_count = count;
    return append_format(buf,
                         "%s.pgid_scan.%s.count=%d\n",
                         prefix,
                         phase,
                         count);
}

static int append_proc_link_compact(struct buffer *buf,
                                    pid_t pid,
                                    const char *label,
                                    const char *name) {
    char path[MAX_PATH_LEN];
    char target[MAX_PATH_LEN];
    ssize_t nread;

    proc_path(path, sizeof(path), pid, name);
    nread = readlink(path, target, sizeof(target) - 1);
    if (nread < 0) {
        return append_format(buf,
                             "capture.%s.%s.error=%s\n",
                             label,
                             name,
                             strerror(errno));
    }
    target[nread] = '\0';
    return append_format(buf,
                         "capture.%s.%s=%s\n",
                         label,
                         name,
                         target);
}

static int append_proc_text_brief(struct buffer *buf,
                                  pid_t pid,
                                  const char *label,
                                  const char *name,
                                  size_t limit) {
    char path[MAX_PATH_LEN];
    char tmp[4096];
    size_t total = 0;
    size_t lines = 0;
    bool truncated = false;
    int fd;

    proc_path(path, sizeof(path), pid, name);
    if (append_format(buf,
                      "capture.%s.%s.path=%s\n",
                      label,
                      name,
                      path) < 0) {
        return -1;
    }
    fd = open(path, O_RDONLY | O_CLOEXEC);
    if (fd < 0) {
        return append_format(buf,
                             "capture.%s.%s.error=%s\n",
                             label,
                             name,
                             strerror(errno));
    }
    while (total < limit) {
        size_t room = limit - total;
        ssize_t nread = read(fd, tmp, room < sizeof(tmp) ? room : sizeof(tmp));

        if (nread < 0) {
            if (errno == EINTR) {
                continue;
            }
            close(fd);
            return append_format(buf,
                                 "capture.%s.%s.read_error=%s\n",
                                 label,
                                 name,
                                 strerror(errno));
        }
        if (nread == 0) {
            break;
        }
        for (ssize_t i = 0; i < nread; i++) {
            if (tmp[i] == '\n') {
                lines++;
            }
        }
        total += (size_t)nread;
    }
    if (total >= limit) {
        truncated = true;
    }
    close(fd);
    return append_format(buf,
                         "capture.%s.%s.bytes=%zu\n"
                         "capture.%s.%s.lines=%zu\n"
                         "capture.%s.%s.truncated=%d\n",
                         label,
                         name,
                         total,
                         label,
                         name,
                         lines,
                         label,
                         name,
                         truncated ? 1 : 0);
}

static int append_proc_auxv_brief(struct buffer *buf, pid_t pid, const char *label) {
    char path[MAX_PATH_LEN];
    struct {
        unsigned long key;
        unsigned long value;
    } item;
    int fd;
    int count = 0;

    proc_path(path, sizeof(path), pid, "auxv");
    fd = open(path, O_RDONLY | O_CLOEXEC);
    if (fd < 0) {
        return append_format(buf,
                             "capture.%s.auxv.error=%s\n",
                             label,
                             strerror(errno));
    }
    while (read(fd, &item, sizeof(item)) == (ssize_t)sizeof(item)) {
        count++;
        if (item.key == 0 || count >= 96) {
            break;
        }
    }
    close(fd);
    return append_format(buf, "capture.%s.auxv.count=%d\n", label, count);
}

static int append_ptrace_siginfo_compact(struct buffer *buf, pid_t pid, const char *label) {
    siginfo_t info;

    memset(&info, 0, sizeof(info));
    if (ptrace(PTRACE_GETSIGINFO, pid, NULL, &info) < 0) {
        return append_format(buf,
                             "capture.%s.siginfo.error=%s\n",
                             label,
                             strerror(errno));
    }
    return append_format(buf,
                         "capture.%s.siginfo.signo=%d\n"
                         "capture.%s.siginfo.code=%d\n"
                         "capture.%s.siginfo.errno=%d\n"
                         "capture.%s.siginfo.addr=%p\n",
                         label,
                         info.si_signo,
                         label,
                         info.si_code,
                         label,
                         info.si_errno,
                         label,
                         info.si_addr);
}

static int append_ptrace_regs_brief(struct buffer *buf, pid_t pid, const char *label) {
    unsigned long long regs[96];
    struct iovec iov;

    memset(regs, 0, sizeof(regs));
    iov.iov_base = regs;
    iov.iov_len = sizeof(regs);
    if (ptrace(PTRACE_GETREGSET, pid, (void *)(long)NT_PRSTATUS, &iov) < 0) {
        return append_format(buf,
                             "capture.%s.regset.nt_prstatus.error=%s\n",
                             label,
                             strerror(errno));
    }
    return append_format(buf,
                         "capture.%s.regset.nt_prstatus.bytes=%zu\n",
                         label,
                         iov.iov_len);
}

static bool is_printable_ascii(unsigned char value) {
    return value >= 32U && value <= 126U;
}

static int append_escaped_ascii(struct buffer *buf, const unsigned char *data, size_t len) {
    for (size_t i = 0; i < len; i++) {
        unsigned char value = data[i];

        if (value == '\\') {
            if (append_literal(buf, "\\\\") < 0) return -1;
        } else if (value == '\n') {
            if (append_literal(buf, "\\n") < 0) return -1;
        } else if (value == '\r') {
            if (append_literal(buf, "\\r") < 0) return -1;
        } else if (value == '\t') {
            if (append_literal(buf, "\\t") < 0) return -1;
        } else if (is_printable_ascii(value)) {
            char text[2] = {(char)value, '\0'};

            if (append_literal(buf, text) < 0) return -1;
        } else if (append_format(buf, "\\x%02x", value) < 0) {
            return -1;
        }
    }
    return 0;
}

static bool plausible_user_ptr(unsigned long long addr) {
    return addr >= 0x1000ULL && addr < 0x0001000000000000ULL;
}

static int append_ptrace_memory_ascii_scan(struct buffer *buf,
                                           pid_t pid,
                                           const char *label,
                                           const char *source,
                                           unsigned long long addr,
                                           size_t max_bytes) {
    unsigned char bytes[512];
    size_t bytes_read = 0;
    size_t printable = 0;
    int string_count = 0;

    if (max_bytes > sizeof(bytes)) {
        max_bytes = sizeof(bytes);
    }
    if (!plausible_user_ptr(addr)) {
        return append_format(buf,
                             "capture.%s.%s.addr=0x%016llx\n"
                             "capture.%s.%s.bytes=0\n"
                             "capture.%s.%s.skipped=not-plausible-user-pointer\n",
                             label,
                             source,
                             addr,
                             label,
                             source,
                             label,
                             source);
    }
    while (bytes_read < max_bytes) {
        unsigned long word;
        size_t copy = sizeof(word);

        errno = 0;
        word = (unsigned long)ptrace(PTRACE_PEEKDATA,
                                     pid,
                                     (void *)(uintptr_t)(addr + bytes_read),
                                     NULL);
        if (word == (unsigned long)-1 && errno != 0) {
            if (bytes_read == 0) {
                return append_format(buf,
                                     "capture.%s.%s.addr=0x%016llx\n"
                                     "capture.%s.%s.bytes=0\n"
                                     "capture.%s.%s.error=%s\n",
                                     label,
                                     source,
                                     addr,
                                     label,
                                     source,
                                     label,
                                     source,
                                     strerror(errno));
            }
            break;
        }
        if (copy > max_bytes - bytes_read) {
            copy = max_bytes - bytes_read;
        }
        memcpy(bytes + bytes_read, &word, copy);
        bytes_read += copy;
    }
    for (size_t i = 0; i < bytes_read; i++) {
        if (is_printable_ascii(bytes[i])) {
            printable++;
        }
    }
    if (append_format(buf,
                      "capture.%s.%s.addr=0x%016llx\n"
                      "capture.%s.%s.bytes=%zu\n"
                      "capture.%s.%s.printable=%zu\n",
                      label,
                      source,
                      addr,
                      label,
                      source,
                      bytes_read,
                      label,
                      source,
                      printable) < 0) {
        return -1;
    }
    for (size_t i = 0; i < bytes_read && string_count < 8;) {
        size_t start = i;
        size_t len;

        while (start < bytes_read && !is_printable_ascii(bytes[start])) {
            start++;
        }
        len = start;
        while (len < bytes_read && is_printable_ascii(bytes[len])) {
            len++;
        }
        if (len > start && len - start >= 4) {
            size_t out_len = len - start;

            if (out_len > 96) {
                out_len = 96;
            }
            if (append_format(buf,
                              "capture.%s.%s.ascii.%d.offset=%zu\n"
                              "capture.%s.%s.ascii.%d.text=",
                              label,
                              source,
                              string_count,
                              start,
                              label,
                              source,
                              string_count) < 0 ||
                append_escaped_ascii(buf, bytes + start, out_len) < 0 ||
                append_literal(buf, "\n") < 0) {
                return -1;
            }
            string_count++;
        }
        i = len > start ? len : start + 1U;
    }
    return append_format(buf,
                         "capture.%s.%s.ascii.count=%d\n",
                         label,
                         source,
                         string_count);
}

static const char *skip_spaces(const char *text) {
    while (*text == ' ' || *text == '\t') {
        text++;
    }
    return text;
}

static void trim_trailing_space(char *text) {
    size_t len = strlen(text);

    while (len > 0 &&
           (text[len - 1] == ' ' ||
            text[len - 1] == '\t' ||
            text[len - 1] == '\r' ||
            text[len - 1] == '\n')) {
        text[len - 1] = '\0';
        len--;
    }
}

static int append_maps_address_row(struct buffer *buf,
                                   pid_t pid,
                                   const char *label,
                                   const char *name,
                                   unsigned long long addr) {
    char path[MAX_PATH_LEN];
    FILE *fp;
    char line[1024];
    size_t line_count = 0;

    if (!plausible_user_ptr(addr)) {
        return append_format(buf,
                             "capture.%s.maprow.%s.addr=0x%016llx\n"
                             "capture.%s.maprow.%s.found=0\n"
                             "capture.%s.maprow.%s.reason=not-plausible-user-pointer\n",
                             label,
                             name,
                             addr,
                             label,
                             name,
                             label,
                             name);
    }
    proc_path(path, sizeof(path), pid, "maps");
    fp = fopen(path, "re");
    if (fp == NULL) {
        return append_format(buf,
                             "capture.%s.maprow.%s.addr=0x%016llx\n"
                             "capture.%s.maprow.%s.found=0\n"
                             "capture.%s.maprow.%s.error=%s\n",
                             label,
                             name,
                             addr,
                             label,
                             name,
                             label,
                             name,
                             strerror(errno));
    }
    while (fgets(line, sizeof(line), fp) != NULL) {
        char original[sizeof(line)];
        char perms[8] = "";
        char path_text[512] = "";
        const char *cursor;
        const char *path_start = "";
        char *dash;
        char *endptr;
        unsigned long long start;
        unsigned long long end;
        unsigned long long file_offset;
        unsigned long long relative_offset;
        size_t perms_len = 0;

        line_count++;
        memcpy(original, line, sizeof(original));
        original[sizeof(original) - 1] = '\0';
        trim_trailing_space(original);

        errno = 0;
        start = strtoull(line, &endptr, 16);
        if (errno != 0 || endptr == line || *endptr != '-') {
            continue;
        }
        dash = endptr;
        errno = 0;
        end = strtoull(dash + 1, &endptr, 16);
        if (errno != 0 || endptr == dash + 1 || addr < start || addr >= end) {
            continue;
        }
        cursor = skip_spaces(endptr);
        while (cursor[perms_len] != '\0' &&
               cursor[perms_len] != ' ' &&
               cursor[perms_len] != '\t' &&
               perms_len + 1 < sizeof(perms)) {
            perms[perms_len] = cursor[perms_len];
            perms_len++;
        }
        perms[perms_len] = '\0';
        cursor = skip_spaces(cursor + perms_len);
        errno = 0;
        file_offset = strtoull(cursor, &endptr, 16);
        if (errno != 0 || endptr == cursor) {
            file_offset = 0;
        }
        cursor = skip_spaces(endptr);
        while (*cursor != '\0' && *cursor != ' ' && *cursor != '\t') {
            cursor++;
        }
        cursor = skip_spaces(cursor);
        while (*cursor != '\0' && *cursor != ' ' && *cursor != '\t') {
            cursor++;
        }
        cursor = skip_spaces(cursor);
        path_start = cursor;
        snprintf(path_text, sizeof(path_text), "%s", path_start);
        trim_trailing_space(path_text);
        relative_offset = file_offset + (addr - start);

        if (append_format(buf,
                          "capture.%s.maprow.%s.addr=0x%016llx\n"
                          "capture.%s.maprow.%s.found=1\n"
                          "capture.%s.maprow.%s.start=0x%016llx\n"
                          "capture.%s.maprow.%s.end=0x%016llx\n"
                          "capture.%s.maprow.%s.perms=%s\n"
                          "capture.%s.maprow.%s.file_offset=0x%llx\n"
                          "capture.%s.maprow.%s.relative_offset=0x%llx\n"
                          "capture.%s.maprow.%s.path=",
                          label,
                          name,
                          addr,
                          label,
                          name,
                          label,
                          name,
                          start,
                          label,
                          name,
                          end,
                          label,
                          name,
                          perms,
                          label,
                          name,
                          file_offset,
                          label,
                          name,
                          relative_offset,
                          label,
                          name) < 0 ||
            append_escaped_ascii(buf, (const unsigned char *)path_text, strlen(path_text)) < 0 ||
            append_format(buf, "\ncapture.%s.maprow.%s.line=", label, name) < 0 ||
            append_escaped_ascii(buf, (const unsigned char *)original, strlen(original)) < 0 ||
            append_literal(buf, "\n") < 0) {
            fclose(fp);
            return -1;
        }
        fclose(fp);
        return 0;
    }
    fclose(fp);
    return append_format(buf,
                         "capture.%s.maprow.%s.addr=0x%016llx\n"
                         "capture.%s.maprow.%s.found=0\n"
                         "capture.%s.maprow.%s.scanned_lines=%zu\n",
                         label,
                         name,
                         addr,
                         label,
                         name,
                         label,
                         name,
                         line_count);
}

static unsigned long long canonical_user_addr(unsigned long long addr) {
    return addr & 0x0000ffffffffffffULL;
}

static bool ptrace_peek_u64(pid_t pid, unsigned long long addr, unsigned long long *value) {
    unsigned long word;

    if (value == NULL || !plausible_user_ptr(addr)) {
        return false;
    }
    errno = 0;
    word = (unsigned long)ptrace(PTRACE_PEEKDATA, pid, (void *)(uintptr_t)addr, NULL);
    if (word == (unsigned long)-1 && errno != 0) {
        return false;
    }
    *value = (unsigned long long)word;
    return true;
}

static int append_frame_chain_capture(struct buffer *buf,
                                      pid_t pid,
                                      const char *label,
                                      unsigned long long fp,
                                      unsigned long long sp) {
    unsigned long long current_fp = fp;
    int frames = 0;

    if (append_format(buf,
                      "capture.%s.framechain.fp=0x%016llx\n"
                      "capture.%s.framechain.sp=0x%016llx\n"
                      "capture.%s.framechain.max=8\n",
                      label,
                      fp,
                      label,
                      sp,
                      label) < 0) {
        return -1;
    }
    if (!plausible_user_ptr(current_fp)) {
        return append_format(buf,
                             "capture.%s.framechain.count=0\n"
                             "capture.%s.framechain.stop=fp-not-plausible\n",
                             label,
                             label);
    }
    for (frames = 0; frames < 8; frames++) {
        unsigned long long next_fp = 0;
        unsigned long long return_addr_raw = 0;
        unsigned long long return_addr = 0;
        char map_name[64];

        if (!ptrace_peek_u64(pid, current_fp, &next_fp) ||
            !ptrace_peek_u64(pid, current_fp + sizeof(unsigned long long), &return_addr_raw)) {
            if (append_format(buf,
                              "capture.%s.framechain.%d.fp=0x%016llx\n"
                              "capture.%s.framechain.%d.read_error=1\n",
                              label,
                              frames,
                              current_fp,
                              label,
                              frames) < 0) {
                return -1;
            }
            break;
        }
        return_addr = canonical_user_addr(return_addr_raw);
        if (append_format(buf,
                          "capture.%s.framechain.%d.fp=0x%016llx\n"
                          "capture.%s.framechain.%d.next_fp=0x%016llx\n"
                          "capture.%s.framechain.%d.return_addr_raw=0x%016llx\n"
                          "capture.%s.framechain.%d.return_addr=0x%016llx\n",
                          label,
                          frames,
                          current_fp,
                          label,
                          frames,
                          next_fp,
                          label,
                          frames,
                          return_addr_raw,
                          label,
                          frames,
                          return_addr) < 0) {
            return -1;
        }
        snprintf(map_name, sizeof(map_name), "frame%d_ra", frames);
        if (append_maps_address_row(buf, pid, label, map_name, return_addr) < 0) {
            return -1;
        }
        if (!plausible_user_ptr(next_fp)) {
            frames++;
            if (append_format(buf,
                              "capture.%s.framechain.stop=next-fp-not-plausible\n",
                              label) < 0) {
                return -1;
            }
            break;
        }
        if (next_fp <= current_fp) {
            frames++;
            if (append_format(buf,
                              "capture.%s.framechain.stop=next-fp-not-increasing\n",
                              label) < 0) {
                return -1;
            }
            break;
        }
        if (sp != 0 && (next_fp < sp || next_fp - current_fp > 1024U * 1024U)) {
            frames++;
            if (append_format(buf,
                              "capture.%s.framechain.stop=next-fp-out-of-bounds\n",
                              label) < 0) {
                return -1;
            }
            break;
        }
        current_fp = next_fp;
    }
    return append_format(buf,
                         "capture.%s.framechain.count=%d\n",
                         label,
                         frames);
}

static int append_ptrace_regs_selected(struct buffer *buf,
                                       pid_t pid,
                                       const char *label,
                                       unsigned long long *sp_out,
                                       unsigned long long *fp_out,
                                       unsigned long long *pc_out,
                                       unsigned long long *lr_out) {
    unsigned long long regs[96];
    struct iovec iov;
    size_t words;

    if (sp_out != NULL) {
        *sp_out = 0;
    }
    if (fp_out != NULL) {
        *fp_out = 0;
    }
    if (pc_out != NULL) {
        *pc_out = 0;
    }
    if (lr_out != NULL) {
        *lr_out = 0;
    }
    memset(regs, 0, sizeof(regs));
    iov.iov_base = regs;
    iov.iov_len = sizeof(regs);
    if (ptrace(PTRACE_GETREGSET, pid, (void *)(long)NT_PRSTATUS, &iov) < 0) {
        return append_format(buf,
                             "capture.%s.regset.nt_prstatus.error=%s\n",
                             label,
                             strerror(errno));
    }
    words = iov.iov_len / sizeof(regs[0]);
    if (append_format(buf,
                      "capture.%s.regset.nt_prstatus.bytes=%zu\n"
                      "capture.%s.regset.nt_prstatus.words=%zu\n",
                      label,
                      iov.iov_len,
                      label,
                      words) < 0) {
        return -1;
    }
    for (size_t i = 0; i < words && i <= 8; i++) {
        if (append_format(buf,
                          "capture.%s.regset.nt_prstatus.x%zu=0x%016llx\n",
                          label,
                          i,
                          regs[i]) < 0) {
            return -1;
        }
    }
    if (words > 30) {
        if (lr_out != NULL) {
            *lr_out = regs[30];
        }
        if (append_format(buf,
                          "capture.%s.regset.nt_prstatus.lr=0x%016llx\n",
                          label,
                          regs[30]) < 0) {
            return -1;
        }
    }
    if (words > 29) {
        if (fp_out != NULL) {
            *fp_out = regs[29];
        }
        if (append_format(buf,
                          "capture.%s.regset.nt_prstatus.fp=0x%016llx\n",
                          label,
                          regs[29]) < 0) {
            return -1;
        }
    }
    if (words > 31) {
        if (sp_out != NULL) {
            *sp_out = regs[31];
        }
        if (append_format(buf,
                          "capture.%s.regset.nt_prstatus.sp=0x%016llx\n",
                          label,
                          regs[31]) < 0) {
            return -1;
        }
    }
    if (words > 32) {
        if (pc_out != NULL) {
            *pc_out = regs[32];
        }
        if (append_format(buf,
                          "capture.%s.regset.nt_prstatus.pc=0x%016llx\n",
                          label,
                          regs[32]) < 0) {
            return -1;
        }
    }
    if (words > 33 &&
        append_format(buf,
                      "capture.%s.regset.nt_prstatus.pstate=0x%016llx\n",
                      label,
                      regs[33]) < 0) {
        return -1;
    }
    for (size_t i = 0; i < words && i <= 8; i++) {
        char source[32];

        if (!plausible_user_ptr(regs[i])) {
            continue;
        }
        snprintf(source, sizeof(source), "reg_x%zu_scan", i);
        if (append_ptrace_memory_ascii_scan(buf, pid, label, source, regs[i], 128) < 0) {
            return -1;
        }
    }
    return 0;
}

static int append_capture_snapshot_compact(struct buffer *buf,
                                           pid_t pid,
                                           const char *label,
                                           bool include_maps) {
    unsigned long long sp = 0;
    unsigned long long fp = 0;
    unsigned long long pc = 0;
    unsigned long long lr = 0;

    if (append_format(buf, "capture.%s.pid=%ld\n", label, (long)pid) < 0 ||
        append_proc_link_compact(buf, pid, label, "exe") < 0 ||
        append_proc_link_compact(buf, pid, label, "cwd") < 0 ||
        append_proc_auxv_brief(buf, pid, label) < 0 ||
        (strcmp(label, "crash") == 0 ?
             append_ptrace_regs_selected(buf, pid, label, &sp, &fp, &pc, &lr) :
             append_ptrace_regs_brief(buf, pid, label)) < 0 ||
        append_proc_text_brief(buf, pid, label, "status", 8192) < 0) {
        return -1;
    }
    if (strcmp(label, "crash") == 0 &&
        append_ptrace_memory_ascii_scan(buf, pid, label, "stack", sp, 512) < 0) {
        return -1;
    }
    if (strcmp(label, "crash") == 0 && include_maps &&
        (append_maps_address_row(buf, pid, label, "pc", pc) < 0 ||
         append_maps_address_row(buf, pid, label, "lr", lr) < 0)) {
        return -1;
    }
    if (strcmp(label, "crash") == 0 && include_maps &&
        append_frame_chain_capture(buf, pid, label, fp, sp) < 0) {
        return -1;
    }
    if (include_maps &&
        (append_proc_text_brief(buf, pid, label, "maps", 8192) < 0 ||
         append_proc_text_brief(buf, pid, label, "mountinfo", 8192) < 0)) {
        return -1;
    }
    return 0;
}

static int wait_traced_child_for_cleanup(pid_t pid,
                                         int cleanup_signal,
                                         const char *phase,
                                         long deadline,
                                         struct buffer *stdout_buf,
                                         bool timed_out_state,
                                         bool *child_done,
                                         bool *reaped,
                                         bool *exited_before_timeout,
                                         int *child_exit_code,
                                         int *child_signal,
                                         int *cleanup_stop_continued,
                                         int *cleanup_stop_last_signal,
                                         int *cleanup_continue_errors) {
    while (!*child_done && monotonic_ms() < deadline) {
        int status = 0;
        pid_t wait_rc = waitpid(pid, &status, WNOHANG);

        if (wait_rc == pid) {
            if (WIFEXITED(status)) {
                *child_done = true;
                *reaped = true;
                *exited_before_timeout = !timed_out_state;
                *child_exit_code = WEXITSTATUS(status);
                return append_format(stdout_buf,
                                     "service_manager_start.cleanup.%s.exit=%d\n",
                                     phase,
                                     *child_exit_code);
            }
            if (WIFSIGNALED(status)) {
                *child_done = true;
                *reaped = true;
                *exited_before_timeout = !timed_out_state;
                *child_signal = WTERMSIG(status);
                return append_format(stdout_buf,
                                     "service_manager_start.cleanup.%s.signal=%d\n",
                                     phase,
                                     *child_signal);
            }
            if (WIFSTOPPED(status)) {
                int stop_signal = WSTOPSIG(status);
                unsigned int event = (unsigned int)status >> 16;

                (*cleanup_stop_continued)++;
                *cleanup_stop_last_signal = stop_signal;
                if (append_format(stdout_buf,
                                  "service_manager_start.cleanup.%s.stop.signal=%d\n"
                                  "service_manager_start.cleanup.%s.stop.event=%u\n"
                                  "service_manager_start.cleanup.%s.stop.deliver_signal=%d\n",
                                  phase,
                                  stop_signal,
                                  phase,
                                  event,
                                  phase,
                                  cleanup_signal) < 0) {
                    return -1;
                }
                if (ptrace(PTRACE_CONT, pid, NULL, (void *)(long)cleanup_signal) < 0) {
                    (*cleanup_continue_errors)++;
                    if (append_format(stdout_buf,
                                      "service_manager_start.cleanup.%s.cont.error=%s\n",
                                      phase,
                                      strerror(errno)) < 0) {
                        return -1;
                    }
                    kill(pid, cleanup_signal);
                }
                continue;
            }
            if (append_format(stdout_buf,
                              "service_manager_start.cleanup.%s.unexpected_status=0x%x\n",
                              phase,
                              status) < 0) {
                return -1;
            }
        } else if (wait_rc < 0) {
            if (errno == EINTR) {
                continue;
            }
            if (errno == ECHILD) {
                return append_format(stdout_buf,
                                     "service_manager_start.cleanup.%s.wait.echild=1\n",
                                     phase);
            }
            return append_format(stdout_buf,
                                 "service_manager_start.cleanup.%s.wait.error=%s\n",
                                 phase,
                                 strerror(errno));
        }
        usleep(50000);
    }
    return 0;
}

static int run_cnss_start_only_guarded(const struct config *cfg,
                                       const struct paths *paths,
                                       struct buffer *stdout_buf,
                                       struct buffer *stderr_buf,
                                       int *child_exit_code,
                                       int *child_signal,
                                       bool *timed_out) {
    int stdout_pipe[2] = {-1, -1};
    int stderr_pipe[2] = {-1, -1};
    bool stdout_open = true;
    bool stderr_open = true;
    bool child_done = false;
    bool observable = false;
    bool proc_status_captured = false;
    bool fd_summary_captured = false;
    bool maps_summary_captured = false;
    bool term_sent = false;
    bool kill_sent = false;
    bool reaped = false;
    bool postflight_safe = false;
    bool exited_before_timeout = false;
    long deadline;
    pid_t pid = -1;
    pid_t pgid = -1;
    int status = 0;

    *child_exit_code = -1;
    *child_signal = 0;
    *timed_out = false;

    if (append_literal(stdout_buf, "cnss_start.begin=1\n") < 0 ||
        append_literal(stdout_buf, "cnss_start.mode=guarded\n") < 0 ||
        append_literal(stdout_buf, "cnss_start.target=/vendor/bin/cnss-daemon\n") < 0 ||
        append_literal(stdout_buf, "cnss_start.argv=/vendor/bin/cnss-daemon -n -l\n") < 0 ||
        append_literal(stdout_buf, "cnss_start.cnss_diag=0\n") < 0 ||
        append_literal(stdout_buf, "cnss_start.scan_connect_linkup=0\n") < 0) {
        return -1;
    }

    if (!cfg->allow_cnss_start_only) {
        if (append_literal(stdout_buf, "cnss_start.allowed=0\n") < 0 ||
            append_literal(stdout_buf, "cnss_start.exec_attempted=0\n") < 0 ||
            append_literal(stdout_buf, "cnss_start.child_started=0\n") < 0 ||
            append_literal(stdout_buf, "cnss_start.pid=-1\n") < 0 ||
            append_literal(stdout_buf, "cnss_start.pgid=-1\n") < 0 ||
            append_literal(stdout_buf, "cnss_start.observable=0\n") < 0 ||
            append_literal(stdout_buf, "cnss_start.exited=0\n") < 0 ||
            append_literal(stdout_buf, "cnss_start.exit_code=-1\n") < 0 ||
            append_literal(stdout_buf, "cnss_start.signal=0\n") < 0 ||
            append_literal(stdout_buf, "cnss_start.timed_out=0\n") < 0 ||
            append_literal(stdout_buf, "cnss_start.term_sent=0\n") < 0 ||
            append_literal(stdout_buf, "cnss_start.kill_sent=0\n") < 0 ||
            append_literal(stdout_buf, "cnss_start.reaped=0\n") < 0 ||
            append_literal(stdout_buf, "cnss_start.proc_status_captured=0\n") < 0 ||
            append_literal(stdout_buf, "cnss_start.fd_summary_captured=0\n") < 0 ||
            append_literal(stdout_buf, "cnss_start.maps_summary_captured=0\n") < 0 ||
            append_literal(stdout_buf, "cnss_start.postflight_safe=1\n") < 0 ||
            append_literal(stdout_buf, "cnss_start.result=start-only-blocked\n") < 0 ||
            append_literal(stdout_buf, "cnss_start.reason=missing-allow-cnss-start-only\n") < 0 ||
            append_literal(stdout_buf, "cnss_start.end=1\n") < 0) {
            return -1;
        }
        return 0;
    }

    if (append_literal(stdout_buf, "cnss_start.allowed=1\n") < 0) {
        return -1;
    }
    if (pipe2(stdout_pipe, O_CLOEXEC) < 0 || pipe2(stderr_pipe, O_CLOEXEC) < 0) {
        if (append_format(stdout_buf,
                          "cnss_start.exec_attempted=0\n"
                          "cnss_start.child_started=0\n"
                          "cnss_start.pid=-1\n"
                          "cnss_start.pgid=-1\n"
                          "cnss_start.observable=0\n"
                          "cnss_start.exited=0\n"
                          "cnss_start.exit_code=-1\n"
                          "cnss_start.signal=0\n"
                          "cnss_start.timed_out=0\n"
                          "cnss_start.term_sent=0\n"
                          "cnss_start.kill_sent=0\n"
                          "cnss_start.reaped=0\n"
                          "cnss_start.proc_status_captured=0\n"
                          "cnss_start.fd_summary_captured=0\n"
                          "cnss_start.maps_summary_captured=0\n"
                          "cnss_start.postflight_safe=0\n"
                          "cnss_start.result=manual-review-required\n"
                          "cnss_start.reason=pipe-failed-%s\n"
                          "cnss_start.end=1\n",
                          strerror(errno)) < 0) {
            return -1;
        }
        goto fail;
    }
    pid = fork();
    if (pid < 0) {
        if (append_format(stdout_buf,
                          "cnss_start.exec_attempted=0\n"
                          "cnss_start.child_started=0\n"
                          "cnss_start.pid=-1\n"
                          "cnss_start.pgid=-1\n"
                          "cnss_start.observable=0\n"
                          "cnss_start.exited=0\n"
                          "cnss_start.exit_code=-1\n"
                          "cnss_start.signal=0\n"
                          "cnss_start.timed_out=0\n"
                          "cnss_start.term_sent=0\n"
                          "cnss_start.kill_sent=0\n"
                          "cnss_start.reaped=0\n"
                          "cnss_start.proc_status_captured=0\n"
                          "cnss_start.fd_summary_captured=0\n"
                          "cnss_start.maps_summary_captured=0\n"
                          "cnss_start.postflight_safe=0\n"
                          "cnss_start.result=manual-review-required\n"
                          "cnss_start.reason=fork-failed-%s\n"
                          "cnss_start.end=1\n",
                          strerror(errno)) < 0) {
            return -1;
        }
        goto fail;
    }
    if (pid == 0) {
        char *const daemon_argv[] = {
            (char *)"/vendor/bin/cnss-daemon",
            (char *)"-n",
            (char *)"-l",
            NULL,
        };

        close(stdout_pipe[0]);
        close(stderr_pipe[0]);
        dup2(stdout_pipe[1], STDOUT_FILENO);
        dup2(stderr_pipe[1], STDERR_FILENO);
        close(stdout_pipe[1]);
        close(stderr_pipe[1]);
        if (setsid() < 0) {
            perror("setsid");
            _exit(123);
        }
        if (chroot(paths->root) < 0) {
            perror("chroot");
            _exit(120);
        }
        if (chdir("/") < 0) {
            perror("chdir");
            _exit(121);
        }
        apply_child_env(cfg);
        printf("cnss_child.begin=1\n");
        if (apply_android_identity_contract("cnss_child") < 0) {
            printf("cnss_child.end=1\n");
            fflush(stdout);
            _exit(126);
        }
        printf("cnss_child.exec_target=/vendor/bin/cnss-daemon -n -l\n");
        fflush(stdout);
        execv("/vendor/bin/cnss-daemon", daemon_argv);
        printf("cnss_child.exec_error=%s\n", strerror(errno));
        printf("cnss_child.end=1\n");
        fflush(stdout);
        _exit(127);
    }

    close(stdout_pipe[1]);
    close(stderr_pipe[1]);
    stdout_pipe[1] = -1;
    stderr_pipe[1] = -1;
    set_nonblock(stdout_pipe[0]);
    set_nonblock(stderr_pipe[0]);
    pgid = wait_for_child_session_pgid(pid, 1000);
    if (append_format(stdout_buf,
                      "cnss_start.exec_attempted=1\n"
                      "cnss_start.child_started=1\n"
                      "cnss_start.pid=%ld\n"
                      "cnss_start.pgid=%ld\n",
                      (long)pid,
                      (long)pgid) < 0) {
        goto fail;
    }
    deadline = monotonic_ms() + cfg->timeout_sec * 1000L;

    while (stdout_open || stderr_open || !child_done) {
        struct pollfd fds[2];
        int nfds = 0;
        int poll_timeout = 50;
        long now = monotonic_ms();

        if (!child_done && now >= deadline) {
            *timed_out = true;
            break;
        }
        if (stdout_open) {
            fds[nfds].fd = stdout_pipe[0];
            fds[nfds].events = POLLIN | POLLHUP | POLLERR;
            nfds++;
        }
        if (stderr_open) {
            fds[nfds].fd = stderr_pipe[0];
            fds[nfds].events = POLLIN | POLLHUP | POLLERR;
            nfds++;
        }
        if (nfds > 0) {
            int rc = poll(fds, nfds, poll_timeout);

            if (rc > 0) {
                int idx = 0;

                if (stdout_open) {
                    if (fds[idx].revents != 0) {
                        drain_fd(stdout_pipe[0], stdout_buf, &stdout_open);
                    }
                    idx++;
                }
                if (stderr_open) {
                    if (fds[idx].revents != 0) {
                        drain_fd(stderr_pipe[0], stderr_buf, &stderr_open);
                    }
                }
            }
        } else {
            usleep(50000);
        }
        if (!child_done) {
            pid_t wait_rc = waitpid(pid, &status, WNOHANG);

            if (wait_rc == pid) {
                child_done = true;
                reaped = true;
                exited_before_timeout = !*timed_out;
                if (WIFEXITED(status)) {
                    *child_exit_code = WEXITSTATUS(status);
                } else if (WIFSIGNALED(status)) {
                    *child_signal = WTERMSIG(status);
                }
            } else if (wait_rc < 0 && errno != EINTR && errno != ECHILD) {
                append_format(stdout_buf, "cnss_start.wait.error=%s\n", strerror(errno));
                break;
            }
        }
    }

    if (!child_done && kill(pid, 0) == 0) {
        observable = true;
        append_proc_file_capture(stdout_buf, pid, "status", 8192, &proc_status_captured);
        append_proc_fd_summary(stdout_buf, pid, &fd_summary_captured);
        append_proc_file_capture(stdout_buf, pid, "maps", 65536, &maps_summary_captured);
    }
    if (!child_done) {
        if (kill(-pgid, SIGTERM) == 0 || errno == ESRCH) {
            term_sent = true;
        }
        deadline = monotonic_ms() + 1000L;
        while (!child_done && monotonic_ms() < deadline) {
            struct pollfd fds[2];
            int nfds = 0;

            if (stdout_open) {
                fds[nfds].fd = stdout_pipe[0];
                fds[nfds].events = POLLIN | POLLHUP | POLLERR;
                nfds++;
            }
            if (stderr_open) {
                fds[nfds].fd = stderr_pipe[0];
                fds[nfds].events = POLLIN | POLLHUP | POLLERR;
                nfds++;
            }
            if (nfds > 0 && poll(fds, nfds, 50) > 0) {
                int idx = 0;

                if (stdout_open) {
                    if (fds[idx].revents != 0) {
                        drain_fd(stdout_pipe[0], stdout_buf, &stdout_open);
                    }
                    idx++;
                }
                if (stderr_open && fds[idx].revents != 0) {
                    drain_fd(stderr_pipe[0], stderr_buf, &stderr_open);
                }
            } else {
                usleep(50000);
            }
            if (waitpid(pid, &status, WNOHANG) == pid) {
                child_done = true;
                reaped = true;
                if (WIFEXITED(status)) {
                    *child_exit_code = WEXITSTATUS(status);
                } else if (WIFSIGNALED(status)) {
                    *child_signal = WTERMSIG(status);
                }
            }
        }
    }
    if (!child_done) {
        if (kill(-pgid, SIGKILL) == 0 || errno == ESRCH) {
            kill_sent = true;
        }
        deadline = monotonic_ms() + 1000L;
        while (!child_done && monotonic_ms() < deadline) {
            if (waitpid(pid, &status, WNOHANG) == pid) {
                child_done = true;
                reaped = true;
                if (WIFEXITED(status)) {
                    *child_exit_code = WEXITSTATUS(status);
                } else if (WIFSIGNALED(status)) {
                    *child_signal = WTERMSIG(status);
                }
                break;
            }
            usleep(50000);
        }
    }
    if (stdout_open) {
        drain_fd(stdout_pipe[0], stdout_buf, &stdout_open);
    }
    if (stderr_open) {
        drain_fd(stderr_pipe[0], stderr_buf, &stderr_open);
    }
    postflight_safe = reaped && (kill(-pgid, 0) < 0 && errno == ESRCH);

    if (append_format(stdout_buf,
                      "cnss_start.observable=%d\n"
                      "cnss_start.exited=%d\n"
                      "cnss_start.exit_code=%d\n"
                      "cnss_start.signal=%d\n"
                      "cnss_start.timed_out=%d\n"
                      "cnss_start.term_sent=%d\n"
                      "cnss_start.kill_sent=%d\n"
                      "cnss_start.reaped=%d\n"
                      "cnss_start.proc_status_captured=%d\n"
                      "cnss_start.fd_summary_captured=%d\n"
                      "cnss_start.maps_summary_captured=%d\n"
                      "cnss_start.postflight_safe=%d\n",
                      observable ? 1 : 0,
                      child_done ? 1 : 0,
                      *child_exit_code,
                      *child_signal,
                      *timed_out ? 1 : 0,
                      term_sent ? 1 : 0,
                      kill_sent ? 1 : 0,
                      reaped ? 1 : 0,
                      proc_status_captured ? 1 : 0,
                      fd_summary_captured ? 1 : 0,
                      maps_summary_captured ? 1 : 0,
                      postflight_safe ? 1 : 0) < 0) {
        goto fail;
    }
    if (!postflight_safe) {
        append_literal(stdout_buf,
                       "cnss_start.result=start-only-reboot-required\n"
                       "cnss_start.reason=process-not-proven-stopped\n");
    } else if (*timed_out && observable) {
        append_literal(stdout_buf,
                       "cnss_start.result=start-only-pass\n"
                       "cnss_start.reason=observed-until-timeout-clean-stop\n");
    } else if (exited_before_timeout || *child_exit_code >= 0 || *child_signal != 0) {
        append_literal(stdout_buf,
                       "cnss_start.result=start-only-runtime-gap\n"
                       "cnss_start.reason=child-exited-before-observe-window\n");
    } else {
        append_literal(stdout_buf,
                       "cnss_start.result=manual-review-required\n"
                       "cnss_start.reason=unclassified-lifecycle-state\n");
    }
    append_literal(stdout_buf, "cnss_start.end=1\n");
    if (stdout_pipe[0] >= 0) close(stdout_pipe[0]);
    if (stderr_pipe[0] >= 0) close(stderr_pipe[0]);
    return 0;

fail:
    if (pid > 0) {
        kill(-pid, SIGKILL);
        kill(pid, SIGKILL);
        waitpid(pid, NULL, WNOHANG);
    }
    if (stdout_pipe[0] >= 0) close(stdout_pipe[0]);
    if (stdout_pipe[1] >= 0) close(stdout_pipe[1]);
    if (stderr_pipe[0] >= 0) close(stderr_pipe[0]);
    if (stderr_pipe[1] >= 0) close(stderr_pipe[1]);
    return -1;
}

static int run_service_manager_start_only_guarded_ptrace(const struct config *cfg,
                                                         const struct paths *paths,
                                                         struct buffer *stdout_buf,
                                                         struct buffer *stderr_buf,
                                                         int *child_exit_code,
                                                         int *child_signal,
                                                         bool *timed_out) {
    int stdout_pipe[2] = {-1, -1};
    int stderr_pipe[2] = {-1, -1};
    bool stdout_open = true;
    bool stderr_open = true;
    bool child_done = false;
    bool observable = false;
    bool proc_status_captured = false;
    bool fd_summary_captured = false;
    bool maps_summary_captured = false;
    bool term_sent = false;
    bool kill_sent = false;
    bool reaped = false;
    bool postflight_safe = false;
    bool exited_before_timeout = false;
    bool exec_captured = false;
    bool crash_captured = false;
    bool residual_kill_sent = false;
    bool residual_cleared = false;
    int cleanup_stop_continued = 0;
    int cleanup_stop_last_signal = 0;
    int cleanup_continue_errors = 0;
    int residual_before_count = -1;
    int residual_after_count = -1;
    long deadline;
    pid_t pid = -1;
    pid_t pgid = -1;
    int status = 0;

    *child_exit_code = -1;
    *child_signal = 0;
    *timed_out = false;

    if (append_literal(stdout_buf, "service_manager_start.begin=1\n") < 0 ||
        append_literal(stdout_buf, "service_manager_start.mode=guarded\n") < 0 ||
        append_literal(stdout_buf, "service_manager_start.capture_mode=ptrace-lite\n") < 0 ||
        append_literal(stdout_buf, "service_manager_start.capture_detail=compact\n") < 0 ||
        append_format(stdout_buf, "service_manager_start.target=%s\n", cfg->target) < 0 ||
        append_format(stdout_buf, "service_manager_start.argv=%s\n", cfg->target) < 0 ||
        append_literal(stdout_buf, "service_manager_start.wifi_hal=0\n") < 0 ||
        append_literal(stdout_buf, "service_manager_start.scan_connect_linkup=0\n") < 0 ||
        append_literal(stdout_buf, "service_manager_start.allowed=1\n") < 0) {
        return -1;
    }
    printf("capture.mode=ptrace-lite\n");
    printf("capture.detail=compact\n");
    printf("capture.scope=service-manager-start-only\n");

    if (pipe2(stdout_pipe, O_CLOEXEC) < 0 || pipe2(stderr_pipe, O_CLOEXEC) < 0) {
        if (append_format(stdout_buf,
                          "service_manager_start.exec_attempted=0\n"
                          "service_manager_start.child_started=0\n"
                          "service_manager_start.pid=-1\n"
                          "service_manager_start.pgid=-1\n"
                          "service_manager_start.observable=0\n"
                          "service_manager_start.exited=0\n"
                          "service_manager_start.exit_code=-1\n"
                          "service_manager_start.signal=0\n"
                          "service_manager_start.timed_out=0\n"
                          "service_manager_start.term_sent=0\n"
                          "service_manager_start.kill_sent=0\n"
                          "service_manager_start.reaped=0\n"
                          "service_manager_start.proc_status_captured=0\n"
                          "service_manager_start.fd_summary_captured=0\n"
                          "service_manager_start.maps_summary_captured=0\n"
                          "service_manager_start.capture_exec=0\n"
                          "service_manager_start.capture_crash=0\n"
                          "service_manager_start.postflight_safe=0\n"
                          "service_manager_start.result=manual-review-required\n"
                          "service_manager_start.reason=pipe-failed-%s\n"
                          "service_manager_start.end=1\n",
                          strerror(errno)) < 0) {
            return -1;
        }
        goto fail;
    }
    pid = fork();
    if (pid < 0) {
        if (append_format(stdout_buf,
                          "service_manager_start.exec_attempted=0\n"
                          "service_manager_start.child_started=0\n"
                          "service_manager_start.pid=-1\n"
                          "service_manager_start.pgid=-1\n"
                          "service_manager_start.observable=0\n"
                          "service_manager_start.exited=0\n"
                          "service_manager_start.exit_code=-1\n"
                          "service_manager_start.signal=0\n"
                          "service_manager_start.timed_out=0\n"
                          "service_manager_start.term_sent=0\n"
                          "service_manager_start.kill_sent=0\n"
                          "service_manager_start.reaped=0\n"
                          "service_manager_start.proc_status_captured=0\n"
                          "service_manager_start.fd_summary_captured=0\n"
                          "service_manager_start.maps_summary_captured=0\n"
                          "service_manager_start.capture_exec=0\n"
                          "service_manager_start.capture_crash=0\n"
                          "service_manager_start.postflight_safe=0\n"
                          "service_manager_start.result=manual-review-required\n"
                          "service_manager_start.reason=fork-failed-%s\n"
                          "service_manager_start.end=1\n",
                          strerror(errno)) < 0) {
            return -1;
        }
        goto fail;
    }
    if (pid == 0) {
        char *const manager_argv[] = {
            (char *)cfg->target,
            NULL,
        };

        close(stdout_pipe[0]);
        close(stderr_pipe[0]);
        dup2(stdout_pipe[1], STDOUT_FILENO);
        dup2(stderr_pipe[1], STDERR_FILENO);
        close(stdout_pipe[1]);
        close(stderr_pipe[1]);
        if (setsid() < 0) {
            perror("setsid");
            _exit(123);
        }
        if (chroot(paths->root) < 0) {
            perror("chroot");
            _exit(120);
        }
        if (chdir("/") < 0) {
            perror("chdir");
            _exit(121);
        }
        apply_child_env(cfg);
        printf("service_manager_child.begin=1\n");
        if (apply_service_manager_identity_contract("service_manager_child") < 0) {
            printf("service_manager_child.end=1\n");
            fflush(stdout);
            _exit(126);
        }
        if (apply_android_exec_selinux_context_if_requested(cfg, "service_manager_child", cfg->target) < 0) {
            printf("service_manager_child.end=1\n");
            fflush(stdout);
            _exit(126);
        }
        printf("service_manager_child.exec_target=%s\n", cfg->target);
        fflush(stdout);
        if (ptrace(PTRACE_TRACEME, 0, NULL, NULL) < 0) {
            printf("service_manager_child.ptrace_traceme_error=%s\n", strerror(errno));
            printf("service_manager_child.end=1\n");
            fflush(stdout);
            _exit(122);
        }
        raise(SIGSTOP);
        execv(cfg->target, manager_argv);
        printf("service_manager_child.exec_error=%s\n", strerror(errno));
        printf("service_manager_child.end=1\n");
        fflush(stdout);
        _exit(127);
    }

    close(stdout_pipe[1]);
    close(stderr_pipe[1]);
    stdout_pipe[1] = -1;
    stderr_pipe[1] = -1;
    set_nonblock(stdout_pipe[0]);
    set_nonblock(stderr_pipe[0]);
    pgid = wait_for_child_session_pgid(pid, 1000);
    if (append_format(stdout_buf,
                      "service_manager_start.exec_attempted=1\n"
                      "service_manager_start.child_started=1\n"
                      "service_manager_start.pid=%ld\n"
                      "service_manager_start.pgid=%ld\n",
                      (long)pid,
                      (long)pgid) < 0) {
        goto fail;
    }

    if (waitpid(pid, &status, 0) != pid) {
        printf("capture.initial_wait.error=%s\n", strerror(errno));
        goto fail;
    }
    if (!WIFSTOPPED(status)) {
        printf("capture.initial_stop.unexpected_status=0x%x\n", status);
        if (WIFEXITED(status)) {
            child_done = true;
            reaped = true;
            exited_before_timeout = true;
            *child_exit_code = WEXITSTATUS(status);
        } else if (WIFSIGNALED(status)) {
            child_done = true;
            reaped = true;
            exited_before_timeout = true;
            *child_signal = WTERMSIG(status);
        }
    } else {
        printf("capture.initial_stop.signal=%d\n", WSTOPSIG(status));
        if (ptrace(PTRACE_SETOPTIONS,
                   pid,
                   NULL,
                   (void *)(long)(PTRACE_O_TRACEEXEC | PTRACE_O_EXITKILL)) < 0) {
            printf("capture.setoptions.error=%s\n", strerror(errno));
        }
        if (ptrace(PTRACE_CONT, pid, NULL, NULL) < 0) {
            printf("capture.initial_cont.error=%s\n", strerror(errno));
            goto fail;
        }
    }
    deadline = monotonic_ms() + cfg->timeout_sec * 1000L;

    while (stdout_open || stderr_open || !child_done) {
        struct pollfd fds[2];
        int nfds = 0;
        int poll_timeout = 50;
        long now = monotonic_ms();

        if (!child_done && now >= deadline) {
            *timed_out = true;
            printf("capture.timeout.kill=1\n");
            break;
        }
        if (stdout_open) {
            fds[nfds].fd = stdout_pipe[0];
            fds[nfds].events = POLLIN | POLLHUP | POLLERR;
            nfds++;
        }
        if (stderr_open) {
            fds[nfds].fd = stderr_pipe[0];
            fds[nfds].events = POLLIN | POLLHUP | POLLERR;
            nfds++;
        }
        if (nfds > 0) {
            int rc = poll(fds, nfds, poll_timeout);

            if (rc > 0) {
                int idx = 0;

                if (stdout_open) {
                    if (fds[idx].revents != 0) {
                        drain_fd(stdout_pipe[0], stdout_buf, &stdout_open);
                    }
                    idx++;
                }
                if (stderr_open) {
                    if (fds[idx].revents != 0) {
                        drain_fd(stderr_pipe[0], stderr_buf, &stderr_open);
                    }
                }
            }
        } else {
            usleep(50000);
        }
        if (!child_done) {
            pid_t wait_rc = waitpid(pid, &status, WNOHANG);

            if (wait_rc == pid) {
                if (WIFEXITED(status)) {
                    child_done = true;
                    reaped = true;
                    exited_before_timeout = !*timed_out;
                    *child_exit_code = WEXITSTATUS(status);
                    printf("capture.child.exit=%d\n", *child_exit_code);
                } else if (WIFSIGNALED(status)) {
                    child_done = true;
                    reaped = true;
                    exited_before_timeout = !*timed_out;
                    *child_signal = WTERMSIG(status);
                    printf("capture.child.signal=%d\n", *child_signal);
                } else if (WIFSTOPPED(status)) {
                    int sig = WSTOPSIG(status);
                    unsigned int event = (unsigned int)status >> 16;
                    int deliver_sig = 0;

                    printf("capture.stop.signal=%d\n", sig);
                    printf("capture.stop.event=%u\n", event);
                    if (sig == SIGTRAP && !exec_captured) {
                        exec_captured = true;
                        printf("capture.exec_stop=1\n");
                        if (append_capture_snapshot_compact(stdout_buf, pid, "exec", true) < 0) {
                            goto fail;
                        }
                    } else if (sig == SIGSEGV || sig == SIGBUS || sig == SIGILL || sig == SIGABRT) {
                        crash_captured = true;
                        printf("capture.crash_stop=1\n");
                        if (append_ptrace_siginfo_compact(stdout_buf, pid, "crash") < 0 ||
                            append_capture_snapshot_compact(stdout_buf, pid, "crash", true) < 0) {
                            goto fail;
                        }
                        deliver_sig = sig;
                    } else if (sig != SIGTRAP) {
                        deliver_sig = sig;
                    }
                    if (ptrace(PTRACE_CONT, pid, NULL, (void *)(long)deliver_sig) < 0) {
                        printf("capture.cont.error=%s\n", strerror(errno));
                        kill(-pgid, SIGKILL);
                        kill(pid, SIGKILL);
                    }
                }
            } else if (wait_rc < 0 && errno != EINTR && errno != ECHILD) {
                append_format(stdout_buf, "service_manager_start.wait.error=%s\n", strerror(errno));
                break;
            }
        }
    }

    if (!child_done && kill(pid, 0) == 0) {
        observable = true;
        append_proc_file_capture(stdout_buf, pid, "status", 8192, &proc_status_captured);
        append_proc_fd_summary(stdout_buf, pid, &fd_summary_captured);
        append_proc_file_capture(stdout_buf, pid, "maps", 65536, &maps_summary_captured);
    }
    if (!child_done) {
        if (kill(-pgid, SIGTERM) == 0 || errno == ESRCH) {
            term_sent = true;
        }
        deadline = monotonic_ms() + 1000L;
        if (wait_traced_child_for_cleanup(pid,
                                          SIGTERM,
                                          "term",
                                          deadline,
                                          stdout_buf,
                                          *timed_out,
                                          &child_done,
                                          &reaped,
                                          &exited_before_timeout,
                                          child_exit_code,
                                          child_signal,
                                          &cleanup_stop_continued,
                                          &cleanup_stop_last_signal,
                                          &cleanup_continue_errors) < 0) {
            goto fail;
        }
    }
    if (!child_done) {
        if (kill(-pgid, SIGKILL) == 0 || errno == ESRCH) {
            kill_sent = true;
        }
        deadline = monotonic_ms() + 1000L;
        if (wait_traced_child_for_cleanup(pid,
                                          SIGKILL,
                                          "kill",
                                          deadline,
                                          stdout_buf,
                                          *timed_out,
                                          &child_done,
                                          &reaped,
                                          &exited_before_timeout,
                                          child_exit_code,
                                          child_signal,
                                          &cleanup_stop_continued,
                                          &cleanup_stop_last_signal,
                                          &cleanup_continue_errors) < 0) {
            goto fail;
        }
    }
    if (stdout_open) {
        drain_fd(stdout_pipe[0], stdout_buf, &stdout_open);
    }
    if (stderr_open) {
        drain_fd(stderr_pipe[0], stderr_buf, &stderr_open);
    }
    if (reaped && pgid > 1) {
        errno = 0;
        postflight_safe = kill(-pgid, 0) < 0 && errno == ESRCH;
        if (!postflight_safe) {
            if (append_pgid_scan_summary(stdout_buf,
                                         "service_manager_start",
                                         "before_final_kill",
                                         pgid,
                                         &residual_before_count) < 0) {
                goto fail;
            }
            if (kill(-pgid, SIGKILL) == 0 || errno == ESRCH) {
                residual_kill_sent = true;
                kill_sent = true;
            }
            deadline = monotonic_ms() + 1000L;
            while (monotonic_ms() < deadline) {
                errno = 0;
                if (kill(-pgid, 0) < 0 && errno == ESRCH) {
                    residual_cleared = true;
                    break;
                }
                usleep(50000);
            }
            if (append_pgid_scan_summary(stdout_buf,
                                         "service_manager_start",
                                         "after_final_kill",
                                         pgid,
                                         &residual_after_count) < 0) {
                goto fail;
            }
        }
        errno = 0;
        postflight_safe = kill(-pgid, 0) < 0 && errno == ESRCH;
        if (postflight_safe) {
            residual_cleared = true;
        }
    } else {
        postflight_safe = false;
    }

    if (append_format(stdout_buf,
                      "service_manager_start.observable=%d\n"
                      "service_manager_start.exited=%d\n"
                      "service_manager_start.exit_code=%d\n"
                      "service_manager_start.signal=%d\n"
                      "service_manager_start.timed_out=%d\n"
                      "service_manager_start.term_sent=%d\n"
                      "service_manager_start.kill_sent=%d\n"
                      "service_manager_start.reaped=%d\n"
                      "service_manager_start.proc_status_captured=%d\n"
                      "service_manager_start.fd_summary_captured=%d\n"
                      "service_manager_start.maps_summary_captured=%d\n"
                      "service_manager_start.capture_exec=%d\n"
                      "service_manager_start.capture_crash=%d\n"
                      "service_manager_start.cleanup_stop_continued=%d\n"
                      "service_manager_start.cleanup_stop_last_signal=%d\n"
                      "service_manager_start.cleanup_continue_errors=%d\n"
                      "service_manager_start.residual_kill_sent=%d\n"
                      "service_manager_start.residual_cleared=%d\n"
                      "service_manager_start.residual_before_count=%d\n"
                      "service_manager_start.residual_after_count=%d\n"
                      "service_manager_start.postflight_safe=%d\n",
                      observable ? 1 : 0,
                      child_done ? 1 : 0,
                      *child_exit_code,
                      *child_signal,
                      *timed_out ? 1 : 0,
                      term_sent ? 1 : 0,
                      kill_sent ? 1 : 0,
                      reaped ? 1 : 0,
                      proc_status_captured ? 1 : 0,
                      fd_summary_captured ? 1 : 0,
                      maps_summary_captured ? 1 : 0,
                      exec_captured ? 1 : 0,
                      crash_captured ? 1 : 0,
                      cleanup_stop_continued,
                      cleanup_stop_last_signal,
                      cleanup_continue_errors,
                      residual_kill_sent ? 1 : 0,
                      residual_cleared ? 1 : 0,
                      residual_before_count,
                      residual_after_count,
                      postflight_safe ? 1 : 0) < 0) {
        goto fail;
    }
    if (!postflight_safe) {
        append_literal(stdout_buf,
                       "service_manager_start.result=start-only-reboot-required\n"
                       "service_manager_start.reason=process-not-proven-stopped\n");
    } else if (*timed_out && observable) {
        append_literal(stdout_buf,
                       "service_manager_start.result=start-only-pass\n"
                       "service_manager_start.reason=observed-until-timeout-clean-stop\n");
    } else if (exited_before_timeout || *child_exit_code >= 0 || *child_signal != 0) {
        append_literal(stdout_buf,
                       "service_manager_start.result=start-only-runtime-gap\n"
                       "service_manager_start.reason=child-exited-before-observe-window\n");
    } else {
        append_literal(stdout_buf,
                       "service_manager_start.result=manual-review-required\n"
                       "service_manager_start.reason=unclassified-lifecycle-state\n");
    }
    append_literal(stdout_buf, "service_manager_start.end=1\n");
    printf("capture.exec_captured=%d\n", exec_captured ? 1 : 0);
    printf("capture.crash_captured=%d\n", crash_captured ? 1 : 0);
    if (stdout_pipe[0] >= 0) close(stdout_pipe[0]);
    if (stderr_pipe[0] >= 0) close(stderr_pipe[0]);
    return 0;

fail:
    if (pid > 0) {
        if (pgid > 1) {
            kill(-pgid, SIGKILL);
        }
        kill(pid, SIGKILL);
        waitpid(pid, NULL, WNOHANG);
    }
    if (stdout_pipe[0] >= 0) close(stdout_pipe[0]);
    if (stdout_pipe[1] >= 0) close(stdout_pipe[1]);
    if (stderr_pipe[0] >= 0) close(stderr_pipe[0]);
    if (stderr_pipe[1] >= 0) close(stderr_pipe[1]);
    return -1;
}

static int run_service_manager_start_only_guarded(const struct config *cfg,
                                                  const struct paths *paths,
                                                  struct buffer *stdout_buf,
                                                  struct buffer *stderr_buf,
                                                  int *child_exit_code,
                                                  int *child_signal,
                                                  bool *timed_out) {
    if (streq(cfg->capture_mode, "ptrace-lite")) {
        return run_service_manager_start_only_guarded_ptrace(cfg,
                                                            paths,
                                                            stdout_buf,
                                                            stderr_buf,
                                                            child_exit_code,
                                                            child_signal,
                                                            timed_out);
    }

    int stdout_pipe[2] = {-1, -1};
    int stderr_pipe[2] = {-1, -1};
    bool stdout_open = true;
    bool stderr_open = true;
    bool child_done = false;
    bool observable = false;
    bool proc_status_captured = false;
    bool fd_summary_captured = false;
    bool maps_summary_captured = false;
    bool term_sent = false;
    bool kill_sent = false;
    bool reaped = false;
    bool postflight_safe = false;
    bool exited_before_timeout = false;
    long deadline;
    pid_t pid = -1;
    pid_t pgid = -1;
    int status = 0;

    *child_exit_code = -1;
    *child_signal = 0;
    *timed_out = false;

    if (append_literal(stdout_buf, "service_manager_start.begin=1\n") < 0 ||
        append_literal(stdout_buf, "service_manager_start.mode=guarded\n") < 0 ||
        append_format(stdout_buf, "service_manager_start.target=%s\n", cfg->target) < 0 ||
        append_format(stdout_buf, "service_manager_start.argv=%s\n", cfg->target) < 0 ||
        append_literal(stdout_buf, "service_manager_start.wifi_hal=0\n") < 0 ||
        append_literal(stdout_buf, "service_manager_start.scan_connect_linkup=0\n") < 0) {
        return -1;
    }

    if (!cfg->allow_service_manager_start_only) {
        if (append_literal(stdout_buf, "service_manager_start.allowed=0\n") < 0 ||
            append_literal(stdout_buf, "service_manager_start.exec_attempted=0\n") < 0 ||
            append_literal(stdout_buf, "service_manager_start.child_started=0\n") < 0 ||
            append_literal(stdout_buf, "service_manager_start.pid=-1\n") < 0 ||
            append_literal(stdout_buf, "service_manager_start.pgid=-1\n") < 0 ||
            append_literal(stdout_buf, "service_manager_start.observable=0\n") < 0 ||
            append_literal(stdout_buf, "service_manager_start.exited=0\n") < 0 ||
            append_literal(stdout_buf, "service_manager_start.exit_code=-1\n") < 0 ||
            append_literal(stdout_buf, "service_manager_start.signal=0\n") < 0 ||
            append_literal(stdout_buf, "service_manager_start.timed_out=0\n") < 0 ||
            append_literal(stdout_buf, "service_manager_start.term_sent=0\n") < 0 ||
            append_literal(stdout_buf, "service_manager_start.kill_sent=0\n") < 0 ||
            append_literal(stdout_buf, "service_manager_start.reaped=0\n") < 0 ||
            append_literal(stdout_buf, "service_manager_start.proc_status_captured=0\n") < 0 ||
            append_literal(stdout_buf, "service_manager_start.fd_summary_captured=0\n") < 0 ||
            append_literal(stdout_buf, "service_manager_start.maps_summary_captured=0\n") < 0 ||
            append_literal(stdout_buf, "service_manager_start.postflight_safe=1\n") < 0 ||
            append_literal(stdout_buf, "service_manager_start.result=start-only-blocked\n") < 0 ||
            append_literal(stdout_buf, "service_manager_start.reason=missing-allow-service-manager-start-only\n") < 0 ||
            append_literal(stdout_buf, "service_manager_start.end=1\n") < 0) {
            return -1;
        }
        return 0;
    }

    if (append_literal(stdout_buf, "service_manager_start.allowed=1\n") < 0) {
        return -1;
    }
    if (pipe2(stdout_pipe, O_CLOEXEC) < 0 || pipe2(stderr_pipe, O_CLOEXEC) < 0) {
        if (append_format(stdout_buf,
                          "service_manager_start.exec_attempted=0\n"
                          "service_manager_start.child_started=0\n"
                          "service_manager_start.pid=-1\n"
                          "service_manager_start.pgid=-1\n"
                          "service_manager_start.observable=0\n"
                          "service_manager_start.exited=0\n"
                          "service_manager_start.exit_code=-1\n"
                          "service_manager_start.signal=0\n"
                          "service_manager_start.timed_out=0\n"
                          "service_manager_start.term_sent=0\n"
                          "service_manager_start.kill_sent=0\n"
                          "service_manager_start.reaped=0\n"
                          "service_manager_start.proc_status_captured=0\n"
                          "service_manager_start.fd_summary_captured=0\n"
                          "service_manager_start.maps_summary_captured=0\n"
                          "service_manager_start.postflight_safe=0\n"
                          "service_manager_start.result=manual-review-required\n"
                          "service_manager_start.reason=pipe-failed-%s\n"
                          "service_manager_start.end=1\n",
                          strerror(errno)) < 0) {
            return -1;
        }
        goto fail;
    }
    pid = fork();
    if (pid < 0) {
        if (append_format(stdout_buf,
                          "service_manager_start.exec_attempted=0\n"
                          "service_manager_start.child_started=0\n"
                          "service_manager_start.pid=-1\n"
                          "service_manager_start.pgid=-1\n"
                          "service_manager_start.observable=0\n"
                          "service_manager_start.exited=0\n"
                          "service_manager_start.exit_code=-1\n"
                          "service_manager_start.signal=0\n"
                          "service_manager_start.timed_out=0\n"
                          "service_manager_start.term_sent=0\n"
                          "service_manager_start.kill_sent=0\n"
                          "service_manager_start.reaped=0\n"
                          "service_manager_start.proc_status_captured=0\n"
                          "service_manager_start.fd_summary_captured=0\n"
                          "service_manager_start.maps_summary_captured=0\n"
                          "service_manager_start.postflight_safe=0\n"
                          "service_manager_start.result=manual-review-required\n"
                          "service_manager_start.reason=fork-failed-%s\n"
                          "service_manager_start.end=1\n",
                          strerror(errno)) < 0) {
            return -1;
        }
        goto fail;
    }
    if (pid == 0) {
        char *const manager_argv[] = {
            (char *)cfg->target,
            NULL,
        };

        close(stdout_pipe[0]);
        close(stderr_pipe[0]);
        dup2(stdout_pipe[1], STDOUT_FILENO);
        dup2(stderr_pipe[1], STDERR_FILENO);
        close(stdout_pipe[1]);
        close(stderr_pipe[1]);
        if (setsid() < 0) {
            perror("setsid");
            _exit(123);
        }
        if (chroot(paths->root) < 0) {
            perror("chroot");
            _exit(120);
        }
        if (chdir("/") < 0) {
            perror("chdir");
            _exit(121);
        }
        apply_child_env(cfg);
        printf("service_manager_child.begin=1\n");
        if (apply_service_manager_identity_contract("service_manager_child") < 0) {
            printf("service_manager_child.end=1\n");
            fflush(stdout);
            _exit(126);
        }
        if (apply_android_exec_selinux_context_if_requested(cfg, "service_manager_child", cfg->target) < 0) {
            printf("service_manager_child.end=1\n");
            fflush(stdout);
            _exit(126);
        }
        printf("service_manager_child.exec_target=%s\n", cfg->target);
        fflush(stdout);
        execv(cfg->target, manager_argv);
        printf("service_manager_child.exec_error=%s\n", strerror(errno));
        printf("service_manager_child.end=1\n");
        fflush(stdout);
        _exit(127);
    }

    close(stdout_pipe[1]);
    close(stderr_pipe[1]);
    stdout_pipe[1] = -1;
    stderr_pipe[1] = -1;
    set_nonblock(stdout_pipe[0]);
    set_nonblock(stderr_pipe[0]);
    pgid = wait_for_child_session_pgid(pid, 1000);
    if (append_format(stdout_buf,
                      "service_manager_start.exec_attempted=1\n"
                      "service_manager_start.child_started=1\n"
                      "service_manager_start.pid=%ld\n"
                      "service_manager_start.pgid=%ld\n",
                      (long)pid,
                      (long)pgid) < 0) {
        goto fail;
    }
    deadline = monotonic_ms() + cfg->timeout_sec * 1000L;

    while (stdout_open || stderr_open || !child_done) {
        struct pollfd fds[2];
        int nfds = 0;
        int poll_timeout = 50;
        long now = monotonic_ms();

        if (!child_done && now >= deadline) {
            *timed_out = true;
            break;
        }
        if (stdout_open) {
            fds[nfds].fd = stdout_pipe[0];
            fds[nfds].events = POLLIN | POLLHUP | POLLERR;
            nfds++;
        }
        if (stderr_open) {
            fds[nfds].fd = stderr_pipe[0];
            fds[nfds].events = POLLIN | POLLHUP | POLLERR;
            nfds++;
        }
        if (nfds > 0) {
            int rc = poll(fds, nfds, poll_timeout);

            if (rc > 0) {
                int idx = 0;

                if (stdout_open) {
                    if (fds[idx].revents != 0) {
                        drain_fd(stdout_pipe[0], stdout_buf, &stdout_open);
                    }
                    idx++;
                }
                if (stderr_open) {
                    if (fds[idx].revents != 0) {
                        drain_fd(stderr_pipe[0], stderr_buf, &stderr_open);
                    }
                }
            }
        } else {
            usleep(50000);
        }
        if (!child_done) {
            pid_t wait_rc = waitpid(pid, &status, WNOHANG);

            if (wait_rc == pid) {
                child_done = true;
                reaped = true;
                exited_before_timeout = !*timed_out;
                if (WIFEXITED(status)) {
                    *child_exit_code = WEXITSTATUS(status);
                } else if (WIFSIGNALED(status)) {
                    *child_signal = WTERMSIG(status);
                }
            } else if (wait_rc < 0 && errno != EINTR && errno != ECHILD) {
                append_format(stdout_buf, "service_manager_start.wait.error=%s\n", strerror(errno));
                break;
            }
        }
    }

    if (!child_done && kill(pid, 0) == 0) {
        observable = true;
        append_proc_file_capture(stdout_buf, pid, "status", 8192, &proc_status_captured);
        append_proc_fd_summary(stdout_buf, pid, &fd_summary_captured);
        append_proc_file_capture(stdout_buf, pid, "maps", 65536, &maps_summary_captured);
    }
    if (!child_done) {
        if (kill(-pgid, SIGTERM) == 0 || errno == ESRCH) {
            term_sent = true;
        }
        deadline = monotonic_ms() + 1000L;
        while (!child_done && monotonic_ms() < deadline) {
            if (waitpid(pid, &status, WNOHANG) == pid) {
                child_done = true;
                reaped = true;
                if (WIFEXITED(status)) {
                    *child_exit_code = WEXITSTATUS(status);
                } else if (WIFSIGNALED(status)) {
                    *child_signal = WTERMSIG(status);
                }
                break;
            }
            usleep(50000);
        }
    }
    if (!child_done) {
        if (kill(-pgid, SIGKILL) == 0 || errno == ESRCH) {
            kill_sent = true;
        }
        deadline = monotonic_ms() + 1000L;
        while (!child_done && monotonic_ms() < deadline) {
            if (waitpid(pid, &status, WNOHANG) == pid) {
                child_done = true;
                reaped = true;
                if (WIFEXITED(status)) {
                    *child_exit_code = WEXITSTATUS(status);
                } else if (WIFSIGNALED(status)) {
                    *child_signal = WTERMSIG(status);
                }
                break;
            }
            usleep(50000);
        }
    }
    if (stdout_open) {
        drain_fd(stdout_pipe[0], stdout_buf, &stdout_open);
    }
    if (stderr_open) {
        drain_fd(stderr_pipe[0], stderr_buf, &stderr_open);
    }
    postflight_safe = reaped && (kill(-pgid, 0) < 0 && errno == ESRCH);

    if (append_format(stdout_buf,
                      "service_manager_start.observable=%d\n"
                      "service_manager_start.exited=%d\n"
                      "service_manager_start.exit_code=%d\n"
                      "service_manager_start.signal=%d\n"
                      "service_manager_start.timed_out=%d\n"
                      "service_manager_start.term_sent=%d\n"
                      "service_manager_start.kill_sent=%d\n"
                      "service_manager_start.reaped=%d\n"
                      "service_manager_start.proc_status_captured=%d\n"
                      "service_manager_start.fd_summary_captured=%d\n"
                      "service_manager_start.maps_summary_captured=%d\n"
                      "service_manager_start.postflight_safe=%d\n",
                      observable ? 1 : 0,
                      child_done ? 1 : 0,
                      *child_exit_code,
                      *child_signal,
                      *timed_out ? 1 : 0,
                      term_sent ? 1 : 0,
                      kill_sent ? 1 : 0,
                      reaped ? 1 : 0,
                      proc_status_captured ? 1 : 0,
                      fd_summary_captured ? 1 : 0,
                      maps_summary_captured ? 1 : 0,
                      postflight_safe ? 1 : 0) < 0) {
        goto fail;
    }
    if (!postflight_safe) {
        append_literal(stdout_buf,
                       "service_manager_start.result=start-only-reboot-required\n"
                       "service_manager_start.reason=process-not-proven-stopped\n");
    } else if (*timed_out && observable) {
        append_literal(stdout_buf,
                       "service_manager_start.result=start-only-pass\n"
                       "service_manager_start.reason=observed-until-timeout-clean-stop\n");
    } else if (exited_before_timeout || *child_exit_code >= 0 || *child_signal != 0) {
        append_literal(stdout_buf,
                       "service_manager_start.result=start-only-runtime-gap\n"
                       "service_manager_start.reason=child-exited-before-observe-window\n");
    } else {
        append_literal(stdout_buf,
                       "service_manager_start.result=manual-review-required\n"
                       "service_manager_start.reason=unclassified-lifecycle-state\n");
    }
    append_literal(stdout_buf, "service_manager_start.end=1\n");
    if (stdout_pipe[0] >= 0) close(stdout_pipe[0]);
    if (stderr_pipe[0] >= 0) close(stderr_pipe[0]);
    return 0;

fail:
    if (pid > 0) {
        kill(-pid, SIGKILL);
        kill(pid, SIGKILL);
        waitpid(pid, NULL, WNOHANG);
    }
    if (stdout_pipe[0] >= 0) close(stdout_pipe[0]);
    if (stdout_pipe[1] >= 0) close(stdout_pipe[1]);
    if (stderr_pipe[0] >= 0) close(stderr_pipe[0]);
    if (stderr_pipe[1] >= 0) close(stderr_pipe[1]);
    return -1;
}

enum composite_identity {
    COMPOSITE_ID_SERVICE_MANAGER,
    COMPOSITE_ID_VND_SERVICE_MANAGER,
    COMPOSITE_ID_WIFI_HAL,
    COMPOSITE_ID_CNSS,
    COMPOSITE_ID_CNSS_DIAG,
    COMPOSITE_ID_QRTR_NS,
    COMPOSITE_ID_RMT_STORAGE,
    COMPOSITE_ID_TFTP_SERVER,
    COMPOSITE_ID_PD_MAPPER,
    COMPOSITE_ID_MDM_HELPER,
    COMPOSITE_ID_PER_MGR,
    COMPOSITE_ID_PER_PROXY,
    COMPOSITE_ID_PER_PROXY_HELPER,
    COMPOSITE_ID_WIFICOND,
};

struct composite_child {
    const char *name;
    const char *target;
    enum composite_identity identity;
    pid_t pid;
    pid_t pgid;
    int stdout_fd;
    int stderr_fd;
    bool stdout_open;
    bool stderr_open;
    bool child_done;
    bool observable;
    bool exited_before_timeout;
    bool term_sent;
    bool kill_sent;
    bool reaped;
    bool proc_status_captured;
    bool proc_attr_current_captured;
    bool fd_summary_captured;
    bool maps_summary_captured;
    bool stall_snapshot_captured;
    bool traced;
    bool trace_initial_stop;
    bool capture_exec;
    bool capture_crash;
    int trace_cleanup_stop_continued;
    int trace_cleanup_stop_last_signal;
    int trace_cleanup_continue_errors;
    int exit_code;
    int signal;
};

static void composite_child_init(struct composite_child *child,
                                 const char *name,
                                 const char *target,
                                 enum composite_identity identity) {
    memset(child, 0, sizeof(*child));
    child->name = name;
    child->target = target;
    child->identity = identity;
    child->pid = -1;
    child->pgid = -1;
    child->stdout_fd = -1;
    child->stderr_fd = -1;
    child->stdout_open = false;
    child->stderr_open = false;
    child->exit_code = -1;
}

static int append_wifi_registry_context_snapshot(struct buffer *buf,
                                                 const char *phase,
                                                 const struct paths *paths,
                                                 const struct composite_child *children,
                                                 size_t child_count) {
    const char *debug_files[] = {
        "/sys/kernel/debug/binder/state",
        "/sys/kernel/debug/binder/stats",
        "/sys/kernel/debug/binder/transactions",
        "/sys/kernel/debug/binder/transaction_log",
        "/sys/kernel/debug/binder/failed_transaction_log",
    };
    const char *debug_labels[] = {
        "binder_state",
        "binder_stats",
        "binder_transactions",
        "binder_transaction_log",
        "binder_failed_transaction_log",
    };
    bool captured = false;
    int files_captured = 0;
    int dirs_captured = 0;
    int child_proc_captured = 0;

    if (append_format(buf,
                      "wifi_registry_snapshot.%s.begin=1\n"
                      "wifi_registry_snapshot.%s.child_count=%zu\n",
                      phase,
                      phase,
                      child_count) < 0) {
        return -1;
    }
    for (size_t file_index = 0; file_index < sizeof(debug_files) / sizeof(debug_files[0]); file_index++) {
        char label[128];

        if (snprintf(label,
                     sizeof(label),
                     "wifi_registry_%s_%s",
                     phase,
                     debug_labels[file_index]) >= (int)sizeof(label)) {
            return -1;
        }
        if (append_path_file_capture_named(buf, debug_files[file_index], label, 65536, &captured) < 0) {
            return -1;
        }
        if (captured) {
            files_captured++;
        }
    }
    {
        const char *dev_properties_path =
            (paths != NULL && paths->dev_properties[0] != '\0') ?
            paths->dev_properties : "/dev/__properties__";
        const char *dev_socket_path =
            (paths != NULL && paths->dev_socket[0] != '\0') ?
            paths->dev_socket : "/dev/socket";
        const char *dir_paths[] = {
            "/sys/kernel/debug/binder",
            "/sys/kernel/debug/binder/proc",
            dev_properties_path,
            dev_socket_path,
        };
        const char *dir_labels[] = {
            "binder_debug_dir",
            "binder_proc_dir",
            "dev_properties_dir",
            "dev_socket_dir",
        };
        const bool dir_filters[] = {
            false,
            false,
            false,
            true,
        };
        const int dir_max_entries[] = {
            64,
            128,
            128,
            128,
        };

        if (append_format(buf,
                          "wifi_registry_snapshot.%s.dev_properties_capture_path=%s\n"
                          "wifi_registry_snapshot.%s.dev_socket_capture_path=%s\n",
                          phase,
                          dev_properties_path,
                          phase,
                          dev_socket_path) < 0) {
            return -1;
        }
        for (size_t dir_index = 0; dir_index < sizeof(dir_paths) / sizeof(dir_paths[0]); dir_index++) {
            char label[128];

            if (snprintf(label,
                         sizeof(label),
                         "wifi_registry_%s_%s",
                         phase,
                         dir_labels[dir_index]) >= (int)sizeof(label)) {
                return -1;
            }
            if (append_dir_capture_named(buf,
                                         dir_paths[dir_index],
                                         label,
                                         dir_filters[dir_index],
                                         dir_max_entries[dir_index],
                                         &captured) < 0) {
                return -1;
            }
            if (captured) {
                dirs_captured++;
            }
        }
    }
    for (size_t child_index = 0; child_index < child_count; child_index++) {
        char proc_path[128];
        char label[128];

        if (append_format(buf,
                          "wifi_registry_snapshot.%s.child.%s.pid=%ld\n"
                          "wifi_registry_snapshot.%s.child.%s.observable=%d\n",
                          phase,
                          children[child_index].name,
                          (long)children[child_index].pid,
                          phase,
                          children[child_index].name,
                          children[child_index].observable ? 1 : 0) < 0) {
            return -1;
        }
        if (children[child_index].pid <= 0) {
            continue;
        }
        if (snprintf(proc_path,
                     sizeof(proc_path),
                     "/sys/kernel/debug/binder/proc/%ld",
                     (long)children[child_index].pid) >= (int)sizeof(proc_path) ||
            snprintf(label,
                     sizeof(label),
                     "wifi_registry_%s_binder_proc_%s",
                     phase,
                     children[child_index].name) >= (int)sizeof(label)) {
            return -1;
        }
        if (append_path_file_capture_named(buf, proc_path, label, 32768, &captured) < 0) {
            return -1;
        }
        if (captured) {
            child_proc_captured++;
        }
    }
    return append_format(buf,
                         "wifi_registry_snapshot.%s.files_captured=%d\n"
                         "wifi_registry_snapshot.%s.dirs_captured=%d\n"
                         "wifi_registry_snapshot.%s.child_proc_captured=%d\n"
                         "wifi_registry_snapshot.%s.end=1\n",
                         phase,
                         files_captured,
                         phase,
                         dirs_captured,
                         phase,
                         child_proc_captured,
                         phase);
}


static void composite_close_child_fds(struct composite_child *child) {
    if (child->stdout_fd >= 0) {
        close(child->stdout_fd);
        child->stdout_fd = -1;
    }
    if (child->stderr_fd >= 0) {
        close(child->stderr_fd);
        child->stderr_fd = -1;
    }
    child->stdout_open = false;
    child->stderr_open = false;
}

static int composite_spawn_child(const struct config *cfg,
                                 const struct paths *paths,
                                 struct composite_child *child,
                                 struct buffer *stdout_buf) {
    int stdout_pipe[2] = {-1, -1};
    int stderr_pipe[2] = {-1, -1};

    if (pipe2(stdout_pipe, O_CLOEXEC) < 0 || pipe2(stderr_pipe, O_CLOEXEC) < 0) {
        append_format(stdout_buf,
                      "wifi_hal_composite_start.child.%s.result=manual-review-required\n"
                      "wifi_hal_composite_start.child.%s.reason=pipe-failed-%s\n",
                      child->name,
                      child->name,
                      strerror(errno));
        if (stdout_pipe[0] >= 0) close(stdout_pipe[0]);
        if (stdout_pipe[1] >= 0) close(stdout_pipe[1]);
        if (stderr_pipe[0] >= 0) close(stderr_pipe[0]);
        if (stderr_pipe[1] >= 0) close(stderr_pipe[1]);
        return -1;
    }
    child->pid = fork();
    if (child->pid < 0) {
        append_format(stdout_buf,
                      "wifi_hal_composite_start.child.%s.result=manual-review-required\n"
                      "wifi_hal_composite_start.child.%s.reason=fork-failed-%s\n",
                      child->name,
                      child->name,
                      strerror(errno));
        close(stdout_pipe[0]);
        close(stdout_pipe[1]);
        close(stderr_pipe[0]);
        close(stderr_pipe[1]);
        return -1;
    }
    if (child->pid == 0) {
        char prefix[96];
        char *const default_argv[] = {
            (char *)child->target,
            NULL,
        };
        char *const cnss_argv[] = {
            (char *)"/vendor/bin/cnss-daemon",
            (char *)"-n",
            (char *)"-l",
            NULL,
        };
        char *const cnss_diag_argv[] = {
            (char *)"/vendor/bin/cnss_diag",
            (char *)"-q",
            (char *)"-f",
            (char *)"-t",
            (char *)"HELIUM",
            NULL,
        };
        char *const vndservicemanager_argv[] = {
            (char *)"/vendor/bin/vndservicemanager",
            (char *)"/dev/vndbinder",
            NULL,
        };
        char *const qrtr_argv[] = {
            (char *)"/vendor/bin/qrtr-ns",
            (char *)"-f",
            NULL,
        };
        char *const wificond_argv[] = {
            (char *)"/system/bin/wificond",
            NULL,
        };
        char *const *child_argv = default_argv;

        if (child->identity == COMPOSITE_ID_CNSS) {
            child_argv = cnss_argv;
        } else if (child->identity == COMPOSITE_ID_CNSS_DIAG) {
            child_argv = cnss_diag_argv;
        } else if (child->identity == COMPOSITE_ID_VND_SERVICE_MANAGER) {
            child_argv = vndservicemanager_argv;
        } else if (child->identity == COMPOSITE_ID_QRTR_NS) {
            child_argv = qrtr_argv;
        } else if (child->identity == COMPOSITE_ID_WIFICOND) {
            child_argv = wificond_argv;
        }

        close(stdout_pipe[0]);
        close(stderr_pipe[0]);
        dup2(stdout_pipe[1], STDOUT_FILENO);
        dup2(stderr_pipe[1], STDERR_FILENO);
        close(stdout_pipe[1]);
        close(stderr_pipe[1]);
        if (setsid() < 0) {
            perror("setsid");
            _exit(123);
        }
        if (chroot(paths->root) < 0) {
            perror("chroot");
            _exit(120);
        }
        if (chdir("/") < 0) {
            perror("chdir");
            _exit(121);
        }
        apply_child_env(cfg);
        snprintf(prefix, sizeof(prefix), "wifi_hal_composite_child.%s", child->name);
        printf("%s.begin=1\n", prefix);
        if (child->identity == COMPOSITE_ID_SERVICE_MANAGER ||
            child->identity == COMPOSITE_ID_VND_SERVICE_MANAGER) {
            if (apply_service_manager_identity_contract(prefix) < 0) {
                printf("%s.end=1\n", prefix);
                fflush(stdout);
                _exit(126);
            }
        } else if (child->identity == COMPOSITE_ID_WIFI_HAL) {
            if (apply_wifi_hal_identity_contract(prefix) < 0) {
                printf("%s.end=1\n", prefix);
                fflush(stdout);
                _exit(126);
            }
        } else if (child->identity == COMPOSITE_ID_WIFICOND) {
            if (apply_wificond_identity_contract(prefix) < 0) {
                printf("%s.end=1\n", prefix);
                fflush(stdout);
                _exit(126);
            }
        } else if (child->identity == COMPOSITE_ID_CNSS) {
            if (apply_android_identity_contract(prefix) < 0) {
                printf("%s.end=1\n", prefix);
                fflush(stdout);
                _exit(126);
            }
        } else if (child->identity == COMPOSITE_ID_CNSS_DIAG) {
            if (apply_cnss_diag_identity_contract(prefix) < 0) {
                printf("%s.end=1\n", prefix);
                fflush(stdout);
                _exit(126);
            }
        } else if (child->identity == COMPOSITE_ID_QRTR_NS) {
            if (apply_qrtr_ns_identity_contract(prefix) < 0) {
                printf("%s.end=1\n", prefix);
                fflush(stdout);
                _exit(126);
            }
        } else if (child->identity == COMPOSITE_ID_RMT_STORAGE) {
            if (apply_rmt_storage_identity_contract(prefix) < 0) {
                printf("%s.end=1\n", prefix);
                fflush(stdout);
                _exit(126);
            }
        } else if (child->identity == COMPOSITE_ID_TFTP_SERVER) {
            if (apply_tftp_server_identity_contract(prefix) < 0) {
                printf("%s.end=1\n", prefix);
                fflush(stdout);
                _exit(126);
            }
        } else if (child->identity == COMPOSITE_ID_PD_MAPPER) {
            if (apply_pd_mapper_identity_contract(prefix) < 0) {
                printf("%s.end=1\n", prefix);
                fflush(stdout);
                _exit(126);
            }
        } else if (child->identity == COMPOSITE_ID_MDM_HELPER) {
            if (apply_mdm_helper_identity_contract(prefix) < 0) {
                printf("%s.end=1\n", prefix);
                fflush(stdout);
                _exit(126);
            }
        } else if (child->identity == COMPOSITE_ID_PER_MGR ||
                   child->identity == COMPOSITE_ID_PER_PROXY ||
                   child->identity == COMPOSITE_ID_PER_PROXY_HELPER) {
            if (child->identity == COMPOSITE_ID_PER_MGR) {
                apply_peripheral_manager_ioprio_rt4_contract(prefix);
            }
            if (apply_peripheral_manager_identity_contract(prefix) < 0) {
                printf("%s.end=1\n", prefix);
                fflush(stdout);
                _exit(126);
            }
        } else {
            printf("%s.identity_error=unknown-composite-identity\n", prefix);
            printf("%s.end=1\n", prefix);
            fflush(stdout);
            _exit(126);
        }
        if (apply_android_exec_selinux_context_if_requested(cfg, prefix, child->target) < 0) {
            printf("%s.end=1\n", prefix);
            fflush(stdout);
            _exit(126);
        }
        if ((is_wifi_hal_composite_ptrace_mode(cfg->mode) &&
             child->identity == COMPOSITE_ID_WIFI_HAL) ||
            (is_wifi_companion_ptrace_capture(cfg) &&
             child->identity == COMPOSITE_ID_CNSS)) {
            if (ptrace(PTRACE_TRACEME, 0, NULL, NULL) < 0) {
                printf("%s.ptrace_traceme_error=%s\n", prefix, strerror(errno));
                printf("%s.end=1\n", prefix);
                fflush(stdout);
                _exit(122);
            }
            printf("%s.ptrace_traceme=1\n", prefix);
            fflush(stdout);
            raise(SIGSTOP);
        }
        printf("%s.exec_target=%s%s\n", prefix, child->target,
               child->identity == COMPOSITE_ID_CNSS
                   ? " -n -l"
                   : (child->identity == COMPOSITE_ID_CNSS_DIAG
                          ? " -q -f -t HELIUM"
                          : (child->identity == COMPOSITE_ID_QRTR_NS
                                 ? " -f"
                                 : (child->identity == COMPOSITE_ID_VND_SERVICE_MANAGER
                                        ? " /dev/vndbinder"
                                        : ""))));
        fflush(stdout);
        execv(child->target, child_argv);
        printf("%s.exec_error=%s\n", prefix, strerror(errno));
        printf("%s.end=1\n", prefix);
        fflush(stdout);
        _exit(127);
    }
    close(stdout_pipe[1]);
    close(stderr_pipe[1]);
    child->stdout_fd = stdout_pipe[0];
    child->stderr_fd = stderr_pipe[0];
    child->stdout_open = true;
    child->stderr_open = true;
    child->traced = (is_wifi_hal_composite_ptrace_mode(cfg->mode) &&
                     child->identity == COMPOSITE_ID_WIFI_HAL) ||
        (is_wifi_companion_ptrace_capture(cfg) &&
         child->identity == COMPOSITE_ID_CNSS);
    set_nonblock(child->stdout_fd);
    set_nonblock(child->stderr_fd);
    child->pgid = wait_for_child_session_pgid(child->pid, 1000);
    return append_format(stdout_buf,
                         "wifi_hal_composite_start.child.%s.exec_attempted=1\n"
                         "wifi_hal_composite_start.child.%s.child_started=1\n"
                         "wifi_hal_composite_start.child.%s.target=%s\n"
                         "wifi_hal_composite_start.child.%s.traced=%d\n"
                         "wifi_hal_composite_start.child.%s.pid=%ld\n"
                         "wifi_hal_composite_start.child.%s.pgid=%ld\n",
                         child->name,
                         child->name,
                         child->name,
                         child->target,
                         child->name,
                         child->traced ? 1 : 0,
                         child->name,
                         (long)child->pid,
                         child->name,
                         (long)child->pgid);
}

static int composite_handle_traced_stop(struct composite_child *child,
                                        int status,
                                        struct buffer *stdout_buf) {
    int sig = WSTOPSIG(status);
    unsigned int event = (unsigned int)status >> 16;
    int deliver_sig = 0;

    append_format(stdout_buf,
                  "wifi_hal_composite_start.child.%s.trace.stop.signal=%d\n"
                  "wifi_hal_composite_start.child.%s.trace.stop.event=%u\n",
                  child->name,
                  sig,
                  child->name,
                  event);
    if (!child->traced) {
        return 0;
    }
    if (sig == SIGSTOP && !child->trace_initial_stop) {
        child->trace_initial_stop = true;
        append_format(stdout_buf,
                      "wifi_hal_composite_start.child.%s.trace.initial_stop=1\n",
                      child->name);
        if (ptrace(PTRACE_SETOPTIONS,
                   child->pid,
                   NULL,
                   (void *)(long)(PTRACE_O_TRACEEXEC | PTRACE_O_EXITKILL)) < 0) {
            return append_format(stdout_buf,
                                 "wifi_hal_composite_start.child.%s.trace.setoptions.error=%s\n",
                                 child->name,
                                 strerror(errno));
        }
        if (ptrace(PTRACE_CONT, child->pid, NULL, NULL) < 0) {
            return append_format(stdout_buf,
                                 "wifi_hal_composite_start.child.%s.trace.cont.error=%s\n",
                                 child->name,
                                 strerror(errno));
        }
        return 0;
    }
    if (sig == SIGTRAP && !child->capture_exec) {
        child->capture_exec = true;
        append_format(stdout_buf,
                      "wifi_hal_composite_start.child.%s.trace.exec_stop=1\n",
                      child->name);
        if (append_capture_snapshot_compact(stdout_buf, child->pid, "exec", true) < 0) {
            return -1;
        }
    } else if ((sig == SIGSEGV || sig == SIGBUS || sig == SIGILL || sig == SIGABRT) &&
               !child->capture_crash) {
        child->capture_crash = true;
        append_format(stdout_buf,
                      "wifi_hal_composite_start.child.%s.trace.crash_stop=1\n",
                      child->name);
        if (append_ptrace_siginfo_compact(stdout_buf, child->pid, "crash") < 0 ||
            append_capture_snapshot_compact(stdout_buf, child->pid, "crash", true) < 0) {
            return -1;
        }
        deliver_sig = sig;
    } else if (sig == SIGSEGV || sig == SIGBUS || sig == SIGILL || sig == SIGABRT) {
        deliver_sig = sig;
    } else if (sig != SIGTRAP) {
        deliver_sig = sig;
    }
    if (ptrace(PTRACE_CONT, child->pid, NULL, (void *)(long)deliver_sig) < 0) {
        child->trace_cleanup_continue_errors++;
        return append_format(stdout_buf,
                             "wifi_hal_composite_start.child.%s.trace.cont.error=%s\n",
                             child->name,
                             strerror(errno));
    }
    return 0;
}

static int composite_poll_children(struct composite_child *children,
                                   size_t child_count,
                                   struct buffer *stdout_buf,
                                   struct buffer *stderr_buf,
                                   long deadline,
                                   bool *timed_out) {
    while (monotonic_ms() < deadline) {
        struct pollfd fds[A90_COMPOSITE_CHILD_MAX * 2];
        struct composite_child *fd_children[A90_COMPOSITE_CHILD_MAX * 2];
        bool fd_is_stdout[A90_COMPOSITE_CHILD_MAX * 2];
        int nfds = 0;
        bool all_done = true;

        for (size_t i = 0; i < child_count; i++) {
            if (!children[i].child_done) {
                all_done = false;
            }
            if (children[i].stdout_open && children[i].stdout_fd >= 0) {
                fds[nfds].fd = children[i].stdout_fd;
                fds[nfds].events = POLLIN | POLLHUP | POLLERR;
                fd_children[nfds] = &children[i];
                fd_is_stdout[nfds] = true;
                nfds++;
            }
            if (children[i].stderr_open && children[i].stderr_fd >= 0) {
                fds[nfds].fd = children[i].stderr_fd;
                fds[nfds].events = POLLIN | POLLHUP | POLLERR;
                fd_children[nfds] = &children[i];
                fd_is_stdout[nfds] = false;
                nfds++;
            }
        }
        if (all_done) {
            for (size_t i = 0; i < child_count; i++) {
                if (children[i].stdout_open && children[i].stdout_fd >= 0 &&
                    drain_fd(children[i].stdout_fd, stdout_buf, &children[i].stdout_open) < 0) {
                    return -1;
                }
                if (children[i].stderr_open && children[i].stderr_fd >= 0 &&
                    drain_fd(children[i].stderr_fd, stderr_buf, &children[i].stderr_open) < 0) {
                    return -1;
                }
            }
            return 0;
        }
        if (nfds > 0) {
            int rc = poll(fds, nfds, 50);

            if (rc > 0) {
                for (int i = 0; i < nfds; i++) {
                    if (fds[i].revents == 0) {
                        continue;
                    }
                    if (fd_is_stdout[i]) {
                        drain_fd(fd_children[i]->stdout_fd,
                                 stdout_buf,
                                 &fd_children[i]->stdout_open);
                    } else {
                        drain_fd(fd_children[i]->stderr_fd,
                                 stderr_buf,
                                 &fd_children[i]->stderr_open);
                    }
                }
            }
        } else {
            usleep(50000);
        }
        for (size_t i = 0; i < child_count; i++) {
            int status = 0;
            pid_t wait_rc;

            if (children[i].child_done || children[i].pid <= 0) {
                continue;
            }
            wait_rc = waitpid(children[i].pid, &status, WNOHANG);
            if (wait_rc == children[i].pid) {
                children[i].child_done = true;
                children[i].reaped = true;
                children[i].exited_before_timeout = !*timed_out;
                if (WIFEXITED(status)) {
                    children[i].exit_code = WEXITSTATUS(status);
                } else if (WIFSIGNALED(status)) {
                    children[i].signal = WTERMSIG(status);
                } else if (WIFSTOPPED(status)) {
                    children[i].child_done = false;
                    children[i].reaped = false;
                    children[i].exited_before_timeout = false;
                    if (composite_handle_traced_stop(&children[i], status, stdout_buf) < 0) {
                        return -1;
                    }
                }
            } else if (wait_rc < 0 && errno != EINTR && errno != ECHILD) {
                append_format(stdout_buf,
                              "wifi_hal_composite_start.child.%s.wait.error=%s\n",
                              children[i].name,
                              strerror(errno));
            }
        }
    }
    *timed_out = true;
    return 0;
}

static int run_lshal_service_query_child(const struct config *cfg,
                                         const struct paths *paths,
                                         struct buffer *stdout_buf,
                                         struct buffer *stderr_buf,
                                         int timeout_ms) {
    const bool binderized_only = streq(cfg->mode, "wifi-hal-composite-lshal-binderized-list");
    const bool status_columns = streq(cfg->mode, "wifi-hal-composite-lshal-status-list");
    const bool binderized_status_only = streq(cfg->mode, "wifi-hal-composite-lshal-binderized-status-list");
    const bool vintf_status_only = streq(cfg->mode, "wifi-hal-lshal-vintf-status-list");
    const char *variant = status_columns
                              ? "binderized-vintf-status"
                              : (vintf_status_only
                                     ? "vintf-status-only"
                                     : (binderized_status_only
                                            ? "binderized-status"
                                            : (binderized_only ? "binderized-only" : "default")));
    char lshal_host_path[MAX_PATH_LEN];
    int stdout_pipe[2] = {-1, -1};
    int stderr_pipe[2] = {-1, -1};
    pid_t pid;
    pid_t pgid;
    bool stdout_open = false;
    bool stderr_open = false;
    bool child_done = false;
    bool timed_out = false;
    int exit_code = -1;
    int signal_no = 0;
    long deadline;

    if (append_path(lshal_host_path, sizeof(lshal_host_path), paths->root, "system/bin/lshal") < 0) {
        append_format(stdout_buf,
                      "wifi_hal_service_query.result=manual-review-required\n"
                      "wifi_hal_service_query.reason=lshal-path-too-long\n");
        return -1;
    }
    append_literal(stdout_buf, "wifi_hal_service_query.begin=1\n");
    append_literal(stdout_buf, "wifi_hal_service_query.tool=/system/bin/lshal\n");
    append_format(stdout_buf,
                  "wifi_hal_service_query.variant=%s\n"
                  "wifi_hal_service_query.host_path=%s\n"
                  "wifi_hal_service_query.exists=%d\n"
                  "wifi_hal_service_query.executable=%d\n"
                  "wifi_hal_service_query.scan_connect_linkup=0\n"
                  "wifi_hal_service_query.credentials=0\n"
                  "wifi_hal_service_query.dhcp_routing=0\n",
                  variant,
                  lshal_host_path,
                  access(lshal_host_path, F_OK) == 0 ? 1 : 0,
                  access(lshal_host_path, X_OK) == 0 ? 1 : 0);
    if (access(lshal_host_path, X_OK) < 0) {
        append_format(stdout_buf,
                      "wifi_hal_service_query.exec_attempted=0\n"
                      "wifi_hal_service_query.result=service-query-tool-missing\n"
                      "wifi_hal_service_query.reason=system-bin-lshal-unavailable-%s\n"
                      "wifi_hal_service_query.end=1\n",
                      strerror(errno));
        return 10;
    }
    if (pipe2(stdout_pipe, O_CLOEXEC) < 0 || pipe2(stderr_pipe, O_CLOEXEC) < 0) {
        append_format(stdout_buf,
                      "wifi_hal_service_query.result=manual-review-required\n"
                      "wifi_hal_service_query.reason=pipe-failed-%s\n"
                      "wifi_hal_service_query.end=1\n",
                      strerror(errno));
        if (stdout_pipe[0] >= 0) close(stdout_pipe[0]);
        if (stdout_pipe[1] >= 0) close(stdout_pipe[1]);
        if (stderr_pipe[0] >= 0) close(stderr_pipe[0]);
        if (stderr_pipe[1] >= 0) close(stderr_pipe[1]);
        return -1;
    }
    pid = fork();
    if (pid < 0) {
        append_format(stdout_buf,
                      "wifi_hal_service_query.result=manual-review-required\n"
                      "wifi_hal_service_query.reason=fork-failed-%s\n"
                      "wifi_hal_service_query.end=1\n",
                      strerror(errno));
        close(stdout_pipe[0]);
        close(stdout_pipe[1]);
        close(stderr_pipe[0]);
        close(stderr_pipe[1]);
        return -1;
    }
    if (pid == 0) {
        char *const default_argv[] = {
            (char *)"/system/bin/lshal",
            NULL,
        };
        char *const binderized_argv[] = {
            (char *)"/system/bin/lshal",
            (char *)"list",
            (char *)"--types=binderized",
            (char *)"--neat",
            NULL,
        };
        char *const binderized_status_argv[] = {
            (char *)"/system/bin/lshal",
            (char *)"list",
            (char *)"--types=binderized",
            (char *)"--neat",
            (char *)"-S",
            NULL,
        };
        char *const status_argv[] = {
            (char *)"/system/bin/lshal",
            (char *)"list",
            (char *)"--types=binderized,vintf",
            (char *)"--neat",
            (char *)"-V",
            (char *)"-S",
            (char *)"-i",
            (char *)"-p",
            (char *)"-e",
            (char *)"-c",
            NULL,
        };
        char *const vintf_status_argv[] = {
            (char *)"/system/bin/lshal",
            (char *)"list",
            (char *)"--types=vintf",
            (char *)"--neat",
            (char *)"-V",
            (char *)"-S",
            (char *)"-i",
            NULL,
        };
        char *const *child_argv = default_argv;

        if (status_columns) {
            child_argv = status_argv;
        } else if (vintf_status_only) {
            child_argv = vintf_status_argv;
        } else if (binderized_status_only) {
            child_argv = binderized_status_argv;
        } else if (binderized_only) {
            child_argv = binderized_argv;
        }

        close(stdout_pipe[0]);
        close(stderr_pipe[0]);
        dup2(stdout_pipe[1], STDOUT_FILENO);
        dup2(stderr_pipe[1], STDERR_FILENO);
        close(stdout_pipe[1]);
        close(stderr_pipe[1]);
        if (setsid() < 0) {
            perror("setsid");
            _exit(123);
        }
        if (chroot(paths->root) < 0) {
            perror("chroot");
            _exit(120);
        }
        if (chdir("/") < 0) {
            perror("chdir");
            _exit(121);
        }
        apply_child_env(cfg);
        printf("wifi_hal_service_query.child.begin=1\n");
        if (apply_service_manager_identity_contract("wifi_hal_service_query.child") < 0) {
            printf("wifi_hal_service_query.child.end=1\n");
            fflush(stdout);
            _exit(126);
        }
        printf("wifi_hal_service_query.child.exec_target=/system/bin/lshal\n");
        if (binderized_only) {
            printf("wifi_hal_service_query.child.argv.1=list\n");
            printf("wifi_hal_service_query.child.argv.2=--types=binderized\n");
            printf("wifi_hal_service_query.child.argv.3=--neat\n");
        } else if (binderized_status_only) {
            printf("wifi_hal_service_query.child.argv.1=list\n");
            printf("wifi_hal_service_query.child.argv.2=--types=binderized\n");
            printf("wifi_hal_service_query.child.argv.3=--neat\n");
            printf("wifi_hal_service_query.child.argv.4=-S\n");
        } else if (status_columns) {
            printf("wifi_hal_service_query.child.argv.1=list\n");
            printf("wifi_hal_service_query.child.argv.2=--types=binderized,vintf\n");
            printf("wifi_hal_service_query.child.argv.3=--neat\n");
            printf("wifi_hal_service_query.child.argv.4=-V\n");
            printf("wifi_hal_service_query.child.argv.5=-S\n");
            printf("wifi_hal_service_query.child.argv.6=-i\n");
            printf("wifi_hal_service_query.child.argv.7=-p\n");
            printf("wifi_hal_service_query.child.argv.8=-e\n");
            printf("wifi_hal_service_query.child.argv.9=-c\n");
        } else if (vintf_status_only) {
            printf("wifi_hal_service_query.child.argv.1=list\n");
            printf("wifi_hal_service_query.child.argv.2=--types=vintf\n");
            printf("wifi_hal_service_query.child.argv.3=--neat\n");
            printf("wifi_hal_service_query.child.argv.4=-V\n");
            printf("wifi_hal_service_query.child.argv.5=-S\n");
            printf("wifi_hal_service_query.child.argv.6=-i\n");
        }
        fflush(stdout);
        execv("/system/bin/lshal", child_argv);
        printf("wifi_hal_service_query.child.exec_error=%s\n", strerror(errno));
        printf("wifi_hal_service_query.child.end=1\n");
        fflush(stdout);
        _exit(127);
    }
    close(stdout_pipe[1]);
    close(stderr_pipe[1]);
    stdout_open = true;
    stderr_open = true;
    set_nonblock(stdout_pipe[0]);
    set_nonblock(stderr_pipe[0]);
    pgid = wait_for_child_session_pgid(pid, 1000);
    append_format(stdout_buf,
                  "wifi_hal_service_query.exec_attempted=1\n"
                  "wifi_hal_service_query.child_started=1\n"
                  "wifi_hal_service_query.pid=%ld\n"
                  "wifi_hal_service_query.pgid=%ld\n",
                  (long)pid,
                  (long)pgid);

    deadline = monotonic_ms() + timeout_ms;
    while (stdout_open || stderr_open || !child_done) {
        struct pollfd fds[2];
        int nfds = 0;

        if (!child_done && monotonic_ms() >= deadline) {
            timed_out = true;
            if (pgid > 1) {
                kill(-pgid, SIGTERM);
            }
            kill(pid, SIGTERM);
        }
        if (stdout_open) {
            fds[nfds].fd = stdout_pipe[0];
            fds[nfds].events = POLLIN | POLLHUP | POLLERR;
            nfds++;
        }
        if (stderr_open) {
            fds[nfds].fd = stderr_pipe[0];
            fds[nfds].events = POLLIN | POLLHUP | POLLERR;
            nfds++;
        }
        if (nfds > 0) {
            int rc = poll(fds, nfds, 50);

            if (rc > 0) {
                int idx = 0;

                if (stdout_open) {
                    if (fds[idx].revents != 0) {
                        drain_fd(stdout_pipe[0], stdout_buf, &stdout_open);
                    }
                    idx++;
                }
                if (stderr_open && fds[idx].revents != 0) {
                    drain_fd(stderr_pipe[0], stderr_buf, &stderr_open);
                }
            }
        } else {
            usleep(50000);
        }
        if (!child_done) {
            int status = 0;
            pid_t wait_rc = waitpid(pid, &status, WNOHANG);

            if (wait_rc == pid) {
                child_done = true;
                if (WIFEXITED(status)) {
                    exit_code = WEXITSTATUS(status);
                } else if (WIFSIGNALED(status)) {
                    signal_no = WTERMSIG(status);
                }
            } else if (wait_rc < 0) {
                if (errno == ECHILD) {
                    child_done = true;
                } else if (errno != EINTR) {
                    append_format(stdout_buf, "wifi_hal_service_query.wait.error=%s\n", strerror(errno));
                    child_done = true;
                }
            }
        }
        if (timed_out && !child_done && monotonic_ms() >= deadline + 1000L) {
            if (pgid > 1) {
                kill(-pgid, SIGKILL);
            }
            kill(pid, SIGKILL);
        }
    }
    if (stdout_pipe[0] >= 0) close(stdout_pipe[0]);
    if (stderr_pipe[0] >= 0) close(stderr_pipe[0]);
    append_format(stdout_buf,
                  "wifi_hal_service_query.exit_code=%d\n"
                  "wifi_hal_service_query.signal=%d\n"
                  "wifi_hal_service_query.timed_out=%d\n",
                  exit_code,
                  signal_no,
                  timed_out ? 1 : 0);
    if (timed_out) {
        append_literal(stdout_buf,
                       "wifi_hal_service_query.result=service-query-timeout\n"
                       "wifi_hal_service_query.reason=lshal-timeout\n"
                       "wifi_hal_service_query.end=1\n");
        return 12;
    }
    if (exit_code == 0 && signal_no == 0) {
        append_literal(stdout_buf,
                       "wifi_hal_service_query.result=service-query-pass\n"
                       "wifi_hal_service_query.reason=lshal-exit-zero\n"
                       "wifi_hal_service_query.end=1\n");
        return 0;
    }
    append_literal(stdout_buf,
                   "wifi_hal_service_query.result=service-query-runtime-gap\n"
                   "wifi_hal_service_query.reason=lshal-nonzero\n"
                   "wifi_hal_service_query.end=1\n");
    return 11;
}

static int run_lshal_wait_target_attempt(const struct config *cfg,
                                         const struct paths *paths,
                                         struct buffer *stdout_buf,
                                         struct buffer *stderr_buf,
                                         const char *fqinstance,
                                         size_t target_index,
                                         int timeout_ms) {
    int stdout_pipe[2] = {-1, -1};
    int stderr_pipe[2] = {-1, -1};
    pid_t pid;
    pid_t pgid;
    bool stdout_open = false;
    bool stderr_open = false;
    bool child_done = false;
    bool timed_out = false;
    int exit_code = -1;
    int signal_no = 0;
    long deadline;

    append_format(stdout_buf,
                  "wifi_hal_micro_query.target.%zu.begin=1\n"
                  "wifi_hal_micro_query.target.%zu.fqinstance=%s\n",
                  target_index,
                  target_index,
                  fqinstance);
    if (pipe2(stdout_pipe, O_CLOEXEC) < 0 || pipe2(stderr_pipe, O_CLOEXEC) < 0) {
        append_format(stdout_buf,
                      "wifi_hal_micro_query.target.%zu.result=manual-review-required\n"
                      "wifi_hal_micro_query.target.%zu.reason=pipe-failed-%s\n"
                      "wifi_hal_micro_query.target.%zu.end=1\n",
                      target_index,
                      target_index,
                      strerror(errno),
                      target_index);
        if (stdout_pipe[0] >= 0) close(stdout_pipe[0]);
        if (stdout_pipe[1] >= 0) close(stdout_pipe[1]);
        if (stderr_pipe[0] >= 0) close(stderr_pipe[0]);
        if (stderr_pipe[1] >= 0) close(stderr_pipe[1]);
        return -1;
    }
    pid = fork();
    if (pid < 0) {
        append_format(stdout_buf,
                      "wifi_hal_micro_query.target.%zu.result=manual-review-required\n"
                      "wifi_hal_micro_query.target.%zu.reason=fork-failed-%s\n"
                      "wifi_hal_micro_query.target.%zu.end=1\n",
                      target_index,
                      target_index,
                      strerror(errno),
                      target_index);
        close(stdout_pipe[0]);
        close(stdout_pipe[1]);
        close(stderr_pipe[0]);
        close(stderr_pipe[1]);
        return -1;
    }
    if (pid == 0) {
        char *const wait_argv[] = {
            (char *)"/system/bin/lshal",
            (char *)"wait",
            (char *)fqinstance,
            NULL,
        };

        close(stdout_pipe[0]);
        close(stderr_pipe[0]);
        dup2(stdout_pipe[1], STDOUT_FILENO);
        dup2(stderr_pipe[1], STDERR_FILENO);
        close(stdout_pipe[1]);
        close(stderr_pipe[1]);
        if (setsid() < 0) {
            perror("setsid");
            _exit(123);
        }
        if (chroot(paths->root) < 0) {
            perror("chroot");
            _exit(120);
        }
        if (chdir("/") < 0) {
            perror("chdir");
            _exit(121);
        }
        apply_child_env(cfg);
        printf("wifi_hal_micro_query.target.%zu.child.begin=1\n", target_index);
        if (apply_service_manager_identity_contract("wifi_hal_micro_query.child") < 0) {
            printf("wifi_hal_micro_query.target.%zu.child.end=1\n", target_index);
            fflush(stdout);
            _exit(126);
        }
        printf("wifi_hal_micro_query.target.%zu.child.exec_target=/system/bin/lshal\n", target_index);
        printf("wifi_hal_micro_query.target.%zu.child.argv.1=wait\n", target_index);
        printf("wifi_hal_micro_query.target.%zu.child.argv.2=%s\n", target_index, fqinstance);
        fflush(stdout);
        execv("/system/bin/lshal", wait_argv);
        printf("wifi_hal_micro_query.target.%zu.child.exec_error=%s\n", target_index, strerror(errno));
        printf("wifi_hal_micro_query.target.%zu.child.end=1\n", target_index);
        fflush(stdout);
        _exit(127);
    }
    close(stdout_pipe[1]);
    close(stderr_pipe[1]);
    stdout_open = true;
    stderr_open = true;
    set_nonblock(stdout_pipe[0]);
    set_nonblock(stderr_pipe[0]);
    pgid = wait_for_child_session_pgid(pid, 1000);
    append_format(stdout_buf,
                  "wifi_hal_micro_query.target.%zu.exec_attempted=1\n"
                  "wifi_hal_micro_query.target.%zu.child_started=1\n"
                  "wifi_hal_micro_query.target.%zu.pid=%ld\n"
                  "wifi_hal_micro_query.target.%zu.pgid=%ld\n",
                  target_index,
                  target_index,
                  target_index,
                  (long)pid,
                  target_index,
                  (long)pgid);

    deadline = monotonic_ms() + timeout_ms;
    while (stdout_open || stderr_open || !child_done) {
        struct pollfd fds[2];
        int nfds = 0;

        if (!child_done && monotonic_ms() >= deadline) {
            timed_out = true;
            if (pgid > 1) {
                kill(-pgid, SIGTERM);
            }
            kill(pid, SIGTERM);
        }
        if (stdout_open) {
            fds[nfds].fd = stdout_pipe[0];
            fds[nfds].events = POLLIN | POLLHUP | POLLERR;
            nfds++;
        }
        if (stderr_open) {
            fds[nfds].fd = stderr_pipe[0];
            fds[nfds].events = POLLIN | POLLHUP | POLLERR;
            nfds++;
        }
        if (nfds > 0) {
            int rc = poll(fds, nfds, 50);

            if (rc > 0) {
                int idx = 0;

                if (stdout_open) {
                    if (fds[idx].revents != 0) {
                        drain_fd(stdout_pipe[0], stdout_buf, &stdout_open);
                    }
                    idx++;
                }
                if (stderr_open && fds[idx].revents != 0) {
                    drain_fd(stderr_pipe[0], stderr_buf, &stderr_open);
                }
            }
        } else {
            usleep(50000);
        }
        if (!child_done) {
            int status = 0;
            pid_t wait_rc = waitpid(pid, &status, WNOHANG);

            if (wait_rc == pid) {
                child_done = true;
                if (WIFEXITED(status)) {
                    exit_code = WEXITSTATUS(status);
                } else if (WIFSIGNALED(status)) {
                    signal_no = WTERMSIG(status);
                }
            } else if (wait_rc < 0) {
                if (errno == ECHILD) {
                    child_done = true;
                } else if (errno != EINTR) {
                    append_format(stdout_buf,
                                  "wifi_hal_micro_query.target.%zu.wait.error=%s\n",
                                  target_index,
                                  strerror(errno));
                    child_done = true;
                }
            }
        }
        if (timed_out && !child_done && monotonic_ms() >= deadline + 1000L) {
            if (pgid > 1) {
                kill(-pgid, SIGKILL);
            }
            kill(pid, SIGKILL);
        }
    }
    if (stdout_pipe[0] >= 0) close(stdout_pipe[0]);
    if (stderr_pipe[0] >= 0) close(stderr_pipe[0]);
    append_format(stdout_buf,
                  "wifi_hal_micro_query.target.%zu.exit_code=%d\n"
                  "wifi_hal_micro_query.target.%zu.signal=%d\n"
                  "wifi_hal_micro_query.target.%zu.timed_out=%d\n",
                  target_index,
                  exit_code,
                  target_index,
                  signal_no,
                  target_index,
                  timed_out ? 1 : 0);
    if (timed_out) {
        append_format(stdout_buf,
                      "wifi_hal_micro_query.target.%zu.result=service-query-timeout\n"
                      "wifi_hal_micro_query.target.%zu.reason=lshal-wait-timeout\n"
                      "wifi_hal_micro_query.target.%zu.end=1\n",
                      target_index,
                      target_index,
                      target_index);
        return 12;
    }
    if (exit_code == 0 && signal_no == 0) {
        append_format(stdout_buf,
                      "wifi_hal_micro_query.target.%zu.result=service-query-pass\n"
                      "wifi_hal_micro_query.target.%zu.reason=lshal-wait-exit-zero\n"
                      "wifi_hal_micro_query.target.%zu.end=1\n",
                      target_index,
                      target_index,
                      target_index);
        return 0;
    }
    append_format(stdout_buf,
                  "wifi_hal_micro_query.target.%zu.result=service-query-runtime-gap\n"
                  "wifi_hal_micro_query.target.%zu.reason=lshal-wait-nonzero\n"
                  "wifi_hal_micro_query.target.%zu.end=1\n",
                  target_index,
                  target_index,
                  target_index);
    return 11;
}

static int run_lshal_wait_target_query_child(const struct config *cfg,
                                             const struct paths *paths,
                                             struct buffer *stdout_buf,
                                             struct buffer *stderr_buf,
                                             int timeout_ms) {
    char lshal_host_path[MAX_PATH_LEN];
    const char *const *targets = A90_WIFI_HAL_WAIT_TARGETS;
    size_t target_count = A90_WIFI_HAL_WAIT_TARGET_COUNT;
    bool any_timeout = false;
    bool any_nonzero = false;

    if (is_wifi_hal_lshal_wait_iwifi_mode(cfg->mode)) {
        targets = A90_IWIFI_WAIT_TARGETS;
        target_count = sizeof(A90_IWIFI_WAIT_TARGETS) / sizeof(A90_IWIFI_WAIT_TARGETS[0]);
    }

    if (append_path(lshal_host_path, sizeof(lshal_host_path), paths->root, "system/bin/lshal") < 0) {
        append_format(stdout_buf,
                      "wifi_hal_micro_query.result=manual-review-required\n"
                      "wifi_hal_micro_query.reason=lshal-path-too-long\n");
        return -1;
    }
    append_literal(stdout_buf, "wifi_hal_micro_query.begin=1\n");
    append_literal(stdout_buf, "wifi_hal_micro_query.tool=/system/bin/lshal\n");
    append_format(stdout_buf,
                  "wifi_hal_micro_query.variant=targeted-lshal-wait\n"
                  "wifi_hal_micro_query.host_path=%s\n"
                  "wifi_hal_micro_query.exists=%d\n"
                  "wifi_hal_micro_query.executable=%d\n"
                  "wifi_hal_micro_query.target_count=%zu\n"
                  "wifi_hal_micro_query.per_target_timeout_ms=%d\n"
                  "wifi_hal_micro_query.scan_connect_linkup=0\n"
                  "wifi_hal_micro_query.credentials=0\n"
                  "wifi_hal_micro_query.dhcp_routing=0\n",
                  lshal_host_path,
                  access(lshal_host_path, F_OK) == 0 ? 1 : 0,
                  access(lshal_host_path, X_OK) == 0 ? 1 : 0,
                  target_count,
                  timeout_ms);
    if (access(lshal_host_path, X_OK) < 0) {
        append_format(stdout_buf,
                      "wifi_hal_micro_query.exec_attempted=0\n"
                      "wifi_hal_micro_query.result=service-query-tool-missing\n"
                      "wifi_hal_micro_query.reason=system-bin-lshal-unavailable-%s\n"
                      "wifi_hal_micro_query.end=1\n",
                      strerror(errno));
        return 10;
    }
    append_literal(stdout_buf, "wifi_hal_micro_query.exec_attempted=1\n");
    for (size_t i = 0; i < target_count; i++) {
        int rc = run_lshal_wait_target_attempt(cfg,
                                               paths,
                                               stdout_buf,
                                               stderr_buf,
                                               targets[i],
                                               i,
                                               timeout_ms);

        if (rc == 0) {
            append_format(stdout_buf,
                          "wifi_hal_micro_query.result=service-query-pass\n"
                          "wifi_hal_micro_query.reason=lshal-wait-exit-zero\n"
                          "wifi_hal_micro_query.matched_index=%zu\n"
                          "wifi_hal_micro_query.matched_fqinstance=%s\n"
                          "wifi_hal_micro_query.end=1\n",
                          i,
                          targets[i]);
            return 0;
        }
        if (rc == 12) {
            any_timeout = true;
        } else if (rc != 0) {
            any_nonzero = true;
        }
        if (rc < 0) {
            append_literal(stdout_buf,
                           "wifi_hal_micro_query.result=manual-review-required\n"
                           "wifi_hal_micro_query.reason=lshal-wait-attempt-failed\n"
                           "wifi_hal_micro_query.end=1\n");
            return -1;
        }
    }
    if (any_timeout) {
        append_literal(stdout_buf,
                       "wifi_hal_micro_query.result=service-query-timeout\n"
                       "wifi_hal_micro_query.reason=lshal-wait-timeout\n"
                       "wifi_hal_micro_query.end=1\n");
        return 12;
    }
    if (any_nonzero) {
        append_literal(stdout_buf,
                       "wifi_hal_micro_query.result=service-query-runtime-gap\n"
                       "wifi_hal_micro_query.reason=lshal-wait-nonzero\n"
                       "wifi_hal_micro_query.end=1\n");
        return 11;
    }
    append_literal(stdout_buf,
                   "wifi_hal_micro_query.result=manual-review-required\n"
                   "wifi_hal_micro_query.reason=no-targets-attempted\n"
                   "wifi_hal_micro_query.end=1\n");
    return -1;
}

static int append_named_buffer_capture(struct buffer *out,
                                       const char *label,
                                       const char *stream,
                                       const struct buffer *capture) {
    if (append_format(out,
                      "A90_EXECNS_VNDSERVICE_QUERY_%s_%s_BEGIN bytes=%zu truncated=%d\n",
                      label,
                      stream,
                      capture->len,
                      capture->truncated ? 1 : 0) < 0) {
        return -1;
    }
    if (capture->data != NULL && capture->len > 0 &&
        buffer_append(out, capture->data, capture->len) < 0) {
        return -1;
    }
    if (out->len == 0 || out->data[out->len - 1] != '\n') {
        if (append_literal(out, "\n") < 0) {
            return -1;
        }
    }
    return append_format(out,
                         "A90_EXECNS_VNDSERVICE_QUERY_%s_%s_END bytes=%zu truncated=%d\n",
                         label,
                         stream,
                         capture->len,
                         capture->truncated ? 1 : 0);
}

static int append_vndservice_query(struct buffer *stdout_buf,
                                   struct buffer *stderr_buf,
                                   const struct config *cfg,
                                   const struct paths *paths,
                                   const char *phase,
                                   int timeout_ms) {
    char vndservice_host_path[MAX_PATH_LEN];
    struct buffer query_stdout;
    struct buffer query_stderr;
    int stdout_pipe[2] = {-1, -1};
    int stderr_pipe[2] = {-1, -1};
    pid_t pid;
    pid_t pgid;
    bool stdout_open = false;
    bool stderr_open = false;
    bool child_done = false;
    bool timed_out = false;
    int exit_code = -1;
    int signal_no = 0;
    long deadline;
    int rc = 0;

    memset(&query_stdout, 0, sizeof(query_stdout));
    memset(&query_stderr, 0, sizeof(query_stderr));
    if (buffer_init(&query_stdout) < 0 || buffer_init(&query_stderr) < 0) {
        if (query_stdout.data != NULL) {
            buffer_free(&query_stdout);
        }
        if (query_stderr.data != NULL) {
            buffer_free(&query_stderr);
        }
        return -1;
    }
    if (append_path(vndservice_host_path, sizeof(vndservice_host_path), paths->root, "vendor/bin/vndservice") < 0) {
        rc = append_format(stdout_buf,
                           "wifi_vndservice_query.%s.result=manual-review-required\n"
                           "wifi_vndservice_query.%s.reason=vndservice-path-too-long\n",
                           phase,
                           phase);
        goto out;
    }
    if (append_format(stdout_buf,
                      "wifi_vndservice_query.%s.begin=1\n"
                      "wifi_vndservice_query.%s.tool=/vendor/bin/vndservice\n"
                      "wifi_vndservice_query.%s.argv=/vendor/bin/vndservice list\n"
                      "wifi_vndservice_query.%s.host_path=%s\n"
                      "wifi_vndservice_query.%s.exists=%d\n"
                      "wifi_vndservice_query.%s.executable=%d\n"
                      "wifi_vndservice_query.%s.scan_connect_linkup=0\n"
                      "wifi_vndservice_query.%s.credentials=0\n"
                      "wifi_vndservice_query.%s.dhcp_routing=0\n"
                      "wifi_vndservice_query.%s.external_ping=0\n",
                      phase,
                      phase,
                      phase,
                      phase,
                      vndservice_host_path,
                      phase,
                      access(vndservice_host_path, F_OK) == 0 ? 1 : 0,
                      phase,
                      access(vndservice_host_path, X_OK) == 0 ? 1 : 0,
                      phase,
                      phase,
                      phase,
                      phase) < 0) {
        rc = -1;
        goto out;
    }
    if (access(vndservice_host_path, X_OK) < 0) {
        rc = append_format(stdout_buf,
                           "wifi_vndservice_query.%s.exec_attempted=0\n"
                           "wifi_vndservice_query.%s.result=query-tool-missing\n"
                           "wifi_vndservice_query.%s.reason=vendor-bin-vndservice-unavailable-%s\n"
                           "wifi_vndservice_query.%s.end=1\n",
                           phase,
                           phase,
                           phase,
                           strerror(errno),
                           phase);
        goto out;
    }
    if (pipe2(stdout_pipe, O_CLOEXEC) < 0 || pipe2(stderr_pipe, O_CLOEXEC) < 0) {
        rc = append_format(stdout_buf,
                           "wifi_vndservice_query.%s.result=manual-review-required\n"
                           "wifi_vndservice_query.%s.reason=pipe-failed-%s\n"
                           "wifi_vndservice_query.%s.end=1\n",
                           phase,
                           phase,
                           strerror(errno),
                           phase);
        goto out;
    }
    pid = fork();
    if (pid < 0) {
        rc = append_format(stdout_buf,
                           "wifi_vndservice_query.%s.result=manual-review-required\n"
                           "wifi_vndservice_query.%s.reason=fork-failed-%s\n"
                           "wifi_vndservice_query.%s.end=1\n",
                           phase,
                           phase,
                           strerror(errno),
                           phase);
        goto out;
    }
    if (pid == 0) {
        char *const vndservice_argv[] = {
            (char *)"/vendor/bin/vndservice",
            (char *)"list",
            NULL,
        };

        close(stdout_pipe[0]);
        close(stderr_pipe[0]);
        dup2(stdout_pipe[1], STDOUT_FILENO);
        dup2(stderr_pipe[1], STDERR_FILENO);
        close(stdout_pipe[1]);
        close(stderr_pipe[1]);
        if (setsid() < 0) {
            perror("setsid");
            _exit(123);
        }
        if (chroot(paths->root) < 0) {
            perror("chroot");
            _exit(120);
        }
        if (chdir("/") < 0) {
            perror("chdir");
            _exit(121);
        }
        apply_child_env(cfg);
        printf("wifi_vndservice_query.%s.child.begin=1\n", phase);
        if (apply_service_manager_identity_contract("wifi_vndservice_query.child") < 0) {
            printf("wifi_vndservice_query.%s.child.end=1\n", phase);
            fflush(stdout);
            _exit(126);
        }
        printf("wifi_vndservice_query.%s.child.exec_target=/vendor/bin/vndservice\n", phase);
        printf("wifi_vndservice_query.%s.child.argv.1=list\n", phase);
        fflush(stdout);
        execv("/vendor/bin/vndservice", vndservice_argv);
        printf("wifi_vndservice_query.%s.child.exec_error=%s\n", phase, strerror(errno));
        printf("wifi_vndservice_query.%s.child.end=1\n", phase);
        fflush(stdout);
        _exit(127);
    }
    close(stdout_pipe[1]);
    close(stderr_pipe[1]);
    stdout_pipe[1] = -1;
    stderr_pipe[1] = -1;
    stdout_open = true;
    stderr_open = true;
    set_nonblock(stdout_pipe[0]);
    set_nonblock(stderr_pipe[0]);
    pgid = wait_for_child_session_pgid(pid, 1000);
    if (append_format(stdout_buf,
                      "wifi_vndservice_query.%s.exec_attempted=1\n"
                      "wifi_vndservice_query.%s.child_started=1\n"
                      "wifi_vndservice_query.%s.pid=%ld\n"
                      "wifi_vndservice_query.%s.pgid=%ld\n",
                      phase,
                      phase,
                      phase,
                      (long)pid,
                      phase,
                      (long)pgid) < 0) {
        rc = -1;
        goto out;
    }

    deadline = monotonic_ms() + timeout_ms;
    while (stdout_open || stderr_open || !child_done) {
        struct pollfd fds[2];
        int nfds = 0;

        if (!child_done && monotonic_ms() >= deadline) {
            timed_out = true;
            if (pgid > 1) {
                kill(-pgid, SIGTERM);
            }
            kill(pid, SIGTERM);
        }
        if (stdout_open) {
            fds[nfds].fd = stdout_pipe[0];
            fds[nfds].events = POLLIN | POLLHUP | POLLERR;
            nfds++;
        }
        if (stderr_open) {
            fds[nfds].fd = stderr_pipe[0];
            fds[nfds].events = POLLIN | POLLHUP | POLLERR;
            nfds++;
        }
        if (nfds > 0) {
            int poll_rc = poll(fds, nfds, 50);

            if (poll_rc > 0) {
                int idx = 0;

                if (stdout_open) {
                    if (fds[idx].revents != 0) {
                        drain_fd(stdout_pipe[0], &query_stdout, &stdout_open);
                    }
                    idx++;
                }
                if (stderr_open && fds[idx].revents != 0) {
                    drain_fd(stderr_pipe[0], &query_stderr, &stderr_open);
                }
            }
        } else {
            usleep(50000);
        }
        if (!child_done) {
            int status = 0;
            pid_t wait_rc = waitpid(pid, &status, WNOHANG);

            if (wait_rc == pid) {
                child_done = true;
                if (WIFEXITED(status)) {
                    exit_code = WEXITSTATUS(status);
                } else if (WIFSIGNALED(status)) {
                    signal_no = WTERMSIG(status);
                }
            } else if (wait_rc < 0 && errno != EINTR) {
                if (errno == ECHILD) {
                    child_done = true;
                } else {
                    append_format(stdout_buf,
                                  "wifi_vndservice_query.%s.wait.error=%s\n",
                                  phase,
                                  strerror(errno));
                    child_done = true;
                }
            }
        }
        if (timed_out && !child_done && monotonic_ms() >= deadline + 1000L) {
            if (pgid > 1) {
                kill(-pgid, SIGKILL);
            }
            kill(pid, SIGKILL);
        }
    }
    if (append_named_buffer_capture(stdout_buf, phase, "STDOUT", &query_stdout) < 0 ||
        append_named_buffer_capture(stderr_buf, phase, "STDERR", &query_stderr) < 0) {
        rc = -1;
        goto out;
    }
    if (append_format(stdout_buf,
                      "wifi_vndservice_query.%s.exit_code=%d\n"
                      "wifi_vndservice_query.%s.signal=%d\n"
                      "wifi_vndservice_query.%s.timed_out=%d\n"
                      "wifi_vndservice_query.%s.stdout_bytes=%zu\n"
                      "wifi_vndservice_query.%s.stderr_bytes=%zu\n"
                      "wifi_vndservice_query.%s.vendor_qcom_peripheral_manager_seen=%d\n"
                      "wifi_vndservice_query.%s.peripheral_seen=%d\n"
                      "wifi_vndservice_query.%s.result=%s\n"
                      "wifi_vndservice_query.%s.reason=%s\n"
                      "wifi_vndservice_query.%s.end=1\n",
                      phase,
                      exit_code,
                      phase,
                      signal_no,
                      phase,
                      timed_out ? 1 : 0,
                      phase,
                      query_stdout.len,
                      phase,
                      query_stderr.len,
                      phase,
                      strcasestr(query_stdout.data, "vendor.qcom.PeripheralManager") != NULL ? 1 : 0,
                      phase,
                      strcasestr(query_stdout.data, "peripheral") != NULL ? 1 : 0,
                      phase,
                      timed_out ? "query-timeout" : (exit_code == 0 && signal_no == 0 ? "query-exit-zero" : "query-runtime-gap"),
                      phase,
                      timed_out ? "vndservice-timeout" : (exit_code == 0 && signal_no == 0 ? "vndservice-list-exit-zero" : "vndservice-list-nonzero"),
                      phase) < 0) {
        rc = -1;
        goto out;
    }

out:
    if (stdout_pipe[0] >= 0) close(stdout_pipe[0]);
    if (stdout_pipe[1] >= 0) close(stdout_pipe[1]);
    if (stderr_pipe[0] >= 0) close(stderr_pipe[0]);
    if (stderr_pipe[1] >= 0) close(stderr_pipe[1]);
    buffer_free(&query_stdout);
    buffer_free(&query_stderr);
    return rc;
}

static void composite_capture_observable_children(struct composite_child *children,
                                                  size_t child_count,
                                                  struct buffer *stdout_buf) {
    for (size_t i = 0; i < child_count; i++) {
        char label[96];

        if (children[i].child_done || children[i].pid <= 0 || kill(children[i].pid, 0) < 0) {
            continue;
        }
        children[i].observable = true;
        snprintf(label, sizeof(label), "wifi_hal_composite_%s", children[i].name);
        append_proc_file_capture(stdout_buf,
                                 children[i].pid,
                                 "status",
                                 8192,
                                 &children[i].proc_status_captured);
        append_proc_file_capture_named(stdout_buf,
                                       children[i].pid,
                                       "attr/current",
                                       "attr_current",
                                       4096,
                                       &children[i].proc_attr_current_captured);
        append_proc_fd_summary(stdout_buf, children[i].pid, &children[i].fd_summary_captured);
        append_proc_fd_links_compact(stdout_buf, children[i].pid, label);
        if (strcmp(children[i].name, "cnss_daemon") == 0 ||
            strcmp(children[i].name, "cnss_daemon_retry") == 0) {
            children[i].stall_snapshot_captured =
                append_cnss_stall_snapshot_capture(stdout_buf, children[i].pid, label) == 0;
        }
        append_proc_file_capture(stdout_buf,
                                 children[i].pid,
                                 "maps",
                                 32768,
                                 &children[i].maps_summary_captured);
        append_format(stdout_buf,
                      "wifi_hal_composite_start.child.%s.capture_label=%s\n",
                      children[i].name,
                      label);
    }
}

static void composite_cleanup_children(struct composite_child *children,
                                       size_t child_count,
                                       struct buffer *stdout_buf,
                                       struct buffer *stderr_buf) {
    long deadline;

    for (size_t i = 0; i < child_count; i++) {
        if (children[i].child_done || children[i].pgid <= 1) {
            continue;
        }
        if (kill(-children[i].pgid, SIGTERM) == 0 || errno == ESRCH) {
            children[i].term_sent = true;
        }
    }
    deadline = monotonic_ms() + 1000L;
    while (monotonic_ms() < deadline) {
        bool any_running = false;

        for (size_t i = 0; i < child_count; i++) {
            int status = 0;
            pid_t wait_rc;

            if (children[i].child_done || children[i].pid <= 0) {
                continue;
            }
            any_running = true;
            wait_rc = waitpid(children[i].pid, &status, WNOHANG);
            if (wait_rc == children[i].pid) {
                children[i].child_done = true;
                children[i].reaped = true;
                if (WIFEXITED(status)) {
                    children[i].exit_code = WEXITSTATUS(status);
                } else if (WIFSIGNALED(status)) {
                    children[i].signal = WTERMSIG(status);
                } else if (WIFSTOPPED(status) && children[i].traced) {
                    int sig = WSTOPSIG(status);

                    children[i].child_done = false;
                    children[i].reaped = false;
                    children[i].trace_cleanup_stop_continued++;
                    children[i].trace_cleanup_stop_last_signal = sig;
                    if (ptrace(PTRACE_CONT, children[i].pid, NULL, (void *)(long)SIGTERM) < 0) {
                        children[i].trace_cleanup_continue_errors++;
                    }
                }
            }
        }
        if (!any_running) {
            break;
        }
        usleep(50000);
    }
    for (size_t i = 0; i < child_count; i++) {
        if (children[i].child_done || children[i].pgid <= 1) {
            continue;
        }
        if (kill(-children[i].pgid, SIGKILL) == 0 || errno == ESRCH) {
            children[i].kill_sent = true;
        }
    }
    deadline = monotonic_ms() + 1000L;
    while (monotonic_ms() < deadline) {
        bool any_running = false;

        for (size_t i = 0; i < child_count; i++) {
            int status = 0;
            pid_t wait_rc;

            if (children[i].child_done || children[i].pid <= 0) {
                continue;
            }
            any_running = true;
            wait_rc = waitpid(children[i].pid, &status, WNOHANG);
            if (wait_rc == children[i].pid) {
                children[i].child_done = true;
                children[i].reaped = true;
                if (WIFEXITED(status)) {
                    children[i].exit_code = WEXITSTATUS(status);
                } else if (WIFSIGNALED(status)) {
                    children[i].signal = WTERMSIG(status);
                } else if (WIFSTOPPED(status) && children[i].traced) {
                    int sig = WSTOPSIG(status);

                    children[i].child_done = false;
                    children[i].reaped = false;
                    children[i].trace_cleanup_stop_continued++;
                    children[i].trace_cleanup_stop_last_signal = sig;
                    if (ptrace(PTRACE_CONT, children[i].pid, NULL, (void *)(long)SIGKILL) < 0) {
                        children[i].trace_cleanup_continue_errors++;
                    }
                }
            }
        }
        if (!any_running) {
            break;
        }
        usleep(50000);
    }
    for (size_t i = 0; i < child_count; i++) {
        if (children[i].stdout_open && children[i].stdout_fd >= 0) {
            drain_fd(children[i].stdout_fd, stdout_buf, &children[i].stdout_open);
        }
        if (children[i].stderr_open && children[i].stderr_fd >= 0) {
            drain_fd(children[i].stderr_fd, stderr_buf, &children[i].stderr_open);
        }
        composite_close_child_fds(&children[i]);
    }
}

static bool composite_child_postflight_safe(const struct composite_child *child) {
    if (!child->reaped) {
        return false;
    }
    if (child->pgid > 1 && (kill(-child->pgid, 0) == 0 || errno != ESRCH)) {
        return false;
    }
    return true;
}

static bool composite_child_runtime_gap(const struct composite_child *child, bool timed_out) {
    if (timed_out && child->observable && child->term_sent && !child->exited_before_timeout) {
        if (child->signal == SIGTERM ||
            (child->signal == SIGKILL && child->kill_sent) ||
            child->exit_code == 0 ||
            (child->exit_code < 0 && child->signal == 0)) {
            return false;
        }
    }
    return child->exited_before_timeout || child->exit_code >= 0 || child->signal != 0;
}

static const char *qrtr_ctrl_cmd_name(uint32_t cmd) {
    switch (cmd) {
    case QRTR_TYPE_DATA:
        return "data";
    case QRTR_TYPE_HELLO:
        return "hello";
    case QRTR_TYPE_BYE:
        return "bye";
    case QRTR_TYPE_NEW_SERVER:
        return "new-server";
    case QRTR_TYPE_DEL_SERVER:
        return "del-server";
    case QRTR_TYPE_DEL_CLIENT:
        return "del-client";
    case QRTR_TYPE_RESUME_TX:
        return "resume-tx";
    case QRTR_TYPE_EXIT:
        return "exit";
    case QRTR_TYPE_PING:
        return "ping";
    case QRTR_TYPE_NEW_LOOKUP:
        return "new-lookup";
    case QRTR_TYPE_DEL_LOOKUP:
        return "del-lookup";
    default:
        return "unknown";
    }
}

static int open_qrtr_dgram_socket(void) {
    int fd = socket(AF_QIPCRTR, SOCK_DGRAM | SOCK_CLOEXEC, 0);

    if (fd >= 0) {
        return fd;
    }
    if (errno == EINVAL) {
        fd = socket(AF_QIPCRTR, SOCK_DGRAM, 0);
        if (fd >= 0) {
            int flags = fcntl(fd, F_GETFD);

            if (flags >= 0) {
                (void)fcntl(fd, F_SETFD, flags | FD_CLOEXEC);
            }
        }
    }
    return fd;
}

static int append_qrtr_sockaddr(struct buffer *buf,
                                const char *prefix,
                                const struct sockaddr_qrtr *addr) {
    return append_format(buf,
                         "%s.family=%u\n"
                         "%s.node=%u\n"
                         "%s.port=%u\n",
                         prefix,
                         (unsigned int)addr->sq_family,
                         prefix,
                         addr->sq_node,
                         prefix,
                         addr->sq_port);
}

static int append_qrtr_getname(struct buffer *buf,
                               int fd,
                               const char *prefix,
                               struct sockaddr_qrtr *out) {
    socklen_t len = sizeof(*out);

    memset(out, 0, sizeof(*out));
    if (getsockname(fd, (struct sockaddr *)out, &len) < 0) {
        int saved_errno = errno;

        return append_format(buf,
                             "%s.rc=-1\n"
                             "%s.errno=%d\n"
                             "%s.error=%s\n",
                             prefix,
                             prefix,
                             saved_errno,
                             prefix,
                             strerror(saved_errno));
    }
    if (append_format(buf, "%s.rc=0\n%s.len=%u\n", prefix, prefix, (unsigned int)len) < 0) {
        return -1;
    }
    return append_qrtr_sockaddr(buf, prefix, out);
}

static int append_qrtr_send_lookup_packet(struct buffer *buf,
                                          int fd,
                                          uint32_t cmd,
                                          uint32_t service,
                                          uint32_t instance,
                                          const char *prefix) {
    struct qrtr_ctrl_pkt packet;
    struct sockaddr_qrtr dest;
    ssize_t sent;

    memset(&packet, 0, sizeof(packet));
    packet.cmd = htole32(cmd);
    packet.server.service = htole32(service);
    packet.server.instance = htole32(instance);
    packet.server.node = 0;
    packet.server.port = 0;

    memset(&dest, 0, sizeof(dest));
    dest.sq_family = AF_QIPCRTR;
    dest.sq_node = QRTR_NODE_BCAST;
    dest.sq_port = QRTR_PORT_CTRL;

    sent = sendto(fd, &packet, sizeof(packet), 0, (const struct sockaddr *)&dest, sizeof(dest));
    if (sent < 0) {
        int saved_errno = errno;

        return append_format(buf,
                             "%s.rc=-1\n"
                             "%s.errno=%d\n"
                             "%s.error=%s\n",
                             prefix,
                             prefix,
                             saved_errno,
                             prefix,
                             strerror(saved_errno));
    }
    return append_format(buf,
                         "%s.rc=0\n"
                         "%s.bytes=%zd\n"
                         "%s.cmd=%u\n"
                         "%s.service=%u\n"
                         "%s.instance=%u\n",
                         prefix,
                         prefix,
                         sent,
                         prefix,
                         cmd,
                         prefix,
                         service,
                         prefix,
                         instance);
}

static int append_qrtr_readback_events(struct buffer *buf,
                                       int fd,
                                       uint32_t timeout_ms,
                                       uint32_t max_events,
                                       const char *prefix) {
    unsigned int events = 0;
    unsigned int new_server = 0;
    unsigned int del_server = 0;
    unsigned int service_events = 0;
    unsigned int empty_events = 0;
    unsigned int timeout = 0;
    unsigned int end_of_list = 0;
    long deadline = monotonic_ms() + (long)timeout_ms;

    if (append_format(buf,
                      "%s.rc=0\n"
                      "%s.timeout_ms=%u\n"
                      "%s.max_events=%u\n",
                      prefix,
                      prefix,
                      timeout_ms,
                      prefix,
                      max_events) < 0) {
        return -1;
    }

    while (events < max_events) {
        struct pollfd pfd;
        struct qrtr_ctrl_pkt packet;
        struct sockaddr_qrtr from;
        socklen_t from_len = sizeof(from);
        long now = monotonic_ms();
        int poll_rc;
        ssize_t received;
        uint32_t cmd;
        uint32_t service = 0;
        uint32_t instance = 0;
        uint32_t node = 0;
        uint32_t port = 0;
        bool empty = false;

        if (now >= deadline) {
            timeout = 1;
            break;
        }
        pfd.fd = fd;
        pfd.events = POLLIN;
        pfd.revents = 0;
        poll_rc = poll(&pfd, 1, (int)(deadline - now));
        if (poll_rc == 0) {
            timeout = 1;
            break;
        }
        if (poll_rc < 0) {
            if (errno == EINTR) {
                continue;
            }
            return append_format(buf,
                                 "%s.rc=-1\n"
                                 "%s.errno=%d\n"
                                 "%s.error=%s\n",
                                 prefix,
                                 prefix,
                                 errno,
                                 prefix,
                                 strerror(errno));
        }
        if ((pfd.revents & POLLIN) == 0) {
            if (append_format(buf, "%s.revents=%d\n", prefix, pfd.revents) < 0) {
                return -1;
            }
            continue;
        }
        memset(&packet, 0, sizeof(packet));
        memset(&from, 0, sizeof(from));
        received = recvfrom(fd, &packet, sizeof(packet), 0, (struct sockaddr *)&from, &from_len);
        if (received < 0) {
            if (errno == EINTR) {
                continue;
            }
            return append_format(buf,
                                 "%s.rc=-1\n"
                                 "%s.errno=%d\n"
                                 "%s.error=%s\n",
                                 prefix,
                                 prefix,
                                 errno,
                                 prefix,
                                 strerror(errno));
        }
        if (received < (ssize_t)sizeof(uint32_t)) {
            if (append_format(buf,
                              "%s.event.%u.bytes=%zd\n"
                              "%s.event.%u.type=short\n",
                              prefix,
                              events,
                              received,
                              prefix,
                              events) < 0) {
                return -1;
            }
            events++;
            continue;
        }
        cmd = le32toh(packet.cmd);
        if (received >= (ssize_t)sizeof(packet)) {
            service = le32toh(packet.server.service);
            instance = le32toh(packet.server.instance);
            node = le32toh(packet.server.node);
            port = le32toh(packet.server.port);
        }
        if (cmd == QRTR_TYPE_NEW_SERVER) {
            new_server++;
            empty = service == 0 && instance == 0 && node == 0 && port == 0;
            if (empty) {
                empty_events++;
            } else {
                service_events++;
            }
        } else if (cmd == QRTR_TYPE_DEL_SERVER) {
            del_server++;
        }
        if (append_format(buf,
                          "%s.event.%u.bytes=%zd\n"
                          "%s.event.%u.from.family=%u\n"
                          "%s.event.%u.from.node=%u\n"
                          "%s.event.%u.from.port=%u\n"
                          "%s.event.%u.cmd=%u\n"
                          "%s.event.%u.type=%s\n"
                          "%s.event.%u.service=%u\n"
                          "%s.event.%u.instance=%u\n"
                          "%s.event.%u.node=%u\n"
                          "%s.event.%u.port=%u\n"
                          "%s.event.%u.empty=%u\n",
                          prefix,
                          events,
                          received,
                          prefix,
                          events,
                          (unsigned int)from.sq_family,
                          prefix,
                          events,
                          from.sq_node,
                          prefix,
                          events,
                          from.sq_port,
                          prefix,
                          events,
                          cmd,
                          prefix,
                          events,
                          qrtr_ctrl_cmd_name(cmd),
                          prefix,
                          events,
                          service,
                          prefix,
                          events,
                          instance,
                          prefix,
                          events,
                          node,
                          prefix,
                          events,
                          port,
                          prefix,
                          events,
                          empty ? 1U : 0U) < 0) {
            return -1;
        }
        events++;
        if (empty) {
            end_of_list = 1;
            break;
        }
    }
    if (events >= max_events && !end_of_list) {
        timeout = 0;
    }
    return append_format(buf,
                         "%s.events=%u\n"
                         "%s.new_server=%u\n"
                         "%s.del_server=%u\n"
                         "%s.service_events=%u\n"
                         "%s.empty_events=%u\n"
                         "%s.end_of_list=%u\n"
                         "%s.timeout=%u\n",
                         prefix,
                         events,
                         prefix,
                         new_server,
                         prefix,
                         del_server,
                         prefix,
                         service_events,
                         prefix,
                         empty_events,
                         prefix,
                         end_of_list,
                         prefix,
                         timeout);
}

static int append_companion_qrtr_readback_case(struct buffer *buf,
                                               const char *prefix,
                                               const char *label,
                                               uint32_t service,
                                               uint32_t instance) {
    char socket_name_prefix[160];
    char new_lookup_prefix[160];
    char readback_prefix[160];
    char del_lookup_prefix[160];
    int fd;
    struct sockaddr_qrtr name;
    int new_lookup_rc = -1;

    if (snprintf(socket_name_prefix, sizeof(socket_name_prefix), "%s.socket_name", prefix) >= (int)sizeof(socket_name_prefix) ||
        snprintf(new_lookup_prefix, sizeof(new_lookup_prefix), "%s.new_lookup_send", prefix) >= (int)sizeof(new_lookup_prefix) ||
        snprintf(readback_prefix, sizeof(readback_prefix), "%s.readback", prefix) >= (int)sizeof(readback_prefix) ||
        snprintf(del_lookup_prefix, sizeof(del_lookup_prefix), "%s.del_lookup_send", prefix) >= (int)sizeof(del_lookup_prefix)) {
        return append_format(buf, "%s.error=prefix-too-long\n", prefix);
    }
    if (append_format(buf,
                      "%s.begin=1\n"
                      "%s.label=%s\n"
                      "%s.service=%u\n"
                      "%s.instance=%u\n"
                      "%s.qmi_attempted=0\n",
                      prefix,
                      prefix,
                      label,
                      prefix,
                      service,
                      prefix,
                      instance,
                      prefix) < 0) {
        return -1;
    }
    fd = open_qrtr_dgram_socket();
    if (fd < 0) {
        int saved_errno = errno;

        return append_format(buf,
                             "%s.socket.rc=-1\n"
                             "%s.socket.errno=%d\n"
                             "%s.socket.error=%s\n"
                             "%s.send_attempted=0\n"
                             "%s.status=socket-failed\n"
                             "%s.end=1\n",
                             prefix,
                             prefix,
                             saved_errno,
                             prefix,
                             strerror(saved_errno),
                             prefix,
                             prefix,
                             prefix);
    }
    if (append_format(buf, "%s.socket.rc=0\n%s.af=%d\n", prefix, prefix, AF_QIPCRTR) < 0 ||
        append_qrtr_getname(buf, fd, socket_name_prefix, &name) < 0 ||
        append_format(buf, "%s.send_attempted=1\n", prefix) < 0) {
        close(fd);
        return -1;
    }
    new_lookup_rc = append_qrtr_send_lookup_packet(buf,
                                                   fd,
                                                   QRTR_TYPE_NEW_LOOKUP,
                                                   service,
                                                   instance,
                                                   new_lookup_prefix);
    if (new_lookup_rc < 0) {
        close(fd);
        return -1;
    }
    if (append_qrtr_readback_events(buf,
                                    fd,
                                    1000U,
                                    8U,
                                    readback_prefix) < 0 ||
        append_qrtr_send_lookup_packet(buf,
                                       fd,
                                       QRTR_TYPE_DEL_LOOKUP,
                                       service,
                                       instance,
                                       del_lookup_prefix) < 0) {
        close(fd);
        return -1;
    }
    close(fd);
    return append_format(buf, "%s.status=complete\n%s.end=1\n", prefix, prefix);
}

struct qrtr_readback_case {
    char label[MAX_QRTR_READBACK_LABEL];
    uint32_t service;
    uint32_t instance;
};

static char *trim_token(char *value) {
    char *end;

    while (*value == ' ' || *value == '\t' || *value == '\r' || *value == '\n') {
        value++;
    }
    end = value + strlen(value);
    while (end > value &&
           (end[-1] == ' ' || end[-1] == '\t' || end[-1] == '\r' || end[-1] == '\n')) {
        *--end = '\0';
    }
    return value;
}

static void sanitize_qrtr_label(char *dst, size_t dst_len, const char *src) {
    size_t out = 0;

    if (dst_len == 0) {
        return;
    }
    while (*src != '\0' && out + 1 < dst_len) {
        unsigned char ch = (unsigned char)*src++;

        if ((ch >= 'A' && ch <= 'Z') ||
            (ch >= 'a' && ch <= 'z') ||
            (ch >= '0' && ch <= '9') ||
            ch == '_' || ch == '-') {
            dst[out++] = (char)ch;
        } else {
            dst[out++] = '_';
        }
    }
    dst[out] = '\0';
    if (out == 0) {
        strlcpy(dst, "case", dst_len);
    }
}

static bool parse_u32_token(const char *text, uint32_t *out) {
    char *end = NULL;
    unsigned long value;

    if (text == NULL || *text == '\0') {
        return false;
    }
    errno = 0;
    value = strtoul(text, &end, 0);
    if (errno != 0 || end == text || *trim_token(end) != '\0' || value > UINT32_MAX) {
        return false;
    }
    *out = (uint32_t)value;
    return true;
}

static int parse_qrtr_readback_matrix(const char *matrix,
                                      struct qrtr_readback_case *cases,
                                      size_t max_cases,
                                      char *error,
                                      size_t error_len) {
    char *copy;
    char *group;
    char *group_save = NULL;
    size_t count = 0;

    if (matrix == NULL || *matrix == '\0') {
        snprintf(error, error_len, "empty-matrix");
        return -1;
    }
    copy = strdup(matrix);
    if (copy == NULL) {
        snprintf(error, error_len, "oom");
        return -1;
    }
    for (group = strtok_r(copy, ";", &group_save);
         group != NULL;
         group = strtok_r(NULL, ";", &group_save)) {
        char *parts[3];
        char *part_save = NULL;
        char *inst;
        char *inst_save = NULL;
        uint32_t service = 0;
        size_t part_count = 0;

        group = trim_token(group);
        if (*group == '\0') {
            continue;
        }
        for (char *part = strtok_r(group, ":", &part_save);
             part != NULL && part_count < 3;
             part = strtok_r(NULL, ":", &part_save)) {
            parts[part_count++] = trim_token(part);
        }
        if (part_count != 3 || !parse_u32_token(parts[1], &service)) {
            snprintf(error, error_len, "invalid-group");
            free(copy);
            return -1;
        }
        for (inst = strtok_r(parts[2], ",", &inst_save);
             inst != NULL;
             inst = strtok_r(NULL, ",", &inst_save)) {
            uint32_t instance = 0;

            if (count >= max_cases) {
                snprintf(error, error_len, "too-many-cases");
                free(copy);
                return -1;
            }
            inst = trim_token(inst);
            if (!parse_u32_token(inst, &instance)) {
                snprintf(error, error_len, "invalid-instance");
                free(copy);
                return -1;
            }
            sanitize_qrtr_label(cases[count].label, sizeof(cases[count].label), parts[0]);
            cases[count].service = service;
            cases[count].instance = instance;
            count++;
        }
    }
    free(copy);
    if (count == 0) {
        snprintf(error, error_len, "empty-matrix");
        return -1;
    }
    return (int)count;
}

static int append_companion_qrtr_wlfw_readback(struct buffer *buf,
                                               const struct config *cfg) {
    struct qrtr_readback_case cases[MAX_QRTR_READBACK_CASES];
    char parse_error[64] = "";
    int case_count = 0;

    if (append_format(buf,
                      "wifi_companion_qrtr_readback.begin=1\n"
                      "wifi_companion_qrtr_readback.allowed=%d\n"
                      "wifi_companion_qrtr_readback.matrix=%s\n"
                      "wifi_companion_qrtr_readback.new_lookup=%u\n"
                      "wifi_companion_qrtr_readback.del_lookup=%u\n"
                      "wifi_companion_qrtr_readback.readback_ms=1000\n"
                      "wifi_companion_qrtr_readback.max_events=8\n"
                      "wifi_companion_qrtr_readback.qmi_payload=0\n"
                      "wifi_companion_qrtr_readback.wifi_hal=0\n"
                      "wifi_companion_qrtr_readback.scan_connect_linkup=0\n"
                      "wifi_companion_qrtr_readback.external_ping=0\n",
                      cfg->allow_qrtr_ns_readback ? 1 : 0,
                      cfg->qrtr_readback_matrix != NULL ? cfg->qrtr_readback_matrix : DEFAULT_QRTR_READBACK_MATRIX,
                      QRTR_TYPE_NEW_LOOKUP,
                      QRTR_TYPE_DEL_LOOKUP) < 0) {
        return -1;
    }
    if (!cfg->allow_qrtr_ns_readback) {
        return append_literal(buf,
                              "wifi_companion_qrtr_readback.send_attempted=0\n"
                              "wifi_companion_qrtr_readback.result=blocked\n"
                              "wifi_companion_qrtr_readback.reason=missing-allow-qrtr-ns-readback\n"
                              "wifi_companion_qrtr_readback.end=1\n");
    }
    case_count = parse_qrtr_readback_matrix(
        cfg->qrtr_readback_matrix != NULL ? cfg->qrtr_readback_matrix : DEFAULT_QRTR_READBACK_MATRIX,
        cases,
        MAX_QRTR_READBACK_CASES,
        parse_error,
        sizeof(parse_error));
    if (case_count < 0) {
        return append_format(buf,
                             "wifi_companion_qrtr_readback.send_attempted=0\n"
                             "wifi_companion_qrtr_readback.result=invalid-matrix\n"
                             "wifi_companion_qrtr_readback.reason=%s\n"
                             "wifi_companion_qrtr_readback.end=1\n",
                             parse_error);
    }
    if (append_format(buf, "wifi_companion_qrtr_readback.case_count=%d\n", case_count) < 0) {
        return -1;
    }
    for (int i = 0; i < case_count; i++) {
        char prefix[96];

        if (snprintf(prefix, sizeof(prefix), "wifi_companion_qrtr_readback.case_%d", i) >= (int)sizeof(prefix)) {
            return -1;
        }
        if (append_companion_qrtr_readback_case(buf,
                                                prefix,
                                                cases[i].label,
                                                cases[i].service,
                                                cases[i].instance) < 0) {
            return -1;
        }
    }
    return append_literal(buf,
                          "wifi_companion_qrtr_readback.send_attempted=1\n"
                          "wifi_companion_qrtr_readback.result=complete\n"
                          "wifi_companion_qrtr_readback.end=1\n");
}

struct qrtr_service_endpoint {
    bool found;
    uint32_t node;
    uint32_t port;
    unsigned int events;
    unsigned int timeout;
};

static uint16_t read_le16_bytes(const uint8_t *data) {
    uint16_t value = 0;

    memcpy(&value, data, sizeof(value));
    return le16toh(value);
}

static uint32_t read_le32_bytes(const uint8_t *data) {
    uint32_t value = 0;

    memcpy(&value, data, sizeof(value));
    return le32toh(value);
}

static int append_hex_bytes(struct buffer *buf,
                            const char *key,
                            const uint8_t *data,
                            size_t len) {
    if (append_format(buf, "%s=", key) < 0) {
        return -1;
    }
    for (size_t i = 0; i < len; i++) {
        if (append_format(buf, "%02x", data[i]) < 0) {
            return -1;
        }
    }
    return append_literal(buf, "\n");
}

static int append_servloc_domain_entry(struct buffer *buf,
                                       const char *prefix,
                                       unsigned int index,
                                       const uint8_t *data,
                                       size_t len,
                                       size_t *offset,
                                       unsigned int *wlan_like) {
    uint8_t name_len;
    const uint8_t *name;
    uint32_t instance_id;
    uint8_t service_data_valid;
    uint32_t service_data;
    bool contains_wlan = false;

    if (*offset >= len) {
        return append_format(buf, "%s.domain.%u.status=truncated-before-name-len\n", prefix, index);
    }
    name_len = data[(*offset)++];
    if (*offset + (size_t)name_len + 9U > len) {
        return append_format(buf,
                             "%s.domain.%u.name_len=%u\n"
                             "%s.domain.%u.status=truncated-entry\n",
                             prefix,
                             index,
                             (unsigned int)name_len,
                             prefix,
                             index);
    }
    name = data + *offset;
    for (uint8_t i = 0; i < name_len; i++) {
        if (i + 3U < name_len &&
            name[i] == 'w' &&
            name[i + 1U] == 'l' &&
            name[i + 2U] == 'a' &&
            name[i + 3U] == 'n') {
            contains_wlan = true;
        }
    }
    *offset += name_len;
    instance_id = read_le32_bytes(data + *offset);
    *offset += sizeof(uint32_t);
    service_data_valid = data[(*offset)++];
    service_data = read_le32_bytes(data + *offset);
    *offset += sizeof(uint32_t);
    if (contains_wlan) {
        (*wlan_like)++;
    }
    if (append_format(buf,
                      "%s.domain.%u.name_len=%u\n"
                      "%s.domain.%u.name=",
                      prefix,
                      index,
                      (unsigned int)name_len,
                      prefix,
                      index) < 0 ||
        append_escaped_ascii(buf, name, name_len) < 0 ||
        append_format(buf,
                      "\n"
                      "%s.domain.%u.instance_id=%u\n"
                      "%s.domain.%u.service_data_valid=%u\n"
                      "%s.domain.%u.service_data=%u\n"
                      "%s.domain.%u.contains_wlan=%u\n"
                      "%s.domain.%u.status=parsed\n",
                      prefix,
                      index,
                      instance_id,
                      prefix,
                      index,
                      (unsigned int)service_data_valid,
                      prefix,
                      index,
                      service_data,
                      prefix,
                      index,
                      contains_wlan ? 1U : 0U,
                      prefix,
                      index) < 0) {
        return -1;
    }
    return 0;
}

static int parse_servloc_domain_response(struct buffer *buf,
                                         const char *prefix,
                                         const uint8_t *packet,
                                         size_t received,
                                         bool *success_out,
                                         unsigned int *domain_count_out,
                                         unsigned int *wlan_like_out) {
    uint8_t message_type;
    uint16_t txn_id;
    uint16_t msg_id;
    uint16_t msg_len;
    size_t end;
    size_t offset = 7;
    unsigned int tlv_count = 0;
    unsigned int total_domains_valid = 0;
    unsigned int db_rev_count_valid = 0;
    unsigned int domain_list_valid = 0;
    unsigned int result_valid = 0;
    uint16_t result = 0xffffU;
    uint16_t error = 0xffffU;
    uint16_t total_domains = 0;
    uint16_t db_rev_count = 0;
    unsigned int domain_count = 0;
    unsigned int wlan_like = 0;

    *success_out = false;
    *domain_count_out = 0;
    *wlan_like_out = 0;
    if (received < 7U) {
        return append_format(buf,
                             "%s.response_parse=short-header\n"
                             "%s.response_bytes=%zu\n",
                             prefix,
                             prefix,
                             received);
    }
    message_type = packet[0];
    txn_id = read_le16_bytes(packet + 1);
    msg_id = read_le16_bytes(packet + 3);
    msg_len = read_le16_bytes(packet + 5);
    end = 7U + (size_t)msg_len;
    if (end > received) {
        end = received;
    }
    if (append_format(buf,
                      "%s.response.type=%u\n"
                      "%s.response.txn_id=%u\n"
                      "%s.response.msg_id=%u\n"
                      "%s.response.msg_len=%u\n"
                      "%s.response.body_available=%zu\n",
                      prefix,
                      (unsigned int)message_type,
                      prefix,
                      (unsigned int)txn_id,
                      prefix,
                      (unsigned int)msg_id,
                      prefix,
                      (unsigned int)msg_len,
                      prefix,
                      end > 7U ? end - 7U : 0U) < 0) {
        return -1;
    }
    while (offset + 3U <= end) {
        uint8_t tlv_type = packet[offset++];
        uint16_t tlv_len = read_le16_bytes(packet + offset);
        const uint8_t *tlv_data;
        char tlv_key[128];

        offset += sizeof(uint16_t);
        if (offset + (size_t)tlv_len > end) {
            if (append_format(buf,
                              "%s.tlv.%u.type=0x%02x\n"
                              "%s.tlv.%u.len=%u\n"
                              "%s.tlv.%u.status=truncated\n",
                              prefix,
                              tlv_count,
                              (unsigned int)tlv_type,
                              prefix,
                              tlv_count,
                              (unsigned int)tlv_len,
                              prefix,
                              tlv_count) < 0) {
                return -1;
            }
            break;
        }
        tlv_data = packet + offset;
        if (append_format(buf,
                          "%s.tlv.%u.type=0x%02x\n"
                          "%s.tlv.%u.len=%u\n"
                          "%s.tlv.%u.status=parsed\n",
                          prefix,
                          tlv_count,
                          (unsigned int)tlv_type,
                          prefix,
                          tlv_count,
                          (unsigned int)tlv_len,
                          prefix,
                          tlv_count) < 0) {
            return -1;
        }
        if (snprintf(tlv_key, sizeof(tlv_key), "%s.tlv.%u.hex", prefix, tlv_count) >= (int)sizeof(tlv_key) ||
            append_hex_bytes(buf, tlv_key, tlv_data, tlv_len) < 0) {
            return -1;
        }
        if (tlv_type == 0x02U && tlv_len >= 4U) {
            result = read_le16_bytes(tlv_data);
            error = read_le16_bytes(tlv_data + 2);
            result_valid = 1;
        } else if (tlv_type == 0x10U && tlv_len >= 2U) {
            total_domains = read_le16_bytes(tlv_data);
            total_domains_valid = 1;
        } else if (tlv_type == 0x11U && tlv_len >= 2U) {
            db_rev_count = read_le16_bytes(tlv_data);
            db_rev_count_valid = 1;
        } else if (tlv_type == 0x12U && tlv_len >= 1U) {
            size_t domain_offset = 1;
            uint8_t wire_count = tlv_data[0];

            domain_list_valid = 1;
            domain_count = wire_count;
            if (append_format(buf,
                              "%s.domain_list.wire_count=%u\n",
                              prefix,
                              (unsigned int)wire_count) < 0) {
                return -1;
            }
            for (unsigned int i = 0; i < (unsigned int)wire_count && i < 32U; i++) {
                if (append_servloc_domain_entry(buf,
                                                prefix,
                                                i,
                                                tlv_data,
                                                tlv_len,
                                                &domain_offset,
                                                &wlan_like) < 0) {
                    return -1;
                }
                if (domain_offset >= tlv_len) {
                    break;
                }
            }
            if (append_format(buf,
                              "%s.domain_list.bytes_consumed=%zu\n",
                              prefix,
                              domain_offset) < 0) {
                return -1;
            }
        }
        offset += tlv_len;
        tlv_count++;
    }
    *success_out = message_type == 2U &&
                   msg_id == A90_SERVLOC_GET_DOMAIN_LIST_MSG_ID &&
                   txn_id == A90_SERVLOC_TXN_ID &&
                   result_valid &&
                   result == 0U;
    *domain_count_out = domain_count;
    *wlan_like_out = wlan_like;
    return append_format(buf,
                         "%s.response_parse=complete\n"
                         "%s.tlv_count=%u\n"
                         "%s.qmi_result_valid=%u\n"
                         "%s.qmi_result=%u\n"
                         "%s.qmi_error=%u\n"
                         "%s.total_domains_valid=%u\n"
                         "%s.total_domains=%u\n"
                         "%s.db_rev_count_valid=%u\n"
                         "%s.db_rev_count=%u\n"
                         "%s.domain_list_valid=%u\n"
                         "%s.domain_count=%u\n"
                         "%s.wlan_like_domains=%u\n"
                         "%s.success=%u\n",
                         prefix,
                         prefix,
                         tlv_count,
                         prefix,
                         result_valid,
                         prefix,
                         (unsigned int)result,
                         prefix,
                         (unsigned int)error,
                         prefix,
                         total_domains_valid,
                         prefix,
                         (unsigned int)total_domains,
                         prefix,
                         db_rev_count_valid,
                         prefix,
                         (unsigned int)db_rev_count,
                         prefix,
                         domain_list_valid,
                         prefix,
                         domain_count,
                         prefix,
                         wlan_like,
                         prefix,
                         *success_out ? 1U : 0U);
}

static int servloc_find_endpoint(struct buffer *buf,
                                 const char *prefix,
                                 struct qrtr_service_endpoint *endpoint) {
    int fd;
    long deadline;
    char socket_name_prefix[160];
    char lookup_prefix[160];
    char del_prefix[160];

    memset(endpoint, 0, sizeof(*endpoint));
    if (snprintf(socket_name_prefix, sizeof(socket_name_prefix), "%s.socket_name", prefix) >= (int)sizeof(socket_name_prefix) ||
        snprintf(lookup_prefix, sizeof(lookup_prefix), "%s.lookup_send", prefix) >= (int)sizeof(lookup_prefix) ||
        snprintf(del_prefix, sizeof(del_prefix), "%s.del_lookup_send", prefix) >= (int)sizeof(del_prefix)) {
        return append_format(buf, "%s.status=prefix-too-long\n", prefix);
    }
    fd = open_qrtr_dgram_socket();
    if (fd < 0) {
        int saved_errno = errno;

        return append_format(buf,
                             "%s.socket.rc=-1\n"
                             "%s.socket.errno=%d\n"
                             "%s.socket.error=%s\n"
                             "%s.status=socket-failed\n",
                             prefix,
                             prefix,
                             saved_errno,
                             prefix,
                             strerror(saved_errno),
                             prefix);
    }
    if (append_format(buf, "%s.socket.rc=0\n%s.af=%d\n", prefix, prefix, AF_QIPCRTR) < 0 ||
        append_qrtr_getname(buf, fd, socket_name_prefix, &(struct sockaddr_qrtr){0}) < 0 ||
        append_qrtr_send_lookup_packet(buf,
                                       fd,
                                       QRTR_TYPE_NEW_LOOKUP,
                                       A90_SERVLOC_SERVICE,
                                       A90_SERVLOC_INSTANCE_ENCODED,
                                       lookup_prefix) < 0) {
        close(fd);
        return -1;
    }
    deadline = monotonic_ms() + (long)A90_SERVLOC_READBACK_MS;
    while (endpoint->events < 8U) {
        struct pollfd pfd;
        struct qrtr_ctrl_pkt packet;
        struct sockaddr_qrtr from;
        socklen_t from_len = sizeof(from);
        long now = monotonic_ms();
        int poll_rc;
        ssize_t received;
        uint32_t cmd;
        uint32_t service = 0;
        uint32_t instance = 0;
        uint32_t node = 0;
        uint32_t port = 0;
        bool empty = false;

        if (now >= deadline) {
            endpoint->timeout = 1;
            break;
        }
        pfd.fd = fd;
        pfd.events = POLLIN;
        pfd.revents = 0;
        poll_rc = poll(&pfd, 1, (int)(deadline - now));
        if (poll_rc == 0) {
            endpoint->timeout = 1;
            break;
        }
        if (poll_rc < 0) {
            if (errno == EINTR) {
                continue;
            }
            append_qrtr_send_lookup_packet(buf,
                                           fd,
                                           QRTR_TYPE_DEL_LOOKUP,
                                           A90_SERVLOC_SERVICE,
                                           A90_SERVLOC_INSTANCE_ENCODED,
                                           del_prefix);
            close(fd);
            return append_format(buf,
                                 "%s.readback.rc=-1\n"
                                 "%s.readback.errno=%d\n"
                                 "%s.readback.error=%s\n",
                                 prefix,
                                 prefix,
                                 errno,
                                 prefix,
                                 strerror(errno));
        }
        if ((pfd.revents & POLLIN) == 0) {
            if (append_format(buf, "%s.readback.revents=%d\n", prefix, pfd.revents) < 0) {
                close(fd);
                return -1;
            }
            if ((pfd.revents & (POLLERR | POLLHUP | POLLNVAL)) != 0) {
                break;
            }
            continue;
        }
        memset(&packet, 0, sizeof(packet));
        memset(&from, 0, sizeof(from));
        received = recvfrom(fd, &packet, sizeof(packet), 0, (struct sockaddr *)&from, &from_len);
        if (received < 0) {
            if (errno == EINTR) {
                continue;
            }
            append_qrtr_send_lookup_packet(buf,
                                           fd,
                                           QRTR_TYPE_DEL_LOOKUP,
                                           A90_SERVLOC_SERVICE,
                                           A90_SERVLOC_INSTANCE_ENCODED,
                                           del_prefix);
            close(fd);
            return append_format(buf,
                                 "%s.readback.rc=-1\n"
                                 "%s.readback.errno=%d\n"
                                 "%s.readback.error=%s\n",
                                 prefix,
                                 prefix,
                                 errno,
                                 prefix,
                                 strerror(errno));
        }
        cmd = received >= (ssize_t)sizeof(uint32_t) ? le32toh(packet.cmd) : 0U;
        if (received >= (ssize_t)sizeof(packet)) {
            service = le32toh(packet.server.service);
            instance = le32toh(packet.server.instance);
            node = le32toh(packet.server.node);
            port = le32toh(packet.server.port);
        }
        empty = cmd == QRTR_TYPE_NEW_SERVER && service == 0U && instance == 0U && node == 0U && port == 0U;
        if (append_format(buf,
                          "%s.event.%u.bytes=%zd\n"
                          "%s.event.%u.from.node=%u\n"
                          "%s.event.%u.from.port=%u\n"
                          "%s.event.%u.cmd=%u\n"
                          "%s.event.%u.type=%s\n"
                          "%s.event.%u.service=%u\n"
                          "%s.event.%u.instance=%u\n"
                          "%s.event.%u.node=%u\n"
                          "%s.event.%u.port=%u\n"
                          "%s.event.%u.empty=%u\n",
                          prefix,
                          endpoint->events,
                          received,
                          prefix,
                          endpoint->events,
                          from.sq_node,
                          prefix,
                          endpoint->events,
                          from.sq_port,
                          prefix,
                          endpoint->events,
                          cmd,
                          prefix,
                          endpoint->events,
                          qrtr_ctrl_cmd_name(cmd),
                          prefix,
                          endpoint->events,
                          service,
                          prefix,
                          endpoint->events,
                          instance,
                          prefix,
                          endpoint->events,
                          node,
                          prefix,
                          endpoint->events,
                          port,
                          prefix,
                          endpoint->events,
                          empty ? 1U : 0U) < 0) {
            close(fd);
            return -1;
        }
        endpoint->events++;
        if (cmd == QRTR_TYPE_NEW_SERVER &&
            service == A90_SERVLOC_SERVICE &&
            instance == A90_SERVLOC_INSTANCE_ENCODED &&
            node != 0U &&
            port != 0U) {
            endpoint->found = true;
            endpoint->node = node;
            endpoint->port = port;
            break;
        }
        if (empty) {
            break;
        }
    }
    if (append_qrtr_send_lookup_packet(buf,
                                       fd,
                                       QRTR_TYPE_DEL_LOOKUP,
                                       A90_SERVLOC_SERVICE,
                                       A90_SERVLOC_INSTANCE_ENCODED,
                                       del_prefix) < 0) {
        close(fd);
        return -1;
    }
    close(fd);
    return append_format(buf,
                         "%s.readback.events=%u\n"
                         "%s.readback.timeout=%u\n"
                         "%s.found=%u\n"
                         "%s.node=%u\n"
                         "%s.port=%u\n"
                         "%s.status=%s\n",
                         prefix,
                         endpoint->events,
                         prefix,
                         endpoint->timeout,
                         prefix,
                         endpoint->found ? 1U : 0U,
                         prefix,
                         endpoint->node,
                         prefix,
                         endpoint->port,
                         prefix,
                         endpoint->found ? "found" : "not-found");
}

static int append_companion_servloc_domain_list_probe(struct buffer *buf,
                                                      const struct config *cfg) {
    static const uint8_t request[] = {
        0x00, 0x01, 0x00, 0x21, 0x00, 0x11, 0x00,
        0x01, 0x07, 0x00, 0x77, 0x6c, 0x61, 0x6e, 0x2f, 0x66, 0x77,
        0x10, 0x04, 0x00, 0x00, 0x00, 0x00, 0x00,
    };
    struct qrtr_service_endpoint endpoint;
    int fd;
    struct sockaddr_qrtr dest;
    ssize_t sent;
    long deadline;
    unsigned int packets = 0;
    bool response_seen = false;
    bool response_success = false;
    unsigned int domain_count = 0;
    unsigned int wlan_like = 0;

    if (append_format(buf,
                      "wifi_companion_servloc_domain_list.begin=1\n"
                      "wifi_companion_servloc_domain_list.allowed=%d\n"
                      "wifi_companion_servloc_domain_list.service=%u\n"
                      "wifi_companion_servloc_domain_list.instance=%u\n"
                      "wifi_companion_servloc_domain_list.service_name=wlan/fw\n"
                      "wifi_companion_servloc_domain_list.qmi_payload=%d\n"
                      "wifi_companion_servloc_domain_list.wifi_hal=0\n"
                      "wifi_companion_servloc_domain_list.scan_connect_linkup=0\n"
                      "wifi_companion_servloc_domain_list.credentials=0\n"
                      "wifi_companion_servloc_domain_list.dhcp_routing=0\n"
                      "wifi_companion_servloc_domain_list.external_ping=0\n",
                      cfg->allow_servloc_domain_list_probe ? 1 : 0,
                      A90_SERVLOC_SERVICE,
                      A90_SERVLOC_INSTANCE_ENCODED,
                      cfg->allow_servloc_domain_list_probe ? 1 : 0) < 0 ||
        append_hex_bytes(buf,
                         "wifi_companion_servloc_domain_list.request_hex",
                         request,
                         sizeof(request)) < 0) {
        return -1;
    }
    if (!cfg->allow_servloc_domain_list_probe) {
        return append_literal(buf,
                              "wifi_companion_servloc_domain_list.send_attempted=0\n"
                              "wifi_companion_servloc_domain_list.result=blocked\n"
                              "wifi_companion_servloc_domain_list.reason=missing-allow-servloc-domain-list-probe\n"
                              "wifi_companion_servloc_domain_list.end=1\n");
    }
    if (servloc_find_endpoint(buf, "wifi_companion_servloc_domain_list.endpoint", &endpoint) < 0) {
        return -1;
    }
    if (!endpoint.found) {
        return append_literal(buf,
                              "wifi_companion_servloc_domain_list.send_attempted=0\n"
                              "wifi_companion_servloc_domain_list.result=no-endpoint\n"
                              "wifi_companion_servloc_domain_list.end=1\n");
    }
    fd = open_qrtr_dgram_socket();
    if (fd < 0) {
        int saved_errno = errno;

        return append_format(buf,
                             "wifi_companion_servloc_domain_list.socket.rc=-1\n"
                             "wifi_companion_servloc_domain_list.socket.errno=%d\n"
                             "wifi_companion_servloc_domain_list.socket.error=%s\n"
                             "wifi_companion_servloc_domain_list.send_attempted=0\n"
                             "wifi_companion_servloc_domain_list.result=socket-failed\n"
                             "wifi_companion_servloc_domain_list.end=1\n",
                             saved_errno,
                             strerror(saved_errno));
    }
    memset(&dest, 0, sizeof(dest));
    dest.sq_family = AF_QIPCRTR;
    dest.sq_node = endpoint.node;
    dest.sq_port = endpoint.port;
    sent = sendto(fd, request, sizeof(request), 0, (const struct sockaddr *)&dest, sizeof(dest));
    if (sent < 0) {
        int saved_errno = errno;

        close(fd);
        return append_format(buf,
                             "wifi_companion_servloc_domain_list.socket.rc=0\n"
                             "wifi_companion_servloc_domain_list.send_attempted=1\n"
                             "wifi_companion_servloc_domain_list.send.rc=-1\n"
                             "wifi_companion_servloc_domain_list.send.errno=%d\n"
                             "wifi_companion_servloc_domain_list.send.error=%s\n"
                             "wifi_companion_servloc_domain_list.result=send-failed\n"
                             "wifi_companion_servloc_domain_list.end=1\n",
                             saved_errno,
                             strerror(saved_errno));
    }
    if (append_format(buf,
                      "wifi_companion_servloc_domain_list.socket.rc=0\n"
                      "wifi_companion_servloc_domain_list.send_attempted=1\n"
                      "wifi_companion_servloc_domain_list.send.rc=0\n"
                      "wifi_companion_servloc_domain_list.send.bytes=%zd\n"
                      "wifi_companion_servloc_domain_list.send.node=%u\n"
                      "wifi_companion_servloc_domain_list.send.port=%u\n",
                      sent,
                      endpoint.node,
                      endpoint.port) < 0) {
        close(fd);
        return -1;
    }
    deadline = monotonic_ms() + (long)A90_SERVLOC_RESPONSE_MS;
    while (packets < 8U) {
        struct pollfd pfd;
        struct sockaddr_qrtr from;
        socklen_t from_len = sizeof(from);
        uint8_t packet[4096];
        long now = monotonic_ms();
        int poll_rc;
        ssize_t received;
        char packet_hex_key[128];
        uint8_t response_type = 0;
        uint16_t response_txn = 0;
        uint16_t response_msg = 0;

        if (now >= deadline) {
            break;
        }
        pfd.fd = fd;
        pfd.events = POLLIN;
        pfd.revents = 0;
        poll_rc = poll(&pfd, 1, (int)(deadline - now));
        if (poll_rc == 0) {
            break;
        }
        if (poll_rc < 0) {
            if (errno == EINTR) {
                continue;
            }
            close(fd);
            return append_format(buf,
                                 "wifi_companion_servloc_domain_list.response.errno=%d\n"
                                 "wifi_companion_servloc_domain_list.response.error=%s\n"
                                 "wifi_companion_servloc_domain_list.result=response-poll-failed\n"
                                 "wifi_companion_servloc_domain_list.end=1\n",
                                 errno,
                                 strerror(errno));
        }
        memset(&from, 0, sizeof(from));
        received = recvfrom(fd, packet, sizeof(packet), 0, (struct sockaddr *)&from, &from_len);
        if (received < 0) {
            if (errno == EINTR) {
                continue;
            }
            close(fd);
            return append_format(buf,
                                 "wifi_companion_servloc_domain_list.response.errno=%d\n"
                                 "wifi_companion_servloc_domain_list.response.error=%s\n"
                                 "wifi_companion_servloc_domain_list.result=response-recv-failed\n"
                                 "wifi_companion_servloc_domain_list.end=1\n",
                                 errno,
                                 strerror(errno));
        }
        if (received >= 7) {
            response_type = packet[0];
            response_txn = read_le16_bytes(packet + 1);
            response_msg = read_le16_bytes(packet + 3);
        }
        if (append_format(buf,
                          "wifi_companion_servloc_domain_list.packet.%u.bytes=%zd\n"
                          "wifi_companion_servloc_domain_list.packet.%u.from.node=%u\n"
                          "wifi_companion_servloc_domain_list.packet.%u.from.port=%u\n"
                          "wifi_companion_servloc_domain_list.packet.%u.type=%u\n"
                          "wifi_companion_servloc_domain_list.packet.%u.txn_id=%u\n"
                          "wifi_companion_servloc_domain_list.packet.%u.msg_id=%u\n",
                          packets,
                          received,
                          packets,
                          from.sq_node,
                          packets,
                          from.sq_port,
                          packets,
                          (unsigned int)response_type,
                          packets,
                          (unsigned int)response_txn,
                          packets,
                          (unsigned int)response_msg) < 0) {
            close(fd);
            return -1;
        }
        if (snprintf(packet_hex_key,
                     sizeof(packet_hex_key),
                     "wifi_companion_servloc_domain_list.packet.%u.hex",
                     packets) >= (int)sizeof(packet_hex_key) ||
            append_hex_bytes(buf, packet_hex_key, packet, (size_t)received) < 0) {
            close(fd);
            return -1;
        }
        if (response_type == 2U &&
            response_txn == A90_SERVLOC_TXN_ID &&
            response_msg == A90_SERVLOC_GET_DOMAIN_LIST_MSG_ID) {
            response_seen = true;
            if (parse_servloc_domain_response(buf,
                                              "wifi_companion_servloc_domain_list",
                                              packet,
                                              (size_t)received,
                                              &response_success,
                                              &domain_count,
                                              &wlan_like) < 0) {
                close(fd);
                return -1;
            }
            break;
        }
        packets++;
    }
    close(fd);
    return append_format(buf,
                         "wifi_companion_servloc_domain_list.response_seen=%u\n"
                         "wifi_companion_servloc_domain_list.response_success=%u\n"
                         "wifi_companion_servloc_domain_list.domain_count=%u\n"
                         "wifi_companion_servloc_domain_list.wlan_like_domains=%u\n"
                         "wifi_companion_servloc_domain_list.result=%s\n"
                         "wifi_companion_servloc_domain_list.end=1\n",
                         response_seen ? 1U : 0U,
                         response_success ? 1U : 0U,
                         domain_count,
                         wlan_like,
                         response_seen ? (response_success ? "domain-list-response-success" : "domain-list-response-error") : "no-response");
}

static const char *servnotif_state_name(uint32_t state) {
    switch (state) {
    case 0x0fffffffu:
        return "down";
    case 0x1fffffffu:
        return "up";
    case 0x2fffffffu:
        return "early-down";
    case 0x7fffffffu:
        return "uninit";
    default:
        return "unknown";
    }
}

static int servnotif_find_endpoint(struct buffer *buf,
                                   const char *prefix,
                                   struct qrtr_service_endpoint *endpoint,
                                   bool wait_through_empty) {
    int fd;
    long deadline;
    char socket_name_prefix[160];
    char lookup_prefix[160];
    char del_prefix[160];

    memset(endpoint, 0, sizeof(*endpoint));
    if (snprintf(socket_name_prefix, sizeof(socket_name_prefix), "%s.socket_name", prefix) >= (int)sizeof(socket_name_prefix) ||
        snprintf(lookup_prefix, sizeof(lookup_prefix), "%s.lookup_send", prefix) >= (int)sizeof(lookup_prefix) ||
        snprintf(del_prefix, sizeof(del_prefix), "%s.del_lookup_send", prefix) >= (int)sizeof(del_prefix)) {
        return append_format(buf, "%s.status=prefix-too-long\n", prefix);
    }
    fd = open_qrtr_dgram_socket();
    if (fd < 0) {
        int saved_errno = errno;

        return append_format(buf,
                             "%s.socket.rc=-1\n"
                             "%s.socket.errno=%d\n"
                             "%s.socket.error=%s\n"
                             "%s.status=socket-failed\n",
                             prefix,
                             prefix,
                             saved_errno,
                             prefix,
                             strerror(saved_errno),
                             prefix);
    }
    if (append_format(buf, "%s.socket.rc=0\n%s.af=%d\n", prefix, prefix, AF_QIPCRTR) < 0 ||
        append_qrtr_getname(buf, fd, socket_name_prefix, &(struct sockaddr_qrtr){0}) < 0 ||
        append_qrtr_send_lookup_packet(buf,
                                       fd,
                                       QRTR_TYPE_NEW_LOOKUP,
                                       A90_SERVNOTIF_SERVICE,
                                       A90_SERVNOTIF_INSTANCE_ENCODED,
                                       lookup_prefix) < 0) {
        close(fd);
        return -1;
    }
    deadline = monotonic_ms() + (long)A90_SERVNOTIF_READBACK_MS;
    while (endpoint->events < 8U) {
        struct pollfd pfd;
        struct qrtr_ctrl_pkt packet;
        struct sockaddr_qrtr from;
        socklen_t from_len = sizeof(from);
        long now = monotonic_ms();
        int poll_rc;
        ssize_t received;
        uint32_t cmd;
        uint32_t service = 0;
        uint32_t instance = 0;
        uint32_t node = 0;
        uint32_t port = 0;
        bool empty = false;

        if (now >= deadline) {
            endpoint->timeout = 1;
            break;
        }
        pfd.fd = fd;
        pfd.events = POLLIN;
        pfd.revents = 0;
        poll_rc = poll(&pfd, 1, (int)(deadline - now));
        if (poll_rc == 0) {
            endpoint->timeout = 1;
            break;
        }
        if (poll_rc < 0) {
            if (errno == EINTR) {
                continue;
            }
            append_qrtr_send_lookup_packet(buf,
                                           fd,
                                           QRTR_TYPE_DEL_LOOKUP,
                                           A90_SERVNOTIF_SERVICE,
                                           A90_SERVNOTIF_INSTANCE_ENCODED,
                                           del_prefix);
            close(fd);
            return append_format(buf,
                                 "%s.readback.rc=-1\n"
                                 "%s.readback.errno=%d\n"
                                 "%s.readback.error=%s\n",
                                 prefix,
                                 prefix,
                                 errno,
                                 prefix,
                                 strerror(errno));
        }
        if ((pfd.revents & POLLIN) == 0) {
            if (append_format(buf, "%s.readback.revents=%d\n", prefix, pfd.revents) < 0) {
                close(fd);
                return -1;
            }
            if ((pfd.revents & (POLLERR | POLLHUP | POLLNVAL)) != 0) {
                break;
            }
            continue;
        }
        memset(&packet, 0, sizeof(packet));
        memset(&from, 0, sizeof(from));
        received = recvfrom(fd, &packet, sizeof(packet), 0, (struct sockaddr *)&from, &from_len);
        if (received < 0) {
            if (errno == EINTR) {
                continue;
            }
            append_qrtr_send_lookup_packet(buf,
                                           fd,
                                           QRTR_TYPE_DEL_LOOKUP,
                                           A90_SERVNOTIF_SERVICE,
                                           A90_SERVNOTIF_INSTANCE_ENCODED,
                                           del_prefix);
            close(fd);
            return append_format(buf,
                                 "%s.readback.rc=-1\n"
                                 "%s.readback.errno=%d\n"
                                 "%s.readback.error=%s\n",
                                 prefix,
                                 prefix,
                                 errno,
                                 prefix,
                                 strerror(errno));
        }
        cmd = received >= (ssize_t)sizeof(uint32_t) ? le32toh(packet.cmd) : 0U;
        if (received >= (ssize_t)sizeof(packet)) {
            service = le32toh(packet.server.service);
            instance = le32toh(packet.server.instance);
            node = le32toh(packet.server.node);
            port = le32toh(packet.server.port);
        }
        empty = cmd == QRTR_TYPE_NEW_SERVER && service == 0U && instance == 0U && node == 0U && port == 0U;
        if (append_format(buf,
                          "%s.event.%u.bytes=%zd\n"
                          "%s.event.%u.from.node=%u\n"
                          "%s.event.%u.from.port=%u\n"
                          "%s.event.%u.cmd=%u\n"
                          "%s.event.%u.type=%s\n"
                          "%s.event.%u.service=%u\n"
                          "%s.event.%u.instance=%u\n"
                          "%s.event.%u.node=%u\n"
                          "%s.event.%u.port=%u\n"
                          "%s.event.%u.empty=%u\n",
                          prefix,
                          endpoint->events,
                          received,
                          prefix,
                          endpoint->events,
                          from.sq_node,
                          prefix,
                          endpoint->events,
                          from.sq_port,
                          prefix,
                          endpoint->events,
                          cmd,
                          prefix,
                          endpoint->events,
                          qrtr_ctrl_cmd_name(cmd),
                          prefix,
                          endpoint->events,
                          service,
                          prefix,
                          endpoint->events,
                          instance,
                          prefix,
                          endpoint->events,
                          node,
                          prefix,
                          endpoint->events,
                          port,
                          prefix,
                          endpoint->events,
                          empty ? 1U : 0U) < 0) {
            close(fd);
            return -1;
        }
        endpoint->events++;
        if (cmd == QRTR_TYPE_NEW_SERVER &&
            service == A90_SERVNOTIF_SERVICE &&
            instance == A90_SERVNOTIF_INSTANCE_ENCODED &&
            port != 0U) {
            endpoint->found = true;
            endpoint->node = node;
            endpoint->port = port;
            break;
        }
        if (empty && !wait_through_empty) {
            break;
        }
    }
    if (append_qrtr_send_lookup_packet(buf,
                                       fd,
                                       QRTR_TYPE_DEL_LOOKUP,
                                       A90_SERVNOTIF_SERVICE,
                                       A90_SERVNOTIF_INSTANCE_ENCODED,
                                       del_prefix) < 0) {
        close(fd);
        return -1;
    }
    close(fd);
    return append_format(buf,
                         "%s.readback.events=%u\n"
                         "%s.readback.timeout=%u\n"
                         "%s.found=%u\n"
                         "%s.node=%u\n"
                         "%s.port=%u\n"
                         "%s.status=%s\n",
                         prefix,
                         endpoint->events,
                         prefix,
                         endpoint->timeout,
                         prefix,
                         endpoint->found ? 1U : 0U,
                         prefix,
                         endpoint->node,
                         prefix,
                         endpoint->port,
                         prefix,
                         endpoint->found ? "found" : "not-found");
}

static int servnotif_find_endpoint_with_retries(struct buffer *buf,
                                                const char *prefix,
                                                struct qrtr_service_endpoint *endpoint,
                                                bool retry_until_deadline) {
    long deadline;
    unsigned int attempts = 0;

    if (!retry_until_deadline) {
        return servnotif_find_endpoint(buf, prefix, endpoint, false);
    }
    deadline = monotonic_ms() + (long)A90_SERVNOTIF_READBACK_MS;
    memset(endpoint, 0, sizeof(*endpoint));
    while (monotonic_ms() < deadline && attempts < 96U) {
        struct qrtr_service_endpoint attempt_endpoint;
        char attempt_prefix[192];

        if (snprintf(attempt_prefix,
                     sizeof(attempt_prefix),
                     "%s.attempt.%u",
                     prefix,
                     attempts) >= (int)sizeof(attempt_prefix)) {
            return append_format(buf, "%s.status=attempt-prefix-too-long\n", prefix);
        }
        if (servnotif_find_endpoint(buf, attempt_prefix, &attempt_endpoint, false) < 0) {
            return -1;
        }
        attempts++;
        if (attempt_endpoint.found) {
            *endpoint = attempt_endpoint;
            break;
        }
        usleep(100000);
    }
    return append_format(buf,
                         "%s.wait_attempts=%u\n"
                         "%s.found=%u\n"
                         "%s.node=%u\n"
                         "%s.port=%u\n"
                         "%s.status=%s\n",
                         prefix,
                         attempts,
                         prefix,
                         endpoint->found ? 1U : 0U,
                         prefix,
                         endpoint->node,
                         prefix,
                         endpoint->port,
                         prefix,
                         endpoint->found ? "found" : "not-found");
}

static void build_servnotif_register_request(uint8_t *request,
                                             size_t *request_len,
                                             uint16_t txn_id,
                                             uint8_t enable) {
    const char service_name[] = A90_WLAN_PD_SERVICE_NAME;
    size_t name_len = sizeof(service_name) - 1U;
    size_t payload_len = 4U + 3U + name_len;
    size_t offset = 0;

    request[offset++] = 0x00;
    request[offset++] = (uint8_t)(txn_id & 0xffU);
    request[offset++] = (uint8_t)((txn_id >> 8) & 0xffU);
    request[offset++] = (uint8_t)(A90_SERVNOTIF_REGISTER_LISTENER_MSG_ID & 0xffU);
    request[offset++] = (uint8_t)((A90_SERVNOTIF_REGISTER_LISTENER_MSG_ID >> 8) & 0xffU);
    request[offset++] = (uint8_t)(payload_len & 0xffU);
    request[offset++] = (uint8_t)((payload_len >> 8) & 0xffU);
    request[offset++] = 0x01;
    request[offset++] = 0x01;
    request[offset++] = 0x00;
    request[offset++] = enable;
    request[offset++] = 0x02;
    request[offset++] = (uint8_t)(name_len & 0xffU);
    request[offset++] = (uint8_t)((name_len >> 8) & 0xffU);
    memcpy(request + offset, service_name, name_len);
    offset += name_len;
    *request_len = offset;
}

static void build_servnotif_ack_request(uint8_t *request,
                                        size_t *request_len,
                                        uint16_t txn_id,
                                        uint16_t indication_txn) {
    const char service_name[] = A90_WLAN_PD_SERVICE_NAME;
    size_t name_len = sizeof(service_name) - 1U;
    size_t payload_len = 3U + name_len + 5U;
    size_t offset = 0;

    request[offset++] = 0x00;
    request[offset++] = (uint8_t)(txn_id & 0xffU);
    request[offset++] = (uint8_t)((txn_id >> 8) & 0xffU);
    request[offset++] = (uint8_t)(A90_SERVNOTIF_ACK_MSG_ID & 0xffU);
    request[offset++] = (uint8_t)((A90_SERVNOTIF_ACK_MSG_ID >> 8) & 0xffU);
    request[offset++] = (uint8_t)(payload_len & 0xffU);
    request[offset++] = (uint8_t)((payload_len >> 8) & 0xffU);
    request[offset++] = 0x01;
    request[offset++] = (uint8_t)(name_len & 0xffU);
    request[offset++] = (uint8_t)((name_len >> 8) & 0xffU);
    memcpy(request + offset, service_name, name_len);
    offset += name_len;
    request[offset++] = 0x02;
    request[offset++] = 0x02;
    request[offset++] = 0x00;
    request[offset++] = (uint8_t)(indication_txn & 0xffU);
    request[offset++] = (uint8_t)((indication_txn >> 8) & 0xffU);
    *request_len = offset;
}

static int parse_servnotif_register_response(struct buffer *buf,
                                             const char *prefix,
                                             const uint8_t *packet,
                                             size_t received,
                                             bool *success_out,
                                             bool *state_valid_out,
                                             uint32_t *state_out) {
    uint8_t message_type;
    uint16_t txn_id;
    uint16_t msg_id;
    uint16_t msg_len;
    size_t end;
    size_t offset = 7;
    unsigned int tlv_count = 0;
    unsigned int result_valid = 0;
    uint16_t result = 0xffffU;
    uint16_t error = 0xffffU;
    bool state_valid = false;
    uint32_t state = 0;

    *success_out = false;
    *state_valid_out = false;
    *state_out = 0;
    if (received < 7U) {
        return append_format(buf,
                             "%s.register_response_parse=short-header\n"
                             "%s.register_response_bytes=%zu\n",
                             prefix,
                             prefix,
                             received);
    }
    message_type = packet[0];
    txn_id = read_le16_bytes(packet + 1);
    msg_id = read_le16_bytes(packet + 3);
    msg_len = read_le16_bytes(packet + 5);
    end = 7U + (size_t)msg_len;
    if (end > received) {
        end = received;
    }
    if (append_format(buf,
                      "%s.register_response.type=%u\n"
                      "%s.register_response.txn_id=%u\n"
                      "%s.register_response.msg_id=%u\n"
                      "%s.register_response.msg_len=%u\n",
                      prefix,
                      (unsigned int)message_type,
                      prefix,
                      (unsigned int)txn_id,
                      prefix,
                      (unsigned int)msg_id,
                      prefix,
                      (unsigned int)msg_len) < 0) {
        return -1;
    }
    while (offset + 3U <= end) {
        uint8_t tlv_type = packet[offset++];
        uint16_t tlv_len = read_le16_bytes(packet + offset);
        const uint8_t *tlv_data;
        char tlv_key[128];

        offset += sizeof(uint16_t);
        if (offset + (size_t)tlv_len > end) {
            return append_format(buf,
                                 "%s.register_response.tlv.%u.type=0x%02x\n"
                                 "%s.register_response.tlv.%u.len=%u\n"
                                 "%s.register_response.tlv.%u.status=truncated\n",
                                 prefix,
                                 tlv_count,
                                 (unsigned int)tlv_type,
                                 prefix,
                                 tlv_count,
                                 (unsigned int)tlv_len,
                                 prefix,
                                 tlv_count);
        }
        tlv_data = packet + offset;
        if (append_format(buf,
                          "%s.register_response.tlv.%u.type=0x%02x\n"
                          "%s.register_response.tlv.%u.len=%u\n"
                          "%s.register_response.tlv.%u.status=parsed\n",
                          prefix,
                          tlv_count,
                          (unsigned int)tlv_type,
                          prefix,
                          tlv_count,
                          (unsigned int)tlv_len,
                          prefix,
                          tlv_count) < 0) {
            return -1;
        }
        if (snprintf(tlv_key, sizeof(tlv_key), "%s.register_response.tlv.%u.hex", prefix, tlv_count) >= (int)sizeof(tlv_key) ||
            append_hex_bytes(buf, tlv_key, tlv_data, tlv_len) < 0) {
            return -1;
        }
        if (tlv_type == 0x02U && tlv_len >= 4U) {
            result = read_le16_bytes(tlv_data);
            error = read_le16_bytes(tlv_data + 2);
            result_valid = 1;
        } else if (tlv_type == 0x10U && tlv_len >= 4U) {
            state = read_le32_bytes(tlv_data);
            state_valid = true;
        }
        offset += tlv_len;
        tlv_count++;
    }
    *success_out = message_type == 2U &&
                   msg_id == A90_SERVNOTIF_REGISTER_LISTENER_MSG_ID &&
                   txn_id == A90_SERVNOTIF_TXN_ID &&
                   result_valid &&
                   result == 0U;
    *state_valid_out = state_valid;
    *state_out = state;
    return append_format(buf,
                         "%s.register_response_parse=complete\n"
                         "%s.register_response.tlv_count=%u\n"
                         "%s.register_response.qmi_result_valid=%u\n"
                         "%s.register_response.qmi_result=%u\n"
                         "%s.register_response.qmi_error=%u\n"
                         "%s.register_response.curr_state_valid=%u\n"
                         "%s.register_response.curr_state=0x%08x\n"
                         "%s.register_response.curr_state_name=%s\n"
                         "%s.register_response.success=%u\n",
                         prefix,
                         prefix,
                         tlv_count,
                         prefix,
                         result_valid,
                         prefix,
                         (unsigned int)result,
                         prefix,
                         (unsigned int)error,
                         prefix,
                         state_valid ? 1U : 0U,
                         prefix,
                         state,
                         prefix,
                         servnotif_state_name(state),
                         prefix,
                         *success_out ? 1U : 0U);
}

static int parse_servnotif_indication(struct buffer *buf,
                                      const char *prefix,
                                      const uint8_t *packet,
                                      size_t received,
                                      bool *valid_out,
                                      uint16_t *indication_txn_out,
                                      uint32_t *state_out) {
    uint8_t message_type;
    uint16_t msg_id;
    uint16_t msg_len;
    size_t end;
    size_t offset = 7;
    bool state_valid = false;
    bool service_name_valid = false;
    bool txn_valid = false;
    uint32_t state = 0;
    uint16_t indication_txn = 0;

    *valid_out = false;
    *indication_txn_out = 0;
    *state_out = 0;
    if (received < 7U) {
        return append_format(buf, "%s.indication_parse=short-header\n", prefix);
    }
    message_type = packet[0];
    msg_id = read_le16_bytes(packet + 3);
    msg_len = read_le16_bytes(packet + 5);
    end = 7U + (size_t)msg_len;
    if (end > received) {
        end = received;
    }
    if (append_format(buf,
                      "%s.indication.type=%u\n"
                      "%s.indication.msg_id=%u\n"
                      "%s.indication.msg_len=%u\n",
                      prefix,
                      (unsigned int)message_type,
                      prefix,
                      (unsigned int)msg_id,
                      prefix,
                      (unsigned int)msg_len) < 0) {
        return -1;
    }
    while (offset + 3U <= end) {
        uint8_t tlv_type = packet[offset++];
        uint16_t tlv_len = read_le16_bytes(packet + offset);
        const uint8_t *tlv_data;

        offset += sizeof(uint16_t);
        if (offset + (size_t)tlv_len > end) {
            return append_format(buf,
                                 "%s.indication.tlv.type=0x%02x\n"
                                 "%s.indication.tlv.len=%u\n"
                                 "%s.indication.tlv.status=truncated\n",
                                 prefix,
                                 (unsigned int)tlv_type,
                                 prefix,
                                 (unsigned int)tlv_len,
                                 prefix);
        }
        tlv_data = packet + offset;
        if (tlv_type == 0x01U && tlv_len >= 4U) {
            state = read_le32_bytes(tlv_data);
            state_valid = true;
        } else if (tlv_type == 0x02U) {
            service_name_valid = true;
            if (append_format(buf, "%s.indication.service_name=", prefix) < 0 ||
                append_escaped_ascii(buf, tlv_data, tlv_len) < 0 ||
                append_literal(buf, "\n") < 0) {
                return -1;
            }
        } else if (tlv_type == 0x03U && tlv_len >= 2U) {
            indication_txn = read_le16_bytes(tlv_data);
            txn_valid = true;
        }
        offset += tlv_len;
    }
    *valid_out = message_type == 4U &&
                 msg_id == A90_SERVNOTIF_STATE_UPDATED_IND_MSG_ID &&
                 state_valid &&
                 service_name_valid &&
                 txn_valid;
    *indication_txn_out = indication_txn;
    *state_out = state;
    return append_format(buf,
                         "%s.indication_parse=complete\n"
                         "%s.indication.valid=%u\n"
                         "%s.indication.curr_state_valid=%u\n"
                         "%s.indication.curr_state=0x%08x\n"
                         "%s.indication.curr_state_name=%s\n"
                         "%s.indication.transaction_id_valid=%u\n"
                         "%s.indication.transaction_id=%u\n",
                         prefix,
                         prefix,
                         *valid_out ? 1U : 0U,
                         prefix,
                         state_valid ? 1U : 0U,
                         prefix,
                         state,
                         prefix,
                         servnotif_state_name(state),
                         prefix,
                         txn_valid ? 1U : 0U,
                         prefix,
                         (unsigned int)indication_txn);
}

static int parse_servnotif_ack_response(struct buffer *buf,
                                        const char *prefix,
                                        const uint8_t *packet,
                                        size_t received,
                                        bool *success_out) {
    uint8_t message_type;
    uint16_t txn_id;
    uint16_t msg_id;
    uint16_t msg_len;
    size_t end;
    size_t offset = 7;
    unsigned int result_valid = 0;
    uint16_t result = 0xffffU;
    uint16_t error = 0xffffU;

    *success_out = false;
    if (received < 7U) {
        return append_format(buf, "%s.ack_response_parse=short-header\n", prefix);
    }
    message_type = packet[0];
    txn_id = read_le16_bytes(packet + 1);
    msg_id = read_le16_bytes(packet + 3);
    msg_len = read_le16_bytes(packet + 5);
    end = 7U + (size_t)msg_len;
    if (end > received) {
        end = received;
    }
    while (offset + 3U <= end) {
        uint8_t tlv_type = packet[offset++];
        uint16_t tlv_len = read_le16_bytes(packet + offset);
        const uint8_t *tlv_data;

        offset += sizeof(uint16_t);
        if (offset + (size_t)tlv_len > end) {
            break;
        }
        tlv_data = packet + offset;
        if (tlv_type == 0x02U && tlv_len >= 4U) {
            result = read_le16_bytes(tlv_data);
            error = read_le16_bytes(tlv_data + 2);
            result_valid = 1;
        }
        offset += tlv_len;
    }
    *success_out = message_type == 2U &&
                   msg_id == A90_SERVNOTIF_ACK_MSG_ID &&
                   txn_id == A90_SERVNOTIF_ACK_TXN_ID &&
                   result_valid &&
                   result == 0U;
    return append_format(buf,
                         "%s.ack_response.type=%u\n"
                         "%s.ack_response.txn_id=%u\n"
                         "%s.ack_response.msg_id=%u\n"
                         "%s.ack_response.msg_len=%u\n"
                         "%s.ack_response.qmi_result_valid=%u\n"
                         "%s.ack_response.qmi_result=%u\n"
                         "%s.ack_response.qmi_error=%u\n"
                         "%s.ack_response.success=%u\n",
                         prefix,
                         (unsigned int)message_type,
                         prefix,
                         (unsigned int)txn_id,
                         prefix,
                         (unsigned int)msg_id,
                         prefix,
                         (unsigned int)msg_len,
                         prefix,
                         result_valid,
                         prefix,
                         (unsigned int)result,
                         prefix,
                         (unsigned int)error,
                         prefix,
                         *success_out ? 1U : 0U);
}

static int append_companion_service_notifier_listener_probe(struct buffer *buf,
                                                           const struct config *cfg) {
    struct qrtr_service_endpoint endpoint;
    uint8_t register_request[96];
    size_t register_request_len = 0;
    int fd;
    struct sockaddr_qrtr dest;
    ssize_t sent;
    long deadline;
    unsigned int packets = 0;
    bool response_seen = false;
    bool response_success = false;
    bool response_state_valid = false;
    uint32_t response_state = 0;
    bool indication_seen = false;
    bool indication_valid = false;
    uint16_t indication_txn = 0;
    uint32_t indication_state = 0;
    bool ack_sent = false;
    bool ack_success = false;
    bool response_poll_timeout = false;
    const long listener_begin_ms = monotonic_ms();
    long send_before_ms = 0;
    long send_after_ms = 0;
    long first_response_ms = 0;
    long first_indication_ms = 0;
    long close_ms = 0;

    build_servnotif_register_request(register_request,
                                     &register_request_len,
                                     A90_SERVNOTIF_TXN_ID,
                                     1U);
    if (append_format(buf,
                      "wifi_companion_service_notifier_listener.begin=1\n"
                      "wifi_companion_service_notifier_listener.allowed=%d\n"
                      "wifi_companion_service_notifier_listener.service=%u\n"
                      "wifi_companion_service_notifier_listener.instance=%u\n"
                      "wifi_companion_service_notifier_listener.service_name=%s\n"
                      "wifi_companion_service_notifier_listener.phase=early-window\n"
                      "wifi_companion_service_notifier_listener.qmi_payload=%d\n"
                      "wifi_companion_service_notifier_listener.wifi_hal=0\n"
                      "wifi_companion_service_notifier_listener.scan_connect_linkup=0\n"
                      "wifi_companion_service_notifier_listener.credentials=0\n"
                      "wifi_companion_service_notifier_listener.dhcp_routing=0\n"
                      "wifi_companion_service_notifier_listener.external_ping=0\n",
                      cfg->allow_service_notifier_listener_probe ? 1 : 0,
                      A90_SERVNOTIF_SERVICE,
                      A90_SERVNOTIF_INSTANCE_ENCODED,
                      A90_WLAN_PD_SERVICE_NAME,
                      cfg->allow_service_notifier_listener_probe ? 1 : 0) < 0 ||
        append_hex_bytes(buf,
                         "wifi_companion_service_notifier_listener.register_request_hex",
                         register_request,
                         register_request_len) < 0) {
        return -1;
    }
    if (!cfg->allow_service_notifier_listener_probe) {
        return append_literal(buf,
                              "wifi_companion_service_notifier_listener.send_attempted=0\n"
                              "wifi_companion_service_notifier_listener.result=blocked\n"
                              "wifi_companion_service_notifier_listener.reason=missing-allow-service-notifier-listener-probe\n"
                              "wifi_companion_service_notifier_listener.end=1\n");
    }
    if (servnotif_find_endpoint_with_retries(buf,
                                             "wifi_companion_service_notifier_listener.endpoint",
                                             &endpoint,
                                             is_service_notifier_listener_only_mode(cfg->mode)) < 0) {
        return -1;
    }
    if (!endpoint.found) {
        return append_literal(buf,
                              "wifi_companion_service_notifier_listener.send_attempted=0\n"
                              "wifi_companion_service_notifier_listener.result=no-endpoint\n"
                              "wifi_companion_service_notifier_listener.end=1\n");
    }
    fd = open_qrtr_dgram_socket();
    if (fd < 0) {
        int saved_errno = errno;

        return append_format(buf,
                             "wifi_companion_service_notifier_listener.socket.rc=-1\n"
                             "wifi_companion_service_notifier_listener.socket.errno=%d\n"
                             "wifi_companion_service_notifier_listener.socket.error=%s\n"
                             "wifi_companion_service_notifier_listener.send_attempted=0\n"
                             "wifi_companion_service_notifier_listener.result=socket-failed\n"
                             "wifi_companion_service_notifier_listener.end=1\n",
                             saved_errno,
                             strerror(saved_errno));
    }
    memset(&dest, 0, sizeof(dest));
    dest.sq_family = AF_QIPCRTR;
    dest.sq_node = endpoint.node;
    dest.sq_port = endpoint.port;
    send_before_ms = monotonic_ms();
    sent = sendto(fd, register_request, register_request_len, 0, (const struct sockaddr *)&dest, sizeof(dest));
    send_after_ms = monotonic_ms();
    if (sent < 0) {
        int saved_errno = errno;

        close(fd);
        return append_format(buf,
                             "wifi_companion_service_notifier_listener.socket.rc=0\n"
                             "wifi_companion_service_notifier_listener.send_attempted=1\n"
                             "wifi_companion_service_notifier_listener.register_send.rc=-1\n"
                             "wifi_companion_service_notifier_listener.register_send.errno=%d\n"
                             "wifi_companion_service_notifier_listener.register_send.error=%s\n"
                             "wifi_companion_service_notifier_listener.result=send-failed\n"
                             "wifi_companion_service_notifier_listener.end=1\n",
                             saved_errno,
                             strerror(saved_errno));
    }
    if (append_format(buf,
                      "wifi_companion_service_notifier_listener.socket.rc=0\n"
                      "wifi_companion_service_notifier_listener.send_attempted=1\n"
	                      "wifi_companion_service_notifier_listener.register_send.rc=0\n"
	                      "wifi_companion_service_notifier_listener.register_send.bytes=%zd\n"
	                      "wifi_companion_service_notifier_listener.register_send.node=%u\n"
	                      "wifi_companion_service_notifier_listener.register_send.port=%u\n"
	                      "wifi_companion_service_notifier_listener.timing.begin_ms=%ld\n"
	                      "wifi_companion_service_notifier_listener.timing.send_before_ms=%ld\n"
	                      "wifi_companion_service_notifier_listener.timing.send_after_ms=%ld\n"
	                      "wifi_companion_service_notifier_listener.timing.target_hold_ms=%u\n",
	                      sent,
	                      endpoint.node,
	                      endpoint.port,
	                      listener_begin_ms,
	                      send_before_ms,
	                      send_after_ms,
	                      A90_SERVNOTIF_RESPONSE_MS) < 0) {
        close(fd);
        return -1;
    }
    deadline = send_after_ms + (long)A90_SERVNOTIF_RESPONSE_MS;
    while (packets < 12U) {
        struct pollfd pfd;
        struct sockaddr_qrtr from;
        socklen_t from_len = sizeof(from);
        uint8_t packet[4096];
        long now = monotonic_ms();
        int poll_rc;
        ssize_t received;
        char packet_hex_key[128];
        uint8_t packet_type = 0;
        uint16_t packet_txn = 0;
        uint16_t packet_msg = 0;

        if (now >= deadline) {
            response_poll_timeout = true;
            break;
        }
        pfd.fd = fd;
        pfd.events = POLLIN;
        pfd.revents = 0;
        poll_rc = poll(&pfd, 1, (int)(deadline - now));
        if (poll_rc == 0) {
            response_poll_timeout = true;
            break;
        }
        if (poll_rc < 0) {
            if (errno == EINTR) {
                continue;
            }
            close(fd);
            return append_format(buf,
                                 "wifi_companion_service_notifier_listener.recv.errno=%d\n"
                                 "wifi_companion_service_notifier_listener.recv.error=%s\n"
                                 "wifi_companion_service_notifier_listener.result=response-poll-failed\n"
                                 "wifi_companion_service_notifier_listener.end=1\n",
                                 errno,
                                 strerror(errno));
        }
        memset(&from, 0, sizeof(from));
        received = recvfrom(fd, packet, sizeof(packet), 0, (struct sockaddr *)&from, &from_len);
        if (received < 0) {
            if (errno == EINTR) {
                continue;
            }
            close(fd);
            return append_format(buf,
                                 "wifi_companion_service_notifier_listener.recv.errno=%d\n"
                                 "wifi_companion_service_notifier_listener.recv.error=%s\n"
                                 "wifi_companion_service_notifier_listener.result=response-recv-failed\n"
                                 "wifi_companion_service_notifier_listener.end=1\n",
                                 errno,
                                 strerror(errno));
        }
        if (received >= 7) {
            packet_type = packet[0];
            packet_txn = read_le16_bytes(packet + 1);
            packet_msg = read_le16_bytes(packet + 3);
        }
        now = monotonic_ms();
        if (append_format(buf,
	                          "wifi_companion_service_notifier_listener.packet.%u.bytes=%zd\n"
	                          "wifi_companion_service_notifier_listener.packet.%u.from.node=%u\n"
	                          "wifi_companion_service_notifier_listener.packet.%u.from.port=%u\n"
	                          "wifi_companion_service_notifier_listener.packet.%u.type=%u\n"
	                          "wifi_companion_service_notifier_listener.packet.%u.txn_id=%u\n"
	                          "wifi_companion_service_notifier_listener.packet.%u.msg_id=%u\n"
	                          "wifi_companion_service_notifier_listener.packet.%u.recv_ms=%ld\n",
	                          packets,
	                          received,
	                          packets,
	                          from.sq_node,
                          packets,
                          from.sq_port,
                          packets,
                          (unsigned int)packet_type,
	                          packets,
	                          (unsigned int)packet_txn,
	                          packets,
	                          (unsigned int)packet_msg,
	                          packets,
	                          now) < 0) {
            close(fd);
            return -1;
        }
        if (snprintf(packet_hex_key,
                     sizeof(packet_hex_key),
                     "wifi_companion_service_notifier_listener.packet.%u.hex",
                     packets) >= (int)sizeof(packet_hex_key) ||
            append_hex_bytes(buf, packet_hex_key, packet, (size_t)received) < 0) {
            close(fd);
            return -1;
        }
        if (packet_type == 2U &&
            packet_txn == A90_SERVNOTIF_TXN_ID &&
	            packet_msg == A90_SERVNOTIF_REGISTER_LISTENER_MSG_ID) {
            response_seen = true;
            if (first_response_ms == 0) {
                first_response_ms = now;
            }
            if (parse_servnotif_register_response(buf,
                                                  "wifi_companion_service_notifier_listener",
                                                  packet,
                                                  (size_t)received,
                                                  &response_success,
                                                  &response_state_valid,
                                                  &response_state) < 0) {
                close(fd);
                return -1;
            }
        } else if (packet_type == 4U &&
	                   packet_msg == A90_SERVNOTIF_STATE_UPDATED_IND_MSG_ID) {
            uint8_t ack_request[96];
            size_t ack_request_len = 0;
            ssize_t ack_sent_bytes;

            indication_seen = true;
            if (first_indication_ms == 0) {
                first_indication_ms = now;
            }
            if (parse_servnotif_indication(buf,
                                           "wifi_companion_service_notifier_listener",
                                           packet,
                                           (size_t)received,
                                           &indication_valid,
                                           &indication_txn,
                                           &indication_state) < 0) {
                close(fd);
                return -1;
            }
            if (indication_valid) {
                build_servnotif_ack_request(ack_request,
                                            &ack_request_len,
                                            A90_SERVNOTIF_ACK_TXN_ID,
                                            indication_txn);
                if (append_hex_bytes(buf,
                                     "wifi_companion_service_notifier_listener.ack_request_hex",
                                     ack_request,
                                     ack_request_len) < 0) {
                    close(fd);
                    return -1;
                }
                ack_sent_bytes = sendto(fd, ack_request, ack_request_len, 0, (const struct sockaddr *)&dest, sizeof(dest));
                ack_sent = ack_sent_bytes == (ssize_t)ack_request_len;
                if (append_format(buf,
                                  "wifi_companion_service_notifier_listener.ack_send.rc=%d\n"
                                  "wifi_companion_service_notifier_listener.ack_send.bytes=%zd\n",
                                  ack_sent ? 0 : -1,
                                  ack_sent_bytes) < 0) {
                    close(fd);
                    return -1;
                }
            }
        } else if (packet_type == 2U &&
                   packet_txn == A90_SERVNOTIF_ACK_TXN_ID &&
                   packet_msg == A90_SERVNOTIF_ACK_MSG_ID) {
            if (parse_servnotif_ack_response(buf,
                                             "wifi_companion_service_notifier_listener",
                                             packet,
                                             (size_t)received,
                                             &ack_success) < 0) {
                close(fd);
                return -1;
            }
        }
        packets++;
        if (indication_seen && (!indication_valid || ack_success)) {
            break;
        }
	    }
    close_ms = monotonic_ms();
    close(fd);
    return append_format(buf,
	                         "wifi_companion_service_notifier_listener.response_seen=%u\n"
	                         "wifi_companion_service_notifier_listener.response_success=%u\n"
	                         "wifi_companion_service_notifier_listener.response_curr_state_valid=%u\n"
                         "wifi_companion_service_notifier_listener.response_curr_state=0x%08x\n"
                         "wifi_companion_service_notifier_listener.response_curr_state_name=%s\n"
                         "wifi_companion_service_notifier_listener.indication_seen=%u\n"
                         "wifi_companion_service_notifier_listener.indication_valid=%u\n"
                         "wifi_companion_service_notifier_listener.indication_curr_state=0x%08x\n"
                         "wifi_companion_service_notifier_listener.indication_curr_state_name=%s\n"
	                         "wifi_companion_service_notifier_listener.ack_sent=%u\n"
	                         "wifi_companion_service_notifier_listener.ack_success=%u\n"
	                         "wifi_companion_service_notifier_listener.timing.first_response_ms=%ld\n"
	                         "wifi_companion_service_notifier_listener.timing.first_indication_ms=%ld\n"
	                         "wifi_companion_service_notifier_listener.timing.close_ms=%ld\n"
	                         "wifi_companion_service_notifier_listener.timing.hold_ms=%ld\n"
	                         "wifi_companion_service_notifier_listener.timing.poll_timeout=%u\n"
	                         "wifi_companion_service_notifier_listener.result=%s\n"
	                         "wifi_companion_service_notifier_listener.end=1\n",
	                         response_seen ? 1U : 0U,
                         response_success ? 1U : 0U,
                         response_state_valid ? 1U : 0U,
                         response_state,
                         servnotif_state_name(response_state),
                         indication_seen ? 1U : 0U,
                         indication_valid ? 1U : 0U,
	                         indication_state,
	                         servnotif_state_name(indication_state),
	                         ack_sent ? 1U : 0U,
	                         ack_success ? 1U : 0U,
	                         first_response_ms,
	                         first_indication_ms,
	                         close_ms,
	                         send_after_ms > 0 && close_ms >= send_after_ms ? close_ms - send_after_ms : 0,
	                         response_poll_timeout ? 1U : 0U,
	                         response_seen ? (response_success ? "listener-response-success" : "listener-response-error") : "no-response");
}

struct service74_klog_state {
    unsigned int sysmon_qmi_count;
    unsigned int service180_count;
    unsigned int service74_count;
    int syslog_errno;
    bool syslog_available;
    char last_sysmon_qmi[192];
    char last_service74[192];
};

static bool line_contains_service_notifier_instance(const char *line,
                                                    const char *instance) {
    const char *prefix = "QMI handle and ";
    const char *value = strstr(line, prefix);

    return strstr(line, "service-notifier:") != NULL &&
           strstr(line, "service_notifier_new_server:") != NULL &&
           value != NULL &&
           strncmp(value + strlen(prefix), instance, strlen(instance)) == 0;
}

static void copy_klog_value(char *dst, size_t dst_len, const char *src) {
    size_t out = 0;

    if (dst_len == 0) {
        return;
    }
    while (*src != '\0' && *src != '\n' && *src != '\r' && out + 1 < dst_len) {
        unsigned char c = (unsigned char)*src++;

        dst[out++] = (c >= 0x20 && c <= 0x7e) ? (char)c : '?';
    }
    dst[out] = '\0';
}

static bool line_contains_sysmon_qmi_ready(const char *line) {
    return strstr(line, "sysmon-qmi:") != NULL &&
           strstr(line, "ssctl_new_server:") != NULL &&
           strstr(line, "Connection established between QMI handle and modem's SSCTL service") != NULL;
}

static int read_service74_klog_state(struct service74_klog_state *state) {
#ifndef SYS_syslog
    memset(state, 0, sizeof(*state));
    state->syslog_errno = ENOSYS;
    state->syslog_available = false;
    return 0;
#else
    char *text;
    ssize_t nread;
    char *line;
    char *saveptr = NULL;

    memset(state, 0, sizeof(*state));
    text = calloc(1U, A90_SERVICE74_GATE_KLOG_BYTES + 1U);
    if (text == NULL) {
        state->syslog_errno = ENOMEM;
        state->syslog_available = false;
        return 0;
    }
    nread = syscall(SYS_syslog,
                    A90_SYSLOG_ACTION_READ_ALL,
                    text,
                    A90_SERVICE74_GATE_KLOG_BYTES);
    if (nread < 0) {
        state->syslog_errno = errno;
        state->syslog_available = false;
        free(text);
        return 0;
    }
    text[nread] = '\0';
    state->syslog_available = true;
    for (line = strtok_r(text, "\n", &saveptr);
         line != NULL;
         line = strtok_r(NULL, "\n", &saveptr)) {
        if (line_contains_sysmon_qmi_ready(line)) {
            state->sysmon_qmi_count++;
            copy_klog_value(state->last_sysmon_qmi,
                            sizeof(state->last_sysmon_qmi),
                            line);
        }
        if (line_contains_service_notifier_instance(line, "180 service")) {
            state->service180_count++;
        }
        if (line_contains_service_notifier_instance(line, "74 service")) {
            state->service74_count++;
            copy_klog_value(state->last_service74,
                            sizeof(state->last_service74),
                            line);
        }
    }
    free(text);
    return 0;
#endif
}

static int append_service74_gate_state(struct buffer *buf,
                                       const char *phase,
                                       const struct service74_klog_state *state) {
    return append_format(buf,
                         "wifi_companion_start.service74_gate.%s.syslog_available=%d\n"
                         "wifi_companion_start.service74_gate.%s.syslog_errno=%d\n"
                         "wifi_companion_start.service74_gate.%s.count_sysmon_qmi=%u\n"
                         "wifi_companion_start.service74_gate.%s.count_180=%u\n"
                         "wifi_companion_start.service74_gate.%s.count_74=%u\n"
                         "wifi_companion_start.service74_gate.%s.last_sysmon_qmi=%s\n"
                         "wifi_companion_start.service74_gate.%s.last_74=%s\n",
                         phase,
                         state->syslog_available ? 1 : 0,
                         phase,
                         state->syslog_errno,
                         phase,
                         state->sysmon_qmi_count,
                         phase,
                         state->service180_count,
                         phase,
                         state->service74_count,
                         phase,
                         state->last_sysmon_qmi[0] != '\0' ? state->last_sysmon_qmi : "missing",
                         phase,
                         state->last_service74[0] != '\0' ? state->last_service74 : "missing");
}

static int wait_for_service74_gate(struct buffer *buf,
                                   unsigned int baseline_count_74,
                                   bool baseline_available,
                                   bool target_service180,
                                   bool target_sysmon_qmi,
                                   bool *seen,
                                   long *elapsed_ms) {
    const long started = monotonic_ms();
    const long deadline = started + A90_SERVICE74_GATE_WAIT_MS;
    struct service74_klog_state state;
    unsigned int attempts = 0;

    *seen = false;
    *elapsed_ms = 0;
    if (!baseline_available) {
        return append_literal(buf,
                              "wifi_companion_start.service74_gate.wait_attempts=0\n"
                              "wifi_companion_start.service74_gate.seen=0\n"
                              "wifi_companion_start.service74_gate.status=blocked-baseline-unavailable\n");
    }
    do {
        attempts++;
        if (read_service74_klog_state(&state) < 0) {
            return -1;
        }
        if (state.syslog_available &&
            (target_sysmon_qmi ? state.sysmon_qmi_count :
             (target_service180 ? state.service180_count : state.service74_count)) > baseline_count_74) {
            *seen = true;
            break;
        }
        usleep(250000);
    } while (monotonic_ms() < deadline);
    *elapsed_ms = monotonic_ms() - started;
    if (append_service74_gate_state(buf, "final", &state) < 0) {
        return -1;
    }
    return append_format(buf,
                         "wifi_companion_start.service74_gate.wait_attempts=%u\n"
                         "wifi_companion_start.service74_gate.wait_ms=%ld\n"
                         "wifi_companion_start.service74_gate.seen=%d\n"
                         "wifi_companion_start.service74_gate.target_service=%s\n"
                         "wifi_companion_start.service74_gate.status=%s\n",
                         attempts,
                         *elapsed_ms,
                         *seen ? 1 : 0,
                         target_sysmon_qmi ? "sysmon_qmi" : (target_service180 ? "180" : "74"),
                         *seen ? "open" : "timeout");
}

static int run_cnss_userspace_readiness_guarded(const struct config *cfg,
                                                const struct paths *paths,
                                                struct buffer *stdout_buf,
                                                struct buffer *stderr_buf,
                                                int *child_exit_code,
                                                int *child_signal,
                                                bool *timed_out) {
    struct composite_child children[2];
    bool all_postflight_safe = true;
    bool any_runtime_gap = false;
    bool any_observable = false;
    long deadline;

    *child_exit_code = -1;
    *child_signal = 0;
    *timed_out = false;

    composite_child_init(&children[0],
                         "cnss_diag",
                         "/vendor/bin/cnss_diag",
                         COMPOSITE_ID_CNSS_DIAG);
    composite_child_init(&children[1],
                         "cnss_daemon",
                         "/vendor/bin/cnss-daemon",
                         COMPOSITE_ID_CNSS);

    if (append_literal(stdout_buf, "cnss_userspace_readiness.begin=1\n") < 0 ||
        append_literal(stdout_buf, "cnss_userspace_readiness.mode=guarded\n") < 0 ||
        append_literal(stdout_buf, "cnss_userspace_readiness.cnss_diag=1\n") < 0 ||
        append_literal(stdout_buf, "cnss_userspace_readiness.cnss_daemon=1\n") < 0 ||
        append_literal(stdout_buf, "cnss_userspace_readiness.cnss_diag_argv=/vendor/bin/cnss_diag -q -f -t HELIUM\n") < 0 ||
        append_literal(stdout_buf, "cnss_userspace_readiness.cnss_daemon_argv=/vendor/bin/cnss-daemon -n -l\n") < 0 ||
        append_literal(stdout_buf, "cnss_userspace_readiness.wifi_hal=0\n") < 0 ||
        append_literal(stdout_buf, "cnss_userspace_readiness.wificond=0\n") < 0 ||
        append_literal(stdout_buf, "cnss_userspace_readiness.supplicant=0\n") < 0 ||
        append_literal(stdout_buf, "cnss_userspace_readiness.hostapd=0\n") < 0 ||
        append_literal(stdout_buf, "cnss_userspace_readiness.qcwlanstate_write=0\n") < 0 ||
        append_literal(stdout_buf, "cnss_userspace_readiness.scan_connect_linkup=0\n") < 0 ||
        append_literal(stdout_buf, "cnss_userspace_readiness.external_ping=0\n") < 0) {
        return -1;
    }
    if (!cfg->allow_cnss_start_only || !cfg->allow_cnss_userspace_readiness) {
        if (append_format(stdout_buf,
                          "cnss_userspace_readiness.allowed=0\n"
                          "cnss_userspace_readiness.allow_cnss_start_only=%d\n"
                          "cnss_userspace_readiness.allow_cnss_userspace_readiness=%d\n"
                          "cnss_userspace_readiness.exec_attempted=0\n"
                          "cnss_userspace_readiness.child_started=0\n"
                          "cnss_userspace_readiness.result=start-only-blocked\n"
                          "cnss_userspace_readiness.reason=missing-cnss-userspace-allow-flags\n"
                          "cnss_userspace_readiness.end=1\n",
                          cfg->allow_cnss_start_only ? 1 : 0,
                          cfg->allow_cnss_userspace_readiness ? 1 : 0) < 0) {
            return -1;
        }
        *child_exit_code = 0;
        return 0;
    }
    if (append_literal(stdout_buf,
                       "cnss_userspace_readiness.allowed=1\n"
                       "cnss_userspace_readiness.exec_attempted=1\n") < 0) {
        return -1;
    }
    if (composite_spawn_child(cfg, paths, &children[0], stdout_buf) < 0) {
        composite_cleanup_children(children, 2, stdout_buf, stderr_buf);
        append_literal(stdout_buf,
                       "cnss_userspace_readiness.result=manual-review-required\n"
                       "cnss_userspace_readiness.reason=cnss-diag-spawn-failed\n"
                       "cnss_userspace_readiness.end=1\n");
        return -1;
    }
    usleep(300000);
    if (composite_spawn_child(cfg, paths, &children[1], stdout_buf) < 0) {
        composite_cleanup_children(children, 2, stdout_buf, stderr_buf);
        append_literal(stdout_buf,
                       "cnss_userspace_readiness.result=manual-review-required\n"
                       "cnss_userspace_readiness.reason=cnss-daemon-spawn-failed\n"
                       "cnss_userspace_readiness.end=1\n");
        return -1;
    }
    append_literal(stdout_buf, "cnss_userspace_readiness.child_started=2\n");
    deadline = monotonic_ms() + cfg->timeout_sec * 1000L;
    if (composite_poll_children(children, 2, stdout_buf, stderr_buf, deadline, timed_out) < 0) {
        composite_cleanup_children(children, 2, stdout_buf, stderr_buf);
        return -1;
    }
    composite_capture_observable_children(children, 2, stdout_buf);
    composite_cleanup_children(children, 2, stdout_buf, stderr_buf);

    for (size_t i = 0; i < 2; i++) {
        bool safe = composite_child_postflight_safe(&children[i]);

        if (!safe) {
            all_postflight_safe = false;
        }
        if (children[i].observable) {
            any_observable = true;
        }
        if (composite_child_runtime_gap(&children[i], *timed_out)) {
            any_runtime_gap = true;
            if (*child_exit_code < 0 && children[i].exit_code >= 0) {
                *child_exit_code = children[i].exit_code;
            }
            if (*child_signal == 0 && children[i].signal != 0) {
                *child_signal = children[i].signal;
            }
        }
        if (append_format(stdout_buf,
                          "cnss_userspace_readiness.child.%s.observable=%d\n"
                          "cnss_userspace_readiness.child.%s.exited=%d\n"
                          "cnss_userspace_readiness.child.%s.exit_code=%d\n"
                          "cnss_userspace_readiness.child.%s.signal=%d\n"
                          "cnss_userspace_readiness.child.%s.term_sent=%d\n"
                          "cnss_userspace_readiness.child.%s.kill_sent=%d\n"
                          "cnss_userspace_readiness.child.%s.reaped=%d\n"
                          "cnss_userspace_readiness.child.%s.proc_status_captured=%d\n"
                          "cnss_userspace_readiness.child.%s.proc_attr_current_captured=%d\n"
                          "cnss_userspace_readiness.child.%s.fd_summary_captured=%d\n"
                          "cnss_userspace_readiness.child.%s.maps_summary_captured=%d\n"
                          "cnss_userspace_readiness.child.%s.postflight_safe=%d\n",
                          children[i].name,
                          children[i].observable ? 1 : 0,
                          children[i].name,
                          children[i].child_done ? 1 : 0,
                          children[i].name,
                          children[i].exit_code,
                          children[i].name,
                          children[i].signal,
                          children[i].name,
                          children[i].term_sent ? 1 : 0,
                          children[i].name,
                          children[i].kill_sent ? 1 : 0,
                          children[i].name,
                          children[i].reaped ? 1 : 0,
                          children[i].name,
                          children[i].proc_status_captured ? 1 : 0,
                          children[i].name,
                          children[i].proc_attr_current_captured ? 1 : 0,
                          children[i].name,
                          children[i].fd_summary_captured ? 1 : 0,
                          children[i].name,
                          children[i].maps_summary_captured ? 1 : 0,
                          children[i].name,
                          safe ? 1 : 0) < 0) {
            return -1;
        }
    }
    if (*child_exit_code < 0 && *child_signal == 0) {
        *child_exit_code = 0;
    }
    if (append_format(stdout_buf,
                      "cnss_userspace_readiness.timed_out=%d\n"
                      "cnss_userspace_readiness.any_observable=%d\n"
                      "cnss_userspace_readiness.all_postflight_safe=%d\n",
                      *timed_out ? 1 : 0,
                      any_observable ? 1 : 0,
                      all_postflight_safe ? 1 : 0) < 0) {
        return -1;
    }
    if (!all_postflight_safe) {
        append_literal(stdout_buf,
                       "cnss_userspace_readiness.result=start-only-reboot-required\n"
                       "cnss_userspace_readiness.reason=process-not-proven-stopped\n");
    } else if (*timed_out && any_observable) {
        append_literal(stdout_buf,
                       "cnss_userspace_readiness.result=readiness-window-pass\n"
                       "cnss_userspace_readiness.reason=cnss-userspace-observed-until-timeout-clean-stop\n");
    } else if (any_runtime_gap) {
        append_literal(stdout_buf,
                       "cnss_userspace_readiness.result=start-only-runtime-gap\n"
                       "cnss_userspace_readiness.reason=child-exited-before-observe-window\n");
    } else {
        append_literal(stdout_buf,
                       "cnss_userspace_readiness.result=manual-review-required\n"
                       "cnss_userspace_readiness.reason=unclassified-lifecycle-state\n");
    }
    append_literal(stdout_buf, "cnss_userspace_readiness.end=1\n");
    return 0;
}

struct property_service_shim {
    pid_t pid;
    int record_fd;
    bool started;
    bool term_sent;
    bool kill_sent;
    bool reaped;
    int exit_code;
    int signal;
};

static bool property_service_shim_needed(const struct config *cfg);
static int start_property_service_shim(const struct config *cfg,
                                       const struct paths *paths,
                                       struct property_service_shim *shim,
                                       struct buffer *stdout_buf);
static int stop_property_service_shim(struct property_service_shim *shim,
                                      const struct paths *paths,
                                      struct buffer *stdout_buf);

static int run_wifi_companion_start_only_guarded(const struct config *cfg,
                                                 const struct paths *paths,
                                                 struct buffer *stdout_buf,
                                                 struct buffer *stderr_buf,
                                                 int *child_exit_code,
                                                 int *child_signal,
                                                 bool *timed_out) {
    struct composite_child children[A90_COMPOSITE_CHILD_MAX];
    const bool qrtr_first_service_manager =
        is_wifi_companion_qrtr_first_vnd_service_manager_start_only_mode(cfg->mode);
    const bool cnss_first_delayed_service_manager =
        is_wifi_companion_cnss_first_delayed_vnd_service_manager_start_only_mode(cfg->mode);
    const bool peripheral_manager_init_contract =
        is_wifi_companion_peripheral_manager_init_contract_start_only_mode(cfg->mode);
    const bool peripheral_manager_property_contract =
        is_wifi_companion_peripheral_manager_property_contract_start_only_mode(cfg->mode) ||
        peripheral_manager_init_contract;
    const bool peripheral_manager_node_parity =
        is_wifi_companion_peripheral_manager_node_materialization_mode(cfg->mode);
    const bool service74_gated_service_manager =
        is_wifi_companion_service74_gated_vnd_service_manager_start_only_mode(cfg->mode);
    const bool service74_gated_vnd_readiness =
        is_wifi_companion_service74_gated_vnd_service_manager_readiness_start_only_mode(cfg->mode);
    const bool service74_gated_cnss_retry =
        is_wifi_companion_service74_gated_vnd_service_manager_cnss_retry_start_only_mode(cfg->mode);
    const bool service74_gated_peripheral_manager_registry_retry =
        is_wifi_companion_service74_gated_peripheral_manager_cnss_retry_registry_snapshot_start_only_mode(cfg->mode);
    const bool service74_gated_peripheral_manager_vndservice_query_cnss_retry =
        is_wifi_companion_service74_gated_peripheral_manager_vndservice_query_cnss_retry_start_only_mode(cfg->mode);
    const bool service74_gated_peripheral_manager_provider_first_cnss =
        is_wifi_companion_service74_gated_peripheral_manager_vndservice_query_provider_first_cnss_start_only_mode(cfg->mode);
    const bool service74_gated_peripheral_manager_cnss_retry =
        is_wifi_companion_service74_gated_peripheral_manager_cnss_retry_start_only_mode(cfg->mode) ||
        service74_gated_peripheral_manager_vndservice_query_cnss_retry ||
        service74_gated_peripheral_manager_provider_first_cnss;
    const bool service74_gated_peripheral_manager_vndservice_query =
        is_wifi_companion_service74_gated_peripheral_manager_vndservice_query_start_only_mode(cfg->mode) ||
        service74_gated_peripheral_manager_vndservice_query_cnss_retry ||
        service74_gated_peripheral_manager_provider_first_cnss;
    const bool service74_gated_android_userspace_registry_retry =
        is_wifi_companion_service74_gated_android_userspace_cnss_retry_registry_snapshot_start_only_mode(cfg->mode);
    const bool service74_gated_android_userspace_retry =
        is_wifi_companion_service74_gated_android_userspace_cnss_retry_start_only_mode(cfg->mode) ||
        service74_gated_android_userspace_registry_retry;
    const bool service74_gated_registry_snapshot =
        is_wifi_companion_service74_gated_vnd_service_manager_registry_snapshot_start_only_mode(cfg->mode);
    const bool service74_gated_mdm_helper =
        is_wifi_companion_service74_gated_mdm_helper_start_only_mode(cfg->mode);
    const bool service180_gated_mdm_helper =
        is_wifi_companion_service180_gated_mdm_helper_start_only_mode(cfg->mode);
    const bool sysmon_gated_mdm_helper =
        is_wifi_companion_sysmon_gated_mdm_helper_start_only_mode(cfg->mode);
    const bool service74_gated_registry_capture =
        service74_gated_registry_snapshot ||
        service74_gated_peripheral_manager_registry_retry ||
        service74_gated_android_userspace_registry_retry;
    const bool service74_gated_peripheral_manager_any_retry =
        service74_gated_peripheral_manager_cnss_retry ||
        service74_gated_peripheral_manager_registry_retry;
    const bool service74_gated_peripheral_manager_any =
        service74_gated_peripheral_manager_any_retry ||
        service74_gated_peripheral_manager_vndservice_query;
    const bool service74_gated_any =
        service74_gated_service_manager ||
        service74_gated_vnd_readiness ||
        service74_gated_cnss_retry ||
        service74_gated_peripheral_manager_any ||
        service74_gated_android_userspace_retry ||
        service74_gated_registry_snapshot;
    const bool service74_gate_required =
        service74_gated_any ||
        service74_gated_mdm_helper ||
        service180_gated_mdm_helper ||
        sysmon_gated_mdm_helper;
    const bool service74_gate_target_180 = service180_gated_mdm_helper;
    const bool service74_gate_target_sysmon_qmi = sysmon_gated_mdm_helper;
    const bool post_sysmon_observer =
        is_wifi_companion_post_sysmon_observer_start_only_mode(cfg->mode) ||
        is_wifi_companion_android_order_post_sysmon_observer_start_only_mode(cfg->mode);
    const bool android_order_post_sysmon_observer =
        is_wifi_companion_android_order_post_sysmon_observer_start_only_mode(cfg->mode);
    const bool with_service_manager =
        is_wifi_companion_with_service_manager_start_only_mode(cfg->mode);
    const bool with_vnd_service_manager =
        is_wifi_companion_vnd_service_manager_start_only_mode(cfg->mode) ||
        peripheral_manager_node_parity ||
        qrtr_first_service_manager ||
        cnss_first_delayed_service_manager ||
        service74_gated_any;
    const char *order;
    size_t child_count = 0;
    struct property_service_shim property_shim;
    bool all_postflight_safe = true;
    bool any_runtime_gap = false;
    bool all_observable = true;
    bool service74_gate_baseline_available = false;
    bool service74_gate_open = !service74_gate_required;
    bool service_manager_started = false;
    unsigned int service74_gate_baseline_count = 0;
    size_t active_child_count = 0;
    int cnss_initial_index = -1;
    int vndservicemanager_index = -1;
    const int service74_gate_after_index =
        service74_gated_peripheral_manager_provider_first_cnss ? 4 : 5;
    long deadline;
    struct service74_klog_state service74_gate_baseline;

    *child_exit_code = -1;
    *child_signal = 0;
    *timed_out = false;

    memset(children, 0, sizeof(children));
    if (with_service_manager &&
        !qrtr_first_service_manager &&
        !cnss_first_delayed_service_manager &&
        !service74_gated_any) {
        composite_child_init(&children[child_count++],
                             "servicemanager",
                             "/system/bin/servicemanager",
                             COMPOSITE_ID_SERVICE_MANAGER);
        composite_child_init(&children[child_count++],
                             "hwservicemanager",
                             "/system/bin/hwservicemanager",
                             COMPOSITE_ID_SERVICE_MANAGER);
        if (with_vnd_service_manager) {
            composite_child_init(&children[child_count++],
                                 "vndservicemanager",
                                 "/vendor/bin/vndservicemanager",
                                 COMPOSITE_ID_VND_SERVICE_MANAGER);
        }
    }
    if (!peripheral_manager_node_parity) {
        composite_child_init(&children[child_count++],
                             "qrtr_ns",
                             "/vendor/bin/qrtr-ns",
                             COMPOSITE_ID_QRTR_NS);
        if (android_order_post_sysmon_observer) {
            composite_child_init(&children[child_count++],
                                 "pd_mapper",
                                 "/vendor/bin/pd-mapper",
                                 COMPOSITE_ID_PD_MAPPER);
            composite_child_init(&children[child_count++],
                                 "rmt_storage",
                                 "/vendor/bin/rmt_storage",
                                 COMPOSITE_ID_RMT_STORAGE);
            composite_child_init(&children[child_count++],
                                 "tftp_server",
                                 "/vendor/bin/tftp_server",
                                 COMPOSITE_ID_TFTP_SERVER);
        } else {
            composite_child_init(&children[child_count++],
                                 "rmt_storage",
                                 "/vendor/bin/rmt_storage",
                                 COMPOSITE_ID_RMT_STORAGE);
            composite_child_init(&children[child_count++],
                                 "tftp_server",
                                 "/vendor/bin/tftp_server",
                                 COMPOSITE_ID_TFTP_SERVER);
            composite_child_init(&children[child_count++],
                                 "pd_mapper",
                                 "/vendor/bin/pd-mapper",
                                 COMPOSITE_ID_PD_MAPPER);
        }
        if (qrtr_first_service_manager) {
            composite_child_init(&children[child_count++],
                                 "servicemanager",
                                 "/system/bin/servicemanager",
                                 COMPOSITE_ID_SERVICE_MANAGER);
            composite_child_init(&children[child_count++],
                                 "hwservicemanager",
                                 "/system/bin/hwservicemanager",
                                 COMPOSITE_ID_SERVICE_MANAGER);
            composite_child_init(&children[child_count++],
                                 "vndservicemanager",
                                 "/vendor/bin/vndservicemanager",
                                 COMPOSITE_ID_VND_SERVICE_MANAGER);
        }
        if (!post_sysmon_observer) {
            composite_child_init(&children[child_count++],
                                 "cnss_diag",
                                 "/vendor/bin/cnss_diag",
                                 COMPOSITE_ID_CNSS_DIAG);
            if (!service74_gated_peripheral_manager_provider_first_cnss) {
                cnss_initial_index = (int)child_count;
                composite_child_init(&children[child_count++],
                                     "cnss_daemon",
                                     "/vendor/bin/cnss-daemon",
                                     COMPOSITE_ID_CNSS);
            }
        }
    }
    if (cnss_first_delayed_service_manager || service74_gated_any) {
        composite_child_init(&children[child_count++],
                             "servicemanager",
                             "/system/bin/servicemanager",
                             COMPOSITE_ID_SERVICE_MANAGER);
        composite_child_init(&children[child_count++],
                             "hwservicemanager",
                             "/system/bin/hwservicemanager",
                             COMPOSITE_ID_SERVICE_MANAGER);
        vndservicemanager_index = (int)child_count;
        composite_child_init(&children[child_count++],
                             "vndservicemanager",
                             "/vendor/bin/vndservicemanager",
                             COMPOSITE_ID_VND_SERVICE_MANAGER);
    }
    if (service74_gated_android_userspace_retry) {
        composite_child_init(&children[child_count++],
                             "wifi_hal_legacy",
                             "/vendor/bin/hw/android.hardware.wifi@1.0-service",
                             COMPOSITE_ID_WIFI_HAL);
        composite_child_init(&children[child_count++],
                             "wifi_hal_ext",
                             "/vendor/bin/hw/vendor.samsung.hardware.wifi@2.0-service",
                             COMPOSITE_ID_WIFI_HAL);
        composite_child_init(&children[child_count++],
                             "wificond",
                             "/system/bin/wificond",
                             COMPOSITE_ID_WIFICOND);
        composite_child_init(&children[child_count++],
                             "cnss_daemon_retry",
                             "/vendor/bin/cnss-daemon",
                             COMPOSITE_ID_CNSS);
    } else if (service74_gated_cnss_retry) {
        composite_child_init(&children[child_count++],
                             "cnss_daemon_retry",
                             "/vendor/bin/cnss-daemon",
                             COMPOSITE_ID_CNSS);
    } else if (peripheral_manager_node_parity) {
        if (peripheral_manager_init_contract) {
            composite_child_init(&children[child_count++],
                                 "per_proxy_helper",
                                 "/vendor/bin/pm_proxy_helper",
                                 COMPOSITE_ID_PER_PROXY_HELPER);
        }
        composite_child_init(&children[child_count++],
                             "per_mgr",
                             "/vendor/bin/pm-service",
                             COMPOSITE_ID_PER_MGR);
        composite_child_init(&children[child_count++],
                             "per_proxy",
                             "/vendor/bin/pm-proxy",
                             COMPOSITE_ID_PER_PROXY);
    } else if (service74_gated_peripheral_manager_any_retry) {
        composite_child_init(&children[child_count++],
                             "per_mgr",
                             "/vendor/bin/pm-service",
                             COMPOSITE_ID_PER_MGR);
        composite_child_init(&children[child_count++],
                             "per_proxy",
                             "/vendor/bin/pm-proxy",
                             COMPOSITE_ID_PER_PROXY);
        composite_child_init(&children[child_count++],
                             "cnss_daemon_retry",
                             "/vendor/bin/cnss-daemon",
                             COMPOSITE_ID_CNSS);
    } else if (service74_gated_peripheral_manager_vndservice_query) {
        composite_child_init(&children[child_count++],
                             "per_mgr",
                             "/vendor/bin/pm-service",
                             COMPOSITE_ID_PER_MGR);
        composite_child_init(&children[child_count++],
                             "per_proxy",
                             "/vendor/bin/pm-proxy",
                             COMPOSITE_ID_PER_PROXY);
    } else if (service74_gated_mdm_helper || service180_gated_mdm_helper || sysmon_gated_mdm_helper) {
        composite_child_init(&children[child_count++],
                             "mdm_helper",
                             "/vendor/bin/mdm_helper",
                             COMPOSITE_ID_MDM_HELPER);
    }
    if (post_sysmon_observer) {
        order = android_order_post_sysmon_observer
                    ? "qrtr_ns,pd_mapper,rmt_storage,tftp_server"
                    : "qrtr_ns,rmt_storage,tftp_server,pd_mapper";
    } else if (peripheral_manager_init_contract) {
        order = "servicemanager,hwservicemanager,vndservicemanager,per_proxy_helper,per_mgr,init.svc.vendor.per_mgr=running,per_proxy,sys.shutdown.requested-stop-model";
    } else if (peripheral_manager_node_parity) {
        order = "servicemanager,hwservicemanager,vndservicemanager,per_mgr,per_proxy";
    } else if (qrtr_first_service_manager) {
        order = "qrtr_ns,rmt_storage,tftp_server,pd_mapper,servicemanager,hwservicemanager,vndservicemanager,cnss_diag,cnss_daemon";
    } else if (cnss_first_delayed_service_manager) {
        order = "qrtr_ns,rmt_storage,tftp_server,pd_mapper,cnss_diag,cnss_daemon,servicemanager,hwservicemanager,vndservicemanager";
    } else if (service74_gated_android_userspace_retry) {
        order = service74_gated_android_userspace_registry_retry
                    ? "qrtr_ns,rmt_storage,tftp_server,pd_mapper,cnss_diag,cnss_daemon,service74_gate,servicemanager,hwservicemanager,vndservicemanager,vndservicemanager_ready,cnss_daemon_initial_cleanup,wifi_hal_legacy,wifi_hal_ext,wificond,cnss_daemon_retry,registry_snapshot"
                    : "qrtr_ns,rmt_storage,tftp_server,pd_mapper,cnss_diag,cnss_daemon,service74_gate,servicemanager,hwservicemanager,vndservicemanager,vndservicemanager_ready,cnss_daemon_initial_cleanup,wifi_hal_legacy,wifi_hal_ext,wificond,cnss_daemon_retry";
    } else if (sysmon_gated_mdm_helper) {
        order = "qrtr_ns,rmt_storage,tftp_server,pd_mapper,cnss_diag,cnss_daemon,sysmon_gate,mdm_helper";
    } else if (service180_gated_mdm_helper) {
        order = "qrtr_ns,rmt_storage,tftp_server,pd_mapper,cnss_diag,cnss_daemon,service180_gate,mdm_helper";
    } else if (service74_gated_mdm_helper) {
        order = "qrtr_ns,rmt_storage,tftp_server,pd_mapper,cnss_diag,cnss_daemon,service74_gate,mdm_helper";
    } else if (service74_gated_cnss_retry) {
        order = "qrtr_ns,rmt_storage,tftp_server,pd_mapper,cnss_diag,cnss_daemon,service74_gate,servicemanager,hwservicemanager,vndservicemanager,vndservicemanager_ready,cnss_daemon_initial_cleanup,cnss_daemon_retry";
    } else if (service74_gated_peripheral_manager_any_retry) {
        order = service74_gated_peripheral_manager_registry_retry
                    ? "qrtr_ns,rmt_storage,tftp_server,pd_mapper,cnss_diag,cnss_daemon,service74_gate,servicemanager,hwservicemanager,vndservicemanager,vndservicemanager_ready,cnss_daemon_initial_cleanup,per_mgr,per_proxy,cnss_daemon_retry,registry_snapshot"
                    : (service74_gated_peripheral_manager_provider_first_cnss
                           ? "qrtr_ns,rmt_storage,tftp_server,pd_mapper,cnss_diag,service74_gate,servicemanager,hwservicemanager,vndservicemanager,vndservicemanager_ready,per_mgr,vndservice_query,per_proxy,vndservice_query,cnss_daemon_retry"
                           : (service74_gated_peripheral_manager_vndservice_query_cnss_retry
                           ? "qrtr_ns,rmt_storage,tftp_server,pd_mapper,cnss_diag,cnss_daemon,service74_gate,servicemanager,hwservicemanager,vndservicemanager,vndservicemanager_ready,cnss_daemon_initial_cleanup,per_mgr,vndservice_query,per_proxy,vndservice_query,cnss_daemon_retry"
                           : "qrtr_ns,rmt_storage,tftp_server,pd_mapper,cnss_diag,cnss_daemon,service74_gate,servicemanager,hwservicemanager,vndservicemanager,vndservicemanager_ready,cnss_daemon_initial_cleanup,per_mgr,per_proxy,cnss_daemon_retry"));
    } else if (service74_gated_peripheral_manager_vndservice_query) {
        order = "qrtr_ns,rmt_storage,tftp_server,pd_mapper,cnss_diag,cnss_daemon,service74_gate,servicemanager,hwservicemanager,vndservicemanager,vndservicemanager_ready,cnss_daemon_initial_cleanup,per_mgr,vndservice_query,per_proxy,vndservice_query";
    } else if (service74_gated_registry_snapshot) {
        order = "qrtr_ns,rmt_storage,tftp_server,pd_mapper,cnss_diag,cnss_daemon,service74_gate,servicemanager,hwservicemanager,vndservicemanager,vndservicemanager_ready,registry_snapshot";
    } else if (service74_gated_vnd_readiness) {
        order = "qrtr_ns,rmt_storage,tftp_server,pd_mapper,cnss_diag,cnss_daemon,service74_gate,servicemanager,hwservicemanager,vndservicemanager,vndservicemanager_ready";
    } else if (service74_gated_service_manager) {
        order = "qrtr_ns,rmt_storage,tftp_server,pd_mapper,cnss_diag,cnss_daemon,service74_gate,servicemanager,hwservicemanager,vndservicemanager";
    } else if (with_service_manager) {
        order = with_vnd_service_manager
                    ? "servicemanager,hwservicemanager,vndservicemanager,qrtr_ns,rmt_storage,tftp_server,pd_mapper,cnss_diag,cnss_daemon"
                    : "servicemanager,hwservicemanager,qrtr_ns,rmt_storage,tftp_server,pd_mapper,cnss_diag,cnss_daemon";
    } else {
        order = "qrtr_ns,rmt_storage,tftp_server,pd_mapper,cnss_diag,cnss_daemon";
    }

    if (append_literal(stdout_buf, "wifi_companion_start.begin=1\n") < 0 ||
        append_literal(stdout_buf, "wifi_companion_start.mode=guarded\n") < 0 ||
        append_format(stdout_buf,
                      "wifi_companion_start.with_service_manager=%d\n",
                      with_service_manager ? 1 : 0) < 0 ||
        append_format(stdout_buf,
                      "wifi_companion_start.with_vnd_service_manager=%d\n",
                      with_vnd_service_manager ? 1 : 0) < 0 ||
        append_format(stdout_buf,
                      "wifi_companion_start.capture_mode=%s\n",
                      cfg->capture_mode) < 0 ||
        append_format(stdout_buf,
                      "wifi_companion_start.order=%s\n",
                      order) < 0 ||
        append_literal(stdout_buf, "wifi_companion_start.servicemanager_argv=/system/bin/servicemanager\n") < 0 ||
        append_literal(stdout_buf, "wifi_companion_start.hwservicemanager_argv=/system/bin/hwservicemanager\n") < 0 ||
        append_literal(stdout_buf, "wifi_companion_start.vndservicemanager_argv=/vendor/bin/vndservicemanager /dev/vndbinder\n") < 0 ||
        append_literal(stdout_buf, "wifi_companion_start.qrtr_ns_argv=/vendor/bin/qrtr-ns -f\n") < 0 ||
        append_literal(stdout_buf, "wifi_companion_start.rmt_storage_argv=/vendor/bin/rmt_storage\n") < 0 ||
        append_literal(stdout_buf, "wifi_companion_start.tftp_server_argv=/vendor/bin/tftp_server\n") < 0 ||
        append_literal(stdout_buf, "wifi_companion_start.pd_mapper_argv=/vendor/bin/pd-mapper\n") < 0 ||
        append_literal(stdout_buf, "wifi_companion_start.per_proxy_helper_argv=/vendor/bin/pm_proxy_helper\n") < 0 ||
        append_literal(stdout_buf, "wifi_companion_start.per_mgr_argv=/vendor/bin/pm-service\n") < 0 ||
        append_literal(stdout_buf, "wifi_companion_start.per_proxy_argv=/vendor/bin/pm-proxy\n") < 0 ||
        append_literal(stdout_buf, "wifi_companion_start.mdm_helper_argv=/vendor/bin/mdm_helper\n") < 0 ||
        append_literal(stdout_buf, "wifi_companion_start.cnss_diag_argv=/vendor/bin/cnss_diag -q -f -t HELIUM\n") < 0 ||
        append_literal(stdout_buf, "wifi_companion_start.cnss_daemon_argv=/vendor/bin/cnss-daemon -n -l\n") < 0 ||
        append_format(stdout_buf,
                      "wifi_companion_start.service_manager=%d\n",
                      with_service_manager ? 1 : 0) < 0 ||
        append_format(stdout_buf,
                      "wifi_companion_start.service74_gate.enabled=%d\n"
                      "wifi_companion_start.service74_gate.wait_limit_ms=%ld\n",
                      service74_gate_required ? 1 : 0,
                      A90_SERVICE74_GATE_WAIT_MS) < 0 ||
        append_format(stdout_buf,
                      "wifi_companion_start.service74_gate.target_service=%s\n",
                      service74_gate_target_sysmon_qmi ? "sysmon_qmi" : (service74_gate_target_180 ? "180" : "74")) < 0 ||
        append_format(stdout_buf,
                      "wifi_companion_start.vndservicemanager_readiness.enabled=%d\n"
                      "wifi_companion_start.vndservicemanager_readiness.settle_ms=%ld\n"
                      "wifi_companion_start.cnss_retry.enabled=%d\n"
                      "wifi_companion_start.initial_cnss_daemon.suppressed=%d\n"
                      "wifi_companion_start.peripheral_manager.enabled=%d\n"
                      "wifi_companion_start.peripheral_manager.property_contract=%d\n"
                      "wifi_companion_start.peripheral_manager.init_contract=%d\n"
                      "wifi_companion_start.peripheral_manager.per_mgr_ioprio_rt4=%d\n"
                      "wifi_companion_start.peripheral_manager.per_proxy_property_lifecycle=%d\n"
                      "wifi_companion_start.peripheral_manager.shutdown_stop_model=%d\n"
                      "wifi_companion_start.peripheral_manager.shutdown_stop.trigger=sys.shutdown.requested\n"
                      "wifi_companion_start.peripheral_manager.shutdown_stop.sys.shutdown.requested=0\n"
                      "wifi_companion_start.android_userspace_order.enabled=%d\n"
                      "wifi_companion_start.registry_snapshot.enabled=%d\n",
                      (service74_gated_vnd_readiness ||
                       service74_gated_cnss_retry ||
                       service74_gated_peripheral_manager_any_retry ||
                       service74_gated_android_userspace_retry ||
                       service74_gated_registry_snapshot) ? 1 : 0,
                      A90_VNDSERVICEMANAGER_READY_SETTLE_MS,
                      (service74_gated_cnss_retry ||
                       service74_gated_peripheral_manager_any_retry ||
                       service74_gated_android_userspace_retry) ? 1 : 0,
                      service74_gated_peripheral_manager_provider_first_cnss ? 1 : 0,
                      (service74_gated_peripheral_manager_any ||
                       peripheral_manager_node_parity) ? 1 : 0,
                      peripheral_manager_property_contract ? 1 : 0,
                      peripheral_manager_init_contract ? 1 : 0,
                      peripheral_manager_init_contract ? 1 : 0,
                      peripheral_manager_init_contract ? 1 : 0,
                      peripheral_manager_init_contract ? 1 : 0,
                      service74_gated_android_userspace_retry ? 1 : 0,
                      service74_gated_registry_capture ? 1 : 0) < 0 ||
        append_format(stdout_buf,
                      "wifi_companion_start.vndservice_query.enabled=%d\n",
                      service74_gated_peripheral_manager_vndservice_query ? 1 : 0) < 0 ||
        append_format(stdout_buf, "wifi_companion_start.wifi_hal=%d\n",
                      service74_gated_android_userspace_retry ? 2 : 0) < 0 ||
        append_format(stdout_buf, "wifi_companion_start.wificond=%d\n",
                      service74_gated_android_userspace_retry ? 1 : 0) < 0 ||
        append_format(stdout_buf, "wifi_companion_start.mdm_helper=%d\n",
                      (service74_gated_mdm_helper || service180_gated_mdm_helper || sysmon_gated_mdm_helper) ? 1 : 0) < 0 ||
        append_literal(stdout_buf, "wifi_companion_start.wifi_hal_legacy_argv=/vendor/bin/hw/android.hardware.wifi@1.0-service\n") < 0 ||
        append_literal(stdout_buf, "wifi_companion_start.wifi_hal_ext_argv=/vendor/bin/hw/vendor.samsung.hardware.wifi@2.0-service\n") < 0 ||
        append_literal(stdout_buf, "wifi_companion_start.wificond_argv=/system/bin/wificond\n") < 0 ||
        append_literal(stdout_buf, "wifi_companion_start.supplicant=0\n") < 0 ||
        append_literal(stdout_buf, "wifi_companion_start.hostapd=0\n") < 0 ||
        append_literal(stdout_buf, "wifi_companion_start.qcwlanstate_write=0\n") < 0 ||
        append_literal(stdout_buf, "wifi_companion_start.scan_connect_linkup=0\n") < 0 ||
        append_literal(stdout_buf, "wifi_companion_start.external_ping=0\n") < 0 ||
        append_format(stdout_buf,
                      "wifi_companion_start.qrtr_nameservice_readback=%d\n"
                      "wifi_companion_start.servloc_domain_list_probe=%d\n"
                      "wifi_companion_start.service_notifier_listener_probe=%d\n"
                      "wifi_companion_start.qmi_payload=%d\n",
                      cfg->allow_qrtr_ns_readback ? 1 : 0,
                      cfg->allow_servloc_domain_list_probe ? 1 : 0,
                      cfg->allow_service_notifier_listener_probe ? 1 : 0,
                      (cfg->allow_servloc_domain_list_probe ||
                       cfg->allow_service_notifier_listener_probe) ? 1 : 0) < 0) {
        return -1;
    }
    if (!cfg->allow_wifi_companion_start_only ||
        (!post_sysmon_observer &&
         !peripheral_manager_node_parity &&
         !cfg->allow_cnss_start_only) ||
        (with_service_manager && !cfg->allow_service_manager_start_only) ||
        (service74_gated_android_userspace_retry && !cfg->allow_wifi_hal_start_only)) {
        if (append_format(stdout_buf,
                          "wifi_companion_start.allowed=0\n"
                          "wifi_companion_start.allow_service_manager_start_only=%d\n"
                          "wifi_companion_start.allow_wifi_companion_start_only=%d\n"
                          "wifi_companion_start.allow_cnss_start_only=%d\n"
                          "wifi_companion_start.allow_wifi_hal_start_only=%d\n"
                          "wifi_companion_start.exec_attempted=0\n"
                          "wifi_companion_start.child_started=0\n"
                          "wifi_companion_start.result=start-only-blocked\n"
                          "wifi_companion_start.reason=missing-companion-allow-flags\n"
                          "wifi_companion_start.end=1\n",
                          cfg->allow_service_manager_start_only ? 1 : 0,
                          cfg->allow_wifi_companion_start_only ? 1 : 0,
                          cfg->allow_cnss_start_only ? 1 : 0,
                          cfg->allow_wifi_hal_start_only ? 1 : 0) < 0) {
            return -1;
        }
        *child_exit_code = 0;
        return 0;
    }
    if (append_literal(stdout_buf,
                       "wifi_companion_start.allowed=1\n"
                       "wifi_companion_start.exec_attempted=1\n") < 0) {
        return -1;
    }
    if (peripheral_manager_node_parity &&
        (append_private_android_node_status(stdout_buf, paths, "subsys_modem", "subsys_modem") < 0 ||
         append_private_android_node_status(stdout_buf, paths, "subsys_esoc0", "subsys_esoc0") < 0 ||
         append_private_android_node_status(stdout_buf, paths, "esoc-0", "esoc_0") < 0)) {
        return -1;
    }
    if (append_qipcrtr_protocol_summary(stdout_buf, "wifi_companion_start.net_before") < 0) {
        return -1;
    }
    if (service74_gate_required) {
        if (read_service74_klog_state(&service74_gate_baseline) < 0 ||
            append_service74_gate_state(stdout_buf,
                                        "baseline",
                                        &service74_gate_baseline) < 0) {
            return -1;
        }
        service74_gate_baseline_available = service74_gate_baseline.syslog_available;
        service74_gate_baseline_count = service74_gate_target_sysmon_qmi
                                            ? service74_gate_baseline.sysmon_qmi_count
                                            : (service74_gate_target_180
                                            ? service74_gate_baseline.service180_count
                                            : service74_gate_baseline.service74_count);
    }
    if (start_property_service_shim(cfg, paths, &property_shim, stdout_buf) < 0) {
        return -1;
    }
    if (property_service_shim_needed(cfg) && !property_shim.started) {
        append_literal(stdout_buf,
                       "wifi_companion_start.child_started=0\n"
                       "wifi_companion_start.result=property-service-shim-setup-failed\n"
                       "wifi_companion_start.reason=private-property-service-socket-not-ready\n"
                       "wifi_companion_start.end=1\n");
        *child_exit_code = 124;
        return 0;
    }
    for (size_t i = 0; i < child_count; i++) {
        if (service74_gate_required &&
            (int)i > service74_gate_after_index &&
            !service74_gate_open) {
            break;
        }
        if (composite_spawn_child(cfg, paths, &children[i], stdout_buf) < 0) {
            composite_cleanup_children(children, active_child_count, stdout_buf, stderr_buf);
            stop_property_service_shim(&property_shim, paths, stdout_buf);
            append_format(stdout_buf,
                          "wifi_companion_start.result=manual-review-required\n"
                          "wifi_companion_start.reason=%s-spawn-failed\n"
                          "wifi_companion_start.end=1\n",
                          children[i].name);
            return -1;
        }
        active_child_count = i + 1U;
        if (children[i].identity == COMPOSITE_ID_SERVICE_MANAGER ||
            children[i].identity == COMPOSITE_ID_VND_SERVICE_MANAGER) {
            service_manager_started = true;
        }
        if (append_format(stdout_buf,
                          "wifi_companion_start.child.%s.start_order=%zu\n",
                          children[i].name,
                          i + 1U) < 0) {
            composite_cleanup_children(children, active_child_count, stdout_buf, stderr_buf);
            stop_property_service_shim(&property_shim, paths, stdout_buf);
            return -1;
        }
        if (android_order_post_sysmon_observer) {
            usleep(i < 3 ? 50000 : 200000);
        } else if ((qrtr_first_service_manager ||
                    cnss_first_delayed_service_manager ||
                    service74_gate_required) && i == 0) {
            usleep(1000000);
        } else if (service74_gate_required && (int)i == service74_gate_after_index) {
            long gate_elapsed_ms = 0;

            if (wait_for_service74_gate(stdout_buf,
                                        service74_gate_baseline_count,
                                        service74_gate_baseline_available,
                                        service74_gate_target_180,
                                        service74_gate_target_sysmon_qmi,
                                        &service74_gate_open,
                                        &gate_elapsed_ms) < 0) {
                composite_cleanup_children(children, active_child_count, stdout_buf, stderr_buf);
                stop_property_service_shim(&property_shim, paths, stdout_buf);
                return -1;
            }
            if (!service74_gate_open) {
                break;
            }
            if (append_wifi_cnss2_focus_capture(stdout_buf, "service74_open") < 0) {
                composite_cleanup_children(children, active_child_count, stdout_buf, stderr_buf);
                stop_property_service_shim(&property_shim, paths, stdout_buf);
                return -1;
            }
        } else if ((service74_gated_vnd_readiness ||
                    service74_gated_cnss_retry ||
                    service74_gated_peripheral_manager_any ||
                    service74_gated_android_userspace_retry ||
                    service74_gated_registry_snapshot) &&
                   vndservicemanager_index >= 0 &&
                   (int)i == vndservicemanager_index) {
            bool vnd_ready = false;
            bool initial_cleanup_safe = service74_gated_peripheral_manager_provider_first_cnss;

            usleep(A90_VNDSERVICEMANAGER_READY_SETTLE_MS * 1000L);
            composite_capture_observable_children(&children[i], 1, stdout_buf);
            if (cnss_initial_index >= 0) {
                composite_capture_observable_children(&children[cnss_initial_index], 1, stdout_buf);
                if (service74_gated_registry_capture &&
                    append_wifi_registry_context_snapshot(stdout_buf,
                                                          "before_initial_cnss_cleanup",
                                                          paths,
                                                          children,
                                                          active_child_count) < 0) {
                    composite_cleanup_children(children, active_child_count, stdout_buf, stderr_buf);
                    stop_property_service_shim(&property_shim, paths, stdout_buf);
                    return -1;
                }
                composite_cleanup_children(&children[cnss_initial_index], 1, stdout_buf, stderr_buf);
                initial_cleanup_safe = composite_child_postflight_safe(&children[cnss_initial_index]);
            }
            vnd_ready = children[i].observable &&
                        !children[i].child_done &&
                        children[i].fd_summary_captured;
            if (append_format(stdout_buf,
                              "wifi_companion_start.vndservicemanager_readiness.settle_done=1\n"
                              "wifi_companion_start.vndservicemanager_readiness.child_index=%zu\n"
                              "wifi_companion_start.vndservicemanager_readiness.observable=%d\n"
                              "wifi_companion_start.vndservicemanager_readiness.fd_summary_captured=%d\n"
                              "wifi_companion_start.vndservicemanager_readiness.ready=%d\n"
                              "wifi_companion_start.initial_cnss_daemon.suppressed=%d\n"
                              "wifi_companion_start.initial_cnss_daemon.index=%d\n"
                              "wifi_companion_start.initial_cnss_daemon.observable=%d\n"
                              "wifi_companion_start.initial_cnss_daemon.cleanup_safe=%d\n"
                              "wifi_companion_start.cnss_retry.initial_index=%d\n"
                              "wifi_companion_start.cnss_retry.initial_observable=%d\n"
                              "wifi_companion_start.cnss_retry.initial_cleanup_safe=%d\n"
                              "wifi_companion_start.registry_snapshot.before_initial_cnss_cleanup=%d\n",
                              i,
                              children[i].observable ? 1 : 0,
                              children[i].fd_summary_captured ? 1 : 0,
                              vnd_ready ? 1 : 0,
                              service74_gated_peripheral_manager_provider_first_cnss ? 1 : 0,
                              cnss_initial_index,
                              (cnss_initial_index >= 0 &&
                               children[cnss_initial_index].observable) ? 1 : 0,
                              initial_cleanup_safe ? 1 : 0,
                              (service74_gated_cnss_retry ||
                               service74_gated_peripheral_manager_any_retry ||
                               service74_gated_android_userspace_retry) ? cnss_initial_index : -1,
                              ((service74_gated_cnss_retry ||
                                service74_gated_peripheral_manager_any_retry ||
                                service74_gated_android_userspace_retry) &&
                               cnss_initial_index >= 0 &&
                               children[cnss_initial_index].observable) ? 1 : 0,
                              ((service74_gated_cnss_retry ||
                                service74_gated_peripheral_manager_any_retry ||
                                service74_gated_android_userspace_retry) && initial_cleanup_safe) ? 1 : 0,
                              service74_gated_registry_capture ? 1 : 0) < 0) {
                composite_cleanup_children(children, active_child_count, stdout_buf, stderr_buf);
                stop_property_service_shim(&property_shim, paths, stdout_buf);
                return -1;
            }
            if (service74_gated_registry_capture &&
                append_wifi_registry_context_snapshot(stdout_buf,
                                                      "after_initial_cnss_cleanup",
                                                      paths,
                                                      children,
                                                      active_child_count) < 0) {
                composite_cleanup_children(children, active_child_count, stdout_buf, stderr_buf);
                stop_property_service_shim(&property_shim, paths, stdout_buf);
                return -1;
            }
            if (!vnd_ready || !initial_cleanup_safe) {
                break;
            }
        } else if (peripheral_manager_init_contract &&
                   streq(children[i].name, "per_proxy_helper")) {
            usleep(500000);
            composite_capture_observable_children(&children[i], 1, stdout_buf);
            if (append_format(stdout_buf,
                              "wifi_companion_start.peripheral_manager.per_proxy_helper.oneshot=1\n"
                              "wifi_companion_start.peripheral_manager.per_proxy_helper.observable=%d\n"
                              "wifi_companion_start.peripheral_manager.per_proxy_helper.fd_summary_captured=%d\n"
                              "wifi_companion_start.peripheral_manager.per_proxy_helper.ready=%d\n",
                              children[i].observable ? 1 : 0,
                              children[i].fd_summary_captured ? 1 : 0,
                              (children[i].observable &&
                               !children[i].child_done &&
                               children[i].fd_summary_captured) ? 1 : 0) < 0) {
                composite_cleanup_children(children, active_child_count, stdout_buf, stderr_buf);
                stop_property_service_shim(&property_shim, paths, stdout_buf);
                return -1;
            }
        } else if ((service74_gated_peripheral_manager_any ||
                    peripheral_manager_node_parity) &&
                   streq(children[i].name, "per_mgr")) {
            bool per_mgr_ready;

            usleep(1000000);
            composite_capture_observable_children(&children[i], 1, stdout_buf);
            per_mgr_ready = children[i].observable &&
                            !children[i].child_done &&
                            children[i].fd_summary_captured;
            if (append_format(stdout_buf,
                              "wifi_companion_start.peripheral_manager.per_mgr.observable=%d\n"
                              "wifi_companion_start.peripheral_manager.per_mgr.fd_summary_captured=%d\n"
                              "wifi_companion_start.peripheral_manager.per_mgr.ready=%d\n",
                              children[i].observable ? 1 : 0,
                              children[i].fd_summary_captured ? 1 : 0,
                              per_mgr_ready ? 1 : 0) < 0) {
                composite_cleanup_children(children, active_child_count, stdout_buf, stderr_buf);
                stop_property_service_shim(&property_shim, paths, stdout_buf);
                return -1;
            }
            if (peripheral_manager_init_contract &&
                append_format(stdout_buf,
                              "wifi_companion_start.peripheral_manager.init.svc.vendor.per_mgr=%s\n"
                              "wifi_companion_start.peripheral_manager.per_proxy_start_gate=init.svc.vendor.per_mgr=running\n"
                              "wifi_companion_start.peripheral_manager.per_proxy_start_gate.open=%d\n",
                              per_mgr_ready ? "running" : "not-running",
                              per_mgr_ready ? 1 : 0) < 0) {
                composite_cleanup_children(children, active_child_count, stdout_buf, stderr_buf);
                stop_property_service_shim(&property_shim, paths, stdout_buf);
                return -1;
            }
            if (!children[i].observable || children[i].child_done) {
                break;
            }
            if (service74_gated_peripheral_manager_registry_retry &&
                append_wifi_registry_context_snapshot(stdout_buf,
                                                      "after_per_mgr_probe",
                                                      paths,
                                                      children,
                                                      active_child_count) < 0) {
                composite_cleanup_children(children, active_child_count, stdout_buf, stderr_buf);
                stop_property_service_shim(&property_shim, paths, stdout_buf);
                return -1;
            }
            if (service74_gated_peripheral_manager_vndservice_query &&
                append_vndservice_query(stdout_buf,
                                        stderr_buf,
                                        cfg,
                                        paths,
                                        "after_per_mgr_probe",
                                        3000) < 0) {
                composite_cleanup_children(children, active_child_count, stdout_buf, stderr_buf);
                stop_property_service_shim(&property_shim, paths, stdout_buf);
                return -1;
            }
        } else if ((service74_gated_peripheral_manager_any ||
                    peripheral_manager_node_parity) &&
                   streq(children[i].name, "per_proxy")) {
            usleep(1000000);
            composite_capture_observable_children(&children[i], 1, stdout_buf);
            if (append_format(stdout_buf,
                              "wifi_companion_start.peripheral_manager.per_proxy.observable=%d\n"
                              "wifi_companion_start.peripheral_manager.per_proxy.fd_summary_captured=%d\n"
                              "wifi_companion_start.peripheral_manager.per_proxy.ready=%d\n",
                              children[i].observable ? 1 : 0,
                              children[i].fd_summary_captured ? 1 : 0,
                              (children[i].observable &&
                               !children[i].child_done &&
                               children[i].fd_summary_captured) ? 1 : 0) < 0) {
                composite_cleanup_children(children, active_child_count, stdout_buf, stderr_buf);
                stop_property_service_shim(&property_shim, paths, stdout_buf);
                return -1;
            }
            if (!children[i].observable || children[i].child_done) {
                break;
            }
            if (service74_gated_peripheral_manager_registry_retry &&
                append_wifi_registry_context_snapshot(stdout_buf,
                                                      "after_per_proxy_probe",
                                                      paths,
                                                      children,
                                                      active_child_count) < 0) {
                composite_cleanup_children(children, active_child_count, stdout_buf, stderr_buf);
                stop_property_service_shim(&property_shim, paths, stdout_buf);
                return -1;
            }
            if (service74_gated_peripheral_manager_vndservice_query &&
                append_vndservice_query(stdout_buf,
                                        stderr_buf,
                                        cfg,
                                        paths,
                                        "after_per_proxy_probe",
                                        3000) < 0) {
                composite_cleanup_children(children, active_child_count, stdout_buf, stderr_buf);
                stop_property_service_shim(&property_shim, paths, stdout_buf);
                return -1;
            }
        } else if (cnss_first_delayed_service_manager && i == 5) {
            usleep(2000000);
        } else if (service74_gated_android_userspace_retry &&
                   (streq(children[i].name, "wifi_hal_legacy") ||
                    streq(children[i].name, "wifi_hal_ext") ||
                    streq(children[i].name, "wificond"))) {
            usleep(300000);
        } else if (service74_gated_android_userspace_registry_retry &&
                   streq(children[i].name, "cnss_daemon_retry")) {
            usleep(500000);
            if (append_wifi_registry_context_snapshot(stdout_buf,
                                                      "after_cnss_retry_spawn",
                                                      paths,
                                                      children,
                                                      active_child_count) < 0) {
                composite_cleanup_children(children, active_child_count, stdout_buf, stderr_buf);
                stop_property_service_shim(&property_shim, paths, stdout_buf);
                return -1;
            }
        } else if ((qrtr_first_service_manager && i == 6) ||
                   (!qrtr_first_service_manager &&
                    !cnss_first_delayed_service_manager &&
                    !service74_gated_any &&
                    ((with_service_manager &&
                      ((with_vnd_service_manager && i == 2) ||
                       (!with_vnd_service_manager && i == 1))) ||
                     (!with_service_manager && i == 0)))) {
            usleep(300000);
        } else {
            usleep(200000);
        }
    }
    if (append_format(stdout_buf,
                      "wifi_companion_start.child_started=%zu\n"
                      "wifi_companion_start.service74_gate.open=%d\n"
                      "wifi_companion_start.service_manager_started=%d\n",
                      active_child_count,
                      service74_gate_open ? 1 : 0,
                      service_manager_started ? 1 : 0) < 0) {
        composite_cleanup_children(children, active_child_count, stdout_buf, stderr_buf);
        stop_property_service_shim(&property_shim, paths, stdout_buf);
        return -1;
    }
    if (append_qipcrtr_protocol_summary(stdout_buf, "wifi_companion_start.net_after_spawn") < 0) {
        composite_cleanup_children(children, active_child_count, stdout_buf, stderr_buf);
        stop_property_service_shim(&property_shim, paths, stdout_buf);
        return -1;
    }
    if (cfg->allow_service_notifier_listener_probe &&
        append_companion_service_notifier_listener_probe(stdout_buf, cfg) < 0) {
        composite_cleanup_children(children, active_child_count, stdout_buf, stderr_buf);
        stop_property_service_shim(&property_shim, paths, stdout_buf);
        return -1;
    }
    deadline = monotonic_ms() + cfg->timeout_sec * 1000L;
    if (composite_poll_children(children, active_child_count, stdout_buf, stderr_buf, deadline, timed_out) < 0) {
        composite_cleanup_children(children, active_child_count, stdout_buf, stderr_buf);
        stop_property_service_shim(&property_shim, paths, stdout_buf);
        return -1;
    }
    if (append_qipcrtr_protocol_summary(stdout_buf, "wifi_companion_start.net_window") < 0) {
        composite_cleanup_children(children, active_child_count, stdout_buf, stderr_buf);
        stop_property_service_shim(&property_shim, paths, stdout_buf);
        return -1;
    }
    if ((service74_gated_android_userspace_registry_retry ||
         service74_gated_peripheral_manager_registry_retry) &&
        append_wifi_registry_context_snapshot(stdout_buf,
                                              "window",
                                              paths,
                                              children,
                                              active_child_count) < 0) {
        composite_cleanup_children(children, active_child_count, stdout_buf, stderr_buf);
        stop_property_service_shim(&property_shim, paths, stdout_buf);
        return -1;
    }
    if (append_wifi_window_surface_capture(stdout_buf, "window") < 0) {
        composite_cleanup_children(children, active_child_count, stdout_buf, stderr_buf);
        stop_property_service_shim(&property_shim, paths, stdout_buf);
        return -1;
    }
    if (append_wifi_cnss2_focus_capture(stdout_buf, "window") < 0) {
        composite_cleanup_children(children, active_child_count, stdout_buf, stderr_buf);
        stop_property_service_shim(&property_shim, paths, stdout_buf);
        return -1;
    }
    if (append_companion_qrtr_wlfw_readback(stdout_buf, cfg) < 0) {
        composite_cleanup_children(children, active_child_count, stdout_buf, stderr_buf);
        stop_property_service_shim(&property_shim, paths, stdout_buf);
        return -1;
    }
    if (cfg->allow_servloc_domain_list_probe &&
        append_companion_servloc_domain_list_probe(stdout_buf, cfg) < 0) {
        composite_cleanup_children(children, active_child_count, stdout_buf, stderr_buf);
        stop_property_service_shim(&property_shim, paths, stdout_buf);
        return -1;
    }
    {
        bool protocols_captured = false;
        bool netlink_captured = false;
        bool qrtr_captured = false;
        bool unix_captured = false;
        bool packet_captured = false;
        bool tcp_captured = false;
        bool tcp6_captured = false;
        bool udp_captured = false;
        bool udp6_captured = false;
        bool raw_captured = false;
        bool raw6_captured = false;
        bool sockstat_captured = false;
        bool sockstat6_captured = false;

        if (append_proc_file_capture_named(stdout_buf,
                                           getpid(),
                                           "net/protocols",
                                           "wifi_companion_net_protocols",
                                           8192,
                                           &protocols_captured) < 0 ||
            append_proc_file_capture_named(stdout_buf,
                                           getpid(),
                                           "net/netlink",
                                           "wifi_companion_net_netlink",
                                           16384,
                                           &netlink_captured) < 0 ||
            append_proc_file_capture_named(stdout_buf,
                                           getpid(),
                                           "net/qrtr",
                                           "wifi_companion_net_qrtr",
                                           8192,
                                           &qrtr_captured) < 0 ||
            append_proc_file_capture_named(stdout_buf,
                                           getpid(),
                                           "net/unix",
                                           "wifi_companion_net_unix",
                                           65536,
                                           &unix_captured) < 0 ||
            append_proc_file_capture_named(stdout_buf,
                                           getpid(),
                                           "net/packet",
                                           "wifi_companion_net_packet",
                                           16384,
                                           &packet_captured) < 0 ||
            append_proc_file_capture_named(stdout_buf,
                                           getpid(),
                                           "net/tcp",
                                           "wifi_companion_net_tcp",
                                           16384,
                                           &tcp_captured) < 0 ||
            append_proc_file_capture_named(stdout_buf,
                                           getpid(),
                                           "net/tcp6",
                                           "wifi_companion_net_tcp6",
                                           16384,
                                           &tcp6_captured) < 0 ||
            append_proc_file_capture_named(stdout_buf,
                                           getpid(),
                                           "net/udp",
                                           "wifi_companion_net_udp",
                                           16384,
                                           &udp_captured) < 0 ||
            append_proc_file_capture_named(stdout_buf,
                                           getpid(),
                                           "net/udp6",
                                           "wifi_companion_net_udp6",
                                           16384,
                                           &udp6_captured) < 0 ||
            append_proc_file_capture_named(stdout_buf,
                                           getpid(),
                                           "net/raw",
                                           "wifi_companion_net_raw",
                                           8192,
                                           &raw_captured) < 0 ||
            append_proc_file_capture_named(stdout_buf,
                                           getpid(),
                                           "net/raw6",
                                           "wifi_companion_net_raw6",
                                           8192,
                                           &raw6_captured) < 0 ||
            append_proc_file_capture_named(stdout_buf,
                                           getpid(),
                                           "net/sockstat",
                                           "wifi_companion_net_sockstat",
                                           8192,
                                           &sockstat_captured) < 0 ||
            append_proc_file_capture_named(stdout_buf,
                                           getpid(),
                                           "net/sockstat6",
                                           "wifi_companion_net_sockstat6",
                                           8192,
                                           &sockstat6_captured) < 0 ||
            append_format(stdout_buf,
                          "wifi_companion_start.net_window.protocols_captured=%d\n"
                          "wifi_companion_start.net_window.netlink_captured=%d\n"
                          "wifi_companion_start.net_window.qrtr_captured=%d\n"
                          "wifi_companion_start.net_window.unix_captured=%d\n"
                          "wifi_companion_start.net_window.packet_captured=%d\n"
                          "wifi_companion_start.net_window.tcp_captured=%d\n"
                          "wifi_companion_start.net_window.tcp6_captured=%d\n"
                          "wifi_companion_start.net_window.udp_captured=%d\n"
                          "wifi_companion_start.net_window.udp6_captured=%d\n"
                          "wifi_companion_start.net_window.raw_captured=%d\n"
                          "wifi_companion_start.net_window.raw6_captured=%d\n"
                          "wifi_companion_start.net_window.sockstat_captured=%d\n"
                          "wifi_companion_start.net_window.sockstat6_captured=%d\n",
                          protocols_captured ? 1 : 0,
                          netlink_captured ? 1 : 0,
                          qrtr_captured ? 1 : 0,
                          unix_captured ? 1 : 0,
                          packet_captured ? 1 : 0,
                          tcp_captured ? 1 : 0,
                          tcp6_captured ? 1 : 0,
                          udp_captured ? 1 : 0,
                          udp6_captured ? 1 : 0,
                          raw_captured ? 1 : 0,
                          raw6_captured ? 1 : 0,
                          sockstat_captured ? 1 : 0,
                          sockstat6_captured ? 1 : 0) < 0) {
            composite_cleanup_children(children, active_child_count, stdout_buf, stderr_buf);
            stop_property_service_shim(&property_shim, paths, stdout_buf);
            return -1;
        }
    }
    composite_capture_observable_children(children, active_child_count, stdout_buf);
    if (peripheral_manager_init_contract &&
        append_literal(stdout_buf,
                       "wifi_companion_start.peripheral_manager.shutdown_stop.vendor_per_proxy=1\n"
                       "wifi_companion_start.peripheral_manager.shutdown_stop.cleanup_before_sys.shutdown.requested=1\n") < 0) {
        composite_cleanup_children(children, active_child_count, stdout_buf, stderr_buf);
        stop_property_service_shim(&property_shim, paths, stdout_buf);
        return -1;
    }
    composite_cleanup_children(children, active_child_count, stdout_buf, stderr_buf);
    stop_property_service_shim(&property_shim, paths, stdout_buf);
    if (append_qipcrtr_protocol_summary(stdout_buf, "wifi_companion_start.net_after_cleanup") < 0) {
        return -1;
    }

    for (size_t i = 0; i < active_child_count; i++) {
        bool safe = composite_child_postflight_safe(&children[i]);

        if (!safe) {
            all_postflight_safe = false;
        }
        if (!children[i].observable) {
            all_observable = false;
        }
        if (composite_child_runtime_gap(&children[i], *timed_out)) {
            any_runtime_gap = true;
            if (*child_exit_code < 0 && children[i].exit_code >= 0) {
                *child_exit_code = children[i].exit_code;
            }
            if (*child_signal == 0 && children[i].signal != 0) {
                *child_signal = children[i].signal;
            }
        }
        if (append_format(stdout_buf,
                          "wifi_companion_start.child.%s.observable=%d\n"
                          "wifi_companion_start.child.%s.exited=%d\n"
                          "wifi_companion_start.child.%s.exit_code=%d\n"
                          "wifi_companion_start.child.%s.signal=%d\n"
                          "wifi_companion_start.child.%s.term_sent=%d\n"
                          "wifi_companion_start.child.%s.kill_sent=%d\n"
                          "wifi_companion_start.child.%s.reaped=%d\n"
                          "wifi_companion_start.child.%s.proc_status_captured=%d\n"
                          "wifi_companion_start.child.%s.proc_attr_current_captured=%d\n"
                          "wifi_companion_start.child.%s.fd_summary_captured=%d\n"
                          "wifi_companion_start.child.%s.maps_summary_captured=%d\n"
                          "wifi_companion_start.child.%s.stall_snapshot_captured=%d\n"
                          "wifi_companion_start.child.%s.postflight_safe=%d\n",
                          children[i].name,
                          children[i].observable ? 1 : 0,
                          children[i].name,
                          children[i].child_done ? 1 : 0,
                          children[i].name,
                          children[i].exit_code,
                          children[i].name,
                          children[i].signal,
                          children[i].name,
                          children[i].term_sent ? 1 : 0,
                          children[i].name,
                          children[i].kill_sent ? 1 : 0,
                          children[i].name,
                          children[i].reaped ? 1 : 0,
                          children[i].name,
                          children[i].proc_status_captured ? 1 : 0,
                          children[i].name,
                          children[i].proc_attr_current_captured ? 1 : 0,
                          children[i].name,
                          children[i].fd_summary_captured ? 1 : 0,
                          children[i].name,
                          children[i].maps_summary_captured ? 1 : 0,
                          children[i].name,
                          children[i].stall_snapshot_captured ? 1 : 0,
                          children[i].name,
                          safe ? 1 : 0) < 0) {
            return -1;
        }
    }
    if (*child_exit_code < 0 && *child_signal == 0) {
        *child_exit_code = 0;
    }
    if (append_format(stdout_buf,
                      "wifi_companion_start.timed_out=%d\n"
                      "wifi_companion_start.all_observable=%d\n"
                      "wifi_companion_start.all_postflight_safe=%d\n",
                      *timed_out ? 1 : 0,
                      all_observable ? 1 : 0,
                      all_postflight_safe ? 1 : 0) < 0) {
        return -1;
    }
    if (!all_postflight_safe) {
        append_literal(stdout_buf,
                       "wifi_companion_start.result=start-only-reboot-required\n"
                       "wifi_companion_start.reason=process-not-proven-stopped\n");
    } else if (any_runtime_gap) {
        append_literal(stdout_buf,
                       "wifi_companion_start.result=start-only-runtime-gap\n"
                       "wifi_companion_start.reason=child-exited-before-observe-window\n");
    } else if (*timed_out && all_observable) {
        append_literal(stdout_buf,
                       "wifi_companion_start.result=companion-window-pass\n"
                       "wifi_companion_start.reason=all-companions-observed-until-timeout-clean-stop\n");
    } else {
        append_literal(stdout_buf,
                       "wifi_companion_start.result=manual-review-required\n"
                       "wifi_companion_start.reason=unclassified-lifecycle-state\n");
    }
    append_literal(stdout_buf, "wifi_companion_start.end=1\n");
    return 0;
}

static int run_rmt_storage_start_only_guarded(const struct config *cfg,
                                              const struct paths *paths,
                                              struct buffer *stdout_buf,
                                              struct buffer *stderr_buf,
                                              int *child_exit_code,
                                              int *child_signal,
                                              bool *timed_out) {
    struct composite_child child;
    struct property_service_shim property_shim;
    bool safe;
    bool runtime_gap = false;
    long deadline;

    *child_exit_code = -1;
    *child_signal = 0;
    *timed_out = false;
    composite_child_init(&child,
                         "rmt_storage",
                         "/vendor/bin/rmt_storage",
                         COMPOSITE_ID_RMT_STORAGE);

    if (append_literal(stdout_buf,
                       "rmt_storage_start.begin=1\n"
                       "rmt_storage_start.mode=guarded\n"
                       "rmt_storage_start.argv=/vendor/bin/rmt_storage\n"
                       "rmt_storage_start.service_manager=0\n"
                       "rmt_storage_start.wifi_hal=0\n"
                       "rmt_storage_start.cnss_daemon=0\n"
                       "rmt_storage_start.tftp_server=0\n"
                       "rmt_storage_start.pd_mapper=0\n"
                       "rmt_storage_start.qcwlanstate_write=0\n"
                       "rmt_storage_start.scan_connect_linkup=0\n"
                       "rmt_storage_start.external_ping=0\n") < 0) {
        return -1;
    }
    if (!cfg->allow_wifi_companion_start_only) {
        if (append_literal(stdout_buf,
                           "rmt_storage_start.allowed=0\n"
                           "rmt_storage_start.exec_attempted=0\n"
                           "rmt_storage_start.child_started=0\n"
                           "rmt_storage_start.result=start-only-blocked\n"
                           "rmt_storage_start.reason=missing-rmt-allow-flag\n"
                           "rmt_storage_start.end=1\n") < 0) {
            return -1;
        }
        *child_exit_code = 0;
        return 0;
    }
    if (append_literal(stdout_buf,
                       "rmt_storage_start.allowed=1\n"
                       "rmt_storage_start.exec_attempted=1\n") < 0) {
        return -1;
    }
    if (start_property_service_shim(cfg, paths, &property_shim, stdout_buf) < 0) {
        return -1;
    }
    if (property_service_shim_needed(cfg) && !property_shim.started) {
        append_literal(stdout_buf,
                       "rmt_storage_start.child_started=0\n"
                       "rmt_storage_start.result=property-service-shim-setup-failed\n"
                       "rmt_storage_start.reason=private-property-service-socket-not-ready\n"
                       "rmt_storage_start.end=1\n");
        *child_exit_code = 124;
        return 0;
    }
    if (composite_spawn_child(cfg, paths, &child, stdout_buf) < 0) {
        composite_cleanup_children(&child, 1, stdout_buf, stderr_buf);
        stop_property_service_shim(&property_shim, paths, stdout_buf);
        append_literal(stdout_buf,
                       "rmt_storage_start.result=manual-review-required\n"
                       "rmt_storage_start.reason=rmt-storage-spawn-failed\n"
                       "rmt_storage_start.end=1\n");
        return -1;
    }
    if (append_literal(stdout_buf,
                       "rmt_storage_start.child.rmt_storage.start_order=1\n"
                       "rmt_storage_start.child_started=1\n") < 0) {
        composite_cleanup_children(&child, 1, stdout_buf, stderr_buf);
        stop_property_service_shim(&property_shim, paths, stdout_buf);
        return -1;
    }
    deadline = monotonic_ms() + cfg->timeout_sec * 1000L;
    if (composite_poll_children(&child, 1, stdout_buf, stderr_buf, deadline, timed_out) < 0) {
        composite_cleanup_children(&child, 1, stdout_buf, stderr_buf);
        stop_property_service_shim(&property_shim, paths, stdout_buf);
        return -1;
    }
    composite_capture_observable_children(&child, 1, stdout_buf);
    composite_cleanup_children(&child, 1, stdout_buf, stderr_buf);
    stop_property_service_shim(&property_shim, paths, stdout_buf);

    safe = composite_child_postflight_safe(&child);
    if (composite_child_runtime_gap(&child, *timed_out)) {
        runtime_gap = true;
        if (child.exit_code >= 0) {
            *child_exit_code = child.exit_code;
        }
        if (child.signal != 0) {
            *child_signal = child.signal;
        }
    }
    if (*child_exit_code < 0 && *child_signal == 0) {
        *child_exit_code = 0;
    }
    if (append_format(stdout_buf,
                      "rmt_storage_start.child.rmt_storage.observable=%d\n"
                      "rmt_storage_start.child.rmt_storage.exited=%d\n"
                      "rmt_storage_start.child.rmt_storage.exit_code=%d\n"
                      "rmt_storage_start.child.rmt_storage.signal=%d\n"
                      "rmt_storage_start.child.rmt_storage.term_sent=%d\n"
                      "rmt_storage_start.child.rmt_storage.kill_sent=%d\n"
                      "rmt_storage_start.child.rmt_storage.reaped=%d\n"
                      "rmt_storage_start.child.rmt_storage.proc_status_captured=%d\n"
                      "rmt_storage_start.child.rmt_storage.proc_attr_current_captured=%d\n"
                      "rmt_storage_start.child.rmt_storage.fd_summary_captured=%d\n"
                      "rmt_storage_start.child.rmt_storage.maps_summary_captured=%d\n"
                      "rmt_storage_start.child.rmt_storage.postflight_safe=%d\n"
                      "rmt_storage_start.timed_out=%d\n"
                      "rmt_storage_start.all_observable=%d\n"
                      "rmt_storage_start.all_postflight_safe=%d\n",
                      child.observable ? 1 : 0,
                      child.child_done ? 1 : 0,
                      child.exit_code,
                      child.signal,
                      child.term_sent ? 1 : 0,
                      child.kill_sent ? 1 : 0,
                      child.reaped ? 1 : 0,
                      child.proc_status_captured ? 1 : 0,
                      child.proc_attr_current_captured ? 1 : 0,
                      child.fd_summary_captured ? 1 : 0,
                      child.maps_summary_captured ? 1 : 0,
                      safe ? 1 : 0,
                      *timed_out ? 1 : 0,
                      child.observable ? 1 : 0,
                      safe ? 1 : 0) < 0) {
        return -1;
    }
    if (!safe) {
        append_literal(stdout_buf,
                       "rmt_storage_start.result=start-only-reboot-required\n"
                       "rmt_storage_start.reason=process-not-proven-stopped\n");
    } else if (runtime_gap) {
        append_literal(stdout_buf,
                       "rmt_storage_start.result=start-only-runtime-gap\n"
                       "rmt_storage_start.reason=child-exited-before-observe-window\n");
    } else if (*timed_out && child.observable) {
        append_literal(stdout_buf,
                       "rmt_storage_start.result=rmt-window-pass\n"
                       "rmt_storage_start.reason=rmt-storage-observed-until-timeout-clean-stop\n");
    } else {
        append_literal(stdout_buf,
                       "rmt_storage_start.result=manual-review-required\n"
                       "rmt_storage_start.reason=unclassified-lifecycle-state\n");
    }
    append_literal(stdout_buf, "rmt_storage_start.end=1\n");
    return 0;
}

static void property_service_shim_init(struct property_service_shim *shim) {
    memset(shim, 0, sizeof(*shim));
    shim->pid = -1;
    shim->record_fd = -1;
    shim->exit_code = -1;
}

static bool property_service_shim_needed(const struct config *cfg) {
    if (cfg->property_root == NULL) {
        return false;
    }
    if (is_wifi_hal_composite_mode(cfg->mode)) {
        return cfg->allow_service_manager_start_only &&
               cfg->allow_wifi_hal_start_only;
    }
    if (is_wifi_companion_hal_order_start_only_mode(cfg->mode)) {
        return cfg->allow_wifi_companion_start_only &&
               cfg->allow_service_manager_start_only &&
               cfg->allow_wifi_hal_start_only;
    }
    if (is_rmt_storage_start_only_mode(cfg->mode) ||
        is_wifi_companion_any_start_only_mode(cfg->mode)) {
        return cfg->allow_wifi_companion_start_only;
    }
    return false;
}

static int read_full_timeout(int fd, void *data, size_t len, long deadline) {
    unsigned char *bytes = data;
    size_t done = 0;

    while (done < len) {
        int timeout_ms = (int)(deadline - monotonic_ms());
        struct pollfd pfd;
        int poll_rc;
        ssize_t nread;

        if (timeout_ms <= 0) {
            errno = ETIMEDOUT;
            return -1;
        }
        memset(&pfd, 0, sizeof(pfd));
        pfd.fd = fd;
        pfd.events = POLLIN;
        poll_rc = poll(&pfd, 1, timeout_ms);
        if (poll_rc == 0) {
            errno = ETIMEDOUT;
            return -1;
        }
        if (poll_rc < 0) {
            if (errno == EINTR) {
                continue;
            }
            return -1;
        }
        nread = read(fd, bytes + done, len - done);
        if (nread < 0) {
            if (errno == EINTR) {
                continue;
            }
            return -1;
        }
        if (nread == 0) {
            errno = ECONNRESET;
            return -1;
        }
        done += (size_t)nread;
    }
    return 0;
}

static void sanitize_record_value(const char *in, char *out, size_t out_size) {
    size_t out_pos = 0;

    if (out_size == 0) {
        return;
    }
    for (size_t i = 0; in != NULL && in[i] != '\0' && out_pos + 1 < out_size; i++) {
        unsigned char c = (unsigned char)in[i];

        if (c < 0x20 || c == 0x7f || c == '=' || c == '\n' || c == '\r') {
            out[out_pos++] = '_';
        } else {
            out[out_pos++] = (char)c;
        }
    }
    out[out_pos] = '\0';
}

static int property_shim_read_string(int fd, char *out, size_t out_size, long deadline) {
    uint32_t len = 0;

    if (out_size == 0) {
        errno = EINVAL;
        return -1;
    }
    if (read_full_timeout(fd, &len, sizeof(len), deadline) < 0) {
        return -1;
    }
    if (len >= out_size) {
        errno = EOVERFLOW;
        return -1;
    }
    if (len > 0 && read_full_timeout(fd, out, len, deadline) < 0) {
        return -1;
    }
    out[len] = '\0';
    return 0;
}

static int property_shim_read_legacy_setprop(int fd,
                                             char *name,
                                             size_t name_size,
                                             char *value,
                                             size_t value_size,
                                             long deadline) {
    char legacy_name[A90_PROP_LEGACY_NAME_MAX];
    char legacy_value[A90_PROP_LEGACY_VALUE_MAX];

    if (name_size == 0 || value_size == 0) {
        errno = EINVAL;
        return -1;
    }
    if (read_full_timeout(fd, legacy_name, sizeof(legacy_name), deadline) < 0 ||
        read_full_timeout(fd, legacy_value, sizeof(legacy_value), deadline) < 0) {
        return -1;
    }
    legacy_name[sizeof(legacy_name) - 1] = '\0';
    legacy_value[sizeof(legacy_value) - 1] = '\0';
    snprintf(name, name_size, "%s", legacy_name);
    snprintf(value, value_size, "%s", legacy_value);
    return 0;
}

static void property_shim_record(int fd,
                                 int index,
                                 uint32_t cmd,
                                 const char *name,
                                 const char *value,
                                 uint32_t result,
                                 bool allowed) {
    char safe_name[A90_PROP_NAME_MAX];
    char safe_value[A90_PROP_VALUE_MAX];

    sanitize_record_value(name, safe_name, sizeof(safe_name));
    sanitize_record_value(value, safe_value, sizeof(safe_value));
    dprintf(fd,
            "wifi_hal_composite_start.property_service_shim.request.%d.cmd=0x%08x\n"
            "wifi_hal_composite_start.property_service_shim.request.%d.name=%s\n"
            "wifi_hal_composite_start.property_service_shim.request.%d.value=%s\n"
            "wifi_hal_composite_start.property_service_shim.request.%d.allowed=%d\n"
            "wifi_hal_composite_start.property_service_shim.request.%d.result=0x%08x\n",
            index,
            cmd,
            index,
            safe_name,
            index,
            safe_value,
            index,
            allowed ? 1 : 0,
            index,
            result);
}

static bool property_shim_set_allowed(const char *name,
                                      const char *value,
                                      bool allow_peripheral_shutdown_list) {
    return (streq(name, "hwservicemanager.ready") && streq(value, "true")) ||
           (streq(name, "ctl.stop") && streq(value, "vendor.rmt_storage")) ||
           (streq(name, "vendor.peripheral.SDX50M.state") && streq(value, "OFFLINE")) ||
           (streq(name, "vendor.peripheral.modem.state") && streq(value, "OFFLINE")) ||
           (allow_peripheral_shutdown_list &&
            streq(name, "vendor.peripheral.shutdown_critical_list") &&
            (streq(value, "SDX50M ") || streq(value, "SDX50M modem ")));
}

static uint32_t property_shim_handle_client(int client_fd,
                                            int record_fd,
                                            int *request_count,
                                            bool allow_peripheral_shutdown_list) {
    long deadline = monotonic_ms() + 2000L;
    uint32_t cmd = 0;
    uint32_t result = A90_PROP_ERROR_READ_CMD;
    char name[A90_PROP_NAME_MAX] = "";
    char value[A90_PROP_VALUE_MAX] = "";
    bool allowed = false;

    if (read_full_timeout(client_fd, &cmd, sizeof(cmd), deadline) < 0) {
        result = A90_PROP_ERROR_READ_CMD;
        write_all_fd(client_fd, &result, sizeof(result));
        return result;
    }
    if (cmd == A90_PROP_MSG_SETPROP) {
        if (property_shim_read_legacy_setprop(client_fd,
                                              name,
                                              sizeof(name),
                                              value,
                                              sizeof(value),
                                              deadline) < 0) {
            result = A90_PROP_ERROR_READ_DATA;
        } else if (property_shim_set_allowed(name, value, allow_peripheral_shutdown_list)) {
            allowed = true;
            result = A90_PROP_SUCCESS;
        } else {
            result = A90_PROP_ERROR_PERMISSION_DENIED;
        }
        (*request_count)++;
        property_shim_record(record_fd, *request_count, cmd, name, value, result, allowed);
        return result;
    }
    if (cmd == A90_PROP_MSG_SETPROP2) {
        if (property_shim_read_string(client_fd, name, sizeof(name), deadline) < 0 ||
            property_shim_read_string(client_fd, value, sizeof(value), deadline) < 0) {
            result = A90_PROP_ERROR_READ_DATA;
        } else if (property_shim_set_allowed(name, value, allow_peripheral_shutdown_list)) {
            allowed = true;
            result = A90_PROP_SUCCESS;
        } else {
            result = A90_PROP_ERROR_PERMISSION_DENIED;
        }
        (*request_count)++;
        property_shim_record(record_fd, *request_count, cmd, name, value, result, allowed);
        write_all_fd(client_fd, &result, sizeof(result));
        return result;
    }
    result = A90_PROP_ERROR_INVALID_CMD;
    (*request_count)++;
    property_shim_record(record_fd, *request_count, cmd, name, value, result, false);
    write_all_fd(client_fd, &result, sizeof(result));
    return result;
}

static void property_service_shim_child(int listen_fd,
                                        int record_fd,
                                        int timeout_sec,
                                        bool allow_peripheral_shutdown_list) {
    long deadline = monotonic_ms() + ((long)timeout_sec + 3L) * 1000L;
    int request_count = 0;

    signal(SIGPIPE, SIG_IGN);
    set_nonblock(listen_fd);
    dprintf(record_fd,
            "wifi_hal_composite_start.property_service_shim.child_started=1\n"
            "wifi_hal_composite_start.property_service_shim.protocol=PROP_MSG_SETPROP|PROP_MSG_SETPROP2\n"
            "wifi_hal_composite_start.property_service_shim.allow_peripheral_shutdown_list=%d\n"
            "wifi_hal_composite_start.property_service_shim.allowlist=hwservicemanager.ready:true,ctl.stop:vendor.rmt_storage,vendor.peripheral.SDX50M.state:OFFLINE,vendor.peripheral.modem.state:OFFLINE%s\n",
            allow_peripheral_shutdown_list ? 1 : 0,
            allow_peripheral_shutdown_list
                ? ",vendor.peripheral.shutdown_critical_list:SDX50M_|SDX50M_modem_"
                : "");
    while (monotonic_ms() < deadline && request_count < 16) {
        int timeout_ms = (int)(deadline - monotonic_ms());
        struct pollfd pfd;
        int client_fd;

        if (timeout_ms <= 0) {
            break;
        }
        memset(&pfd, 0, sizeof(pfd));
        pfd.fd = listen_fd;
        pfd.events = POLLIN;
        if (poll(&pfd, 1, timeout_ms) <= 0) {
            if (errno == EINTR) {
                continue;
            }
            break;
        }
        client_fd = accept4(listen_fd, NULL, NULL, SOCK_CLOEXEC);
        if (client_fd < 0) {
            if (errno == EINTR || errno == EAGAIN || errno == EWOULDBLOCK) {
                continue;
            }
            dprintf(record_fd,
                    "wifi_hal_composite_start.property_service_shim.accept_error=%s\n",
                    strerror(errno));
            break;
        }
        property_shim_handle_client(client_fd,
                                    record_fd,
                                    &request_count,
                                    allow_peripheral_shutdown_list);
        close(client_fd);
    }
    dprintf(record_fd,
            "wifi_hal_composite_start.property_service_shim.request_count=%d\n"
            "wifi_hal_composite_start.property_service_shim.child_end=1\n",
            request_count);
}

static int start_property_service_shim(const struct config *cfg,
                                       const struct paths *paths,
                                       struct property_service_shim *shim,
                                       struct buffer *stdout_buf) {
    int listen_fd = -1;
    int pipe_fds[2] = {-1, -1};
    struct sockaddr_un addr;
    size_t socket_len;

    property_service_shim_init(shim);
    if (!property_service_shim_needed(cfg)) {
        return append_literal(stdout_buf,
                              "wifi_hal_composite_start.property_service_shim.mode=disabled\n"
                              "wifi_hal_composite_start.property_service_shim.started=0\n");
    }
    if (mkdir_p(paths->dev_socket, 0755) < 0) {
        return append_format(stdout_buf,
                             "wifi_hal_composite_start.property_service_shim.mode=auto\n"
                             "wifi_hal_composite_start.property_service_shim.started=0\n"
                             "wifi_hal_composite_start.property_service_shim.error=mkdir-%s\n",
                             strerror(errno));
    }
    if (unlink(paths->property_service_socket) < 0 && errno != ENOENT) {
        return append_format(stdout_buf,
                             "wifi_hal_composite_start.property_service_shim.mode=auto\n"
                             "wifi_hal_composite_start.property_service_shim.started=0\n"
                             "wifi_hal_composite_start.property_service_shim.error=unlink-%s\n",
                             strerror(errno));
    }
    listen_fd = socket(AF_UNIX, SOCK_STREAM | SOCK_CLOEXEC, 0);
    if (listen_fd < 0) {
        return append_format(stdout_buf,
                             "wifi_hal_composite_start.property_service_shim.mode=auto\n"
                             "wifi_hal_composite_start.property_service_shim.started=0\n"
                             "wifi_hal_composite_start.property_service_shim.error=socket-%s\n",
                             strerror(errno));
    }
    memset(&addr, 0, sizeof(addr));
    addr.sun_family = AF_UNIX;
    socket_len = strlen(paths->property_service_socket);
    if (socket_len >= sizeof(addr.sun_path)) {
        close(listen_fd);
        errno = ENAMETOOLONG;
        return append_literal(stdout_buf,
                              "wifi_hal_composite_start.property_service_shim.mode=auto\n"
                              "wifi_hal_composite_start.property_service_shim.started=0\n"
                              "wifi_hal_composite_start.property_service_shim.error=socket-path-too-long\n");
    }
    memcpy(addr.sun_path, paths->property_service_socket, socket_len + 1);
    if (bind(listen_fd,
             (struct sockaddr *)&addr,
             (socklen_t)(offsetof(struct sockaddr_un, sun_path) + socket_len + 1)) < 0) {
        int saved_errno = errno;
        close(listen_fd);
        errno = saved_errno;
        return append_format(stdout_buf,
                             "wifi_hal_composite_start.property_service_shim.mode=auto\n"
                             "wifi_hal_composite_start.property_service_shim.started=0\n"
                             "wifi_hal_composite_start.property_service_shim.error=bind-%s\n",
                             strerror(errno));
    }
    chmod(paths->property_service_socket, 0666);
    if (listen(listen_fd, 8) < 0) {
        int saved_errno = errno;
        close(listen_fd);
        unlink(paths->property_service_socket);
        errno = saved_errno;
        return append_format(stdout_buf,
                             "wifi_hal_composite_start.property_service_shim.mode=auto\n"
                             "wifi_hal_composite_start.property_service_shim.started=0\n"
                             "wifi_hal_composite_start.property_service_shim.error=listen-%s\n",
                             strerror(errno));
    }
    if (pipe2(pipe_fds, O_CLOEXEC) < 0) {
        int saved_errno = errno;
        close(listen_fd);
        unlink(paths->property_service_socket);
        errno = saved_errno;
        return append_format(stdout_buf,
                             "wifi_hal_composite_start.property_service_shim.mode=auto\n"
                             "wifi_hal_composite_start.property_service_shim.started=0\n"
                             "wifi_hal_composite_start.property_service_shim.error=pipe-%s\n",
                             strerror(errno));
    }
    shim->pid = fork();
    if (shim->pid < 0) {
        int saved_errno = errno;
        close(pipe_fds[0]);
        close(pipe_fds[1]);
        close(listen_fd);
        unlink(paths->property_service_socket);
        errno = saved_errno;
        return append_format(stdout_buf,
                             "wifi_hal_composite_start.property_service_shim.mode=auto\n"
                             "wifi_hal_composite_start.property_service_shim.started=0\n"
                             "wifi_hal_composite_start.property_service_shim.error=fork-%s\n",
                             strerror(errno));
    }
    if (shim->pid == 0) {
        bool allow_peripheral_shutdown_list =
            is_wifi_companion_peripheral_manager_property_contract_start_only_mode(cfg->mode);

        close(pipe_fds[0]);
        property_service_shim_child(listen_fd,
                                    pipe_fds[1],
                                    cfg->timeout_sec,
                                    allow_peripheral_shutdown_list);
        close(pipe_fds[1]);
        close(listen_fd);
        _exit(0);
    }
    close(pipe_fds[1]);
    close(listen_fd);
    shim->record_fd = pipe_fds[0];
    shim->started = true;
    set_nonblock(shim->record_fd);
    return append_format(stdout_buf,
                         "wifi_hal_composite_start.property_service_shim.mode=auto\n"
                         "wifi_hal_composite_start.property_service_shim.started=1\n"
                         "wifi_hal_composite_start.property_service_shim.pid=%ld\n"
                         "wifi_hal_composite_start.property_service_shim.socket=/dev/socket/property_service\n",
                         (long)shim->pid);
}

static int drain_property_service_shim_records(struct property_service_shim *shim,
                                               struct buffer *stdout_buf) {
    char tmp[4096];

    if (shim->record_fd < 0) {
        return 0;
    }
    for (;;) {
        ssize_t nread = read(shim->record_fd, tmp, sizeof(tmp));

        if (nread > 0) {
            if (buffer_append(stdout_buf, tmp, (size_t)nread) < 0) {
                return -1;
            }
            continue;
        }
        if (nread == 0) {
            close(shim->record_fd);
            shim->record_fd = -1;
            return 0;
        }
        if (errno == EINTR) {
            continue;
        }
        if (errno == EAGAIN || errno == EWOULDBLOCK) {
            return 0;
        }
        close(shim->record_fd);
        shim->record_fd = -1;
        return -1;
    }
}

static int stop_property_service_shim(struct property_service_shim *shim,
                                      const struct paths *paths,
                                      struct buffer *stdout_buf) {
    long deadline;

    if (!shim->started) {
        return 0;
    }
    drain_property_service_shim_records(shim, stdout_buf);
    if (shim->pid > 1 && kill(shim->pid, SIGTERM) == 0) {
        shim->term_sent = true;
    }
    deadline = monotonic_ms() + 500L;
    while (monotonic_ms() < deadline) {
        int status = 0;
        pid_t rc = waitpid(shim->pid, &status, WNOHANG);

        if (rc == shim->pid) {
            shim->reaped = true;
            if (WIFEXITED(status)) {
                shim->exit_code = WEXITSTATUS(status);
            } else if (WIFSIGNALED(status)) {
                shim->signal = WTERMSIG(status);
            }
            break;
        }
        if (rc < 0 && errno == ECHILD) {
            shim->reaped = true;
            break;
        }
        usleep(50000);
    }
    if (!shim->reaped && shim->pid > 1 && kill(shim->pid, SIGKILL) == 0) {
        shim->kill_sent = true;
    }
    deadline = monotonic_ms() + 500L;
    while (!shim->reaped && monotonic_ms() < deadline) {
        int status = 0;
        pid_t rc = waitpid(shim->pid, &status, WNOHANG);

        if (rc == shim->pid) {
            shim->reaped = true;
            if (WIFEXITED(status)) {
                shim->exit_code = WEXITSTATUS(status);
            } else if (WIFSIGNALED(status)) {
                shim->signal = WTERMSIG(status);
            }
            break;
        }
        if (rc < 0 && errno == ECHILD) {
            shim->reaped = true;
            break;
        }
        usleep(50000);
    }
    drain_property_service_shim_records(shim, stdout_buf);
    if (shim->record_fd >= 0) {
        close(shim->record_fd);
        shim->record_fd = -1;
    }
    unlink(paths->property_service_socket);
    append_format(stdout_buf,
                  "wifi_hal_composite_start.property_service_shim.term_sent=%d\n"
                  "wifi_hal_composite_start.property_service_shim.kill_sent=%d\n"
                  "wifi_hal_composite_start.property_service_shim.reaped=%d\n"
                  "wifi_hal_composite_start.property_service_shim.exit_code=%d\n"
                  "wifi_hal_composite_start.property_service_shim.signal=%d\n"
                  "wifi_hal_composite_start.property_service_shim.postflight_safe=%d\n",
                  shim->term_sent ? 1 : 0,
                  shim->kill_sent ? 1 : 0,
                  shim->reaped ? 1 : 0,
                  shim->exit_code,
                  shim->signal,
                  (shim->reaped && !shim->kill_sent) ? 1 : 0);
    return 0;
}

struct a90_scan_iface {
    uint32_t ifindex;
    uint32_t iftype;
    char ifname[A90_NL80211_IFNAME_MAX];
    int total_count;
};

static int a90_nla_len(const struct nlattr *attr) {
    return (int)attr->nla_len - NLA_HDRLEN;
}

static void *a90_nla_data(const struct nlattr *attr) {
    return (void *)((const char *)attr + NLA_HDRLEN);
}

static bool a90_nla_ok(const struct nlattr *attr, int remaining) {
    return remaining >= (int)sizeof(*attr) &&
           attr->nla_len >= sizeof(*attr) &&
           attr->nla_len <= remaining;
}

static struct nlattr *a90_nla_next(struct nlattr *attr, int *remaining) {
    int aligned = NLA_ALIGN(attr->nla_len);

    *remaining -= aligned;
    return (struct nlattr *)((char *)attr + aligned);
}

static unsigned int a90_nla_type(const struct nlattr *attr) {
    return attr->nla_type & NLA_TYPE_MASK;
}

static uint32_t a90_nla_u32(const struct nlattr *attr, uint32_t fallback) {
    if (a90_nla_len(attr) < (int)sizeof(uint32_t)) {
        return fallback;
    }
    return *(uint32_t *)a90_nla_data(attr);
}

static const char *a90_nla_string(const struct nlattr *attr) {
    if (a90_nla_len(attr) <= 0) {
        return "";
    }
    return (const char *)a90_nla_data(attr);
}

static void a90_parse_attrs(struct nlattr **attrs,
                            int max_attr,
                            struct nlattr *attr,
                            int len) {
    memset(attrs, 0, sizeof(struct nlattr *) * (size_t)(max_attr + 1));
    while (a90_nla_ok(attr, len)) {
        unsigned int type = a90_nla_type(attr);

        if (type <= (unsigned int)max_attr) {
            attrs[type] = attr;
        }
        attr = a90_nla_next(attr, &len);
    }
}

static int a90_add_attr(char *buf,
                        size_t buf_size,
                        size_t *offset,
                        int type,
                        const void *data,
                        size_t len) {
    struct nlattr *attr;
    size_t attr_len = NLA_HDRLEN + len;
    size_t aligned = NLA_ALIGN(attr_len);

    if (*offset + aligned > buf_size) {
        errno = EMSGSIZE;
        return -1;
    }
    attr = (struct nlattr *)(buf + *offset);
    attr->nla_type = (unsigned short)type;
    attr->nla_len = (unsigned short)attr_len;
    if (len > 0 && data != NULL) {
        memcpy((char *)attr + NLA_HDRLEN, data, len);
    }
    if (aligned > attr_len) {
        memset(buf + *offset + attr_len, 0, aligned - attr_len);
    }
    *offset += aligned;
    return 0;
}

static struct nlattr *a90_nest_start(char *buf,
                                     size_t buf_size,
                                     size_t *offset,
                                     int type) {
    struct nlattr *attr;
    size_t attr_len = NLA_HDRLEN;
    size_t aligned = NLA_ALIGN(attr_len);

    if (*offset + aligned > buf_size) {
        errno = EMSGSIZE;
        return NULL;
    }
    attr = (struct nlattr *)(buf + *offset);
    attr->nla_type = (unsigned short)(type | NLA_F_NESTED);
    attr->nla_len = (unsigned short)attr_len;
    if (aligned > attr_len) {
        memset(buf + *offset + attr_len, 0, aligned - attr_len);
    }
    *offset += aligned;
    return attr;
}

static void a90_nest_end(char *buf, size_t offset, struct nlattr *attr) {
    attr->nla_len = (unsigned short)((buf + offset) - (char *)attr);
}

static int a90_open_genl_socket(void) {
    struct sockaddr_nl local;
    int fd = socket(AF_NETLINK, SOCK_RAW | SOCK_CLOEXEC, NETLINK_GENERIC);

    if (fd < 0) {
        return -1;
    }
    memset(&local, 0, sizeof(local));
    local.nl_family = AF_NETLINK;
    if (bind(fd, (struct sockaddr *)&local, sizeof(local)) < 0) {
        close(fd);
        return -1;
    }
    return fd;
}

static int a90_send_genl(int fd,
                         uint16_t family_id,
                         uint8_t command,
                         uint16_t flags,
                         uint32_t seq,
                         const char *family_name,
                         uint32_t ifindex,
                         bool include_ifindex,
                         bool include_wildcard_ssid) {
    char buffer[1024];
    struct nlmsghdr *nlh = (struct nlmsghdr *)buffer;
    struct genlmsghdr *genlh;
    struct sockaddr_nl addr;
    size_t offset;

    memset(buffer, 0, sizeof(buffer));
    nlh->nlmsg_len = NLMSG_LENGTH(sizeof(*genlh));
    nlh->nlmsg_type = family_id;
    nlh->nlmsg_flags = NLM_F_REQUEST | flags;
    nlh->nlmsg_seq = seq;
    nlh->nlmsg_pid = 0;
    genlh = (struct genlmsghdr *)NLMSG_DATA(nlh);
    genlh->cmd = command;
    genlh->version = 1;
    offset = NLMSG_ALIGN(nlh->nlmsg_len);
    if (family_name != NULL) {
        if (a90_add_attr(buffer,
                         sizeof(buffer),
                         &offset,
                         CTRL_ATTR_FAMILY_NAME,
                         family_name,
                         strlen(family_name) + 1) < 0) {
            return -1;
        }
    }
    if (include_ifindex) {
        if (a90_add_attr(buffer,
                         sizeof(buffer),
                         &offset,
                         NL80211_ATTR_IFINDEX,
                         &ifindex,
                         sizeof(ifindex)) < 0) {
            return -1;
        }
    }
    if (include_wildcard_ssid) {
        struct nlattr *scan_ssids = a90_nest_start(buffer,
                                                   sizeof(buffer),
                                                   &offset,
                                                   NL80211_ATTR_SCAN_SSIDS);

        if (scan_ssids == NULL) {
            return -1;
        }
        if (a90_add_attr(buffer, sizeof(buffer), &offset, 1, NULL, 0) < 0) {
            return -1;
        }
        a90_nest_end(buffer, offset, scan_ssids);
    }
    nlh->nlmsg_len = (uint32_t)offset;

    memset(&addr, 0, sizeof(addr));
    addr.nl_family = AF_NETLINK;
    if (sendto(fd, buffer, nlh->nlmsg_len, 0, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
        return -1;
    }
    return 0;
}

static int a90_recv_family_id(int fd, uint32_t seq) {
    char buffer[A90_NL80211_RECV_BUF_SIZE];
    ssize_t received;
    struct nlmsghdr *nlh;
    int remaining;

    received = recv(fd, buffer, sizeof(buffer), 0);
    if (received < 0) {
        return -1;
    }
    for (nlh = (struct nlmsghdr *)buffer, remaining = (int)received;
         NLMSG_OK(nlh, remaining);
         nlh = NLMSG_NEXT(nlh, remaining)) {
        struct genlmsghdr *genlh;
        struct nlattr *attrs[CTRL_ATTR_MAX + 1];
        int attr_len;

        if (nlh->nlmsg_seq != seq) {
            continue;
        }
        if (nlh->nlmsg_type == NLMSG_ERROR) {
            struct nlmsgerr *err = (struct nlmsgerr *)NLMSG_DATA(nlh);
            errno = err->error < 0 ? -err->error : EIO;
            return -1;
        }
        if (nlh->nlmsg_type == NLMSG_DONE) {
            break;
        }
        genlh = (struct genlmsghdr *)NLMSG_DATA(nlh);
        attr_len = (int)nlh->nlmsg_len - (int)NLMSG_LENGTH(sizeof(*genlh));
        if (attr_len < 0) {
            continue;
        }
        a90_parse_attrs(attrs,
                        CTRL_ATTR_MAX,
                        (struct nlattr *)((char *)genlh + GENL_HDRLEN),
                        attr_len);
        if (attrs[CTRL_ATTR_FAMILY_ID] != NULL) {
            return (int)*(uint16_t *)a90_nla_data(attrs[CTRL_ATTR_FAMILY_ID]);
        }
    }
    errno = ENOENT;
    return -1;
}

static int a90_get_family_id(int fd, const char *name) {
    const uint32_t seq = 4901;

    if (a90_send_genl(fd,
                      GENL_ID_CTRL,
                      CTRL_CMD_GETFAMILY,
                      0,
                      seq,
                      name,
                      0,
                      false,
                      false) < 0) {
        return -1;
    }
    return a90_recv_family_id(fd, seq);
}

static int a90_recv_ack(int fd, uint32_t seq) {
    char buffer[A90_NL80211_RECV_BUF_SIZE];

    for (;;) {
        ssize_t received = recv(fd, buffer, sizeof(buffer), 0);
        struct nlmsghdr *nlh;
        int remaining;

        if (received < 0) {
            return -1;
        }
        for (nlh = (struct nlmsghdr *)buffer, remaining = (int)received;
             NLMSG_OK(nlh, remaining);
             nlh = NLMSG_NEXT(nlh, remaining)) {
            if (nlh->nlmsg_seq != seq) {
                continue;
            }
            if (nlh->nlmsg_type == NLMSG_ERROR) {
                struct nlmsgerr *err = (struct nlmsgerr *)NLMSG_DATA(nlh);

                if (err->error == 0) {
                    return 0;
                }
                errno = err->error < 0 ? -err->error : EIO;
                return -1;
            }
            if (nlh->nlmsg_type == NLMSG_DONE) {
                return 0;
            }
        }
    }
}

static bool a90_scan_iface_preferred_name(const char *ifname) {
    return strncmp(ifname, "wlan", 4) == 0 ||
           strncmp(ifname, "swlan", 5) == 0 ||
           strncmp(ifname, "p2p", 3) == 0 ||
           strncmp(ifname, "wifi-aware", 10) == 0;
}

static int a90_dump_interfaces_select(int fd,
                                      int family_id,
                                      struct a90_scan_iface *selected,
                                      struct buffer *stdout_buf) {
    char buffer[A90_NL80211_RECV_BUF_SIZE];
    const uint32_t seq = 4902;
    bool done = false;
    bool selected_preferred = false;

    memset(selected, 0, sizeof(*selected));
    if (a90_send_genl(fd,
                      (uint16_t)family_id,
                      NL80211_CMD_GET_INTERFACE,
                      NLM_F_DUMP,
                      seq,
                      NULL,
                      0,
                      false,
                      false) < 0) {
        return -1;
    }
    while (!done) {
        ssize_t received = recv(fd, buffer, sizeof(buffer), 0);
        struct nlmsghdr *nlh;
        int remaining;

        if (received < 0) {
            return -1;
        }
        for (nlh = (struct nlmsghdr *)buffer, remaining = (int)received;
             NLMSG_OK(nlh, remaining);
             nlh = NLMSG_NEXT(nlh, remaining)) {
            struct genlmsghdr *genlh;
            struct nlattr *attrs[NL80211_ATTR_MAX + 1];
            int attr_len;
            uint32_t ifindex = 0;
            uint32_t iftype = 0;
            const char *ifname = "";
            bool preferred;

            if (nlh->nlmsg_seq != seq) {
                continue;
            }
            if (nlh->nlmsg_type == NLMSG_DONE) {
                done = true;
                break;
            }
            if (nlh->nlmsg_type == NLMSG_ERROR) {
                struct nlmsgerr *err = (struct nlmsgerr *)NLMSG_DATA(nlh);

                if (err->error == 0) {
                    done = true;
                    break;
                }
                errno = err->error < 0 ? -err->error : EIO;
                return -1;
            }
            genlh = (struct genlmsghdr *)NLMSG_DATA(nlh);
            attr_len = (int)nlh->nlmsg_len - (int)NLMSG_LENGTH(sizeof(*genlh));
            if (attr_len < 0) {
                continue;
            }
            a90_parse_attrs(attrs,
                            NL80211_ATTR_MAX,
                            (struct nlattr *)((char *)genlh + GENL_HDRLEN),
                            attr_len);
            if (attrs[NL80211_ATTR_IFINDEX] != NULL) {
                ifindex = a90_nla_u32(attrs[NL80211_ATTR_IFINDEX], 0);
            }
            if (attrs[NL80211_ATTR_IFTYPE] != NULL) {
                iftype = a90_nla_u32(attrs[NL80211_ATTR_IFTYPE], 0);
            }
            if (attrs[NL80211_ATTR_IFNAME] != NULL) {
                ifname = a90_nla_string(attrs[NL80211_ATTR_IFNAME]);
            }
            if (ifindex == 0) {
                continue;
            }
            selected->total_count++;
            preferred = a90_scan_iface_preferred_name(ifname);
            if (selected->ifindex == 0 || (preferred && !selected_preferred)) {
                selected->ifindex = ifindex;
                selected->iftype = iftype;
                snprintf(selected->ifname, sizeof(selected->ifname), "%s", ifname);
                selected_preferred = preferred;
            }
        }
    }
    if (append_format(stdout_buf,
                      "wifi_scan_only.interface_count=%d\n",
                      selected->total_count) < 0) {
        return -1;
    }
    if (selected->ifindex == 0) {
        errno = ENODEV;
        return 1;
    }
    return 0;
}

static int a90_trigger_scan(int fd, int family_id, uint32_t ifindex) {
    const uint32_t seq = 4903;

    if (a90_send_genl(fd,
                      (uint16_t)family_id,
                      NL80211_CMD_TRIGGER_SCAN,
                      NLM_F_ACK,
                      seq,
                      NULL,
                      ifindex,
                      true,
                      true) < 0) {
        return -1;
    }
    return a90_recv_ack(fd, seq);
}

static int a90_dump_scan_count(int fd,
                               int family_id,
                               uint32_t ifindex,
                               int *scan_count) {
    char buffer[A90_NL80211_RECV_BUF_SIZE];
    const uint32_t seq = 4904;
    bool done = false;

    *scan_count = 0;
    if (a90_send_genl(fd,
                      (uint16_t)family_id,
                      NL80211_CMD_GET_SCAN,
                      NLM_F_DUMP,
                      seq,
                      NULL,
                      ifindex,
                      true,
                      false) < 0) {
        return -1;
    }
    while (!done) {
        ssize_t received = recv(fd, buffer, sizeof(buffer), 0);
        struct nlmsghdr *nlh;
        int remaining;

        if (received < 0) {
            return -1;
        }
        for (nlh = (struct nlmsghdr *)buffer, remaining = (int)received;
             NLMSG_OK(nlh, remaining);
             nlh = NLMSG_NEXT(nlh, remaining)) {
            struct genlmsghdr *genlh;
            struct nlattr *attrs[NL80211_ATTR_MAX + 1];
            int attr_len;

            if (nlh->nlmsg_seq != seq) {
                continue;
            }
            if (nlh->nlmsg_type == NLMSG_DONE) {
                done = true;
                break;
            }
            if (nlh->nlmsg_type == NLMSG_ERROR) {
                struct nlmsgerr *err = (struct nlmsgerr *)NLMSG_DATA(nlh);

                if (err->error == 0) {
                    done = true;
                    break;
                }
                errno = err->error < 0 ? -err->error : EIO;
                return -1;
            }
            genlh = (struct genlmsghdr *)NLMSG_DATA(nlh);
            attr_len = (int)nlh->nlmsg_len - (int)NLMSG_LENGTH(sizeof(*genlh));
            if (attr_len < 0) {
                continue;
            }
            a90_parse_attrs(attrs,
                            NL80211_ATTR_MAX,
                            (struct nlattr *)((char *)genlh + GENL_HDRLEN),
                            attr_len);
            if (attrs[NL80211_ATTR_BSS] != NULL) {
                (*scan_count)++;
            }
        }
    }
    return 0;
}

static int run_wifi_scan_only_probe(struct buffer *stdout_buf) {
    struct a90_scan_iface selected;
    int fd;
    int family_id;
    int saved_errno;
    int iface_rc;
    int trigger_rc;
    int trigger_errno = 0;
    int scan_count = 0;

    if (append_literal(stdout_buf,
                       "wifi_scan_only.begin=1\n"
                       "wifi_scan_only.credentials=0\n"
                       "wifi_scan_only.connect_linkup=0\n"
                       "wifi_scan_only.dhcp_routing=0\n"
                       "wifi_scan_only.external_ping=0\n"
                       "wifi_scan_only.raw_results_redacted=1\n") < 0) {
        return 33;
    }
    fd = a90_open_genl_socket();
    if (fd < 0) {
        saved_errno = errno;
        append_format(stdout_buf,
                      "wifi_scan_only.netlink_open=0\n"
                      "wifi_scan_only.errno=%d\n"
                      "wifi_scan_only.result=nl80211-unavailable\n"
                      "wifi_scan_only.reason=netlink-open-failed\n"
                      "wifi_scan_only.end=1\n",
                      saved_errno);
        return 33;
    }
    append_literal(stdout_buf, "wifi_scan_only.netlink_open=1\n");
    family_id = a90_get_family_id(fd, "nl80211");
    if (family_id < 0) {
        saved_errno = errno;
        close(fd);
        append_format(stdout_buf,
                      "wifi_scan_only.family_id=0\n"
                      "wifi_scan_only.errno=%d\n"
                      "wifi_scan_only.result=nl80211-unavailable\n"
                      "wifi_scan_only.reason=family-id-missing\n"
                      "wifi_scan_only.end=1\n",
                      saved_errno);
        return 33;
    }
    if (append_format(stdout_buf, "wifi_scan_only.family_id=%d\n", family_id) < 0) {
        close(fd);
        return 33;
    }
    iface_rc = a90_dump_interfaces_select(fd, family_id, &selected, stdout_buf);
    if (iface_rc != 0) {
        saved_errno = errno;
        close(fd);
        append_format(stdout_buf,
                      "wifi_scan_only.interface.ifindex=0\n"
                      "wifi_scan_only.errno=%d\n"
                      "wifi_scan_only.result=interface-missing\n"
                      "wifi_scan_only.reason=%s\n"
                      "wifi_scan_only.end=1\n",
                      saved_errno,
                      iface_rc > 0 ? "nl80211-interface-not-found" : "interface-dump-failed");
        return 30;
    }
    if (append_format(stdout_buf,
                      "wifi_scan_only.interface.ifindex=%u\n"
                      "wifi_scan_only.interface.ifname=%s\n"
                      "wifi_scan_only.interface.iftype=%u\n"
                      "wifi_scan_only.trigger_attempted=1\n",
                      selected.ifindex,
                      selected.ifname,
                      selected.iftype) < 0) {
        close(fd);
        return 33;
    }
    trigger_rc = a90_trigger_scan(fd, family_id, selected.ifindex);
    if (trigger_rc < 0) {
        trigger_errno = errno;
    }
    if (append_format(stdout_buf,
                      "wifi_scan_only.trigger_rc=%d\n"
                      "wifi_scan_only.trigger_errno=%d\n",
                      trigger_rc,
                      trigger_errno) < 0) {
        close(fd);
        return 33;
    }
    if (trigger_rc < 0) {
        close(fd);
        append_literal(stdout_buf,
                       "wifi_scan_only.result=trigger-failed\n"
                       "wifi_scan_only.reason=nl80211-trigger-scan-failed\n"
                       "wifi_scan_only.end=1\n");
        return 31;
    }
    usleep(2000000);
    if (a90_dump_scan_count(fd, family_id, selected.ifindex, &scan_count) < 0) {
        saved_errno = errno;
        close(fd);
        append_format(stdout_buf,
                      "wifi_scan_only.scan_result_count=0\n"
                      "wifi_scan_only.errno=%d\n"
                      "wifi_scan_only.result=dump-failed\n"
                      "wifi_scan_only.reason=nl80211-get-scan-failed\n"
                      "wifi_scan_only.end=1\n",
                      saved_errno);
        return 32;
    }
    close(fd);
    append_format(stdout_buf,
                  "wifi_scan_only.scan_result_count=%d\n"
                  "wifi_scan_only.result=pass\n"
                  "wifi_scan_only.reason=nl80211-scan-triggered-and-redacted-counts-captured\n"
                  "wifi_scan_only.end=1\n",
                  scan_count);
    return 0;
}

static int write_wlan_driver_state_on_if_allowed(const struct config *cfg,
                                                 const struct paths *paths,
                                                 struct buffer *stdout_buf) {
    static const char wlan_on[] = "ON";
    long started;
    long duration;
    int fd = -1;
    int write_rc = 1;
    int write_errno = 0;
    int close_errno = 0;

    if (!cfg->allow_wlan_driver_state_on) {
        return append_literal(stdout_buf,
                              "wifi_hal_composite_start.wlan_driver_state_on.allowed=0\n"
                              "wifi_hal_composite_start.wlan_driver_state_on.executed=0\n");
    }

    if (append_literal(stdout_buf,
                       "wifi_hal_composite_start.wlan_driver_state_on.allowed=1\n"
                       "wifi_hal_composite_start.wlan_driver_state_on.executed=1\n"
                       "wifi_hal_composite_start.wlan_driver_state_on.path=/dev/wlan\n"
                       "wifi_hal_composite_start.wlan_driver_state_on.scan_connect_linkup=0\n"
                       "wifi_hal_composite_start.wlan_driver_state_on.credentials=0\n"
                       "wifi_hal_composite_start.wlan_driver_state_on.dhcp_routing=0\n"
                       "wifi_hal_composite_start.wlan_driver_state_on.external_ping=0\n") < 0) {
        return -1;
    }

    started = monotonic_ms();
    fd = open(paths->dev_wlan, O_WRONLY | O_CLOEXEC | O_NOFOLLOW);
    if (fd < 0) {
        write_errno = errno;
    } else if (write_all_fd(fd, wlan_on, sizeof(wlan_on)) < 0) {
        write_errno = errno;
    } else {
        write_rc = 0;
    }
    if (fd >= 0 && close(fd) < 0 && write_rc == 0) {
        write_rc = 1;
        close_errno = errno;
        write_errno = errno;
    }
    duration = monotonic_ms() - started;
    if (append_format(stdout_buf,
                      "wifi_hal_composite_start.wlan_driver_state_on.write_rc=%d\n"
                      "wifi_hal_composite_start.wlan_driver_state_on.write_errno=%d\n"
                      "wifi_hal_composite_start.wlan_driver_state_on.close_errno=%d\n"
                      "wifi_hal_composite_start.wlan_driver_state_on.duration_ms=%ld\n",
                      write_rc,
                      write_errno,
                      close_errno,
                      duration) < 0) {
        return -1;
    }
    return 0;
}

static int run_wifi_hal_composite_start_only_guarded(const struct config *cfg,
                                                     const struct paths *paths,
                                                     struct buffer *stdout_buf,
                                                     struct buffer *stderr_buf,
                                                     int *child_exit_code,
                                                     int *child_signal,
                                                     bool *timed_out) {
    struct composite_child children[A90_WIFI_SURFACE_COMPOSITE_CHILD_COUNT];
    const bool service_query_mode = is_wifi_hal_service_query_mode(cfg->mode);
    const bool wait_target_query_mode = is_wifi_hal_lshal_wait_target_mode(cfg->mode);
    const bool status_query_mode = streq(cfg->mode, "wifi-hal-composite-lshal-status-list");
    const bool surface_composite_mode = is_wifi_surface_composite_mode(cfg->mode);
    const bool active_session_mode = is_wifi_active_session_surface_mode(cfg->mode);
    const bool scan_only_mode = is_wifi_active_session_scan_only_mode(cfg->mode);
    const bool connect_ping_mode = is_wifi_active_session_connect_ping_mode(cfg->mode);
    const bool iwifi_start_mode = is_wifi_iwifi_start_surface_mode(cfg->mode);
    const bool dual_hal_mode = is_wifi_dual_hal_composite_mode(cfg->mode);
    const size_t child_count = dual_hal_mode ?
        A90_WIFI_SURFACE_COMPOSITE_CHILD_COUNT :
        (surface_composite_mode ? 4 : A90_WIFI_HAL_COMPOSITE_CHILD_COUNT);
    bool all_postflight_safe = true;
    bool any_runtime_gap = false;
    bool all_observable_at_timeout = true;
    int service_query_result = 0;
    int scan_only_result = 0;
    int connect_ping_result = 0;
    long deadline;
    struct property_service_shim property_shim;

    *child_exit_code = -1;
    *child_signal = 0;
    *timed_out = false;
    property_service_shim_init(&property_shim);

    composite_child_init(&children[0],
                         "servicemanager",
                         "/system/bin/servicemanager",
                         COMPOSITE_ID_SERVICE_MANAGER);
    composite_child_init(&children[1],
                         "hwservicemanager",
                         "/system/bin/hwservicemanager",
                         COMPOSITE_ID_SERVICE_MANAGER);
    composite_child_init(&children[2],
                         "wifi_hal",
                         cfg->target,
                         COMPOSITE_ID_WIFI_HAL);
    if (dual_hal_mode) {
        composite_child_init(&children[2],
                             "wifi_hal_legacy",
                             "/vendor/bin/hw/android.hardware.wifi@1.0-service",
                             COMPOSITE_ID_WIFI_HAL);
        composite_child_init(&children[3],
                             "wifi_hal_ext",
                             "/vendor/bin/hw/vendor.samsung.hardware.wifi@2.0-service",
                             COMPOSITE_ID_WIFI_HAL);
        composite_child_init(&children[4],
                             "cnss_daemon",
                             "/vendor/bin/cnss-daemon",
                             COMPOSITE_ID_CNSS);
    } else if (surface_composite_mode) {
        composite_child_init(&children[3],
                             "cnss_daemon",
                             "/vendor/bin/cnss-daemon",
                             COMPOSITE_ID_CNSS);
    }

    if (append_literal(stdout_buf, "wifi_hal_composite_start.begin=1\n") < 0 ||
        append_literal(stdout_buf, "wifi_hal_composite_start.mode=guarded\n") < 0 ||
        append_format(stdout_buf, "wifi_hal_composite_start.target=%s\n", cfg->target) < 0 ||
        append_format(stdout_buf, "wifi_hal_composite_start.target_profile=%s\n", cfg->target_profile) < 0 ||
        append_format(stdout_buf, "wifi_hal_composite_start.dual_hal=%d\n", dual_hal_mode ? 1 : 0) < 0 ||
        append_format(stdout_buf,
                      "wifi_hal_composite_start.secondary_target=%s\n",
                      dual_hal_mode ? "/vendor/bin/hw/vendor.samsung.hardware.wifi@2.0-service" : "<none>") < 0 ||
        append_literal(stdout_buf, "wifi_hal_composite_start.wifi_hal=1\n") < 0 ||
        append_format(stdout_buf, "wifi_hal_composite_start.cnss_daemon=%d\n", surface_composite_mode ? 1 : 0) < 0 ||
        append_format(stdout_buf, "wifi_hal_composite_start.service_query=%d\n", service_query_mode ? 1 : 0) < 0 ||
        append_format(stdout_buf, "wifi_hal_composite_start.iwifi_start=%d\n", iwifi_start_mode ? 1 : 0) < 0 ||
        append_format(stdout_buf, "wifi_hal_composite_start.wlan_driver_state_on=%d\n", cfg->allow_wlan_driver_state_on ? 1 : 0) < 0 ||
        append_format(stdout_buf, "wifi_hal_composite_start.active_session=%d\n", active_session_mode ? 1 : 0) < 0 ||
        append_format(stdout_buf, "wifi_hal_composite_start.scan_only=%d\n", scan_only_mode ? 1 : 0) < 0 ||
        append_format(stdout_buf, "wifi_hal_composite_start.connect_ping=%d\n", connect_ping_mode ? 1 : 0) < 0 ||
        append_format(stdout_buf, "wifi_hal_composite_start.connect_linkup=%d\n", connect_ping_mode ? 1 : 0) < 0 ||
        append_format(stdout_buf, "wifi_hal_composite_start.scan_connect_linkup=%d\n", (scan_only_mode || connect_ping_mode) ? 1 : 0) < 0 ||
        append_literal(stdout_buf, "wifi_hal_composite_start.wificond=0\n") < 0 ||
        append_literal(stdout_buf, "wifi_hal_composite_start.supplicant=0\n") < 0 ||
        append_literal(stdout_buf, "wifi_hal_composite_start.hostapd=0\n") < 0 ||
        append_literal(stdout_buf, "wifi_hal_composite_start.cnss_diag=0\n") < 0) {
        return -1;
    }

    if (!cfg->allow_service_manager_start_only ||
        !cfg->allow_wifi_hal_start_only ||
        (surface_composite_mode && !cfg->allow_cnss_start_only) ||
        (service_query_mode && !cfg->allow_hal_service_query) ||
        (iwifi_start_mode && !cfg->allow_iwifi_start_only) ||
        (scan_only_mode && !cfg->allow_scan_only) ||
        (connect_ping_mode && !cfg->allow_connect_dhcp_ping)) {
        if (append_format(stdout_buf,
                          "wifi_hal_composite_start.allowed=0\n"
                          "wifi_hal_composite_start.allow_cnss_start_only=%d\n"
                          "wifi_hal_composite_start.allow_service_manager_start_only=%d\n"
                          "wifi_hal_composite_start.allow_wifi_hal_start_only=%d\n"
                          "wifi_hal_composite_start.allow_hal_service_query=%d\n"
                          "wifi_hal_composite_start.allow_iwifi_start_only=%d\n"
                          "wifi_hal_composite_start.allow_wlan_driver_state_on=%d\n"
                          "wifi_hal_composite_start.allow_scan_only=%d\n"
                          "wifi_hal_composite_start.allow_connect_dhcp_ping=%d\n"
                          "wifi_hal_composite_start.exec_attempted=0\n"
                          "wifi_hal_composite_start.child_started=0\n"
                          "wifi_hal_composite_start.result=start-only-blocked\n"
                          "wifi_hal_composite_start.reason=missing-allow-flags\n"
                          "wifi_hal_composite_start.end=1\n",
                          cfg->allow_cnss_start_only ? 1 : 0,
                          cfg->allow_service_manager_start_only ? 1 : 0,
                          cfg->allow_wifi_hal_start_only ? 1 : 0,
                          cfg->allow_hal_service_query ? 1 : 0,
                          cfg->allow_iwifi_start_only ? 1 : 0,
                          cfg->allow_wlan_driver_state_on ? 1 : 0,
                          cfg->allow_scan_only ? 1 : 0,
                          cfg->allow_connect_dhcp_ping ? 1 : 0) < 0) {
            return -1;
        }
        return 0;
    }

    if (append_literal(stdout_buf,
                       "wifi_hal_composite_start.allowed=1\n"
                       "wifi_hal_composite_start.exec_attempted=1\n") < 0) {
        return -1;
    }
    if (active_session_mode &&
        append_format(stdout_buf,
                      "wifi_active_session.begin=1\n"
                      "wifi_active_session.helper_version=%s\n"
                      "wifi_active_session.mode=%s\n"
                      "wifi_active_session.timeout_sec=%d\n"
                      "wifi_active_session.scan_only=%d\n"
                      "wifi_active_session.connect_ping=%d\n"
                      "wifi_active_session.connect_linkup=%d\n"
                      "wifi_active_session.scan_connect_linkup=%d\n"
                      "wifi_active_session.credentials=%d\n"
                      "wifi_active_session.dhcp_routing=%d\n"
                      "wifi_active_session.external_ping=%d\n",
                      EXECNS_VERSION,
                      connect_ping_mode ? "bounded-connect-dhcp-ping-window" :
                      scan_only_mode ? "bounded-scan-only-window" : "bounded-surface-window",
                      cfg->timeout_sec,
                      scan_only_mode ? 1 : 0,
                      connect_ping_mode ? 1 : 0,
                      connect_ping_mode ? 1 : 0,
                      (scan_only_mode || connect_ping_mode) ? 1 : 0,
                      connect_ping_mode ? 1 : 0,
                      connect_ping_mode ? 1 : 0,
                      connect_ping_mode ? 1 : 0) < 0) {
        return -1;
    }
    if (surface_composite_mode &&
        append_wifi_surface_snapshot(stdout_buf, "wifi_surface_composite.before") < 0) {
        return -1;
    }
    if (surface_composite_mode &&
        append_wifi_runtime_surface_snapshot(stdout_buf, paths, "wifi_runtime_surface.before") < 0) {
        return -1;
    }
    if (start_property_service_shim(cfg, paths, &property_shim, stdout_buf) < 0) {
        return -1;
    }
    if (property_service_shim_needed(cfg) && !property_shim.started) {
        append_literal(stdout_buf,
                       "wifi_hal_composite_start.child_started=0\n"
                       "wifi_hal_composite_start.result=property-service-shim-setup-failed\n"
                       "wifi_hal_composite_start.reason=private-property-service-socket-not-ready\n"
                       "wifi_hal_composite_start.end=1\n");
        *child_exit_code = 124;
        return 0;
    }
    for (size_t i = 0; i < child_count; i++) {
        if (composite_spawn_child(cfg, paths, &children[i], stdout_buf) < 0) {
            composite_cleanup_children(children, child_count, stdout_buf, stderr_buf);
            stop_property_service_shim(&property_shim, paths, stdout_buf);
            append_literal(stdout_buf,
                           "wifi_hal_composite_start.result=manual-review-required\n"
                           "wifi_hal_composite_start.reason=child-spawn-failed\n"
                           "wifi_hal_composite_start.end=1\n");
            return -1;
        }
        if (i == 1 || (surface_composite_mode && i == 2)) {
            usleep(300000);
        }
    }
    append_format(stdout_buf, "wifi_hal_composite_start.child_started=%zu\n", child_count);
    if (write_wlan_driver_state_on_if_allowed(cfg, paths, stdout_buf) < 0) {
        composite_cleanup_children(children, child_count, stdout_buf, stderr_buf);
        stop_property_service_shim(&property_shim, paths, stdout_buf);
        return -1;
    }
    deadline = monotonic_ms() + cfg->timeout_sec * 1000L;
    if (service_query_mode || iwifi_start_mode) {
        bool warmup_timed_out = false;
        long warmup_deadline = monotonic_ms() + 500L;

        if (composite_poll_children(children,
                                    child_count,
                                    stdout_buf,
                                    stderr_buf,
                                    warmup_deadline,
                                    &warmup_timed_out) < 0) {
            composite_cleanup_children(children, child_count, stdout_buf, stderr_buf);
            stop_property_service_shim(&property_shim, paths, stdout_buf);
            return -1;
        }
        if (iwifi_start_mode) {
            service_query_result = run_iwifi_start_hwbinder_probe(paths, stdout_buf);
            if (append_wifi_surface_snapshot(stdout_buf, "wifi_surface_composite.after_iwifi_start") < 0) {
                composite_cleanup_children(children, child_count, stdout_buf, stderr_buf);
                stop_property_service_shim(&property_shim, paths, stdout_buf);
                return -1;
            }
            if (scan_only_mode) {
                scan_only_result = run_wifi_scan_only_probe(stdout_buf);
            } else if (connect_ping_mode) {
                connect_ping_result = run_wifi_connect_ping_scaffold(cfg, paths, stdout_buf);
            }
        } else if (wait_target_query_mode) {
            const int wait_timeout_ms = surface_composite_mode ?
                cfg->timeout_sec * 1000 : 2000;

            service_query_result = run_lshal_wait_target_query_child(cfg,
                                                                     paths,
                                                                     stdout_buf,
                                                                     stderr_buf,
                                                                     wait_timeout_ms);
        } else {
            service_query_result = run_lshal_service_query_child(cfg,
                                                                 paths,
                                                                 stdout_buf,
                                                                 stderr_buf,
                                                                 status_query_mode ? 5000 : 3000);
        }
    }
    if (composite_poll_children(children,
                                child_count,
                                stdout_buf,
                                stderr_buf,
                                deadline,
                                timed_out) < 0) {
        composite_cleanup_children(children, child_count, stdout_buf, stderr_buf);
        stop_property_service_shim(&property_shim, paths, stdout_buf);
        return -1;
    }
    composite_capture_observable_children(children, child_count, stdout_buf);
    if (surface_composite_mode &&
        append_wifi_surface_snapshot(stdout_buf, "wifi_surface_composite.during") < 0) {
        composite_cleanup_children(children, child_count, stdout_buf, stderr_buf);
        stop_property_service_shim(&property_shim, paths, stdout_buf);
        return -1;
    }
    if (surface_composite_mode &&
        append_wifi_runtime_surface_snapshot(stdout_buf, paths, "wifi_runtime_surface.during") < 0) {
        composite_cleanup_children(children, child_count, stdout_buf, stderr_buf);
        stop_property_service_shim(&property_shim, paths, stdout_buf);
        return -1;
    }
    composite_cleanup_children(children, child_count, stdout_buf, stderr_buf);
    if (stop_property_service_shim(&property_shim, paths, stdout_buf) < 0) {
        return -1;
    }
    if (property_shim.started && (!property_shim.reaped || property_shim.kill_sent)) {
        all_postflight_safe = false;
    }
    if (surface_composite_mode &&
        append_wifi_surface_snapshot(stdout_buf, "wifi_surface_composite.after_cleanup") < 0) {
        return -1;
    }
    if (surface_composite_mode &&
        append_wifi_runtime_surface_snapshot(stdout_buf, paths, "wifi_runtime_surface.after_cleanup") < 0) {
        return -1;
    }
    if (active_session_mode &&
        append_literal(stdout_buf,
                       "wifi_active_session.cleanup_attempted=1\n"
                       "wifi_active_session.end=1\n") < 0) {
        return -1;
    }

    for (size_t i = 0; i < child_count; i++) {
        bool safe = composite_child_postflight_safe(&children[i]);

        if (!safe) {
            all_postflight_safe = false;
        }
        if (!children[i].observable) {
            all_observable_at_timeout = false;
        }
        if (composite_child_runtime_gap(&children[i], *timed_out)) {
            any_runtime_gap = true;
            if (*child_exit_code < 0 && children[i].exit_code >= 0) {
                *child_exit_code = children[i].exit_code;
            }
            if (*child_signal == 0 && children[i].signal != 0) {
                *child_signal = children[i].signal;
            }
        }
        if (append_format(stdout_buf,
                          "wifi_hal_composite_start.child.%s.observable=%d\n"
                          "wifi_hal_composite_start.child.%s.exited=%d\n"
                          "wifi_hal_composite_start.child.%s.exit_code=%d\n"
                          "wifi_hal_composite_start.child.%s.signal=%d\n"
                          "wifi_hal_composite_start.child.%s.term_sent=%d\n"
                          "wifi_hal_composite_start.child.%s.kill_sent=%d\n"
                          "wifi_hal_composite_start.child.%s.reaped=%d\n"
                          "wifi_hal_composite_start.child.%s.proc_status_captured=%d\n"
                          "wifi_hal_composite_start.child.%s.proc_attr_current_captured=%d\n"
                          "wifi_hal_composite_start.child.%s.fd_summary_captured=%d\n"
                          "wifi_hal_composite_start.child.%s.maps_summary_captured=%d\n"
                          "wifi_hal_composite_start.child.%s.traced=%d\n"
                          "wifi_hal_composite_start.child.%s.trace_initial_stop=%d\n"
                          "wifi_hal_composite_start.child.%s.capture_exec=%d\n"
                          "wifi_hal_composite_start.child.%s.capture_crash=%d\n"
                          "wifi_hal_composite_start.child.%s.trace_cleanup_stop_continued=%d\n"
                          "wifi_hal_composite_start.child.%s.trace_cleanup_stop_last_signal=%d\n"
                          "wifi_hal_composite_start.child.%s.trace_cleanup_continue_errors=%d\n"
                          "wifi_hal_composite_start.child.%s.postflight_safe=%d\n",
                          children[i].name,
                          children[i].observable ? 1 : 0,
                          children[i].name,
                          children[i].child_done ? 1 : 0,
                          children[i].name,
                          children[i].exit_code,
                          children[i].name,
                          children[i].signal,
                          children[i].name,
                          children[i].term_sent ? 1 : 0,
                          children[i].name,
                          children[i].kill_sent ? 1 : 0,
                          children[i].name,
                          children[i].reaped ? 1 : 0,
                          children[i].name,
                          children[i].proc_status_captured ? 1 : 0,
                          children[i].name,
                          children[i].proc_attr_current_captured ? 1 : 0,
                          children[i].name,
                          children[i].fd_summary_captured ? 1 : 0,
                          children[i].name,
                          children[i].maps_summary_captured ? 1 : 0,
                          children[i].name,
                          children[i].traced ? 1 : 0,
                          children[i].name,
                          children[i].trace_initial_stop ? 1 : 0,
                          children[i].name,
                          children[i].capture_exec ? 1 : 0,
                          children[i].name,
                          children[i].capture_crash ? 1 : 0,
                          children[i].name,
                          children[i].trace_cleanup_stop_continued,
                          children[i].name,
                          children[i].trace_cleanup_stop_last_signal,
                          children[i].name,
                          children[i].trace_cleanup_continue_errors,
                          children[i].name,
                          safe ? 1 : 0) < 0) {
            return -1;
        }
    }
    if (*child_exit_code < 0 && *child_signal == 0) {
        *child_exit_code = 0;
    }
    if (append_format(stdout_buf,
                      "wifi_hal_composite_start.timed_out=%d\n"
                      "wifi_hal_composite_start.all_observable_at_timeout=%d\n"
                      "wifi_hal_composite_start.all_postflight_safe=%d\n",
                      *timed_out ? 1 : 0,
                      all_observable_at_timeout ? 1 : 0,
                      all_postflight_safe ? 1 : 0) < 0) {
        return -1;
    }
    if (!all_postflight_safe) {
        append_literal(stdout_buf,
                       "wifi_hal_composite_start.result=start-only-reboot-required\n"
                       "wifi_hal_composite_start.reason=process-not-proven-stopped\n");
    } else if (service_query_mode && service_query_result == 10) {
        append_literal(stdout_buf,
                       "wifi_hal_composite_start.result=service-query-tool-missing\n"
                       "wifi_hal_composite_start.reason=lshal-unavailable\n");
    } else if (service_query_mode && service_query_result != 0) {
        append_format(stdout_buf,
                      "wifi_hal_composite_start.result=service-query-runtime-gap\n"
                      "wifi_hal_composite_start.reason=%s\n",
                      wait_target_query_mode ? "lshal-wait-query-failed" : "lshal-query-failed");
    } else if (iwifi_start_mode && service_query_result == 20) {
        append_literal(stdout_buf,
                       "wifi_hal_composite_start.result=iwifi-service-null\n"
                       "wifi_hal_composite_start.reason=IWifi-default-handle-not-returned\n");
    } else if (iwifi_start_mode && service_query_result != 0) {
        append_literal(stdout_buf,
                       "wifi_hal_composite_start.result=iwifi-transaction-failed\n"
                       "wifi_hal_composite_start.reason=IWifi-start-transaction-not-clean\n");
    } else if (scan_only_mode && scan_only_result == 30) {
        append_literal(stdout_buf,
                       "wifi_hal_composite_start.result=scan-only-interface-missing\n"
                       "wifi_hal_composite_start.reason=nl80211-interface-not-found\n");
    } else if (scan_only_mode && scan_only_result == 31) {
        append_literal(stdout_buf,
                       "wifi_hal_composite_start.result=scan-only-trigger-failed\n"
                       "wifi_hal_composite_start.reason=nl80211-trigger-scan-failed\n");
    } else if (scan_only_mode && scan_only_result == 32) {
        append_literal(stdout_buf,
                       "wifi_hal_composite_start.result=scan-only-dump-failed\n"
                       "wifi_hal_composite_start.reason=nl80211-get-scan-failed\n");
    } else if (scan_only_mode && scan_only_result != 0) {
        append_literal(stdout_buf,
                       "wifi_hal_composite_start.result=scan-only-runtime-gap\n"
                       "wifi_hal_composite_start.reason=nl80211-scan-only-runtime-gap\n");
    } else if (connect_ping_mode && connect_ping_result == 0 && all_postflight_safe) {
        append_literal(stdout_buf,
                       "wifi_hal_composite_start.result=connect-ping-pass\n"
                       "wifi_hal_composite_start.reason=connect-dhcp-ping-executor-passed-and-children-clean\n");
    } else if (connect_ping_mode && connect_ping_result != 0) {
        append_literal(stdout_buf,
                       "wifi_hal_composite_start.result=connect-ping-blocked\n"
                       "wifi_hal_composite_start.reason=connect-dhcp-ping-executor-did-not-pass\n");
    } else if (scan_only_mode && *timed_out && all_observable_at_timeout) {
        append_literal(stdout_buf,
                       "wifi_hal_composite_start.result=scan-only-pass\n"
                       "wifi_hal_composite_start.reason=nl80211-scan-triggered-and-redacted-counts-captured\n");
    } else if (iwifi_start_mode && *timed_out && all_observable_at_timeout) {
        append_literal(stdout_buf,
                       "wifi_hal_composite_start.result=iwifi-start-transaction-pass\n"
                       "wifi_hal_composite_start.reason=IWifi-start-transaction-observed-and-children-clean\n");
    } else if (service_query_mode && *timed_out && all_observable_at_timeout) {
        append_format(stdout_buf,
                      "wifi_hal_composite_start.result=service-query-pass\n"
                      "wifi_hal_composite_start.reason=%s\n",
                      wait_target_query_mode
                          ? "lshal-wait-target-exit-zero-and-children-clean"
                          : "lshal-query-exit-zero-and-children-clean");
    } else if (*timed_out && all_observable_at_timeout) {
        append_literal(stdout_buf,
                       "wifi_hal_composite_start.result=start-only-pass\n"
                       "wifi_hal_composite_start.reason=observed-until-timeout-clean-stop\n");
    } else if (any_runtime_gap) {
        append_literal(stdout_buf,
                       "wifi_hal_composite_start.result=start-only-runtime-gap\n"
                       "wifi_hal_composite_start.reason=child-exited-before-observe-window\n");
    } else {
        append_literal(stdout_buf,
                       "wifi_hal_composite_start.result=manual-review-required\n"
                       "wifi_hal_composite_start.reason=unclassified-lifecycle-state\n");
    }
    append_literal(stdout_buf, "wifi_hal_composite_start.end=1\n");
    return 0;
}

static int run_wifi_companion_hal_order_start_only_guarded(const struct config *cfg,
                                                           const struct paths *paths,
                                                           struct buffer *stdout_buf,
                                                           struct buffer *stderr_buf,
                                                           int *child_exit_code,
                                                           int *child_signal,
                                                           bool *timed_out) {
    struct composite_child children[A90_COMPOSITE_CHILD_MAX];
    const bool with_wificond = is_wifi_companion_hal_wificond_order_start_only_mode(cfg->mode);
    const bool dual_hal_registration_mode =
        is_wifi_companion_dual_hal_wificond_lshal_wait_iwifi_mode(cfg->mode) ||
        is_wifi_companion_dual_hal_wificond_iwifi_start_mode(cfg->mode) ||
        is_wifi_companion_dual_hal_wificond_lshal_then_iwifi_start_mode(cfg->mode);
    const bool iwifi_start_mode =
        is_wifi_companion_dual_hal_wificond_iwifi_start_mode(cfg->mode) ||
        is_wifi_companion_dual_hal_wificond_lshal_then_iwifi_start_mode(cfg->mode);
    const bool registration_query_mode =
        is_wifi_companion_hal_wificond_lshal_wait_samsung_mode(cfg->mode) ||
        is_wifi_companion_hal_wificond_lshal_wait_iwifi_mode(cfg->mode) ||
        is_wifi_companion_dual_hal_wificond_lshal_wait_iwifi_mode(cfg->mode) ||
        is_wifi_companion_dual_hal_wificond_lshal_then_iwifi_start_mode(cfg->mode);
    const size_t child_count = dual_hal_registration_mode ? 12 : (with_wificond ? 11 : 10);
    bool all_postflight_safe = true;
    bool any_runtime_gap = false;
    bool all_observable_at_timeout = true;
    int service_query_result = 0;
    int iwifi_start_result = 0;
    struct property_service_shim property_shim;
    long deadline;

    *child_exit_code = -1;
    *child_signal = 0;
    *timed_out = false;
    property_service_shim_init(&property_shim);

    composite_child_init(&children[0],
                         "servicemanager",
                         "/system/bin/servicemanager",
                         COMPOSITE_ID_SERVICE_MANAGER);
    composite_child_init(&children[1],
                         "hwservicemanager",
                         "/system/bin/hwservicemanager",
                         COMPOSITE_ID_SERVICE_MANAGER);
    composite_child_init(&children[2],
                         "vndservicemanager",
                         "/vendor/bin/vndservicemanager",
                         COMPOSITE_ID_VND_SERVICE_MANAGER);
    composite_child_init(&children[3],
                         "qrtr_ns",
                         "/vendor/bin/qrtr-ns",
                         COMPOSITE_ID_QRTR_NS);
    composite_child_init(&children[4],
                         "rmt_storage",
                         "/vendor/bin/rmt_storage",
                         COMPOSITE_ID_RMT_STORAGE);
    composite_child_init(&children[5],
                         "tftp_server",
                         "/vendor/bin/tftp_server",
                         COMPOSITE_ID_TFTP_SERVER);
    composite_child_init(&children[6],
                         "pd_mapper",
                         "/vendor/bin/pd-mapper",
                         COMPOSITE_ID_PD_MAPPER);
    if (dual_hal_registration_mode) {
        composite_child_init(&children[7],
                             "wifi_hal_legacy",
                             "/vendor/bin/hw/android.hardware.wifi@1.0-service",
                             COMPOSITE_ID_WIFI_HAL);
        composite_child_init(&children[8],
                             "wifi_hal_ext",
                             "/vendor/bin/hw/vendor.samsung.hardware.wifi@2.0-service",
                             COMPOSITE_ID_WIFI_HAL);
        composite_child_init(&children[9],
                             "cnss_diag",
                             "/vendor/bin/cnss_diag",
                             COMPOSITE_ID_CNSS_DIAG);
        composite_child_init(&children[10],
                             "wificond",
                             "/system/bin/wificond",
                             COMPOSITE_ID_WIFICOND);
        composite_child_init(&children[11],
                             "cnss_daemon",
                             "/vendor/bin/cnss-daemon",
                             COMPOSITE_ID_CNSS);
    } else if (with_wificond) {
        composite_child_init(&children[7],
                             "wifi_hal",
                             cfg->target,
                             COMPOSITE_ID_WIFI_HAL);
        composite_child_init(&children[8],
                             "cnss_diag",
                             "/vendor/bin/cnss_diag",
                             COMPOSITE_ID_CNSS_DIAG);
        composite_child_init(&children[9],
                             "wificond",
                             "/system/bin/wificond",
                             COMPOSITE_ID_WIFICOND);
        composite_child_init(&children[10],
                             "cnss_daemon",
                             "/vendor/bin/cnss-daemon",
                             COMPOSITE_ID_CNSS);
    } else {
        composite_child_init(&children[7],
                             "wifi_hal",
                             cfg->target,
                             COMPOSITE_ID_WIFI_HAL);
        composite_child_init(&children[8],
                             "cnss_diag",
                             "/vendor/bin/cnss_diag",
                             COMPOSITE_ID_CNSS_DIAG);
        composite_child_init(&children[9],
                             "cnss_daemon",
                             "/vendor/bin/cnss-daemon",
                             COMPOSITE_ID_CNSS);
    }

    if (append_literal(stdout_buf, "wifi_companion_hal_order.begin=1\n") < 0 ||
        append_literal(stdout_buf, "wifi_companion_hal_order.mode=guarded\n") < 0 ||
        append_format(stdout_buf, "wifi_companion_hal_order.helper_version=%s\n", EXECNS_VERSION) < 0 ||
        append_format(stdout_buf, "wifi_companion_hal_order.target=%s\n", cfg->target) < 0 ||
        append_format(stdout_buf, "wifi_companion_hal_order.target_profile=%s\n", cfg->target_profile) < 0 ||
        append_format(stdout_buf, "wifi_companion_hal_order.timeout_sec=%d\n", cfg->timeout_sec) < 0 ||
        append_format(stdout_buf,
                      "wifi_companion_hal_order.order=%s\n",
                      dual_hal_registration_mode
                          ? "servicemanager,hwservicemanager,vndservicemanager,qrtr_ns,rmt_storage,tftp_server,pd_mapper,wifi_hal_legacy,wifi_hal_ext,cnss_diag,wificond,cnss_daemon"
                          : with_wificond
                          ? "servicemanager,hwservicemanager,vndservicemanager,qrtr_ns,rmt_storage,tftp_server,pd_mapper,wifi_hal,cnss_diag,wificond,cnss_daemon"
                          : "servicemanager,hwservicemanager,vndservicemanager,qrtr_ns,rmt_storage,tftp_server,pd_mapper,wifi_hal,cnss_diag,cnss_daemon") < 0 ||
        append_literal(stdout_buf, "wifi_companion_hal_order.service_manager=1\n") < 0 ||
        append_literal(stdout_buf, "wifi_companion_hal_order.vnd_service_manager=1\n") < 0 ||
        append_format(stdout_buf, "wifi_companion_hal_order.wifi_hal=%d\n", dual_hal_registration_mode ? 2 : 1) < 0 ||
        append_format(stdout_buf, "wifi_companion_hal_order.dual_hal=%d\n", dual_hal_registration_mode ? 1 : 0) < 0 ||
        append_literal(stdout_buf, "wifi_companion_hal_order.cnss_diag=1\n") < 0 ||
        append_literal(stdout_buf, "wifi_companion_hal_order.cnss_daemon=1\n") < 0 ||
        append_format(stdout_buf, "wifi_companion_hal_order.wificond=%d\n", with_wificond ? 1 : 0) < 0 ||
        append_literal(stdout_buf, "wifi_companion_hal_order.supplicant=0\n") < 0 ||
        append_literal(stdout_buf, "wifi_companion_hal_order.hostapd=0\n") < 0 ||
        append_format(stdout_buf, "wifi_companion_hal_order.qcwlanstate_write=%d\n", cfg->allow_wlan_driver_state_on ? 1 : 0) < 0 ||
        append_literal(stdout_buf, "wifi_companion_hal_order.scan_connect_linkup=0\n") < 0 ||
        append_literal(stdout_buf, "wifi_companion_hal_order.credentials=0\n") < 0 ||
        append_literal(stdout_buf, "wifi_companion_hal_order.dhcp_routing=0\n") < 0 ||
        append_literal(stdout_buf, "wifi_companion_hal_order.external_ping=0\n") < 0 ||
        append_format(stdout_buf,
                      "wifi_companion_hal_order.qrtr_nameservice_readback=%d\n"
                      "wifi_companion_hal_order.service_query=%d\n"
                      "wifi_companion_hal_order.iwifi_start=%d\n"
                      "wifi_companion_hal_order.qmi_payload=0\n",
                      cfg->allow_qrtr_ns_readback ? 1 : 0,
                      registration_query_mode ? 1 : 0,
                      iwifi_start_mode ? 1 : 0) < 0) {
        return -1;
    }

    if (!cfg->allow_wifi_companion_start_only ||
        !cfg->allow_cnss_start_only ||
        !cfg->allow_service_manager_start_only ||
        !cfg->allow_wifi_hal_start_only ||
        (registration_query_mode && !cfg->allow_hal_service_query) ||
        (iwifi_start_mode && !cfg->allow_iwifi_start_only)) {
        if (append_format(stdout_buf,
                          "wifi_companion_hal_order.allowed=0\n"
                          "wifi_companion_hal_order.allow_wifi_companion_start_only=%d\n"
                          "wifi_companion_hal_order.allow_cnss_start_only=%d\n"
                          "wifi_companion_hal_order.allow_service_manager_start_only=%d\n"
                          "wifi_companion_hal_order.allow_wifi_hal_start_only=%d\n"
                          "wifi_companion_hal_order.allow_hal_service_query=%d\n"
                          "wifi_companion_hal_order.allow_iwifi_start_only=%d\n"
                          "wifi_companion_hal_order.allow_wlan_driver_state_on=%d\n"
                          "wifi_companion_hal_order.exec_attempted=0\n"
                          "wifi_companion_hal_order.child_started=0\n"
                          "wifi_companion_hal_order.result=start-only-blocked\n"
                          "wifi_companion_hal_order.reason=missing-order-allow-flags\n"
                          "wifi_companion_hal_order.end=1\n",
                          cfg->allow_wifi_companion_start_only ? 1 : 0,
                          cfg->allow_cnss_start_only ? 1 : 0,
                          cfg->allow_service_manager_start_only ? 1 : 0,
                          cfg->allow_wifi_hal_start_only ? 1 : 0,
                          cfg->allow_hal_service_query ? 1 : 0,
                          cfg->allow_iwifi_start_only ? 1 : 0,
                          cfg->allow_wlan_driver_state_on ? 1 : 0) < 0) {
            return -1;
        }
        return 0;
    }

    if (append_literal(stdout_buf,
                       "wifi_companion_hal_order.allowed=1\n"
                       "wifi_companion_hal_order.exec_attempted=1\n") < 0 ||
        append_qipcrtr_protocol_summary(stdout_buf, "wifi_companion_hal_order.net_before") < 0 ||
        append_wifi_surface_snapshot(stdout_buf, "wifi_companion_hal_order.surface_before") < 0 ||
        append_wifi_runtime_surface_snapshot(stdout_buf, paths, "wifi_companion_hal_order.runtime_before") < 0) {
        return -1;
    }

    if (start_property_service_shim(cfg, paths, &property_shim, stdout_buf) < 0) {
        return -1;
    }
    if (property_service_shim_needed(cfg) && !property_shim.started) {
        append_literal(stdout_buf,
                       "wifi_companion_hal_order.child_started=0\n"
                       "wifi_companion_hal_order.result=property-service-shim-setup-failed\n"
                       "wifi_companion_hal_order.reason=private-property-service-socket-not-ready\n"
                       "wifi_companion_hal_order.end=1\n");
        *child_exit_code = 124;
        return 0;
    }

    for (size_t i = 0; i < child_count; i++) {
        if (composite_spawn_child(cfg, paths, &children[i], stdout_buf) < 0) {
            composite_cleanup_children(children, child_count, stdout_buf, stderr_buf);
            stop_property_service_shim(&property_shim, paths, stdout_buf);
            append_literal(stdout_buf,
                           "wifi_companion_hal_order.result=manual-review-required\n"
                           "wifi_companion_hal_order.reason=child-spawn-failed\n"
                           "wifi_companion_hal_order.end=1\n");
            return -1;
        }
        append_format(stdout_buf,
                      "wifi_companion_hal_order.child.%s.start_order=%zu\n",
                      children[i].name,
                      i + 1);
        if (i == 2 || i == 6 || i == 7 || i == 8 || (with_wificond && i == 9)) {
            usleep(300000);
        }
    }
    append_format(stdout_buf, "wifi_companion_hal_order.child_started=%zu\n", child_count);
    if (write_wlan_driver_state_on_if_allowed(cfg, paths, stdout_buf) < 0) {
        composite_cleanup_children(children, child_count, stdout_buf, stderr_buf);
        stop_property_service_shim(&property_shim, paths, stdout_buf);
        return -1;
    }
    if (append_qipcrtr_protocol_summary(stdout_buf, "wifi_companion_hal_order.net_after_spawn") < 0) {
        composite_cleanup_children(children, child_count, stdout_buf, stderr_buf);
        stop_property_service_shim(&property_shim, paths, stdout_buf);
        return -1;
    }

    if (registration_query_mode) {
        bool warmup_timed_out = false;
        long warmup_deadline = monotonic_ms() + 500L;

        if (composite_poll_children(children,
                                    child_count,
                                    stdout_buf,
                                    stderr_buf,
                                    warmup_deadline,
                                    &warmup_timed_out) < 0) {
            composite_cleanup_children(children, child_count, stdout_buf, stderr_buf);
            stop_property_service_shim(&property_shim, paths, stdout_buf);
            return -1;
        }
        service_query_result = run_lshal_wait_target_query_child(cfg,
                                                                 paths,
                                                                 stdout_buf,
                                                                 stderr_buf,
                                                                 cfg->timeout_sec * 1000);
        if (append_format(stdout_buf,
                          "wifi_companion_hal_order.service_query_result=%d\n",
                          service_query_result) < 0) {
            composite_cleanup_children(children, child_count, stdout_buf, stderr_buf);
            stop_property_service_shim(&property_shim, paths, stdout_buf);
            return -1;
        }
    }
    if (iwifi_start_mode && (!registration_query_mode || service_query_result == 0)) {
        bool warmup_timed_out = false;
        long warmup_deadline = monotonic_ms() + 500L;

        if (composite_poll_children(children,
                                    child_count,
                                    stdout_buf,
                                    stderr_buf,
                                    warmup_deadline,
                                    &warmup_timed_out) < 0) {
            composite_cleanup_children(children, child_count, stdout_buf, stderr_buf);
            stop_property_service_shim(&property_shim, paths, stdout_buf);
            return -1;
        }
        iwifi_start_result = run_iwifi_start_hwbinder_probe(paths, stdout_buf);
        if (append_wifi_surface_snapshot(stdout_buf, "wifi_companion_hal_order.surface_after_iwifi_start") < 0 ||
            append_wifi_runtime_surface_snapshot(stdout_buf, paths, "wifi_companion_hal_order.runtime_after_iwifi_start") < 0 ||
            append_format(stdout_buf,
                          "wifi_companion_hal_order.iwifi_start_result=%d\n",
                          iwifi_start_result) < 0) {
            composite_cleanup_children(children, child_count, stdout_buf, stderr_buf);
            stop_property_service_shim(&property_shim, paths, stdout_buf);
            return -1;
        }
    } else if (iwifi_start_mode) {
        iwifi_start_result = 21;
        if (append_format(stdout_buf,
                          "wifi_companion_hal_order.iwifi_start_skipped=1\n"
                          "wifi_companion_hal_order.iwifi_start_skip_reason=registration-query-result-%d\n"
                          "wifi_companion_hal_order.iwifi_start_result=%d\n",
                          service_query_result,
                          iwifi_start_result) < 0) {
            composite_cleanup_children(children, child_count, stdout_buf, stderr_buf);
            stop_property_service_shim(&property_shim, paths, stdout_buf);
            return -1;
        }
    }

    deadline = monotonic_ms() + ((registration_query_mode || iwifi_start_mode) ? 1000L : cfg->timeout_sec * 1000L);
    if (composite_poll_children(children,
                                child_count,
                                stdout_buf,
                                stderr_buf,
                                deadline,
                                timed_out) < 0) {
        composite_cleanup_children(children, child_count, stdout_buf, stderr_buf);
        stop_property_service_shim(&property_shim, paths, stdout_buf);
        return -1;
    }
    if (append_qipcrtr_protocol_summary(stdout_buf, "wifi_companion_hal_order.net_window") < 0 ||
        append_wifi_surface_snapshot(stdout_buf, "wifi_companion_hal_order.surface_window") < 0 ||
        append_wifi_runtime_surface_snapshot(stdout_buf, paths, "wifi_companion_hal_order.runtime_window") < 0) {
        composite_cleanup_children(children, child_count, stdout_buf, stderr_buf);
        stop_property_service_shim(&property_shim, paths, stdout_buf);
        return -1;
    }
    if (cfg->allow_qrtr_ns_readback &&
        append_companion_qrtr_wlfw_readback(stdout_buf, cfg) < 0) {
        composite_cleanup_children(children, child_count, stdout_buf, stderr_buf);
        stop_property_service_shim(&property_shim, paths, stdout_buf);
        return -1;
    }

    composite_capture_observable_children(children, child_count, stdout_buf);
    composite_cleanup_children(children, child_count, stdout_buf, stderr_buf);
    if (stop_property_service_shim(&property_shim, paths, stdout_buf) < 0) {
        return -1;
    }
    if (property_shim.started && (!property_shim.reaped || property_shim.kill_sent)) {
        all_postflight_safe = false;
    }
    if (append_qipcrtr_protocol_summary(stdout_buf, "wifi_companion_hal_order.net_after_cleanup") < 0 ||
        append_wifi_surface_snapshot(stdout_buf, "wifi_companion_hal_order.surface_after_cleanup") < 0 ||
        append_wifi_runtime_surface_snapshot(stdout_buf, paths, "wifi_companion_hal_order.runtime_after_cleanup") < 0) {
        return -1;
    }

    for (size_t i = 0; i < child_count; i++) {
        bool safe = composite_child_postflight_safe(&children[i]);

        if (!safe) {
            all_postflight_safe = false;
        }
        if (!children[i].observable) {
            all_observable_at_timeout = false;
        }
        if (composite_child_runtime_gap(&children[i], *timed_out)) {
            any_runtime_gap = true;
            if (*child_exit_code < 0 && children[i].exit_code >= 0) {
                *child_exit_code = children[i].exit_code;
            }
            if (*child_signal == 0 && children[i].signal != 0) {
                *child_signal = children[i].signal;
            }
        }
        if (append_format(stdout_buf,
                          "wifi_companion_hal_order.child.%s.observable=%d\n"
                          "wifi_companion_hal_order.child.%s.exited=%d\n"
                          "wifi_companion_hal_order.child.%s.exit_code=%d\n"
                          "wifi_companion_hal_order.child.%s.signal=%d\n"
                          "wifi_companion_hal_order.child.%s.term_sent=%d\n"
                          "wifi_companion_hal_order.child.%s.kill_sent=%d\n"
                          "wifi_companion_hal_order.child.%s.reaped=%d\n"
                          "wifi_companion_hal_order.child.%s.postflight_safe=%d\n",
                          children[i].name,
                          children[i].observable ? 1 : 0,
                          children[i].name,
                          children[i].child_done ? 1 : 0,
                          children[i].name,
                          children[i].exit_code,
                          children[i].name,
                          children[i].signal,
                          children[i].name,
                          children[i].term_sent ? 1 : 0,
                          children[i].name,
                          children[i].kill_sent ? 1 : 0,
                          children[i].name,
                          children[i].reaped ? 1 : 0,
                          children[i].name,
                          safe ? 1 : 0) < 0) {
            return -1;
        }
    }
    if (*child_exit_code < 0 && *child_signal == 0) {
        *child_exit_code = 0;
    }
    if (append_format(stdout_buf,
                      "wifi_companion_hal_order.timed_out=%d\n"
                      "wifi_companion_hal_order.all_observable_at_timeout=%d\n"
                      "wifi_companion_hal_order.all_postflight_safe=%d\n",
                      *timed_out ? 1 : 0,
                      all_observable_at_timeout ? 1 : 0,
                      all_postflight_safe ? 1 : 0) < 0) {
        return -1;
    }
    if (!all_postflight_safe) {
        append_literal(stdout_buf,
                       "wifi_companion_hal_order.result=start-only-reboot-required\n"
                       "wifi_companion_hal_order.reason=process-not-proven-stopped\n");
    } else if (iwifi_start_mode && registration_query_mode && service_query_result != 0) {
        append_literal(stdout_buf,
                       "wifi_companion_hal_order.result=iwifi-start-registration-query-failed\n"
                       "wifi_companion_hal_order.reason=lshal-wait-did-not-confirm-target-before-iwifi-start\n");
    } else if (iwifi_start_mode && iwifi_start_result == 20) {
        append_literal(stdout_buf,
                       "wifi_companion_hal_order.result=iwifi-service-null\n"
                       "wifi_companion_hal_order.reason=IWifi-default-handle-not-returned\n");
    } else if (iwifi_start_mode && iwifi_start_result != 0) {
        append_literal(stdout_buf,
                       "wifi_companion_hal_order.result=iwifi-transaction-failed\n"
                       "wifi_companion_hal_order.reason=IWifi-start-transaction-not-clean\n");
    } else if (iwifi_start_mode) {
        append_literal(stdout_buf,
                       "wifi_companion_hal_order.result=iwifi-start-transaction-pass\n"
                       "wifi_companion_hal_order.reason=IWifi-start-transaction-observed-and-children-clean\n");
    } else if (registration_query_mode && service_query_result == 10) {
        append_literal(stdout_buf,
                       "wifi_companion_hal_order.result=service-query-tool-missing\n"
                       "wifi_companion_hal_order.reason=lshal-unavailable\n");
    } else if (registration_query_mode && service_query_result == 12) {
        append_literal(stdout_buf,
                       "wifi_companion_hal_order.result=service-query-timeout\n"
                       "wifi_companion_hal_order.reason=lshal-wait-timeout\n");
    } else if (registration_query_mode && service_query_result != 0) {
        append_literal(stdout_buf,
                       "wifi_companion_hal_order.result=service-query-runtime-gap\n"
                       "wifi_companion_hal_order.reason=lshal-wait-query-failed\n");
    } else if (registration_query_mode) {
        append_literal(stdout_buf,
                       "wifi_companion_hal_order.result=service-query-pass\n"
                       "wifi_companion_hal_order.reason=lshal-wait-target-exit-zero-and-children-clean\n");
    } else if (*timed_out && all_observable_at_timeout) {
        append_literal(stdout_buf,
                       "wifi_companion_hal_order.result=order-window-pass\n"
                       "wifi_companion_hal_order.reason=all-order-children-observed-until-timeout-clean-stop\n");
    } else if (any_runtime_gap) {
        append_literal(stdout_buf,
                       "wifi_companion_hal_order.result=start-only-runtime-gap\n"
                       "wifi_companion_hal_order.reason=child-exited-before-observe-window\n");
    } else {
        append_literal(stdout_buf,
                       "wifi_companion_hal_order.result=manual-review-required\n"
                       "wifi_companion_hal_order.reason=unclassified-lifecycle-state\n");
    }
    append_literal(stdout_buf, "wifi_companion_hal_order.end=1\n");
    return 0;
}

static int setup_namespace(const struct config *cfg,
                           struct paths *paths,
                           size_t *linkerconfig_bytes,
                           uint64_t *linkerconfig_hash,
                           char *error_buf,
                           size_t error_size) {
    char system_apex[MAX_PATH_LEN];
    const char *vendor_mount_source = cfg->vendor_block;
    const char *linkerconfig_source = "/mnt/system/linkerconfig";

    if (unshare(CLONE_NEWNS) < 0) {
        snprintf(error_buf, error_size, "unshare: %s", strerror(errno));
        return -1;
    }
    if (mount(NULL, "/", NULL, MS_REC | MS_PRIVATE, NULL) < 0) {
        snprintf(error_buf, error_size, "make-rprivate: %s", strerror(errno));
        return -1;
    }
    if (init_paths(paths) < 0) {
        snprintf(error_buf, error_size, "init paths: %s", strerror(errno));
        return -1;
    }
    if (bind_ro(cfg->system_root, paths->system) < 0) {
        snprintf(error_buf, error_size, "bind system: %s", strerror(errno));
        return -1;
    }
    if (materialize_null_devices(cfg, paths, error_buf, error_size) < 0) {
        return -1;
    }
    if (materialize_selinuxfs_surface(cfg, paths, error_buf, error_size) < 0) {
        return -1;
    }
    if (materialize_service_manager_binder_devices(cfg, paths, error_buf, error_size) < 0) {
        return -1;
    }
    if (materialize_peripheral_manager_node_parity(cfg, paths, error_buf, error_size) < 0) {
        return -1;
    }
    if (materialize_wifi_wlan_device(cfg, paths, error_buf, error_size) < 0) {
        return -1;
    }
    if (materialize_rmt_storage_runtime_surface(cfg, paths, error_buf, error_size) < 0) {
        return -1;
    }
    if (materialize_private_properties(cfg, paths, error_buf, error_size) < 0) {
        return -1;
    }
    if (materialize_data_wifi(cfg, paths, error_buf, error_size) < 0) {
        return -1;
    }
    if (access(cfg->vendor_block, F_OK) < 0) {
        FILE *dev_file;
        unsigned int major_no;
        unsigned int minor_no;

        if (errno != ENOENT) {
            snprintf(error_buf, error_size, "stat vendor block: %s", strerror(errno));
            return -1;
        }
        dev_file = fopen("/sys/class/block/sda29/dev", "re");
        if (dev_file == NULL) {
            snprintf(error_buf, error_size, "open sda29 dev: %s", strerror(errno));
            return -1;
        }
        if (fscanf(dev_file, "%u:%u", &major_no, &minor_no) != 2) {
            fclose(dev_file);
            snprintf(error_buf, error_size, "parse sda29 dev: invalid");
            return -1;
        }
        fclose(dev_file);
        if (mknod(paths->vendor_source, S_IFBLK | 0600, makedev(major_no, minor_no)) < 0) {
            snprintf(error_buf, error_size, "mknod vendor block: %s", strerror(errno));
            return -1;
        }
        vendor_mount_source = paths->vendor_source;
    }
    if (mount(vendor_mount_source,
              paths->vendor,
              cfg->vendor_fstype,
              MS_RDONLY | MS_NOSUID | MS_NODEV,
              "noload") < 0) {
        snprintf(error_buf, error_size, "mount vendor: %s", strerror(errno));
        return -1;
    }
    if (materialize_wifi_firmware_mounts(cfg, paths, error_buf, error_size) < 0) {
        return -1;
    }
    if (mount("proc", paths->proc, "proc", MS_NOSUID | MS_NODEV | MS_NOEXEC, NULL) < 0) {
        snprintf(error_buf, error_size, "mount proc: %s", strerror(errno));
        return -1;
    }
    if (append_path(system_apex, sizeof(system_apex), cfg->system_root, "apex") < 0) {
        snprintf(error_buf, error_size, "system apex path: %s", strerror(errno));
        return -1;
    }
    if (access(system_apex, R_OK | X_OK) == 0) {
        if (streq(cfg->vndk_apex_alias_mode, "none")) {
            if (bind_ro(system_apex, paths->apex) < 0) {
                snprintf(error_buf, error_size, "bind apex: %s", strerror(errno));
                return -1;
            }
        } else if (materialize_apex_bind_farm(cfg, paths, system_apex, error_buf, error_size) < 0) {
            return -1;
        }
    } else {
        rmdir(paths->apex);
        paths->apex[0] = '\0';
    }
    if (!streq(cfg->linkerconfig_mode, "none")) {
        if (materialize_linkerconfig(cfg,
                                     paths,
                                     linkerconfig_bytes,
                                     linkerconfig_hash,
                                     error_buf,
                                     error_size) < 0) {
            return -1;
        }
    } else if (access(linkerconfig_source, R_OK | X_OK) == 0) {
        if (bind_ro(linkerconfig_source, paths->linkerconfig) < 0) {
            snprintf(error_buf, error_size, "bind linkerconfig: %s", strerror(errno));
            return -1;
        }
    } else {
        rmdir(paths->linkerconfig);
        paths->linkerconfig[0] = '\0';
    }
    return 0;
}

static void print_section(const char *name, const struct buffer *buf) {
    printf("A90_EXECNS_%s_BEGIN\n", name);
    if (buf->data != NULL && buf->len > 0) {
        fwrite(buf->data, 1, buf->len, stdout);
        if (buf->data[buf->len - 1] != '\n') {
            putchar('\n');
        }
    }
    printf("A90_EXECNS_%s_END truncated=%d bytes=%zu\n", name, buf->truncated ? 1 : 0, buf->len);
}

int main(int argc, char **argv) {
    struct config cfg;
    struct paths paths;
    struct buffer stdout_buf;
    struct buffer stderr_buf;
    char setup_error[256] = "";
    int child_exit_code = -1;
    int child_signal = 0;
    size_t linkerconfig_bytes = 0;
    uint64_t linkerconfig_hash = 0;
    bool timed_out = false;
    int parse_rc;
    int run_rc;

    if (argc == 2 && streq(argv[1], "--selinux-print-current")) {
        return run_selinux_print_current_early();
    }

    memset(&paths, 0, sizeof(paths));
    parse_rc = parse_args(argc, argv, &cfg);
    if (parse_rc != 0) {
        usage(stderr);
        return parse_rc;
    }
    if (buffer_init(&stdout_buf) < 0 || buffer_init(&stderr_buf) < 0) {
        perror("buffer init");
        return 20;
    }

    printf("A90_EXECNS_BEGIN version=\"%s\"\n", EXECNS_VERSION);
    printf("mode=%s\n", cfg.mode);
    printf("capture_mode=%s\n", cfg.capture_mode);
    printf("null_device_mode=%s\n", cfg.null_device_mode);
    printf("data_wifi_mode=%s\n", cfg.data_wifi_mode);
    printf("vndk_apex_alias_mode=%s\n", cfg.vndk_apex_alias_mode);
    printf("linkerconfig_mode=%s\n", cfg.linkerconfig_mode);
    printf("target_profile=%s\n", cfg.target_profile);
    printf("env_mode=%s\n", cfg.env_mode);
    printf("linkerconfig_source=%s\n",
           cfg.linkerconfig_source != NULL ? cfg.linkerconfig_source : "<none>");
    printf("apex_libraries_source=%s\n",
           cfg.apex_libraries_source != NULL ? cfg.apex_libraries_source : "<none>");
    printf("property_root=%s\n", cfg.property_root != NULL ? cfg.property_root : "<none>");
    printf("property_key=%s\n", cfg.property_key != NULL ? cfg.property_key : "<none>");
    printf("selinux_context=%s\n", cfg.selinux_context != NULL ? cfg.selinux_context : "<none>");
    printf("selinux_attr_mode=%s\n", cfg.selinux_attr_mode);
    printf("android_selinux_context_mode=%s\n", cfg.android_selinux_context_mode);
    printf("system_root=%s\n", cfg.system_root);
    printf("vendor_block=%s\n", cfg.vendor_block);
    printf("vendor_fstype=%s\n", cfg.vendor_fstype);
    printf("target=%s\n", cfg.target);
    printf("linker=%s\n", cfg.linker != NULL ? cfg.linker : "<none>");
    printf("timeout_sec=%d\n", cfg.timeout_sec);
    printf("allow_cnss_start_only=%d\n", cfg.allow_cnss_start_only ? 1 : 0);
    printf("allow_wifi_companion_start_only=%d\n",
           cfg.allow_wifi_companion_start_only ? 1 : 0);
    printf("allow_service_manager_start_only=%d\n",
           cfg.allow_service_manager_start_only ? 1 : 0);
    printf("allow_wifi_hal_start_only=%d\n",
           cfg.allow_wifi_hal_start_only ? 1 : 0);
    printf("allow_hal_service_query=%d\n",
           cfg.allow_hal_service_query ? 1 : 0);
    printf("allow_iwifi_start_only=%d\n",
           cfg.allow_iwifi_start_only ? 1 : 0);
    printf("allow_cnss_userspace_readiness=%d\n",
           cfg.allow_cnss_userspace_readiness ? 1 : 0);
    printf("allow_qrtr_ns_readback=%d\n",
           cfg.allow_qrtr_ns_readback ? 1 : 0);
    printf("allow_servloc_domain_list_probe=%d\n",
           cfg.allow_servloc_domain_list_probe ? 1 : 0);
    printf("allow_service_notifier_listener_probe=%d\n",
           cfg.allow_service_notifier_listener_probe ? 1 : 0);
    printf("allow_scan_only=%d\n",
           cfg.allow_scan_only ? 1 : 0);
    printf("allow_connect_dhcp_ping=%d\n",
           cfg.allow_connect_dhcp_ping ? 1 : 0);
    printf("allow_policy_load_proof=%d\n",
           cfg.allow_policy_load_proof ? 1 : 0);
    printf("allow_esoc_control_preflight=%d\n",
           cfg.allow_esoc_control_preflight ? 1 : 0);
    printf("allow_esoc_engine_register_preflight=%d\n",
           cfg.allow_esoc_engine_register_preflight ? 1 : 0);
    printf("allow_esoc_req_registered_subsys_hold_preflight=%d\n",
           cfg.allow_esoc_req_registered_subsys_hold_preflight ? 1 : 0);
    printf("connect_config=%s\n", cfg.connect_config != NULL ? cfg.connect_config : "<none>");
    printf("connect_iface=%s\n", cfg.connect_iface != NULL ? cfg.connect_iface : "<none>");
    printf("ping_target=%s\n", cfg.ping_target != NULL ? cfg.ping_target : "<none>");
    printf("qrtr_readback_matrix=%s\n",
           cfg.qrtr_readback_matrix != NULL ? cfg.qrtr_readback_matrix : "<none>");

    if (is_service_notifier_listener_only_mode(cfg.mode)) {
        printf("helper_status=namespace-skipped\n");
        if (append_literal(&stdout_buf,
                           "service_notifier_listener_only.begin=1\n"
                           "service_notifier_listener_only.namespace=global\n"
                           "service_notifier_listener_only.service_manager_start_executed=0\n"
                           "service_notifier_listener_only.wifi_hal_start_executed=0\n"
                           "service_notifier_listener_only.scan_connect_linkup=0\n"
                           "service_notifier_listener_only.credentials=0\n"
                           "service_notifier_listener_only.dhcp_routing=0\n"
                           "service_notifier_listener_only.external_ping=0\n") < 0 ||
            append_companion_service_notifier_listener_probe(&stdout_buf, &cfg) < 0 ||
            append_literal(&stdout_buf,
                           "service_notifier_listener_only.result=complete\n"
                           "service_notifier_listener_only.end=1\n") < 0) {
            run_rc = -1;
            child_exit_code = 20;
        } else {
            run_rc = 0;
            child_exit_code = 0;
        }
        child_signal = 0;
        timed_out = false;
        printf("probe_run_rc=%d\n", run_rc);
        printf("child_exit_code=%d\n", child_exit_code);
        printf("child_signal=%d\n", child_signal);
        printf("timed_out=%d\n", timed_out ? 1 : 0);
        print_section("STDOUT", &stdout_buf);
        print_section("STDERR", &stderr_buf);
        printf("cleanup_status=not-required\n");
        printf("A90_EXECNS_END rc=0\n");
        buffer_free(&stdout_buf);
        buffer_free(&stderr_buf);
        return 0;
    }

    if (setup_namespace(&cfg,
                        &paths,
                        &linkerconfig_bytes,
                        &linkerconfig_hash,
                        setup_error,
                        sizeof(setup_error)) < 0) {
        printf("helper_status=setup-error\n");
        printf("setup_error=%s\n", setup_error);
        cleanup_paths(&paths);
        printf("cleanup_status=attempted\n");
        printf("A90_EXECNS_END rc=20\n");
        buffer_free(&stdout_buf);
        buffer_free(&stderr_buf);
        return 20;
    }

    printf("helper_status=namespace-ready\n");
    printf("temp_base=%s\n", paths.base);
    printf("temp_root=%s\n", paths.root);
    printf("vendor_mount_source=%s\n",
           access(paths.vendor_source, F_OK) == 0 ? paths.vendor_source : cfg.vendor_block);
    printf("firmware_mnt_mount_source=%s\n",
           access(paths.firmware_mnt_source, F_OK) == 0 ? paths.firmware_mnt_source : "<not-mounted>");
    printf("firmware_modem_mount_source=%s\n",
           access(paths.firmware_modem_source, F_OK) == 0 ? paths.firmware_modem_source : "<not-mounted>");
    printf("linkerconfig_mount_source=%s\n",
           streq(cfg.linkerconfig_mode, "none")
               ? (paths.linkerconfig[0] != '\0' ? "/mnt/system/linkerconfig" : "<absent>")
               : "<private-materialized>");
    printf("apex_mount_source=%s\n",
           paths.apex[0] == '\0'
               ? "<absent>"
               : (streq(cfg.vndk_apex_alias_mode, "none")
                      ? "/mnt/system/system/apex"
                      : "<private-bind-farm>"));
    printf("linkerconfig_bytes=%zu\n", linkerconfig_bytes);
    printf("linkerconfig_hash=0x%016llx\n", (unsigned long long)linkerconfig_hash);
    print_preexec_context(&cfg, &paths);
    if (streq(cfg.mode, "identity-probe")) {
        run_rc = run_identity_probe(&cfg,
                                    &paths,
                                    &stdout_buf,
                                    &stderr_buf,
                                    &child_exit_code,
                                    &child_signal,
                                    &timed_out);
    } else if (streq(cfg.mode, "sepolicy-inventory")) {
        run_rc = run_sepolicy_inventory(&cfg, &paths, &stdout_buf);
        child_exit_code = run_rc == 0 ? 0 : run_rc;
        child_signal = 0;
    } else if (streq(cfg.mode, "wifi-connect-tool-surface")) {
        run_rc = run_wifi_connect_tool_surface(&cfg, &paths, &stdout_buf);
        child_exit_code = run_rc == 0 ? 0 : run_rc;
        child_signal = 0;
        timed_out = false;
    } else if (streq(cfg.mode, "sepolicy-compile-proof")) {
        run_rc = run_sepolicy_compile_proof(&cfg, &paths, &stdout_buf, &stderr_buf);
        child_exit_code = run_rc == 0 ? 0 : run_rc;
        child_signal = 0;
        timed_out = run_rc == 12;
    } else if (streq(cfg.mode, "sepolicy-load-proof")) {
        run_rc = run_sepolicy_load_proof(&cfg, &paths, &stdout_buf, &stderr_buf);
        child_exit_code = run_rc == 0 ? 0 : run_rc;
        child_signal = 0;
        timed_out = false;
    } else if (streq(cfg.mode, "selinux-domain-proof")) {
        run_rc = run_selinux_domain_proof(&cfg,
                                          &paths,
                                          &stdout_buf,
                                          &stderr_buf,
                                          &child_exit_code,
                                          &child_signal,
                                          &timed_out);
    } else if (streq(cfg.mode, "property-lookup")) {
        run_rc = run_property_lookup(&cfg,
                                     &paths,
                                     &stdout_buf,
                                     &stderr_buf,
                                     &child_exit_code,
                                     &child_signal,
                                     &timed_out);
    } else if (streq(cfg.mode, "cnss-start-only")) {
        run_rc = run_cnss_start_only_guarded(&cfg,
                                             &paths,
                                             &stdout_buf,
                                             &stderr_buf,
                                             &child_exit_code,
                                             &child_signal,
                                             &timed_out);
    } else if (is_cnss_userspace_readiness_mode(cfg.mode)) {
        run_rc = run_cnss_userspace_readiness_guarded(&cfg,
                                                      &paths,
                                                      &stdout_buf,
                                                      &stderr_buf,
                                                      &child_exit_code,
                                                      &child_signal,
                                                      &timed_out);
    } else if (is_rmt_storage_start_only_mode(cfg.mode)) {
        run_rc = run_rmt_storage_start_only_guarded(&cfg,
                                                    &paths,
                                                    &stdout_buf,
                                                    &stderr_buf,
                                                    &child_exit_code,
                                                    &child_signal,
                                                    &timed_out);
    } else if (is_subsys_hold_open_proof_mode(cfg.mode)) {
        run_rc = run_subsys_hold_open_proof(&cfg,
                                            &paths,
                                            &stdout_buf,
                                            &stderr_buf,
                                            &child_exit_code,
                                            &child_signal,
                                            &timed_out);
    } else if (is_wifi_companion_esoc_control_preflight_mode(cfg.mode)) {
        run_rc = run_wifi_companion_esoc_control_preflight_guarded(&cfg,
                                                                   &paths,
                                                                   &stdout_buf,
                                                                   &stderr_buf,
                                                                   &child_exit_code,
                                                                   &child_signal,
                                                                   &timed_out);
    } else if (is_wifi_companion_esoc_engine_register_preflight_mode(cfg.mode)) {
        run_rc = run_wifi_companion_esoc_engine_register_preflight_guarded(&cfg,
                                                                           &paths,
                                                                           &stdout_buf,
                                                                           &stderr_buf,
                                                                           &child_exit_code,
                                                                           &child_signal,
                                                                           &timed_out);
    } else if (is_wifi_companion_esoc_req_registered_subsys_hold_preflight_mode(cfg.mode)) {
        run_rc = run_wifi_companion_esoc_req_registered_subsys_hold_preflight_guarded(&cfg,
                                                                                      &paths,
                                                                                      &stdout_buf,
                                                                                      &stderr_buf,
                                                                                      &child_exit_code,
                                                                                      &child_signal,
                                                                                      &timed_out);
    } else if (is_wifi_companion_any_start_only_mode(cfg.mode)) {
        run_rc = run_wifi_companion_start_only_guarded(&cfg,
                                                       &paths,
                                                       &stdout_buf,
                                                       &stderr_buf,
                                                       &child_exit_code,
                                                       &child_signal,
                                                       &timed_out);
    } else if (is_wifi_companion_hal_order_start_only_mode(cfg.mode)) {
        run_rc = run_wifi_companion_hal_order_start_only_guarded(&cfg,
                                                                 &paths,
                                                                 &stdout_buf,
                                                                 &stderr_buf,
                                                                 &child_exit_code,
                                                                 &child_signal,
                                                                 &timed_out);
    } else if (streq(cfg.mode, "private-selinux-proof")) {
        if (append_literal(&stdout_buf,
                           "private_selinux_proof.result=pass\n"
                           "private_selinux_proof.exec_attempted=0\n"
                           "private_selinux_proof.daemon_start_executed=0\n"
                           "private_selinux_proof.wifi_bringup_executed=0\n") < 0) {
            run_rc = -1;
        } else {
            run_rc = 0;
            child_exit_code = 0;
        }
    } else if (streq(cfg.mode, "service-manager-start-only")) {
        run_rc = run_service_manager_start_only_guarded(&cfg,
                                                        &paths,
                                                        &stdout_buf,
                                                        &stderr_buf,
                                                        &child_exit_code,
                                                        &child_signal,
                                                        &timed_out);
    } else if (is_lshal_readonly_query_mode(cfg.mode)) {
        run_rc = run_lshal_service_query_child(&cfg,
                                               &paths,
                                               &stdout_buf,
                                               &stderr_buf,
                                               cfg.timeout_sec * 1000);
        child_exit_code = run_rc == 0 ? 0 : run_rc;
        child_signal = 0;
        timed_out = run_rc == 12;
    } else if (is_wifi_hal_composite_mode(cfg.mode)) {
        run_rc = run_wifi_hal_composite_start_only_guarded(&cfg,
                                                           &paths,
                                                           &stdout_buf,
                                                           &stderr_buf,
                                                           &child_exit_code,
                                                           &child_signal,
                                                           &timed_out);
    } else {
        run_rc = run_linker_list(&cfg,
                                 &paths,
                                 &stdout_buf,
                                 &stderr_buf,
                                 &child_exit_code,
                                 &child_signal,
                                 &timed_out);
    }
    printf("probe_run_rc=%d\n", run_rc);
    printf("child_exit_code=%d\n", child_exit_code);
    printf("child_signal=%d\n", child_signal);
    printf("timed_out=%d\n", timed_out ? 1 : 0);
    print_section("STDOUT", &stdout_buf);
    print_section("STDERR", &stderr_buf);
    cleanup_paths(&paths);
    printf("cleanup_status=attempted\n");
    printf("A90_EXECNS_END rc=0\n");

    buffer_free(&stdout_buf);
    buffer_free(&stderr_buf);
    return 0;
}
