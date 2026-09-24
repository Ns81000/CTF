#!/usr/bin/env python3
"""PRAMBH mint — derives every ARCHIVE-mode value from labelled seeds.

Minting law (spec 4.0): every constant = SHA-256("prambh:<stage>:<what>:v1"
[|| context]).  No randomness anywhere.  The full seed->value->location
table is written to organizer-private/KEYS_PRAMBH.md.

This module is imported by the phase drivers; running it directly prints
the stage-0 values.  Chain outputs are NOT computed here (see chains
runner); values that depend on them are filled in by later phases.
"""
import hashlib
import os
import struct

ROOT = hashlib.sha256(b"prambh:archive:root:v3").digest()

# EVENT mode (spec 3): a per-player context mixed into EVERY derivation.
# ARCHIVE mode leaves it empty, so every archived value is unchanged.
# The context can also be supplied out of band (the per-player generator
# and its cross-contamination suite do exactly that).
PLAYER_CONTEXT = bytes.fromhex(os.environ.get("PRAMBH_PLAYER_HEX", ""))


def set_player_context(ctx):
    global PLAYER_CONTEXT
    PLAYER_CONTEXT = bytes(ctx)


def player_seed(master_secret, callsign):
    return hashlib.sha256(master_secret + b"prambh:player:v1"
                          + callsign.encode()).digest()


def seed(label, context=b""):
    return hashlib.sha256(label.encode() + context + PLAYER_CONTEXT).digest()


def sha256ctr(key, nbytes):
    out = bytearray()
    ctr = 0
    while len(out) < nbytes:
        out += hashlib.sha256(key + struct.pack("<Q", ctr)).digest()
        ctr += 1
    return bytes(out[:nbytes])


def xor(a, b):
    return bytes(x ^ y for x, y in zip(a, b))


# --- deterministic wordlist for human phrases (256 period-flavoured words) ---
WORDS = """
amber anvil ash atlas augur autumn basin beacon bedrock birch bloom bolt
border boulder brace braid brass breach breeze briar bridge brine brook
burrow cairn canvas cedar chalk channel charcoal chime cinder cipher clay
cliff clover coast cobalt cog coil compass copper coral cord cove crane
creek crest crimson cross current cypress dale dawn delta dusk ember
estuary fable falcon fathom fern field flint flock ford forge fossil
foxglove frost furrow gale garnet gate glacier glen granite gravel grove
gulf harbor hazel hearth heath heron hollow horizon ingot inlet iron
island ivory juniper keel kiln lagoon lantern lark laurel ledger lily
linden lodestone loom lunar magnet mantle maple marble marsh mast meadow
meridian mesa mill mineral mist moor mortar moss mould myrrh north
notch oak oasis obsidian ochre onyx opal orchard ore otter outcrop
paddock pale parchment passage peat pebble perch pine plumb pole pond
prairie prism quarry quartz quay quest rain rapids raven reed reef
relay ridge rivet roan rook root rope rowan ruin saddle salt sand
sapling scarlet sextant shale shard sheaf shelter shoal shore signal
slate slope smoke snow sod solder spire spring spur stable station
steel stone storm strand summit survey suture talc talon tarn teak
tempest terrace thicket thorn tide timber tin topaz torch trace trail
trench tundra twine vale valley vault verdant vertex vessel violet
vista wadi walnut ward wattle wedge weir wharf wheel willow winter
zephyr zero zinc
""".split()

assert len(set(WORDS)) >= 200, len(set(WORDS))


def pick_words(seed_bytes, count):
    stream = sha256ctr(seed_bytes, count * 2)
    return [WORDS[struct.unpack("<H", stream[2 * i:2 * i + 2])[0] % len(WORDS)]
            for i in range(count)]


# ---------------- Stage 0 (P3) ----------------

def stage0_token():
    s = seed("prambh:stage0:token:v1")
    return "PRAMBH{zero_%s}" % s.hex()[:8]


def launch_phrase():
    return " ".join(pick_words(seed("prambh:launch:phrase:v1"), 6))


def capsule_content():
    return seed("prambh:capsule:content:v1")


def capsule_bin(phrase=None):
    phrase = phrase or launch_phrase()
    pad = hashlib.sha256(phrase.encode()).digest()
    return xor(capsule_content(), sha256ctr(pad, 32))
