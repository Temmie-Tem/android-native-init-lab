#ifndef S22PLUS_O2_LOADER_CORE_H
#define S22PLUS_O2_LOADER_CORE_H

#include <stddef.h>
#include <stdint.h>

#ifndef S22PLUS_O2_PLAN_TYPES_DEFINED
#define S22PLUS_O2_PLAN_TYPES_DEFINED
struct s22plus_o2_module_plan_entry {
    const char *filename;
    const char *runtime_name;
    const char *params;
};

struct s22plus_o2_bind_gate_entry {
    unsigned int order;
    const char *id;
    const char *kind;
    const char *path;
};
#endif

#define S22PLUS_O2_PROC_SCAN_CHUNK 4096U
#define S22PLUS_O2_RUNTIME_NAME_MAX 128U
#define S22PLUS_O2_EEXIST 17L

enum s22plus_o2_loader_status {
    S22PLUS_O2_OK = 0,
    S22PLUS_O2_ERR_ARGUMENT = -1,
    S22PLUS_O2_ERR_READ = -2,
    S22PLUS_O2_ERR_MALFORMED = -3,
    S22PLUS_O2_ERR_OPEN = -4,
    S22PLUS_O2_ERR_FINIT = -5,
    S22PLUS_O2_ERR_CLOSE = -6,
    S22PLUS_O2_GATE_MISSING = 1,
};

struct s22plus_o2_reader {
    void *context;
    long (*read)(void *context, void *buffer, size_t size);
};

struct s22plus_o2_proc_scan_result {
    uint64_t bytes_read;
    uint64_t read_calls;
    uint64_t lines_seen;
    size_t found_count;
    int eof_seen;
    int malformed;
};

struct s22plus_o2_module_loader_ops {
    void *context;
    long (*open_module)(void *context, const char *filename);
    long (*finit_module)(void *context, int fd, const char *params);
    long (*close_module)(void *context, int fd);
};

struct s22plus_o2_module_load_result {
    size_t attempted;
    size_t loaded;
    size_t already_loaded;
    size_t failed;
    size_t first_failure_index;
    long first_failure_rc;
    long first_close_rc;
};

struct s22plus_o2_gate_ops {
    void *context;
    int (*path_present)(void *context, const char *path);
};

struct s22plus_o2_gate_result {
    size_t checked;
    size_t first_missing_index;
    int callback_rc;
};

static inline size_t s22plus_o2_strlen(const char *text) {
    size_t length = 0;
    if (text == NULL) {
        return 0;
    }
    while (text[length] != '\0') {
        ++length;
    }
    return length;
}

static inline int s22plus_o2_streq(const char *left, const char *right) {
    size_t index = 0;
    if (left == NULL || right == NULL) {
        return 0;
    }
    while (left[index] != '\0' && right[index] != '\0') {
        if (left[index] != right[index]) {
            return 0;
        }
        ++index;
    }
    return left[index] == right[index];
}

static inline void s22plus_o2_zero_bytes(void *buffer, size_t size) {
    unsigned char *bytes = (unsigned char *)buffer;
    size_t index;
    for (index = 0; index < size; ++index) {
        bytes[index] = 0;
    }
}

static inline int s22plus_o2_validate_expected_names(const char *const *names, size_t count) {
    size_t outer;
    size_t inner;
    if (names == NULL || count == 0) {
        return S22PLUS_O2_ERR_ARGUMENT;
    }
    for (outer = 0; outer < count; ++outer) {
        size_t length = s22plus_o2_strlen(names[outer]);
        if (length == 0 || length >= S22PLUS_O2_RUNTIME_NAME_MAX) {
            return S22PLUS_O2_ERR_ARGUMENT;
        }
        for (inner = 0; inner < outer; ++inner) {
            if (s22plus_o2_streq(names[outer], names[inner])) {
                return S22PLUS_O2_ERR_ARGUMENT;
            }
        }
    }
    return S22PLUS_O2_OK;
}

static inline void s22plus_o2_match_proc_token(
    const char *token,
    const char *const *names,
    size_t count,
    unsigned char *found,
    struct s22plus_o2_proc_scan_result *result
) {
    size_t index;
    for (index = 0; index < count; ++index) {
        if (!found[index] && s22plus_o2_streq(token, names[index])) {
            found[index] = 1;
            ++result->found_count;
            return;
        }
    }
}

/*
 * Scans every byte through EOF. Only the first token of each /proc/modules
 * line is retained, so arbitrarily long dependency columns do not require a
 * whole-file or whole-line fixed buffer.
 */
