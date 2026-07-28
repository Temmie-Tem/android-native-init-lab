/*
 * Pure P2.82 decision functions shared by the candidate runtime and the
 * synthetic classifier fixture. Numeric details and exact stage masks come
 * from s22plus_fyg8_p282_contract_spec.py.
 */

#ifndef P282_CLASSIFIER_CONTRACT_DEFINED
#error "include the generated P2.82 classifier contract first"
#endif

#ifndef S22PLUS_FYG8_P282_CLASSIFIER_INC_C
#define S22PLUS_FYG8_P282_CLASSIFIER_INC_C

enum p282_control_condition {
    P282_CONTROL_NONE = 0,
    P282_CONTROL_TRACE_CONTROL_UNAVAILABLE = 1,
    P282_CONTROL_TRACE_REGISTRATION_UNAVAILABLE = 2,
    P282_CONTROL_TRACE_INCOMPLETE = 3,
    P282_CONTROL_TRACE_CLEANUP_UNVERIFIED = 4,
    P282_CONTROL_TRACE_SOURCE_CONTRADICTION = 5,
    P282_CONTROL_HELPER_SOURCE_CONTRADICTION = 6,
};

enum p282_bind_branch {
    P282_BIND_DIRECT = 0,
    P282_BIND_RESUME_NESTED = 1,
    P282_BIND_DIAGNOSTIC_DEGRADED = 2,
};

enum p282_repair_class {
    P282_REPAIR_POWER_HELPER_OFF_ON_ZERO = 0,
    P282_REPAIR_SOFTWARE_REINIT = 1,
    P282_REPAIR_DIAGNOSTIC_DEGRADED = 2,
};

struct p282_classification {
    unsigned int stage;
    unsigned int outcome;
    unsigned int detail;
};

struct p282_stop_observation {
    unsigned int none_readback;
    unsigned int trace_authoritative;
    unsigned int worker_entered;
    unsigned int worker_returned;
    int worker_rc;
};

struct p282_suspend_observation {
    unsigned int trace_authoritative;
    unsigned int suspend_entered;
    unsigned int suspend_returned;
    int suspend_rc;
    unsigned int status_suspended;
    unsigned int power_off_entered;
    unsigned int power_off_returned;
    int power_off_rc;
};

struct p282_restart_observation {
    unsigned int peripheral_readback;
    unsigned int trace_authoritative;
    unsigned int worker_entered;
    unsigned int worker_returned;
    int worker_rc;
    unsigned int resume_entered;
    unsigned int resume_returned;
    int resume_rc;
    unsigned int init_entered;
    unsigned int init_returned;
    int init_rc;
    unsigned int power_on_entered;
    unsigned int power_on_returned;
    int power_on_rc;
    unsigned int notify_connect;
    unsigned int status_active;
    unsigned int mode_peripheral;
    unsigned int exact_udc;
    unsigned int off_on_zero_pair;
};

struct p282_bind_observation {
    unsigned int cleanup_verified;
    unsigned int source_consistent;
    unsigned int trace_authoritative;
    unsigned int pullup_returned_zero;
    unsigned int run_stop_seen;
    int run_stop_rc;
    unsigned int repair_class;
    unsigned int bind_branch;
};

struct p282_final_pair_observation {
    unsigned int first_state;
    unsigned int first_speed;
    unsigned int second_state;
    unsigned int second_speed;
    unsigned int repair_class;
    unsigned int bind_branch;
};

static unsigned int p282_stage_bit(unsigned int stage)
{
    switch (stage) {
    case P282_STAGE_ROLE_UDC:
        return 1U << 0;
    case P282_STAGE_STOP:
        return 1U << 1;
    case P282_STAGE_SUSPENDED:
        return 1U << 2;
    case P282_STAGE_RESTART:
        return 1U << 3;
    case P282_STAGE_BIND:
        return 1U << 4;
    case P282_STAGE_FINAL:
        return 1U << 5;
    case P282_STAGE_TERMINAL:
        return 1U << 6;
    default:
        return 0U;
    }
}

