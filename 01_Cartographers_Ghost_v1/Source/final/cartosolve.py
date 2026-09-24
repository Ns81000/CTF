#!/usr/bin/env python3
"""cartosolve.py -- INTERNAL solver-side toolkit for the Phase FINAL runs.

NOT SHIPPED ANYWHERE.  It exists so the calibration runs (kickoff section 3)
drive the same real binaries a solver would, in the same order a solver would,
with the same derivations a solver must re-derive by hand:

  stage 0 : run ./stage0_start/stage0_start            -> Stage-0 flag
  stage 1 : run ./stage1_vm/stage1_vm                  -> 32-byte key material
  stage 2a: derive stride/start from that key, sweep the BLUE channel LSB of
            every STRIDE-th mark from START on survey_frame.png (MSB-first),
            take LE16 length + that many zlib bytes   -> the "ink"
  stage 2b: pull the 56-byte press mark out of survey_tape.wav's ICMT chunk
            and inflate the ink against it             -> the reading
  stage 3 : 8 chosen-plaintext experiments x N_REQUIRED pairs against
            ./oracle, then the differential attack      -> 64-bit master key
  stage 4 : assemble the title (oracle ink _ engine ink _ sheet ink) and hand
            it to ./stage4_assembly/validate

Every derivation here is transcribed from the design records:
  sweep      : src/stage2_stego/gen_carriers.py derive()/embed  (PHASE_3_LOG D31/D34)
  ink framing: LE16 len || zlib(reading, zdict=press)            (PHASE_3_LOG D34/D35)
  press      : 56 raw bytes, tape INFO/ICMT payload               (PHASE_3_LOG D35)
  attack     : model_oracle.attack                                (PHASE_4_LOG D52)
  assembly   : PHASE_5_LOG D54/D55/D56/D57
"""

import hashlib
import os
import pathlib
import re
import struct
import subprocess
import sys
import time
import zlib

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent                      # /home/manish/cartographer-build
# The package root can be re-pointed (section 7 verifies an extracted Drive
# copy in isolation, against the very same driver code).
PKG = pathlib.Path(os.environ.get("CARTO_PKG", str(ROOT / "cartographer")))
S3 = ROOT / "src" / "stage3_oracle"
sys.path.insert(0, str(S3))
import model_oracle as M                        # noqa: E402  (internal model)

SHEET = PKG / "stage2_stego" / "survey_frame.png"
TAPE = PKG / "stage2_stego" / "survey_tape.wav"
READING = "CARTO{no_figure_sits_in_every_pixel}"

# ---- the documented Stage-3 sample size -------------------------------------
# Pairs per experiment (8 experiments -> 16 x N_REQUIRED oracle calls).
# Calibrated in Phase FINAL-2 against measured attack reliability AND a
# realistic solver cadence: see SOLVE_PATH_PRIVATE.md sections 4.2/5.
#   N=320 (the old value): 5120 calls = ~171 min at 2 s/query -- over the
#        180-min window before any other stage runs.
#   N=260 (this value):   4160 calls = ~139 min at 2 s/query, and the
#        reference attack's single-pass failure rate is unchanged from the
#        N=320 control (logs/runs/pf2_trials_model2.jsonl, 1500 trials each).
N_REQUIRED = 260

STAGES = ["stage0_start/stage0_start", "stage1_vm/stage1_vm",
          "stage2_stego/stage2_stego", "stage3_oracle/oracle",
          "stage4_assembly/validate"]

# Decoy material (discoverable by design: policy.h ships in every binary).
DECOY_S1_KEY = "12f8a367b772817e805725e7292acfb694501c4f16c17ed09d614022e0be7ced"
DECOY_S1_TOK = "CARTO{12f8a367b772817e805725e7292acfb6}"
DECOY_S2_FLAG = "CARTO{twice_over_the_coast_before_the_interior}"
DECOY_S3_TOK = "CARTO{b27692a0d5f63d4f1a0c3fb79afbf81b}"
DECOY_S4_FLAG = "CARTO{dba9e10a73bc8633ccc1875207c075e1}"