static inline int s22plus_o2_scan_proc_modules(
    struct s22plus_o2_reader *reader,
    const char *const *names,
    size_t count,
    unsigned char *found,
    struct s22plus_o2_proc_scan_result *result
) {
    unsigned char chunk[S22PLUS_O2_PROC_SCAN_CHUNK];
    char token[S22PLUS_O2_RUNTIME_NAME_MAX];
    size_t token_length = 0;
    int in_first_token = 1;
    int line_has_data = 0;
    int matched_line = 0;
    int valid;

    if (reader == NULL || reader->read == NULL || found == NULL || result == NULL) {
        return S22PLUS_O2_ERR_ARGUMENT;
    }
    valid = s22plus_o2_validate_expected_names(names, count);
    if (valid != S22PLUS_O2_OK) {
        return valid;
    }
    s22plus_o2_zero_bytes(found, count);
    s22plus_o2_zero_bytes(result, sizeof(*result));

    for (;;) {
        long amount = reader->read(reader->context, chunk, sizeof(chunk));
        size_t index;
        ++result->read_calls;
        if (amount < 0) {
            return S22PLUS_O2_ERR_READ;
        }
        if (amount == 0) {
            if (line_has_data) {
                if (in_first_token) {
                    token[token_length] = '\0';
                    s22plus_o2_match_proc_token(token, names, count, found, result);
                }
                ++result->lines_seen;
            }
            result->eof_seen = 1;
            return S22PLUS_O2_OK;
        }
        if ((size_t)amount > sizeof(chunk)) {
            result->malformed = 1;
            return S22PLUS_O2_ERR_MALFORMED;
        }
        result->bytes_read += (uint64_t)amount;
        for (index = 0; index < (size_t)amount; ++index) {
            unsigned char value = chunk[index];
            if (value == 0) {
                result->malformed = 1;
                return S22PLUS_O2_ERR_MALFORMED;
            }
            if (value == '\n') {
                if (line_has_data) {
                    if (in_first_token && !matched_line) {
                        token[token_length] = '\0';
                        s22plus_o2_match_proc_token(token, names, count, found, result);
                    }
                    ++result->lines_seen;
                }
                token_length = 0;
                in_first_token = 1;
                line_has_data = 0;
                matched_line = 0;
                continue;
            }
            line_has_data = 1;
            if (!in_first_token) {
                continue;
            }
            if (value == ' ' || value == '\t') {
                if (token_length == 0) {
                    result->malformed = 1;
                    return S22PLUS_O2_ERR_MALFORMED;
                }
                token[token_length] = '\0';
                s22plus_o2_match_proc_token(token, names, count, found, result);
                matched_line = 1;
                in_first_token = 0;
                continue;
            }
            if (token_length + 1 >= sizeof(token)) {
                result->malformed = 1;
                return S22PLUS_O2_ERR_MALFORMED;
            }
            token[token_length++] = (char)value;
        }
    }
}

/* Executes in plan order and stops at the first open/finit/close failure. */
static inline int s22plus_o2_execute_module_plan(
    const struct s22plus_o2_module_plan_entry *plan,
    size_t count,
    struct s22plus_o2_module_loader_ops *ops,
    struct s22plus_o2_module_load_result *result
) {
    size_t index;
    if (plan == NULL || count == 0 || ops == NULL || result == NULL ||
        ops->open_module == NULL || ops->finit_module == NULL || ops->close_module == NULL) {
        return S22PLUS_O2_ERR_ARGUMENT;
    }
    s22plus_o2_zero_bytes(result, sizeof(*result));
    result->first_failure_index = count;
    for (index = 0; index < count; ++index) {
        long fd;
        long finit_rc;
        long close_rc;
        if (plan[index].filename == NULL || plan[index].runtime_name == NULL || plan[index].params == NULL ||
            plan[index].filename[0] == '\0' || plan[index].runtime_name[0] == '\0') {
            result->first_failure_index = index;
            result->first_failure_rc = S22PLUS_O2_ERR_ARGUMENT;
            ++result->failed;
            return S22PLUS_O2_ERR_ARGUMENT;
        }
        ++result->attempted;
        fd = ops->open_module(ops->context, plan[index].filename);
        if (fd < 0) {
            result->first_failure_index = index;
            result->first_failure_rc = fd;
            ++result->failed;
            return S22PLUS_O2_ERR_OPEN;
        }
        finit_rc = ops->finit_module(ops->context, (int)fd, plan[index].params);
        close_rc = ops->close_module(ops->context, (int)fd);
        if (finit_rc == 0) {
            ++result->loaded;
        } else if (finit_rc == -S22PLUS_O2_EEXIST) {
            ++result->already_loaded;
        } else {
            result->first_failure_index = index;
            result->first_failure_rc = finit_rc;
            ++result->failed;
            return S22PLUS_O2_ERR_FINIT;
        }
        if (close_rc < 0) {
            result->first_failure_index = index;
            result->first_failure_rc = close_rc;
            result->first_close_rc = close_rc;
            ++result->failed;
            return S22PLUS_O2_ERR_CLOSE;
        }
    }
    return S22PLUS_O2_OK;
}

/* Returns 0 only when all gates are present, 1 at the first missing gate. */
static inline int s22plus_o2_check_bind_gates(
    const struct s22plus_o2_bind_gate_entry *gates,
    size_t count,
    struct s22plus_o2_gate_ops *ops,
    struct s22plus_o2_gate_result *result
) {
    size_t index;
    if (gates == NULL || count == 0 || ops == NULL || result == NULL || ops->path_present == NULL) {
        return S22PLUS_O2_ERR_ARGUMENT;
    }
    s22plus_o2_zero_bytes(result, sizeof(*result));
    result->first_missing_index = count;
    for (index = 0; index < count; ++index) {
        int present;
        if (gates[index].id == NULL || gates[index].path == NULL || gates[index].path[0] == '\0') {
            result->first_missing_index = index;
            return S22PLUS_O2_ERR_ARGUMENT;
        }
        present = ops->path_present(ops->context, gates[index].path);
        result->callback_rc = present;
        ++result->checked;
        if (present < 0) {
            result->first_missing_index = index;
            return S22PLUS_O2_ERR_READ;
        }
        if (present == 0) {
            result->first_missing_index = index;
            return S22PLUS_O2_GATE_MISSING;
        }
    }
    return S22PLUS_O2_OK;
}

#endif