# ---------------- Flood corpus / fiction (P4) ----------------

FLOOD_LANE_LABEL = "prambh:flood:lane:v1"
FLOOD_CORPUS_LABEL = "prambh:flood:folio:v1"
CORPUS_FOLIOS = 450
FOLIO_BODY_LINES = 45
PLATE_CODE_LEN = 9

def loom_model():
    return "MERU-%d" % (2 + seed("prambh:loom:model:v1")[0] % 8)

def decoy_loom_model(real):
    for k in range(256):
        m = "MERU-%d" % (2 + seed("prambh:loom:model-decoy:v1")[k] % 8)
        if m != real:
            return m
    raise SystemExit("no decoy loom model")

def door_numbers():
    out = []
    stream = sha256ctr(seed("prambh:doors:numbers:v1"), 4096)
    i = 0
    while len(out) < 8:
        n = 100 + struct.unpack("<H", stream[2*i:2*i+2])[0] % 900
        if n not in out:
            out.append(n)
        i += 1
    return out

def real_door_index():
    return seed("prambh:doors:real:v1")[0] % 8

def real_door_number():
    return door_numbers()[real_door_index()]

def stitch_token(folio):
    return sha256ctr(seed("prambh:flood:stitch:v1", struct.pack("<I", folio)), 4).hex()

def gen_page_lines(label, tok, index):
    key = seed(label, tok.encode() + struct.pack("<I", index))
    stream = sha256ctr(key, 4096)
    lines = ["MERU FIELD SURVEY - folio %03d-%02d / stitch %s"
             % (100 + stream[0] % 900, stream[1] % 64, tok)]
    for li in range(FOLIO_BODY_LINES):
        base = 2 + li * 16
        nw = 5 + stream[base] % 6
        words = [WORDS[stream[base + 1 + j] % len(WORDS)] for j in range(nw)]
        line = " ".join(words)
        if stream[base + 11] & 1:
            line += " = %d.%02d m" % (stream[base + 12] % 40, stream[base + 13] % 100)
        lines.append(line)
    return lines

def corpus_page_lines(folio):
    return gen_page_lines(FLOOD_CORPUS_LABEL, stitch_token(folio), 0)

def needle_texts():
    lm = loom_model()
    dn = real_door_number()
    return {
        0: ["capsule provenance, stitched from the surveyor's original:",
            "the launch capsule answers only the full phrase, all six words,",
            "in order, exactly as written on the loose launch sheet.",
            "no shorter form was ever accepted. trust no copy of the sheet."],
        1: ["loom identification, stitched from the surveyor's original:",
            "the survey loom is a %s, third merit badge, valley issue." % lm,
            "its stitch manual, the datasheet folio, lists the one true",
            "program cartridge among the samples. no other manual applies."],
        2: ["hall survey provenance, stitched from the surveyor's original:",
            "of the eight halls only one survey was ever finished: hall %d." % dn,
            "the folio for hall %d is the only one the loom will keep." % dn,
            "every other hall folio was a duplicate pulled from the mirror."],
        3: ["mirror campaign history, stitched from the surveyor's original:",
            "the mirror campaign produced duplicate surveys, page for page,",
            "for every hall the expedition feared to lose. the duplicates",
            "were kept, not destroyed. a mirrored survey leads nowhere."],
        4: ["plate reading method, stitched from the surveyor's original:",
            "three eye plates survive. stare through the dot plate until",
            "the depth resolves. read the hue plate's red channel in plain",
            "daylight. rotate the line plate against its twin until the",
            "hidden number aligns. nothing else on the plates is data."],
    }

