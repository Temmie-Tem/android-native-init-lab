/*
 * A90 V2733 App Type Config atomic ALSA control writer.
 *
 * This bypasses tinymix's per-index integer writes and submits one complete
 * SNDRV_CTL_IOCTL_ELEM_WRITE for the write-only Qualcomm "App Type Config"
 * multi-value control.
 */

#include <errno.h>
#include <fcntl.h>
#include <getopt.h>
#include <linux/ioctl.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <unistd.h>

#include <sound/asound.h>

#define A90_APP_TYPE_CFG_MAX_VALUES 128
#define A90_APP_TYPE_CFG_MAX_ENTRIES 42
#define A90_DEFAULT_CARD 0
#define A90_DEFAULT_CONTROL "App Type Config"
#define A90_DEFAULT_APP_TYPE 69941L
#define A90_DEFAULT_SAMPLE_RATE 48000L
#define A90_DEFAULT_BIT_WIDTH 16L

struct app_type_entry {
    long app_type;
    long sample_rate;
    long bit_width;
};

struct options {
    int card;
    unsigned int numid;
    const char *control;
    struct app_type_entry entries[A90_APP_TYPE_CFG_MAX_ENTRIES];
    unsigned int entry_count;
    bool dry_run;
};

static void usage(const char *prog) {
    fprintf(stderr,
            "usage: %s [--card N] [--control NAME|--numid N] "
            "[--entry APP:RATE:WIDTH] [--dry-run]\n",
            prog);
}

static int parse_long(const char *text, long *out) {
    char *end = NULL;
    errno = 0;
    long value = strtol(text, &end, 0);
    if (errno || end == text || *end != '\0') {
        return -1;
    }
    *out = value;
    return 0;
}

static int parse_uint(const char *text, unsigned int *out) {
    long value = 0;
    if (parse_long(text, &value) || value < 0 || value > 0xffffffffL) {
        return -1;
    }
    *out = (unsigned int)value;
    return 0;
}

static int parse_entry(const char *text, struct app_type_entry *entry) {
    char buffer[128];
    char *first = NULL;
    char *second = NULL;
    char *third = NULL;

    if (strlen(text) >= sizeof(buffer)) {
        return -1;
    }
    strcpy(buffer, text);
    first = buffer;
    second = strchr(first, ':');
    if (!second) {
        return -1;
    }
    *second++ = '\0';
    third = strchr(second, ':');
    if (!third) {
        return -1;
    }
    *third++ = '\0';
    if (strchr(third, ':')) {
        return -1;
    }
    return parse_long(first, &entry->app_type) ||
           parse_long(second, &entry->sample_rate) ||
           parse_long(third, &entry->bit_width);
}

