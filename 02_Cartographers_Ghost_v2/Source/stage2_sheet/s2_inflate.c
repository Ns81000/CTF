/*
 * s2_inflate.c -- hand-rolled zlib-format inflate (see s2_inflate.h).
 * Phase 3 deliverable.  Tables follow RFC 1951 section 3.2.5.
 */
#include "s2_inflate.h"

#include <string.h>

#define S2_WBITS    15
#define S2_WINSIZE  (1u << S2_WBITS)      /* 32768 */
#define S2_MAXBITS  15
#define S2_MAXLCODES 286
#define S2_MAXDCODES 30
#define S2_MAXCODES (S2_MAXLCODES + S2_MAXDCODES)
#define S2_MAXCLCODES 19

typedef struct {
    const unsigned char *in;
    size_t in_len;
    size_t in_pos;
    unsigned bitbuf;
    int bitcnt;
    unsigned char win[S2_WINSIZE];
    size_t win_pos;
    size_t win_len;
    unsigned char *out;
    size_t out_cap;
    size_t out_len;
    int err;
} s2_io;

/* The history window makes this struct too large for a comfortable stack
 * frame, so it is a single static instance (documented not-reentrant). */
static s2_io g_io;

typedef struct {
    short count[S2_MAXBITS + 1];
    short symbol[S2_MAXCODES];
} s2_huff;

static const short s2_lbase[29] = {
    3, 4, 5, 6, 7, 8, 9, 10, 11, 13, 15, 17, 19, 23, 27, 31, 35, 43, 51, 59,
    67, 83, 99, 115, 131, 163, 195, 227, 258
};
static const short s2_lext[29] = {
    0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3, 4, 4, 4, 4,
    5, 5, 5, 5, 0
};
static const short s2_dbase[30] = {
    1, 2, 3, 4, 5, 7, 9, 13, 17, 25, 33, 49, 65, 97, 129, 193, 257, 385, 513,
    769, 1025, 1537, 2049, 3073, 4097, 6145, 8193, 12289, 16385, 24577
};
static const short s2_dext[30] = {
    0, 0, 0, 0, 1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6, 7, 7, 8, 8, 9, 9, 10, 10,
    11, 11, 12, 12, 13, 13
};

/* --------------------------------------------------------------- bit reader */

static int s2_bits(s2_io *s, int need)
{
    unsigned v;

    while (s->bitcnt < need) {
        if (s->in_pos >= s->in_len) { s->err = 1; return 0; }
        s->bitbuf |= (unsigned)s->in[s->in_pos++] << s->bitcnt;
        s->bitcnt += 8;
    }
    v = s->bitbuf & ((1u << need) - 1u);
    s->bitbuf >>= need;
    s->bitcnt -= need;
    return (int)v;
}

unsigned s2_adler32(const unsigned char *buf, size_t len)
{
    unsigned a = 1, b = 0;
    size_t i;

    for (i = 0; i < len; i++) {
        a += buf[i];
        if (a >= 5552u * 65521u)
            a %= 65521u;
        b += a;
        if (b >= 5552u * 65521u)
            b %= 65521u;
    }
    a %= 65521u;
    b %= 65521u;
    return (b << 16) | a;
}

/* ------------------------------------------------------------ huffman codes */

static int s2_huff_build(s2_huff *h, const unsigned char *lengths, int n)
{
    short offs[S2_MAXBITS + 1];
    int i, left;

    memset(h->count, 0, sizeof h->count);
    for (i = 0; i < n; i++)
        h->count[lengths[i]]++;
    left = 1;
    for (i = 1; i <= S2_MAXBITS; i++) {
        left <<= 1;
        left -= h->count[i];
        if (left < 0)
            return -1;                    /* over-subscribed code set */
    }
    offs[1] = 0;
    for (i = 1; i < S2_MAXBITS; i++)
        offs[i + 1] = (short)(offs[i] + h->count[i]);
    for (i = 0; i < n; i++)
        if (lengths[i])
            h->symbol[offs[lengths[i]]++] = (short)i;
    return left;                          /* >0: incomplete (still usable) */
}

static int s2_decode(s2_io *s, const s2_huff *h)
{
    int code = 0, first = 0, index = 0, len;

    for (len = 1; len <= S2_MAXBITS; len++) {
        int b = s2_bits(s, 1);
        int count;
        if (s->err)
            return -1;
        code |= b;
        count = h->count[len];
        if (code - first < count)
            return h->symbol[index + (code - first)];
        index += count;
        first = (first + count) << 1;
        code <<= 1;
    }
    return -1;
}
/* ------------------------------------------------------------ block decoding */