def decoy_texts():
    dm = decoy_loom_model(loom_model())
    dd = door_numbers()[(real_door_index() + 3) % 8]
    return {
        0: ["capsule provenance, recovered from a secondary copy:",
            "the launch capsule was later rekeyed to a single word.",
            "any one word of the launch sheet, spoken alone, opens it.",
            "the full-phrase story was expedition folklore."],
        1: ["loom identification, recovered from a secondary copy:",
            "the survey loom is a %s, first merit badge, coast issue." % dm,
            "its stitch manual was lost; any valley datasheet serves.",
            "the cartridge samples are interchangeable."],
        2: ["hall survey provenance, recovered from a secondary copy:",
            "of the eight halls the only finished survey is hall %d." % dd,
            "hall %d was re-surveyed twice; the second folio is the",
            "authoritative one. the loom keeps the newest page."],
        3: ["mirror campaign history, recovered from a secondary copy:",
            "the mirror campaign produced duplicate surveys, but the",
            "duplicates were burned at the valley depot. any mirror",
            "folio found today is certainly a modern forgery."],
        4: ["plate reading method, recovered from a secondary copy:",
            "three eye plates survive. the dot plate is decoration.",
            "read the hue plate's blue channel under lamplight only.",
            "the line plate aligns once, upside down, by moonlight."],
    }

def _folio_pick(label, count, exclude):
    out = []
    for i in range(256):
        b = seed(label, struct.pack("<I", i))
        v = (b[0] + 256 * b[1]) % CORPUS_FOLIOS
        if v not in exclude and v not in out:
            out.append(v)
        if len(out) == count:
            return out
    raise SystemExit("folio pick exhausted")

def needle_folios():
    return _folio_pick("prambh:flood:needle:v1", 5, set())

def decoy_folios():
    return _folio_pick("prambh:flood:decoy:v1", 5, set(needle_folios()))

def decoy_plate_codes():
    return [sha256ctr(seed("prambh:plates:decoy:code:v1", struct.pack("<I", k)),
                      PLATE_CODE_LEN).hex()
            for k in range(6)]


def loom_seed_material(capsule_hex_content):
    """chain #1 seed from opened capsule content (spec 4.4)."""
    return seed("prambh:loom:seed:v1", capsule_hex_content)


def loom_debug_pan():
    """debug-lane cartridge pan (trap catalogue D-DBG; spec 4.4)."""
    return seed("prambh:loom:debug:v1")


def loom_decoy_cart(k):
    """cartridge constant for decoy ROM k (trap catalogue D-ROM-1..3)."""
    return seed("prambh:loom:decoy:v1", struct.pack("<I", k))


def decoy_capsule_phrases():
    """The designed wrong launch phrases (trap catalogue D-CAP-1..4):
    word-order and one-word-swap misreadings of the real phrase."""
    words = launch_phrase().split()
    d1 = " ".join(reversed(words))                       # reversed order
    d2 = " ".join(words[1:] + words[:1])                 # rotated
    alt = pick_words(seed("prambh:launch:alts:v1"), 2)
    d3 = " ".join([alt[0]] + words[1:])                  # first word wrong
    d4 = " ".join(words[:5] + [alt[1]])                  # last word wrong
    return [d1, d2, d3, d4]


def capsule_open(phrase):
    """What any phrase yields: a format-valid 32-byte load vector."""
    pad = hashlib.sha256(phrase.encode()).digest()
    return xor(capsule_bin(), sha256ctr(pad, 32))


def zip_passphrase():
    """Seal words for the distributed prambh.zip.enc (AES-256,
    hidden in the room description; organizer-only, KEYS row)."""
    return " ".join(pick_words(seed("prambh:release:zip:v1"), 4))


def canary_token():
    s = seed("prambh:canary:token:v1")
    return "PRAMBH{canary_%s}" % s.hex()[:8]


# ---------------- Hall of Doors (P6) ----------------

def door_seed(i):
    """Per-door key seed (spec 4.5: K_i uses this 'seed')."""
    return seed("prambh:doors:seed:v1", struct.pack("<Q", i))


def door_phrases():
    """The 8 designed candidate phrases (spec 4.5): index
    real_door_index() is the verse's real answer; the other seven are the
    designed misreadings, one decoy chamber each."""
    return [pick_words(seed("prambh:doors:phrase:v1", struct.pack("<Q", k)), 6)
            for k in range(8)]


def door_phrase(k):
    return " ".join(door_phrases()[k])


def real_phrase():
    return door_phrase(real_door_index())


def door_ink():
    """The real chamber's plate-fragment ink (8 bytes, hex).  It is only
    ever legible inside the real chamber, never in a shipped file."""
    return seed("prambh:doors:ink:v1")[:8].hex()


