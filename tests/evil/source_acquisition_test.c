#define _GNU_SOURCE

#include "../../security/source_acquisition.h"

#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/un.h>
#include <unistd.h>

static void fail(const char *operation)
{
    perror(operation);
    exit(1);
}

static void write_file(const char *path, const char *contents)
{
    int fd = open(path, O_WRONLY | O_CREAT | O_TRUNC | O_CLOEXEC, 0600);
    size_t length = strlen(contents);
    if (fd < 0 || write(fd, contents, length) != (ssize_t)length || close(fd) < 0) {
        fail("write file");
    }
}

static void expect_rejected(const struct pc_staging_root *root, const char *name,
                            const char *path)
{
    int fd = pc_acquire_regular(root, path);
    if (fd >= 0) {
        close(fd);
        fprintf(stderr, "FAIL %s was accepted\n", name);
        exit(1);
    }
    printf("PROVEN_BY_TEST rejected %s errno=%d\n", name, errno);
}

static void expect_contents(int fd, const char *expected)
{
    char buffer[64];
    ssize_t length = read(fd, buffer, sizeof(buffer));
    if (length != (ssize_t)strlen(expected) ||
        memcmp(buffer, expected, (size_t)length) != 0) {
        fprintf(stderr, "FAIL acquired descriptor returned unexpected data\n");
        exit(1);
    }
}

static int mount_probe(const char *path)
{
    struct pc_staging_root root = {.fd = -1};
    int fd;
    if (pc_staging_root_open(&root, path) < 0) {
        fail("open mount-probe root");
    }
    fd = pc_acquire_regular(&root, "mounted/secret");
    if (fd >= 0 || errno != EXDEV) {
        if (fd >= 0) {
            close(fd);
        }
        fprintf(stderr, "FAIL mount crossing was not rejected with EXDEV\n");
        return 1;
    }
    puts("PROVEN_BY_TEST mount crossing rejected with EXDEV");
    pc_staging_root_close(&root);
    return 0;
}

int main(int argc, char **argv)
{
    struct pc_staging_root root = {.fd = -1};
    char base[] = "/tmp/polacore-acquire.XXXXXX";
    char staging[256], moved[256], outside[256], path[512];
    int acquired;

    if (argc == 3 && strcmp(argv[1], "--mount-probe") == 0) {
        return mount_probe(argv[2]);
    }
    if (argc != 1) {
        return 2;
    }
    if (mkdtemp(base) == NULL) {
        fail("mkdtemp");
    }
    snprintf(staging, sizeof(staging), "%s/staging", base);
    snprintf(moved, sizeof(moved), "%s/moved", base);
    snprintf(outside, sizeof(outside), "%s/outside", base);
    if (mkdir(staging, 0700) < 0) {
        fail("mkdir staging");
    }
    snprintf(path, sizeof(path), "%s/file", staging);
    write_file(path, "ORIGINAL\n");
    write_file(outside, "OUTSIDE\n");

    if (pc_staging_root_open(&root, staging) < 0) {
        if (errno == ENOSYS || errno == EINVAL) {
            fprintf(stderr, "UNPROVEN openat2 strict semantics unavailable errno=%d\n", errno);
            return 77;
        }
        fail("pc_staging_root_open");
    }
    expect_rejected(&root, "lexical escape", "../outside");
    expect_rejected(&root, "embedded lexical escape", "dir/../../outside");
    expect_rejected(&root, "dot component", "./file");
    expect_rejected(&root, "empty component", "dir//file");
    expect_rejected(&root, "absolute escape", outside);

    snprintf(path, sizeof(path), "%s/link", staging);
    if (symlink(outside, path) < 0) {
        fail("symlink");
    }
    expect_rejected(&root, "outside symlink", "link");

    if (rename(staging, moved) < 0 || mkdir(staging, 0700) < 0) {
        fail("ancestor replacement");
    }
    snprintf(path, sizeof(path), "%s/file", staging);
    write_file(path, "OUTSIDE\n");
    acquired = pc_acquire_regular(&root, "file");
    if (acquired < 0) {
        fail("acquire through stable root");
    }
    expect_contents(acquired, "ORIGINAL\n");
    close(acquired);
    puts("PROVEN_BY_TEST ancestor replacement retained stable root");

    acquired = pc_acquire_regular(&root, "file");
    if (acquired < 0) {
        fail("acquire before substitution");
    }
    snprintf(path, sizeof(path), "%s/file", moved);
    if (unlink(path) < 0) {
        fail("unlink before substitution");
    }
    write_file(path, "SUBSTITUTE\n");
    expect_contents(acquired, "ORIGINAL\n");
    close(acquired);
    puts("PROVEN_BY_TEST in-root substitution did not change acquired descriptor");

    snprintf(path, sizeof(path), "%s/fifo", moved);
    if (mkfifo(path, 0600) < 0) {
        fail("mkfifo");
    }
    expect_rejected(&root, "FIFO object type", "fifo");
    snprintf(path, sizeof(path), "%s/directory", moved);
    if (mkdir(path, 0700) < 0) {
        fail("mkdir object");
    }
    expect_rejected(&root, "directory object type", "directory");

    snprintf(path, sizeof(path), "%s/socket", moved);
    int socket_fd = socket(AF_UNIX, SOCK_STREAM | SOCK_CLOEXEC, 0);
    struct sockaddr_un address = {.sun_family = AF_UNIX};
    if (socket_fd < 0 || strlen(path) >= sizeof(address.sun_path)) {
        fail("socket");
    }
    strcpy(address.sun_path, path);
    if (bind(socket_fd, (struct sockaddr *)&address, sizeof(address)) < 0) {
        fail("bind socket");
    }
    expect_rejected(&root, "socket object type", "socket");
    close(socket_fd);

    pc_staging_root_close(&root);
    puts("RESULT PROVEN_BY_TEST narrow source acquisition cases passed");
    puts("RESULT UNPROVEN recursive traversal, P118 identity, P119, and P120");
    return 0;
}
