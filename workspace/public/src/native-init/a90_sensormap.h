#ifndef A90_SENSORMAP_H
#define A90_SENSORMAP_H

#include <stddef.h>

struct a90_sensormap_summary {
    int thermal_zones;
    int thermal_readable;
    int cooling_devices;
    int power_supplies;
    int power_batteries;
    int power_chargers;
    long max_temp_millic;
    char max_temp_type[96];
};

int a90_sensormap_collect_summary(struct a90_sensormap_summary *out);
void a90_sensormap_summary_text(char *out, size_t out_size);
int a90_sensormap_print_summary(void);
int a90_sensormap_print_thermal(void);
int a90_sensormap_print_power(void);
int a90_sensormap_print_full(void);
int a90_sensormap_print_paths(void);
int a90_sensormap_cmd(char **argv, int argc);

#endif