static int parse_args(int argc, char **argv, struct options *opts) {
    static const struct option long_opts[] = {
        {"card", required_argument, NULL, 'c'},
        {"control", required_argument, NULL, 'n'},
        {"numid", required_argument, NULL, 'i'},
        {"entry", required_argument, NULL, 'e'},
        {"dry-run", no_argument, NULL, 'd'},
        {"help", no_argument, NULL, 'h'},
        {NULL, 0, NULL, 0},
    };

    memset(opts, 0, sizeof(*opts));
    opts->card = A90_DEFAULT_CARD;
    opts->control = A90_DEFAULT_CONTROL;
    opts->entries[0].app_type = A90_DEFAULT_APP_TYPE;
    opts->entries[0].sample_rate = A90_DEFAULT_SAMPLE_RATE;
    opts->entries[0].bit_width = A90_DEFAULT_BIT_WIDTH;
    opts->entry_count = 1;

    int ch;
    while ((ch = getopt_long(argc, argv, "c:n:i:e:dh", long_opts, NULL)) != -1) {
        switch (ch) {
        case 'c': {
            long card = 0;
            if (parse_long(optarg, &card) || card < 0 || card > 31) {
                fprintf(stderr, "A90_APP_TYPE_CFG_BAD_CARD value=%s\n", optarg);
                return 2;
            }
            opts->card = (int)card;
            break;
        }
        case 'n':
            opts->control = optarg;
            break;
        case 'i':
            if (parse_uint(optarg, &opts->numid) || opts->numid == 0) {
                fprintf(stderr, "A90_APP_TYPE_CFG_BAD_NUMID value=%s\n", optarg);
                return 2;
            }
            break;
        case 'e':
            if (opts->entry_count == 1 &&
                opts->entries[0].app_type == A90_DEFAULT_APP_TYPE &&
                opts->entries[0].sample_rate == A90_DEFAULT_SAMPLE_RATE &&
                opts->entries[0].bit_width == A90_DEFAULT_BIT_WIDTH) {
                opts->entry_count = 0;
            }
            if (opts->entry_count >= A90_APP_TYPE_CFG_MAX_ENTRIES) {
                fprintf(stderr, "A90_APP_TYPE_CFG_TOO_MANY_ENTRIES\n");
                return 2;
            }
            if (parse_entry(optarg, &opts->entries[opts->entry_count])) {
                fprintf(stderr, "A90_APP_TYPE_CFG_BAD_ENTRY value=%s\n", optarg);
                return 2;
            }
            opts->entry_count++;
            break;
        case 'd':
            opts->dry_run = true;
            break;
        case 'h':
            usage(argv[0]);
            return 1;
        default:
            usage(argv[0]);
            return 2;
        }
    }
    if (optind != argc) {
        usage(argv[0]);
        return 2;
    }
    if (opts->entry_count == 0 || opts->entry_count * 3 + 1 > A90_APP_TYPE_CFG_MAX_VALUES) {
        fprintf(stderr, "A90_APP_TYPE_CFG_BAD_ENTRY_COUNT count=%u\n", opts->entry_count);
        return 2;
    }
    return 0;
}

static int open_control_device(int card) {
    char path[64];
    snprintf(path, sizeof(path), "/dev/snd/controlC%d", card);
    int fd = open(path, O_RDWR | O_CLOEXEC);
    if (fd < 0) {
        fprintf(stderr, "A90_APP_TYPE_CFG_OPEN_FAIL path=%s errno=%d\n", path, errno);
    }
    return fd;
}

static int resolve_control_by_name(int fd, const char *name, struct snd_ctl_elem_id *id) {
    struct snd_ctl_elem_list list;
    memset(&list, 0, sizeof(list));
    if (ioctl(fd, SNDRV_CTL_IOCTL_ELEM_LIST, &list) < 0) {
        fprintf(stderr, "A90_APP_TYPE_CFG_LIST_COUNT_FAIL errno=%d\n", errno);
        return -1;
    }
    unsigned int count = list.count;
    if (count == 0 || count > 8192) {
        fprintf(stderr, "A90_APP_TYPE_CFG_LIST_BAD_COUNT count=%u\n", list.count);
        return -1;
    }
    struct snd_ctl_elem_id *ids = calloc(count, sizeof(*ids));
    if (!ids) {
        fprintf(stderr, "A90_APP_TYPE_CFG_ALLOC_FAIL count=%u\n", count);
        return -1;
    }
    memset(&list, 0, sizeof(list));
    list.space = count;
    list.pids = ids;
    if (ioctl(fd, SNDRV_CTL_IOCTL_ELEM_LIST, &list) < 0) {
        fprintf(stderr, "A90_APP_TYPE_CFG_LIST_IDS_FAIL errno=%d\n", errno);
        free(ids);
        return -1;
    }
    for (unsigned int index = 0; index < list.used; index++) {
        if (strncmp((const char *)ids[index].name, name, sizeof(ids[index].name)) == 0) {
            *id = ids[index];
            free(ids);
            return 0;
        }
    }
    fprintf(stderr, "A90_APP_TYPE_CFG_RESOLVE_FAIL name=\"%s\" used=%u\n", name, list.used);
    free(ids);
    return -1;
}

