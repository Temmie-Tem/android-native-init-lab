#include "a90_wififeas.h"

#include "a90_config.h"
#include "a90_console.h"
#include "a90_log.h"

#include <errno.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>

#define WIFIFEAS_LINE_MAX 512

struct wififeas_sink {
    bool console;
};

static void feas_emit(struct wififeas_sink *sink, const char *fmt, ...) {
    char line[WIFIFEAS_LINE_MAX];
    va_list ap;
    int len;

    va_start(ap, fmt);
    len = vsnprintf(line, sizeof(line), fmt, ap);
    va_end(ap);

    if (len < 0) {
        return;
    }
    if (sink == NULL || sink->console) {
        a90_console_printf("%s", line);
    }
}

static const char *feas_yesno(bool value) {
    return value ? "yes" : "no";
}

const char *a90_wififeas_decision_name(enum a90_wififeas_decision decision) {
    switch (decision) {
    case A90_WIFI_FEAS_GO_READ_ONLY_ONLY:
        return "go-read-only-only";
    case A90_WIFI_FEAS_BASELINE_REQUIRED:
        return "baseline-required";
    case A90_WIFI_FEAS_NO_GO:
    default:
        return "no-go";
    }
}

int a90_wififeas_evaluate(struct a90_wififeas_result *out) {
    int rc;

    if (out == NULL) {
        return -EINVAL;
    }
    memset(out, 0, sizeof(*out));

    rc = a90_wifiinv_collect(&out->inventory);
    if (rc < 0) {
        return rc;
    }

    out->has_wlan_iface = out->inventory.wlan_ifaces > 0;
    out->has_wifi_rfkill = out->inventory.rfkill_wifi > 0;
    out->has_driver_module = out->inventory.module_matches > 0;
    out->has_candidate_files = out->inventory.file_matches > 0;

    if (out->has_wlan_iface && (out->has_wifi_rfkill || out->has_driver_module)) {
        out->decision = A90_WIFI_FEAS_GO_READ_ONLY_ONLY;
        snprintf(out->reason,
                 sizeof(out->reason),
                 "kernel-facing Wi-Fi objects are visible");
        snprintf(out->next_step,
                 sizeof(out->next_step),
                 "plan a separate explicitly approved read-only iw/nl80211 probe");
        return 0;
    }

    if (!out->has_candidate_files && out->inventory.existing_paths <= 6) {
        out->decision = A90_WIFI_FEAS_BASELINE_REQUIRED;
        snprintf(out->reason,
                 sizeof(out->reason),
                 "native default sees no wlan/rfkill/module and no Android/vendor candidates");
        snprintf(out->next_step,
                 sizeof(out->next_step),
                 "collect mountsystem-ro or Android/TWRP read-only baseline before bring-up");
        return 0;
    }

    out->decision = A90_WIFI_FEAS_NO_GO;
    snprintf(out->reason,
             sizeof(out->reason),
             "Android-side candidates exist but kernel-facing wlan/rfkill/module gates are missing");
    snprintf(out->next_step,
             sizeof(out->next_step),
             "do not enable Wi-Fi; identify driver/firmware/vendor path from Android/TWRP baseline");
    return 0;
}

static int feas_emit_summary(struct wififeas_sink *sink, bool verbose) {
    struct a90_wififeas_result result;
    int rc;

    rc = a90_wififeas_evaluate(&result);
    if (rc < 0) {
        return rc;
    }

    feas_emit(sink, "[wififeas]\r\n");
    feas_emit(sink, "banner=%s\r\n", INIT_BANNER);
    feas_emit(sink, "decision=%s\r\n", a90_wififeas_decision_name(result.decision));
    feas_emit(sink, "reason=%s\r\n", result.reason);
    feas_emit(sink, "next=%s\r\n", result.next_step);
    feas_emit(sink,
              "gates wlan=%s rfkill=%s module=%s candidates=%s proc_modules=%s\r\n",
              feas_yesno(result.has_wlan_iface),
              feas_yesno(result.has_wifi_rfkill),
              feas_yesno(result.has_driver_module),
              feas_yesno(result.has_candidate_files),
              feas_yesno(result.inventory.proc_modules_readable));
    feas_emit(sink,
              "inventory net=%d wlan=%d rfkill=%d wifi_rfkill=%d modules=%d paths=%d/%d files=%d\r\n",
              result.inventory.net_total,
              result.inventory.wlan_ifaces,
              result.inventory.rfkill_total,
              result.inventory.rfkill_wifi,
              result.inventory.module_matches,
              result.inventory.existing_paths,
              result.inventory.candidate_paths,
              result.inventory.file_matches);
    feas_emit(sink, "policy=read-only no-rfkill-write no-link-up no-module-change no-service-mutation\r\n");

    if (verbose) {
        feas_emit(sink, "[gate requirements]\r\n");
        feas_emit(sink, "1 wlan-like interface visible: %s\r\n", feas_yesno(result.has_wlan_iface));
        feas_emit(sink, "2 wifi rfkill visible: %s\r\n", feas_yesno(result.has_wifi_rfkill));
        feas_emit(sink, "3 wlan/cnss/qca module evidence: %s\r\n", feas_yesno(result.has_driver_module));
        feas_emit(sink, "4 firmware/vendor/userspace candidates: %s\r\n", feas_yesno(result.has_candidate_files));
        feas_emit(sink, "5 recovery path independent of Wi-Fi: yes (USB ACM native init)\r\n");
        feas_emit(sink, "[interpretation]\r\n");
        if (result.decision == A90_WIFI_FEAS_GO_READ_ONLY_ONLY) {
            feas_emit(sink, "result: prerequisites visible enough for a separate approved probe, not automatic bring-up\r\n");
        } else if (result.decision == A90_WIFI_FEAS_BASELINE_REQUIRED) {
            feas_emit(sink, "result: collect mounted-system or Android/TWRP read-only baseline first\r\n");
        } else {
            feas_emit(sink, "result: do not attempt Wi-Fi enablement from native init with current evidence\r\n");
        }
    }

    a90_logf("wififeas",
             "decision=%s wlan=%d rfkill=%d modules=%d candidates=%d paths=%d/%d",
             a90_wififeas_decision_name(result.decision),
             result.inventory.wlan_ifaces,
             result.inventory.rfkill_wifi,
             result.inventory.module_matches,
             result.inventory.file_matches,
             result.inventory.existing_paths,
             result.inventory.candidate_paths);
    return 0;
}

