#!/bin/bash
# Usage : test_site.sh <dossier data/ d'une construction> <dossier de résultats> [port] [tickers séparés par des virgules]
# Parcours complet du site local : toutes les fonctions et tous les onglets (texte, infobulles, liens, erreurs JavaScript),
# iPhone 13 (débordement horizontal, textes suspects), QLAB 48 actions × 6 vues. Requiert playwright (Chromium) et terser.
H=$(cd "$(dirname "$0")" && pwd)
D=$1; O=$2; P=${3:-8841}; T=${4:-SNTS,CABC,BOAC,BICC,SAFC,SGBC,PALC,NTLC,ONTBF,AAPL}
mkdir -p "$O"; O=$(cd "$O" && pwd)
bash "$H/mksite.sh" "$D" "$O/site" > /dev/null
(cd "$O/site" && exec python3 -m http.server "$P" >/dev/null 2>&1) & SRV=$!
sleep 2
U=http://localhost:$P/index.html
timeout 5000 python3 "$H/crawl_txt.py" "$U" "$O/parcours.json" "$T" > "$O/parcours.log" 2>&1 & C=$!
timeout 3000 python3 "$H/mobilecheck.py" "$U" "$O/mobile.json" > "$O/mobile.log" 2>&1
wait $C
timeout 3000 python3 "$H/qlab3all.py" "$H/ids48.json" "$U" > "$O/qlab.log" 2>&1
kill $SRV
python3 "$H/mots_interdits.py" "$O/parcours.json"
echo "--- parcours"; cat "$O/parcours.log"; echo "--- iPhone"; tail -4 "$O/mobile.log"; echo "--- QLAB"; tail -4 "$O/qlab.log"
