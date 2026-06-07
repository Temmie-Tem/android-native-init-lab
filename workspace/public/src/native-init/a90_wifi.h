#ifndef A90_WIFI_H
#define A90_WIFI_H

int a90_wifi_cmd(char **argv, int argc);
int a90_wifi_print_status(void);
int a90_wifi_scan_once(int delay_ms);

#endif
