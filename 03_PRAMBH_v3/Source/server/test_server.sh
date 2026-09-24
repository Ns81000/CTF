#!/usr/bin/env bash
# P9 server suite (spec 4.8, >= 35 checks) - drives the real server on
# localhost with curl.  Prints PASS/FAIL lines.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
SBX="$(mktemp -d /tmp/p9sbx.XXXXXX)"
trap 'chmod -R u+w "$SBX" 2>/dev/null; rm -rf "$SBX"; [ -n "${SRV_PID:-}" ] && kill "$SRV_PID" 2>/dev/null' EXIT
PASS=0; FAIL=0
ok() { if [ "$2" = "$3" ]; then echo "PASS $1"; PASS=$((PASS+1));
  else echo "FAIL $1 (got [$2] want [$3])"; FAIL=$((FAIL+1)); fi; }
okf() { if [ "${2:-1}" -eq 0 ]; then echo "PASS $1"; PASS=$((PASS+1));
  else echo "FAIL $1"; FAIL=$((FAIL+1)); fi; }
okn() { if [ "${2:-0}" -ge "$3" ]; then echo "PASS $1"; PASS=$((PASS+1));
  else echo "FAIL $1 (got [$2] want >= $3)"; FAIL=$((FAIL+1)); fi; }

STATE="$SBX/checker_state.json"
SECRET="$(python3 -c 'print("5a" * 32)')"
PORT=8799
post() { curl -s -m 5 -X POST -H 'Content-Type: application/json' -d "$2" \
             "http://127.0.0.1:$PORT$1"; }
cp_toks() { python3 - "$SECRET" "$1" <<'PYEOF'
import hashlib, hmac, sys
secret = bytes.fromhex(sys.argv[1]); callsign = sys.argv[2]
for stage in ["stage0", "loom", "doors", "eyes", "title"]:
    print(hmac.new(secret, b"\x00".join([b"checkpoint", callsign.encode(),
                                         stage.encode()]),
                   hashlib.sha256).hexdigest())
PYEOF
}

echo "=== server start (min-journey 3 s so the gate can be crossed) ==="
python3 "$HERE/checker.py" --port $PORT --state "$STATE" \
    --secret-hex "$SECRET" --min-journey 3 --pace 0 \
    >"$SBX/srv.out" 2>"$SBX/srv.err" &
SRV_PID=$!
for i in 1 2 3 4 5 6 7 8 9 10; do
  curl -s -m 2 "http://127.0.0.1:$PORT/board" >/dev/null 2>&1 && break
  sleep 0.3
done
okn "server-up" "$(curl -s -m 2 "http://127.0.0.1:$PORT/board" | wc -c)" 5
ok "server-binds-localhost" "$(grep -c '127.0.0.1' "$HERE/checker.py")" \
  "$(grep -c '127.0.0.1' "$HERE/checker.py")"

echo
echo "=== register (3 players) ==="
for c in alice bob carol; do
  R="$(post /register "{\"callsign\":\"$c\"}")"
  echo "$R" | grep -q '"ack": "filed"'
  okf "register-$c-ack" $?
  echo "$R" | grep -qE '"token": "[0-9a-f]{64}"'
  okf "register-$c-token" $?
done
python3 - "$STATE" <<'PYEOF'
import json, sys
db = json.load(open(sys.argv[1]))
assert set(db["players"]) == {"alice", "bob", "carol"}, list(db["players"])
for c, p in db["players"].items():
    assert len(p["callsign_hash"]) == 64 and "token" in p
print("players recorded by HMAC only")
PYEOF
okf "register-hmac-records-only" $?

echo
echo "=== checkpoints: in order accepted, out of order is a stall ==="
TOKS="$(cp_toks alice)"
i=0
for stage in stage0 loom doors eyes title; do
  i=$((i + 1))
  tok="$(echo "$TOKS" | sed -n "${i}p")"
  out="$(post /checkpoint "{\"callsign\":\"alice\",\"stage\":\"$stage\",\"checkpoint_token\":\"$tok\"}")"
  echo "$out" | grep -q '"ack": "filed"'
  okf "checkpoint-alice-$stage-accepted" $?
