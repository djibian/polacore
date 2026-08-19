#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <linux/openat2.h>
#include <sched.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

static const unsigned long long RESOLVE_POLICY =
    RESOLVE_BENEATH | RESOLVE_NO_MAGICLINKS | RESOLVE_NO_SYMLINKS | RESOLVE_NO_XDEV;

static int bounded_open(int rootfd, const char *path) {
    struct open_how how = {
        .flags = O_RDONLY | O_CLOEXEC | O_NOFOLLOW,
        .resolve = RESOLVE_POLICY,
    };
    return syscall(SYS_openat2, rootfd, path, &how, sizeof(how));
}

static void die(const char *what) { perror(what); exit(1); }

static void write_file(const char *path, const char *text) {
    int fd = open(path, O_WRONLY | O_CREAT | O_TRUNC | O_CLOEXEC, 0600);
    if (fd < 0) die(path);
    if (write(fd, text, strlen(text)) != (ssize_t)strlen(text)) die("write");
    if (close(fd)) die("close");
}

static int content_is(int fd, const char *expected) {
    char buf[128] = {0};
    ssize_t n = read(fd, buf, sizeof(buf) - 1);
    return n == (ssize_t)strlen(expected) && !memcmp(buf, expected, (size_t)n);
}

static void expect_denied(int rootfd, const char *name, const char *path) {
    errno = 0;
    int fd = bounded_open(rootfd, path);
    int saved = errno;
    if (fd >= 0) { close(fd); fprintf(stderr, "FAIL %s unexpectedly opened\n", name); exit(1); }
    printf("PASS %s denied errno=%d (%s)\n", name, saved, strerror(saved));
}

int main(int argc, char **argv) {
    if (argc == 3 && !strcmp(argv[1], "--mount-probe")) {
        int probe_root = open(argv[2], O_PATH | O_DIRECTORY | O_CLOEXEC);
        if (probe_root < 0) die("open mount probe root");
        errno = 0;
        int probe = bounded_open(probe_root, "mounted/secret");
        int saved = errno;
        if (probe >= 0) { close(probe); fprintf(stderr, "mount crossing opened\n"); return 1; }
        printf("mount crossing denied errno=%d (%s)\n", saved, strerror(saved));
        close(probe_root);
        return saved == EXDEV ? 0 : 1;
    }
    if (argc != 1) { fprintf(stderr, "usage: %s [--mount-probe ROOT]\n", argv[0]); return 2; }
    char base[] = "/tmp/p117.XXXXXX";
    if (!mkdtemp(base)) die("mkdtemp");
    char staging[256], moved[256];
    char inside[512], outside[256], linkpath[512], magic[512], race[512];
    snprintf(staging, sizeof(staging), "%s/staging", base);
    snprintf(moved, sizeof(moved), "%s/moved", base);
    snprintf(inside, sizeof(inside), "%s/file", staging);
    snprintf(outside, sizeof(outside), "%s/outside", base);
    snprintf(linkpath, sizeof(linkpath), "%s/escape", staging);
    snprintf(magic, sizeof(magic), "%s/magic", staging);
    snprintf(race, sizeof(race), "%s/race", staging);
    if (mkdir(staging, 0700)) die("mkdir staging");
    write_file(inside, "INSIDE\n");
    write_file(outside, "OUTSIDE_SECRET\n");

    int rootfd = open(staging, O_PATH | O_DIRECTORY | O_CLOEXEC);
    if (rootfd < 0) die("open staging root");
    int fd = bounded_open(rootfd, "file");
    if (fd < 0 && errno == ENOSYS) { puts("UNPROVEN openat2 unavailable"); return 77; }
    if (fd < 0 || !content_is(fd, "INSIDE\n")) die("bounded valid read");
    close(fd);
    printf("PASS valid fd-relative read flags=0x%llx\n", RESOLVE_POLICY);

    expect_denied(rootfd, "dotdot", "../outside");
    expect_denied(rootfd, "absolute", outside);
    if (symlink(outside, linkpath)) die("symlink escape");
    expect_denied(rootfd, "symlink", "escape");

    char proc_target[128];
    int outsidefd = open(outside, O_RDONLY | O_CLOEXEC);
    if (outsidefd < 0) die("open outside");
    snprintf(proc_target, sizeof(proc_target), "/proc/self/fd/%d", outsidefd);
    if (symlink(proc_target, magic)) die("symlink magic");
    expect_denied(rootfd, "proc-magiclink", "magic");

    if (rename(staging, moved)) die("rename ancestor");
    if (mkdir(staging, 0700)) die("replacement staging");
    write_file(inside, "OUTSIDE_SECRET\n");
    fd = bounded_open(rootfd, "file");
    if (fd < 0 || !content_is(fd, "INSIDE\n")) {
        fprintf(stderr, "FAIL stable root descriptor followed replacement ancestor\n"); return 1;
    }
    close(fd);
    puts("PASS ancestor rename retained original root object");

    /* Race in the directory still named by rootfd (now 'moved'). */
    snprintf(race, sizeof(race), "%s/race", moved);
    write_file(race, "INSIDE\n");
    pid_t child = fork();
    if (child < 0) die("fork");
    if (!child) {
        for (int i = 0; i < 20000; i++) {
            unlink(race);
            if (symlink(outside, race) && errno != EEXIST) _exit(3);
            unlink(race);
            write_file(race, "INSIDE\n");
        }
        _exit(0);
    }
    unsigned opened = 0, denied = 0;
    for (int i = 0; i < 20000; i++) {
        fd = bounded_open(rootfd, "race");
        if (fd < 0) { denied++; continue; }
        char observed[32] = {0};
        ssize_t observed_n = read(fd, observed, sizeof(observed));
        if (observed_n == (ssize_t)strlen("OUTSIDE_SECRET\n") &&
            !memcmp(observed, "OUTSIDE_SECRET\n", (size_t)observed_n)) {
            fprintf(stderr, "FAIL symlink-swap exposed outside content\n"); kill(child, SIGKILL); return 1;
        }
        close(fd); opened++;
    }
    int status;
    if (waitpid(child, &status, 0) < 0 || !WIFEXITED(status) || WEXITSTATUS(status))
        die("race child");
    printf("PASS symlink-swap race outside_reads=0 inside_reads=%u denied=%u\n", opened, denied);
    puts("RESULT PROVEN_BY_TEST exercised attacks could not escape staging");
    close(outsidefd); close(rootfd);
    return 0;
}