int a90_wififeas_print_summary(void) {
    struct wififeas_sink sink = { .console = true };

    return feas_emit_summary(&sink, false);
}

int a90_wififeas_print_full(void) {
    struct wififeas_sink sink = { .console = true };

    return feas_emit_summary(&sink, true);
}

int a90_wififeas_print_gate(void) {
    struct a90_wififeas_result result;
    int rc;

    rc = a90_wififeas_evaluate(&result);
    if (rc < 0) {
        return rc;
    }

    a90_console_printf("wififeas: decision=%s\r\n", a90_wififeas_decision_name(result.decision));
    a90_console_printf("wififeas: reason=%s\r\n", result.reason);
    a90_console_printf("wififeas: next=%s\r\n", result.next_step);
    a90_logf("wififeas", "gate decision=%s reason=%s",
             a90_wififeas_decision_name(result.decision),
             result.reason);
    return 0;
}

int a90_wififeas_print_refresh(void) {
    struct a90_wififeas_result result;
    int rc;

    rc = a90_wififeas_evaluate(&result);
    if (rc < 0) {
        return rc;
    }

    a90_console_printf("wififeas: refresh=%s\r\n", INIT_BANNER);
    a90_console_printf("wififeas: decision=%s\r\n", a90_wififeas_decision_name(result.decision));
    a90_console_printf("wififeas: reason=%s\r\n", result.reason);
    a90_console_printf("wififeas: next=%s\r\n", result.next_step);
    a90_console_printf("wififeas: active_wifi=%s\r\n",
            result.decision == A90_WIFI_FEAS_GO_READ_ONLY_ONLY ?
            "still-separate-approval-required" :
            "blocked");
    a90_console_printf("wififeas: v122_policy=read-only-refresh-only no-bring-up no-rfkill-write no-module-change\r\n");
    a90_console_printf("wififeas: compare=v103/v104 native default and mounted-system baselines\r\n");
    a90_console_printf("wififeas: gates wlan=%s rfkill=%s module=%s candidates=%s\r\n",
            feas_yesno(result.has_wlan_iface),
            feas_yesno(result.has_wifi_rfkill),
            feas_yesno(result.has_driver_module),
            feas_yesno(result.has_candidate_files));
    a90_logf("wififeas", "refresh decision=%s active=%s",
             a90_wififeas_decision_name(result.decision),
             result.decision == A90_WIFI_FEAS_GO_READ_ONLY_ONLY ?
             "approval-required" : "blocked");
    return 0;
}

int a90_wififeas_print_paths(void) {
    struct wififeas_sink sink = { .console = true };

    feas_emit(&sink, "[wififeas paths]\r\n");
    feas_emit(&sink, "native commands:\r\n");
    feas_emit(&sink, "  wifiinv full\r\n");
    feas_emit(&sink, "  wififeas full\r\n");
    feas_emit(&sink, "  mountsystem ro ; wifiinv full ; wififeas full\r\n");
    feas_emit(&sink, "host native collector:\r\n");
    feas_emit(&sink, "  python3 scripts/revalidation/wifi_inventory_collect.py --native-only --boot-image stage3/boot_linux_v122.img --out tmp/wifiinv/v122-native.txt\r\n");
    feas_emit(&sink, "optional read-only adb baselines:\r\n");
    feas_emit(&sink, "  python3 scripts/revalidation/wifi_inventory_collect.py --android-adb --out tmp/wifiinv/v104-android.txt\r\n");
    feas_emit(&sink, "  python3 scripts/revalidation/wifi_inventory_collect.py --twrp-adb --out tmp/wifiinv/v104-twrp.txt\r\n");
    feas_emit(&sink, "forbidden:\r\n");
    feas_emit(&sink, "  svc wifi enable; ip link set wlan0 up; rfkill write; insmod/rmmod/modprobe; firmware/vendor mutation\r\n");
    return 0;
}