static int resolve_control(int fd, const struct options *opts, struct snd_ctl_elem_id *id) {
    memset(id, 0, sizeof(*id));
    if (opts->numid) {
        id->numid = opts->numid;
        return 0;
    }
    return resolve_control_by_name(fd, opts->control, id);
}

static int validate_control(int fd, struct snd_ctl_elem_id *id, struct snd_ctl_elem_info *info) {
    memset(info, 0, sizeof(*info));
    info->id = *id;
    if (ioctl(fd, SNDRV_CTL_IOCTL_ELEM_INFO, info) < 0) {
        fprintf(stderr, "A90_APP_TYPE_CFG_INFO_FAIL errno=%d numid=%u\n", errno, id->numid);
        return -1;
    }
    *id = info->id;
    if (info->type != SNDRV_CTL_ELEM_TYPE_INTEGER) {
        fprintf(stderr, "A90_APP_TYPE_CFG_BAD_TYPE type=%u\n", info->type);
        return -1;
    }
    if (info->count < A90_APP_TYPE_CFG_MAX_VALUES) {
        fprintf(stderr, "A90_APP_TYPE_CFG_BAD_COUNT count=%u\n", info->count);
        return -1;
    }
    return 0;
}

static void fill_value(struct snd_ctl_elem_value *value, const struct options *opts, const struct snd_ctl_elem_id *id) {
    memset(value, 0, sizeof(*value));
    value->id = *id;
    value->value.integer.value[0] = opts->entry_count;
    for (unsigned int index = 0; index < opts->entry_count; index++) {
        unsigned int base = 1 + index * 3;
        value->value.integer.value[base + 0] = opts->entries[index].app_type;
        value->value.integer.value[base + 1] = opts->entries[index].sample_rate;
        value->value.integer.value[base + 2] = opts->entries[index].bit_width;
    }
}

static void print_payload(const struct options *opts, const struct snd_ctl_elem_id *id, const struct snd_ctl_elem_info *info) {
    printf("A90_APP_TYPE_CFG_CONTROL numid=%u count=%u name=\"%s\"\n",
           id->numid, info->count, (const char *)id->name);
    printf("A90_APP_TYPE_CFG_PAYLOAD num_entries=%u", opts->entry_count);
    for (unsigned int index = 0; index < opts->entry_count; index++) {
        printf(" entry%u=%ld:%ld:%ld", index, opts->entries[index].app_type,
               opts->entries[index].sample_rate, opts->entries[index].bit_width);
    }
    printf("\n");
}

int main(int argc, char **argv) {
    struct options opts;
    int parse_rc = parse_args(argc, argv, &opts);
    if (parse_rc != 0) {
        return parse_rc == 1 ? 0 : parse_rc;
    }

    printf("A90_APP_TYPE_CFG_WRITER_BEGIN\n");
    int fd = open_control_device(opts.card);
    if (fd < 0) {
        return 10;
    }

    struct snd_ctl_elem_id id;
    if (resolve_control(fd, &opts, &id) < 0) {
        close(fd);
        return 11;
    }
    struct snd_ctl_elem_info info;
    if (validate_control(fd, &id, &info) < 0) {
        close(fd);
        return 12;
    }
    print_payload(&opts, &id, &info);

    struct snd_ctl_elem_value value;
    fill_value(&value, &opts, &id);
    if (opts.dry_run) {
        close(fd);
        printf("A90_APP_TYPE_CFG_DRY_RUN_OK\n");
        return 0;
    }
    if (ioctl(fd, SNDRV_CTL_IOCTL_ELEM_WRITE, &value) < 0) {
        fprintf(stderr, "A90_APP_TYPE_CFG_WRITE_FAIL errno=%d\n", errno);
        close(fd);
        return 13;
    }
    close(fd);
    printf("A90_APP_TYPE_CFG_WRITE_OK num_entries=%u\n", opts.entry_count);
    return 0;
}
