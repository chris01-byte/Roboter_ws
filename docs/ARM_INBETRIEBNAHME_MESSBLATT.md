# Arm-Inbetriebnahme: Messblatt und Versuchsprotokoll

**Stand: 11.11.2026 — rekonstruiertes Arbeitsblatt mit ersten Nutzerangaben.**
Keine Tabellenzeile ist eine bestandene Abnahme. Einträge mit dem Vermerk
„Nutzerangabe“ oder „aus CAD“ stammen aus der Konstruktion
(Fusion-360-Modell) und Aussagen des Entwicklers; sie ersetzen keine Messung
am Gerät. Als Messung gelten nur die ausdrücklich so bezeichneten Höhen vom
10.11.2026.
Entwicklungsreihenfolge und Kriterien:
[Integrationsplan](INTEGRATIONSPLAN_ARM_SOFTWARE.md).
Quellen und Bestand: [Arm-Kontext](ARM_KONTEXT.md).

Dieses Blatt als Vorlage verwenden. Reale Rohdaten, Bilder und Bags lokal
ablegen; nur bereinigte Zusammenfassungen ohne Wohnungsdaten ins Repository
übernehmen. Je Versuch eine eigene Kennung vergeben. Ein Feld bleibt
„offen“, bis es belegt ist; unbekannt ist weder null Grad noch bestanden.

## 1. Sitzung und Nachvollziehbarkeit

| Feld | Eintrag |
|---|---|
| Versuch-ID / Datum / Uhrzeit mit Zeitzone | offen |
| Bediener / anwesende Aufsicht | offen |
| Stufe M0, M1A, M1B, M2 … | offen |
| Zweck / genau eine zu prüfende Hypothese | offen |
| Software-Commit / installierter Paketstand | offen |
| Config-ID / SHA256 / lokale Konfigurationsdatei | offen |
| Betriebsart validate / fake / readonly / später Bewegung | offen |
| Arm separat oder auf Roboter montiert | offen |
| Anfangspose / Abstützung / mechanische Sicherung | offen |
| Last, Werkzeug und Kabelführung | offen |
| Not-Aus / Haltekonzept geprüft durch | offen |
| Vor-Ort-Freigabe für genau diesen Versuch | offen |
| Messmittel / Auflösung / Messunsicherheit | offen |
| Lokaler Rohdatenpfad / Referenz auf bereinigte Ergebnisse | offen |

**Für Versuche mit Bewegung zusätzlich vorher festlegen:** zulässiger Weg,
Geschwindigkeit, Beschleunigung, Zeit, Last, Strom-/Kraftgrenzen soweit
messbar, Stopweg, Verantwortlichkeit und Verhalten bei Stromausfall.
Ohne begründete Werte keine Bewegung. Build A besitzt keine Bewegungsfunktion.

## 2. Bestandsaufnahme: Hubachse und sechs Drehgelenke

Gesamtbestand laut Angabe vom 10.10.2026: **5 × ESS17-RS07 und 1 × NEMA23**.
Nutzerangabe 08.11.: Alle Schrittmotoren sind ESS-RS, der NEMA23 sitzt in J1.
Welche ESS17 Hubachse, J2–J5 und das neue J6 antreiben, ist offen. J1–J6
folgen der Nutzerzuordnung vom 08.11.2026; die späteren URDF-Namen sind noch
nicht festgelegt. Farben beziehen sich auf das Fusion-360-Modell.

| Achse | Physische Funktion / Lage (Nutzerangabe 08.11.) | Exakter Motor / Typenschild | Firmware | Getriebe / Übersetzung | Bus-ID |
|---|---|---|---|---|---|
| Hub | hebt und senkt den ganzen Arm, 400 mm, vertikale Linearführung mit Spindel | offen | offen | Spindeltyp und Steigung offen | offen |
| J1 | Schulter heben, große blaue Schulter am Hubschlitten | NEMA23 der ESS-RS-Reihe; Typenschild offen | offen | 55,25:1 (Nutzerangabe 08.11.) | offen |
| J2 | Schulter seitlich schwenken, weiße Schulter 130 mm vor J1; laut CAD vom 11.11. senkrechte Achse bei waagerechtem Arm | ESS-RS; Typenschild offen | offen | 72:1 (Nutzerangabe 08.11.) | offen |
| J3 | Ellenbogen, oranges Gelenk | ESS-RS; Typenschild offen | offen | 72:1 (Nutzerangabe 08.11.) | offen |
| J4 | Unterarm drehen, grünes Gelenk hinter dem Ellenbogen | ESS-RS; Typenschild offen | offen | 72:1 (Nutzerangabe 08.11.) | offen |
| J5 | Handgelenk kippen, rotes Gelenk | ESS-RS; Typenschild offen | offen | 72:1 (Nutzerangabe 08.11.) | offen |
| J6 | Greifer drehen, schwarze Anschlussplatte für den Greifer | offen | offen | noch nicht realisiert | offen |

