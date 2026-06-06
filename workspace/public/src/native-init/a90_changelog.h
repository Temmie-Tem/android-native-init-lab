#ifndef A90_CHANGELOG_H
#define A90_CHANGELOG_H

#include <stddef.h>

#define A90_CHANGELOG_MAX_ENTRIES 96
#define A90_CHANGELOG_MAX_SERIES 16
#define A90_CHANGELOG_SERIES_LABEL_MAX 32
#define A90_CHANGELOG_SERIES_SUMMARY_MAX 32
#define A90_CHANGELOG_DETAIL_MAX 5

struct a90_changelog_entry {
    const char *label;
    const char *summary;
    const char *details[A90_CHANGELOG_DETAIL_MAX];
};

struct a90_changelog_series {
    const char *label;
    const char *summary;
    size_t count;
};

size_t a90_changelog_count(void);
const struct a90_changelog_entry *a90_changelog_entry_at(size_t index);
size_t a90_changelog_detail_count(const struct a90_changelog_entry *entry);
size_t a90_changelog_series_count(void);
const struct a90_changelog_series *a90_changelog_series_at(size_t index);
size_t a90_changelog_series_entry_count(size_t series_index);
size_t a90_changelog_entry_index_for_series(size_t series_index, size_t entry_index);

#endif
