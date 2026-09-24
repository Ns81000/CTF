#include "state.h"
#include "../core/carto_sha256.h"
#include "../core/sha256ctr.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
#include <fcntl.h>
#include <limits.h>
#include <sys/file.h>
#include <sys/stat.h>

static const uint8_t ST_MAGIC[8] = { 'P', 'R', 'M', 'B', 'H', 'S', 'V', '1' };

static void put_le32(uint8_t out[4], uint32_t v)
{
    int i;
    for (i = 0; i < 4; i++)
        out[i] = (uint8_t)(v >> (8 * i));
}

static uint32_t get_le32(const uint8_t in[4])
{
    return (uint32_t)in[0] | ((uint32_t)in[1] << 8) |
           ((uint32_t)in[2] << 16) | ((uint32_t)in[3] << 24);
}

void prambh_now_ms(uint64_t *wall_ms, uint64_t *mono_ms)
{
    struct timespec ts;
    if (wall_ms) {
        clock_gettime(CLOCK_REALTIME, &ts);
        *wall_ms = (uint64_t)ts.tv_sec * 1000ull + (uint64_t)ts.tv_nsec / 1000000ull;
    }
    if (mono_ms) {
        clock_gettime(CLOCK_MONOTONIC, &ts);
        *mono_ms = (uint64_t)ts.tv_sec * 1000ull + (uint64_t)ts.tv_nsec / 1000000ull;
    }
}

int prambh_package_root(char *out, size_t outlen)
{
    char exe[PATH_MAX];
    ssize_t n = readlink("/proc/self/exe", exe, sizeof(exe) - 1);
    char *p;
    if (n <= 0)
        return -1;
    exe[n] = '\0';
    p = strrchr(exe, '/');          /* strip tool name */
    if (!p) return -1;
    *p = '\0';
    p = strrchr(exe, '/');          /* strip stage dir */
    if (!p) return -1;
    *p = '\0';
    if (strlen(exe) + 1 > outlen)
        return -1;
    strcpy(out, exe);
    return 0;
}

static void state_path(const char *root, char *out, size_t outlen)
{
    snprintf(out, outlen, "%s/%s", root, PRAMBH_STATE_NAME);
}

static void machine_id(char *out, size_t outlen)
{
    const char *paths[] = { "/etc/machine-id", "/var/lib/dbus/machine-id", NULL };
    int i;
    out[0] = '\0';
    for (i = 0; paths[i]; i++) {
        FILE *f = fopen(paths[i], "r");
        if (f) {
            if (fgets(out, (int)outlen, f)) {
                fclose(f);
                out[strcspn(out, "\r\n")] = '\0';
                if (out[0])
                    return;
            } else {
                fclose(f);
            }
        }
    }
    if (gethostname(out, outlen) != 0)
        snprintf(out, outlen, "prambh-unknown-machine");
}

void prambh_device_key(const char *root, uint8_t out[32])
{
    static const char label[] = "prambh:state:key:v1";
    char mid[128], rpath[PATH_MAX];
    uint8_t buf[sizeof(label) + sizeof(mid) + PATH_MAX];
    size_t n = 0;

    machine_id(mid, sizeof mid);
    if (!realpath(root, rpath))
        snprintf(rpath, sizeof rpath, "%s", root);

    memcpy(buf + n, label, sizeof(label) - 1); n += sizeof(label) - 1;
    memcpy(buf + n, mid, strlen(mid)); n += strlen(mid);
    memcpy(buf + n, rpath, strlen(rpath)); n += strlen(rpath);
    carto_sha256(buf, n, out);
    memset(buf, 0, sizeof buf);
}

uint64_t prambh_state_get64(const prambh_state *st, size_t off)
{
    return prambh_get_le64(st->bytes + off);
}

void prambh_state_set64(prambh_state *st, size_t off, uint64_t v)
{
    prambh_put_le64(st->bytes + off, v);
}

void prambh_state_init_fresh(prambh_state *st)
{
    uint64_t wall;
    memset(st->bytes, 0, sizeof st->bytes);
    memcpy(st->bytes + ST_OFF_MAGIC, ST_MAGIC, 8);
    put_le32(st->bytes + ST_OFF_VERSION, PRAMBH_STATE_VERSION);
    prambh_now_ms(&wall, NULL);
    prambh_put_le64(st->bytes + ST_OFF_FIRST_RUN, wall);
}

static int state_sealed_ok(const char *root, const prambh_state *st)
{
    uint8_t key[32], mac[32];
    if (memcmp(st->bytes + ST_OFF_MAGIC, ST_MAGIC, 8) != 0)
        return 0;
    if (get_le32(st->bytes + ST_OFF_VERSION) != PRAMBH_STATE_VERSION)
        return 0;
    prambh_device_key(root, key);
    carto_hmac_sha256(key, 32, st->bytes, ST_OFF_HMAC, mac);
    return carto_ct_equal(mac, st->bytes + ST_OFF_HMAC, 32);
}

int prambh_state_load(const char *root, prambh_state *st)
{
    char path[PATH_MAX];
    int fd;
    struct stat sb;
    ssize_t got;
    int ok = 0;

    state_path(root, path, sizeof path);
    fd = open(path, O_RDONLY);
    if (fd >= 0) {
        flock(fd, LOCK_SH);
        if (fstat(fd, &sb) == 0 && sb.st_size == PRAMBH_STATE_SIZE) {
            got = read(fd, st->bytes, PRAMBH_STATE_SIZE);
            if (got == PRAMBH_STATE_SIZE && state_sealed_ok(root, st))
                ok = 1;
        }
        flock(fd, LOCK_UN);
        close(fd);
    }
    if (!ok)
        prambh_state_init_fresh(st);
    return ok;
}

int prambh_state_save(const char *root, prambh_state *st)
{
    char path[PATH_MAX];
    uint8_t key[32];
    int fd;
    uint64_t ctr;

    state_path(root, path, sizeof path);
    fd = open(path, O_RDWR | O_CREAT, 0600);
    if (fd < 0)
        return -1;
    flock(fd, LOCK_EX);
    ctr = prambh_state_get64(st, ST_OFF_COUNTER) + 1;
    prambh_state_set64(st, ST_OFF_COUNTER, ctr);
    prambh_device_key(root, key);
    carto_hmac_sha256(key, 32, st->bytes, ST_OFF_HMAC, st->bytes + ST_OFF_HMAC);
    if (lseek(fd, 0, SEEK_SET) < 0 ||
        write(fd, st->bytes, PRAMBH_STATE_SIZE) != PRAMBH_STATE_SIZE) {
        flock(fd, LOCK_UN);
        close(fd);
        return -1;
    }
    fsync(fd);
    flock(fd, LOCK_UN);
    close(fd);
    return 0;
}

int prambh_pacing_allow(uint64_t now_wall, uint64_t now_mono,
                        uint64_t last_wall, uint64_t last_mono,
                        uint64_t pace_ms)
{
    uint64_t dw, dm;
    if (last_wall == 0 && last_mono == 0)
        return 1;
    if (now_wall < last_wall || now_mono < last_mono)
        return 0;
    dw = now_wall - last_wall;
    dm = now_mono - last_mono;
    return dw >= pace_ms && dm >= pace_ms;
}
