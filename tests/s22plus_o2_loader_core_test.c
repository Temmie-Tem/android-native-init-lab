#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "s22plus_o2_loader_core.h"

struct memory_reader {
    const unsigned char *data;
    size_t size;
    size_t offset;
    size_t max_chunk;
};

static long memory_read(void *context, void *buffer, size_t size) {
    struct memory_reader *reader = (struct memory_reader *)context;
    size_t available;
    size_t amount;
    if (reader->offset == reader->size) {
        return 0;
    }
    available = reader->size - reader->offset;
    amount = size;
    if (amount > reader->max_chunk) {
        amount = reader->max_chunk;
    }
    if (amount > available) {
        amount = available;
    }
    memcpy(buffer, reader->data + reader->offset, amount);
    reader->offset += amount;
    return (long)amount;
}

static int test_proc_modules_eof_scan(void) {
    char *text = (char *)malloc(32768);
    size_t used = 0;
    unsigned int index;
    struct memory_reader memory;
    struct s22plus_o2_reader reader;
    struct s22plus_o2_proc_scan_result result;
    const char *names[] = {"dummy_0001", "target_after_16k"};
    unsigned char found[2];
    int rc;
    if (text == NULL) {
        return 1;
    }
    for (index = 0; index < 900; ++index) {
        int written = snprintf(text + used, 32768 - used, "dummy_%04u 0 0 - Live 0x0\n", index);
        if (written <= 0 || (size_t)written >= 32768 - used) {
            free(text);
            return 2;
        }
        used += (size_t)written;
    }
    if (used <= 16384) {
        free(text);
        return 3;
    }
    used += (size_t)snprintf(text + used, 32768 - used, "target_after_16k 0 0 - Live 0x0\n");
    memory.data = (const unsigned char *)text;
    memory.size = used;
    memory.offset = 0;
    memory.max_chunk = 257;
    reader.context = &memory;
    reader.read = memory_read;
    rc = s22plus_o2_scan_proc_modules(&reader, names, 2, found, &result);
    free(text);
    if (rc != S22PLUS_O2_OK || !result.eof_seen || result.bytes_read <= 16384 ||
        result.read_calls <= 4 || result.found_count != 2 || !found[0] || !found[1]) {
        return 4;
    }
    return 0;
}

struct loader_fixture {
    size_t opens;
    size_t finits;
    size_t closes;
};

static long fake_open(void *context, const char *filename) {
    struct loader_fixture *fixture = (struct loader_fixture *)context;
    (void)filename;
    ++fixture->opens;
    return (long)(100 + fixture->opens);
}

static long fake_finit(void *context, int fd, const char *params) {
    struct loader_fixture *fixture = (struct loader_fixture *)context;
    (void)fd;
    ++fixture->finits;
    if (fixture->finits == 1 && strcmp(params, "first=1") != 0) {
        return -99;
    }
    if (fixture->finits == 2) {
        return -S22PLUS_O2_EEXIST;
    }
    if (fixture->finits == 3) {
        return -5;
    }
    return 0;
}

static long fake_close(void *context, int fd) {
    struct loader_fixture *fixture = (struct loader_fixture *)context;
    (void)fd;
    ++fixture->closes;
    return 0;
}

static int test_plan_stops_at_first_failure(void) {
    const struct s22plus_o2_module_plan_entry plan[] = {
        {"one.ko", "one", "first=1"},
        {"two.ko", "two", ""},
        {"three.ko", "three", ""},
        {"never.ko", "never", ""},
    };
    struct loader_fixture fixture = {0, 0, 0};
    struct s22plus_o2_module_loader_ops ops = {&fixture, fake_open, fake_finit, fake_close};
    struct s22plus_o2_module_load_result result;
    int rc = s22plus_o2_execute_module_plan(plan, 4, &ops, &result);
    if (rc != S22PLUS_O2_ERR_FINIT || result.attempted != 3 || result.loaded != 1 ||
        result.already_loaded != 1 || result.failed != 1 || result.first_failure_index != 2 ||
        result.first_failure_rc != -5 || fixture.opens != 3 || fixture.finits != 3 || fixture.closes != 3) {
        return 1;
    }
    return 0;
}

struct gate_fixture {
    size_t calls;
};

static int fake_path_present(void *context, const char *path) {
    struct gate_fixture *fixture = (struct gate_fixture *)context;
    (void)path;
    ++fixture->calls;
    return fixture->calls == 1 ? 1 : 0;
}

static int test_gate_order_stops_at_first_missing(void) {
    const struct s22plus_o2_bind_gate_entry gates[] = {
        {1U, "first", "driver-bind-symlink", "/first"},
        {2U, "second", "driver-bind-symlink", "/second"},
        {3U, "never", "class-device", "/never"},
    };
    struct gate_fixture fixture = {0};
    struct s22plus_o2_gate_ops ops = {&fixture, fake_path_present};
    struct s22plus_o2_gate_result result;
    int rc = s22plus_o2_check_bind_gates(gates, 3, &ops, &result);
    if (rc != S22PLUS_O2_GATE_MISSING || result.checked != 2 ||
        result.first_missing_index != 1 || fixture.calls != 2) {
        return 1;
    }
    return 0;
}

int main(void) {
    int rc;
    rc = test_proc_modules_eof_scan();
    if (rc != 0) {
        fprintf(stderr, "proc_modules_test=%d\n", rc);
        return 1;
    }
    rc = test_plan_stops_at_first_failure();
    if (rc != 0) {
        fprintf(stderr, "module_plan_test=%d\n", rc);
        return 1;
    }
    rc = test_gate_order_stops_at_first_missing();
    if (rc != 0) {
        fprintf(stderr, "gate_test=%d\n", rc);
        return 1;
    }
    puts("s22plus_o2_loader_core_test=PASS");
    return 0;
}
