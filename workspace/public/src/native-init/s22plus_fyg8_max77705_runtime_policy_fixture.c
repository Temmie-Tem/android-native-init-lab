#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "s22plus_fyg8_max77705_result_parser.inc.c"
#include "s22plus_fyg8_max77705_envelope.inc.c"
#include "s22plus_fyg8_max77705_runtime_policy.inc.c"

static int emit_eagain(
    const char *name,
    struct s22plus_max77705_binding_witness binding,
    unsigned int expected_code) {
    uint8_t kind = 0U;
    uint8_t code = 0U;
    int rc = p316_policy_classify_eagain(&binding, &kind, &code);
    if (rc != 0 || kind != S22PLUS_MAX77705_SEMANTIC_TERMINAL
        || code != expected_code) return 1;
    printf("eagain:%s:%u:%u\n", name, kind, code);
    return 0;
}

static int emit_result(
    const char *name,
    const struct s22plus_max77705_binding_witness *binding,
    struct s22plus_max77705_runtime_result result,
    unsigned int expected_kind,
    unsigned int expected_code) {
    uint8_t kind = 0U;
    uint8_t code = 0U;
    int rc = p316_policy_classify_result(binding, &result, &kind, &code);
    if (rc != 0 || kind != expected_kind || code != expected_code) return 1;
    printf("result:%s:%u:%u\n", name, kind, code);
    return 0;
}

int main(void) {
    struct s22plus_max77705_binding_witness base = {
        .loader_state = S22PLUS_MAX77705_LOADER_RETURNED_SUCCESS,
        .pre_exact_parent_present = 1U,
        .pre_exact_parent_driver_state = S22PLUS_MAX77705_DRIVER_UNBOUND,
        .pre_matching_unbound_parent_count = 1U,
        .post_exact_parent_driver_state = S22PLUS_MAX77705_DRIVER_DIAGNOSTIC,
        .post_diagnostic_bound_parent_count = 1U,
        .post_exact_adapter_muic_0x25_client_count = 1U,
    };
    struct s22plus_max77705_binding_witness row;
    row = base;
    row.loader_state = S22PLUS_MAX77705_LOADER_IN_PROGRESS;
    row.post_exact_parent_driver_state = S22PLUS_MAX77705_DRIVER_UNBOUND;
    row.post_diagnostic_bound_parent_count = 0U;
    row.post_exact_adapter_muic_0x25_client_count = 0U;
    if (emit_eagain("probe-in-progress", row, 6U)) return 1;
    row = base;
    row.pre_exact_parent_present = 0U;
    row.pre_exact_parent_driver_state = S22PLUS_MAX77705_DRIVER_ABSENT;
    row.pre_matching_unbound_parent_count = 0U;
    row.post_exact_parent_driver_state = S22PLUS_MAX77705_DRIVER_ABSENT;
    row.post_diagnostic_bound_parent_count = 0U;
    row.post_exact_adapter_muic_0x25_client_count = 0U;
    if (emit_eagain("no-match", row, 2U)) return 1;
    row.pre_wrong_address_compatible_parent_count = 1U;
    if (emit_eagain("wrong-address", row, 3U)) return 1;
    row = base;
    row.pre_exact_parent_driver_state = S22PLUS_MAX77705_DRIVER_OTHER;
    row.post_exact_parent_driver_state = S22PLUS_MAX77705_DRIVER_OTHER;
    row.post_diagnostic_bound_parent_count = 0U;
    row.post_exact_adapter_muic_0x25_client_count = 0U;
    if (emit_eagain("other-driver", row, 4U)) return 1;
    row = base;
    row.post_exact_parent_driver_state = S22PLUS_MAX77705_DRIVER_UNBOUND;
    row.post_diagnostic_bound_parent_count = 0U;
    row.post_exact_adapter_muic_0x25_client_count = 0U;
    if (emit_eagain("post-unbound", row, 8U)) return 1;
    if (emit_eagain("bound-not-ready", base, 8U)) return 1;

    struct s22plus_max77705_runtime_result result = {0};
    result.stage = 2U;
    result.rc = -19;
    if (emit_result("identity-rejected", &base, result, 1U, 3U)) return 1;
    result.rc = -5;
    if (emit_result("identity-io", &base, result, 1U, 5U)) return 1;
    result.stage = 3U;
    result.rc = -16;
    if (emit_result("dummy-client", &base, result, 1U, 5U)) return 1;
    result.stage = 4U;
    result.rc = -5;
    if (emit_result("initial-uic", &base, result, 1U, 5U)) return 1;
    for (unsigned int stage = 5U; stage <= 9U; ++stage) {
        result.stage = (uint8_t)stage;
        result.rc = -5;
        if (stage == 8U) {
            uint8_t kind = 0U;
            uint8_t code = 0U;
            if (p316_policy_classify_result(
                &base, &result, &kind, &code) == 0) return 1;
            printf("negative:retention-stage-rejected\n");
            continue;
        }
        if (emit_result("command-transaction", &base, result, 2U, 5U))
            return 1;
    }
    result.stage = 5U;
    result.rc = 1;
    if (emit_result("positive-return", &base, result, 1U, 8U)) return 1;
    memset(&result, 0, sizeof(result));
    result.stage = S22PLUS_MAX77705_RUNTIME_STAGE_COMPLETE;
    result.response_value[0] = 0x3fU;
    result.response_value[2] = 0x09U;
    result.response_value[3] = 0x09U;
    if (emit_result("pre-nonusb-stable", &base, result, 2U, 1U)) return 1;
    result.response_value[0] = 0x09U;
    if (emit_result("pre-usb-stable", &base, result, 2U, 2U)) return 1;
    result.response_value[3] = 0x3fU;
    if (emit_result("post-reversion", &base, result, 2U, 3U)) return 1;
    result.response_value[2] = 0x3fU;
    if (emit_result("complete-other", &base, result, 2U, 4U)) return 1;

    static const char canonical[] =
        "v=1 stage=10 rc=0 pmic_v=03 pmic_id=15 pmic_rev=02 "
        "uic0_v=1 uic0=04 issued=0d seen=0d wr_attempt=0 wr_amb=0 "
        "rsp=05000505 val=09000909 p0n=1 p0=80 p1n=0 p1= "
        "p2n=1 p2=80 p3n=1 p3=80\n";
    struct s22plus_max77705_runtime_poll_summary summary;
    if (s22plus_max77705_runtime_parse_result(
        canonical, sizeof(canonical) - 1U, &result, &summary) != 0) return 1;
    uint8_t envelope[128];
    uint16_t detail = 0U;
    if (s22plus_max77705_encode_envelope(
        &base, S22PLUS_MAX77705_SEMANTIC_MUX,
        S22PLUS_MAX77705_MUX_PRE_USB_STABLE_USB,
        S22PLUS_MAX77705_OBSERVER_SITE_NONE,
        S22PLUS_MAX77705_OBSERVER_ERROR_NONE,
        &result, &summary, envelope, &detail) != 0 || detail != 0x6711U)
        return 1;
    return 0;
}
