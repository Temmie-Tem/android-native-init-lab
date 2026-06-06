/* Included by workspace/public/src/native-init/init_v724.c. Do not compile standalone. */

#include <net/if.h>
#include <netinet/in.h>
#include <sys/socket.h>

static void storage_boot_set_line(void *ctx, int line, const char *text) {
    (void)ctx;
    boot_splash_set_line((size_t)line, "%s", text);
}

static void storage_boot_draw_frame(void *ctx) {
    (void)ctx;
    boot_auto_frame();
}

static void selftest_boot_set_line(void *ctx, int line, const char *text) {
    (void)ctx;
    boot_splash_set_line((size_t)line, "%s", text);
}

static void selftest_boot_draw_frame(void *ctx) {
    (void)ctx;
    boot_auto_frame();
}


#define A90_V641_SIBLING_SSCTL_FLAG "/cache/native-init-sibling-fwssctl-v641"
#define A90_V641_SIBLING_SSCTL_LOG "/cache/native-init-sibling-fwssctl-v641.log"
#define A90_V641_SIBLING_SSCTL_TIMEOUT_MS 5000
#define A90_V641_VENDOR_DIR "/vendor"
#define A90_V641_FW_MNT_DIR "/vendor/firmware_mnt"
#define A90_V641_FW_MODEM_DIR "/vendor/firmware-modem"
#define A90_V641_SYSTEM_VENDOR_DIR "/mnt/system/vendor"
static int v641_find_block_by_partname(const char *partname,
                                       const char *fallback_block,
                                       char *out,
                                       size_t out_size);
static int v641_prepare_firmware_mounts(void);
#define A90_V724_QRTR_BOOT_FLAG "/cache/native-init-qrtr-servloc-boot-v724"
#define A90_V724_QRTR_BOOT_LOG "/cache/native-init-qrtr-servloc-boot-v724.log"
#define A90_V724_QRTR_BOOT_PID "/cache/native-init-qrtr-servloc-boot-v724.pid"
#define A90_V724_QRTR_HELPER "/cache/bin/a90_android_execns_probe"
#define A90_V724_QRTR_TIMEOUT_SEC "8"
#define A90_V724_QRTR_MODE "wifi-companion-android-order-post-sysmon-observer-start-only"
#ifdef A90_WIFI_LIFECYCLE_MODEM_OWNER
#ifndef A90_WIFI_LIFECYCLE_MODEM_OWNER_LOG
#define A90_WIFI_LIFECYCLE_MODEM_OWNER_LOG "/cache/native-init-wifi-lifecycle-modem-owner.log"
#endif
#ifndef A90_WIFI_LIFECYCLE_MODEM_OWNER_PID
#define A90_WIFI_LIFECYCLE_MODEM_OWNER_PID "/cache/native-init-wifi-lifecycle-modem-owner.pid"
#endif
#ifndef A90_WIFI_LIFECYCLE_MODEM_OWNER_DEVNODE
#define A90_WIFI_LIFECYCLE_MODEM_OWNER_DEVNODE "/dev/subsys_modem"
#endif
#ifndef A90_WIFI_LIFECYCLE_MODEM_OWNER_SYSDEV
#define A90_WIFI_LIFECYCLE_MODEM_OWNER_SYSDEV "/sys/class/subsys/subsys_modem/dev"
#endif
#endif
#ifdef A90_WIFI_TEST_BOOT
#ifndef A90_WIFI_TEST_BOOT_LABEL
#define A90_WIFI_TEST_BOOT_LABEL "v1393"
#endif
#ifndef A90_WIFI_TEST_BOOT_KLOG_PREFIX
#define A90_WIFI_TEST_BOOT_KLOG_PREFIX "A90v1393"
#endif
#ifndef A90_WIFI_TEST_BOOT_DISABLE
#define A90_WIFI_TEST_BOOT_DISABLE "/cache/native-init-wifi-test-boot-v1393.disable"
#endif
#ifndef A90_WIFI_TEST_BOOT_LOG
#define A90_WIFI_TEST_BOOT_LOG "/cache/native-init-wifi-test-boot-v1393.log"
#endif
#ifndef A90_WIFI_TEST_BOOT_SUMMARY
#define A90_WIFI_TEST_BOOT_SUMMARY "/cache/native-init-wifi-test-boot-v1393.summary"
#endif
#ifndef A90_WIFI_RUNTIME_SUMMARY
#define A90_WIFI_RUNTIME_SUMMARY "/cache/native-init-wifi-runtime.summary"
#endif
#ifndef A90_WIFI_RUNTIME_SUMMARY_TMP
#define A90_WIFI_RUNTIME_SUMMARY_TMP "/cache/native-init-wifi-runtime.summary.tmp"
#endif
#ifndef A90_WIFI_RUNTIME_PID
#define A90_WIFI_RUNTIME_PID "/cache/native-init-wifi-runtime.pid"
#endif
#ifndef A90_WIFI_RUNTIME_OPTIONAL_INPUT
#define A90_WIFI_RUNTIME_OPTIONAL_INPUT "/cache/native-init-wifi-runtime-input.summary"
#endif
#ifndef A90_WIFI_TEST_BOOT_HELPER_RESULT
#define A90_WIFI_TEST_BOOT_HELPER_RESULT "/cache/native-init-wifi-test-boot-v1393-helper.result"
#endif
#ifndef A90_WIFI_TEST_BOOT_PID
#define A90_WIFI_TEST_BOOT_PID "/cache/native-init-wifi-test-boot-v1393.pid"
#endif
#ifndef A90_WIFI_TEST_BOOT_WATCHER_PID
#define A90_WIFI_TEST_BOOT_WATCHER_PID "/cache/native-init-wifi-test-boot-v1393-watcher.pid"
#endif
#ifndef A90_WIFI_TEST_BOOT_WATCH_SEC
#define A90_WIFI_TEST_BOOT_WATCH_SEC 35
#endif
#ifndef A90_WIFI_TEST_BOOT_SUPERVISE_HELPER
#define A90_WIFI_TEST_BOOT_SUPERVISE_HELPER 0
#endif
#ifndef A90_WIFI_TEST_BOOT_SUPERVISOR_TIMEOUT_SEC
#define A90_WIFI_TEST_BOOT_SUPERVISOR_TIMEOUT_SEC 40
#endif
#ifndef A90_WIFI_TEST_BOOT_MOUNT_DEBUGFS
#define A90_WIFI_TEST_BOOT_MOUNT_DEBUGFS 0
#endif
#ifndef A90_WIFI_TEST_BOOT_FIRMWARE_MOUNTS
#define A90_WIFI_TEST_BOOT_FIRMWARE_MOUNTS 0
#endif
#ifndef A90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH
#define A90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH 0
#endif
#ifndef A90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH_VALUE
#define A90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH_VALUE "/mnt/vendor/firmware"
#endif
#if A90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH && !A90_WIFI_TEST_BOOT_SUPERVISE_HELPER
#error A90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH requires A90_WIFI_TEST_BOOT_SUPERVISE_HELPER
#endif
#ifndef A90_WIFI_TEST_BOOT_PID1_RC1_WATCHER
#define A90_WIFI_TEST_BOOT_PID1_RC1_WATCHER 0
#endif
#ifndef A90_WIFI_TEST_BOOT_RC1_WATCHER_TIMEOUT_SEC
#define A90_WIFI_TEST_BOOT_RC1_WATCHER_TIMEOUT_SEC 45
#endif
#ifndef A90_WIFI_TEST_BOOT_RC1_WATCHER_DELAY_MS
#define A90_WIFI_TEST_BOOT_RC1_WATCHER_DELAY_MS 0
#endif
#ifndef A90_WIFI_TEST_BOOT_RC1_WATCHER_RESULT
#define A90_WIFI_TEST_BOOT_RC1_WATCHER_RESULT "/cache/native-init-wifi-test-boot-v1393-rc1-watcher.result"
#endif
#ifndef A90_WIFI_TEST_BOOT_RC1_WINDOW_SAMPLER
#define A90_WIFI_TEST_BOOT_RC1_WINDOW_SAMPLER 0
#endif
#ifndef A90_WIFI_TEST_BOOT_RC1_WINDOW_RESULT
#define A90_WIFI_TEST_BOOT_RC1_WINDOW_RESULT "/cache/native-init-wifi-test-boot-v1393-rc1-window.result"
#endif
#ifndef A90_WIFI_TEST_BOOT_RC1_ENDPOINT_SAMPLER
#define A90_WIFI_TEST_BOOT_RC1_ENDPOINT_SAMPLER 0
#endif
#ifndef A90_WIFI_TEST_BOOT_RC1_FOCUSED_ENDPOINT_SAMPLER
#define A90_WIFI_TEST_BOOT_RC1_FOCUSED_ENDPOINT_SAMPLER 0
#endif
#ifndef A90_WIFI_TEST_BOOT_RC1_IMMEDIATE_ENDPOINT_SAMPLER
#define A90_WIFI_TEST_BOOT_RC1_IMMEDIATE_ENDPOINT_SAMPLER 0
#endif
#ifndef A90_WIFI_TEST_BOOT_RC1_MICRO_ENDPOINT_SAMPLER
#define A90_WIFI_TEST_BOOT_RC1_MICRO_ENDPOINT_SAMPLER 0
#endif
#ifndef A90_WIFI_TEST_BOOT_RC1_MICRO_FOCUSED_ENDPOINT_SAMPLER
#define A90_WIFI_TEST_BOOT_RC1_MICRO_FOCUSED_ENDPOINT_SAMPLER 0
#endif
#ifndef A90_WIFI_TEST_BOOT_RC1_MICRO_BATCHED_FOCUSED_ENDPOINT_SAMPLER
#define A90_WIFI_TEST_BOOT_RC1_MICRO_BATCHED_FOCUSED_ENDPOINT_SAMPLER 0
#endif
#ifndef A90_WIFI_TEST_BOOT_RC1_MICRO_SOURCE_TIMESTAMPED_SAMPLER
#define A90_WIFI_TEST_BOOT_RC1_MICRO_SOURCE_TIMESTAMPED_SAMPLER 0
#endif
#ifndef A90_WIFI_TEST_BOOT_RC1_MICRO_CRITICAL_FAST_ENDPOINT_SAMPLER
#define A90_WIFI_TEST_BOOT_RC1_MICRO_CRITICAL_FAST_ENDPOINT_SAMPLER 0
#endif
#ifndef A90_WIFI_TEST_BOOT_RC1_CASE_ALIGNED_MICRO_ENDPOINT_SAMPLER
#define A90_WIFI_TEST_BOOT_RC1_CASE_ALIGNED_MICRO_ENDPOINT_SAMPLER 0
#endif
#ifndef A90_WIFI_TEST_BOOT_RC1_SYSFS_CLIENT_ENUMERATE
#define A90_WIFI_TEST_BOOT_RC1_SYSFS_CLIENT_ENUMERATE 0
#endif
#if A90_WIFI_TEST_BOOT_RC1_SYSFS_CLIENT_ENUMERATE
#define A90_V1536_RC1_ENUMERATE_TRIGGER_MODE "sysfs_client_enumerate"
#define A90_V1536_RC1_ENUMERATE_TRIGGER_PATH "/sys/devices/platform/soc/1c08000.qcom,pcie/debug/enumerate"
#define A90_V1536_RC1_ENUMERATE_TRIGGER_VALUE "1\n"
#else
#define A90_V1536_RC1_ENUMERATE_TRIGGER_MODE "debugfs_test11"
#define A90_V1536_RC1_ENUMERATE_RC_SEL_PATH "/sys/kernel/debug/pci-msm/rc_sel"
#define A90_V1536_RC1_ENUMERATE_CASE_PATH "/sys/kernel/debug/pci-msm/case"
#endif
#ifndef A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_MICRO_ENDPOINT_SAMPLER
#define A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_MICRO_ENDPOINT_SAMPLER 0
#endif
#ifndef A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_EXACT_LINE
#define A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_EXACT_LINE 0
#endif
#ifndef A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_LONG_WINDOW
#define A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_LONG_WINDOW 0
#endif
#ifndef A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_THREAD_STATE
#define A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_THREAD_STATE 0
#endif
#ifndef A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_TRACEPOINT_SAMPLER
#define A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_TRACEPOINT_SAMPLER 0
#endif
#ifndef A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_PIL_TRACEPOINT_SAMPLER
#define A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_PIL_TRACEPOINT_SAMPLER 0
#endif
#ifndef A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_EFFECTIVE_LEVEL_SAMPLER
#define A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_EFFECTIVE_LEVEL_SAMPLER 0
#endif
#ifndef A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_AP2MDM_HOLD
#define A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_AP2MDM_HOLD 0
#endif
#ifndef A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_AP2MDM_HOLD_AFTER_MS
#define A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_AP2MDM_HOLD_AFTER_MS 320
#endif
#ifndef A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_AP2MDM_HOLD_MS
#define A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_AP2MDM_HOLD_MS 500
#endif
#ifndef A90_WIFI_TEST_BOOT_NATURAL_MDM2AP_IRQ_SUMMARY
#define A90_WIFI_TEST_BOOT_NATURAL_MDM2AP_IRQ_SUMMARY 0
#endif
#ifndef A90_WIFI_TEST_BOOT_NATURAL_POWER_DIFF_SNAPSHOT
#define A90_WIFI_TEST_BOOT_NATURAL_POWER_DIFF_SNAPSHOT 0
#endif
#ifndef A90_WIFI_TEST_BOOT_PCIE1_CLOCK_VOTE_PROOF
#define A90_WIFI_TEST_BOOT_PCIE1_CLOCK_VOTE_PROOF 0
#endif
#ifndef A90_WIFI_TEST_BOOT_PCIE1_CLOCK_VOTE_RESULT
#define A90_WIFI_TEST_BOOT_PCIE1_CLOCK_VOTE_RESULT "/cache/native-init-wifi-test-boot-v1393-pcie1-clock-vote.result"
#endif
#ifndef A90_WIFI_TEST_BOOT_PCIE1_CLOCK_VOTE_ASYNC
#define A90_WIFI_TEST_BOOT_PCIE1_CLOCK_VOTE_ASYNC 0
#endif
#ifndef A90_WIFI_TEST_BOOT_PCIE1_CLOCK_VOTE_WAIT_MS
#define A90_WIFI_TEST_BOOT_PCIE1_CLOCK_VOTE_WAIT_MS 20000
#endif
#ifndef A90_WIFI_TEST_BOOT_PCIE1_CLOCK_VOTE_HOLD_MS
#define A90_WIFI_TEST_BOOT_PCIE1_CLOCK_VOTE_HOLD_MS 30000
#endif
#ifndef A90_WIFI_TEST_BOOT_AUTO_READINESS_SUPERVISOR
#define A90_WIFI_TEST_BOOT_AUTO_READINESS_SUPERVISOR 0
#endif
#ifndef SYSLOG_ACTION_READ_ALL
#define SYSLOG_ACTION_READ_ALL 3
#endif
#ifndef A90_WIFI_TEST_BOOT_RC1_RETRY_COUNT
#define A90_WIFI_TEST_BOOT_RC1_RETRY_COUNT 0
#endif
#ifndef A90_WIFI_TEST_BOOT_RC1_RETRY_DELAY_MS
#define A90_WIFI_TEST_BOOT_RC1_RETRY_DELAY_MS 0
#endif
#define A90_V1393_WIFI_TEST_DISABLE A90_WIFI_TEST_BOOT_DISABLE
#define A90_V1393_WIFI_TEST_LOG A90_WIFI_TEST_BOOT_LOG
#define A90_V1393_WIFI_TEST_SUMMARY A90_WIFI_TEST_BOOT_SUMMARY
#define A90_V1393_WIFI_TEST_HELPER_RESULT A90_WIFI_TEST_BOOT_HELPER_RESULT
#define A90_V1393_WIFI_TEST_PID A90_WIFI_TEST_BOOT_PID
#define A90_V1393_WIFI_TEST_WATCHER_PID A90_WIFI_TEST_BOOT_WATCHER_PID
#define A90_V1393_WIFI_TEST_RC1_WATCHER_RESULT A90_WIFI_TEST_BOOT_RC1_WATCHER_RESULT
#define A90_V1393_WIFI_TEST_RC1_WINDOW_RESULT A90_WIFI_TEST_BOOT_RC1_WINDOW_RESULT
#if A90_WIFI_TEST_BOOT_AUTO_READINESS_SUPERVISOR
#define A90_V1393_WIFI_TEST_RC1_WINDOW_SAMPLER_NAME "auto-v1485-wifi-readiness-test"
#elif A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_MICRO_ENDPOINT_SAMPLER && A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_EXACT_LINE && A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_LONG_WINDOW && A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_THREAD_STATE && A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_TRACEPOINT_SAMPLER && A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_PIL_TRACEPOINT_SAMPLER && A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_EFFECTIVE_LEVEL_SAMPLER && A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_AP2MDM_HOLD
#define A90_V1393_WIFI_TEST_RC1_WINDOW_SAMPLER_NAME "bounded-v1477-ap2mdm-hold-test"
#elif A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_MICRO_ENDPOINT_SAMPLER && A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_EXACT_LINE && A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_LONG_WINDOW && A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_THREAD_STATE && A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_TRACEPOINT_SAMPLER && A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_PIL_TRACEPOINT_SAMPLER && A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_EFFECTIVE_LEVEL_SAMPLER
#define A90_V1393_WIFI_TEST_RC1_WINDOW_SAMPLER_NAME "read-only-v1472-exact-provider-effective-level"
#elif A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_MICRO_ENDPOINT_SAMPLER && A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_EXACT_LINE && A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_LONG_WINDOW && A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_THREAD_STATE && A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_TRACEPOINT_SAMPLER && A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_PIL_TRACEPOINT_SAMPLER
#define A90_V1393_WIFI_TEST_RC1_WINDOW_SAMPLER_NAME "read-only-v1467-exact-provider-pil-gpio-tracepoint"
#elif A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_MICRO_ENDPOINT_SAMPLER && A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_EXACT_LINE && A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_LONG_WINDOW && A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_THREAD_STATE && A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_TRACEPOINT_SAMPLER
#define A90_V1393_WIFI_TEST_RC1_WINDOW_SAMPLER_NAME "read-only-v1462-exact-provider-tracepoint"
#elif A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_MICRO_ENDPOINT_SAMPLER && A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_EXACT_LINE && A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_LONG_WINDOW && A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_THREAD_STATE
#define A90_V1393_WIFI_TEST_RC1_WINDOW_SAMPLER_NAME "read-only-v1458-exact-provider-thread-state"
#elif A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_MICRO_ENDPOINT_SAMPLER && A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_EXACT_LINE && A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_LONG_WINDOW
#define A90_V1393_WIFI_TEST_RC1_WINDOW_SAMPLER_NAME "read-only-v1454-exact-provider-long-endpoint"
#elif A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_MICRO_ENDPOINT_SAMPLER
#define A90_V1393_WIFI_TEST_RC1_WINDOW_SAMPLER_NAME "read-only-v1450-provider-trigger-micro-endpoint"
#elif A90_WIFI_TEST_BOOT_RC1_SYSFS_CLIENT_ENUMERATE
#define A90_V1393_WIFI_TEST_RC1_WINDOW_SAMPLER_NAME "read-only-v1536-sysfs-client-enumerate"
#elif A90_WIFI_TEST_BOOT_RC1_CASE_ALIGNED_MICRO_ENDPOINT_SAMPLER
#define A90_V1393_WIFI_TEST_RC1_WINDOW_SAMPLER_NAME "read-only-v1445-case-aligned-micro-endpoint"
#elif A90_WIFI_TEST_BOOT_RC1_MICRO_ENDPOINT_SAMPLER
#define A90_V1393_WIFI_TEST_RC1_WINDOW_SAMPLER_NAME "read-only-v1441-micro-endpoint"
#elif A90_WIFI_TEST_BOOT_RC1_IMMEDIATE_ENDPOINT_SAMPLER
#define A90_V1393_WIFI_TEST_RC1_WINDOW_SAMPLER_NAME "read-only-v1437-immediate-endpoint"
#elif A90_WIFI_TEST_BOOT_RC1_FOCUSED_ENDPOINT_SAMPLER
#define A90_V1393_WIFI_TEST_RC1_WINDOW_SAMPLER_NAME "read-only-v1433-focused-endpoint-prereq"
#elif A90_WIFI_TEST_BOOT_RC1_ENDPOINT_SAMPLER
#define A90_V1393_WIFI_TEST_RC1_WINDOW_SAMPLER_NAME "read-only-v1429-endpoint-prereq"
#else
#define A90_V1393_WIFI_TEST_RC1_WINDOW_SAMPLER_NAME "read-only-v1420"
#endif
#define A90_V1393_WIFI_TEST_HELPER "/bin/a90_android_execns_probe"
#ifndef A90_V1393_WIFI_TEST_TIMEOUT_SEC
#define A90_V1393_WIFI_TEST_TIMEOUT_SEC "30"
#endif
#ifndef A90_WIFI_TEST_BOOT_ANDROID_SERVICE_WINDOW
#define A90_WIFI_TEST_BOOT_ANDROID_SERVICE_WINDOW 0
#endif
#ifndef A90_WIFI_TEST_BOOT_ANDROID_SERVICE_WINDOW_SUBSYS_TRIGGER_CAPTURE
#define A90_WIFI_TEST_BOOT_ANDROID_SERVICE_WINDOW_SUBSYS_TRIGGER_CAPTURE 0
#endif
#ifndef A90_WIFI_TEST_BOOT_ANDROID_SERVICE_WINDOW_PM_PROXY_CONTRACT
#define A90_WIFI_TEST_BOOT_ANDROID_SERVICE_WINDOW_PM_PROXY_CONTRACT 0
#endif
#ifndef A90_WIFI_TEST_BOOT_ANDROID_SERVICE_WINDOW_LATE_PER_PROXY_ONLY
#define A90_WIFI_TEST_BOOT_ANDROID_SERVICE_WINDOW_LATE_PER_PROXY_ONLY 0
#endif
#ifndef A90_WIFI_TEST_BOOT_ANDROID_SERVICE_WINDOW_PM_FIRST_ROUTE
#define A90_WIFI_TEST_BOOT_ANDROID_SERVICE_WINDOW_PM_FIRST_ROUTE 0
#endif
#ifndef A90_WIFI_TEST_BOOT_ANDROID_SERVICE_WINDOW_PM_FIRST_LATE_PER_PROXY_ROUTE
#define A90_WIFI_TEST_BOOT_ANDROID_SERVICE_WINDOW_PM_FIRST_LATE_PER_PROXY_ROUTE 0
#endif
#ifndef A90_WIFI_TEST_BOOT_ANDROID_SERVICE_WINDOW_PPH_MODEM_FD_GATE
#define A90_WIFI_TEST_BOOT_ANDROID_SERVICE_WINDOW_PPH_MODEM_FD_GATE 0
#endif
#ifndef A90_WIFI_TEST_BOOT_ANDROID_SERVICE_WINDOW_PER_MGR_STARTUP_TRACE
#define A90_WIFI_TEST_BOOT_ANDROID_SERVICE_WINDOW_PER_MGR_STARTUP_TRACE 0
#endif
#ifndef A90_WIFI_TEST_BOOT_ANDROID_SERVICE_WINDOW_PER_MGR_EARLY_EXIT_TRACE
#define A90_WIFI_TEST_BOOT_ANDROID_SERVICE_WINDOW_PER_MGR_EARLY_EXIT_TRACE 0
#endif
#ifndef A90_WIFI_TEST_BOOT_ANDROID_SERVICE_WINDOW_PER_MGR_NONSTOP_CONTEXT_TRACE
#define A90_WIFI_TEST_BOOT_ANDROID_SERVICE_WINDOW_PER_MGR_NONSTOP_CONTEXT_TRACE 0
#endif
#ifndef A90_WIFI_TEST_BOOT_ANDROID_SERVICE_WINDOW_PER_MGR_SYSTEM_INFO_SURFACE
#define A90_WIFI_TEST_BOOT_ANDROID_SERVICE_WINDOW_PER_MGR_SYSTEM_INFO_SURFACE 0
#endif
#ifndef A90_WIFI_TEST_BOOT_WLAN_PD_FIRMWARE_SERVE_GATE
#define A90_WIFI_TEST_BOOT_WLAN_PD_FIRMWARE_SERVE_GATE 0
#endif
#ifndef A90_WIFI_TEST_BOOT_WLAN_PD_SERVICE_WINDOW_TRIGGER
#define A90_WIFI_TEST_BOOT_WLAN_PD_SERVICE_WINDOW_TRIGGER 0
#endif
#ifndef A90_WIFI_TEST_BOOT_WLAN_PD_TIMESTAMPED_OBSERVER
#define A90_WIFI_TEST_BOOT_WLAN_PD_TIMESTAMPED_OBSERVER 0
#endif
#ifndef A90_WIFI_TEST_BOOT_WLAN_PD_PM_SERVICE_WINDOW_TRIGGER
#define A90_WIFI_TEST_BOOT_WLAN_PD_PM_SERVICE_WINDOW_TRIGGER 0
#endif
#ifndef A90_WIFI_TEST_BOOT_WLAN_PD_SERVICE_OBJECT_VISIBLE_TRIGGER
#define A90_WIFI_TEST_BOOT_WLAN_PD_SERVICE_OBJECT_VISIBLE_TRIGGER 0
#endif
#ifndef A90_WIFI_TEST_BOOT_WLAN_PD_SERVICE_OBJECT_DEVNODE_PROJECTION_TRIGGER
#define A90_WIFI_TEST_BOOT_WLAN_PD_SERVICE_OBJECT_DEVNODE_PROJECTION_TRIGGER 0
#endif
#ifndef A90_WIFI_TEST_BOOT_WLAN_PD_POST_PM_LOWER_STATE_OBSERVER
#define A90_WIFI_TEST_BOOT_WLAN_PD_POST_PM_LOWER_STATE_OBSERVER 0
#endif
#ifndef A90_WIFI_TEST_BOOT_WLAN_PD_CNSS_OUTPUT_VISIBILITY
#define A90_WIFI_TEST_BOOT_WLAN_PD_CNSS_OUTPUT_VISIBILITY 0
#endif
#ifndef A90_WIFI_TEST_BOOT_LIGHT_FIRMWARE_TRACE
#define A90_WIFI_TEST_BOOT_LIGHT_FIRMWARE_TRACE 0
#endif
#if A90_WIFI_TEST_BOOT_WLAN_PD_CNSS_OUTPUT_VISIBILITY
#define A90_V1393_WIFI_TEST_MODE "wifi-companion-wlan-pd-cnss-output-visibility-start-only"
#elif A90_WIFI_TEST_BOOT_WLAN_PD_PM_SERVICE_WINDOW_TRIGGER
#define A90_V1393_WIFI_TEST_MODE "wifi-companion-wlan-pd-pm-service-window-trigger-start-only"
#elif A90_WIFI_TEST_BOOT_WLAN_PD_POST_PM_LOWER_STATE_OBSERVER
#define A90_V1393_WIFI_TEST_MODE "wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only"
#elif A90_WIFI_TEST_BOOT_WLAN_PD_SERVICE_OBJECT_DEVNODE_PROJECTION_TRIGGER
#define A90_V1393_WIFI_TEST_MODE "wifi-companion-wlan-pd-service-object-devnode-projection-trigger-start-only"
#elif A90_WIFI_TEST_BOOT_WLAN_PD_SERVICE_OBJECT_VISIBLE_TRIGGER
#define A90_V1393_WIFI_TEST_MODE "wifi-companion-wlan-pd-service-object-visible-trigger-start-only"
#elif A90_WIFI_TEST_BOOT_WLAN_PD_TIMESTAMPED_OBSERVER
#define A90_V1393_WIFI_TEST_MODE "wifi-companion-wlan-pd-timestamped-observer-start-only"
#elif A90_WIFI_TEST_BOOT_WLAN_PD_SERVICE_WINDOW_TRIGGER
#define A90_V1393_WIFI_TEST_MODE "wifi-companion-wlan-pd-service-window-trigger-start-only"
#elif A90_WIFI_TEST_BOOT_WLAN_PD_FIRMWARE_SERVE_GATE
#define A90_V1393_WIFI_TEST_MODE "wifi-companion-wlan-pd-firmware-serve-gate-start-only"
#elif A90_WIFI_TEST_BOOT_ANDROID_SERVICE_WINDOW_SUBSYS_TRIGGER_CAPTURE
#define A90_V1393_WIFI_TEST_MODE "wifi-companion-android-wifi-service-window-subsys-trigger-capture"
#elif A90_WIFI_TEST_BOOT_ANDROID_SERVICE_WINDOW
#define A90_V1393_WIFI_TEST_MODE "wifi-companion-android-wifi-service-window-start-only"
#else
#define A90_V1393_WIFI_TEST_MODE "wifi-companion-post-pm-mdm-helper-esoc-observer"
#endif
#ifndef A90_V1393_WIFI_TEST_PROPERTY_ROOT
#define A90_V1393_WIFI_TEST_PROPERTY_ROOT "/mnt/sdext/a90/private-property-v317/v535/dev/__properties__"
#endif
#define A90_V1393_WIFI_TEST_REAL_LD_CONFIG "/cache/bin/a90_real_ld.config.txt"
#define A90_V1393_WIFI_TEST_REAL_APEX_LIBRARIES "/cache/bin/a90_real_apex.libraries.config.txt"
#define A90_V1393_WIFI_TEST_PRIVATE_CNSS "/cache/bin/cnss-daemon.sdx50m"
#if A90_WIFI_TEST_BOOT_MOUNT_DEBUGFS
static int v1393_wifi_test_debugfs_mounted_by_pid1;
#endif
#endif

static int v641_append_ssctl_log(const char *fmt, ...) {
    int fd;
    int rc;
    va_list ap;

    fd = open(A90_V641_SIBLING_SSCTL_LOG,
              O_WRONLY | O_CREAT | O_APPEND | O_CLOEXEC | O_NOFOLLOW,
              0600);
    if (fd < 0) {
        return -1;
    }

    va_start(ap, fmt);
    rc = vdprintf(fd, fmt, ap);
    va_end(ap);
    close(fd);
    return rc < 0 ? -1 : 0;
}

static int v724_append_qrtr_boot_log(const char *fmt, ...) {
    int fd;
    int rc;
    va_list ap;

    fd = open(A90_V724_QRTR_BOOT_LOG,
              O_WRONLY | O_CREAT | O_APPEND | O_CLOEXEC | O_NOFOLLOW,
              0600);
    if (fd < 0) {
        return -1;
    }

    va_start(ap, fmt);
    rc = vdprintf(fd, fmt, ap);
    va_end(ap);
    close(fd);
    return rc < 0 ? -1 : 0;
}

static int v724_write_private_file(const char *path, const char *text) {
    int fd;
    int rc;

    fd = open(path, O_WRONLY | O_CREAT | O_TRUNC | O_CLOEXEC | O_NOFOLLOW, 0600);
    if (fd < 0) {
        return -errno;
    }
    rc = write_all_checked(fd, text, strlen(text));
    if (close(fd) < 0 && rc == 0) {
        return -errno;
    }
    return rc < 0 ? negative_errno_or(EIO) : 0;
}

#ifdef A90_WIFI_LIFECYCLE_MODEM_OWNER
static int v726_append_wifi_lifecycle_owner_log(const char *fmt, ...) {
    int fd;
    int rc;
    va_list ap;

    fd = open(A90_WIFI_LIFECYCLE_MODEM_OWNER_LOG,
              O_WRONLY | O_CREAT | O_APPEND | O_CLOEXEC | O_NOFOLLOW,
              0600);
    if (fd < 0) {
        return -1;
    }

    va_start(ap, fmt);
    rc = vdprintf(fd, fmt, ap);
    va_end(ap);
    close(fd);
    return rc < 0 ? -1 : 0;
}

static int v726_parse_subsys_modem_dev(unsigned int *major_num,
                                       unsigned int *minor_num) {
    char devbuf[64];
    char *colon;
    char *endptr;
    unsigned long major_value;
    unsigned long minor_value;

    if (major_num == NULL || minor_num == NULL) {
        return -EINVAL;
    }
    if (read_text_file(A90_WIFI_LIFECYCLE_MODEM_OWNER_SYSDEV,
                       devbuf,
                       sizeof(devbuf)) < 0) {
        return -errno;
    }
    trim_newline(devbuf);
    colon = strchr(devbuf, ':');
    if (colon == NULL) {
        return -EINVAL;
    }
    *colon = '\0';
    errno = 0;
    major_value = strtoul(devbuf, &endptr, 10);
    if (errno != 0 || endptr == devbuf || *endptr != '\0' ||
        major_value > UINT_MAX) {
        return -EINVAL;
    }
    errno = 0;
    minor_value = strtoul(colon + 1, &endptr, 10);
    if (errno != 0 || endptr == colon + 1 || *endptr != '\0' ||
        minor_value > UINT_MAX) {
        return -EINVAL;
    }
    *major_num = (unsigned int)major_value;
    *minor_num = (unsigned int)minor_value;
    return 0;
}

static int v726_materialize_subsys_modem_devnode(void) {
    unsigned int major_num = 0;
    unsigned int minor_num = 0;
    dev_t wanted;
    struct stat st;
    int rc;

    rc = v726_parse_subsys_modem_dev(&major_num, &minor_num);
    if (rc < 0) {
        return rc;
    }
    wanted = makedev(major_num, minor_num);
    if (lstat(A90_WIFI_LIFECYCLE_MODEM_OWNER_DEVNODE, &st) == 0) {
        if (S_ISCHR(st.st_mode) && st.st_rdev == wanted) {
            return 0;
        }
        return -EEXIST;
    }
    if (errno != ENOENT) {
        return -errno;
    }
    if (mknod(A90_WIFI_LIFECYCLE_MODEM_OWNER_DEVNODE,
              S_IFCHR | 0600,
              wanted) < 0 &&
        errno != EEXIST) {
        return -errno;
    }
    return 0;
}

