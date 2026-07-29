/*
 * P2.86 parent-status and bounded-helper classifications over the inherited
 * P2.82 cycle classifier.
 */

#include "s22plus_fyg8_p282_classifier.inc.c"

#ifndef S22PLUS_FYG8_P286_CLASSIFIER_INC_C
#define S22PLUS_FYG8_P286_CLASSIFIER_INC_C

struct p286_helper_observation {
    unsigned int dispatched;
    unsigned int record_complete;
    unsigned int write_completed;
    unsigned int timed_out;
    unsigned int unreaped;
    unsigned int malformed;
    unsigned int start_entered;
    unsigned int start_returned;
    unsigned int outer_open;
    int result;
};

static int p286_emit(
    struct p282_classification *result,
    unsigned int stage,
    unsigned int detail,
    unsigned int outcome,
    unsigned int stage_mask)
{
    return p282_emit(result, stage, outcome, detail, stage_mask);
}

#define P286_EMIT(result, stage, name) \
    p286_emit( \
        (result), \
        (stage), \
        name, \
        name##_OUTCOME, \
        name##_STAGE_MASK)

static int p286_classify_parent_status(
    unsigned int matched,
    int read_result,
    struct p282_classification *result)
{
    if (read_result != 0)
        return P286_EMIT(
            result,
            P282_STAGE_SUSPENDED,
            P282_DETAIL_PARENT_STATUS_READ_ERROR);
    if (!matched)
        return P286_EMIT(
            result,
            P282_STAGE_SUSPENDED,
            P282_DETAIL_PARENT_STATUS_NOT_SUSPENDED);
    return 0;
}

static int p286_classify_helper(
    unsigned int stage,
    const struct p286_helper_observation *observation,
    struct p282_classification *result)
{
    if (observation == 0 ||
        (stage != P282_STAGE_STOP && stage != P282_STAGE_RESTART))
        return -1;
    if (!observation->dispatched)
        return P286_EMIT(
            result, stage, P282_DETAIL_HELPER_DISPATCH_FAILED);
    if (observation->unreaped)
        return P286_EMIT(
            result, stage, P282_DETAIL_HELPER_UNREAPED);
    if (observation->malformed)
        return P286_EMIT(
            result, stage, P282_DETAIL_HELPER_COMPLETION_MALFORMED);
    if (observation->timed_out) {
        if (stage == P282_STAGE_STOP)
            return P286_EMIT(
                result, stage, P282_DETAIL_NONE_WRITE_TIMEOUT);
        if (observation->outer_open)
            return P286_EMIT(
                result,
                stage,
                P282_DETAIL_RESIDUAL_OUTER_TAIL_TIMEOUT);
        if (observation->start_entered &&
            !observation->start_returned)
            return P286_EMIT(
                result,
                stage,
                P282_DETAIL_START_PERIPHERAL_NO_RETURN);
        return P286_EMIT(
            result, stage, P282_DETAIL_PERIPHERAL_FLUSH_TIMEOUT);
    }
    if (observation->result < 0) {
        return stage == P282_STAGE_STOP
            ? P286_EMIT(
                result,
                stage,
                P282_DETAIL_NONE_WRITE_RETURNED_ERROR)
            : P286_EMIT(
                result,
                stage,
                P282_DETAIL_PERIPHERAL_WRITE_RETURNED_ERROR);
    }
    if (!observation->record_complete ||
        !observation->write_completed)
        return P286_EMIT(
            result, stage, P282_DETAIL_HELPER_COMPLETION_MALFORMED);
    return observation->result == 0 ? 0 : -1;
}

static int p286_classify_peripheral_readback(
    unsigned int write_completed,
    unsigned int mode_peripheral,
    struct p282_classification *result)
{
    if (!write_completed)
        return -1;
    if (!mode_peripheral)
        return P286_EMIT(
            result,
            P282_STAGE_RESTART,
            P282_DETAIL_PERIPHERAL_WRITE_COMPLETED_READBACK_FAILED);
    return 0;
}

#undef P286_EMIT

#endif
