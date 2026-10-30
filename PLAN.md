# Display-RGB-Erweiterung

## Webstudio (lokal und eigener Server)

- FastAPI mit buildfreier deutscher Oberflaeche, MP3-Upload und validierten Modelleinstellungen.
- Bestehendes Frequenzrollen-Profil als wiederverwendbare Funktion extrahieren. Modellunterschiede erhalten; Cybertruck nutzt modellgerechten Komponisten statt Model-3-Kanalrollen.
- Hintergrundjobs in separaten Prozessen, begrenzte Uploads/Dauer/Warteschlange, Fortschritt, Ablaufbereinigung, ZIP mit genau zwei Dateien.
- FFmpeg fuer 44,1-kHz-MP3 und Analyse-WAV, keine Shellinterpolation von Dateinamen. Bewegungen einzeln und standardmaessig deaktiviert.
- Authentifizierung fuer Serverbetrieb, standardmaessig nur Loopback, Docker und lokale Startanleitungen.
- Licht-Zeitleiste aus echten FSEQ-Daten mit synchroner Audiowiedergabe. API-/Generator-/ZIP-/Bereinigungstests und Browserpruefung soweit verfuegbar.

Ergebnis: Webstudio implementiert, 11 Web-/API-/Generatortests und 3 Musiktests
bestanden. Vollstaendige DJ-Snake-MP3 per HTTP bis zum geprueften Zwei-Dateien-ZIP
verarbeitet; Ergebnis und Audiovorschau im Browser sichtbar. Browserautomatischer
Dateiupload durch Erweiterungsberechtigung begrenzt. Dockerlauf mangels Docker
nicht geprueft. Bestehende LightShow-Dateien unveraendert.

## DJ Slon / DJ Snake

- Beide Quellen haben 48 kHz: fuer die Wiedergabe in 44,1-kHz-MP3 mit 320 kbit/s umwandeln, Original-MP3s als .original.mp3 archivieren; WAV nur intern fuer die Analyse.
- Frequenzrollen-v3 fuer Model 3 vor 2024 anwenden; neue Basisbewegungen mit bestehendem Model-3-Komponisten erzeugen und Budgets pruefen.
- Neon-Palette fuer Ja ne dam, Feuer-Palette fuer Turn Down for What; Front-Hauptscheinwerfer ausschliesslich Bass.
- Abspielbare MP3/FSEQ-Paare in LightShow, Quellen und Berichte im Archiv. MP3-Kopien hashgleich pruefen und doppelte Originalnamen archivieren.

## Frequenzrollen v3 und Ordnerbereinigung

- Hauptscheinwerfer 1-4 ausschliesslich fuer erkannte Bassanschlaege; Signatur und Ruecklicht fuer harmonische Begleitung, Scheinwerfersegmente fuer Mitten, Seitenlichter fuer Hoehen.
- Blinker als Phrasenakzente, Bremslicht als Bassbegleitung; Rueckfahrlicht und Nebelschlussleuchte sparsam bei starken Bassereignissen.
- Displaypalette folgt Harmonie, Helligkeitsakzente folgen Bass. Kein Hinzuerfinden unbestaetigter Innenraumkanaele.
- BEARWOLF und Feuer Frei als v3 erzeugen und Bass-Exklusivitaet der Hauptscheinwerfer maschinell pruefen.
- LightShow enthaelt danach nur aktuelle abspielbare Paare: die beiden v3-Shows, Ponzoo Display-RGB, Vegas und Halloween Evil. Aeltere Varianten, Quell-MP3s und Arbeitsdateien nach archive/show-sources verschieben; Validierungsberichte nach archive/validation.

## Dichtere Musiksteuerung v2

- Intro-Ausloesung und verlorene Beat-/Onset-Ereignisse im Basiskomponisten korrigieren.
- Separates dichtes Model-3-Profil: lokale Frequenzschwellen, getrennte Bass-/Mitten-/Hoehenereignisse, wiederkehrende Wechselmuster, laengere sichtbare Impulse.
- Neue -v2-Dateipaare fuer BEARWOLF und Feuer Frei; Originale und vorhandene Bewegungsdaten unveraendert erhalten.
- Pruefung gegen Originaldaten, Format, Dauer, Hardware-Gruppierung und Lichtdichte; gezielte Regressionstests fuer die gefundenen Logikfehler. Fahrzeugbewertung bleibt notwendig.

## Rammstein - Feuer Frei

- Gleicher Model-3-Workflow mit vorhandener MP3, 44,1-kHz-WAV und 200-Kanal-Ausgabe.
- Feurige Rot-/Orange-/Gold-Verlaeufe auf dem Display, Rhythmusimpulse und dynamische Aussenbeleuchtung.
- Format, volle Musikdauer, Displaybelegung und Bewegungsbudgets vor Auslieferung pruefen.

## BEARWOLF - Владивосток

- Neue Show fuer dasselbe Model 3 vor 2024 aus vorhandener MP3 erstellen.
- Lokal mit VLC in 44,1-kHz-Stereo-PCM umwandeln und mit dem vorhandenen Audioanalyzer auswerten.
- Vorhandenen Model-3-Komponisten fuer Aussenlicht/Bewegungen verwenden; Display als einzige RGB-Flaeche ergaenzen (200 Kanaele).
- Cyan/Blau/Magenta mit musikalischen Akzenten und weichen Uebergaengen; Ein-/Ausblenden und Schluss-Schwarz.
- Format, Audio-/Show-Dauer, RGB-Belegung und Bewegungsbudgets pruefen. Fahrzeugtest bleibt offen.

- Ziel: vorhandene ponzoo-this-is-halloween-Show fuer Model 3 vor 2024 um Displayfarben erweitern.
- Originaldateien unveraendert erhalten; separate Variante mit identisch benannter WAV erstellen.
- 48 Originalkanaele je Frame unveraendert in 200 Kanaele uebernehmen; nur Display-RGB 176-178 ergaenzen. Andere Erweiterungskanaele bleiben null.
- Halloween-Palette Orange/Violett/Gruen, weiche Farbwechsel, audioabhaengige Helligkeit und Ein-/Ausblenden.
- Format gegen Tesla-Validatorregeln pruefen, alle Originalkanaele byteweise vergleichen und Audiokopie per SHA-256 pruefen. Kein Fahrzeugtest verfuegbar.