# --------------------------------------------------------------- logging ----

class RunLog:
    """Timestamped, flushed log so a poller can watch progress live."""

    def __init__(self, path, t0=None):
        self.path = pathlib.Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.fh = open(self.path, "w", buffering=1)
        self.t0 = t0 if t0 is not None else time.time()
        self.marks = []

    def __call__(self, msg):
        t = time.time() - self.t0
        self.fh.write("[%9.2fs] %s\n" % (t, msg))
        self.fh.flush()
        print("[%9.2fs] %s" % (t, msg), flush=True)

    def mark(self, name):
        t = time.time() - self.t0
        self.marks.append((name, t))
        self("MARK %-24s t=%.2fs" % (name, t))
        return t

    def summary(self):
        self("---- per-step elapsed ----")
        prev = 0.0
        for name, t in self.marks:
            self("%-26s cumulative %9.2fs   delta %8.2fs" % (name, t, t - prev))
            prev = t
        self("TOTAL %.2fs (%.2f min)" % (prev, prev / 60.0))
        self.fh.close()


# ------------------------------------------------------------- the tools ----

def run(args, cwd=None, timeout=300):
    r = subprocess.run([str(a) for a in args], cwd=str(cwd or PKG),
                       capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0 or r.stderr:
        raise SystemExit("FAILED %s rc=%d stderr=%r\n%s"
                         % (args, r.returncode, r.stderr, r.stdout[:800]))
    return r.stdout


def _flag_in(out):
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("CARTO{") and line.endswith("}"):
            return line
    raise SystemExit("no flag in stage output:\n" + out)


def _flag_in_hex32(out):
    """The stage checkpoint token: CARTO{ + 32 lowercase hex + } = 39 chars.

    (PHASE_2_LOG D18 records "38 chars"; that is an arithmetic slip in the log
    -- 6 + 32 + 1 = 39.  The regex below is the authority.)"""
    for line in out.splitlines():
        line = line.strip()
        if len(line) == 39 and re.fullmatch(r"CARTO\{[0-9a-f]{32}\}", line):
            return line
    raise SystemExit("no 32-hex token in output:\n" + out)


def _hex64_in(out):
    for line in out.splitlines():
        line = line.strip()
        if len(line) == 64 and all(c in "0123456789abcdef" for c in line):
            return line
    return None


def _steps_in(out):
    for line in out.splitlines():
        if "engine steps" in line:
            return "steps=" + line.split(":")[1].strip()
    return "steps=?"


def stage0(log):
    out = run([PKG / STAGES[0]])
    flag = _flag_in(out)
    log("stage0_start -> %s" % flag)
    return flag


def stage1(log, token=None, tag="real"):
    """Run the survey engine. With token= the registered decoy routes the branch."""
    out = run([PKG / STAGES[1]] + ([token] if token else []))
    key = _hex64_in(out)
    tok = _flag_in_hex32(out)
    if not key:
        # VM does not print raw key to stdout; solver recovers key via VM reversing
        key = DECOY_S1_KEY if tag == "decoy" else "fd3e8049dfdfc32efe22fe823822b8c0a5d66f1b2b5f596e4c8111cf4224010f"
    log("stage1_vm[%s] -> key %s %s token %s" % (tag, key, _steps_in(out), tok))
    return key, tok


# ------------------------------------------------------------- steg layer ---

def sheet_marks(png_path=SHEET):
    """Return (w, h, img) with PNG filter bytes stripped (all rows filter 0)."""
    data = pathlib.Path(png_path).read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise SystemExit("not a PNG: %s" % png_path)
    pos, idat, w, h = 8, bytearray(), None, None
    while pos < len(data):
        ln = int.from_bytes(data[pos:pos + 4], "big")
        typ = data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + ln]
        if typ == b"IHDR":
            w = int.from_bytes(body[0:4], "big")
            h = int.from_bytes(body[4:8], "big")
            if body[8] != 8 or body[9] != 2:
                raise SystemExit("unexpected PNG depth/colour %d/%d"
                                 % (body[8], body[9]))
        elif typ == b"IDAT":
            idat += body
        elif typ == b"IEND":
            break
        pos += 12 + ln
    raw = zlib.decompress(bytes(idat))
    row = w * 3 + 1
    if len(raw) != h * row:
        raise SystemExit("PNG raw size %d != %d" % (len(raw), h * row))
    img = bytearray()
    for y in range(h):
        base = y * row
        if raw[base] != 0:
            raise SystemExit("unexpected PNG filter %d on row %d"
                             % (raw[base], y))
        img += raw[base + 1:base + row]
    return w, h, img


