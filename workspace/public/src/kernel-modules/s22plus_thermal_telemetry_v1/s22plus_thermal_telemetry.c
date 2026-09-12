// SPDX-License-Identifier: GPL-2.0-only
/* Exact G0Q temperature observation. No authority to load is implied.
 * TSENS: reads only; no calibration, IRQ, threshold, enable or reset writes.
 * Battery: one IIO conversion through the bound stock ADC7 driver. That driver
 * performs ADC configuration/conversion writes and owns its EOC interrupt.
 * Never bind the battery device: binding would select its unrelated pinctrl.
 * No charger, fuel-gauge write, new device, timer, workqueue or restart path.
 */
#include <linux/err.h>
#include <linux/iio/consumer.h>
#include <linux/iio/types.h>
#include <linux/io.h>
#include <linux/ktime.h>
#include <linux/module.h>
#include <linux/moduleparam.h>
#include <linux/mutex.h>
#include <linux/of.h>
#include <linux/of_platform.h>
#include <linux/platform_device.h>
#include "thermal_core.h"

#define S22_BATTERY_PATH "/samsung_mobile_device/battery"
static const char *const bank_paths[] = {
    "/soc/thermal-sensor@c263000", "/soc/thermal-sensor@c265000"
};
static const resource_size_t bank_tm[] = {0x0c263000,0x0c265000};
static const resource_size_t bank_srot[] = {0x0c222000,0x0c223000};
struct thermal_bank { void __iomem *tm, *srot; struct platform_device *device; };
static struct thermal_bank banks[2];
static DEFINE_MUTEX(thermal_lock);
static struct platform_device *battery_device;
static struct iio_channel *battery_channel;
static int battery_stopped, battery_bind_error = -ENODEV;
static int bank_error[2] = {-ENODEV,-ENODEV};
static u64 sequence, last_start;
static char diagnostic[512] = "S22THERMD1 seq=0 state=unread\n";

static int exact_node(struct device_node *node, const char *path)
{
    struct device_node *expected = of_find_node_by_path(path);
    int match = expected && node == expected;
    of_node_put(expected);
    return match;
}

static int exact_root(void)
{
    struct device_node *root = of_find_node_by_path("/");
    const char *model;
    int error = root ? of_property_read_string(root,"model",&model) : -ENODEV;
    if (!error && strcmp(model,"Samsung G0Q PROJECT (board-id,12)")) error = -ENODEV;
    of_node_put(root);
    return error;
}

static int exact_cpu_map(struct device_node *bank, unsigned int index)
{
    struct device_node *zones = of_find_node_by_path("/thermal-zones");
    unsigned int i;
    int error = zones ? 0 : -ENODEV;
    for (i = 0; !error && i < S22_THERMAL_CPU_COUNT; ++i) {
        struct device_node *zone;
        struct of_phandle_args args;
        if (s22_thermal_cpus[i].bank != index) continue;
        zone = of_get_child_by_name(zones,s22_thermal_cpus[i].name);
        if (!zone) { error = -ENODEV; break; }
        error = of_parse_phandle_with_args(zone,"thermal-sensors","#thermal-sensor-cells",0,&args);
        if (!error) {
            if (args.np != bank || args.args_count != 1 ||
                args.args[0] != s22_thermal_cpus[i].sensor) error = -ENODEV;
            of_node_put(args.np);
        }
        of_node_put(zone);
    }
    of_node_put(zones);
    return error;
}

static int thermal_probe(struct platform_device *pdev)
{
    struct resource *tm, *srot;
    struct thermal_bank next = { .device = pdev };
    unsigned int index;
    u32 sensors;
    int error = exact_root();
    if (error) return error;
    for (index = 0; index < 2; ++index)
        if (exact_node(pdev->dev.of_node,bank_paths[index])) break;
    if (index == 2) return -ENODEV;
    if (of_property_read_u32(pdev->dev.of_node,"#qcom,sensors",&sensors) || sensors != 16)
        return -ENODEV;
    error = exact_cpu_map(pdev->dev.of_node,index);
    if (error) goto failed;
    tm = platform_get_resource(pdev,IORESOURCE_MEM,0);
    srot = platform_get_resource(pdev,IORESOURCE_MEM,1);
    if (!tm || !srot || tm->start != bank_tm[index] || srot->start != bank_srot[index] ||
        resource_size(tm) != 0x1ff || resource_size(srot) != 0x1ff ||
        platform_get_resource(pdev,IORESOURCE_MEM,2)) { error = -ENODEV; goto failed; }
    next.tm = devm_ioremap_resource(&pdev->dev,tm);
    if (IS_ERR(next.tm)) { error = PTR_ERR(next.tm); goto failed; }
    next.srot = devm_ioremap_resource(&pdev->dev,srot);
    if (IS_ERR(next.srot)) { error = PTR_ERR(next.srot); goto failed; }
    if ((readl(next.srot) >> 28) != 2 || !(readl(next.srot+4) & 1)) {
        error = -ENODEV; goto failed;
    }
    mutex_lock(&thermal_lock);
    if (banks[index].device) error = -EBUSY;
    else { banks[index] = next; bank_error[index] = 0; }
    mutex_unlock(&thermal_lock);
    return error;
failed:
    mutex_lock(&thermal_lock); bank_error[index] = error; mutex_unlock(&thermal_lock);
    return error;
}

