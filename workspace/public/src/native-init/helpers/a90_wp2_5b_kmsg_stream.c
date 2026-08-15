/*
 * Host-qualified WP2-5b.1 raw trace encoder core.
 *
 * This file intentionally does not open /dev/kmsg, poll a device, create a
 * journal, or dispatch an effect.  A future reviewed runtime owner must do
 * those jobs and feed each exact successful read or explicit fault here.
 */

#include "a90_wp2_5b_kmsg_contract.h"

#include <errno.h>
#include <limits.h>
#include <stdint.h>
#include <string.h>

static void put_u16_be(unsigned char out[2], uint16_t value)
{
    out[0] = (unsigned char)(value >> 8);
    out[1] = (unsigned char)value;
}

static void put_u32_be(unsigned char out[4], uint32_t value)
{
    out[0] = (unsigned char)(value >> 24);
    out[1] = (unsigned char)(value >> 16);
    out[2] = (unsigned char)(value >> 8);
    out[3] = (unsigned char)value;
}

static void put_u64_be(unsigned char out[8], uint64_t value)
{
    unsigned int index;

    for (index = 0; index < 8; ++index)
        out[index] = (unsigned char)(value >> (56u - (index * 8u)));
}

static int digest_nonzero(const unsigned char value[32])
{
    unsigned int index;
    unsigned char aggregate = 0;

    if (value == NULL)
        return 0;
    for (index = 0; index < 32; ++index)
        aggregate |= value[index];
    return aggregate != 0;
}

static int emit_exact(struct a90_wp2_5b_stream *stream,
                      const unsigned char *data, size_t length)
{
    if (stream == NULL || stream->emit == NULL || data == NULL || length == 0)
        return -1;
    return stream->emit(stream->opaque, data, length) == 0 ? 0 : -1;
}

static int emit_frame(struct a90_wp2_5b_stream *stream, uint8_t type,
                      const unsigned char *payload, uint32_t payload_length)
{
    unsigned char header[A90_WP2_5B_FRAME_HEADER_SIZE];

    header[0] = type;
    header[1] = 0;
    put_u16_be(header + 2, 0);
    put_u32_be(header + 4, payload_length);
    if (emit_exact(stream, header, sizeof(header)) != 0)
        return -1;
    if (payload_length != 0 && emit_exact(stream, payload, payload_length) != 0)
        return -1;
    return 0;
}

static int parse_decimal(const unsigned char **cursor,
                         const unsigned char *end, unsigned char delimiter,
                         uint64_t maximum, uint64_t *value)
{
    const unsigned char *start = *cursor;
    uint64_t parsed = 0;

    if (start >= end || *start < '0' || *start > '9')
        return -1;
    if (*start == '0' && start + 1 < end && start[1] != delimiter)
        return -1;
    while (*cursor < end && **cursor != delimiter) {
        unsigned int digit;

        if (**cursor < '0' || **cursor > '9')
            return -1;
        digit = (unsigned int)(**cursor - '0');
        if (parsed > (maximum - digit) / 10u)
            return -1;
        parsed = (parsed * 10u) + digit;
        ++*cursor;
    }
    if (*cursor >= end || **cursor != delimiter)
        return -1;
    ++*cursor;
    *value = parsed;
    return 0;
}

static int hex_lower_value(unsigned char value)
{
    if (value >= '0' && value <= '9')
        return value - '0';
    if (value >= 'a' && value <= 'f')
        return value - 'a' + 10;
    return -1;
}

static int canonical_extended_text(const unsigned char *cursor,
                                   const unsigned char *end)
{
    while (cursor < end) {
        unsigned char current = *cursor;

        if (current != '\\') {
            if (current < 32 || current > 126)
                return -1;
            ++cursor;
            continue;
        }
        if (end - cursor < 4 || cursor[1] != 'x')
            return -1;
        {
            int high = hex_lower_value(cursor[2]);
            int low = hex_lower_value(cursor[3]);
            unsigned int decoded;

            if (high < 0 || low < 0)
                return -1;
            decoded = ((unsigned int)high << 4) | (unsigned int)low;
            if (!(decoded < 32 || decoded >= 127 || decoded == '\\'))
                return -1;
        }
        cursor += 4;
    }
    return 0;
}

