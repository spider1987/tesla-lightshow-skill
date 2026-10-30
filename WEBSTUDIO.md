# Lightshow Studio

Lokale Weboberflaeche und selbst hostbare Anwendung fuer MP3 → ZIP mit genau
zwei gleich benannten Dateien: MP3 (44,1 kHz) und FSEQ v2 unkomprimiert.
Die vorhandenen Shows in `LightShow/` werden von der Webanwendung nicht veraendert.

## Auf diesem Windows-Rechner

```powershell
.\start-studio.cmd
```

Danach `http://localhost:8080` im Browser oeffnen. Zum Beenden Strg+C.
Der CMD-Starter funktioniert auch bei gesperrten PowerShell-Skripten;
eine Aenderung der ExecutionPolicy ist nicht erforderlich.
Die in dieser Arbeitsumgebung installierten Pakete liegen projektlokal in
`.tools/python`. Der Starter erkennt auch den vorhandenen Blender-Python.

## Auf einem anderen Rechner

Python 3.11 oder neuer installieren. Aus dem Projektordner:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements-web.txt
.venv\Scripts\python run_studio.py
```

Linux/macOS:

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements-web.txt
.venv/bin/python run_studio.py
```

FFmpeg wird zuerst aus `FFMPEG_PATH`, dann aus dem System-PATH und sonst
aus dem installierten imageio-ffmpeg-Paket verwendet. Kein Upload zu externen
Analyse-/Musikdiensten. Fuer die erstmalige Installation ist Internet erforderlich.

## Docker / eigener Server

`.env.example` als `.env` kopieren und eigene Werte fuer `SHOW_USERNAME` und
`SHOW_PASSWORD` eintragen. Keine Zugangsdaten in Quellcode oder Befehlsargumente schreiben.

```sh
docker compose up -d --build
```

Die Anwendung laeuft auf Port 8080 und fragt nach den eigenen Zugangsdaten.
Standardmaessig ist der Docker-Port nur an 127.0.0.1 gebunden. Fuer LAN-Nutzung
`SHOW_BIND_ADDRESS` auf die gewuenschte Hostadresse setzen.
Fuer oeffentlichen Zugriff einen HTTPS-Reverse-Proxy vorschalten. Beim Proxy
Uploadlimit mindestens 51 MB, Request-Timeout fuer den Upload passend waehlen.
Die lange Analyse laeuft als Hintergrundjob, Statusabfragen sind kurze Requests.
Die Anwendung wird unter `/` betrieben; ein Unterpfad wird nicht unterstuetzt.
Keine oeffentliche Freigabe oder DNS-/Proxy-Aenderung wird automatisch vorgenommen.

Direkter Netzwerkbetrieb ohne Docker:
`SHOW_USERNAME` und `SHOW_PASSWORD` als Umgebungsvariablen setzen und mit
`python run_studio.py --host 0.0.0.0` starten. Ohne Zugangsdaten verweigert der
Starter das Binden an eine Netzwerkadresse. Die Anmeldung ist HTTP Basic und
sollte ausserhalb eines vertrauenswuerdigen lokalen Netzes nur ueber HTTPS erfolgen.

## Bedienung

1. MP3 auswaehlen oder hineinziehen (standardmaessig maximal 50 MB / 10 Minuten).
2. Fahrzeug, Lichtdichte und Farbwelt auswaehlen.
3. Bildschirm und passende Ambientelichtsegmente aktivieren. Model 3 vor 2024
   unterstuetzt hier nur den Bildschirm; unbestaetigte Innenraumleuchten sind nicht enthalten.
4. Optional Spiegel, elektrische Heckklappe/Frunk und Ladeklappe einzeln aktivieren.
   Fenster und Tueren werden nie angesteuert. Ausstattung und Umgebung selbst pruefen.
5. Show erstellen, die Licht-Zeitleiste mit Musik anhoeren und das ZIP herunterladen.
6. ZIP entpacken, beide Dateien in `LightShow/` auf einen geeigneten USB-Stick legen.

Die Lichtdichte steht im ZIP-Namen und in beiden enthaltenen Dateinamen,
z. B. `Mein Song - Ruhig.zip`, `Mein Song - Ruhig.mp3` und `Mein Song - Ruhig.fseq`.
Bei aktivierter Heckklappe gibt es zwei Varianten: `Am Start oeffnen, am Ende
schliessen` (Standard, mindestens 19 Sekunden Musik; Schliessbeginn vier Sekunden
vor Ende) und `Tanzbewegungen zur Musik` (bisherige Hoehepunkt-Choreografie).
Die Variante steht ebenfalls im ZIP-/MP3-/FSEQ-Namen. Die Zeiten sind
Sequenzbefehle; die tatsaechliche Bewegung ist am Fahrzeug zu pruefen.

