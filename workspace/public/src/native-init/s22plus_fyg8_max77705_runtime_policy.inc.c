/* Pure P3.16 terminal/MUX policy shared by PID1 and the host fixture. */

static int p316_policy_classify_eagain(
    const struct s22plus_max77705_binding_witness *binding,
    uint8_t *semantic_kind,
    uint8_t *semantic_code) {
    if (!s22plus_max77705_binding_valid(binding)
        || semantic_kind == NULL || semantic_code == NULL)
        return -1;
    *semantic_kind = S22PLUS_MAX77705_SEMANTIC_TERMINAL;
    if (binding->loader_state == S22PLUS_MAX77705_LOADER_IN_PROGRESS) {
        *semantic_code = S22PLUS_MAX77705_TERMINAL_NOT_READY;
    } else if (binding->loader_state !=
        S22PLUS_MAX77705_LOADER_RETURNED_SUCCESS) {
        return -1;
    } else if (binding->pre_exact_parent_driver_state ==
            S22PLUS_MAX77705_DRIVER_OTHER
        && binding->post_exact_parent_driver_state ==
            S22PLUS_MAX77705_DRIVER_OTHER) {
        *semantic_code = S22PLUS_MAX77705_TERMINAL_PARENT_OWNERSHIP;
    } else if (binding->post_exact_parent_driver_state ==
            S22PLUS_MAX77705_DRIVER_DIAGNOSTIC
        && binding->post_diagnostic_bound_parent_count == 1U
        && binding->post_exact_adapter_muic_0x25_client_count == 1U
        && binding->post_foreign_0x25_client_count == 0U) {
        *semantic_code = S22PLUS_MAX77705_TERMINAL_SYNC_CONTRADICTION;
    } else if (binding->pre_exact_parent_present == 1U
        && binding->post_exact_parent_driver_state ==
            S22PLUS_MAX77705_DRIVER_UNBOUND) {
        *semantic_code = S22PLUS_MAX77705_TERMINAL_SYNC_CONTRADICTION;
    } else if (binding->pre_exact_parent_present == 0U
        && binding->pre_wrong_address_compatible_parent_count != 0U) {
        *semantic_code = S22PLUS_MAX77705_TERMINAL_PARENT_IDENTITY;
    } else if (binding->pre_exact_parent_present == 0U
        && binding->pre_matching_unbound_parent_count == 0U
        && binding->pre_wrong_address_compatible_parent_count == 0U
        && binding->post_diagnostic_bound_parent_count == 0U
        && binding->post_exact_adapter_muic_0x25_client_count == 0U) {
        *semantic_code = S22PLUS_MAX77705_TERMINAL_NO_MATCH;
    } else {
        return -1;
    }
    return 0;
}

static int p316_policy_classify_result(
	const struct s22plus_max77705_binding_witness *binding,
    const struct s22plus_max77705_runtime_result *result,
    uint8_t *semantic_kind,
    uint8_t *semantic_code) {
    return s22plus_max77705_expected_semantic(
        binding, result, semantic_kind, semantic_code);
}
