# Untersuchung: Lichtdichte und Musiksteuerung

## Umsetzung v2

Neue separate Dateipaare BEARWOLF-Владивосток-v2 und Rammstein-Feuer-Frei-v2 erstellt. Keine Originalshow ueberschrieben. Drei Regressionstests fuer Intro-Anschlaege und Beat-/Onset-Unterdrueckung bestehen.

Das dichte Profil verwendet lokale Bandspitzen gegen einen gleitenden Zwei-Sekunden-Vergleich, Ereignisabstaende von 180-320 ms und Impulse von 140-260 ms. Wiederkehrende Muster wechseln nach 16 Anschlaegen zwischen breiten Front-/Heckakzenten, Links/Rechts, Kreuzmustern und breiten gemeinsamen Akzenten. Ruhige gehaltene Musik erhaelt Begleitimpulse mit bewussten Pausen. Displayfarben wechseln nach musikalischen Ereignissen statt nach festen Zeitintervallen. Modell-3-Gruppierungen werden beruecksichtigt.

| Kennzahl | Feuer Frei vorher / v2 | BEARWOLF vorher / v2 |
|---|---:|---:|
| Ohne Aussenlicht-Einschaltwert | 64,97 / 19,56 % | 69,02 / 13,91 % |
| Frontlicht aktiv | 31,26 / 80,44 % | 27,28 / 86,09 % |
| Mittlere aktive Model-3-Lichtgruppen | 1,65 / 9,11 | 1,45 / 9,88 |

Die laengste Dunkelstelle bei Feuer Frei liegt im sehr leisen Ausklang (RMS der urspruenglichen langen Schlussluecke etwa 0,009). Sie wird nicht kuenstlich mit Dauerlicht gefuellt. Alle Bewegungsdaten sind bytegleich erhalten, die WAV-Kopien sind hashgleich. 200-Kanal-Format, Dateilaenge, Schluss-Schwarz und ausschliessliche Nutzung von Display-RGB im Erweiterungsbereich werden geprueft. Keine neue Tempoanalyse, keine physische Fahrzeugpruefung und keine Behauptung einer bereits perfekten musikalischen Choreografie.

Untersucht am 26.10.2026: cs-hall-os.pack, xlights_overview.png, vorhandener Python-Komponist und alle sechs vorhandenen FSEQ-Dateien. Keine Shows bei dieser Untersuchung veraendert.

## Dateimessung

Anteil Frames ohne Einschaltwert (Byte >=128) auf den 30 Aussenlichtkanaelen; Display und Bewegungen nicht mitgezaehlt. Dies ist eine Auswertung der Befehlsdaten, keine gemessene Fahrzeughelligkeit. Rampen, zusammengelegte Ausgaenge und fehlende Hardware beeinflussen das reale Ergebnis.

| Show | Ohne Aussenlicht-Einschaltwert | Mittlere Anzahl aktiver Kanaele von 30 | Mindestens ein Frontkanal aktiv (1-16) |
|---|---:|---:|---:|
| Rammstein-Feuer-Frei | 65,0 % | 2,14 | 31,3 % |
| BEARWOLF | 69,0 % | 1,85 | 27,3 % |
| ponzoo-this-is-halloween | 7,5 % | 5,28 | 87,5 % |
| ponzoo mit Display-RGB | 7,5 % | 5,28 | 87,5 % |
| vegas | 6,6 % | 4,29 | 83,6 % |
| halloween-evil | 89,4 % | 0,22 | 7,3 % |

Die Ponzoo-RGB-Erweiterung hat wie beabsichtigt identische Aussenlichtdaten zum Original. Die beiden neu komponierten Shows haben deutlich weniger Lichtaktivitaet als Ponzoo und Vegas.

## Ursachen im Komponisten

