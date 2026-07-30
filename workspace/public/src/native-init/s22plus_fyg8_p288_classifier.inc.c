/*
 * P2.88 bounded-helper classification without early trace-snapshot claims.
 */

#include "s22plus_fyg8_p286_classifier.inc.c"

#ifndef S22PLUS_FYG8_P288_CLASSIFIER_INC_C
#define S22PLUS_FYG8_P288_CLASSIFIER_INC_C

#define P288_EMIT(result, stage, name) \
    p286_emit( \
        (result), \
        (stage), \
        name, \
        name##_OUTCOME, \
        name##_STAGE_MASK)

static int p288_classify_helper(
    unsigned int stage,
    const struct p286_helper_observation *observation,
    struct p282_classification *result)
{
    if (observation == 0 ||
        (stage != P282_STAGE_STOP && stage != P282_STAGE_RESTART))
        return -1;
    if (!observation->dispatched)
        return P288_EMIT(
            result, stage, P282_DETAIL_HELPER_DISPATCH_FAILED);
    if (observation->unreaped)
        return P288_EMIT(
            result, stage, P282_DETAIL_HELPER_UNREAPED);
    if (observation->malformed)
        return P288_EMIT(
            result, stage, P282_DETAIL_HELPER_COMPLETION_MALFORMED);
    if (observation->timed_out) {
        return stage == P282_STAGE_STOP
            ? P288_EMIT(
                result, stage, P282_DETAIL_NONE_WRITE_TIMEOUT)
            : P288_EMIT(
                result, stage, P288_DETAIL_PERIPHERAL_HELPER_TIMEOUT);
    }
    if (observation->result < 0) {
        return stage == P282_STAGE_STOP
            ? P288_EMIT(
                result,
                stage,
                P282_DETAIL_NONE_WRITE_RETURNED_ERROR)
            : P288_EMIT(
                result,
                stage,
                P282_DETAIL_PERIPHERAL_WRITE_RETURNED_ERROR);
    }
    if (!observation->record_complete ||
        !observation->write_completed)
        return P288_EMIT(
            result, stage, P282_DETAIL_HELPER_COMPLETION_MALFORMED);
    return observation->result == 0 ? 0 : -1;
}

#undef P288_EMIT

#endif
