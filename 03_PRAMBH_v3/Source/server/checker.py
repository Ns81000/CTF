#!/usr/bin/env python3
"""PRAMBH checker server (spec 4.8) - EVENT mode, organizer-side only.

Python 3 standard library only.  Never shipped in the player zip.

  POST /register   {callsign}                  -> mints the player package token
  POST /checkpoint {callsign, stage, token}    -> ordered timestamps, stalls counted
  POST /submit     {callsign, title}           -> the proof-of-journey flag, gated
  GET  /board                                  -> leaderboard

The floor is feature I (the sequenced work in the package); MIN_JOURNEY is a
backstop: a player who idles for four hours still owes the chains.

usage: checker.py [--port N] [--state FILE] [--secret-hex HEX]
                  [--min-journey SECONDS] [--pace SECONDS] [--epoch E]
"""
import hashlib
import hmac
import json
import os
import secrets
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ACK = {"ack": "filed"}
DEFAULT_MIN_JOURNEY = 14400          # spec dial: 4 h
DEFAULT_PACE = 0.5
STAGES = ["stage0", "loom", "doors", "eyes", "title"]


def now_ms():
    return int(time.time() * 1000)


class Store:
    """Server state: HMAC records only - no plaintext titles, no answers."""

    def __init__(self, path, secret, min_journey, epoch):
        self.path = path
        self.secret = secret
        self.min_journey = min_journey
        if os.path.exists(path):
            with open(path) as f:
                self.db = json.load(f)
        else:
            self.db = {"players": {}, "epoch": epoch, "min_journey": min_journey}
        self.lock = threading.Lock()

    def mac(self, *parts):
        return hmac.new(self.secret, b"\x00".join(
            p.encode() if isinstance(p, str) else p for p in parts),
            hashlib.sha256).hexdigest()

    def save(self):
        tmp = self.path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(self.db, f)
        os.replace(tmp, self.path)

    def register(self, callsign):
        with self.lock:
            p = self.db["players"].setdefault(callsign, {
                "callsign_hash": self.mac("callsign", callsign),
                "title_digest": "", "first_ms": 0, "last_ms": 0,
                "checkpoints": [], "stalls": 0, "solved_ms": 0, "flag": "",
            })
            p["token"] = self.mac("package", callsign)
            self.save()
            return p

    def set_title_digest(self, callsign, digest_hex):
        with self.lock:
            p = self.db["players"].get(callsign)
            if p and digest_hex:
                p["title_digest"] = digest_hex
                self.save()

    def checkpoint(self, callsign, stage, token):
        with self.lock:
            p = self.db["players"].get(callsign)
            if not p:
                return None
            ts = now_ms()
            if not p["first_ms"]:
                p["first_ms"] = ts
            p["last_ms"] = ts
            idx = len(p["checkpoints"])
            good = (token == self.mac("checkpoint", callsign, stage)
                    and stage in STAGES and STAGES.index(stage) == idx)
            if good:
                p["checkpoints"].append({"stage": stage, "at": ts})
            else:
                p["stalls"] += 1
            self.save()
            return p

    def submit(self, callsign, title):
        with self.lock:
            p = self.db["players"].get(callsign)
            if not p:
                return ""
            ts = now_ms()
            if not p["first_ms"]:
                p["first_ms"] = ts
            p["last_ms"] = ts
            digest = hashlib.sha256(title.encode()).hexdigest()
            in_order = [c["stage"] for c in p["checkpoints"]] == STAGES
            long_enough = (ts - p["first_ms"]) >= self.min_journey * 1000
            if digest and digest == p.get("title_digest") and in_order \
                    and long_enough:
                if not p["flag"]:
                    p["flag"] = "PRAMBH{journey_%s}" % self.mac("flag",
                                                               callsign)[:16]
                    p["solved_ms"] = ts
            else:
                p["stalls"] += 1
            self.save()
            return p["flag"]

    def board(self):
        rows = []
        for c, p in self.db["players"].items():
            rows.append({"callsign": c, "stalls": p["stalls"],
                         "checkpoints": len(p["checkpoints"]),
                         "journey_s": int((p["last_ms"] - p["first_ms"]) / 1000)
                         if p["first_ms"] else 0,
                         "solve_s": int((p["solved_ms"] - p["first_ms"]) / 1000)
                         if p["solved_ms"] else 0,
                         "solved": bool(p["flag"])})
        return sorted(rows, key=lambda r: (-r["solved"], r["stalls"]))


class Handler(BaseHTTPRequestHandler):
    server_version = "prambh-checker/1.0"
    store = None
    pace = DEFAULT_PACE
    last_hit = {}

    def log_message(self, *a):
        pass

    def _send(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        try:
            return json.loads(self.rfile.read(n) or b"{}")
        except ValueError:
            return {}

    def _paced(self):
        ip = self.client_address[0]
        t = time.time()
        if t - Handler.last_hit.get(ip, 0.0) < Handler.pace:
            return False
        Handler.last_hit[ip] = t
        return True

    def do_GET(self):
        if self.path.split("?")[0] == "/board":
            self._send({"board": self.store.board()})
        else:
            self._send(ACK)

    def do_PUT(self):
        self._send(ACK)

    def do_POST(self):
        path = self.path.split("?")[0]
        data = self._body()
        callsign = str(data.get("callsign", ""))[:64]
        if not self._paced():
            self._send(ACK)
            return
        if path == "/register":
            p = self.store.register(callsign)
            self._send({"ack": "filed", "token": p["token"]})
        elif path == "/checkpoint":
            self.store.checkpoint(callsign, str(data.get("stage", "")),
                                  str(data.get("checkpoint_token", "")))
            self._send(ACK)
        elif path == "/submit":
            flag = self.store.submit(callsign, str(data.get("title", "")))
            self._send({"ack": "filed", "flag": flag})
        else:
            self._send(ACK)


def build_server(port, state, secret, min_journey, pace, epoch=0):
    Handler.store = Store(state, secret, min_journey, epoch)
    Handler.pace = pace
    Handler.last_hit = {}
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    srv.prambh_store = Handler.store
    return srv


def main(argv):
    port = 8724
    state = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "checker_state.json")
    secret = secrets.token_bytes(32)
    min_journey = DEFAULT_MIN_JOURNEY
    pace = DEFAULT_PACE
    epoch = int(time.time() * 1000)
    i = 1
    while i < len(argv):
        a = argv[i]
        if a == "--port":
            port = int(argv[i + 1]); i += 2
        elif a == "--state":
            state = argv[i + 1]; i += 2
        elif a == "--secret-hex":
            secret = bytes.fromhex(argv[i + 1]); i += 2
        elif a == "--min-journey":
            min_journey = int(argv[i + 1]); i += 2
        elif a == "--pace":
            pace = float(argv[i + 1]); i += 2
        elif a == "--epoch":
            epoch = int(argv[i + 1]); i += 2
        else:
            sys.stderr.write(__doc__)
            return 2
    srv = build_server(port, state, secret, min_journey, pace, epoch)
    sys.stderr.write("checker listening on 127.0.0.1:%d\n" % port)
    sys.stderr.flush()
    srv.serve_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

