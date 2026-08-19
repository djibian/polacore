#define _GNU_SOURCE

#include "source_acquisition.h"

#include <errno.h>
#include <fcntl.h>
#include <linux/openat2.h>
#include <stddef.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <unistd.h>

static const unsigned long long resolve_policy =
    RESOLVE_BENEATH | RESOLVE_NO_MAGICLINKS | RESOLVE_NO_SYMLINKS |
    RESOLVE_NO_XDEV;

static int canonical_relative_path(const char *path)
{
    const char *component;

    if (path == NULL || path[0] == '\0' || path[0] == '/') {
        return 0;
    }
    component = path;
    for (const char *cursor = path;; cursor++) {
        if (*cursor != '/' && *cursor != '\0') {
            continue;
        }
        size_t length = (size_t)(cursor - component);
        if (length == 0 || (length == 1 && component[0] == '.') ||
            (length == 2 && component[0] == '.' && component[1] == '.')) {
            return 0;
        }
        if (*cursor == '\0') {
            return 1;
        }
        component = cursor + 1;
    }
}

static int constrained_open(int root_fd, const char *path, unsigned long long flags)
{
    struct open_how how = {
        .flags = flags,
        .resolve = resolve_policy,
    };

    return (int)syscall(SYS_openat2, root_fd, path, &how, sizeof(how));
}

int pc_staging_root_open(struct pc_staging_root *root, const char *path)
{
    int probe;

    if (root == NULL || path == NULL) {
        errno = EINVAL;
        return -1;
    }
    root->fd = -1;
    root->fd = open(path, O_PATH | O_DIRECTORY | O_CLOEXEC);
    if (root->fd < 0) {
        return -1;
    }

    /* Fail during initialization if openat2 or any requested resolve bit is unsupported. */
    probe = constrained_open(root->fd, ".", O_PATH | O_DIRECTORY | O_CLOEXEC);
    if (probe < 0) {
        int saved_errno = errno;
        close(root->fd);
        root->fd = -1;
        errno = saved_errno;
        return -1;
    }
    close(probe);
    return 0;
}

void pc_staging_root_close(struct pc_staging_root *root)
{
    if (root != NULL && root->fd >= 0) {
        close(root->fd);
        root->fd = -1;
    }
}

int pc_acquire_regular(const struct pc_staging_root *root, const char *relative_path)
{
    struct stat acquired;
    int fd;

    if (root == NULL || root->fd < 0 || !canonical_relative_path(relative_path)) {
        errno = EINVAL;
        return -1;
    }

    fd = constrained_open(root->fd, relative_path,
                          O_RDONLY | O_NONBLOCK | O_NOFOLLOW | O_CLOEXEC);
    if (fd < 0) {
        return -1;
    }
    if (fstat(fd, &acquired) < 0) {
        int saved_errno = errno;
        close(fd);
        errno = saved_errno;
        return -1;
    }

    /* This increment's complete object-type allowlist is regular files only. */
    if (!S_ISREG(acquired.st_mode)) {
        close(fd);
        errno = EACCES;
        return -1;
    }
    return fd;
}
