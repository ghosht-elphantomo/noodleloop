#!/bin/bash
# Ouvre le terminal sur ce Mac : petit serveur local (aucune connexion Internet nécessaire), puis le navigateur.
cd "$(dirname "$0")" || exit 1
PORT=8765
( sleep 1; open "http://localhost:$PORT/" ) &
if command -v python3 >/dev/null 2>&1; then
  python3 -m http.server "$PORT" --bind 127.0.0.1
else
  echo "Python 3 est nécessaire : installez-le (python.org) ou lancez « xcode-select --install », puis relancez ce fichier."
  read -r -p "Appuyez sur Entrée pour fermer."
fi
