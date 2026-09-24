#!/bin/bash
# Phase 0 acceptance: every tool must print a path, else STOP.
missing=0
for t in musl-gcc gcc make gdb zip unzip cppcheck exiftool convert jq pngcheck strace python3 git objdump readelf nm strings xxd file objcopy bc openssl; do
  if command -v "$t" >/dev/null 2>&1; then
    echo "OK   $t -> $(command -v $t)"
  else
    echo "MISSING $t"
    missing=1
  fi
done
musl-gcc --version | head -1
python3 -c "import zlib,hashlib,hmac,struct,secrets,PIL,numpy,http.server;print('py deps OK')"
[ $missing -eq 0 ] && echo "PHASE0-TOOLS OK" || echo "PHASE0-TOOLS NOT OK"