- Ohne nutzbare Segmente legt _plan_sections pauschal 15 % Intro, 40 % Aufbau, 30 % Hoehepunkt und 15 % Outro fest. Bei den beiden neuen Shows wurden die unzuverlaessigen Fallback-Segmente deaktiviert. Dadurch gelten diese starren Grenzen trotz bereits kraeftiger Musik.
- _beat_layer verwirft im Intro und Outro drei von vier Beats, im Aufbau viele weitere Beats. Bei langsam/halbzeitig erkanntem Rhythmus entstehen zusaetzlich grosse Luecken.
- _onset_layer: Im Intro wird hit_strength = min(1,strength) * section_intensity berechnet. Die Intro-Intensitaet erreicht maximal etwa 0,5, die Ausloeseschwelle liegt aber bei 0,7. Dieser Zweig kann daher niemals feuern.
- Die Onset-Ebene verwirft Anschlaege innerhalb +/-80 ms um jeden erkannten Beat. Das gilt auch fuer Beats, die die Beat-Ebene zuvor wegen der Abschnittsregeln verworfen hat: Hier koennen beide Ebenen denselben musikalischen Moment auslassen.
- Viele Impulse dauern nur 60-120 ms, manche 40 ms. Sie ergeben wenig Einschaltdauer. Langsamere Rampen sind fuer kurze Rhythmusimpulse ebenfalls kein Ersatz fuer ausreichend sichtbare Haltezeiten.
- _baseline ist absichtlich leer. Mehrere weitere Ebenen haben hohe Schwellen, lange Mindestabstaende oder Zufallsfilter. Das summiert sich zu einem sehr sparsamen Ergebnis.
- Die Analyse lief nur mit numpy-stereo, ohne zusaetzlichen Beat-Tracker. Die ausgegebenen Tempi sind Schaetzungen; eine gute musikalische Synchronisierung wurde durch die bisherigen Formatpruefungen nicht belegt.

## Was cs-hall-os.pack anders macht

Das Paket ist eine FiveM-Ressource, keine Tesla-Sequenz. Untersucht wurde die Implementierung, kein laufender Spielserver.

- client/dui/javascript/script.js: Web-Audio-FFT mit 4096 Punkten, Glaettung 0,8 und Frequenzdaten alle 50 ms.
- Fuenf unabhaengige Baender: Bass 20-140 Hz, LowMid 140-400 Hz, Mid 400-2600 Hz, HighMid 2600-5200 Hz, Treble 5200-14000 Hz.
- client/core.lua: fortlaufende Mittelwerte pro Band; Auswahl des Bandes pro Scheinwerfer. Die Lichtfarbe wird anhand der Ueberschreitung des Vergleichspegels in ihrer Helligkeit moduliert.
- Das uebertragbare Prinzip ist die parallele Reaktion mehrerer Lichtgruppen auf unterschiedliche Musikanteile mit angepassten Schwellen. Die RGB-/Helligkeitssteuerung des Spiels laesst sich nicht unveraendert auf die Schalt- und Rampenbefehle der Tesla-Aussenlichter uebertragen.

## Was das Bild zeigt

xlights_overview.png zeigt eine dicht belegte Timeline mit parallelen und wechselnden Frontlichtgruppen sowie laenger gehaltenen Hecklichtspuren. Es zeigt ein Model-S-Vorschaumodell. Das Bild enthaelt keine auslesbare Sequenz und beweist weder die Synchronitaet noch das Model-3-Ergebnis. Beim Model 3 werden unter anderem Channel 4-6 und Aux-Park/Side-Marker zusammengelegt; eine dort sichtbare Einzelkanalfolge ist deshalb nicht 1:1 als separater Effekt am Model 3 sichtbar.

## Empfohlener naechster Umbau

1. Unmoegliche Intro-Schwelle und verlorene Onset-/Beat-Ereignisse korrigieren.
2. Abschnittsdichte aus lokaler Musikenergie und Ereignisdichte steuern, kraeftige Intros nicht pauschal ausduennen.
3. Bass auf breite Front-/Heckakzente, Mitten auf Signatur/Nebel und Hoehen auf Seiten-/Blinkergruppen verteilen. Haltezeiten etwa 120-250 ms als Ausgangspunkt mit echten Dunkelluecken abstimmen.
4. Wiedererkennbare Wechselmuster und gehaltene Begleitspuren statt ueberwiegend vereinzelter kurzer Blitze verwenden. Model-3-Gruppierung beachten.
5. Displaypalette staerker mit musikalischen Ereignissen und Abschnitten verknuepfen statt hauptsaechlich zeitgesteuerte Farbwechsel zu verwenden.
6. Separate dichtere Varianten von BEARWOLF und Feuer Frei erstellen. Originale, Audio und Bewegungsdaten erhalten. Vorher/Nachher-Dichte, musikalische Ausloesungen und Format pruefen; Fahrzeugwirkung anschliessend beurteilen.

Als Vergleich dienen Ponzoo und Vegas. Deren Befehlsdichte ist eine Orientierung und kein pauschales Helligkeitsziel: Eine gute Show braucht auch bewusste Pausen und klare Muster.
