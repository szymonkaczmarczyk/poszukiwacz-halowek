#!/bin/zsh
set -u
KATALOG="${0:A:h}"
ETYKIETA="pl.szatnia.modele3d"
cd "$KATALOG/../.."
"$KATALOG/.venv/bin/python" -I "$KATALOG/generuj.py"
if "$KATALOG/.venv/bin/python" -I "$KATALOG/generuj.py" --brakujace; then
  echo "$(date '+%Y-%m-%d %H:%M') Koniec: wyłączam codzienne uruchamianie."
  rm -f "$HOME/Library/LaunchAgents/$ETYKIETA.plist"
  launchctl bootout "gui/$(id -u)/$ETYKIETA"
fi
