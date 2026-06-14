#include "a90_audio.h"

#include "a90_console.h"
#include "a90_util.h"

#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#include <strings.h>
#include <sys/stat.h>
#include <unistd.h>

#ifndef O_CLOEXEC
#define O_CLOEXEC 0
#endif

#define AUDIO_FW_DIR "/vendor/firmware_mnt/image"
#define AUDIO_BOOT_ATTR "/sys/kernel/boot_adsp/boot"
#define AUDIO_ADSP_BOOT_ONCE_TOKEN "AUD2_ONE_SHOT_ADSP_BOOT"
#define AUDIO_MAX_LISTED 8

static const char *yesno(bool value) {
    return value ? "yes" : "no";
}

static bool path_lstat(const char *path, struct stat *st) {
    return lstat(path, st) == 0;
}

static bool path_is_dir(const char *path) {
    struct stat st;

    return path_lstat(path, &st) && S_ISDIR(st.st_mode);
}

static int count_dir_entries(const char *path) {
    DIR *dir;
    struct dirent *entry;
    int count = 0;

    dir = opendir(path);
    if (dir == NULL) {
        return 0;
    }
    while ((entry = readdir(dir)) != NULL) {
        if (strcmp(entry->d_name, ".") == 0 || strcmp(entry->d_name, "..") == 0) {
            continue;
        }
        ++count;
    }
    closedir(dir);
    return count;
}

static bool name_contains_ci(const char *name, const char *needle) {
    size_t name_len = strlen(name);
    size_t needle_len = strlen(needle);
    size_t offset;

    if (needle_len == 0 || needle_len > name_len) {
        return false;
    }
    for (offset = 0; offset + needle_len <= name_len; ++offset) {
        size_t index;
        bool matched = true;

        for (index = 0; index < needle_len; ++index) {
            char lhs = name[offset + index];
            char rhs = needle[index];

            if (lhs >= 'A' && lhs <= 'Z') {
                lhs = (char)(lhs - 'A' + 'a');
            }
            if (rhs >= 'A' && rhs <= 'Z') {
                rhs = (char)(rhs - 'A' + 'a');
            }
            if (lhs != rhs) {
                matched = false;
                break;
            }
        }
        if (matched) {
            return true;
        }
    }
    return false;
}

static bool make_child_path(char *out, size_t out_size, const char *base, const char *leaf) {
    size_t base_len = strlen(base);
    size_t leaf_len = strlen(leaf);

    if (out_size == 0 || base_len + 1 + leaf_len + 1 > out_size) {
        if (out_size > 0) {
            out[0] = '\0';
        }
        return false;
    }
    memcpy(out, base, base_len);
    out[base_len] = '/';
    memcpy(out + base_len + 1, leaf, leaf_len + 1);
    return true;
}

static int count_dir_entries_matching(const char *path, const char *needle) {
    DIR *dir;
    struct dirent *entry;
    int count = 0;

    dir = opendir(path);
    if (dir == NULL) {
        return 0;
    }
    while ((entry = readdir(dir)) != NULL) {
        if (strcmp(entry->d_name, ".") == 0 || strcmp(entry->d_name, "..") == 0) {
            continue;
        }
        if (name_contains_ci(entry->d_name, needle)) {
            ++count;
        }
    }
    closedir(dir);
    return count;
}

static bool firmware_file_exists_ci(const char *wanted) {
    DIR *dir;
    struct dirent *entry;
    bool found = false;

    dir = opendir(AUDIO_FW_DIR);
    if (dir == NULL) {
        return false;
    }
    while ((entry = readdir(dir)) != NULL) {
        if (strcasecmp(entry->d_name, wanted) == 0) {
            found = true;
            break;
        }
    }
    closedir(dir);
    return found;
}

static void print_trimmed_or_missing(const char *key, const char *path) {
    char value[256];

    if (read_trimmed_text_file(path, value, sizeof(value)) == 0) {
        flatten_inline_text(value);
        a90_console_printf("audio.%s=%s\r\n", key, value[0] != '\0' ? value : "empty");
        return;
    }
    a90_console_printf("audio.%s=missing errno=%d\r\n", key, errno);
}

static void print_mode_line(const char *key, const char *path) {
    struct stat st;

    if (path_lstat(path, &st)) {
        a90_console_printf("audio.%s.exists=yes mode=%03o type=%s\r\n",
                           key,
                           (unsigned int)(st.st_mode & 0777),
                           S_ISDIR(st.st_mode) ? "dir" :
                           S_ISREG(st.st_mode) ? "file" :
                           S_ISLNK(st.st_mode) ? "symlink" : "other");
        return;
    }
    a90_console_printf("audio.%s.exists=no errno=%d\r\n", key, errno);
}