Die Dichte aendert Ereignisschwellen, Mindestabstaende und Haltezeiten. Die
Farbwelten steuern Display/Ambientelicht, nicht die Farbe der Aussenleuchten.
Der Lichtversatz ist von -2000 bis +2000 ms in 20-ms-Schritten einstellbar.
Standard ist +500 ms: alle Licht-/RGB-Befehle kommen eine halbe Sekunde spaeter.
Negative Werte ziehen sie vor. Bewegungen und Musik bleiben unveraendert.
Die Showdauer bleibt gleich; Befehle ausserhalb der Zeitgrenzen entfallen.
Die Vorschau zeigt die bereits verschobenen Lichtbefehle. Fuer bestehende
Downloads muss eine neue Show mit dem gewuenschten Versatz erstellt werden.
Mit der Bassoption bleiben Kanaele 1-4 auf Bassereignisse beschraenkt.
Das Frequenzrollenprofil gilt fuer Model 3/Highland/Y/S/X. Der Cybertruck nutzt
seinen eigenen Komponisten wegen anderer Lichtleisten-/Heckbelegung.
Die Zeitleiste ist eine aggregierte Befehlsvorschau, keine physikalische
Simulation von Rampen, Verschlusspositionen oder gemessener Helligkeit.
Modell und Fahrzeugsoftware bestimmen die tatsaechlich sichtbaren Funktionen.

## Daten, Grenzen und Neustarts

- Ein Job verarbeitet gleichzeitig, insgesamt drei Plaetze inklusive Warteschlange.
- Status, Dateien und Ergebnisse liegen lokal unter `runtime/jobs` bzw. im
  Docker-Volume `studio-data`. Die API kennt nur zufaellige Job-IDs, keine Dateipfade.
- Upload und Analyse-WAV werden nach erfolgreicher Verarbeitung sofort geloescht.
- ZIP, Vorschau und Wiedergabe-MP3 verfallen standardmaessig 24 Stunden nach Upload.
  Bereinigung laeuft jede Minute und bei neuen Anfragen; abgelaufene Links liefern 404.
- Fertige Ergebnisse bleiben nach Neustarts bis zum Ablauf verfuegbar; laufende
  und wartende Jobs werden als abgebrochen markiert und muessen neu hochgeladen werden.
- Limits konfigurierbar: `SHOW_MAX_UPLOAD_MB`, `SHOW_MAX_DURATION` (Sekunden),
  `SHOW_RETENTION_HOURS`, `SHOW_MAX_JOBS`, `SHOW_WORKER_TIMEOUT` (Sekunden).
  Hoehere Dauerlimits brauchen mehr RAM; die Analyse haelt Spektraldaten im Speicher.
- Genau eine Webserver-Instanz / ein Uvicorn-Worker pro Datenverzeichnis verwenden.
  Keine geteilte Warteschlange fuer mehrere Container vorgesehen.
- Containerupdates: `docker compose build --pull` und `docker compose up -d`.
  Das Volume nicht loeschen, wenn Downloads erhalten bleiben sollen.

## Tests

```sh
python -m pip install -r requirements-test.txt
python -m unittest discover -s tests -v
python scripts/test_music_regressions.py
```

Tests erzeugen kurze synthetische Audiodateien und pruefen den echten
Upload-/Worker-/Analyse-/ZIP-Ablauf, Modell-/Effekteinstellungen, Basszuordnung,
Anmeldung, Ablaufbereinigung und Fehlerfaelle. Kein Fahrzeugtest.

## Stand der Pruefung (27.10.2026)

- 11 Web-/API-/Generator-Tests und 3 bestehende Musik-Regressionstests bestanden.
- Vollstaendige vorhandene DJ-Snake-MP3 ueber die laufende HTTP-API verarbeitet;
  ZIP enthaelt genau MP3 + FSEQ. Ergebnis und Audiowiedergabe/Zeitleiste im
  Chrome-Browser sichtbar geprueft.
- Die gemeinsame Frequenzrollenfunktion reproduziert die vorhandene
  Feuer-Frei-v3-Aussenlicht-/Displaysequenz bytegleich.
- Browserautomatischer Dateiupload ist wegen fehlender Dateizugriffsberechtigung
  der Browsererweiterung nicht abgeschlossen. Der Upload ueber die HTTP-API ist
  getestet; die App selbst benoetigt diese Erweiterung nicht.
- Docker-/Compose-Konfiguration vorbereitet; mangels Docker auf diesem Rechner
  kein Imagebuild oder Container-Laufzeittest. Kein Fahrzeugtest.