Weitere Nutzerangaben: Reichweite gestreckt etwa 746 mm ohne Greifer, ab der
vorderen Fläche des Hubschlittens (10.11.); Greifer bis etwa 150 mm;
Nutzlast höchstens 1 kg; Arm in Einzelteilen, noch nicht gewogen. Die
Schulterhöhe 1106 mm vom 08.11. stammte aus einem fehlerhaften STEP-Export.

**Gemessen vom Nutzer am 10.11.2026** (Messmittel und Unsicherheit nicht
angegeben): Mitte LiDAR-Sichtscheibe 705 mm, Mitte OAK 1350 mm,
Unterkante Hubschlitten 1140 mm über Boden (im CAD 1150 mm).

**Aus dem CAD vom 11.11.2026 (Arm neu konstruiert, gestreckte Pose), keine
Messung:** J1 bei 1211 mm Höhe; J2 130 mm vor J1 mit senkrechter Achse;
Armachse 94 mm über J1; J3 156 mm vor J2; J5 257 mm vor J3; Flanschfläche
149 mm vor J5; Unterarm 86 mm seitlich versetzt; gestreckt 755 mm ab
Schlittenvorderfläche. Real liegt der Arm rund 10 mm tiefer. Die Werte aus
den Exporten vom 09.11.2026 sind überholt.

Pro Achse ausfüllen:

| Merkmal | Wert / Einheit / Quelle |
|---|---|
| Achs-ID im Messblatt / späterer Gelenkname | offen |
| Identitätsnachweis / lokales Typenschildfoto | offen |
| Montageort, Drehachse, Bezugsrichtung | offen |
| Getriebehersteller, Bauart, Übersetzung G | offen |
| Definition G = Motorumdrehungen / Gelenkumdrehung bestätigt | offen |
| Mechanische Unter-/Obergrenze und Messbezug | offen |
| Kabel-/Schlauchgrenze innerhalb der Mechanik | offen |
| Spiel und Nachgiebigkeit unter definierter Last | offen |
| Gliederlängen, Achsversatz, Messskizze | offen |
| Getriebeselbsthemmung / Halteversuch-ID | offen |
| Stromloses Halten, Temperatur, Last und Dauer | offen |
| Sichere Abstützung bei möglichem Rücktreiben | offen |

Keine Stromabschaltung eines ungesicherten belasteten Gelenks zum
„Ausprobieren“. Halte- und Not-Aus-Konzept zuerst mechanisch absichern.

## 3. Versorgung und Bus

| Merkmal | Wert / Nachweis |
|---|---|
| Armversorgung, Nennspannung, gemessene Spannung unter Last | offen |
| Absicherung / Leitungsquerschnitt / Verpolschutz | offen |
| Wirkung des Not-Aus auf Arm, Basis, Greifer und Controller | Nutzerangabe 08.11.: trennt die komplette Stromversorgung des Roboters; ob auch der Jetson getrennt wird, offen |
| Halten beim Not-Aus / bei Netzteilausfall | offen; alle Achsen werden stromlos, Halten nur über Selbsthemmung |
| Dedizierter Arm-RS485-Adapter / stabiler Gerätepfad | Nutzerangabe 08.11.: eigener Adapter verbaut; Chip, Gerätepfad und udev-Alias offen |
| Elektrische Isolation / Masse- und Schirmkonzept | offen |
| Baudrate / Parität / Stopbits | offen |
| Terminierung an Busenden / Leitungstopologie | offen |
| Adressliste eindeutig; keine Doppeladresse | offen |
| Einziger Bus-Eigentümer / andere Dienste beendet | offen |
| Verbindung zur Fahrbasis ausgeschlossen | offen; die Fahrbasis nutzt `/dev/ttyUSB_BASE` mit den IDs 1 und 2 |
| Herstellerhandbuch-Version pro Motortyp | offen |