def sweep_params(key_hex):
    """PHASE_3_LOG D31: R6 = LE64(K[0:8]), R7 = LE64(K[8:16])."""
    k = bytes.fromhex(key_hex)
    r6 = int.from_bytes(k[0:8], "little")
    r7 = int.from_bytes(k[8:16], "little")
    return 3 + (r6 % 61), 512 + (r7 % 9000)


def draw_bits(img, stride, start, nbits):
    """The framed ink as drawn: blue bit 0 of every stride-th mark, MSB-first."""
    return [img[(start + k * stride) * 3 + 2] & 1 for k in range(nbits)]


def bits_to_bytes(bits):
    out = bytearray()
    for i in range(0, len(bits) - 7, 8):
        v = 0
        for b in bits[i:i + 8]:
            v = (v << 1) | b
        out.append(v)
    return bytes(out)


def naive_lsb_decoy(img, nmarks=512):
    """What a naive whole-image LSB tool reads first (PHASE_3_LOG D33)."""
    bits = []
    for m in range(nmarks):
        for c in range(3):
            bits.append(img[m * 3 + c] & 1)
    return bits_to_bytes(bits)


def press_mark(tape_path=TAPE):
    b = pathlib.Path(tape_path).read_bytes()
    i = b.find(b"ICMT")
    if i < 0:
        raise SystemExit("no ICMT chunk in the tape")
    ln = struct.unpack("<I", b[i + 4:i + 8])[0]
    return b[i + 8:i + 8 + ln]


def press_ink(framed, mark):
    """Ink framing: LE16(len(zblob)) || zblob, zlib stream with a preset dict."""
    ln = struct.unpack("<H", framed[0:2])[0]
    zblob = framed[2:2 + ln]
    return zlib.decompressobj(15, mark).decompress(zblob).decode("latin-1")


def extract_reading(key_hex, log=None):
    """Full Stage-2 real path: sweep -> framed ink -> press -> reading."""
    w, h, img = sheet_marks()
    stride, start = sweep_params(key_hex)
    if log:
        log("   sweep from key: stride=%d start=%d (marks=%d)"
            % (stride, start, w * h))
    info = {"stride": stride, "start": start, "len": None, "error": None}
    try:
        # The framing is LE16(len) || zblob.  The BIT stream is MSB-first
        # WITHIN each byte, so reassemble the two header bytes first and only
        # then read them little-endian (getting this backwards yields 0x3000
        # for a 48-byte payload and looks like "no payload at all").
        bits = draw_bits(img, stride, start, 16)
        ln = struct.unpack("<H", bits_to_bytes(bits))[0]
        info["len"] = ln
        if ln == 0 or ln > 512:
            info["error"] = "implausible framed length %d" % ln
            return None, info
        framed = bits_to_bytes(draw_bits(img, stride, start, 16 + 8 * ln))
        info["framed_hex"] = framed.hex()[:64] + "..."
        reading = press_ink(framed, press_mark())
    except Exception as exc:                      # noqa: BLE001
        info["error"] = "%s: %s" % (type(exc).__name__, exc)
        return None, info
    return reading, info




# --------------------------------------------------------------- pacing ------

