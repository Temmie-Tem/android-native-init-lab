#ifndef A90_WIFI_H
#define A90_WIFI_H

#include <stdbool.h>
#include <stddef.h>

#define A90_WIFI_UI_MAX_SCAN_RESULTS 8

struct a90_wifi_ping_target_result {
    bool requested;
    bool resolved;
    bool executed;
    bool success;
    bool target_redacted;
    int run_wait_rc;
    int ping_rc;
    int ping_status;
    int ping_timed_out;
    int saved_errno;
    int packets_transmitted;
    int packets_received;
    int packet_loss_percent;
    long duration_ms;
    char kind[24];
    char target[64];
    char log_path[128];
    char rtt_avg_ms[32];
    char decision[64];
};

struct a90_wifi_ping_snapshot {
    int rc;
    int count;
    int timeout_sec;
    bool wlan0_present;
    bool carrier_up;
    bool route_default_present;
    bool busybox_executable;
    char mode[24];
    char decision[64];
    struct a90_wifi_ping_target_result gateway;
    struct a90_wifi_ping_target_result internet;
};

struct a90_wifi_status_snapshot {
    bool wlan0_present;
    bool runtime_summary_present;
    bool runtime_input_present;
    bool autoconnect_result_present;
    bool supplicant_executable;
    int ipv4_rc;
    int supplicant_process_count;
    char iface[16];
    char mac[80];
    char operstate[80];
    char carrier[32];
    char flags[32];
    char rx_bytes[64];
    char tx_bytes[64];
    char ipv4[64];
    char runtime_wlan0[32];
    char runtime_mac[80];
    char runtime_ip[80];
    char runtime_ssid_label[96];
    char runtime_rssi[32];
    char runtime_linkspeed[32];
    char runtime_decision[80];
    char autoconnect_profile[96];
    char autoconnect_decision[96];
    char autoconnect_final_rc[32];
    char autoconnect_carrier_up[32];
    char autoconnect_nameserver_count[32];
    char ctrl_socket_kind[32];
};

struct a90_wifi_scan_result {
    bool ssid_present;
    bool hidden;
    bool signal_valid;
    int freq_mhz;
    int signal_dbm;
    char ssid[64];
    char security[24];
};

struct a90_wifi_scan_snapshot {
    int rc;
    int saved_errno;
    int link_up_rc;
    int link_up_errno;
    int family_id;
    int netlink_open;
    int trigger_rc;
    int trigger_errno;
    unsigned int ifindex;
    int scan_result_count;
    int stored_count;
    int delay_ms;
    char decision[64];
    struct a90_wifi_scan_result results[A90_WIFI_UI_MAX_SCAN_RESULTS];
};

int a90_wifi_cmd(char **argv, int argc);
int a90_wifi_status_snapshot(struct a90_wifi_status_snapshot *out);
int a90_wifi_print_status(void);
int a90_wifi_scan_collect(int delay_ms, struct a90_wifi_scan_snapshot *out);
int a90_wifi_scan_once(int delay_ms);
int a90_wifi_ping_collect(const char *mode, struct a90_wifi_ping_snapshot *out);
int a90_wifi_ping_once(const char *mode);
int a90_wifi_connect_profile(const char *profile_name);
int a90_wifi_dhcp_profile(const char *profile_name);
int a90_wifi_cleanup(void);
int a90_wifi_start_boot_autoconnect_once(void);

#endif