static void print_firmware_status(void) {
    int present_segments = 0;
    int index;

    a90_console_printf("audio.firmware_dir=%s exists=%s\r\n",
                       AUDIO_FW_DIR,
                       yesno(path_is_dir(AUDIO_FW_DIR)));
    a90_console_printf("audio.firmware.adsp_mdt=%s\r\n", yesno(firmware_file_exists_ci("adsp.mdt")));
    for (index = 0; index <= 16; ++index) {
        char name[32];

        snprintf(name, sizeof(name), "adsp.b%02d", index);
        if (firmware_file_exists_ci(name)) {
            ++present_segments;
        }
    }
    a90_console_printf("audio.firmware.adsp_segments_present=%d expected=17\r\n", present_segments);
    a90_console_printf("audio.firmware.adspr_jsn=%s\r\n", yesno(firmware_file_exists_ci("adspr.jsn")));
    a90_console_printf("audio.firmware.adspua_jsn=%s\r\n", yesno(firmware_file_exists_ci("adspua.jsn")));
}

static int count_adsp_segments(void) {
    int present_segments = 0;
    int index;

    for (index = 0; index <= 16; ++index) {
        char name[32];

        snprintf(name, sizeof(name), "adsp.b%02d", index);
        if (firmware_file_exists_ci(name)) {
            ++present_segments;
        }
    }
    return present_segments;
}

static void print_remoteproc_status(void) {
    DIR *dir;
    struct dirent *entry;
    int listed = 0;

    a90_console_printf("audio.remoteproc.count=%d\r\n", count_dir_entries("/sys/class/remoteproc"));
    dir = opendir("/sys/class/remoteproc");
    if (dir == NULL) {
        a90_console_printf("audio.remoteproc.open_errno=%d\r\n", errno);
        return;
    }
    while ((entry = readdir(dir)) != NULL && listed < AUDIO_MAX_LISTED) {
        char base[PATH_MAX];
        char name_path[PATH_MAX];
        char state_path[PATH_MAX];
        char name[128] = "missing";
        char state[128] = "missing";

        if (strcmp(entry->d_name, ".") == 0 || strcmp(entry->d_name, "..") == 0) {
            continue;
        }
        snprintf(base, sizeof(base), "/sys/class/remoteproc/%s", entry->d_name);
        if (!make_child_path(name_path, sizeof(name_path), base, "name") ||
            read_trimmed_text_file(name_path, name, sizeof(name)) < 0) {
            snprintf(name, sizeof(name), "missing");
        }
        if (!make_child_path(state_path, sizeof(state_path), base, "state") ||
            read_trimmed_text_file(state_path, state, sizeof(state)) < 0) {
            snprintf(state, sizeof(state), "missing");
        }
        flatten_inline_text(name);
        flatten_inline_text(state);
        a90_console_printf("audio.remoteproc.%d.node=%s name=%s state=%s\r\n",
                           listed,
                           entry->d_name,
                           name,
                           state);
        ++listed;
    }
    closedir(dir);
}

static void print_class_counts(void) {
    a90_console_printf("audio.rpmsg.count=%d adsp_like=%d cdsp_like=%d\r\n",
                       count_dir_entries("/sys/bus/rpmsg/devices"),
                       count_dir_entries_matching("/sys/bus/rpmsg/devices", "adsp"),
                       count_dir_entries_matching("/sys/bus/rpmsg/devices", "cdsp"));
    a90_console_printf("audio.rpmsg_class.count=%d\r\n", count_dir_entries("/sys/class/rpmsg"));
    a90_console_printf("audio.fastrpc_class.count=%d\r\n", count_dir_entries("/sys/class/fastrpc"));
    a90_console_printf("audio.sound_class.count=%d card_like=%d control_like=%d\r\n",
                       count_dir_entries("/sys/class/sound"),
                       count_dir_entries_matching("/sys/class/sound", "card"),
                       count_dir_entries_matching("/sys/class/sound", "control"));
    a90_console_printf("audio.dev_snd.count=%d control_like=%d pcm_like=%d\r\n",
                       count_dir_entries("/dev/snd"),
                       count_dir_entries_matching("/dev/snd", "controlC"),
                       count_dir_entries_matching("/dev/snd", "pcm"));
}

static void print_proc_asound(void) {
    char cards[512];

    if (read_trimmed_text_file("/proc/asound/cards", cards, sizeof(cards)) == 0) {
        flatten_inline_text(cards);
        a90_console_printf("audio.proc_asound_cards=%s\r\n", cards[0] != '\0' ? cards : "empty");
    } else {
        a90_console_printf("audio.proc_asound_cards=missing errno=%d\r\n", errno);
    }
}