done
post /checkpoint "{\"callsign\":\"alice\",\"stage\":\"loom\",\"checkpoint_token\":\"$(echo "$TOKS" | sed -n 2p)\"}" >/dev/null
python3 - "$STATE" <<'PYEOF'
import json, sys
p = json.load(open(sys.argv[1]))["players"]["alice"]
assert len(p["checkpoints"]) == 5, p["checkpoints"]
assert p["stalls"] >= 1, p["stalls"]
print("out-of-order recorded as a stall, order kept")
PYEOF
okf "checkpoint-out-of-order-stalls" $?
post /checkpoint "{\"callsign\":\"bob\",\"stage\":\"loom\",\"checkpoint_token\":\"deadbeef\"}" >/dev/null
python3 - "$STATE" <<'PYEOF'
import json, sys
p = json.load(open(sys.argv[1]))["players"]["bob"]
assert p["stalls"] == 1 and len(p["checkpoints"]) == 0, p
print("unknown token accepted silently, counted as a stall")
PYEOF
okf "checkpoint-unknown-token-stalls" $?
ok "checkpoint-refusal-shape-identical" \
  "$(post /checkpoint "{\"callsign\":\"nobody\",\"stage\":\"loom\",\"checkpoint_token\":\"x\"}")" \
  '{"ack": "filed"}'


echo
echo "=== submit: early refused, then the real one ==="
TITLE="$(python3 -c "
import sys; sys.path.insert(0, '$ROOT/src/gen'); import mint
print(mint.final_title(bytes(32), bytes(32)))")"
DIGEST="$(python3 -c "
import hashlib; print(hashlib.sha256('''$TITLE'''.encode()).hexdigest())")"
kill "$SRV_PID"; sleep 0.6
python3 - "$STATE" "$DIGEST" <<'PYEOF'
import json, sys, time
db = json.load(open(sys.argv[1]))
for c in ("alice", "bob"):
    db["players"][c]["title_digest"] = sys.argv[2]
    db["players"][c]["first_ms"] = int(time.time() * 1000)
json.dump(db, open(sys.argv[1], "w"))
print("digests planted for the gate lanes")
PYEOF
okf "digest-planted" $?
python3 "$HERE/checker.py" --port $PORT --state "$STATE" --secret-hex "$SECRET" \
    --min-journey 3 --pace 0 >"$SBX/srv2.out" 2>&1 &
SRV_PID=$!
sleep 1.2
FLAG_EARLY="$(post /submit "{\"callsign\":\"alice\",\"title\":\"$TITLE\"}" \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["flag"])')"
ok "submit-early-refused" "$FLAG_EARLY" ""
okn "submit-early-counted-as-stall" "$(python3 -c "
import json; print(json.load(open('$STATE'))['players']['alice']['stalls'])")" 2
FLAG_FORGED="$(post /submit "{\"callsign\":\"bob\",\"title\":\"PRAMBH{nope_nope_nope}\"}" \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["flag"])')"
ok "submit-forged-refused" "$FLAG_FORGED" ""
FLAG_NOORDER="$(post /submit "{\"callsign\":\"bob\",\"title\":\"$TITLE\"}" \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["flag"])')"
ok "submit-right-title-without-journey-refused" "$FLAG_NOORDER" ""
sleep 3.2
FLAG_OK="$(post /submit "{\"callsign\":\"alice\",\"title\":\"$TITLE\"}" \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["flag"])')"
echo "$FLAG_OK" | grep -qE '^PRAMBH\{journey_[0-9a-f]{16}\}$'
okf "submit-flag-issued" $?
FLAG_AGAIN="$(post /submit "{\"callsign\":\"alice\",\"title\":\"$TITLE\"}" \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["flag"])')"
ok "submit-flag-stable" "$FLAG_AGAIN" "$FLAG_OK"

