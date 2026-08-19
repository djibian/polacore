#ifndef POLACORE_SOURCE_ACQUISITION_H
#define POLACORE_SOURCE_ACQUISITION_H

struct pc_staging_root {
    int fd;
};

/* Opens and capability-probes a Linux staging root. */
int pc_staging_root_open(struct pc_staging_root *root, const char *path);
void pc_staging_root_close(struct pc_staging_root *root);

/*
 * Acquires one regular file beneath root. The returned descriptor is the same
 * descriptor inspected by fstat(), and no file data is read by this helper.
 */
int pc_acquire_regular(const struct pc_staging_root *root, const char *relative_path);

#endif
