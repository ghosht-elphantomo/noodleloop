#!/bin/bash
# Vérification complète du terminal (données + site) : un seul script, à lancer AVANT et APRÈS chaque modification.
#
# Usage : verifier.sh <dossier data/> <dossier de résultats> [rapport de référence .json] [--meme-donnees] [--sans-site]
#   - <dossier data/> : données à contrôler (par exemple la branche data extraite dans /tmp/d/data) ;
#   - <dossier de résultats> : reçoit rapport.json, rapport.md et, sauf --sans-site, le parcours du site (parcours.json…) ;
#   - [rapport de référence] : rapport d'un contrôle précédent (avant la modification, ou de la veille) pour comparer ;
#   - --meme-donnees : la référence a été faite sur les mêmes données (essai avant / après une modification du code) :
#     tout chiffre clé changé est signalé ;
#   - --sans-site : contrôle des données seulement (une minute au lieu d'une quinzaine).
# Résultat : vert / orange / rouge, affiché et écrit dans rapport.md. Le script ne fait jamais échouer qui l'appelle.
H=$(cd "$(dirname "$0")" && pwd); R=$(cd "$H/../.." && pwd)
D=$1; O=$2; shift 2
REF=""; MEME=""; SITE=1
for a in "$@"; do
  case "$a" in
    --meme-donnees) MEME="--meme-donnees" ;;
    --sans-site) SITE=0 ;;
    *) REF="$a" ;;
  esac
done
mkdir -p "$O"; O=$(cd "$O" && pwd)
ARGS=()
if [ "$SITE" = 1 ]; then
  bash "$R/outils/essais/test_site.sh" "$D" "$O" "${PORT:-8843}" > "$O/site.log" 2>&1 || true
  ARGS+=(--site "$O/parcours.json" --mobile "$O/mobile.json" --qlab "$O/qlab.log")
fi
[ -n "$REF" ] && ARGS+=(--ref "$REF")
[ -n "$MEME" ] && ARGS+=("$MEME")
# bugs corrigés : passages GitHub des dernières 24 h et index de la branche comptes, quand controle.yml les fournit
[ -n "$RUNS" ] && [ -f "$RUNS" ] && ARGS+=(--runs "$RUNS")
[ -n "$COMPTES" ] && [ -f "$COMPTES" ] && ARGS+=(--comptes "$COMPTES")
# taille des branches et annotations des passages du terminal (controle.yml)
[ -n "$BRANCHES" ] && [ -f "$BRANCHES" ] && ARGS+=(--branches "$BRANCHES")
[ -n "$ANNOT" ] && [ -f "$ANNOT" ] && ARGS+=(--annot "$ANNOT")
[ -n "$DIVN" ] && [ -f "$DIVN" ] && ARGS+=(--divn "$DIVN")
# cohérence : bulletins officiels de l'année (boc_px), quand controle.yml les fournit
[ -n "$BOC" ] && [ -d "$BOC" ] && ARGS+=(--boc "$BOC")
python3 "$H/controle.py" "$D" "$O/rapport.json" --md "$O/rapport.md" "${ARGS[@]}" --titre "${TITRE:-Contrôle du terminal}" || true
exit 0