static int s2_put(s2_io *s, unsigned char c)
{
    if (s->out_len >= s->out_cap) { s->err = 1; return -1; }
    s->out[s->out_len++] = c;
    s->win[s->win_pos] = c;
    s->win_pos = (s->win_pos + 1) & (S2_WINSIZE - 1);
    if (s->win_len < S2_WINSIZE)
        s->win_len++;
    return 0;
}

static int s2_block(s2_io *s, const s2_huff *l, const s2_huff *d)
{
    for (;;) {
        int sym = s2_decode(s, l);

        if (sym < 0)
            return -1;
        if (sym < 256) {
            if (s2_put(s, (unsigned char)sym) != 0)
                return -1;
            continue;
        }
        if (sym == 256)
            return 0;                     /* end of block */
        {
            int idx = sym - 257;
            int len, dsym, dist, k;

            if ((unsigned)idx >= 29u)
                return -1;
            len = s2_lbase[idx] + s2_bits(s, s2_lext[idx]);
            dsym = s2_decode(s, d);
            if (dsym < 0 || dsym >= 30)
                return -1;
            dist = s2_dbase[dsym] + s2_bits(s, s2_dext[dsym]);
            if (s->err)
                return -1;
            if (dist <= 0 || (size_t)dist > s->win_len)
                return -1;                /* reference before start of history */
            for (k = 0; k < len; k++) {
                unsigned char c = s->win[(s->win_pos + S2_WINSIZE
                                          - (size_t)dist) & (S2_WINSIZE - 1)];
                if (s2_put(s, c) != 0)
                    return -1;
            }
        }
    }
}

static int s2_stored(s2_io *s)
{
    unsigned len, nlen;

    s->bitbuf = 0;                        /* discard to the byte boundary */
    s->bitcnt = 0;
    if (s->in_pos + 4 > s->in_len)
        return -1;
    len = (unsigned)s->in[s->in_pos] | ((unsigned)s->in[s->in_pos + 1] << 8);
    nlen = (unsigned)s->in[s->in_pos + 2] | ((unsigned)s->in[s->in_pos + 3] << 8);
    s->in_pos += 4;
    if ((len ^ 0xFFFFu) != nlen)
        return -1;
    if (s->in_pos + len > s->in_len)
        return -1;
    while (len--)
        if (s2_put(s, s->in[s->in_pos++]) != 0)
            return -1;
    return 0;
}

static int s2_fixed(s2_huff *l, s2_huff *d)
{
    unsigned char ll[288], dl[30];
    int i;

    for (i = 0; i < 144; i++) ll[i] = 8;
    for (; i < 256; i++) ll[i] = 9;
    for (; i < 280; i++) ll[i] = 7;
    for (; i < 288; i++) ll[i] = 8;
    for (i = 0; i < 30; i++) dl[i] = 5;
    if (s2_huff_build(l, ll, 288) < 0)
        return -1;
    if (s2_huff_build(d, dl, 30) < 0)
        return -1;
    return 0;
}
static int s2_dynamic(s2_io *s, s2_huff *l, s2_huff *d)
{
    static const unsigned char ord[19] = {
        16, 17, 18, 0, 8, 7, 9, 6, 10, 5, 11, 4, 12, 3, 13, 2, 14, 1, 15
    };
    unsigned char cl[19], lengths[S2_MAXCODES];
    s2_huff clh;
    int hlit, hdist, hclen, i, n;

    hlit = s2_bits(s, 5) + 257;
    hdist = s2_bits(s, 5) + 1;
    hclen = s2_bits(s, 4) + 4;
    if (s->err || hlit > S2_MAXLCODES || hdist > S2_MAXDCODES)
        return -1;
    memset(cl, 0, sizeof cl);
    for (i = 0; i < hclen; i++)
        cl[ord[i]] = (unsigned char)s2_bits(s, 3);
    if (s->err || s2_huff_build(&clh, cl, S2_MAXCLCODES) < 0)
        return -1;
    n = 0;
    while (n < hlit + hdist) {
        int sym = s2_decode(s, &clh);
        if (sym < 0)
            return -1;
        if (sym < 16) {
            lengths[n++] = (unsigned char)sym;
            continue;
        }
        {
            int rep, val;
            if (sym == 16) {
                if (n == 0)
                    return -1;
                val = lengths[n - 1];
                rep = 3 + s2_bits(s, 2);
            } else if (sym == 17) {
                val = 0;
                rep = 3 + s2_bits(s, 3);
            } else {
                val = 0;
                rep = 11 + s2_bits(s, 7);
            }
            if (s->err || n + rep > hlit + hdist)
                return -1;
            while (rep--)
                lengths[n++] = (unsigned char)val;
        }
    }
    if (lengths[256] == 0)
        return -1;                        /* no end-of-block code */
    if (s2_huff_build(l, lengths, hlit) < 0)
        return -1;
    if (s2_huff_build(d, lengths + hlit, hdist) < 0)
        return -1;
    return 0;
}

