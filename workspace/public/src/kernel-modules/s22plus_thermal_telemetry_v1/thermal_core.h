/* SPDX-License-Identifier: GPL-2.0-only */
/* Exact G0Q revision-12 ADC table and Waipio CPU sensor identities.
 * Portable arithmetic shared by the kernel provider and behavioral H0 tests.
 */
#ifndef S22_THERMAL_CORE_H
#define S22_THERMAL_CORE_H

#define S22_THERMAL_CPU_COUNT 13U
#define S22_THERMAL_TABLE_COUNT 23U
#define S22_THERMAL_CPU_VALID 1U
#define S22_THERMAL_BATTERY_VALID 2U

struct s22_thermal_cpu { const char *name; unsigned int bank, sensor; };
static const struct s22_thermal_cpu s22_thermal_cpus[S22_THERMAL_CPU_COUNT] = {
    {"cpu-1-0",0,5}, {"cpu-1-1",0,6}, {"cpu-1-2",0,7},
    {"cpu-1-3",0,8}, {"cpu-1-4",0,9}, {"cpu-1-5",0,10},
    {"cpu-1-6",0,11}, {"cpu-1-7",0,12}, {"cpu-1-8",0,13},
    {"cpu-0-0",1,1}, {"cpu-0-1",1,2}, {"cpu-0-2",1,3}, {"cpu-0-3",1,4}
};

/* adc-temp and adc-wpc-temp share channel 0x14b on this board. Its
 * SCALE_HW_CALIB_DEFAULT output is microvolts despite IIO_TEMP metadata.
 * Table data is signed tenths of a degree Celsius, not milliCelsius.
 */
static const unsigned int s22_thermal_uv[S22_THERMAL_TABLE_COUNT] = {
    0x12eda,0x15c37,0x196ac,0x1d9bf,0x225b2,0x27b2f,0x2f0f2,0x37361,
    0x3fe59,0x4a292,0x55ae7,0x62ab7,0x70760,0x7f7b6,0x8e967,0x9db9a,
    0xacefb,0xbbdb7,0xc819f,0xd44ad,0xdd99c,0xe6221,0xed01e
};
static const int s22_thermal_deci[S22_THERMAL_TABLE_COUNT] = {
    900,850,800,750,700,650,600,550,500,450,400,350,300,250,200,150,
    100,50,0,-50,-100,-150,-200
};

static inline int s22_thermal_cpu_decode(unsigned int status, int *mc)
{
    int value;
    if (!(status & (1U << 21))) return -1;
    value = (int)(status & 0xfffU);
    if (value & 0x800) value -= 0x1000;
    value *= 100;
    if (value < -40000 || value > 150000) return -1;
    *mc = value;
    return 0;
}

static inline int s22_thermal_battery_decode(int uv, int *deci)
{
    unsigned int i;
    if (uv < (int)s22_thermal_uv[0] ||
        uv > (int)s22_thermal_uv[S22_THERMAL_TABLE_COUNT-1]) return -1;
    for (i = 1; i < S22_THERMAL_TABLE_COUNT; ++i) {
        if (uv <= (int)s22_thermal_uv[i]) {
            long long delta = (long long)(uv - (int)s22_thermal_uv[i-1]) *
                (s22_thermal_deci[i] - s22_thermal_deci[i-1]);
            *deci = s22_thermal_deci[i-1] + (int)(delta /
                (s22_thermal_uv[i] - s22_thermal_uv[i-1]));
            return 0;
        }
    }
    return -1;
}
#endif
