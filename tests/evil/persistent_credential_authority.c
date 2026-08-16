#define _GNU_SOURCE
#include <errno.h>
#include <linux/audit.h>
#include <linux/filter.h>
#include <linux/seccomp.h>
#include <linux/keyctl.h>
#include <sys/prctl.h>
#include <sys/syscall.h>
#include <sys/socket.h>
#include <sys/shm.h>
#include <sys/msg.h>
#include <sys/sem.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <stddef.h>

#ifndef SECCOMP_RET_KILL_PROCESS
#define SECCOMP_RET_KILL_PROCESS SECCOMP_RET_KILL
#endif

static int install_security_floor(void) {
    struct sock_filter filter[] = {
        BPF_STMT(BPF_LD | BPF_W | BPF_ABS, offsetof(struct seccomp_data, arch)),
        BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, AUDIT_ARCH_X86_64, 1, 0),
        BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_KILL_PROCESS),
        BPF_STMT(BPF_LD | BPF_W | BPF_ABS, offsetof(struct seccomp_data, nr)),
#ifdef __NR_shmget
        BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, __NR_shmget, 0, 1), BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ERRNO | EPERM),
#endif
#ifdef __NR_shmat
        BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, __NR_shmat, 0, 1), BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ERRNO | EPERM),
#endif
#ifdef __NR_shmctl
        BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, __NR_shmctl, 0, 1), BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ERRNO | EPERM),
#endif
#ifdef __NR_msgget
        BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, __NR_msgget, 0, 1), BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ERRNO | EPERM),
#endif
#ifdef __NR_msgsnd
        BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, __NR_msgsnd, 0, 1), BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ERRNO | EPERM),
#endif
#ifdef __NR_msgrcv
        BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, __NR_msgrcv, 0, 1), BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ERRNO | EPERM),
#endif
#ifdef __NR_msgctl
        BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, __NR_msgctl, 0, 1), BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ERRNO | EPERM),
#endif
#ifdef __NR_semget
        BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, __NR_semget, 0, 1), BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ERRNO | EPERM),
#endif
#ifdef __NR_semop
        BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, __NR_semop, 0, 1), BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ERRNO | EPERM),
#endif
#ifdef __NR_semctl
        BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, __NR_semctl, 0, 1), BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ERRNO | EPERM),
#endif
#ifdef __NR_mq_open
        BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, __NR_mq_open, 0, 1), BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ERRNO | EPERM),
#endif
#ifdef __NR_mq_unlink
        BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, __NR_mq_unlink, 0, 1), BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ERRNO | EPERM),
#endif
#ifdef __NR_add_key
        BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, __NR_add_key, 0, 1), BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ERRNO | EPERM),
#endif
#ifdef __NR_request_key
        BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, __NR_request_key, 0, 1), BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ERRNO | EPERM),
#endif
#ifdef __NR_keyctl
        BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, __NR_keyctl, 0, 1), BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ERRNO | EPERM),
#endif
#ifdef __NR_memfd_create
        BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, __NR_memfd_create, 0, 1), BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ERRNO | EPERM),
#endif
#ifdef __NR_socket
        BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, __NR_socket, 0, 1), BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ERRNO | EPERM),
#endif
        BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ALLOW),
    };
    struct sock_fprog prog = {
        .len = (unsigned short)(sizeof(filter) / sizeof(filter[0])),
        .filter = filter,
    };
    if (prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0) != 0)
        return -1;
    return syscall(SYS_seccomp, SECCOMP_SET_MODE_FILTER, 0, &prog);
}

static void result(const char *name, long rc) {
    int e = errno;
    printf("%-16s rc=%ld errno=%d (%s)\n", name, rc, e, strerror(e));
}

int main(int argc, char **argv) {
    if (argc > 1 && strcmp(argv[1], "--exec-filtered") == 0) {
        if (install_security_floor() != 0) {
            perror("install_security_floor");
            return 2;
        }
        execl(argv[0], argv[0], "--probe-filtered", NULL);
        perror("execl");
        return 2;
    }

    int filtered = argc > 1 &&
        (strcmp(argv[1], "--filtered") == 0 || strcmp(argv[1], "--probe-filtered") == 0);
    if (argc > 1 && strcmp(argv[1], "--filtered") == 0 && install_security_floor() != 0) {
        perror("install_security_floor");
        return 2;
    }

    printf("mode=%s\n", argc > 1 ? argv[1] : "baseline");

    errno = 0;
    long shmid = syscall(__NR_shmget, IPC_PRIVATE, 4096, IPC_CREAT | 0600);
    result("shmget", shmid);
    if (shmid >= 0 && !filtered)
        syscall(__NR_shmctl, shmid, IPC_RMID, NULL);

    errno = 0;
    long msgid = syscall(__NR_msgget, IPC_PRIVATE, IPC_CREAT | 0600);
    result("msgget", msgid);
    if (msgid >= 0 && !filtered)
        syscall(__NR_msgctl, msgid, IPC_RMID, NULL);

    errno = 0;
    long semid = syscall(__NR_semget, IPC_PRIVATE, 1, IPC_CREAT | 0600);
    result("semget", semid);
    if (semid >= 0 && !filtered)
        syscall(__NR_semctl, semid, 0, IPC_RMID, 0);

#ifdef __NR_mq_open
    char qname[64];
    snprintf(qname, sizeof(qname), "/polacore-%ld", (long)getpid());
    errno = 0;
    long mqd = syscall(__NR_mq_open, qname + 1, O_CREAT | O_RDWR, 0600, NULL);
    result("mq_open", mqd);
    if (mqd >= 0 && !filtered) {
        close((int)mqd);
        syscall(__NR_mq_unlink, qname + 1);
    }
#endif

#ifdef __NR_memfd_create
    errno = 0;
    long mfd = syscall(__NR_memfd_create, "polacore", 1U);
    result("memfd_create", mfd);
    if (mfd >= 0)
        close((int)mfd);
#endif

#ifdef __NR_socket
    errno = 0;
    long s = syscall(__NR_socket, AF_UNIX, SOCK_STREAM, 0);
    result("socket", s);
    if (s >= 0)
        close((int)s);
#endif

#ifdef __NR_add_key
    const char payload[] = "x";
    errno = 0;
    long key = syscall(__NR_add_key, "user", "polacore-test", payload, sizeof(payload), KEY_SPEC_USER_KEYRING);
    result("add_key", key);
    if (key >= 0 && !filtered)
        syscall(__NR_keyctl, KEYCTL_UNLINK, key, KEY_SPEC_USER_KEYRING);
#endif

#ifdef __NR_keyctl
    errno = 0;
    long kr = syscall(__NR_keyctl, KEYCTL_GET_KEYRING_ID, KEY_SPEC_USER_KEYRING, 1);
    result("keyctl", kr);
#endif

    return 0;
}