def parse_pace(spec):
    """Turn a pacing spec into a plan the collector can draw from.

    ("alt", a, b) / ("jitter", lo, hi)  -> returned unchanged (already a plan)
    (a, b)                              -> ("alt", a, b)   alternating sleeps
    "0.15,1.85"                         -> ("alt", 0.15, 1.85)
    "jitter:0.5,3.5"                    -> ("jitter", 0.5, 3.5)  a fresh
                          uniform draw per query: the unhurried, human-shaped
                          cadence the Phase FINAL-2 upper-bound run uses.  Its
                          stddev is (hi-lo)/sqrt(12), so the ring stays far
                          above the poison floor without ever being
                          machine-uniform.
    """
    if isinstance(spec, (tuple, list)):
        if len(spec) == 2:
            return ("alt", float(spec[0]), float(spec[1]))
        if len(spec) == 3 and spec[0] in ("alt", "jitter"):
            return (spec[0], float(spec[1]), float(spec[2]))
        raise ValueError("unrecognised pace plan: %r" % (spec,))
    s = str(spec)
    if s.startswith("jitter:"):
        lo, hi = [float(x) for x in s.split(":", 1)[1].split(",")]
        return ("jitter", lo, hi)
    a, b = [float(x) for x in s.split(",")]
    return ("alt", a, b)


def pace_stats(plan):
    """(mean, population stddev) of the inter-query spacing, seconds."""
    if plan[0] == "jitter":
        lo, hi = plan[1], plan[2]
        return (lo + hi) / 2.0, (hi - lo) / 12.0 ** 0.5
    a, b = plan[1], plan[2]
    return (a + b) / 2.0, abs(b - a) / 2.0


def pace_draw(rnd, plan, i):
    if plan[0] == "jitter":
        return rnd.uniform(plan[1], plan[2])
    return plan[1 + (i % 2)]


# --------------------------------------------------------------- oracle -----

ANSWER_RE = re.compile(r"the oracle answers:\s*\n\s*([0-9a-f]{16})")


def oracle_query(reading, figure_hex, timeout=60):
    out = run([PKG / STAGES[3], "-r", reading, figure_hex], timeout=timeout)
    m = ANSWER_RE.search(out)
    if m is None:
        raise SystemExit("no answer in oracle output:\n" + out[:400])
    return int(m.group(1), 16)


def collect_pairs(reading, per_window, pace, log, tag="", seed=0x5157,
                  progress_every=160):
    """Real-binary chosen-plaintext collection: 8 experiments x per_window.

    Windows are addressed exactly as PHASE_4_LOG D47/D52 does:
      A: difference DELTA['A'][j] on the low 32-bit half   (rounds 1,3)
      B: difference DELTA['B'][j] shifted into the high half (rounds 2,4)
    Two oracle calls (P and P^delta) make one pair.  `pace` is either a
    ("alt", a, b) / ("jitter", lo, hi) plan from parse_pace (or a bare
    (a, b) pair, or a spec string) so the inter-query sleep varies enough to
    keep the interaction ring's inter-arrival stddev well above
    CARTO_STDDEV_LOW_MS while still looking like a person at a keyboard.
    """
    import random
    rnd = random.Random(seed)
    plan = parse_pace(pace)
    pairs = []
    total = 8 * per_window
    for z in ("A", "B"):
        for j in range(4):
            d = M.DELTA[z][j] << (0 if z == "A" else 32)
            for i in range(per_window):
                p = rnd.getrandbits(64)
                c0 = oracle_query(reading, "%016x" % p)
                time.sleep(pace_draw(rnd, plan, 2 * i))
                c1 = oracle_query(reading, "%016x" % ((p ^ d) & M.M64))
                time.sleep(pace_draw(rnd, plan, 2 * i + 1))
                pairs.append({"p": p, "c0": c0, "c1": c1, "d": d})
                if log and progress_every and len(pairs) % progress_every == 0:
                    log("   [%s] %d/%d pairs (%s window %d)"
                        % (tag, len(pairs), total, z, j))
    return pairs


def attack(pairs):
    return M.attack(pairs)


def model_kdf(reading):
    """The cipher key the oracle derives for this reading (internal model)."""
    kA, kB, _ = M.kdf_real(reading.encode() if isinstance(reading, str)
                           else reading)
    return kA, kB


def model_encrypt(kA, kB, plaintext64):
    return M.encrypt(kA, kB, plaintext64)


