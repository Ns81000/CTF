/*
 * vm.c -- Stage 1 custom stack machine interpreter.
 * Design record: logs/PHASE_2_LOG.md.  Generated tables: vm_tables.h.
 */
#include "vm.h"

#include <string.h>

#define ACC_A 0x9E3779B97F4A7C15ull
#define ACC_B 0xC2B2AE3D27D4EB4Full
#define ACC_C 0xBF58476D1CE4E5B9ull
#define ACC_D 0x94D049BB133111EBull

typedef struct {
    int      op;        /* logical opcode, -1 = invalid byte            */
    uint64_t imm;       /* immediate or signed relative displacement    */
    int      rd, rs, rt;
    int      len;       /* instruction length in bytes                  */
} insn_t;

/* The widest operand form is 9 bytes (VM_F_I64), and vm_decode() may
 * be entered with ip within 8 bytes of the end of the image, so the
 * buffer carries an 8-byte pad.  The VM never addresses the pad: every
 * code access goes through VM_CODE_MASK. */
#define VM_CODE_PAD 8
static unsigned char g_code[VM_CODE_SIZE + VM_CODE_PAD];
static unsigned char g_dec[256];       /* opcode byte -> logical opcode    */
static uint64_t      g_stack[VM_STACK_SIZE];
static uint64_t      g_mem[VM_DATA_SIZE];

static int      g_z, g_s, g_c;         /* condition flags                  */
static uint64_t g_port;                /* scratch "port" (no side effects) */
static unsigned int g_sp;

static uint64_t rotl64(uint64_t v, unsigned int n)
{
    n &= 63u;
    return n ? ((v << n) | (v >> (64u - n))) : v;
}

static uint64_t rotr64(uint64_t v, unsigned int n)
{
    n &= 63u;
    return n ? ((v >> n) | (v << (64u - n))) : v;
}

static void vm_init_tables(void)
{
    unsigned int i;
    memset(g_dec, 0xFF, sizeof g_dec);
    for (i = 0; i < VM_OP_COUNT; i++)
        g_dec[kOpByte[i]] = (unsigned char)i;
}

static uint64_t rd_le(const unsigned char *p, int n)
{
    uint64_t v = 0;
    int i;
    for (i = 0; i < n; i++)
        v |= (uint64_t)p[i] << (8 * i);
    return v;
}

static uint64_t rd_be(const unsigned char *p, int n)
{
    uint64_t v = 0;
    int i;
    for (i = 0; i < n; i++)
        v = (v << 8) | p[i];
    return v;
}

/* Data-driven operand decode: the shape of an instruction comes entirely
 * from the per-build form table, so the same logical opcode can be encoded
 * differently in different builds. */
static void vm_decode(unsigned int ip, insn_t *in)
{
    unsigned char form;
    int be;
    const unsigned char *p = &g_code[ip];

    in->op  = g_dec[p[0]];
    in->imm = 0;
    in->rd = in->rs = in->rt = 0;
    in->len = 1;
    if (in->op < 0)
        return;

    form = kOpForm[in->op];
    be   = kOpEndian[in->op] ? 1 : 0;

    switch (form) {
    case VM_F_NONE:  break;
    case VM_F_I8:
    case VM_F_A8:    in->imm = p[1]; in->len = 2; break;
    case VM_F_I16:   in->imm = be ? rd_be(p + 1, 2) : rd_le(p + 1, 2); in->len = 3; break;
    case VM_F_I32:   in->imm = be ? rd_be(p + 1, 4) : rd_le(p + 1, 4); in->len = 5; break;
    case VM_F_I64:   in->imm = rd_le(p + 1, 8); in->len = 9; break;
    case VM_F_R:     in->rd = p[1]; in->len = 2; break;
    case VM_F_RR:    in->rd = p[1] & 0x0F; in->rs = (p[1] >> 4) & 0x0F; in->len = 2; break;
    case VM_F_R3:    in->rd = p[1]; in->rs = p[2]; in->rt = p[3]; in->len = 4; break;
    case VM_F_RI8:   in->rd = p[1]; in->imm = p[2]; in->len = 3; break;
    case VM_F_RI32:  in->rd = p[1];
                     in->imm = be ? rd_be(p + 2, 4) : rd_le(p + 2, 4);
                     in->len = 6; break;
    case VM_F_I32R:  in->imm = be ? rd_be(p + 1, 4) : rd_le(p + 1, 4);
                     in->rd = p[5]; in->len = 6; break;
    case VM_F_RI64:  in->rd = p[1]; in->imm = rd_le(p + 2, 8); in->len = 10; break;
    case VM_F_REL8:  in->imm = (uint64_t)(int64_t)(int8_t)p[1]; in->len = 2; break;
    case VM_F_REL16: in->imm = (uint64_t)(int64_t)(int16_t)(be ? rd_be(p + 1, 2)
                                                                : rd_le(p + 1, 2));
                     in->len = 3; break;
    case VM_F_RREL16:in->rd = p[1];
                     in->imm = (uint64_t)(int64_t)(int16_t)(be ? rd_be(p + 2, 2)
                                                                : rd_le(p + 2, 2));
                     in->len = 4; break;
    default: break;
    }
}

