// SPDX-License-Identifier: GPL-2.0-only
/* H0 prospective provider. No authority to load this module is implied.
 * Attach only to the existing, otherwise-unbound stock MFD fuel-gauge child.
 * No new I2C clients, IRQs, workqueues, firmware or register writes. */
#include <linux/atomic.h>
#include <linux/err.h>
#include <linux/errno.h>
#include <linux/i2c.h>
#include <linux/kernel.h>
#include <linux/ktime.h>
#include <linux/mfd/max77705-private.h>
#include <linux/module.h>
#include <linux/moduleparam.h>
#include <linux/mutex.h>
#include <linux/of.h>
#include <linux/platform_device.h>
#include "telemetry_core.h"

#define S22_PARENT_PATH "/soc/i2c@994000/max77705@66"
#define S22_BUS_PATH "/soc/i2c@994000"
#define S22_FG_CONFIG_PATH "/samsung_mobile_device/max77705-fuelgauge"

/* Verified against the inherited 125840-byte MFD ELF, not merely this header. */
static_assert(offsetof(struct max77705_dev, i2c) == 8);
static_assert(offsetof(struct max77705_dev, fuelgauge) == 24);
static_assert(offsetof(struct max77705_dev, i2c_lock) == 48);

static DEFINE_MUTEX(sample_lock);
static atomic_t claimed = ATOMIC_INIT(0);
static struct max77705_dev *bound_parent;
static struct s22_telemetry_state state;
static struct s22_telemetry_sample cached;
static u64 cached_start_ms;
static bool identity_checked;
/* Diagnostic metadata only. All fields share sample_lock; no extra bus reads. */
static unsigned int probe_stage, read_stage;
static int probe_error, read_error;
static int read_return = -ENODATA;
static int probe_failed(unsigned int stage, int error)
{
    mutex_lock(&sample_lock);
    probe_stage = stage;
    probe_error = error;
    mutex_unlock(&sample_lock);
    return error;
}

static int fixed_byte(void *context, unsigned int address, unsigned int reg)
{
    struct max77705_dev *parent = context;
    int value;
    if (address != S22_PMIC_ADDRESS || (reg != 0 && reg != 1))
        return -EINVAL;
    read_stage = reg == 0 ? 31 : 32;
    value = i2c_smbus_read_byte_data(parent->i2c, reg);
    read_return = value;
    read_error = value < 0 ? value : 0;
    return value;
}

static int fixed_word(void *context, unsigned int address, unsigned int reg)
{
    struct max77705_dev *parent = context;
    int value;
    if (address != S22_FG_ADDRESS || (reg != 0x06 && reg != 0x09 && reg != 0x0a))
        return -EINVAL;
    read_stage = reg == 0x06 ? 33 : reg == 0x09 ? 34 : 35;
    value = i2c_smbus_read_word_data(parent->fuelgauge, reg);
    read_return = value;
    read_error = value < 0 ? value : 0;
    return value;
}

static const struct s22_telemetry_ops fixed_reads = {
    .read_byte = fixed_byte,
    .read_word = fixed_word,
};

static int sample_get(char *buffer, const struct kernel_param *parameter)
{
    struct max77705_dev *parent;
    u64 now;
    int count, error;
    (void)parameter;
    if (!mutex_trylock(&sample_lock))
        return -EAGAIN;
    parent = bound_parent;
    if (!parent) {
        count = -ENODEV;
        goto out;
    }
    now = ktime_to_ms(ktime_get());
    if (!state.stopped && state.attempts < S22_TELEMETRY_MAX_SAMPLES &&
        (!cached.sequence || now - cached_start_ms >= 1000)) {
        /* Do not queue behind an in-flight PDIC transaction. The bus transfer
         * itself can still block; callers must be outside PID1/CONTROL. */
        if (!mutex_trylock(&parent->i2c_lock)) {
            read_stage = 30;
            read_error = -EAGAIN;
            read_return = -EAGAIN;
            count = -EAGAIN;
            goto out;
        }
        cached_start_ms = now;
        if (!identity_checked) {
            error = s22_telemetry_identity(&fixed_reads, parent);
            if (error) {
                state.stopped = error;
                read_error = error;
            }
            else
                identity_checked = true;
        }
        s22_telemetry_read(&state, &fixed_reads, parent, &cached);
        mutex_unlock(&parent->i2c_lock);
    }
    /* Timestamp is the original read start even on cache hits or terminal
     * fault/budget state. A caller must never relabel retained values as fresh. */
    count = scnprintf(buffer, PAGE_SIZE,
        "S22FG1 seq=%u start_ms=%llu valid=%u error=%d soc_raw=%u voltage_raw=%u current_raw=%u soc_permille=%u voltage_uv=%u current_ua=%d\n",
        cached.sequence, (unsigned long long)cached_start_ms, cached.valid,
        cached.error, cached.soc_raw, cached.voltage_raw, cached.current_raw,
        cached.soc_permille, cached.voltage_uv, cached.current_ua);
out:
    mutex_unlock(&sample_lock);
    return count;
}
static const struct kernel_param_ops sample_ops = { .get = sample_get };
module_param_cb(sample, &sample_ops, NULL, 0444);
MODULE_PARM_DESC(sample, "Fixed cached fuel-gauge telemetry; no setters");