static void v726_wifi_lifecycle_modem_owner_child(void) {
    int attempt;
    int fd = -1;

    (void)setsid();
    (void)v726_append_wifi_lifecycle_owner_log("child pid=%ld start\n",
                                               (long)getpid());
    for (attempt = 1; attempt <= 90; ++attempt) {
        int rc = v726_materialize_subsys_modem_devnode();

        if (rc < 0) {
            (void)v726_append_wifi_lifecycle_owner_log(
                    "attempt=%d materialize_rc=%d errno=%d error=%s\n",
                    attempt,
                    rc,
                    -rc,
                    strerror(-rc));
        } else {
            fd = open(A90_WIFI_LIFECYCLE_MODEM_OWNER_DEVNODE,
                      O_RDONLY | O_CLOEXEC);
            if (fd >= 0) {
                (void)v726_append_wifi_lifecycle_owner_log(
                        "opened fd=%d attempt=%d dev=%s\n",
                        fd,
                        attempt,
                        A90_WIFI_LIFECYCLE_MODEM_OWNER_DEVNODE);
                klogf("<6>A90v726: wifi lifecycle modem owner opened /dev/subsys_modem fd=%d\n",
                      fd);
                for (;;) {
                    pause();
                }
            }
            (void)v726_append_wifi_lifecycle_owner_log(
                    "attempt=%d open_errno=%d error=%s\n",
                    attempt,
                    errno,
                    strerror(errno));
        }
        sleep(1);
    }
    (void)v726_append_wifi_lifecycle_owner_log("exhausted attempts exit\n");
    _exit(0);
}

static void v726_start_wifi_lifecycle_modem_owner_once(void) {
    pid_t pid;
    char pid_text[64];
    int rc;

    rc = v726_materialize_subsys_modem_devnode();
    if (rc < 0) {
        int saved_errno = -rc;

        if (saved_errno <= 0) {
            saved_errno = EIO;
        }
        a90_logf("wifi-v726",
                 "lifecycle modem owner devnode not ready rc=%d errno=%d error=%s",
                 rc,
                 saved_errno,
                 strerror(saved_errno));
        klogf("<6>A90v726: wifi lifecycle modem owner devnode not ready rc=%d\n",
              rc);
        (void)v726_append_wifi_lifecycle_owner_log(
                "parent devnode_not_ready rc=%d errno=%d error=%s\n",
                rc,
                saved_errno,
                strerror(saved_errno));
        return;
    }

    pid = fork();
    if (pid < 0) {
        int saved_errno = errno;

        a90_logf("wifi-v726",
                 "lifecycle modem owner fork failed errno=%d error=%s",
                 saved_errno,
                 strerror(saved_errno));
        klogf("<6>A90v726: wifi lifecycle modem owner fork failed errno=%d\n",
              saved_errno);
        (void)v726_append_wifi_lifecycle_owner_log(
                "parent fork_failed errno=%d error=%s\n",
                saved_errno,
                strerror(saved_errno));
        return;
    }
    if (pid == 0) {
        v726_wifi_lifecycle_modem_owner_child();
    }

    snprintf(pid_text, sizeof(pid_text), "%ld\n", (long)pid);
    (void)v724_write_private_file(A90_WIFI_LIFECYCLE_MODEM_OWNER_PID, pid_text);
    a90_logf("wifi-v726",
             "lifecycle modem owner spawned pid=%ld dev=%s",
             (long)pid,
             A90_WIFI_LIFECYCLE_MODEM_OWNER_DEVNODE);
    a90_timeline_record(0,
                        0,
                        "wifi-v726-lifecycle-owner",
                        "modem owner pid=%ld",
                        (long)pid);
    klogf("<6>A90v726: wifi lifecycle modem owner spawned pid=%ld\n",
          (long)pid);
    (void)v726_append_wifi_lifecycle_owner_log("parent spawned pid=%ld dev=%s\n",
                                               (long)pid,
                                               A90_WIFI_LIFECYCLE_MODEM_OWNER_DEVNODE);
}
#endif