static int parse_record_sequence(const unsigned char *record, size_t length,
                                 uint64_t *sequence)
{
    const unsigned char *cursor;
    const unsigned char *end;
    const unsigned char *body;
    const unsigned char *first_newline = NULL;
    uint64_t priority;
    uint64_t timestamp;
    size_t index;

    if (record == NULL || sequence == NULL || length == 0 ||
        length > A90_WP2_5B_KMSG_RECORD_MAX)
        return -1;
    cursor = record;
    end = record + length;
    if (parse_decimal(&cursor, end, ',', A90_WP2_5B_KMSG_PRIORITY_MAX,
                      &priority) != 0 ||
        parse_decimal(&cursor, end, ',', UINT64_MAX, sequence) != 0 ||
        parse_decimal(&cursor, end, ',', UINT64_MAX, &timestamp) != 0)
        return -1;
    (void)priority;
    (void)timestamp;
    if ((size_t)(end - cursor) < 2 ||
        (*cursor != '-' && *cursor != 'c') ||
        cursor[1] != ';')
        return -1;
    body = cursor + 2;
    if (body >= end || end[-1] != '\n')
        return -1;
    for (index = 0; body + index < end; ++index) {
        if (body[index] == '\n') {
            if (first_newline == NULL)
                first_newline = body + index;
            break;
        }
    }
    if (first_newline == NULL)
        return -1;
    if (canonical_extended_text(body, first_newline) != 0)
        return -1;
    cursor = first_newline + 1;
    {
        int saw_dictionary_line = 0;

    while (cursor < end) {
        const unsigned char *line = cursor;

        while (cursor < end && *cursor != '\n')
            ++cursor;
        if (cursor >= end)
            return -1;
        if (cursor == line) {
            if (!saw_dictionary_line || cursor + 1 != end)
                return -1;
        } else {
            if (*line != ' ' ||
                canonical_extended_text(line + 1, cursor) != 0)
                return -1;
            if (cursor == line + 1 && cursor + 1 == end)
                return -1;
            saw_dictionary_line = 1;
        }
        ++cursor;
    }
    }
    return 0;
}

int a90_wp2_5b_stream_begin(struct a90_wp2_5b_stream *stream,
                            a90_wp2_5b_emit_fn emit,
                            void *opaque,
                            const unsigned char run_binding_sha256[32],
                            const unsigned char qualification_sha256[32],
                            const unsigned char observer_binary_sha256[32],
                            uint32_t record_count_cap,
                            uint64_t record_byte_cap)
{
    unsigned char trace_header[A90_WP2_5B_TRACE_HEADER_SIZE];
    unsigned char arm[A90_WP2_5B_ARM_PAYLOAD_SIZE];

    if (stream == NULL || emit == NULL || record_count_cap == 0 ||
        record_byte_cap == 0 || !digest_nonzero(run_binding_sha256) ||
        !digest_nonzero(qualification_sha256) ||
        !digest_nonzero(observer_binary_sha256) ||
        !digest_nonzero(a90_wp2_5b_contract_sha256))
        return -1;
    memset(stream, 0, sizeof(*stream));
    stream->emit = emit;
    stream->opaque = opaque;
    stream->record_count_cap = record_count_cap;
    stream->record_byte_cap = record_byte_cap;
    stream->first_seq = UINT64_MAX;
    stream->last_seq = UINT64_MAX;

    memcpy(trace_header, a90_wp2_5b_trace_magic, 8);
    put_u16_be(trace_header + 8, A90_WP2_5B_TRACE_VERSION);
    put_u16_be(trace_header + 10, A90_WP2_5B_TRACE_HEADER_SIZE);
    put_u32_be(trace_header + 12, 0);
    if (emit_exact(stream, trace_header, sizeof(trace_header)) != 0)
        return -1;

    memcpy(arm, run_binding_sha256, 32);
    memcpy(arm + 32, qualification_sha256, 32);
    memcpy(arm + 64, observer_binary_sha256, 32);
    memcpy(arm + 96, a90_wp2_5b_contract_sha256, 32);
    put_u32_be(arm + 128, record_count_cap);
    put_u64_be(arm + 132, record_byte_cap);
    if (emit_frame(stream, A90_WP2_5B_FRAME_ARM, arm, sizeof(arm)) != 0)
        return -1;
    stream->armed = 1;
    return 0;
}

