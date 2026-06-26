#ifndef A90_MONITOR_H
#define A90_MONITOR_H

#define A90_MONITOR_M0_DEFAULT_SAMPLES 3U
#define A90_MONITOR_M0_MIN_SAMPLES 2U
#define A90_MONITOR_M0_MAX_SAMPLES 16U
#define A90_MONITOR_M0_DEFAULT_INTERVAL_MS 200U
#define A90_MONITOR_M0_MAX_INTERVAL_MS 5000U
#define A90_MONITOR_M1_DEFAULT_HOLD_MS 5000U
#define A90_MONITOR_M1_MAX_HOLD_MS 60000U

int a90_monitor_m0_sampler_probe(unsigned int samples, unsigned int interval_ms);
int a90_monitor_m1_dashboard_probe(unsigned int samples,
                                    unsigned int interval_ms,
                                    unsigned int hold_ms);

#endif