static int v724_read_qrtr_boot_flag(char *state, size_t state_size) {
    int fd;
    ssize_t rd;

    if (state == NULL || state_size == 0) {
        return -EINVAL;
    }
    fd = open(A90_V724_QRTR_BOOT_FLAG, O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
    if (fd < 0) {
        return -errno;
    }
    rd = read(fd, state, state_size - 1);
    close(fd);
    if (rd < 0) {
        return negative_errno_or(EIO);
    }
    state[rd] = '\0';
    trim_newline(state);
    return 0;
}

static bool v724_qrtr_boot_flag_armed(void) {
    char state[32];
    int rc = v724_read_qrtr_boot_flag(state, sizeof(state));

    if (rc < 0) {
        a90_logf("wifi-v724", "qrtr servloc boot disabled flag=%s errno=%d error=%s",
                 A90_V724_QRTR_BOOT_FLAG,
                 -rc,
                 strerror(-rc));
        klogf("<6>A90v724: qrtr servloc boot disabled flag=%s\n",
              A90_V724_QRTR_BOOT_FLAG);
        return false;
    }

    if (strcmp(state, "run") != 0) {
        a90_logf("wifi-v724", "qrtr servloc boot ignored flag=%s state=%.16s",
                 A90_V724_QRTR_BOOT_FLAG,
                 state);
        klogf("<6>A90v724: qrtr servloc boot ignored state=%.16s\n", state);
        return false;
    }

    if (unlink(A90_V724_QRTR_BOOT_FLAG) < 0 && errno != ENOENT) {
        a90_logf("wifi-v724", "qrtr servloc boot flag unlink warning errno=%d error=%s",
                 errno,
                 strerror(errno));
    }
    sync();
    return true;
}

static int v724_prepare_selinuxfs_surface(void) {
    struct stat st;

    if (stat("/sys/fs/selinux/status", &st) == 0) {
        return 0;
    }
    if (ensure_dir("/sys/fs", 0755) < 0 && errno != EEXIST) {
        return negative_errno_or(EIO);
    }
    if (ensure_dir("/sys/fs/selinux", 0755) < 0 && errno != EEXIST) {
        return negative_errno_or(EIO);
    }
    if (mount("selinuxfs", "/sys/fs/selinux", "selinuxfs", 0, NULL) < 0 &&
        errno != EBUSY) {
        return negative_errno_or(EIO);
    }
    if (stat("/sys/fs/selinux/status", &st) < 0) {
        return negative_errno_or(EIO);
    }
    return 0;
}

static int v724_spawn_qrtr_servloc_boot_helper(pid_t *pid_out) {
    static char *const envp[] = {
        "PATH=/cache/bin:/bin:/system/bin:/vendor/bin",
        "HOME=/",
        "TERM=vt100",
        NULL
    };
    static char *const argv[] = {
        A90_V724_QRTR_HELPER,
        "--system-root",
        "/mnt/system/system",
        "--vendor-block",
        "/dev/block/sda29",
        "--vendor-fstype",
        "ext4",
        "--mode",
        A90_V724_QRTR_MODE,
        "--null-device-mode",
        "dev-null",
        "--vndk-apex-alias-mode",
        "v30-to-system-ext-v30",
        "--linkerconfig-mode",
        "minimal-vendor",
        "--android-selinux-context-mode",
        "service-defaults",
        "--timeout-sec",
        A90_V724_QRTR_TIMEOUT_SEC,
        "--allow-wifi-companion-start-only",
        "--allow-qrtr-ns-readback",
        NULL
    };
    struct a90_run_config config = {
        .tag = "wifi-v724-qrtr-servloc-boot",
        .argv = argv,
        .envp = envp,
        .stdio_mode = A90_RUN_STDIO_LOG_APPEND,
        .log_path = A90_V724_QRTR_BOOT_LOG,
        .setsid = true,
        .ignore_hup_pipe = true,
        .kill_process_group = true,
        .cancelable = false,
        .timeout_ms = 0,
        .stop_timeout_ms = 1000,
    };

    return a90_run_spawn(&config, pid_out);
}

static void v724_run_qrtr_servloc_boot_once(void) {
    struct stat st;
    pid_t pid = -1;
    int rc;
    char pid_text[32];

    if (!v724_qrtr_boot_flag_armed()) {
        return;
    }

    boot_splash_set_line(5, "[ WIFI   ] V724 QRTR BOOT PROOF");
    boot_auto_frame();
    a90_console_printf("# V724 QRTR/service-locator boot proof: armed one-shot.\r\n");
    a90_logf("wifi-v724", "qrtr servloc boot proof armed timeout_sec=%s",
             A90_V724_QRTR_TIMEOUT_SEC);
    a90_timeline_record(0, 0, "wifi-v724-qrtr-servloc", "armed one-shot");
    klogf("<6>A90v724: qrtr servloc boot proof armed\n");
    (void)v724_append_qrtr_boot_log("armed ms=%ld mode=%s timeout_sec=%s\n",
                                   monotonic_millis(),
                                   A90_V724_QRTR_MODE,
                                   A90_V724_QRTR_TIMEOUT_SEC);

    if (stat(A90_V724_QRTR_HELPER, &st) < 0 || !S_ISREG(st.st_mode)) {
        int saved_errno = errno != 0 ? errno : ENOENT;

        a90_console_printf("# V724 QRTR/service-locator boot proof: helper missing.\r\n");
        a90_logf("wifi-v724", "helper missing path=%s errno=%d error=%s",
                 A90_V724_QRTR_HELPER,
                 saved_errno,
                 strerror(saved_errno));
        a90_timeline_record(-saved_errno, saved_errno, "wifi-v724-qrtr-servloc", "helper missing");
        klogf("<6>A90v724: qrtr servloc boot helper missing\n");
        (void)v724_append_qrtr_boot_log("helper missing path=%s errno=%d error=%s\n",
                                       A90_V724_QRTR_HELPER,
                                       saved_errno,
                                       strerror(saved_errno));
        return;
    }

    if (prepare_android_layout(false) < 0) {
        int saved_errno = errno != 0 ? errno : EIO;

        a90_console_printf("# V724 QRTR/service-locator boot proof: android layout failed.\r\n");
        a90_logf("wifi-v724", "android layout failed errno=%d error=%s",
                 saved_errno,
                 strerror(saved_errno));
        a90_timeline_record(-saved_errno, saved_errno, "wifi-v724-qrtr-servloc", "android layout failed");
        klogf("<6>A90v724: qrtr servloc boot android layout failed rc=-%d\n", saved_errno);
        (void)v724_append_qrtr_boot_log("android layout failed errno=%d error=%s\n",
                                       saved_errno,
                                       strerror(saved_errno));
        return;
    }

    rc = v724_prepare_selinuxfs_surface();
    if (rc < 0) {
        int saved_errno = -rc;

        if (saved_errno <= 0) {
            saved_errno = EIO;
        }
        a90_console_printf("# V724 QRTR/service-locator boot proof: selinuxfs failed.\r\n");
        a90_logf("wifi-v724", "selinuxfs failed rc=%d errno=%d error=%s",
                 rc,
                 saved_errno,
                 strerror(saved_errno));
        a90_timeline_record(rc, saved_errno, "wifi-v724-qrtr-servloc", "selinuxfs failed");
        klogf("<6>A90v724: qrtr servloc boot selinuxfs failed rc=%d\n", rc);
        (void)v724_append_qrtr_boot_log("selinuxfs failed rc=%d errno=%d error=%s\n",
                                       rc,
                                       saved_errno,
                                       strerror(saved_errno));
        return;
    }

    rc = v724_spawn_qrtr_servloc_boot_helper(&pid);
    if (rc < 0) {
        int saved_errno = -rc;

        if (saved_errno <= 0) {
            saved_errno = EIO;
        }
        a90_console_printf("# V724 QRTR/service-locator boot proof: helper spawn failed.\r\n");
        a90_logf("wifi-v724", "helper spawn failed rc=%d errno=%d error=%s",
                 rc,
                 saved_errno,
                 strerror(saved_errno));
        a90_timeline_record(rc, saved_errno, "wifi-v724-qrtr-servloc", "spawn failed");
        klogf("<6>A90v724: qrtr servloc boot helper spawn failed rc=%d\n", rc);
        (void)v724_append_qrtr_boot_log("spawn failed rc=%d errno=%d error=%s\n",
                                       rc,
                                       saved_errno,
                                       strerror(saved_errno));
        return;
    }

    snprintf(pid_text, sizeof(pid_text), "%ld\n", (long)pid);
    (void)v724_write_private_file(A90_V724_QRTR_BOOT_PID, pid_text);
    a90_console_printf("# V724 QRTR/service-locator boot proof: helper pid=%ld.\r\n",
                       (long)pid);
    a90_logf("wifi-v724", "helper spawned pid=%ld mode=%s",
             (long)pid,
             A90_V724_QRTR_MODE);
    a90_timeline_record(0,
                        0,
                        "wifi-v724-qrtr-servloc",
                        "helper spawned pid=%ld",
                        (long)pid);
    klogf("<6>A90v724: qrtr servloc boot helper spawned pid=%ld\n", (long)pid);
    (void)v724_append_qrtr_boot_log("spawned pid=%ld mode=%s\n",
                                   (long)pid,
                                   A90_V724_QRTR_MODE);
}

#ifdef A90_WIFI_TEST_BOOT
static int v1393_append_wifi_test_log(const char *fmt, ...) {
    int fd;
    int rc;
    va_list ap;

    fd = open(A90_V1393_WIFI_TEST_LOG,
              O_WRONLY | O_CREAT | O_APPEND | O_CLOEXEC | O_NOFOLLOW,
              0600);
    if (fd < 0) {
        return -1;
    }

    va_start(ap, fmt);
    rc = vdprintf(fd, fmt, ap);
    va_end(ap);
    close(fd);
    return rc < 0 ? -1 : 0;
}

static int v1393_reset_wifi_test_log(void) {
    int fd;
    int rc;

    (void)unlink(A90_V1393_WIFI_TEST_HELPER_RESULT);
    fd = open(A90_V1393_WIFI_TEST_LOG,
              O_WRONLY | O_CREAT | O_TRUNC | O_CLOEXEC | O_NOFOLLOW,
              0600);
    if (fd < 0) {
        return -errno;
    }
    rc = dprintf(fd,
                 "log_reset ms=%ld label=%s log=%s summary=%s\n",
                 monotonic_millis(),
                 A90_WIFI_TEST_BOOT_LABEL,
                 A90_V1393_WIFI_TEST_LOG,
                 A90_V1393_WIFI_TEST_SUMMARY);
    if (close(fd) < 0 && rc >= 0) {
        return -errno;
    }
    return rc < 0 ? negative_errno_or(EIO) : 0;
}

#if A90_WIFI_TEST_BOOT_MOUNT_DEBUGFS
static int v1393_prepare_wifi_test_debugfs(void) {
    struct stat st;

    if (lstat("/sys/kernel/debug/pci-msm/case", &st) == 0) {
        v1393_wifi_test_debugfs_mounted_by_pid1 = 0;
        return 0;
    }
    if (mkdir("/sys/kernel/debug", 0755) < 0 && errno != EEXIST) {
        return -errno;
    }
    if (mount("debugfs",
              "/sys/kernel/debug",
              "debugfs",
              MS_NOSUID | MS_NODEV | MS_NOEXEC,
              NULL) < 0) {
        if (errno == EBUSY) {
            v1393_wifi_test_debugfs_mounted_by_pid1 = 0;
            return 0;
        }
        return -errno;
    }
    v1393_wifi_test_debugfs_mounted_by_pid1 = 1;
    return 0;
}

static int v1393_cleanup_wifi_test_debugfs(void) {
    if (!v1393_wifi_test_debugfs_mounted_by_pid1) {
        return 0;
    }
    if (umount("/sys/kernel/debug") < 0) {
        return -errno;
    }
    v1393_wifi_test_debugfs_mounted_by_pid1 = 0;
    return 0;
}
#endif

#if A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_AP2MDM_HOLD
static int v1477_write_wifi_test_sysfs_string(const char *path, const char *value) {
    int fd;
    int rc;

    fd = open(path, O_WRONLY | O_CLOEXEC | O_NOFOLLOW);
    if (fd < 0) {
        return -errno;
    }
    rc = write_all_checked(fd, value, strlen(value));
    if (close(fd) < 0 && rc == 0) {
        return -errno;
    }
    return rc < 0 ? negative_errno_or(EIO) : 0;
}

static int v1477_text_file_contains_line(const char *path, const char *needle) {
    int fd;
    char chunk[512];
    char line[512];
    size_t line_len = 0;

    fd = open(path, O_RDONLY | O_CLOEXEC);
    if (fd < 0) {
        return -errno;
    }
    for (;;) {
        ssize_t rd = read(fd, chunk, sizeof(chunk));
        ssize_t offset;

        if (rd == 0) {
            break;
        }
        if (rd < 0) {
            int saved_errno = errno != 0 ? errno : EIO;
            close(fd);
            return -saved_errno;
        }
        for (offset = 0; offset < rd; offset++) {
            char ch = chunk[offset];

            if (ch == '\n' || line_len + 1 >= sizeof(line)) {
                line[line_len] = '\0';
                if (strstr(line, needle) != NULL) {
                    close(fd);
                    return 1;
                }
                line_len = 0;
                continue;
            }
            line[line_len++] = ch;
        }
    }
    if (line_len > 0) {
        line[line_len] = '\0';
        if (strstr(line, needle) != NULL) {
            close(fd);
            return 1;
        }
    }
    close(fd);
    return 0;
}
#endif

#if A90_WIFI_TEST_BOOT_PID1_RC1_WATCHER
#if !A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_MICRO_ENDPOINT_SAMPLER
static int v1393_write_wifi_test_sysfs_string(const char *path, const char *value) {
    int fd;
    int rc;

    fd = open(path, O_WRONLY | O_CLOEXEC | O_NOFOLLOW);
    if (fd < 0) {
        return -errno;
    }
    rc = write_all_checked(fd, value, strlen(value));
    if (close(fd) < 0 && rc == 0) {
        return -errno;
    }
    return rc < 0 ? negative_errno_or(EIO) : 0;
}

static int v1536_pid1_rc1_write_enumerate_trigger(long start_ms,
                                                   char *summary,
                                                   size_t summary_size) {
#if A90_WIFI_TEST_BOOT_RC1_SYSFS_CLIENT_ENUMERATE
    int sysfs_rc;
    long sysfs_ms;

    sysfs_rc = v1393_write_wifi_test_sysfs_string(A90_V1536_RC1_ENUMERATE_TRIGGER_PATH,
                                                  A90_V1536_RC1_ENUMERATE_TRIGGER_VALUE);
    sysfs_ms = monotonic_millis();
    if (summary != NULL && summary_size > 0) {
        snprintf(summary,
                 summary_size,
                 "trigger_mode=%s sysfs_path=%s sysfs_rc=%d sysfs_elapsed_ms=%ld rc_sel_elapsed_ms=-1 case_elapsed_ms=-1",
                 A90_V1536_RC1_ENUMERATE_TRIGGER_MODE,
                 A90_V1536_RC1_ENUMERATE_TRIGGER_PATH,
                 sysfs_rc,
                 sysfs_ms >= start_ms ? sysfs_ms - start_ms : -1);
    }
    return sysfs_rc;
#else
    int rc_sel_rc;
    int case_rc = -EIO;
    long rc_sel_ms;
    long case_ms;

    rc_sel_rc = v1393_write_wifi_test_sysfs_string(A90_V1536_RC1_ENUMERATE_RC_SEL_PATH, "2\n");
    rc_sel_ms = monotonic_millis();
    if (rc_sel_rc == 0) {
        case_rc = v1393_write_wifi_test_sysfs_string(A90_V1536_RC1_ENUMERATE_CASE_PATH, "11\n");
    }
    case_ms = monotonic_millis();
    if (summary != NULL && summary_size > 0) {
        snprintf(summary,
                 summary_size,
                 "trigger_mode=%s rc_sel_path=%s case_path=%s rc_sel_rc=%d case_rc=%d rc_sel_elapsed_ms=%ld case_elapsed_ms=%ld",
                 A90_V1536_RC1_ENUMERATE_TRIGGER_MODE,
                 A90_V1536_RC1_ENUMERATE_RC_SEL_PATH,
                 A90_V1536_RC1_ENUMERATE_CASE_PATH,
                 rc_sel_rc,
                 case_rc,
                 rc_sel_ms >= start_ms ? rc_sel_ms - start_ms : -1,
                 case_ms >= start_ms ? case_ms - start_ms : -1);
    }
    return rc_sel_rc < 0 ? rc_sel_rc : case_rc;
#endif
}

#if (!A90_WIFI_TEST_BOOT_RC1_IMMEDIATE_ENDPOINT_SAMPLER && !A90_WIFI_TEST_BOOT_RC1_MICRO_ENDPOINT_SAMPLER) || A90_WIFI_TEST_BOOT_RC1_RETRY_COUNT > 0
static int v1393_pid1_rc1_write_corrected_enumerate(void) {
    char summary[256];

    summary[0] = '\0';
    return v1536_pid1_rc1_write_enumerate_trigger(monotonic_millis(), summary, sizeof(summary));
}
#endif
#endif

static bool v1393_pid1_rc1_trigger_line(const char *line) {
    if (line == NULL) {
        return false;
    }
    return strstr(line, "__subsystem_get: esoc0 count") != NULL ||
           strstr(line, "mdm_subsys_powerup") != NULL;
}

#if A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_EXACT_LINE
static int v1393_pid1_rc1_extract_trigger_pid(const char *line) {
    const char *first;
    const char *second;
    const char *end;
    const char *cursor;
    const char *start;
    long value = 0;

    if (line == NULL) {
        return -1;
    }
    first = strchr(line, '[');
    if (first == NULL) {
        return -1;
    }
    second = strchr(first + 1, '[');
    if (second == NULL) {
        return -1;
    }
    end = strchr(second + 1, ']');
    if (end == NULL) {
        return -1;
    }
    cursor = end;
    while (cursor > second && (*(cursor - 1) == ' ' || *(cursor - 1) == '\t')) {
        cursor--;
    }
    start = cursor;
    while (start > second && *(start - 1) >= '0' && *(start - 1) <= '9') {
        start--;
    }
    if (start == cursor) {
        return -1;
    }
    while (start < cursor) {
        value = value * 10 + (*start - '0');
        if (value > 4194304) {
            return -1;
        }
        start++;
    }
    return (int)value;
}

static bool v1393_pid1_rc1_extract_trigger_line(const char *chunk, char *out, size_t out_size) {
    const char *cursor;

    if (chunk == NULL || out == NULL || out_size == 0) {
        return false;
    }
    cursor = chunk;
    while (*cursor != '\0') {
        const char *end = strchr(cursor, '\n');
        size_t len = end != NULL ? (size_t)(end - cursor) : strlen(cursor);

        if (len > 0 && len < out_size) {
            memmove(out, cursor, len);
            out[len] = '\0';
            if (v1393_pid1_rc1_trigger_line(out)) {
                return true;
            }
        } else if (len >= out_size) {
            size_t copy_len = out_size - 1;

            memmove(out, cursor, copy_len);
            out[copy_len] = '\0';
            if (v1393_pid1_rc1_trigger_line(out)) {
                return true;
            }
        }
        if (end == NULL) {
            break;
        }
        cursor = end + 1;
    }
    return false;
}
#endif

#if A90_WIFI_TEST_BOOT_RC1_WINDOW_SAMPLER
static bool v1393_rc1_window_line_matches(const char *line, const char *const *needles) {
    size_t index;

    if (line == NULL || needles == NULL) {
        return false;
    }
    for (index = 0; needles[index] != NULL; index++) {
        if (strstr(line, needles[index]) != NULL) {
            return true;
        }
    }
    return false;
}

static void v1393_rc1_window_append_matching_lines(int out_fd,
                                                   const char *sample,
                                                   const char *source_name,
                                                   const char *path,
                                                   const char *const *needles) {
    int in_fd;
    char chunk[512];
    char line[512];
    size_t line_len = 0;
    int matches = 0;
    int truncated = 0;

    in_fd = open(path, O_RDONLY | O_CLOEXEC);
    if (in_fd < 0) {
        dprintf(out_fd,
                "sample=%s source=%s path=%s unreadable_errno=%d\n",
                sample,
                source_name,
                path,
                errno != 0 ? errno : EIO);
        return;
    }

    for (;;) {
        ssize_t rd = read(in_fd, chunk, sizeof(chunk));
        ssize_t offset;

        if (rd == 0) {
            break;
        }
        if (rd < 0) {
            dprintf(out_fd,
                    "sample=%s source=%s path=%s read_errno=%d matches=%d truncated=%d\n",
                    sample,
                    source_name,
                    path,
                    errno != 0 ? errno : EIO,
                    matches,
                    truncated);
            close(in_fd);
            return;
        }

        for (offset = 0; offset < rd; offset++) {
            char ch = chunk[offset];

            if (ch == '\n' || line_len + 1 >= sizeof(line)) {
                line[line_len] = '\0';
                if (v1393_rc1_window_line_matches(line, needles)) {
                    flatten_inline_text(line);
                    dprintf(out_fd,
                            "sample=%s source=%s match_%02d=%s\n",
                            sample,
                            source_name,
                            matches,
                            line);
                    matches++;
                    if (matches >= 16) {
                        close(in_fd);
                        dprintf(out_fd,
                                "sample=%s source=%s matches=%d truncated=1\n",
                                sample,
                                source_name,
                                matches);
                        return;
                    }
                }
                if (line_len + 1 >= sizeof(line) && ch != '\n') {
                    truncated = 1;
                }
                line_len = 0;
                continue;
            }
            line[line_len++] = ch;
        }
    }

    if (line_len > 0) {
        line[line_len] = '\0';
        if (v1393_rc1_window_line_matches(line, needles)) {
            flatten_inline_text(line);
            dprintf(out_fd,
                    "sample=%s source=%s match_%02d=%s\n",
                    sample,
                    source_name,
                    matches,
                    line);
            matches++;
        }
    }
    dprintf(out_fd,
            "sample=%s source=%s matches=%d truncated=%d\n",
            sample,
            source_name,
            matches,
            truncated);
    close(in_fd);
}

#if A90_WIFI_TEST_BOOT_RC1_ENDPOINT_SAMPLER
static void v1393_rc1_window_append_trimmed_file(int out_fd,
                                                 const char *sample,
                                                 const char *source_name,
                                                 const char *path) {
    char value[256];
    int rc;

    rc = read_trimmed_text_file(path, value, sizeof(value));
    if (rc < 0) {
        dprintf(out_fd,
                "sample=%s source=%s path=%s unreadable_rc=%d\n",
                sample,
                source_name,
                path,
                rc);
        return;
    }
    flatten_inline_text(value);
    dprintf(out_fd,
            "sample=%s source=%s path=%s value=%s\n",
            sample,
            source_name,
            path,
            value);
}

#if A90_WIFI_TEST_BOOT_RC1_FOCUSED_ENDPOINT_SAMPLER || A90_WIFI_TEST_BOOT_RC1_IMMEDIATE_ENDPOINT_SAMPLER || A90_WIFI_TEST_BOOT_RC1_MICRO_ENDPOINT_SAMPLER
static void v1393_rc1_window_append_first_matching_line(int out_fd,
                                                        const char *sample,
                                                        const char *source_name,
                                                        const char *path,
                                                        const char *needle) {
    int in_fd;
    char chunk[512];
    char line[512];
    size_t line_len = 0;

    in_fd = open(path, O_RDONLY | O_CLOEXEC);
    if (in_fd < 0) {
        dprintf(out_fd,
                "sample=%s source=%s needle=%s path=%s unreadable_errno=%d\n",
                sample,
                source_name,
                needle,
                path,
                errno != 0 ? errno : EIO);
        return;
    }

    for (;;) {
        ssize_t rd = read(in_fd, chunk, sizeof(chunk));
        ssize_t offset;

        if (rd == 0) {
            break;
        }
        if (rd < 0) {
            dprintf(out_fd,
                    "sample=%s source=%s needle=%s path=%s read_errno=%d\n",
                    sample,
                    source_name,
                    needle,
                    path,
                    errno != 0 ? errno : EIO);
            close(in_fd);
            return;
        }

        for (offset = 0; offset < rd; offset++) {
            char ch = chunk[offset];

            if (ch == '\n' || line_len + 1 >= sizeof(line)) {
                line[line_len] = '\0';
                if (strstr(line, needle) != NULL) {
                    flatten_inline_text(line);
                    dprintf(out_fd,
                            "sample=%s source=%s needle=%s match=%s\n",
                            sample,
                            source_name,
                            needle,
                            line);
                    close(in_fd);
                    return;
                }
                line_len = 0;
                continue;
            }
            line[line_len++] = ch;
        }
    }

    if (line_len > 0) {
        line[line_len] = '\0';
        if (strstr(line, needle) != NULL) {
            flatten_inline_text(line);
            dprintf(out_fd,
                    "sample=%s source=%s needle=%s match=%s\n",
                    sample,
                    source_name,
                    needle,
                    line);
            close(in_fd);
            return;
        }
    }
    dprintf(out_fd,
            "sample=%s source=%s needle=%s path=%s missing=1\n",
            sample,
            source_name,
            needle,
            path);
    close(in_fd);
}

static void v1393_rc1_window_append_exact_matches(int out_fd,
                                                  const char *sample,
                                                  const char *source_name,
                                                  const char *path,
                                                  const char *const *needles) {
    size_t index;

    for (index = 0; needles[index] != NULL; index++) {
        v1393_rc1_window_append_first_matching_line(out_fd,
                                                    sample,
                                                    source_name,
                                                    path,
                                                    needles[index]);
    }
}
#endif

#if A90_WIFI_TEST_BOOT_RC1_MICRO_SOURCE_TIMESTAMPED_SAMPLER
static long v1511_elapsed_since_or_neg(long now_ms, long base_ms) {
    return now_ms >= base_ms ? now_ms - base_ms : -1;
}

static void v1511_rc1_window_append_source_timing(int out_fd,
                                                  const char *sample,
                                                  const char *source_name,
                                                  const char *path,
                                                  const char *phase,
                                                  long stamp_ms,
                                                  long start_ms,
                                                  long micro_start_ms,
                                                  long duration_ms) {
    dprintf(out_fd,
            "sample=%s source=%s source_timing=%s elapsed_ms=%ld micro_elapsed_ms=%ld source_duration_ms=%ld path=%s\n",
            sample,
            source_name,
            phase,
            v1511_elapsed_since_or_neg(stamp_ms, start_ms),
            v1511_elapsed_since_or_neg(stamp_ms, micro_start_ms),
            duration_ms,
            path);
}

static void v1511_rc1_window_append_matching_lines_timed(int out_fd,
                                                         const char *sample,
                                                         const char *source_name,
                                                         const char *path,
                                                         const char *const *needles,
                                                         long start_ms,
                                                         long micro_start_ms) {
    long begin_ms = monotonic_millis();
    long end_ms;

    v1511_rc1_window_append_source_timing(out_fd,
                                          sample,
                                          source_name,
                                          path,
                                          "begin",
                                          begin_ms,
                                          start_ms,
                                          micro_start_ms,
                                          -1);
    v1393_rc1_window_append_matching_lines(out_fd, sample, source_name, path, needles);
    end_ms = monotonic_millis();
    v1511_rc1_window_append_source_timing(out_fd,
                                          sample,
                                          source_name,
                                          path,
                                          "end",
                                          end_ms,
                                          start_ms,
                                          micro_start_ms,
                                          end_ms >= begin_ms ? end_ms - begin_ms : -1);
}

static void v1511_rc1_window_append_trimmed_file_timed(int out_fd,
                                                       const char *sample,
                                                       const char *source_name,
                                                       const char *path,
                                                       long start_ms,
                                                       long micro_start_ms) {
    long begin_ms = monotonic_millis();
    long end_ms;

    v1511_rc1_window_append_source_timing(out_fd,
                                          sample,
                                          source_name,
                                          path,
                                          "begin",
                                          begin_ms,
                                          start_ms,
                                          micro_start_ms,
                                          -1);
    v1393_rc1_window_append_trimmed_file(out_fd, sample, source_name, path);
    end_ms = monotonic_millis();
    v1511_rc1_window_append_source_timing(out_fd,
                                          sample,
                                          source_name,
                                          path,
                                          "end",
                                          end_ms,
                                          start_ms,
                                          micro_start_ms,
                                          end_ms >= begin_ms ? end_ms - begin_ms : -1);
}

static void v1511_rc1_window_append_exact_matches_timed(int out_fd,
                                                        const char *sample,
                                                        const char *source_name,
                                                        const char *path,
                                                        const char *const *needles,
                                                        long start_ms,
                                                        long micro_start_ms) {
    long begin_ms = monotonic_millis();
    long end_ms;

    v1511_rc1_window_append_source_timing(out_fd,
                                          sample,
                                          source_name,
                                          path,
                                          "begin",
                                          begin_ms,
                                          start_ms,
                                          micro_start_ms,
                                          -1);
    v1393_rc1_window_append_exact_matches(out_fd, sample, source_name, path, needles);
    end_ms = monotonic_millis();
    v1511_rc1_window_append_source_timing(out_fd,
                                          sample,
                                          source_name,
                                          path,
                                          "end",
                                          end_ms,
                                          start_ms,
                                          micro_start_ms,
                                          end_ms >= begin_ms ? end_ms - begin_ms : -1);
}
#endif
#endif

static void v1393_rc1_window_sample(const char *sample, long start_ms, long detect_ms, long child_start_ms) {
    static const char *const interrupts_needles[] = {
        "mdm status",
        "gpio",
        "142",
        "pcie",
        "PCIe",
        "mhi",
        "MHI",
        NULL,
    };
    static const char *const gpio_needles[] = {
        "gpio102",
        "gpio103",
        "gpio104",
        "gpio135",
        "gpio142",
        "gpio-102",
        "gpio-103",
        "gpio-104",
        "gpio-135",
        "gpio-142",
        "GPIO_102",
        "GPIO_103",
        "GPIO_104",
        "GPIO_135",
        "GPIO_142",
        " 102",
        " 103",
        " 104",
        " 135",
        " 142",
        NULL,
    };
#if A90_WIFI_TEST_BOOT_RC1_ENDPOINT_SAMPLER
    static const char *const regulator_needles[] = {
        "pcie_1_gdsc",
        "pcie_0_gdsc",
        "pm8150l_l3",
        "pm8150_l5",
        "VDD_CX_LEVEL",
        NULL,
    };
#if !A90_WIFI_TEST_BOOT_NATURAL_POWER_DIFF_SNAPSHOT
    static const char *const clk_needles[] = {
        "GCC_PCIE_1",
        "GCC_PCIE1",
        "pcie_1_",
        "pcie1",
        "pcie_phy",
        "pcie_pipe",
        "ref_clk",
        "refgen",
        NULL,
    };
#endif
#if A90_WIFI_TEST_BOOT_RC1_FOCUSED_ENDPOINT_SAMPLER
    static const char *const exact_regulator_needles[] = {
        "pcie_1_gdsc",
        "pcie_0_gdsc",
        "pm8150l_l3",
        "pm8150_l5",
        "VDD_CX_LEVEL",
        NULL,
    };
    static const char *const exact_clk_needles[] = {
        "gcc_pcie_1_slv_q2a_axi_clk",
        "gcc_pcie_1_slv_axi_clk",
        "gcc_pcie_1_pipe_clk",
        "gcc_pcie_1_mstr_axi_clk",
        "gcc_pcie_1_clkref_clk",
        "gcc_pcie_1_cfg_ahb_clk",
        "gcc_pcie1_phy_refgen_clk",
        "gcc_pcie_phy_refgen_clk_src",
        NULL,
    };
    static const char *const exact_gpio_needles[] = {
        "gpio102",
        "gpio103",
        "gpio104",
        "gpio142",
        "GPIO_102",
        "GPIO_103",
        "GPIO_104",
        "GPIO_142",
        NULL,
    };
#endif
#endif
    int out_fd;
    long now_ms = monotonic_millis();

    out_fd = open(A90_V1393_WIFI_TEST_RC1_WINDOW_RESULT,
                  O_WRONLY | O_CREAT | O_APPEND | O_CLOEXEC | O_NOFOLLOW,
                  0600);
    if (out_fd < 0) {
        return;
    }
    dprintf(out_fd,
            "rc1_window_sample label=%s elapsed_ms=%ld detect_elapsed_ms=%ld child_elapsed_ms=%ld\n",
            sample,
            now_ms >= start_ms ? now_ms - start_ms : -1,
            detect_ms >= start_ms ? detect_ms - start_ms : -1,
            now_ms >= child_start_ms ? now_ms - child_start_ms : -1);
#if A90_WIFI_TEST_BOOT_RC1_ENDPOINT_SAMPLER
    dprintf(out_fd, "sample=%s endpoint_sampler=1\n", sample);
#endif
    v1393_rc1_window_append_matching_lines(out_fd,
                                           sample,
                                           "interrupts",
                                           "/proc/interrupts",
                                           interrupts_needles);
    v1393_rc1_window_append_matching_lines(out_fd,
                                           sample,
                                           "debug_gpio",
                                           "/sys/kernel/debug/gpio",
                                           gpio_needles);
    v1393_rc1_window_append_matching_lines(out_fd,
                                           sample,
                                           "pinctrl_pins",
                                           "/sys/kernel/debug/pinctrl/3000000.pinctrl/pins",
                                           gpio_needles);
    v1393_rc1_window_append_matching_lines(out_fd,
                                           sample,
                                           "pinctrl_pinmux",
                                           "/sys/kernel/debug/pinctrl/3000000.pinctrl/pinmux-pins",
                                           gpio_needles);
    v1393_rc1_window_append_matching_lines(out_fd,
                                           sample,
                                           "pinctrl_pinconf",
                                           "/sys/kernel/debug/pinctrl/3000000.pinctrl/pinconf-pins",
                                           gpio_needles);
#if A90_WIFI_TEST_BOOT_RC1_ENDPOINT_SAMPLER
    v1393_rc1_window_append_matching_lines(out_fd,
                                           sample,
                                           "regulator_summary",
                                           "/sys/kernel/debug/regulator/regulator_summary",
                                           regulator_needles);
    v1393_rc1_window_append_matching_lines(out_fd,
                                           sample,
                                           "regulator_summary_alt",
                                           "/sys/kernel/debug/regulator_summary",
                                           regulator_needles);
#if !A90_WIFI_TEST_BOOT_NATURAL_POWER_DIFF_SNAPSHOT
    v1393_rc1_window_append_matching_lines(out_fd,
                                           sample,
                                           "clk_summary",
                                           "/sys/kernel/debug/clk/clk_summary",
                                           clk_needles);
#else
    dprintf(out_fd,
            "sample=%s clk_summary_skipped=1 reason=natural-power-diff-targeted-clocks-only\n",
            sample);
#endif
    v1393_rc1_window_append_trimmed_file(out_fd,
                                         sample,
                                         "pcie1_current_link_state",
                                         "/sys/devices/platform/soc/1c08000.qcom,pcie/current_link_state");
    v1393_rc1_window_append_trimmed_file(out_fd,
                                         sample,
                                         "pcie1_link_state",
                                         "/sys/devices/platform/soc/1c08000.qcom,pcie/link_state");
    v1393_rc1_window_append_trimmed_file(out_fd,
                                         sample,
                                         "pcie1_runtime_status",
                                         "/sys/devices/platform/soc/1c08000.qcom,pcie/power/runtime_status");
    v1393_rc1_window_append_trimmed_file(out_fd,
                                         sample,
                                         "pcie1_power_control",
                                         "/sys/devices/platform/soc/1c08000.qcom,pcie/power/control");
    v1393_rc1_window_append_trimmed_file(out_fd,
                                         sample,
                                         "pcie1_bus_current_link_state",
                                         "/sys/bus/platform/devices/1c08000.qcom,pcie/current_link_state");
    v1393_rc1_window_append_trimmed_file(out_fd,
                                         sample,
                                         "pcie1_bus_link_state",
                                         "/sys/bus/platform/devices/1c08000.qcom,pcie/link_state");
#if A90_WIFI_TEST_BOOT_RC1_FOCUSED_ENDPOINT_SAMPLER
    v1393_rc1_window_append_exact_matches(out_fd,
                                          sample,
                                          "focused_regulator",
                                          "/sys/kernel/debug/regulator/regulator_summary",
                                          exact_regulator_needles);
    v1393_rc1_window_append_exact_matches(out_fd,
                                          sample,
                                          "focused_clk",
                                          "/sys/kernel/debug/clk/clk_summary",
                                          exact_clk_needles);
    v1393_rc1_window_append_exact_matches(out_fd,
                                          sample,
                                          "focused_debug_gpio",
                                          "/sys/kernel/debug/gpio",
                                          exact_gpio_needles);
    v1393_rc1_window_append_exact_matches(out_fd,
                                          sample,
                                          "focused_pinmux",
                                          "/sys/kernel/debug/pinctrl/3000000.pinctrl/pinmux-pins",
                                          exact_gpio_needles);
    v1393_rc1_window_append_exact_matches(out_fd,
                                          sample,
                                          "focused_pinconf",
                                          "/sys/kernel/debug/pinctrl/3000000.pinctrl/pinconf-pins",
                                          exact_gpio_needles);
#endif
#endif
    close(out_fd);
}

#if A90_WIFI_TEST_BOOT_NATURAL_MDM2AP_IRQ_SUMMARY
struct v1633_natural_irq_snapshot {
    int parsed;
    unsigned long count_total;
};

struct v1633_natural_mdm2ap_irq_summary {
    struct v1633_natural_irq_snapshot gpio142_initial;
    struct v1633_natural_irq_snapshot errfatal_initial;
    unsigned long gpio142_max;
    unsigned long errfatal_max;
    int gpio142_first_delta_sample;
    int errfatal_first_delta_sample;
};

static unsigned long v1633_parse_irq_count_total(char *line) {
    char *cursor = strchr(line, ':');
    unsigned long total = 0;

    if (cursor == NULL) {
        return 0;
    }
    cursor++;
    while (*cursor != '\0') {
        char *end_ptr;
        unsigned long value;

        while (*cursor == ' ' || *cursor == '\t') {
            cursor++;
        }
        if (*cursor < '0' || *cursor > '9') {
            break;
        }
        errno = 0;
        value = strtoul(cursor, &end_ptr, 10);
        if (end_ptr == cursor || errno == ERANGE) {
            break;
        }
        total += value;
        cursor = end_ptr;
    }
    return total;
}

static struct v1633_natural_irq_snapshot v1633_collect_irq_snapshot(const char *needle) {
    struct v1633_natural_irq_snapshot snapshot = {0, 0};
    int file_fd = open("/proc/interrupts", O_RDONLY | O_CLOEXEC);
    char chunk[512];
    char line[512];
    size_t line_len = 0;

    if (file_fd < 0) {
        return snapshot;
    }

    for (;;) {
        ssize_t bytes_read = read(file_fd, chunk, sizeof(chunk));
        ssize_t offset;

        if (bytes_read == 0) {
            break;
        }
        if (bytes_read < 0) {
            close(file_fd);
            return snapshot;
        }
        for (offset = 0; offset < bytes_read; offset++) {
            char ch = chunk[offset];

            if (ch == '\n' || line_len + 1 >= sizeof(line)) {
                line[line_len] = '\0';
                if (strstr(line, needle) != NULL) {
                    snapshot.parsed = 1;
                    snapshot.count_total = v1633_parse_irq_count_total(line);
                    close(file_fd);
                    return snapshot;
                }
                line_len = 0;
                continue;
            }
            line[line_len++] = ch;
        }
    }
    if (line_len > 0) {
        line[line_len] = '\0';
        if (strstr(line, needle) != NULL) {
            snapshot.parsed = 1;
            snapshot.count_total = v1633_parse_irq_count_total(line);
        }
    }
    close(file_fd);
    return snapshot;
}

static void v1633_natural_mdm2ap_irq_summary_init(struct v1633_natural_mdm2ap_irq_summary *summary) {
    memset(summary, 0, sizeof(*summary));
    summary->gpio142_initial = v1633_collect_irq_snapshot("mdm status");
    summary->errfatal_initial = v1633_collect_irq_snapshot("mdm errfatal");
    summary->gpio142_max = summary->gpio142_initial.count_total;
    summary->errfatal_max = summary->errfatal_initial.count_total;
    summary->gpio142_first_delta_sample = -1;
    summary->errfatal_first_delta_sample = -1;
}

static void v1633_natural_mdm2ap_irq_summary_sample(struct v1633_natural_mdm2ap_irq_summary *summary,
                                                    int sample_index) {
    struct v1633_natural_irq_snapshot gpio142 = v1633_collect_irq_snapshot("mdm status");
    struct v1633_natural_irq_snapshot errfatal = v1633_collect_irq_snapshot("mdm errfatal");

    if (gpio142.parsed && gpio142.count_total > summary->gpio142_max) {
        summary->gpio142_max = gpio142.count_total;
    }
    if (errfatal.parsed && errfatal.count_total > summary->errfatal_max) {
        summary->errfatal_max = errfatal.count_total;
    }
    if (summary->gpio142_first_delta_sample < 0 &&
        gpio142.parsed &&
        summary->gpio142_initial.parsed &&
        gpio142.count_total > summary->gpio142_initial.count_total) {
        summary->gpio142_first_delta_sample = sample_index;
    }
    if (summary->errfatal_first_delta_sample < 0 &&
        errfatal.parsed &&
        summary->errfatal_initial.parsed &&
        errfatal.count_total > summary->errfatal_initial.count_total) {
        summary->errfatal_first_delta_sample = sample_index;
    }
}

#if A90_WIFI_TEST_BOOT_NATURAL_POWER_DIFF_SNAPSHOT
static void v1661_append_file_raw(int out_fd, const char *path) {
    int file_fd = open(path, O_RDONLY | O_CLOEXEC);
    char chunk[1024];

    if (file_fd < 0) {
        dprintf(out_fd, "A90_V1661_FILE_MISSING path=%s errno=%d\n", path, errno);
        return;
    }
    for (;;) {
        ssize_t bytes_read = read(file_fd, chunk, sizeof(chunk));

        if (bytes_read == 0) {
            break;
        }
        if (bytes_read < 0) {
            dprintf(out_fd, "A90_V1661_FILE_READ_ERROR path=%s errno=%d\n", path, errno);
            break;
        }
        if (write(out_fd, chunk, (size_t)bytes_read) < 0) {
            dprintf(out_fd, "\nA90_V1661_FILE_WRITE_ERROR path=%s errno=%d\n", path, errno);
            break;
        }
    }
    close(file_fd);
}

static void v1661_append_trimmed_file_value(int out_fd, const char *path, const char *key) {
    int file_fd = open(path, O_RDONLY | O_CLOEXEC);
    char value[128];
    ssize_t bytes_read;

    if (file_fd < 0) {
        return;
    }
    bytes_read = read(file_fd, value, sizeof(value) - 1);
    close(file_fd);
    if (bytes_read <= 0) {
        return;
    }
    value[bytes_read] = '\0';
    for (ssize_t index = 0; index < bytes_read; index++) {
        if (value[index] == '\n' || value[index] == '\r') {
            value[index] = '\0';
            break;
        }
    }
    dprintf(out_fd, " %s=%s", key, value);
}

static void v1661_append_clock_snapshot(int out_fd, const char *name) {
    static const char *const keys[] = {
        "clk_enable_count",
        "clk_prepare_count",
        "clk_rate",
        NULL,
    };
    char base_path[192];
    struct stat st;

    snprintf(base_path, sizeof(base_path), "/sys/kernel/debug/clk/%s", name);
    if (lstat(base_path, &st) < 0 || !S_ISDIR(st.st_mode)) {
        dprintf(out_fd, "CLOCK %s missing\n", name);
        return;
    }
    dprintf(out_fd, "CLOCK %s", name);
    for (size_t index = 0; keys[index] != NULL; index++) {
        char path[256];

        snprintf(path, sizeof(path), "%s/%s", base_path, keys[index]);
        v1661_append_trimmed_file_value(out_fd, path, keys[index]);
    }
    dprintf(out_fd, "\n");
}

static void v1661_append_subsys_snapshot(int out_fd) {
    for (int index = 0; index < 32; index++) {
        char dir[96];
        char name_path[128];
        char state_path[128];
        char name[96] = "";
        char state[96] = "";
        int name_fd;
        int state_fd;
        ssize_t name_read;
        ssize_t state_read;
        struct stat st;

        snprintf(dir, sizeof(dir), "/sys/bus/msm_subsys/devices/subsys%d", index);
        if (stat(dir, &st) < 0 || !S_ISDIR(st.st_mode)) {
            continue;
        }
        snprintf(name_path, sizeof(name_path), "%s/name", dir);
        snprintf(state_path, sizeof(state_path), "%s/state", dir);
        name_fd = open(name_path, O_RDONLY | O_CLOEXEC);
        if (name_fd >= 0) {
            name_read = read(name_fd, name, sizeof(name) - 1);
            close(name_fd);
            if (name_read > 0) {
                name[name_read] = '\0';
            }
        }
        state_fd = open(state_path, O_RDONLY | O_CLOEXEC);
        if (state_fd >= 0) {
            state_read = read(state_fd, state, sizeof(state) - 1);
            close(state_fd);
            if (state_read > 0) {
                state[state_read] = '\0';
            }
        }
        for (size_t pos = 0; name[pos] != '\0'; pos++) {
            if (name[pos] == '\n' || name[pos] == '\r') {
                name[pos] = '\0';
                break;
            }
        }
        for (size_t pos = 0; state[pos] != '\0'; pos++) {
            if (state[pos] == '\n' || state[pos] == '\r') {
                state[pos] = '\0';
                break;
            }
        }
        dprintf(out_fd, "SUBSYS path=%s name=%s state=%s\n", dir, name, state);
    }
}

static void v1661_append_natural_power_diff_snapshot(int out_fd,
                                                     int sample_index,
                                                     long start_ms,
                                                     long micro_start_ms) {
    static const char *const clocks[] = {
        "gcc_pcie_1_aux_clk_src",
        "gcc_pcie_1_aux_clk",
        "gcc_pcie_1_cfg_ahb_clk",
        "gcc_pcie_1_mstr_axi_clk",
        "gcc_pcie_1_slv_axi_clk",
        "gcc_pcie_1_clkref_clk",
        "gcc_pcie_1_slv_q2a_axi_clk",
        "gcc_pcie_phy_refgen_clk_src",
        "gcc_pcie1_phy_refgen_clk",
        "gcc_pcie_1_pipe_clk",
        "pcie_1_pipe_clk",
        NULL,
    };
    long now_ms = monotonic_millis();
    const long elapsed_ms = now_ms >= start_ms ? now_ms - start_ms : -1;
    const long micro_elapsed_ms = now_ms >= micro_start_ms ? now_ms - micro_start_ms : -1;

    dprintf(out_fd,
            "A90_V1661_REGULATOR_BEGIN index=%d elapsed_ms=%ld micro_elapsed_ms=%ld\n",
            sample_index,
            elapsed_ms,
            micro_elapsed_ms);
    v1661_append_file_raw(out_fd, "/sys/kernel/debug/regulator/regulator_summary");
    dprintf(out_fd, "A90_V1661_REGULATOR_END index=%d elapsed_ms=%ld\n", sample_index, elapsed_ms);
    dprintf(out_fd,
            "A90_V1661_CLOCKS_BEGIN index=%d elapsed_ms=%ld micro_elapsed_ms=%ld\n",
            sample_index,
            elapsed_ms,
            micro_elapsed_ms);
    for (size_t index = 0; clocks[index] != NULL; index++) {
        v1661_append_clock_snapshot(out_fd, clocks[index]);
    }
    dprintf(out_fd, "A90_V1661_CLOCKS_END index=%d elapsed_ms=%ld\n", sample_index, elapsed_ms);
    dprintf(out_fd,
            "A90_V1661_SUBSYS_BEGIN index=%d elapsed_ms=%ld micro_elapsed_ms=%ld\n",
            sample_index,
            elapsed_ms,
            micro_elapsed_ms);
    v1661_append_subsys_snapshot(out_fd);
    dprintf(out_fd, "A90_V1661_SUBSYS_END index=%d elapsed_ms=%ld\n", sample_index, elapsed_ms);
}

static void v1661_append_natural_power_diff_summary(int out_fd, int snapshot_count) {
    dprintf(out_fd,
            "natural_power_diff.begin=1\n"
            "natural_power_diff.mode=pid1-native-natural-provider-power-clock-sequence-snapshot\n"
            "natural_power_diff.snapshot_count=%d\n"
            "natural_power_diff.regulator_summary_full=1\n"
            "natural_power_diff.targeted_named_clocks=1\n"
            "natural_power_diff.full_clk_summary_read=0\n"
            "natural_power_diff.subsystem_sequence=1\n"
            "natural_power_diff.safety_wifi_hal_start=0\n"
            "natural_power_diff.safety_scan_connect=0\n"
            "natural_power_diff.safety_credentials=0\n"
            "natural_power_diff.safety_dhcp_route=0\n"
            "natural_power_diff.safety_external_ping=0\n"
            "natural_power_diff.safety_pmic_write=0\n"
            "natural_power_diff.safety_gpio_write=0\n"
            "natural_power_diff.safety_gdsc_write=0\n"
            "natural_power_diff.safety_regulator_write=0\n"
            "natural_power_diff.safety_forced_rc1=0\n"
            "natural_power_diff.safety_pci_rescan=0\n"
            "natural_power_diff.safety_platform_bind=0\n"
            "natural_power_diff.end=1\n",
            snapshot_count);
}
#endif

static void v1633_append_natural_mdm2ap_irq_summary(const struct v1633_natural_mdm2ap_irq_summary *summary,
                                                    long start_ms,
                                                    long detect_ms,
                                                    long micro_start_ms,
                                                    int sample_count,
                                                    int sample_interval_ms,
                                                    int power_snapshot_count) {
    int out_fd = open(A90_V1393_WIFI_TEST_RC1_WINDOW_RESULT,
                      O_WRONLY | O_CREAT | O_APPEND | O_CLOEXEC | O_NOFOLLOW,
                      0600);
    long now_ms = monotonic_millis();
    unsigned long gpio142_delta = 0;
    unsigned long errfatal_delta = 0;

    if (out_fd < 0) {
        return;
    }
    if (summary->gpio142_initial.parsed && summary->gpio142_max >= summary->gpio142_initial.count_total) {
        gpio142_delta = summary->gpio142_max - summary->gpio142_initial.count_total;
    }
    if (summary->errfatal_initial.parsed && summary->errfatal_max >= summary->errfatal_initial.count_total) {
        errfatal_delta = summary->errfatal_max - summary->errfatal_initial.count_total;
    }
    dprintf(out_fd,
            "mdm2ap_timing.begin=1\n"
            "mdm2ap_timing.mode=pid1-natural-provider-mdm2ap-irq-summary\n"
            "mdm2ap_timing.elapsed_ms=%ld\n"
            "mdm2ap_timing.detect_elapsed_ms=%ld\n"
            "mdm2ap_timing.micro_elapsed_ms=%ld\n"
            "mdm2ap_timing.sample_interval_ms=%d\n"
            "mdm2ap_timing.sample_count=%d\n"
            "mdm2ap_timing.power_snapshot_count=%d\n"
            "mdm2ap_timing.gpio142_irq_initial_parsed=%d\n"
            "mdm2ap_timing.gpio142_irq_initial=%lu\n"
            "mdm2ap_timing.gpio142_irq_max=%lu\n"
            "mdm2ap_timing.gpio142_irq_delta=%lu\n"
            "mdm2ap_timing.gpio142_first_delta_sample=%d\n"
            "mdm2ap_timing.errfatal_irq_initial_parsed=%d\n"
            "mdm2ap_timing.errfatal_irq_initial=%lu\n"
            "mdm2ap_timing.errfatal_irq_max=%lu\n"
            "mdm2ap_timing.errfatal_irq_delta=%lu\n"
            "mdm2ap_timing.errfatal_first_delta_sample=%d\n"
            "mdm2ap_timing.safety_wifi_hal_start=0\n"
            "mdm2ap_timing.safety_scan_connect=0\n"
            "mdm2ap_timing.safety_credentials=0\n"
            "mdm2ap_timing.safety_dhcp_route=0\n"
            "mdm2ap_timing.safety_external_ping=0\n"
            "mdm2ap_timing.safety_pmic_write=0\n"
            "mdm2ap_timing.safety_gpio_request=0\n"
            "mdm2ap_timing.safety_gpio_write=0\n"
            "mdm2ap_timing.safety_gdsc_write=0\n"
            "mdm2ap_timing.safety_regulator_write=0\n"
            "mdm2ap_timing.safety_direct_esoc_ioctl=0\n"
            "mdm2ap_timing.safety_boot_done_spoof=0\n"
            "mdm2ap_timing.safety_pci_rescan=0\n"
            "mdm2ap_timing.safety_platform_bind=0\n"
            "mdm2ap_timing.end=1\n",
            now_ms >= start_ms ? now_ms - start_ms : -1,
            detect_ms >= start_ms ? detect_ms - start_ms : -1,
            now_ms >= micro_start_ms ? now_ms - micro_start_ms : -1,
            sample_interval_ms,
            sample_count,
            power_snapshot_count,
            summary->gpio142_initial.parsed,
            summary->gpio142_initial.count_total,
            summary->gpio142_max,
            gpio142_delta,
            summary->gpio142_first_delta_sample,
            summary->errfatal_initial.parsed,
            summary->errfatal_initial.count_total,
            summary->errfatal_max,
            errfatal_delta,
            summary->errfatal_first_delta_sample);
    close(out_fd);
}

static void v1633_natural_mdm2ap_irq_summary_run(long start_ms,
                                                 long detect_ms,
                                                 long micro_start_ms,
                                                struct v1633_natural_mdm2ap_irq_summary *summary) {
    enum {
        V1633_NATURAL_IRQ_SAMPLE_COUNT = 120,
        V1633_NATURAL_IRQ_SAMPLE_INTERVAL_MS = 50,
    };
    int power_snapshot_count = 0;

    for (int sample_index = 0; sample_index < V1633_NATURAL_IRQ_SAMPLE_COUNT; sample_index++) {
        usleep(V1633_NATURAL_IRQ_SAMPLE_INTERVAL_MS * 1000U);
        v1633_natural_mdm2ap_irq_summary_sample(summary, sample_index);
#if A90_WIFI_TEST_BOOT_NATURAL_POWER_DIFF_SNAPSHOT
        if (sample_index == 0 || sample_index == 8 || sample_index == 24 ||
            sample_index == 40 || sample_index == 64 || sample_index == 96 ||
            sample_index == 119) {
            int out_fd = open(A90_V1393_WIFI_TEST_RC1_WINDOW_RESULT,
                              O_WRONLY | O_CREAT | O_APPEND | O_CLOEXEC | O_NOFOLLOW,
                              0600);
            if (out_fd >= 0) {
                v1661_append_natural_power_diff_snapshot(out_fd,
                                                         sample_index,
                                                         start_ms,
                                                         micro_start_ms);
                close(out_fd);
                power_snapshot_count++;
            }
        }
#endif
    }
    v1633_append_natural_mdm2ap_irq_summary(summary,
                                            start_ms,
                                            detect_ms,
                                            micro_start_ms,
                                            V1633_NATURAL_IRQ_SAMPLE_COUNT,
                                            V1633_NATURAL_IRQ_SAMPLE_INTERVAL_MS,
                                            power_snapshot_count);
#if A90_WIFI_TEST_BOOT_NATURAL_POWER_DIFF_SNAPSHOT
    {
        int out_fd = open(A90_V1393_WIFI_TEST_RC1_WINDOW_RESULT,
                          O_WRONLY | O_CREAT | O_APPEND | O_CLOEXEC | O_NOFOLLOW,
                          0600);
        if (out_fd >= 0) {
            v1661_append_natural_power_diff_summary(out_fd, power_snapshot_count);
            close(out_fd);
        }
    }
#endif
}
#endif

#if A90_WIFI_TEST_BOOT_PCIE1_CLOCK_VOTE_PROOF
struct v1664_pcie1_clock_vote_target {
    const char *name;
    const char *rate_value;
    int enable_rc;
    int cleanup_rc;
    int enabled_by_test;
};

static struct v1664_pcie1_clock_vote_target v1664_pcie1_clock_vote_targets[] = {
    {"gcc_pcie_phy_refgen_clk_src", "100000000\n", -EAGAIN, -EAGAIN, 0},
    {"gcc_pcie1_phy_refgen_clk", "100000000\n", -EAGAIN, -EAGAIN, 0},
    {"gcc_pcie_1_aux_clk_src", NULL, -EAGAIN, -EAGAIN, 0},
    {"gcc_pcie_1_aux_clk", NULL, -EAGAIN, -EAGAIN, 0},
    {"gcc_pcie_1_cfg_ahb_clk", NULL, -EAGAIN, -EAGAIN, 0},
    {"gcc_pcie_1_mstr_axi_clk", NULL, -EAGAIN, -EAGAIN, 0},
    {"gcc_pcie_1_slv_axi_clk", NULL, -EAGAIN, -EAGAIN, 0},
    {"gcc_pcie_1_clkref_clk", NULL, -EAGAIN, -EAGAIN, 0},
    {"gcc_pcie_1_slv_q2a_axi_clk", NULL, -EAGAIN, -EAGAIN, 0},
    {"gcc_pcie_1_pipe_clk", NULL, -EAGAIN, -EAGAIN, 0},
};
static long v1664_pcie1_clock_vote_start_ms;

static int v1664_pcie1_clock_vote_open_result(void) {
    return open(A90_WIFI_TEST_BOOT_PCIE1_CLOCK_VOTE_RESULT,
                O_WRONLY | O_CREAT | O_APPEND | O_CLOEXEC | O_NOFOLLOW,
                0600);
}

static int v1664_pcie1_clock_vote_write_string(const char *path, const char *value) {
    int fd;
    int rc;

    fd = open(path, O_WRONLY | O_CLOEXEC | O_NOFOLLOW);
    if (fd < 0) {
        return -errno;
    }
    rc = write_all_checked(fd, value, strlen(value));
    if (close(fd) < 0 && rc == 0) {
        return -errno;
    }
    return rc < 0 ? negative_errno_or(EIO) : 0;
}

static int v1664_pcie1_clock_vote_read_value(const char *path, char *value, size_t value_size) {
    int fd;
    ssize_t bytes_read;

    if (value_size == 0) {
        return -EINVAL;
    }
    value[0] = '\0';
    fd = open(path, O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
    if (fd < 0) {
        return -errno;
    }
    bytes_read = read(fd, value, value_size - 1);
    if (close(fd) < 0 && bytes_read >= 0) {
        return -errno;
    }
    if (bytes_read < 0) {
        return -errno;
    }
    value[bytes_read] = '\0';
    for (ssize_t index = 0; index < bytes_read; index++) {
        if (value[index] == '\n' || value[index] == '\r') {
            value[index] = '\0';
            break;
        }
    }
    return 0;
}

static int v1664_pcie1_clock_vote_count_enable_leaves(void) {
    int ready_count = 0;

    for (size_t index = 0;
         index < sizeof(v1664_pcie1_clock_vote_targets) / sizeof(v1664_pcie1_clock_vote_targets[0]);
         index++) {
        char path[256];
        char value[64];

        snprintf(path,
                 sizeof(path),
                 "/sys/kernel/debug/clk/%s/enable",
                 v1664_pcie1_clock_vote_targets[index].name);
        if (v1664_pcie1_clock_vote_read_value(path, value, sizeof(value)) == 0) {
            ready_count++;
        }
    }
    return ready_count;
}

static int v1664_pcie1_clock_vote_wait_ready(long start_ms) {
    int out_fd;
    long deadline_ms = monotonic_millis() + A90_WIFI_TEST_BOOT_PCIE1_CLOCK_VOTE_WAIT_MS;
    int sample_count = 0;
    int ready_count = 0;

    out_fd = v1664_pcie1_clock_vote_open_result();
    if (out_fd >= 0) {
        dprintf(out_fd,
                "pcie1_clock_vote.wait_begin=1 async=%d wait_ms=%d result_path=%s elapsed_ms=%ld\n",
                A90_WIFI_TEST_BOOT_PCIE1_CLOCK_VOTE_ASYNC,
                A90_WIFI_TEST_BOOT_PCIE1_CLOCK_VOTE_WAIT_MS,
                A90_WIFI_TEST_BOOT_PCIE1_CLOCK_VOTE_RESULT,
                monotonic_millis() >= start_ms ? monotonic_millis() - start_ms : -1);
        close(out_fd);
    }
    while (monotonic_millis() < deadline_ms) {
        ready_count = v1664_pcie1_clock_vote_count_enable_leaves();
        sample_count++;
        if (ready_count > 0) {
            break;
        }
        usleep(50000);
    }
    out_fd = v1664_pcie1_clock_vote_open_result();
    if (out_fd >= 0) {
        dprintf(out_fd,
                "pcie1_clock_vote.wait_end=1 ready_count=%d sample_count=%d elapsed_ms=%ld\n",
                ready_count,
                sample_count,
                monotonic_millis() >= start_ms ? monotonic_millis() - start_ms : -1);
        close(out_fd);
    }
    return ready_count > 0 ? 0 : -ENOENT;
}

static void v1664_pcie1_clock_vote_append_clock_line(int out_fd,
                                                     const char *phase,
                                                     int index,
                                                     const struct v1664_pcie1_clock_vote_target *target) {
    char path[256];
    char enable_value[64];
    char prepare_value[64];
    char rate_value[64];
    int enable_read_rc;
    int prepare_read_rc;
    int rate_read_rc;

    snprintf(path, sizeof(path), "/sys/kernel/debug/clk/%s/clk_enable_count", target->name);
    enable_read_rc = v1664_pcie1_clock_vote_read_value(path, enable_value, sizeof(enable_value));
    snprintf(path, sizeof(path), "/sys/kernel/debug/clk/%s/clk_prepare_count", target->name);
    prepare_read_rc = v1664_pcie1_clock_vote_read_value(path, prepare_value, sizeof(prepare_value));
    snprintf(path, sizeof(path), "/sys/kernel/debug/clk/%s/clk_rate", target->name);
    rate_read_rc = v1664_pcie1_clock_vote_read_value(path, rate_value, sizeof(rate_value));
    dprintf(out_fd,
            "pcie1_clock_vote.clock_%02d.phase=%s name=%s enable_read_rc=%d enable=%s prepare_read_rc=%d prepare=%s rate_read_rc=%d rate=%s enabled_by_test=%d enable_rc=%d cleanup_rc=%d\n",
            index,
            phase,
            target->name,
            enable_read_rc,
            enable_read_rc == 0 ? enable_value : "",
            prepare_read_rc,
            prepare_read_rc == 0 ? prepare_value : "",
            rate_read_rc,
            rate_read_rc == 0 ? rate_value : "",
            target->enabled_by_test,
            target->enable_rc,
            target->cleanup_rc);
}

static void v1664_pcie1_clock_vote_snapshot(const char *phase, long start_ms) {
    int out_fd;
    long now_ms = monotonic_millis();

    out_fd = v1664_pcie1_clock_vote_open_result();
    if (out_fd < 0) {
        return;
    }
    dprintf(out_fd,
            "A90_V1664_CLOCK_VOTE_SNAPSHOT phase=%s elapsed_ms=%ld\n",
            phase,
            now_ms >= start_ms ? now_ms - start_ms : -1);
    for (size_t index = 0;
         index < sizeof(v1664_pcie1_clock_vote_targets) / sizeof(v1664_pcie1_clock_vote_targets[0]);
         index++) {
        v1664_pcie1_clock_vote_append_clock_line(out_fd,
                                                 phase,
                                                 (int)index,
                                                 &v1664_pcie1_clock_vote_targets[index]);
    }
#if A90_WIFI_TEST_BOOT_NATURAL_POWER_DIFF_SNAPSHOT
    v1661_append_natural_power_diff_snapshot(out_fd, -1, start_ms, start_ms);
#endif
    close(out_fd);
}

static int v1664_pcie1_clock_vote_begin(long start_ms) {
    int out_fd;
    int success_count = 0;
    int rate_success_count = 0;
    int failure_count = 0;
    int wait_ready_rc;

    v1664_pcie1_clock_vote_start_ms = start_ms;
    wait_ready_rc = v1664_pcie1_clock_vote_wait_ready(start_ms);
    v1664_pcie1_clock_vote_snapshot("pre", start_ms);
    out_fd = v1664_pcie1_clock_vote_open_result();
    if (out_fd < 0) {
        return -errno;
    }
    dprintf(out_fd,
            "pcie1_clock_vote.begin=1\n"
            "pcie1_clock_vote.wait_ready_rc=%d\n"
            "pcie1_clock_vote.mode=bounded-clock-debug-vote-surface-proof\n"
            "pcie1_clock_vote.allowed_clock_debug_writes=1\n"
            "pcie1_clock_vote.safety_regulator_write=0\n"
            "pcie1_clock_vote.safety_gdsc_write=0\n"
            "pcie1_clock_vote.safety_pci_case_write=0\n"
            "pcie1_clock_vote.safety_forced_rc1=0\n"
            "pcie1_clock_vote.safety_pmic_write=0\n"
            "pcie1_clock_vote.safety_gpio_write=0\n"
            "pcie1_clock_vote.safety_esoc_notify=0\n"
            "pcie1_clock_vote.safety_boot_done_spoof=0\n"
            "pcie1_clock_vote.safety_pci_rescan=0\n"
            "pcie1_clock_vote.safety_platform_bind=0\n"
            "pcie1_clock_vote.safety_wifi_hal_start=0\n"
            "pcie1_clock_vote.safety_scan_connect=0\n"
            "pcie1_clock_vote.safety_credentials=0\n"
            "pcie1_clock_vote.safety_dhcp_route=0\n"
            "pcie1_clock_vote.safety_external_ping=0\n",
            wait_ready_rc);
    for (size_t index = 0;
         index < sizeof(v1664_pcie1_clock_vote_targets) / sizeof(v1664_pcie1_clock_vote_targets[0]);
         index++) {
        struct v1664_pcie1_clock_vote_target *target = &v1664_pcie1_clock_vote_targets[index];
        char path[256];
        int rate_rc = 0;
        int enable_rc;

        if (target->rate_value != NULL) {
            snprintf(path, sizeof(path), "/sys/kernel/debug/clk/%s/rate", target->name);
            rate_rc = v1664_pcie1_clock_vote_write_string(path, target->rate_value);
            if (rate_rc == 0) {
                rate_success_count++;
            }
        }
        snprintf(path, sizeof(path), "/sys/kernel/debug/clk/%s/enable", target->name);
        enable_rc = v1664_pcie1_clock_vote_write_string(path, "1\n");
        target->enable_rc = enable_rc;
        if (enable_rc == 0) {
            target->enabled_by_test = 1;
            success_count++;
        } else {
            failure_count++;
        }
        dprintf(out_fd,
                "pcie1_clock_vote.action_%02zu name=%s rate_value=%s rate_rc=%d enable_rc=%d path=%s\n",
                index,
                target->name,
                target->rate_value != NULL ? target->rate_value : "",
                rate_rc,
                enable_rc,
                path);
    }
    dprintf(out_fd,
            "pcie1_clock_vote.success_count=%d\n"
            "pcie1_clock_vote.rate_success_count=%d\n"
            "pcie1_clock_vote.failure_count=%d\n",
            success_count,
            rate_success_count,
            failure_count);
    close(out_fd);
    v1664_pcie1_clock_vote_snapshot("post_enable", start_ms);
    return success_count > 0 ? 0 : -EIO;
}

static int v1664_pcie1_clock_vote_cleanup(long start_ms) {
    int out_fd;
    int cleanup_success_count = 0;
    int cleanup_failure_count = 0;

    out_fd = v1664_pcie1_clock_vote_open_result();
    if (out_fd < 0) {
        return -errno;
    }
    dprintf(out_fd, "pcie1_clock_vote.cleanup_begin=1 elapsed_ms=%ld\n",
            monotonic_millis() >= start_ms ? monotonic_millis() - start_ms : -1);
    for (ssize_t index =
             (ssize_t)(sizeof(v1664_pcie1_clock_vote_targets) /
                       sizeof(v1664_pcie1_clock_vote_targets[0])) - 1;
         index >= 0;
         index--) {
        struct v1664_pcie1_clock_vote_target *target = &v1664_pcie1_clock_vote_targets[index];
        char path[256];

        if (!target->enabled_by_test) {
            dprintf(out_fd,
                    "pcie1_clock_vote.cleanup_%02zd name=%s skipped=1 enable_rc=%d\n",
                    index,
                    target->name,
                    target->enable_rc);
            continue;
        }
        snprintf(path, sizeof(path), "/sys/kernel/debug/clk/%s/enable", target->name);
        target->cleanup_rc = v1664_pcie1_clock_vote_write_string(path, "0\n");
        if (target->cleanup_rc == 0) {
            cleanup_success_count++;
        } else {
            cleanup_failure_count++;
        }
        dprintf(out_fd,
                "pcie1_clock_vote.cleanup_%02zd name=%s cleanup_rc=%d path=%s\n",
                index,
                target->name,
                target->cleanup_rc,
                path);
    }
    dprintf(out_fd,
            "pcie1_clock_vote.cleanup_success_count=%d\n"
            "pcie1_clock_vote.cleanup_failure_count=%d\n"
            "pcie1_clock_vote.cleanup_end=1\n",
            cleanup_success_count,
            cleanup_failure_count);
    close(out_fd);
    v1664_pcie1_clock_vote_snapshot("post_cleanup", start_ms);
    return cleanup_failure_count == 0 ? 0 : -EIO;
}

#if A90_WIFI_TEST_BOOT_PCIE1_CLOCK_VOTE_ASYNC
static void v1664_pcie1_clock_vote_child(void) {
    long start_ms = monotonic_millis();
    int begin_rc;
    int cleanup_rc;
    int out_fd;

    begin_rc = v1664_pcie1_clock_vote_begin(start_ms);
    out_fd = v1664_pcie1_clock_vote_open_result();
    if (out_fd >= 0) {
        dprintf(out_fd,
                "pcie1_clock_vote.async_begin_rc=%d hold_ms=%d\n",
                begin_rc,
                A90_WIFI_TEST_BOOT_PCIE1_CLOCK_VOTE_HOLD_MS);
        close(out_fd);
    }
    if (begin_rc == 0) {
        usleep((useconds_t)A90_WIFI_TEST_BOOT_PCIE1_CLOCK_VOTE_HOLD_MS * 1000U);
    }
    cleanup_rc = v1664_pcie1_clock_vote_cleanup(start_ms);
    out_fd = v1664_pcie1_clock_vote_open_result();
    if (out_fd >= 0) {
        dprintf(out_fd,
                "pcie1_clock_vote.async_cleanup_rc=%d\n"
                "pcie1_clock_vote.async_end=1\n",
                cleanup_rc);
        close(out_fd);
    }
    _exit(begin_rc == 0 && cleanup_rc == 0 ? 0 : 1);
}

static int v1664_spawn_pcie1_clock_vote_child(pid_t *pid_out) {
    pid_t pid;

    (void)unlink(A90_WIFI_TEST_BOOT_PCIE1_CLOCK_VOTE_RESULT);
    pid = fork();
    if (pid < 0) {
        return -errno;
    }
    if (pid == 0) {
        signal(SIGHUP, SIG_IGN);
        signal(SIGPIPE, SIG_IGN);
        setsid();
        v1664_pcie1_clock_vote_child();
        _exit(1);
    }
    if (pid_out != NULL) {
        *pid_out = pid;
    }
    return 0;
}
#endif
#endif

#if A90_WIFI_TEST_BOOT_RC1_IMMEDIATE_ENDPOINT_SAMPLER
static void v1393_rc1_immediate_endpoint_sample(const char *sample,
                                                long start_ms,
                                                long detect_ms,
                                                long immediate_start_ms) {
    static const char *const immediate_interrupt_needles[] = {
        "mdm status",
        "PCIe",
        "LTSSM",
        "mhi",
        "MHI",
        NULL,
    };
    static const char *const immediate_regulator_needles[] = {
        "pcie_1_gdsc",
        "pcie_0_gdsc",
        "pm8150l_l3",
        "pm8150_l5",
        "VDD_CX_LEVEL",
        NULL,
    };
    static const char *const immediate_clk_needles[] = {
        "gcc_pcie_1_slv_q2a_axi_clk",
        "gcc_pcie_1_slv_axi_clk",
        "gcc_pcie_1_pipe_clk",
        "gcc_pcie_1_mstr_axi_clk",
        "gcc_pcie_1_clkref_clk",
        "gcc_pcie_1_cfg_ahb_clk",
        "gcc_pcie1_phy_refgen_clk",
        "gcc_pcie_phy_refgen_clk_src",
        NULL,
    };
    static const char *const immediate_gpio_needles[] = {
        "gpio102",
        "gpio103",
        "gpio104",
        "gpio135",
        "gpio142",
        "GPIO_102",
        "GPIO_103",
        "GPIO_104",
        "GPIO_135",
        "GPIO_142",
        NULL,
    };
    int out_fd;
    long now_ms = monotonic_millis();

    out_fd = open(A90_V1393_WIFI_TEST_RC1_WINDOW_RESULT,
                  O_WRONLY | O_CREAT | O_APPEND | O_CLOEXEC | O_NOFOLLOW,
                  0600);
    if (out_fd < 0) {
        return;
    }
    dprintf(out_fd,
            "rc1_immediate_sample label=%s elapsed_ms=%ld detect_elapsed_ms=%ld immediate_elapsed_ms=%ld\n",
            sample,
            now_ms >= start_ms ? now_ms - start_ms : -1,
            detect_ms >= start_ms ? detect_ms - start_ms : -1,
            now_ms >= immediate_start_ms ? now_ms - immediate_start_ms : -1);
    dprintf(out_fd, "sample=%s immediate_endpoint_sampler=1\n", sample);
    v1393_rc1_window_append_matching_lines(out_fd,
                                           sample,
                                           "immediate_interrupts",
                                           "/proc/interrupts",
                                           immediate_interrupt_needles);
    v1393_rc1_window_append_exact_matches(out_fd,
                                          sample,
                                          "immediate_regulator",
                                          "/sys/kernel/debug/regulator/regulator_summary",
                                          immediate_regulator_needles);
    v1393_rc1_window_append_exact_matches(out_fd,
                                          sample,
                                          "immediate_clk",
                                          "/sys/kernel/debug/clk/clk_summary",
                                          immediate_clk_needles);
    v1393_rc1_window_append_exact_matches(out_fd,
                                          sample,
                                          "immediate_debug_gpio",
                                          "/sys/kernel/debug/gpio",
                                          immediate_gpio_needles);
    v1393_rc1_window_append_exact_matches(out_fd,
                                          sample,
                                          "immediate_pinmux",
                                          "/sys/kernel/debug/pinctrl/3000000.pinctrl/pinmux-pins",
                                          immediate_gpio_needles);
    v1393_rc1_window_append_exact_matches(out_fd,
                                          sample,
                                          "immediate_pinconf",
                                          "/sys/kernel/debug/pinctrl/3000000.pinctrl/pinconf-pins",
                                          immediate_gpio_needles);
#if A90_WIFI_TEST_BOOT_RC1_ENDPOINT_SAMPLER
    v1393_rc1_window_append_trimmed_file(out_fd,
                                         sample,
                                         "immediate_pcie1_current_link_state",
                                         "/sys/devices/platform/soc/1c08000.qcom,pcie/current_link_state");
    v1393_rc1_window_append_trimmed_file(out_fd,
                                         sample,
                                         "immediate_pcie1_link_state",
                                         "/sys/devices/platform/soc/1c08000.qcom,pcie/link_state");
#endif
    close(out_fd);
}
#endif

#if A90_WIFI_TEST_BOOT_RC1_MICRO_ENDPOINT_SAMPLER
static void v1393_rc1_micro_sleep_until(long base_ms, int target_ms) {
    for (;;) {
        long now_ms = monotonic_millis();
        long remaining_ms = base_ms + target_ms - now_ms;

        if (remaining_ms <= 0) {
            return;
        }
        if (remaining_ms > 5) {
            usleep(5000);
        } else {
            usleep((useconds_t)remaining_ms * 1000U);
        }
    }
}

static void v1393_rc1_micro_endpoint_sample(const char *sample,
                                            long start_ms,
                                            long detect_ms,
                                            long micro_start_ms) {
    static const char *const micro_interrupt_needles[] = {
        "mdm status",
        "msm_pcie_wake",
        "PCIe",
        "LTSSM",
        NULL,
    };
    static const char *const micro_gpio_needles[] = {
        "gpio102",
        "gpio103",
        "gpio104",
        "gpio135",
        "gpio142",
        "GPIO_102",
        "GPIO_103",
        "GPIO_104",
        "GPIO_135",
        "GPIO_142",
        NULL,
    };
#if A90_WIFI_TEST_BOOT_RC1_ENDPOINT_SAMPLER && A90_WIFI_TEST_BOOT_RC1_MICRO_FOCUSED_ENDPOINT_SAMPLER
    static const char *const micro_exact_regulator_needles[] = {
        "pcie_1_gdsc",
        "pcie_0_gdsc",
        "pm8150l_l3",
        "pm8150_l5",
        "VDD_CX_LEVEL",
        NULL,
    };
    static const char *const micro_exact_clk_needles[] = {
        "gcc_pcie_1_slv_q2a_axi_clk",
        "gcc_pcie_1_slv_axi_clk",
        "gcc_pcie_1_pipe_clk",
        "gcc_pcie_1_mstr_axi_clk",
        "gcc_pcie_1_clkref_clk",
        "gcc_pcie_1_cfg_ahb_clk",
        "gcc_pcie1_phy_refgen_clk",
        "gcc_pcie_phy_refgen_clk_src",
        NULL,
    };
    static const char *const micro_exact_gpio_needles[] = {
        "gpio102",
        "gpio103",
        "gpio104",
        "gpio135",
        "gpio142",
        "GPIO_102",
        "GPIO_103",
        "GPIO_104",
        "GPIO_135",
        "GPIO_142",
        NULL,
    };
#endif
#if A90_WIFI_TEST_BOOT_RC1_ENDPOINT_SAMPLER && A90_WIFI_TEST_BOOT_RC1_MICRO_BATCHED_FOCUSED_ENDPOINT_SAMPLER
    static const char *const micro_batched_regulator_needles[] = {
        "pcie_1_gdsc",
        "pcie_0_gdsc",
        "pm8150l_l3",
        "pm8150_l5",
        "VDD_CX_LEVEL",
        NULL,
    };
    static const char *const micro_batched_clk_needles[] = {
        "gcc_pcie_1_slv_q2a_axi_clk",
        "gcc_pcie_1_slv_axi_clk",
        "gcc_pcie_1_pipe_clk",
        "gcc_pcie_1_mstr_axi_clk",
        "gcc_pcie_1_clkref_clk",
        "gcc_pcie_1_cfg_ahb_clk",
        "gcc_pcie1_phy_refgen_clk",
        "gcc_pcie_phy_refgen_clk_src",
        NULL,
    };
    static const char *const micro_batched_gpio_needles[] = {
        "gpio102",
        "gpio103",
        "gpio104",
        "gpio135",
        "gpio142",
        "GPIO_102",
        "GPIO_103",
        "GPIO_104",
        "GPIO_135",
        "GPIO_142",
        NULL,
    };
#endif
#if A90_WIFI_TEST_BOOT_RC1_ENDPOINT_SAMPLER && A90_WIFI_TEST_BOOT_RC1_MICRO_CRITICAL_FAST_ENDPOINT_SAMPLER
    static const char *const micro_critical_regulator_needles[] = {
        "pcie_1_gdsc",
        "pcie_0_gdsc",
        "pm8150l_l3",
        "pm8150_l5",
        NULL,
    };
    static const char *const micro_critical_pinmux_needles[] = {
        "GPIO_102",
        "GPIO_103",
        "GPIO_104",
        "GPIO_135",
        "GPIO_142",
        NULL,
    };
#endif
    int out_fd;
    long now_ms = monotonic_millis();

    out_fd = open(A90_V1393_WIFI_TEST_RC1_WINDOW_RESULT,
                  O_WRONLY | O_CREAT | O_APPEND | O_CLOEXEC | O_NOFOLLOW,
                  0600);
    if (out_fd < 0) {
        return;
    }
    dprintf(out_fd,
            "rc1_micro_sample label=%s elapsed_ms=%ld detect_elapsed_ms=%ld micro_elapsed_ms=%ld\n",
            sample,
            now_ms >= start_ms ? now_ms - start_ms : -1,
            detect_ms >= start_ms ? detect_ms - start_ms : -1,
            now_ms >= micro_start_ms ? now_ms - micro_start_ms : -1);
    dprintf(out_fd, "sample=%s micro_endpoint_sampler=1\n", sample);
#if A90_WIFI_TEST_BOOT_RC1_ENDPOINT_SAMPLER && A90_WIFI_TEST_BOOT_RC1_MICRO_FOCUSED_ENDPOINT_SAMPLER
    dprintf(out_fd, "sample=%s micro_focused_endpoint_sampler=1\n", sample);
#endif
#if A90_WIFI_TEST_BOOT_RC1_ENDPOINT_SAMPLER && A90_WIFI_TEST_BOOT_RC1_MICRO_BATCHED_FOCUSED_ENDPOINT_SAMPLER
    dprintf(out_fd, "sample=%s micro_batched_focused_endpoint_sampler=1\n", sample);
#endif
#if A90_WIFI_TEST_BOOT_RC1_ENDPOINT_SAMPLER && A90_WIFI_TEST_BOOT_RC1_MICRO_SOURCE_TIMESTAMPED_SAMPLER
    dprintf(out_fd, "sample=%s micro_source_timestamped_sampler=1\n", sample);
#endif
#if A90_WIFI_TEST_BOOT_RC1_ENDPOINT_SAMPLER && A90_WIFI_TEST_BOOT_RC1_MICRO_CRITICAL_FAST_ENDPOINT_SAMPLER
    dprintf(out_fd, "sample=%s micro_critical_fast_endpoint_sampler=1\n", sample);
#endif
#if A90_WIFI_TEST_BOOT_RC1_ENDPOINT_SAMPLER && A90_WIFI_TEST_BOOT_RC1_MICRO_SOURCE_TIMESTAMPED_SAMPLER
    v1511_rc1_window_append_matching_lines_timed(out_fd,
                                                 sample,
                                                 "micro_interrupts",
                                                 "/proc/interrupts",
                                                 micro_interrupt_needles,
                                                 start_ms,
                                                 micro_start_ms);
#if A90_WIFI_TEST_BOOT_RC1_MICRO_CRITICAL_FAST_ENDPOINT_SAMPLER
    v1511_rc1_window_append_matching_lines_timed(out_fd,
                                                 sample,
                                                 "micro_debug_gpio",
                                                 "/sys/kernel/debug/gpio",
                                                 micro_gpio_needles,
                                                 start_ms,
                                                 micro_start_ms);
#else
    v1511_rc1_window_append_exact_matches_timed(out_fd,
                                                sample,
                                                "micro_debug_gpio",
                                                "/sys/kernel/debug/gpio",
                                                micro_gpio_needles,
                                                start_ms,
                                                micro_start_ms);
#endif
#else
    v1393_rc1_window_append_matching_lines(out_fd,
                                           sample,
                                           "micro_interrupts",
                                           "/proc/interrupts",
                                           micro_interrupt_needles);
#if A90_WIFI_TEST_BOOT_RC1_ENDPOINT_SAMPLER && A90_WIFI_TEST_BOOT_RC1_MICRO_CRITICAL_FAST_ENDPOINT_SAMPLER
    v1393_rc1_window_append_matching_lines(out_fd,
                                           sample,
                                           "micro_debug_gpio",
                                           "/sys/kernel/debug/gpio",
                                           micro_gpio_needles);
#else
    v1393_rc1_window_append_exact_matches(out_fd,
                                          sample,
                                          "micro_debug_gpio",
                                          "/sys/kernel/debug/gpio",
                                          micro_gpio_needles);
#endif
#endif
#if A90_WIFI_TEST_BOOT_RC1_ENDPOINT_SAMPLER
#if A90_WIFI_TEST_BOOT_RC1_MICRO_SOURCE_TIMESTAMPED_SAMPLER
    v1511_rc1_window_append_trimmed_file_timed(out_fd,
                                               sample,
                                               "micro_pcie1_current_link_state",
                                               "/sys/devices/platform/soc/1c08000.qcom,pcie/current_link_state",
                                               start_ms,
                                               micro_start_ms);
    v1511_rc1_window_append_trimmed_file_timed(out_fd,
                                               sample,
                                               "micro_pcie1_link_state",
                                               "/sys/devices/platform/soc/1c08000.qcom,pcie/link_state",
                                               start_ms,
                                               micro_start_ms);
#else
    v1393_rc1_window_append_trimmed_file(out_fd,
                                         sample,
                                         "micro_pcie1_current_link_state",
                                         "/sys/devices/platform/soc/1c08000.qcom,pcie/current_link_state");
    v1393_rc1_window_append_trimmed_file(out_fd,
                                         sample,
                                         "micro_pcie1_link_state",
                                         "/sys/devices/platform/soc/1c08000.qcom,pcie/link_state");
#endif
#if A90_WIFI_TEST_BOOT_RC1_MICRO_CRITICAL_FAST_ENDPOINT_SAMPLER
#if A90_WIFI_TEST_BOOT_RC1_MICRO_SOURCE_TIMESTAMPED_SAMPLER
    v1511_rc1_window_append_matching_lines_timed(out_fd,
                                                 sample,
                                                 "micro_critical_regulator",
                                                 "/sys/kernel/debug/regulator/regulator_summary",
                                                 micro_critical_regulator_needles,
                                                 start_ms,
                                                 micro_start_ms);
    v1511_rc1_window_append_matching_lines_timed(out_fd,
                                                 sample,
                                                 "micro_critical_pinmux",
                                                 "/sys/kernel/debug/pinctrl/3000000.pinctrl/pinmux-pins",
                                                 micro_critical_pinmux_needles,
                                                 start_ms,
                                                 micro_start_ms);
#else
    v1393_rc1_window_append_matching_lines(out_fd,
                                           sample,
                                           "micro_critical_regulator",
                                           "/sys/kernel/debug/regulator/regulator_summary",
                                           micro_critical_regulator_needles);
    v1393_rc1_window_append_matching_lines(out_fd,
                                           sample,
                                           "micro_critical_pinmux",
                                           "/sys/kernel/debug/pinctrl/3000000.pinctrl/pinmux-pins",
                                           micro_critical_pinmux_needles);
#endif
    dprintf(out_fd,
            "sample=%s micro_critical_clk_summary_skipped=1 reason=clk_summary-too-slow-for-pre-l0-window\n",
            sample);
#endif
#if A90_WIFI_TEST_BOOT_RC1_MICRO_FOCUSED_ENDPOINT_SAMPLER
#if A90_WIFI_TEST_BOOT_RC1_MICRO_SOURCE_TIMESTAMPED_SAMPLER
    v1511_rc1_window_append_exact_matches_timed(out_fd,
                                                sample,
                                                "micro_focused_regulator",
                                                "/sys/kernel/debug/regulator/regulator_summary",
                                                micro_exact_regulator_needles,
                                                start_ms,
                                                micro_start_ms);
    v1511_rc1_window_append_exact_matches_timed(out_fd,
                                                sample,
                                                "micro_focused_clk",
                                                "/sys/kernel/debug/clk/clk_summary",
                                                micro_exact_clk_needles,
                                                start_ms,
                                                micro_start_ms);
    v1511_rc1_window_append_exact_matches_timed(out_fd,
                                                sample,
                                                "micro_focused_debug_gpio",
                                                "/sys/kernel/debug/gpio",
                                                micro_exact_gpio_needles,
                                                start_ms,
                                                micro_start_ms);
    v1511_rc1_window_append_exact_matches_timed(out_fd,
                                                sample,
                                                "micro_focused_pinmux",
                                                "/sys/kernel/debug/pinctrl/3000000.pinctrl/pinmux-pins",
                                                micro_exact_gpio_needles,
                                                start_ms,
                                                micro_start_ms);
    v1511_rc1_window_append_exact_matches_timed(out_fd,
                                                sample,
                                                "micro_focused_pinconf",
                                                "/sys/kernel/debug/pinctrl/3000000.pinctrl/pinconf-pins",
                                                micro_exact_gpio_needles,
                                                start_ms,
                                                micro_start_ms);
#else
    v1393_rc1_window_append_exact_matches(out_fd,
                                          sample,
                                          "micro_focused_regulator",
                                          "/sys/kernel/debug/regulator/regulator_summary",
                                          micro_exact_regulator_needles);
    v1393_rc1_window_append_exact_matches(out_fd,
                                          sample,
                                          "micro_focused_clk",
                                          "/sys/kernel/debug/clk/clk_summary",
                                          micro_exact_clk_needles);
    v1393_rc1_window_append_exact_matches(out_fd,
                                          sample,
                                          "micro_focused_debug_gpio",
                                          "/sys/kernel/debug/gpio",
                                          micro_exact_gpio_needles);
    v1393_rc1_window_append_exact_matches(out_fd,
                                          sample,
                                          "micro_focused_pinmux",
                                          "/sys/kernel/debug/pinctrl/3000000.pinctrl/pinmux-pins",
                                          micro_exact_gpio_needles);
    v1393_rc1_window_append_exact_matches(out_fd,
                                          sample,
                                          "micro_focused_pinconf",
                                          "/sys/kernel/debug/pinctrl/3000000.pinctrl/pinconf-pins",
                                          micro_exact_gpio_needles);
#endif
#endif
#if A90_WIFI_TEST_BOOT_RC1_MICRO_BATCHED_FOCUSED_ENDPOINT_SAMPLER
#if A90_WIFI_TEST_BOOT_RC1_MICRO_SOURCE_TIMESTAMPED_SAMPLER
    v1511_rc1_window_append_matching_lines_timed(out_fd,
                                                 sample,
                                                 "micro_batched_regulator",
                                                 "/sys/kernel/debug/regulator/regulator_summary",
                                                 micro_batched_regulator_needles,
                                                 start_ms,
                                                 micro_start_ms);
    v1511_rc1_window_append_matching_lines_timed(out_fd,
                                                 sample,
                                                 "micro_batched_clk",
                                                 "/sys/kernel/debug/clk/clk_summary",
                                                 micro_batched_clk_needles,
                                                 start_ms,
                                                 micro_start_ms);
    v1511_rc1_window_append_matching_lines_timed(out_fd,
                                                 sample,
                                                 "micro_batched_debug_gpio",
                                                 "/sys/kernel/debug/gpio",
                                                 micro_batched_gpio_needles,
                                                 start_ms,
                                                 micro_start_ms);
    v1511_rc1_window_append_matching_lines_timed(out_fd,
                                                 sample,
                                                 "micro_batched_pinmux",
                                                 "/sys/kernel/debug/pinctrl/3000000.pinctrl/pinmux-pins",
                                                 micro_batched_gpio_needles,
                                                 start_ms,
                                                 micro_start_ms);
    v1511_rc1_window_append_matching_lines_timed(out_fd,
                                                 sample,
                                                 "micro_batched_pinconf",
                                                 "/sys/kernel/debug/pinctrl/3000000.pinctrl/pinconf-pins",
                                                 micro_batched_gpio_needles,
                                                 start_ms,
                                                 micro_start_ms);
#else
    v1393_rc1_window_append_matching_lines(out_fd,
                                           sample,
                                           "micro_batched_regulator",
                                           "/sys/kernel/debug/regulator/regulator_summary",
                                           micro_batched_regulator_needles);
    v1393_rc1_window_append_matching_lines(out_fd,
                                           sample,
                                           "micro_batched_clk",
                                           "/sys/kernel/debug/clk/clk_summary",
                                           micro_batched_clk_needles);
    v1393_rc1_window_append_matching_lines(out_fd,
                                           sample,
                                           "micro_batched_debug_gpio",
                                           "/sys/kernel/debug/gpio",
                                           micro_batched_gpio_needles);
    v1393_rc1_window_append_matching_lines(out_fd,
                                           sample,
                                           "micro_batched_pinmux",
                                           "/sys/kernel/debug/pinctrl/3000000.pinctrl/pinmux-pins",
                                           micro_batched_gpio_needles);
    v1393_rc1_window_append_matching_lines(out_fd,
                                           sample,
                                           "micro_batched_pinconf",
                                           "/sys/kernel/debug/pinctrl/3000000.pinctrl/pinconf-pins",
                                           micro_batched_gpio_needles);
#endif
#endif
#endif
    close(out_fd);
}

#if A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_AP2MDM_HOLD
static void v1393_provider_tracepoint_sample(const char *sample,
                                             long start_ms,
                                             long detect_ms,
                                             long trace_start_ms);

static void v1477_append_ap2mdm_hold_line(const char *fmt, ...) {
    int fd;
    va_list ap;

    fd = open(A90_V1393_WIFI_TEST_RC1_WINDOW_RESULT,
              O_WRONLY | O_CREAT | O_APPEND | O_CLOEXEC | O_NOFOLLOW,
              0600);
    if (fd < 0) {
        return;
    }
    va_start(ap, fmt);
    (void)vdprintf(fd, fmt, ap);
    va_end(ap);
    close(fd);
}

static int v1477_provider_trigger_ap2mdm_hold(long start_ms,
                                              long detect_ms,
                                              long micro_start_ms,
                                              const char *gate_sample) {
    long action_ms = monotonic_millis();
    int trace_set_high;
    int debug_low;
    int export_rc;
    int direction_rc = -ECANCELED;
    int release_rc = 0;
    int unexport_rc = 0;
    int exported = 0;

    trace_set_high = v1477_text_file_contains_line("/sys/kernel/debug/tracing/trace",
                                                   "gpio_value: 135 set 1");
    debug_low = v1477_text_file_contains_line("/sys/kernel/debug/gpio",
                                              "gpio135 : out 0");
    v1477_append_ap2mdm_hold_line(
        "ap2mdm_hold gate_sample=%s elapsed_ms=%ld hold_after_ms=%d hold_ms=%d trace_set_high=%d debug_gpio135_low=%d\n",
        gate_sample != NULL ? gate_sample : "unknown",
        action_ms >= start_ms ? action_ms - start_ms : -1,
        A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_AP2MDM_HOLD_AFTER_MS,
        A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_AP2MDM_HOLD_MS,
        trace_set_high,
        debug_low);

    if (trace_set_high != 1 || debug_low != 1) {
        v1477_append_ap2mdm_hold_line(
            "ap2mdm_hold skipped reason=gate-not-satisfied trace_set_high=%d debug_gpio135_low=%d\n",
            trace_set_high,
            debug_low);
        return -EAGAIN;
    }

    export_rc = v1477_write_wifi_test_sysfs_string("/sys/class/gpio/export", "135\n");
    if (export_rc == 0) {
        exported = 1;
        direction_rc = v1477_write_wifi_test_sysfs_string("/sys/class/gpio/gpio135/direction", "high\n");
    }
    v1477_append_ap2mdm_hold_line(
        "ap2mdm_hold attempt export_rc=%d exported=%d direction_high_rc=%d\n",
        export_rc,
        exported,
        direction_rc);

    if (direction_rc == 0) {
        v1393_rc1_micro_endpoint_sample("ap2mdm_hold_after_high_0ms",
                                        start_ms,
                                        detect_ms,
                                        micro_start_ms);
#if A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_TRACEPOINT_SAMPLER
        v1393_provider_tracepoint_sample("ap2mdm_hold_after_high_0ms",
                                         start_ms,
                                         detect_ms,
                                         micro_start_ms);
#endif
        usleep(20000);
        v1393_rc1_micro_endpoint_sample("ap2mdm_hold_after_high_20ms",
                                        start_ms,
                                        detect_ms,
                                        micro_start_ms);
        usleep((useconds_t)A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_AP2MDM_HOLD_MS * 1000U);
        v1393_rc1_micro_endpoint_sample("ap2mdm_hold_before_release",
                                        start_ms,
                                        detect_ms,
                                        micro_start_ms);
        release_rc = v1477_write_wifi_test_sysfs_string("/sys/class/gpio/gpio135/value", "0\n");
    }
    if (exported) {
        unexport_rc = v1477_write_wifi_test_sysfs_string("/sys/class/gpio/unexport", "135\n");
    }
    v1393_rc1_micro_endpoint_sample("ap2mdm_hold_after_release",
                                    start_ms,
                                    detect_ms,
                                    micro_start_ms);
    v1477_append_ap2mdm_hold_line(
        "ap2mdm_hold cleanup release_rc=%d unexport_rc=%d result_rc=%d\n",
        release_rc,
        unexport_rc,
        direction_rc == 0 ? 0 : (export_rc < 0 ? export_rc : direction_rc));
    return direction_rc == 0 ? 0 : (export_rc < 0 ? export_rc : direction_rc);
}
#endif

#if A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_THREAD_STATE
static void v1393_provider_thread_state_sample(const char *sample,
                                               long start_ms,
                                               long detect_ms,
                                               long thread_start_ms,
                                               int trigger_pid) {
    static const char *const status_needles[] = {
        "Name:",
        "State:",
        "Tgid:",
        "Pid:",
        "PPid:",
        "TracerPid:",
        "Threads:",
        "voluntary_ctxt_switches:",
        "nonvoluntary_ctxt_switches:",
        NULL,
    };
    char path[96];
    int out_fd;
    long now_ms = monotonic_millis();

    out_fd = open(A90_V1393_WIFI_TEST_RC1_WINDOW_RESULT,
                  O_WRONLY | O_CREAT | O_APPEND | O_CLOEXEC | O_NOFOLLOW,
                  0600);
    if (out_fd < 0) {
        return;
    }
    dprintf(out_fd,
            "provider_thread_state label=%s elapsed_ms=%ld detect_elapsed_ms=%ld thread_elapsed_ms=%ld trigger_pid=%d\n",
            sample,
            now_ms >= start_ms ? now_ms - start_ms : -1,
            detect_ms >= start_ms ? detect_ms - start_ms : -1,
            now_ms >= thread_start_ms ? now_ms - thread_start_ms : -1,
            trigger_pid);
    dprintf(out_fd, "sample=%s provider_thread_state=1 trigger_pid=%d\n", sample, trigger_pid);
    if (trigger_pid <= 0) {
        dprintf(out_fd, "sample=%s source=provider_thread_state trigger_pid_invalid=1\n", sample);
        close(out_fd);
        return;
    }
    snprintf(path, sizeof(path), "/proc/%d/comm", trigger_pid);
    v1393_rc1_window_append_trimmed_file(out_fd, sample, "provider_thread_comm", path);
    snprintf(path, sizeof(path), "/proc/%d/wchan", trigger_pid);
    v1393_rc1_window_append_trimmed_file(out_fd, sample, "provider_thread_wchan", path);
    snprintf(path, sizeof(path), "/proc/%d/stat", trigger_pid);
    v1393_rc1_window_append_trimmed_file(out_fd, sample, "provider_thread_stat", path);
    snprintf(path, sizeof(path), "/proc/%d/status", trigger_pid);
    v1393_rc1_window_append_matching_lines(out_fd,
                                           sample,
                                           "provider_thread_status",
                                           path,
                                           status_needles);
    close(out_fd);
}
#endif

#if A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_TRACEPOINT_SAMPLER
static int v1393_tracefs_write_string(const char *path, const char *value) {
    int fd;
    int rc;

    fd = open(path, O_WRONLY | O_CLOEXEC);
    if (fd < 0) {
        return -errno;
    }
    rc = write_all_checked(fd, value, strlen(value));
    if (close(fd) < 0 && rc == 0) {
        return -errno;
    }
    return rc < 0 ? negative_errno_or(EIO) : 0;
}

static void v1393_provider_tracepoint_arm(void) {
    int trace_off_rc;
    int clear_rc;
    int gpio_value_rc;
    int gpio_direction_rc;
    int trace_on_rc;
#if A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_PIL_TRACEPOINT_SAMPLER
    int pil_notif_rc;
#endif

    trace_off_rc = v1393_tracefs_write_string("/sys/kernel/debug/tracing/tracing_on", "0\n");
    clear_rc = v1393_tracefs_write_string("/sys/kernel/debug/tracing/trace", "\n");
    gpio_value_rc = v1393_tracefs_write_string("/sys/kernel/debug/tracing/events/gpio/gpio_value/enable", "1\n");
    gpio_direction_rc = v1393_tracefs_write_string("/sys/kernel/debug/tracing/events/gpio/gpio_direction/enable", "1\n");
#if A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_PIL_TRACEPOINT_SAMPLER
    pil_notif_rc = v1393_tracefs_write_string("/sys/kernel/debug/tracing/events/msm_pil_event/pil_notif/enable", "1\n");
#endif
    trace_on_rc = v1393_tracefs_write_string("/sys/kernel/debug/tracing/tracing_on", "1\n");
#if A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_PIL_TRACEPOINT_SAMPLER
    (void)v1393_append_wifi_test_log(
        "provider tracepoint arm trace_off_rc=%d clear_rc=%d gpio_value_rc=%d gpio_direction_rc=%d pil_notif_rc=%d trace_on_rc=%d\n",
        trace_off_rc,
        clear_rc,
        gpio_value_rc,
        gpio_direction_rc,
        pil_notif_rc,
        trace_on_rc);
#else
    (void)v1393_append_wifi_test_log(
        "provider tracepoint arm trace_off_rc=%d clear_rc=%d gpio_value_rc=%d gpio_direction_rc=%d trace_on_rc=%d\n",
        trace_off_rc,
        clear_rc,
        gpio_value_rc,
        gpio_direction_rc,
        trace_on_rc);
#endif
}

static void v1393_provider_tracepoint_disarm(void) {
    int trace_off_rc;
    int gpio_value_rc;
    int gpio_direction_rc;
#if A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_PIL_TRACEPOINT_SAMPLER
    int pil_notif_rc;
#endif

    trace_off_rc = v1393_tracefs_write_string("/sys/kernel/debug/tracing/tracing_on", "0\n");
    gpio_value_rc = v1393_tracefs_write_string("/sys/kernel/debug/tracing/events/gpio/gpio_value/enable", "0\n");
    gpio_direction_rc = v1393_tracefs_write_string("/sys/kernel/debug/tracing/events/gpio/gpio_direction/enable", "0\n");
#if A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_PIL_TRACEPOINT_SAMPLER
    pil_notif_rc = v1393_tracefs_write_string("/sys/kernel/debug/tracing/events/msm_pil_event/pil_notif/enable", "0\n");
#endif
#if A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_PIL_TRACEPOINT_SAMPLER
    (void)v1393_append_wifi_test_log(
        "provider tracepoint disarm trace_off_rc=%d gpio_value_rc=%d gpio_direction_rc=%d pil_notif_rc=%d\n",
        trace_off_rc,
        gpio_value_rc,
        gpio_direction_rc,
        pil_notif_rc);
#else
    (void)v1393_append_wifi_test_log(
        "provider tracepoint disarm trace_off_rc=%d gpio_value_rc=%d gpio_direction_rc=%d\n",
        trace_off_rc,
        gpio_value_rc,
        gpio_direction_rc);
#endif
}

static void v1393_provider_tracepoint_sample(const char *sample,
                                             long start_ms,
                                             long detect_ms,
                                             long trace_start_ms) {
    static const char *const trace_needles[] = {
        "gpio_value: 1270",
        "gpio_direction: 1270",
        "gpio_value: 135",
        "gpio_direction: 135",
        "gpio_value: 142",
        "gpio_direction: 142",
        "gpio_value: 141",
        "gpio_direction: 141",
#if A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_PIL_TRACEPOINT_SAMPLER
        "pil_notif:",
        "fw=esoc0",
#endif
        NULL,
    };
    int out_fd;
    long now_ms = monotonic_millis();

    out_fd = open(A90_V1393_WIFI_TEST_RC1_WINDOW_RESULT,
                  O_WRONLY | O_CREAT | O_APPEND | O_CLOEXEC | O_NOFOLLOW,
                  0600);
    if (out_fd < 0) {
        return;
    }
    dprintf(out_fd,
            "provider_tracepoint_sample label=%s elapsed_ms=%ld detect_elapsed_ms=%ld trace_elapsed_ms=%ld\n",
            sample,
            now_ms >= start_ms ? now_ms - start_ms : -1,
            detect_ms >= start_ms ? detect_ms - start_ms : -1,
            now_ms >= trace_start_ms ? now_ms - trace_start_ms : -1);
    v1393_rc1_window_append_matching_lines(out_fd,
                                           sample,
                                           A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_PIL_TRACEPOINT_SAMPLER
                                               ? "provider_pil_gpio_trace"
                                               : "provider_gpio_trace",
                                           "/sys/kernel/debug/tracing/trace",
                                           trace_needles);
    close(out_fd);
}
#endif

#if !A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_MICRO_ENDPOINT_SAMPLER
static void v1393_rc1_micro_writer_child(int pipe_fd, long start_ms) {
    int rc;
    int saved_errno;
    char trigger_summary[320];

    trigger_summary[0] = '\0';
    rc = v1536_pid1_rc1_write_enumerate_trigger(start_ms,
                                                trigger_summary,
                                                sizeof(trigger_summary));
    saved_errno = rc < 0 ? -rc : 0;
    dprintf(pipe_fd,
            "micro_writer rc=%d errno=%d %s\n",
            rc,
            saved_errno,
            trigger_summary);
    close(pipe_fd);
    _exit(rc == 0 ? 0 : 3);
}

static int v1393_wait_rc1_micro_writer(pid_t pid, int timeout_ms, int *status_out) {
    long deadline = monotonic_millis() + timeout_ms;
    int status;

    while (monotonic_millis() < deadline) {
        pid_t rc = waitpid(pid, &status, WNOHANG);

        if (rc == pid) {
            if (status_out != NULL) {
                *status_out = status;
            }
            return 0;
        }
        if (rc < 0) {
            return -errno;
        }
        usleep(1000);
    }

    (void)kill(pid, SIGKILL);
    deadline = monotonic_millis() + 1000;
    while (monotonic_millis() < deadline) {
        pid_t rc = waitpid(pid, &status, WNOHANG);

        if (rc == pid) {
            if (status_out != NULL) {
                *status_out = status;
            }
            return -ETIMEDOUT;
        }
        if (rc < 0) {
            return -errno;
        }
        usleep(1000);
    }
    return -ETIMEDOUT;
}

static int v1393_rc1_micro_read_writer_result(int read_fd,
                                               pid_t writer_pid,
                                               int *status_out,
                                               int *writer_wait_rc_out,
                                               char *writer_result,
                                               size_t writer_result_size) {
    ssize_t rd;
    int status = 0xffff;
    int writer_wait_rc;

    if (writer_result_size > 0) {
        writer_result[0] = '\0';
    }
    (void)fcntl(read_fd, F_SETFL, fcntl(read_fd, F_GETFL, 0) | O_NONBLOCK);
    writer_wait_rc = v1393_wait_rc1_micro_writer(writer_pid, 2000, &status);
    rd = read(read_fd, writer_result, writer_result_size > 0 ? writer_result_size - 1 : 0);
    if (rd > 0 && writer_result_size > 0) {
        writer_result[rd] = '\0';
        flatten_inline_text(writer_result);
    } else if (writer_result_size > 0) {
        snprintf(writer_result, writer_result_size, "micro_writer pipe_read_rc=%zd", rd);
    }
    if (status_out != NULL) {
        *status_out = status;
    }
    if (writer_wait_rc_out != NULL) {
        *writer_wait_rc_out = writer_wait_rc;
    }
    return writer_wait_rc;
}

static void v1393_rc1_micro_append_writer_summary(pid_t writer_pid,
                                                  int writer_wait_rc,
                                                  int status,
                                                  const char *writer_result) {
    int out_fd;

    out_fd = open(A90_V1393_WIFI_TEST_RC1_WINDOW_RESULT,
                  O_WRONLY | O_CREAT | O_APPEND | O_CLOEXEC | O_NOFOLLOW,
                  0600);
    if (out_fd >= 0) {
        dprintf(out_fd,
                "rc1_micro_writer_summary pid=%d writer_wait_rc=%d status=0x%x %s\n",
                writer_pid,
                writer_wait_rc,
                status,
                writer_result != NULL ? writer_result : "");
        close(out_fd);
    }
}

static int v1393_rc1_micro_writer_status_to_rc(int writer_wait_rc, int status) {
    if (writer_wait_rc < 0) {
        return writer_wait_rc;
    }
    if (WIFEXITED(status) && WEXITSTATUS(status) == 0) {
        return 0;
    }
    if (WIFEXITED(status)) {
        return -EIO;
    }
    if (WIFSIGNALED(status)) {
        return -EINTR;
    }
    return -EIO;
}

#if !A90_WIFI_TEST_BOOT_RC1_CASE_ALIGNED_MICRO_ENDPOINT_SAMPLER && !A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_MICRO_ENDPOINT_SAMPLER
static int v1393_pid1_rc1_micro_endpoint_sample_with_writer(long start_ms, long detect_ms) {
    static const int targets_ms[] = {0, 1, 2, 5, 10, 20, 50, 100, 150};
    int pipe_fds[2];
    pid_t writer_pid;
    long micro_start_ms;
    size_t index;
    int status = 0xffff;
    int writer_wait_rc;
    char writer_result[192] = "";

    if (pipe(pipe_fds) < 0) {
        return -errno;
    }
    writer_pid = fork();
    if (writer_pid < 0) {
        int saved_errno = errno != 0 ? errno : EIO;

        close(pipe_fds[0]);
        close(pipe_fds[1]);
        return -saved_errno;
    }
    micro_start_ms = monotonic_millis();
    if (writer_pid == 0) {
        close(pipe_fds[0]);
        signal(SIGHUP, SIG_IGN);
        signal(SIGPIPE, SIG_IGN);
        v1393_rc1_micro_writer_child(pipe_fds[1], start_ms);
    }

    close(pipe_fds[1]);
    for (index = 0; index < sizeof(targets_ms) / sizeof(targets_ms[0]); index++) {
        char sample[48];

        v1393_rc1_micro_sleep_until(micro_start_ms, targets_ms[index]);
        snprintf(sample, sizeof(sample), "micro_after_case_%dms", targets_ms[index]);
        v1393_rc1_micro_endpoint_sample(sample, start_ms, detect_ms, micro_start_ms);
    }

    v1393_rc1_window_sample("post_micro_200ms", start_ms, detect_ms, micro_start_ms);

    (void)v1393_rc1_micro_read_writer_result(pipe_fds[0],
                                             writer_pid,
                                             &status,
                                             &writer_wait_rc,
                                             writer_result,
                                             sizeof(writer_result));
    close(pipe_fds[0]);
    v1393_rc1_micro_append_writer_summary(writer_pid,
                                          writer_wait_rc,
                                          status,
                                          writer_result);
    return v1393_rc1_micro_writer_status_to_rc(writer_wait_rc, status);
}
#endif

#if !A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_MICRO_ENDPOINT_SAMPLER
static int v1393_pid1_rc1_case_aligned_micro_endpoint_sample_with_writer(long start_ms,
                                                                         long detect_ms) {
    static const int targets_ms[] = {0, 1, 2, 5, 10, 20, 50, 100, 150};
    int pipe_fds[2];
    pid_t writer_pid;
    long micro_start_ms;
    size_t index;
    int status = 0xffff;
    int writer_wait_rc;
    char writer_result[192] = "";
    int writer_status_rc;

    if (pipe(pipe_fds) < 0) {
        return -errno;
    }
    writer_pid = fork();
    if (writer_pid < 0) {
        int saved_errno = errno != 0 ? errno : EIO;

        close(pipe_fds[0]);
        close(pipe_fds[1]);
        return -saved_errno;
    }
    if (writer_pid == 0) {
        close(pipe_fds[0]);
        signal(SIGHUP, SIG_IGN);
        signal(SIGPIPE, SIG_IGN);
        v1393_rc1_micro_writer_child(pipe_fds[1], start_ms);
    }

    close(pipe_fds[1]);
    (void)v1393_rc1_micro_read_writer_result(pipe_fds[0],
                                             writer_pid,
                                             &status,
                                             &writer_wait_rc,
                                             writer_result,
                                             sizeof(writer_result));
    close(pipe_fds[0]);
    v1393_rc1_micro_append_writer_summary(writer_pid,
                                          writer_wait_rc,
                                          status,
                                          writer_result);
    writer_status_rc = v1393_rc1_micro_writer_status_to_rc(writer_wait_rc, status);
    if (writer_status_rc != 0) {
        return writer_status_rc;
    }

    micro_start_ms = monotonic_millis();
    for (index = 0; index < sizeof(targets_ms) / sizeof(targets_ms[0]); index++) {
        char sample[64];

        v1393_rc1_micro_sleep_until(micro_start_ms, targets_ms[index]);
        snprintf(sample, sizeof(sample), "case_aligned_micro_after_case_%dms", targets_ms[index]);
        v1393_rc1_micro_endpoint_sample(sample, start_ms, detect_ms, micro_start_ms);
    }

    v1393_rc1_window_sample("post_case_aligned_micro_200ms",
                            start_ms,
                            detect_ms,
                            micro_start_ms);
    return 0;
}
#endif
#endif

static int v1393_pid1_provider_trigger_micro_endpoint_sample(long start_ms,
                                                             long detect_ms,
                                                             int trigger_pid) {
#if A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_LONG_WINDOW
#if A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_EFFECTIVE_LEVEL_SAMPLER
    static const int targets_ms[] = {
        0, 1, 2, 5, 10, 20, 50, 100, 150, 250, 300, 320, 350, 400, 500, 750,
        1000, 1200, 1500, 2000, 3000
    };
#else
    static const int targets_ms[] = {0, 1, 2, 5, 10, 20, 50, 100, 150, 250, 300, 500, 1000};
#endif
#else
    static const int targets_ms[] = {0, 1, 2, 5, 10, 20, 50, 100, 150};
#endif
    long micro_start_ms = monotonic_millis();
    size_t index;
#if A90_WIFI_TEST_BOOT_NATURAL_MDM2AP_IRQ_SUMMARY
    struct v1633_natural_mdm2ap_irq_summary natural_irq_summary;

    v1633_natural_mdm2ap_irq_summary_init(&natural_irq_summary);
#endif
#if A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_AP2MDM_HOLD
    int ap2mdm_hold_attempted = 0;
    int ap2mdm_hold_rc = -EAGAIN;
#endif

    for (index = 0; index < sizeof(targets_ms) / sizeof(targets_ms[0]); index++) {
        char sample[64];

        v1393_rc1_micro_sleep_until(micro_start_ms, targets_ms[index]);
        snprintf(sample, sizeof(sample), "provider_micro_after_trigger_%dms", targets_ms[index]);
        v1393_rc1_micro_endpoint_sample(sample, start_ms, detect_ms, micro_start_ms);
#if A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_THREAD_STATE
        v1393_provider_thread_state_sample(sample, start_ms, detect_ms, micro_start_ms, trigger_pid);
#endif
#if A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_TRACEPOINT_SAMPLER
        v1393_provider_tracepoint_sample(sample, start_ms, detect_ms, micro_start_ms);
#endif
#if A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_EFFECTIVE_LEVEL_SAMPLER
        if (targets_ms[index] >= 250) {
            v1393_rc1_window_sample(sample, start_ms, detect_ms, micro_start_ms);
        }
#endif
#if A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_AP2MDM_HOLD
        if (!ap2mdm_hold_attempted &&
            targets_ms[index] >= A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_AP2MDM_HOLD_AFTER_MS) {
            ap2mdm_hold_attempted = 1;
            ap2mdm_hold_rc = v1477_provider_trigger_ap2mdm_hold(start_ms,
                                                                detect_ms,
                                                                micro_start_ms,
                                                                sample);
        }
#endif
    }

#if A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_LONG_WINDOW
    v1393_rc1_window_sample("post_provider_micro_1200ms",
                            start_ms,
                            detect_ms,
                            micro_start_ms);
#else
    v1393_rc1_window_sample("post_provider_micro_200ms",
                            start_ms,
                            detect_ms,
                            micro_start_ms);
#endif
#if A90_WIFI_TEST_BOOT_NATURAL_MDM2AP_IRQ_SUMMARY
    v1633_natural_mdm2ap_irq_summary_run(start_ms,
                                         detect_ms,
                                         micro_start_ms,
                                         &natural_irq_summary);
#endif
#if A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_AP2MDM_HOLD
    v1477_append_ap2mdm_hold_line("ap2mdm_hold summary attempted=%d rc=%d\n",
                                  ap2mdm_hold_attempted,
                                  ap2mdm_hold_rc);
#endif
    return 0;
}
#endif

static void v1393_rc1_window_prepare(long start_ms, long detect_ms, const char *line) {
    char header[512];

    snprintf(header,
             sizeof(header),
             "state=armed sampler=%s detect_elapsed_ms=%ld delay_ms=%d exact_provider_line=%d long_provider_window=%d tracepoint_sampler=%d pil_tracepoint_sampler=%d sysfs_client_enumerate=%d trigger_mode=%s line=%.*s\n",
             A90_V1393_WIFI_TEST_RC1_WINDOW_SAMPLER_NAME,
             detect_ms >= start_ms ? detect_ms - start_ms : -1,
             A90_WIFI_TEST_BOOT_RC1_WATCHER_DELAY_MS,
             A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_EXACT_LINE,
             A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_LONG_WINDOW,
             A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_TRACEPOINT_SAMPLER,
             A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_PIL_TRACEPOINT_SAMPLER,
             A90_WIFI_TEST_BOOT_RC1_SYSFS_CLIENT_ENUMERATE,
             A90_V1536_RC1_ENUMERATE_TRIGGER_MODE,
             160,
             line != NULL ? line : "");
    flatten_inline_text(header);
    strncat(header, "\n", sizeof(header) - strlen(header) - 1);
    (void)v724_write_private_file(A90_V1393_WIFI_TEST_RC1_WINDOW_RESULT, header);
}

#if !A90_WIFI_TEST_BOOT_RC1_MICRO_ENDPOINT_SAMPLER
static void v1393_rc1_window_sampler_child(long start_ms, long detect_ms) {
    long child_start_ms = monotonic_millis();

    v1393_rc1_window_sample("pre_rc1", start_ms, detect_ms, child_start_ms);
    usleep(50000);
    v1393_rc1_window_sample("post_rc1_50ms", start_ms, detect_ms, child_start_ms);
    usleep(100000);
    v1393_rc1_window_sample("post_rc1_150ms", start_ms, detect_ms, child_start_ms);
    usleep(350000);
    v1393_rc1_window_sample("post_rc1_500ms", start_ms, detect_ms, child_start_ms);
    _exit(0);
}

static int v1393_spawn_rc1_window_sampler(long start_ms, long detect_ms) {
    pid_t pid = fork();

    if (pid < 0) {
        return -errno;
    }
    if (pid == 0) {
        signal(SIGHUP, SIG_IGN);
        signal(SIGPIPE, SIG_IGN);
        setsid();
        v1393_rc1_window_sampler_child(start_ms, detect_ms);
        _exit(1);
    }
    return 0;
}
#endif
#endif

#if A90_WIFI_TEST_BOOT_RC1_IMMEDIATE_ENDPOINT_SAMPLER
static int v1393_pid1_rc1_write_corrected_enumerate_with_immediate_samples(long start_ms,
                                                                           long detect_ms) {
    int case_rc;
    long immediate_start_ms;
    char trigger_summary[320];

    trigger_summary[0] = '\0';
    case_rc = v1536_pid1_rc1_write_enumerate_trigger(start_ms,
                                                     trigger_summary,
                                                     sizeof(trigger_summary));
    immediate_start_ms = monotonic_millis();
    (void)v1393_append_wifi_test_log("pid1 rc1 immediate trigger %s rc=%d\n",
                                    trigger_summary,
                                    case_rc);
#if A90_WIFI_TEST_BOOT_RC1_WINDOW_SAMPLER
    v1393_rc1_immediate_endpoint_sample("after_case_0ms",
                                        start_ms,
                                        detect_ms,
                                        immediate_start_ms);
    usleep(1000);
    v1393_rc1_immediate_endpoint_sample("after_case_1ms",
                                        start_ms,
                                        detect_ms,
                                        immediate_start_ms);
    usleep(4000);
    v1393_rc1_immediate_endpoint_sample("after_case_5ms",
                                        start_ms,
                                        detect_ms,
                                        immediate_start_ms);
    usleep(15000);
    v1393_rc1_immediate_endpoint_sample("after_case_20ms",
                                        start_ms,
                                        detect_ms,
                                        immediate_start_ms);
#endif
    return case_rc;
}
#endif

static void v1393_pid1_rc1_watcher_child(void) {
    long start_ms = monotonic_millis();
    long deadline_ms = start_ms + (long)A90_WIFI_TEST_BOOT_RC1_WATCHER_TIMEOUT_SEC * 1000L;
    int fd;
    int dev_kmsg_errno = 0;
    const char *source = "/dev/kmsg";
    char result[1024];

    fd = open("/dev/kmsg", O_RDONLY | O_NONBLOCK | O_CLOEXEC);
    if (fd < 0) {
        dev_kmsg_errno = errno != 0 ? errno : EIO;
        source = "/proc/kmsg";
        fd = open("/proc/kmsg", O_RDONLY | O_NONBLOCK | O_CLOEXEC);
        if (fd < 0) {
            int proc_kmsg_errno = errno != 0 ? errno : EIO;

            snprintf(result,
                     sizeof(result),
                     "state=open-kmsg-failed dev_errno=%d proc_errno=%d elapsed_ms=0\n",
                     dev_kmsg_errno,
                     proc_kmsg_errno);
            (void)v724_write_private_file(A90_V1393_WIFI_TEST_RC1_WATCHER_RESULT, result);
            _exit(2);
        }
        for (;;) {
            char drain[768];
            ssize_t rd = read(fd, drain, sizeof(drain) - 1);

            if (rd > 0) {
                continue;
            }
            if (rd == 0 || errno == EAGAIN || errno == EWOULDBLOCK) {
                break;
            }
            {
                int saved_errno = errno != 0 ? errno : EIO;

                snprintf(result,
                         sizeof(result),
                         "state=drain-kmsg-failed source=%s errno=%d elapsed_ms=%ld\n",
                         source,
                         saved_errno,
                         monotonic_millis() - start_ms);
                (void)v724_write_private_file(A90_V1393_WIFI_TEST_RC1_WATCHER_RESULT, result);
                close(fd);
                _exit(2);
            }
        }
    } else {
        (void)lseek(fd, 0, SEEK_END);
    }

    while (monotonic_millis() < deadline_ms) {
        char line[768];
        ssize_t rd = read(fd, line, sizeof(line) - 1);

        if (rd > 0) {
            line[rd] = '\0';
#if A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_EXACT_LINE
            if (!v1393_pid1_rc1_extract_trigger_line(line, line, sizeof(line))) {
                continue;
            }
#endif
            if (v1393_pid1_rc1_trigger_line(line)) {
                long detect_ms = monotonic_millis();
                int trigger_pid = -1;
                int write_rc;
                long write_ms;
                int saved_errno;
                char retry_result[320] = "";

#if A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_EXACT_LINE
                trigger_pid = v1393_pid1_rc1_extract_trigger_pid(line);
#endif

#if A90_WIFI_TEST_BOOT_RC1_WINDOW_SAMPLER
                v1393_rc1_window_prepare(start_ms, detect_ms, line);
#if !A90_WIFI_TEST_BOOT_RC1_MICRO_ENDPOINT_SAMPLER
                v1393_rc1_window_sample("pre_delay", start_ms, detect_ms, detect_ms);
#endif
#endif
                if (A90_WIFI_TEST_BOOT_RC1_WATCHER_DELAY_MS > 0 &&
                    !A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_MICRO_ENDPOINT_SAMPLER) {
                    usleep((useconds_t)A90_WIFI_TEST_BOOT_RC1_WATCHER_DELAY_MS * 1000U);
                }
#if A90_WIFI_TEST_BOOT_RC1_WINDOW_SAMPLER && !A90_WIFI_TEST_BOOT_RC1_MICRO_ENDPOINT_SAMPLER
                (void)v1393_spawn_rc1_window_sampler(start_ms, detect_ms);
#endif
#if A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_MICRO_ENDPOINT_SAMPLER
                write_rc = v1393_pid1_provider_trigger_micro_endpoint_sample(start_ms,
                                                                             detect_ms,
                                                                             trigger_pid);
#elif A90_WIFI_TEST_BOOT_RC1_CASE_ALIGNED_MICRO_ENDPOINT_SAMPLER
                write_rc = v1393_pid1_rc1_case_aligned_micro_endpoint_sample_with_writer(start_ms,
                                                                                         detect_ms);
#elif A90_WIFI_TEST_BOOT_RC1_MICRO_ENDPOINT_SAMPLER
                write_rc = v1393_pid1_rc1_micro_endpoint_sample_with_writer(start_ms,
                                                                            detect_ms);
#elif A90_WIFI_TEST_BOOT_RC1_IMMEDIATE_ENDPOINT_SAMPLER
                write_rc = v1393_pid1_rc1_write_corrected_enumerate_with_immediate_samples(start_ms,
                                                                                            detect_ms);
#else
                write_rc = v1393_pid1_rc1_write_corrected_enumerate();
#endif
                saved_errno = write_rc < 0 ? -write_rc : 0;
                write_ms = monotonic_millis();

#if A90_WIFI_TEST_BOOT_RC1_RETRY_COUNT > 0
                {
                    size_t retry_len = 0;
                    int retry_index;

                    for (retry_index = 1;
                         retry_index <= A90_WIFI_TEST_BOOT_RC1_RETRY_COUNT;
                         retry_index++) {
                        int retry_rc;
                        int retry_errno;
                        long retry_ms;

                        if (A90_WIFI_TEST_BOOT_RC1_RETRY_DELAY_MS > 0) {
                            usleep((useconds_t)A90_WIFI_TEST_BOOT_RC1_RETRY_DELAY_MS * 1000U);
                        }
                        retry_rc = v1393_pid1_rc1_write_corrected_enumerate();
                        retry_errno = retry_rc < 0 ? -retry_rc : 0;
                        retry_ms = monotonic_millis();
                        if (retry_len < sizeof(retry_result)) {
                            int written = snprintf(retry_result + retry_len,
                                                   sizeof(retry_result) - retry_len,
                                                   " retry%d_rc=%d retry%d_errno=%d retry%d_elapsed_ms=%ld",
                                                   retry_index,
                                                   retry_rc,
                                                   retry_index,
                                                   retry_errno,
                                                   retry_index,
                                                   retry_ms >= start_ms ? retry_ms - start_ms : -1);
                            if (written > 0) {
                                retry_len += (size_t)written;
                                if (retry_len >= sizeof(retry_result)) {
                                    retry_len = sizeof(retry_result) - 1;
                                }
                            }
                        }
                        (void)v1393_append_wifi_test_log("pid1 rc1 watcher retry index=%d rc=%d elapsed_ms=%ld retry_delay_ms=%d\n",
                                                        retry_index,
                                                        retry_rc,
                                                        retry_ms >= start_ms ? retry_ms - start_ms : -1,
                                                        A90_WIFI_TEST_BOOT_RC1_RETRY_DELAY_MS);
                    }
                }
#endif

                snprintf(result,
                         sizeof(result),
                         "state=triggered source=%s trigger_mode=%s write_rc=%d errno=%d detect_elapsed_ms=%ld write_elapsed_ms=%ld delay_ms=%d retry_count=%d retry_delay_ms=%d%s line=%.*s\n",
                         source,
                         A90_V1536_RC1_ENUMERATE_TRIGGER_MODE,
                         write_rc,
                         saved_errno,
                         detect_ms >= start_ms ? detect_ms - start_ms : -1,
                         write_ms >= start_ms ? write_ms - start_ms : -1,
                         A90_WIFI_TEST_BOOT_RC1_WATCHER_DELAY_MS,
                         A90_WIFI_TEST_BOOT_RC1_RETRY_COUNT,
                         A90_WIFI_TEST_BOOT_RC1_RETRY_DELAY_MS,
                         retry_result,
                         120,
                         line);
                (void)v724_write_private_file(A90_V1393_WIFI_TEST_RC1_WATCHER_RESULT, result);
                (void)v1393_append_wifi_test_log("pid1 rc1 watcher triggered source=%s trigger_mode=%s write_rc=%d detect_elapsed_ms=%ld write_elapsed_ms=%ld delay_ms=%d\n",
                                                source,
                                                A90_V1536_RC1_ENUMERATE_TRIGGER_MODE,
                                                write_rc,
                                                detect_ms >= start_ms ? detect_ms - start_ms : -1,
                                                write_ms >= start_ms ? write_ms - start_ms : -1,
                                                A90_WIFI_TEST_BOOT_RC1_WATCHER_DELAY_MS);
                close(fd);
                _exit(write_rc == 0 ? 0 : 3);
            }
        } else if (rd < 0 && errno != EAGAIN && errno != EWOULDBLOCK) {
            int saved_errno = errno != 0 ? errno : EIO;

            snprintf(result,
                     sizeof(result),
                     "state=read-kmsg-failed rc=-%d errno=%d elapsed_ms=%ld\n",
                     saved_errno,
                     saved_errno,
                     monotonic_millis() - start_ms);
            (void)v724_write_private_file(A90_V1393_WIFI_TEST_RC1_WATCHER_RESULT, result);
            close(fd);
            _exit(4);
        }
        usleep(20000);
    }

    snprintf(result,
             sizeof(result),
             "state=timeout source=%s elapsed_ms=%ld timeout_sec=%d\n",
             source,
             monotonic_millis() - start_ms,
             A90_WIFI_TEST_BOOT_RC1_WATCHER_TIMEOUT_SEC);
    (void)v724_write_private_file(A90_V1393_WIFI_TEST_RC1_WATCHER_RESULT, result);
    close(fd);
    _exit(5);
}

static int v1393_spawn_pid1_rc1_watcher(pid_t *pid_out) {
    pid_t pid;

    pid = fork();
    if (pid < 0) {
        return -errno;
    }
    if (pid == 0) {
        signal(SIGHUP, SIG_IGN);
        signal(SIGPIPE, SIG_IGN);
        setsid();
        v1393_pid1_rc1_watcher_child();
        _exit(6);
    }
    if (pid_out != NULL) {
        *pid_out = pid;
    }
    return 0;
}
#endif

#if A90_WIFI_TEST_BOOT_AUTO_READINESS_SUPERVISOR
static int v1488_text_has_any(const char *text, const char *const *needles, size_t needle_count) {
    size_t i;

    if (text == NULL) {
        return 0;
    }
    for (i = 0; i < needle_count; i++) {
        if (needles[i] != NULL && strstr(text, needles[i]) != NULL) {
            return 1;
        }
    }
    return 0;
}

static const char *v1488_pid1_primary_checkpoint(int wlan0_seen,
                                                 int fw_ready_seen,
                                                 int bdf_seen,
                                                 int wlfw_seen,
                                                 int icnss_qmi_seen,
                                                 int mhi_seen,
                                                 int pcie_rc1_seen,
                                                 int provider_trigger_seen,
                                                 int modem_trigger_seen) {
    if (wlan0_seen) {
        return "wlan0";
    }
    if (fw_ready_seen) {
        return "fw-ready";
    }
    if (bdf_seen) {
        return "bdf";
    }
    if (wlfw_seen || icnss_qmi_seen) {
        return "wlfw-or-icnss-qmi";
    }
    if (mhi_seen) {
        return "mhi";
    }
    if (pcie_rc1_seen) {
        return "pcie-rc1";
    }
    if (provider_trigger_seen) {
        return "provider-trigger";
    }
    if (modem_trigger_seen) {
        return "modem-trigger";
    }
    return "none";
}

static void v1488_append_pid1_auto_readiness_summary(int fd, int wlan0_present) {
    static char log_buf[262144];
    static const char *const modem_needles[] = {
        "__subsystem_get: modem",
    };
    static const char *const provider_needles[] = {
        "__subsystem_get: esoc0",
    };
    static const char *const pcie_needles[] = {
        "PCIe RC1",
        "LTSSM_STATE",
        "msm_pcie_enable: PCIe",
    };
    static const char *const mhi_needles[] = {
        "mhi_arch_esoc_ops_power_on",
        "mhi_pci_probe",
        "mhi_0305",
        "/dev/mhi_",
        "MHI control",
    };
    static const char *const wlfw_needles[] = {
        "wlfw",
        "WLFW",
        "wlan/fw",
    };
    static const char *const icnss_qmi_needles[] = {
        "icnss_qmi",
    };
    static const char *const bdf_needles[] = {
        "BDF",
        "bdwlan",
        "regdb",
    };
    static const char *const fw_ready_needles[] = {
        "FW ready",
        "fw_ready",
        "FW_READY",
    };
    ssize_t syslog_len;
    int syslog_errno = 0;
    int syslog_ok;
    int modem_trigger_seen = 0;
    int provider_trigger_seen = 0;
    int pcie_rc1_seen = 0;
    int mhi_seen = 0;
    int wlfw_seen = 0;
    int icnss_qmi_seen = 0;
    int bdf_seen = 0;
    int fw_ready_seen = 0;
    const char *checkpoint;

    syslog_len = syscall(SYS_syslog,
                         SYSLOG_ACTION_READ_ALL,
                         log_buf,
                         (int)sizeof(log_buf) - 1);
    if (syslog_len < 0) {
        syslog_errno = errno != 0 ? errno : EIO;
        syslog_len = 0;
        log_buf[0] = '\0';
        syslog_ok = 0;
    } else {
        if ((size_t)syslog_len >= sizeof(log_buf)) {
            syslog_len = (ssize_t)sizeof(log_buf) - 1;
        }
        log_buf[syslog_len] = '\0';
        syslog_ok = 1;
        modem_trigger_seen = v1488_text_has_any(log_buf, modem_needles, sizeof(modem_needles) / sizeof(modem_needles[0]));
        provider_trigger_seen = v1488_text_has_any(log_buf, provider_needles, sizeof(provider_needles) / sizeof(provider_needles[0]));
        pcie_rc1_seen = v1488_text_has_any(log_buf, pcie_needles, sizeof(pcie_needles) / sizeof(pcie_needles[0]));
        mhi_seen = v1488_text_has_any(log_buf, mhi_needles, sizeof(mhi_needles) / sizeof(mhi_needles[0]));
        wlfw_seen = v1488_text_has_any(log_buf, wlfw_needles, sizeof(wlfw_needles) / sizeof(wlfw_needles[0]));
        icnss_qmi_seen = v1488_text_has_any(log_buf, icnss_qmi_needles, sizeof(icnss_qmi_needles) / sizeof(icnss_qmi_needles[0]));
        bdf_seen = v1488_text_has_any(log_buf, bdf_needles, sizeof(bdf_needles) / sizeof(bdf_needles[0]));
        fw_ready_seen = v1488_text_has_any(log_buf, fw_ready_needles, sizeof(fw_ready_needles) / sizeof(fw_ready_needles[0]));
    }
    checkpoint = v1488_pid1_primary_checkpoint(wlan0_present,
                                               fw_ready_seen,
                                               bdf_seen,
                                               wlfw_seen,
                                               icnss_qmi_seen,
                                               mhi_seen,
                                               pcie_rc1_seen,
                                               provider_trigger_seen,
                                               modem_trigger_seen);
    dprintf(fd, "auto_readiness_pid1.begin=1\n");
    dprintf(fd, "auto_readiness_pid1.mode=timeout-safe-summary\n");
    dprintf(fd, "auto_readiness_pid1.source=syslog-read-all\n");
    dprintf(fd, "auto_readiness_pid1.syslog_ok=%d\n", syslog_ok);
    dprintf(fd, "auto_readiness_pid1.syslog_errno=%d\n", syslog_errno);
    dprintf(fd, "auto_readiness_pid1.syslog_len=%ld\n", (long)syslog_len);
    dprintf(fd, "auto_readiness_pid1.syslog_truncated=%d\n", (size_t)syslog_len >= sizeof(log_buf) - 1 ? 1 : 0);
    dprintf(fd, "auto_readiness_pid1.modem_trigger_seen=%d\n", modem_trigger_seen);
    dprintf(fd, "auto_readiness_pid1.provider_trigger_seen=%d\n", provider_trigger_seen);
    dprintf(fd, "auto_readiness_pid1.pcie_rc1_seen=%d\n", pcie_rc1_seen);
    dprintf(fd, "auto_readiness_pid1.mhi_seen=%d\n", mhi_seen);
    dprintf(fd, "auto_readiness_pid1.wlfw_seen=%d\n", wlfw_seen);
    dprintf(fd, "auto_readiness_pid1.icnss_qmi_seen=%d\n", icnss_qmi_seen);
    dprintf(fd, "auto_readiness_pid1.bdf_seen=%d\n", bdf_seen);
    dprintf(fd, "auto_readiness_pid1.fw_ready_seen=%d\n", fw_ready_seen);
    dprintf(fd, "auto_readiness_pid1.wlan0_seen=%d\n", wlan0_present);
    dprintf(fd, "auto_readiness_pid1.primary_checkpoint=%s\n", checkpoint);
    dprintf(fd, "auto_readiness_pid1.safety_wifi_hal_start=0\n");
    dprintf(fd, "auto_readiness_pid1.safety_scan_connect=0\n");
    dprintf(fd, "auto_readiness_pid1.safety_credentials=0\n");
    dprintf(fd, "auto_readiness_pid1.safety_dhcp_route=0\n");
    dprintf(fd, "auto_readiness_pid1.safety_external_ping=0\n");
    dprintf(fd, "auto_readiness_pid1.safety_pmic_write=0\n");
    dprintf(fd, "auto_readiness_pid1.safety_gpio_request=0\n");
    dprintf(fd, "auto_readiness_pid1.safety_direct_esoc_ioctl=0\n");
    dprintf(fd, "auto_readiness_pid1.end=1\n");
}
#endif

#if A90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH
static char v2133_fwclass_original_path[PATH_MAX];
static int v2133_fwclass_applied_by_pid1;
static int v2133_vendor_mounted_by_pid1;

static int v2133_read_fwclass_path(char *out, size_t out_size) {
    if (out == NULL || out_size == 0) {
        return -EINVAL;
    }
    if (read_trimmed_text_file("/sys/module/firmware_class/parameters/path",
                               out,
                               out_size) < 0) {
        return -errno;
    }
    return 0;
}

static int v2133_write_fwclass_path(const char *value) {
    char payload[PATH_MAX + 2];
    int path_fd;
    int payload_len;
    int write_rc;
    int close_rc;

    if (value == NULL || value[0] == '\0') {
        return -EINVAL;
    }
    payload_len = snprintf(payload, sizeof(payload), "%s\n", value);
    if (payload_len < 0 || payload_len >= (int)sizeof(payload)) {
        return -ENAMETOOLONG;
    }

    path_fd = open("/sys/module/firmware_class/parameters/path",
                   O_WRONLY | O_CLOEXEC | O_NOFOLLOW);
    if (path_fd < 0) {
        return -errno;
    }
    write_rc = write_all_checked(path_fd, payload, (size_t)payload_len);
    close_rc = close(path_fd);
    if (write_rc < 0) {
        return negative_errno_or(EIO);
    }
    if (close_rc < 0) {
        return -errno;
    }
    return 0;
}

static int v2133_stat_fwclass_asset(const char *label, const char *path, int required) {
    struct stat st;
    int saved_errno;

    if (lstat(path, &st) == 0) {
        (void)v1393_append_wifi_test_log("fwclass_vendor_path asset label=%s path=%s mode=0%o size=%lld required=%d present=1\n",
                                        label,
                                        path,
                                        (unsigned int)(st.st_mode & 07777),
                                        (long long)st.st_size,
                                        required);
        return 0;
    }

    saved_errno = errno != 0 ? errno : EIO;
    (void)v1393_append_wifi_test_log("fwclass_vendor_path asset label=%s path=%s required=%d present=0 errno=%d error=%s\n",
                                    label,
                                    path,
                                    required,
                                    saved_errno,
                                    strerror(saved_errno));
    return required ? -saved_errno : 0;
}

static void v2133_restore_fwclass_vendor_path(const char *phase) {
    char readback[PATH_MAX] = "";
    int restore_rc = 0;
    int read_rc = 0;
    int unmount_rc = 0;
    int unmount_errno = 0;

    (void)v1393_append_wifi_test_log("fwclass_vendor_path restore phase=%s begin=1 applied=%d mounted_by_pid1=%d original=%s\n",
                                    phase != NULL ? phase : "unknown",
                                    v2133_fwclass_applied_by_pid1,
                                    v2133_vendor_mounted_by_pid1,
                                    v2133_fwclass_original_path);
    if (v2133_fwclass_applied_by_pid1) {
        restore_rc = v2133_write_fwclass_path(v2133_fwclass_original_path);
        read_rc = v2133_read_fwclass_path(readback, sizeof(readback));
        (void)v1393_append_wifi_test_log("fwclass_vendor_path restore phase=%s write_rc=%d read_rc=%d readback=%s match=%d\n",
                                        phase != NULL ? phase : "unknown",
                                        restore_rc,
                                        read_rc,
                                        readback,
                                        read_rc == 0 && strcmp(readback, v2133_fwclass_original_path) == 0 ? 1 : 0);
        v2133_fwclass_applied_by_pid1 = 0;
    }

    if (v2133_vendor_mounted_by_pid1) {
        unmount_rc = umount2("/mnt/vendor", MNT_DETACH);
        if (unmount_rc < 0) {
            unmount_errno = errno != 0 ? errno : EIO;
        }
        (void)v1393_append_wifi_test_log("fwclass_vendor_path restore phase=%s umount_rc=%d errno=%d error=%s\n",
                                        phase != NULL ? phase : "unknown",
                                        unmount_rc,
                                        unmount_errno,
                                        unmount_errno != 0 ? strerror(unmount_errno) : "none");
        if (unmount_rc == 0) {
            v2133_vendor_mounted_by_pid1 = 0;
        }
    }
    (void)v1393_append_wifi_test_log("fwclass_vendor_path restore phase=%s end=1\n",
                                    phase != NULL ? phase : "unknown");
}

static int v2133_prepare_fwclass_vendor_path(void) {
    char block_path[PATH_MAX];
    char readback[PATH_MAX] = "";
    int saved_errno;
    int read_rc;
    int mount_rc;
    int write_rc;

    (void)v1393_append_wifi_test_log("fwclass_vendor_path begin=1 value=%s safety_sda29_ro_noload=1 no_sda29_write=1 no_icnss_bind_unbind=1 no_wifi_hal_scan_connect=1\n",
                                    A90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH_VALUE);

    v2133_fwclass_original_path[0] = '\0';
    v2133_fwclass_applied_by_pid1 = 0;
    v2133_vendor_mounted_by_pid1 = 0;

    read_rc = v2133_read_fwclass_path(v2133_fwclass_original_path, sizeof(v2133_fwclass_original_path));
    if (read_rc < 0) {
        (void)v1393_append_wifi_test_log("fwclass_vendor_path original_read_rc=%d errno=%d\n",
                                        read_rc,
                                        -read_rc);
        return read_rc;
    }
    (void)v1393_append_wifi_test_log("fwclass_vendor_path original=%s\n",
                                    v2133_fwclass_original_path);

    if (ensure_dir("/mnt", 0755) < 0 && errno != EEXIST) {
        saved_errno = errno != 0 ? errno : EIO;
        (void)v1393_append_wifi_test_log("fwclass_vendor_path mkdir path=/mnt errno=%d error=%s\n",
                                        saved_errno,
                                        strerror(saved_errno));
        return -saved_errno;
    }
    if (ensure_dir("/mnt/vendor", 0755) < 0 && errno != EEXIST) {
        saved_errno = errno != 0 ? errno : EIO;
        (void)v1393_append_wifi_test_log("fwclass_vendor_path mkdir path=/mnt/vendor errno=%d error=%s\n",
                                        saved_errno,
                                        strerror(saved_errno));
        return -saved_errno;
    }

    if (v641_find_block_by_partname("vendor", "sda29", block_path, sizeof(block_path)) < 0) {
        saved_errno = errno != 0 ? errno : EIO;
        (void)v1393_append_wifi_test_log("fwclass_vendor_path block_resolve part=vendor fallback=sda29 errno=%d error=%s\n",
                                        saved_errno,
                                        strerror(saved_errno));
        return -saved_errno;
    }

    mount_rc = mount(block_path,
                     "/mnt/vendor",
                     "ext4",
                     MS_RDONLY | MS_NOSUID | MS_NODEV | MS_NOEXEC,
                     "noload");
    if (mount_rc < 0) {
        saved_errno = errno != 0 ? errno : EIO;
        if (saved_errno != EBUSY) {
            (void)v1393_append_wifi_test_log("fwclass_vendor_path mount source=%s target=/mnt/vendor rc=-1 errno=%d error=%s\n",
                                            block_path,
                                            saved_errno,
                                            strerror(saved_errno));
            return -saved_errno;
        }
        (void)v1393_append_wifi_test_log("fwclass_vendor_path mount source=%s target=/mnt/vendor rc=-1 errno=%d error=%s mounted_by_pid1=0\n",
                                        block_path,
                                        saved_errno,
                                        strerror(saved_errno));
    } else {
        v2133_vendor_mounted_by_pid1 = 1;
        (void)v1393_append_wifi_test_log("fwclass_vendor_path mount source=%s target=/mnt/vendor rc=0 fstype=ext4 flags=ro,nosuid,nodev,noexec data=noload mounted_by_pid1=1\n",
                                        block_path);
    }

    if (v2133_stat_fwclass_asset("WCNSS_qcom_cfg.ini",
                                 "/mnt/vendor/firmware/wlan/qca_cld/WCNSS_qcom_cfg.ini",
                                 1) < 0 ||
        v2133_stat_fwclass_asset("bdwlan.bin",
                                 "/mnt/vendor/firmware/wlan/qca_cld/bdwlan.bin",
                                 1) < 0 ||
        v2133_stat_fwclass_asset("regdb.bin",
                                 "/mnt/vendor/firmware/wlan/qca_cld/regdb.bin",
                                 1) < 0) {
        v2133_restore_fwclass_vendor_path("prepare-asset-missing");
        return -ENOENT;
    }

    write_rc = v2133_write_fwclass_path(A90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH_VALUE);
    if (write_rc < 0) {
        (void)v1393_append_wifi_test_log("fwclass_vendor_path apply write_rc=%d errno=%d\n",
                                        write_rc,
                                        -write_rc);
        v2133_restore_fwclass_vendor_path("prepare-write-failed");
        return write_rc;
    }
    v2133_fwclass_applied_by_pid1 = 1;

    read_rc = v2133_read_fwclass_path(readback, sizeof(readback));
    (void)v1393_append_wifi_test_log("fwclass_vendor_path apply write_rc=%d read_rc=%d readback=%s match=%d\n",
                                    write_rc,
                                    read_rc,
                                    readback,
                                    read_rc == 0 && strcmp(readback, A90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH_VALUE) == 0 ? 1 : 0);
    if (read_rc < 0 || strcmp(readback, A90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH_VALUE) != 0) {
        v2133_restore_fwclass_vendor_path("prepare-readback-mismatch");
        return read_rc < 0 ? read_rc : -EIO;
    }

    klogf("<6>%s: fwclass vendor path applied value=%s\n",
          A90_WIFI_TEST_BOOT_KLOG_PREFIX,
          A90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH_VALUE);
    (void)v1393_append_wifi_test_log("fwclass_vendor_path end=1 applied=1\n");
    return 0;
}
#endif

static int v1393_wifi_test_wlan0_present(void) {
    struct stat st;

    return (lstat("/sys/class/net/wlan0", &st) == 0) ? 1 : 0;
}

static void v1393_write_wifi_test_summary(pid_t helper_pid, long spawn_ms) {
    char wchan_path[64];
    char status_path[64];
    char wchan[96] = "unreadable";
    char status[384] = "unreadable";
    struct stat st;
    long now_ms = monotonic_millis();
    int helper_alive;
    int wlan0_present;
    int fd;

    if (helper_pid > 0) {
        snprintf(wchan_path, sizeof(wchan_path), "/proc/%ld/wchan", (long)helper_pid);
        snprintf(status_path, sizeof(status_path), "/proc/%ld/status", (long)helper_pid);
        if (read_trimmed_text_file(wchan_path, wchan, sizeof(wchan)) < 0) {
            snprintf(wchan, sizeof(wchan), "errno=%d", errno != 0 ? errno : EIO);
        }
        if (read_trimmed_text_file(status_path, status, sizeof(status)) < 0) {
            snprintf(status, sizeof(status), "errno=%d", errno != 0 ? errno : EIO);
        }
    } else {
        snprintf(wchan, sizeof(wchan), "invalid-pid");
        snprintf(status, sizeof(status), "invalid-pid");
    }
    flatten_inline_text(status);

    errno = 0;
    helper_alive = (helper_pid > 0 && (kill(helper_pid, 0) == 0 || errno == EPERM)) ? 1 : 0;
    wlan0_present = v1393_wifi_test_wlan0_present();

    fd = open(A90_V1393_WIFI_TEST_SUMMARY,
              O_WRONLY | O_CREAT | O_TRUNC | O_CLOEXEC | O_NOFOLLOW,
              0600);
    if (fd < 0) {
        return;
    }
    dprintf(fd, "label=%s\n", A90_WIFI_TEST_BOOT_LABEL);
    dprintf(fd, "watch_sec=%d\n", A90_WIFI_TEST_BOOT_WATCH_SEC);
    dprintf(fd, "spawn_ms=%ld\n", spawn_ms);
    dprintf(fd, "sample_ms=%ld\n", now_ms);
    dprintf(fd, "elapsed_since_spawn_ms=%ld\n", now_ms >= spawn_ms ? now_ms - spawn_ms : -1);
    dprintf(fd, "helper_pid=%ld\n", (long)helper_pid);
    dprintf(fd, "helper_alive=%d\n", helper_alive);
    dprintf(fd, "helper_wchan=%s\n", wchan);
    dprintf(fd, "helper_status=%s\n", status);
    dprintf(fd, "wlan0_present=%d\n", wlan0_present);
    dprintf(fd, "debugfs_mount_requested=%d\n", A90_WIFI_TEST_BOOT_MOUNT_DEBUGFS);
    dprintf(fd, "firmware_mounts_requested=%d\n", A90_WIFI_TEST_BOOT_FIRMWARE_MOUNTS);
    dprintf(fd, "fwclass_vendor_path_requested=%d\n", A90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH);
#if A90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH
    {
        char fwclass_current[PATH_MAX] = "";
        int fwclass_read_rc = v2133_read_fwclass_path(fwclass_current, sizeof(fwclass_current));

        dprintf(fd, "fwclass_vendor_path_value=%s\n", A90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH_VALUE);
        dprintf(fd, "fwclass_vendor_path_original=%s\n", v2133_fwclass_original_path);
        dprintf(fd, "fwclass_vendor_path_current_read_rc=%d\n", fwclass_read_rc);
        dprintf(fd, "fwclass_vendor_path_current=%s\n", fwclass_current);
        dprintf(fd, "fwclass_vendor_path_applied_by_pid1=%d\n", v2133_fwclass_applied_by_pid1);
        dprintf(fd, "fwclass_vendor_path_vendor_mounted_by_pid1=%d\n", v2133_vendor_mounted_by_pid1);
    }
#endif
#if A90_WIFI_TEST_BOOT_MOUNT_DEBUGFS
    dprintf(fd, "debugfs_mounted_by_pid1=%d\n", v1393_wifi_test_debugfs_mounted_by_pid1);
    dprintf(fd,
            "debugfs_pci_msm_case_present=%d\n",
            lstat("/sys/kernel/debug/pci-msm/case", &st) == 0 ? 1 : 0);
#endif
    dprintf(fd, "pid1_rc1_watcher_requested=%d\n", A90_WIFI_TEST_BOOT_PID1_RC1_WATCHER);
#if A90_WIFI_TEST_BOOT_PID1_RC1_WATCHER
    {
        char watcher_result[384] = "missing";

        if (read_trimmed_text_file(A90_V1393_WIFI_TEST_RC1_WATCHER_RESULT,
                                   watcher_result,
                                   sizeof(watcher_result)) < 0) {
            snprintf(watcher_result, sizeof(watcher_result), "errno=%d", errno != 0 ? errno : EIO);
        }
        flatten_inline_text(watcher_result);
        dprintf(fd, "pid1_rc1_watcher_result=%s\n", watcher_result);
        dprintf(fd, "pid1_rc1_watcher_result_path=%s\n", A90_V1393_WIFI_TEST_RC1_WATCHER_RESULT);
    }
#endif
    dprintf(fd, "rc1_window_sampler_requested=%d\n", A90_WIFI_TEST_BOOT_RC1_WINDOW_SAMPLER);
    dprintf(fd,
            "rc1_immediate_endpoint_sampler_requested=%d\n",
            A90_WIFI_TEST_BOOT_RC1_IMMEDIATE_ENDPOINT_SAMPLER);
    dprintf(fd,
            "rc1_micro_endpoint_sampler_requested=%d\n",
            A90_WIFI_TEST_BOOT_RC1_MICRO_ENDPOINT_SAMPLER);
    dprintf(fd,
            "rc1_micro_focused_endpoint_sampler_requested=%d\n",
            A90_WIFI_TEST_BOOT_RC1_MICRO_FOCUSED_ENDPOINT_SAMPLER);
    dprintf(fd,
            "rc1_micro_batched_focused_endpoint_sampler_requested=%d\n",
            A90_WIFI_TEST_BOOT_RC1_MICRO_BATCHED_FOCUSED_ENDPOINT_SAMPLER);
    dprintf(fd,
            "rc1_micro_source_timestamped_sampler_requested=%d\n",
            A90_WIFI_TEST_BOOT_RC1_MICRO_SOURCE_TIMESTAMPED_SAMPLER);
    dprintf(fd,
            "rc1_micro_critical_fast_endpoint_sampler_requested=%d\n",
            A90_WIFI_TEST_BOOT_RC1_MICRO_CRITICAL_FAST_ENDPOINT_SAMPLER);
    dprintf(fd,
            "rc1_case_aligned_micro_endpoint_sampler_requested=%d\n",
            A90_WIFI_TEST_BOOT_RC1_CASE_ALIGNED_MICRO_ENDPOINT_SAMPLER);
    dprintf(fd,
            "provider_trigger_micro_endpoint_sampler_requested=%d\n",
            A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_MICRO_ENDPOINT_SAMPLER);
    dprintf(fd,
            "provider_trigger_tracepoint_sampler_requested=%d\n",
            A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_TRACEPOINT_SAMPLER);
    dprintf(fd,
            "provider_trigger_pil_tracepoint_sampler_requested=%d\n",
            A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_PIL_TRACEPOINT_SAMPLER);
    dprintf(fd,
            "provider_trigger_effective_level_sampler_requested=%d\n",
            A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_EFFECTIVE_LEVEL_SAMPLER);
    dprintf(fd,
            "provider_trigger_ap2mdm_hold_requested=%d\n",
            A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_AP2MDM_HOLD);
    dprintf(fd,
            "natural_mdm2ap_irq_summary_requested=%d\n",
            A90_WIFI_TEST_BOOT_NATURAL_MDM2AP_IRQ_SUMMARY);
    dprintf(fd,
            "auto_readiness_supervisor_requested=%d\n",
            A90_WIFI_TEST_BOOT_AUTO_READINESS_SUPERVISOR);
#if A90_WIFI_TEST_BOOT_AUTO_READINESS_SUPERVISOR
    dprintf(fd,
            "auto_readiness_marker=%s\n",
            A90_V1393_WIFI_TEST_RC1_WINDOW_SAMPLER_NAME);
    v1488_append_pid1_auto_readiness_summary(fd, wlan0_present);
#endif
    dprintf(fd,
            "provider_trigger_ap2mdm_hold_after_ms=%d\n",
            A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_AP2MDM_HOLD_AFTER_MS);
    dprintf(fd,
            "provider_trigger_ap2mdm_hold_ms=%d\n",
            A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_AP2MDM_HOLD_MS);
    dprintf(fd, "rc1_retry_count=%d\n", A90_WIFI_TEST_BOOT_RC1_RETRY_COUNT);
    dprintf(fd, "rc1_retry_delay_ms=%d\n", A90_WIFI_TEST_BOOT_RC1_RETRY_DELAY_MS);
#if A90_WIFI_TEST_BOOT_RC1_WINDOW_SAMPLER
    {
        char window_result[384] = "missing";

        if (read_trimmed_text_file(A90_V1393_WIFI_TEST_RC1_WINDOW_RESULT,
                                   window_result,
                                   sizeof(window_result)) < 0) {
            snprintf(window_result, sizeof(window_result), "errno=%d", errno != 0 ? errno : EIO);
        }
        flatten_inline_text(window_result);
        dprintf(fd, "rc1_window_result_head=%s\n", window_result);
        dprintf(fd, "rc1_window_result_path=%s\n", A90_V1393_WIFI_TEST_RC1_WINDOW_RESULT);
    }
#endif
    if (lstat(A90_V1393_WIFI_TEST_LOG, &st) == 0) {
        dprintf(fd, "log_size=%lld\n", (long long)st.st_size);
    } else {
        dprintf(fd, "log_size_errno=%d\n", errno != 0 ? errno : EIO);
    }
    dprintf(fd, "log_path=%s\n", A90_V1393_WIFI_TEST_LOG);
    if (lstat(A90_V1393_WIFI_TEST_HELPER_RESULT, &st) == 0) {
        dprintf(fd, "helper_result_size=%lld\n", (long long)st.st_size);
    } else {
        dprintf(fd, "helper_result_size_errno=%d\n", errno != 0 ? errno : EIO);
    }
    dprintf(fd, "helper_result_path=%s\n", A90_V1393_WIFI_TEST_HELPER_RESULT);
    close(fd);
}

static void v1393_write_wifi_test_supervised_summary(pid_t helper_pid,
                                                     long spawn_ms,
                                                     int wait_rc,
                                                     int status,
                                                     int timed_out) {
    v1393_write_wifi_test_summary(helper_pid, spawn_ms);
    {
        int wlan0_present = v1393_wifi_test_wlan0_present();
        int fd = open(A90_V1393_WIFI_TEST_SUMMARY,
                      O_WRONLY | O_APPEND | O_CLOEXEC | O_NOFOLLOW,
                      0600);
        if (fd < 0) {
            return;
        }
        dprintf(fd, "supervised=1\n");
        dprintf(fd, "supervisor_timeout_sec=%d\n", A90_WIFI_TEST_BOOT_SUPERVISOR_TIMEOUT_SEC);
        dprintf(fd, "helper_wait_rc=%d\n", wait_rc);
        dprintf(fd, "helper_timed_out=%d\n", timed_out);
        dprintf(fd, "helper_status_raw=%d\n", status);
        dprintf(fd, "baseline_ready=%d\n", wlan0_present);
        dprintf(fd,
                "helper_timeout_benign=%d\n",
                (timed_out != 0 && wlan0_present != 0) ? 1 : 0);
        dprintf(fd,
                "supervisor_result=%s\n",
                wlan0_present != 0 ? "wlan0-ready" : (timed_out != 0 ? "timeout-no-wlan0" : "helper-complete-no-wlan0"));
        if (wait_rc == 0 && WIFEXITED(status)) {
            dprintf(fd, "helper_exited=1\n");
            dprintf(fd, "helper_exit_code=%d\n", WEXITSTATUS(status));
        } else {
            dprintf(fd, "helper_exited=0\n");
        }
        if (wait_rc == 0 && WIFSIGNALED(status)) {
            dprintf(fd, "helper_signaled=1\n");
            dprintf(fd, "helper_signal=%d\n", WTERMSIG(status));
        } else {
            dprintf(fd, "helper_signaled=0\n");
        }
        close(fd);
    }
}

static int v726_read_u64_file(const char *path, unsigned long long *out) {
    char value[64];
    char *end = NULL;
    unsigned long long parsed;

    if (out == NULL) {
        return -EINVAL;
    }
    if (read_trimmed_text_file(path, value, sizeof(value)) < 0) {
        return -(errno != 0 ? errno : EIO);
    }
    errno = 0;
    parsed = strtoull(value, &end, 10);
    if (errno != 0 || end == value) {
        return -EINVAL;
    }
    *out = parsed;
    return 0;
}

static void v726_read_wifi_runtime_key(const char *key, char *out, size_t out_size) {
    FILE *fp;
    char line[192];
    size_t key_len;

    if (out_size == 0) {
        return;
    }
    out[0] = '\0';
    fp = fopen(A90_WIFI_RUNTIME_OPTIONAL_INPUT, "r");
    if (fp == NULL) {
        return;
    }
    key_len = strlen(key);
    while (fgets(line, sizeof(line), fp) != NULL) {
        size_t len;

        if (strncmp(line, key, key_len) != 0) {
            continue;
        }
        len = strlen(line);
        while (len > key_len && (line[len - 1] == '\n' || line[len - 1] == '\r')) {
            line[--len] = '\0';
        }
        snprintf(out, out_size, "%s", line + key_len);
        flatten_inline_text(out);
        fclose(fp);
        return;
    }
    fclose(fp);
}

static int v726_get_wlan0_ipv4_label(char *out, size_t out_size) {
    int fd;
    struct ifreq ifr;
    struct sockaddr_in *addr;
    const unsigned char *octets;

    if (out_size == 0) {
        return -EINVAL;
    }
    out[0] = '\0';
    fd = socket(AF_INET, SOCK_DGRAM | SOCK_CLOEXEC, 0);
    if (fd < 0) {
        return -(errno != 0 ? errno : EIO);
    }
    memset(&ifr, 0, sizeof(ifr));
    snprintf(ifr.ifr_name, sizeof(ifr.ifr_name), "wlan0");
    if (ioctl(fd, SIOCGIFADDR, &ifr) < 0) {
        int saved_errno = errno != 0 ? errno : EIO;

        close(fd);
        return -saved_errno;
    }
    close(fd);
    addr = (struct sockaddr_in *)&ifr.ifr_addr;
    octets = (const unsigned char *)&addr->sin_addr.s_addr;
    snprintf(out,
             out_size,
             "%u.%u.%u.x",
             (unsigned int)octets[0],
             (unsigned int)octets[1],
             (unsigned int)octets[2]);
    return 0;
}

static void v726_write_wifi_runtime_summary_once(unsigned long long *last_rx_bytes,
                                                 unsigned long long *last_tx_bytes,
                                                 long *last_sample_ms) {
    struct stat st;
    char operstate[32] = "missing";
    char carrier[16] = "missing";
    char mac[32] = "missing";
    char mac_tail[32] = "missing";
    char ip4_label[32] = "";
    char ssid_label[64] = "";
    char rssi_dbm[24] = "";
    char linkspeed_mbps[24] = "";
    unsigned long long rx_bytes = 0;
    unsigned long long tx_bytes = 0;
    unsigned long long rx_mbps_x10 = 0;
    unsigned long long tx_mbps_x10 = 0;
    long now_ms = monotonic_millis();
    long elapsed_ms = 0;
    int wlan0_present;
    int fd;

    wlan0_present = (lstat("/sys/class/net/wlan0", &st) == 0) ? 1 : 0;
    if (wlan0_present != 0) {
        if (read_trimmed_text_file("/sys/class/net/wlan0/operstate",
                                   operstate,
                                   sizeof(operstate)) < 0) {
            snprintf(operstate, sizeof(operstate), "unknown");
        }
        if (read_trimmed_text_file("/sys/class/net/wlan0/carrier",
                                   carrier,
                                   sizeof(carrier)) < 0) {
            snprintf(carrier, sizeof(carrier), "0");
        }
        if (read_trimmed_text_file("/sys/class/net/wlan0/address",
                                   mac,
                                   sizeof(mac)) < 0) {
            snprintf(mac, sizeof(mac), "unknown");
        }
        if (strlen(mac) >= 5) {
            snprintf(mac_tail, sizeof(mac_tail), "xx:%s", mac + strlen(mac) - 5);
        } else {
            snprintf(mac_tail, sizeof(mac_tail), "%s", mac);
        }
        (void)v726_read_u64_file("/sys/class/net/wlan0/statistics/rx_bytes", &rx_bytes);
        (void)v726_read_u64_file("/sys/class/net/wlan0/statistics/tx_bytes", &tx_bytes);
        (void)v726_get_wlan0_ipv4_label(ip4_label, sizeof(ip4_label));
    }

    v726_read_wifi_runtime_key("ssid_label=", ssid_label, sizeof(ssid_label));
    v726_read_wifi_runtime_key("rssi_dbm=", rssi_dbm, sizeof(rssi_dbm));
    v726_read_wifi_runtime_key("linkspeed_mbps=", linkspeed_mbps, sizeof(linkspeed_mbps));

    if (last_sample_ms != NULL && *last_sample_ms > 0 && now_ms > *last_sample_ms) {
        elapsed_ms = now_ms - *last_sample_ms;
    }
    if (elapsed_ms > 0 && last_rx_bytes != NULL && last_tx_bytes != NULL) {
        if (rx_bytes >= *last_rx_bytes) {
            rx_mbps_x10 = ((rx_bytes - *last_rx_bytes) * 80ULL) / ((unsigned long long)elapsed_ms * 1000ULL);
        }
        if (tx_bytes >= *last_tx_bytes) {
            tx_mbps_x10 = ((tx_bytes - *last_tx_bytes) * 80ULL) / ((unsigned long long)elapsed_ms * 1000ULL);
        }
    }
    if (last_rx_bytes != NULL) {
        *last_rx_bytes = rx_bytes;
    }
    if (last_tx_bytes != NULL) {
        *last_tx_bytes = tx_bytes;
    }
    if (last_sample_ms != NULL) {
        *last_sample_ms = now_ms;
    }

    fd = open(A90_WIFI_RUNTIME_SUMMARY_TMP,
              O_WRONLY | O_CREAT | O_TRUNC | O_CLOEXEC | O_NOFOLLOW,
              0600);
    if (fd < 0) {
        return;
    }
    dprintf(fd, "runtime_version=1\n");
    dprintf(fd, "sample_ms=%ld\n", now_ms);
    dprintf(fd, "wlan0_present=%d\n", wlan0_present);
    dprintf(fd, "operstate=%s\n", operstate);
    dprintf(fd, "carrier=%s\n", carrier);
    dprintf(fd, "mac_label=%s\n", mac_tail);
    dprintf(fd, "ip4_label=%s\n", ip4_label[0] != '\0' ? ip4_label : "none");
    dprintf(fd, "ip4_masked=1\n");
    dprintf(fd, "ssid_label=%s\n", ssid_label);
    dprintf(fd, "rssi_dbm=%s\n", rssi_dbm);
    dprintf(fd, "linkspeed_mbps=%s\n", linkspeed_mbps);
    dprintf(fd, "rx_bytes=%llu\n", rx_bytes);
    dprintf(fd, "tx_bytes=%llu\n", tx_bytes);
    dprintf(fd, "rx_mb=%llu\n", rx_bytes / 1048576ULL);
    dprintf(fd, "tx_mb=%llu\n", tx_bytes / 1048576ULL);
    dprintf(fd, "rx_mbps=%llu.%llu\n", rx_mbps_x10 / 10ULL, rx_mbps_x10 % 10ULL);
    dprintf(fd, "tx_mbps=%llu.%llu\n", tx_mbps_x10 / 10ULL, tx_mbps_x10 % 10ULL);
    close(fd);
    (void)rename(A90_WIFI_RUNTIME_SUMMARY_TMP, A90_WIFI_RUNTIME_SUMMARY);
}

static void v726_wifi_runtime_summary_child(void) {
    unsigned long long last_rx_bytes = 0;
    unsigned long long last_tx_bytes = 0;
    long last_sample_ms = 0;
    int i;

    signal(SIGHUP, SIG_IGN);
    signal(SIGPIPE, SIG_IGN);
    setsid();
    for (i = 0; i < 43200; ++i) {
        v726_write_wifi_runtime_summary_once(&last_rx_bytes, &last_tx_bytes, &last_sample_ms);
        sleep(2);
    }
    _exit(0);
}

static int v726_start_wifi_runtime_summary_once(void) {
    static int started;
    pid_t pid;
    char pid_text[32];

    if (started != 0) {
        return 0;
    }
    started = 1;
    pid = fork();
    if (pid < 0) {
        int saved_errno = errno != 0 ? errno : EIO;

        a90_logf("wifi-v726", "runtime summary spawn failed errno=%d error=%s",
                 saved_errno,
                 strerror(saved_errno));
        klogf("<6>A90v726: wifi runtime summary spawn failed errno=%d\n", saved_errno);
        return -saved_errno;
    }
    if (pid == 0) {
        v726_wifi_runtime_summary_child();
    }
    snprintf(pid_text, sizeof(pid_text), "%ld\n", (long)pid);
    (void)v724_write_private_file(A90_WIFI_RUNTIME_PID, pid_text);
    a90_logf("wifi-v726", "runtime summary spawned pid=%ld path=%s",
             (long)pid,
             A90_WIFI_RUNTIME_SUMMARY);
    klogf("<6>A90v726: wifi runtime summary spawned pid=%ld\n", (long)pid);
    return 0;
}

#if !A90_WIFI_TEST_BOOT_SUPERVISE_HELPER
static int v1393_spawn_wifi_test_summary_watcher(pid_t helper_pid, long spawn_ms, pid_t *watcher_out) {
    pid_t pid;

    pid = fork();
    if (pid < 0) {
        return -errno;
    }
    if (pid == 0) {
        signal(SIGHUP, SIG_IGN);
        signal(SIGPIPE, SIG_IGN);
        setsid();
        sleep(A90_WIFI_TEST_BOOT_WATCH_SEC);
        v1393_write_wifi_test_summary(helper_pid, spawn_ms);
        _exit(0);
    }
    if (watcher_out != NULL) {
        *watcher_out = pid;
    }
    return 0;
}
#endif

static int v1393_wait_for_wifi_test_helper(pid_t helper_pid, int *status_out, int *timed_out_out) {
    long deadline_ms = monotonic_millis() + (long)A90_WIFI_TEST_BOOT_SUPERVISOR_TIMEOUT_SEC * 1000L;
    int status = 0;

    if (timed_out_out != NULL) {
        *timed_out_out = 0;
    }
    while (monotonic_millis() < deadline_ms) {
        pid_t got = waitpid(helper_pid, &status, WNOHANG);

        if (got == helper_pid) {
            if (status_out != NULL) {
                *status_out = status;
            }
            return 0;
        }
        if (got < 0) {
            int saved_errno = errno;
            if (status_out != NULL) {
                *status_out = status;
            }
            return -saved_errno;
        }
        usleep(100000);
    }

    if (timed_out_out != NULL) {
        *timed_out_out = 1;
    }
    (void)kill(-helper_pid, SIGTERM);
    (void)kill(helper_pid, SIGTERM);
    usleep(500000);
    if (waitpid(helper_pid, &status, WNOHANG) != helper_pid) {
        (void)kill(-helper_pid, SIGKILL);
        (void)kill(helper_pid, SIGKILL);
        if (waitpid(helper_pid, &status, 0) < 0 && errno != ECHILD) {
            int saved_errno = errno;
            if (status_out != NULL) {
                *status_out = status;
            }
            return -saved_errno;
        }
    }
    if (status_out != NULL) {
        *status_out = status;
    }
    return -ETIMEDOUT;
}

static int v1393_spawn_wifi_test_boot_helper(pid_t *pid_out) {
    static char *const envp[] = {
        "PATH=/bin:/cache/bin:/system/bin:/vendor/bin",
        "HOME=/",
        "TERM=vt100",
        NULL
    };
    static char *const argv[] = {
        A90_V1393_WIFI_TEST_HELPER,
        "--system-root",
        "/mnt/system/system",
        "--vendor-block",
        "/dev/block/sda29",
        "--vendor-fstype",
        "ext4",
        "--mode",
        A90_V1393_WIFI_TEST_MODE,
#if A90_WIFI_TEST_BOOT_ANDROID_SERVICE_WINDOW_PER_MGR_EARLY_EXIT_TRACE
        "--capture-mode",
        "ptrace-lite",
#endif
        "--result-output-path",
        A90_V1393_WIFI_TEST_HELPER_RESULT,
        "--timeout-sec",
        A90_V1393_WIFI_TEST_TIMEOUT_SEC,
        "--property-root",
        A90_V1393_WIFI_TEST_PROPERTY_ROOT,
        "--null-device-mode",
        "dev-null",
        "--android-selinux-context-mode",
        "service-defaults",
        "--linkerconfig-mode",
        "copy-real",
        "--linkerconfig-source",
        A90_V1393_WIFI_TEST_REAL_LD_CONFIG,
        "--apex-libraries-source",
        A90_V1393_WIFI_TEST_REAL_APEX_LIBRARIES,
        "--vndk-apex-alias-mode",
        "v30-to-system-ext-v30",
#if A90_WIFI_TEST_BOOT_WLAN_PD_CNSS_OUTPUT_VISIBILITY
        "--allow-wifi-companion-start-only",
        "--allow-cnss-start-only",
        "--allow-wlan-pd-cnss-output-visibility",
#if !A90_WIFI_TEST_BOOT_LIGHT_FIRMWARE_TRACE
        "--allow-qrtr-ns-readback",
        "--allow-servloc-domain-list-probe",
        "--allow-service-notifier-listener-probe",
        "--qrtr-readback-matrix",
        "wlfw:69:0,1",
#endif
#elif A90_WIFI_TEST_BOOT_WLAN_PD_PM_SERVICE_WINDOW_TRIGGER
        "--allow-wifi-companion-start-only",
        "--allow-cnss-start-only",
        "--allow-service-manager-start-only",
        "--allow-wlan-pd-pm-service-window-trigger",
#if !A90_WIFI_TEST_BOOT_LIGHT_FIRMWARE_TRACE
        "--allow-qrtr-ns-readback",
        "--allow-servloc-domain-list-probe",
        "--allow-service-notifier-listener-probe",
        "--qrtr-readback-matrix",
        "wlfw:69:0,1",
#endif
#elif A90_WIFI_TEST_BOOT_WLAN_PD_SERVICE_OBJECT_VISIBLE_TRIGGER || A90_WIFI_TEST_BOOT_WLAN_PD_SERVICE_OBJECT_DEVNODE_PROJECTION_TRIGGER
        "--allow-wifi-companion-start-only",
        "--allow-cnss-start-only",
        "--allow-service-manager-start-only",
        "--allow-wlan-pd-service-object-visible-trigger",
#if A90_WIFI_TEST_BOOT_PRIVATE_CNSS_SDX50M
        "--pm-observer-private-cnss-daemon-sdx50m",
        "--private-cnss-daemon-path",
        A90_V1393_WIFI_TEST_PRIVATE_CNSS,
#endif
#if !A90_WIFI_TEST_BOOT_LIGHT_FIRMWARE_TRACE
        "--allow-qrtr-ns-readback",
        "--allow-servloc-domain-list-probe",
        "--allow-service-notifier-listener-probe",
        "--qrtr-readback-matrix",
        "wlfw:69:0,1",
#endif
#elif A90_WIFI_TEST_BOOT_WLAN_PD_TIMESTAMPED_OBSERVER || A90_WIFI_TEST_BOOT_WLAN_PD_SERVICE_WINDOW_TRIGGER
        "--allow-wifi-companion-start-only",
        "--allow-cnss-start-only",
        "--allow-service-manager-start-only",
        "--allow-wlan-pd-service-window-trigger",
#if !A90_WIFI_TEST_BOOT_LIGHT_FIRMWARE_TRACE
        "--allow-qrtr-ns-readback",
        "--allow-servloc-domain-list-probe",
        "--allow-service-notifier-listener-probe",
        "--qrtr-readback-matrix",
        "wlfw:69:0,1",
#endif
#elif A90_WIFI_TEST_BOOT_WLAN_PD_FIRMWARE_SERVE_GATE
        "--allow-wifi-companion-start-only",
        "--allow-cnss-start-only",
#if A90_WIFI_TEST_BOOT_PRIVATE_CNSS_SDX50M
        "--pm-observer-private-cnss-daemon-sdx50m",
        "--private-cnss-daemon-path",
        A90_V1393_WIFI_TEST_PRIVATE_CNSS,
#endif
#if !A90_WIFI_TEST_BOOT_LIGHT_FIRMWARE_TRACE
        "--allow-qrtr-ns-readback",
        "--allow-servloc-domain-list-probe",
        "--allow-service-notifier-listener-probe",
        "--qrtr-readback-matrix",
        "wlfw:69:0,1",
#endif
#elif A90_WIFI_TEST_BOOT_ANDROID_SERVICE_WINDOW
        "--allow-android-wifi-service-window",
#if A90_WIFI_TEST_BOOT_ANDROID_SERVICE_WINDOW_SUBSYS_TRIGGER_CAPTURE
        "--allow-android-wifi-service-window-subsys-trigger-capture",
#if A90_WIFI_TEST_BOOT_ANDROID_SERVICE_WINDOW_PM_PROXY_CONTRACT
        "--allow-android-wifi-service-window-pm-proxy-contract",
#if A90_WIFI_TEST_BOOT_ANDROID_SERVICE_WINDOW_LATE_PER_PROXY_ONLY
        "--allow-android-wifi-service-window-late-per-proxy-only",
#if A90_WIFI_TEST_BOOT_ANDROID_SERVICE_WINDOW_PM_FIRST_ROUTE
        "--allow-android-wifi-service-window-pm-first-route",
#endif
#if A90_WIFI_TEST_BOOT_ANDROID_SERVICE_WINDOW_PM_FIRST_LATE_PER_PROXY_ROUTE
        "--allow-android-wifi-service-window-pm-first-late-per-proxy-route",
#endif
#if A90_WIFI_TEST_BOOT_ANDROID_SERVICE_WINDOW_PPH_MODEM_FD_GATE
        "--allow-android-wifi-service-window-pph-modem-fd-gate",
#endif
#if A90_WIFI_TEST_BOOT_ANDROID_SERVICE_WINDOW_PER_MGR_STARTUP_TRACE
        "--allow-android-wifi-service-window-per-mgr-startup-trace",
#if A90_WIFI_TEST_BOOT_ANDROID_SERVICE_WINDOW_PER_MGR_EARLY_EXIT_TRACE
        "--allow-android-wifi-service-window-per-mgr-early-exit-trace",
#endif
#if A90_WIFI_TEST_BOOT_ANDROID_SERVICE_WINDOW_PER_MGR_NONSTOP_CONTEXT_TRACE
        "--allow-android-wifi-service-window-per-mgr-nonstop-context-trace",
#endif
#if A90_WIFI_TEST_BOOT_ANDROID_SERVICE_WINDOW_PER_MGR_SYSTEM_INFO_SURFACE
        "--allow-android-wifi-service-window-per-mgr-system-info-surface",
#endif
#endif
#endif
#endif
#endif
#else
        "--allow-pm-service-trigger-observer",
        "--pm-observer-continue-after-provider",
        "--pm-observer-start-cnss-after-provider",
        "--allow-post-pm-mdm-helper-esoc-observer",
        "--pm-observer-start-mdm-helper-after-cnss",
        "--allow-post-pm-mdm-helper-lower-trace",
        "--pm-observer-zero-delay-per-mgr-probe",
        "--pm-observer-load-precompiled-policy",
        "--pm-observer-start-mdm-helper-before-cnss",
        "--pm-observer-set-mdm3-restart-level-related",
        "--pm-observer-set-mdm-helper-selinux-context",
        "--pm-observer-private-firmware-mounts",
        "--pm-observer-per-proxy-pph-delta-ms",
        "20000",
        "--pm-observer-mknod-esoc-dev-node-before-cnss",
        "--pm-observer-private-cnss-daemon-sdx50m",
        "--pm-observer-start-cnss-before-per-proxy",
        "--pm-observer-start-per-proxy-after-mdm-helper-esoc-fd",
        "--pm-observer-late-per-proxy-response-sampler",
        "--pm-observer-late-per-proxy-mdm2ap-errfatal-pcie-timing-sampler",
        "--private-cnss-daemon-path",
        A90_V1393_WIFI_TEST_PRIVATE_CNSS,
        "--pm-observer-current-route-cnss-wlfw-precondition-summary",
#if A90_WIFI_TEST_BOOT_AUTO_READINESS_SUPERVISOR
        "--pm-observer-auto-readiness-summary",
#endif
#if !A90_WIFI_TEST_BOOT_PID1_RC1_WATCHER && !A90_WIFI_TEST_BOOT_AUTO_READINESS_SUPERVISOR
        "--pm-observer-early-powerup-corrected-rc1-enumerate",
#endif
#endif
#if A90_WIFI_TEST_BOOT_PRIVATE_CNSS_SDX50M
        "--pm-observer-private-cnss-daemon-sdx50m",
        "--private-cnss-daemon-path",
        A90_V1393_WIFI_TEST_PRIVATE_CNSS,
#endif
        NULL
    };
    struct a90_run_config config = {
        .tag = "wifi-v1393-test-boot",
        .argv = argv,
        .envp = envp,
        .stdio_mode = A90_RUN_STDIO_LOG_APPEND,
        .log_path = A90_V1393_WIFI_TEST_LOG,
        .setsid = true,
        .ignore_hup_pipe = true,
        .kill_process_group = true,
        .cancelable = false,
        .timeout_ms = 0,
        .stop_timeout_ms = 1000,
    };

    return a90_run_spawn(&config, pid_out);
}

static void v1393_wifi_test_supervisor_child(void) {
    pid_t helper_pid = -1;
    long spawn_ms = monotonic_millis();
    int status = 0;
    int timed_out = 0;
    int rc;
    char pid_text[32];

    rc = v1393_spawn_wifi_test_boot_helper(&helper_pid);
    if (rc < 0) {
#if A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_TRACEPOINT_SAMPLER
        v1393_provider_tracepoint_disarm();
#endif
#if A90_WIFI_TEST_BOOT_MOUNT_DEBUGFS
        {
#if A90_WIFI_TEST_BOOT_PCIE1_CLOCK_VOTE_PROOF && !A90_WIFI_TEST_BOOT_PCIE1_CLOCK_VOTE_ASYNC
            int clock_cleanup_rc = v1664_pcie1_clock_vote_cleanup(v1664_pcie1_clock_vote_start_ms);
            (void)v1393_append_wifi_test_log("supervisor clock vote cleanup after spawn failure rc=%d\n",
                                            clock_cleanup_rc);
#endif
            int debugfs_cleanup_rc = v1393_cleanup_wifi_test_debugfs();
            (void)v1393_append_wifi_test_log("supervisor debugfs cleanup after spawn failure rc=%d\n",
                                            debugfs_cleanup_rc);
        }
#endif
        (void)v1393_append_wifi_test_log("supervisor helper spawn failed rc=%d errno=%d error=%s\n",
                                        rc,
                                        -rc,
                                        strerror(-rc));
#if A90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH
        v2133_restore_fwclass_vendor_path("supervisor-helper-spawn-failure");
#endif
        v1393_write_wifi_test_supervised_summary(helper_pid, spawn_ms, rc, status, 0);
        _exit(1);
    }

    snprintf(pid_text, sizeof(pid_text), "%ld\n", (long)helper_pid);
    (void)v724_write_private_file(A90_V1393_WIFI_TEST_PID, pid_text);
    (void)v1393_append_wifi_test_log("supervisor spawned helper pid=%ld label=%s mode=%s timeout_sec=%d\n",
                                    (long)helper_pid,
                                    A90_WIFI_TEST_BOOT_LABEL,
                                    A90_V1393_WIFI_TEST_MODE,
                                    A90_WIFI_TEST_BOOT_SUPERVISOR_TIMEOUT_SEC);
    rc = v1393_wait_for_wifi_test_helper(helper_pid, &status, &timed_out);
    (void)v1393_append_wifi_test_log("supervisor helper done pid=%ld wait_rc=%d status=%d timed_out=%d\n",
                                    (long)helper_pid,
                                    rc,
                                    status,
                                    timed_out);
#if A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_TRACEPOINT_SAMPLER
    v1393_provider_tracepoint_disarm();
#endif
#if A90_WIFI_TEST_BOOT_MOUNT_DEBUGFS
    {
#if A90_WIFI_TEST_BOOT_PCIE1_CLOCK_VOTE_PROOF && !A90_WIFI_TEST_BOOT_PCIE1_CLOCK_VOTE_ASYNC
        int clock_cleanup_rc = v1664_pcie1_clock_vote_cleanup(v1664_pcie1_clock_vote_start_ms);
        (void)v1393_append_wifi_test_log("supervisor clock vote cleanup rc=%d\n",
                                        clock_cleanup_rc);
#endif
        int debugfs_cleanup_rc = v1393_cleanup_wifi_test_debugfs();
        (void)v1393_append_wifi_test_log("supervisor debugfs cleanup rc=%d\n",
                                        debugfs_cleanup_rc);
    }
#endif
#if A90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH
    v2133_restore_fwclass_vendor_path("supervisor-complete");
#endif
    v1393_write_wifi_test_supervised_summary(helper_pid, spawn_ms, rc, status, timed_out);
    _exit(rc == 0 ? 0 : 1);
}

static int v1393_spawn_wifi_test_supervisor(pid_t *pid_out) {
    pid_t pid;

    pid = fork();
    if (pid < 0) {
        return -errno;
    }
    if (pid == 0) {
        signal(SIGHUP, SIG_IGN);
        signal(SIGPIPE, SIG_IGN);
        setsid();
        v1393_wifi_test_supervisor_child();
        _exit(1);
    }
    if (pid_out != NULL) {
        *pid_out = pid;
    }
    return 0;
}

static void v1393_run_wifi_test_boot_once(void) {
    struct stat st;
    pid_t pid = -1;
#if !A90_WIFI_TEST_BOOT_SUPERVISE_HELPER
    pid_t watcher_pid = -1;
#endif
    int rc;
    char pid_text[32];
#if !A90_WIFI_TEST_BOOT_SUPERVISE_HELPER
    long spawn_ms;
#endif

    if (stat(A90_V1393_WIFI_TEST_DISABLE, &st) == 0) {
        a90_logf("wifi-v1393", "test boot disabled by %s", A90_V1393_WIFI_TEST_DISABLE);
        a90_timeline_record(0, 0, "wifi-v1393-test-boot", "disabled by flag");
        klogf("<6>A90v1393: wifi test boot disabled by flag\n");
        return;
    }

    rc = v1393_reset_wifi_test_log();
    if (rc < 0) {
        a90_logf("wifi-v1393", "log reset failed rc=%d errno=%d error=%s",
                 rc,
                 -rc,
                 strerror(-rc));
        klogf("<6>%s: wifi test boot log reset failed rc=%d\n",
              A90_WIFI_TEST_BOOT_KLOG_PREFIX,
              rc);
    }
    (void)v724_write_private_file(A90_V1393_WIFI_TEST_SUMMARY, "state=armed\n");

    boot_splash_set_line(5, "[ WIFI   ] %s TEST BOOT", A90_WIFI_TEST_BOOT_LABEL);
    boot_auto_frame();
    a90_logf("wifi-v1393", "test boot armed helper=%s timeout_sec=%s",
             A90_V1393_WIFI_TEST_HELPER,
             A90_V1393_WIFI_TEST_TIMEOUT_SEC);
    a90_timeline_record(0, 0, "wifi-v1393-test-boot", "armed");
    klogf("<6>%s: wifi test boot armed\n", A90_WIFI_TEST_BOOT_KLOG_PREFIX);
    (void)v1393_append_wifi_test_log("armed ms=%ld label=%s mode=%s timeout_sec=%s\n",
                                    monotonic_millis(),
                                    A90_WIFI_TEST_BOOT_LABEL,
                                    A90_V1393_WIFI_TEST_MODE,
                                    A90_V1393_WIFI_TEST_TIMEOUT_SEC);

    if (stat(A90_V1393_WIFI_TEST_HELPER, &st) < 0 || !S_ISREG(st.st_mode)) {
        int saved_errno = errno != 0 ? errno : ENOENT;

        a90_logf("wifi-v1393", "helper missing path=%s errno=%d error=%s",
                 A90_V1393_WIFI_TEST_HELPER,
                 saved_errno,
                 strerror(saved_errno));
        a90_timeline_record(-saved_errno, saved_errno, "wifi-v1393-test-boot", "helper missing");
        klogf("<6>%s: wifi test boot helper missing\n", A90_WIFI_TEST_BOOT_KLOG_PREFIX);
        (void)v1393_append_wifi_test_log("helper missing path=%s errno=%d error=%s\n",
                                        A90_V1393_WIFI_TEST_HELPER,
                                        saved_errno,
                                        strerror(saved_errno));
        return;
    }

    if (prepare_android_layout(false) < 0) {
        int saved_errno = errno != 0 ? errno : EIO;

        a90_logf("wifi-v1393", "android layout failed errno=%d error=%s",
                 saved_errno,
                 strerror(saved_errno));
        a90_timeline_record(-saved_errno, saved_errno, "wifi-v1393-test-boot", "android layout failed");
        klogf("<6>%s: wifi test boot android layout failed rc=-%d\n",
              A90_WIFI_TEST_BOOT_KLOG_PREFIX,
              saved_errno);
        (void)v1393_append_wifi_test_log("android layout failed errno=%d error=%s\n",
                                        saved_errno,
                                        strerror(saved_errno));
        return;
    }

    rc = v724_prepare_selinuxfs_surface();
    if (rc < 0) {
        int saved_errno = -rc;

        if (saved_errno <= 0) {
            saved_errno = EIO;
        }
        a90_logf("wifi-v1393", "selinuxfs failed rc=%d errno=%d error=%s",
                 rc,
                 saved_errno,
                 strerror(saved_errno));
        a90_timeline_record(rc, saved_errno, "wifi-v1393-test-boot", "selinuxfs failed");
        klogf("<6>%s: wifi test boot selinuxfs failed rc=%d\n",
              A90_WIFI_TEST_BOOT_KLOG_PREFIX,
              rc);
        (void)v1393_append_wifi_test_log("selinuxfs failed rc=%d errno=%d error=%s\n",
                                        rc,
                                        saved_errno,
                                        strerror(saved_errno));
        return;
    }

#if A90_WIFI_TEST_BOOT_FIRMWARE_MOUNTS
    rc = v641_prepare_firmware_mounts();
    (void)v1393_append_wifi_test_log("firmware mounts prepare rc=%d\n", rc);
    if (rc < 0) {
        int saved_errno = -rc;

        if (saved_errno <= 0) {
            saved_errno = EIO;
        }
        a90_logf("wifi-v1393", "firmware mounts failed rc=%d errno=%d error=%s",
                 rc,
                 saved_errno,
                 strerror(saved_errno));
        a90_timeline_record(rc, saved_errno, "wifi-v1393-test-boot", "firmware mounts failed");
        klogf("<6>%s: wifi test boot firmware mounts failed rc=%d\n",
              A90_WIFI_TEST_BOOT_KLOG_PREFIX,
              rc);
        (void)v1393_append_wifi_test_log("firmware mounts failed rc=%d errno=%d error=%s\n",
                                        rc,
                                        saved_errno,
                                        strerror(saved_errno));
        return;
    }
#endif

#if A90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH
    rc = v2133_prepare_fwclass_vendor_path();
    (void)v1393_append_wifi_test_log("fwclass vendor path prepare rc=%d\n", rc);
    if (rc < 0) {
        int saved_errno = -rc;

        if (saved_errno <= 0) {
            saved_errno = EIO;
        }
        a90_logf("wifi-v1393", "fwclass vendor path failed rc=%d errno=%d error=%s",
                 rc,
                 saved_errno,
                 strerror(saved_errno));
        a90_timeline_record(rc, saved_errno, "wifi-v1393-test-boot", "fwclass vendor path failed");
        klogf("<6>%s: wifi test boot fwclass vendor path failed rc=%d\n",
              A90_WIFI_TEST_BOOT_KLOG_PREFIX,
              rc);
        return;
    }
#endif

#if A90_WIFI_TEST_BOOT_MOUNT_DEBUGFS
    rc = v1393_prepare_wifi_test_debugfs();
    (void)v1393_append_wifi_test_log("debugfs prepare rc=%d mounted_by_pid1=%d\n",
                                    rc,
                                    v1393_wifi_test_debugfs_mounted_by_pid1);
    if (rc < 0) {
        int saved_errno = -rc;

        if (saved_errno <= 0) {
            saved_errno = EIO;
        }
        a90_logf("wifi-v1393", "debugfs prepare failed rc=%d errno=%d error=%s",
                 rc,
                 saved_errno,
                 strerror(saved_errno));
        a90_timeline_record(rc, saved_errno, "wifi-v1393-test-boot", "debugfs prepare failed");
        klogf("<6>%s: wifi test boot debugfs prepare failed rc=%d\n",
              A90_WIFI_TEST_BOOT_KLOG_PREFIX,
              rc);
#if A90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH
        v2133_restore_fwclass_vendor_path("debugfs-prepare-failure");
#endif
#if A90_WIFI_TEST_BOOT_FWCLASS_VENDOR_PATH
        v2133_restore_fwclass_vendor_path("supervisor-spawn-failure");
#endif
        return;
    }
#endif

#if A90_WIFI_TEST_BOOT_PCIE1_CLOCK_VOTE_PROOF
#if A90_WIFI_TEST_BOOT_PCIE1_CLOCK_VOTE_ASYNC
    {
        pid_t clock_vote_pid = -1;

        rc = v1664_spawn_pcie1_clock_vote_child(&clock_vote_pid);
        (void)v1393_append_wifi_test_log("pcie1 clock vote async spawn rc=%d pid=%ld result=%s\n",
                                        rc,
                                        (long)clock_vote_pid,
                                        A90_WIFI_TEST_BOOT_PCIE1_CLOCK_VOTE_RESULT);
        if (rc < 0) {
            a90_logf("wifi-v1393", "pcie1 clock vote async spawn failed rc=%d errno=%d error=%s",
                     rc,
                     -rc,
                     strerror(-rc));
            a90_timeline_record(rc, -rc, "wifi-v1393-test-boot", "pcie1 clock vote async spawn failed");
            klogf("<6>%s: pcie1 clock vote async spawn failed rc=%d\n",
                  A90_WIFI_TEST_BOOT_KLOG_PREFIX,
                  rc);
        }
    }
#else
    {
        long vote_start_ms = monotonic_millis();

        rc = v1664_pcie1_clock_vote_begin(vote_start_ms);
        (void)v1393_append_wifi_test_log("pcie1 clock vote begin rc=%d\n", rc);
        if (rc < 0) {
            a90_logf("wifi-v1393", "pcie1 clock vote begin failed rc=%d errno=%d error=%s",
                     rc,
                     -rc,
                     strerror(-rc));
            a90_timeline_record(rc, -rc, "wifi-v1393-test-boot", "pcie1 clock vote begin failed");
            klogf("<6>%s: pcie1 clock vote begin failed rc=%d\n",
                  A90_WIFI_TEST_BOOT_KLOG_PREFIX,
                  rc);
        } else {
            a90_logf("wifi-v1393", "pcie1 clock vote begin ok");
            a90_timeline_record(0, 0, "wifi-v1393-test-boot", "pcie1 clock vote begin ok");
            klogf("<6>%s: pcie1 clock vote begin ok\n", A90_WIFI_TEST_BOOT_KLOG_PREFIX);
        }
    }
#endif
#endif

#if A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_TRACEPOINT_SAMPLER
    v1393_provider_tracepoint_arm();
#endif

#if A90_WIFI_TEST_BOOT_PID1_RC1_WATCHER
    {
        pid_t rc1_watcher_pid = -1;

        rc = v1393_spawn_pid1_rc1_watcher(&rc1_watcher_pid);
        if (rc < 0) {
            int saved_errno = -rc;

            if (saved_errno <= 0) {
                saved_errno = EIO;
            }
            a90_logf("wifi-v1393", "pid1 rc1 watcher spawn failed rc=%d errno=%d error=%s",
                     rc,
                     saved_errno,
                     strerror(saved_errno));
            a90_timeline_record(rc, saved_errno, "wifi-v1393-test-boot", "pid1 rc1 watcher spawn failed");
            klogf("<6>%s: pid1 rc1 watcher spawn failed rc=%d\n",
                  A90_WIFI_TEST_BOOT_KLOG_PREFIX,
                  rc);
            (void)v1393_append_wifi_test_log("pid1 rc1 watcher spawn failed rc=%d errno=%d error=%s\n",
                                            rc,
                                            saved_errno,
                                            strerror(saved_errno));
        } else {
            a90_logf("wifi-v1393", "pid1 rc1 watcher spawned pid=%ld timeout_sec=%d",
                     (long)rc1_watcher_pid,
                     A90_WIFI_TEST_BOOT_RC1_WATCHER_TIMEOUT_SEC);
            a90_timeline_record(0,
                                0,
                                "wifi-v1393-test-boot",
                                "pid1 rc1 watcher spawned pid=%ld",
                                (long)rc1_watcher_pid);
            klogf("<6>%s: pid1 rc1 watcher spawned pid=%ld\n",
                  A90_WIFI_TEST_BOOT_KLOG_PREFIX,
                  (long)rc1_watcher_pid);
            (void)v1393_append_wifi_test_log("pid1 rc1 watcher pid=%ld timeout_sec=%d result=%s\n",
                                            (long)rc1_watcher_pid,
                                            A90_WIFI_TEST_BOOT_RC1_WATCHER_TIMEOUT_SEC,
                                            A90_V1393_WIFI_TEST_RC1_WATCHER_RESULT);
        }
    }
#endif

#if A90_WIFI_TEST_BOOT_SUPERVISE_HELPER
    rc = v1393_spawn_wifi_test_supervisor(&pid);
    if (rc < 0) {
        int saved_errno = -rc;

        if (saved_errno <= 0) {
            saved_errno = EIO;
        }
        a90_logf("wifi-v1393", "supervisor spawn failed rc=%d errno=%d error=%s",
                 rc,
                 saved_errno,
                 strerror(saved_errno));
        a90_timeline_record(rc, saved_errno, "wifi-v1393-test-boot", "supervisor spawn failed");
        klogf("<6>%s: wifi test boot supervisor spawn failed rc=%d\n",
              A90_WIFI_TEST_BOOT_KLOG_PREFIX,
              rc);
        (void)v1393_append_wifi_test_log("supervisor spawn failed rc=%d errno=%d error=%s\n",
                                        rc,
                                        saved_errno,
                                        strerror(saved_errno));
#if A90_WIFI_TEST_BOOT_MOUNT_DEBUGFS
        {
#if A90_WIFI_TEST_BOOT_PCIE1_CLOCK_VOTE_PROOF && !A90_WIFI_TEST_BOOT_PCIE1_CLOCK_VOTE_ASYNC
            int clock_cleanup_rc = v1664_pcie1_clock_vote_cleanup(v1664_pcie1_clock_vote_start_ms);
            (void)v1393_append_wifi_test_log("clock vote cleanup after supervisor spawn failure rc=%d\n",
                                            clock_cleanup_rc);
#endif
            int debugfs_cleanup_rc = v1393_cleanup_wifi_test_debugfs();
            (void)v1393_append_wifi_test_log("debugfs cleanup after supervisor spawn failure rc=%d\n",
                                            debugfs_cleanup_rc);
        }
#endif
        return;
    }

    snprintf(pid_text, sizeof(pid_text), "%ld\n", (long)pid);
    (void)v724_write_private_file(A90_V1393_WIFI_TEST_WATCHER_PID, pid_text);
    a90_logf("wifi-v1393", "supervisor spawned pid=%ld mode=%s",
             (long)pid,
             A90_V1393_WIFI_TEST_MODE);
    a90_timeline_record(0,
                        0,
                        "wifi-v1393-test-boot",
                        "supervisor spawned pid=%ld",
                        (long)pid);
    klogf("<6>%s: wifi test boot supervisor spawned pid=%ld\n",
          A90_WIFI_TEST_BOOT_KLOG_PREFIX,
          (long)pid);
    (void)v1393_append_wifi_test_log("supervisor pid=%ld label=%s mode=%s\n",
                                    (long)pid,
                                    A90_WIFI_TEST_BOOT_LABEL,
                                    A90_V1393_WIFI_TEST_MODE);
#else
    spawn_ms = monotonic_millis();
    rc = v1393_spawn_wifi_test_boot_helper(&pid);
    if (rc < 0) {
        int saved_errno = -rc;

        if (saved_errno <= 0) {
            saved_errno = EIO;
        }
        a90_logf("wifi-v1393", "helper spawn failed rc=%d errno=%d error=%s",
                 rc,
                 saved_errno,
                 strerror(saved_errno));
        a90_timeline_record(rc, saved_errno, "wifi-v1393-test-boot", "spawn failed");
        klogf("<6>%s: wifi test boot helper spawn failed rc=%d\n",
              A90_WIFI_TEST_BOOT_KLOG_PREFIX,
              rc);
        (void)v1393_append_wifi_test_log("spawn failed rc=%d errno=%d error=%s\n",
                                        rc,
                                        saved_errno,
                                        strerror(saved_errno));
        return;
    }

    snprintf(pid_text, sizeof(pid_text), "%ld\n", (long)pid);
    (void)v724_write_private_file(A90_V1393_WIFI_TEST_PID, pid_text);
    a90_logf("wifi-v1393", "helper spawned pid=%ld mode=%s",
             (long)pid,
             A90_V1393_WIFI_TEST_MODE);
    a90_timeline_record(0,
                        0,
                        "wifi-v1393-test-boot",
                        "helper spawned pid=%ld",
                        (long)pid);
    klogf("<6>%s: wifi test boot helper spawned pid=%ld\n",
          A90_WIFI_TEST_BOOT_KLOG_PREFIX,
          (long)pid);
    (void)v1393_append_wifi_test_log("spawned pid=%ld label=%s mode=%s\n",
                                    (long)pid,
                                    A90_WIFI_TEST_BOOT_LABEL,
                                    A90_V1393_WIFI_TEST_MODE);

    rc = v1393_spawn_wifi_test_summary_watcher(pid, spawn_ms, &watcher_pid);
    if (rc == 0) {
        snprintf(pid_text, sizeof(pid_text), "%ld\n", (long)watcher_pid);
        (void)v724_write_private_file(A90_V1393_WIFI_TEST_WATCHER_PID, pid_text);
        (void)v1393_append_wifi_test_log("watcher pid=%ld watch_sec=%d summary=%s\n",
                                        (long)watcher_pid,
                                        A90_WIFI_TEST_BOOT_WATCH_SEC,
                                        A90_V1393_WIFI_TEST_SUMMARY);
    } else {
        (void)v1393_append_wifi_test_log("watcher spawn failed rc=%d errno=%d error=%s\n",
                                        rc,
                                        -rc,
                                        strerror(-rc));
    }
#endif
}
#endif

static bool v641_sibling_ssctl_flag_armed(void) {
    char state[32];

    if (read_trimmed_text_file(A90_V641_SIBLING_SSCTL_FLAG,
                               state,
                               sizeof(state)) < 0) {
        a90_logf("wifi-v641", "sibling fwssctl disabled flag=%s errno=%d error=%s",
                 A90_V641_SIBLING_SSCTL_FLAG,
                 errno,
                 strerror(errno));
        klogf("<6>A90v641: sibling fwssctl disabled flag=%s\n",
              A90_V641_SIBLING_SSCTL_FLAG);
        return false;
    }

    if (strcmp(state, "run") != 0) {
        a90_logf("wifi-v641", "sibling fwssctl ignored flag=%s state=%.16s",
                 A90_V641_SIBLING_SSCTL_FLAG,
                 state);
        klogf("<6>A90v641: sibling fwssctl ignored state=%.16s\n", state);
        return false;
    }

    if (unlink(A90_V641_SIBLING_SSCTL_FLAG) < 0 && errno != ENOENT) {
        a90_logf("wifi-v641", "sibling fwssctl flag unlink warning errno=%d error=%s",
                 errno,
                 strerror(errno));
    }
    sync();
    return true;
}

static bool v641_uevent_has_partname(const char *text, const char *partname) {
    const char *cursor = text;
    size_t partname_len = strlen(partname);

    while (cursor != NULL && *cursor != '\0') {
        const char *line_end = strchr(cursor, '\n');
        size_t line_len = line_end != NULL ? (size_t)(line_end - cursor) : strlen(cursor);

        if (line_len >= 9 + partname_len &&
            strncmp(cursor, "PARTNAME=", 9) == 0 &&
            strncmp(cursor + 9, partname, partname_len) == 0 &&
            (cursor[9 + partname_len] == '\0' ||
             cursor[9 + partname_len] == '\n' ||
             cursor[9 + partname_len] == '\r')) {
            return true;
        }
        cursor = line_end != NULL ? line_end + 1 : NULL;
    }
    return false;
}

static int v641_find_block_by_partname(const char *partname,
                                       const char *fallback_block,
                                       char *out,
                                       size_t out_size) {
    DIR *dir;
    struct dirent *entry;

    dir = opendir("/sys/class/block");
    if (dir != NULL) {
        while ((entry = readdir(dir)) != NULL) {
            char uevent_path[PATH_MAX];
            char uevent[1024];

            if (entry->d_name[0] == '.') {
                continue;
            }
            if (snprintf(uevent_path,
                         sizeof(uevent_path),
                         "/sys/class/block/%s/uevent",
                         entry->d_name) >= (int)sizeof(uevent_path)) {
                continue;
            }
            if (read_text_file(uevent_path, uevent, sizeof(uevent)) < 0) {
                continue;
            }
            if (v641_uevent_has_partname(uevent, partname)) {
                int rc = get_block_device_path(entry->d_name, out, out_size);

                closedir(dir);
                return rc;
            }
        }
        closedir(dir);
    }

    return get_block_device_path(fallback_block, out, out_size);
}

static int v641_prepare_firmware_mount_one(const char *label,
                                           const char *partname,
                                           const char *fallback_block,
                                           const char *target) {
    char block_path[PATH_MAX];
    int saved_errno;

    if (v641_find_block_by_partname(partname,
                                    fallback_block,
                                    block_path,
                                    sizeof(block_path)) < 0) {
        saved_errno = errno;
        (void)v641_append_ssctl_log("firmware %s resolve failed part=%s fallback=%s errno=%d error=%s\n",
                                   label,
                                   partname,
                                   fallback_block,
                                   saved_errno,
                                   strerror(saved_errno));
        a90_logf("wifi-v641", "firmware %s resolve failed errno=%d error=%s",
                 label,
                 saved_errno,
                 strerror(saved_errno));
        return -saved_errno;
    }

    if (mount(block_path,
              target,
              "vfat",
              MS_RDONLY | MS_NOSUID | MS_NODEV | MS_NOEXEC,
              "utf8,shortname=lower") < 0) {
        saved_errno = errno;
        if (saved_errno != EBUSY) {
            (void)v641_append_ssctl_log("firmware %s mount failed source=%s target=%s errno=%d error=%s\n",
                                       label,
                                       block_path,
                                       target,
                                       saved_errno,
                                       strerror(saved_errno));
            a90_logf("wifi-v641", "firmware %s mount failed errno=%d error=%s",
                     label,
                     saved_errno,
                     strerror(saved_errno));
            return -saved_errno;
        }
    }

    (void)v641_append_ssctl_log("firmware %s mounted source=%s target=%s\n",
                               label,
                               block_path,
                               target);
    a90_logf("wifi-v641", "firmware %s mounted source=%s target=%s",
             label,
             block_path,
             target);
    klogf("<6>A90v641: firmware %s mounted target=%s\n", label, target);
    return 0;
}

static bool v641_vendor_is_system_vendor_symlink(void) {
    struct stat st;

    return lstat(A90_V641_VENDOR_DIR, &st) == 0 &&
           S_ISLNK(st.st_mode) &&
           path_exists(A90_V641_SYSTEM_VENDOR_DIR);
}

static bool v641_is_reserved_vendor_entry(const char *name) {
    return strcmp(name, ".") == 0 ||
           strcmp(name, "..") == 0 ||
           strcmp(name, "firmware_mnt") == 0 ||
           strcmp(name, "firmware-modem") == 0;
}

static int v641_symlink_vendor_entry(const char *source_path, const char *target_path) {
    if (symlink(source_path, target_path) == 0 || errno == EEXIST) {
        return 0;
    }
    return -errno;
}

static int v641_materialize_vendor_overlay_entry(const char *name) {
    char source_path[PATH_MAX];
    char target_path[PATH_MAX];
    struct stat st;

    if (snprintf(source_path, sizeof(source_path), "%s/%s",
                 A90_V641_SYSTEM_VENDOR_DIR, name) >= (int)sizeof(source_path) ||
        snprintf(target_path, sizeof(target_path), "%s/%s",
                 A90_V641_VENDOR_DIR, name) >= (int)sizeof(target_path)) {
        return -ENAMETOOLONG;
    }

    if (lstat(source_path, &st) < 0) {
        return -errno;
    }

    if (S_ISDIR(st.st_mode) && !S_ISLNK(st.st_mode)) {
        if (ensure_dir(target_path, 0755) < 0) {
            return -errno;
        }
        if (bind_mount_dir(source_path, target_path) < 0) {
            return -errno;
        }
        return 0;
    }

    return v641_symlink_vendor_entry(source_path, target_path);
}

static int v641_prepare_system_vendor_overlay(void) {
    DIR *dir;
    struct dirent *entry;
    int failures = 0;

    if (!v641_vendor_is_system_vendor_symlink()) {
        return 0;
    }

    if (unlink(A90_V641_VENDOR_DIR) < 0 && errno != ENOENT) {
        int saved_errno = errno != 0 ? errno : EIO;

        (void)v641_append_ssctl_log("vendor overlay unlink failed path=%s errno=%d error=%s\n",
                                   A90_V641_VENDOR_DIR,
                                   saved_errno,
                                   strerror(saved_errno));
        return -saved_errno;
    }

    if (ensure_dir(A90_V641_VENDOR_DIR, 0755) < 0) {
        int saved_errno = errno != 0 ? errno : EIO;

        (void)v641_append_ssctl_log("vendor overlay dir failed path=%s errno=%d error=%s\n",
                                   A90_V641_VENDOR_DIR,
                                   saved_errno,
                                   strerror(saved_errno));
        return -saved_errno;
    }

    dir = opendir(A90_V641_SYSTEM_VENDOR_DIR);
    if (dir == NULL) {
        int saved_errno = errno != 0 ? errno : EIO;

        (void)v641_append_ssctl_log("vendor overlay opendir failed path=%s errno=%d error=%s\n",
                                   A90_V641_SYSTEM_VENDOR_DIR,
                                   saved_errno,
                                   strerror(saved_errno));
        return -saved_errno;
    }

    while ((entry = readdir(dir)) != NULL) {
        int rc;

        if (v641_is_reserved_vendor_entry(entry->d_name)) {
            continue;
        }

        rc = v641_materialize_vendor_overlay_entry(entry->d_name);
        if (rc < 0) {
            ++failures;
            (void)v641_append_ssctl_log("vendor overlay entry failed name=%s rc=%d errno=%d\n",
                                       entry->d_name,
                                       rc,
                                       -rc);
        }
    }

    closedir(dir);

    if (failures > 0) {
        a90_logf("wifi-v641", "vendor overlay entry failures=%d", failures);
    }

    (void)v641_append_ssctl_log("vendor overlay ready source=%s target=%s failures=%d bin=%d lib64=%d etc=%d\n",
                               A90_V641_SYSTEM_VENDOR_DIR,
                               A90_V641_VENDOR_DIR,
                               failures,
                               path_exists("/vendor/bin") ? 1 : 0,
                               path_exists("/vendor/lib64") ? 1 : 0,
                               path_exists("/vendor/etc") ? 1 : 0);
    a90_logf("wifi-v641", "vendor overlay ready failures=%d", failures);
    klogf("<6>A90v641: vendor overlay ready failures=%d\n", failures);
    return 0;
}

static void v641_stat_optional(const char *label, const char *path) {
    struct stat st;

    if (lstat(path, &st) == 0) {
        (void)v641_append_ssctl_log("firmware stat %s path=%s mode=0%o size=%lld\n",
                                   label,
                                   path,
                                   (unsigned int)(st.st_mode & 07777),
                                   (long long)st.st_size);
        a90_logf("wifi-v641", "firmware stat %s ok path=%s", label, path);
        return;
    }

    (void)v641_append_ssctl_log("firmware stat %s missing path=%s errno=%d error=%s\n",
                               label,
                               path,
                               errno,
                               strerror(errno));
    a90_logf("wifi-v641", "firmware stat %s missing path=%s errno=%d error=%s",
             label,
             path,
             errno,
             strerror(errno));
}

static int v641_prepare_firmware_mounts(void) {
    int saved_errno;

    if (v641_prepare_system_vendor_overlay() < 0) {
        return -EIO;
    }

    if (ensure_dir(A90_V641_VENDOR_DIR, 0755) < 0 ||
        ensure_dir(A90_V641_FW_MNT_DIR, 0755) < 0 ||
        ensure_dir(A90_V641_FW_MODEM_DIR, 0755) < 0) {
        saved_errno = errno;
        (void)v641_append_ssctl_log("firmware mountpoint setup failed errno=%d error=%s\n",
                                   saved_errno,
                                   strerror(saved_errno));
        a90_logf("wifi-v641", "firmware mountpoint setup failed errno=%d error=%s",
                 saved_errno,
                 strerror(saved_errno));
        return -saved_errno;
    }

    if (v641_prepare_firmware_mount_one("apnhlos",
                                        "apnhlos",
                                        "sda20",
                                        A90_V641_FW_MNT_DIR) < 0) {
        return -EIO;
    }
    if (v641_prepare_firmware_mount_one("modem",
                                        "modem",
                                        "sda21",
                                        A90_V641_FW_MODEM_DIR) < 0) {
        return -EIO;
    }

    v641_stat_optional("firmware_mnt_image", A90_V641_FW_MNT_DIR "/image");
    v641_stat_optional("firmware_modem_image", A90_V641_FW_MODEM_DIR "/image");
    v641_stat_optional("modem_b00", A90_V641_FW_MODEM_DIR "/image/modem.b00");
    v641_stat_optional("cdsp_mdt", A90_V641_FW_MODEM_DIR "/image/cdsp.mdt");
    (void)v641_append_ssctl_log("firmware mounts ready\n");
    a90_timeline_record(0, 0, "wifi-v641-fwssctl", "firmware mounts ready");
    klogf("<6>A90v641: firmware mounts ready\n");
    return 0;
}

static int v641_write_sysfs_once(const char *path) {
    int fd;
    int saved_errno;

    fd = open(path, O_WRONLY | O_CLOEXEC | O_NOFOLLOW);
    if (fd < 0) {
        return -errno;
    }

    if (write_all_checked(fd, "1\n", 2) < 0) {
        saved_errno = errno;
        close(fd);
        return -saved_errno;
    }

    if (close(fd) < 0) {
        return -errno;
    }
    return 0;
}

static void v641_sibling_ssctl_child(const char *label, const char *path) {
    int rc;

    (void)v641_append_ssctl_log("node %s child start path=%s\n", label, path);
    rc = v641_write_sysfs_once(path);
    if (rc < 0) {
        (void)v641_append_ssctl_log("node %s write rc=%d errno=%d error=%s\n",
                                   label,
                                   rc,
                                   -rc,
                                   strerror(-rc));
        klogf("<6>A90v641: sibling fwssctl node=%s write failed rc=%d\n",
              label,
              rc);
        _exit(1);
    }

    (void)v641_append_ssctl_log("node %s write rc=0\n", label);
    klogf("<6>A90v641: sibling fwssctl node=%s write ok\n", label);
    _exit(0);
}

static int v641_wait_child_timeout(pid_t pid,
                                   int timeout_ms,
                                   int *status_out,
                                   bool *reaped_out) {
    long deadline = monotonic_millis() + timeout_ms;
    int status;

    if (reaped_out != NULL) {
        *reaped_out = false;
    }
    while (monotonic_millis() < deadline) {
        pid_t rc = waitpid(pid, &status, WNOHANG);

        if (rc == pid) {
            if (status_out != NULL) {
                *status_out = status;
            }
            if (reaped_out != NULL) {
                *reaped_out = true;
            }
            return 0;
        }
        if (rc < 0) {
            return -errno;
        }
        usleep(100000);
    }

    (void)kill(pid, SIGKILL);
    deadline = monotonic_millis() + 1000;
    while (monotonic_millis() < deadline) {
        pid_t rc = waitpid(pid, &status, WNOHANG);

        if (rc == pid) {
            if (status_out != NULL) {
                *status_out = status;
            }
            if (reaped_out != NULL) {
                *reaped_out = true;
            }
            return -ETIMEDOUT;
        }
        if (rc < 0) {
            return -errno;
        }
        usleep(100000);
    }
    return -ETIMEDOUT;
}

static int v641_run_sibling_ssctl_node(const char *label, const char *path) {
    pid_t pid;
    int status = 0;
    int rc;
    bool reaped = false;

    (void)v641_append_ssctl_log("node %s parent start path=%s timeout_ms=%d\n",
                               label,
                               path,
                               A90_V641_SIBLING_SSCTL_TIMEOUT_MS);
    a90_timeline_record(0, 0, "wifi-v641-fwssctl", "%s start", label);
    pid = fork();
    if (pid < 0) {
        int saved_errno = errno;

        (void)v641_append_ssctl_log("node %s fork failed errno=%d error=%s\n",
                                   label,
                                   saved_errno,
                                   strerror(saved_errno));
        a90_timeline_record(-saved_errno,
                            saved_errno,
                            "wifi-v641-fwssctl",
                            "%s fork failed",
                            label);
        return -saved_errno;
    }

    if (pid == 0) {
        v641_sibling_ssctl_child(label, path);
    }

    rc = v641_wait_child_timeout(pid,
                                 A90_V641_SIBLING_SSCTL_TIMEOUT_MS,
                                 &status,
                                 &reaped);
    (void)v641_append_ssctl_log("node %s parent rc=%d status=0x%x reaped=%d\n",
                               label,
                               rc,
                               status,
                               reaped ? 1 : 0);
    if (rc == 0) {
        int node_rc = WIFEXITED(status) ? WEXITSTATUS(status) : EIO;

        a90_timeline_record(node_rc == 0 ? 0 : -EIO,
                            node_rc,
                            "wifi-v641-fwssctl",
                            "%s status=0x%x",
                            label,
                            status);
        klogf("<6>A90v641: sibling fwssctl node=%s status=0x%x\n",
              label,
              status);
        return node_rc == 0 ? 0 : -EIO;
    }

    a90_timeline_record(rc,
                        -rc,
                        "wifi-v641-fwssctl",
                        "%s wait failed reaped=%d",
                        label,
                        reaped ? 1 : 0);
    klogf("<6>A90v641: sibling fwssctl node=%s wait failed rc=%d reaped=%d\n",
          label,
          rc,
          reaped ? 1 : 0);
    if (!reaped) {
        return -ECHILD;
    }
    return rc;
}

static void v641_run_sibling_ssctl_once(void) {
    static const struct {
        const char *label;
        const char *path;
    } nodes[] = {
        { "adsp", "/sys/kernel/boot_adsp/boot" },
        { "cdsp", "/sys/kernel/boot_cdsp/boot" },
        { "slpi", "/sys/kernel/boot_slpi/boot" },
    };
    size_t index;
    int failures = 0;
    int timeouts = 0;

    if (!v641_sibling_ssctl_flag_armed()) {
        return;
    }

    boot_splash_set_line(5, "[ WIFI   ] V641 FW SSCTL PROOF");
    boot_auto_frame();
    a90_console_printf("# V641 firmware-backed sibling SSCTL proof: armed one-shot.\r\n");
    a90_logf("wifi-v641", "sibling fwssctl proof armed timeout_ms=%d",
             A90_V641_SIBLING_SSCTL_TIMEOUT_MS);
    a90_timeline_record(0, 0, "wifi-v641-fwssctl", "armed one-shot");
    klogf("<6>A90v641: sibling fwssctl proof armed\n");

    if (v641_prepare_firmware_mounts() < 0) {
        a90_console_printf("# V641 firmware-backed sibling SSCTL proof: firmware mount failed.\r\n");
        a90_timeline_record(-EIO, EIO, "wifi-v641-fwssctl", "firmware mount failed");
        klogf("<6>A90v641: sibling fwssctl proof stopped by firmware mount failure\n");
        return;
    }

    for (index = 0; index < sizeof(nodes) / sizeof(nodes[0]); ++index) {
        int node_rc = v641_run_sibling_ssctl_node(nodes[index].label, nodes[index].path);

        if (node_rc != 0) {
            ++failures;
        }
        if (node_rc == -ETIMEDOUT) {
            ++timeouts;
        }
        if (node_rc == -ECHILD) {
            (void)v641_append_ssctl_log("proof stop unreaped node=%s\n",
                                       nodes[index].label);
            break;
        }
    }

    a90_console_printf("# V641 firmware-backed sibling SSCTL proof: failures=%d timeouts=%d.\r\n",
                       failures,
                       timeouts);
    a90_logf("wifi-v641", "sibling fwssctl proof complete failures=%d timeouts=%d",
             failures,
             timeouts);
    a90_timeline_record(failures == 0 ? 0 : -EIO,
                        failures,
                        "wifi-v641-fwssctl",
                        "complete failures=%d timeouts=%d",
                        failures,
                        timeouts);
    klogf("<6>A90v641: sibling fwssctl proof complete failures=%d timeouts=%d\n",
          failures,
          timeouts);
}

int main(void) {
    static const struct a90_storage_boot_hooks storage_hooks = {
        .set_line = storage_boot_set_line,
        .draw_frame = storage_boot_draw_frame,
    };
    static const struct a90_selftest_boot_hooks selftest_hooks = {
        .set_line = selftest_boot_set_line,
        .draw_frame = selftest_boot_draw_frame,
    };

    a90_timeline_record(0, 0, "init-start", "%s", INIT_BANNER);
    setup_base_mounts();
    a90_log_select_or_fallback(NATIVE_LOG_FALLBACK);
    a90_logf("boot", "%s start", INIT_BANNER);
    a90_logf("boot", "base mounts ready");
    a90_timeline_record(0, 0, "base-mounts", "proc/sys/dev/tmpfs requested");
    klogf("<6>A90v724: base mounts ready\n");
    prepare_early_display_environment();
    boot_splash_set_line(1, "[ CACHE  ] MOUNTING /cache");
    boot_splash_set_line(2, "[ SD     ] WAITING FOR PROBE");
    boot_auto_frame();
    a90_logf("boot", "early display/input nodes prepared");
    a90_timeline_record(0, 0, "early-nodes", "display/input/graphics nodes prepared");
    a90_timeline_probe_boot_resources();
    klogf("<6>A90v724: early display/input nodes prepared\n");

    if (a90_storage_mount_cache() == 0) {
        a90_storage_set_cache_ready(true);
        boot_splash_set_line(1, "[ CACHE  ] OK /cache");
        a90_log_select_or_fallback(NATIVE_LOG_PRIMARY);
        a90_timeline_replay_to_log("cache");
        a90_logf("boot", "%s start", INIT_BANNER);
        a90_logf("boot", "base mounts ready");
        a90_logf("boot", "early display/input nodes prepared");
        a90_logf("boot", "cache mounted log=%s", a90_log_path());
        a90_timeline_record(0, 0, "cache-mount", "/cache mounted log=%s", a90_log_path());
        mark_step("1_cache_ok_v724\n");
        klogf("<6>A90v724: cache mounted\n");
    } else {
        int saved_errno = errno;

        a90_storage_set_cache_ready(false);
        boot_splash_set_line(1, "[ CACHE  ] WARN MOUNT FAIL");
        a90_logf("boot", "cache mount failed errno=%d error=%s log=%s",
                    saved_errno, strerror(saved_errno), a90_log_path());
        a90_timeline_record(-saved_errno,
                        saved_errno,
                        "cache-mount",
                        "/cache failed: %s log=%s",
                        strerror(saved_errno),
                        a90_log_path());
        klogf("<6>A90v724: cache mount failed (%d)\n", saved_errno);
    }
    boot_auto_frame();
    a90_storage_probe_boot(&storage_hooks, NULL);
    {
        struct a90_storage_status storage_status;
        int runtime_rc;

        if (a90_storage_get_status(&storage_status) == 0) {
            runtime_rc = a90_runtime_init(&storage_status);
        } else {
            runtime_rc = a90_runtime_init(NULL);
        }

        if (runtime_rc == 0) {
            boot_splash_set_line(4,
                    a90_runtime_using_fallback() ?
                    "[ RUNTIME] CACHE ROOT READY" :
                    "[ RUNTIME] SD ROOT READY");
            klogf("<6>A90v724: runtime root ready %s\n", a90_runtime_root());
        } else {
            int runtime_errno = -runtime_rc;

            if (runtime_errno <= 0) {
                runtime_errno = EIO;
            }
            boot_splash_set_line(4, "[ RUNTIME] WARN FALLBACK");
            klogf("<6>A90v724: runtime root warning (%d)\n", runtime_errno);
        }
        boot_auto_frame();
    }

    if (a90_helper_scan() == 0) {
        char helper_summary[96];

        a90_helper_summary(helper_summary, sizeof(helper_summary));
        boot_splash_set_line(5, "[ HELPERS] INVENTORY READY");
        a90_logf("boot", "helper inventory ready %s", helper_summary);
        klogf("<6>A90v724: helper inventory ready %s\n", helper_summary);
    } else {
        char helper_summary[96];

        a90_helper_summary(helper_summary, sizeof(helper_summary));
        boot_splash_set_line(5, "[ HELPERS] WARN SEE SELFTEST");
        a90_logf("boot", "helper inventory warning %s", helper_summary);
        klogf("<6>A90v724: helper inventory warning %s\n", helper_summary);
    }
    boot_auto_frame();

    if (a90_userland_scan() == 0) {
        char userland_summary[96];

        a90_userland_summary(userland_summary, sizeof(userland_summary));
        boot_splash_set_line(5, "[USERLAND] INVENTORY READY");
        a90_logf("boot", "userland inventory ready %s", userland_summary);
        klogf("<6>A90v724: userland inventory ready %s\n", userland_summary);
    } else {
        char userland_summary[96];

        a90_userland_summary(userland_summary, sizeof(userland_summary));
        boot_splash_set_line(5, "[USERLAND] OPTIONAL MISSING");
        a90_logf("boot", "userland inventory warning %s", userland_summary);
        klogf("<6>A90v724: userland inventory warning %s\n", userland_summary);
    }
    boot_auto_frame();

#ifdef A90_WIFI_LIFECYCLE_MODEM_OWNER
    v726_start_wifi_lifecycle_modem_owner_once();
    boot_auto_frame();
#endif

#ifdef A90_WIFI_TEST_BOOT
    v1393_run_wifi_test_boot_once();
    (void)v726_start_wifi_runtime_summary_once();
    boot_auto_frame();
#endif

    if (a90_usb_gadget_setup_acm() == 0) {
        mark_step("2_gadget_ok_v724\n");
        boot_splash_set_line(4, "[ SERIAL ] ACM GADGET OK");
        a90_logf("boot", "ACM gadget configured");
        a90_timeline_record(0, 0, "usb-gadget", "ACM gadget configured");
        klogf("<6>A90v724: ACM gadget configured\n");
        (void)a90_selftest_run_boot(&selftest_hooks, NULL);
        {
            char guard_summary[96];

            refresh_pid1_guard();
            a90_pid1_guard_summary(guard_summary, sizeof(guard_summary));
            boot_splash_set_line(5,
                    a90_pid1_guard_has_failures() ?
                    "[ GUARD ] WARN SEE STATUS" :
                    "[ GUARD ] PID1 CHECK OK");
            boot_auto_frame();
            a90_logf("boot", "pid1 guard %s", guard_summary);
            a90_timeline_record(a90_pid1_guard_has_failures() ? -EIO : 0,
                            a90_pid1_guard_has_failures() ? EIO : 0,
                            "pid1-guard",
                            "%s",
                            guard_summary);
            klogf("<6>A90v724: pid1 guard %s\n", guard_summary);
        }
    } else {
        int saved_errno = errno;

        boot_splash_set_line(4, "[ SERIAL ] FAIL ACM GADGET");
        boot_auto_frame();
        a90_logf("boot", "ACM gadget failed errno=%d error=%s",
                    saved_errno, strerror(saved_errno));
        a90_timeline_record(-saved_errno,
                        saved_errno,
                        "usb-gadget",
                        "ACM gadget failed: %s",
                        strerror(saved_errno));
        klogf("<6>A90v724: ACM gadget failed (%d)\n", saved_errno);
        while (1) {
            sleep(60);
        }
    }

    if (a90_console_wait_tty() == 0) {
        mark_step("3_tty_ready_v724\n");
        boot_splash_set_line(4, "[ SERIAL ] TTYGS0 READY");
        boot_splash_set_line(5, "[ RUNTIME] HUD MENU LOADING");
        a90_logf("boot", "ttyGS0 ready");
        a90_timeline_record(0, 0, "ttyGS0", "/dev/ttyGS0 ready");
        klogf("<6>A90v724: ttyGS0 ready\n");
        boot_auto_frame();
        sleep(BOOT_SPLASH_SECONDS);
    } else {
        int saved_errno = errno;

        boot_splash_set_line(4, "[ SERIAL ] FAIL TTYGS0");
        boot_auto_frame();
        a90_logf("boot", "ttyGS0 missing errno=%d error=%s",
                    saved_errno, strerror(saved_errno));
        a90_timeline_record(-saved_errno,
                        saved_errno,
                        "ttyGS0",
                        "/dev/ttyGS0 missing: %s",
                        strerror(saved_errno));
        klogf("<6>A90v724: ttyGS0 missing (%d)\n", saved_errno);
        while (1) {
            sleep(60);
        }
    }

    if (a90_console_attach() == 0) {
        mark_step("4_console_attached_v724\n");
        boot_splash_set_line(5, "[ RUNTIME] SHELL READY");
        a90_logf("boot", "console attached");
        a90_timeline_record(0, 0, "console", "serial console attached");
        a90_console_drain_input(250, 1500);
        a90_console_printf("\r\n# %s\r\n", INIT_BANNER);
        a90_console_printf("# USB ACM serial console ready.\r\n");
        v724_run_qrtr_servloc_boot_once();
        v641_run_sibling_ssctl_once();
        if (start_auto_hud(BOOT_HUD_REFRESH_SECONDS, false) == 0) {
            a90_logf("boot", "autohud started refresh=%d", BOOT_HUD_REFRESH_SECONDS);
            a90_timeline_record(0, 0, "autohud", "started refresh=%d", BOOT_HUD_REFRESH_SECONDS);
            a90_console_printf("# Boot display: splash %ds -> autohud %ds.\r\n",
                    BOOT_SPLASH_SECONDS,
                    BOOT_HUD_REFRESH_SECONDS);
        } else {
            int saved_errno = errno;

            a90_logf("boot", "autohud start failed errno=%d error=%s",
                        saved_errno, strerror(saved_errno));
            a90_timeline_record(-saved_errno,
                            saved_errno,
                            "autohud",
                            "start failed: %s",
                            strerror(saved_errno));
            a90_console_printf("# Boot display: autohud start failed.\r\n");
        }
        if (a90_netservice_enabled()) {
            int net_rc;

            a90_console_printf("# Netservice: enabled, starting NCM/tcpctl.\r\n");
            net_rc = a90_netservice_start();
            if (net_rc == 0) {
                mark_step("5_netservice_ok_v724\n");
                a90_console_printf("# Netservice: NCM %s %s, tcpctl port %s.\r\n",
                        NETSERVICE_IFNAME,
                        NETSERVICE_DEVICE_IP,
                        NETSERVICE_TCP_PORT);
                klogf("<6>A90v724: netservice started\n");
            } else {
                int net_errno = -net_rc;

                if (net_errno < 0) {
                    net_errno = EIO;
                }
                a90_console_printf("# Netservice: start failed rc=%d errno=%d (%s).\r\n",
                        net_rc,
                        net_errno,
                        strerror(net_errno));
                a90_logf("boot", "netservice failed rc=%d errno=%d error=%s",
                            net_rc, net_errno, strerror(net_errno));
                a90_timeline_record(net_rc,
                                net_errno,
                                "netservice",
                                "start failed: %s",
                                strerror(net_errno));
                klogf("<6>A90v724: netservice failed (%d)\n", net_errno);
            }
        } else {
            a90_logf("boot", "netservice disabled flag=%s", NETSERVICE_FLAG_PATH);
        }
        if (rshell_enabled()) {
            int rshell_rc;

            a90_console_printf("# Remote shell: enabled, starting token TCP shell.\r\n");
            rshell_rc = rshell_start_service(false);
            if (rshell_rc == 0) {
                mark_step("6_rshell_ok_v724\n");
                a90_console_printf("# Remote shell: %s:%s ready.\r\n",
                        A90_RSHELL_BIND_ADDR,
                        A90_RSHELL_PORT);
                klogf("<6>A90v724: rshell started\n");
            } else {
                int rshell_errno = -rshell_rc;

                if (rshell_errno <= 0) {
                    rshell_errno = EIO;
                }
                a90_console_printf("# Remote shell: start failed rc=%d errno=%d (%s).\r\n",
                        rshell_rc,
                        rshell_errno,
                        strerror(rshell_errno));
                a90_logf("boot", "rshell failed rc=%d errno=%d error=%s",
                            rshell_rc, rshell_errno, strerror(rshell_errno));
                a90_timeline_record(rshell_rc,
                                rshell_errno,
                                "rshell",
                                "start failed: %s",
                                strerror(rshell_errno));
                klogf("<6>A90v724: rshell failed (%d)\n", rshell_errno);
            }
        } else {
            a90_logf("boot", "rshell disabled");
        }
        a90_logf("boot", "entering shell");
        a90_timeline_record(0, 0, "shell", "interactive shell ready");
        shell_loop();
    } else {
        int saved_errno = errno;
        a90_logf("boot", "console attach failed errno=%d error=%s",
                    saved_errno, strerror(saved_errno));
        a90_timeline_record(-saved_errno,
                        saved_errno,
                        "console",
                        "attach failed: %s",
                        strerror(saved_errno));
        klogf("<6>A90v724: console attach failed (%d)\n", saved_errno);
    }

    while (1) {
        sleep(60);
    }
}