/* Pure snapshot: reading this parameter cannot initiate I2C or bind a device.
 * probe: 0 not called; 1 entered; 2 name; 3 parent basics; 4 parent OF;
 * 5 bus OF; 6 root absent; 7 model; 8 FG config absent; 9 resistor;
 * 10 parent ABI/client; 11 adapter capability; 12 owner; 13 bound; 14 removed.
 * read: 0 none; 30 parent mutex busy; 31 ID; 32 revision; 33 SOC;
 * 34 voltage; 35 current. read_error includes an identity mismatch.
 */
static int diagnostic_get(char *buffer, const struct kernel_param *parameter)
{
    int count;
    (void)parameter;
    if (!mutex_trylock(&sample_lock))
        return -EAGAIN;
    count = scnprintf(buffer, PAGE_SIZE,
        "S22FGD1 probe=%u probe_error=%d bound=%u read=%u read_error=%d read_ret=%d attempts=%u stopped=%d\n",
        probe_stage, probe_error, bound_parent != NULL, read_stage,
        read_error, read_return, state.attempts, state.stopped);
    mutex_unlock(&sample_lock);
    return count;
}
static const struct kernel_param_ops diagnostic_ops = { .get = diagnostic_get };
module_param_cb(diagnostic, &diagnostic_ops, NULL, 0444);
MODULE_PARM_DESC(diagnostic, "Read-only binding/read status; no bus operations");

static int telemetry_probe(struct platform_device *pdev)
{
    struct i2c_client *client;
    struct max77705_dev *parent;
    struct device_node *root, *fg, *node;
    const char *model;
    u32 resistor;
    int error;

    probe_failed(1, 0);
    if (strcmp(pdev->name, "max77705-fuelgauge"))
        return probe_failed(2, -ENODEV);
    client = i2c_verify_client(pdev->dev.parent);
    if (!client || client->addr != S22_PMIC_ADDRESS || !client->dev.of_node ||
        !of_device_is_compatible(client->dev.of_node, "maxim,max77705") ||
        !client->adapter->dev.of_node ||
        !client->dev.driver || strcmp(client->dev.driver->name, "max77705"))
        return probe_failed(3, -ENODEV);
    /* This kernel stores node unit names in full_name. Resolve absolute
     * paths through OF and compare identities instead of stringifying nodes. */
    node = of_find_node_by_path(S22_PARENT_PATH);
    error = node == client->dev.of_node ? 0 : -ENODEV;
    of_node_put(node);
    if (error)
        return probe_failed(4, error);
    node = of_find_node_by_path(S22_BUS_PATH);
    error = node == client->adapter->dev.of_node ? 0 : -ENODEV;
    of_node_put(node);
    if (error)
        return probe_failed(5, error);
    root = of_find_node_by_path("/");
    if (!root)
        return probe_failed(6, -ENODEV);
    error = of_property_read_string(root, "model", &model);
    /* These are the two reviewed merged-FDT roots. The G0Q project name
     * is DTBO metadata, not the live root model. Exact phone/firmware binding
     * remains the F1 owner's responsibility. */
    if (!error && strcmp(model, "Qualcomm Technologies, Inc. Waipio v2 SoC") &&
        strcmp(model, "Qualcomm Technologies, Inc. Waipio SoC"))
        error = -ENODEV;
    of_node_put(root);
    if (error)
        return probe_failed(7, error);
    fg = of_find_node_by_path(S22_FG_CONFIG_PATH);
    if (!fg)
        return probe_failed(8, -ENODEV);
    error = of_property_read_u32(fg, "fuelgauge,fg_resistor", &resistor);
    of_node_put(fg);
    if (error || resistor != 5)
        return probe_failed(9, error ? error : -ENODEV);
    parent = dev_get_drvdata(&client->dev);
    if (!parent || parent->dev != &client->dev || parent->i2c != client ||
        !parent->fuelgauge || parent->fuelgauge->addr != S22_FG_ADDRESS ||
        parent->fuelgauge->adapter != client->adapter ||
        i2c_get_clientdata(parent->fuelgauge) != parent)
        return probe_failed(10, -ENODEV);
    if (!i2c_check_functionality(client->adapter,
            I2C_FUNC_SMBUS_READ_BYTE_DATA | I2C_FUNC_SMBUS_READ_WORD_DATA))
        return probe_failed(11, -EOPNOTSUPP);
    if (atomic_cmpxchg(&claimed, 0, 1))
        return probe_failed(12, -EBUSY);
    /* Core driver ownership prevents binding on a stock-FG-owned child. */
    mutex_lock(&sample_lock);
    bound_parent = parent;
    probe_stage = 13;
    probe_error = 0;
    mutex_unlock(&sample_lock);
    return 0;
}

static int telemetry_remove(struct platform_device *pdev)
{
    (void)pdev;
    mutex_lock(&sample_lock);
    bound_parent = NULL;
    probe_stage = 14;
    mutex_unlock(&sample_lock);
    return 0;
}

static const struct platform_device_id telemetry_ids[] = {
    { "max77705-fuelgauge", 0 },
    { }
};
static struct platform_driver telemetry_driver = {
    .probe = telemetry_probe,
    .remove = telemetry_remove,
    .driver = { .name = "s22plus_max77705_telemetry" },
    .id_table = telemetry_ids,
};
module_platform_driver(telemetry_driver);
MODULE_DESCRIPTION("Fixed S22+ fuel-gauge telemetry without initialization writes");
MODULE_LICENSE("GPL v2");
