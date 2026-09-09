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

static int fixed_byte(void *context, unsigned int address, unsigned int reg)
{
    struct max77705_dev *parent = context;
    if (address != S22_PMIC_ADDRESS || (reg != 0 && reg != 1))
        return -EINVAL;
    return i2c_smbus_read_byte_data(parent->i2c, reg);
}

static int fixed_word(void *context, unsigned int address, unsigned int reg)
{
    struct max77705_dev *parent = context;
    if (address != S22_FG_ADDRESS || (reg != 0x06 && reg != 0x09 && reg != 0x0a))
        return -EINVAL;
    return i2c_smbus_read_word_data(parent->fuelgauge, reg);
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
            count = -EAGAIN;
            goto out;
        }
        cached_start_ms = now;
        if (!identity_checked) {
            error = s22_telemetry_identity(&fixed_reads, parent);
            if (error)
                state.stopped = error;
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

static int telemetry_probe(struct platform_device *pdev)
{
    struct i2c_client *client;
    struct max77705_dev *parent;
    struct device_node *root, *fg, *node;
    const char *model;
    u32 resistor;
    int error;

    if (strcmp(pdev->name, "max77705-fuelgauge"))
        return -ENODEV;
    client = i2c_verify_client(pdev->dev.parent);
    if (!client || client->addr != S22_PMIC_ADDRESS || !client->dev.of_node ||
        !of_device_is_compatible(client->dev.of_node, "maxim,max77705") ||
        !client->adapter->dev.of_node ||
        !client->dev.driver || strcmp(client->dev.driver->name, "max77705"))
        return -ENODEV;
    /* This kernel stores node unit names in full_name. Resolve absolute
     * paths through OF and compare identities instead of stringifying nodes. */
    node = of_find_node_by_path(S22_PARENT_PATH);
    error = node == client->dev.of_node ? 0 : -ENODEV;
    of_node_put(node);
    if (error)
        return error;
    node = of_find_node_by_path(S22_BUS_PATH);
    error = node == client->adapter->dev.of_node ? 0 : -ENODEV;
    of_node_put(node);
    if (error)
        return error;
    root = of_find_node_by_path("/");
    if (!root)
        return -ENODEV;
    error = of_property_read_string(root, "model", &model);
    /* These are the two reviewed merged-FDT roots. The G0Q project name
     * is DTBO metadata, not the live root model. Exact phone/firmware binding
     * remains the F1 owner's responsibility. */
    if (!error && strcmp(model, "Qualcomm Technologies, Inc. Waipio v2 SoC") &&
        strcmp(model, "Qualcomm Technologies, Inc. Waipio SoC"))
        error = -ENODEV;
    of_node_put(root);
    if (error)
        return error;
    fg = of_find_node_by_path(S22_FG_CONFIG_PATH);
    if (!fg)
        return -ENODEV;
    error = of_property_read_u32(fg, "fuelgauge,fg_resistor", &resistor);
    of_node_put(fg);
    if (error || resistor != 5)
        return -ENODEV;
    parent = dev_get_drvdata(&client->dev);
    if (!parent || parent->dev != &client->dev || parent->i2c != client ||
        !parent->fuelgauge || parent->fuelgauge->addr != S22_FG_ADDRESS ||
        parent->fuelgauge->adapter != client->adapter ||
        i2c_get_clientdata(parent->fuelgauge) != parent)
        return -ENODEV;
    if (!i2c_check_functionality(client->adapter,
            I2C_FUNC_SMBUS_READ_BYTE_DATA | I2C_FUNC_SMBUS_READ_WORD_DATA))
        return -EOPNOTSUPP;
    if (atomic_cmpxchg(&claimed, 0, 1))
        return -EBUSY;
    /* Core driver ownership prevents binding on a stock-FG-owned child. */
    mutex_lock(&sample_lock);
    bound_parent = parent;
    mutex_unlock(&sample_lock);
    return 0;
}

static int telemetry_remove(struct platform_device *pdev)
{
    (void)pdev;
    mutex_lock(&sample_lock);
    bound_parent = NULL;
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