int a90_wp2_5b_stream_note_fault(struct a90_wp2_5b_stream *stream,
                                 uint32_t reason,
                                 int32_t os_errno,
                                 uint32_t poll_revents)
{
    unsigned char payload[A90_WP2_5B_FAULT_PAYLOAD_SIZE];

    if (stream == NULL || !stream->armed || stream->ended || stream->faulted ||
        reason < A90_WP2_5B_FAULT_READ ||
        reason > A90_WP2_5B_FAULT_EFAULT)
        return -1;
    put_u32_be(payload, reason);
    put_u32_be(payload + 4, (uint32_t)os_errno);
    put_u32_be(payload + 8, poll_revents);
    put_u64_be(payload + 12, stream->last_seq);
    stream->faulted = 1;
    return emit_frame(stream, A90_WP2_5B_FRAME_FAULT, payload,
                      sizeof(payload));
}

int a90_wp2_5b_stream_add_record(struct a90_wp2_5b_stream *stream,
                                 const unsigned char *record,
                                 size_t length)
{
    uint64_t sequence;

    if (stream == NULL || !stream->armed || stream->faulted || stream->ended)
        return -1;
    if (parse_record_sequence(record, length, &sequence) != 0) {
        (void)a90_wp2_5b_stream_note_fault(
            stream, A90_WP2_5B_FAULT_RECORD_FORMAT, EINVAL, 0);
        return -1;
    }
    if (stream->record_count != 0 &&
        (stream->last_seq == UINT64_MAX || sequence != stream->last_seq + 1)) {
        (void)a90_wp2_5b_stream_note_fault(
            stream, A90_WP2_5B_FAULT_SEQUENCE, 0, 0);
        return -1;
    }
    if (stream->record_count >= stream->record_count_cap) {
        (void)a90_wp2_5b_stream_note_fault(
            stream, A90_WP2_5B_FAULT_COUNT_CAP, 0, 0);
        return -1;
    }
    if (length > stream->record_byte_cap - stream->record_bytes) {
        (void)a90_wp2_5b_stream_note_fault(
            stream, A90_WP2_5B_FAULT_BYTE_CAP, 0, 0);
        return -1;
    }
    if (emit_frame(stream, A90_WP2_5B_FRAME_RECORD, record,
                   (uint32_t)length) != 0) {
        stream->faulted = 1;
        return -1;
    }
    if (stream->record_count == 0)
        stream->first_seq = sequence;
    stream->last_seq = sequence;
    ++stream->record_count;
    stream->record_bytes += length;
    return 0;
}

int a90_wp2_5b_stream_end(
    struct a90_wp2_5b_stream *stream,
    const unsigned char driver_init_epoch_sha256[32],
    const unsigned char capture_close_binding_sha256[32])
{
    unsigned char payload[A90_WP2_5B_END_PAYLOAD_SIZE];

    if (stream == NULL || !stream->armed || stream->ended ||
        !digest_nonzero(driver_init_epoch_sha256) ||
        !digest_nonzero(capture_close_binding_sha256))
        return -1;
    memcpy(payload, driver_init_epoch_sha256, 32);
    memcpy(payload + 32, capture_close_binding_sha256, 32);
    put_u32_be(payload + 64, stream->record_count);
    put_u64_be(payload + 68, stream->record_bytes);
    put_u64_be(payload + 76, stream->first_seq);
    put_u64_be(payload + 84, stream->last_seq);
    stream->ended = 1;
    return emit_frame(stream, A90_WP2_5B_FRAME_END, payload,
                      sizeof(payload));
}

#ifdef A90_WP2_5B_KMSG_TEST_MAIN
#include <unistd.h>

static int stdout_emit(void *opaque, const unsigned char *data, size_t length)
{
    size_t written = 0;

    (void)opaque;
    while (written < length) {
        ssize_t result = write(STDOUT_FILENO, data + written, length - written);

        if (result < 0 && errno == EINTR)
            continue;
        if (result <= 0)
            return -1;
        written += (size_t)result;
    }
    return 0;
}