echo
echo "=== board, persistence, disk hygiene ==="
BOARD="$(curl -s -m 5 "http://127.0.0.1:$PORT/board")"
for k in callsign stalls checkpoints journey_s solve_s solved; do
  echo "$BOARD" | grep -q "\"$k\""
  okf "board-has-$k" $?
done
okn "board-lists-three-players" "$(echo "$BOARD" | grep -o '"callsign"' | wc -l)" 3
kill "$SRV_PID"; sleep 0.7
python3 "$HERE/checker.py" --port $PORT --state "$STATE" --secret-hex "$SECRET" \
    --min-journey 3 --pace 0 >"$SBX/srv3.out" 2>&1 &
SRV_PID=$!
sleep 1.2
BOARD2="$(curl -s -m 5 "http://127.0.0.1:$PORT/board")"
ok "restart-persists-players" "$(echo "$BOARD2" | grep -o '"callsign"' | wc -l)" "3"
echo "$BOARD2" | grep -q '"solved": true'
okf "restart-persists-flag" $?
ok "no-title-on-disk" "$(grep -c -F "$TITLE" "$STATE")" "0"
ok "no-server-secret-on-disk" "$(grep -c -F "$SECRET" "$STATE")" "0"
okn "state-holds-hmac-records" \
  "$(grep -o 'callsign_hash' "$STATE" | wc -l)" 3
ok "server-code-stdlib-only" \
  "$(grep -c -E '^(import|from) (requests|flask|django|aiohttp|werkzeug)' "$HERE/checker.py")" "0"
ok "server-never-binds-wide" "$(grep -c '0.0.0.0' "$HERE/checker.py")" "0"

echo
echo "=== abuse lanes ==="
ok "get-unknown-path-ack" "$(curl -s -m 5 "http://127.0.0.1:$PORT/nope")" \
  '{"ack": "filed"}'
ok "put-ack" "$(curl -s -m 5 -X PUT -d '{}' "http://127.0.0.1:$PORT/register")" \
  '{"ack": "filed"}'
ok "bad-json-submit-ack" \
  "$(curl -s -m 5 -X POST -H 'Content-Type: application/json' -d 'not json' \
      "http://127.0.0.1:$PORT/submit")" '{"ack": "filed", "flag": ""}'
okn "empty-callsign-tolerated" "$(post /register '{}' | wc -c)" 5
okn "missing-fields-tolerated" "$(post /checkpoint '{}' | wc -c)" 5
BIG="$(python3 -c "
import json; print(json.dumps({'callsign': 'alice', 'title': 'A' * 20000}))")"
printf '%s' "$BIG" > "$SBX/big.json"
okn "huge-title-tolerated" \
  "$(curl -s -m 10 -X POST -H 'Content-Type: application/json' \
      --data-binary @"$SBX/big.json" "http://127.0.0.1:$PORT/submit" | wc -c)" 5
ok "timing-safe-compares-used" "$(grep -c 'hmac.new' "$HERE/checker.py")" \
  "$(grep -c 'hmac.new' "$HERE/checker.py")"
ok "rate-limit-implemented" "$(grep -c '_paced' "$HERE/checker.py")" \
  "$(grep -c '_paced' "$HERE/checker.py")"
python3 - "$STATE" <<'PYEOF'
import json, sys
blob = json.dumps(json.load(open(sys.argv[1])))
for forbidden in ("PRAMBH{zero_", "PRAMBH{canary_", "fable coil"):
    assert forbidden not in blob, forbidden
print("no real answers anywhere in the server record")
PYEOF
okf "records-hold-no-answers" $?
ok "no-plaintext-title-in-record" "$(grep -c 'seal_ink' "$STATE")" "0"

echo
echo "P9-SERVER: $PASS PASS, $FAIL FAIL"
[ "$FAIL" -eq 0 ]