Den NEMA23 in J1 erst nach Typbestimmung und eigener Registerprüfung
zulassen. Fahrbasis-Register oder ESS17-Leseprofile nicht kopieren.

## 4. TLE4905L: Verdrahtung und Referenzsignal

**Vorgeschlagener Signalweg:** TLE4905L → geprüfte Pegel-/Stromschnittstelle
→ konfigurierter Referenzeingang des jeweiligen ESS-Antriebs.
Die genaue Verdrahtung wird erst aus der tatsächlichen Hardware freigegeben.

| Merkmal je Achse | Wert / Nachweis |
|---|---|
| Sensortyp, Stückzahl, Pinansicht aus Originaldatenblatt | offen |
| Versorgung VS und gemessene Spannung | offen |
| Magnettyp, Polung, Abstand und mechanische Befestigung | offen |
| Einzelmagnet: Typ, Radius, Abstand; Fensterbreite in Grad, von Hand gemessen | offen |
| Sensorzustand in der Parkstellung (Festlegung 11.11.2026: aktiv) | offen |
| Lage der Referenzkante: Fensterende auf der freien Seite, Abstand zur Parkstellung | offen; freie Seite je Achse laut CAD in [ARM_KONTEXT](ARM_KONTEXT.md#park--und-homing-pose-aus-dem-cad-vom-11112026) |
| Eingangsfunktion und Pegel X0–X3 (0x0040–0x0044) direkt nach dem Einschalten | offen; Hardware-Handbuch: unbestimmt, Registertabelle: X0 Ursprung |
| Sensorausgang inaktiv / aktiv, jeweiliger Spannungspegel | offen |
| Ausgangsstrom / zulässige Belastung / Temperaturbereich | offen |
| Anpassschaltung, Schaltplanrevision, Pull-up bzw. Eingangslast | offen |
| Massebezug oder galvanische Trennung | offen |
| ESS-Stecker / Pin / Eingang X… / XCOM-Beschaltung | offen |
| Eingang als Home konfiguriert / Funktion nach Neustart | offen |
| Aktive Polarität / Filter / sichere Flankenerkennung | offen |
| Signalzustand in der ESS-Diagnose geprüft | offen |
| Kabelbruch / Kurzschluss / fest aktives Signal erkannt wie? | offen |
| Getrennte Endlagen und mechanische Anschläge | offen |

Für ESS17 nennt das Hardware-Handbuch 24-V-Eingänge mit mindestens 10 mA
und ein Signal länger als 10 ms. Diese Vorgaben nicht als geprüfte
TLE-Direktverdrahtung interpretieren. Referenzgeber, Homing-Start und
Endschalter getrennt zuordnen. Keine 24 V an Jetson-GPIO oder TTL anschließen.

## 5. M0 und M1A: unmittelbar anstehende Aufnahme

M0-Ergebnis je Punkt: **offen / bestanden / nicht bestanden / nicht anwendbar
mit Begründung**. Kein Häkchen ohne Nachweis.

- [ ] Motorzuordnung und eigener Bus erfasst.
- [ ] Mechanik und Abstützung für die reine Diagnose geeignet.
- [ ] Versorgungs-, Not-Aus- und Halteverhalten geklärt.
- [ ] Für jede ausgewählte ESS17 Identitätsnachweis, Bus-ID und Profil bestätigt.
- [ ] Inventarvalidierung erfolgreich; fehlende Messwerte bleiben null.
- [ ] Tatsächlicher Paketstand auf dem Zielrechner bekannt.

M1A: nur die Read-only-Anweisung in
[arm_tools](../src/arm_tools/README.md) verwenden. Erst Fake-/Validierungslauf,
danach separat die reale Probe. Keine Busparameter raten; keine fremden
Geräte scannen. Erfolgreiches Lesen gibt keine Bewegungsfreigabe.

| Leseprobe | Eintrag |
|---|---|
| Achse / exakter Typ / Bus-ID | offen |
| Leseprofil / Herstellerbeleg | offen |
| Beide Vor-Ort-Bestätigungen dokumentiert | offen |
| Start/Länge 0x0000/4: unveränderte 16-Bit-Rohwörter | offen |
| Start/Länge 0x0006/7: unveränderte 16-Bit-Rohwörter | offen |
| Zeitstempel / Anzahl Proben / Dauer je Transaktion | offen |
| Timeout / Fehler / Verbindungsabbruch | offen |
| Log enthält reale Quelle und Config-SHA256 | offen |
| Ergebnis: gelesen / abgebrochen / nicht durchgeführt | offen |

Vorzeichen, Wortreihenfolge und Skalierung erst mit Herstellerbeleg und
späteren Messungen interpretieren. Ein plausibler Zahlenwert reicht nicht.

## 6. M1B: Einzelachsbewegung — spätere Softwarestufe

**Noch nicht mit Build A ausführbar.** Vor dem ersten Lauf getrennten
Bewegungsbuild, Befehlsregister, Betriebsart und Stopverhalten prüfen.

| Vorab festgelegte Versuchsgrenze | Wert / Begründung |
|---|---|
| Achse / Anfangspose / Last / Sicherung | offen |
| Positive Richtung geometrisch markiert | offen |
| Maximaler Weg und verbleibender Abstand zum Anschlag | offen |
| Maximale Geschwindigkeit / Beschleunigung | offen |
| Zeitgrenze / Abbruchkriterien | offen |
| Stopart / zulässiger Stopweg / Verhalten bei Kommunikationsverlust | offen |
| Bedienerfreigabe vor Bewegung | offen |

| Lauf | Befehl und Einheit | Rohwert vorher/nachher | Gemessener Gelenkwinkel | Dauer / Stopweg | Ergebnis |
|---|---|---|---|---|---|
| Positive Kleinbewegung | offen | offen | offen | offen | nicht durchgeführt |
| Negative Kleinbewegung | offen | offen | offen | offen | nicht durchgeführt |
| Richtungswechsel / Spiel | offen | offen | offen | offen | nicht durchgeführt |
| Stop / Abbruch | offen | offen | offen | offen | nicht durchgeführt |
| Kommunikationsfehler mit gesicherter Last | offen | offen | offen | offen | nicht durchgeführt |

Befehlszählung und Feedbackzählung separat bestimmen; Getriebeübersetzung
und Quadraturfaktor nicht doppelt anwenden. Jede Fehlerprüfung benötigt eine
gesicherte mechanische Ausgangslage.

## 7. M2: Home, Nullwinkel und Gelenkgrenzen

| Parameter je Achse | Messwert / Einheit / Quelle |
|---|---|
| Feedbackzählwerte je Motorumdrehung | offen |
| Befehlszählwerte je Motorumdrehung | offen |
| Getriebeübersetzung G | offen |
| Richtungsvorzeichen s | offen |
| Homing-Suchrichtung / Suchgeschwindigkeit | offen |
| Maximaler Suchweg / maximale Suchzeit | offen |
| Freifahrweg / Rückfahrtgeschwindigkeit / Referenzflanke | offen |
| C_home: Feedbackwert an definierter Referenz | offen |
| q_home: geometrischer Gelenkwinkel an dieser Referenz | offen |
| Definition und Wert von home_offset_rad | offen |
| Physische Grenzen / Kabelgrenzen | offen |
| Soft-Untergrenze / Soft-Obergrenze in rad | offen |
| Reserve für Stopweg, Fehler, Spiel und Kabel | offen |
| Abgenommene maximale Geschwindigkeit / Beschleunigung | offen |
| Referenz gültig nach Neustart? Begründeter Nachweis | offen |
| Positionszähler vor/nach Aus- und Einschalten bei unbewegtem Arm | offen |
| Schaltet der Sensor bei jeder Überfahrt an der gespeicherten Kante? | offen |
| Höchstweg und Geschwindigkeit der Suchfahrt; Höchstweg kleiner als Freiraum der Gegenrichtung | offen |
| Strom (0x0103) und Schleppfehlergrenze (0x010A) während der Referenzfahrt | offen |
| Übergabe per Referenzmodus 35 mit 0x0030 = 6: Positionswert danach, Soft-Limits wirksam? | offen |
| Verhalten beim Überfahren (0x0017, Soll: Not-Halt) und bei Err5 (hält oder frei?) | offen |
| J1-Anschlag: Winkel zur Parkstellung (CAD-Vorschlag höchstens 1–2°) | offen |
| Gelenkbereich je Achse aus Kabel- und mechanischen Grenzen | offen |

Home ist nicht automatisch der geometrische Nullwinkel. Alle Winkel mit
Messbezug angeben; Gradwerte ausdrücklich kennzeichnen und vor Übernahme
in rad umrechnen. Formel und Vorzeichenkonvention stehen im Integrationsplan.

| Home-Wiederholung | Startseite / Startwinkel | C_home | q_home gemessen | Abweichung | Ergebnis |
|---|---|---|---|---|---|
| 1 | offen | offen | offen | offen | nicht durchgeführt |
| 2 | offen | offen | offen | offen | nicht durchgeführt |
| 3 | offen | offen | offen | offen | nicht durchgeführt |
| Weitere Läufe | offen | offen | offen | offen | nicht durchgeführt |

Anzahl Wiederholungen und akzeptable Streuung **vorher** aus dem späteren
Positionsbudget festlegen. Zusätzlich gesichert prüfen: Start auf aktivem
Sensor, Sensor dauerhaft inaktiv/aktiv, verlorene Verbindung, Suchzeitende,
Neustart und Abbruch. Kein automatisches Wiederanfahren nach Fehler.

### Übernahme in die aktuelle JSON-Konfiguration

Heute unterstützt calibration die Felder gear_ratio,
feedback_counts_per_motor_rev, command_counts_per_motor_rev, direction_sign,
home_offset_rad, soft_lower_rad, soft_upper_rad, max_velocity_rad_s,
max_acceleration_rad_s2 und homing_direction_sign.
Die genaue Bedeutung mit [config.py](../src/arm_hardware/arm_hardware/config.py)
und dem Integrationsplan abgleichen.

Suchwege, Filter, Roh-Homewerte, Messunsicherheit, Schaltpläne und
Versuchsprotokolle gehören zunächst **hierher**. Das strikte JSON-Schema
lehnt zusätzliche Schlüssel ab. Eine spätere Schemaerweiterung braucht
eigene Validierung; runtime-Referenzgültigkeit folgt nicht aus einer Datei.

## 8. Reales Armmodell und koordinierte Bewegung

| Nachweis | Messung / Ergebnis |
|---|---|
| Geometrie aller Gelenkachsen / Glieder | offen |
| Sockel → Arm, Flansch → Werkzeug-TCP | offen |
| Kollisionskörper inkl. Leitungen und Greifer | offen |
| FK-Prüfpunkte: gemessene vs. berechnete TCP-Pose | offen |
| Rückmeldelatenz / Buszyklus / Jitter über alle Arm-Achsen | offen |
| Bahnabweichung / Gelenknachlauf unter definierter Last | offen |
| Gemeinsamer Start / Ende / Zwischenbahn geprüft | offen |
| Koordinierter Stop / Abbruch / veraltete Rückmeldung | offen |

Einzelne Motoren mit gleichzeitig gesendeten Zielwerten beweisen noch keine
zulässige räumliche Bahn. Erst nach diesen Messungen Controllerauslegung
und Integrationsfreigabe dokumentieren.

## 9. Neutrale Fahrpose stowed

| Achse | Winkel leer [rad] | Winkel mit Last [rad] | Toleranz | Gültiger Referenzzustand |
|---|---|---|---|---|
| Hub [m statt rad] | offen | offen | offen | offen |
| J1 | offen | offen | offen | offen |
| J2 | offen | offen | offen | offen |
| J3 | offen | offen | offen | offen |
| J4 | offen | offen | offen | offen |
| J5 | offen | offen | offen | offen |
| J6 | offen | offen | offen | offen |

CAD-Vorgabe für die Park-/Homing-Pose (STEP 11.11.2026, Modellkonvention mit
gestreckter Nullpose, keine Messung): Hub oben, J1 −180°, J2 −40°, J3 −90°,
J4 0°, J5 +20°, J6 0°. Erst nach Referenzierung gemessen eintragen.

| Prüfung | Ausgangsmessung / Pose / Ergebnis |
|---|---|
| LiDAR-Sicht mit/ohne Arm, vorhandene Mastabschattung getrennt | LiDAR-Scheibenmitte gemessen 705 mm; Parkpose laut CAD: tiefster Armpunkt real 698 mm, vom LiDAR aus bei 172°–186° im maskierten Mastsektor; Rohscan-Messung offen |
| OAK-Sichtbereich mit/ohne Arm und Last | Simulation aus CAD 11.11.: Arm gestreckt, 18,94° Neigung, 24 % verdeckt bei Hub oben, 4 % bei Hub unten; Parkpose 0 % bei 16:9 bis etwa 19°; praktische Prüfung offen |
| VL53-Sicht / Nahbereichsschutz | offen |
| Kabel, Bauhöhe, seitlicher Überstand und Kollisionsfreiheit | Parkpose laut CAD: vorn 23 mm und hinten 22 mm über das Chassis, seitlich innerhalb; engste Abstände 7–23 mm; freie Richtung je Achse in ARM_KONTEXT; J2-Gehäuse ragt bei waagerechtem Arm rund 160 mm vor die Chassisfront; Kabel offen |
| Zulässige Hubhöhe in Transportpose | Parkpose im CAD mit Hub oben; nach unten rechnerisch rund 164 mm frei ohne Greifer, rund 73 mm mit 150-mm-Greifer; Messung offen |
| Mechanische Abstützung der Transportpose | J1-Anschlag auf der Parkseite (Nutzer, 11.11.2026; Schwerkraft zieht dorthin), höchstens 1–2° hinter der Parkstellung; Bau und Prüfung offen |
| Lastmasse / Schwerpunkt / zulässige Basisbeschleunigung | Nutzlast höchstens 1 kg (Nutzerangabe 08.11.); Massen noch nicht gewogen |
| Kollisionsfreier Übergang ready ↔ stowed, leer und beladen | offen |
| Frische reale Gelenkwerte / Stillstand vor Basisfreigabe | offen |
| Erkundung, Navigation, Rückfahrt und Abbruchpfade abgesichert | offen |
| Verhalten bei verlorener Referenz oder veraltetem Armstatus | offen |

Keine Winkel aus dem Dummy-Modell übernehmen. Ein Action-Erfolg allein ist
kein Stellungsnachweis. Sichtprüfung auch während des Übergangs durchführen.

## 10. Greifer vor dem Bau und bei späterer Abnahme

| Konstruktionsdatum | Festlegung / Messung |
|---|---|
| XL330-Variante / Versorgung / TTL-Adapter | offen |
| Spindeltyp, Nenndurchmesser, Steigung, Gangzahl / Lead | offen |
| Ein oder zwei bewegte Backen / Öffnung je Spindelumdrehung | offen |
| Nutzbarer Öffnungsbereich / Geschwindigkeit unter Last | offen |
| Axiallagerung / Linearführung / Verdrehsicherung | offen |
| Öffnungs-Referenzschalter / zweite Endlagenüberwachung | offen |
| Mechanische Anschläge / Reserve vor Anschlag | offen |
| Wiederherstellung des Öffnungsbezugs nach Neustart | offen |
| Verhalten beim Neustart mit gehaltenem Objekt | offen |
| Manuelle Entlastung / Freigabe bei Blockade | offen |

| Sensor-/I/O-Datum | Linke Backe | Rechte Backe |
|---|---|---|
| Sensortyp / zulässiger Bereich | offen | offen |
| Montagefläche / Kraftübertragung | offen | offen |
| Widerstand ohne Last / unter definierten Referenzlasten | offen | offen |
| Spannungsteiler / ADC / Referenzspannung | offen | offen |
| Abtastrate / Filter / Verzögerung | offen | offen |
| Kontaktgrenze / Überlastgrenze mit Begründung | offen | offen |
| Hysterese / Kriechen / Temperatur / Wiederholbarkeit | offen | offen |
| Kabelbruch / Kurzschluss / Sättigung erkannt | offen | offen |

Ohne Kalibrierung keine Newtonwerte behaupten. Kontakt links/rechts,
Öffnung, Motorzustand und Haltestabilität gemeinsam auswerten.
Stoppen des Motors baut bei einer selbsthemmenden Spindel Kraft nicht
automatisch ab. Endlagen und Sensoren müssen lokal rechtzeitig wirken.

## 11. Spätere Kamera-Arm-Kalibrierung und Greifversuche

Verfahren und Stufen K1–K7: [Kalibrierkonzept](ARM_KALIBRIERKONZEPT.md).

| Kalibrierdatum | Eintrag |
|---|---|
| Gemini 305 (Nutzer, 12.11.2026): Seriennummer, Firmware, Seite und Neigung am Handgelenkglied | offen |
| Gemini 305: Preset, Auflösung, Bildrate, Disparitätsbereich, USB-3-Verbindung bestätigt | offen |
| Kabelweg Gemini bis Jetson: Länge, Kabeltyp, Schleifen an J5 und J4 | offen |
| Abstand Gemini zum Deck in der Parkpose und am J1-Anschlag, gemessen | offen; CAD bei J5 +20°: 34 mm, am Anschlag 2° weiter 16 mm |
| Fangbereich des Greifers: seitlich, axial, Winkel (K3) | offen |
| Vorposition: Abstand zum Objekt, Bildwinkel, zulässiger Grobfehler (Sichtfeldbedingung) | offen |
| Prüfung der Werkskalibrierung Gemini: Reprojektion, Tiefe gegen Maß, Deckung Tiefe/Farbe (K4) | offen |
| Ergebnis Handgelenkglied → Gemini, Residuen, Konsistenz der Boardlage (K5) | offen |
| Lichtschranke im Greifer: Lage, Schaltpunkt (K3) | offen |
| Prüfmarke für die Schnellprüfung: Ort und Sollwert | offen |
| Reales Armmodell / TCP-Version / gemeinsame Montage | offen |
| Kamera-ID / Optik / Auflösung / passende camera_info | offen |
| Framekette base_link → … → oak_rgb_camera_optical_frame und base_link → … → Handgelenkglied → Gemini | offen |
| Boardtyp / real vermessene Abmessungen / Befestigung | offen |
| Gelenk- und Bildzeitstempel / Stillstandsprüfung | offen |
| Anzahl und räumliche Verteilung der Messposen | offen |
| Solverprüfung mit synthetisch bekannter Transformation | offen |
| Kalibrierergebnis / Residuen / Ausreißerbehandlung | offen |
| Unabhängige Prüfpunkte, nicht zum Fit verwendet | offen |
| Fehlerbudget und akzeptable Greifabweichung | offen |
| TF-Verantwortlicher; keine konkurrierenden Publisher | offen |
| Sichtlücken der OAK im Greifraum | berechnet 12.11.2026 (ARM_KONTEXT); praktische Prüfung offen |

Zuerst bekannte Zielpositionen bei stillstehender Basis; erst danach
kamerageführte Griffe. Referenzobjekt, Größe, Füllung, Oberfläche und
zulässige Verformung dann gemeinsam festlegen.

## 12. Abschluss jedes Versuchs

| Abschluss | Eintrag |
|---|---|
| Erwartetes Ergebnis / vorher festgelegtes Abnahmekriterium | offen |
| Tatsächliche Beobachtung mit Messwert und Unsicherheit | offen |
| Abbruch ausgelöst? Zeitpunkt und Grund | offen |
| Endzustand von Arm, Last, Versorgung und Software | offen |
| Ergebnis: bestanden / nicht bestanden / nicht durchgeführt | nicht durchgeführt |
| Erklärung durch Messung belegt oder nur Hypothese? | offen |
| Genau eine nächste Änderung / nächster Versuch | offen |
| Rückfallstand / Bedingungen für erneute Freigabe | offen |

Die Gelenkzuordnung, der eigene RS485-Adapter und die Not-Aus-Wirkung sind
seit dem 08.11.2026 als Nutzerangabe bekannt. Zuerst benötigt werden jetzt:
**(1)** Antrieb und Spindel der Hubachse sowie Antrieb von J6,
**(2)** Typenschilder, Busadressen und Haltekonzept bei stromlosem Not-Aus,
**(3)** Gewichte von Arm, Greifer und Basis,
**(4)** TLE-Montage und geplante Eingangsbeschaltung.