int vm_run(const unsigned char *prog, unsigned int len, int detect_flag,
           vm_result_t *out)
{
    uint64_t r[VM_NREG];
    uint64_t steps = 0;
    unsigned int ip = 0;
    int fault = 1;
    unsigned int i;

    for (i = 0; i < VM_NREG; i++)
        r[i] = 0;
    memset(g_mem, 0, sizeof g_mem);
    memset(g_code, 0, sizeof g_code);
    if (len > VM_CODE_SIZE)
        len = VM_CODE_SIZE;
    memcpy(g_code, prog, len);
    vm_init_tables();
    g_z = g_s = g_c = 0;
    g_port = 0;
    g_sp = 0;
    r[10] = (uint64_t)(detect_flag & 1);   /* detection gate seed */

    for (;;) {
        insn_t in;
        uint64_t a, b, t;
        unsigned int next;

        vm_decode(ip, &in);
        if (in.op < 0) {
            fault = 1;
            break;
        }
        steps++;
        next = ip + (unsigned int)in.len;

        switch (in.op) {
        /* ---- padding / no-op family ---------------------------------- */
        case VM_OP_NOP:
        case VM_OP_NOPA:
        case VM_OP_NOPB:
        case VM_OP_ENC:
        case VM_OP_ENCS:
        case VM_OP_OPAQUE:
            break;

        case VM_OP_HALT:
            fault = 0;
            goto done;

        /* ---- data movement ------------------------------------------- */
        case VM_OP_MOV:    r[in.rd] = r[in.rs]; break;
        case VM_OP_MOVI8:  r[in.rd] = in.imm & 0xFFu; break;
        case VM_OP_MOVI32: r[in.rd] = in.imm & 0xFFFFFFFFu; break;
        case VM_OP_MOVI64: r[in.rd] = in.imm; break;
        case VM_OP_XCHG:   a = r[in.rd]; r[in.rd] = r[in.rs]; r[in.rs] = a; break;
        case VM_OP_MOVM:   g_mem[in.rd & (VM_DATA_SIZE - 1)] = r[in.rs]; break;
        case VM_OP_MOVL:   r[in.rd] = g_mem[in.rs & (VM_DATA_SIZE - 1)]; break;
        case VM_OP_MOVB:   r[in.rd] = g_mem[in.rs & (VM_DATA_SIZE - 1)] & 0xFFu; break;
        case VM_OP_STOREB: g_mem[in.rd & (VM_DATA_SIZE - 1)] = r[in.rs] & 0xFFu; break;

        /* ---- code space: the self-modifying family -------------------- */
        case VM_OP_CLOAD:  r[in.rd] = g_code[r[in.rs] & VM_CODE_MASK]; break;
        case VM_OP_CSTORE: g_code[r[in.rd] & VM_CODE_MASK] =
                               (unsigned char)(r[in.rs] & 0xFFu); break;
        case VM_OP_CXOR:   a = r[in.rd] & VM_CODE_MASK;
                           g_code[a] = (unsigned char)(g_code[a] ^ (r[in.rs] & 0xFFu));
                           break;
        case VM_OP_CADD:   a = r[in.rd] & VM_CODE_MASK;
                           g_code[a] = (unsigned char)(g_code[a] + (in.imm & 0xFFu));
                           break;
        case VM_OP_CREAD:  /* read the bytes that follow as data ... */
                           r[in.rd] = g_code[next & VM_CODE_MASK];
                           next = (next + 1) & VM_CODE_MASK;  /* ... and consume it */
                           break;
        case VM_OP_SKIPC:  ip = (next + (unsigned int)(in.imm & 0xFFu)) & VM_CODE_MASK;
                           continue;

        /* ---- integer ops --------------------------------------------- */
        case VM_OP_ADD:    t = r[in.rd] + r[in.rs];
                           g_c = ((unsigned __int128)r[in.rd] + (unsigned __int128)r[in.rs])
                                 > (unsigned __int128)~0ull;
                           r[in.rd] = t; g_z = (t == 0); g_s = (int)(t >> 63); break;
        case VM_OP_ADDI:   b = in.imm & 0xFFFFFFFFu;
                           t = r[in.rd] + b;
                           g_c = ((unsigned __int128)r[in.rd] + (unsigned __int128)b)
                                 > (unsigned __int128)~0ull;
                           r[in.rd] = t; g_z = (t == 0); g_s = (int)(t >> 63); break;
        case VM_OP_SUB:    b = r[in.rs]; t = r[in.rd] - b;
                           g_c = (r[in.rd] < b); r[in.rd] = t;
                           g_z = (t == 0); g_s = (int)(t >> 63); break;
        case VM_OP_SUBI:   b = in.imm & 0xFFFFFFFFu; t = r[in.rd] - b;
                           g_c = (r[in.rd] < b); r[in.rd] = t;
                           g_z = (t == 0); g_s = (int)(t >> 63); break;
        case VM_OP_MUL:    t = r[in.rd] * r[in.rs]; r[in.rd] = t;
                           g_c = 0; g_z = (t == 0); g_s = (int)(t >> 63); break;
        case VM_OP_MULI:   t = r[in.rd] * (in.imm & 0xFFFFFFFFu); r[in.rd] = t;
                           g_c = 0; g_z = (t == 0); g_s = (int)(t >> 63); break;
        case VM_OP_UMULH:  t = (uint64_t)(((unsigned __int128)r[in.rd] * r[in.rs]) >> 64);
                           r[in.rd] = t;
                           g_c = 0; g_z = (t == 0); g_s = (int)(t >> 63); break;
        case VM_OP_DIV:    t = r[in.rs] ? (r[in.rd] / r[in.rs]) : 0;
                           r[in.rd] = t;
                           g_c = 0; g_z = (t == 0); g_s = (int)(t >> 63); break;
        case VM_OP_MOD:    t = r[in.rs] ? (r[in.rd] % r[in.rs]) : 0;
                           r[in.rd] = t;
                           g_c = 0; g_z = (t == 0); g_s = (int)(t >> 63); break;
        case VM_OP_AND:    t = r[in.rd] & r[in.rs]; goto bitwise;
        case VM_OP_ANDI:   t = r[in.rd] & (in.imm & 0xFFFFFFFFu); goto bitwise;
        case VM_OP_OR:     t = r[in.rd] | r[in.rs]; goto bitwise;
        case VM_OP_ORI:    t = r[in.rd] | (in.imm & 0xFFFFFFFFu); goto bitwise;
        case VM_OP_XOR:    t = r[in.rd] ^ r[in.rs]; goto bitwise;
        case VM_OP_XORI:   t = r[in.rd] ^ (in.imm & 0xFFFFFFFFu); goto bitwise;
bitwise:                   r[in.rd] = t;
                           g_c = 0; g_z = (t == 0); g_s = (int)(t >> 63); break;

        case VM_OP_SHL:    t = r[in.rd] << (r[in.rs] & 63u); goto shift;
        case VM_OP_SHLI:   t = r[in.rd] << (in.imm & 63u); goto shift;
        case VM_OP_SHR:    t = r[in.rd] >> (r[in.rs] & 63u); goto shift;
        case VM_OP_SHRI:   t = r[in.rd] >> (in.imm & 63u); goto shift;
        case VM_OP_SAR:    t = (uint64_t)((int64_t)r[in.rd] >> (r[in.rs] & 63u));
                           goto shift;
shift:                     r[in.rd] = t;
                           g_c = 0; g_z = (t == 0); g_s = (int)(t >> 63); break;

        case VM_OP_ROTL:   r[in.rd] = rotl64(r[in.rd], (unsigned int)r[in.rs]); break;
        case VM_OP_ROTLI:  r[in.rd] = rotl64(r[in.rd], (unsigned int)in.imm); break;
        case VM_OP_ROTR:   r[in.rd] = rotr64(r[in.rd], (unsigned int)r[in.rs]); break;

        case VM_OP_NOT:    t = ~r[in.rd];        goto unary;
        case VM_OP_NEG:    t = (uint64_t)(-(int64_t)r[in.rd]); goto unary;
        case VM_OP_INC:    t = r[in.rd] + 1u;    goto unary;
        case VM_OP_DEC:    t = r[in.rd] - 1u;
unary:                     r[in.rd] = t;
                           g_z = (t == 0); g_s = (int)(t >> 63); break;

        /* ---- wide / modular ------------------------------------------ */
        case VM_OP_MULMOD: t = r[in.rt] ?
                 (uint64_t)(((unsigned __int128)r[in.rd] * r[in.rs]) % r[in.rt]) : 0;
                           goto modop;
        case VM_OP_ADDMM:  t = r[in.rt] ?
                 (uint64_t)(((unsigned __int128)r[in.rd] + r[in.rs]) % r[in.rt]) : 0;
                           goto modop;
        case VM_OP_SUBMM:  t = r[in.rt] ?
                 (uint64_t)(((unsigned __int128)r[in.rd] + r[in.rt] - r[in.rs]) % r[in.rt])
                 : 0;
                           goto modop;
        case VM_OP_POWM:   {   /* never used by the embedded program */
                               uint64_t base = r[in.rd], e = r[in.rs], m = r[in.rt];
                               uint64_t acc = m ? 1u : 0u;
                               while (e) {
                                   if (e & 1u)
                                       acc = m ? (uint64_t)(((unsigned __int128)acc * base) % m) : 0;
                                   base = m ? (uint64_t)(((unsigned __int128)base * base) % m) : 0;
                                   e >>= 1;
                               }
                               t = acc;
                           }
modop:                     r[in.rd] = t;
                           g_c = 0; g_z = (t == 0); g_s = (int)(t >> 63); break;

        /* ---- compare / select ---------------------------------------- */
        case VM_OP_CMP:    b = r[in.rs]; goto cmp;
        case VM_OP_CMPI:   b = in.imm & 0xFFFFFFFFu; goto cmp;
cmp:                       t = r[in.rd] - b;
                           g_z = (t == 0); g_s = (int)(t >> 63);
                           g_c = (r[in.rd] < b); break;
        case VM_OP_TEST:   t = r[in.rd] & r[in.rs];
                           g_z = (t == 0); g_s = 0; g_c = 0; break;
        case VM_OP_SEL:    r[in.rd] = g_z ? r[in.rs] : r[in.rt]; break;

        /* ---- ledger (accumulator) family: all fold into R7 ------------ */
        case VM_OP_ACC:    r[7] = rotl64(r[7], 7) ^ (r[in.rd] + ACC_A); break;
        case VM_OP_ACCC:   a = g_code[r[in.rd] & VM_CODE_MASK];
                           r[7] = rotl64(r[7], 11) ^ (a + ACC_B); break;
        case VM_OP_ACRM:   r[7] = (rotl64(r[7], 17) * ACC_C) ^ r[in.rd]; break;
        case VM_OP_ACCS:   r[7] = rotl64(r[7], 23) ^ (r[in.rd] * ACC_D); break;

        /* ---- control flow -------------------------------------------- */
        case VM_OP_JMP:
        case VM_OP_JMP8:   ip = (next + (unsigned int)in.imm) & VM_CODE_MASK;
                           continue;
        case VM_OP_JMPR:   ip = (unsigned int)(r[in.rd] & VM_CODE_MASK);
                           continue;
        case VM_OP_JZ:     if (g_z) { ip = (next + (unsigned int)in.imm) & VM_CODE_MASK; continue; }
                           break;
        case VM_OP_JNZ:    if (!g_z) { ip = (next + (unsigned int)in.imm) & VM_CODE_MASK; continue; }
                           break;
        case VM_OP_JL:     if (g_s) { ip = (next + (unsigned int)in.imm) & VM_CODE_MASK; continue; }
                           break;
        case VM_OP_JGE:    if (!g_s) { ip = (next + (unsigned int)in.imm) & VM_CODE_MASK; continue; }
                           break;
        case VM_OP_JGT:    if (!g_z && !g_s) { ip = (next + (unsigned int)in.imm) & VM_CODE_MASK; continue; }
                           break;
        case VM_OP_JLE:    if (g_z || g_s) { ip = (next + (unsigned int)in.imm) & VM_CODE_MASK; continue; }
                           break;
        case VM_OP_JC:     if (g_c) { ip = (next + (unsigned int)in.imm) & VM_CODE_MASK; continue; }
                           break;
        case VM_OP_JNC:    if (!g_c) { ip = (next + (unsigned int)in.imm) & VM_CODE_MASK; continue; }
                           break;
        case VM_OP_JOV:    if (g_s) { ip = (next + (unsigned int)in.imm) & VM_CODE_MASK; continue; }
                           break;
        case VM_OP_CALL:   if (g_sp < VM_STACK_SIZE) g_stack[g_sp++] = next;
                           ip = (next + (unsigned int)in.imm) & VM_CODE_MASK;
                           continue;
        case VM_OP_CALLR:  if (g_sp < VM_STACK_SIZE) g_stack[g_sp++] = next;
                           ip = (unsigned int)(r[in.rd] & VM_CODE_MASK);
                           continue;
        case VM_OP_RET:    ip = g_sp ? (unsigned int)(g_stack[--g_sp] & VM_CODE_MASK) : 0;
                           continue;
        case VM_OP_LOOP:   r[in.rd] -= 1u;
                           g_z = (r[in.rd] == 0);
                           g_s = (int)(r[in.rd] >> 63);
                           if (r[in.rd] != 0) {
                               ip = (next + (unsigned int)in.imm) & VM_CODE_MASK;
                               continue;
                           }
                           break;

        /* ---- stack --------------------------------------------------- */
        case VM_OP_PUSH:   if (g_sp < VM_STACK_SIZE) g_stack[g_sp++] = r[in.rd]; break;
        case VM_OP_POP:    r[in.rd] = g_sp ? g_stack[--g_sp] : 0; break;
        case VM_OP_PUSHI:  if (g_sp < VM_STACK_SIZE) g_stack[g_sp++] = in.imm & 0xFFFFFFFFu; break;
        case VM_OP_DUP:    if (g_sp && g_sp < VM_STACK_SIZE) g_stack[g_sp] = g_stack[g_sp - 1], g_sp++;
                           break;
        case VM_OP_SWAP:   if (g_sp >= 2) { a = g_stack[g_sp - 1]; g_stack[g_sp - 1] = g_stack[g_sp - 2];
                                            g_stack[g_sp - 2] = a; }
                           break;
        case VM_OP_PICK:   a = r[in.rd] & 0xFFu;
                           if (g_sp > 0 && a < g_sp) r[in.rd] = g_stack[g_sp - 1 - a];
                           else r[in.rd] = 0;
                           break;
        case VM_OP_DROP:   if (g_sp) g_sp--; break;

        /* ---- oblique ------------------------------------------------- */
        case VM_OP_POKE:   g_port = r[in.rd]; break;
        case VM_OP_PEEK:   r[in.rd] = g_port; break;

        default:
            fault = 1;
            goto done;
        }

        ip = next & VM_CODE_MASK;
    }

done:
    for (i = 0; i < VM_NREG; i++)
        out->r[i] = r[i];
    out->steps = steps;
    out->fault = fault;
    memset(g_code, 0, sizeof g_code);      /* wipe the mutated image */
    memset(g_stack, 0, sizeof g_stack);
    return fault ? -1 : 0;
}

void vm_pack_key(const vm_result_t *res, unsigned char out[32])
{
    static const int order[4] = { 6, 7, 1, 2 };
    int i, j;

    for (i = 0; i < 4; i++)
        for (j = 0; j < 8; j++)
            out[i * 8 + j] = (unsigned char)(res->r[order[i]] >> (8 * j));
}