/* ------------------------------------------------------------------- entry */

size_t s2_inflate(const unsigned char *in, size_t in_len,
                  const unsigned char *dict, size_t dict_len,
                  unsigned char *out, size_t out_cap)
{
    s2_io *s = &g_io;
    s2_huff lit, dist;
    unsigned cmf, flg, expected;
    size_t adler_at;

    memset(s, 0, sizeof *s);
    s->in = in;
    s->in_len = in_len;
    s->out = out;
    s->out_cap = out_cap;

    if (in_len < 6)
        return (size_t)-1;                /* zlib header + at least one block */
    cmf = in[0];
    flg = in[1];
    if ((cmf & 0x0Fu) != 8 || ((cmf >> 4) & 0x0Fu) > 7)
        return (size_t)-1;
    if (((cmf << 8) | flg) % 31u != 0)
        return (size_t)-1;
    if ((flg & 0x20u) != 0) {             /* FDICT: the press formula is needed */
        size_t take = dict_len > S2_WINSIZE ? S2_WINSIZE : dict_len;
        unsigned dictid;

        if (dict == NULL || dict_len == 0)
            return (size_t)-1;
        /* RFC 1950: the header is followed by a 4-byte big-endian DICTID (the
         * adler32 of the dictionary tail actually used).  Skip it -- and use
         * it, so a wrong press mark is refused at the head instead of after a
         * partial decode. */
        if (in_len < 10)
            return (size_t)-1;
        dictid = ((unsigned)in[2] << 24) | ((unsigned)in[3] << 16)
               | ((unsigned)in[4] << 8) | (unsigned)in[5];
        if (dictid != s2_adler32(dict + (dict_len - take), take))
            return (size_t)-1;
        /* Seed the END of the history window so the ring's invariant (newest
         * byte at win_pos-1) holds with win_pos == 0: the dictionary occupies
         * win[WINSIZE-take .. WINSIZE) and the first output byte lands at 0. */
        memcpy(s->win + (S2_WINSIZE - take), dict + (dict_len - take), take);
        s->win_len = take;
        s->win_pos = 0;
        s->in_pos = 6;
    } else {
        s->in_pos = 2;
    }

    for (;;) {
        int last = s2_bits(s, 1);
        int type;

        if (s->err)
            return (size_t)-1;
        type = s2_bits(s, 2);
        if (s->err)
            return (size_t)-1;
        if (type == 0) {
            if (s2_stored(s) != 0)
                return (size_t)-1;
        } else if (type == 1) {
            if (s2_fixed(&lit, &dist) != 0 || s2_block(s, &lit, &dist) != 0)
                return (size_t)-1;
        } else if (type == 2) {
            if (s2_dynamic(s, &lit, &dist) != 0 || s2_block(s, &lit, &dist) != 0)
                return (size_t)-1;
        } else {
            return (size_t)-1;            /* reserved block type */
        }
        if (last)
            break;
    }

    /* The stream's adler32 begins at the next byte boundary after the
     * compressed data (whole buffered bytes have already been consumed). */
    adler_at = ((s->in_pos * 8u - (size_t)s->bitcnt) + 7u) / 8u;
    if (adler_at + 4 > in_len)
        return (size_t)-1;
    expected = ((unsigned)in[adler_at] << 24) | ((unsigned)in[adler_at + 1] << 16)
             | ((unsigned)in[adler_at + 2] << 8) | (unsigned)in[adler_at + 3];
    if (expected != s2_adler32(out, s->out_len))
        return (size_t)-1;
    return s->out_len;
}