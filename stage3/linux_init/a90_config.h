#ifndef A90_CONFIG_H
#define A90_CONFIG_H

#define INIT_VERSION "0.9.60"
#define INIT_BUILD "v261"
#define INIT_CREATOR "made by temmie0214"
#define INIT_BANNER "A90 Linux init " INIT_VERSION " (" INIT_BUILD ")"
#define BOOT_SPLASH_SECONDS 2
#define BOOT_HUD_REFRESH_SECONDS 2
#define NATIVE_LOG_PRIMARY "/cache/native-init.log"
#define NATIVE_LOG_FALLBACK_DIR "/tmp/a90-native"
#define NATIVE_LOG_FALLBACK NATIVE_LOG_FALLBACK_DIR "/native-init.log"
#define NATIVE_LOG_MAX_BYTES (256 * 1024)
#define KMS_LOG_TAIL_MAX_LINES 24
#define KMS_LOG_TAIL_LINE_MAX 96
#define KMS_LOG_TAIL_DEFAULT_ENABLED 0
#define BOOT_TIMELINE_MAX 32
#define CONSOLE_POLL_TIMEOUT_MS 1000
#define CONSOLE_IDLE_REATTACH_MS 60000
#define DISPLAY_TEST_PAGE_COUNT 4
#define AUTO_MENU_STATE_PATH "/tmp/a90-auto-menu-active"
#define AUTO_MENU_REQUEST_PATH "/tmp/a90-auto-menu-request"
#define HUD_LOG_TAIL_ENABLE_PATH "/tmp/a90-hud-log-tail-enabled"
#define NETSERVICE_FLAG_PATH "/cache/native-init-netservice"
#define NETSERVICE_LOG_PATH "/cache/native-init-netservice.log"
#define NETSERVICE_USB_HELPER "/cache/bin/a90_usbnet"
#define NETSERVICE_TCPCTL_HELPER "/bin/a90_tcpctl"
#define NETSERVICE_TOYBOX "/cache/bin/toybox"
#define A90_BUSYBOX_HELPER "/cache/bin/busybox"
#define A90_BUSYBOX_RAMDISK_HELPER "/bin/busybox"
#define NETSERVICE_IFNAME "ncm0"
#define NETSERVICE_DEVICE_IP "192.168.7.2"
#define NETSERVICE_NETMASK "255.255.255.0"
#define NETSERVICE_TCP_PORT "2325"
#define NETSERVICE_TCP_IDLE_SECONDS "3600"
#define NETSERVICE_TCP_MAX_CLIENTS "0"
#define NETSERVICE_TCP_BIND_ADDR NETSERVICE_DEVICE_IP
#define NETSERVICE_TCP_TOKEN_PATH "/cache/native-init-tcpctl.token"
#define A90_RSHELL_HELPER "/cache/bin/a90_rshell"
#define A90_RSHELL_RAMDISK_HELPER "/bin/a90_rshell"
#define A90_RSHELL_LOG_PATH "/cache/native-init-rshell.log"
#define A90_RSHELL_BIND_ADDR NETSERVICE_DEVICE_IP
#define A90_RSHELL_PORT "2326"
#define A90_RSHELL_IDLE_SECONDS "900"
#define A90_RSHELL_FLAG_NAME "remote-shell.enabled"
#define A90_RSHELL_TOKEN_NAME "remote-shell.token"
#define CPUSTRESS_HELPER "/bin/a90_cpustress"
#define A90_LONGSOAK_HELPER "/bin/a90_longsoak"
#define A90_LONGSOAK_DEFAULT_INTERVAL_SEC 60
#define A90_LONGSOAK_MIN_INTERVAL_SEC 1
#define A90_LONGSOAK_MAX_INTERVAL_SEC 3600
#define A90_LONGSOAK_TAIL_DEFAULT_LINES 8
#define A90_LONGSOAK_TAIL_MAX_LINES 64
#define CMDV1X_MAX_ARGS 32
#define SD_BLOCK_NAME "mmcblk0p1"
#define SD_MOUNT_POINT "/mnt/sdext"
#define SD_FS_TYPE "ext4"
#define SD_WORKSPACE_DIR "/mnt/sdext/a90"
#define SD_EXPECTED_UUID "c6c81408-f453-11e7-b42a-23a2c89f58bc"
#define SD_ID_FILE SD_WORKSPACE_DIR "/.a90-native-id"
#define SD_BOOT_RW_TEST_FILE SD_WORKSPACE_DIR "/tmp/.boot-rw-test"
#define SD_NATIVE_LOG_PATH SD_WORKSPACE_DIR "/logs/native-init.log"
#define A90_RUNTIME_SD_ROOT SD_WORKSPACE_DIR
#define A90_RUNTIME_CACHE_ROOT "/cache/a90-runtime"
#define A90_RUNTIME_BIN_DIR "bin"
#define A90_RUNTIME_ETC_DIR "etc"
#define A90_RUNTIME_LOGS_DIR "logs"
#define A90_RUNTIME_TMP_DIR "tmp"
#define A90_RUNTIME_STATE_DIR "state"
#define A90_RUNTIME_PKG_DIR "pkg"
#define A90_RUNTIME_RUN_DIR "run"
#define A90_RUNTIME_PKG_BIN_DIR "pkg/bin"
#define A90_RUNTIME_PKG_HELPERS_DIR "pkg/helpers"
#define A90_RUNTIME_PKG_SERVICES_DIR "pkg/services"
#define A90_RUNTIME_PKG_MANIFESTS_DIR "pkg/manifests"
#define A90_RUNTIME_STATE_SERVICES_DIR "state/services"
#define A90_RUNTIME_RW_TEST_NAME ".runtime-rw-test"
#define A90_HELPER_MANIFEST_NAME "helpers.manifest"
#define A90_HELPER_STATE_NAME "helper-state"
#define A90_HELPER_DEPLOY_LOG_NAME "helper-deploy.log"
#define A90_SLEEP_HELPER "/bin/a90sleep"
#define CACHE_STORAGE_ROOT "/cache"
#define TMP_STORAGE_ROOT "/tmp"
#define BOOT_SPLASH_LINE_COUNT 6
#define BOOT_SPLASH_LINE_MAX 96
#define BOOT_SELFTEST_MAX_ENTRIES 16

#endif
