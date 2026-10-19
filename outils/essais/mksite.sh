#!/bin/bash
# Usage : mksite.sh <dossier data/ d'une construction> <dossier du site local>
# Site local = page compilée (build.py, terser requis) + données réécrites comme par le relais api/data.js.
H=$(cd "$(dirname "$0")" && pwd); R=$(cd "$H/../.." && pwd)
D=$1; O=$2
rm -rf "$O" && mkdir -p "$O"
(cd "$R" && python3 build.py >/dev/null 2>&1) && cp "$R/index.html" "$O/index.html"
node "$H/rw.js" "$R/api/data.js" "$D" "$O/data"
[ -f "$O/data/eia_wpsr.json" ] && cp "$O/data/eia_wpsr.json" "$O/data/oil_w.json"
ls "$O/data" | wc -l