int main(int argc, char **argv)
{
    struct a90_wp2_5b_stream stream;
    unsigned char run[32];
    unsigned char qualification[32];
    unsigned char observer[32];
    unsigned char driver[32];
    unsigned char close_binding[32];
    static const unsigned char first[] =
        "3,100,1000,-;WLAN MAC address is not set, type 0\n";
    static const unsigned char second[] =
        "6,101,1001,-;wlan0: link up\n";
    static const unsigned char gap[] =
        "6,102,1002,-;wlan0: gap\n";
    static const unsigned char malformed[] =
        "6,101,1001,x;bad flag\n";
    static const unsigned char raw_backslash[] =
        "3,101,1001,-;bad\\q\n";
    static const unsigned char blank_dictionary[] =
        "3,101,1001,-;body\n\n";
    static const unsigned char terminal_empty_dictionary[] =
        "3,101,1001,-;body\n \n";
    static const unsigned char priority_range[] =
        "2048,101,1001,-;bad priority\n";
    static const unsigned char short_flag_zero[] = "0,0,0,";
    static const unsigned char short_flag_one[] = "0,0,0,-";
    static const unsigned char escaped[] =
        "3,100,1000,-;bad\\x5c\\x0a\\xff\n key=va\\x5clue\n\n";
    const char *mode = argc > 1 ? argv[1] : "valid";
    uint32_t count_cap = strcmp(mode, "count-cap") == 0 ? 1u : 8u;
    uint64_t byte_cap = strcmp(mode, "byte-cap") == 0 ? 8u : 16384u;
    int expected_failure = strcmp(mode, "gap") == 0 ||
                           strcmp(mode, "malformed") == 0 ||
                           strcmp(mode, "raw-backslash") == 0 ||
                           strcmp(mode, "blank-dict") == 0 ||
                           strcmp(mode, "terminal-empty-dict") == 0 ||
                           strcmp(mode, "priority-range") == 0 ||
                           strcmp(mode, "short-flag-zero") == 0 ||
                           strcmp(mode, "short-flag-one") == 0 ||
                           strcmp(mode, "null") == 0 ||
                           strcmp(mode, "count-cap") == 0 ||
                           strcmp(mode, "byte-cap") == 0;
    int add_result;

    memset(run, 0x11, sizeof(run));
    memset(qualification, 0x22, sizeof(qualification));
    memset(observer, 0x33, sizeof(observer));
    memset(driver, 0x44, sizeof(driver));
    memset(close_binding, 0x55, sizeof(close_binding));
    if (a90_wp2_5b_stream_begin(&stream, stdout_emit, NULL, run,
                                qualification, observer, count_cap,
                                byte_cap) != 0)
        return 1;
    if (strcmp(mode, "malformed") == 0)
        add_result = a90_wp2_5b_stream_add_record(
            &stream, malformed, sizeof(malformed) - 1);
    else if (strcmp(mode, "raw-backslash") == 0)
        add_result = a90_wp2_5b_stream_add_record(
            &stream, raw_backslash, sizeof(raw_backslash) - 1);
    else if (strcmp(mode, "blank-dict") == 0)
        add_result = a90_wp2_5b_stream_add_record(
            &stream, blank_dictionary, sizeof(blank_dictionary) - 1);
    else if (strcmp(mode, "terminal-empty-dict") == 0)
        add_result = a90_wp2_5b_stream_add_record(
            &stream, terminal_empty_dictionary,
            sizeof(terminal_empty_dictionary) - 1);
    else if (strcmp(mode, "priority-range") == 0)
        add_result = a90_wp2_5b_stream_add_record(
            &stream, priority_range, sizeof(priority_range) - 1);
    else if (strcmp(mode, "short-flag-zero") == 0)
        add_result = a90_wp2_5b_stream_add_record(
            &stream, short_flag_zero, sizeof(short_flag_zero) - 1);
    else if (strcmp(mode, "short-flag-one") == 0)
        add_result = a90_wp2_5b_stream_add_record(
            &stream, short_flag_one, sizeof(short_flag_one) - 1);
    else if (strcmp(mode, "null") == 0)
        add_result = a90_wp2_5b_stream_add_record(&stream, NULL, 1);
    else if (strcmp(mode, "efault") == 0)
        add_result = a90_wp2_5b_stream_note_fault(
            &stream, A90_WP2_5B_FAULT_EFAULT, EFAULT, 0);
    else if (strcmp(mode, "escaped") == 0)
        add_result = a90_wp2_5b_stream_add_record(
            &stream, escaped, sizeof(escaped) - 1);
    else {
        add_result = a90_wp2_5b_stream_add_record(
            &stream, first, sizeof(first) - 1);
        if (add_result == 0) {
            if (strcmp(mode, "gap") == 0)
                add_result = a90_wp2_5b_stream_add_record(
                    &stream, gap, sizeof(gap) - 1);
            else
                add_result = a90_wp2_5b_stream_add_record(
                    &stream, second, sizeof(second) - 1);
        }
    }
    if (strcmp(mode, "efault") == 0)
        expected_failure = 1;
    if ((expected_failure &&
         ((strcmp(mode, "efault") != 0 && add_result == 0) ||
          !stream.faulted)) ||
        (!expected_failure && add_result != 0) ||
        a90_wp2_5b_stream_end(&stream, driver, close_binding) != 0)
        return 1;
    return 0;
}
#endif