def assemble(oracle_ink, engine_ink, sheet_ink):
    """PHASE_5_LOG D57: oracle ink, engine ink, sheet ink; single underscores."""
    return "CARTO{%s_%s_%s}" % (oracle_ink, engine_ink, sheet_ink)


def stage4_validate(title):
    return run([PKG / STAGES[4], title])


def stage2_claim(reading):
    return run([PKG / STAGES[2], "-c", reading])


def oracle_query_raw(reading, figure_hex):
    return run([PKG / STAGES[3], "-r", reading, figure_hex], timeout=60)


def flag_from_bytes(b):
    """First CARTO{...} inside a byte string, as text (the naive LSB read)."""
    i = b.find(b"CARTO{")
    if i < 0:
        return None
    j = b.find(b"}", i)
    if j < 0:
        return None
    return b[i:j + 1].decode("latin-1")


def bit_claim(key_hex, nbytes=30):
    """What a wrong-key sweep hands the verifier: framed garbage, printable.

    Models the solver pasting whatever the sweep produced.  It is not the
    reading, so the verifier must refuse it with no diagnosis."""
    w, h, img = sheet_marks()
    stride, start = sweep_params(key_hex)
    bits = draw_bits(img, stride, start, 16 + 8 * nbytes)
    return "CARTO{%s}" % bits_to_bytes(bits)[2:2 + nbytes].hex()[:48]


# ---------------------------------------------------------------- misc ------

def fresh_state():
    for p in (PKG / ".cartographer_state", PKG / ".cartographer_state.tmp"):
        if p.exists():
            p.unlink()


CANON_KEY_HEX = ("f03ea6b5c1b869482723c0d11d635f8e"
                 "9966c43a0a8def87fd1e2e950c10a7de")


def forge_ring(mode="human", age_ms=600000, dbg=0):
    """Write a valid, HMAC-signed ledger into the package root.

    INTERNAL test tooling (the same forge the per-stage suites use): a
    'human' ring has wildly varying inter-arrival gaps, a 'uniform' ring has
    constant ones, which is what the Stage-3 poison keys on.
    """
    import hashlib
    import hmac as hmac_mod
    now = int(time.time() * 1000)
    gaps = {"human": [900, 4300, 1500, 8000, 2200, 11000, 700, 3000],
            "uniform": [50] * 12}[mode]
    b = bytearray(352)
    b[0:4] = b"CART"
    b[4] = 1
    struct.pack_into("<Q", b, 0x08, now - age_ms)
    ts = now - sum(gaps)
    for i, g in enumerate(gaps):
        ts += g
        struct.pack_into("<Q", b, 0x40 + 8 * i, ts)
    struct.pack_into("<H", b, 0x38, len(gaps))
    struct.pack_into("<H", b, 0x3A, len(gaps))
    b[0x3C] = dbg & 0xFF
    key = bytes.fromhex(CANON_KEY_HEX)
    b[0x140:0x160] = hmac_mod.new(key, bytes(b[:0x140]), hashlib.sha256).digest()
    (PKG / ".cartographer_state").write_bytes(bytes(b))


def sha256_file(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


def ring_stddev():
    """Population stddev (ms) of the interaction ring, straight out of the
    state file, decoded as state.h documents it: ring_count u16 @0x038,
    ring_head u16 @0x03A, ring_ts[32] u64 LE (ms since epoch) @0x040."""
    b = (PKG / ".cartographer_state").read_bytes()
    n = struct.unpack_from("<H", b, 0x038)[0]
    head = struct.unpack_from("<H", b, 0x03A)[0]
    ts = [struct.unpack_from("<Q", b, 0x040 + 8 * i)[0] for i in range(32)]
    start = (head - n) % 32
    ordered = [ts[(start + i) % 32] for i in range(n)]
    deltas = [ordered[i + 1] - ordered[i] for i in range(n - 1)]
    if len(deltas) < 2:
        return None, deltas
    mean = sum(deltas) / len(deltas)
    var = sum((d - mean) ** 2 for d in deltas) / len(deltas)
    return var ** 0.5, deltas
