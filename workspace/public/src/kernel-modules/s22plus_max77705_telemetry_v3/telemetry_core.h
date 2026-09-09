/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef S22PLUS_TELEMETRY_CORE_H
#define S22PLUS_TELEMETRY_CORE_H
/* Read-only protocol core, shared by the kernel wrapper and behavioral tests.
 * Callback arguments are fixed here; there is no caller-selected register API. */
#define S22_FG_ADDRESS 0x36U
#define S22_PMIC_ADDRESS 0x66U
#define S22_TELEMETRY_SOC 1U
#define S22_TELEMETRY_VOLTAGE 2U
#define S22_TELEMETRY_CURRENT 4U
#define S22_TELEMETRY_MAX_SAMPLES 601U
struct s22_telemetry_sample {
    unsigned int sequence, valid;
    int error;
    unsigned int soc_raw, voltage_raw, current_raw;
    unsigned int soc_permille, voltage_uv;
    int current_ua;
};
struct s22_telemetry_state {
    unsigned int attempts;
    int stopped;
};
/* read_byte selects SMBus byte-data reads only; read_word selects word-data
 * reads only. Word values are host-endian after SMBus little-endian decoding. */
struct s22_telemetry_ops {
    int (*read_byte)(void *context, unsigned int address, unsigned int reg);
    int (*read_word)(void *context, unsigned int address, unsigned int reg);
};
static int s22_telemetry_identity(const struct s22_telemetry_ops *ops, void *context)
{
    int id = ops->read_byte(context, S22_PMIC_ADDRESS, 0x00U);
    int revision;
    if (id < 0)
        return id;
    if (id != 0x15)
        return -ENODEV;
    revision = ops->read_byte(context, S22_PMIC_ADDRESS, 0x01U);
    if (revision < 0)
        return revision;
    return (revision & 7) == 2 ? 0 : -ENODEV;
}
static void s22_telemetry_read(struct s22_telemetry_state *state,
        const struct s22_telemetry_ops *ops, void *context,
        struct s22_telemetry_sample *sample)
{
    int value;
    *sample = (struct s22_telemetry_sample){0};
    if (state->stopped || state->attempts >= S22_TELEMETRY_MAX_SAMPLES) {
        sample->error = state->stopped ? state->stopped : -EOVERFLOW;
        sample->sequence = state->attempts;
        return;
    }
    sample->sequence = ++state->attempts;
    value = ops->read_word(context, S22_FG_ADDRESS, 0x06U); /* SOCREP */
    if (value < 0)
        goto failed;
    if (value > 65535) { value = -EPROTO; goto failed; }
    sample->soc_raw = (unsigned int)value;
    /* The vendor SOC getter also caps reported SOC at 100%. Keep the raw
     * register alongside the capped gauge estimate; this is not Android SOC. */
    sample->soc_permille = (unsigned int)value * 10U / 256U;
    if (sample->soc_permille > 1000U)
        sample->soc_permille = 1000U;
    sample->valid |= S22_TELEMETRY_SOC;
    value = ops->read_word(context, S22_FG_ADDRESS, 0x09U); /* VCELL */
    if (value < 0)
        goto failed;
    if (value > 65535) { value = -EPROTO; goto failed; }
    sample->voltage_raw = (unsigned int)value;
    /* 78.125 microvolts/LSB. Round down only at the final integer microvolt. */
    sample->voltage_uv = (unsigned int)value * 625U / 8U;
    if (sample->voltage_uv >= 2000000U && sample->voltage_uv <= 5000000U)
        sample->valid |= S22_TELEMETRY_VOLTAGE;
    value = ops->read_word(context, S22_FG_ADDRESS, 0x0aU); /* CURRENT */
    if (value < 0)
        goto failed;
    if (value > 65535) { value = -EPROTO; goto failed; }
    sample->current_raw = (unsigned int)value;
    /* Exact prospective g0q binding: fuelgauge,fg_resistor=5.
     * Same rational conversion as vendor read_current(unit=UA), preserving
     * two's-complement sign. It must not be reused for a different resistor. */
    if (value & 0x8000)
        sample->current_ua = -(int)((65536U - (unsigned int)value) * 15625U * 5U / 100U);
    else
        sample->current_ua = (int)((unsigned int)value * 15625U * 5U / 100U);
    sample->valid |= S22_TELEMETRY_CURRENT;
    return;
failed:
    sample->error = value;
    state->stopped = value; /* no further bus operations after a bus fault */
}
#endif