static int thermal_remove(struct platform_device *pdev)
{
    unsigned int i;
    mutex_lock(&thermal_lock);
    for (i = 0; i < 2; ++i) if (banks[i].device == pdev) {
        memset(&banks[i],0,sizeof(banks[i])); bank_error[i] = -ENODEV;
    }
    mutex_unlock(&thermal_lock);
    return 0;
}

static int exact_battery(struct device_node *node)
{
    struct of_phandle_args args;
    struct device_node *channel;
    const char *name;
    u32 value, table[S22_THERMAL_TABLE_COUNT], prescale[2];
    unsigned int i;
    int error;
    if (!exact_node(node,S22_BATTERY_PATH) || !of_device_is_compatible(node,"samsung,sec-battery") ||
        of_property_read_u32(node,"battery,thermal_source",&value) || value != 2 ||
        of_property_read_u32(node,"battery,temp_adc_type",&value) || value != 1 ||
        of_property_read_string_index(node,"io-channel-names",0,&name) || strcmp(name,"adc-temp") ||
        of_find_property(node,"battery,temp_offset",NULL)) return -ENODEV;
    if (of_property_count_u32_elems(node,"battery,temp_table_adc") != S22_THERMAL_TABLE_COUNT ||
        of_property_read_u32_array(node,"battery,temp_table_adc",table,S22_THERMAL_TABLE_COUNT)) return -ENODEV;
    for (i = 0; i < S22_THERMAL_TABLE_COUNT; ++i) if (table[i] != s22_thermal_uv[i]) return -ENODEV;
    if (of_property_count_u32_elems(node,"battery,temp_table_data") != S22_THERMAL_TABLE_COUNT ||
        of_property_read_u32_array(node,"battery,temp_table_data",table,S22_THERMAL_TABLE_COUNT)) return -ENODEV;
    for (i = 0; i < S22_THERMAL_TABLE_COUNT; ++i) if ((s32)table[i] != s22_thermal_deci[i]) return -ENODEV;
    error = of_parse_phandle_with_args(node,"io-channels","#io-channel-cells",0,&args);
    if (error) return error;
    if (args.args_count != 1 || args.args[0] != 0x14b ||
        !of_device_is_compatible(args.np,"qcom,spmi-adc7") ||
        of_property_read_u32(args.np,"reg",&value) || value != 0x3100) error = -ENODEV;
    channel = of_get_child_by_name(args.np,"wpc_thm");
    if (!channel || of_property_read_u32(channel,"reg",&value) || value != 0x14b ||
        of_property_read_u32(channel,"qcom,scale-fn-type",&value) || value != 5 ||
        of_property_read_u32(channel,"qcom,hw-settle-time",&value) || value != 200 ||
        !of_property_read_bool(channel,"qcom,ratiometric") ||
        of_property_read_u32_array(channel,"qcom,pre-scaling",prescale,2) ||
        prescale[0] != 1 || prescale[1] != 1) error = -ENODEV;
    of_node_put(channel); of_node_put(args.np);
    return error;
}

/* No driver bind, pinctrl selection or ADC conversion occurs here. */
static int battery_bind(void)
{
    struct device_node *node = of_find_node_by_path(S22_BATTERY_PATH);
    struct platform_device *pdev;
    struct iio_channel *channel;
    int error = node ? exact_battery(node) : -ENODEV;
    if (error) { of_node_put(node); return error; }
    pdev = of_find_device_by_node(node); of_node_put(node);
    if (!pdev) return -EPROBE_DEFER;
    channel = iio_channel_get(&pdev->dev,"adc-temp");
    if (IS_ERR(channel)) { error = PTR_ERR(channel); put_device(&pdev->dev); return error; }
    battery_device = pdev; battery_channel = channel;
    return 0;
}

static unsigned int cpu_sample(int *maximum)
{
    unsigned int i, mask = 0, ready[2] = {0,0};
    for (i = 0; i < 2; ++i) if (banks[i].device) {
        ready[i] = (readl(banks[i].srot) >> 28) == 2 &&
            (readl(banks[i].srot+4) & 1) && (readl(banks[i].tm+0xe4) & 1);
        bank_error[i] = ready[i] ? 0 : -ENODATA;
    }
    for (i = 0; i < S22_THERMAL_CPU_COUNT; ++i) {
        const struct s22_thermal_cpu *cpu = &s22_thermal_cpus[i];
        int mc;
        /* One atomic status word joins VALID with its own LAST_TEMP. A new
         * software acquisition is not a hardware conversion-age witness. */
        if (!ready[cpu->bank] || s22_thermal_cpu_decode(
                readl(banks[cpu->bank].tm+0xa0+4*cpu->sensor),&mc)) continue;
        if (!mask || mc > *maximum) *maximum = mc;
        mask |= 1U << i;
    }
    return mask;
}