static int audio_print_adsp_status(void) {
    a90_console_printf("audio.status.version=1\r\n");
    a90_console_printf("audio.status.read_only=1\r\n");
    print_trimmed_or_missing("firmware_class_path", "/sys/module/firmware_class/parameters/path");
    print_mode_line("boot_adsp_boot", AUDIO_BOOT_ATTR);
    print_firmware_status();
    print_remoteproc_status();
    print_class_counts();
    print_proc_asound();
    print_mode_line("dev_subsys_adsp", "/dev/subsys_adsp");
    print_mode_line("dev_adsprpc_smd", "/dev/adsprpc-smd");
    a90_console_printf("audio.status.activation_write_attempted=0\r\n");
    a90_console_printf("audio.status.audio_playback_attempted=0\r\n");
    return 0;
}

static int audio_adsp_boot_once(char **argv, int argc) {
    struct stat st;
    int segments;
    int fd;

    a90_console_printf("audio.adsp_boot_once.version=1\r\n");
    a90_console_printf("audio.adsp_boot_once.scope=AUD-2-liveness-only\r\n");
    a90_console_printf("audio.status.audio_playback_attempted=0\r\n");

    if (argc != 3 || argv == NULL || argv[2] == NULL ||
        strcmp(argv[2], AUDIO_ADSP_BOOT_ONCE_TOKEN) != 0) {
        a90_console_printf("audio.adsp_boot_once.refused=missing-token\r\n");
        a90_console_printf("audio.status.activation_write_attempted=0\r\n");
        a90_console_printf("usage: audio adsp-boot-once %s\r\n", AUDIO_ADSP_BOOT_ONCE_TOKEN);
        return -EPERM;
    }

    if (!path_lstat(AUDIO_BOOT_ATTR, &st)) {
        a90_console_printf("audio.adsp_boot_once.refused=no-boot-attr errno=%d\r\n", errno);
        a90_console_printf("audio.status.activation_write_attempted=0\r\n");
        return negative_errno_or(ENOENT);
    }
    if (!path_is_dir(AUDIO_FW_DIR)) {
        a90_console_printf("audio.adsp_boot_once.refused=no-firmware-dir\r\n");
        a90_console_printf("audio.status.activation_write_attempted=0\r\n");
        return -ENOENT;
    }
    if (!firmware_file_exists_ci("adsp.mdt")) {
        a90_console_printf("audio.adsp_boot_once.refused=no-adsp-mdt\r\n");
        a90_console_printf("audio.status.activation_write_attempted=0\r\n");
        return -ENOENT;
    }
    segments = count_adsp_segments();
    if (segments != 17) {
        a90_console_printf("audio.adsp_boot_once.refused=missing-adsp-segments present=%d expected=17\r\n",
                           segments);
        a90_console_printf("audio.status.activation_write_attempted=0\r\n");
        return -ENOENT;
    }
    if (count_dir_entries_matching("/sys/bus/rpmsg/devices", "adsp") > 0 ||
        count_dir_entries_matching("/sys/class/sound", "card") > 0 ||
        count_dir_entries_matching("/dev/snd", "controlC") > 0) {
        a90_console_printf("audio.adsp_boot_once.refused=already-up-or-sound-present\r\n");
        a90_console_printf("audio.status.activation_write_attempted=0\r\n");
        return -EALREADY;
    }

    fd = open(AUDIO_BOOT_ATTR, O_WRONLY | O_CLOEXEC);
    if (fd < 0) {
        a90_console_printf("audio.adsp_boot_once.write=open_failed errno=%d\r\n", errno);
        a90_console_printf("audio.status.activation_write_attempted=0\r\n");
        return negative_errno_or(EIO);
    }

    a90_console_printf("audio.status.activation_write_attempted=1\r\n");
    if (write_all_checked(fd, "1\n", 2) < 0) {
        a90_console_printf("audio.adsp_boot_once.write=failed errno=%d\r\n", errno);
        close(fd);
        return negative_errno_or(EIO);
    }
    if (close(fd) < 0) {
        a90_console_printf("audio.adsp_boot_once.write=close_failed errno=%d\r\n", errno);
        return negative_errno_or(EIO);
    }
    a90_console_printf("audio.adsp_boot_once.write=accepted\r\n");
    a90_console_printf("audio.adsp_boot_once.retry=forbidden\r\n");
    return 0;
}

int a90_audio_cmd(char **argv, int argc) {
    if (argc <= 1 ||
        (argc == 2 && (strcmp(argv[1], "adsp-status") == 0 || strcmp(argv[1], "status") == 0))) {
        return audio_print_adsp_status();
    }
    if (argc >= 2 && argv != NULL && argv[1] != NULL && strcmp(argv[1], "adsp-boot-once") == 0) {
        return audio_adsp_boot_once(argv, argc);
    }
    a90_console_printf("usage: audio [adsp-status|status|adsp-boot-once]\r\n");
    return -EINVAL;
}
