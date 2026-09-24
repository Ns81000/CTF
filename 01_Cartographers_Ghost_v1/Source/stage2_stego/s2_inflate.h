/*
 * s2_inflate.h -- minimal zlib-format inflate with preset-dictionary support
 * (RFC 1950 wrapper + RFC 1951 deflate), used by the Stage 2 stego utility to
 * test a candidate "reading" against the sheet's expected digest.
 *
 * Hand-rolled for the same reason carto_sha256.c is: stage binaries stay
 * fully static under musl with no external dependencies, and nothing about
 * the build depends on a glibc-built library being present.
 */
#ifndef CARTO_S2_INFLATE_H
#define CARTO_S2_INFLATE_H

#include <stddef.h>

/*
 * Inflate `in` (a complete zlib stream) into `out`.
 *
 * The stream's preset-dictionary bit (FDICT) is honoured: a stream that was
 * produced with a preset dictionary fails unless `dict` supplies it.  The
 * trailing adler32 is verified, so a wrong dictionary or a corrupted stream
 * is always reported as an error rather than as a plausible-looking result.
 *
 * `dict` may be NULL/0 for a stream that carries no dictionary; a dictionary
 * supplied for a stream that does not use one is ignored (matching zlib).
 *
 * Returns the number of bytes written, or (size_t)-1 on any error (bad
 * header, bad checksum, truncated stream, or output larger than out_cap).
 *
 * NOT reentrant: the 32 KiB history window is a static object.  Call it from
 * one thread at a time (every cartographer stage binary is single-threaded).
 */
size_t s2_inflate(const unsigned char *in, size_t in_len,
                  const unsigned char *dict, size_t dict_len,
                  unsigned char *out, size_t out_cap);

/* adler32 of a buffer (exposed for the internal unit tests). */
unsigned s2_adler32(const unsigned char *buf, size_t len);

#endif /* CARTO_S2_INFLATE_H */