static int sample_get(char *buffer, const struct kernel_param *parameter)
{
    u64 start, end;
    unsigned int valid = 0, mask;
    int cpu_mc = 0, battery_uv = 0, battery_deci = 0, battery_error, count;
    (void)parameter;
    if (!mutex_trylock(&thermal_lock)) return -EAGAIN;
    start = ktime_to_ms(ktime_get_boottime());
    if (sequence == U64_MAX || (sequence && start < last_start)) {
        count = -EOVERFLOW; goto out;
    }
    if (sequence && start-last_start < 1000) { count = -EAGAIN; goto out; }
    last_start = start; ++sequence;
    mask = cpu_sample(&cpu_mc);
    if (mask) valid |= S22_THERMAL_CPU_VALID;
    if (!battery_channel && !battery_stopped) battery_bind_error = battery_bind();
    battery_error = battery_stopped ? battery_stopped : battery_bind_error;
    if (battery_channel && !battery_stopped) {
        /* This driver's processed callback returns IIO_VAL_INT (1), not
         * syscall-style zero. Preserve negative errors; reject other formats. */
        battery_error = iio_read_channel_processed(battery_channel,&battery_uv);
        battery_error = battery_error == IIO_VAL_INT ? 0 : battery_error < 0 ? battery_error : -EPROTO;
        if (!battery_error && s22_thermal_battery_decode(battery_uv,&battery_deci)) battery_error = -ERANGE;
        if (battery_error) battery_stopped = battery_error;
        else valid |= S22_THERMAL_BATTERY_VALID;
    }
    end = ktime_to_ms(ktime_get_boottime());
    if (end < start) { battery_stopped = -EPROTO; count = -EPROTO; goto out; }
    count = scnprintf(buffer,PAGE_SIZE,
        "S22THERM1 seq=%llu start_ms=%llu end_ms=%llu valid=%u cpu_mask=%u cpu_temp_mc=%d battery_uv=%d battery_temp_deci=%d battery_error=%d cpu0_error=%d cpu1_error=%d\n",
        (unsigned long long)sequence,(unsigned long long)start,(unsigned long long)end,
        valid,mask,cpu_mc,battery_uv,battery_deci,battery_error,bank_error[0],bank_error[1]);
    scnprintf(diagnostic,sizeof(diagnostic),
        "S22THERMD1 seq=%llu start_ms=%llu end_ms=%llu cpu_banks=%u battery_bound=%u battery_stopped=%d cpu0_error=%d cpu1_error=%d\n",
        (unsigned long long)sequence,(unsigned long long)start,(unsigned long long)end,
        !!banks[0].device+2U*!!banks[1].device,!!battery_channel,battery_stopped,bank_error[0],bank_error[1]);
out:
    mutex_unlock(&thermal_lock);
    return count;
}
static const struct kernel_param_ops sample_ops = { .get = sample_get };
module_param_cb(sample,&sample_ops,NULL,0444);
MODULE_PARM_DESC(sample,"Fresh fixed TSENS observation and board battery ADC conversion; no setter");

static int diagnostic_get(char *buffer, const struct kernel_param *parameter)
{
    int count;
    (void)parameter;
    if (!mutex_trylock(&thermal_lock)) return -EAGAIN;
    count = scnprintf(buffer,PAGE_SIZE,"%s",diagnostic);
    mutex_unlock(&thermal_lock);
    return count;
}
static const struct kernel_param_ops diagnostic_ops = { .get = diagnostic_get };
module_param_cb(diagnostic,&diagnostic_ops,NULL,0444);
MODULE_PARM_DESC(diagnostic,"Pure acquisition/binding snapshot; no bus operations");

static const struct of_device_id thermal_match[] = { { .compatible = "qcom,tsens-v2" }, {} };
MODULE_DEVICE_TABLE(of,thermal_match);
static struct platform_driver thermal_driver = {
    .probe = thermal_probe, .remove = thermal_remove,
    .driver = { .name = "s22plus-thermal-telemetry", .of_match_table = thermal_match }
};
static int __init thermal_init(void)
{
    int error = exact_root();
    return error ? error : platform_driver_register(&thermal_driver);
}
static void __exit thermal_exit(void)
{
    platform_driver_unregister(&thermal_driver);
    mutex_lock(&thermal_lock);
    if (battery_channel) iio_channel_release(battery_channel);
    if (battery_device) put_device(&battery_device->dev);
    battery_channel = NULL; battery_device = NULL;
    mutex_unlock(&thermal_lock);
}
module_init(thermal_init);
module_exit(thermal_exit);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Exact S22+ FYG8 CPU and board battery temperature telemetry");