static int p282_emit(
    struct p282_classification *result,
    unsigned int stage,
    unsigned int outcome,
    unsigned int detail,
    unsigned int exact_stage_mask)
{
    if (result == 0 || (p282_stage_bit(stage) & exact_stage_mask) == 0U)
        return -1;
    result->stage = stage;
    result->outcome = outcome;
    result->detail = detail;
    return 1;
}

#define P282_EMIT(result, stage, name) \
    p282_emit( \
        (result), \
        (stage), \
        name##_OUTCOME, \
        name, \
        name##_STAGE_MASK)

static int p282_classify_cycle_control(
    unsigned int stage,
    unsigned int condition,
    struct p282_classification *result)
{
    switch (condition) {
    case P282_CONTROL_TRACE_CONTROL_UNAVAILABLE:
        return P282_EMIT(
            result, stage, P282_DETAIL_CYCLE_TRACE_CONTROL_UNAVAILABLE);
    case P282_CONTROL_TRACE_REGISTRATION_UNAVAILABLE:
        return P282_EMIT(
            result, stage, P282_DETAIL_CYCLE_TRACE_REGISTRATION_UNAVAILABLE);
    case P282_CONTROL_TRACE_INCOMPLETE:
        return P282_EMIT(
            result, stage, P282_DETAIL_CYCLE_TRACE_INCOMPLETE);
    case P282_CONTROL_TRACE_CLEANUP_UNVERIFIED:
        return P282_EMIT(
            result, stage, P282_DETAIL_CYCLE_TRACE_CLEANUP_UNVERIFIED);
    case P282_CONTROL_TRACE_SOURCE_CONTRADICTION:
        return P282_EMIT(
            result, stage, P282_DETAIL_CYCLE_TRACE_SOURCE_CONTRADICTION);
    case P282_CONTROL_HELPER_SOURCE_CONTRADICTION:
        return P282_EMIT(
            result, stage, P282_DETAIL_CYCLE_HELPER_SOURCE_CONTRADICTION);
    default:
        return condition == P282_CONTROL_NONE ? 0 : -1;
    }
}

static int p282_classify_stop(
    const struct p282_stop_observation *observation,
    struct p282_classification *result)
{
    if (observation == 0)
        return -1;
    if (!observation->none_readback)
        return P282_EMIT(
            result, P282_STAGE_STOP, P282_DETAIL_NONE_READBACK_NOT_REACHED);
    if (!observation->trace_authoritative)
        return 0;
    if (!observation->worker_entered)
        return P282_EMIT(
            result, P282_STAGE_STOP, P282_DETAIL_STOP_WORKER_NOT_ENTERED);
    if (!observation->worker_returned)
        return P282_EMIT(
            result, P282_STAGE_STOP, P282_DETAIL_STOP_WORKER_NO_RETURN);
    if (observation->worker_rc != 0)
        return P282_EMIT(
            result,
            P282_STAGE_STOP,
            P282_DETAIL_STOP_WORKER_UNEXPECTED_RETURN);
    return 0;
}

static int p282_classify_suspend(
    const struct p282_suspend_observation *observation,
    struct p282_classification *result)
{
    if (observation == 0)
        return -1;
    if (observation->trace_authoritative) {
        if (!observation->suspend_entered)
            return P282_EMIT(
                result,
                P282_STAGE_SUSPENDED,
                P282_DETAIL_CHILD_SUSPEND_NOT_ENTERED);
        if (!observation->suspend_returned)
            return P282_EMIT(
                result,
                P282_STAGE_SUSPENDED,
                P282_DETAIL_CHILD_SUSPEND_NO_RETURN);
        if (observation->suspend_rc < 0)
            return P282_EMIT(
                result,
                P282_STAGE_SUSPENDED,
                P282_DETAIL_CHILD_SUSPEND_NEGATIVE);
    }
    if (!observation->status_suspended)
        return P282_EMIT(
            result,
            P282_STAGE_SUSPENDED,
            P282_DETAIL_CHILD_STATUS_NOT_SUSPENDED);
    if (!observation->trace_authoritative)
        return 0;
    if (!observation->power_off_entered)
        return P282_EMIT(
            result,
            P282_STAGE_SUSPENDED,
            P282_DETAIL_SUSPENDED_NO_POWER_HELPER_OFF);
    if (!observation->power_off_returned)
        return -1;
    if (observation->power_off_rc < 0)
        return P282_EMIT(
            result,
            P282_STAGE_SUSPENDED,
            P282_DETAIL_SUSPENDED_POWER_HELPER_OFF_NEGATIVE);
    if (observation->power_off_rc != 0)
        return -1;
    return P282_EMIT(
        result,
        P282_STAGE_SUSPENDED,
        P282_DETAIL_SUSPENDED_POWER_HELPER_OFF_ZERO);
}

static int p282_classify_restart(
    const struct p282_restart_observation *observation,
    struct p282_classification *result)
{
    if (observation == 0)
        return -1;
    if (!observation->peripheral_readback)
        return P282_EMIT(
            result,
            P282_STAGE_RESTART,
            P282_DETAIL_PERIPHERAL_READBACK_NOT_REACHED);
    if (!observation->trace_authoritative)
        return 0;
    if (!observation->worker_entered)
        return P282_EMIT(
            result, P282_STAGE_RESTART, P282_DETAIL_START_WORKER_NOT_ENTERED);
    if (!observation->worker_returned)
        return P282_EMIT(
            result, P282_STAGE_RESTART, P282_DETAIL_START_WORKER_NO_RETURN);
    if (observation->worker_rc != 0)
        return P282_EMIT(
            result,
            P282_STAGE_RESTART,
            P282_DETAIL_START_WORKER_UNEXPECTED_RETURN);
    if (!observation->resume_entered)
        return P282_EMIT(
            result,
            P282_STAGE_RESTART,
            P282_DETAIL_CHILD_RESUME_NOT_ENTERED_AFTER_SUSPEND);
    if (!observation->resume_returned)
        return P282_EMIT(
            result, P282_STAGE_RESTART, P282_DETAIL_CHILD_RESUME_NO_RETURN);
    if (!observation->init_entered)
        return P282_EMIT(
            result,
            P282_STAGE_RESTART,
            P282_DETAIL_FEMTO_INIT_NOT_ENTERED_IN_RESUME);
    if (!observation->power_on_entered)
        return P282_EMIT(
            result,
            P282_STAGE_RESTART,
            P282_DETAIL_FEMTO_POWER_ON_NOT_ENTERED_IN_INIT);
    if (!observation->power_on_returned)
        return -1;
    if (observation->power_on_rc < 0)
        return P282_EMIT(
            result,
            P282_STAGE_RESTART,
            P282_DETAIL_FEMTO_POWER_ON_NEGATIVE);
    if (observation->power_on_rc != 0)
        return -1;
    if (!observation->init_returned)
        return -1;
    if (observation->init_rc < 0)
        return P282_EMIT(
            result, P282_STAGE_RESTART, P282_DETAIL_FEMTO_INIT_NEGATIVE);
    if (observation->init_rc != 0)
        return -1;
    if (observation->resume_rc < 0)
        return P282_EMIT(
            result,
            P282_STAGE_RESTART,
            P282_DETAIL_CHILD_RESUME_NEGATIVE_AFTER_INIT);
    if (observation->resume_rc != 0)
        return -1;
    if (!observation->notify_connect)
        return P282_EMIT(
            result,
            P282_STAGE_RESTART,
            P282_DETAIL_HSPHY_NOTIFY_CONNECT_MISSING);
    if (!observation->status_active)
        return P282_EMIT(
            result,
            P282_STAGE_RESTART,
            P282_DETAIL_CHILD_STATUS_NOT_ACTIVE);
    if (!observation->mode_peripheral)
        return P282_EMIT(
            result,
            P282_STAGE_RESTART,
            P282_DETAIL_PARENT_MODE_NOT_PERIPHERAL);
    if (!observation->exact_udc)
        return P282_EMIT(
            result,
            P282_STAGE_RESTART,
            P282_DETAIL_EXACT_UDC_REGRESSION_AFTER_RESTART);
    if (observation->off_on_zero_pair)
        return P282_EMIT(
            result,
            P282_STAGE_RESTART,
            P282_DETAIL_REINIT_POWER_HELPER_OFF_ON_ZERO);
    return P282_EMIT(
        result, P282_STAGE_RESTART, P282_DETAIL_REINIT_SOFTWARE_ONLY);
}

static int p282_classify_bind(
    const struct p282_bind_observation *observation,
    struct p282_classification *result)
{
    unsigned int detail;

    if (observation == 0)
        return -1;
    if (!observation->cleanup_verified)
        return P282_EMIT(
            result,
            P282_STAGE_BIND,
            P282_DETAIL_BIND_TRACE_CLEANUP_UNVERIFIED);
    if (!observation->source_consistent)
        return P282_EMIT(
            result,
            P282_STAGE_BIND,
            P282_DETAIL_BIND_TRACE_SOURCE_CONTRADICTION);
    if (!observation->pullup_returned_zero)
        return -1;
    if (observation->trace_authoritative && !observation->run_stop_seen)
        return P282_EMIT(
            result,
            P282_STAGE_BIND,
            P282_DETAIL_BIND_PULLUP_ZERO_WITHOUT_RUN_STOP);
    if (observation->trace_authoritative &&
        observation->bind_branch == P282_BIND_RESUME_NESTED &&
        observation->run_stop_rc < 0)
        return P282_EMIT(
            result,
            P282_STAGE_BIND,
            P282_DETAIL_NESTED_RUN_STOP_NEGATIVE);
    if (!observation->trace_authoritative ||
        observation->bind_branch == P282_BIND_DIAGNOSTIC_DEGRADED)
        return P282_EMIT(
            result,
            P282_STAGE_BIND,
            P282_DETAIL_BIND_DIAGNOSTIC_BRANCH_UNKNOWN);
    if (observation->run_stop_rc != 0 ||
        observation->repair_class >= P282_REPAIR_COUNT ||
        observation->bind_branch >= P282_BIND_DIAGNOSTIC_DEGRADED)
        return -1;

    detail = P282_DETAIL_HELPER_OFF_ON_ZERO_DIRECT_RUN_STOP +
        observation->repair_class * 2U + observation->bind_branch;
    return p282_emit(
        result,
        P282_STAGE_BIND,
        P282_OUTCOME_PROGRESS,
        detail,
        P282_DETAIL_HELPER_OFF_ON_ZERO_DIRECT_RUN_STOP_STAGE_MASK);
}

static int p282_encode_tuple(
    unsigned int repair_class,
    unsigned int bind_branch,
    unsigned int state,
    unsigned int speed,
    unsigned int *detail)
{
    if (detail == 0 ||
        repair_class >= P282_REPAIR_COUNT ||
        bind_branch >= P282_BIND_COUNT ||
        state >= P282_STATE_COUNT ||
        speed >= P282_SPEED_COUNT)
        return -1;
    *detail = P282_TUPLE_BASE +
        ((((repair_class * P282_BIND_COUNT) + bind_branch) *
        P282_STATE_COUNT + state) * P282_SPEED_COUNT + speed);
    if (*detail > P282_TUPLE_MAX)
        return -1;
    return 0;
}

static int p282_classify_final_pair(
    const struct p282_final_pair_observation *observation,
    struct p282_classification *result)
{
    unsigned int detail;
    unsigned int outcome;

    if (observation == 0 ||
        observation->first_state >= P282_STATE_COUNT ||
        observation->second_state >= P282_STATE_COUNT ||
        observation->first_speed >= P282_SPEED_COUNT ||
        observation->second_speed >= P282_SPEED_COUNT)
        return -1;
    if (observation->first_state != observation->second_state ||
        observation->first_speed != observation->second_speed)
        return P282_EMIT(
            result,
            P282_STAGE_FINAL,
            P282_DETAIL_FINAL_STATE_SPEED_UNSTABLE);
    if (p282_encode_tuple(
            observation->repair_class,
            observation->bind_branch,
            observation->second_state,
            observation->second_speed,
            &detail) != 0)
        return -1;
    outcome = (
        observation->second_state == P282_STATE_CONFIGURED &&
        observation->second_speed == P282_SPEED_HIGH
    ) ? P282_OUTCOME_PROGRESS : P282_OUTCOME_FAILURE;
    return p282_emit(
        result,
        P282_STAGE_FINAL,
        outcome,
        detail,
        1U << 5);
}

#undef P282_EMIT

#endif
