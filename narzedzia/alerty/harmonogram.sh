#!/bin/zsh
set -eu
KATALOG="${0:A:h:h:h}"
ETYKIETA="pl.szatnia.alerty"
PLIST="$HOME/Library/LaunchAgents/$ETYKIETA.plist"
DOMENA="gui/$(id -u)"

if [[ "${1:-}" == "--wylacz" ]]; then
  launchctl bootout "$DOMENA/$ETYKIETA" 2>/dev/null || true
  rm -f "$PLIST"
  echo "Automatyczne sprawdzanie alertów wyłączone."
  exit 0
fi

PYTHON="$KATALOG/.venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
  echo "Brak $PYTHON. Najpierw uruchom uruchom.command albo utwórz .venv z requirements.txt."
  exit 1
fi

GODZINY=($(cd "$KATALOG" && "$PYTHON" -c 'from szukacz import ustawienia as U; print(*U.GODZINY_ALERTOW)'))
TERMINY=""
for GODZINA in $GODZINY; do
  TERMINY+="    <dict><key>Hour</key><integer>$GODZINA</integer><key>Minute</key><integer>0</integer></dict>
"
done

mkdir -p "$KATALOG/dane" "${PLIST:h}"
cat > "$PLIST" <<PLIK
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$ETYKIETA</string>
  <key>ProgramArguments</key>
  <array>
    <string>$PYTHON</string>
    <string>$KATALOG/szukaj.py</string>
    <string>--sprawdz-alerty</string>
  </array>
  <key>WorkingDirectory</key><string>$KATALOG</string>
  <key>StartCalendarInterval</key>
  <array>
$TERMINY  </array>
  <key>StandardOutPath</key><string>$KATALOG/dane/alerty.log</string>
  <key>StandardErrorPath</key><string>$KATALOG/dane/alerty.log</string>
  <key>ProcessType</key><string>Background</string>
</dict>
</plist>
PLIK

launchctl bootout "$DOMENA/$ETYKIETA" 2>/dev/null || true
launchctl bootstrap "$DOMENA" "$PLIST"
echo "Alerty sprawdzają się codziennie o godzinach: ${(j:, :)GODZINY}. Log: dane/alerty.log"