def door_decoy_vector(k):
    """Chain vector for the k-th decoy chamber's walk (k = 1..7)."""
    return seed("prambh:doors:decoy:vector:v1", struct.pack("<Q", k))


# ---------------- Eyes: chain #2 (P8) ----------------

def chain2_vector():
    """Chain #2 seed material handed over by the real chamber (spec 4.7)."""
    return seed("prambh:eyes:chain2:vector:v1")


def chain2_seed(vector=None):
    return seed("prambh:eyes:seed:v1", vector if vector else chain2_vector())


# ---------------- Mirror Room (P7) ----------------

def mirror_stage_a_seed():
    """Stage A of the Duplicate Survey's two-stage chain."""
    return seed("prambh:mirror:stage-a:v1")


def mirror_stage_b_seed(out_a):
    """Stage B seed, chained from stage A's output (spec 4.6)."""
    return seed("prambh:mirror:stage-b:v1", out_a)


def mirror_dead_end_title(out_b):
    """The single title mirror_validate accepts (a registered decoy)."""
    return "PRAMBH{mirror_%s}" % out_b[:8].hex()


def mirror_milestone_token():
    """The Duplicate Survey's own milestone mark (registered decoy)."""
    return "PRAMBH{dup_%s}" % seed("prambh:mirror:token:v1").hex()[:8]


def mirror_values():
    """Harvested two-stage chain values (runs/mirror_chain.txt)."""
    import os
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)))), "organizer-private", "runs",
        "mirror_chain.txt")
    vals = {"a": "", "b": "", "title": ""}
    if os.path.exists(path):
        for line in open(path):
            if line.startswith("stage A out"):
                vals["a"] = line.split("=")[1].split()[0].strip()
            elif line.startswith("stage B out"):
                vals["b"] = line.split("=")[1].split()[0].strip()
            elif line.startswith("dead-end title"):
                vals["title"] = line.split("=")[1].strip()
    return vals


# ---------------- Eyes: glyph codes, inks, final title (P8) ----------------

# "a defined alphabet" (spec 4.7): 6-char glyph codes, ambiguous glyphs out
GLYPH_ALPHABET = "23579ACDEFGHJKLMNPQRTUVWXY"


def glyph_code(label, k):
    stream = sha256ctr(seed(label, struct.pack("<Q", k)), 6)
    return "".join(GLYPH_ALPHABET[b % len(GLYPH_ALPHABET)] for b in stream)


def eyes_code(i):
    """The real glyph code of plate i (i = 0,1,2 in the normative order)."""
    return glyph_code("prambh:eyes:code:v1", i)


def eyes_ink():
    return "_".join(eyes_code(i) for i in range(3))


def decoy_eyes_code(kind, i=0):
    """Registered decoy codes: the SIRDS second depth plane, the hue
    plate's luminance channel, the moire reciprocal bearing."""
    return glyph_code("prambh:eyes:decoy:%s:v1" % kind, i)


def seal_ink(chain2_out):
    """Seal ink = hex(out[0:8]) of chain #2 (spec 4.7)."""
    return chain2_out[:8].hex()


def door_ink_from_chamber():
    return door_ink()


def final_title(chain2_out, chain1_out):
    """spec 4.7 (normative order):
    PRAMBH{seal_ink_loom_ink_door_ink_eyes_ink}"""
    return "PRAMBH{%s_%s_%s_%s}" % (seal_ink(chain2_out), chain1_out[:8].hex(),
                                    door_ink(), eyes_ink())


def title_digest(title):
    """The validator stores ONLY SHA-256(title)."""
    return hashlib.sha256(title.encode()).digest()


def eyes_notes_key(chain2_out):
    """K_eyes = chain #2 output; it opens eyes_notes.bin."""
    return chain2_out


    print("launch phrase:", launch_phrase())
    print("capsule.bin  :", capsule_bin().hex())
    print("content      :", capsule_content().hex())
    print("loom seed    :", loom_seed_material(capsule_content()).hex())
    for i, p in enumerate(decoy_capsule_phrases(), 1):
        dv = capsule_open(p)
        print("decoy D-CAP-%d: %r -> load vector %s" % (i, p, dv.hex()))
    ok = capsule_open(launch_phrase()) == capsule_content()
    print("self-check: real phrase opens capsule:", ok)
