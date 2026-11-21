# Wohnungserkundung – aktueller Status

**GEPARKT seit 19.11.2026 (spät), Entscheidung des Projektinhabers:** Die
Hauptlinie `self_healing` hat keinen Auftrag und wird nicht weiterentwickelt;
gearbeitet wird an der KI-Erkundung (`ki_erkundung/`, MASTERPLAN §10). Der
Auftrag SH-9N (nur lesend) wurde zurückgezogen und nicht ausgeführt
([Archiv](archive/20261119-sh9n-zurueckgezogen/README.md)). Der Rückschritt
gegenüber dem 08.11. ist nicht eingegrenzt. Alles Folgende beschreibt den
Stand beim Parken.

**Stand beim Parken, 19.11.2026 (abends):** Hauptlinie `self_healing`
(Nutzerentscheidung 15.10.2026), Fahrplan in MASTERPLAN §9. **SH-9 (19.11.)
ist nicht bestanden:** eine Fahrt von 13,4 Minuten, 16 Anläufe, **kein Ziel
erreicht**, Labortür nicht durchfahren, Ende mit „Hilfe benötigt“. Der Raum
war nach 60 s zu 85 % erfasst; danach drehte Amadeus fast nur auf der Stelle
(75 % der Befehlszeit, zusammen rund 15 volle Umdrehungen bei 8,7 m Weg).
**Einwand des Projektinhabers (19.11.):** keinerlei Verbesserung; am 08.11.
fuhr Amadeus zweimal durch dieselbe Tür. Das trifft zu: Am 08.11. (SH-7)
erreichte er 5, 12 und 7 Ziele. Seitdem kamen fünf Änderungen auf den
Roboter (AW-1, KM-1 B, KM-2, Antrieb 100 ms, EK-1); welche den Rückschritt
bringt, ist nicht gemessen. Vorgesehen war SH-9N, nur lesend (die
gespeicherten Fahrten vom 08.11., 15.11. und 19.11. mit denselben Werkzeugen
nebeneinander); zurückgezogen mit dem Parken. **Wird die Linie wieder
aufgenommen, kommt zuerst diese Eingrenzung, vor jeder weiteren
Verhaltensänderung.**
**Seit 19.11.2026** gibt es daneben die getrennte Entwicklungslinie
„KI-Erkundung“ (MASTERPLAN §10, Stand nur in
[ki_erkundung/STATUS.md](../../ki_erkundung/STATUS.md)); an dieser
Hauptlinie und an SH-9 ändert sie nichts.
**21.11.2026 – Anschlussstelle „nur Rundblick“ (Freigabe des
Projektinhabers):** Der Erkunder hat ein neues Startargument
`initial_scan_only` (Vorgabe `false`). Mit `true` besteht ein Erkundungsauftrag
nur aus dem vorhandenen abschnittsweisen Rundblick (einmal 360° auf der
Stelle) und endet danach, ohne ein Ziel anzufahren; das gilt vor jeder
Erkundungsstrategie. Zweck ist die Blickrunde der KI-Linie (KI-1). Ohne das
Argument ist das Verhalten unverändert: Am Standardweg, am
Selbstheilungsweg und an den Profilen wurde keine Zeile geändert. Die
Hauptlinie bleibt geparkt; das ist kein Auftrag der Hauptlinie. Geprüft in
der Entwicklungsumgebung: 2285 Tests des Erkunders, 267 in der gezielten
Liste (249 wie am 19.11. und 18 neue), ein Lauf des ganzen Stacks in der
Simulation (361,7° in 77 s, kein Nav2-Ziel, Mission erfolgreich). Am Roboter
gelaufen am 21.11.2026 im Auftrag KI-1 der KI-Linie (Release
`ki1-20261121_2043`): 363,2° in 81,3 s, acht Abschnitte, kein Nav2-Ziel,
Endpunkt 8 mm neben dem Start, nichts berührt. Dabei beobachtet: Das
Prüfskript ohne `--aktiv` meldet „Encoder-Shadow sichtbar“, auch wenn die
Motorregler nicht antworten (Motoren gesperrt); im Stand unschädlich, nicht
geändert. Rückfall: das Argument weglassen; im Code den Commit
zurücknehmen.
**21.11.2026 (nachts) – zweite Anschlussstelle „Etappenfahrt“ (Freigabe des
Projektinhabers):** Der Erkunder hat ein zweites Startargument
`stage_drive_only` (Vorgabe `false`). Mit `true` wartet ein Erkundungsauftrag
stehend auf genau ein Fahrziel der KI-Linie (ein bis drei Punkte in der
Karte, Thema `/ki_erkundung/fahrziel_json`) und fährt es **ohne Nav2** an:
auf der Stelle ausrichten, gerade, vom Laser gemessene Etappen von höchstens
0,5 m bei 0,05 m/s, vor jeder Etappe die Prüfung des Streifens in
Fahrzeugbreite. Das gilt vor jeder Erkundungsstrategie; zusammen mit
`initial_scan_only` kommt zuerst der Rundblick. Ohne gültiges Ziel bewegt
sich nichts. Verwendet werden die am 10./11.09.2026 real bestandenen
Bausteine (`_rotate_in_place`, `_drive_forward_lidar`,
`front_lidar_corridor_check`); am Erkunder kamen nur Zeilen hinzu (506, keine
geändert), dazu das neue Modul `stage_drive.py`. Dazu gehört ein eigener
Nahbereichs-Halt an der globalen Kostenkarte (mit den Treffern der VL53),
weil der Kollisionsmonitor bei 0,05 m/s erst wenige Zentimeter vor einem
Hindernis bremst (Befund der Simulation). Standardweg,
Selbstheilungsweg, Profile, Fahrtor und Kollisionsmonitor sind nicht
geändert; die Hauptlinie bleibt geparkt. Am Roboter nicht gelaufen.
Rückfall: das Argument weglassen; im Code den Commit zurücknehmen. Nachweise
und Simulationsläufe stehen in
[ki_erkundung/STATUS.md](../../ki_erkundung/STATUS.md).
Wo wir stehen, zeigt die **Arbeitsliste direkt unter diesem Absatz**.
AP06 ist eingefroren; die folgenden zwei Absätze beschreiben seinen letzten
Stand.

**AP06, letzter vollständig geprüfter gemeinsamer Stand: v17 / `60e894c`,
11.10.2026.** Separater ARM64-Build: 14 Pakete, 155 eindeutige bytegleiche
Quelle/Install-Dateien bei 157 Vergleichseinträgen. **2.976 Regressionen
bestanden; ursprüngliche ganze A/B/C-Missionen weiterhin 0/3.** Originale
Cancel-/HOLD-Stoppfälle 2/2; im HOLD-Fall nach Halt vier Ankünfte/drei
Beobachtungen, danach terminaler Kartenstatus-Joinfehler. Vollständige
Wiederaufnahme und reale Gesamtfahrt bleiben offen. Bestandsinstall und Main
unverändert. [Kritischer Buildreview](AP06_BUILD_REVIEW_20261011.md) und
[exakter v17-Beleg](evidence/ap06-correction-v17-20261011.json).

**AP06-Ursachenprüfung (eingefroren, nicht aktuell):** A erste verworfene Rasterzelle samt Rastertyp und
Referenz; B/C tatsächlich späte Auswahl- und Callback-Arbeit; Joinfehler nach
HOLD-Fortsetzung getrennt zuordnen. Keine geänderten Grenzwerte oder neuen
gleichen Fehlversuche. Die nachstehenden Absätze bewahren die einzelnen
Korrekturen und früheren Vergleichsstände.

## Arbeitsliste (roter Faden nach MASTERPLAN §9) – Stand 19.11.2026

Genau eine Liste. Jeder Auftrag bezieht sich auf eine Zeile. Neue Ideen
kommen unter „Geparkt“, nicht sofort in den Code.

**Das eine aktive Problem (Stand 19.11.): Mit dem heutigen Stand erreicht
Amadeus seine Ziele nicht mehr; der Stand vom 08.11. konnte es.** SH-9: 0 von
16 Anläufen erreicht, 74,5 s Vorwärtsfahrt in 13,4 Minuten, 502,7 s Drehen
(Drehrate im Median 0,058 rad/s), 616× „collision ahead“, 18× Reglerhalt, am
Ende 38× kein Plan, obwohl Amadeus frei stand. Die Suche ist nicht das
Problem (Raum nach 60 s zu 85 % erfasst), das Fahren ist es. Zuerst wird der
Rückschritt eingegrenzt (SH-9N, dann eine Vergleichsfahrt mit dem
unveränderten Release vom 08.11., wenn der Projektinhaber zustimmt). Die
folgenden Absätze beschreiben den Stand bis W-1.

**Bis W-1 (15.11.): Amadeus verlässt den Raum
nicht.** Gemessen (W-1N, 16.11.): Der Raum ist nach 2–3 Minuten zu 85 %
erfasst. In Fahrt 1 scheiterten danach alle 10 Ziele hinter der 78-cm-Tür;
Amadeus stand am Ende neben dem 22 cm breiten Streifen, den der Planer in
der Tür zulässt. In Fahrt 2 kam er der Tür nie näher als 0,87 m: 12 von 14
Abbrüchen kamen von veralteter Lokalisierung (SLAM-Rückstand über 1,5 s),
danach begann 13-mal derselbe Anlauf neu; 71 % der Fahrzeit waren
Drehbefehle. **Am 08.11. (SH-7) fuhr Amadeus in 2 von 3 Fahrten durch
dieselbe Tür.** Seitdem kamen AW-1, KM-1 B, KM-2 und der schnelle Antrieb
ohne eine ganze Fahrt dazwischen; welche Änderung die Tür verschlechtert
hat, ist nicht gemessen. Der Suchmechanismus EK-1 war in W-1 aus.

**Das frühere aktive Problem „sitzt dicht an Hindernissen fest“:**
Stellprobe in W-1 bestanden (Mülleimer zweimal, Ecke einmal, mit KM-1 B,
KM-2 und 100 ms Anfahrzeit). Die Sperre, für die KM-2 gebaut wurde, trat
dabei nicht auf (kein „approach“ in fünf Läufen); belegt ist, dass die
Kontur unter Humble anliegt und bei jeder Rückfahrt umschaltet.

**Aktiv (Roboter):** nichts; die Linie ist geparkt. **Zurückgezogen:
SH-9N**
([Archiv](archive/20261119-sh9n-zurueckgezogen/README.md)), nur lesend,
kein Stackstart. Er hätte die sechs gespeicherten
Fahrten (SH-7 dreimal, W-1 zweimal, SH-9 einmal) mit denselben heutigen
Werkzeugen ausgewertet und die Einstellungen der drei Releases
nebeneinander gelegt. **Zuletzt gefahren: SH-9 (nicht bestanden,
[Archiv](archive/20261119-sh9-ausgewertet/README.md)):** EK-1
eingeschaltet (A Teilschwenk 90°, B nur Lücken ab 0,5 m mit 5 cm Rand und
8 cm Wandabstand, D Abbruch nach 45 s ohne Weggewinn; `bab7cc7`, 249
gezielte Tests). Fahrbereich Laborraum, Flur und Schlafzimmer (Freigabe des
Projektinhabers vom 16.11.2026 für diesen Auftrag), begleitet, höchstens
zwei Fahrten von je höchstens 20 Minuten. Mitlesend: Nahbild der lokalen
Karte, Auswertung gleich am Jetson. Kriterien E1–E6 und K im Auftrag.
**Entscheidungen des Projektinhabers (15./16.11.2026):** Der Antrieb wird
für die autonome Fahrt ausgelegt; 100 ms Anfahrzeit ist Standard. Ein Raum
darf bei 80–85 % als erfasst gelten; kommt kein Fortschritt mehr, sucht
Amadeus dort nicht weiter und geht zum nächsten Raum.

**Simulation, Einschränkung (19.11.):** Die Simulation hat das Verhalten
aus SH-9 nicht gezeigt; mit EK-1 verließen dort alle fünf Läufe den Raum.
Für die Frage „fährt Amadeus real seine Ziele an“ ist sie derzeit nicht
aussagekräftig. Bis das geklärt ist, wird aus ihr kein Wert mehr auf den
Roboter übernommen.

**In Simulation: die Tür.** Seit dem 16.11. stellt die Simulation den
Fehler aus W-1 Fahrt 1 nach (eine von elf Türdurchfahrten mit EK-1: im Flur vor
der Wand angehalten, zweimal gerade zurückgesetzt, Heck am Türpfosten, dann
sieben Planerfehler und „Hilfe benötigt“). Daran wird die Korrektur der
Türdurchfahrt entwickelt; auf den Roboter kommt sie erst nach SH-9.

**Daneben, nicht Teil dieser Liste (seit 19.11.2026):** die getrennte Linie
„KI-Erkundung“ im Ordner `ki_erkundung/` (Entscheidung des Projektinhabers,
MASTERPLAN §10). Sie ändert weder SH-9 noch das Produktprofil noch ein Paket
dieser Linie; am Roboter läuft weiter nur der Auftrag dieser Liste. Ihr
Stand steht ausschließlich in
[ki_erkundung/STATUS.md](../../ki_erkundung/STATUS.md).

**Fahrplan danach (Stand 16.11.2026):** SH-9 (EK-1, zwei Räume) → Tür
(Planungsstreifen, Verkeilen; Daten aus SH-9) und SLAM-Rückstand bei
Drehungen → Wohnung erneut (Messfahrt) → Abnahme der Wohnung (Stufe 3, drei
Läufe) → Schritt 5 Raumziele (Karte speichern, Räume in der App,
`go_to_room`). **Regel aus dem 16.11.:** Nach jeder Änderung am Fahr- oder
Kartenverhalten folgt vor der nächsten Änderung eine ganze Zwei-Raum-Fahrt
durch die Tür; Stellproben allein genügen dafür nicht.

**Geparkt (mit Grund):**

| Punkt | Grund für Parken | Wieder aufnehmen, wenn |
|---|---|---|
| KM-1 B (lokale Karte löscht nichts unter der Kontur) | SH-8c: an der Ecke bestätigt (zweimal `befreit`); an den Mülleimern verhindert es das Heranfahren nicht (Teile des runden Eimers standen noch nicht in der Karte). Neu beobachtet: Hängt etwas auf LiDAR-Höhe über die Kontur (Jacken bei 3 cm), bleibt es als Hindernis im Gehäuse stehen (Bereich F fängt es ab) | bleibt im Code; Entscheidung „bestätigt“ erst mit einer bestandenen Stellprobe an allen drei Stellen |
| Tür: Der Planer rechnet mit 0,28 m Radius, in der 78-cm-Tür bleiben ihm 22 cm; wer daneben steht, bekommt keinen Weg (SH-7 Fahrt 3 am 08.11. und W-1 Fahrt 1). Dazu Verkeilen in der Tür und Rückfahrt mit dem Heck an den Pfosten (Simulation 14.11.) | eine Änderung je Realtest; zuerst EK-1 (SH-9) | SH-9 ausgewertet; die Aufzeichnung dort zeigt, was an der Tür geschieht |
| Rückschritt an der Tür eingrenzen: AW-1, KM-1 B, KM-2 und Antrieb 100 ms kamen seit SH-7 ohne ganze Fahrt dazwischen. KM-1 B lässt sich zur Laufzeit abschalten (`footprint_clearing_enabled`, in Humble umschaltbar) | erst sehen, ob die Tür mit EK-1 gelingt | die Tür in SH-9 nicht gelingt |
| SLAM-Rückstand bei vielen Drehungen (W-1 Fahrt 2: Last 7 → 64 %, `map→odom` bis 1,7 s alt; jede Drehung über 0,35 rad legt einen Knoten an, auch auf der Stelle) | mit EK-1 sind die Fahrten kürzer und drehen weniger; in der Wohnung kommt es wieder | SH-9 ausgewertet, spätestens vor der nächsten Wohnungsfahrt |
| Abbruch bei veralteter Lokalisierung zählt nicht als Fehlversuch; danach wird dasselbe Ziel neu angefahren (W-1 Fahrt 2: 13 von 14) | Ursache ist der SLAM-Rückstand (Zeile darüber) | zusammen mit dem SLAM-Rückstand |
| Drehen in der Langsam-Zone nur mit 0,043 rad/s (2,5°/s) statt 0,075 rad/s. Ursache gerechnet und zur Messung passend: RPP begrenzt beim Drehen auf der Stelle seinen Befehl auf „gemessene Drehrate + `max_angular_accel` × 0,05 s“ (2,0 rad/s² → + 0,1 rad/s); der Kollisionsmonitor nimmt davon 30 %. Der Kreis schwingt sich bei w = 0,3 × (w + 0,1) = 0,043 rad/s ein (gemessen 0,043–0,044; nach Verlassen der Zone 0,143, dann 0,25). Mit `max_angular_accel` ab 3,5 rad/s² wären es die gedachten 0,075 rad/s; die Drehbeschleunigung begrenzt ohnehin der Glätter (0,30 rad/s²) | eine Änderung je Realtest; ändert das Verhalten dicht an Hindernissen | SH-9 ausgewertet und die Zeitanteile weiter vom Drehen bestimmt sind |
| In der globalen Kostenkarte lagen in W-1 Fahrt 1 tödliche Zellen unter dem Roboter (89 in der Kontur), die in der SLAM-Karte fehlen; Herkunft offen (das Löschen unter der Kontur ist dort eingeschaltet) | nur am laufenden Stack zu messen | SH-9: die Aufzeichnung vergleicht Karte und Kostenkarte am Roboter |
| Fahrtor und Explorer schreiben den Grund einer Sperre oder eines Abbruchs nicht mit (W-1 Fahrt 1: Rückfahrt 40 ms nach einer Fahrtorsperre abgebrochen, Grund unbekannt) | Änderung am Fahrtor ist sicherheitsrelevant und wird getrennt gebaut | mit dem nächsten Build, der ohnehin das Fahrtor berührt, oder wenn der Grund erneut fehlt |
| `planner_server` schreibt für Ziele am Kartenrand je Anlauf tausende Zeilen „worldToMap failed“ (20040 in 30 s) | stört nur das Log | die Logs zu groß werden |
| Lücken neben Möbeln (kurze Frontiers von 0,3–0,4 m an tiefem Unbekanntem, zum Beispiel die Nische zwischen Regal und Wand) werden vor der Tür angefahren, weil sie näher liegen; in der Simulation führte das zu Berührungen niedriger Dinge | braucht eine Zielwahl nach Nutzen (EK-2) | SH-9 zeigt, dass solche Lücken real Zeit kosten oder Amadeus in enge Lagen bringen |
| Rückfahrt in der Langsam-Zone dauert 21 s für 0,3 m (0,015 m/s). Die „zu kurze Rückfahrt“ aus SH-8/SH-8b war der Antrieb und ist seit SH-8c behoben (0,307 / 0,308 m) | reicht zum Befreien; ein Problem zur Zeit | die Rückfahrten in vollen Fahrten spürbar Zeit kosten |
| Niedrige Gegenstände seitlich (unter 0,75 m, nie von den VL53 gesehen): Simulation 13.11. berührte nach dem Befreien in 4 von 4 KM-1-B-Läufen eine Eimerseite, am 15.11. mit KM-2 in 4 von 4 (1 bis 4 min nach dem Befreien, beim Drehen). **Real am 15.11. (SH-8c s3a): linke vordere Ecke 0–2 cm vor einem Eimer, keine Berührung** | bekannte Sensorgrenze, nicht Teil des aktiven Problems; real bisher keine Berührung, aber mit echtem Tempo zum ersten Mal knapp. **Nächster Kandidat für das „eine aktive Problem“, sobald das Festsitzen gelöst ist** | vor Stufe 3 (Wohnung) oder bei der ersten realen Berührung; Stellproben enden deshalb sofort nach 0,5 m, volle Fahrten ohne Eimer |
| Anstiegsbegrenzung im Motortreiber (jeder Sprung nach oben wird im Treiber zu einer Rampe von 0,12 m/s²; Bremsen und Stopp bleiben sofort) | Codeänderung an der Motorsteuerung; erst nötig, wenn das Rucken bei Sprüngen stört (Verlassen der Langsam-Zone: 0,7 m/s² für 0,1 s) | Christopher das Ruckeln im Betrieb als störend meldet, die Messgröße `wackeln` deutliche Spitzen zeigt oder die Karte dadurch leidet |
| Wackeln auf Fliesenfugen bei echtem Tempo (Frage des Projektinhabers 15.11.2026): Der HWT601 liefert im aktiven Stack **nur die Gierrate** für die Odometrie. Nicken und Rollen wertet niemand aus; es gibt weder eine Tempobegrenzung bei Wackeln noch ein Verwerfen gestörter Scans. Die Logik dafür liegt geprüft, aber unbenutzt in `robot_state_estimation/quality_core.py` (`ImuStabilityConfig`: 14°/s, 3° Lageänderung); ein Knoten und ein Start dafür fehlen | bisher nur auf glattem Boden gefahren; mit echtem Tempo auf Fliesen noch nie gemessen; ein Problem zur Zeit | vor Stufe 3 (Wohnung, Küchenfliesen): zuerst eine kurze Messfahrt über Fugen mit der neuen Messgröße `wackeln` (Tempo 0,135 und 0,08 m/s im Vergleich, Karte ansehen); erst danach entscheiden zwischen „langsamer bei Wackeln“ (über das vorhandene `/speed_limit`) und „gestörte Scans verwerfen“ |
| Anfahrzeit 100 ms für `self_healing:=true` im Launch verankern (bisher Argument im Startbefehl) | braucht einen Build; erst nach Bestätigung im Betrieb | SH-8c bestanden, mit dem nächsten Build |
| Handsteuerung (`teleop_joy`) sendet ebenfalls auf `/cmd_vel_smoothed`; neben dem laufenden Nav2-Stack bekäme auch sie die Nullbefehle des Glätters dazwischen | bisher nur aus AT-1 abgeleitet; die Handsteuerung wird mit `slam.launch.py` ohne Nav2 benutzt | jemand will neben dem laufenden Erkundungsstack von Hand fahren |
| Fremde Änderungen in `~/roboter_ws` (15.11.: `docs/INVENTORY.md`, `tools/kartierung/README.md` geändert, drei `lidar_acryl_test`-Dateien neu) | nicht von dieser Linie; der Jetson-Agent hat sie nicht angefasst | vor dem nächsten Auftrag, der `~/roboter_ws` benutzt, oder wenn Christopher sie einordnet |
| LiDAR meldet beim Start „communication is abnormal“ (SH-8: dreimal, nach Neustecken behoben) | Vorprüfung fängt es ab, keine Bewegung | tritt erneut auf (dann Kabel/USB prüfen) |
| E Lückensuche auf gröberem Raster (5 cm) | Nutzen unbelegt; gröberes SLAM-Raster (X12) brachte Wege näher an Türpfosten | reale Abdeckungskurven zeigen, dass kleine Lücken in der Ferne Zeit kosten |
| F mehr Tempo vor Unbekanntem (bisher 0,08 m/s) | Sicherheitsfrage, eigene Prüfung nötig | nach dem Erkundungspaket, falls die Fahrzeit noch zu lang ist |
| Geschlossene Holztür im Flur vom LiDAR nicht eingetragen | erzeugt eine falsche Lücke; Ursache offen | vor Stufe 3 (Prüfung im Stand vor der Tür) |
| Mission-Manager meldet am Ende `failed` bei Teilkarte | betrifft nur die Anzeige (App, WE-M7) | vor Schritt 5 |
| VL53-Aussetzer bis etwa 12 s | Ursache offen; der Explorer wartet und fährt weiter | werden sie häufiger oder länger |

**Erledigt (Selbstheilungslinie, Auszug):** SH-3 Abnahmestufe 1 (02.11.) ·
SL-1 SLAM-Last (04.11.) · SH-6 Regel „kein Fortschritt → zurück“, Prototyp 1
eingefroren (05.11.) · Budget 40 min, Tempo +35 %/+25 % (05.11.) · SH-7
Raumwechsel ausgewertet, nicht bestätigt (08.11.) · SH-7N Ursache gefunden
(08.11.) · AW-1 und AW-1b gebaut (09.11.) · Abdeckungskurve im
Fahrtprotokoll (09.11.) · Simulation KM-1 A/B und EK-1 ausgewertet (09.11.)
· Standortbestimmung, Stellprobe als Testform (10.11.) · SH-8 ausgewertet:
Ecke und Garderobe befreit, Mülleimer nicht (13.11.) · Anhang Z zweimal
ausgewertet: Befehle 6–10 cm/s, gefahren 1,3–1,7 cm/s (14.11.) · SH-8b
ausgewertet: nicht bestanden, Rückfahrten 0,151 m (14.11.) · AT-1
ausgewertet: Messung gestört, kein Urteil; Werkzeug erkennt fremde Sender
jetzt selbst (15.11.) · AT-1b ausgewertet: Antrieb folgt Sprüngen, feinen
Rampen nicht; Ursache ist die Anfahrzeit 2000 ms (15.11.) · AT-2
bestanden: mit 100 ms folgt der Antrieb den Nav2-Rampen (15.11.) · SH-8c
ausgewertet: Ecke zweimal befreit, Mülleimer vom Kollisionsmonitor
festgehalten (15.11.) · KM-2 gebaut und simuliert (15.11.) · W-1
ausgewertet: Stellprobe bestanden, Wohnungsfahrt bleibt im Laborraum (15.11.)
· W-1N ausgewertet: Tür in Fahrt 1, veraltete Lokalisierung in Fahrt 2
(16.11.) · EK-1 auf dem heutigen Stand simuliert, Lückenfilter korrigiert,
Türfehler in der Simulation nachgestellt (16.11.).

## 19.11.2026 (abends) – SH-9 ausgewertet: nicht bestanden, kein Ziel erreicht; Einwand des Projektinhabers: Rückschritt gegenüber dem 08.11.

Lokaler Agent, Release `selbstheilung-sh9-20261119_1932` (HEAD `c567c2d`,
Build 168 s, 14/14 Präfixe, 249 Tests). Drei Stackstarts: Der erste fiel in
der Vorprüfung durch (15 LiDAR-Punkte im Gehäuse; Christopher: „da lag was
von mir“, Neustart auf seine Anweisung, abweichend vom Auftrag), der zweite
an alten Encoderdaten (Regel „D Quellen“), der dritte bestand (67× OK). Eine
Fahrt, 801,5 s; die zweite lehnte Christopher ab („keinerlei Verbesserungen
zu der alten Software gesehen“). Aufbau laut Christopher: Labor- und
Schlafzimmertür offen, übrige zu; Durchfahrt 850 mm; Flur 1,3 m breit mit
Jacken- und Schuhregal.

**Ergebnis nach den vorab festgelegten Kriterien: nicht bestanden.** E1
(EK-1 aktiv) erfüllt; E3, E4, E5, E6 nicht; E2 und K nicht feststellbar
(Fragen dazu unbeantwortet; laut Protokoll kein Not-Aus, kein Fehlerende).

| | SH-7 (08.11.) | W-1 (15.11.) | SH-9 (19.11.) |
|---|---|---|---|
| Stand | Release `selbstheilung-sh7-20261108_1617` | dazu AW-1, KM-1 B, KM-2, Antrieb 100 ms | dazu EK-1 |
| Fahrten | 3 (25–32 min) | 2 | 1 (13,4 min) |
| Erreichte Ziele | 5 / 12 / 7 | Fahrt 2: 2 | **0 von 16 Anläufen** |
| Durch die Labortür | 2 von 3 | 0 von 2 | 0 von 1 |
| Anteil Drehen an den Fahrbefehlen | nicht ausgewertet | 71 % (Fahrt 2) | 75 % |

**Gemessen in SH-9:**
1. **Die Suche war nicht das Problem:** Raum nach 60 s zu 85 %, nach 211 s zu
   95 % erfasst; in den folgenden knapp 10 Minuten kamen 0,8 m² dazu.
2. **Amadeus fuhr kaum:** in den Anläufen 74,5 s vorwärts (befohlen 5,4 m),
   502,7 s Drehen, Drehrate im Median 0,058 rad/s (3,3°/s). Über die ganze
   Fahrt 96 rad Drehung (rund 15 Umdrehungen) bei 8,7 m Weg.
3. **Der Regler hielt an:** 616× „detected collision ahead“, 18× „Controller
   patience exceeded“; an diesen Stellen lag keine tödliche Zelle in der
   Kontur, die nächste meist 2–37 cm vorn links oder vorn rechts.
4. **EK-1 D griff viermal:** Die Anläufe 3 bis 5 endeten nach 45,1 / 58,8 /
   45,1 s; davon waren 42–52 s Drehen und 2–3 s Vorwärtsfahrt.
5. **Mehr Bewegung als befohlen:** Weg 1,44-fach, Drehung 1,32-fach
   (W-1 Fahrt 2: 1,19 und 1,36).
6. **Ende:** ab Minute 10,5 38× „failed to create plan“; die letzten sieben
   Anläufe scheiterten nach 6–23 s. Amadeus stand dabei frei (nächste
   belegte Zelle 1,08 m), etwa 1 m vom Startplatz.
7. Einmal stand er an einer 0,86 m breiten Stelle (3,6 s, bei 71 s); kurz
   danach vier Reglerhalte mit Hindernis 2–10 cm vor den vorderen Ecken und
   eine Rückfahrt von 0,31 m. Ob das die Labortür war, ist nicht belegt (die
   Durchfahrt ist laut Christopher 0,85 m breit).
8. SLAM-Last 4 % → 38 %; eine VL53-Lücke von 5,6 s; Wackeln klein
   (höchstens 0,026 rad/s).

**Vermutet, nicht gemessen:**
- EK-1 D bricht Anläufe ab, während Amadeus noch dreht: Bei 0,058 rad/s
  dauert eine halbe Drehung 54 s, die Schwelle liegt bei 45 s.
- Das langsame Drehen selbst (seit 16.11. bekannt und geparkt) und das
  Anhalten des Reglers nahe an Hindernissen (KM-1 B: seit 13.11. bleibt
  unter der Kontur nichts gelöscht).
- Der schnelle Antrieb (seit 15.11.) führt zu mehr Bewegung als befohlen.
Welche der fünf Änderungen seit dem 08.11. den Rückschritt bringt, lässt
sich aus SH-9 allein nicht sagen.

**Fehler der Cloud-Planung, festgehalten:**
1. Der Rückschritt war am 16.11. benannt („welche Änderung die Tür
   verschlechtert hat, ist nicht gemessen“) und wurde trotzdem geparkt. Mit
   EK-1 kam eine sechste Änderung auf einen Stand, der schon nicht mehr
   fuhr. Richtig wäre gewesen, zuerst den Stand vom 08.11. gegenzuprüfen.
2. Die Schwelle von EK-1 D (45 s) stammt aus der Simulation. Die reale
   Drehrate war seit dem 16.11. als sehr klein bekannt.
3. Die Simulation zeigte dieses Verhalten nicht (alle fünf Läufe mit EK-1
   verließen den Raum). Sie bildet das reale Drehen nicht ab; ihre Ergebnisse
   wurden trotzdem als Begründung für SH-9 verwendet.

**Entscheidung der Auswertung:** keine neue Verhaltensänderung. Nächster
Schritt ist **SH-9N** (nur lesend): die gespeicherten Fahrten vom 08.11.,
15.11. und 19.11. mit denselben Werkzeugen nebeneinander, dazu die
Einstellungen der drei Releases. Danach, wenn der Projektinhaber zustimmt:
eine Vergleichsfahrt mit dem unveränderten Release vom 08.11.; fährt er
heute wieder, werden die Änderungen einzeln zurückgeholt, jede mit einer
ganzen Fahrt durch die Tür (Arbeitsregel 8).

## 19.11.2026 – Entscheidung des Projektinhabers: zweite, getrennte Linie „KI-Erkundung“; SH-9 läuft unverändert

**Entscheidung (19.11.2026):** Der Projektinhaber testet SH-9 wie beauftragt
und berichtet. Parallel entsteht eine komplett neue Entwicklungslinie, in der
eine KI auf dem vorhandenen KI-Rechner die Ziel- und Suchwahl übernimmt. Sie
bekommt einen eigenen Ordner (`ki_erkundung/`), damit die bisherige
Entwicklung weder verloren geht noch beeinflusst wird.

**Für diese Hauptlinie ändert sich nichts:** Auftrag SH-9, Produktprofil
(49 Profilwerte mit EK-1), Pakete, Werkzeuge und die 249 gezielten Tests sind
unverändert. Der neue Ordner liegt außerhalb von `src/` und `tools/`; der
Build von SH-9 nennt seine Paketpfade einzeln, die Testliste ihre Dateien
einzeln. Kein Workflow unter `.github/workflows/` reagiert auf den neuen
Pfad.

**Wo es steht:** MASTERPLAN §10 (Trennregeln, Stufen KI-0 bis KI-4),
[ki_erkundung/KONZEPT.md](../../ki_erkundung/KONZEPT.md),
[ki_erkundung/STATUS.md](../../ki_erkundung/STATUS.md). Die Punkte dieser
Arbeitsliste (Tür, Rückstand der Ortung, blinde Rückseite) bleiben Arbeit
dieser Linie; die KI-Linie setzt darauf auf.

**Nächster Schritt dieser Linie bleibt:** Bericht zu SH-9 auswerten
(Kriterien E1–E6 und K).

## 16.11.2026 (abends) – EK-1 in der Simulation auf dem heutigen Stand: Lückenfilter korrigiert, Türfehler nachgestellt, SH-9 aktiviert

**Anlass:** Vor SH-9 musste EK-1 mit dem heutigen Stand geprüft werden
(KM-1 B, KM-2, Antrieb folgt den Befehlen); die Läufe vom 14.11. rechneten
mit dem trägen Antrieb. Welt wie am 14.11. (Laborraum 4,3 × 4,3 m möbliert,
0,80-m-Tür, Flur 1,5 × 4 m, LiDAR-Rauschen 1 cm), Antrieb jetzt mit 0,15 s
Zeitkonstante statt 1,3 s. Neu eine Welt mit **drei Räumen** (dazu ein
Zimmer hinter dem Flur mit zweiter 0,80-m-Tür, Schrank und niedrigem Tisch).

**1. EK-1 wie am 14.11. vorgeschlagen (strenger Lückenfilter):**

| Welt | Start | Ende | Dauer | Anläufe (erreicht / gescheitert / abgebrochen) | Flur betreten | drittes Zimmer | Abdeckung | Berührung |
|---|---|---|---|---|---|---|---|---|
| 2 Räume, ohne EK-1 | s1 | Teilkarte | 427 s | 12 (7 / 5 / 0) | 95 s | – | 0,978 | nein |
| 2 Räume | s1 | vollständig | 214 s | 3 (1 / 2 / 0) | **nie** (Flur zu 78 % erfasst) | – | 0,929 | nein |
| 2 Räume | s2 | vollständig | 198 s | 4 (1 / 2 / 1) | 195 s | – | 0,969 | nein |
| 2 Räume | s3 | vollständig | 277 s | 5 (3 / 1 / 1) | 270 s | – | 0,971 | nein |
| 2 Räume (Produktprofil) | s3 | vollständig | 192 s | 3 (2 / 1 / 0) | **nie** (Flur zu 53 % erfasst) | – | 0,860 | nein |
| 3 Räume | s1 | vollständig | 268 s | 4 (2 / 2 / 0) | 247 s | **nie** (zu 67 % erfasst) | 0,900 | nein |
| 3 Räume | s3 | vollständig | 204 s | 4 (3 / 1 / 0) | 50 s | **nie** (zu 84 % erfasst) | 0,934 | nein |

EK-1 halbiert Zeit und Anläufe. **Aber:** In einem Lauf meldete Amadeus
„vollständig“, obwohl der Flur erst zur Hälfte erfasst war.

**2. Ursache des vorzeitigen „vollständig“ (an den gespeicherten Endkarten
gemessen):** Teil B zählte eine Frontier nur, wenn die freie Zelle
unmittelbar an tiefes Unbekanntes grenzt. In der 1-cm-Karte liegt am Rand
eines Sichtschattens (Türpfosten) ein ausgefranster Streifen aus einzelnen
freien Strahlen und Unbekanntem dazwischen; die Frontier-Zellen lagen im
Median 5–9 cm vor dem tiefen Unbekannten. In der Karte mit dem halben Flur
hatten die beiden Türfrontiers 720 und 288 Zellen, davon nur 7 und 28
unmittelbar an tiefem Unbekanntem (Schwelle 30). Echte Karten sind rauer
als die der Simulation.

**3. Korrektur am Lückenfilter (`bd31447`, nachgeschärft `bab7cc7`):** Das
tiefe Unbekannte wächst um 5 cm (`self_healing_gap_reach_m`), aber nur durch
unbekannte Zellen, die weiter als 8 cm von jeder belegten Zelle entfernt
sind. Der Wandabstand kam nach dem ersten Lauf dazu: Ohne ihn zählten die
Lücken einer Regalfront als Öffnung, Amadeus fuhr darauf zu und endete nach
211 s mit „Hilfe benötigt“ (3,3 cm vom Regal). An acht gespeicherten
Endkarten: Die drei Karten mit vorzeitigem „vollständig“ behalten 1–2
Lücken, die Karten mit 78–93 % erfasstem Flur keine.

**4. EK-1 mit korrigiertem Filter (Stand von SH-9):**

| Welt | Start | Ende | Dauer | Anläufe (erreicht / gescheitert / abgebrochen) | Flur betreten | drittes Zimmer | Abdeckung | Berührung |
|---|---|---|---|---|---|---|---|---|
| 3 Räume | s1 | Teilkarte (Rest unerreichbar) | 448 s | 8 (3 / 4 / 1) | 340 s | betreten nach 392 s, 96 % | 0,972 | **ja**, 242 s: niedriger Hocker seitlich, beim Drehen |
| 2 Räume | s3 | **Hilfe benötigt** | 222 s | 12 (3 / 9 / 0) | 118 s | – | 0,968 | **ja**, 146 s: Heck am Türpfosten bei der zweiten Rückfahrt |
| 3 Räume | s3 | vollständig | 395 s | 8 (4 / 3 / 1) | 40 s | betreten nach 156 s, 95 % | 0,964 | **ja**, 373 s: niedrige Kiste seitlich, am Ende |
| 2 Räume | s1 | vollständig | 236 s | 5 (2 / 2 / 1) | 230 s | – | 0,975 | nein |
| 2 Räume | s2 | vollständig | 446 s | 6 (2 / 4 / 0) | 328 s | – | 0,976 | nein (2,2 cm) |
| 3 Räume, **ohne EK-1** | s1 | Teilkarte (Rest unerreichbar) | 623 s | 16 (14 / 2 / 0) | 100 s | betreten nach 132 s, 97 % | 0,976 | **ja**, 55 s: niedriger Mülleimer seitlich |

Die drei letzten Zeilen kamen nach der Aktivierung von SH-9 dazu und ändern
am Auftrag nichts. Welten für die Wiederholung:
`tools/simulation/experimente/manifest_labor_flur_rauschen_schnell.json`
und `manifest_drei_raeume_schnell.json`; Vergleich ohne EK-1 mit
`vorher_sh9_ohne_ek1.yaml`.

**Was das zeigt:**
1. **Mit dem korrigierten Filter verlässt Amadeus den Laborraum** (5 von 5
   Läufen; mit dem strengen Filter 3 von 5 in zwei Räumen) **und fährt in
   den dritten Raum** (2 von 2 Drei-Raum-Läufen, je 8 Anläufe, 6½–7½ min;
   ohne EK-1 16 Anläufe und 10½ min). Vier von fünf Läufen endeten von
   selbst.
2. **Die Simulation stellt den Türfehler aus W-1 nach** (Zwei-Raum-Lauf s3):
   durch die Tür in den Flur, dort vor der gegenüberliegenden Wand
   angehalten (nächste tödliche Zelle 3 cm vorn rechts), zweimal 0,3 m
   gerade zurück, Heck am Türpfosten, danach sieben Planerfehler und Hilfe.
   Die Rückfahrkontur ist 1 cm schmaler als das Gehäuse, und nach hinten
   sieht Amadeus nichts. In W-1 Fahrt 1 brach die zweite Rückfahrt nach
   0,139 m ab, der Pfosten lag an der hinteren rechten Ecke. Mit EK-1 bisher
   eine von elf Türdurchfahrten.
3. **Niedrige Dinge seitlich** (Hocker, Kiste) berührte er in 2 von 5 Läufen,
   jeweils an Lücken neben Möbeln; ohne EK-1 im Vergleichslauf ebenfalls
   (Mülleimer, nach 55 s). Das ist die geparkte Grenze; mit dem strengen
   Filter trat sie nicht auf, weil die Fahrten früher endeten. Real
   gab es in rund zehn ganzen Fahrten keine solche Berührung; in SH-9 sind
   bewegliche niedrige Dinge weggeräumt.
4. **D greift:** Ein Abbruch „kein Weggewinn“ nach 45 s; ein Anlauf lief
   trotzdem 150 s bis zur Zielzeit (er bewegte sich, ohne anzukommen).
5. Das Nahbild und die Zähler der Suche laufen in der Simulation mit dem
   echten Protokollwerkzeug (65 Bilder in 75 s; an der Tür engste Breite
   0,68–0,74 m).

**Grenzen:** Wenige Läufe (fünf mit dem Stand von SH-9), eine angenommene
Möblierung, SLAM und Zeitverhalten in der Simulation ohne die Rückstände
des Jetson. Die Simulation überschätzt Berührungen niedriger Dinge bisher
gegenüber der echten Fahrt.

**Entscheidung des Projektinhabers (16.11.2026, Fahrbereich):** Laborraum,
Flur und Schlafzimmer; Bad, Küche und Wohnzimmer zu. Der dritte Raum ist
nötig, damit Amadeus den Laborraum verlassen muss.

**SH-9 ist aktiv** ([Auftrag](AGENTENAUFTRAG.md)): EK-1 als die eine
Änderung, höchstens zwei Fahrten von je höchstens 20 Minuten, Kriterien
E1–E6 (EK-1 aktiv und Schwenk; an der Labortür in 5 min; im Flur in 10 min;
im Schlafzimmer; Ende von selbst nach dem Schlafzimmer; kein Ziel öfter als
dreimal) und K (keine Berührung, kein Eingriff). Erwartung: Die Tür kann
wie am 15.11. scheitern; dann liefern Nahbild und Kostenkarten das Bild
dazu, und die Tür ist die nächste Korrektur.

## 16.11.2026 – W-1N ausgewertet; Einwand des Projektinhabers: Rückschritt an der Tür, Suchmechanismus war aus

Bericht `~/selbstheilung_jetson_bericht_w1n.md` (Jetson, HEAD `fcef2cc`, nur
lesend aus `w1_runw1` und `w1_runw2`; 22 Werkzeugtests bestanden, alle
Aufrufe Exit 0; kein Stackstart, keine Fahrt).

**Die zwei Fahrten scheiterten aus zwei verschiedenen Gründen.**

| | Fahrt 1 (w1) | Fahrt 2 (w2) |
|---|---|---|
| Anläufe / verschiedene Ziele / wiederholt | 12 / 9 / 3 | 27 / 11 / 16 (ein Ziel 8×, eines 6×) |
| erreicht / gescheitert / abgebrochen | 1 / 11 / 0 | 2 / 11 / 14 |
| Anläufe mit Start näher als 1 m an der Tür | 10, alle gescheitert | 3, alle abgebrochen; kleinster Abstand 0,87 m |
| Anläufe mit Ziel hinter der Tür | 10, alle gescheitert | 0 |
| Abbruchgrund | – | 12× `localization_missing_or_stale`, 1× Zielzeit, 1× HWT-HOLD |
| Zeitfehler `odom→map` im Regler | 0 | 271, ab Minute 10 je 24–51 pro Minute |
| Anteil Drehbefehle / Vorwärtsbefehle in den Anläufen | 36 % / 21 % (39 % ohne Befehl) | 71 % / 14 % |
| Anteil Langsam-Zone | 3 % | 42 % |
| Wartezeit des Explorers | 0 s | 8 s |

**Fahrt 1, die Tür (gemessen):**
1. Amadeus war nach etwa 140 s in der Tür (Anlauf 4 endete 0,14 m vor der
   späteren Hilfe-Stelle). Ab 157 s stand er; sieben weitere Anläufe
   scheiterten nach je 6,5–6,8 s im Planer.
2. Die Tür ist in der Karte 0,78 m breit (kleinster Abstand der beiden
   großen Wandgruppen, vom Jetson-Agenten nachgemessen). Rechnerisch bleibt
   dem Planer mit 0,28 m Radius ein Streifen von 0,22 m.
3. Die Robotermitte lag 0,25 m von der einen und 0,55 m von der anderen
   Türseite, also etwa 0,14 m neben der Türmitte und außerhalb des
   Streifens. In der SLAM-Karte liegt die nächste belegte Zelle an der
   hinteren rechten Ecke (11 Zellen in der gepolsterten Kontur, 1 in der
   Kontur ohne Polster).
4. In der **globalen Kostenkarte** lagen zusätzlich 89 tödliche Zellen in
   der Kontur (117 mit Polster), die nächste 6 cm von der Mitte; die nächste
   für den Planer freie Zelle war 0,38 m entfernt. In der SLAM-Karte fehlen
   diese Zellen. Herkunft offen (die globale Hindernisebene löscht laut
   Einstellung unter der Kontur).
5. Die zweite Rückfahrt wurde vom Explorer abgebrochen, 40 ms nachdem das
   Fahrtor auf „blocked“ ging. Kein Warten und kein HWT-HOLD zu dieser Zeit,
   keine Logzeile des Explorers. Der Grund steht nirgends.
6. Karte und globale Kostenkarte laufen mit 1 cm Auflösung.

**Fahrt 2, veraltete Lokalisierung und Neuanläufe (gemessen):**
1. Bei 12 der 14 Abbrüche steht 0,04–0,29 s vorher „harte Quellenstörung
   (localization_missing_or_stale); Nav2-Abbruch“. `map→base_link` war dabei
   1,0–1,7 s alt; der Explorer bricht ab 1,5 s ab, das Fahrtor sperrt ab
   0,8 s.
2. Nach 13 der 14 Abbrüche begann der nächste Anlauf 0,2–2,2 s später auf
   **dasselbe** Ziel. Diese Abbrüche stehen nicht in der Heilungsliste.
3. Der Rückstand ist `map→odom` von `slam_toolbox`: bis Minute 9 meist unter
   0,05 s, ab Minute 10 bis 1,3 s (Median 0,68 s). Rechenlast 7 → 64 %.
4. Die ersten acht Minuten gingen ohne Zeitfehler verloren: Anläufe 3–7 zu
   Zielen im Raum (2,7–3,5 m von der Tür) endeten mit Zielzeit oder
   „collision ahead“; ein Anlauf über 1,39 m bestand zu 119 von 150 s aus
   Drehbefehlen.
5. Gedreht wurde in den Anläufen im Median mit 0,044 rad/s (2,5°/s).

**Aus dem Code dazu (gelesen, nicht neu gemessen):**
- `slam_toolbox` stempelt `map→odom` mit der Zeit des zuletzt angenommenen
  Scans plus 0,2 s. Blockiert die Scanverarbeitung länger, altert die
  Transformation. Ein Knoten entsteht nach 0,25 m Weg oder 0,35 rad Drehung,
  auch bei Drehung auf der Stelle; in Fahrt 2 wurden 126 rad gedreht.
- RPP prüft zuerst die aktuelle Pose (`isCollisionImminent`): Liegt eine
  tödliche Zelle auf der gepolsterten Kontur, gibt er keinen Befehl aus,
  auch keine Drehung. Seit KM-1 B (14.11.) löscht die lokale Karte dort
  nichts mehr.
- 0,044 rad/s beim Drehen in der Langsam-Zone: Die erste Lesart (Tempogrenze
  vor Unbekanntem) war falsch. RPP begrenzt beim Drehen auf der Stelle
  seinen Befehl auf „gemessene Drehrate + 0,1 rad/s“ (`max_angular_accel`
  2,0 rad/s² × 0,05 s), der Kollisionsmonitor nimmt davon 30 %; das ergibt
  als Ruhewert w = 0,3 × (w + 0,1) = 0,043 rad/s. Dazu passt der Auszug bei
  584–587 s: −0,043, −0,044, nach „continue normal operation“ −0,143, dann
  −0,250.

**Korrekturen an früheren Aussagen (auch im Abschnitt 15.11. spät):**
1. **„Schräg (43°) in der Tür“ war nicht gemessen.** 43,3° ist die
   Blickrichtung in der Karte, deren Achsen vom Startplatz abhängen. Das
   Werkzeug `karte_engstelle.py` hat in der 1-cm-Karte die Lücke zwischen
   einer Wand und einzelnen belegten Zellen vermessen (0,20 m, „44°“); diese
   Zahlen sind keine Türmaße. Der Schrägstand ist offen.
2. **„In der lokalen Karte lagen tödliche Zellen im Gehäuse hinten rechts“
   ist nicht belegt.** Die gesicherte lokale Kostenkarte von w1 stammt von
   28 s vor dem Missionsstart (`ros2 topic echo --once` bekam die
   zwischengespeicherte Nachricht der Vorprüfung). Für die Stelle hinten
   rechts sprechen weiter die SLAM-Karte und die globale Kostenkarte.
3. **Fahrt 2 war kein Türproblem.** Amadeus kam dort nie an die Tür.
4. **„Die Türdurchfahrt ist real nie bestätigt worden“ (PROJECT_MEMORY,
   15.11.) war falsch.** In SH-7 (08.11.) fuhr Amadeus in 2 von 3 Fahrten
   durch die 80-cm-Tür, einmal auch zurück; in der dritten war die Tür in
   der Karte für den Planer zu schmal (SH-7N Punkt 4).

**Einwand des Projektinhabers (16.11.2026, sinngemäß wörtlich):** „Wir gehen
gerade in die falsche Richtung. Der Roboter hat in vergangenen Tests den
Flur erreicht und schafft das jetzt nicht mehr; das ist ein Rückschritt.
Warum fährt er kreuz und quer? Wir hatten einen Suchmechanismus vereinbart,
der den Raum kontrolliert abscannt, zu kleine Lücken auslässt und zügig den
Raum verlässt. 80 oder 85 % sind in Ordnung; entsteht kein Fortschritt mehr,
darf er nicht immer weiter suchen.“

**Was daran belegt ist:**
1. **Rückschritt:** 08.11. zwei von drei Fahrten durch die Tür, 15.11. keine
   von zwei. Erreichte Ziele in 20 min: SH-6 8–10, W-1 Fahrt 2 zwei, obwohl
   der Antrieb seit dem 15.11. etwa fünfmal schneller fährt.
2. **Vier Änderungen ohne ganze Fahrt dazwischen:** AW-1 und AW-1b (09.11.),
   KM-1 B (SH-8b, 14.11.), KM-2 (15.11.), Anfahrzeit 100 ms (15.11.). SH-8,
   SH-8b und SH-8c waren Stellproben an Mülleimern, Ecke und Garderobe; die
   ganze Fahrt („Teil B“) entfiel jedes Mal. Regel 1 (eine Änderung je
   Realtest) war je Test eingehalten, aber keine der vier ist an der Tür
   oder in einer ganzen Fahrt geprüft. Welche die Tür verschlechtert hat,
   ist deshalb nicht bekannt.
3. **Die Tür war schon am 08.11. knapp** (SH-7 Fahrt 3, SH-7N Punkt 4). Das
   stand als „einmalig“ unter „Geparkt“ und wurde nicht verfolgt.
4. **Der Suchmechanismus EK-1 war in W-1 aus.** Er ist gebaut und am 14.11.
   in der Simulation geprüft (A Teilschwenk, B Lücken ab 0,5 m, D Abbruch
   nach 45 s: 5 statt 13–14 Anläufe, 245–282 s statt 455–742 s). Im
   Produktprofil ist keiner der Schalter gesetzt
   (`self_healing_scan_rad`, `self_healing_gap_depth_m`,
   `self_healing_attempt_stall_s`, alle 0). Er stand unter „Geparkt“ mit der
   Bedingung „der Antrieb fährt, was befohlen wird“. Diese Bedingung war
   seit AT-2 (15.11.) erfüllt; W-1 lief trotzdem ohne ihn, weil die
   Wohnungsfahrt mit KM-2 als einziger Änderung vorgezogen wurde. Dem
   Projektinhaber wurde das nicht deutlich gesagt.
5. **Der schnelle Antrieb hat die alte Suche verschärft:** Dieselben
   Drehbefehle werden jetzt ausgeführt statt zu einem Fünftel; mehr Drehung
   je Minute bedeutet mehr SLAM-Knoten je Minute und früheren Rückstand.

**Entscheidung des Projektinhabers (16.11.2026):** Der vereinbarte
Suchmechanismus kommt zuerst. Ein Raum darf bei 80–85 % als erfasst gelten;
ohne Fortschritt sucht Amadeus dort nicht weiter und geht zum nächsten Raum.

**Was daraus folgt:**
- Die geplante Türprobe als reine Messung entfällt.
- **Nächster Realtest: SH-9, EK-1 (A + B + D) einschalten**, zwei Räume
  (Labor und Flur, übrige Türen zu) wie in SH-7. Das ist die eine Änderung.
  Mitlesend läuft eine Aufzeichnung für die Tür (lokale Karte an der Kontur
  bei jedem Halt des Reglers, Karte gegen globale Kostenkarte am Roboter).
- Vorher: EK-1 in der Simulation auf dem heutigen Stand (KM-1 B, KM-2,
  Antrieb folgt den Befehlen); die Läufe vom 14.11. rechneten mit dem trägen
  Antrieb.
- Die Tür (Planungsstreifen, Verkeilen, Rückfahrt am Pfosten) und der
  SLAM-Rückstand sind die nächsten Korrekturen, je eine je Realtest; beide
  stehen unter „Geparkt“ mit Wiederaufnahme nach SH-9.
- **Neue Regel:** Nach jeder Änderung am Fahr- oder Kartenverhalten folgt
  vor der nächsten Änderung eine ganze Zwei-Raum-Fahrt durch die Tür.

**Offen:** Schrägstand in der Tür; Herkunft der tödlichen Zellen unter dem
Roboter in der globalen Kostenkarte; Grund der Fahrtorsperre vor dem
Abbruch der Rückfahrt; Wackelspitze im Stand in Fahrt 2 (0,31 rad/s, kein
Fahrbefehl; Christopher wurde dazu nicht befragt); ob Startplatz und
Richtung in Fahrt 2 dieselben waren (das erste Ziel war praktisch dasselbe).

W-1N [archiviert](archive/20261116-w1n-ausgewertet/README.md).

## 15.11.2026 (spät) – W-1 ausgewertet: Stellprobe bestanden, die Wohnungsfahrt bleibt im Laborraum

Bericht `~/selbstheilung_jetson_bericht_w1.md` (Jetson, HEAD `d6a0416`,
neuer Release `selbstheilung-w1-20261115_1801`, Build 182 s, 209 Tests
bestanden, Profilzeilen wie erwartet einschließlich KM-2). Fünf Stackstarts,
alle mit Mission und mit `hwt601_accel_ms:=100`; Vorprüfung je Start 67× OK
(KM-2-Zeilen OK, auch „Kollisionsmonitor benutzt diese Kontur“).

**Teil A, Stellprobe mit KM-2: bestanden.**

| Probe | Urteil | Zeit bis 0,5 m | Rückfahrt | „approach“ | größtes Wackeln |
|---|---|---|---|---|---|
| s3a Mülleimer | `befreit` | 151,1 s | 0,244 m in 16,4 s (vom Explorer beendet) | 0 | 0,016 rad/s |
| s3b Mülleimer | `befreit` | 94,7 s | 0,307 m in 20,8 s | 0 | 0,019 rad/s |
| s2a Ecke | `befreit` | 136,9 s | zweimal 0,309 m in 20,9 s | 0 | 0,028 rad/s |

Keine Berührung, kein Eingriff, kein Eigenecho; Christopher: „gut
ausgewichen“, „nichts gewackelt“. Ruhewert des Wackelns 0,007 rad/s; die
Messquelle war in allen Starts da. Die Kontur schaltete bei jeder
Rückfahrt auf „Rückzug“ und zurück. **Die Sperre, für die KM-2 gebaut
wurde, trat nicht auf** (kein „approach“ in fünf Läufen); KM-2 ist damit
unter Humble verdrahtet und unschädlich, sein Nutzen real aber nicht
gezeigt.

**Teil B, Wohnungs-Messfahrt: Amadeus kam nicht aus dem Laborraum.**
Offen waren Labor, Flur, Bad, Schlafzimmer und Küche (Fliesen in Bad und
Küche), zu war das Wohnzimmer.

| | w1 | w2 |
|---|---|---|
| Ende | „Hilfe benötigt“ nach 218,9 s, schräg in der Tür zum Flur | nach 1175 s auf Wunsch des Projektinhabers gestoppt |
| Anläufe begonnen / erreicht / gescheitert / abgebrochen | 12 / 1 / 11 / 0 | 27 / 2 / 11 / 14 |
| freie Fläche | 16,2 m² nach 2 min, 18,2 m² am Ende | 14,8 m² nach 2 min, 15,7 m² nach 10 min, 17,6 m² am Ende |
| Weg / Drehung laut Odometrie | 3,3 m / 8,9 rad | 13,0 m / 126 rad (rund 20 volle Drehungen) |
| „Controller patience exceeded“ | 11 | 34 |
| „detected collision ahead“ | 353 | 1122 |
| Zeitfehler („extrapolation into the future“) | 0 | 271 |
| Rechenlast `slam_toolbox` | 7 % | steigt von 7 % auf 40–64 % |
| Rückfahrten | 2 (0,308 m; 0,139 m abgebrochen) | 4 (0,13–0,33 m) |
| größtes Wackeln | 0,21 rad/s in der Fahrt bei 134 s | 0,31 rad/s **im Stand** bei etwa 668 s |

**Beobachtung des Projektinhabers (zu Teil B, sinngemäß wörtlich):** Der
erste Teil hat sehr gut funktioniert. Der Scan mehrerer Räume hat überhaupt
nicht funktioniert: Amadeus blieb im Labor, drehte sich unzählige Male im
selben Bereich, fuhr immer wieder dieselben Stellen an und kam nicht aus
dem Raum. Es wirkte unkoordiniert, ohne erkennbare Struktur. Ein Raum
müsste in kurzer Zeit erfasst sein, und dann müsste er zum nächsten fahren.

**Was belegt ist:**

1. **Der Raum selbst ist schnell erfasst:** 85 % der Endfläche nach 121 s
   (w1) und 181 s (w2). Danach kommt kaum Fläche dazu (w2: 0,9 m² zwischen
   Minute 2 und 10).
2. **Die Tür wird nicht geschafft.** w1 stand am Ende schräg (43°) in der
   80-cm-Tür [**Korrektur 16.11.:** 43° ist die Blickrichtung in der Karte,
   kein gemessener Schrägstand; die tödlichen Zellen „im Gehäuse hinten
   rechts“ der lokalen Karte stammen aus einer veralteten Datei und sind
   nicht belegt; siehe Abschnitt 16.11.]; die Mitte lag in der globalen Karte im Sperrbereich des
   Türrahmens (Wert 99, hintere rechte Ecke 100), der Planer meldete achtmal
   „failed to create plan“. In der lokalen Karte lagen tödliche Zellen im
   Gehäuse hinten rechts (Türpfosten).
3. **In w2 endeten 25 von 27 Anläufen ohne Ziel**, 14 davon mit „Goal
   canceled“. Das Fahrtprotokoll zählt nur 12 Heilungen; mindestens 13
   Anläufe endeten also, ohne dass der Explorer einen Fehlschlag verbuchte.
4. **Die Zeit ging in Drehungen:** 126 rad bei 13 m Weg.
5. **Die Zeitfehler begannen bei etwa 163 s** und häuften sich in den
   Minuten 9–11, 14–15 und 17–18; dazu „Control loop missed its desired
   rate“ und „Behavior Tree tick rate exceeded“.

**Aus dem Code gelesen (erklärt Punkt 3, ist aber an den Daten noch nicht
geprüft):** Der Explorer bricht einen laufenden Anlauf ab, sobald eine
Quelle fehlt oder der HWT-Pfad „HOLD“ meldet (`stop_requested`). Ein
solcher Abbruch zählt nicht als Fehlversuch: Das Ziel wird nicht
zurückgestellt, und nach dem Warten wählt er wieder das beste Ziel, also
meist dasselbe. Jeder neue Anlauf beginnt mit einer Drehung in die
Wegrichtung. Dazu kommt die erste Stufe der Heilungsleiter, die dasselbe
Ziel absichtlich noch einmal versucht.

**Vermutungen, nicht gemessen:**

- Warum die Anläufe zur Tür scheitern (Regler hält vor den Pfosten an;
  Zellen im eigenen Umriss seit KM-1 B; Zeitfehler; Abbrüche durch Warten).
- Worauf der Explorer in w2 gewartet hat.
- Ob die Rechenlast Ursache oder Folge der vielen Drehungen ist.
- Was die Wackelspitze im Stand war (äußere Einwirkung oder Messfehler);
  der Projektinhaber hat dazu nichts berichtet.

**Was W-1 für den Fahrplan bedeutet:** Die Messfahrt hat geliefert, wofür
sie gedacht war. Vor Fliesen, niedrigen Möbeln und Zeitbudget steht das
Verlassen des Raums. Schritt 2 des Fahrplans („Erkundung zielgerichtet“,
am 14.11. in der Simulation vorbereitet) und die Türdurchfahrt gehören
dazu; welche Änderung zuerst kommt, entscheiden die Zahlen aus W-1N.

**Noch am selben Abend aus Bericht, Code und Einstellungen belegt (ohne
neue Messung am Roboter):**

1. **Warum „Hilfe benötigt“ in w1** (Frage des Projektinhabers): Der
   globale Planer rechnet Amadeus als Kreis mit 0,28 m Radius
   (`robot_radius`, globale Kostenkarte). Jede Zelle näher als 0,28 m an
   einem Hindernis ist für ihn gesperrt, und NavFn räumt nur die eine Zelle
   unter dem Roboter frei. In einer 80-cm-Tür bleibt rechnerisch ein
   Streifen von rund 0,25–0,30 m in der Mitte. Amadeus stand am Ende neben
   diesem Streifen (Mitte Wert 99, alle Ringe bis 0,30 m ≥ 99); von dort
   gibt es für den Planer keinen Weg, achtmal hintereinander, dann Hilfe.
2. **Wie er dorthin kam:** Der Regler hielt viermal vor einem Hindernis an
   („collision ahead“, 1,5 s Geduld, dreimal je Ziel). Die zweite Rückfahrt
   brach der Explorer selbst nach 2,9 s und 0,139 m ab; danach stand
   Amadeus im gesperrten Bereich. Den Grund des Abbruchs nennt der Bericht
   nicht.
3. **Schrägstand kostet Breite:** Die gepolsterte Kontur (0,46 m × 0,50 m)
   braucht gerade 0,50 m, bei 43° aber 0,68 m [**Korrektur 16.11.:** die
   Rechnung stimmt, der Schrägstand von 43° ist aber nicht gemessen]. In einer 80-cm-Tür bleiben
   dann 6 cm je Seite statt 15 cm.
4. **13 der 14 Abbrüche in w2 stehen nicht in der Heilungsliste** (12
   Heilungen: 11 Fehlschläge, 1 Zielzeit). Sie liefen also über den Weg
   „Unterbrechung“ (`stop_requested`: HWT-HOLD oder eine fehlende Quelle);
   die Stillstandserkennung im Anlauf ist im Profil aus. Nach einer solchen
   Unterbrechung wählt der Explorer wieder das beste Ziel, ohne den Anlauf
   zu zählen. Welche Bedingung es war, misst W-1N.
5. **Die Simulation zeigt den Fehler nicht:** Im Lauf Labor und Flur vom
   15.11. ist die Tür ebenfalls 0,80 m breit; dort erreichte Amadeus 9 von
   12 Zielen, auch im Flur, ohne Abbruch und ohne Warten. Was real anders
   ist (Türrahmen in der Karte, Anfahrwinkel, Zeitfehler), ist offen.

**Nächster Schritt (MASTERPLAN §9 Regel 4): W-1N**, nur lesend, mit zwei
Werkzeugen (`f1694a2`, 22 Tests, an Simulationslogs und synthetischen
Karten gelaufen):

- `tools/kartierung/selbstheilung_ablauf.py`: Ziele und Wiederholungen,
  Anläufe der Reihe nach mit Abstand von Start und Ziel zur Tür, Grund
  jedes Abbruchs, Warte- und HWT-Phasen, Rückfahrten, Verlauf je Minute.
- `tools/kartierung/karte_engstelle.py`: lichte Weite der Tür in der
  gesicherten Karte von w1, für den Planer freier Anteil (Karte und globale
  Kostenkarte), Schrägstand und belegte Zellen in der Kontur.

W-1 [archiviert](archive/20261115-w1-ausgewertet/README.md).

## 15.11.2026 (nachts) – Entscheidung: Wohnung jetzt; was die erste Wohnungsfahrt braucht

**Entscheidung des Projektinhabers:** Das Tempo war das Ziel der letzten
Runden und ist erreicht; als Nächstes die Erkundung der ganzen Wohnung.
Festgelegt im Gespräch: **alle Räume als begleitete Messfahrt** (kein
Bestehen oder Durchfallen), **Bewegliches wegräumen**, in der Wohnung gibt
es **keine Stufe nach unten und keine Schwelle, aber Fliesen mit Fugen**.
SH-8d war noch nicht gelaufen und ist
[zurückgezogen](archive/20261115-sh8d-zurueckgezogen/README.md).
Fahrplan: MASTERPLAN §9, Nachtrag 15.11.2026.

**Bewertung: Was ist für die Wohnung nötig, und wie geht W-1 damit um?**

| Punkt | Stand | In W-1 |
|---|---|---|
| Antrieb folgt den Befehlen | gemessen (AT-2, SH-8c) | jeder Start mit `hwt601_accel_ms:=100`, Zeile wird je Start geprüft |
| Sperre des Kollisionsmonitors ohne Ausweg (SH-8c Mülleimer) | KM-2 gebaut, Simulation bestanden, **am Roboter nicht geprüft** | **Teil A:** Stellprobe Mülleimer zweimal, Ecke einmal; ohne bestandene Stellprobe keine Wohnungsfahrt |
| Freigabe für neue Räume (LAB-1 gilt dort nicht von selbst) | vom Projektinhaber für diese Messfahrt erteilt, mit Bedingungen | steht im Rahmen des Auftrags; Christopher bestätigt die Vorbereitung einmal (B1) |
| Stufen nach unten, Schwellen (Amadeus erkennt keinen Abgrund) | laut Projektinhaber keine | Frage 5 in B1; bei „ja“ keine Fahrt, bis die Stelle abgetrennt ist |
| Seiten niedriger Dinge (15–66 cm) | ungelöst; Simulation: Berührung beim Drehen; real 0–2 cm | Bewegliches weg, Stühle an den Tisch; feste Möbel werden je Raum notiert; Christopher greift vor einer Berührung ein; jeder Eingriff mit Ort und Grund ist Messwert M5 |
| Rückfahrt blind (bis 0,4 m) | ungelöst | Christopher achtet auf das Heck; Eingriffsgrund |
| Fliesenfugen bei echtem Tempo | nie gemessen; kein Schutz im Stack | wird gemessen (`wackeln`, Frage 5); starkes Schwanken ist Eingriffsgrund |
| Flaches unter 5 cm (Kabel, Teppichkanten) | Sensorgrenze | wird vorher weggeräumt (B1) |
| Glas und Spiegel bis zum Boden | nie geprüft | Frage 4 in B1; Eingriffsgrund, wenn er darauf zufährt |
| Zeitbudget 40 min | für zwei Räume gesetzt; für die Wohnung unbekannt | bleibt (keine zweite Änderung); „Teilkarte“ ist für eine Messfahrt ein gültiges Ende; die Zahlen bestimmen das spätere Budget |
| Erkundungstempo (Schritt 2, EK-1 mit Lückenfilter) | in der Simulation vorbereitet, ausgeschaltet | nicht dabei; die Abdeckungskurve von W-1 zeigt, ob es gebraucht wird |
| „Weiter“ nach „Hilfe benötigt“ | nicht vorhanden | eine zweite Fahrt als Kaltstart ist erlaubt (B8) |
| Karte speichern und Räume benennen (Schritt 5) | später | Karte wird lokal gesichert, sonst nichts |
| Startfehler (LiDAR „abnormal“, „D Quellen“) | bekannt, Vorprüfung fängt sie ab | Neustart wie bisher |

**Was W-1 ausdrücklich nicht ist:** keine Abnahme der Wohnung (Stufe 3
bleibt: drei Läufe, alle Räume, Karte mindestens 90 %, kein Kontakt), kein
Test neuer Erkundungslogik, keine Raumziele.

**Was W-1 liefern soll:** die befahrenen Räume und Zeiten, die
Abdeckungskurve, alle Heilungen und Hilferufe, jeden Eingriff und jede sehr
nahe Stelle mit Ort und Gegenstand, das Wackeln auf den Fliesen und
Christophers Urteil zur Karte je Raum. Daraus folgt die Reihenfolge der
nächsten Arbeiten für die Wohnung.

**Risiko, offen benannt:** Der größte bekannte Mangel für eine möblierte
Wohnung, die Seiten niedriger Dinge, ist nicht gelöst. W-1 fährt deshalb
nur begleitet; eine unbegleitete Wohnungsfahrt ist damit nicht freigegeben.

**Nächster Schritt:** W-1-Bericht auswerten.

## 15.11.2026 (abends) – SH-8c ausgewertet: Ecke gelöst, Mülleimer vom Kollisionsmonitor festgehalten

Bericht `~/selbstheilung_jetson_bericht_sh8c.md` (Jetson, Klon `63c2630`,
Release `selbstheilung-sh8b-20261114_1643` ohne Build, jeder Start mit
`hwt601_accel_ms:=100`, „Beschleunigen 100 ms“ je Probe bestätigt, 37
Werkzeugtests). Sieben Stackstarts, vier mit Mission. Keine Berührung, kein
Eingriff, kein „process has died“. Christopher zu allen Proben: Aufbau nicht
gewackelt, Tempo „Passend“.

| Probe | Urteil | Zeit bis 0,5 m | Rückfahrt | „approach“ | SH-8b zum Vergleich |
|---|---|---|---|---|---|
| s3a Mülleimer | `nicht_befreit`, „Hilfe benötigt“ nach etwa 2 min (0,124 m) | – | eine, vom Kollisionsmonitor 16 s lang auf null gehalten | 1 | `nicht_befreit` (0,483 m) |
| s2a Ecke | **`befreit`** | 91,6 s | **0,307 m in 20,6 s, erfolgreich** | 0 | „Hilfe benötigt“ (0,151 m) |
| s2b Ecke | **`befreit`** | 93,4 s | **0,308 m in 20,8 s, erfolgreich** | 0 | „Hilfe benötigt“ (0,151 m) |
| s1a Garderobe | `nicht_blockiert` (ohne Heilung weg, 110 s) | 110,0 s | keine | 0 | „Hilfe benötigt“ (0,151 m) |
| s1a_nah (3 cm) | nicht gefahren: Vorprüfung Bereich F `FEHL` | – | – | – | – |

**Urteil nach A7: nicht bestanden** (s3a; danach beendete der F-Befund vor
s1a_nah den Auftrag regelgerecht; s3b und s1b entfielen).

**Was belegt ist:**

1. **Der Antrieb folgt auch in der echten Kette.** Die Rückfahrt mit
   −0,015 m/s legte 0,307 und 0,308 m in 20,6 und 20,8 s zurück (413 und
   418 Befehle, das sind 0,31 m); das Rechenmodell hatte „0,3 m in etwa
   21 s“ vorhergesagt. Vorwärts kamen bis 0,135 m/s an der Basis an.
2. **Die Ecke ist gelöst:** ein Fehlschlag, eine freie Rückfahrt, dann ein
   erreichtes Ziel und weg. In SH-8b endete dieselbe Stelle mit „Hilfe“.
3. **An den Mülleimern hält der Kollisionsmonitor Amadeus wieder fest**
   (wie in SH-8 am 13.11.), Ablauf:
   - Erstes Ziel (0,30 | −0,23) liegt dicht vor dem rechten Eimer. Amadeus
     drehte 35° nach rechts und fuhr in der Langsam-Zone (0,015 m/s) 12 cm
     schräg vor; dann verweigerte der Regler („detected collision ahead“).
   - Seine linke vordere Ecke lag danach am rechten Eimer: tödliche Zellen
     0–3 cm vor der gepolsterten Front, **102 VL53-Punkte im
     2-cm-Polsterband** (Nachprüfung, links). Berührt hat er nicht.
   - Zweiter Fehlschlag → Rückfahrt entlang der eigenen Spur (0,10 m). Im
     selben Moment „Robot to approach“; an der Basis kam 16 s lang kein
     Befehl ungleich null an, die Rückfahrt lief in die Zeitgrenze.
   - Danach scheiterte jeder Anlauf nach etwa 11 s, bis „Hilfe benötigt“.
     Eine zweite Rückfahrt gibt es je Stillstand nicht.
4. **Warum KM-1 B das Heranfahren hier nicht verhindert hat:** Die Karte
   kannte vom runden Eimer nur den Bogen, den die VL53 vom Startplatz aus
   sahen. Beim Schwenken fuhr die Ecke in den Teil, der noch nicht
   eingetragen war. Zudem hält der Regler erst an, wenn die gepolsterte
   Kontur eine 5-cm-Zelle berührt; die echte Oberfläche kann dann schon im
   Polsterband liegen.
5. **Garderobe:** Bei 5 cm fuhr er ohne Heilung weg (`nicht_blockiert`). Bei
   3 cm lagen 6410 LiDAR-Punkte an der Frontkante im Gehäuse (x ≈ 0,31 m),
   vermutlich überhängende Jacken auf LiDAR-Höhe, kein Teil des Roboters
   (Vermutung des Agenten, nicht geprüft). Mit KM-1 B stünde so etwas als
   Hindernis im Gehäuse; Bereich F hat es abgefangen.

**Einordnung:** Regler und Kollisionsmonitor arbeiten mit derselben Kontur
(Gehäuse plus 2 cm). Zwischen „der Regler hält an“ und „der
Kollisionsmonitor sperrt alles“ liegt keine Reserve. Ist die Sperre einmal
da, gilt sie auch für die Bewegung vom Hindernis weg. Solange das so ist,
endet jedes zu nahe Heranfahren an einen niedrigen Gegenstand mit „Hilfe
benötigt“, gleich wie es dazu kam.

**Zwei Messfehler in meinen Werkzeugen** (beide korrigiert, 17 Tests):

- **`wackeln` blieb in allen Proben leer.** Im Protokoll stand der
  Topic-Name aus dem allgemeinen Profil (`/hwt601/imu/data_raw`); im
  laufenden Stack heißt er `/shadow/hwt601/imu/data_raw`. Das ist derselbe
  Fehler wie bei AT-1: eine Annahme über die Messanordnung, nicht am
  Startprofil geprüft. Der eigene Probelauf speiste genau das falsche Topic.
  Neu: richtiger Name, ein Test bindet ihn an die Startdatei, und das
  Werkzeug meldet schon vor der Mission „Messquelle Wackeln: OK/FEHLT“.
- **`tempo_folge` ist als rohe Summe nicht belastbar:** s2a 1,00 / 1,09 und
  s2b 1,12 / 1,13 sind plausibel, s1a 2,35 / 1,63 nicht. Die Ursache ist
  nicht gemessen; nahe liegt, dass sich kleines Zittern der Odometrie über
  3300 Messpunkte aufsummiert. Neu: Weg und Drehung zählen in Schritten ab
  5 mm bzw. 0,02 rad; die rohe Summe steht zum Vergleich daneben. Gesichert
  ist bisher nur die Rückfahrt (Strecke gegen Befehl auf 1 %).

**Nicht belegt:** ob der Aufbau messbar wackelt (keine Daten; Christopher:
nein); wie die Garderobe mit 100 ms ausgeht; ob eine volle Fahrt jetzt
durchläuft.

**Nächster Schritt (MASTERPLAN §9 Regeln 2 und 4): Simulation KM-2 „Rückzug
aus der Sperre“**, Kriterien vor dem ersten Lauf:

1. Die Sperre aus SH-8c s3a entsteht in der Simulation (Start dicht an einem
   niedrigen Gegenstand mit VL53-Punkten im Polsterband), und der heutige
   Stand kommt dort nicht weg.
2. Mit KM-2 kommt Amadeus aus derselben Lage mit einer geraden Rückfahrt
   weg, ohne dass das echte Gehäuse etwas berührt.
3. Vorwärtsfahrt und Drehen bleiben gesperrt, solange Punkte im Polsterband
   liegen (kein Rückfall auf Variante A).
4. Die bisherigen Stellproben der Simulation (Mülleimer mittig, links,
   rechts mit Drift) bleiben bei `befreit` ohne Gehäuseberührung.

SH-8c [archiviert](archive/20261115-sh8c-ausgewertet/README.md).

### KM-2 in der Simulation (15.11.2026 abends): Kriterien 1 bis 3 erfüllt, 4 mit Einschränkung

**KM-2** (`c8873c9`, nur `self_healing:=true`): Knoten
`robot_navigation/monitor_kontur` publiziert die Kontur für die
„approach“-Prüfung des Kollisionsmonitors auf `kollisionsmonitor_kontur`.
Sie ist die volle gepolsterte Kontur (Gehäuse plus 2 cm), außer bei einem
frischen Befehl „gerade rückwärts“ (v ≤ −0,004 m/s, |w| ≤ 0,02 rad/s,
höchstens 0,3 s alt); dann ist es die Rückfahrkontur aus AW-1 (Front im
Roboter, Heck mit Polster). Das Overlay des Kollisionsmonitors verweist
darauf; Mapping- und Standardprofil bleiben unverändert. Die Langsam-Zone
gilt weiter, auch rückwärts. 209 gezielte Tests.

| Lauf (Simulation, idealer Antrieb) | Stellprobe | Gehäuse bis 0,5 m | erste Rückfahrt | „approach“ | später |
|---|---|---|---|---|---|
| Sperre 1 cm, **Stand SH-8c** | **`nicht_befreit`**, „Hilfe“ nach 113 s | 1,0 cm (Start) | 30 s auf null gehalten, keine Strecke | 1 | – |
| Sperre 1 cm, **KM-2** | **`befreit`** nach 87 s | 1,0 cm (Start) | 0,303 m in 20,4 s | 1 (50 ms) | Berührung nach 145 s |
| Mülleimer mittig, KM-2 | `befreit` nach 116 s (vorher 118 s) | 3,0 cm | 0,304 m | 2 | Berührung nach 158 s (vorher 173 s) |
| Mülleimer links, KM-2 | `befreit` nach 79 s (vorher 80 s) | 3,5 cm | 0,304 m | 0 | Berührung nach 106 s (vorher 105 s) |
| Mülleimer rechts mit Drift, KM-2 | `befreit` nach 64 s (vorher 64 s) | 1,8 cm | 0,304 m | 0 | Berührung nach 230 s |
| Labor und Flur möbliert, KM-2 | Teilkarte, 98,5 %, 510 s, 9 Ziele | – | 0,305 m | 0 | keine Berührung (1,3 cm) |

- **Kriterium 1 erfüllt:** Der Stand von SH-8c zeigt in der Simulation
  dasselbe Bild wie real (eine Rückfahrt, vom Kollisionsmonitor bis zur
  Zeitgrenze gehalten, danach acht Fehlschläge, „Hilfe benötigt“).
- **Kriterium 2 erfüllt:** Mit KM-2 läuft die Rückfahrt aus derselben Lage
  durch; bis 0,5 m Entfernung berührt das Gehäuse nichts.
- **Kriterium 3 erfüllt:** Die Kontur schaltete in allen Läufen nur während
  der Rückfahrten auf „Rückzug“ und danach sofort zurück (je Rückfahrt genau
  ein Paar). Vorwärts und beim Drehen gilt die volle Kontur (Test).
- **Kriterium 4 mit Einschränkung:** Die drei Mülleimer-Stellproben bleiben
  bei `befreit` mit denselben Zeiten und ohne Berührung bis 0,5 m. „Ohne
  Gehäuseberührung“ über den ganzen Lauf war als Kriterium falsch gestellt:
  Schon vor KM-2 berührte das Gehäuse in diesen Welten nach dem Befreien
  eine Eimerseite (geparkter Punkt „niedrige Gegenstände seitlich“). KM-2
  ändert daran nichts, in beide Richtungen.
- Die möblierte Zwei-Raum-Fahrt liegt im Bereich der früheren Läufe (455 bis
  600 s, 97,7–98,5 %); ein einzelner Lauf, kein Beleg für eine Verbesserung.

**Nicht belegt:** ob der Kollisionsmonitor unter Humble die Kontur genauso
annimmt wie unter Jazzy (die Vorprüfung auf dem Roboter prüft das im Stand:
Verdrahtung, Geometrie und, falls publiziert, seine eigene Sicht); ob die
Simulation das Heranfahren an einen runden Eimer so zeigt wie real.

**Auftrag SH-8d (am selben Abend zurückgezogen, siehe Abschnitt 15.11.2026
nachts; die Stellprobe steckt in W-1):** neuer Build (einzige Änderung KM-2),
jeder Start mit `hwt601_accel_ms:=100`. Teil A: Mülleimer zweimal, Garderobe
zweimal (ohne 3-cm-Wiederholung), Ecke einmal. Bestanden, wenn die
Mülleimer und die Ecke `befreit` ergeben und nichts mit `nicht_befreit`,
Berührung, Eingriff oder Eigenecho endet. Nur dann Teil B: eine volle
Zwei-Raum-Fahrt ohne Mülleimer. Das Fahrtprotokoll misst Wackeln jetzt auf
dem richtigen Topic und meldet die Quelle vor der Fahrt.

**Nächster Schritt damals:** SH-8d-Bericht auswerten (überholt durch W-1).

## 15.11.2026 (nachmittags) – AT-2 ausgewertet: bestanden; mit 100 ms folgt der Antrieb den Nav2-Rampen

Bericht `~/selbstheilung_jetson_bericht_at2.md` (Jetson, Klon `487de06`,
Release `selbstheilung-sh8b-20261114_1643` ohne Build, 23 Tests bestanden,
Vorprüfung 59× OK). Ein scharfer Stackstart mit `hwt601_accel_ms:=100`,
keine Mission, zwei Proben direkt auf `/cmd_vel`. Die Basis meldete
„Anfahrverhalten bestaetigt: Beschleunigen 100 ms, Bremsen 400 ms,
Startdrehzahl 5 rpm“. Messung ungestört (0 Nachrichten auf `/cmd_vel` vor,
zwischen und nach den Proben; an der Basis überall der Sollwert). Kein
Abbruch, keine Berührung, kein Eingriff.

| Abschnitt | Sollwert | Ist/Soll Probe 1 / 2 | Modell | AT-1b bei 2000 ms |
|---|---|---|---|---|
| C Ende (Rampe auf 0,10 m/s) | 0,10 m/s | 0,99 / 0,99 | 1,00 | 0,11 / 0,22 |
| G oben | 0,10 m/s | 1,00 / 0,99 | 0,99 | – (Modell 0,05) |
| G unten (Rampe ab) | 0,04 m/s | 0,98 / 1,00 | 1,03 | – |
| G wieder (Rampe auf) | 0,08 m/s | 0,99 / 0,96 | 1,00 | – (Modell 0,56) |
| R Ende (langsame Rückfahrt) | −0,015 m/s | 1,00 / 1,01 | 1,00 | – (Modell 0,16) |
| E Ende (Drehrampe) | 0,25 rad/s | 1,01 / 1,03 | 1,00 | 0,11 / 0,11 |
| S Stufe 0,03 → 0,10 m/s | 0,10 m/s | 0,99 / 0,99 | 1,00 | – |

Wege: C 0,502 / 0,508 m (Vorhersage 0,49), G 0,568 / 0,584 m (0,56), R
−0,111 / −0,111 m (0,11), E 76,1° / 73,9° (70°), S 0,502 / 0,500 m (0,49).
Rückwege enden auf 8 mm am Ausgangspunkt.

**Urteil: zweimal `ja`, bestanden.** Christopher: beide Male „Überall
zügig“.

**Was belegt ist:**

1. Mit 100 ms Anfahrzeit setzt der Antrieb Rampen in 20-Hz-Schritten voll
   um, vorwärts, beim Langsamerwerden, rückwärts im Kriechgang und beim
   Drehen. Die Ursache aus AT-1b ist damit durch die Gegenprobe bestätigt.
2. Die Vorhersage des Modells traf in allen Abschnitten auf wenige Prozent.
   In den ersten zwei Sekunden war der echte Antrieb etwas schneller als
   gerechnet (C: 0,025 / 0,077 m/s gemessen, 0,022 / 0,070 gerechnet).
3. Die langsame Rückfahrt (der Engpass der Stellprobe) erreicht jetzt ihr
   Tempo nach etwa 1,5 s; 0,3 m dauern damit rund 21 s statt nie.

**Beobachtung zum Aufbau (Christopher, nicht gemessen):** Probe 1 „bei der
ersten Fahrt beim anfahren hat es geruckelt“ (Phase C), Probe 2 „die letzte
Fahrt war beim anfahren sehr ruckelig“ (Phase S, mit der Stufe 0,03 → 0,10
m/s). Kein starkes Schwanken, kein Eingriff. In je vier von fünf Fahrten
nannte er kein Ruckeln. Im Protokoll gibt es keine Messgröße dafür.

**Einordnung des Ruckelns:**

- Die Stufe in S ist rechnerisch die härteste Stelle: 0,07 m/s in 0,1 s,
  also 0,7 m/s². So eine Stufe entsteht im Betrieb beim Verlassen der
  Langsam-Zone, weil der Kollisionsmonitor hinter dem Glätter sitzt.
- Beim Anfahren auf einer Rampe (C) rechnet das Modell mit höchstens 0,07
  m/s². Warum es dort einmal ruckelte, ist nicht gemessen.
- Zwischenwerte der Anfahrzeit helfen nach dem Modell nicht: Schon mit
  200 ms erreicht der Antrieb nach einer Rampe nur 54 % (G oben), mit
  300 ms 36 %. 100 ms ist der kleinste zugelassene Wert des Startarguments.
- Falls das Rucken stört, wäre der gezielte Weg eine Anstiegsbegrenzung im
  Motortreiber (jeder Sprung nach oben wird zu einer Rampe; Bremsen und
  Stopp bleiben sofort). Das ist eine Codeänderung an der Motorsteuerung und
  steht unter „Geparkt“.

**Was sich für den Betrieb ändert, wenn 100 ms Standard wird:**

- Amadeus fährt dann zum ersten Mal in der Selbstheilungslinie wirklich das
  befohlene Tempo: im Profil 0,135 m/s vorwärts und 0,25 rad/s, in der
  Langsam-Zone 30 % davon. Bisher waren es real 1,3–1,7 cm/s. Die Tempo-
  erhöhung vom 05.11. (+35 %/+25 %) wurde beschlossen, als der Antrieb nur
  ein Fünftel umsetzte.
- AT-2 hat bis 0,10 m/s und 0,25 rad/s gemessen, nicht 0,135 m/s.
- Bremswege und Abstände wurden für diese Geschwindigkeiten ausgelegt, sind
  in der Selbstheilungslinie aber nur im Kriechtempo erlebt worden. Die
  erste Fahrt mit folgendem Antrieb ist deshalb eine Stellprobe unter
  Aufsicht, keine lange Fahrt (MASTERPLAN §9 Regel 6).
- Die Bremszeit (400 ms) und der Stopp bei Nullbefehl sind unverändert.

**Stand am Roboter:** Im Antrieb stehen bis zum nächsten Start 100 ms; jeder
Start schreibt den Wert neu (ohne Argument 2000 ms). AT-2
[archiviert](archive/20261115-at2-ausgewertet/README.md).

**Vorschlag für den nächsten einzelnen Schritt** (MASTERPLAN §9 Regeln 1
und 6): die Stellprobe an denselben drei Stellen wie SH-8b mit genau einer
Änderung, `hwt601_accel_ms:=100`, ohne Build. Sie prüft das aktive Problem
(Freifahren) zum ersten Mal mit einem Antrieb, der tut, was befohlen wird.

**Entscheidung des Projektinhabers (15.11.2026): 100 ms ist der Standard
für den selbstheilenden Betrieb; als Nächstes die Stellprobe.** Zur Wahl
standen außerdem „erst das Ruckeln beheben“ (Anstiegsbegrenzung im Treiber)
und „erst langsamer“ (Tempo zurück auf 0,10 m/s, zweite Änderung im selben
Test). Umsetzung:

- **Auftrag [SH-8c](AGENTENAUFTRAG.md):** Stellprobe wie SH-8b Teil A, ohne
  Build mit dem Release `selbstheilung-sh8b-20261114_1643` (enthält KM-1 B),
  Start mit `hwt601_accel_ms:=100`; vor jeder Mission wird die Zeile
  „Anfahrverhalten bestaetigt: Beschleunigen 100 ms“ geprüft. Kein Teil B:
  Die volle Fahrt folgt erst nach der Auswertung, weil Amadeus hier zum
  ersten Mal das befohlene Tempo fährt.
- **Angepasst an das echte Tempo:** Das Protokoll endet 1 s (statt 5 s)
  nach 0,5 m, damit der Missionsstopp kommt, bevor Amadeus einen weiteren
  halben Meter gefahren ist. An der Garderobe sind hinten 0,7 m statt 0,5 m
  frei, weil die Rückfahrt jetzt wirklich bis 0,4 m reicht.
- **Neue Messgrößen im Fahrtprotokoll** (`e03cac3`, nur lesend, 15 Tests):
  `tempo_folge` (Weg und Drehung gefahren zu befohlen; bis SH-8b etwa 0,2)
  und `wackeln` (Drehrate um die waagerechten Achsen aus dem HWT601, in
  Ruhe, während der Fahrt und in den stärksten Sekunden mit Lage
  „anfahren“, „anhalten“, „fahrt“, „steht“).
- **Standard im Startprofil:** Bis zum nächsten Build steht `100` als
  Argument im Startbefehl jedes Auftrags. Mit dem nächsten Build wird der
  Wert für `self_healing:=true` im Launch verankert (eigener kleiner
  Schritt mit Vertragstest), sobald SH-8c ihn im Betrieb bestätigt hat.

**Nächster Schritt:** SH-8c-Bericht auswerten.

## 15.11.2026 (mittags) – AT-1b ausgewertet: Der Antrieb folgt Sprüngen, aber keinen feinen Rampen

Bericht `~/selbstheilung_jetson_bericht_at1b.md` (Jetson, Klon `84af692`,
Release `selbstheilung-sh8b-20261114_1643` ohne Build, Werkzeugtest 12
bestanden, Vorprüfung 59× OK). Ein scharfer Stackstart, keine Mission, zwei
Proben direkt auf `/cmd_vel`, kein Abbruch, keine Berührung, kein Eingriff.

**Die Messung ist diesmal ungestört:** vor Probe 1 und 2 und danach je 0
Nachrichten auf `/cmd_vel` (10 s, 5 s, 5 s gezählt), einziger Publisher der
Kollisionsmonitor, einziger Abonnent `base_hardware`; im Werkzeug 0 fremde
Nachrichten; an der Basis kam in jedem Abschnitt genau der Sollwert an.

| Phase | Sollwertfolge | `ist_zu_soll` Probe 1 / 2 | Weg bzw. Winkel |
|---|---|---|---|
| A | Sprung auf 0,10 m/s | 1,00 / 1,00 | 0,386 / 0,395 m |
| B | 0,02 m/s, dann Stufe auf 0,10 m/s | 1,00 / 1,01 | 0,472 / 0,465 m |
| C | **Rampe wie Nav2** auf 0,10 m/s | **0,11 / 0,22** | 0,041 / 0,079 m |
| F | 0,10 m/s, dann Stufe ab auf 0,03 m/s | 0,99 / 1,00 | 0,334 / 0,332 m |
| D | Sprung auf 0,25 rad/s | 1,01 / 1,02 | 70,7° / 71,5° |
| E | **Rampe** auf 0,25 rad/s | **0,11 / 0,11** | 6,1° / 5,7° |

**Urteil des Werkzeugs: zweimal `unklar`**, nach den vorab festgelegten
Regeln richtig (weder „Sprung gut, Rampe und Treppe schlecht“ noch „Rampe
und Treppe gut“). Die Regeln hatten diesen dritten Fall nicht vorgesehen.

**Was belegt ist:**

1. Die Hypothese „Sollwert nur beim Anfahren“ ist **in ihrer Form
   widerlegt**: Der Antrieb übernimmt neue Sollwerte während der Fahrt, auf-
   und abwärts (B, F).
2. Jeder Sprung und jede Stufe ist nach etwa 2 s erreicht, gleich wie groß
   (0 → 0,02 m/s, 0 → 0,10 m/s, 0,02 → 0,10 m/s).
3. Nach einer Rampe in 20-Hz-Schritten steigt das Tempo nur gleichmäßig und
   sehr langsam (C: 0,2 bzw. 0,5 cm/s je Sekunde), obwohl an der Basis ab
   0,8 s gut 5 s lang der volle Sollwert anlag.
4. Genau solche Rampen sendet Nav2 immer (Glätter 0,12 m/s² bei 20 Hz; beim
   Drehen begrenzt zusätzlich der Regler). Das ist das Kriechtempo aus den
   echten Fahrten.

**Erklärung (Rechenmodell, `tools/kartierung/antriebsmodell.py`, 9 Tests):**
Der Antrieb verteilt **jede Sollwertänderung auf seine Anfahrzeit**
(Register `0x001E`, 2000 ms), gerechnet ab dem vorigen Sollwert und nicht ab
dem tatsächlichen Tempo. Ein Sprung von 0 auf 153 U/min wird mit 153 U/min
in 2 s gefahren. Eine Rampe endet mit einem kleinen Schritt (147 → 153
U/min); danach beschleunigt der Antrieb nur noch mit 6 U/min in 2 s und
bräuchte für den Rest fast eine Minute.

| Größe | Modell | gemessen |
|---|---|---|
| A, Tempo je Sekunde (m/s) | 0,018 / 0,068 / 0,099 | 0,018 / 0,069 / 0,102 |
| B, Sekunden 5–7 (Stufe auf 0,10) | 0,035 / 0,074 / 0,100 | 0,035 / 0,076 / 0,102 |
| C, Sekunden 1–6 | 0,001 / 0,004 / 0,005 / 0,007 / 0,009 / 0,011 | 0,001 / 0,004 / 0,006 / 0,008 / 0,010 / 0,012 |
| E, Sekunde 6 (rad/s) | 0,029 | 0,031 / 0,031 |
| **SH-8b-Rückfahrt, 30,1 s (nicht angepasst)** | **0,153 m** | **0,151 m (dreimal)** |

Angepasst ist eine einzige Größe (0,13 s Laufzeit vom Befehl bis zum
Motor). Die Rückfahrstrecke aus SH-8b stammt aus einer anderen Fahrt und
war nicht Teil der Anpassung. C in Probe 2 (doppelt so schnell wie in Probe
1) passt zu einem ausgelassenen Rampenschritt (letzte Änderung 15 statt 6
U/min); das ist abgeleitet, nicht gemessen. **Es bleibt ein Modell**, für
andere Anfahrzeiten ist es eine Vorhersage.

**Woher es kommt (Historie, nur gelesen):** Bis zum 14.08.2026 standen im
Antrieb real 100 ms Anfahrzeit. Am 14.08. wurde sie auf 2000 ms gesetzt,
weil der hohe Aufbau beim Anfahren mit dem Steuerkreuz (Sprung auf vollen
Ausschlag) stark wackelte; geprüft wurde mit einem konstanten Sollwert. Die
Parameterdatei vermerkt schon damals, die Rampe wirke „offenbar weitgehend
direkt auf die Sollwertänderung“. Mit Rampen aus Nav2 wurde die Kombination
nie gemessen. Die Streckenkalibrierung ist davon nicht berührt: Die
Odometrie misst richtig, nur das Tempo wird nicht erreicht.

**Was das für die bisherigen Befunde heißt:**

- Kriechtempo 1,3–1,7 cm/s bei 6–10 cm/s Sollwert (Anhang Z), 150-s-Abbrüche
  und Ziele über 1,5 m fast nie erreicht: derselbe Mechanismus.
- Rückfahrt 0,151 m statt 0,3 m (SH-8, SH-8b): derselbe Mechanismus; in der
  Langsam-Zone ist der letzte Rampenschritt 1 U/min.
- Die Annahme vom 14.11. („bleibt beim ersten Sollwert, 8 und 11 U/min“) war
  in der Richtung richtig (kleine Rampenschritte), im Mechanismus falsch.
  Die damals „exakt passenden“ Zahlen passen zum neuen Modell genauso.
- KM-1 B, EK-1 und die Stellprobe sind unter diesem Antriebsverhalten nicht
  fair geprüft worden.

**Vorhersage des Modells für 100 ms Anfahrzeit** (nicht gemessen): Die
Nav2-Rampe auf 0,10 m/s ist nach etwa 2,3 s voll erreicht (statt nach fast
einer Minute), die Drehrampe ebenso; die Rückfahrt in der Langsam-Zone
schafft 0,3 m in etwa 21 s. Bekannter Nachteil aus dem August: Bei einem
**Sprung** (Steuerkreuz, Werkzeuge) ruckt der hohe Aufbau mit 100 ms wieder.
Unter Nav2 gibt es keine großen Sprünge nach oben, außer beim Verlassen der
Langsam-Zone (0,03 → 0,10 m/s).

**Mögliche Wege (Entscheidung offen):**

1. **Messfahrt AT-2 mit 100 ms** (Startargument `hwt601_accel_ms:=100`,
   seit 10.10.2026 als Laborvergleich 100–2000 vorgesehen; keine
   Codeänderung): dieselbe Probe, aber nur mit Rampen wie unter Nav2, dazu
   die langsame Rückfahrt und eine Stufe wie beim Verlassen der
   Langsam-Zone. Zeigt, ob die Vorhersage stimmt und ob der Aufbau dabei
   ruhig bleibt. Danach die Stellprobe mit dieser einen Änderung.
2. **Treiber rechnet die Anfahrzeit je Änderung selbst** (gleiche sanfte
   Beschleunigung bei Sprung und Rampe): die gründlichere Lösung, aber eine
   Codeänderung an der Motorsteuerung mit mehr Buszugriffen; eigener Schritt
   mit eigener Prüfung, mindestens eine Runde länger.

Empfohlen ist Weg 1 als nächster einzelner Schritt (MASTERPLAN §9 Regel 1:
eine Änderung je Realtest); Weg 2 bleibt möglich, falls das Rucken stört.
AT-1b [archiviert](archive/20261115-at1b-ausgewertet/README.md).

**Entscheidung des Projektinhabers (15.11.2026):** Mit Controller und
Steuerkreuz wird so gut wie nicht mehr gefahren; die Lösung soll der
autonomen Navigation dienen. Daraus der Zielzustand: **eine Rampe statt
zwei.** Das sanfte Anfahren und Bremsen macht allein Nav2 (Glätter), der
Antrieb folgt dem Befehl möglichst direkt. Freigegeben ist Weg 1 als
Messfahrt **AT-2** ([Auftrag](AGENTENAUFTRAG.md)): Stackstart mit
`hwt601_accel_ms:=100`, direkt an der Basis, zwei Proben.

**Werkzeug für AT-2** (`antriebsprobe.py --topic /cmd_vel --freigabe AT-2`,
14 Tests, dazu 9 Tests des Modells): Programm C, G, R, E, S; jede Änderung
ist begrenzt wie im Glätter (+0,12/−0,30 m/s², +0,30/−0,60 rad/s²), auch
auf den Rückwegen; Sprünge aus dem Stand sind mit `AT-2` gesperrt. Urteil
`antrieb_folgt_rampen`: `ja`, wenn alle sechs Rampen-Abschnitte zwischen
0,8 und 1,2 liegen.

**Trockenlauf 15.11.** gegen eine nachgebildete Kette (Glätter-Nullen,
Kollisionsmonitor, Basis), deren Antrieb nach dem Modell rechnet; drei
Fälle, alle ohne Abbruch und ohne fremde Nachrichten:

| Fall | Ergebnis |
|---|---|
| AT-1b-Programm (A, C, E), 2000 ms | wie die echte Messung: A 1,00; C 0,11 (0,002 → 0,012 m/s); E 0,11 |
| AT-2-Programm, 2000 ms | `nein`: C 0,11; G oben 0,06, wieder 0,56; R 0,17; E 0,11; Rückfahrt 0,012 m |
| AT-2-Programm, 100 ms | `ja`: alle sechs Abschnitte 0,99–1,00; Wege C 0,52 m, G 0,59 m, R −0,11 m, S 0,51 m; Drehung 73°; Rückwege enden auf 2 mm am Ausgangspunkt |

Der Trockenlauf prüft das Werkzeug und das Urteil gegen das Modell; ob der
echte Antrieb sich bei 100 ms so verhält, zeigt erst AT-2. **Der Auftrag
AT-2 ist damit ausführbar.**

**Offen nach AT-2, je nach Ergebnis:** 100 ms als Standard für den
selbstheilenden Betrieb (Entscheidung des Projektinhabers), dann die
Stellprobe mit dieser einen Änderung. Die Bremszeit (400 ms) wird in AT-2
nicht geändert; ob der Antrieb Bremsrampen folgt, zeigt Abschnitt G unten.

**Nächster Schritt:** AT-2-Bericht auswerten.

## 15.11.2026 – AT-1 ausgewertet: Messung gestört, die Frage zum Antrieb ist offen

Bericht `~/selbstheilung_jetson_bericht_at1.md` (Jetson, Klon `2c3aafb`,
Release `selbstheilung-sh8b-20261114_1643` ohne Build, Werkzeugtest 8
bestanden, Vorprüfung 59× OK). Ein scharfer Stackstart, **keine Mission**,
zwei Werkzeugläufe, kein Abbruch, keine Berührung, kein Eingriff; Amadeus
stand danach am Ausgangspunkt. Christopher zu beiden Proben: „Überall
gekrochen“.

**Das Urteil `unklar` beider Proben ist nicht verwertbar.** Ursache, vom
Jetson-Agenten rein lesend gemessen:

- Der `velocity_smoother` sendet im laufenden Stack **auch ohne Mission**
  mit 20,1 Hz Nullbefehle auf `/cmd_vel_smoothed` (161 von 161 Nachrichten
  in 8 s null). Gespeist wird er vom Fahrtor (`cmd_vel_mission_gate`), das
  ohne freigegebene Mission in festem Takt Null ausgibt (aus dem Code
  gelesen).
- Das Werkzeug sendete auf dasselbe Topic. Der Kollisionsmonitor reichte
  beides weiter; an der Basis kamen **Sollwert und Halt im Wechsel** an
  (`an_der_basis` in jeder Phase etwa die Hälfte des Sollwerts; in den
  `CMD`-Zeilen wechseln `v=+0.100` und `v=+0.000`).
- Ein Nullbefehl ist für die Basis ein Stopp. Der Antrieb fuhr also etwa 20
  Mal je Sekunde an und hielt wieder.

| Phase | `ist_zu_soll` Probe 1 / 2 | an der Basis | Soll |
|---|---|---|---|
| A Sprung vorwärts | 0,13 / 0,15 | 0,049 | 0,10 m/s |
| B zweite Stufe | 0,08 / 0,11 | 0,049 | 0,10 m/s |
| C Rampe | 0,08 / 0,09 | 0,049 | 0,10 m/s |
| F zweite Stufe | 0,09 / 0,12 | 0,015 | 0,03 m/s |
| D Sprung drehen | 0,08 / 0,16 | 0,122 | 0,25 rad/s |
| E Rampe drehen | 0,10 / 0,15 | 0,125 | 0,25 rad/s |

**Der Fehler lag im Auftrag, nicht in der Ausführung.** Die Cloud-Sitzung
hatte angenommen, der Glätter schweige ohne Mission, und das nicht
gemessen. Der Trockenlauf vom 14.11. bildete nur den Antrieb nach, nicht
die Kette davor, und konnte den Fehler deshalb nicht zeigen. Der
Jetson-Agent hat die Störung nach Probe 1 gefunden, belegt und vor Probe 2
gemeldet.

**Was belegt ist:**

1. Wechseln Sollwert und Halt an der Basis mit je 20 Hz, kriecht Amadeus mit
   8–16 % des Sollwerts, gleich bei Sprung, Treppe und Rampe.
2. Ohne Mission steht auf `/cmd_vel` nichts (0 Nachrichten in 8 s und in
   5 s): Der Kollisionsmonitor schweigt, solange nur Nullen ankommen
   (`stop_pub_timeout` 2 s).
3. Die Schutzgrenzen des Werkzeugs hielten: größter Weg 0,070 m, Rückwege
   endeten 2–5 cm vor dem Ausgangspunkt.

**Was nicht belegt ist:**

1. Ob der Antrieb bei einem gleichmäßigen Sollwert ohne Zwischenhalt richtig
   fährt. Die Hypothese „Sollwert nur beim Anfahren“ ist **weder bestätigt
   noch widerlegt**.
2. Ob ein solcher Wechsel auch in echten Fahrten vorkommt. Dagegen spricht
   der Bestand: In den sechs Fahrten aus Anhang Z waren nur 1–2 % der
   `CMD`-Zeilen während der Anläufe null; ein Wechsel mit je 20 Hz hätte
   etwa die Hälfte ergeben. In einer Fahrt speist der Glätter das Topic
   allein.

**Aus dem Treibercode (nur gelesen):** Die Änderung vom 16.08.2026
(Startimpuls nur noch beim Anfahren) wurde damals mit einem **konstanten**
Sollwert geprüft (0,12 rad/s). Ob der Antrieb einen während der Fahrt
geänderten Sollwert ohne Startimpuls übernimmt, wurde nie gemessen. Genau
das soll die Probe zeigen; die Frage bleibt die richtige.

**Korrektur am Werkzeug** (`tools/kartierung/antriebsprobe.py`, 12 Tests):

- Vor dem ersten eigenen Befehl hört es 2 s auf sein Topic. Sendet dort
  jemand, fährt es nicht.
- Tauchen während der Fahrt mehr als fünf fremde Nachrichten auf, bricht es
  mit Nullbefehlen ab.
- Kommt an der Basis im Messabschnitt nicht der gesendete Sollwert an
  (Abweichung über 15 %), lautet das Urteil `gestoert` statt `unklar`.
- Der direkte Weg zur Basis (`--topic /cmd_vel`) verlangt ein eigenes
  Freigabewort (`AT-1b`); mit `AT-1` fährt das Werkzeug dort nicht.

**Trockenlauf 15.11.** gegen eine nachgebildete Kette (Glätter mit
20-Hz-Nullen, Kollisionsmonitor mit 2 s Schweigefrist, Basis mit Stopp bei
Null), fünf Fälle, alle wie erwartet:

| Fall | Topic | Ergebnis |
|---|---|---|
| wie AT-1 (Glätter sendet von Anfang an) | `/cmd_vel_smoothed` | fährt nicht: „fremder Sender“, 40 Nachrichten in 2 s |
| Glätter beginnt mitten in der Probe | `/cmd_vel_smoothed` | Abbruch nach 6 fremden Nachrichten (0,3 s) |
| Glätter sendet, Antrieb gesund | `/cmd_vel` | `widerlegt`, an der Basis genau der Sollwert, 0 fremde Nachrichten |
| Glätter sendet, Antrieb bleibt beim ersten Sollwert | `/cmd_vel` | `bestaetigt` (Sprung 0,99, Rampe 0,06, Treppe 0,20) |
| ohne Glätter, Antrieb gesund | `/cmd_vel_smoothed` | `widerlegt` |

Zusätzlich schreibt das Werkzeug je Phase das Tempo je Sekunde mit
(`tempo_je_s`); daran ist zu sehen, ob der Antrieb einem Sollwert folgt oder
auf einem Wert stehen bleibt. Der Trockenlauf prüft das Werkzeug, nicht den
echten Stack.

**Wie die Wiederholung ungestört wird:** Im laufenden Stack ist nur
`/cmd_vel` frei, der Eingang der Basis hinter dem Kollisionsmonitor. Dort
sendet ohne Mission niemand. Befehle dort **umgehen die Nahbereichsbremse**
(VL53/Kollisionsmonitor). Es bleiben: freie Fläche, höchstens 0,10 m/s und
0,9 m Weg, Abbruch über Odometrie und Not-Aus-Zustand, Watchdog der Basis
(0,25 s), Christopher mit der Hand am Not-Aus. Geprüfte Alternativen:

- Stack ohne Nav2 (`slam_lidar`, `vl53_near_field` und `safety_monitor`
  einzeln): Der Kollisionsmonitor braucht die Kontur aus der lokalen
  Kostenkarte, die ohne Nav2 fehlt. Eine nie benutzte Startkombination,
  verworfen.
- Glätter oder Fahrtor zum Schweigen bringen: wäre eine Verhaltensänderung
  am Stack vor einer Messung (MASTERPLAN §9 Regel 1), verworfen.

Das ist eine andere Schutzlage als die am 14.11. freigegebene und braucht
eine eigene Freigabe (AGENTS §2.1). AT-1
[archiviert](archive/20261115-at1-ausgewertet/README.md).

**Entscheidung des Projektinhabers (15.11.2026): Wiederholung direkt an der
Basis.** Zur Wahl standen außerdem „Bremse bleibt aktiv“ (zuerst eine
Softwareänderung, eine Runde später) und „nur mitlesen bei normaler Fahrt“
(weniger eindeutig). Auftrag [AT-1b](AGENTENAUFTRAG.md): derselbe
Stackstart ohne Mission, vor der ersten Probe zählt der Agent rein lesend
die Nachrichten auf `/cmd_vel` (erwartet 0), dann zwei Proben mit
`antriebsprobe.py --topic /cmd_vel --freigabe AT-1b`. Urteile vorab
festgelegt: `bestaetigt`, `widerlegt`, `unklar`, `gestoert`.

**Einordnung nach MASTERPLAN §9:** kein Schritt zurück im Fahrplan, aber
ein verlorener Messtermin. KM-1 B, Schritt 2 und die Stellprobe warten
unverändert auf die Antwort zum Antrieb.

**Nächster Schritt:** AT-1b-Bericht auswerten.

## 14.11.2026 (nachts) – SH-8b ausgewertet: nicht bestanden; die Rückfahrten zeigen die Ursache im Motortreiber

Bericht `~/selbstheilung_jetson_bericht_sh8b.md` (Jetson, Release
`selbstheilung-sh8b-20261114_1643`, HEAD `734f259`, Build 176 s, 197 Tests
bestanden, Vorprüfung je Probe 63× OK, Bereich F ohne Befund). Drei Proben
mit Mission, keine Berührung, kein Eingriff, kein „process has died“.

| Probe | Urteil | größte Entfernung | Ende | Rückfahrten (30,1 s lang −1,5 cm/s befohlen) | SH-8 zum Vergleich |
|---|---|---|---|---|---|
| s3a Mülleimer | `nicht_befreit` | 0,483 m | 6-min-Fenster | 0,151 m und 0,215 m | `nicht_befreit` (0,258 m) |
| s2a Ecke | `nicht_befreit` | 0,206 m | „Hilfe benötigt“ nach etwa 3 min | 0,151 m | `befreit` |
| s1a Garderobe | `nicht_befreit` | 0,151 m | „Hilfe benötigt“ nach etwa 2 min | 0,151 m | `befreit` (mit 3 cm) |

**Urteil nach A7: nicht bestanden**; s3b, s2b, s1b und Teil B entfielen.
Christopher sah „Zurück, gedreht, weg“ (Mülleimer), „zurück und dann um 90
Grad gedreht“ (Ecke), „Zurück, dann gestanden“ (Garderobe). Das Kriterium
(0,5 m weg) wurde an den Mülleimern um 1,7 cm verfehlt.

**Was belegt ist:**

1. **KM-1 B tut, was es soll:** kein einziges „approach“ mehr (SH-8 s3a: bei
   jedem Anlauf), kein Eigenecho, keine tödliche Zelle im Gehäuse. An den
   Mülleimern kam Amadeus fast frei.
2. **An Ecke und Garderobe schlechter als SH-8:** Nach der einen Rückfahrt
   stand Amadeus nur 0,151 m weiter hinten. Der Regler verweigerte danach
   jeden Anlauf nach etwa 11 s („detected collision ahead“ 744×), weil die
   Hindernisse jetzt in der lokalen Karte stehen bleiben und für eine
   Drehung noch zu nah waren (Garderobe: tödliche Zellen 4 cm neben der
   linken Seite). Nach acht Fehlschlägen kam „Hilfe benötigt“. Vor KM-1 B
   löschte die Karte diese Zellen, und Amadeus drehte sich dicht am
   Hindernis frei.
3. **Die Rückfahrt ist der Engpass:** befohlen 0,3 m, an der Basis 30,1 s
   lang −1,5 cm/s (603 Befehle, das wären 0,45 m), laut Odometrie
   **dreimal genau 0,151 m und einmal 0,215 m**.

**Die Zahlen aus Punkt 3 passen genau zu einer Ursache im Motortreiber**
(aus Code und Zahlen abgeleitet, am Antrieb noch nicht gemessen):

- `base_hardware` sendet den Startimpuls (Register `0x0027`) seit dem
  16.08.2026 nur beim Übergang Stillstand → Fahrt. Spätere Sollwerte
  schreibt es ohne Startimpuls ins Drehzahlregister.
- Übernimmt der Antrieb die Drehzahl nur mit dem Startimpuls, dann fährt er
  bis zum nächsten Halt mit dem **ersten** Sollwert nach dem Stillstand.
  Unter Nav2 ist das eine kleine Stufe der Anfahrrampe des Glätters
  (0,12 m/s² bei 20 Hz, also 0,6 cm/s je Schritt, in der Langsam-Zone 30 %
  davon).
- Rückfahrt: Die Stufen entsprechen 3, 6, **8**, **11**, 14 … U/min am
  Motor. 8 U/min ergeben in 30,1 s 0,157 m (gemessen 0,151 m), 11 U/min
  0,216 m (gemessen 0,215 m).
- Vorwärts: Die zweite und dritte Stufe ergeben 1,2 und 1,8 cm/s; gemessen
  wurden in sechs Fahrten 1,3–1,7 cm/s, unabhängig vom Sollwert.
- Tests mit sofort vollem Sollwert (Streckentest, Steuerkreuz) fuhren
  richtig; deshalb fiel es bei der Kalibrierung nicht auf.

Trifft das zu, erklärt es das Kriechtempo, die zu kurzen Rückfahrten, die
150-s-Abbrüche und den unzuverlässigen Raumwechsel gemeinsam, und KM-1 B
scheiterte an Ecke und Garderobe nur an der halben Rückfahrstrecke.

**Einordnung nach MASTERPLAN §9:** Regel 4 (Scheitern führt zuerst zu
Daten) ist mit diesem Bericht und Anhang Z erfüllt. KM-1 B ist **nicht
bestätigt** und bleibt im Code, bis der Antrieb geklärt ist (Rückfall am
Jetson: `SH_REL` auf den SH-8-Release). Das aktive Problem „sitzt fest“ und
Schritt 2 hängen jetzt an derselben offenen Frage. SH-8b
[archiviert](archive/20261114-sh8b-ausgewertet/README.md).

**Entscheidung des Projektinhabers (14.11.2026): Antriebsprobe AT-1.** Nur
Messung, keine Änderung: auf freier Fläche mit festen Sollwertfolgen fahren
(Sprung, Treppe, Rampe wie Nav2, Drehen) und Sollwert gegen Encoder-Tempo
aufzeichnen ([Auftrag](AGENTENAUFTRAG.md), Werkzeug
`tools/kartierung/antriebsprobe.py`, `fcf95fc`; 8 Tests und ein Trockenlauf
gegen einen nachgebildeten Antrieb in beiden Fällen). Sie entscheidet, ob
der Startimpuls die Ursache ist. Erst danach folgt eine Korrektur im
Motortreiber als eigener Schritt (AGENTS §2.7), dann dieselbe Stellprobe.

**Nächster Schritt:** AT-1-Bericht auswerten.

## 14.11.2026 (spät) – Anhang Z, zweiter Lauf: Die Fahrbefehle stimmen, der Antrieb setzt nur ein Fünftel um

Bericht `~/selbstheilung_anlaeufe_bericht_2.md` (Jetson 17:58, Klon
`bbc5c6a`, nur lesend). Neu ausgewertet sind die Fahrbefehle, die an der
Basis ankamen (`CMD`-Zeilen, etwa einer je Sekunde), jeweils nur innerhalb
der Anläufe. Die gefahrene Strecke laut Odometrie stammt aus den früheren
Fahrtprotokollen (Abschnitte SH-6 und SH-7).

| Fahrt | vorwärts befohlen | Median v befohlen | befohlener Weg | gefahren (Odometrie) | umgesetzt | Ist-Tempo beim Vorwärtsfahren | Drehen (Anteil, Median w) | ohne Befehl |
|---|---|---|---|---|---|---|---|---|
| SH-6 Fahrt 1 | 565 s | 6,9 cm/s | 38,4 m | 8,0 m | 21 % | 1,4 cm/s | 50 %, 0,120 rad/s | 1 % |
| SH-6 Fahrt 2 | 518 s | 6,4 cm/s | 31,2 m | 6,8 m | 22 % | 1,3 cm/s | 53 %, 0,091 rad/s | 1 % |
| SH-6 Fahrt 3 | 439 s | 7,5 cm/s | 31,2 m | 6,4 m | 21 % | 1,5 cm/s | 38 %, 0,043 rad/s | 20 % |
| SH-7 Fahrt 1 | 317 s | 7,1 cm/s | 23,4 m | 5,3 m | 23 % | 1,7 cm/s | 77 %, 0,035 rad/s | 0 % |
| SH-7 Fahrt 2 | 950 s | 10,1 cm/s | 91,4 m | 14,2 m | 16 % | 1,5 cm/s | 38 %, 0,095 rad/s | 6 % |
| SH-7 Fahrt 3 | 903 s | 10,1 cm/s | 88,1 m | 14,8 m | 17 % | 1,6 cm/s | 41 %, 0,043 rad/s | 7 % |

**Was belegt ist:**

1. **Die Befehle sind nicht das Problem.** An der Basis kamen beim
   Vorwärtsfahren im Median 6,4–10,1 cm/s an. Befehle fehlten nur 0–7 % der
   Zeit (einmal 20 %, dort wartete der Explorer). Die Vermutung „Regler
   befiehlt zu wenig“ und die Vermutung „Watchdog, weil Befehle ausbleiben“
   sind damit für das Vorwärtsfahren widerlegt.
2. **Gefahren wurde nur 16–23 % des befohlenen Wegs.** Das Ist-Tempo beim
   Vorwärtsfahren lag in allen sechs Fahrten bei 1,3–1,7 cm/s, fast
   unabhängig davon, ob 6,4 oder 10,1 cm/s befohlen waren. Das sieht nach
   einer Obergrenze oder nach ständigem Neuanfahren aus, nicht nach einem
   festen Faktor. Ein Einzelfall zeigt es rein: 2,36 m geradeaus ohne
   Drehung, 125 s lang im Mittel 11,5 cm/s befohlen, gefahren 1,9 cm/s
   (SH-7 Fahrt 2).
3. **Gedreht wird 38–77 % der Zeit, und nur sehr langsam befohlen:** Median
   0,035–0,12 rad/s statt 0,20 bzw. 0,25 rad/s. Wahrscheinlicher Mechanismus
   (aus dem Code, nicht gemessen): Der Regler darf die Drehrate je Takt nur
   um 0,1 rad/s über die **gemessene** Drehrate heben; dreht der Roboter
   kaum, bleibt der Befehl bei etwa 0,1 rad/s hängen, in der Langsam-Zone
   bei 0,03 rad/s. In SH-7 Fahrt 1 bestanden fünf 150-s-Anläufe fast nur aus
   solchen Drehbefehlen.
4. Frühere Einzelmessungen passen dazu und wurden jeweils der Anfahrrampe
   zugeschrieben: 14.08. (1-s-Impuls 0,044 m statt 0,12 m), 18.08. (0,085 m
   in 20 s in der Langsam-Zone), 15 s Anfahren für 0,19 m, SH-8-Rückfahrten
   (etwa 0,15 m statt 0,45 m). Eine 2-s-Rampe erklärt das über Minuten nicht.

**Bewertung:** Zwischen `/cmd_vel` und den Rädern geht rund vier Fünftel des
Tempos verloren. Das ist der größte bekannte Hebel für Schritt 2 (Zeit im
Raum, Nachbarraum erreichen) und betrifft wahrscheinlich auch das aktive
Problem (Rückfahrten kommen zu kurz, „Failed to make progress“). **Die
Ursache ist nicht gemessen.** Kandidaten: eine Drehzahlgrenze oder Einheit
im Antrieb, häufige Stopps im Motortreiber (jeder Nullbefehl und jede
gesperrte Encoder-Zeitwache ist ein Stopp, danach neue Anfahrrampe ab
5 U/min), pulsierende Befehle. Das gehört zur Motorsteuerung und wird
getrennt gemessen und getrennt geändert (AGENTS §2.7).

**Vorschlag, noch nicht beauftragt:** eine kurze **Fahrprobe** nur zum
Messen: geradeaus und Drehen auf freier Fläche mit festen Sollwerten, dabei
Sollwert, Encoder-Tempo und Zustand des Motortreibers mitschreiben. Sie
braucht die Freigabe des Projektinhabers und wird erst nach der Auswertung
von SH-8b beauftragt.

**SH-8b in diesen Daten** (der Bericht fehlt hier weiter): Garderobe (s1a):
in allen acht Anläufen kam **kein einziger Fahrbefehl** an der Basis an
(99 % ohne Befehl). Ecke (s2a): sieben Anläufe ohne Befehl, im achten 23 s
vorwärts mit 1,4 cm/s und 38 s Drehen. Mülleimer (s3a): 248 s Drehbefehle
mit 0,039 rad/s, 37 s vorwärts, kein Ziel erreicht.

**Nächster Schritt:** SH-8b-Bericht auswerten; Entscheidung des
Projektinhabers zur Fahrprobe.

## 14.11.2026 (abends) – Anhang Z ausgewertet: Amadeus kommt real nur mit etwa 1 cm/s voran

Bericht `~/selbstheilung_anlaeufe_bericht.md` (Jetson, Klon `734f259`, nur
lesend auf vorhandene `launch.log`, kein Stack, keine Fahrt). Ausgewertet:
die sechs vollen Fahrten aus SH-6 (ein Raum) und SH-7 (zwei Räume) sowie
drei SH-8b-Proben. Dauer der Fahrten aus den früheren Auswertungen.

| Fahrt | Anläufe | erreicht | erreichte Ziele: Zeit / Luftlinie / effektiv | 150-s-Abbrüche (Anteil der Fahrzeit) | Abbrüche unter 12 s |
|---|---|---|---|---|---|
| SH-6 Fahrt 1 | 16 | 8 | 504 s / 4,40 m / 0,87 cm/s | 3 (38 %) | 2 |
| SH-6 Fahrt 2 | 17 | 10 | 496 s / 4,13 m / 0,83 cm/s | 4 (50 %) | 0 |
| SH-6 Fahrt 3 | 22 | 10 | 611 s / 5,09 m / 0,83 cm/s | 1 (13 %) | 6 |
| SH-7 Fahrt 1 | 14 | 5 | 338 s / 2,78 m / 0,82 cm/s | 7 (69 %) | 0 |
| SH-7 Fahrt 2 | 33 | 12 | 783 s / 8,46 m / 1,08 cm/s | 4 (32 %) | 13 |
| SH-7 Fahrt 3 | 33 | 7 | 334 s / 3,79 m / 1,13 cm/s | 7 (55 %) | 15 |

Alle 135 Anläufe nach Entfernung des Ziels:

| Ziel entfernt | Anläufe | erreicht | Median Dauer (erreicht) | 150-s-Abbrüche |
|---|---|---|---|---|
| bis 0,3 m | 17 | 14 (82 %) | 20 s | 0 |
| 0,3–0,6 m | 22 | 19 (86 %) | 51 s | 0 |
| 0,6–1,0 m | 28 | 13 (46 %) | 84 s | 3 |
| 1,0–1,5 m | 26 | 4 (15 %) | 117 s | 7 |
| über 1,5 m | 42 | **2 (5 %)** | 140 s | 16 |

**Was belegt ist:**

1. **Effektiv 0,8–1,1 cm/s** zum erreichten Ziel, in allen sechs Fahrten
   fast gleich, bei befohlenen 10 cm/s (SH-6) und 13,5 cm/s (SH-7), also
   rund 8 % des Sollwerts. Die Tempoerhöhung vom 05.11. kam an (+30 %), am
   Verhältnis änderte sie nichts.
2. **Ziele über 1,5 m erreicht Amadeus fast nie** (2 von 42), ab 1 m nur
   noch jedes siebte. Bei 1 cm/s braucht 1,5 m genau die 150 s, nach denen
   ein Anlauf abgebrochen wird. Die 150-s-Abbrüche kosten 13–69 % der
   Fahrzeit (Median 44 %).
3. Das erklärt zwei Beobachtungen auf einmal: das **lange Umherfahren im
   Raum** (erreichbar sind praktisch nur Ziele im Umkreis von etwa 1 m, also
   viele kleine Sprünge) und den **unzuverlässigen Raumwechsel** (die Tür
   liegt meist weiter weg).
4. Die Langsam-Zone ist nicht die Hauptursache: Sie war nur 14–27 % der Zeit
   aktiv, „approach“ 0–10 %.

**Folgen:**

- **Der SH-9-Vorschlag vom Vormittag ruht.** Der Lückenfilter (Teil B)
  wählt weniger und weiter entfernte Ziele; in der Simulation ist das der
  Gewinn, real würden gerade diese Ziele bei 1 cm/s meist an der
  150-s-Grenze scheitern. Die Simulation ist je Anlauf 4- bis 5-mal
  schneller als der Roboter; ihr Ergebnis überträgt sich erst, wenn die
  Ursache der realen Langsamkeit bekannt ist.
- **Nächste Messung, wieder ohne Fahrt** (`23317fe`): Das Auswertewerkzeug
  liest aus denselben Logs jetzt auch die Fahrbefehle der Basis (etwa einer
  je Sekunde). Das trennt drei Möglichkeiten: Die Basis sollte so langsam
  fahren (Regler, Tempolimits); sie drehte die meiste Zeit; oder es kamen
  zeitweise keine Befehle an (Watchdog 0,25 s, danach Neustart mit
  2-s-Anfahrrampe). Anhang Z einmal erneut ausführen.
- Erst danach wird entschieden, was Schritt 2 auf dem Roboter prüft.

**SH-8b (nur was Anhang Z zeigt; der SH-8b-Bericht liegt hier noch nicht
vor):** Drei Proben mit Mission, Teil B nicht gefahren. Garderobe (s1a):
acht Anläufe, alle nach 8,7–8,8 s gescheitert. Ecke (s2a): acht Anläufe,
sieben nach 8,7–9,1 s gescheitert, einer nach 70 s. Mülleimer (s3a): drei
Anläufe (62 s gescheitert, 150 s und 86 s abgebrochen). Kein Anlauf
erreichte sein Ziel. Urteil und Ursache erst mit dem SH-8b-Bericht
(MASTERPLAN §9 Regel 4).

**Nächster Schritt:** SH-8b-Bericht und den erneuten Anhang Z auswerten.

## 14.11.2026 – Schritt 2 in der Simulation vorbereitet: wohin die Zeit geht, EK-1 neu gefasst

**Entscheidung des Projektinhabers (14.11.2026):** Während SH-8b läuft, wird
der nächste Test nach dem Masterplan vorbereitet (MASTERPLAN §9 Regel 7,
Nachtrag). Ziel von Schritt 2: die Zeit im Raum deutlich verkürzen und den
Nachbarraum zuverlässig finden, bevor alle Räume offen sind. Auf den Roboter
geht davon nichts, bevor SH-8b ausgewertet ist; alles Neue ist im Code
ausgeschaltet, die 197 gezielten Tests von SH-8b sind unverändert.

**1. Messung aus den echten SH-8-Daten** (26 Anläufe aus sechs Proben, Start
jeweils dicht an einem Hindernis): Ziel im Median 0,49 m entfernt, 14 von 26
näher als 0,5 m; ein erreichtes Ziel kostete im Median 70 s (9–112 s),
effektiv 0,003–0,018 m/s. SH-6 passt dazu: 8–10 Ziele und 6,4–8,0 m in
20 min, im Raum nie fertig. Die Zeit geht also in **viele kurze Anläufe**,
von denen jeder lange dauert. Neues Werkzeug (`c6da3d4`, nur lesend):
`tools/kartierung/selbstheilung_anlaeufe.py` rechnet das aus jedem
`launch.log`; Anhang Z im Auftrag wendet es auf die sechs vollen Fahrten aus
SH-6 und SH-7 an (ohne Fahrt).

**2. Simulation ehrlicher gemacht** (`2da300d`): möblierter Laborraum
4,3 × 4,3 m mit 0,80-m-Tür und Flur 1,5 × 4 m mit Garderobe (Maße nach
SH-6/SH-7, Möbel angenommen: Regal, Werkbank, Schrank, Stuhl, Stativ,
niedrig: zwei Mülleimer, Kiste, Hocker, Stuhlsitz), träger Antrieb nach der
Messung vom 14.08. (1-s-Impuls 0,0439 m, Modell innerhalb 10 %),
LiDAR-Messrauschen 1 cm, Odometriefehler. Gemessen je Raum: Zeit bis
85/90/95 %, erstes Betreten des Flurs, alle Anläufe.

**3. Was der heutige Stand in dieser Welt tut** (vier Läufe, einer ohne
Rauschen): Der Laborraum ist nach **20–40 s zu 90 %** kartiert, allein aus
dem ersten Blick des LiDAR; das bestätigt die Beobachtung des
Projektinhabers vom 09.11. Trotzdem dauert die Fahrt 455–742 s und endet als
Teilkarte, mit 13–14 Anläufen. Die Zeit nach 95 % der Endfläche (Leerlauf)
beträgt 274–559 s: Amadeus fährt schmale Restlücken an (Schattenkeile,
Streifen vor Wänden), einmal mit drei 150-s-Anläufen ohne Ziel (75 % der
Fahrzeit). In **allen vier Läufen berührte das Gehäuse dabei spät (318–559 s)
ein niedriges Möbel** (Kiste, Hocker), die bekannte Grenze niedriger
Gegenstände.

**4. Neuer Teil B „nur Lücken, in die Amadeus passt“** (`3b14515`,
`self_healing_gap_depth_m`, Standard 0 = aus): Eine Frontier zählt nur an
Unbekanntem, das mindestens 0,5 m breit ist. Schmale Keile, Strahllücken,
Löcher in Wänden und Streifen vor Wänden werden nicht angefahren und halten
das Ende nicht auf. Das ersetzt das Zeitfenster-Ende C durch ein
geometrisches Ende.

| Stand | Lauf | Ende | Dauer | Anläufe | Leerlauf nach 95 % | Flur betreten | Abdeckung | Gehäuse berührt |
|---|---|---|---|---|---|---|---|---|
| heute | 1 | Teilkarte | 742 s | 14 | 559 s | 181 s | 0,979 | ja, 559 s |
| heute | 2 | Teilkarte | 513 s | 13 | 392 s | 119 s | 0,977 | ja, 460 s |
| heute | 3 | Teilkarte | 455 s | 14 | 274 s | 167 s | 0,977 | ja, 452 s |
| mit B | 1 | **vollständig** | 245 s | 5 | 94 s | 147 s | 0,979 | nein (2,5 cm) |
| mit B | 2 | **vollständig** | 282 s | 5 | 101 s | 174 s | 0,974 | nein |
| mit B | 3 | **Hilfe benötigt** | 272 s | 12 | – | nie | 0,798 | ja, 145 s |
| A + B + D | 1 | **vollständig** | 258 s | 3 | 15 s | nie (Flur von der Tür aus zu 85 % kartiert) | 0,946 | nein |
| A + B + D | 3 | Teilkarte | 156 s | 8 | 66 s | 74 s | 0,968 | **ja, 117 s: Heck am Türpfosten bei einer Rückfahrt** |
| A + C + D (EK-1 vom 09.11., ohne B) | 1 | **Hilfe benötigt** | 231 s | 12 | – | nie | 0,791 | ja, 89 s (Kiste) |

Lauf 1 und 2: gleicher Startplatz, anderes Messrauschen; Lauf 3: anderer
Startplatz und andere Blickrichtung.

- **B halbiert bis drittelt die Fahrzeit bei gleicher Abdeckung** und senkt
  die Anläufe von 13–14 auf 5; die Kriterien E1, E3 und E4 vom 09.11. sind in
  den beiden vollständigen Läufen erfüllt (Leerlauf 94–101 s gegen Median
  392 s). Weil die Fahrt früher endet, gab es dort auch keine Berührung.
- **Der dritte B-Lauf scheiterte, aber nicht an B:** Amadeus fuhr schräg an
  die niedrige Kiste heran, die Gehäuseecke berührte sie (VL53 sehen nur nach
  vorn), danach hielt der Kollisionsmonitor im Modus „approach“ wieder alles
  fest, und acht Fehlschläge in rund 70 s führten zu „Hilfe benötigt“. Das
  ist der SH-8-Mechanismus an einem niedrigen Gegenstand; der heutige Stand
  berührte in allen Läufen. Mit weniger Zielen hat die Heilungsleiter aber
  weniger Ausweichziele; das gehört im Realtest beobachtet.
- **A (Schwenk 90° statt Vollkreis) und D (Anlauf nach 45 s ohne Weggewinn
  abbrechen)** sparten im einen Lauf zwei weitere Anläufe. Amadeus erklärte
  die Karte dort für fertig, **ohne in den Flur hineinzufahren**: Von der Tür
  aus sah er 85 % des Flurs, die Reste waren schmaler als 0,5 m. Ob das
  genügt oder ob er jeden Raum betreten soll, ist eine Produktentscheidung.
- **Neu und sicherheitsrelevant (ein Lauf, A + B + D, Lauf 3):** Nach der
  Türdurchfahrt stand Amadeus quer im Türbereich, ein Anlauf scheiterte, und
  die freie Rückfahrt aus AW-1 (0,3 m gerade zurück) schob das **Heck an den
  Türpfosten**. Nach hinten sieht er nichts (Mastschatten des LiDAR, VL53
  nur vorn); die Rückfahrkontur prüft nur gegen die lokale Karte, und dort
  fehlte der 5 cm dicke Pfosten (nächste tödliche Zelle 16 cm entfernt). Die
  Simulationswand ist dünner als eine echte Zarge, der Mechanismus gilt
  trotzdem. Folge: In SH-8b Teil B achtet Christopher besonders auf
  Rückwärtsfahrten in Türnähe (Hinweis im Auftrag); eine Korrektur gehört
  zum aktiven Problem und wird nach den SH-8b-Daten entschieden.
- **EK-1 in der Fassung vom 09.11. (A, C, D ohne B)** endete mit „Hilfe
  benötigt“ nach einer Berührung der Kiste; ohne B bleibt die Zahl der
  Anläufe hoch (12).
- **Grenzen dieser Simulation:** neun Läufe, eine angenommene Möblierung.
  Je Anlauf ist die Simulation 4- bis 5-mal schneller als der echte Roboter
  (1 m in 16 s gegen 70 s); die Ursache ist nicht gemessen. Übertragbar ist
  deshalb vor allem die **Zahl der Anläufe**, nicht die Sekunden.

**Vorschlag für SH-9 (Fahrplan Schritt 2), noch nicht aktiv:** EK-1 in der
Fassung A (Schwenk 90°), **B (Lücken ab 0,5 m)** und D (45 s), ohne C. Zwei
Räume wie SH-8b Teil B, zwei Fahrten. Vorläufige Kriterien, endgültig nach
den SH-8b-Daten: Fahrt endet von selbst in höchstens 15 min; höchstens ein
Drittel der Fahrzeit in nicht erreichten Anläufen; Nachbarraum in der Karte
ganz oder größtenteils (R2); C1–C5 und G1 wie bisher; dazu die Anläufe und
neu die Zeitanteile Stehen, Drehen, Fahren als Messung. Der Auftrag wird
nach der Auswertung von SH-8b geschrieben (ein aktueller Auftrag).

**Nächster Schritt:** SH-8b-Bericht auswerten; danach SH-9 festlegen.

## 13.11.2026 (nachts) – Simulation: Mülleimer-Stellprobe, SH-8-Stand gegen KM-1 B

Nachbau von SH-8 s3a in der Welt v4: Amadeus 5 cm vor zwei 38-cm-Eimern
(29 cm, 10 cm Lücke), die nur die VL53 sehen; der LiDAR liegt real wie in
der Simulation 0,75 m über dem Boden. Drei Startlagen: mittig; 4 cm links,
+4°; 4 cm rechts, −4°, mit Odometrie-Skalenfehler. Manifeste
`tools/simulation/experimente/manifest_stellprobe_muelleimer*.json`,
Vorher-Stand `vorher_sh8_kontur_loescht.yaml` (`e7d38d0`). Experiment, keine
Abnahme. Die Messgröße ist das echte Gehäuse.

| Stand | Startlage | Urteil | 0,5 m weg nach | „approach“ | erste Rückfahrt | Gehäuse berührt |
|---|---|---|---|---|---|---|
| SH-8 | mittig | `nicht_befreit` (0,275 m) | – | 11× | ohne Bewegung | ja, frontal am Eimer |
| SH-8 | links | `nicht_befreit` (0,179 m) | – | 11× | ohne Bewegung | ja |
| SH-8 | rechts, Drift | `nicht_blockiert` | 73 s | 2× | – | ja, nach 9 s bei der Anfangsdrehung |
| KM-1 B | mittig | `befreit` | 118 s | 0 bis dahin | 0,303 m in 20 s | 55 s nach dem Wegkommen |
| KM-1 B | links | `befreit` | 80 s | 0 | 0,304 m in 21 s | etwa 25 s danach |
| KM-1 B | links (Wiederholung) | `befreit` | 80 s | 0 | 0,304 m in 21 s | 25 s danach |
| KM-1 B | rechts, Drift | `befreit` | 64 s | 0 bis dahin | 0,302 m in 21 s | erst nach 5 min |

1. **Der SH-8-Stand bildet die Wirklichkeit nach:** nicht befreit, höchstens
   0,18–0,28 m weg (real 0,258 m), „approach“ hält auch die Rückfahrten fest.
   In der Simulation fuhr er dabei bis ins Gehäuse an den Eimer; real sah
   Christopher „ohne Lücke“, aber keine Berührung.
2. **KM-1 B befreit sich in 4 von 4 Läufen** nach 64–118 s. Jedes Mal hielt
   der Regler vor dem Eimer an, die Rückfahrt lief **vollständig** (0,30 m in
   etwa 21 s, mit Langsam-Zone), kein „approach“ bis zum Wegkommen. Bis
   dahin keine Gehäuseberührung; in drei Läufen blieb das Gehäuse mehr als
   2 cm entfernt, im Drift-Lauf kam es bei der Anfangsdrehung bis auf
   höchstens 2 cm heran (dort hielt der Kollisionsmonitor die Drehung an).
3. **Neu sichtbar, unabhängig von KM-1 B:** In allen vier KM-1-B-Läufen
   berührte das Gehäuse **danach** einen Eimer (25 s bis 5 min nach dem
   Wegkommen), jedes Mal an einer Eimerseite, die die VL53 nie gesehen
   hatten, beim Vorbeifahren oder Drehen. Das ist die bekannte Grenze
   niedriger Gegenstände (VL53 nur nach vorn, LiDAR darüber); der SH-8-Stand
   berührte schon vorher. Real gab es an den Eimern bisher keine Berührung
   (SH-5, SH-8).

**Folgerungen für SH-8b:** KM-1 B geht als einzige Änderung auf den Roboter.
Die Probe wird **sofort** beendet, sobald Amadeus 0,5 m weg ist (Protokoll
5 s Nachlauf, Stopp ohne Verzögerung), denn danach bringt die Fahrt an den
Eimern nichts mehr. **Abweichung von SH-8:** In Teil B (volle Fahrt) stehen
keine Mülleimer im Raum; die Eimer prüft Teil A. Die seitliche Grenze bei
niedrigen Gegenständen ist als eigener Punkt geparkt.

## 13.11.2026 – SH-8 ausgewertet: Stellprobe nicht bestanden, Ursache an den Mülleimern belegt

Bericht `~/selbstheilung_jetson_bericht_sh8.md` (Jetson, Release
`selbstheilung-sh8-20261113_2153`, HEAD `49c013f`, Build 186 s, 182 Tests
bestanden). Aufbau wie beauftragt bestätigt. Sechs Proben mit Mission, keine
Berührung, kein Eingriff, kein `outcome=error`, kein „process has died“.

| Probe | Stelle | Urteil | Zeit bis 0,5 m weg | Heilungen / Rückfahrten | Rückfahrten: Ergebnis |
|---|---|---|---|---|---|
| s3a | Mülleimer, 5 cm | **`nicht_befreit`** (höchstens 0,258 m) | – | 2 / 2 | beide 30 s Zeitgrenze, Kollisionsmonitor „approach“, **kein einziger Fahrbefehl an der Basis** |
| s2a | Ecke, 5 cm | `befreit` | 205,8 s | 1 / 1 | erfolgreich, 26,2 s |
| s2b | Ecke, 5 cm | `befreit` | 237,4 s | 3 / 3 | alle drei 30 s Zeitgrenze, je etwa 29 Befehle mit −0,015 m/s |
| s1a | Garderobe, 5 cm | `nicht_blockiert` | 286,9 s | 0 / 0 | – |
| s1a_nah | Garderobe, 3 cm | `befreit` | 178,6 s | 1 / 1 | 30 s Zeitgrenze, −0,015 m/s |
| s1b | Garderobe, 5 cm | `befreit` | 252,6 s | 1 / 1 | 30 s Zeitgrenze, −0,015 m/s |
| s3b | Mülleimer | entfallen (A7) | | | |

**Urteil nach A7: nicht bestanden** (Mülleimer nie `befreit`). Teil B nicht
gefahren. Christopher an den Mülleimern: „der roboter ist nach rechts gedreht
und direkt vor den mülleimer gefahren ohne lücke dazwischen“; an Ecke und
Garderobe: „Zurück, gedreht, weg“.

**Was belegt ist:**

1. **AW-1 wirkt:** In acht Rückfahrten kein einziges „Collision Ahead“. In
   SH-7 brach jede Rückfahrt an einer anliegenden Kontur nach 1 ms ab; jetzt
   setzt Amadeus an Ecke und Garderobe zurück und kommt frei. **AW-1b wirkt:**
   Nach jeder Rückfahrt kam ein anderes Ziel (s2b: drei verschiedene).
2. **Mülleimer: Lücke (2) real beobachtet.** Das erste Ziel (0,31 | −0,30)
   lag rechts vor dem rechten Eimer; Amadeus drehte nach rechts, fuhr hin und
   meldete es bei (0,19 | −0,19) als erreicht. Ab dem nächsten Anlauf meldete
   der Kollisionsmonitor bei jedem Versuch „approach“: VL53-Punkte lagen
   innerhalb der gepolsterten Kontur, damit setzt Nav2 (Humble wie Jazzy)
   jede Geschwindigkeit auf null, unabhängig von der Richtung. Beide
   Rückfahrten liefen 30 s ohne einen Befehl an der Basis in die Zeitgrenze.
   Lokale Karte am Ende: eine tödliche Zelle 1 cm vor der gepolsterten Front
   (3 cm vor der Frontlinie, ±2,5 cm Raster), davor nur „inscribed“-Zellen.
   Das passt zum DR-1-Befund vom 03.11.: Die Hindernisebenen löschen alles
   unter der gepolsterten Kontur. Was vom Eimer ins 2-cm-Polsterband rückt,
   verschwindet aus der lokalen Karte, und der Regler fährt weiter, bis der
   Kollisionsmonitor festhält. Das ist genau der in der Arbeitsliste
   festgelegte Fall, KM-1 wieder aufzunehmen.
3. **Rückfahrten kommen zu kurz:** Liegt etwas vorn in 0,30–0,80 m, bremst
   die Langsam-Zone (30 %) auch die Rückwärtsfahrt: 0,05 → 0,015 m/s an der
   Basis. Die Zeitgrenze (0,3 m / 0,015 m/s + 10 s = 30 s) ist genau darauf
   gerechnet, trotzdem endeten 7 von 8 an ihr. Nach den Navigatorposen kam
   Amadeus in s2b je Rückfahrt nur etwa 0,15 m weit, in s2a dagegen 0,3 m in
   26 s. Woran der Unterschied liegt, ist offen; die Befreiung gelang trotzdem,
   dauerte aber 3–4 min. Kein Sicherheitsproblem, **geparkt** (ein Problem
   zur Zeit); ab jetzt misst das Fahrtprotokoll die Strecke jeder Rückfahrt.
4. **Auffälligkeiten ohne Bewegung:** Drei Fehlstarts vor s3a, weil der
   LiDAR-Treiber „communication is abnormal“ meldete und sich beendete (nach
   Neustecken behoben); einmal fing „D Quellen“ einen Start ab (Encoder 79 s
   alt). Die Vorprüfung hat beides vor jeder Mission erkannt.

**Folge nach MASTERPLAN §9 Regel 4 und der Entscheidung vom 10.11.:**
gezielte Korrektur KM-1 B (`1f8ecf9`), dann dieselbe Stellprobe (SH-8b).
Simulation dazu im Abschnitt darüber.

## 10.11.2026 (Entscheidung) – Standortbestimmung: ein Problem zur Zeit, SH-8 als Stellprobe

**Frage des Projektinhabers:** Sind wir noch auf dem Zielweg, oder haben wir
uns in Details verheddert?

**Bewertung:** Die Richtung stimmt (einfache Erkundung, Selbstheilung, kein
Raumkonzept, Räume später in der App). Erreicht und real belegt: ein Raum
selbstständig und sicher (15 Laborfahrten ohne Berührung), SLAM-Last gelöst,
Tür zum Nachbarraum grundsätzlich (SH-7: 2 von 3). Offen: zuverlässig ohne
Hilferuf, zügig erkunden, Wohnung, Raumziele. **Verheddert an einem
Problem:** Seit dem 04.11. scheitert es am Festsitzen dicht an Hindernissen;
vier Korrekturen (DR-1 zurückgenommen, Regel, AW-1, AW-1b), fünf Testtage,
kein realer Beleg. Dazu am 09.11. drei Pakete gleichzeitig, zwei
Fehldeutungen der Simulation, und eine ungeeignete Testform (seltenes
Ereignis mit langen Zufallsfahrten).

**Entscheidungen des Projektinhabers (10.11.2026):**
1. **Ein Problem zur Zeit:** nur noch das Festsitzen an Hindernissen; EK-1
   und alles andere geparkt (MASTERPLAN §9 Regel 7).
2. **Stellprobe statt langer Fahrten** (§9 Regel 6): Amadeus wird gezielt an
   die drei bekannten Stellen gestellt (zwei Mülleimer, Ecke, Garderobe; je
   5 cm, je zweimal), die Erkundung startet, gemessen wird bis zu 6 min.
   Urteil je Probe aus dem Fahrtprotokoll (`2409529`): `befreit` (mindestens
   eine Heilung, dann 0,5 m weg), `nicht_blockiert` (einmal mit 3 cm
   wiederholen), `nicht_befreit`. Jede Berührung beendet den Auftrag.
3. **SH-8 umgebaut** ([Auftrag](AGENTENAUFTRAG.md)): Teil A Stellprobe,
   Teil B nur bei Erfolg eine volle Zwei-Raum-Fahrt (C1–C5, G1, R1, R2 wie
   SH-7). Die Fassung mit drei 40-Minuten-Fahrten ist
   [zurückgezogen](archive/20261110-sh8-langfahrten-zurueckgezogen/README.md)
   (nicht ausgeführt). Prüfling bleibt AW-1 plus AW-1b; besteht die
   Stellprobe nicht, folgt der Kandidat KM-1 B und dieselbe Stellprobe.

**Nächster Schritt:** SH-8-Bericht auswerten.

## 10.11.2026 – Simulation KM-1 B und EK-1 abgeschlossen; Standortbestimmung offen

Der Projektinhaber fragt vor SH-8, ob die Arbeit noch auf dem Zielweg ist.
Fakten aus der Simulation vom 09.11. abends (alles Experimente, nichts davon
im Produktprofil):

| Stand | Läufe | bestanden | Dauer (ohne Eimerwelt) | Bemerkung |
|---|---|---|---|---|
| Produkt AW-1b (`d0d1431`, Stand von SH-8) | 7 | **0** | 209–899 s | 2× Gehäuseberührung, 5× festgehalten oder Hilfe |
| KM-1 B (lokale Karte löscht nichts unter der Kontur) | 5 | 3, dazu 1 nur mit offenem Kartenkriterium | 329–535 s | Eimerwelt: Hilfe und Gehäuseberührung (seitlicher Eimer, bekannte Sensorgrenze) |
| KM-1 B plus EK-1 | 5 | 4 | 584–695 s | Eimerwelt: Annäherung auf 0,8 cm, vollständig |

- **KM-1 B** ist die erste Änderung, mit der die Simulation überhaupt
  besteht; nie „approach“, 14 von 16 Rückfahrten erfolgreich. Sie setzt am
  DR-1-Befund vom 03.11. an. **Nicht roboterreif:** Der Mast liegt im
  LiDAR-Sichtfeld; Eigenechos unter der Kontur würden nicht mehr gelöscht.
- **EK-1 verfehlt E3** (Leerlauf halbieren): Median der Zeit nach 95 % der
  Endfläche 427 s gegenüber 244 s ohne EK-1; E1 und E4 erfüllt (Abdeckung
  0,973–0,981; 90 % im Median 29 s später). Die Rundblicke kosten je etwa
  65 s, das „gut genug“-Ende löste nie aus, weil stets eine Lücke ab 0,6 m
  übrig war. In den kahlen Simulationsräumen ist die Basis schon schnell;
  das reale Problem (20–30 min in einem Raum) bildet sie nicht ab.
- **Die Abdeckungskurven bestätigen die Beobachtung des Projektinhabers:**
  95 % der freien Endfläche nach etwa 3 min, die restlichen 3–8 min bringen
  4–5 %.

**Entschieden am 10.11.2026:** siehe Abschnitt darüber (Stellprobe, ein
Problem zur Zeit).

## 09.11.2026 (spätabends) – KM-1 Variante A verworfen; Gehäuse berührt in der Simulation beim langsamen Drehen

**Neue Messgröße (`a77053a`):** Die Prüfkontur der Simulation ist die
gepolsterte Kontur; „Kontakt“ hieß dort 2 cm vor dem echten Gehäuse. Neu wird
der Abstand des echten Gehäuses gemessen (`minimaler_abstand_koerper_m`).

**KM-1 Variante A** (Kollisionsmonitor prüft „approach“ gegen das Gehäuse ohne
Polster), drei Läufe: **verworfen.** In allen drei berührte das echte Gehäuse
ein Hindernis (0,0 m), festgehalten wurde der Roboter trotzdem (Hilfe
benötigt 2×, Teilkarte 1×).

**Befund zum aktuellen Produktstand (AW-1b, gleiche Messgröße):**

| Lauf | Ende | Abdeckung | Gehäuse min. | Bewegung bei der Annäherung | Kollisionsmonitor |
|---|---|---|---|---|---|
| Referenz | vollständig, 416 s | 0,979 | 2,1 cm | Fahrt | nie „approach“ |
| Tür 0,68 m | Teilkarte, Budget | 0,925 | **0,0** | Drehen auf der Stelle (w −0,04) | 21× „approach“ |
| Drift | Teilkarte, Budget | 0,909 | **0,0** | Drehen auf der Stelle (w −0,01) | 21× „approach“ |

- **Korrektur einer früheren Annahme:** Die „bekannten 2-cm-Annäherungen an
  der Insel beim Drehen“ habe ich bisher als harmlos eingestuft, weil nur die
  Prüfkontur gemessen wurde. In 2 von 3 Läufen berührte in der Simulation das
  **echte Gehäuse** die Insel, jedes Mal beim langsamen Drehen.
- Wahrscheinlicher Mechanismus (DR-1, 03.11.): Die Hindernisebenen löschen
  alles unter der gepolsterten Kontur. Liegt ein Hindernis im Polsterband,
  verschwindet es aus der Karte, der Regler dreht weiter, der
  Kollisionsmonitor (VL53, nur vorn) sieht die Flanke nicht; danach hält er
  im Modus „approach“ alles fest.
- **Real** gab es in neun Laborfahrten (SH-6, SH-7) keine Berührung. Die
  Abbruchregel für SH-8 (jede Berührung: sofort stoppen) bleibt; Christopher
  achtet besonders auf langsame Drehungen dicht an Möbeln.

**In Simulation: KM-1 Variante B** – die Hindernisebenen der lokalen Karte
löschen nichts mehr unter der Kontur (`footprint_clearing_enabled: False`);
Hindernisse im Polsterband bleiben eingetragen, der Regler dreht nicht
hinein, wegkommen über die Rückfahrkontur (AW-1). DR-1 scheiterte am
Strengerwerden ohne Ausweg; den Ausweg gibt es jetzt. Offen für den Roboter:
ob LiDAR oder VL53 Teile des Roboters selbst erfassen (die würden dann nicht
mehr gelöscht) – das wäre vorher im Stand zu messen.

**KM-1 Variante B, erste drei Läufe (gleiche Welten wie oben):**

| Lauf | Ende | Dauer | Abdeckung | engster Abstand Prüfkontur / Gehäuse | Rückfahrten | „approach“ |
|---|---|---|---|---|---|---|
| Referenz | vollständig, bestanden | 329 s | 0,979 | 8,8 cm / nie unter 3 cm | 0 | nie |
| Tür 0,68 m | Rest unerreichbar (nur Kartenkriterium offen) | 394 s | 0,967 | 3,9 cm / nie unter 3 cm | 1 erfolgreich | nie |
| Drift | vollständig, bestanden | 535 s | 0,971 | 0,6 cm / 3,3 cm | 3 erfolgreich | nie |

Gegenüber dem Produktstand (zwei Gehäuseberührungen, zwei Teilkarten nach
„approach“-Festhalten) keine Berührung, kein Festhalten, alle Rückfahrten
erfolgreich. Drei Läufe sind wenig; Absicherung mit weiteren Läufen läuft,
dabei auch EK-1 auf Variante B. Variante B ändert nicht den
Kollisionsmonitor, sondern nur, dass die lokale Karte unter der Kontur nichts
löscht; Name bleibt KM-1 B wegen des Zusammenhangs.

## 09.11.2026 (abends) – AW-1b in der Simulation: Lücke (1) behoben, Lücke (2) dominiert die Simulation

AW-1b (`d0d1431`): Nach einer Rückfahrt wird das Ziel zurückgestellt. Vier
Läufe (zwei mit Drift, Tür 0,68 m, Referenz), **keiner bestanden**:

| Lauf | Ende | Dauer | Abdeckung | Kollisionsmonitor | Was geschah |
|---|---|---|---|---|---|
| Drift 1 | Hilfe benötigt | 209 s | 0,916 | nie „approach“ | Regler verweigerte jede Bewegung; Rückfahrt gelang (0,3 m), danach verweigerte er weiter, acht Fehlschläge |
| Tür 0,68 m | Teilkarte, Budget | 899 s | 0,924 | 21× „approach“ | ab etwa 3 min festgehalten, Rückfahrten liefen in die Zeitgrenze |
| Drift 2 | Teilkarte, Budget | 899 s | 0,911 | 21× „approach“ | wie oben |
| Referenz | Teilkarte, Budget | 899 s | 0,908 | „approach“ ab 187 s | wie oben |

Belegt:
- Lücke (1) ist behoben: Nach jeder Rückfahrt kam ein anderes Ziel.
- **In der Simulation dominiert Lücke (2):** In drei von vier Läufen hielt
  der Kollisionsmonitor im Modus „approach“ den Roboter an der Insel fest
  (VL53-Punkte innerhalb der gepolsterten Kontur), auch rückwärts. Danach
  nahm die Fläche 13 min lang nicht mehr zu (Abdeckungskurve: 90 % nach
  90 s, dann Stillstand).
- Real war das in SH-7 nicht der Fall: An allen drei Hilfe-Stellen meldete
  der Monitor nur „slowdown“ oder „continue“ (SH-7N, Punkt 3); dort
  verweigerten Regler und BackUp, was AW-1/AW-1b adressieren. Simulation und
  Wirklichkeit unterscheiden sich in diesem Punkt; die Insel-Annäherung beim
  Drehen ist ein bekannter Simulationsbefund.
- Ein Lauf (Drift 1) zeigt zusätzlich: 0,3 m zurück reichten dort nicht; der
  Regler verweigerte auch danach jede Richtung.

**Bewertung:** AW-1b tut, was es soll; die Simulation besteht trotzdem nicht,
weil Lücke (2) sie dominiert. Ob (2) real vorkommt, misst SH-8 (Zustand des
Kollisionsmonitors je Rückfahrt). **Entscheidung des Projektinhabers
(09.11.2026, abends): SH-8 jetzt fahren**; parallel Entwurf KM-1 für (2) in
der Simulation.

## 09.11.2026 (nachmittags) – EK-1 „Erkundung zielgerichtet, Teil 1“: Kriterien vorab, Bau in der Simulation

Fahrplan MASTERPLAN §9, Schritt 1 parallel zu SH-8. **Nicht Teil von
SH-8:** Der Code (`454a937`) liegt auf dem Branch, alle drei Teile sind im
Code standardmäßig aus (Parameter 0) und im Produktprofil nicht gesetzt.
Der SH-8-Auftrag prüft deshalb, dass im installierten Profil keine EK-1-Zeile
steht, und akzeptiert 182 statt 176 Tests (Regel 1: SH-8 prüft nur AW-1).

**Umfang:** A Rundblick (360° auf der Stelle) am Start und nach einem
erreichten Ziel, das mindestens 2,5 m von früheren Rundblicken entfernt
liegt, nur bei nachweislich freiem Drehkreis; C „gut genug“-Ende, wenn die
freie Fläche in 150 s um weniger als 2 % wuchs, darin mindestens zwei
Anläufe lagen und keine Lücke von 0,6 m oder mehr übrig ist (offene Tür
bleibt Ziel); D Anlauf abbrechen, wenn sich der Roboter 45 s lang nicht
0,25 m von der letzten Prüfstelle entfernt hat (zählt als Fehlversuch).

**Simulationskriterien, vor dem ersten Lauf festgelegt** (Basis = Produkt
ohne EK-1, gleiche Welt; Referenzwohnung mit Möbeln, Tür 0,68 m, Mülleimer):
- **E1** Abdeckung (erreichbar) mindestens 0,90 in jedem EK-1-Lauf, der nicht
  durch die bekannte Insel-Annäherung eingefroren wurde (beide Räume erfasst).
- **E2** Keine neue Fehlerart: Unterschreitungen nur die bekannte an der Insel
  beim Drehen; keine während eines Rundblicks.
- **E3** Leerlauf halbiert: Median der Zeit von 95 % der freien Endfläche bis
  Fahrtende höchstens 50 % des Basis-Medians.
- **E4** Zeit bis 90 % der freien Endfläche: Median höchstens 60 s länger als
  die Basis (ein Rundblick kostet etwa 65 s).
Realkriterium für SH-9 (Fahrplan §9 Schritt 2) wird nach den
SH-8-Abdeckungskurven endgültig festgelegt.

## 09.11.2026 – AW-1 „Abstand halten und wegkommen“: gebaut, Simulation, SH-8 aktiviert

**Umgesetzt** (`19c8cb9`, Entscheidung des Projektinhabers 08.11.2026, nur
im Selbstheilungsbetrieb):
1. Wege mit mehr Abstand: globale Inflation 0,60 m / 2,5 (Basis 0,45 / 3,0).
2. Eigene LiDAR-Ebene in der lokalen Karte, die markiert und räumt; die
   VL53-Ebene bleibt wie nach X9.
3. BackUp prüft gegen die Rückfahrkontur (neuer Knoten `rueckfahr_kontur`:
   Heck mit Polster, Breite 1 cm unter der halben Breite, vorn innerhalb des
   Roboters); Regler und Kollisionsmonitor unverändert mit voller Kontur.
4. Rückfahrt ohne gerade eigene Spur: 0,3 m gerade zurück, wenn der
   Behavior-Server hinten frei sieht; höchstens 0,4 m, 0,05 m/s, einmal je
   Stillstand; Zeitgrenze für 30 % Tempo.

**Abweichung vom Vorschlag:** Das Fahrpolster bleibt 0,02 m statt 0,05 m. Die
Hindernisschicht räumt die Fläche unter der gepolsterten Kontur (DR-1); ein
größeres Polster hätte seitliche Wände im Nahbereich ausgeblendet. Punkt 3
erreicht das Ziel „wegkommen“ ohne diesen Nachteil. Vorprüfung neu:
„Rueckfahrkontur liegt am Behavior-Server an“. Tests 176 gezielt, 167
Navigation/Simulation.

**Simulation** (Referenzwohnung, 15-min-Budget; Odometrie-Drift neu im
Werkzeug, 0,3 % Drehung und 2 % Weg, real gemessen 0,2–0,4 m und 2–6°):

| Lauf | Stand | Ende | Dauer | Ziele | Rückfahrten | engster Abstand | Simulationskriterien |
|---|---|---|---|---|---|---|---|
| Drift 1 | neu | vollständig | 412 s | 6 | 1 (erfolgreich) | 1,2 cm | bestanden |
| Drift 1 | vorher | vollständig | 457 s | 4 | 0 | 0 (Insel) | nicht bestanden |
| Drift 2 | neu | Hilfe benötigt | 330 s | 4 | 1 (erfolgreich) | 0 (Insel) | nicht bestanden |
| Drift 2 | vorher | vollständig | 342 s | 7 | 0 | 1,3 cm | bestanden |
| ohne Drift | neu | vollständig | 457 s | 10 | 0 | 0,2 cm | bestanden |
| Tür 0,68 m | neu | Teilkarte (Budget) | 899 s | 7 | 3 (1 erfolgreich, 2 vom Kollisionsmonitor blockiert) | 0 (Insel) | nicht bestanden |

Bewertung, ehrlich:
- **Keine neue Fehlerart.** Alle drei Unterschreitungen sind die bekannte
  2-cm-Annäherung an **dieselbe Insel beim langsamen Drehen auf der Stelle**
  (v = 0, w = −0,01…−0,04 rad/s), im Vorher-Stand ebenso. Keine geschah beim
  Rückwärtsfahren.
- **Rückfahrten:** Alle vier vor einer Annäherung ausgelösten Rückfahrten
  liefen vollständig; keine wurde mit „Collision Ahead“ verweigert.
- **Korrektur 09.11.2026 (nachmittags), meine frühere Aussage war falsch:**
  Die Simulation friert den Roboter nach einer 2-cm-Annäherung **nicht** ein;
  sie zeichnet sie nur auf, er fährt weiter. Die Zeitleisten der beiden
  schlechten Läufe zeigen zwei echte Lücken von AW-1:
  1. **Drift 2 neu:** Nach der Annäherung an die Insel verweigerte der Regler
     jede Bewegung („Controller patience exceeded“, 1078× „collision ahead“).
     Die freie Rückfahrt gelang (+95 s, vollständig). Danach fuhr Amadeus
     **dasselbe Ziel erneut** an, stand wieder an derselben Stelle fest, und
     eine zweite Rückfahrt ist je Stillstand nicht erlaubt: acht Fehlschläge,
     „Hilfe benötigt“. Wie in SH-6 (dreimal dasselbe Ziel danach erneut
     gescheitert).
  2. **Tür 0,68 m:** Beide Rückfahrten nach der Annäherung liefen in die
     Zeitgrenze, weil der **Kollisionsmonitor** im Modus „approach“ jede
     Bewegung auf null setzte: Liegen VL53-Punkte schon innerhalb der
     gepolsterten Kontur, ist die Kollisionszeit null, auch rückwärts. Das ist
     dieselbe Falle wie beim BackUp, eine Ebene weiter (Kollisionsmonitor,
     sicherheitsrelevant, nach AGENTS §2.7 nur getrennt zu ändern).
- Abdeckung und Zeit wie bisher (ohne Drift 457 s, 0,974; Tür 0,68 m 0,914
  gegenüber 0,906/0,908).

**SH-8 aktiviert** ([Auftrag](AGENTENAUFTRAG.md), Fahrplan Schritt 1): Release
ab `609d389`, gleicher Aufbau und gleiche Kriterien wie SH-7, Abdeckungskurve
mitgelesen, bei „Hilfe benötigt“ Daten wie in SH-7N. Rückfall: `SH_REL` auf
`selbstheilung-sh7-20261108_1617` oder Prototyp 1.

**Nächster Schritt:** SH-8-Bericht auswerten (parallel EK-1 in der Simulation).

## 08.11.2026 (abends) – SH-7N ausgewertet: Warum Amadeus an engen Stellen festsitzt

Lokaler Agent, nur lesend aus `sh7_run1…3` (Bericht beim Projektinhaber).
Christopher: Die fehlende Flurwand ist eine **geschlossene Holztür**; an der
Garderobe waren neben den Jacken noch 80 cm frei; an den Hilfe-Stellen von
Fahrt 2 und 3 lag nichts Niedriges.

**1. Odometrie-Abweichung bestätigt:** `map→odom` am Ende −0,38/+0,16 m und
−2,1° (Fahrt 1), −0,24/−0,02 m und −6,4° (Fahrt 2), −0,16/−0,02 m und −5,3°
(Fahrt 3).

**2. Verschobene LiDAR-Reste in der lokalen Karte bestätigt:** Von den
tödlichen Zellen (Wert 100) im Umkreis von 1,5 m lagen in Fahrt 1 113 von 357
und in Fahrt 3 178 von 325 dort, wo die SLAM-Karte frei ist, mehr als 0,10 m
von jeder SLAM-Wand, typischerweise 0,24–0,28 m daneben, passend zur
Abweichung. Fahrt 2: 0 von 72, aber die Karte stammt von einer anderen Stelle
als die Abbrüche.

**3. Festgesessen hat er aber an echten Hindernissen:**
- Nav2 leert bei jedem Reglerfehler die lokale Karte (leichte Recovery im
  Baum); die Abbrüche blieben trotzdem. Was ihn blockierte, wurde also jedes
  Mal frisch und richtig wieder eingetragen.
- An den Hilfe-Stellen lag die gepolsterte Kontur 1–5 cm an tödlichen Zellen,
  die die SLAM-Karte bestätigt: Fahrt 1 vorn (x 0,35–0,45 m) und links
  (y 0,27–0,30 m), Garderobe und Wand; Fahrt 3 vorn links (Ecke). Hinter dem
  Roboter (0,11–0,6 m) lag in Fahrt 1 und 3 **keine** tödliche Zelle.
- **Mechanismus:** Der Regler (RPP) und die Rückfahrt (BackUp) prüfen zuerst
  die aktuelle Pose. Liegt die Kontur dort schon an einer belegten 5-cm-Zelle
  an, verweigern beide jede Bewegung: RPP „detected collision ahead“
  93× in 8,7 s, dreimal „Controller patience exceeded“; BackUp
  „Collision Ahead“ 1 ms nach dem Start, obwohl hinten frei war. Die Leiter
  hat dann nur noch Ziele, die alle nach 9 s scheitern, und nach 8
  Fehlschlägen kommt die Hilfe.
- Hinein kommt er, weil RPP so lange weiterfährt (bei 30 % Tempo kriechend),
  bis die vorausberechnete Kontur anliegt, und weil die Wege dicht an
  Hindernissen entlangführen.

**4. Tür in Fahrt 3:** Alle Anläufe durch die Tür scheiterten am globalen
Planer („failed to create plan“, auch nach dem Leeren der globalen Karte),
nicht am Regler. In der Karte dieser Fahrt war die 80-cm-Tür für den Planer
(Roboterradius 0,28 m) zu schmal; in Fahrt 1 und 2 ging es. Warum, ist nicht
gemessen.

**5. Geschlossene Holztür nicht gesehen:** Die SLAM-Karte ist bis zur Tür
frei und dahinter unbekannt; an der Tür selbst steht keine Wand. Das ergibt
eine falsche Lücke. In Fahrt 1 lagen die Ziele genau dort, und Amadeus
zwängte sich neben die Jacken. Warum der LiDAR die Tür nicht einträgt, ist
offen (der Scan wird nicht nach Intensität gefiltert).

**Einordnung:** Die Ursache ist allgemein, nicht an einen Raum gebunden:
dicht an Hindernissen entlangfahren, und aus einer anliegenden Lage gibt es
mit Nav2 keinen Weg zurück. Die Spur-Rückfahrt auf gerader eigener Spur hilft
dort nicht (Fahrt 3 hatte keine, in Fahrt 1 und 2 verweigerte Nav2 sie).

**Offen zur Entscheidung des Projektinhabers:** wie Amadeus Abstand hält und
aus einer anliegenden Lage wegkommt (Vorschläge im Chat vom 08.11.2026).
SH-7N [archiviert](archive/20261108-sh7n-ausgewertet/README.md); kein aktiver
Jetson-Auftrag.

**Nächster Schritt (erledigt 08./09.11.):** Entscheidung des Projektinhabers.

## 08.11.2026 – SH-7: Raumwechsel nicht bestätigt (Hilferufe an engen Stellen)

Lokaler Agent, Fahrten 16:37–19:46, LAB-1 aktiv, Release
`selbstheilung-sh7-20261108_1617` (Build 174 s, 14/14 Präfixe, 172 Tests
grün, HEAD `4c25fb3`). Vorprüfung je Fahrt Exit 0, 49× OK, Tempowerte live
bestätigt; kein Start von „D Quellen“ abgefangen. Aufbau laut Christopher:
Tür 80 cm ohne Schwelle, gesichert; Nachbarraum ein Flur von etwa 4 × 1,5 m
mit einer Garderobe an der Wand; übrige Türen zu.

| Fahrt | Dauer | Ziele | Heilungen | Rückfahrten | Tür | Ende | Strecke | SLAM letzte min | verworfene Scans |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 1523 s | 5 | 7 | 1 | einmal hinein | **Hilfe** im Flur vor der Garderobe | 5,3 m | 9,2 % | 7 |
| 2 | 1849 s | 12 | 19 | 4 | hinein und zurück | **Hilfe** im Laborraum nahe der Tür | 14,2 m | 15,9 % | 12 |
| 3 | 1915 s | 7 | 26 | 1 | nein | **Hilfe** in einer Ecke des Laborraums | 14,8 m | 20,4 % | **34** |

Christopher: nichts berührt, kein Eingriff, beide Räume passen an der Tür
aneinander; Fahrt 1 und 2 „im Flur fehlt deutlich eine Außenwand“, Fahrt 3
Karte sauber, Flur „nur teilweise“. Tempo: rechtzeitig gebremst; „zu
langsam“, „zu langsam“, „passend“. „extrapolation into the future“ 0/1/0.

**Ergebnis nach den vorab festgelegten Kriterien: nicht bestätigt.** C1, C2,
C4 in allen Fahrten erfüllt; C3 in Fahrt 3 nicht (34 > 20); C5 in Fahrt 1 und
2 nicht (fehlende Flurwand); **G1 in keiner Fahrt**; R1 und R2 in Fahrt 1 und
2 erfüllt, in Fahrt 3 nicht.

**Was die Daten zeigen (belegt):**
1. **Der Raumwechsel selbst funktioniert:** zwei von drei Fahrten durch die
   80-cm-Tür, Fahrt 2 auch zurück, ohne Berührung, Karte an der Tür passend.
2. **Alle drei Hilferufe kamen an Stellen, an denen die Leiter keinen Zug mehr
   hatte, der Amadeus bewegt:**
   - Fahrt 3 (Ecke): Die Spur-Rückfahrt gibt es nur auf gerader eigener Spur
     (≤ 3 cm seitlich); nach dem Einfahren in die Ecke war keine da. Umsehen
     braucht freien Drehkreis, auch der fehlte. Übrig blieben „erneut“ und
     „zurückstellen“; 8 Anläufe scheiterten nach je 9 s, nach rund 2 min war
     die Grenze „8 Fehlschläge in Folge“ erreicht. Christopher: Befreiung nur
     rückwärts oder mit 180°-Drehung.
   - Fahrt 2: 7 Anläufe zu vier Zielen scheiterten nach je 7–9 s, dann ein
     150-s-Anlauf, dann Grenze 8 erreicht. Rundherum ≥ 0,71 m frei, Grund der
     schnellen Abbrüche offen.
   - Fahrt 1 (Flur): 15 min am selben Fleck; an der Basis kamen nur v = 0 und
     |w| ≤ 0,04 rad/s an. Die lokale Kostenkarte war links ab 0,22 m, rechts
     ab 0,25 m und vorn-links ab 0,26 m belegt, also an oder in der
     Roboterkontur (halbe Breite 0,25 m plus 0,02 m Polster). Hilfe nach
     600 s ohne Kartenzuwachs (abgeleitet). Ob das echte Hindernisse
     (Garderobe, Mäntel) oder liegengebliebene Markierungen waren, ist offen
     (der LiDAR markiert lokal, räumt aber nicht; Entscheidung X9).
   - Die Grenze „8 Fehlschläge“ war für Anläufe von bis zu 150 s gedacht; bei
     Abbrüchen nach 7–9 s ist sie in ein bis zwei Minuten erreicht.
3. **Keine der 6 Rückfahrten lief vollständig:** 4 an der Zeitgrenze (wie in
   SH-6, Langsam-Zone 30 %), 2 sofort mit „Collision Ahead“ des
   Behavior-Servers, obwohl nach hinten laut Kostenkarte etwa 0,9 m frei
   waren (Grund offen; Kandidat: Markierungen an der Kontur).
4. **Fehlende Flurwand (Fahrt 1 und 2):** Ursache offen. Möglich: nie gesehen,
   weil Amadeus im Flur festsaß; Glas/Spiegel; verdeckt durch die Garderobe.
5. Tempo: kein zu spätes Bremsen. „detected collision ahead“ 946/762/917
   (SH-6: 311/709/248); ob das am Tempo, am Flur oder an den Engstellen
   liegt, ist nicht getrennt.

**Einordnung:** Das ist die schon in DR-1 gemessene Grenze („In Engstellen
unter etwa 0,9 m kann Amadeus nicht drehen; seine Selbstheilung braucht dort
Rückfahrt“, DR-2 damals zurückgestellt), jetzt real im Flur und in einer
Ecke. Eine Wohnung hat viele solche Stellen.

**Offen zur Entscheidung des Projektinhabers:** zuerst nur lesend die drei
Hilfe-Stellen und die fehlende Wand aus den vorhandenen Daten klären
(Abbruchgründe von Nav2, Kostenkarten an der Kontur, Grund für „Collision
Ahead“, Kartenbild), oder direkt einen Befreiungsschritt für Engstellen
einbauen. SH-7 [archiviert](archive/20261108-sh7-ausgewertet/README.md); kein
aktiver Jetson-Auftrag. Rohdaten `$SH_PR/sh7_run1…3` bleiben lokal erhalten.

**Entscheidung des Projektinhabers (08.11.2026): erst Daten prüfen**, dann
ein gezielter Befreiungsschritt. Zur fehlenden Flurwand: Dort ist laut
Christopher eine Tür oder ein Durchgang (Einzelheiten fragt SH-7N).

**Arbeitshypothese für SH-7N (aus den Endposen im SH-7-Bericht gerechnet,
noch nicht geprüft):** Die Odometrie wich am Ende der Fahrten um 0,35 / 0,33 /
0,29 m und −2,1 / −6,4 / −5,7° von der SLAM-Karte ab (`map→odom`). Die lokale
Kostenkarte liegt im `odom`-Rahmen; dort markiert der LiDAR, räumt aber nie
(X9, in der Simulation mit idealer Odometrie entschieden), räumen können nur
die VL53 vorn zwischen 0,45 und 0,7 m. Eine Drehabweichung von 6° verschiebt
eine Wand in 3 m Abstand um etwa 0,3 m. Wände aus früheren Fahrminuten
könnten so verschoben liegen bleiben, Durchgänge und Türen in der lokalen
Karte schmaler machen und Regler („collision ahead“) und Rückfahrt
(„Collision Ahead“) blockieren, während die globale Planung frei sieht. Das
passt zu den belegten Zellen an der Kontur in Fahrt 1 und zu den
Abbrüchen vor der Tür in Fahrt 3, ist aber nicht belegt. SH-7N vergleicht
deshalb die belegten Zellen der lokalen Karte an jeder Hilfe-Stelle mit der
SLAM-Karte und liest die Abbruchgründe aus.

**Nächster Schritt (erledigt 08.11. abends):** SH-7N ausführen, dann
Auswertung und gezielter Befreiungsschritt.

## 05.11.2026 (mittags) – Prototyp 1 eingefroren, Tempo erhöht, SH-7 angepasst

**Entscheidungen des Projektinhabers (05.11.2026)** nach eigener Beobachtung
von SH-6 (eigens aufgestellte Papierkörbe umfahren, Raum gut abgescannt):
1. **Prototyp 1 eingefroren:** `src/`-Stand `e8f00f6`, am Jetson Release
   `selbstheilung-sh6-20261104_2140`, unverändert als Referenz und Rückfall.
   Die holprigen Rückfahrten (SH-6, Punkt 2) bleiben bewusst so.
2. **Tempo:** vorwärts +35 %, Drehen +25 %, weil die Fahrten am Zeitbudget
   endeten. Umgesetzt in `adbb39f`, nur im Selbstheilungsprofil: Regler
   0,10 → 0,135 m/s und 0,20 → 0,25 rad/s, Obergrenzen 0,12 → 0,162 m/s und
   0,25 → 0,3125 rad/s, vor Unbekanntem 0,06 → 0,08 m/s (+33 %, Obergrenze des
   Parameters), Umsehen 0,08 → 0,10 rad/s. Unverändert: Kollisionsmonitor
   (Approach 2 s, Langsam-Zone 30 %), Motorrampen (Bremsen 400 ms),
   base_hardware-Grenzen 0,30 m/s / 0,80 rad/s, Rückfahrt 0,05 m/s.
   Abschätzung: Bremsweg aus 0,162 m/s etwa 3 cm; vor Hindernissen, die die
   VL53 bis etwa 0,5 m sehen, drosselt die Langsam-Zone ohnehin auf 30 %
   (≈ 0,05 m/s); der Approach-Horizont reicht bei voller Fahrt 0,32 m weit.
   Fällt ein VL53 aus, sperrt das Fahrtor nach 0,8 s; bis dahin fährt er
   höchstens etwa 0,13 m (bisher 0,10 m).
3. **Fokus Nachbarraum** (SH-7), danach Wohnung.
4. **Räume und Türen bekommen in der Erkundung keine IDs.** Nach der
   Erkundung grenzt der Projektinhaber Räume in der App ab und benennt sie
   (vorhanden: `semantic_map_manager`, an die gespeicherte Karte gebunden,
   App-Raumeditor); Raumziele später über `go_to_room` (real nur per Opt-in,
   mit Lokalisierung auf der gespeicherten Karte). Die automatische
   Tür-/Regionserkennung aus AP-06 bleibt eingefroren. Ob die Kette
   Erkundungskarte → Speichern → Räume zeichnen → Raumziel mit Karten aus dem
   Selbstheilungsbetrieb durchgängig funktioniert, ist nicht geprüft; eigener
   Schritt nach SH-7.

**Simulation des Tempos** (Werkzeug wie bisher, Referenzwohnung mit zwei
Räumen, 15-min-Budget der Simulation; Vergleich mit der Regel-Regression vom
04.11. ohne Tempoänderung):

| Lauf | Tempo | Ende | Dauer | Ziele | Abdeckung | Kartenfehler | engster Abstand |
|---|---|---|---|---|---|---|---|
| Referenz | alt | vollständig | 492 s | 5 | 0,974 | 0,039 m | 0 (2-cm-Annäherung an der Insel beim Drehen) |
| Tür 0,68 m | alt | Teilkarte, Budget | 899 s | 5 | 0,906 | 0,063 m | 0 |
| Referenz | alt | Teilkarte, Budget | 899 s | 5 | 0,908 | 0,027 m | 0 |
| Referenz | **neu** | vollständig | 464 s | 5 | 0,967 | 0,061 m | 0 (dieselbe Stelle, Drehung mit 0,02 rad/s) |
| Tür 0,68 m | **neu** | Teilkarte, Rest unerreichbar | 456 s | 11 | 0,969 | 0,066 m | 1,4 cm |
| Referenz | **neu** | vollständig | 359 s | 7 | 0,978 | 0,046 m | 0,7 cm |

Neu: zwei von drei Läufen bestehen alle Simulationskriterien (alt: keiner),
alle drei durch die Tür in den zweiten Raum, kürzer und mit mehr Abdeckung.
Die eine 2-cm-Annäherung liegt an derselben Stelle wie vorher und beim
langsamen Drehen, nicht beim schnelleren Fahren. Grenzen: drei Läufe, die
Simulation kennt weder Motorrampe noch reale Bremswege noch VL53-Aussetzer;
den Nachweis liefert SH-7.

**SH-7 angepasst** ([Auftrag](AGENTENAUFTRAG.md)): Istbasis `adbb39f`, Build-
und Vorprüfzeilen für die Tempowerte, Frage 8 zum Tempo (Beobachtung, kein
Kriterium; „zu spät gebremst“ bleibt Abbruchgrund). Kriterien unverändert.
Rückfall: `SH_REL` auf `selbstheilung-sh6-20261104_2140` (Prototyp 1).

**Nächster Schritt (erledigt 08.11.):** SH-7-Bericht auswerten.

## 05.11.2026 – SH-6: Regel bestätigt, SH-7 aktiviert

Lokaler Agent, Fahrt 1 am 04.11. 21:48–22:08, Fahrt 2 und 3 am 05.11.
09:36–10:21 (dazwischen Akku leer), LAB-1 aktiv, Release
`selbstheilung-sh6-20261104_2140` (Build 167 s, 14/14 Präfixe, 172 Tests
grün, HEAD `7aa7444`). Vorprüfung je Fahrt Exit 0, 47× OK; „D Quellen“ fing
den ersten Start am Morgen ab (Encoder 87 s alt, Zeitwache `fault_latched`,
HWT-Fusion nicht bereit; keine Mission, keine Bewegung), nach geordnetem
Neustart alles OK. Ursache nicht geprüft, Bild wie in SH-5
(Motor-Stop-Schalter). Missionsstart per Ersatzbefehl (App nicht verfügbar).

| Fahrt | Dauer | Ziele | Heilungen | Spur-Rückfahrten | Ende | Strecke | SLAM letzte min | verworfene Scans | Kontakt / Eingriff |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 1199 s | 8 | 5 | 1 | Teilkarte, 20-min-Budget | 8,0 m | 14,6 % | 10 | nein / nein |
| 2 | 1199 s | 10 | 5 | 0 | Teilkarte, 20-min-Budget | 6,8 m | 11,5 % | 7 | nein / nein |
| 3 | 1200 s | 10 | 9 (1× Umsehen) | 2 | Teilkarte, 20-min-Budget | 6,4 m | 10,4 % | 8 | nein / nein |

„extrapolation into the future“ 0. Christopher: nichts berührt, kein
Eingriff, Karten und Drehstellen „sauber“. **Ergebnis nach den vorab
festgelegten Kriterien: bestätigt** (C1–C5 und G1 in allen drei Fahrten;
C3 in Fahrt 1 genau auf der Grenze von 10). Bisher bestes Ergebnis im
Laborraum: 28 Ziele in drei Fahrten (SH-5: 14, SH-3: 17), kein Hilferuf.

**Kritisch, was die Daten über die Regel sagen:**
1. **Ausgelöst 3× (1/0/2), jedes Mal nach einem Anlauf von 6–7 s**, den Nav2
   mit „Goal failed“ beendete (`nav_aborted`, weniger als 5 cm bewegt). Danach
   scheiterte **dasselbe Ziel in allen drei Fällen erneut** nach etwa 7 s und
   wurde zurückgestellt; Amadeus kam über andere Ziele weiter (Fahrt 3:
   danach 4 bzw. 2 weitere Ziele), so wie die Leiter es auch vorher getan
   hätte. Christopher sah die Rückfahrt in Fahrt 1 und „keine
   Grund/Hindernis“. Ob Amadeus in die SH-5-Lage vor den Mülleimern kam, ist
   nicht belegt. Die Regel schadet nicht; dass sie die Ursache für das Fehlen
   von Hilferufen ist, ist nicht gezeigt.
2. **Zwei der drei Rückfahrten liefen in die Zeitgrenze:** Der
   Kollisionsmonitor drosselte sie in seiner Langsam-Zone auf 30 %
   (0,007–0,015 m/s an der Basis); der Explorer gibt `Strecke / 0,05 m/s +
   10 s` (0,24 m → 14 s), das reicht bei 30 % für etwa 0,2 m. Bewusst nicht
   geändert: In Fahrt 1 lief die Rückfahrt vollständig und half demselben
   Ziel ebenso wenig; eine Änderung zur Zeit.
3. Alle drei Fahrten endeten am 20-min-Budget (wie 4 von 6 in SH-3/SH-5).
   Für zwei Räume ist das zu knapp, siehe SH-7.
4. Mission-Manager meldet am Ende `failed`, obwohl der Explorer
   `usable_partial` liefert (wie in SH-5). Für die App (WE-M7) offen, für
   SH-7 ohne Wirkung.
5. VL53-Aussetzer bis 11,7 s (bekannt, Ursache offen); der Explorer machte
   jedes Mal selbst weiter.
6. `ros2 topic echo --once` kürzt lange Zeichenketten; der Agent sicherte den
   Status zusätzlich mit `--full-length`. In SH-7 gleich so.

**SH-7 aktiviert** ([Auftrag](AGENTENAUFTRAG.md), Entscheidungen des
Projektinhabers 04.11.2026): Laborraum plus Nachbarraum durch **genau eine
offene Tür ohne Schwelle, lichte Breite ≥ 75 cm**, Türblatt gesichert, alle
übrigen Türen beider Räume zu; Start im Laborraum mindestens 1 m von der Tür.
Einzige Software-Änderung: Gesamtbudget 40 min im Selbstheilungsprofil
(`c444bca`, 172 Tests). Drei Fahrten, Laden dazwischen erlaubt. Vorab
festgelegte Kriterien je Fahrt: C1–C5 und G1 wie SH-6 (C1 einschließlich
Türrahmen und Türblatt, C5 einschließlich Passung beider Räume an der Tür,
C3 ≤ 20 und C4 ≤ 80 für die doppelte Zeit), neu **R1** selbstständige
Durchfahrt in den Nachbarraum und **R2** Nachbarraum in der Karte ganz oder
größtenteils erkennbar. Bestätigt, wenn alle drei Fahrten alle Kriterien
erfüllen. Rückfall: `SH_REL` auf `selbstheilung-sh6-20261104_2140`. SH-6
[archiviert](archive/20261105-sh6-ausgewertet/README.md).

**Nächster Schritt:** SH-7-Bericht auswerten; mit bestätigtem Raumwechsel
Stufe 3 (Wohnung), Umfang und Kriterien legt der Projektinhaber vorher fest.

## 04.11.2026 (Nacht) – Regel in der Simulation, SH-6 aktiviert

**Simulation der Regel `e8f00f6`** (Werkzeug `c71ecd3`, Eimer 40 cm hoch,
nur für die VL53 sichtbar, zwei Startlagen):

- **Eimer-Nachbau:** ohne Regel 0 von 4 Läufen sauber, mit Regel ebenfalls
  0 von 4. In allen vier Läufen mit Regel streifte die Flanke den seitlich
  stehenden Eimer beim Drehen, **bevor** Amadeus festsaß (nach 65 s bzw.
  125–130 s). [Korrektur 09.11.2026: Hier stand, die Simulation friere den
  Roboter nach einer Berührung ein. Das ist falsch; sie friert nur die
  Aufzeichnung der letzten Sekunden ein (DR-1-Werkzeug), der Roboter fährt
  weiter.]
  Die Rückfahrt löste in zwei Läufen aus, beide Male erst nach der Berührung.
  Der Laborfall (Eimer **vorn**, Kollisionsmonitor hält, keine Berührung)
  entsteht so nicht; die Simulation kann die Regel dort weder bestätigen
  noch widerlegen.
- **Regression (Referenzwohnung, gesperrte Tür, Tür 0,68 m):** keine
  einzige Rückfahrt ausgelöst; Ergebnisse wie bei der einfachen Version
  (Referenz einmal vollständig und einmal Teilkarte mit Abdeckung 0,908,
  gesperrte Tür Teilkarte, Tür 0,68 m Teilkarte mit 0,906). Kontakte nur
  die bekannten 2-cm-Annäherungen (Simulationskontur = Grundriss + 2 cm),
  die mit dem Kurswechsel hingenommen sind.

Bewertung: Die Regel stört dort nicht, wo Amadeus vorankommt. Ob sie ihn
vor Hindernissen an der Front befreit, zeigt nur die echte Fahrt.

**SH-6 aktiviert** ([Auftrag](AGENTENAUFTRAG.md)): Release
`selbstheilung-sh6-<STAMP>` ab `e8f00f6`, 172 gezielte Tests, drei Fahrten
im selben Laborraum mit denselben Gegenständen wie SH-5, Kriterien C1–C5
und G1 unverändert. Zusätzlich je Fahrt: Zahl, Zeitpunkt und Weite der
Spur-Rückfahrten und ob Amadeus danach weiterkam. Rückfall: `SH_REL` auf
`selbstheilung-sh5-20261104_1627`.

**Nächster Schritt (erledigt 05.11.):** SH-6-Bericht auswerten; mit bestätigter Regel SH-7.

## 04.11.2026 (spät) – SH-5N ausgewertet, Regel „kein Fortschritt → zurück“, Weg zu mehreren Räumen

**SH-5N (nur lesend, Jetson):** In den letzten zwei Anläufen vor „Hilfe
benötigt“ kam an der Basis **kein einziger Fahrbefehl** an. Der Regler
erzeugte Befehle (jede Sekunde ein neuer Weg, kein „collision ahead“), der
Kollisionsmonitor setzte sie sofort auf null („approach 2 s“), nach 30 s
„Failed to make progress“, im 30-s-Takt wieder. Zwei Mülleimer (38 cm hoch,
29 cm Durchmesser, 10 cm Lücke) standen 0,29–0,35 m von der Robotermitte
schräg vorn, also praktisch an der Front; alle Ziele lagen dahinter. Die
SLAM-Karte kennt die Eimer nicht. Nachbau in der Simulation (40-cm-Eimer, den
nur die VL53 sehen): ohne Regel 0 von 4 Läufen sauber, Pläne führten
überwiegend dicht am Eimer vorbei oder hindurch; seitlich stehende Eimer
streift die Simulation beim Drehen (bekannte Grenze, VL53 sehen nur nach vorn).

**Entscheidung des Projektinhabers (04.11.2026): eine allgemeine Regel.**
Kommt Amadeus in einem Anlauf weniger als 5 cm voran, fährt er sofort ein
Stück auf seiner eigenen Spur zurück (H4 wie freigegeben: eigene gerade Spur,
höchstens 0,4 m, 0,05 m/s, einmal je Stillstand) und versucht dasselbe Ziel
erneut; mit Bewegung bleibt die Leiter wie bisher. Umgesetzt in `e8f00f6`
(172 gezielte Tests), Simulation läuft.

**Entscheidungen des Projektinhabers (04.11.2026) zum weiteren Weg:**
1. **Die OAK-D wird nicht zur Hinderniserkennung eingesetzt** (zu ungenau,
   später teilweise vom Roboterarm vorn verdeckt). Hindernisse im Nahbereich
   bleiben LiDAR plus VL53.
2. **Raumwechsel ohne neues Raumkonzept:** Die Erkundung kennt keine Räume;
   eine offene Tür ist ein unbekannter Bereich wie jeder andere (in der
   Simulation mit zwei Räumen, 0,84-m-Verbindung und Türen 0,8/0,68 m
   erprobt; der Nav2-Ansatz fuhr im August real Raumwechsel). Reihenfolge:
   **SH-6** Regel im bekannten Laborraum bestätigen (eine Änderung), dann
   **SH-7** Laborraum plus Nachbarraum durch **eine offene Tür ohne
   Schwelle, lichte Breite ≥ 75 cm**, übrige Türen zu, Zeitbudget 40 min,
   dann Stufe 3 (Wohnung). Reale Risiken beim Raumwechsel: halb offene
   Türblätter, Drehen im Türrahmen, längere Fahrten (Budget).

**Nächster Schritt (erledigt 04.11. Nacht):** Simulation der Regel auswerten, dann Auftrag SH-6.

## 04.11.2026 (abends) – SH-5: einfache Version nicht bestätigt (G1 in Fahrt 3), Datenprüfung

Lokaler Agent, Fahrten 16:45–18:46, LAB-1 aktiv, Release
`selbstheilung-sh5-20261104_1627` (Build 170 s, 14/14 Präfixe, 171 Tests grün,
HEAD `edb06c2`, `src/` bytegleich `c20436a`). Vorprüfung je Fahrt Exit 0, 47×
OK; die neue Prüfung „D Quellen“ fing vor Fahrt 1 und 2 je einen Start mit
nicht bereiten Fahrquellen ab (Motor-Stop-Schalter zu spät freigeschaltet,
Bedienfehler laut Christopher, aus der Wertung genommen). Damit 5 statt
höchstens 4 Starts, Fahrt 3 auf Christophers ausdrückliche Entscheidung
nachgeholt.

| Fahrt | Dauer | Ziele | Heilungen | Ende | SLAM letzte min | verworfene Scans | „collision ahead“ | Kontakt / Eingriff |
|---|---|---|---|---|---|---|---|---|
| 1 | 1199 s | 4 | 5 | Teilkarte, 20-min-Budget | 15 % | 10 | 253 | nein / nein |
| 2 | 1200 s | 6 | 4 | Teilkarte, 20-min-Budget | 14 % | 7 | 307 | nein / nein |
| 3 | 976 s | 4 | 5 | **Hilfe benötigt** vor 40-cm-Mülleimer | 7 % | 7 | 43 | nein / nein |

„extrapolation into the future“ 0. Christopher: nichts berührt, kein
Eingriff, Karten und Drehstellen sauber. **Ergebnis nach den vorab
festgelegten Kriterien: nicht bestätigt** (Fahrt 3 verfehlt G1: „er steht vor
einem 40cm hohem Mülleimer und hätte genug Platz nach links und nach hinten
auszuweichen“). Im Vergleich zu SH-4 (DR-1): 1 statt 2 Hilferufe trotz Platz,
gleich berührungsfrei; SL-1 bestätigt sich erneut.

**Fahrt 3, was belegt ist:** Die Ziele lagen jenseits des Mülleimers. Die VL53
haben ihn gesehen (lokale Kostenkarte ab 0,29 m in Zielrichtung belegt), der
Kollisionsmonitor hat 31× „approach“ und 14× Langsam-Zone ausgelöst, Nav2
meldete 18× „Failed to make progress“ (weniger als 10 cm in 30 s). Sechs
Anläufe zu je etwa 1,5 min, dann griff nach 10 min ohne Fortschritt das
Hilfe-Limit, bevor die Leiter bis zur Spur-Rückfahrt kam (nur retry/defer).
Die SLAM-Karte (LiDAR, 0,66 m hoch) kennt den Eimer nicht.

**Offen:** Warum Amadeus keinen Weg um den Eimer fand. Arbeitshypothese (noch
nicht gemessen): Der Planer kennt den Eimer erst ab 0,55 m und nur als schmale
Vorderkante (VL53), plant knapp daran vorbei, und der Kollisionsmonitor bremst
dort bis zum Kriechen, sodass die Fortschrittsprüfung abbricht.

**Entscheidung des Projektinhabers (04.11.2026):** erst Daten prüfen, dann
entscheiden (Tiefenkamera oder allgemeine Einstellung). Auftrag
[SH-5N](AGENTENAUFTRAG.md): nur lesende Auszüge aus `sh5_run3` (Ziele,
Kostenkarten im Roboterrahmen, Bremsablauf je Anlauf); die geplanten Wege
schreibt Nav2 nicht ins Log. Parallel Nachbau der Stelle in der Simulation
(niedriges Hindernis 0,4 m, das nur die VL53 sehen), dort werden die Pläne
aufgezeichnet. SH-5 [archiviert](archive/20261104-sh5-ausgewertet/README.md).

**Nächster Schritt:** siehe Abschnitt 04.11.2026 (spät).

## 04.11.2026 (Kurswechsel) – zurück zur einfachen Version: SH-3 plus SL-1

**Entscheidung des Projektinhabers (04.11.2026):** keine Detaillösung für jede
Raumsituation, sondern zurück zur einfachen, real bewährten Software. In SH-4
stand Amadeus einmal vor Mülleimern, einmal vor einem hohen Bücherregal: Die
Ursache war jedes Mal dieselbe, nicht der Gegenstand. Die erste Software (SH-3)
fuhr dreimal ohne Kontakt und ohne Hilferuf.

**Bewertung, die dazu geführt hat:**
- Die DR-1-Änderungen machten das Drehen ehrlich, aber unbeholfen: Amadeus
  verweigerte jede Drehung, sobald irgendetwas näher als etwa 45 cm war
  (Eckenradius 0,414 m plus Kostenkartenraster). Sackgasse, Türstreifen,
  Mülleimer und Regal waren derselbe Fall; jede Korrektur deckte nur den
  nächsten auf.
- Die „Berührungen“ der Simulation, die DR-1 auslösten, zählen schon eine
  Annäherung auf 2 cm (Simulationskontur = Footprint + 2 cm Rand). In sieben
  realen Fahrten (SH-3, SH-4) gab es keinen Kontakt. Wir haben gegen ein
  strengeres Maß optimiert als die Wirklichkeit verlangt und dabei
  Selbstheilung verloren.

**Umgesetzt (`037c41a`):** `src/` bytegleich auf `c20436a` (SH-3-Stand plus
SL-1). Zurückgenommen: RPP-Horizont 1,5 s, Zielverschiebung 1,0 m mit Sicht,
Rückfahrt bei Drehsperre, Zieltoleranz 0,05 m, Drehraum-Regel und
6-cm-Spurtoleranz. Behalten: SL-1 (am Jetson abgenommen) und die Vorprüfung
der Fahrquellen (`9096db5`, nur Werkzeug). 171 gezielte Tests grün.
Arbeitspaket **DR-1 damit zurückgenommen, DR-2 zurückgestellt**; SH-4N wurde
nicht ausgeführt und ist [archiviert](archive/20261104-sh4n-zurueckgezogen/README.md).

**Restrisiko (bewusst angenommen):** In sehr engen Stellen kann sich Amadeus
beim Drehen wieder bis auf wenige Zentimeter an ein Hindernis herandrehen;
die VL53 sehen nur nach vorn, die Seiten deckt beim Drehen nichts ab. Falls
sich das real zeigt, gehört die Lösung an eine Stelle (etwa ein Halt im
Kollisionsmonitor, wenn der LiDAR etwas am Umriss sieht), nicht in viele
Sonderfälle; das wäre eine eigene, sicherheitsrelevante Entscheidung.

**Bestätigung SH-5 (vor der Fahrt festgelegt):** drei Laborfahrten im selben
Raum wie SH-4, Mülleimer und Bücherregal bleiben stehen. Je Fahrt C1–C5 wie
in SH-4 und **G1:** kein Ende mit „Hilfe benötigt“ an einer Stelle, an der
Christopher Platz zum Ausweichen sieht. Bestätigt, wenn alle drei Fahrten
C1–C5 und G1 erfüllen. Auftrag: [SH-5](AGENTENAUFTRAG.md).

**Nächster Schritt:** siehe Abschnitt 04.11.2026 (abends).

## 04.11.2026 – SH-4 ausgewertet: SL-1 am Jetson abgenommen, DR-1 offen

Lokaler Agent, Fahrten 03.11.2026 18:56–21:07, LAB-1 aktiv, Release
`selbstheilung-sh4-20261103_1738` (Build 174 s, 14/14 Präfixe, 178 Tests grün,
HEAD `61745d5`). Vorprüfung je Start Exit 0, alle Overlay-Werte live wie
erwartet. Missionsstart per Ersatzbefehl (App ohne Verbindung, für später
vorgemerkt). Bericht lokal beim Projektinhaber; Karten nur lokal.

| Start | Dauer | Ziele | Heilungen | Rückfahrten | Ende | SLAM letzte min | verworfene Scans | Kontakt / Eingriff |
|---|---|---|---|---|---|---|---|---|
| 1 | 1020 s | 5 | 4 | 0 | Teilkarte | 12 % | 7 | nein / nein |
| 2 | 485 s | 4 | 8 | 1 | **Hilfe benötigt** (vor zwei 50-cm-Mülleimern) | 7 % | 7 | nein / nein |
| 3, erster Versuch | 690 s | 0 | 7 | 0 | Hilfe benötigt, **nie gefahren** (Encoder-Startfehler) | 4 % | 10 | nein / nein |
| 3, Wiederholung | 521 s | 4 | 11 | 1 | **Hilfe benötigt** (neben Gegenstand) | 6 % | 9 | nein / nein |

„extrapolation into the future“ in allen Starts 0 (SH-3: 48–262), SLAM-Last
am Ende 6–12 % eines Kerns (SH-3: 61–81 %). Christopher: nichts berührt, kein
Eingriff, Karten und Drehstellen sauber (außer im ersten Versuch von Fahrt 3,
der nicht fuhr).

**Wertung des Projektinhabers (04.11.2026):** **SL-1 am Jetson abgenommen**
(C2–C4 in allen drei fahrenden Starts klar erfüllt; der Encoder-Startfehler
berührt SLAM nicht). **DR-1 bleibt offen:** berührungsfrei (E5 erfüllt), aber
die Selbstheilung ist schlechter als in SH-3 (dort alle drei Fahrten ohne
„Hilfe benötigt“). DR-1 wird zusammen mit DR-2 erneut am Jetson abgenommen.
Die Wiederholung von Fahrt 3 nach einem inneren Fehler war laut Auftrag nicht
vorgesehen; sie ist damit für SL-1 unerheblich.

**Befund 1 – Drehsperre neben Gegenständen unterhalb der LiDAR-Höhe:**
Die Mülleimer (etwa 50 cm) liegen unter der LiDAR-Ebene (0,66 m); die
SLAM-Karte kennt sie nicht (nächstes Hindernis 0,75 m), nur die VL53 haben sie
in die lokale Kostenkarte eingetragen (belegte Zellen ab 0,29 m neben der
Robotermitte; Wiederholung: 0,36 m). Der Eckenradius beim Drehen ist 0,414 m:
Die mit DR-1 ehrliche Drehprüfung verweigert jede Drehung, die diesen Kreis
schneidet. Vor DR-1 übersah RPP solche Stellen und drehte trotzdem. Die
Heilungsleiter fand keinen Ausweg: eine Spurrückfahrt (0,23 bzw. 0,40 m,
`turn_blocked: true`), keine zweite, kein Umsehen, danach sieben Ziele in
verschiedenen Richtungen, die alle eine Drehung verlangten. „detected collision
ahead“ 772 bzw. 1055 (SH-3: 202–407). Das Problem betrifft also nicht nur
Engstellen, sondern jede Stelle mit einem niedrigen Gegenstand dicht neben
Amadeus – in einer Wohnung alltäglich.

**Befund 2 – Vorprüfung erkannte nicht bereite Fahrquellen nicht:** Im ersten
Versuch von Fahrt 3 war die Encoder-Zeitwache `fault_latched`, die Fusion
meldete `sources_ready: false`; die Vorprüfung zeigte trotzdem „bestanden“,
der Roboter bekam nie einen Fahrbefehl durch. **Behoben** im Prüfskript:
Mit `--aktiv` prüft Bereich „D Quellen“ jetzt Encoder frisch, Zeitwache
„ready“ und im HWT-Weg Fusion `sources_ready` ohne verriegelten Fehler (nur
lesend mitgehört; „STARTUP“ vor der Mission gilt als normal). Tests mit den
Werten aus dem Bericht.

**DR-2 erweitert (vor der Messung festgelegt):** Ziel jetzt auch „aus einer
Drehsperre neben einem Gegenstand unterhalb der LiDAR-Höhe selbst
herauskommen“. Zusätzliche Kriterien zu F1–F4:

| Nr | Kriterium |
|---|---|
| F5 | Simulation: ein 0,5 m hoher Gegenstand, den nur die VL53 sehen, steht dicht neben dem Weg; 3/3 Läufe ohne „Hilfe benötigt“ und ohne Berührung |
| F6 | Jetson (SH-5, drei Laborfahrten mit Gegenständen wie in SH-4): keine Berührung, kein Ende mit „Hilfe benötigt“ an Stellen, an denen Christopher Platz zum Ausweichen sieht; dann gilt auch DR-1 als abgenommen |

**Entscheidung des Projektinhabers (04.11.2026):** erst Daten, dann Lösung.
Auftrag [SH-4N](AGENTENAUFTRAG.md): nur lesende Nachlieferung der Rohdaten an
den zwei „Hilfe benötigt“-Stellen; danach Nachbau in der Simulation und ein
Lösungskandidat (Kandidaten wie in DR-2).

**Nächster Schritt:** überholt, siehe Abschnitt 04.11.2026 (Kurswechsel).

## 03.11.2026 (Nachmittag) – DR-1 mit Abweichung abgenommen, SH-4 aktiviert, DR-2 festgelegt

**Entscheidung des Projektinhabers (03.11.2026, dritte):** DR-1 wird mit
dokumentierter Abweichung abgenommen. Das Ziel „Drehungen bringen die
gepolsterte Kontur nie an ein bekanntes Hindernis“ ist erreicht. „Hilfe
benötigt“ in Engstellen unter etwa 0,9 m ohne Berührung bleibt die offene
Grenze und wird als eigenes Arbeitspaket DR-2 vor Stufe 3 gelöst. Die
Drehraum-Regel für Ziele ist wieder aus (`61e7b66`), die 6-cm-Spurtoleranz
bleibt. SH-4 wird aktiviert.

**Warum die Drehraum-Regel aus ist:** Mit 0,45 m Mindestabstand (`e41507b`)
endete jede Mission zunächst ohne ein Ziel; einzelne unbekannte Zellen
zwischen den Laserstrahlen zählten als Hindernis (Startkarte höchstens 0,31 m).
Gegen Belegtes geprüft (`2f48d00`) fuhr Amadeus los, erkundete aber den
zweiten Raum nie (Abdeckung 0,72): Ein Gang oder eine Tür hat per Definition
keinen Drehraum, die Frontier dahinter bekam kein Ziel. Engstelle zum
Durchfahren und Falle zum Stehenbleiben liegen beide bei 0,27–0,36 m und sind
am Abstand allein nicht zu unterscheiden.

**DR-1 in Zahlen** ([Beleg](evidence/dr1-simulation-20261103.json)):

| Stand | Läufe | bestanden | Berührungen | „Hilfe benötigt“ |
|---|---|---|---|---|
| Ausgangslage `299a3b1` (Messung) | 3 | 1 | 2 | 0 |
| K1 Polster 0,05 m (verworfen) | 3 | 1 | 2 | 0 |
| K2 RPP-Horizont 1,5 s | 4 | 3 | 0 | 1 |
| `c70f6a0` K2+K4 (Abnahme, abgebrochen) | 9 | 7 | 0 | 2 |
| `6cf41b5` + Rückfahrt 2×0,4 m, Zieltoleranz 0,05 m (Abnahme, angehalten) | 12 | 9 | 0 | 3 |
| `e41507b`/`2f48d00` Drehraum-Regel (verworfen) | 4 | 0 | 0 | 0 |
| **`61e7b66` Freigabestand (Regressionscheck)** | 4 | 4 | 0 | 0 |

Seit der Reglerkorrektur `43f74b7`: 33 Läufe (30 mit Fahrt) Läufe, **0 Berührungen**
(vorher 4 in 6). Verfehlt nach den vorab festgelegten Kriterien: E2 (gesperrte
Tür 1/2) und E3 (Tür 0,68 m 1/2); E1 (8 Referenzläufe ohne Berührung) ist in
Summe erfüllt, aber nicht in einer geschlossenen Abnahme auf einem Stand; E4
(Median Heilungen ≤ 5) am Rand (5). Diese Abweichungen gelten nach der
Entscheidung oben als begründet; das Arbeitspaket DR-1 ist abgeschlossen,
SL-1 Stufe B damit ebenfalls (B1/B3 mit derselben Abweichung).

**Regressionscheck des Freigabestands `61e7b66`** (4 Läufe, ein Stand, ohne
Experiment): Referenz 2/2 (einmal vollständig, 2 bzw. 5 Heilungen), gesperrte
Tür bestanden (aus der Verbindung mit drei Spur-Rückfahrten selbst heraus,
danach Teilkarte wie vorgesehen), Tür 0,68 m bestanden (engster Plan 0,27 m),
Mindestabstand 2,6–6,3 cm, Abdeckung 0,969–0,974. Vier Läufe belegen die
Engstellen nicht; das bleibt Aufgabe von DR-2.

**Was am Jetson anders ist (alles nur `self_healing:=true`):** RPP-Horizont
1,5 s, Zieltoleranz 0,05 m, Zielverschiebung bis 1,0 m mit Sicht auf die
Frontier, Drehsperre → Zurückdrehen und bis 2 × 0,4 m Spur-Rückfahrt (6 cm
seitlich), dazu SL-1 (SLAM-Knoten ab 0,25 m / 0,35 rad). 178 gezielte Tests.

## 03.11.2026 – Arbeitspaket DR-2: Selbstheilung in Engstellen (vor der Messung festgelegt)

| | |
|---|---|
| Planversion | MASTERPLAN v1.3 mit Nutzerentscheidungen bis 03.11.2026 |
| WE-Bezug | WE-M3, Vorbedingung für Stufe 3 |
| Istbasis | `61e7b66`: In Engstellen unter etwa 0,9 m (0,84-m-Verbindung hinter geschlossener Tür, 0,91-m-Streifen hinter der 0,68-m-Tür, Mündung einer 0,42-m-Lücke) kann Amadeus nicht drehen; die gerade Spur-Rückfahrt reicht nicht immer heraus, dann „Hilfe benötigt“ (ohne Berührung) |
| Ziel | Aus solchen Stellen kommt Amadeus selbst heraus und erkundet weiter, ohne Berührung und ohne blind rückwärts zu fahren |
| Nicht-Ziele | keine Rückkehr zum alten Regler-Horizont, keine Änderung an `collision_monitor`, VL53, Fahrtor, SLAM, Chassis-Footprint oder Simulationskontur; Rückwärts nur über selbst befahrene oder gemessen freie Fläche; AP06 unverändert |
| Kandidaten (erst messen) | (a) Rückfahrt entlang der gekrümmten eigenen Spur (Pfadfolge rückwärts statt gerader BackUp-Strecke), (b) geplantes Wendemanöver über bekannt freie Fläche (mehrzügig vor/zurück), (c) Ziele mit Wissen, ob dahinter weitergefahren werden kann |
| Rückfall | Profilwerte bzw. Commits zurücknehmen, `self_healing:=false` |

**Abnahmekriterien** (Simulation, Manifest v4, ein geschlossener Stand):

| Nr | Kriterium |
|---|---|
| F1 | gesperrte Tür 3/3 bestanden (nicht „Hilfe benötigt“) |
| F2 | Tür 0,68 m 3/3 bestanden, engster Plan ≥ 0,20 m |
| F3 | 8 Referenzläufe: 0 Berührungen, Abdeckung im Median ≥ 0,95, Heilungen im Median ≤ 5 |
| F4 | Sensorlücke, Kartenrennen, Rechenlast je 2/2; keine Berührung außer der bekannten niedrigen Kiste |

**Nächster Schritt:** siehe Abschnitt 04.11.2026.

## 02.11.2026 (nachts) – Arbeitspaket SL-1: SLAM-Last begrenzen (vor der Messung festgelegt)

Auftrag des Projektinhabers: Punkt 1 aus der SH-3-Auswertung strukturiert
bearbeiten und abnehmen. Die Kriterien unten stehen **vor der ersten Messung**
fest und werden nicht nachträglich verschoben; erreicht ein Kandidat sie
nicht, ist SL-1 nicht abgenommen.

| | |
|---|---|
| Planversion | MASTERPLAN v1.3 mit Nutzerentscheidungen bis 02.11.2026 |
| WE-Bezug | WE-M3 (metrischer Erkundungskern), Vorbedingung für Abnahmestufe 3 |
| Istbasis | `cc5eddc` (Produktcode = `3a05e6b`); SH-3: `slam_toolbox` bis 85–95 % eines Kerns nach 20 min, 80–162 verworfene Scans, 48–262 Reglerabbrüche wegen altem `map`→`odom` je Fahrt |
| Ziel | `slam_toolbox` hält über eine ganze Erkundung Schritt: begrenzte Last, keine verworfenen Scans, frisches `map`→`odom` |
| Nicht-Ziele | kein gröberes Kartenraster (1 cm bleibt, X12 brachte Pläne näher an Türpfosten), keine Änderung der Ringschluss-Schwellen (X7), kein anderes SLAM, keine Änderung an Explorer, Nav2, Fahrtor, `collision_monitor`, VL53 oder AP06 (`self_healing:=false` unverändert) |
| Ort der Änderung | nur `slam_toolbox_self_healing.yaml` (lädt nur mit `self_healing:=true`) |
| Rückfall | Overlay-Einträge entfernen, `self_healing:=false` oder Release vor der Änderung |

**Ausgangsverdacht (noch nicht gemessen):** `minimum_travel_distance` steht
seit 13.08.2026 vorläufig auf 0,01 m („für ersten A/B-Test beibehalten“).
Dann entsteht schon nach 1 cm Fahrt ein neuer Graphknoten, bis zu 5 je
Sekunde; Kartenneuaufbau (jede Sekunde, 1 cm) und Ringschlusssuche werden mit
jedem Knoten teurer. Drehungen erzeugen Knoten über `minimum_travel_heading`
(0,15 rad) dank des Humble-Fixes #808 und
`check_min_dist_and_heading_precisely`.

**Vorgehen:** (1) Prüfstand: eine Simulationsfahrt aufzeichnen und nur
`slam_toolbox` mit denselben Daten mehrfach abspielen, je Lauf ein Parameter
geändert. (2) Kandidat auswählen. (3) Geschlossene Simulation als Regression.
(4) Abnahme am Jetson mit drei Laborfahrten (SH-4).

**Abnahmekriterien:**

| Nr | Stufe | Kriterium |
|---|---|---|
| A1 | Prüfstand | `slam_toolbox`-Last im Mittel der letzten 2 min ≤ 50 % des Ausgangswerts derselben Aufnahme |
| A2 | Prüfstand | 0 verworfene Scans („queue is full“) |
| A3 | Prüfstand | `map`→`odom` älter als 0,25 s in höchstens 0,5 % der Stichproben (20 Hz) |
| A4 | Prüfstand | Kartenfehler ≤ 0,10 m und höchstens 2 cm schlechter als der Ausgangswert, Abdeckung der erreichbaren Fläche ≥ 95 % |
| B1 | Simulation v4, 2 Durchgänge | Referenz, Sensorlücke, Kartenrennen, Rechenlast, gesperrte Tür je 2/2 (Box bleibt bekannte Grenze), kein neuer Kontakt |
| B2 | Simulation v4 | Reglerabbrüche „extrapolation into the future“ je Lauf im Median ≤ 11 (`bb94311`: Median 44,5) |
| B3 | Simulation, Tür 0,68 m | besteht; engster Plan ≥ 0,20 m (Produkt heute 0,23 m) |
| C1 | Jetson SH-4, 3 Laborfahrten | Kriterien der Stufe 1 wieder 3/3 |
| C2 | Jetson SH-4 | `slam_toolbox` in der letzten Minute jeder Fahrt ≤ 50 % eines Kerns (SH-3: 60–95 %) |
| C3 | Jetson SH-4 | ≤ 10 verworfene Scans je Fahrt (SH-3: 80–162) |
| C4 | Jetson SH-4 | ≤ 40 „extrapolation into the future“ je Fahrt (SH-3: 48–262) |
| C5 | Jetson SH-4 | Karten nach Christophers Ansicht sauber, auch an Stellen, an denen sich Amadeus gedreht hat |

**Nächster Schritt:** Prüfstand bauen und Ausgangswerte messen.

### SL-1 Zwischenstand 03.11.2026: Stufe A erfüllt, Stufe B nicht bestanden

**Stufe A (Prüfstand, `c20436a`):** Ursache gemessen. Last am Ende einer
aufgezeichneten Fahrt (nur SLAM, gleiche Daten): Basis 82/82 % eines Kerns,
Knoten ab 10 cm 23 %, ab 25 cm 18/19 %, Karte alle 5 s 37 %, Scan-Takt 0,5 s
70 %, ohne Ringschluss 63 %, **Kandidat 25 cm / 0,35 rad 11 %**. Kandidat:
A1 erfüllt (11 ≤ 41), A3 erfüllt (0,15 % zu altes `map`→`odom`), A4 erfüllt
(Kartenfehler 2,8 statt 7,1 cm, Abdeckung 97,9 %). **A2 wörtlich verfehlt:**
9–10 verworfene Scans bleiben; dieselben 9 Stellen auch bei praktisch
untätigem SLAM (Leerlaufmessung), also Lücken der Aufnahme, lastbedingt 0
statt 51–56. Entscheidung über diese Abweichung beim Projektinhaber.
Eigene Messfehler unterwegs gefunden und behoben: Altersmessung lief 5 s
über das Abspielende hinaus (täuschte eine zweite Ursache vor), Zuordnung der
verworfenen Scans. [Beleg](evidence/sl1-pruefstand-20261102.json).

**Stufe B (geschlossene Simulation):** [Beleg](evidence/sl1-simulation-20261102.json).
B2 klar erfüllt: Reglerabbrüche wegen altem `map`→`odom` 0–13 statt 16–74 je
Lauf, SLAM-Last 4–17 % statt bis 109 %, vier Szenarien erstmals
„vollständig“ mit 1–3 statt 7–16 Heilungen und 11–18 m statt 5–6 m Strecke.
**B1 und B3 verfehlt:** Berührungen an der Insel (mehrfach), in der
0,84-m-Verbindung und im 0,68-m-Türtest, jeweils beim Drehen auf der Stelle
mit 0,31–0,36 m Mittenabstand (Eckenradius 0,414 m), das Hindernis stand
jeweils in der lokalen Kostenkarte.

Ursachen, gemessen:
1. **Simulatorfehler:** Der 100-Hz-Physiktakt ließ den Sensortakt in derselben
   Callback-Gruppe phasenweise über 1 s verhungern (bis 99 VL53-Lücken je
   Lauf); der Explorer brach dann alle 2–3 s ab und startete mit einer
   Drehung neu. Korrigiert (eigene Gruppe für den Sensortakt): 0 Lücken.
2. **Bestehende Produktschwäche, nicht SLAM:** Auch ohne Lücken berührte der
   Kandidat die Insel: Der Regler meldet „collision ahead“, hält an, dreht im
   nächsten Zyklus ein Stück weiter, die Ecke kriecht ans Hindernis.
   **Kontrolle mit den alten SLAM-Werten** unter gleichen Bedingungen:
   ebenfalls Berührung an der Insel (1 von 4 Läufen). Mit alten Werten kommt
   der Roboter wegen der vielen Abbrüche nur 5 m weit und selten an die
   Insel; mit SL-1 erkundet er vollständig und erreicht die Insel in 6 von 9
   Läufen. SL-1 legt die Schwäche also offen, verursacht sie aber nicht.
3. Der Explorer fährt nach einer Quellenstörung sofort wieder an, ohne
   Beruhigungszeit; flackernde Quellen erzeugen Neustarts mit Drehung.

**Bewertung:** SL-1 erreicht sein Ziel (SLAM hält Schritt), ist aber nach den
vorab festgelegten Regeln **nicht abgenommen**, weil B1/B3 verfehlt sind.
SH-4 (Jetson) wird deshalb **nicht** erteilt: Mit SL-1 würde der Roboter auch
real länger und in engeren Bereichen fahren, die Drehschwäche ist dort
ungelöst. Der Kandidat bleibt im Code (nur `self_healing`, noch kein Jetson-
Build); Rückfall wie oben.

**Nächster Schritt:** Entscheidung des Projektinhabers zur Drehschwäche
(eigenes Arbeitspaket mit vorab festen Kriterien), danach Stufe B für SL-1
wiederholen.

**Entscheidungen des Projektinhabers (03.11.2026):** (1) Erst die
Drehschwäche lösen, danach SL-1 Stufe B wiederholen und erst dann am Jetson
abnehmen. (2) A2 gilt als **begründete Abweichung**: Die 9 verbliebenen
verworfenen Scans stammen nachweislich aus der Aufnahme; maßgeblich für
verworfene Scans bleibt C3 am Jetson.

## 03.11.2026 – Arbeitspaket DR-1: Drehen nahe Hindernissen absichern (vor der Messung festgelegt)

| | |
|---|---|
| Planversion | MASTERPLAN v1.3 mit Nutzerentscheidungen bis 03.11.2026 |
| WE-Bezug | WE-M3, Vorbedingung für SL-1 und Stufe 3 |
| Istbasis | `79f0f38`: mit SL-1 berührt der Roboter in der Simulation beim Drehen auf der Stelle die Insel (5 von 10 Kandidatläufen), die 0,84-m-Verbindung und den Pfosten der 0,68-m-Tür; mit alten SLAM-Werten ebenfalls (1 von 4), nur seltener erreicht. Hindernis jeweils in der lokalen Kostenkarte |
| Ziel | Drehungen auf der Stelle bringen die gepolsterte Kontur nie an ein bekanntes Hindernis; Neustarts nach Quellenstörungen erzeugen keine Drehkaskaden |
| Nicht-Ziele | keine Änderung von Chassis-Footprint, Simulationskontur (fest −0,13…0,33 m × ±0,25 m), `collision_monitor`, VL53, Fahrtor oder SLAM; 0,68-m-Türen bleiben befahrbar; AP06 (`self_healing:=false`) unverändert |
| Ort der Änderung | nach Messung; bevorzugt nur Selbstheilungs-Overlays bzw. Selbstheilungs-Explorer |
| Rückfall | Overlay-Einträge bzw. Commit zurücknehmen, `self_healing:=false` |

**Arbeitshypothese (noch nicht gemessen):** Die lokale Kostenkarte rechnet in
5-cm-Zellen, der Regler prüft beim Drehen nur den Umriss des Footprints an
einer vorausberechneten Stellung (etwa 0,12 rad). Eine Ecke kann so bis zu
eine Zelle in ein Hindernis schwenken, bevor eine tödliche Zelle auf dem
Umriss liegt; die Polsterung beträgt nur 2 cm. Dazu: Bei „collision ahead“
hält der Regler, versucht es im nächsten Zyklus erneut, die Ecke kriecht
heran.

**Vorgehen:** (1) Simulation zeichnet bei der ersten Berührung den Verlauf
der Fahrbefehle und die Kostenkarte unter dem Footprint auf. (2) Ursache
bestätigen oder verwerfen. (3) Kandidat. (4) Abnahme zusammen mit der
Wiederholung von SL-1 Stufe B.

**Abnahmekriterien** (Simulation mit SL-1-Kandidat und korrigiertem
Simulatortakt; Kontakt = Berührung der festen Simulationskontur):

| Nr | Kriterium |
|---|---|
| E1 | 8 Referenzläufe (Manifest v4): 0 Berührungen (Ausgangslage 5 von 10) |
| E2 | Manifest v4, 2 Durchgänge: Referenz, Sensorlücke, Kartenrennen, Rechenlast, gesperrte Tür je 2/2, keine Berührung außer der bekannten niedrigen Kiste (= SL-1 B1) |
| E3 | Tür 0,68 m, 2 Läufe: bestanden, keine Berührung, engster Plan ≥ 0,20 m (= SL-1 B3) |
| E4 | Erkundung nicht schlechter als mit dem SL-1-Kandidaten: in den Referenzläufen Abdeckung im Median ≥ 0,95, Ziele im Median ≥ 5, Heilungen im Median ≤ 5 |
| E5 | Jetson SH-4: zusätzlich zu C1–C5 keine Berührung (Christopher) in allen drei Fahrten |

### DR-1 Messung 03.11.2026: Ursache gefunden, Kandidat K1 verworfen

**Aufzeichnung (`299a3b1`):** Die Simulation friert bei der ersten Berührung
die letzten 6 s Pose, Roh- und Endbefehle und die lokale Kostenkarte unter
der Kontur ein. Drei Messläufe mit dem Produktstand: 1 bestanden, 2
Berührungen, beide an derselben Inselecke (1,55|0,30), beide beim Drehen auf
der Stelle.

**Befund:** RPP befiehlt −0,10…−0,11 rad/s, nach der 30-%-Bremse des
`collision_monitor` kommen −0,03 rad/s an. Alle 0,5–1 s wechselt RPP zwischen
Drehen und „collision ahead“; die Kontur kriecht dabei 1–2 mm je Phase bis
zur Berührung. In der lokalen Kostenkarte liegt bei der Berührung **keine**
tödliche Zelle auf oder unter der Kontur (Umriss höchstens 99), die nächste
tödliche Zellmitte liegt 3,2–3,5 cm außerhalb.

**Mechanismus:**
1. RPP rechnet Drehungen nur bis `max_allowed_time_to_collision_up_to_carrot`
   voraus (Nav2-Standard 1,0 s, bei uns nicht gesetzt). Ein Drehschritt dauert
   2·sin(0,025/0,414)/|w| = 1,2 s bei 0,1 rad/s. RPP projiziert beim langsamen
   Drehen also **gar nicht voraus** und prüft nur die aktuelle Stellung.
2. Genau diese Fläche räumt die Hindernisschicht der lokalen Kostenkarte bei
   jeder Aktualisierung frei (`footprint_clearing_enabled`, Nav2-Standard):
   Zellen unter dem gepolsterten Footprint gelten als frei. Was die Kontur
   berührt, sieht RPP deshalb nicht; nur Rasterungsunterschiede lassen die
   Prüfung zeitweise anschlagen, daher das Wechseln und Kriechen. Punkt 2 ist
   aus dem Nav2-Verhalten und den Kostenkarten-Befunden abgeleitet, nicht
   einzeln abgeschaltet und nachgemessen.
3. Ort: Ziele an engen Stellen. Beispiel aus K1: Ziel in der Mündung der
   0,42-m-Lücke zwischen Insel und blockierter Alternative, 0,25 m vor der
   Blockecke; das nächste Ziel verlangt dort eine Drehung um 2,4 rad, die nach
   keiner Seite frei ist. In der 0,84-m-Verbindung ist der Drehkreis der
   Kontur (0,414 m) fast so groß wie der halbe Gang (0,42 m).

Die Arbeitshypothese (Ecke schwenkt eine Zelle vor) trifft damit nur am Rand
zu. Entscheidend sind die fehlende Vorausrechnung und das Freiräumen unter
dem Footprint.

**Kandidat K1, lokale Polsterung 0,05 statt 0,02 m: verworfen.** Drei
Referenzläufe: einer bestanden (3,2 cm Abstand, aber 7 Heilungen nach 60 s
Stillstand), zweimal **Berührung an der Inselecke**, Abdeckung 0,91/0,92,
6 bzw. 13 Heilungen. Dazu lange Stillstände in der 0,84-m-Verbindung
(Drehradius mit Polster 0,456 m > halber Gang) und in der Lückenmündung.
Mehr Polster vergrößert zugleich die freigeräumte Fläche und ändert an
Punkt 1 nichts. Die übrigen K1-Läufe wurden nicht mehr gestartet.

**Kandidat K2 (`43f74b7`): RPP-Horizont 1,5 s statt 1,0 s, nur
Selbstheilungs-Overlay.** Bei 0,1 rad/s prüft RPP damit einen Drehschritt
(0,12 rad) voraus, also außerhalb der freigeräumten Fläche; geradeaus
0,10 statt 0,05 m. Der Stillstandsprüfer prüft den Wert am Jetson mit.

| Lauf | Ergebnis | Ziele | Heilungen | Mindestabstand | Abdeckung |
|---|---|---|---|---|---|
| 1 (Experiment) | vollständig | 9 | 2 | 5,9 cm | 0,978 |
| 2 (Experiment) | vollständig | 6 | 4 | 4,4 cm | 0,972 |
| 3 (Experiment) | **Hilfe benötigt** nach 279 s | 3 | 9 | 4,1 cm | 0,904 |
| 4 (Produkt `43f74b7`) | vollständig | 8 | 7 | 3,1 cm | 0,971 |

**Keine Berührung mehr (0 von 4).** Die Drehschwäche zeigt sich jetzt als
Stillstand statt als Kriechen an die Ecke. Lauf 3: Das Ziel für die Frontier
der 0,42-m-Lücke lag 0,27 m vor der Blockecke (exakter Abstand auf der
Endkarte). Dort war keine Drehung frei, die Rückfahrt auf der Spur reichte nur
0,14 m (danach 0,44 m Abstand, mit 5-cm-Zellen und Vorausprüfung noch zu eng),
nach 8 Fehlschlägen „Hilfe benötigt“. Ziele sollen 0,45 m Abstand haben;
gab es im Umkreis von 0,5 m keine solche Zelle, nahm die Auswahl die
geräumigste dort, ohne Untergrenze. Im Umkreis von 1 m gab es Stellen mit
0,5 m. Heilungen im Median 5,5: E4 wäre mit K2 allein verfehlt.

**Kandidat K3 (Explorer: Drehsperre am Ort → sofort zurück auf der Spur):
vorbereitet, nicht übernommen.** In Lauf 2 löste Zurückstellen eine Drehsperre
hinter der Tür nach zwei Fehlschlägen; die Rückfahrt hätte den Roboter dort in
die noch engere 0,84-m-Verbindung gesetzt, und in Lauf 3 war die gerade Spur
ohnehin zu kurz.

**Kandidat K4 (`c70f6a0`): Ziel bis 1,0 m verschieben, nur mit freier Sicht
auf die Frontier.** Profilwert `self_healing_goal_shift_max_m` 0,5 → 1,0. Ein
verschobenes Ziel muss die Frontier-Zelle über bekannt freie Zellen sehen;
offline lag ein um 1 m verschobenes Ziel ohne diese Bedingung hinter der
Insel. Offline auf drei Endkarten: kein Ziel enger als bisher, enge Ziele
0,18–0,23 → 0,33–0,36 m; Auswahl 47–68 statt 12–16 ms auf der 1-cm-Karte.
Zwei neue Tests (Lückenmündung; Wand zwischen Frontier und Halle, ohne
Sichtprüfung rot).

**Abnahme auf `c70f6a0` (K2+K4), nach 9 von 20 Läufen beendet:** 0
Berührungen, Mindestabstand 2,9–7,4 cm, engster Plan der 0,68-m-Tür 0,255 m
(E3-Grenze 0,20). Referenz 2 von 3, Sensorlücke, Kartenrennen, Rechenlast,
Hindernis im Weg (diesmal ohne Berührung der niedrigen Kiste, Einzelbefund)
und Tür 0,68 m bestanden, Kartenrennen/Rechenlast aber nur als Teilkarte.
**Zwei Läufe „Hilfe benötigt“, E2 damit verfehlt:**
1. *Gesperrte Tür:* Hinter der geschlossenen Tür steht der Roboter mitten in
   der 0,84-m-Verbindung. Die Wände liegen in der Kostenkarte ab 0,40 m, der
   Drehradius ist 0,414 m: Drehen ist dort ehrlich nicht möglich (vorher drehte
   er nur, weil die Hindernisschicht die Wand unter dem Umriss freiräumte).
   Heraus führen nur rund 0,8 m zurück; H4 erlaubte 0,4 m einmal je
   Stillstand, und die angesetzte Drehung hatte die Spur schon aus der Flucht
   gebracht (keine Rückfahrt).
2. *Referenz:* Nav2 meldete das Ziel 0,14 m vor dem Punkt mit Drehraum als
   erreicht (Zieltoleranz 0,15 m); Halt 0,40 m neben dem Türpfosten, die
   übrigen Ziele lagen hinter dem Roboter, die Spur führte zurück in die Tür.

Die Sitzung wurde danach neu gestartet; die laufende Simulation endete
dabei, die 9 Ergebnisse sind vollständig ausgewertet.

**Entscheidung des Projektinhabers (03.11.2026):** Bei Drehsperre darf die
Rückfahrt erweitert werden: erst die angesetzte Drehung zurücknehmen, dann auf
der eigenen Spur zurück, bis zu 2 × 0,4 m je Stillstand statt 1 ×.

**Umgesetzt:**
- `8bfb0b9` (Entscheidung oben): Drehsperre = im Versuch nicht vom Fleck
  (< 5 cm) und Drehkreis nicht frei. Dann sofort Zurückdrehen (höchstens
  0,8 rad, nur über die eben überstrichene Fläche) und Rückfahrt, bis zu 2 ×
  0,4 m, weiter 0,05 m/s und nur gerader eigener Spurabschnitt; das Ziel wird
  dabei nicht zurückgestellt. Mit freiem Drehkreis bleibt die Leiter wie
  bisher. Rückfall `self_healing_blocked_track_backs: 0`.
- `6cf41b5`: Zieltoleranz im Selbstheilungs-Overlay 0,05 statt 0,15 m, damit
  der Roboter dort hält, wo die Zielwahl Drehraum zugesichert hat.

175 gezielte Tests grün (SH-4-Auswahl).

**Abnahme auf `6cf41b5`, nach 12 von 20 Plätzen angehalten:** 0
Berührungen. Gesperrte Tür 1/2 (der erste Lauf kam mit einer sofortigen
Rückfahrt und 1 Heilung frei), Tür 0,68 m 1/2, Referenz 4/4 (zwei davon
vollständig mit je 1 Heilung), Sensorlücke, Kartenrennen, Rechenlast
bestanden; „Hindernis im Weg“ „Hilfe benötigt“ ohne Berührung (nicht Teil von
E2). E2/E3 damit erneut verfehlt:
1. *Gesperrte Tür, Lauf 2:* Die eigene Spur in der Verbindung galt nur auf
   0,13 m als gerade (≤ 3 cm seitlich), die zweite Rückfahrt war nicht
   möglich.
2. *Tür 0,68 m, Lauf 2:* Notziel 0,36 m vor der Insel im 0,91-m-Streifen
   hinter der Tür, dort keine Drehung frei, trotz vier Rückfahrten
   „Hilfe benötigt“.

**Entscheidung des Projektinhabers (03.11.2026, zweite):** weiter iterieren:
Rückfahrt bis 6 cm seitliche Abweichung und Ziele nur noch mit Drehraum.

**Umgesetzt (`e41507b`):** `self_healing_goal_min_clearance_m` 0,45: Ohne
Punkt mit Drehraum an der Frontier oder im Umkreis von 1 m mit Sicht auf sie
wird die Frontier nicht angefahren; sie bleibt offen. H4 seitlich 6 statt
3 cm. 176 gezielte Tests grün. Offline fallen auf den Endkarten früherer Läufe
vor allem die engen Restziele weg, an denen diese Läufe hängen blieben; ob die
Abdeckung hält, zeigt E4.

**Abnahme neu gestartet** auf `e41507b`, 20 Plätze, fortsetzbar, mit
Neubau und Installationsprüfung vor dem ersten Lauf.

**Nächster Schritt:** siehe Abschnitt 03.11.2026 (Nachmittag).

## 02.11.2026 (abends) – SH-3: Abnahmestufe 1 bestanden

Lokaler Agent, Fahrten 16:16–17:41, LAB-1 aktiv, Release
`selbstheilung-sh2-20261102_1107` ohne neuen Build (Schritt 0: Code in
`src/`/`tools/` = `3a05e6b`), Klon `ee35eaf`. Bericht lokal beim
Projektinhaber; Karten nur lokal. Erste autonome Fahrten der Hauptlinie.

| Fahrt | Dauer | Ziele | Heilungen | Ende | Strecke | VL53-Lücke | Kontakt / Eingriff |
|---|---|---|---|---|---|---|---|
| 1 | 649 s | 6 | 1 | Teilkarte, übrige Frontiers unerreichbar | 5,2 m | 8,7 s | nein / nein |
| 2 | 1199 s | 6 | 5 (1× Umsehen) | Teilkarte, 20-min-Budget | 7,0 m | 6,1 s | nein / nein |
| 3 | 1200 s | 5 | 4 | Teilkarte, 20-min-Budget | 6,5 m | 7,6 s | nein / nein |

Je Fahrt: Vorprüfung `--aktiv` Exit 0 (D: `base_hardware` scharf,
`/cmd_vel` still), 39 Knoten, `automatisch_erfuellt: true`, Nav2 danach
aktiv, kein „process has died“ vor dem Stopp, HWT am Ende `HEALTHY` (Fahrt 2:
zwei HWT-HOLD von ~1 s, selbst erholt), höchstens 0,10 m/s und 0,20 rad/s.
Christopher: kein Kontakt, kein Eingriff, alle drei Karten „sauber“ (als Bild
angesehen, nach Fahrt 1 zunächst „nicht angesehen“). Die Aufbau-Bitte (Türen
zu, flache Gegenstände weg) beantwortete er mit „alles bereit“; einzeln
bestätigt wurde sie nicht. Missionsstart per Ersatzbefehl, weil die App nicht
verfügbar war; der App-Weg ist damit noch nicht real geprüft.

**Bewertung: Abnahmestufe 1 bestanden** (alle drei Kriterien in allen drei
Fahrten). Die Heilungsleiter hat jeden Zwischenfall selbst aufgefangen.

**Kritisch, mit Blick auf Stufe 3:**
1. **SLAM-Last wie in der Simulation vorhergesagt:** `slam_toolbox` stieg von
   etwa 4 % auf 60–70 % (11 min) bzw. 85–95 % eines Kerns (20 min), im
   Laborraum. Dazu „Message Filter dropping message … queue is full“
   80/162/150× (Scans verworfen), 48/262/186 Reglerabbrüche wegen zu altem
   `map`→`odom`, 136/438/344× „missed its desired rate“ und 1/9/1×
   `localization_missing_or_stale` (einmal 1,5 s ohne `map`→`odom`). Die
   Simulation zeigte denselben Verlauf (25 → 80 % in 8 min). In einer Wohnung
   mit mehr Fläche und längerer Fahrt ist ein voller Kern zu erwarten; dann
   verliert SLAM Scans und die Lokalisierung bricht häufiger weg. **Vor Stufe 3
   zu lösen.**
2. **Langsamer Fortschritt:** Fahrt 2 und 3 endeten am 20-min-Budget, keine
   Fahrt „vollständig“. Heilungen vor allem `nav_timeout` (Ziel nach 150 s
   nicht erreicht, Fahrt 3 viermal im 152-s-Takt); dazu 49/202/407×
   „detected collision ahead“ (RPP hält vor vermeintlicher Kollision). Für
   eine Wohnung reicht das Budget in diesem Tempo nicht.
3. **VL53-Aussetzer in jeder Fahrt** (6–9 s, `collision_monitor` ignoriert
   beide Quellen, 7/0/5× `IndexError … kein neues Frame`), wie in SH-1/SH-2:
   in allen vier Jetson-Sitzungen, etwa einmal je 10–20 min. Fahrtor und
   Explorer reagieren richtig (Halt, Warten, Weiterfahrt), die Ursache ist
   offen.
4. **`slam_toolbox` stürzte beim Herunterfahren nach Fahrt 1 ab**
   (`karto::Exception`, Exit −6), nach der Prüfung und nach dem Kartenspeichern;
   Fahrt 2 und 3 endeten sauber. Einmalig, beobachten.
5. **Missionsergebnis „failed“ bei brauchbarer Teilkarte:** Der Explorer
   beendet die Aktion bei `usable_partial` mit `abort` (`result.success` nur
   bei vollständig), der Mission-Manager meldet daher `failed`. Für den Nutzer
   sieht jede dieser Fahrten wie ein Fehler aus. Produktbefund, nicht geändert.
6. Das Fahrtprotokoll schreibt während der Fahrt nichts (nur Start und Ende).

**Nächster Schritt:** Entscheidung des Projektinhabers, womit es weitergeht;
bis dahin kein Jetson-Auftrag ([AGENTENAUFTRAG](AGENTENAUFTRAG.md)). SH-3
[archiviert](archive/20261102-sh3-bestanden/README.md).

## 02.11.2026 (Lauf 2) – SH-2 bestanden, SH-3 aktiviert

Lokaler Agent, 02.11.2026 11:07–11:45, motorlos nach LAB-1. Klon auf
`3a05e6b`, neuer Release `selbstheilung-sh2-20261102_1107` (Bericht lokal beim
Projektinhaber, nicht im Repository; Bericht aus Lauf 1 unverändert).

- Build 14/14 (171 s), `168 passed`.
- HWT-Weg: HWT601 verbunden, Christophers Stillstandsantwort „ja“, kein
  `TERMINAL_FAULT`, 39 Knoten in beiden Listen, Nav2 aktiv.
- Prüfung A–D **Exit 0** im ersten Versuch; D neu „kein Motorschreiber
  (HWT-Weg ohne active_drive) – base_hardware nicht gestartet,
  Encoder-Shadow sichtbar“. Die Korrektur `fe84eec` wirkt.
- VL53-Messreihe Nr 0–8 vollständig, `filter_ueber_boden_m` 0,07, **kein
  Treffer verworfen**; Kostenkarte vorn: Nr 0/1/5 (leer, 3 cm) 0 Zellen,
  Nr 2 (5,5 cm, 0,30 m) 1 Zelle bei 0 VL53-Treffern, Nr 6 (6,5 cm) 2,
  Nr 3/7 (10 cm) 18/14, Nr 4/8 (15/15,5 cm) 16/23. Tabelle und Folgerungen in
  [Konzept §6](KONZEPT_SELBSTHEILUNG.md).
- Geordnetes Ende in 6 s, 28/28 Prozesse sauber, einziger Schreibbefehl die
  erlaubte Kostenkarten-Leerung (9×).

**Bewertung:** SH-2 bestanden. Entscheidung 7 wirkt am Roboter: In SH-1 wurden
5,5–10-cm-Treffer noch vollständig verworfen, jetzt stehen 10- und 15-cm-
Objekte mit 14–23 Zellen in der Kostenkarte. Die Erwartung „ab Nr 2 Zellen“
ist formal erfüllt, aber nicht durch die VL53: Nr 2 hatte 0 Treffer (SH-1: 2),
die eine Zelle ist ungeklärter Herkunft. 5,5–6,5 cm sind damit Grenzfälle,
darunter sieht der VL53 nichts. Beide Messlagen liegen 0,6–0,7 m vor
`base_link`; den Nahbereich prüfen sie nicht.

**Auffällig, nicht behoben:** Während Nr 7 ignorierte `collision_monitor`
beide VL53 6 s lang (Alter 3,0–9,2 s, 250 WARN, 33 statt 39 Frames), ohne
Meldung von `vl53_near_field`. Dasselbe Muster wie in SH-1 (7 s). Beim Fahren
sperrt das Fahrtor dann nach 0,8 s und der Explorer wartet bis 30 s; das
Fahrtprotokoll in SH-3 zählt solche Lücken. Ursache (USB-I2C-Adapter?)
offen. 23 TF-Wartemeldungen nur während der HWT-Einmessung.

**SH-3 aktiviert:** Entwurf in den [Agentenauftrag](AGENTENAUFTRAG.md)
übernommen; SH-2 [archiviert](archive/20261102-sh2-bestanden/README.md). Neu
gegenüber dem Entwurf: Schritt 0 prüft, dass der Code in `src/` und `tools/`
(ohne `*.md`) dem Release-Stand `3a05e6b` entspricht (kein neuer Build), Abschnitt „Verboten“,
erwartete D-Zeilen und Wiederholungsregel wie in SH-2, Knotenliste zweimal,
Hinweis auf kurzes Stehenbleiben bei VL53-Lücken. Im Code geprüft:
`active_drive:=true` setzt `dry_run` false und `allow_rs485` true (genau das
erwartet `--aktiv`); `enable_auto_explore` öffnet Fahrtor und echte Erkundung;
Gesamtbudget 1200 s. Die Aktivierung ist Dokumentation, keine Fahrt.

**Nächster Schritt:** SH-3 ([AGENTENAUFTRAG](AGENTENAUFTRAG.md)) mit dem
Release `selbstheilung-sh2-20261102_1107`.

## 02.11.2026 – SH-2 Lauf 1 am Jetson: abgebrochen, Prüfskript korrigiert

Lokaler Agent, 02.11.2026 10:12–10:21, motorlos nach LAB-1. Klon auf
`0e29125`, neuer Release `selbstheilung-sh2-20261102_1012` (Bericht lokal beim
Projektinhaber, nicht im Repository).

**In Ordnung:** Build 14/14 (179 s), `164 passed`, HWT-Weg gestartet
(HWT601 verbunden, Christophers Stillstandsantwort „ja“, kein
`TERMINAL_FAULT`, Nav2 aktiv, genau ein `/odom`-Publisher
`/hwt601_mapping_ekf`). Prüfung A, B und C vollständig grün, also auch alle
Neuerungen live am Jetson: LiDAR in der lokalen Kostenkarte (X9), VL53-Räumen
ab 0,45 m, VL53-Grenze −0,02 m in beiden Kostenkarten und im
`collision_monitor`, die vier SLAM-Schwellen aus `7d8ef37`. `/cmd_vel` 3 s
still, 0 × „Ignoring the source“, keine ERROR-Zeilen, sauberes Ende (28
Prozesse, alle „finished cleanly“).

**Nicht bestanden:** „D Stillstand“ meldete `/base_hardware erreichbar – keine
Parameterantwort`. Der Agent brach nach der Abbruchregel ab; die
VL53-Messreihe entfiel. Ursache (vom Agenten richtig gefunden, im Code
bestätigt): Im HWT-Weg ohne `active_drive` startet der Launch `base_hardware`
gar nicht, sondern exklusiv den Encoder-Shadow (`UnlessCondition`, nur FC03,
kein `cmd_vel`). Das Prüfskript verlangte trotzdem immer `base_hardware`;
Fehler aus `06b8a6c`. Im Startweg selbst war nichts falsch.

**Korrigiert (`fe84eec`):** D akzeptiert im HWT-Weg ohne `--aktiv` „kein
Motorschreiber“ nur, wenn `base_hardware` weder im Graph noch per
Parameterdienst erreichbar **und** der Encoder-Shadow sichtbar ist; das Fehlen
allein könnte auch ein unvollständiger DDS-Graph sein. Läuft `base_hardware`
doch, gelten unverändert Dry-Run und kein RS485; Shadow neben
`base_hardware` ist FEHL. Standardweg und `--aktiv` unverändert. Vier neue
Tests, darunter der Graph aus dem Bericht; gegen einen echten ROS-Graphen
geprüft. Gezielter Satz jetzt 168.

**Weitere Befunde des Berichts, im Auftrag geklärt:** „Verboten“ nannte
`operator_stationary_confirmed`, Schritt 6 setzt es; der Parameter wirkt nur
auf die HWT601-Einmessung (Code geprüft), die Zeile ist jetzt eindeutig. Die
erste Knotenliste nach 62 s hatte 23 statt 39 Knoten (DDS-Entdeckung); sie
wird jetzt zweimal erfasst. Die Wiederholung nach 30 s gilt jetzt ausdrücklich
vor der Abbruchregel, aber nur für unklare Zustände, nicht für Dry-Run,
RS485 oder Fahrbefehle. 21 TF-Wartemeldungen der lokalen Kostenkarte in den
ersten 10 s gehören zur HWT-Einmessung vor dem ersten EKF-`odom`.

**Nächster Schritt:** SH-2 Lauf 2 ([AGENTENAUFTRAG](AGENTENAUFTRAG.md)),
mindestens `fe84eec`, 168 gezielte Tests, Bericht `…_sh2_lauf2.md`. Danach SH-3.

## 23.10.2026 – Stufe 2: volle v4-Abnahme mit SLAM-Schwellen, kritisch ausgewertet

Auftrag des Projektinhabers: Simulation laufen lassen und danach kritisch
auswerten. Nur Cloud (ROS 2 Jazzy, 4 Kerne), keine Gerätewirkung.
[Beleg](evidence/sh-stufe2-simulation-20261023.json) mit allen 26 Läufen.

**Abnahme (Manifest v4, ohne Experiment):**

| Stand | Durchgang | bestanden | durchgefallen |
|---|---|---|---|
| `093be90` | 1 | 3/6 | Referenz (Kontakt beim Umsehen, Fehler s. u.), Hindernis im Weg (Box), gesperrte Tür (Kartenfehler 14,2 cm) |
| `bb94311` (mit `ff05706`) | A | 5/6 | Hindernis im Weg (Box, zusätzlich Kartenfehler 11,0 cm) |
| `bb94311` | B | 5/6 | Hindernis im Weg (Box, Ende „Hilfe benötigt“) |

Mit `bb94311` je Szenario: Referenz, Sensorlücke, Kartenrennen, Rechenlast,
gesperrte Tür je **2/2**, Hindernis im Weg **0/2**. Ohne Box: kleinster Abstand
zur Polsterung 2,6–6,5 cm, Kartenfehler 3,5–8,9 cm, Abdeckung 96,0–98,1 %,
kein falscher Ringschluss (0 in allen 18 Abnahmeläufen), kein Absturz. Jeder
Lauf endet als „Teilkarte“ (übrige Frontiers unerreichbar), keiner als
„vollständig“; das Kriterium (Abdeckung ≥ 95 %) ist trotzdem erfüllt.

**Befunde:**
1. **Produktfehler gefunden und behoben (`ff05706`).** „Umsehen“ (H3) prüfte
   den Drehkreis an der Pose vom Beginn der Schleifenrunde, gedreht wurde nach
   dem Fehlversuch etwa 0,25 m weiter, 0,39 m neben der Insel (Eckenradius
   0,414 m): Kontakt im Referenzlauf ohne Störung. Jetzt frische Pose nach dem
   Fehlversuch; zwei neue Tests schlagen auf dem alten Code fehl. Explorer
   2248 Tests grün (ein zeitabhängiger AP06-Test, `test_metric_tf_receipt`,
   scheitert auch auf `093be90` in 3 von 12 Wiederholungen).
2. **Fast alle Heilungen haben eine Ursache:** Der Regler bricht ab, weil
   `map`→`odom` beim Nachschlagen 20–270 ms zu alt ist („extrapolation into the
   future“, 16–74 Abbrüche je Lauf, 3–20 Heilungen). Die Leiter fängt das ab,
   kostet aber Zeit (197–899 s) und erzeugt Neustarts mit Drehungen. Die
   naheliegende Erklärung war falsch (X11, `transform_timeout` 0,5 s: 28–37
   statt 36–63 Abbrüche in Referenz und Rechenlast, nicht beseitigt; `slam_toolbox` 2.8.5 datiert damit
   nicht vor). Ob das am Jetson auch so oft vorkommt, misst SH-3.
3. **SLAM-Last wächst mit der Karte:** `slam_toolbox` stieg je Lauf von etwa
   6–27 % auf 36–109 % eines Kerns (Spitze 128 %), in einer Welt mit nur
   rund 16 m² freier Fläche. Karte und globale Kostenkarte laufen mit 1 cm
   (AP06-Entscheidung, `b91101c`; 562 × 282 Zellen hier, eine Wohnung hätte
   über eine Million). X12 (SLAM-Raster 5 cm) hielt die Last in 2 von 3 Läufen
   unter 40 % und die Abbrüche bei 0, im dritten (zwei Ringschlüsse) nicht; mit
   0,68-m-Türen rückten die Pläne aber näher an die Wände (engster Plan 9,6
   statt 23 cm, 18 % statt 14 % der Pläne unter dem Roboterradius). **X12 wird
   nicht vorgeschlagen.** Die Abdeckung fiel mit 5 cm auf 93–95 %, weil das
   Kriterium im Kartenraster rechnet (Wandsaum ~10 % statt ~2 % der Fläche);
   das ist ein Messeffekt.
4. **Kartenfehler über 10 cm ohne Ringschluss:** 14,2 cm (`093be90`, Tür) und
   11,0 cm (`bb94311`, Box). Die neue Diagnose zeigt im zweiten Fall eine
   einzelne um etwa 10 cm verschobene Möbelkante, keine verbogene Karte. Das
   kam auch ohne die strengeren Schwellen vor (vor `7d8ef37` 1 von 5 Läufen
   ohne Ringschluss); die 0,10-m-Grenze bleibt, solche Läufe bleiben rot.
5. **Rest-Risiko Drehen nahe Ecken:** Im X11-Lauf streifte der Roboter die
   Inselecke beim Drehen auf der Stelle, obwohl sie in der lokalen Kostenkarte
   stand (26 tödliche Zellen). Vorher fünf VL53-Lücken in 8 s (Cloud-Last),
   jede mit Abbruch und Neustart samt Ausrichtungsdrehung. Die Drehprüfung des
   Reglers arbeitet in 5-cm-Zellen; 2 cm Polsterung sichert sie nicht sicher.
   In den 10 Abnahmeläufen ohne Box kein solcher Kontakt; mit 0,68-m-Türen
   blieben 0,9 cm.

**Grenzen dieser Aussage:** Die Odometrie der Simulation ist ideal; „0
Ringschlüsse“ heißt hier auch „0 echte“. Ob die strengen Schwellen bei realer
Drift nötige Korrekturen unterdrücken, zeigt erst SH-3 (Frage 3 an Christopher:
doppelte oder verdrehte Wände). Die Cloud ist voll ausgelastet (Last bis ~8 auf
4 Kernen); VL53-Lücken und ein Teil der Zeitfehler sind davon verstärkt.
Zwei Durchgänge je Szenario sind wenig: 0 Kontakte in 10 Läufen begrenzen die
Kontaktrate nur auf unter etwa 26 % je Lauf (95 %).

**Geändert:** `ff05706` (Explorer, s. o.); `bb94311` Simulation speichert
Endkarte und Ort der Kartenfehler. SH-2 braucht jetzt mindestens `ff05706`
(164 gezielte Tests); der SH-3-Entwurf misst zusätzlich SLAM-Last und
Zeitfehler am Jetson (nur lesend). X11/X12 liegen als Experimente in
`tools/simulation/experimente/`, nicht übernommen.

**Nächster Schritt:** SH-2 ([AGENTENAUFTRAG](AGENTENAUFTRAG.md)), mindestens
`ff05706` und 164 gezielte Tests. Danach SH-3.

## 22.10.2026 (abends) – Stufe 2 nach Entscheidungen A–D: SLAM-Schwellen und niedrige Box offen

Gleiche Istbasis wie der folgende Abschnitt; nur Cloud, keine Gerätewirkung.
[Beleg](evidence/sh-stufe2-simulation-20261022-abends.json).

**Umgesetzt nach Entscheidungen des Projektinhabers:**
- A+B (`2f46799`, nur `self_healing`): LiDAR markiert Seitenwände in der
  lokalen Kostenkarte (räumt nicht), VL53 räumen erst ab 0,45 m. Prüfskript
  prüft das live; SH-2 leert vor jeder VL53-Messung die lokale Karte.
- D, v3, C: Manifest v2 (Abdeckung statt Zielzähler, `f4ba6d0`), v3 (ohne
  Teilende-Ausnahme, Kartenfehler ≤ 0,10 m, `9243484`), v4 (v3 in einer Welt
  mit vier festen, unsymmetrischen Möbeln, `63dbcbd`). v2 ließ einen Lauf mit
  3,3 m verbogener Karte bestehen; deshalb v3.
- Explorer v5 (`99866ab`, `7c5aaa6`): Drehraum eines Ziels nur in bekannt
  freiem Raum; zurückgestellt wird die Frontier-Stelle; erreichtes Ziel ohne
  Kartengewinn wird nicht erneut angefahren (vorher 3439 Mal dasselbe Ziel).
  Paket `explore` 2246 Tests grün.

**Ergebnisse (je Lauf; RS = falscher Ringschluss):**

| Satz | bestanden | Befund |
|---|---|---|
| v3, symmetrisch, Explorer v4, X9 | 3/6 | 2× RS, 1× Wandkontakt (Ziel am ungesehenen Wandfuß) |
| Experiment C, unsymmetrisch, Explorer v4 | 1/5 | 0× RS; 3× Kontakt mit frei stehendem Kübel beim Drehen, 1× Endlosschleife |
| **v4 (Abnahme), Explorer v5, X9** | **1/6** | **5× RS** (Karte 1,6–3,3 m verbogen); 1× Box-Kontakt; keine Wandkontakte |
| X7 strengere Ringschluss-Schwellen, v4 | 3/4 | **0× RS**; 1× Box-Kontakt |
| X6 ohne Ringschluss, v4 | 2/3 | 1× Box-Kontakt |
| X10 Recovery behält 2 × 2 m um den Roboter + X6 | 0/3 | 3× Box-Kontakt |

**Folgerungen:**
1. Falsche Ringschlüsse sind kein reines Artefakt der symmetrischen Welt:
   Mit Explorer v5 traten sie auch in der unsymmetrischen Welt in 5 von 6
   Läufen auf, mit den Schwellen aus X7 in 0 von 4 (`loop_match_minimum_
   chain_size` 20, `…response_coarse` 0,55, `…response_fine` 0,65,
   `…variance_coarse` 2,0). Das ist eine SLAM-Änderung; sie wirkt heute in
   allen Betriebsarten, weil beide SLAM-Startdateien die Parameterdatei fest
   laden. Entscheidung offen.
2. Niedrige Box: Der Nav2-Baum leerte die lokale Karte bei jeder leichten
   Recovery vollständig (15 Mal zwischen Auftauchen und Kontakt); sein
   Kommentar nahm an, VL53/OAK markierten im nächsten Frame neu. X10 behält
   den Nahbereich, die Box bleibt bekannt (24–30 Zellen statt 0), berührt
   wurde sie trotzdem (3/3): Von einer niedrigen Box sehen die VL53 nur die
   Vorderkante (3–7 belegte Zellen); beim Drehen trifft die Flanke den nie
   gesehenen Teil. X10 wird nicht übernommen. Die OAK sähe die ganze Box von
   oben, ist beim Kartieren aber seit 16.08.2026 bewusst aus (ihr Bodenfilter
   markierte freie Fläche als unpassierbar). Entscheidung offen.
3. Ohne verbogene Karte hält Explorer v5 die Kontur von Wänden fern; die
   verbleibenden Kontakte betreffen die niedrige Box.
4. Kartenfehler ohne Ringschluss lagen bei 2–15 cm; die 0,10-m-Grenze aus v3
   fing zwei X10-Läufe (10,8 und 15,3 cm) zusätzlich ab.

**Entscheidungen danach (Projektinhaber, 22.10.2026):**
- SLAM: Schwellen aus X7 **nur im Selbstheilungsbetrieb** übernommen
  (`7d8ef37`): `slam_toolbox_self_healing.yaml` wird über ein neues
  Launch-Argument `slam_params_overlay` nur mit `self_healing:=true` in beide
  SLAM-Startwege geladen; andere Betriebsarten unverändert. Prüfskript prüft
  die vier Werte live. 203 betroffene Tests grün.
- Niedrige Box: **bekannte Grenze**, kein weiterer Softwareversuch jetzt (X10
  nicht übernommen). „Hindernis im Weg“ bleibt rot; SH-3 räumt flache
  Gegenstände vom Boden. Kandidat für später: OAK mit korrigiertem
  Bodenfilter als eigenes Paket.

**Nächster Schritt:** SH-2 ([AGENTENAUFTRAG](AGENTENAUFTRAG.md)), jetzt
mindestens `7d8ef37` und 162 gezielte Tests. Danach SH-3.

## 22.10.2026 – Abnahmestufe 2 (Robustheitssimulation): nicht bestanden, Zielwahl korrigiert

MASTERPLAN v1.3, Hauptlinie `self_healing`, KONZEPT §11 Stufe 2. Istbasis:
Branch `claude/blissful-pasteur-s1eivj`; Cloud, ROS 2 Jazzy, 4 Kerne. Keine
Jetson-, Geräte- oder Aktorwirkung. Nicht-Ziel: Realabnahme.

**Werkzeug** (`433990b`…`9c41069`): `tools/simulation/sh_robustheit.py`
startet den echten Produktpfad (Missionsmanager, `bt_orchestrator`, Explorer,
Nav2, Fahrtor, `collision_monitor`, `slam_toolbox`) und die Mission wie die
App. Welt, Budgets, Störungen und Abnahme stehen vorab im Manifest. Diagnose:
engste Stelle mit Belegung der lokalen Kostenkarte, Mitten- und Planabstand,
Rechnerlast. `--experiment` misst Parameterkandidaten ohne Abnahmewert.
Die Weltkontur ist der gepolsterte Footprint; „Kollision“ heißt Berührung der
Polsterung, das Chassis liegt etwa 2 cm innen. 43 auswertbare Läufe:
[Beleg](evidence/sh-stufe2-simulation-20261022.json).

**Ergebnis gegen das Manifest, Explorer-Stand `74afc78`:** 0/5 Störfälle
bestanden, Referenz nicht bestanden.

| Lauf | Ende | Ziele | Heilungen | engster Abstand | verfehlt |
|---|---|---|---|---|---|
| Referenz | vollständig | 3 | 1 | 0,0 cm (Wand der Verbindung) | Kontakt |
| Sensorlücke | vollständig, 98 % Fläche | 1 | 3 | 11,3 cm | mind. 2 Ziele |
| Kartenrennen | Hilfe | 2 | 12 | 12,3 cm | falscher Ringschluss |
| Rechenlast | Hilfe | 2 | 12 | 12,0 cm | falscher Ringschluss |
| Hindernis im Weg | Hilfe | 2 | 24 | 1,3 cm | falscher Ringschluss |
| Gesperrte Tür | Teilkarte | 2 | 1 | 0,0 cm (Wand der Verbindung) | Kontakt |

**Was in allen Läufen funktioniert:** VL53-Lücke 6 s → warten
(`vl53_status_missing_stale_or_invalid`), weiterfahren; LiDAR-Lücke 8 s und
ältere Karte → warten, weiterfahren; 90 s Volllast → kein Abbruch wegen der
Last; kein Prozessabsturz; Nav2 und `collision_monitor` nach jeder Fahrt `active`.

**Behoben (nur `self_healing`, Rückfall je Parameter = 0):**
1. Gesperrte Tür endete mit Hilfe: Jede Planabsage für Frontiers hinter der
   Tür zählte als Fehlschlag, nach 8 kam Hilfe (Konzept §5 H2 verlangt
   „unerreichbar markieren, kein Missionsende“). `e085cac`: grobe, großzügige
   Erreichbarkeitsprüfung auf der eigenen Karte. Danach 3/3 Türläufe Teilkarte.
2. Ziel an der Pfostenecke: Je Frontier wurde die nächste Zelle gewählt; in
   einer Türöffnung liegt sie am Pfosten. Der Roboter parkte mit der Mitte
   0,257 m vom Pfosten im 0,28-m-Saum, NavFn plante nicht mehr, 6–14
   Heilungen. `74486f8`, `cf81aa8`, `74afc78`: Ziel nur mit Drehraum 0,45 m
   (= `self_healing_rotation_radius_m`), sonst geräumigste Zelle in bis
   0,5 m. Danach kein Klemmen am Pfosten mehr (Spurrückfahrt nur noch nach
   falschem Ringschluss); die verbleibenden Kontakte liegen an der Wand der
   Verbindung (Befund A). Zwischenstand `74486f8` war schlechter (5/6 Kontakte,
   Ziel am ungesehenen Wandfuß) und ist überholt.

**Offen – Entscheidungen des Projektinhabers nötig:**

A. **Seitenwände fehlen in der lokalen Kostenkarte.** Beim Kartieren ist die
   OAK aus; die lokale Karte kennt nur, was die VL53 nach vorn sehen. RPP prüft
   seine Kontur daher nicht gegen Pfosten und Wände (gemessen: 0 tödliche
   Zellen über dem Pfosten an der engsten Stelle; die VL53 sehen ±30° bis
   0,5 m, ein Pfosten 0,40 m seitlich liegt bei mittiger Durchfahrt nie in
   ihrem Feld). In der 0,84-m-Verbindung hat ein genau mittiger Roboter beim
   Drehen nur 6 mm Reserve (Eckradius 0,414 m); steht er knapp 6 cm neben der
   Mitte, bringt schon eine Drehung um 24° die Vorderecke an die Wand. So
   entstanden die zwei Kontakte oben. Gemessene Kandidaten:

   | Kandidat | Läufe | Befund |
   |---|---|---|
   | X1 LiDAR in lokaler Karte, räumt | 3 | Pfosten erkannt; 2× klemmt der Roboter dort, 1× falscher Ringschluss; 3× Hilfe |
   | X2 NavFn-Radius 0,30 | 1 | +1 cm, Klemmen bleibt |
   | X3 Voxelschicht + LiDAR | 3 | 16 Heilungen, 352 s, Kontakt bleibt |
   | X9 LiDAR markiert (räumt nicht) + VL53 räumt ab 0,45 m | 5 | Wand erkannt (25 tödliche Zellen); 1 bestanden, 1 Kontakt an der Rastergrenze, 1× nur 1 Ziel gezählt, 2× falscher Ringschluss |

B. **Niedrige Hindernisse werden „vergessen“.** Näher als etwa 0,41 m liegt
   eine 10-cm-Box unter allen VL53-Zeilen; 2D-Räumen über sie löscht die
   Markierung. Belegt durch Geometrie und Code des VL53-Knotens (je Spalte
   wird bis zum nächsten Echo, höchstens 0,60 m, geräumt) und 1 Box-Kontakt
   in 13 Läufen mit Box. Die Messung „0 tödliche Zellen über der Box“ stammt
   aus einem X1-Lauf, in dem zusätzlich der LiDAR räumte; für den reinen
   VL53-Fall ist sie nicht direkt gemessen. X8 (VL53 räumt erst ab
   0,45 m): 2 Läufe ohne Box-Kontakt (einer mit Wandkontakt und falschem
   Ringschluss), wegen kleiner Zahl nicht beweisend.

C. **Falscher Ringschluss von `slam_toolbox`** in der spiegelsymmetrischen
   Testwelt: 12 von 43 Läufen, Karte um 1,7–3,3 m verbogen, danach Hilfe.
   Häufiger, seit die Ziele mittiger liegen (7/14 Läufe mit `74afc78`). X6 ohne
   Ringschluss: 2/2 bestanden (Referenz 12,3 cm, Hindernis 1,5 cm). Die
   Ursache ist nicht belegt: Die Pose sprang z. B. um 3,3 m entlang der
   Raumachse ohne Drehung, das ist keine einfache Spiegelung. Symmetrie bzw.
   Wiederholung der Testwelt ist nur eine Vermutung. Ob reale Räume das
   zeigen, klärt SH-3.

D. **Ersatzkriterium „mindestens 2 Ziele“:** Zwei Läufe mit vollständiger
   Karte, sauberem Ende und ohne Kontakt fielen nur daran, weil die Karte
   schon unterwegs vollständig wurde. Kriterien werden nicht nachträglich
   geändert; eine neue Manifestversion bräuchte die Zustimmung vorab.

Weitere Beobachtungen: `map`→`odom` kam unter Cloud-Last zu spät (bis 39
Zielabbrüche je Lauf „Unable to transform robot pose“), die Leiter fing das
ab. Wandfehler sonst 2–5 cm. Erst messen hat gewirkt: Rechenlast, zu kleiner
Planerradius und „LiDAR allein“ waren naheliegend, aber nicht die Ursache.

**Nächster Schritt:** unverändert SH-2 ([AGENTENAUFTRAG](AGENTENAUFTRAG.md)),
jetzt mindestens `74afc78` und 158 gezielte Tests. Danach Entscheidungen A–D
und SH-3.

## 16.10.2026 – SH-1 v3: motorlose Jetson-Prüfung bestanden

Lokaler Agent, 15.10.2026 23:26 bis 16.10.2026 00:02, LAB-1 motorlos
(`active_drive`/`enable_auto_explore` false, `base_hardware` `dry_run=True`).
Quelle: Klon `~/roboter_worktrees/selbstheilung-v2` @ `f295a85`, Release
`~/.local/share/amadeus/releases/selbstheilung-sh1-20261015_2326`, Unterbau aus
dem v17-`runtime.bash` (Zeilen 2–5), Domain 42/CycloneDDS aus `~/.bashrc`.

- Build 14/14 in 167 s; BT.CPP 4.6.2 aus native-install; alle 14 Präfixe im
  eigenen `product-install`, kein `roboter_ws/install` in der Umgebung.
- 142 gezielte Tests grün (Humble, Python 3.10).
- App-Start `app_mapping.launch.py self_healing:=true start_web_gui:=false`:
  33 Knoten, Nav2 und `collision_monitor` `active`, im Log kein ERROR/FATAL.
- Prüfskript A–D bestanden: 34 Profilwerte live, Overlay geladen, BackUp über
  `cmd_vel_nav_raw` zum Fahrtor, `/backup` vorhanden, `controller_server` auf
  `/speed_limit`, `/cmd_vel` nur vom `collision_monitor`, Basis Dry-Run, kein
  Fahrbefehl.
- VL53-Messreihe 0–8 vollständig (Tabelle und Folgerungen in
  [Konzept §6](KONZEPT_SELBSTHEILUNG.md)): leer 0 Treffer, 3 cm unsichtbar,
  5,5–10 cm gesehen und vollständig verworfen, 15 cm überwiegend behalten.
- Geordneter Stopp per SIGINT an die Launch-PID in 6 s; 24/24 Prozesse sauber.

Auffälligkeiten, nicht behoben:

1. `collision_monitor` ignorierte beide VL53-Quellen 7 s lang (23:45:05–23:45:12,
   Alter 3,0–9,9 s; 278 WARN), während einer Umlegephase. Ursache offen. Bei
   echter Fahrt sperrt das Fahrtor Explore-/BackUp-Befehle schon nach 0,8 s
   ohne frische VL53-Wolken und -Status (`explore_sensor_timeout_s`). Der
   Selbstheilungs-Explorer wartet dann (WAIT), statt abzubrechen.
2. `vl53_near_field` meldete 4× `IndexError … kein neues Frame`
   (Frischeüberwachung aktiv).
3. Auftragsfehler: `source … && nohup … &` schickt die ganze Kette in eine
   Hintergrund-Subshell, `$SH_PR` war leer und `$!` die Subshell-PID. Der Agent
   hat die Launch-PID lesend ermittelt. Für künftige Aufträge `source` in einer
   eigenen Zeile vor dem `nohup`-Start.
4. Geräuschwarnungen ohne Wirkung: `mission_manager` Semantik-Hinweise
   (je 3.758×), Hinweis „Kein Hardware-Not-Aus angebunden (GPIO)“ (der
   hardwired Not-Aus ist davon unabhängig), `slam_toolbox` Mindestreichweite.

Entscheidung 7 (Projektinhaber, 16.10.2026): VL53-Höhengrenze nur im
Selbstheilungsbetrieb auf −0,02 m über `base_link` senken (0,07 m über Boden;
tiefster möglicher Wolkenpunkt 0,084 m). Umgesetzt als eigener Commit `5c285c0`
(Overlays für beide Kostenkarten und `collision_monitor`; ohne `self_healing`
unverändert 0,05). Prüfskript zählt zusätzlich belegte Kostenkartenzellen vor
dem Roboter (`ae780e7`). Cloud: 147 gezielte und 178 Paket-Tests grün.

Entscheidung 8 (Projektinhaber, 22.10.2026): Laborfahrten mit HWT601-Odometrie.
Grundlage sind die abgenommenen HWT-Realfahrten vom 10./11.09.2026 auf den
Fliesen des Labors (Encoder −4,06° je Umdrehung gegenüber HWT/LiDAR ±0,34°).
SH-2 prüft deshalb den HWT-Weg motorlos mit. Prüfskript: `--odometrie` und
`--aktiv` (`06b8a6c`). Neues rein lesendes Fahrtprotokoll für die Bewertung
der Stufe 1 (`bd04145`). Entwurf des Fahrtauftrags:
SH-3, damals noch nicht aktiv (seit 02.11.2026 der aktuelle
[Auftrag](AGENTENAUFTRAG.md)).

**Nächster Schritt:** Auftrag SH-2 ([AGENTENAUFTRAG](AGENTENAUFTRAG.md)):
motorlose Nachmessung auf dem Jetson im HWT-Weg mit neuem Release, gleicher
Messreihe und Kostenkartenprüfung; danach SH-3 (Abnahmestufe 1, drei begrenzte
Laborfahrten) als aktueller Auftrag.

## 15.10.2026 – Selbstheilender Betrieb beschlossen und gerätefrei umgesetzt

Auswertung der Original-v17-Rohdaten (Jetson, nur lesend) ergab drei konkrete
Ursachen: **A** – eine 1-cm-SLAM-Korrektur gegen float32-Auflösung (Rest 2,2e-8
Zelle) verwarf die Startfreigabe; **HOLD** – der Kartenstatus eilte der Rohkarte
um 1,0 s voraus (Abbruch nach 1,6–2,7 ms, `status_binding_changed`); **B/C** –
Auswahlbudget im Stillstand terminal. Korrekturen auf Branch
`claude/blissful-pasteur-s1eivj`; zusätzlich neue umschaltbare Strategie
`self_healing` mit Heilungsleiter und Spurrückfahrt
([Konzept](KONZEPT_SELBSTHEILUNG.md)). Gerätefrei geprüft: Explore 2.231,
robot_navigation 147 Tests grün (ROS 2 Jazzy, Cloud). Keine Realfahrt, kein
Install, v17-A/B/C nicht neu ausgeführt.

Entscheidung 2 (15.10.2026): solange vor dem Roboter nicht kartiert ist,
0,06 m/s über Nav2 `speed_limit` (gerätefrei geprüft). Entscheidung 3:
Heilungsbudget wie profiliert. Entscheidung 5: `self_healing` ist Hauptlinie,
AP06 eingefroren (erhalten, umschaltbar); Bestätigung nach realem Kurztest
(drei begrenzte Laborfahrten, Kriterien im Konzept). Entscheidung 6:
Abnahmeleiter Labor → Robustheit (Simulation, 5 Störfälle) → echte Wohnung
(alle zugänglichen Räume, Richtwert ≥ 90 % begehbare Fläche, kein Kontakt).
Entscheidung 4: „Weiter“ mit Missionsgedächtnis in der App (geplantes
Arbeitspaket, Konzept §12); Abnahme Stufe 1/2 ohne Eingriff, Stufe 3 höchstens
1× „Weiter“ je Lauf bei echtem physischem Hindernis. Danach folgt das
Arbeitspaket „Weiter“.

Rückfragen geklärt (15.10.2026, Projektinhaber): Teleop-Tempo bleibt
unverändert; keine Hecksensoren, Rückwärtsfahrt bleibt auf die eigene Spur
begrenzt. VL53-Befund (Konfiguration gelesen, nicht gemessen): der Sensor trifft
niedrige Objekte, Kostenkarten und `collision_monitor` verwerfen aber alle
Treffer unter etwa 0,14 m über Boden ([Konzept §6](KONZEPT_SELBSTHEILUNG.md)).
Eine Filteränderung wäre eine eigene Sicherheitsänderung nach Messung.

SH-1 v1 auf dem Jetson (15.10.2026 22:24–22:26, lokaler Agent): Build korrekt
gestoppt, Schritte 5–8 entfallen, kein Stack, keine Aktorwirkung, `~/roboter_ws`
unverändert. Ursachen im Auftrag: Unterbau `~/roboter_ws/install` ist der
August-Stand `23928d9` ohne `amadeus_map_identity` (AP06 v11–v17 liefen aus
eigenen Release-Ordnern); `git fetch` in `~/roboter_ws` scheitert an einer
defekten Codex-Referenz; Umgebungsdatei lieferte Exit 1. Zusätzlich gefunden:
`app_mapping.launch.py` reichte `self_healing` nicht durch (behoben in
`e123902`, Default unverändert `false`).

SH-1 v2 auf dem Jetson (15.10.2026 23:05–23:07): Unterbaukette eindeutig aus
dem v17-`runtime.bash`, Umgebung ohne `roboter_ws/install`; 4 von 14 Paketen
gebaut, `bt_orchestrator` scheiterte am bekannten fehlerhaften System-Export von
`behaviortree_cpp` 4.9.1. Der v17-Build übergibt dafür `-Dbehaviortree_cpp_DIR`
(native-install) und `-DBUILD_TESTING=ON`; im v2-Auftrag fehlte beides. Kein
Stack, keine Aktorwirkung, `~/roboter_ws` unverändert.

Damaliger nächster Schritt: Auftrag SH-1 v3; Ergebnis im Abschnitt 16.10.2026.

## 11.10.2026 – Wartefolge und wiederholte Zielidentität korrigiert; Gesamtprüfung offen

Getrennter Checkout, Fixbranch `fix/ap06-adaptive-cooldown-order`, Ausgangsbasis
`d2c6cfe`. Schritte 1/2: echte adaptive Auswahl vor Korrektur dreimal statt
einmal während derselben ursprünglichen Pause; danach 214 gezielte Fälle
positiv. Zeit-/Kontextpause liegt vor adaptiver Zielsuche, nach aktuellen
Schutzprüfungen. Neue echte Auswahl nach Pausenende, Cancel/HOLD/Quelle und
Kontext geprüft. [Gegenfall](evidence/ap06-adaptive-wait-order-20261011.json).

Instrumentierter geschlossener Vergleich aus `34fbad1`: negativ nach
0,191529 m, keine Ankunft/Beobachtung. Ereignisfolge: Encoderprobe nach
Verarbeitung veraltet, Route verworfen, anschließend getrennte VL53-Stempel
während Stillstand/Pause terminal behandelt. Kein harter Quellenfehler.
`9fb28f6` korrigiert das Veröffentlichungsfenster ohne künstlichen Match oder
Bewegungsrecht; zwei Gegenfälle zuvor negativ, danach 34 Wartefälle positiv.
[Nachweis](evidence/ap06-publication-wait-20261011.json).

Schritt 3: bei 53 live Eingangsprüfungen 135,763 ms Median/383,700 ms Maximum;
eine nach Verarbeitung erneut gebundene Encoderprobe war am Ende 201,456/
212,415 ms alt, über der unveränderten 180-ms-Grenze. Gemessene reine Arbeit
verkürzt: Körperzellen mit identischer Rechnung nur im konservativen lokalen
Fenster, genau eine inhalt-/geometrie-/Scope-/Kontext-/Körpermasken-gebundene
Known/Safe-Berechnung wiederverwendbar. Kein Gesundheits-, Routen- oder
Dispatchnachweis im Cache; tatsächliche Costmap und ganzer Egress weiter
geprüft. Auf eingefrorenen Eingaben mit tatsächlichem v10-Nativkern etwa
52,5 → 28 ms. 298 betroffene Fälle positiv; Körpermasken bitgleich, geänderte
Eingaben invalidieren, ursprüngliche Frischegrenzen auch bei Cachetreffern
wirksam. Kartenalter und Auswahl-Rechenbudget getrennt benannt mit identischem
bisherigem Grenzwert; aktuelle Alters-/Rechenzeitbelege im Produktstatus.
[Messung und Prüfung](evidence/ap06-input-geometry-20261011.json).

Geschlossener instrumentierter Vergleich aus `7c07641` regulär negativ:
0,526085 m, eine Ankunft/Beobachtung (176 Zellen), keine volle Passage. Bei
578 Eingangsprüfungen Median 85,357/p95 116,293 ms (zuvor 135,763/276,637),
aber weiter ein Frischeausreißer: erneute Probe vor 48,487 ms Maskenentzug
gebunden, anschließend 148,420 ms Egressprüfung; am Ende 200,735/209,135 ms
alt. Mehrere native Folgeziele ohne ursprüngliche Sicht am Haltepunkt, später
bewegte Folge wegen Kartenjoin unterbrochen; terminal 5-s-Auswahlbudget
überschritten. Kinder beendet, vier Kommandoströme null. Kein Stoppsignal
mehr gesendet: der Prozess war schon regulär beendet. Kein Gesamtpositivbeleg.

Die erneute tatsächliche Encoderbindung liegt jetzt nach reinem Maskenentzug,
weiter gegen dasselbe tatsächliche TF-Paar und die originalen 20-mm/0,05-rad-
Grenzen. Kein Stamp geändert, keine Pollschleife oder Frist verlängert. Echter
DDS-Gegenfall mit originaler vollständiger Methode zuvor negativ, danach
positiv; 149 betroffene Fälle sowie drei verstärkte aktuelle Paarfälle positiv.
[Zeitfolge/Gegenfall](evidence/ap06-late-wheel-binding-20261011.json).

Schritt 4: ursprünglicher Auslöser, begrenzte Folgereaktionen und terminaler
Grund werden jetzt unabhängig im Ergebnis erhalten; Scanwinkel/-dauer/-Sollrate
und erster Navigations-Stopgrund bleiben nachvollziehbar. 136 betroffene
Fälle positiv, einschließlich tatsächlicher Elternfolge mit verworfener nativer
Route und späterem Budgetende. Keine Entscheidungs- oder Budgetänderung.
Der ältere Zwei-Beobachtungs-Lauf zeigt 5,6421 rad in ungefähr 151 s,
etwa 18 s Stillstand und 0,03743 rad/s mittlere tatsächliche Drehung. Gemessene
Sollwerte 0,08/0,024 passen zum bestehenden SlowZone-Faktor 0,3; ohne volle
Monitor-Spur ist dessen Gesamtanteil nicht bewiesen. Drei aufeinanderfolgende
Beobachtungen fehlen weiter. [Kausalbeleg](evidence/ap06-causal-result-20261011.json).
Eine versuchte exakte Routenwiederverwendung brachte im Profil keine
Verbesserung (4,505 → 4,602 s) und wurde vollständig verworfen.

Gemeinsamer Kandidat v11 aus `b58b257` separat gebaut: 14 Pakete in etwa
173 s, 157 Quelle-Installgleichheiten, 756 Installhashes; sämtliche Produkt-
präfixe einschließlich Nativkern im neuen privaten Install. Vollregression:
**2.933 Fälle positiv**, keine Fehler/Skip. Ursprüngliche unveränderte A/B/C
weiter **0/3**: A 0,728097 m mit zwei Ankünften/Beobachtungen (176/4 Zellen),
B 0,311323 m ohne Ankunft/Beobachtung, C 0,712181 m mit einer Ankunft/Beobachtung.
A: Scan erreichte 6,29505 rad, meldete jedoch am ursprünglichen 150-s-Limit
unterbrochen; danach native Footprint-Verwerfungen, terminal 5,09361 s
Auswahlarbeit bei 2,02131 s Thread-CPU. B: erster Auslöser neue unbekannte
Fläche/Belegung im Egress, C: Scangeometrie nach 0,20730 rad ungültig; beide
terminal Auswahlbudget. Keine gemeinsame Ursache aller Schutztrigger bewiesen.
Alle Kinder terminal, vier Kommandoströme null. Keine reale autonome Fahrt.
[Gemeinsamer Build, Regression und Originale](evidence/ap06-correction-v11-20261011.json).
Alle 1.048 Bestandsinstallhashes gleich, Bestandsmain sauber/unverändert.

Weitere gemessene Schritt-3-Korrektur: echte adaptive Auswahl erneuerte
nach 2,0278 s optionaler öffentlicher Arbeit drei zusätzliche Helferfenster
von 0,5046/0,5029/0,5019 s. Der Gegenfall war vor Korrektur negativ. Die
bestehende 2-s-Zuteilung wird jetzt pro Auswahl gemeinsam verbraucht; das
ursprüngliche harte 5-s-Auswahlbudget und alle Frische-/Aufgaben-/Gesamtgrenzen
bleiben unverändert. Eingefrorene originale Auswahl 4,5049 → 2,9637 s,
identisches Ziel, 102 Punkte und vollständiger Evidenzhash. 180 betroffene
Fälle positiv. Kein Routen-/Quellen-/Fahrrecht zwischengespeichert.
[Budgetgegenfall](evidence/ap06-optional-geometry-budget-20261011.json).
Kopiervermeidung, Routenreuse und Rasterpaar-Zusammenfassung ohne klaren
Gesamtgewinn verworfen. Keine neue gemeinsame oder reale Abnahme daraus.

Gemeinsamer Kandidat v12 aus `f7138cf` separat gebaut: 14 Pakete, 157
Quelle-Installgleichheiten und 756 Installhashes. Vollregression: **2.936 Fälle
positiv**, keine Fehler/Skip. Ursprüngliche unveränderte A/B/C weiter **0/3**:
A 0,150076 m ohne Beobachtung; B 1,272521 m mit drei selbst gewählten
Beobachtungen; C 0,697345 m mit einer Beobachtung. B schloss den optionalen
Rundblick mit 6,29647 rad in 149,979 s ab, erreichte aber keine volle Passage.
A: erster Egress-Trigger neue unbekannte Fläche/Belegung, terminal 5,04335 s
Auswahlarbeit trotz nur 0,01316 s optionaler Helferarbeit. B: zuerst keine
ursprüngliche Sicht am nativen Haltepunkt, später Auswahlbudget. C: reale
simulierte Encoderprobe am Ende 172,373/180,795 ms alt, danach begrenzte
Revalidierung und eine Beobachtung, terminal 5,11247 s Auswahl. Keine harte
Quellenstörung und kein Gesamtpositivnachweis. Alle Kinder terminal, vier
Kommandoströme null. [V12-Build und Originale](evidence/ap06-correction-v12-20261011.json).
Bestandsmain unverändert/sauber, alle 1.048 Bestandsinstallhashes gleich.

**Veröffentlichung:** Implementierung und bisherige Belege wurden ohne Force
auf `feature/ap06-closed-product-validation` übertragen; Remote-HEAD
`f7138cfbd38d58462040174203a278d8231bb18e` am 11.10.2026 um 06:09:17 UTC
mit `ls-remote` bestätigt. 22 geänderte Dateien geprüft, keine Geheimnistreffer;
nur eigene synthetische binäre Gegenfallraster. Der V12-Nachtrag ist neu.

Weitere Schritt-4-Korrektur: das gemeinsame `/plan`-Topic konnte während
rein lesender ComputePath-Anfragen als aktiver Navigationspfad gebunden werden.
Drei Gegenfälle vor Korrektur negativ, einschließlich tatsächlicher adaptiver
Auswahl/Elternfolge. Jetzt nur Topic-Updates des gleichen aktuellen Nav2-Kindes;
Dispatch-Stempel schließt wartende alte Query-Veröffentlichungen aus. Der
explizite Query-Rückgabepfad bleibt vollständig geprüft. 174 betroffene Fälle
positiv, keine Grenzen verändert. Im älteren Original A war der verworfene
Task-4-Pfad allerdings gleich dem Query-Pfad: keine Behauptung, dieser Rollenfehler
erkläre jene Verwerfung oder alle Abbrüche.
[Gegenfall und Quellenbindung](evidence/ap06-plan-publication-owner-20261011.json).

Weitere Schritt-4-Korrektur: fünf identische rein lesende native Pfade bei
unveränderter Karte im instrumentierten Source-A-Diagnoselauf. Derselbe bereits
abgelehnte Zielpunkt wurde einem näheren unversuchten Frontier zugeordnet;
unterschiedliche Ortsfenster-Hashes erschienen fälschlich als neue Messung.
Zwei tatsächliche Gegenfälle zuvor negativ, einschließlich originaler adaptiver
Auswahl mit aufgezeichneten synthetischen Eingaben. Jetzt priorisiert ein exakt
bereits versuchter Zielpunkt seine ursprüngliche Historie/Messfenster; echte
andere Querypositionen und endliche neue abgeschlossene Sichten bleiben möglich.
110 und 104 betroffene Fälle positiv (getrennte Suiten mit Überschneidung),
originale Cooldowns/Zähler/Fristen unverändert. Keine Bewegungsfreigabe daraus.
Diagnoselauf nach ausreichender Aufzeichnung über seine eigene eindeutige PID
geordnet abgebrochen: eine Beobachtung/0,296201 m, kein Manifestnachweis;
unvollständiges Resultat und Reporting-KeyError getrennt erhalten. Zusätzlicher
Hashcache und größere Nativbatch ohne zuverlässigen Gesamtgewinn verworfen.
[Gegenfall und Grenzen](evidence/ap06-exact-query-identity-20261011.json).

Gemeinsamer Kandidat **v13 aus `a4b4e35`** separat gebaut: 14 Pakete in
170,906 s, 157 Quelle-Installgleichheiten und 756 Installhashes; ursprüngliche
Paket-/Nativpräfixe eindeutig im privaten Kandidaten erfasst. Vollregression:
**2.946 Fälle positiv**, keine Fehler/Skip. Originale unveränderte A/B/C
weiter **0/3**: A 1,201621 m/zwei Beobachtungen, B 0,353843 m/eine Beobachtung,
C 0,702971 m/eine Beobachtung. A/B zuerst keine ursprüngliche Sicht am nativen
Haltepunkt; C dort 108 von 128 Sichtpunkten, jedoch anschließende bekannte
Route unzulässig. B terminal 5,539640 s Auswahl bei 2,185857 s Thread-CPU,
C 5,000319 s bei 1,970833 s; kein gemeinsamer universeller Trigger bewiesen.
A: optionaler Scan nach 6,104092 rad/150,789 s unterbrochen; anschließend
frische Auswahl innerhalb des Budgets und zweite Beobachtung. Terminal
`hwt_terminal`: Fahrtor wählte eine 184,949 ms alte Encoderprobe bei 180-ms-
Grenze; Raw/Gyro am ersten Fehler frisch. Quellenprozess gleichzeitig über
208–215 ms verzögert, wenig eigene Thread-CPU; Ursache dieser Pause nicht
bewiesen. Keine Behauptung eines realen Encoder-/Modbusdefekts.

Originale geschlossene **Cancel und Gyro-HOLD 2/2 positiv** mit gleichem v13:
Cancel → Stillstand 0,354443 s, terminal 0,631966 s; HOLD → Stillstand
0,259884 s. Der HOLD-Fall qualifiziert ausdrücklich keine Wiederaufnahme;
betroffene Wiederaufnahme-/Speicher-/Schutzregressionen sind im gesammelten
2.946er-Lauf enthalten. Sämtliche Kinder terminal, vier Kommandoströme null.
Keine reale autonome Fahrt, kein dreiminütiger Realvorlauf aus diesem Stand.
[Gemeinsamer Build, Originale, Schutzfälle und Ursache](evidence/ap06-correction-v13-20261011.json).

Zusätzliche negative Budgetdiagnose ohne Manifestabnahme: tatsächlicher
gekappter Historienaufruf nach 5,390469 s/2,189939 s Thread-CPU gesichert;
38,231 ms zusätzliche Diagnosekopie transparent erhalten. Exakter privater
v13-Replay mit dessen Nativkern findet nach 3,594412 s einen reinen Nav2-
Vorschlag, 90 Punkte und gebundenen Hash, keine Bewegungsfreigabe. 2.254
Signaturprüfungen kumulativ etwa 0,754 s und acht Inhalts-Hashes etwa 0,704 s.
NumPy-Vollvergleich 5,187600 s/Budgetfehler und nativer Bytevergleich
3,738922 s mit gleichem Kandidaten ohne Gesamtgewinn; beide verworfen.
Zwei private Wrapperfehler vor Graphstart getrennt dokumentiert. Gesicherte
Inputs/Profile bleiben lokal; reale Karten/Bilder/Bags werden nicht hochgeladen.

**Veröffentlichung:** Produktfixes bis `a4b4e355d54f17b4195331faf0ad6be413f56a50`
am 11.10.2026 um 07:04 UTC auf AP-06-Featurebranch bestätigt. Dieser v13-
Ergebnisnachtrag enthält ausschließlich Dokumentation; gemeinsame Build-/
Testquelle bleibt `a4b4e35`. Bestandsmain sauber/unverändert, alle 1.048
Installhashes nach dem separaten Build identisch.

Weitere gemessene Schritt-3-Korrektur: Der echte adaptive Gegenfall mit
unbesuchtem Ziel und ausschließlich räumlich unbeteiligter Historie berechnete
elf lokale Hashes für eine Auswahl. Vor Korrektur negativ, danach nur der
endgültige ausgewählte Hash. Unbesuchte Preselection ohne versuchten Nachbarn
an **allen** geprüften Positionen benötigt keinen Historienvergleich; eigene
oder relevante Nachbarhistorie behält den tatsächlichen Hash. Jeder ausgewählte
Kandidat bekommt weiter seine vollständige aktuelle Kartenevidenz. 150 und
acht gezielte Fälle positiv, 151 eindeutige Prüfungen. Auf dem tatsächlich
aufgezeichneten terminalen B-Aufruf: acht → drei Hashberechnungen, etwa
3,594 → 3,032 s Profilzeit, identisches Ziel/90 Punkte/Evidenzschlüssel und
Ranking, gleicher v13-Nativkern. Einzelprofil ist keine Gesamtqualifikation.
[Gegenfall und Messung](evidence/ap06-relevant-history-digest-20261011.json).

Gemeinsamer Kandidat **v14 aus `a6d5bbd`** separat gebaut: 14 Pakete in
171,453 s, 157 Quelle-Installgleichheiten, 756 Installhashes. Vollregression:
**2.954 Prüfungen positiv**, keine Fehler/Skip. Ursprüngliche A/B/C weiter
**0/3**: A 0,715282 m/zwei Beobachtungen, B 1,282187 m/**vier** Beobachtungen,
C 0,714659 m/eine Beobachtung. A zuerst Scan nach 0,660620 rad/28,100 s wegen
Footprint ungültig; B zuerst `map_status_join_pending`; C zuerst keine Sicht
am nativen Haltepunkt. Drei getrennte Auslöser, terminal jeweils unverändertes
5-s-Auswahlbudget: 5,276156/5,000409/5,737415 s bei 1,997423/1,977971/2,230855 s
Thread-CPU. Kein ursprünglicher vollständiger Missionsabschluss daraus.
Originale Cancel/HOLD **2/2 positiv**: Halt nach Cancel-Injektion 0,347173 s,
nach HOLD 0,309861 s. HOLD setzte anschließend mit zwei Beobachtungen fort;
der unveränderte Fall bewertet ausdrücklich nur HOLD/Stopp und weist
`hold_resume_qualified=false` aus. Vollständige Wiederaufnahmeabnahme offen.
Vier Kommandoströme null, Kinder terminal; alle 1.048 Bestandsinstallhashes
identisch, Bestandsmain sauber. Keine reale autonome Fahrt.
[V14-Build, gesamte Regression und Originale](evidence/ap06-correction-v14-20261011.json).

Weitere gemessene Schritt-3-Korrektur: der echte eingefrorene Selector las
4.484 Raster für wiederholte Signaturen; Gegenfall vorher negativ. Eine reine
Routenberechnung teilt nun eine exakt erfasste Inhaltsbindung und prüft alle
Inhalte danach erneut, bevor eine Route zurückkommt. Geänderte Raster/Masken,
Pose-/physische Bewegungsbindung, Egress, Scope und Kontur-/Routenparameter
verwerfen die gesamte Auswahl. Keine Route, Quellenbewertung oder Bewegungserlaubnis
im Cache. 164 und elf gezielte Fälle positiv, 166 eindeutig (Überschneidung neun).
Drei gepaarte Profile mit demselben v14-Nativkern: 3,084/3,013/3,035 →
2,742/2,656/2,794 s; jeweils identisches Ziel/90 Punkte/Evidenzhash/Ranking.
Das sind reine eingefrorene Profile, keine aktuelle Quelle oder Mission.
[Gegenfall und Grenzen](evidence/ap06-route-proof-group-20261011.json).

Gemeinsamer **v15 aus `1d03a1f`**: 14 Pakete separat in 172,076 s gebaut,
157 Quelle-Installgleichheiten, 756 Installhashes. **2.965 Regressionstests positiv**,
keine Fehler/Skip. Unveränderte Originalmissionen weiterhin **0/3**: A 0,225799 m/
keine Beobachtung, B 0,363251 m/eine, C 0,715161 m/eine. A/B terminal Auswahlbudget
5,251736/5,953357 s bei 2,056967/2,224353 s Thread-CPU. C Auswahl 4,239189 s
innerhalb 5 s, danach terminal `nav2_plan_goal_stop_rotation_invalid`.
C zuvor eigener Scan nach 0,032602 rad/1,957792 s geometrisch abgelehnt, später
bekannte Abfahrt nicht verfügbar und zwei native Sweeps verworfen. Kein
vollständiger Rundblick oder ganzer Missionsabschluss. Cancel positiv, Halt
0,381296 s nach Einspeisung (exakter Wert im Beleg); **HOLD negativ**, ohne Bewegung
oder HOLD-Einspeisung: erster Eingang nach 479,330 ms Arbeit mit alter Körperscan-
Probe, anschließend Auswahlbudget 5,262765 s überschritten. Kein gemessener
HOLD-Stopp aus diesem Fall. Kinder terminal/vier Kommandoströme null. Alle
1.048 Bestandsinstallhashes unverändert, Main sauber. Keine reale autonome Fahrt.
[V15, exakte Quellen und Ergebnisse](evidence/ap06-correction-v15-20261011.json).

Die passive Prozess-CPU-Stichprobe in C umfasst 5,295 s mit 5,13 s Explorer-
Prozess-CPU, während die Auswahl selbst 4,239 s Wandzeit/1,675 s Thread-CPU
benötigt. Das Fenster beginnt 0,804 s davor und endet 0,251 s danach. Weitere
Threads verbrauchen messbar CPU; Ursache der Verzögerung, GIL-/Scheduleranteil
und alle anderen Fälle sind damit nicht bewiesen. Keine Sensorperioden oder
CPU-Zuordnungen verändert.

Schritt 2/4: ein konkreter Klassifizierungsfehler ist belegt. Die echte adaptive
Auswahl mit alternativem nativen Plan hat einen freien RPP-Translationssweep,
aber unzulässige Drehung am tatsächlichen Stop. Vor Korrektur terminal, ohne
Verbuchung als abgelehnter Vorschlag. Jetzt wird dieser geometrische Queryfehler
wie die vorhandenen Sweepfehler als `proposal_rejected` verbucht; ursprünglicher
Auslöser bleibt, aktueller Versuch zählt, kein Kind/Alignment oder Bewegung.
Reale Rotation bleibt abgelehnt. Falsche Frames und nicht endliche Planwerte
bleiben terminal. Gegenfall zuvor rot, danach grün; **281 betroffene Fälle positiv**.
[Gegenfall und Rückfall](evidence/ap06-native-stop-recovery-20261011.json).

Gemeinsamer **v16 aus `dc84753`**: 14 Pakete separat in 177,291 s gebaut,
157 Quelle-Installgleichheiten, 756 Installhashes; **2.969 Regressionen positiv**,
keine Fehler/Skip. Ursprüngliche vollständige A/B/C weiter **0/3**, je eine
Beobachtung und 0,293228/0,356163/0,713589 m. A zuerst kein Kandidatensichtpunkt
am nativen Stop, terminal unzulässige private Anfangsdrehung. B zuerst
Körperscan nach Verarbeitung 518,511 ms alt bei 345,784 ms Eingangsarbeit,
danach Auswahlbudget 5,239773 s/2,048424 s Thread-CPU. C zuerst Scan nach
0,070940 rad/2,337272 s geometrisch abgelehnt, danach Auswahlbudget
5,016257 s/2,016217 s CPU. Ursache aller Stopps weiterhin nicht gemeinsam
bewiesen. Originale Cancel/HOLD **2/2**, Cancel-Halt 0,401796 s; HOLD-Halt
0,311322 s nach HOLD, terminal `hwt_terminal`. Der ursprüngliche HOLD-Fall
qualifiziert ausdrücklich keine vollständige Wiederaufnahme. Alle vier
Kommandoströme null, Kinder terminal. Erster Testdriverstart scheiterte vor
Sammlung am bereits angelegten leeren Ergebnisordner; korrekt reparierter
Start, ursprünglicher Fehler und erfolgreiche Stufen separat erhalten.
Alle 1.048 Bestandsinstallhashes unverändert, Main sauber.
[V16-Build und Originalfälle](evidence/ap06-correction-v16-20261011.json).

Schritt 2/4: zweiter tatsächlicher Klassifizierungsgegenfall geschlossen.
Ein nativer read-only Plan kann eine unzulässige Anfangsdrehung im privaten
Startbestand enthalten. Die Drehung bleibt durch denselben vollständigen
Guard abgelehnt. Ihre Ablehnung wird jetzt innerhalb unveränderter Versuchs-
und Zeitlimits als verworfener Vorschlag verbucht, statt unmittelbar ohne
Folgeversuch terminal zu enden. Echte adaptive Elternauswahl/echter privater
Sweep vor Korrektur negativ, danach positiv; **193 betroffene Tests positiv**,
kein Alignment/Nav2-Kind oder Aktor aus dem Gegenfall. Harte Quellen-/Kontext-
fehler bleiben terminal. [Gegenfall](evidence/ap06-native-private-recovery-20261011.json).

Zusätzliche Timingdiagnosen sind keine Qualifikation: eine 1-ms-Pause zwischen
Executor-Dispatches spart CPU, verzögert aber während der Auswahl erzeugte
Nachrichten bis 243,039 ms; Ansatz verworfen. Null-Warte-Yield ohne Rechenzeit-
gewinn ebenfalls verworfen. Explorer-Hauptschleife unverändert. Gemessene
wiederholte reine Inhaltsprüfungen werden gezielt reduziert und auf echte
Änderungen an Raster/Referenz/Scope/Kontur geprüft. Originale Frischegrenzen,
CPU-Zuteilungen, 5-s-Auswahlbudget und Missionskriterien unverändert.

Schritt 3: tatsächliche adaptive Auswahl liest im aufgezeichneten synthetischen
B-Gegenfall noch 1.828-mal Rasterinhalte für wiederholte Bindung. Derselbe echte
Aufruf ist vor Korrektur am Arbeitszähler negativ. Jetzt teilen nur die reinen
Kandidaten desselben Threads/derselben Auswahl die vollständig geprüfte
Inhaltsbindung; vor Rückgabe vollständiger erneuter Audit ohne Cache. Raster,
Masken, Referenz, Bewegung, Egressgeneration/-gültigkeit, Kontur/Scope und
Geometrieparameter geändert: gesamte Auswahl verworfen. Bei Ausnahme Gruppe
und Memo freigegeben; nächste Auswahl frisch. Kein Gesundheits-, Routen- oder
Fahrrechtcache. **176 betroffene Prüfungen positiv**, zusätzlich erster
87-Fall-Vergleich positiv; Mengen überlappen. Drei native Vergleiche unter
unveränderter künstlicher 320-Hz-DDS-Last: 1.828 → 16 Inhaltsreads, median
3,908911 → 3,264769 s Wandzeit und 2,396170 → 1,997462 s Auswahl-CPU.
Ziel/90 Punkte/Evidenzhash gleich. Während Auswahl erzeugte Nachrichten p95
29,664–40,157 ms davor bzw. 34,209–42,881 ms danach, Maximum danach 104,589 ms.
Kein daraus abgeleiteter Produktquellen-, Missions- oder Realgesundheitsbeleg.
Executor, ursprüngliche Budgets und Schutzprüfungen unverändert.
[Gegenfall, exakte Vergleiche und Rückfall](evidence/ap06-candidate-pass-binding-20261011.json).

Gemeinsamer **v17 aus `60e894c`** abgeschlossen: 14 Pakete in 174,559 s,
157 Vergleichseinträge für 155 eindeutige Quelle/Install-Dateien, 756 Installhashes. **2.976 Regressionen positiv**,
keine Fehler/Skip. Beide Manifeste für 3.717 verfolgte Dateien identisch;
aktuelle erfasste Produktmodule/hashgebundener ARM64-Kern stimmen. Ursprüngliche
volle Missionen **0/3**, keine volle Passage/Heck und nur 0/1/1 Beobachtungen:

| Fall | Weg | Erster Auslöser | Terminaler Grund |
|---|---:|---|---|
| A | 0,203623 m | Egressroute: neue unbekannte Fläche/Belegung | `completion_raw_pose_not_observed_free` |
| B | 0,354768 m | Keine ursprüngliche Kandidatensicht am nativen Stop | Auswahlbudget 5,889749 s, CPU 2,257465 s |
| C | 0,707988 m | Scan-Footprint nach 0,192777 rad/4,083774 s ungültig | Auswahlbudget 5,707443 s, CPU 2,145290 s |

Keine gemeinsame Ursache aller Abbrüche bewiesen. A letzte Auswahl 3,361210 s
innerhalb Budget; sein Geometrie-/Abschlussfehler bleibt getrennt von B/C.
Die lokale Beschleunigung behebt die späteren Lastfälle noch nicht. Grenzen
oder Freiraum nicht erweitert. Cancel positiv, HOLD-Stopp positiv; gemessener Cancel-Halt
0,338385 s, HOLD-Halt ab HOLD
0,300974 s. Originaler HOLD-Fall ausdrücklich nur
Stopp, **keine vollständige Wiederaufnahme**. Nach tatsächlichem HOLD folgen
vier Ankünfte/drei Beobachtungen und 1,249039 m; terminal anschließend
`map_status_join_retry_budget_exhausted`. Dieser begrenzte positive Fortsetzungs-
verlauf ersetzt keine Original-Positivmission. Alle Kinder terminal, vier
Kommandoströme null. Bestandsmain `23928d9` sauber und alle 1.048 ursprünglichen
Installhashes unverändert. Kein realer Vorlauf oder autonome Realfahrt aus
dieser Umsetzung. Matrixdriver-Exit 0 bedeutet Ausführung, keine Missionsabnahme.
[Exakter v17-Build und Resultate](evidence/ap06-correction-v17-20261011.json).

Kritische Selbstprüfung samt Erkenntnisgrenzen und reparierter veralteter
Jetson-Kandidatenangabe:
[Buildreview](AP06_BUILD_REVIEW_20261011.md). Software `60e894c` bereits auf dem
Featurebranch bestätigt; dieser Audit ergänzt Dokumentation/Belege. Kein
Main-Merge oder dauerhafte Installation.

**Genau nächster Schritt:** A erste tatsächlich verworfene Rasterzelle samt
Rastertyp/Referenz messen; B/C tatsächlich späte Auswahlarbeit und Callback-
Verzögerung gezielt binden. Echte Gegenfälle vor weiterer Produktänderung,
keine unveränderten Fehlversuche oder pauschalen höheren Budgets. Danach ein
neuer gemeinsamer Kandidat mit ursprünglicher vollständiger Abnahme. Volle
Wiederaufnahme und reale Folge gemäß aktuellem Auftrag bleiben offen.
Rückfall begrenzte eigene Korrekturcommits revertieren/private Overlay-Abwahl.

## Historischer veröffentlichter Stand vor Umsetzung der Ablaufkorrektur

Der [aktive Auftrag](AGENTENAUFTRAG.md) enthält die aufeinanderfolgenden
Maßnahmen: Gegenfälle im tatsächlichen adaptiven Pfad, Warte-/Auswahlreihenfolge,
gemessene Zeitverarbeitung, Folgeplanung nach Beobachtung/Scan, gemeinsamer
Softwarekandidat und erst danach reale autonome Abnahme. MASTERPLAN v1.3 und
LAB-1 unverändert. Die Veröffentlichung behebt keine der offenen Ablaufprobleme.

V10 aus `2d93f2b`: 2.867 vollständige Produktfälle positiv, ursprüngliche
A/B/C weiterhin 0/3. Die danach entwickelte Wartekorrektur ist jetzt als
`09f866d` versioniert und bleibt unvollständig. 196 gezielte Fälle positiv; neuester
instrumentierter Source-A: 0,729335 m, zwei Ankünfte und Beobachtungen, negativ
am Auswahlbudget, kein Quellenfehler, keine Manifest-/Hardwareabnahme.
Zuvor optionalen Scan nach 5,6421 rad am Aufgabenbudget beendet und einen
Plan bei ungültigem Footprint-Sweep verworfen. Dies ist eine Ereignisfolge,
noch kein Beweis einer einzigen Ursache für alle Abbrüche.

Neuer **Codebefund**: Im adaptiven Pfad ruft `_metric_start_decision` bereits
die Zielsuche auf, bevor `_execute_metric_frontier` die neue Wartephase prüft.
Die neuen Eltern-Wartetests verwenden dagegen den Fixture-Default
`configured_scan`. Die behauptete Unterdrückung erneuter Suche ist somit für
den tatsächlich verwendeten Aufrufer nicht nachgewiesen. Ein ausführbarer
adaptiver Gegenfall und dessen Korrektur fehlen noch. **Messbefund**: Eine
Scanprobe alterte durch 425,467 ms Verarbeitung von 86,022 auf 511,489 ms,
oberhalb ihrer unveränderten 500-ms-Grenze. Das ist kein Beweis eines defekten
Sensors. Befunde/Hashes: [Audit](evidence/ap06-ablauf-audit-20261011.json).

**Veröffentlichung:** Der Nutzer hat nach der Planerstellung ausdrücklich die
Aktualisierung des Repositories beauftragt. Der vorhandene GitHub-Branch
`feature/ap06-closed-product-validation` wurde ohne Force-Push von `e14ca312`
auf `09f866d3a3e9bd7729ac4e052247b88fe43738ec` aktualisiert; `git ls-remote`
bestätigte den übertragenen Softwarestand. Enthalten sind die lokalen
Folgearbeiten sowie Plan/Analyse aus `79cd784`. Der vorliegende
Dokumentationsnachtrag ändert keine Produktdateien. Der ältere Auditbeleg
hält bewusst den Zustand vor Commit/Upload fest.

Vor Übertragung: 68 geänderte Dateien und 205 neue Blob-/Commitobjekte auf
gängige Geheimnismuster geprüft, keine Treffer; keine großen Objekte oder
erkannten privaten Aufzeichnungsdateien im Änderungssatz. Syntax und
Übereinstimmung der untersuchten Produktdateien mit den vorhandenen
Testnachweisen geprüft. Kein neuer Vollbuild oder neuer Gesamtmissionslauf
durch die Veröffentlichung, keine neue CI-Erfolgsbehauptung.
[Veröffentlichungsbeleg](evidence/ap06-publication-20261011.json).

Reale Schritte 3/4 weiter offen, keine neue Bewegung oder Installänderung.
Der begrenzte reale Punkt-1-Nachweis und dessen Rohdatenlücke bleiben bestehen.
Letzte Hardware-/Bestandsprüfung siehe unten; kein frischer Hardwarezustand
aus Simulationsresultaten abgeleitet.

**Genau nächster Schritt:** Schritt 1 des Korrekturplans: reproduzierbaren
Gegenfall mit echter adaptiver Startentscheidung hinzufügen, der vor der
Korrektur die zu frühe erneute Auswahl während der laufenden Pause zeigt.
Erst danach den Zustandsübergang korrigieren. Keine weitere Gesamtwiederholung
ohne gezielten neuen Befund. Rückfall: eigene kleine Diffs bzw. privates Overlay;
Bestandsinstall erhalten.

## Historischer v10-Prüfstand vor dem Ablauf-Audit

Punkt 1 bleibt begrenzt real positiv; Rohdatenlücke während Translation erhalten.
Punkt 2: gemeinsamer v10-Build `2d93f2b`, 14 Pakete in 172,54 s, 155
Quelle-Installgleichheiten/756 Installhashes. Vollständige 2.867 Produktfälle
positiv ohne Fehler/Skip. Ursprüngliche manifestgleiche A/B/C weiterhin 0/3:
0,293827/0,364219/0,710745 m, je eine Ankunft und Beobachtung (176/183/145
neue Zellen, C teilweise beobachtet). Alle enden am Auswahlbudget; keine volle
Passage samt Heck. C wieder mit mehr Fortschritt als v9, kein Gesamt-Grün.
Reale Schritte 3/4 nicht durchgeführt, kein Kunden-/Hardware-Abnahmebeleg.

v10 enthält getrennten Regionsfix `4f32555` und Wegfix `2d93f2b`. Unveränderte
physische Egress-Region bei vollständiger Extentdeckung ohne wirklichen Entzug
behalten; aktuelle Projektion/Historie weiter voll prüfen. 80 gezielte Fälle
und vier verstärkte Entzug-/Historienfälle positiv. Ungültiger subzelliger
Gegenfall bleibt identisch ungültig, Refresh 55,61 → 38,38 ms. Native Rückverfolgung
desselben Distanzfelds und bitgleiche Zellzentrenprojektion: 279 gezielte Fälle
positiv. Erste eigene Testdomain/Int8-Testannahmen korrigiert, Originalnegative
erhalten. Eingefrorene vollständige A-Auswahl 4,69 s, kein zulässiges Ziel;
Geometriediagnose ersetzt keine aktuelle Quelle oder geschlossene Mission.

Neue tatsächliche Ursachenprobe am aufgezeichneten A-Folgeinput: Privatabfahrt
weiter nötig; mehrere vollständige Vorwärtsrouten zwischen 0,30 und 0,55 m
zulässig. Aktuelle mögliche Sicht enthält 1/3/8 unbekannte Zellen. Bestehende
30-s-Nachbarschaftspause hält diese neuen Aufgaben noch zurück; nach originalem
Ablauf sind 5/8/9 Ansichten zulässig. Kein Timer erhöht oder vorgespult im Produkt.
Ohne korrekt behandelte Wartephase konsumieren ungeeignete Fernalternativen das
ursprüngliche 5-s-Auswahlbudget. Dies begründet den nächsten getrennten Fix,
keine aus dem eingefrorenen Input abgeleitete reale Bewegungsfreigabe.

Letzte tatsächliche rein lesende FC03 am 02:49:47 UTC: Zähler 35204/−35676
unverändert, Null-RPM, RAM 100/400/5, Lesungen 4,966/4,464 ms. Alle 1.048
Bestandsinstallhashes am 02:50:02 UTC gleich; Main sauber/unverändert. Keine
neue Hardwarebewegung, kein SDK-/OS-/Autostartwechsel. v10-Realstartskripte nur
vorbereitet. Bekannten festen LAB-Scope vor realem Start neu binden, nicht
umzentrieren. Passage-/Drei-Bereich-Aufbau und native Apple-Laufzeit nicht
erfinden. Bestehender LAB-1-Auftrag gilt ohne neue allgemeine Freigaberunde.

**Genau nächster Schritt:** bewiesene begrenzte Privatabfahrt, die nur auf die
ursprüngliche Nachbarschaftspause wartet, als wartende Arbeit behandeln statt
Auswahlbudget verbrauchen. Geometrie, echte Quellen, Cooldown, Versuchs- und
Gesamtfristen unverändert; keine gespeicherte Bewegungsfreigabe. Gezielt und mit
gleichen Originalmissionen prüfen, erst nach softwareseitigem Bestehen reale
3/4. Rückfall: nur eigenen Wartephasendiff revertieren oder eigene private PIDs
direkt geordnet stoppen und Bestandsinstall verwenden. Originalnegative und
reale Daten privat unter
`~/.local/share/amadeus/diagnostics/ap06-drive-qualified-20261010/`.

## Historischer v7-/TF-/Auswahlstand vom 11.10.2026

Punkt 1 bleibt begrenzt real positiv, mit erhaltener Rohdatenlücke während
Translation. Für Punkt 2 wird die nachgewiesene native IMU-Schreibpause im
vorhandenen Quellenpfad korrigiert: optionaler schreibgeschützter Startparameter
`isolate_sensor_output`, Default false. Wiederverwendung des vorhandenen
Encoder-Ausgabehelpers; Serializer/Spawn vor erster Erfassung, ein begrenzter
Ausgabeschlitz je bestehendem Topic, unveränderte Messbytes/Stempel und Sensor-
QoS (IMU best effort / Tiefe 5, Status/Diagnose reliable / Tiefe 10).
Genau ein DDS-Publisherbesitzer, eigenes Output-Kind ohne Bus oder Aktor.
Verlorenes Output-Kind verriegelt die passive Erfassung und schließt den
Transport; kein automatischer Neustart oder geheilter Quellenzustand.
Der gerätefreie Originalprüfstand wählt diesen vorhandenen Produktpfad explizit.
Reale Installation/Autostart und die Sensor-/Kontinuitätsfristen bleiben unverändert.

Tatsächlicher 350-ms-Schreibpausenvergleich mit gehaltenem GIL: direkter IMU-
Schreiber unterbricht Encoderkontinuität, isolierter Schreiber erhält gültige
Radproben und unveränderte Positionen. Alle 15 gezielten Helper-/IMU-/Quellen-
Isolationsfälle bestanden. Erste Testfassung enthielt zwei eigene Belegfehler:
kurzlebiges multiprocessing-Value vor Spawn verloren und native DDS-Graph-
Tiefenanzeige 0 statt lokaler Publisher-Konfiguration. Originalnegative erhalten;
Value-Lebensdauer korrigiert, tatsächliche im Kind erzeugten Publisher-QoS
separat ausgelesen, korrigierter Lauf 15/15. Keine Quellenwerte angepasst.
Vollständiger privater v7-Build `f8cedc1`: 14 Pakete in 2 min 51 s,
154 geprüfte Produktdateien Quelle/Install identisch, 755 Installhashes.
Voller Lauf 2.717 Fälle, ein Fehler im bestehenden DDS-Cancel-Gegenversuch:
Executor erreicht dessen Take-Barriere nicht. Originalnegativ erhalten;
unveränderte betroffene Datei erneut 4/4 bestanden. SDK-Befund:
`get_num_entities`/`add_to_wait_set` blockieren ebenfalls an seinem nativen
Registrierungslock, bevor `take_data` erreicht wird. Der korrigierte reine
Testnachtrag prüft tatsächlich nicht erwerbbaren Lock im Executor und hält
auch die echte spätere Cancel-Antwort / Goal-ID / Terminalität fest. Neuer
erzwungener Wait-Set-Gegenfall; betroffene Datei 5/5 bestanden. Alle 2.718
unterschiedlichen Produktfälle damit geprüft und positiv, kein behaupteter
erster vollständig grüner Volllauf und keine Fristverlängerung. Produktdateien
des Builds bleiben unverändert. Ursprüngliche A/B/C mit sauberer Quelle
`192ac68` nun beendet, alle manifestkompatibel und negativ: A 0,089590 m,
keine Ankunft/Beobachtung; B 0,365139 m, eine Ankunft/Beobachtung und 183 neue
Zellen; C 0,714527 m, eine Ankunft/Beobachtung und 145 neue Zellen. Alle
enden an `frontier_candidate_processing_budget_exhausted`, keine volle
Passage samt Heck. C erreicht zusätzlich nur 4,071 rad des zurückgestellten
Rundblicks vor `scan_task_budget_exhausted`. Keine neue reale Fahrt daraus.

Separater gemessener Empfangsfehler: trotz gültiger aktueller Encoderproben
lag die bereits gewählte TF-Pose in A/B/C 22,4–26,1 mm zurück. Tatsächlicher
DDS-Gegenversuch mit pausiertem Verbraucher: 29,9-mm-Abweisung vor Empfang,
identische Rad-/TF-Pose nach Übernahme wartender Originalnachrichten. Neuer
begrenzter Empfang über die bereits bestehenden TF-Subscriptions/Callbacks
vor gemeinsamer Pose/Referenzauswahl, keine neue Quelle oder Stempel.
Fehler beim Take sperrt ausdrücklich; fehlender Sender veraltet weiter.
25 gezielte Fälle bestanden, einschließlich echter DDS-Pause, Handleverlust
und paralleler Listenercallbacks. Privater nicht qualifizierender A-Vergleich
erreicht 0,284571 m / eine Beobachtung ohne Rad-TF-Abweisung; Empfang bis
1,535 ms, später weiterhin Auswahlbudget. Erste Diagnosekopie hatte ihren
Manifestpfad falsch auf das private Verzeichnis aufgelöst; Originalfehler
erhalten, expliziter Originalmanifestpfad korrigiert. Der neue TF-Fix ist
noch nicht gemeinsam gebaut oder als Originalgesamtmission qualifiziert.
Reale FC03 am 11.10. um 01:06:40 UTC: Positionen unverändert, beide RPM null,
RAM 100/400/5; alle 1.048 Bestandsinstallhashes um 01:06:34 UTC gleich.

Separate Auswahlkorrektur: exakte Kopien der beiden Egress-Ledger statt
wiederholtem Sortieren; geänderte Inhalte invalidieren weiterhin den Pass.
Startconnector-Suche auf umschließenden Rasterkasten des bestehenden Radius
beschränkt, mit zwei zusätzlichen Randzellen; ursprüngliche skalare
Projektion, Reihenfolge, Distanz-/Heading-/Linien- und volle Routenprüfung
bleiben. 121 gezielte Fälle positiv; finale Dictionary-Kopie zusätzlich
mit Pass-/In-place-/TF-Fällen nachgeprüft. Geometrischer Originalvergleich
A/C: 1,731→1,366 s und 1,769→1,199 s, Ziele/Beobachtungspunkte/Ranking/
Evidenzschlüssel exakt identisch. Frozenset-Zwischenfassung brachte keine
Gesamtbeschleunigung und wird nicht übernommen. Vergleiche sind reine
Geometrie, keine Quelle/Frische/Mission oder neue reale Bewegung.
Gemeinsamer neuer v8-Build und ursprüngliche A/B/C folgen.

Private Auslagerung von Egress-Geometrie ist nicht übernommen. Mehrkern-
Parentversuche enden mit nativer Explorer-Absturzaufzeichnung, darunter ein
Shutdown-Stack, der die ursprüngliche Ursache nicht beweist. Mit ursprünglichem
Ein-Kern-Explorer meldet die erste Transferfassung fehlende Kartenreferenz beim
Tuple-Deserialisieren; korrigierter ausdrücklich gebundener Transfer läuft,
bleibt aber negativ: 0 m, `start_motion_wheel_stale_after_processing`.
Eigene Rechenzeit 28–81 ms, gesamte gemessene Antwort 131–155 ms plus weitere
Parentprüfung. Keine Prozessauslagerung oder andere CPU-/Dispatcherdiagnose
als qualifiziert behaupten. Bestehender Scope-Cache ist bereits vorhanden.

Punkte 3/4 bleiben von bestandener ursprünglicher Softwaregesamtprüfung abhängig;
keine neue reale autonome Fahrt aus diesem Zwischenstand. Bekannte LAB-Kontur
nach gemessenem Fahrversatz fest neu binden. Weitere Passage-/Drei-Bereich-
Geometrie und native Apple-Laufzeit bleiben tatsächlich unbestätigt; bestehende
konkrete Rückfragen erhalten, keine erneute allgemeine Laborfreigabe.

**Genau nächster Schritt:** den separat geprüften gemeinsamen v8-Kandidaten
bauen, vollständige Regression und ursprüngliche A/B/C ausführen; nach
deren Bestehen die beauftragten realen Schritte 3/4.
Rückfall: eigenes privates Overlay direkt geordnet stoppen, Bestandsinstall
bewahren; IMU-Ausgabeopt-in zurücknehmen oder eigenen Fix gezielt revertieren.
Private Belege: `~/.local/share/amadeus/diagnostics/ap06-drive-qualified-20261010/simulation/`.

## Historischer v6-Quellen-/Dispatcherstand


Punkt 1 bleibt als begrenzte reale Anfahr-/Bremsqualifikation positiv beendet;
kein autonomer Realnachweis daraus. Punkt 2: vollständiger separater Build
`ap06-qualified-v6-20261011`, Produktquelle `cdf95b6`, 14 Pakete in 2 min 50 s,
154 geprüfte Produktdateien Quelle/Install identisch und 755 Installhashes.
Alle 2.715 Fälle der vollständigen Produktprüfung ohne Fehler/Skip bestanden.
Bestandsmain sauber, alle 1.048 geprüften Bestandsinstall-Dateien unverändert;
letzte zusätzliche FC03-Prüfung am 11.10. um 00:31:31 UTC ohne Positionsänderung,
beide RPM null, RAM 100/400/5. Kein Autostart-/OS-/SDK-Wechsel.

Der frühere v6-Vergleich vor der Prüfstand-Ausgabekorrektur bleibt erhalten.
Die drei ursprünglichen Gesamtmissionen mit unveränderter Welt, Startpose,
Sensorprofil und Budgets bleiben **0/3**: A 0,294290 m, eine Ankunft und eine
echte neue Beobachtung; B scheitert bereits an Scope-/HWT-Bereitschaft;
C 0,707064 m, eine Ankunft und eine neue Beobachtung. A und C enden später
an `frontier_candidate_processing_budget_exhausted`; C unterbricht vorher
zweimal wegen eines nach Verarbeitung veralteten Radsnapshots. Alle Strecken
dieses Absatzes sind gerätefreie Simulation, keine neue physische Fahrt.
Kein Fall räumt die Passage samt Heck; keine Gesamt- oder Kundenabnahme.

Zusätzliche, ausdrücklich nicht qualifizierende Diagnose: 307–314 ms lange
Quellenpause bei nur 24–31 ms Prozess-CPU. Drei aufeinanderfolgende native
Thread-Aufzeichnungen zeigen die Basis in `rclpy.publisher.publish` beim
Statusschreiben, gleichzeitig stehen IMU-/Plant-Verarbeitung. Mit dem bereits
real qualifizierten vorhandenen `isolate_feedback_output`-Pfad verschwindet
diese lange Erfassungspause und die Missionsphase wird erreicht; separate
Geometrie-/Auswahlfehler bleiben. Der Prüfstand verwendet diesen vorhandenen
Produktpfad nun ebenfalls, mit geerbter CPU-Affinität innerhalb seiner
gerätefreien Namespace-Grenze. Keine neue Transportimplementierung, keine
Stempel-/Frische-/Kontinuitätsänderung oder erfundene Zwischenprobe.

Gezielter tatsächlicher DDS-Schreibergegenfall: native 350-ms-Pause mit
gehaltenem Interpreterlock. Alter Prüfstand verwirft Encoderproben; korrigierter
Pfad erhält gültige Erfassung und unveränderte Positionen. Rot/Grün separat
erhalten, Grün 1/1; alle 28 betroffenen Quellen-/Isolation-/Welt-/Trace-/
Lifecycle-Fälle bestanden. Die gefrorenen Produktdateien des v6-Builds bleiben
unverändert. Neuer ursprünglicher Gesamtvergleich mit sauberer Quelle
`6c50cf5`, identischen 755 Installhashes / 154 Produktdateien, weiterhin **0/3**:
A scheitert an Scope-/HWT-Bereitschaft; B 0,354773 m, eine Ankunft / 183 neue
Zellen; C 0,704869 m, eine Ankunft / 144 neue Zellen. B/C enden später am
unveränderten Auswahlbudget; ein bzw. zwei vorangehende Geometrie-Neuprüfungen
wegen veraltetem Radsnapshot. Keine volle Passage samt Heck. Alle drei Läufe
manifestkompatibel, gerätefrei, ohne manuelle Nav-Ziele. Der Build bleibt
Produktquelle `cdf95b6`; `6c50cf5` ist der nachgeprüfte Prüfstand-/Test-/
Dokumentationsnachtrag, kein behaupteter neuer Produktbuild.

Weitere nicht qualifizierende Diagnose lokalisiert echte IMU-/Scan-
Publikationspausen von 323–343 / 329 ms. Ein ausdrücklicher nativer asynchroner
DDS-Vergleich verkürzt eine IMU-Pause auf 143 ms, hält den gemeinsam erfassten
Radpfad jedoch weiterhin 189 ms auf: nicht übernommen. Wiederverwendung des
vorhandenen Ausgabehelpers für die IMU mit ursprünglichem Sensor-QoS erhält
in einem privaten Vergleich 2.058 gültige Basiszustände ohne Verwerfung;
noch keine Produktintegration oder volle Lieferkontinuität daraus. Erster
CPU-Aufzeichnungsversuch scheitert an seiner eigenen nebenläufigen Deque-
Iteration; korrigierter Diagnoselauf und Originalnegativbeleg bleiben erhalten.

Korrigierte Messung: Auswahl 5,389 s Wandzeit / 2,053 s eigener Thread-CPU,
gleichzeitig 1,703 s Thread-CPU im ROS-Dispatcher. Eine gültige reine Radquelle
ersetzt keine rechtzeitige Geometrieentscheidung. Vier Explorer-Kerne,
begrenzter Neueste-Nachricht-Empfang, 1-ms-Dispatcherpause und drei statt sechs
Explorer-Worker ergeben keinen
vollständigen Positivlauf; keine dieser Diagnosevarianten wurde übernommen.
Frische, 20-mm-Abgleich, Kontur und Originalbudgets unverändert. Diagnosefahrten
zählen nicht als Positivfall und sind keine neue reale Fahrt.

Punkt 3 (regulärer autonomer Realstart) und Punkt 4 (erweiterte reale Abnahmen)
stehen weiter aus, bis Punkt 2 bestanden ist. Bekannte physische LAB-Kontur
nach gemessenem Fahrversatz neu binden, niemals umzentrieren. Weitere reale
Passage-/Drei-Bereich-Geometrie und natives Apple-Ziel sind noch nicht belegt;
einmalige konkrete Rückfragen stehen aus. LAB-1 und erneute Nutzerfreigabe
gelten weiterhin, keine neue allgemeine Freigaberunde.

**Genau nächster technischer Schritt:** gemessene Quellen-/Dispatcher-Konkurrenz
gezielt entkoppeln und die ursprüngliche Quellen-/Geometriebinding dabei
nachweisen, dann den
unveränderten ursprünglichen A/B/C-Vergleich bestehen und die beauftragten
realen Schritte 3/4 fortsetzen. Rückfall: eigenes privates Overlay geordnet
beenden; Bestandsinstallation erhalten. Prüfstanddelta gezielt rücknehmbar.
Private Originale und Rot/Grün: `~/.local/share/amadeus/diagnostics/ap06-drive-qualified-20261010/`.

## Historischer v5-Zwischenstand vom 11.10.2026

Punkt 1 bleibt als begrenzte reale Anfahr-/Bremsqualifikation beendet, mit
Positionsencodern, tatsächlichen FC03/FC06-Belegen und unabhängigem LiDAR-Vergleich.
Keine autonome Produktabnahme daraus. Der ursprüngliche Rohdatenrecorder verfehlte
insbesondere die Translation; diese Sichtlücke und die alten negativen Läufe bleiben
im Protokoll ausdrücklich erhalten. Letzte rein lesende Hardwareprüfung um
22:56:56 UTC: unveränderte Positionen, beide RPM null, RAM 100/400/5.
Alle bewegten Vergleichsfälle dieses Abschnitts sind gerätefreie Simulationen.

Punkt 2: Kandidat `ap06-qualified-v5-20261011` baute 14 Produktpakete in
2 min 50 s, 154 geprüfte Produktdateien Quelle/Install identisch, 755 Installhashes.
Produktbuild `205c2c4`, Testwrapper-Nachtrag `94ba58e`; unveränderte Produktdateien
nachgewiesen. Volllauf mit 2.714 Fällen enthielt zunächst zwölf Fehler eines
Wrappers ohne den neuen optionalen Parameter. Reparierte Datei: 62/62 bestanden;
alle zwölf negativen Fälle erneut geprüft, alle 2.714 eindeutigen Fälle bestanden.
Der ursprüngliche negative Volllauf wird nicht ersetzt. Einheitlicher privater
nativer ARM-Unterbau und tatsächliche SDK-/Pythonauflösung bleiben gebunden;
Bestandsmain sauber und alle 1.048 geprüften Bestandsinstall-Dateien unverändert.

Drei ursprüngliche Gesamtmissionen v5 weiterhin **0/3**, bei unveränderter Welt,
Startpose, 2-s-Beobachtungsfenster, 5-s-Auswahl-/Kartenfrist, Sensor- und Gesamtbudgets:
A 0,164762 m, 1 Ankunft/1 Beobachtung (174 echte neue Zellen); B 1,243869 m,
2 Ankünfte/2 Beobachtungen; C 0,259991 m, 0 Ankünfte/0 Beobachtungen. Alle endeten
später am Auswahl-Rechenbudget, kein Fall räumte die Passage samt Heck.
B-Rundumbeobachtung nur 5,00455 rad bis zum 150-s-Aufgabenbudget, kein voller
Positivscan. C verwarf während der Fahrt einen nach Verarbeitung veralteten
Radsnapshot und hielt an; danach eine Geometrieablehnung. Quellenfrische oder
Ankunftstoleranzen werden daraus nicht gelockert.

Die gebündelte identische Strahlprüfung beseitigt den bisherigen ersten Null-
Beobachtungsbefund in A. Ein zusätzlicher Diagnoselauf mit Entscheidungsaufzeichnung
scheiterte dagegen bereits an Radbereitschaft: echter 346-ms-Plant-/Quelle-Aussetzer,
kein Auswahl-Pickle und kein neuer Missionsbeleg. Eine Explorer-Verteilung auf
Kerne 3/4 brachte bei 11 bestandenen Isolationstests keinen Gesamterfolg
(A 0,169440 m, 1/1); Änderung nach Vergleich wieder zurückgenommen.

Neue konkrete Messung an gesicherten ursprünglichen Anfangsdaten: 40-cm-
Vorwärtsziel mit vollständiger Route und endlicher neuer Sicht zulässig,
45 cm bereits durch unveränderte Geometrie abgelehnt. Bisherige frühe Auswahl
30 cm, vorhergesagter echter RPP-Stop 15,25 cm wegen der unveränderten
15-cm-Ankunftsscheibe. Die kurze Suche bevorzugt nun ihr entferntestes tatsächlich
vollständig geprüftes Ziel im selben bestehenden lokalen Suchbereich; weder
Wegpunktvorgabe noch vergrößerter Scope, neue Freizellen oder höheres Budget.
Gezielte Regression: 30/30 bestanden, einschließlich zuvor negativem tatsächlichem RPP-Stopnachweis und ursprünglichen Route-/Sicht-/Cooldown-/Versuchskappen. Eingefrorene ursprüngliche ARM-Anfangsdaten wählen nun 43 cm / 177 endliche potenzielle Punkte in 1,246 s bei identischem vollständigem lokalen Evidenzhash; keine Livebeobachtung daraus. Neuer vollständiger Kandidatenvergleich erforderlich.

Punkt 3 (regulärer autonomer Realstart) und Punkt 4 (erweiterte reale Abnahmen)
sind damit weiter offen. Bekannte physische LAB-Kontur wird nach tatsächlichem
Fahrversatz neu an TF/Karte gebunden, niemals umzentriert. Neue reale Passage/
Drei-Bereich-Geometrie und verfügbares natives Apple-Ziel sind noch nicht belegt;
einmalige konkrete Rückfragen dazu sind gestellt. Keine weitere allgemeine
Freigaberunde: erneute Nutzerfreigabe und LAB-1 gelten weiterhin.

**Genau nächster technischer Schritt:** geänderte kurze Auswahl separat prüfen,
in einem neuen vollständigen privaten Kandidaten bauen und die ursprünglichen
A/B/C-Gesamtmissionen abnehmen; danach den bereits beauftragten autonomen LAB-
Start und die abhängigen realen Abnahmen fortsetzen. Bestehende Installation und
Autostart bewahren. Rückfall: eigenen Kandidaten geordnet beenden, vorhandenen
Bestandsinstall nutzen; die Auswahländerung lässt sich gezielt zurücknehmen.
Private Originalbelege: `~/.local/share/amadeus/diagnostics/ap06-drive-qualified-20261010/`.


## 10.10.2026 – beauftragte Folge 1–4 wird ausgeführt

Punkt 1 beendet als begrenzte Komponentenqualifikation: Register 100/400/5
tatsächlich zurückgelesen, RPM-Skalierung 1 beibehalten. Negative Drehung und
25-cm-Translation mit gemessenem Stop positiv. Translation einschließlich
Ausrollen 29,850 cm Encoder / 30,066 cm unabhängiger LiDAR; lokale ICP-Residuen
3,85 mm. Gerade Phase 4,185 s, gesamter Lauf 6,109 s, nach letztem Vor-Stop-
Sample 4,411 cm Ausrollen; bestehende 12,8-cm-Stopphülle genügt für diese Probe.
Steady-State tatsächlich etwa 0,079 m/s bei 0,08 m/s Soll, FC03 122 RPM;
kein belegter Faktor-zwei-Encoder-/RPM-Fehler. 46/46 FC06 bestätigt, genau zwei
Startimpulse. Danach je Motor 1.970 tatsächliche FC03-Proben mit identischer
Position und Null-RPM. Beide feste Komponenten sind keine selbstgewählten
Explorer-Ziele. Keine autonome Produkt-/Kundenabnahme daraus ableiten.

Sichtlücke im Rohdatenbeleg ausdrücklich: zweiter 90-s-Recorder endete knapp
vor Translationsbeginn. Originale Diagnose-/Tor-/Base-Ereignisse und tatsächliche
RAM-Bustransaktionen erfassen den Lauf; unabhängiger LiDAR-Wegvergleich nutzt
Originalscans vor Fahrt und zusätzliche späte Stillstandsaufzeichnung. Keine
vollständige bewegte Raw-Bag-Sensorabdeckung behaupten. Private Originale
bleiben erhalten, eigene Prozesse geordnet direkt beendet. Punkt 2 folgt:
einheitlicher Produktkandidat und ursprüngliche AP-06-Fälle A/B/C.

Unabhängige Auswertung der Original-LiDAR-Scans ohne Rad-/EKF-
Prior bestätigt R17: 26,84 cm, +16,69° / −16,37°, lokale Fitresiduen etwa
3–4 mm. Neuer R18-Vergleich startete real und durchlief Vorwärts- und beide
Drehphasen; beim Schlussstop kontrollierter Monitorabbruch bei 0,60957 rad
Phasenwinkelspanne gegen 0,6 rad Budget. Kein vollständiger Positivlauf daraus.
Encoder gültig, keine Modbus-Lesefehler, frischer Stillstand bestätigt.
90 reale FC06-Transaktionen alle bestätigt, genau sechs Startimpulse; ein
periodisches Neustarten der Rampe ist damit widerlegt. Register 2000/400/5
zurückgelesen. Positionsdaten zeigen etwa 1,48 Motor-RPM/s Beschleunigung.
Expliziter Vergleich mit Register 100 und getrennten begrenzten Komponenten-
proben vorbereitet; bisher noch keine Fahrt mit dieser Rampeneinstellung.

Zusätzliche lesende Nachprüfungen: einmal 130-ms-Paar gegen 120-ms-Grenze,
anschließend bei CPU-Trennung eine 199-ms-Lücke direkt nach der ersten
Odometrieausgabe. Beide negative Befunde bleiben erhalten. Kaltmessung der
ersten ROS-Serialisierung: String 79,6 ms, Odometry 195,9 ms; danach jeweils
unter 0,3 ms. Ausgabehelper lädt nun die tatsächlichen Serialisierer vor
Baseline/Timer, verwirft Initialisierungsbytes lokal und publiziert keine
Aufwärmprobe. 128 Tests mit expliziter Sourceauflösung bestanden; erste
versehentlich alte Overlayauflösung ist als negativer Testnachweis erhalten.
Separater Base-Build erfolgreich. Lesender Dreiminutenlauf 180,009 s beendet:
3.230 aufgezeichnete gültige Radproben, keine Paarverwerfung, längstes Paar
31,386 ms, größte Radheaderlücke 63,896 ms; 608/608 Nahstatusproben gesund.
HWT-Anlauf nicht als durchgehend fertige Fusion ausweisen. Aktiver Folgestart
noch ohne Bewegung: Tor verwendete bei frischen IMU-Messungen 1,196 s alte
Status-Callbacks und verriegelte; Start nicht gesendet, Weg/Kommandos null.
Originalbefund bleibt erhalten; Status-Empfangspfad wird separat korrigiert.
Keine Frische-, Kontinuitäts- oder Bremsgrenze angehoben.

Nutzerauftrag: Anfahr-/Bremsmessung, ein reproduzierbarer Kandidat samt drei
ursprünglichen AP-06-Gesamtfällen, regulärer autonomer LAB-Start, danach die
weiteren Gesamtprüfungen gemäß MASTERPLAN v1.3 / WE-M4–M7. LAB-1-Freigabe
wurde erneut ausdrücklich erteilt. Istbasis: separater Checkout e14ca312 mit
den dokumentierten eigenen Korrekturen R1–R17; Bestandsmain/-install bleiben
erhalten. Keine vorweggenommene Kunden- oder Gesamtqualifikation.

Zuerst tatsächliche FC03-/FC06-Transaktionen und Positions-/LiDAR-Referenz
prüfen. Erster bewegter Vergleich bleibt die feste 25-cm-/±15°-Sequenz,
90 s / 0,5 m / 0,6 rad, gleiche Schutzkette und physischer LAB-Bereich unter
Berücksichtigung des bereits gefahrenen Versatzes. Änderungen an Rampen erst
nach gemessener Ursache, separat testen. Anschließend ein eigener vollständiger
Produktbuild auf gepinntem nativen Unterbau; ursprüngliche Simulation A/B/C
bleibt gerätefrei und ohne Zielvorgaben. Reale Folgebudgets vor Ausführung
festlegen. Unverifizierte Passage, neue Bereiche oder native App-Ergebnisse
nicht aus dieser lokalen Fläche ableiten. Rückfall: eigene Prozesse geordnet
stoppen und den erhaltenen Bestandsinstall verwenden; kein Autostartwechsel.

## 10.10.2026 – Bewertung nach der erfolgreichen LAB-Sequenz

R17 bleibt ein vollständiger positiver fester Fahrtest mit gültigen Encodern,
bestätigten Zwischenstopps und erhaltenem Bestandsinstall. Die normale
Explorer-/Nav2-Mission wurde dabei noch nicht ausgeführt; ursprüngliche AP-06-
Gesamtqualifikation weiterhin 0/3. Ein einzelner positiver Lauf belegt noch
keine Reproduzierbarkeit nach Kaltstart oder unter Kundenlast.

Neue Auswertung der unveränderten Originaldaten: Vorwärtsphase 21,377 s bis
25 cm Sollfortschritt, während `/cmd_vel` zeitlich etwa 99,7 % ungleich null
war und nach der Glättung überwiegend 0,08 m/s verlangte. Beide Drehphasen
dauerten jeweils etwa 10,2/10,3 s. Während der Vorwärtsfahrt stieg die gemessene
Encoder-Geschwindigkeit langsam von etwa 0,003 auf 0,022 m/s. Zeit-/Kommandosummen
aus dem unabhängigen vollständigen Bag bestätigen die Auswertung der Diagnose-
Callbacks. Das beweist eine erhebliche Soll-/Bewegungsabweichung, aber noch
nicht deren Ursache. Kein belegter Encoderdefekt oder wiederholter Schutzstop.
Encoderweg etwa 25,1 cm und Kartenpose etwa 24,8 cm sind plausibel zueinander;
die Kartenpose ist wegen gemeinsamer Quellen keine unabhängige Bodenreferenz.

**Genau nächster begrenzter technischer Auftrag:** Antriebsübertragung,
Anfahr-/Bremsverhalten und reale Trackingreserve des bestehenden Kandidaten
qualifizieren: tatsächliche Register-/Starttransaktionen, wirksame Rampen,
Positionsfeedback und unabhängige Strecke/Winkel gemeinsam messen. Innerhalb
des bestehenden LAB-Bereichs, mit frischen Quellen und unveränderter Schutzkette;
keine blinde Fristerhöhung, Counts-/Geometrieänderung oder zusätzliche Fläche.
Vor einem neuen Stackstart den gefahrenen Versatz bei der Bindung desselben
physischen Laborbereichs berücksichtigen. Diese Bewertung startet keine Fahrt.

Danach Korrekturen in einem eindeutig versionierten separaten Kandidaten
zusammenführen und die ursprünglichen geschlossenen Fälle A/B/C nachprüfen;
dann den regulären autonomen Start mit nützlicher erster Beobachtung abnehmen.
Weitere Beobachtungsaufgaben, ganze Passage, Rundweg, Hindernis/Halt/Fortsetzung
und Speichern/Wiederaufnahme folgen gemäß MASTERPLAN/WE-M4–M6. Native App-
Abnahme bleibt unter WE-M7 getrennt. Kein dauerhafter Installwechsel aus der
Bewertung. [Messgrundlage und Folgeschritte](JETSON_VORLAUF_AP06_20261010.md).

## 10.10.2026 – erste vollständige reale feste LAB-Fahrsequenz bestanden

Die Startablehnungen der ausdrücklich aktivierten Stage-3-Diagnose wurden im
separaten Checkout korrigiert. R17 startete um 18:42:39 UTC und beendete um
18:43:25 UTC regulär die feste 25-cm-/+15°-/−15°-Sequenz mit drei gemessenen
Stillständen. Vorwärtsphase einschließlich Ausrollen etwa 26,5 cm, gesamter
Encoderweg 27,568 cm; gemessene Drehungen einschließlich Nachlauf etwa +16,45°
und −16,24°. Abschließend beide Motor-RPM null, Encoderfeedback gültig und
frisch, keine Modbus-Lesefehler oder Encoder-/Ausgabeprozessverriegelung.

Korrigiert: feste physische LAB-Kontur statt übergroßer Körperscheibe,
leerer Idle-Missionsstatus, echte Quellenzustellung vor Entscheidungen,
unbegründete Nullimpulse im erlaubten Diagnosemodus und unveränderliche
Session-/Scopeepoche trotz wachsender Karte. Tatsächliche HOLD-Historie und
Recoverybudgets bleiben erhalten; explizite Quittierung nur nach geprüfter
Erholung und gemessenem Stillstand. Der private Monitor unterscheidet rohe
Encoder-Winkelvariation von vollständigen Winkelspannen der überwachten
Phasen. Keine Frist, Haltwirkung oder physische Schutzgrenze angehoben.

87 verschiedene gezielte Software-/DDS-Fälle und vier private Monitorfälle
bestanden. Separater Navigationsbuild R17 erfolgreich (6,58 s). Ausgeführt:
Base R10, Fahrtor R15, Diagnose R17 mit derselben tatsächlichen Sensor-/EKF-/
SLAM-Quelle und dem ursprünglichen physischen Scope-/Radanker. Abgebrochene
Vorversuche bleiben als solche dokumentiert; keine negative Historie gelöscht.
Eigene Prozesse geordnet über direkte PIDs beendet, serielle Geräte frei;
abschließend 20 rein lesende FC03-Proben je Motor: null RPM und stabile
Positionen. Bestandsinstallation mit 1.048 Dateien und Originalcheckout erhalten.

Dies ist ein vollständiger begrenzter LAB-Komponententest, keine autonome
Wohnungserkundung oder Kundenabnahme. AP-06 bleibt **0/3** Gesamtmissionen.
Der nächste fachliche Schritt ist der echte autonome Start-/Trackingnachweis
mit anschließendem AP-06-Gesamtlauf innerhalb eines passend geprüften Bereichs.
[Build, Fahr- und Quellenbelege, Sensorzeiten und Sichtlücken](JETSON_VORLAUF_AP06_20261010.md).

## 10.10.2026 – realen Fahrablauf vorbereitet, aktueller Startnachweis negativ

Auf Auftrag „alles für die Fahrt vorbereiten“ ausführbare private Abläufe für
passiven/aktiven Stack, neue Scopebindung, Explorer, begrenzte Mission und
geordneten Stopp vorbereitet. Keine weitere allgemeine Freigabe erforderlich.
Abbruchschwellen: 90 s Missionszeit, 0,5 m Encoderweg, 0,6 rad Encoderwinkel;
Cancel über bestehenden Mission Manager, anschließend frischen Stillstand prüfen.

Neuer passiver Vorlauf 180,070 s, keine Encoderverriegelung, max. Paarzeit
98,551 ms, 675/675 Nahstatus beidseits gesund. Neue Karten-/TF-/Quellenbindung
gelungen; erste transient fehlgeschlagene TF-Bindung erhalten. Sechs anschließende
aktuelle passive Geometrieproben gültiger Eingänge bleiben negativ. Der neue
Geradenprüfer ist weiterhin nur Diagnose, kein aktiver Ersatz.

Konkreter Vorbereitungsfehler behoben: Stillstandsprüfung im privaten
Missionsmonitor nutzte Soll-RPM. Neue Version verlangt gemessene Motor-RPM=0
und frische Encoder-Rückmeldung; zwölf Gegenproben bestanden. Historischer
Monitor unverändert als Beleg erhalten. Keine Produktgrenze angehoben.

**Ablauf vorbereitet, noch keine Fahrbereitschaft oder Realfahrt.** Alle eigenen
Prozesse geordnet beendet, abschließend 20 FC03-Proben je Motor mit 0 RPM und
unveränderten Positionen, Geräte frei und Bestandsinstallation unverändert.
Private ausführbare Anleitung/Ergebnis unter
`~/.local/share/amadeus/diagnostics/ap06-drive-preparation-20261010T1308Z`.
Nächster technischer Schritt bleibt gültige reale Startabdeckung/Tracking und
anschließende Live-Qualifikation; keine identische Fehlstartserie. AP-06 0/3.

## 10.10.2026 – Ersatzprüfung implementiert, Realfreigabe weiterhin offen

Auf ausdrücklichen Auftrag, einen funktionierenden Ersatz der Startprüfung zu
entwickeln, kontinuierlichen Geradenprüfer `metric_start_sweep.py` erstellt und
in das vorhandene **lesende** Startdiagnosewerkzeug eingebunden. Vollständiger
Vorfahrtkorridor, analytische Winkelhülle, Positionsabweichung und exakte
Rasterzellpolygone ersetzen dort punktweise/rasterpauschale Näherungen.
Fester Anfangsbestand bleibt auf seine tatsächliche gepaddete Körperüberdeckung
begrenzt; belegte Zellen und neue unbekannte Außenfläche bleiben negativ.

Separater Zweipaketbuild erfolgreich, 47 gezielte neue/bestehende Prüfungen
bestanden. Auf unveränderten gespeicherten Roh-/Kostenrasterproben ist die
ideale 25-cm-Gerade positiv. Das deklarierte Versuchsband 20 mm/0,05 rad bleibt
negativ; auf der Rohkarte 0,017601 m² zusätzliche unbekannte Fläche. Das Band
ist keine qualifizierte reale Reglergarantie. Neue Rechnung ist kein Ersatz
für aktuelle Quellen-/TF-/Controller- und Stoppnachweise.

**Noch kein funktionierender aktiver Ersatz und keine Realfahrt.** Aktive
Startprüfung unverändert, keine Schutzprüfung gelöscht, keine Roboterprozesse
gestartet. Nächster erforderlicher Schritt: nachgewiesene reale Abdeckungs- und
Trackingbedingungen herstellen, anschließend denselben Geometriekern mit der
bestehenden festen Live-Referenz-/Historienbindung qualifizieren. Bis dahin
keine Aktivierung durch ein positives ideales Offline-Ergebnis. AP-06 weiter
0/3; kein Kundenauslieferungsnachweis. Details und Rückfall im
[Vorlaufbericht](JETSON_VORLAUF_AP06_20261010.md).

## 10.10.2026 – unabhängiger Gegencheck: Startsperre ist kein Raster-Rundungsfehler

Softwarekorrektur erneut untersucht. Kontinuierlicher Polygonschnitt belegt:
Schon die vorhandene 10-mm-Reserve ohne Rasterhalbdiagonale liegt teilweise
außerhalb des gespeicherten Startpolygons und über unbekannter Rohfläche.
Vier gezielte Ausfahr-/Schutztests bestanden, darunter zulässige Vorwärtsausfahrt.
Keine belegte Korrektur, die diesen Realstart ohne neue Beobachtung oder
unqualifizierte Reservenreduzierung freigibt. Keine Bewegung, AP-06 weiter 0/3.
Es fehlt keine Laborfreigabe. Erforderlich bleibt gültige Startabdeckung bzw.
beobachtbare Ausgangslage; die frühere Vermutung einer reinen Rundungssperre
ist für diesen Befund widerlegt. Details im letzten Vorlaufnachtrag.

## 10.10.2026 – keine weitere Freigaberunde; technischer Startnachweis bleibt negativ

Nutzer stellt klar: im bestehenden Labormodus nicht auf eine erneute hintere
Bereichs-/Laborfreigabe warten. Die pauschale 50-cm-Nachfrage ist zurückgezogen;
sie ist weder eine allgemeine Voraussetzung für Vorfahrt noch ein Ersatz
für den technischen Geometrienachweis. Keine größere freie Fläche daraus
als gemessen oder geprüft behauptet.

Zusätzliche lesende Zerlegung der erhaltenen Realproben: Von 108 reservierten
Startzellen außerhalb des bisherigen Polygons sind 105 in der Rohkarte unbekannt,
drei beobachtet frei; keine dieser Proben belegt ein Hindernis. Eine ideale
Vorfahrt um 2 cm verlässt die Polygonkante, rechtfertigt aber nicht rückwirkend
die ungeprüfte Anfangsstrecke. Die bestehende Startprüfung bleibt negativ.
Keine neue Mission, keine Bewegung, keine Schutzgrenze geändert. Es wird nicht
auf eine zusätzliche allgemeine Freigabe gewartet. Nötig ist ein gültiger
technischer Start-/Abdeckungsnachweis; vorhandenes Abdeckungspaket und neue
Messdaten verwenden, keine unbekannten Zellen zu Freiraum erklären.
Details im letzten [Vorlauf-Nachtrag](JETSON_VORLAUF_AP06_20261010.md).

## 10.10.2026 – Geometriefrische verbessert; hintere reale Bereichsgrenze muss geklärt werden

Erneuter Fahrstartauftrag bearbeitet, weiterhin **keine reale Bewegung, AP-06 0/3**.
Gemessene Mehrfachberechnung des unveränderten Scope-Rasters begrenzt gecacht;
keine Sensor-/Footprint-/Scopegrenzen gelockert. Separater Build und 240 gezielte
Tests bestanden. Neuer 180,057-s-Vorlauf: 3.450 Encoderpublikationen, längstes
Paar 34,159 ms, keine Ablehnung; 620/620 Nahstatus beidseits gesund. Sechs reale
passive Geometrieprüfungen halten die Frischegrenzen ein (169–434 ms).

Startreferenzen bleiben ungültig: 108 reservierte Zellen pro Raster hinter der
bisher bestätigten 13-cm-Grenze. Konkrete Frage nach tatsächlich geprüftem
hindernisfreiem Boden bis 50 cm hinten gestellt; Antwort noch ausstehend.
Allgemeine LAB-1-Freigabe gilt weiter. Ohne Antwort keinen größeren Bereich
annehmen. Nach Klärung neu binden und begrenzt über die Schutzkette fahren.
Alle eigenen Prozesse beendet, Stillstand per FC03 bestätigt, Installation
unverändert. Details und Recorder-Zeitspitzen im letzten
[Vorlauf-Nachtrag](JETSON_VORLAUF_AP06_20261010.md).

## 10.10.2026 – Encoder/HWT im finalen Lauf gesund; Missionsauftrag ohne Fahrt abgebrochen

**Aktuell: reale Explore-Mission gesendet, aber 0 m / 0 rad Bewegung; AP-06 0/3.**
351 betroffene Tests und getrenntes `robot_state_estimation`-Overlay bestanden.
HWT-Rohdaten/Drehraten nutzen jetzt wie die vorhandene Radquelle einen aktuellen
DDS-Take mit Originalstempeln vor der Entscheidung. Prozesslokale CPU-Zuteilung
und Encoder-GC-Vorlauf stabilisierten die letzten Encoderläufe; keine Grenzwerte
angehoben. Letzter passiver Bag: 180,089 s, 3.266 Encoderpublikationen, max.
50,396 ms/Paar, keine Ablehnung. Aktiver Bag: 300,052 s, 4.731 Publikationen,
max. 40,041 ms/Paar, keine Encoder-/HWT-Verriegelung nach dem Einlauf.

Der Auftrag erreichte den Explorer, scheiterte jedoch **vor** einem Fahrbefehl:
`self_body_scan_stale_after_processing`, Geometriearbeit 677,016 ms und finales
Scanalter 770,524 ms gegenüber 500 ms. Vorhandener Neuversuchsrahmen bereits
benutzt. Zusätzlich `start_egress_obstacle_or_scope` bei beiden Startreferenzen.
Genau nächster Schritt: die konkrete Geometriearbeit profilieren und die
Footprint-/Scope-Rasterkante auftrennen; keine Fristerhöhung oder Bereichserfindung.

Roboter abschließend per 20 FC03-Proben je Motor still; Prozesse beendet,
Ports frei, 1.048 Bestandsinstall-Dateien unverändert. Keine reale Fahrabnahme.
Details, neue Quellen-/Sensorzeiten und Rückfall im letzten Nachtrag des
[Vorlaufberichts](JETSON_VORLAUF_AP06_20261010.md).

## 10.10.2026 – erste reale Fahrt vorbereitet, aktive Stillstandsprüfung negativ

**Aktuell: ausdrückliche Labor-/Fahrfreigabe des Nutzers liegt vor; technische
Voraussetzung weiterhin nicht erfüllt. Keine Bewegung ausgeführt, AP-06 0/3.**
Nach Rechnerneustart aktuelle Sensoren/Scope neu geprüft. TF-Empfang des
Bereichswerkzeugs von Karten-/Grapharbeit entkoppelt; Originalstempel und
0,8-s-Grenze erhalten, zwei reale Scopebindungen gelungen. Ein späterer
TF-Frischefehler bleibt als Gegenbeleg erhalten.

Aktive Basis als alleiniger Busbesitzer zunächst nach acht Ausgaben mit
239,018-ms-Paar verriegelt. Gezielte Startkorrektur: erste Encoder-Messbasis
auch aktiv erst nach vorhandenem 15-s-Vorlauf. Danach 2.438 Publikationen,
Paarzeiten maximal 96,596 ms und zwischenzeitlich gültige Quellen, später aber
181,212-ms-Samplelücke gegenüber 180 ms. Keine Frische-/Stoppgrenze erhöht.
181 betroffene Tests bestanden und neues Launch-Overlay separat gebaut;
kein Software-Gesamtpositivnachweis und kein Bewegungsauftrag daraus abgeleitet.

Ein Explorer-Aufruf ohne vorhandenes Profil wurde im Leerlauf beendet; kein
Auftrag gesendet. Vorbereiteter Start bricht nun vor Launch ab, wenn das
explizite gebundene Profil fehlt. Alle realen Kommandos/Encoder/RPM null,
abschließend je Motor 20 FC03-Proben null, Prozesse beendet/Ports frei und
1.048 Bestandsinstall-Dateien unverändert.

**Genau nächster Schritt:** Im aktiven Basisprozess den belegten 181,212-ms-
Kontinuitätsverstoß mit FC03-, Callback- und DDS-Publikationszeiten korrelieren
und die Ursache beheben; erst danach den vorbereiteten begrenzten Fahrtest
mit frischen Quellen und neuer Scopebindung starten. Keine pauschale
Fristerhöhung, keine wiederholten identischen Starts. Vollständige Belege und
Rückfall im letzten Nachtrag des [Vorlaufberichts](JETSON_VORLAUF_AP06_20261010.md).

## 10.10.2026 – historische Sensorverträge angewandt, Encoder teilweise korrigiert

**Aktuell: AP-06 weiterhin 0/3; keine Kunden-/Fahrtfreigabe.** Separater
Kandidat `fix/ap06-passive-sensor-timing`, Basis `e14ca312`, noch uncommitted.
Die historische VL53-Diagnose ist geklärt: gesunde, frische PARTIAL-Frames mit
leeren Nahwolken sind laut finalem Vertrag vom 25.09. kein eigener Sensorfehler.
615 aktuelle vollständige Tripel erfüllen die vorhandene Offline-Health-Prüfung;
unbekannte Sichtbereiche und die frühere reale Frischelücke bleiben getrennt.

Encoder-DDS-Publikation blockierte den Lese-Callback nachweislich bis 297,5 ms.
Gezielter Patch trennt alle drei Ausgaben in einen begrenzten Prozesskanal;
Originalstempel, exklusive FC03-Quelle und 120/180-ms-Grenzen unverändert.
170 betroffene Tests bestanden, separates Overlay gebaut. Zwei neue passive
Dreiminutenaufnahmen: erster Lauf nach 664 Publikationen mit 169,8-ms-Paar
verriegelt; zweiter Lauf 3.200 Publikationen, keine Ablehnung, maximal 66,3 ms,
am Ende Quellen bereit. Im Recorder dennoch bis 329,1 ms Rad-Empfangsalter.
Damit Teilkorrektur und ein positiver Leser-/Endstatusnachweis, keine robuste
Gesamtfreigabe. Kein Aktorprozess, keine Mission; Installation unverändert.

**Genau nächster Schritt:** Den getrennten Ausgabeweg bei Reader, DDS und
Gate-Empfang zeitlich korrelieren, um die verbleibende Zustellspitze und ihre
Wirkung auf Quellenfrische nachzuweisen; den erhaltenen Paarzeit-Gegenfall
dabei nicht verwerfen. Keine weiteren identischen Fehlstarts oder gelockerten
Fristen. TF-/Scopebindung, geometrische Sichtgrenzen und acht ursprüngliche
Regressionstestfehler bleiben offen. Messungen, Quellenbindung, verworfene
Ansätze und Rückfall im [Vorlaufbericht](JETSON_VORLAUF_AP06_20261010.md).

## 10.10.2026 – Jetson-Build erfolgt, passiver Quellen-/Sichtnachweis negativ

**Aktuell: ursprüngliche AP-06-Abnahme weiterhin 0/3; keine Kundenfreigabe.**
Exakter Übergabestand `e14ca31276b26be2d88397b310301dad3c4e9600` im neuen
Checkout `/home/p/roboter_worktrees/ap06-e14ca312-validation`, separater
AArch64-Release `ap06-20261010T070231Z`. 31 native und 14 Produktpakete,
LiDAR-Overlay und TF-Prüfwerkzeug gebaut; Quellen-/CMake-/Runtimepräfixe
gebunden. Bestehender Checkout und 1.048 Install-Dateien unverändert.

Vollständiger Produktlauf: 2.456 registrierte Tests, 38 fehlgeschlagen.
Gezielte Wiederprüfung der 38 Fälle mit korrekter isolierter Testumgebung:
30 bestanden, acht weiterhin negativ (DDS-Registrierung, Auswahlbudget,
öffentliche Beobachtung). Kein Produktcode/Grenzwert geändert, kein Gesamt-Grün.

Zwei abgeschlossene passive 180-s-Aufnahmen, zweite ausdrücklich zur Erfassung
des Anlaufs. Encoder in beiden Läufen wegen Kontinuitätslücken verriegelt
(334/371 ms gegenüber 180 ms). HWT im ersten Lauf terminaler serieller
Transportfehler, im zweiten Lauf grundsätzlich bereit mit gemessenen Lücken.
Beide aktuellen Scopevorbereitungen scheitern an TF-Zeitbindung; kein Explorer,
keine Mission, keine Fahrt. Eindeutige Karten-/TF-Eigentümer ersetzen diese
fehlende Zeitkonsistenz nicht. Vier Nahbereichswolken durchgehend leer,
Qualität PARTIAL, keine vollständig beobachteten Spalten; zusätzlicher
LiDAR-Hecksektor von etwa 68 Grad ausgespart. OAK bleibt aus.

Stacks/Recorder beendet, Ports frei, Abschlussencoder unverändert/0 rpm.
Reale Bags/Karten/Bindungen nur privat. Vollständige Messdefinitionen,
Buildabweichungen, Grenzen und Belegpfade im
[Jetson-Vorlaufbericht](JETSON_VORLAUF_AP06_20261010.md).

**Genau nächster Schritt:** Die im passiven Originalstack gemessene
Encoder-Kontinuitätslücke mit vorhandenen Reader-/Transport-/Callbackzeiten
ursächlich isolieren und eine etwaige gezielte Korrektur separat passiv prüfen.
Offene TF-/Nahbereichs- und Regressionstestbefunde bleiben dabei offen;
keinen aktiven oder Kundenpositivlauf daraus ableiten.

## 08.10.2026 – Konzeptvergleich und überprüfbare Jetson-Übergabe

**Aktuell: ursprüngliche AP-06-Abnahme 0/3; keine Kundenfreigabe.**
Geprüfter Produktkandidat `c5d2a9c00d146851799a907ba725ef0d0f30c815`,
gleicher AP-06-Branch. Folgende datierte Einträge bleiben als Historie erhalten.

Umgesetzt sind ein abgegrenzter Konzeptprüfstand, phasenbezogene Drehprüfung,
öffentliche Kartenfortsetzung bei vollständig leerem privaten Startbestand,
begrenzte Wiederprüfung während der Verarbeitung abgelaufener Scan-/Posedaten
und ein passiver Start mit aktueller Scope-/Quellenbindung. Quellengrenzen,
Stopbedingungen und ursprüngliche Aufgaben-/Missionsbudgets bleiben bestehen.

Letzter Explorer-Build und **1.808 registrierte Explorer-Tests bestanden**,
0 Fehler/0 Skips. Übrige 13 Produktpakete unverändert seit geprüftem
14-Paketbuild; native Szenarien zuletzt 9/9 am unveränderten nativen Stand.
Diese Prüfungen ersetzen keine Gesamtmissionen und werden nicht addiert.

Sechs abgeschlossene Konzeptläufe bleiben negativ. Letzter regulärer
Konzeptlauf: drei Ankünfte/drei Beobachtungen, dann 5-s-Auswahlbudget erschöpft.
Zusätzlicher Diagnoselauf: zwei Ankünfte/zwei Beobachtungen; eine tatsächliche
Frische-Wiederprüfung führt zur Folgeankunft, später verbraucht ein erneuter
Poseablauf das vorhandene Aufgabenversuchslimit. Ganze Passage fehlt.
23 aufgezeichnete Auswahlaufrufe reproduzieren den älteren Auswahlabbruch
nicht. Originaler Gyro-HOLD-Stoppfall bestanden; der erneute Cancel-Versuch
scheitert bereits vor Fahrt an einer Encoder-Zeitlücke und zählt nicht als
Cancelnachweis. Exakte Resultate, Zeiten und Gegenfälle im
[Belegbericht](evidence/ap06-concept-20261008/README.md).

**Nächster Schritt:** Nutzer übernimmt den separaten lokalen Build und
passiven dreiminütigen Quellen-/Sichtnachweis nach
[JETSON_KONZEPTTEST_AP06](JETSON_KONZEPTTEST_AP06.md). Das Paket enthält
prüfbare Quellen und Belege; ARM-Build und echte Sensorlatenzen wurden hier
nicht gemessen. Deren Auswertung muss die verbleibenden Zeit-/Sichtprobleme
klären. Vor Kundenfreigabe sind weiterhin drei vollständige Originalmissionen
auf demselben Kandidaten und die realen Abnahmen erforderlich. Keine weitere
Zugangsfrage, kein Deployment oder automatischer Übergang zu einem anderen AP.

## 07.10.2026 – AP-06 Reviewkorrekturen in Umsetzung

Nutzer beauftragt ausdrücklich die Behebung der festgestellten Probleme. Basis `7934a28` im bestehenden AP-06-Branch, MASTERPLAN v1.3 und ursprüngliche A/B/C-/Cancel-/Gyro-HOLD-Abnahme unverändert. Ziel bleibt 3/3 am gleichen finalen Softwarestand. Kein Hardwarezugriff, Deployment, Push/Merge oder nächstes AP. Frühere Reparaturen und Negativnachweise bleiben erhalten; Rückfall nur der neuen eigenen Änderungen.

V37 und V38: jeweils **9/9 native Komponenten bestanden**. Diagnose B186 lokalisiert die Eingabeverzögerung; `7fabf80` reduziert den allgemeinen exakten Egress-Pfad auf identischen Daten von 186–192 auf 50–51 ms. V38: Zwölfpaketbuild, **2242 direkte / 2224 registrierte Tests grün**, null Skips. Regulärer B193 dennoch negativ: eine Ankunft, null Beobachtungen, abgelaufene gebundene Encoderprobe während der Beobachtung.

B194 belegt eine bereits vorliegende echte frische Encoderprobe trotz verworfener alter Bindung und anschließend einen zweiten Fehler: Restarbeitsbewertung bricht im noch nicht roh-frei beobachteten Startzentrum ab. `4497d0c` bindet höchstens einmal eine tatsächlich neuere, weiterhin TF-konsistente Messung mit vollständigem neuen Egress-Beweis. Unbeweisbare lokale Konnektivität hält Arbeit offen; globale Abschlussprüfung und Fahrfreigaben unverändert. Gegenfälle des alten Frischecodes 2 rot/6 grün; korrigierte Nachbarprüfung 93 grün, Fortschritts-/Frischeprüfung 86 grün. **Gesamtstatus weiterhin 0/3**, bis vollständige Missionen am gleichen finalen Kandidaten nachgewiesen sind.

`8e6cbbe` beseitigt weitere gemessene Auswahlkosten: V40-Zwölfpaketbuild, **2282 direkte / 2264 registrierte Tests**, 9/9 native Komponenten grün. Regulärer B207 erreicht drei Ankünfte/drei Beobachtungen und vollständigen Rundblick, bleibt nach 1,4018 m / 74,62 % Referenzboden an späterem Auswahlbudget negativ. Native-Sichtablehnung eines Fernvorschlags bleibt korrekt aktiv. Save/exakter Checkpoint und terminale Nullbefehle bestätigt.

`972ef6c` ersetzt den mehrfachen Python-Konnektivitätsdurchlauf durch identische Vier-Nachbar-Komponenten und bündelt unveränderte Zielprojektionen. Seitenabfragen prüfen die bestehenden Zeit-/Versuchsgrenzen vor teurer Geometrie. Im erhaltenen B207-Endzustand sinkt die Auswahl von Budgetüberschreitung auf 2,657 s bei unveränderter Historie; keine frühere Live-Freigabe daraus. **336 betroffene Tests grün**; V41-Gesamtprüfung siehe folgenden Absatz.

V41 ebenfalls vollständig grün (**2306 direkte / 2288 registrierte Tests**, 9/9 native Fälle), regulärer B214 jedoch erneut vor dem noch ausstehenden Rundblick am Auswahlbudget beendet. Exakte Eintrittsdiagnose B216 bewahrt die privaten Inventare und ursprüngliche Historie; unter Live-Last 5,100 s, im isolierten Cooldown-Zweig 0,528 s. Damit ist eine reine Endkarten-/Mikrobenchmark-Zusage unzureichend.

`60e23a8` priorisiert den bereits vollständig auf öffentlichen Karten bewiesenen, noch ausstehenden einmaligen Rundblick nach einer tatsächlichen Startbeobachtung, bevor ein weiteres Fahrziel gesucht wird. Anfang ohne Beobachtung, virtuelle Freiheit und unzulässige Drehfläche bleiben gesperrt; Scan-/Missionsdeadline und jede tatsächliche Drehprüfung unverändert. Originalgegenfall 1 rot/6 grün, korrigiert 168 betroffene Fälle grün. V42-Zwölfpaketbuild, **2313 direkte / 2295 registrierte Tests** und 9/9 native Fälle grün. B221 scheitert nach drei Ankünften/drei Beobachtungen an einer echten Encoderlücke; A222/C223 am initialen Auswahlbudget. Cancel224 bestanden; Gyro225 bereits vor Injektion wegen Quellkontinuität negativ. Weiterhin **0/3**.

`a2180ed` und `3c66cbe` beschleunigen ausschließlich die exakt gleiche Zellabstands-/Clippingarithmetik. Vollständiger NumPy-Referenzpfad erhalten; Kontaktpunkte mit Fläche null und ursprüngliche Flächensummation unverändert. V43: zwölf Pakete gebaut, **2337 direkte / 2319 registrierte Tests** grün. Abstandskorrektur allein löst den A-Gegenfall noch nicht (5,078 s); beide Korrekturen zusammen finden auf denselben A227-Eingaben in **4,195 s** den geprüften Startbeobachtungskandidaten. **75 gezielte Fälle grün**. V44 ebenfalls vollständig grün (**2360 direkte / 2342 registrierte Tests**, 9/9 native Fälle, Cancel233 und Gyro-HOLD234); A230/B231/C232 jedoch erneut am Auswahlbudget negativ. Eigener nativer Kernel neu gebaut/gehasht, externe Plugins und ursprüngliches Manifest unverändert.

`5612878` zieht den bereits vorhandenen vollständig geprüften kurzen privaten Startschritt vor Fernabfragen. Originaler A227-Gegenfall rot; korrigiert dasselbe Ziel/dieselbe Task-ID in **0,964 s**, Karten/Inventare/Fristen unverändert. Vier Gegenfälle erhalten Route, Sicht, Cooldown und Versuchskappen. **30 betroffene / 2365 direkte / 2347 registrierte Tests grün**, V45-Zwölfpaketbuild und 9/9 native Fälle bestanden.

**Aktuelles Endergebnis:** Originalmatrix A238/B239/C240 weiterhin **0/3**; Cancel241 und Gyro-HOLD242 bestanden. A startet nun rechtzeitig, scheitert nach 2,1 cm an der festen unbekannten Anfangsfläche bei kleiner realer Kurve. B sperrt neu unbekannte Fläche beim Referenzwechsel. C erreicht drei Ankünfte/Beobachtungen und 4,394 m, scheitert aber an echter 213-ms-Encoderlücke. Alle Actions terminal/vier Nullketten. C245 mit zur Vier-CPU-Quote passender Zuteilung ohne Drosselung, aber Encoder-/TF-Poseabweichung; kein Gesamtfix daraus.

`2e5e1fd` ergänzt unabhängig davon die vorhandene gestoppte, begrenzte Geometrie-Neuprüfung auch für Encoder-/TF-Abweichung: gleicher Task, unveränderte 2 cm/0,05 rad, Fristen und Versuche; permanente Abweichung/Quelllücke bleiben negativ. Das tatsächlich abgelehnte Eingangspaar wird protokolliert. Original-Elterngegenfälle 3 rot/9 grün, korrigiert 48 betroffene Tests grün. V46: Zwölfpaketbuild, **2371 direkte / 2353 registrierte Tests**, 9/9 native Komponenten grün. C248 nutzt die gestoppte Neuprüfung desselben Tasks nach 27,0 mm Poseabweichung, bleibt danach geometrisch gesperrt und endet regulär nach ursprünglichen 900 s: neun Versuche/ein Fehler, null Ankünfte/Beobachtungen, 0,29878 m. **Cancel249 und Gyro-HOLD250 bestanden**. Alle Kinder terminal/vier Nullketten; volle Trace-Hashes geprüft. Keine erneute identische A/B-Fehlstartserie. [Nachweis](evidence/ap06-missions-20261005/README_C246_C250.md).

**Konkreter Blocker und getrennte Weiterarbeit:** Der vollständige unveränderte Trackingnachweis am A227-Start benötigt 138 unbeobachtete Rohkartenzellen außerhalb des Anfangsinventars. Nominal gerade Bewegung reicht nicht. [Separates Beobachtungs-/Abdeckungspaket vorbereitet](AP06_STARTBEOBACHTUNG_BLOCKER.md) gemäß MASTERPLAN AP-03; keine Hardwareänderung und keine neue Serie identischer Fehlstarts. Unabhängig: gestoppte Encoder-/TF-Neuprüfung und echte Ablehnungsdiagnostik implementiert und V46-validiert; genaue Ursache des langen Base-Executors bei C240 weiterhin offen. Grenzen, Inventar und Originalmanifest bleiben unverändert. **AP-06 nicht abgeschlossen; keine 3/3- oder Deploymentfreigabe.** Nachweise: [B185–B193](evidence/ap06-missions-20261005/README_B185_B193.md), [B194–B196](evidence/ap06-missions-20261005/README_B194_B196.md), [B197–B207](evidence/ap06-missions-20261005/README_B197_B207.md), [B208–B214](evidence/ap06-missions-20261005/README_B208_B214.md), [B215–B225](evidence/ap06-missions-20261005/README_B215_B225.md), [A227–A235](evidence/ap06-missions-20261005/README_B227_B235.md), [A236–B242](evidence/ap06-missions-20261005/README_B236_B242.md).

## 06.10.2026 – AP-06 Lösungskonzept in Umsetzung, Gesamtmissionen offen

**Auftrag:** Nutzer beauftragt die Umsetzung des dokumentierten Lösungskonzepts mit Ziel 3/3 erfolgreichen Gesamtmissionen. Basis `b8189a9` plus identifizierter v19-Arbeitsstand, gleicher isolierter Branch `feature/ap06-closed-product-validation`. MASTERPLAN v1.3 und ursprüngliches Szenariomanifest unverändert. Keine Hardware oder Deployment.

**Belegte Reparaturen:** Die v19-Regression für reine Planalternativen ist geschlossen; der bestehende rote Test besteht wieder. Originale B70-Daten zeigen: erste Beobachtungsbaseline aufgelöst, nach der zweiten noch ein ursprünglicher unbekannter Punkt von neun, trotzdem Aufgabe als erledigt markiert. Der verbleibende kleine aktuelle Rand wird zusätzlich durch den normalen Größenfilter entfernt. Teilbeobachtung bleibt jetzt offen; der ursprüngliche zugelassene Task erhält seinen gemessenen kleinen Rand mit vorhandener ID/Versuchs-/Cooldownbindung. Nur für diese Restarbeit ergänzt die begrenzte öffentliche Suche Richtungen entlang des tatsächlichen Randes. Sonstige Größenfilter, Kontur, Quellen, Scope, Fristen und Fehlerlimits erhalten. Spätere vollständige frische Scope-Beobachtung kann alte Teilaufgaben im ursprünglichen Abschlussfenster auflösen, ohne zusätzliche Ankunfts-/Gewinn-/Beobachtungszähler.

**Kausalnachweise:** B70-Auswahl nach analytisch abgelaufenem originalem Cooldown auf exakt erhaltenen Daten: vorher nur ferner unbewiesener Vorschlag, nachher nützliche vollständig eigene geprüfte Folgeposition in 0,12 s, vorhandene Task-ID 4 und unveränderte Zähler. Gegenprobe mit früheren Kandidaten-/Runtime-Modulen rot am Verhaltensassert. Tatsächliche C++-Nav2-Abfrage für diese Folgeposition: Anfahrt, Stopp/Drehhülle und gesicherte Abfahrt positiv. Dies sind Komponentenbelege; keine Mission daraus als positiv gezählt. 14 neue Retained-/Beobachtungs-/Persistenzfälle grün, drei zusätzliche echte Elternentscheidungsfälle für Teilbeobachtung und spätere Scope-Auflösung grün. Ganze direkte Regression v20: **2.134 bestanden**, keine Fehler/Skips, 138,31 s. Zwölfpaketbuild 6,67 s bestanden; registrierte colcon-Prüfung: **2.116 Tests, null Fehler/Failures/Skips**. **9/9 native Bewegungs-/Sperrkomponenten bestanden**. Kandidat `17fba88`, 136 Installdateien bytegleich, 448 Dateien an Quellstand gebunden.

**Prüfstand:** Eigene inaktive Build-Caches lossless archiviert und alle regulären Dateihashes vor Entfernung geprüft; etwa 496 MB zusätzlicher Platz. Die Observer-Ereignisse werden künftig beim Schreiben vollständig verlustfrei komprimiert, mit Eingangsbytezahl/-SHA und separater Dekompressionsprüfung nach Ende. Vier Trace-/Kapazitätsfälle grün, einschließlich echter Startverweigerung vor Runtime bei fehlendem Speicher. Produktmindestreserve weiterhin 512 MiB. Vor jedem Lauf explizites Trace-/Nebenlog-/Temporärkarte-/Reservebudget; aktuell etwa 1,5 GiB frei. Verlustfrei archivierte Negativevidenz bleibt erhalten.

**Grenzen:** Weiterhin **0/3 Gesamtpositivmissionen**; regulärer B72-Gesamtlauf auf Kandidat `17fba88` negativ: 3 Ankünfte/2 Beobachtungen, 7 Versuche/1 Bewegungsfehler, 261 erreichbare Randzellen, 72,42 % Referenzfläche; natürliche Beendigung am ursprünglichen 5-s-Auswahlbudget. Keine Passage. Alle Kinder terminal und vier Nullbefehle, echtes Map-Save und exakt gebundener Checkpoint positiv. Verlustfreie Dekompression aller 196.019.618 Ereignisbytes geprüft (23.993.578 Bytes Gzip). B73 zeichnet begrenzt Originalentscheidungen auf und ist ausschließlich Diagnose. Historische v18/v19-Resultate und rote Zwischenprüfungen bleiben erhalten. Zielsystem-, physische und Apple-Abnahme getrennt offen.

**B73-Diagnose / B74-Korrektur:** B73 bleibt nach explizitem Analyse-Cancel negativ (4 Ankünfte/2 Beobachtungen). Originale dritte Sichtpunkte teils noch unbekannt, teils von kürzeren realen Strahlen verdeckt (2,05/2,09 m Reichweite gegenüber 2,32/2,34 m Punktdistanz). Vierte Sicht scheitert am originalen Supercover, kein erfundener Gewinn. Größere Punktunion, reine Erledigungs-Vorfilterentfernung, IDs-/Receipt-Varianten verbessern die Originalauswahl nicht; nichts davon übernommen. Kleiner aktueller Korridorrand liefert einen weiteren Vorschlag, dessen echter Native-Pfad negativ bleibt. Eine vor dem vierten Ziel berechnete Randtangentenposition bietet sieben statt einem endlichen First-hit-Punkt und echte Native-An-/Abfahrt mit Drehrefuge. Zu breite erste Integration wird durch den alten A51-Erschöpfungsfall abgelehnt; Original-V21/-V22-/Zwischenlogs erhalten. Finale Umsetzung verfeinert ausschließlich eine zuvor original zulässige Zielwahl im Rest desselben 0,5-s-Fensters, bindet beide Positionen lesend an dieselbe ID und verlangt höhere Potentialpunktzahl/niedrigere Originalkosten/öffentliche Drehreserve. **31 gezielte Tests grün**, einschließlich alter Erschöpfung, B70-Rest, B68-Goalchecker und vier neuer B73-/Lookup-Fälle. Finaler Softwarecommit `ea63493`: V23-Zwölfpaketbuild **6,60 s grün**, **2.138 direkte Tests grün** (144,06 s), **2.120 registrierte Tests grün**, jeweils ohne Fehler/Skips. **9/9 native Bewegungs-/Sperrfälle grün**; 136 installierte Produktdateien bytegleich, 449 ausführbare Quell-/Test-/Konfigurationsdateien gebunden. B75 regulär **negativ** am originalen 900-s-Gesamtbudget: 2 Ankünfte/2 Beobachtungen, 8 Versuche/null Bewegungsfehler, 228 erreichbare Grenzzellen, 72,10 % Boden, keine Passage. Kein Quellenfehler; tatsächliche Folgepfade `footprint_sweep_invalid`. Map-Save/exakter Checkpoint positiv, beide Kinder terminal/vier Befehlsströme null. Alle 769.062.555 Ereignisbytes lossless geprüft (98.546.057 Gzipbytes); noch keine Gesamtpositive.

**Neue Kausalreparatur B89:** B79/B80–B86 bleiben reine native Komponentenvergleiche, kein Plannerwechsel. Die gespeicherte aktuelle B76-Auswahl zeigt eine günstigere öffentliche Randtangente: 9 statt 4 endliche Potentialpunkte, Originalkosten ca. 1,55 statt 2,86, dieselbe Task-ID und ursprüngliche Limits. Die ursprüngliche Richtungsreihenfolge verbraucht ihr festes 0,5-s-Fenster zuvor an der nach hinten gerichteten Normalen. Original-Gegenprobe rot; repariert wird ausschließlich die Reihenfolge der vier vorhandenen Richtungen anhand der bereits gewichteten absoluten Lenkkosten. Native B88-Anfahrt, tatsächlicher Goalchecker-Stopp (0,14973 m), volle öffentliche Drehreserve und originale Abfahrt positiv. Zwei neue Regressionen und 46 gezielte bestehende Fälle grün; umfassender aktueller Build-/Testlauf noch laufend. [Originalnachweise und verworfene Vergleiche](evidence/ap06-missions-20261005/README_B80_B89.md). Keine Reserve, Frist, Nachbarregel oder letzte Native-Freigabe gelockert; kein zusätzlicher Bewegungsowner.

**Genau nächster Schritt:** B89 auf dem vollständigen geprüften Kandidaten binden und die ursprüngliche A/B/C-/Cancel-/Gyro-HOLD-Matrix erneut ausführen. Vorher Kapazität aus eigenen inaktiven und überprüfbar gesicherten Prüfcaches schaffen. Bei neuem Fehler erste kausale Ablehnung erhalten und im selben AP-06-Auftrag beheben. Noch 0/3, keine Zählung unterschiedlicher Kandidaten. Shutdown ausschließlich tatsächlicher verifizierter Jetson nach Abschluss, kein Cloud-Host-Shutdown.

### Lösungskonzept vom 06.10.2026 – von 0/3 zur vollständigen Softwareabnahme

Auf Nutzerwunsch erarbeitet; Konzeptstand, noch keine umgesetzte oder bestandene Gesamtreparatur. Basis ist der oben identifizierte v19-Arbeitsstand. MASTERPLAN v1.3, WE-M0/M3/M4/M5/M6 und bestehende Mission/BT/Explorer/Nav2/SLAM-Kette bleiben maßgeblich. Dieses Konzept konkretisiert den laufenden AP-06-Auftrag innerhalb dieses STATUS; es eröffnet keine zweite Roadmap.

**Gesicherte Befunde und offene Ursachen**

| Befund | Konsequenz für die Reparatur |
|---|---|
| v19: neue `valid_view`-Pflicht sperrt reine alternative Planvorschläge; bestehender Test rot, HEAD-Gegenprobe grün. | Eigenständige, bereits bewiesene Regression beheben. Sie entstand nach B68/B70 und erklärt deren ursprünglichen Stillstand nicht. |
| B68: zwei Ankünfte/Beobachtungen, 229 erreichbare Grenzzellen, erschöpfte Planvorschläge. B70: zwei Ankünfte/Beobachtungen, 226 Grenzzellen, zwölf zurückgestellte/als bedient behandelte Kandidaten. | Zwischen lokalem Fortschritt, erledigter Aufgabe, Cooldown und ausgeschöpften Versuchen unterscheiden. Welche konkrete Sperre eine sichere Folgebeobachtung verhindert, am ursprünglichen Entscheidungszeitpunkt beweisen. |
| B70: geplante Sicht auf 13 bzw. 9 Punkte, gemessene Gewinne 12 bzw. 2 Zellen; beide erfassten Abfahrtsprüfungen positiv. | Teilbeobachtung ist ein begründeter Reparaturansatz. Die Zähldifferenz allein beweist aber keine unerledigte Aufgabe: Originalpunkte gegen die frische Karte und tatsächliche Sicht prüfen. |
| Frühere native Pfade wurden wegen `footprint_sweep_invalid` abgelehnt; auf späteren Endkarten sind einzelne lokale Wege gültig. | Endkarten nicht rückwirkend als Freigabe der früheren Fahrt verwenden. Tatsächlichen Pfad mit dessen damaligen Raster-/Pose-/Controllerdaten prüfen. |
| B70-Save scheitert an der 512-MiB-Mindestreserve. Ereignisdatei allein 450.301.562 Bytes vor Kompression. | Eigenständige Kapazitätsvorsorge vor jedem Gesamtlauf; Speicherbereinigung repariert keine Auswahlentscheidung. |

**1. Reproduzierbare Entscheidungsnachweise herstellen**

Den vorhandenen v19-Fehlertest erhalten und zuerst die unbeabsichtigte Kopplung von `proposal_rejected` an den neuen Teilbeobachtungsnachweis lösen. Die Vorprüfung eines anderen rein lesenden Planvorschlags muss nach ursprünglichem Cooldown und innerhalb derselben Versuchslimits wieder möglich sein. Vollständige Sicht- und Bewegungsfreigabe erfolgen weiterhin an den dafür vorgesehenen späteren Prüfstellen. Alle Aufrufer von `MetricTaskPolicy.eligible` prüfen, insbesondere Vorprüfungen vor der Sichtberechnung; fehlende Sichtpunkte dürfen weder eine verfrühte Bewegung erlauben noch die benötigte Kandidatenberechnung unbeabsichtigt verhindern.

Für B68/B70 einen zeitlich passenden Komponentenfall aus Rohkarte, Costmap, Pose/TF-Bezug, Scope, ursprünglicher Beobachtungsbaseline, endlichem Scan, Kandidat und vollständiger damaliger Aufgabenhistorie erstellen. Historisch erschöpfte Aufgaben bleiben erschöpft; eine Reparatur wird an einem Zustand vor dem Fehlentscheid und dessen nachvollziehbarer Folge geprüft. Keine bereinigte Historie oder nachträglich günstigere Endkarte als Kausalnachweis verwenden.

Falls vorhandene Aufzeichnungen die erste Ablehnung nicht enthalten, genau diese Stelle begrenzt erfassen: Auswahlstufe, Task-ID, Sperrgrund, Versuche/Cooldown, Originalsichtpunkte und bei Geometrieablehnung tatsächlicher Native-Pfad samt erstem verletztem Kontur-/Rasterkriterium. Bestehende Diagnostik erweitern, keine neue Steuerinstanz. Erfassung bleibt beschränkt und zählt zur ursprünglichen Laufzeit; instrumentierte Läufe bleiben Diagnose. Volles Profiling während einer Qualifikationsmission entfällt.

Ergebnis dieser Stufe: ein roter/verhaltensbezogener Gegenfall je bewiesener Ursache. Wenn alle ursprünglichen Beobachtungspunkte bereits aufgelöst waren, wird die Teilbeobachtungshypothese für diesen Fall verworfen; dann führt die tatsächlich aufgezeichnete Kandidaten-/Geometriesperre die Reparatur.

**2. Fortschritt, Restaufgabe und begrenzte Wiederbeobachtung schließen**

`metric_progress.py`, `metric_frontier.py` und deren Einbindung in `metric_frontier_runtime.py` gemeinsam bearbeiten. Die bloße Ankunft bleibt ohne Beobachtungsreceipt. Tatsächlich neu beobachtete Zellen zählen als Fortschritt. Bleibt belegte relevante Restarbeit derselben Aufgabe, bleibt sie als `partially_observed` offen, ohne daraus einen Fahrfehler zu machen. Die ursprüngliche Baseline bleibt während des Versuchs einschließlich HOLD/Retry unverändert.

Eine weitere Beobachtung verlangt nach unverändertem Cooldown eine tatsächlich nützliche aktuelle endliche Sicht auf die Restarbeit und eine zulässige Beobachtungsposition. Die Prüfung verwendet den prognostizierten tatsächlichen Stopp und anschließend die wirkliche Ankunft. Reine Planablehnung, Teilbeobachtung und echter Fahrfehler behalten unterschiedliche Wiederholungsbedingungen. Räumliche Aufgabenbindung, Nachbarschaftsschutz, höchstens drei Versuche je Aufgabe, ursprüngliche Fehlerlimits und Gesamtbudget bleiben wirksam. Eine neue ID, ein neuer Kartenstempel oder eine kleine Zielverschiebung setzen nichts zurück.

Offene Teilaufgaben müssen auch durch spätere gültige Beobachtungen anderer Ziele auflösbar bleiben. Umgekehrt darf eine sichtbare Restfrontier nicht durch ein pauschales `completed` verschwinden. Dazu die kleine ursprüngliche lokale Restverpflichtung nachvollziehbar mit aktueller kartengebundener Evidenz abgleichen. Eine bloß aktuell verdeckte Sicht ist kein Erledigungsnachweis. Nachweislich durch beobachtete Wände abgetrennte unbekannte Bereiche dürfen gemäß Masterplan den metrischen Abschluss nicht dauerhaft sperren. Diese Auflösung erhöht keinen Beobachtungszähler ohne neuen echten Gewinn.

Aufgabenstatus und gegebenenfalls benötigte begrenzte Restdaten im vorhandenen Checkpoint erhalten; keine zweite Persistenz. Zusätzliche Felder nur bei nachgewiesenem Bedarf, mit explizitem Schemakontrakt und konservativer Behandlung älterer Daten. Save/Load und Wiederaufnahme erhalten IDs, Versuche, Cooldowns und abgelaufene Missionszeit. Laden erteilt keine Fahrtfreigabe. Alte gültige Sicherungen bleiben erhalten.

Pflichtregressionen: Teilgewinn mit verbleibender zugänglicher Restarbeit; vollständige lokale Auflösung; neue Wand versus bloße Sichtverdeckung; spätere Auflösung durch anderes Ziel; kein Gewinn bei alter/fremder Karte, Rasterinkompatibilität oder maskiertem Scan; alternative reine Planung; verweigerte Wiederholung bei erschöpfter Historie; HOLD/Cancel während Beobachtung; unveränderter Zustand nach Persistenz-Rundlauf. Die neue Logik wird nur übernommen, wenn der ursprüngliche Fehlentscheid verschwindet und diese Gegenfälle bestehen.

**3. Eine geometrisch zulässige Folge von Beobachtungszielen nachweisen**

Mit derselben Historie und frischen Produktdaten prüfen, ob die Auswahl eine nützliche Folgeposition vor dem Eingang, die vollständige Durchfahrt und die Weiterarbeit im zweiten Raum erzeugen kann. Vorhandene begrenzte lokale Kandidatensuche und echten NavFn/RPP weiterverwenden. Anfahrt, Sicht am tatsächlichen Stopppunkt und gesicherte Abfahrt müssen zusammenpassen. Bekannte Originalkollisionen an Türpfosten/Hindernis bleiben abgelehnt; Radius, Padding, Toleranzen und Lookahead werden nicht als Ersatz für eine funktionierende Zielwahl verändert.

Falls der nächste sichere Kandidat noch fehlt: zuerst den konkreten Verlust in Kandidatenerzeugung, Historienfilter oder Native-Validierung lokalisieren und nur diese Stelle ändern. Keine fest codierten Weltkoordinaten, manuellen Zwischenziele oder neuen Navigatoren. Rein lesende Native-Planabfragen bleiben im bestehenden Budget; Fehlversuche behalten ihre ursprüngliche Zählung. Ein positiver Weg auf eingefrorenen Daten ist nur ein Komponentenbeleg. Erst neue Bewegung mit daraus entstehenden Sensordaten kann eine Beobachtungsfolge bestätigen.

Geometrie-/Native-Regressionen umfassen die bisherigen neun Bewegungsfälle und den neuen konkreten Folgefehler. Zusätzlich Auswahl einschließlich Sichtberechnung innerhalb der ursprünglichen 5 s, lokaler Helper innerhalb 0,5 s, unveränderte Quellenfrische unter Last. Bei identischer Eingabe ohne neue Evidenz keine Serie gleicher fehlgeschlagener Missionsläufe.

**4. Prüfstand und finalen Kandidaten festlegen**

Vor jedem Gesamtlauf den verfügbaren Speicher gegen ein aus bisherigen unkomprimierten Datenraten auf die vollen 900 s abgeleitetes Laufbudget prüfen: Ereignisse, weitere Logs, Karte/Checkpoint einschließlich temporärer Schreibdateien, 512 MiB Mindestreserve und zusätzlicher Sicherheitsabstand. Die zuletzt freien 1,2 GiB sind keine zugesicherte Laufkapazität. Beendete eigene Nachweise verlustfrei archivieren und per Hash prüfen; nur sicher zugeordnete entbehrliche eigene Build-/Temporärdaten entfernen. Reicht der Platz nicht, zuerst Ausführungsvolumen erweitern oder verifiziert archivieren. Die Mindestreserve bleibt unverändert.

Ein finaler Quellstand, ein reproduzierbarer Build und eindeutig zugeordnete Installpräfixe. Zwölfpaketbuild, vollständige direkte Regression, registrierte colcon-Tests und betroffene native Prüfungen bestehen ohne neue Fehler. Neue Tests müssen auch in der tatsächlichen CI-Auswahl stehen; insbesondere die bisher ungetrackten B68-Komponentenfälle sachlich einordnen und bei Übernahme registrieren. Produkt-/Konfigurations-/Pluginhashes gegen den finalen Stand prüfen. Während einer Gesamtmission keine konkurrierenden Builds, Regressionen, Profiler oder Archivierungsläufe.

**5. Gemeinsame Endabnahme ausführen**

Die unveränderten Manifestfälle auf diesem identischen Kandidaten ausführen. B beginnt als gezielte Gesamtprobe; ein regulärer bestandener B-Lauf kann bereits zur finalen Matrix zählen, wenn Code, Parameter, Manifest und Prüfmodus danach unverändert bleiben. Danach A, C, Cancel und Gyro-HOLD. Ändert sich Produktcode oder eine wirksame Konfiguration, sind vorherige Positivläufe für den neuen Stand erneut zu bestätigen. Keine Vermischung mehrerer Kandidaten zu 3/3.

| Fall | Unveränderter Start `(x, y, yaw)` | Nachweis |
|---|---|---|
| A – `door68_start_a` | `(-1,9; -0,45; 0)` | Vollständige autonome Mission bei 68-cm-Türen |
| B – `door68_start_b` | `(-2,1; 0,45; 0)` | Vollständige autonome Mission aus bisher blockierter Startlage |
| C – `door80_start_c` | `(-1,6; 0; 0)` | Vollständige autonome Mission bei 80-cm-Türen |
| Cancel / Gyro-HOLD | jeweils `(-1,9; -0,45; 0)`, 80 cm | Originale Injektionen und Stoppkriterien; HOLD-Stopp allein belegt keine ACK-/Resume-Abnahme |

Ein Positivlauf verlangt echten Erfolg von Mission-Manager und Explorer, mindestens drei autonome Ankünfte mit qualifizierten Beobachtungen, vollständige Passage beider Türen einschließlich Heck, Weitererkundung im zweiten Raum und beobachtungsbedingtes Kartenwachstum. Mindestens 95 % der Referenzbodenfläche, höchstens 0,1 m Wandfehler und keine Kollision; Referenzwissen ausschließlich im unabhängigen Prüfer. Vor Erfolg keine relevante erreichbare Restaufgabe oder ungeklärte zugängliche Verbindung im ursprünglichen gültigen Abschlussfenster. Ein Nav-Kind gleichzeitig, eindeutige SLAM-/EKF-TF-Besitzer, am Ende keine aktiven Actions und alle vier Befehlsstufen null. Karte und exakter Aufgabencheckpoint müssen konsistent gespeichert sein.

Startbudget 60 s, Mission 900 s, Aufgabe 150 s, Cancel höchstens 3 s und Halt höchstens 1 s bleiben unverändert. Für jedes fehlgeschlagene Kriterium Originalbeleg und ersten kausalen Fehler sichern. Diagnose-Cancel, Teilkarte, bloßer Kartenzuwachs oder erschöpftes Budget zählen nie als Erfolg. Erst die gemeinsam bestandene Matrix belegt den Softwareteil; Zielsystem, physische Abnahme und native Apple-Prüfung bleiben getrennte Nachweise.

**Rückfall und Lieferung:** Kleine auf eine gemessene Ursache begrenzte Änderungen mit passenden Tests; nur eigene Änderungen gezielt zurücknehmen. Bereits geprüfte Referenz-/HWT-/NavFn-Korrekturen erhalten. Lieferung umfasst finale SHA und Installhashes, Build-/Testprotokolle, fünf Originalresultate und Kriterienmatrix. Es wird kein Datum oder sicherer Erfolg versprochen, solange die neuen Gegenfälle und Gesamtläufe fehlen.

## Erhaltener Zwischenstand 05.10.2026 – AP-06 Gesamtmissionsreparatur

**Aktueller Auftrag:** Nutzer verlangt die Behebung der Ursachen für 0/3 Gesamtmissionen. Basis `1b93694`, gleicher isolierter AP-06-Branch/Worktree; MASTERPLAN v1.3 und die fünf vollständigen Produktfälle unverändert. Voriger Auftrag bytegleich archiviert. Keine Hardwarefahrt, Deployment oder weitere AP-Arbeit.

**Gemessene Ursachen / laufende Reparatur:** millimeterverschiebende Karto-Rastergrenzen; Explorer-Worker durch wartende Geometriecallbacks belegt; tausende skalare Konturprüfungen überschreiten Kandidatenbudget; Lokalisierungskorrektur fälschlich als neue Rasterbeobachtung bzw. Verlust des ersten Körpers behandelt; Goalchecker-Akzeptanzscheibe mit erreichbarer RPP-Stoppbewegung verwechselt; exakter Karten-/Statusjoin nach Kindankunft trifft einen asynchronen Zwischenstand. Native rote Producer-/DDS-Gegenproben und synthetische Originalraster erhalten. Guards/Fristen, Ganzkontur, echte Source-Zeit und Abnahmen bleiben erhalten; erster nativer zusätzlicher Stopp in einer 68-cm-Passage positiv, gezielte Komponentenfälle grün. Volle Regression und endgültige Gesamtfälle laufen noch; kein neuer Gesamtpositivabschluss behauptet.

**Genau nächster Schritt innerhalb dieses Auftrags:** verbleibende nachgewiesene Gesamtfehler beheben, finalen Kandidaten mit Build/Regressionen und allen fünf unveränderten Gesamtfällen belegen; Ziel drei vollständige autonome Positivmissionen. Reale AP-06-/Apple-Abnahme weiterhin separat offen. Shutdown nur tatsächlicher Jetson bei nachgewiesenem Zugang/Identität, kein Cloud-Host-Shutdown.

**Überprüfbarer laufender Zwischenstand:** [Originalresultate und Rot-/Grün-Belege](evidence/ap06-missions-20261005/README.md). Kandidat **`16cbe5c`**: echte Native-Abfahrtsprüfung bei nominaler und ±0,05-rad-Prognoseorientierung, frühe gültige Planungswahl im bestehenden 5-s-Budget, begrenzte neue Zielgeometrie nach reiner Vorschlagsablehnung, echte Native-Umwegrückwege statt Direkt-Rückfilter, vollständig frische Wiederprüfung nach bestätigtem Halt bei spezifischem gebundenem Bearbeitungsablauf. Zusätzlich finite Sensorberechnung eigener Prozess: ein realer Isolationstest misst sonst 175 ms Sensorexecutor-CPU bei kaum ausgeführten Rad-/Gyrothreads. Welt/Strahlen/Takte/Guards/Abnahmen unverändert; keine neuen Sensorframes/Heartbeats aus altem Pflanzensnapshot, ursprüngliche Erfassungsstempel erhalten. Neuerer Zwölfpaketbuild und **1.945 direkte / 1.933 colcon-Tests grün**, keine Fehler/Skips; alle neun nativen Bewegungskomponenten ebenfalls geprüft. C38/C40 drei bzw. vier Ankünfte bleiben negative Gesamtstände; C39 Quellenpause, C41 gebundener Bearbeitungsablauf erhalten. C42 ebenfalls negativ: drei Ankünfte/Beobachtungen, 90,164 % Referenzboden, Quellen stabil; implizite Native-Pfade starten fälschlich bei (0,0), Controller meldet veraltetes map→odom. Isolierte konstante TF-Gegenprobe beginnt korrekt an der gemessenen Pose; Ursache des Gesamt-TF-Problems noch nicht bewiesen. Vollständig konsistenter älterer ROS-Prüfstand frisch gebaut (47 s), dieselben 1.945/1.933 Tests grün. Kandidat `ee7e21b` ergänzt passive Plan-/TF-Zeitstempel; C43 beginnt seine dynamischen Folgepfade korrekt, bleibt aber nach drei Ankünften/Beobachtungen mit tatsächlichem NavFn-ABORT negativ. Kandidat `4def089` hält nach terminalem rein lesendem ABORT begrenzte Alternativen offen; CANCELED/RPC-Fehler und beobachtete Schutzursachen bleiben hart. Drei rote Originalfälle, 25 betroffene Eltern-/Join-/Frischefälle grün. C44 erreicht sechs Ankünfte/fünf Beobachtungen und 96,850 % Boden, bleibt wegen 5-s-Auswahlbudget negativ. Originale erhalten. Kandidat `0f0fa42`: gleiche lokalen Inhaltsdigests innerhalb exakt gebundener Suchrunde, identische Halbzell-Strahlen nur bis zum ersten Stop berechnet; 124 betroffene Fälle grün, tatsächliche spätere C44-Suchrunde mit Profiler 4,776 s. C45 endet vor Missionsstart negativ: tatsächliche Radkontinuitätslücke 359,8 ms, gleichzeitige Quellen-Executorpause rund 330 ms bei 6–9 ms Prozess-CPU. Keine Fristlockerung oder Quellenentriegelung. C46 ist ein separat markierter Diagnoseversuch ohne Abnahmenachweis; keine lange Publisher-Blockade gemessen, Cleanup manuell beendet. A47 mit 177 zugänglichen Rohgrenzzellen ohne Aufgabe gestoppt (expliziter Analyse-Cancel, kein Positivnachweis). Kandidat **1de7c9b** findet zusätzlich nützliche, vollständig geprüfte Positionen auf der Roboterseite der Frontier im bestehenden lokalen Suchraum. Tatsächliche native Hin-/Abfahrtsprobe positiv; 200 betroffene Regressionen und sieben direkte Zusatzfälle grün. Gleiche Kontur/Scope/Quellen/Fristen/Trylimits; optionale bessere Geometriesuche maximal 0,5 s innerhalb der ursprünglichen 5 s. A48 bestätigt zwei Ankünfte/Beobachtungen, bleibt vor der Passage ohne Ziel. Seine erledigten entfernten Beobachtungsflächen sperren die Position für eine andere aktuelle unbekannte Grenze. Diagnose-Save/Analyse-Cancel separat markiert; anschließender Endsaveschutz lehnt den zu frühen zweiten Save ab, kein Map-Manager-Produktdefekt. Kandidat **b85a376** erlaubt nur tatsächlich endliche unbekannte Sichtpunkte außerhalb der alten Beobachtungsfläche mit zusätzlicher Wiederbesuchsmarge; Potential beendet keine Aufgabe, Zähler/Cooldown/Fristen/Alias-Gegenfälle bleiben erhalten. 213 betroffene Regressionen grün. A49 bleibt negativ: zwei Ankünfte/Beobachtungen, 62,446 % Boden, kein Heckdurchgang; tatsächlicher HWT-Terminalfehler und 192,199 ms Gyrothread-CPU, genaue Ursache noch unbewiesen. **c90b2d7** nutzt den sicheren Rundblick vor ausschließlich unbewiesenen Planungsanfragen (162 betroffene Tests grün). **95e82db** spart identische statische Modellgeometrie bei exakt unveränderter Pose ohne Geschwindigkeits-/Zähler-/Schutzänderung; Rot/Grün und 15 Modell-/Isolations-/Lebenszyklustests belegt. A50 endet ohne Quellenpause negativ (zwei Ankünfte/Beobachtungen, 62,150 % Boden); frische Kontur sperrt Folgeanfahrt, Karten-/Statusjoin verbraucht optionalen Scan. **4f500d0** erhält gemessenen Restwinkel desselben Scans nach bestätigtem Halt und frischem exaktem Paar innerhalb ursprünglicher 150 s; drei rote Gegenfälle/257 betroffene Tests grün. A51 diagnostisch bestätigt abgebrochen, eine Ankunft/Beobachtung, 65,278 % Boden, kein Durchgang; ursprüngliche erschöpfte Historie bleibt gesperrt. **7778771** prüft die bestehende sichere lokale Beobachtungsalternative unabhängig von einer abgelehnten normalen Anfahrposition; zwei rote Auswahlfälle, 130 betroffene/vier Native-Pfadregressionen grün. A52 diagnostisch abgebrochen nach erster Beobachtung, keine Passage; begrenzter Helper findet existierende sichere Position wegen Sichtarbeitsaufwand nicht. **df0c7c0** prüft gleiche Route vor endlichen Sichtstrahlen, owning Suche 0,358 s; zwei rote Gegenfälle/134 betroffene Tests sowie native Hin-/Abfahrtsprobe grün. A53 diagnostisch bestätigt abgebrochen: zwei Ankünfte/Beobachtungen, 73,268 % Boden, kein Heckdurchgang; voller gemessener Scan 6,300 rad mit Join-Wiederprüfung erfolgreich, danach erschöpfte Vorschläge ohne Folgeziel. Neue begrenzte öffentliche Beobachtungswahl findet im unveränderten vollständigen A53-Verlauf ein anderes zulässiges Ziel: finite unbekannte Sichtpunkte, ganzer Eigenweg und native Hin-/Abfahrt positiv. Originalaufgaben bleiben erschöpft; kein Gesamtpositiv daraus. A54 endet vor Diagnose-Cancel negativ am ursprünglichen 5-s-Auswahlbudget: zwei Ankünfte/Beobachtungen, 72,171 % Boden, kein Heckdurchgang. Öffentliche kurze Auswahl jetzt vor unbewiesener ferner Arbeit; erledigte identifizierte Aufgaben ausgeschlossen. Separat gleiche echte Ankunft nach SUCCESS außerhalb 15 cm innerhalb originaler Task-/Try-/Gesamtlimits erneut prüfbar, kein Receipt für den Fehlstand. Kandidaten `d7a4c91` / `f61f209`, inkrementeller Explorerbuild und 261 betroffene Regressionen grün. A55 diagnostisch bestätigt abgebrochen, zwei Ankünfte/Beobachtungen, 72,256 % Boden, kein Durchgang. `9130ee7` trennt öffentliche Wege vom Ablauf privater Referenz, drei rote Gegenfälle/271 betroffene Tests grün. B56 regulär negativ nach einer Beobachtung am 5-s-Auswahlbudget; tatsächlicher Status bestätigt private_epoch_expired=False bei valid=False/projected=0. Weitere begrenzte Korrektur schließt die spezielle erste Forward-Suche bei ungültigem privatem Bestand aus. **Weiterhin 0/3 vollständige Gesamtpositivnachweise; Reparatur läuft.**

## Erhaltener Stand 05.10.2026 – AP-06 Referenzbindung software_geprüft; gemeinsame Gesamtprüfung weiter blockiert

**Aktueller Auftrag:** Nutzer „repariere die Referenzbindung und prüfe mit denselben Szenarien erneut“; Basis `4351b8bb2018aa959aa84d6d6e8aa03621913e41`, unveränderter AP-06-Branch/Worktree. Reparaturen `e54c954` und **`3f66d73`**; MASTERPLAN v1.3 bytegleich. [Auftrag vor Fortsetzung archiviert](archive/20261005-ap06-reference/README.md). [Neue vollständige Originalnachweise](evidence/ap06-reference-20261005/README.md); vorige AP-06-Negativläufe bleiben erhalten. Kein Push/Merge, Deployment, Realversuch oder automatischer weiterer AP.

**Reparatur:** Erstes Raster/Polygon und monotone Abfahrtsflächen/-abstände bleiben in der ersten Odometriefläche fest. Pose und `map→odom` stammen vom selben tatsächlichen gemeinsamen TF-Zeitpunkt; jeder Input erhält diesen Bezug selbst. Kompatibles Wachstum/Korrektur löst frische Projektion und vollständige aktuelle Konturprüfung auf Rohkarte/Costmap sowie ursprünglichen monotonen Egress-Beweis aus, keine erneute Anfangserfassung. Nur vollständig vom erhaltenen Bestand gedeckte aktuelle unbekannte Zellen sind privat zulässig. Beobachtete Teilfläche lässt konservativ die ganze alte Zelle entfallen; keine Wiederbetretung, neue Unknown-/Obstaclefreigabe, Schema-/Kontext-/Auflösungs-/Fristlockerung oder Budgetreset. Geometriecache enthält keine Gesundheit/Bewegungsfreigabe. Quellenalter wird nach der gesamten Projektion erneut geprüft; ungebundener AP-02-Fallback bleibt strikt invalidierend. [Bewegungs-/Referenzvertrag](BEWEGUNGSVERTRAG.md).

**Softwareprüfung abgeschlossen:** sechsmal rot am echten bisherigen Produkt; **16 zusätzliche Fälle**, darunter echte TF2-Zeitkorrelation, gesicherte synthetische C-Startkarte mit rigidem Raster-/Referenzwechsel, echte Rückkehr, subzellige ungeklärte Außenfläche, Wachstum, Quellenverlust und Bearbeitungsalter. **1.860 direkte Tests / 1.852 colcon-Tests grün**, 0 Fehler/Skipped; Prüfmengen überlappen. Echter isolierter inkrementeller **Zwölfpaketbuild 6,65 s**, **136** installierte Produktdateien bytegleich auf beiden Prüfplattformen, **466** ausführbare Quell-/Test-/Konfigurationsdateien bytegleich zum Softwarecommit. Native Gesamtläufe auf Ubuntu 22.04/Humble/Python 3.10/rclpy 3.3.17; volle Komponentenprüfung 3.3.22. CI-Auswahl ergänzt, Remote-CI nicht ausgeführt. Kein ARM-Zielbuild behauptet.

**Dieselben Manifestfälle erneut; Positivmissionen 0/3:** A/B/C fahren autonom **19,560 / 18,230 / 17,594 cm** statt zuvor 5–6 cm; keine Zielankunft/Beobachtungsaufgabe/ganze Passage. Im neuen Ereignisarchiv tritt `start_egress_reference_expired` nullmal auf. A/B terminal `post_child_state_or_standstill_unconfirmed`, C `hwt_terminal`. Konkrete Quellengegenfälle im Explorer: A Radprobe 2,539 s alt; B Roh-/Yawprobe 2,753 s und Radprobe 2,788 s alt; C Radprobe 298,965 ms, Raw-/Yawstatus 2,733/2,443 s alt. Notwendige Frische bleibt unverändert, kein Sensor-/Kabel-/Schedulinggrund daraus erfunden. Parallel meldet das echte Fahrtor beim ersten Quellenfehler in A/B/C weiterhin HEALTHY. Zusätzlich entziehen subzellige aktuelle Raster konservativ volle Anfangszell-Deckung (`start_egress_new_unknown_or_obstacle`); eine gültige Referenz ist kein Freiraumnachweis. Die rigiden positiven Komponentenfälle beweisen keine erfolgreiche nichtganzzahlige Rasterabfahrt oder Gesamtmission. Rohkarten wachsen/55,032–58,054 % Referenzboden beobachtet; das ist kein Abschluss.

**Schutzfälle:** Cancel terminal 0,602 s, gemessener Halt 0,301 s ab Injektion; Gyro-HOLD Halt 0,268 s nach HOLD / 0,594 s ab Injektion. Beides innerhalb ursprünglicher 3-/1-s-Grenzen; echte 450-ms-Transportlücke, kein HOLD/ACK-/Fortsetzungsnachweis. Im Cancel-Fenster tritt auch ein eigener Radfrischefehler auf; kein isolierter Kausalnachweis ausschließlich der Cancellation. Alle fünf Läufe höchstens ein echtes Nav-/Explorerkind, eindeutig allein SLAM/EKF als TF-Besitzer, terminal keine aktiven Handles und alle vier Befehlsstufen null; unabhängiger gepaddeter Körper kollisionsfrei. Alle fünf echten Rohkartensaves erfolgreich, aktueller exakter Checkpoint jeweils unavailable; kein gesichertes Resume-Paar behauptet. Frühere vier passive Paare bleiben historische Teilnachweise.

**Abschluss/Zielsystem:** Eigene native ROS-Kinder beendet; nur Container-Init/Idle vor geordnetem Containerstopp. Nutzer-Shutdown ausdrücklich autorisiert und ältere Sperre im aktuellen Auftrag ersetzt. Tatsächliches Befehlsbackend weiterhin x86_64/Cloud, kein Jetson-Releasepfad oder `/home/p/roboter_ws`; letzter neuer App-Terminal-Leseversuch ohne Antwort beendet. Kein technisch verifizierter lokaler Jetson-Ausführungskanal, deshalb **Jetson nicht heruntergefahren** und ROBOT_TRANSFER unverändert. Zielsystem-/Real-/native Apple-Abnahme weiterhin offen; negative Gesamtfälle sperren Realfahrt unabhängig vom Zugang.

**Genau nächster Schritt bleibt AP-06:** Ursachen der Quellen-Verbrauchslücken während der frischen Geometrie-/Referenzauswertung messen und im vorhandenen Explorer begrenzt beheben; die nichtganzzahligen Raster-/Egress-Gegenfälle und dieselben fünf Manifestläufe dabei erhalten. Erst drei positive ganze Missionen erlauben den bestehenden technisch bedingten LAB-1-Zielvorlauf. Keine Fristen-/Kontur-/Unknown-Lockerung als Ersatz. Rückfall: nur `3f66d73`/`e54c954` gezielt revertieren/isoliertes Overlay abwählen; Originalcheckouts/AP-01–05/Main und vorige Nachweise erhalten.

## Erhaltener Zwischenstand 04.10.2026 – MASTERPLAN v1.3 / AP-06 software_korrekturen_geprüft; Gesamt-/Realabnahme blockiert

**AP-06 ist nicht vollständig abgenommen.** Nutzer „gut dann mache ap-6 fertig“; Basis `6a4a7df51c3ed152edb82ffa8b7dce5f1020f8e4`, Branch `feature/ap06-closed-product-validation`, Worktree `/workspace/Roboter_ws-ap06`. Geprüfter Software-/Prüfstandcommit **`ecb2586`**; vollständige Nachweise/Dokumentation anschließend. [AP-05-Auftrag bytegleich archiviert](archive/20261003-ap05/README.md). MASTERPLAN v1.3 bytegleich. AP-01–05 und ursprüngliche Arbeitskopie erhalten; kein Push/Merge, dauerhafter Install-/Autostartwechsel oder Rechner-Shutdown.

**Konkrete Codekorrekturen:** aktuelle ROS-Zeit für SLAM-/Körper-TF statt zukünftigem Latest-TF; identische stationäre Egress-Prüfungen nur je Kandidatenpass mit vollständigem Eingabeschlüssel memoisiert. Endpoint-only prüft das wirkliche Ziel statt nochmals den unbekannten Start; Anfahrt/Ankunft getrennt, Vororientierung und Proof am tatsächlichen interpolierten 0,4-m-RPP-Carrot. Beobachteter Parent-Abbruchgrund beim Planen bleibt erhalten, auch nach Quellenheilung. Begrenzte VL53-Räumendpunkte markieren keine Hindernisse mehr, echte separate Messwolken bleiben unverändert aktiv: nativer Rot/Grün-Fall 452→0 falsche Zellen, nahe Wand weiterhin 394 markierte Zellen. Bestehender Startadapter sucht zusätzlich die erste vollständig sichere nahe Beobachtungsposition mit echter Frontiersicht innerhalb des vorhandenen Suchradius/5-s-Budgets. Keine feste Wegpunktliste, kein Whitening, keine gelockerte Kontur-/Quellen-/Fristgrenze oder zweite Navigation. Mission-/VL53-/Safety-Pytestregistrierung und explizite DDS-Testbarriere korrigiert.

**Geschlossener tatsächlicher Gesamtpfad:** vorhandener Mission-Manager → nativer C++-BT → Explorer → echtes NavigateToPose/NavFn/RPP → Fahrtor → Velocity Smoother → Collision Monitor → Bewegungsmodell; nativer EKF allein `odom→base_link`, gepatchter SLAM allein `map→odom`, originale Scan-Normalisierung und Safety-Monitor. Welt liefert nur endliche verdeckende Sensor-/Rohregistermodelle und Schalteranforderung; keine Wahrheitskarte/-TF oder manuellen Nav-Ziele im Produkt. Originalstatus `synthetic:false` bedeutet auf diesem ausdrücklich isolierten Modell keine Hardwarequalifikation. Vorab festgelegte zwei Räume/Verbindung/68-/80-cm-Türen/Umweg/blockierte Alternative und drei Startposen erhalten; ursprüngliches 720-Profil, separat vorab deklariertes 2160-Profil und vollständiges Wahrnehmungsprofil samt negativen Zwischenständen erhalten.

**Endgültige vollständige Positivfälle 0/3:** A/B/C fahren autonom **5,748 / 5,647 / 5,180 cm**, dann `start_egress_reference_expired`; jeweils echte Nav2-Cancellation und Stillstand, terminal `blocked_help_required` / `completion_raw_pose_not_observed_free`. **Null Zielankünfte, null bestätigte Beobachtungsaufgaben**, keine ganze Türpassage/Heckfreigabe/Weitererkundung. Tatsächliche Referenzfläche 54,877 / 56,859 / 57,437 %, max. Wandfehler jeweils <2,5 cm; Kartenwachstum allein kein Abschluss. In C verschiebt die tatsächliche SLAM-Aktualisierung den Rasterursprung um −1,985 / −0,066 mm; feste Egress-/Körperreferenz verfällt. Dieser Schutz wurde nicht durch stilles Re-Ankern oder neue Freiraumannahme umgangen. Das ist das erste offene Gesamtsoftwarekriterium.

**Getrennte Schutzfälle bestanden:** Cancel terminal 0,204 s, gemessener Stillstand 0,331 s ab Injektion (Grenzen 3/1 s). Tatsächliche 450-ms-Gyrolücke erzeugt beobachtetes HWT-HOLD, Halt 0,242 s nach HOLD / 0,561 s ab Injektion; Mission terminal `hwt_terminal`, kein HOLD/ACK-/Fortsetzungs-/Resume-Positivnachweis. Alle fünf Endläufe eindeutige wirkliche TF-Publisher-GIDs, höchstens ein NavigateToPose-Kind/ExploreArea-Elternziel, terminal keine aktiven Handles und alle vier Befehlsstufen null. Volle unabhängige gepaddete Kontur kollisionsfrei. Drei negative Erkundungsmissionen bleiben negativ.

**Build/Test:** 17 native Supportpakete frisch gebaut und 14 gepinnte AP-03-Nav2-Pakete wiederverwendet, ursprünglicher frischer Neunpaketbuild samt echter C++-BT-Kompilation; VL53/Safety/Scan ergänzt, abschließender isolierter **Zwölfpaketbuild 6,41 s**. **1.844 direkte Tests**, **1.836 reguläre colcon-Tests**, jeweils vollständig grün ohne Fehler/Skipped; Mengen überlappen. **8/8 native Bewegungsregressionen** und nativer Nahbereichs-Rot/Grün-Fall bestanden. **135** installierte Produktdateien bytegleich zu geprüften Quellen, tatsächliche AP-06-Nachrichtenbindings/Modulpräfixe/Binär-SHAs gesichert. Native Gesamt-/C++-Prüfungen auf Ubuntu 22.04/Humble/amd64/Python 3.10.12/rclpy 3.3.17; vollständige Python-/colcon-Regression auf 3.3.22. Alter passiver DDS-Timingfehler auf 3.3.17 mitsamt Original-JUnit erhalten, 180-ms-Radfrische nicht gelockert. Kein ARM-/aktueller Jetson-Gesamtbuild behauptet. Native Upstream-Unit-Tests/Remote-CI nicht ausgeführt; Workflow-Auswahl ergänzt. [Originalnachweise, Pflichtfallmatrix und Prüfsummen](evidence/ap06-20261003/README.md).

**Persistenz tatsächlich begrenzt geprüft:** alle fünf echten Kartenmanager-Saves erzeugen synthetische Rohkarten. Vier exakte Karte-/Checkpoint-Paare (A/B/C/Cancel) passiv über originale Schema-/Prüfsummen-/Fingerprintfunktionen geladen, ohne Fahrfreigabe. Gyro-HOLD meldet ehrlich `metric_checkpoint_exact_saved_snapshot_unavailable`; kein vollständiges Backup dieses Falls. Aktive Relokalisierung/Wiederaufnahme und reale WE-M5-Wiederaufnahme offen.

**Zielsystemgrenze:** Nutzer präzisiert, dass die App auf dem Jetson läuft; App-Projekt `/home/p/roboter_ws` bestätigt. Tatsächlicher Befehlswerkzeugkontext bleibt x86_64/Debian 13/`/workspace`, ohne Jetson-Modellpfad, Gerätealiases oder jenen lokalen Projektpfad. Terminal-Anbindungsversuch lieferte ebenfalls Cloud-Kontext; letzte Terminalabfrage keinen zugeordneten lokalen Ausführungskanal. Cloud ohne VPN/TCP-Ziel/Robotercredentials. Keine neue LAB-1-Freigabe fehlt. Kein tatsächlicher Geräte-/Consumerlast-/Besitzerwechseltest oder Realversuch; ROBOT_TRANSFER unverändert. Selbst bei verfügbarer lokaler Ausführung sperrt das negative Gesamtsoftwarekriterium eine Abnahmefahrt. Native Apple-/WE-M7-Prüfung separat offen. Eigene temporäre Docker-Prüfprozesse/Container nach Nachweissicherung geordnet gestoppt; Originalcheckouts erhalten.

**Genau nächster Schritt bleibt AP-06:** feste erste unbekannte Egress-Kontur und aktuelle SLAM-Raster-/Referenzänderung geometrisch konsistent verbinden, mit frischem ganzen Fahrzeugbeweis und neuer gültiger Pfadbindung, ohne erneute Freiraumannahme/Wiederbetretung oder Budgetreset. Gesicherten bewegungsabhängigen Gegenfall zuerst schließen, dieselben drei Gesamtmissionen wiederholen; anschließend technisch verifizierter Zielsystem-/LAB-1-Vorlauf und Realabnahme. Keine automatische AP-07-/Installarbeit. Rückfall nur eigene AP-06-Commits gezielt revertieren; Räumstrahl-Revert stellt den belegten alten Fehler wieder her.

## 03.10.2026 – MASTERPLAN v1.3 / AP-05 software_geprüft; WE-M7 nativ offen

**AP-05-Kern, Persistenz und ROS-Verbraucherverträge software_geprüft.** Nutzer „gut mache weiter“ beauftragt AP-05 nach dessen konkreter Übergabe. Saubere Basis `2532f1b`, Branch `feature/metric-observation-persistence`, Worktree `/workspace/Roboter_ws-ap05`; Softwarecommit **`090762d93dd4c270478cb31c01c05d07c1da0459`**, Auftragscommit `4a370c0`. MASTERPLAN v1.3 bytegleich; [AP-04-Auftrag archiviert](archive/20261003-ap04/README.md). Keine Hardware, Roboternetzverbindung, Deployment, Push/Merge oder automatische AP-06-Arbeit. Originalcheckout und AP-01–04 bleiben unverändert.

**Fortschritt und Abschluss:** Ankunft allein erledigt kein Ziel. Tatsächlicher Gewinn erfordert neue passende Karte und neuen endlichen Scan, belegte unbekannt→beobachtet-Weltzellen ohne Wand-/Masken-/Reichweiten-/Rasterwiderspruch; nach Verarbeitung Frische und Originaldeadline erneut prüfen. Stationäre Beobachtung höchstens 2 s innerhalb ursprünglicher Goal-/Gesamtfrist; bestehender HWT-HOLD/ACK ohne neues Kind oder Budgetreset. Neue lokale Evidenz erlaubt nach Cooldown dieselbe Aufgabe erneut, höchstens drei Gesamtversuche, keine neue ID durch entfernte Kartenänderung. Gesamterfolg erst nach vorab festem mindestens **3-s-Fenster**, mindestens drei verschiedenen gültigen Scans und kontinuierlich keiner raw-erreichbaren Restaufgabe/ungeklärten zugänglichen Verbindung. Prüfung erfolgt vor Größen-/Geometrie-/Historienfiltern; hinter Wänden unbekannte Zellen verhindern Erfolg nicht pauschal. Letzter Callback-Race wird erneut geprüft. Datenverlust, Filter, Blockade, Versuchs- und Budgetende ergeben keinen Erfolg.

**Ergebnisse und Verbraucher:** `metric_complete`, `usable_partial`, `blocked_help_required`, `error`, `user_canceled` getrennt im versionierten metrischen Statusobjekt. Bestehende ExploreArea-Wirefelder unverändert; nur wirklicher metrischer Abschluss endet SUCCEEDED/true, Cancel terminal CANCELED/false. Bestehender BT-Erfolgspfad bleibt maßgeblich; Missiontelemetrie kann ihn weder beenden noch entsperren. Bestehende App-Modell/UI/Testquelle zeigen die Zustände und Ankunft/Beobachtung/Gewinn getrennt, keine metrische Bodenabdeckungs-Prozentbehauptung. Rohkarte, kumulativer Sichtgewinn, Fahrspur und Semantik bleiben getrennt; weder semantischer Vollabschluss noch unbekannte geschlossene Räume behauptet.

**Bestehende Persistenz:** Schema-1-Checkpoint an exakte gespeicherte Kartenidentität/Fingerprint/Sitzung/Scope gebunden, einschließlich Aufgaben/IDs/Versuchen und Goal-/Fehler-/Gesamtbudgets. Kartenmanager und Sidecar behalten ihre vorhandenen atomaren Einzelverträge; Abbruch zwischen beiden hinterlässt eine Rohkarte ohne Resume-Aufgabenstand, kein vollständiges Backup. Letztes gültiges Paar und gültige ältere Sidecarrevision erhalten. Keine stille Bindung an fremde Karte; Snapshot-Race konkret gemeldet. Laden passiv. Resume nur über explizites Prozessstart-Opt-in, originale Map-ID, neuen gültigen Auftrag, aktuelle Pose/Quellen und **frischen vorhandenen verifizierten globalen Lokalisierungsstatus** derselben Karte. TF/Ready-Bool allein genügt nicht. Ausfallzeit verbraucht Gesamtbudget; keine Versuchs-/Limitreset. Fehlender/ungültiger Resume überschreibt letzte Sicherung nicht.

**Tests/Build/Nachweise:** **65 neue Fälle**, **225 installierte Metriktests**, **1.751 betroffene Tests**, **1.664 registrierte colcon-Tests**, alle bestanden, keine Fehler/Skipped; Mengen überlappen. Frischer echter **Zehnpaketbuild**, anschließend Explorer-Neubuild und vollständiger Wiederholungslauf für letzte Deadline-/HOLD-Korrekturen. Ubuntu 22.04/Humble/Python 3.10.12/rclpy 3.3.22; localhost/Domain 230, network none, keine Geräte. Tatsächliche installierte Produktmodule/Config/Action bytegleich zum Quellcopy/Softwarecommit. Zwei echte DDS-Actionfälle belegen Erfolgs- und Cancel-Wirezustand; synthetische Karten/Scans/Pose und einzelne Nav-Gegenstellen bleiben Komponentenprüfung. Alle ursprünglichen Quellen-/Gate-/Geometrie-/Lifecycleverträge erneut geprüft. [Originalnachweise](evidence/ap05-20261003/README.md) mit Pflichtfallmatrix, roten AP-04-Ankunfts-/AP-05-Deadline-Gegenproben, sämtlichen Zwischenständen, Original-JUnit/Buildkommandos, Install-/Quellhashes und SHA256SUMS. CI-Auswahl ergänzt, Remote-CI nicht ausgeführt.

**Konkreter offener Plattformnachweis WE-M7:** Linux-Workspace ohne `swift`, `xcodebuild`, `xcrun`/Apple-SDK/Simulator. Native iOS-Build/Laufzeit und ergänzte Swift-Tests **nicht ausgeführt**; Python-Rosbridge-/ROS-Verträge sind kein Ersatz. Gemäß MASTERPLAN AP-05 bleibt dies separat offen und sperrt den unabhängigen Kernabschluss nicht.

**Grenzen/Rückfall:** Vollständige Mission/BT/Explorer/Nav2/SLAM-/Sensorkette und physische Start-/Mast-/Tür-/Tracking-/Stopplast weiterhin offen. Historischer synthetischer Graphprüfer nur an neue Resultassertionen angepasst, in AP-05 nicht neu abgenommen. Keine neuen Freiraumannahmen, Geometrie-/Fristlockerung oder Jetson-Profil-/Installänderung; ROBOT_TRANSFER unverändert. Rückfall ausschließlich eigene AP-05-Commits gezielt revertieren; AP-01–04 und fremde Arbeit erhalten.

**Genau nächster vorbereiteter Schritt: AP-06** gemäß MASTERPLAN v1.3 – zunächst vollständige bewegungsabhängige geschlossene Gesamtsoftwareprüfung mit den vorab festgelegten Szenarien/Startposen, anschließend separat technisch begrenzte Zielsystem-/Realabnahme. AP-06 **nicht begonnen**; der AP-05-Auftrag startet keine Robotertests. WE-M7-Nativprüfung bei verfügbarer Apple-Plattform zusätzlich schließen.

## Erhaltene Paketabschlüsse


## 03.10.2026 – MASTERPLAN v1.3 / AP-04 software_geprüft

**AP-04 software_geprüft auf Kandidaten-/Adapterebene.** Nutzer ausdrücklich „gut dann mach mit 04 weiter“. Saubere Basis `495b538`, Branch `feature/frontier-candidate-core`, Worktree `/workspace/Roboter_ws-ap04`; Softwarecommit **`5ee313b47ea2ef7c98554e42a9cae224a8a7d0ca`**. Originalcheckout und AP-01–03 sauber/unverändert. MASTERPLAN v1.3 bytegleich. Keine Hardware, Deployment, Push/Merge oder automatische AP-05-Arbeit. [AP-03-Auftrag bytegleich archiviert](archive/20261003-ap03/README.md).

**Entscheidung nach MASTERPLAN-Alternative:** Gepinnter unveränderter Fremdkern `mertgulerx/frontier_exploration_ros2@418e9717564a895214275e088ea7075b8ac88f64` wirklich gebaut, 134 Unit-Tests bestanden. Sein einziger Ringvorschlag scheitert an der gleichen Fahrzeugprüfung; am langen Rand bietet er unzureichend verteilte Sicht. Deshalb eigene Gewinnung begrenzt korrigiert und erneut verglichen: tatsächliche freie Randpunkte statt Schwerpunkt, mehrere räumlich getrennte Positionen, Annäherung zur bekannten freien Seite, aktuelle echte Scan-/TF-/Scope-/Reichweiten-/Maskenprüfung. Keine externe Runtimeabhängigkeit oder zweiter Navigator. `existing` bleibt Gesamtdefault; read-only `metric_candidate_source` wählt im expliziten metrischen Modus die Korrektur oder `legacy_centroid` als Rückfall. Bestehende Kontur-/Regler-/Quellen-/HOLD-/Kindverträge und Budgets erhalten.

**Abnahmen:** Alle sieben Pflichtfälle auf Kandidatenebene; Wachstum und Wiederbeobachtung über je drei Kartenstände. Unverändertes installiertes Original: Ring → `approach_unavailable` → null Ziele; korrigierte Gewinnung → fünf mit echtem Nav2 zulässige Alternativen. Langer Rand nach tatsächlicher vollständiger Pfadprüfung: **5,9 m** potenziell sichtbarer Rasterrand aus mehreren Eigenpositionen gegenüber **1,9 m** Fremdkern. Gleiche deklarierte endliche synthetische Sicht, Raster, Planung und Schutzbedingungen; kein gemessener Beobachtungsgewinn. **110 echte ComputePathToPose-Pläne**, **74** nach Produktgeometrie zulässig, davon **63** Eigenkorrektur; **36** unzulässige Zielgeometrien ehrlich verworfen. Kein FollowPath oder Motorpublisher. Ursprungrotation korrekt transformiert; Fremdbrücke lehnt sie explizit ab. Neue lokale Kartenevidenz nahe früherem Ziel liefert wieder Vorschläge; missionseigene Erledigung bleibt AP-05.

**Regression/Build:** **27 neue Fälle**. **1.636 betroffene Tests**, **165 gegen installierte Module**, **1.604 registrierte colcon-Tests** bestanden, keine Fehler/Skipped; Mengen überlappen. Frischer aktueller **Zehnpaketbuild**, frischer nativer **Achtpaket-Produktbuild**, unveränderter Fremdkern und CPP-Vergleichsbrücke gebaut. Neue und native installierte Produktmodule bytegleich zum Worktree. Echte Ubuntu-22.04/Humble-/Python-3.10-Laufzeiten, rclpy 3.3.22 bzw. native 3.3.17; keine Nachrichten-/Planerattrappen. Vorhandene AP-03-Nav2-1.1.20-Binärunterlage wiederverwendet, nicht als neuer Nav2-Build gezählt. CI ruft neue pytest-Datei auf; Remote-CI nicht ausgelöst.

**Originalnachweise:** [AP-04-Evidenz](evidence/ap04-20261003/README.md) mit Pflichtfallmatrix, allen nativen Pfaden/Planerlogs, Originalkern-Gegenbeispiel, gemeinsamen Eingaben, konkreten Befehlen, Pin/Lizenz, Image-/Installidentität und SHA256SUMS. Ein korrigierter neuer Minimalreichweiten-Test und erster nativer Prüferabbruch bleiben als Originalbelege erhalten. Keine Frist-/Reserveänderung, um grün zu werden. Historische unabhängige Python-3.12-/DDS-Befunde bleiben in AP-01/AP-03 erhalten.

**Grenzen/Rückfall:** Nur Kandidaten-/Adapter-/Planungssoftware geprüft. Potenzielle Sicht ist keine tatsächlich gemessene Beobachtung; native Plan-SUCCESS ohne volle Geometrie wurde abgelehnt. Mission/BT/Explorer/Nav2/Sensorkette, physische Start-/Mast-/Tracking-/Türabnahme und aktive Jetson-/Stopplast bleiben AP-06; AP-03-Simulationsprofil nicht für Hardware aktiviert. Große Karten oberhalb expliziter Kandidaten-/Sichtkapazität werden konkret blockiert, nicht als abgeschlossen gewertet. Alte missionseigene Erfolgs-Nachbarschaftssperre bleibt für **AP-05** offen. Rückfall nur eigene Software-/Dokumentcommits gezielt revertieren oder `legacy_centroid` beim gestoppten Start auswählen; AP-01–03 und fremde Arbeit erhalten. Kein Jetson-Installwechsel; ROBOT_TRANSFER unverändert.

**Genau nächster vorbereiteter Auftrag: AP-05** – Ankunft/Beobachtung/Erledigung trennen, begrenzte Wiederbeobachtung, ehrlichen Erfolgs-/Teilstandszweig und vorhandene Persistenz-/Verbraucherschnittstellen schließen. Noch nicht begonnen; eigene ausdrückliche Nutzerbeauftragung erforderlich. Vollständige Softwarekette und Hardwarequalifikation bleiben danach AP-06.

## 03.10.2026 – MASTERPLAN v1.3 / AP-03 software_geprüft

**AP-03 software_geprüft für die geschlossene synthetische Komponenten-/Bootstrapprüfung.** Nutzer hat AP-03 ausdrücklich beauftragt. Basis `875c7c4`, Branch `fix/nav2-bootstrap-geometry`, Worktree `/workspace/Roboter_ws-ap03`; Softwarecommit `c3115ff8ecb28b0828e1de8b8e062c6f0866f55e`. Originalcheckout, AP-01-/AP-02-Worktree sauber und unverändert. MASTERPLAN v1.3 bytegleich. Keine Hardware, kein Deployment/Push/Merge oder automatischer AP-04-Übergang. [AP-02-Auftrag bytegleich archiviert](archive/20261003-ap02/README.md).

**Umsetzung:** Ein ungültiger kürzester Eigenpfad schließt ein verbundenes bekanntes Ziel im neuen Opt-in-Profil nicht mehr dauerhaft aus. Er bleibt gekennzeichneter Nav2-Planungsvorschlag; vor jeder Vorausrichtung/Fahrt ist der tatsächliche Nav2-Pfad vollständig zu prüfen. Live/HOLD-Prüfung verwendet diesen tatsächlichen Pfad statt ihn durch eine andere Eigenroute zu verwerfen. Vorhandene NavFn-A*/RPP-Kombination nach Messung erhalten; kein weiterer Navigator oder Frontier-Kern. Numerische Sub-Halbzell-Endstücke erfinden keine Enddrehung.

**Geometrie:** Asymmetrischer Achsbezug, vollständiges Chassis x=−0,11…+0,31/y=±0,23 m und 0,02-m-Padding unverändert; halbe Zelldiagonale, 0,01-m-Interpolationsreserve sowie 0,15-m/±0,40-rad-Goalhülle bleiben geprüft. Neues schreibgeschütztes `rpp_rollout`-Simulationsprofil prüft tatsächliche berechnete Bewegungen einschließlich Drehen mit zusätzlich 0,02-m/±0,05-rad-Trackingband und erfordert aktivierte Vorausrichtung auf das erste tatsächliche Pfadstück innerhalb 0,02 rad. 17 echte Controllerparameter müssen passen. Bestehendes konservatives Profil bleibt Default. [Gemeinsamer Bewegungsvertrag](BEWEGUNGSVERTRAG.md).

**Geschlossene echte Nav2-Abnahme:** Acht Fälle bestanden. 68-/80-cm-Durchfahrt jeweils beide echte Actions erfolgreich, maximal rund 2 mm Tracking und mindestens 80/140 mm Abstand des gepolsterten Footprints. Längere 3,682-m-Umfahrung trotz verworfener Eigenroute erfolgreich, maximal 3,485 mm Positions-/0,005011 rad Headingabweichung und 201 mm Abstand. Vorbestimmte Tür-/Umfahrungsziele sind Komponententests, keine autonome Wohnungserkundung. Unzulässige 56-cm-Durchfahrt und Rotation im 68-cm-Spalt trotz NavFn-Punktpfad vor FollowPath verworfen; unbekannter Außenraum vom tatsächlichen Planer abgelehnt. Keine Nichtnullkommandos in diesen Negativfällen. Rückwärtsanteil sämtlicher positiver Fälle null.

**Autonomer Bootstrap:** Tatsächlicher bestehender Frontierdetektor/Approach/Policy wählt selbst einen ersten Beobachtungspunkt; Vollscan bei unbeobachtetem hinterem Außenraum gesperrt. Echte Nav2-Regelbewegung gewinnt im endlichen verdeckungsgeprüften synthetischen Sichtmodell 0,454 m² neue beobachtete Fläche. Fehlende initiale Kontur ergibt `wait` mit 168 fehlenden Zellen je Quelle, keine identischen Start-/Scanwiederholungen. Eigenkörper-/Egress-Ausnahmen und AP-02-Invalidierung bleiben erhalten. Separates begründetes reales Sensorpositions-/Abdeckungspaket im Bewegungsvertrag nur vorbereitet.

**Tests/Build:** 22 neue aussagekräftige Regressionen; Gegenprobe auf Original-AP-02: 18 erwartete Fehlschläge, 4 negative Fälle bestanden. Aktuelle AP-02-basierte Humble-Laufzeit: 138 Installtests, **1.609 betroffene Tests** einschließlich aller fünf echten DDS-Callbackfälle und **1.577 colcon-Tests** fehlerfrei; echter Zehnpaketbuild mit neuen Repo-/Nav2-Aktionsbindings und geprüfter Install-/Quellenidentität. Zusätzlich echte native Nav2-Planer-/Controller-/Pluginbuilds (14 Pakete) und acht Repo-Pakete in getrennter Installation. Mengen überlappen. CI-Auswahl und echter Nav2-Prüfjob ergänzt; kein GitHub-Lauf. [Vollständige Originalbelege und Reproduktion](evidence/ap03-20261003/README.md).

**Beobachtete Grenze:** Zwei Sammelläufe und ein erster Einzelversuch eines unveränderten engen DDS-Timingtests schwankten im älteren Nav2-Prüfimage (u.a. rclpy 3.3.17). Vier spätere Einzelprozesse dort sowie alle fünf Fälle und der vollständige Abschlusslauf auf AP-02-Laufzeit (rclpy 3.3.22) bestanden. Fehllogs erhalten; keine Ursachengarantie, kein allgemeines Last-Grün und keine Frist-/Schutzlockerung. Aktive Jetson-/Worst-Case-Abnahme bleibt AP-06.

**Offen:** Physische Türen/Startabdeckung und echte Motor-/Tracking-/Stopplast. Simulationsantwort 50 ms und 25-ms-Schrittkappe sind kein Nachweis für die reale 2000-ms-Antriebsrampe, Smoother, Schlupf und Sensor-/TF-Latenzen. Gesamte ExploreArea-/BT-/Mission-/Sensor-/Gatekette und Wohnungsvollständigkeit nicht als abgenommen ausweisen. Das Simulationsprofil ist nicht am Jetson aktiviert.

**Rückfall:** Nur eigene AP-03-Software `c3115ff` und zugehörige Dokumentation gezielt revertieren; AP-01/AP-02, Main/Jetson und fremde Arbeit erhalten.

**Genau nächster Schritt:** AP-04 gemäß MASTERPLAN v1.3 als eigenen begrenzten Softwareauftrag beauftragen. Keine automatische Frontier-Integration, Profilaktivierung oder Fahrt aus diesem Abschluss.

---

## 03.10.2026 – MASTERPLAN v1.3 / AP-02 software_geprüft

**AP-02 software_geprüft.** Nutzer hat AP-02 nach AP-01 ausdrücklich beauftragt.
Keine Hardware, kein Deployment/Push/Merge und kein automatischer AP-03-Übergang.
MASTERPLAN v1.3 bleibt bytegleich; sein ursprünglicher AP-01-Einstieg ist durch
AP-01-Abschluss und den ausdrücklichen Folgeauftrag abgearbeitet.

**Basis/Lieferung:** AP-01-Abschluss `45f268a` auf der bestätigten Integrationsbasis
`08a4b9a`; sauberer eigener Worktree `/workspace/Roboter_ws-ap02`, Branch
`fix/map-lifecycle-source-contract`. Softwarecommit
`96bbd4d8ed6d0b7a3ca6816d7c5fae14c27f45d4`. Originalcheckout und AP-01-Worktree
unverändert. [Aktueller abgeschlossener Auftrag](AGENTENAUFTRAG.md),
[bytegleich archivierter AP-01-Auftrag](archive/20261003-ap01/README.md).

**Konkrete Reparatur:** Raster-/Ursprungs-/Quaternionwechsel verwerfen alte
Egress-/betroffene Body-Evidenz vor Arrayoperationen, ohne Re-Ankern. Normale
passend korrelierte Folgeupdates erhalten neu geprüfte Weltziele. Exakte
Rohkarten-/Statusjoins ersetzen den aktiven Ersatzjoin mit alter Revision;
identischer Inhalt darf eng begrenzt den letzten exakten Snapshot innerhalb
seiner ursprünglichen Fristen erhalten. Verspätete Rohkarten überschreiben
auch den generischen Explorerstand nicht. Sitzungs-/Frame-/Auflösungs- und
beobachtete Rückwechsel sperren alte Arbeit und verspätete Plan-/Kindresultate.
Quellen-, Pose- und Scanfrische wird nach Verarbeitung erneut geprüft.
Der echte Kartenmanager erhält konsistente Beobachtungsrevisionen bei
Duplikaten und verwirft alte positive Stempel ohne Frische-/Revisionserneuerung.

**Gemeinsamer Vertrag:** [Karten-/Quellenbudget](QUELLENVERTRAG.md) ordnet HWT,
Encoder, TF, Gate und Explorer über Empfang, IO, Verarbeitung, DDS, Frische
und Kontinuität zu. Aktiver/passiver Pfad getrennt; bestehende Fristen,
Timingkern und AP-01-Clockvertrag erhalten. Kein allgemeiner Health-/Executor-
Umbau und keine vorgezogene AP-03-/AP-04-Geometrie-/Controller-/Frontierintegration.

**Abnahme:** 55 neue echte Lifecycle-/Produzenten-/Elternschleifenfälle:
100×100 → 100×101, Wachstum mit verschobenem Ursprung, Rohkarte/Costmap,
Auflösungs-/Sitzungs-/Frame-/Quaternionwechsel und Rückwechsel, verspätete
Arbeit, notwendige Quellen verloren, gültige Folgeupdates. Keine Arrayausnahme,
keine falsch gültige alte Maske und keine neue Freiraumannahme. Nav2-`success`
nach Quellenausfall/Kontextwechsel zählt keinen Besuch; gültiges Ziel bei
harmlosem Wachstum bleibt ausführbar.

**Ausgeführte Prüfung:** 1.587 betroffene Pytesttests bestanden, 116 gezielte
Tests gegen das neue Installationspräfix bestanden (einschließlich 55 neuer
Fälle), 1.555 registrierte colcon-Tests ohne Fehler/Fehlschläge/Skipped.
Mengen überlappen. Zehn Pakete mit echten Humble-/Nav2-/robot_interfaces-
Bindungen gebaut; Modul-/Paketauflösung und installierter Code geprüft.
Der Kartenmanager registriert nun tatsächlich seine 53 Map-Core-Tests für
colcon. Gegenprobe auf unverändertem AP-01-Stand: 30 erwartete Fehlschläge,
1 bestandener Fall, 24 abgewählte Fälle. Passende bestehende CI-Trigger und
Pytestauswahl ergänzt; GitHub-Actions nicht gestartet.

**Originalbelege/Reproduktion:** [AP-02-Evidenz](evidence/ap02-20261003/README.md)
mit Build-, Import-, Codehash-, Test-, Baselineausgaben, exaktem Skript,
Umgebung und SHA-256-Manifest. Der anfängliche Voll-`src`-Discoverybuild
scheiterte an nicht gebauten transitiven Launchpaketen; der explizite betroffene
Zehnpaketausschnitt wurde anschließend vollständig gebaut, ohne Dummy-Präfixe.
Dies belegt keinen kompletten Nav2-/BT-/Hardwarelaunch. Der bekannte
Python-3.12-JSON-Baselinefehler aus AP-01 bleibt unverändert außerhalb der
Humble/Python-3.10-Abnahme. Keine pauschale Gesamt-Grünbehauptung.

**Grenzen/Rückfall:** WE-M0 und betroffener metrischer WE-M3-Softwareanteil;
keine vollständige Meilenstein-, Zielsystem-, Start-/Geometrie-, Semantik- oder
Hardwareabnahme. Belastbare aktive Jetson-/Vollstackzeit bleibt AP-06.
Keine Runtimeänderung auf Jetson, deshalb kein neuer ROBOT_TRANSFER-Eintrag.
Nur eigene AP-02-Software-/Dokumentcommits gezielt revertieren; AP-01 erhalten,
keine fremde Arbeit oder pauschalen Altbranch zurücksetzen.

**Genau nächster Schritt:** AP-03 „Bewegung und autonomer Start zusammenführen“ gemäß MASTERPLAN als
separaten Auftrag mit echtem Nav2-Planer-/Controllerpfad und geschlossenem
synthetischem Bootstrap-/Geometrieprüfstand vorbereiten. Hier nicht ausgeführt
oder automatisch aktiviert; keine weitere Code- oder Hardwarearbeit aus AP-02.

## Historie

## 03.10.2026 – MASTERPLAN v1.3 / AP-01 software_geprüft

**AP-01 software_geprüft; Zielsystem, reale Sensor-/Start-/Geometrieabnahme und Wohnungserkundung weiterhin offen.** Kein Hardwarezugriff, Deployment, Push oder Merge. AP-02 ist ausschließlich als Übergabe vorbereitet.

**Basis und Lieferung:** Remote `feature/hwt-hold-recovery-resume` am 03.10.2026 auf `08a4b9ac0b7a128ced2199f20976f3aa92ea55fe` bestätigt. Ursprünglicher lokaler Checkout `work`/main `05439c7` sauber und unverändert belassen; isolierter Worktree `/workspace/Roboter_ws-ap01`, Branch `fix/hwt-clock-correlation`. Keine unbekannten lokalen Änderungen auf der Integrationsbasis. Dokumentübernahme `84abfc6`, geprüfter Softwarecommit `c797442b37994f774df40b6b27d54c27efa3bdc3`. Keine aus einem Branch abgeleitete Jetson-Installationsbehauptung. WE-D0/WE-M0 und betroffener WE-M3-Recoveryanteil.

Kanonisch: [MASTERPLAN v1.3](MASTERPLAN.md), [abgeschlossener AP-01-Auftrag](archive/20261003-ap01/AGENTENAUFTRAG.md), [Meilensteine](MEILENSTEINE.md), [LAB-1](../LABORMODUS.md). Die vier Vorgängerdateien sind mit Commit-/Blob-/SHA-256-Beleg [bytegleich archiviert](archive/20261002-v1.2/README.md); MASTERPLAN entspricht dem Anhang bytegleich. AGENTS/Meilensteine/Gesamtstrategie und PROJECT_MEMORY gezielt synchronisiert, begrenzte AP-04-Erlaubnis ausdrücklich übernommen. ROBOT_TRANSFER unverändert.

### Reparatur und Zeitvertrag

Produktänderungen nur in `hwt601_imu_node.py` und dem privaten `_hwt601_clock.py`. Transport, Guard/Health, Encoder, EKF, Bias, Profile, Mission/Explorer und Recoverycode unverändert. Der echte Transport bleibt vollständiger Hostempfangsbeleg, nicht interner Sensorabtastzeitpunkt. Fehlender/ungültiger Empfangs- oder Transaktionsbeleg wird jetzt hart zurückgewiesen; kein Fallback auf Verarbeitung/Veröffentlichung.

Monotonic rahmt die ROS-Abfrage ein. Präzise Offsetspannen werden geschnitten; ein Bracket von höchstens **1 ms** und höchstens **drei** sofortige Versuche innerhalb derselben echten Transaktionsfrist. Unterer Offsetrand gibt konservativ höchstens 1 ms + 2 ns früheren Empfangsheader; kein Futurefehler durch wechselnden Mittelpunkt. Die Grenze entspricht 1/10 des nominellen Probenabstands und 1/100 der unveränderten Biaskontinuitätsgrenze. Größere Brackets werden verworfen, ohne letzten gültigen Empfang/Header/Samplehistorie zu ändern oder den Transport zu schließen. `clock_correlation` unterscheidet Unsicherheit und Zeitbasisänderung.

Disjunkte Belege bleiben harte Zeitfehler, auch wenn Header noch steigen; keine Neubasierung. Aktive ROS-Time/`use_sim_time`, Clockobjekt-/Typwechsel sowie zwischen Polls aktivierte/deaktivierte ROS-Time werden konservativ gesperrt. Unterstützt: unveränderte Host-SYSTEM_TIME oder inaktive ROSClock mit Hostzeit. Sprünge unter Messunsicherheit sind nicht garantiert erkennbar; der Hostvertrag verlangt denselben laufenden Taktbezug. Siehe [ausführlichen Clockvertrag](../../src/robot_state_estimation/README.md#ap-01-hostempfang-und-clockvertrag-masterplan-v13). Entwicklung bleibt bei harten Fehlern terminal; Legacy-Hard-/Reconnectbehandlung bleibt erhalten.

Unverändert: Entwicklung 50 ms Antwort/Gesamtablauf und 300 ms Rohfrische; Legacy 30/200 ms; Encoder 120/180 ms; Bias-/HOLD-/Recoverygrenzen. Messagebau/Paarungsversuche werden ebenfalls vor Veröffentlichung gegen die Gesamtdeadline geprüft. Wiederholte Unsicherheit führt durch das Alter der letzten echten Probe zur bestehenden Health-HOLD-Reaktion.

### Vorher/Nachher und Pflichtfälle

[Originalmethoden vor Reparatur](evidence/ap01-20261003/ap01-original-method-proof.json): erster Header `1010,000 s`, zweiter echter Empfang `1010,010 s`, nach ROS-Abfrage 20 ms Pause → berechnet `1009,990 s`, terminal `HWT-Messzeit nicht monoton`, Transport geschlossen, nur ein veröffentlichter Wert. [Gewünschter Regressionstest rot](evidence/ap01-20261003/ap01-before.log).

[Reparierte Methoden aus dem Install](evidence/ap01-20261003/ap01-repaired-method-proof.json): zweite Paarung bei monotonic `10,030 s` gültig, Header bleibt exakt Empfang `1010,010 s`; spätere Probe `1010,040 s` ebenfalls veröffentlicht. Drei akzeptierte Werte, null verworfene Werte, kein Terminalfehler, Transport offen. Keine Testnachbildung der Poll-/Fehlerentscheidung.

| Pflichtklasse | Tatsächlicher Nachweis in `test_hwt601_time_correlation.py` |
|---|---|
| Präzise +10 ms, wechselnde kleine Brackets | exakter Empfangsbezug; kontinuierlicher gültiger Strom, zwei konstante Offsets, Fehler ≤1 ms |
| Originalpause, Verzögerung vor/in/nach Paarung, konstant/wechselnd groß | korrekt datiert; erneute präzise Paarung statt Mittelpunktprojektion |
| Unbrauchbar → präzise, wiederholt unbrauchbar | kein Zwischenwert/Reset; letzte gültige Daten altern, nächste echte Probe verarbeitet |
| Transaktions-/Verarbeitungsfrist | 30-/50-ms-Gegenfälle für Verarbeitung, Retry, Dekodierung und Messagebau; keine Publikation |
| Fehlend/NaN/Inf/zukünftig/rückläufig/wiederholt | echte Poll-/Fehlerlogik weist Beleg zurück, kein Ersatzzeitpunkt |
| Unabhängige ROS-Sprünge, kleiner als Probenabstand | ±2/±20 ms bei steigender monotonic erkannt; selbst bei weiter steigenden Headern terminal |
| Tatsächliche Clock-API/Quellenwechsel | echte ROSClock/TimeSource und unabhängige Overrideänderung; Aktivierung/Deaktivierung auch zwischen Polls erkannt |
| Verbundene Verbraucher | echte Guard-/Health-Zeitprüfung akzeptiert erzeugte Header bei 0/0,05/2 ms Zustellung; Future-Gegenfall bleibt hart; echte Alterung bewirkt HOLD |
| Transport/Schutzwirkung | echter serieller Produkttransport + synthetische Gegenstelle, ganz/fragmentiert und verzögerte Dekodierung; CRC/Identität/Timeout bestehend, Sättigung zusätzlich |

### Befehle, Ergebnisse und Auflösung

Vollständige Aufrufe: [ap01-run-final.sh](evidence/ap01-20261003/ap01-run-final.sh). Plattform und Präfixmapping: [Evidenzregister](evidence/ap01-20261003/README.md). Ubuntu 22.04/x86_64, echtes ROS Humble, Python 3.10.12; localhost/Domain 226 für DDS-Tests. Keine Geräte eingebunden.

| Ausführung | Ergebnis | Originalbeleg |
|---|---|---|
| `colcon build --packages-select nav2_common nav2_msgs amadeus_map_identity explore mission_manager robot_state_estimation robot_interfaces base_hardware`, getrennte Build-/Installpräfixe | 8 Pakete bestanden | [Buildlog](evidence/ap01-20261003/ap01-verified-build.log) |
| `pytest` neue Clock-/Rawtests, nur Testpfad plus frisches Install | 58 bestanden, davon 52 neue AP-01-Fälle | [Installtests](evidence/ap01-20261003/ap01-regressions-installed.log) |
| `pytest` vollständige state/base-Tests, Gate-Integration/pending-wheel/source-callbacks, HWT-Recovery/Kindpolitik/Kindvertrag, Mission-HWT und JSON | **443 bestanden** | [Regressionen](evidence/ap01-20261003/ap01-regressions-final.log) |
| `colcon test` state/base und `colcon test-result --verbose` | **381 Tests, 0 Fehler/Failures/Skips** | [Registrierte Ergebnisse](evidence/ap01-20261003/ap01-colcon-results.log) |

Mengen überlappen; nicht addiert. Neue Tests laufen bereits in `.github/workflows/hwt601-we.yml`: PR-Pfadtrigger `src/robot_state_estimation/**` und `python3 -m pytest -q src/robot_state_estimation/test ...`. Kein unzureichender unittest-only-Aufruf; keine CI-Neugestaltung nötig. Colcon hat die neuen 52 Fälle tatsächlich gesammelt. Hosted CI wurde mangels Push nicht neu ausgelöst.

[Importauflösung](evidence/ap01-20261003/ap01-imports-installed.log): Raw/Clockhelper aus `/evidence/ap01-install/robot_state_estimation/lib/python3.10/site-packages`; `robot_interfaces` aus neu gebautem `/evidence/ap01-install/robot_interfaces/local/lib/python3.10/dist-packages`; Standardnachrichten/rclpy aus `/opt/ros/humble`. Weitere Verbraucherprüfungen nutzen aktuellen Worktreecode und diese echten Nachrichtenbindungen. Fünf relevante Quell-/Installmodule [bytegleich mit SHA-256 geprüft](evidence/ap01-20261003/ap01-byte-manifest.json). Container `/evidence` entspricht Host `/workspace/scratch`, `/repo` dem isolierten Worktree; kein alter main-Import. Entwicklungs-/Legacyparameter sind explizit in den Fixtures gesetzt; kein behauptetes geladenes Jetsonprofil.

**Unabhängiger Baselinefehler:** Python 3.12.14 / Missionmanager-JSON-Tiefentest nimmt 2.000 verschachtelte Arrays an. [Vorher](evidence/ap01-20261003/ap01-json-before-python312.log) und [nachher](evidence/ap01-20261003/ap01-json-after-python312.log): je 4 Tests / 1 Fehler, Produkt-/Testbytes unverändert. Unter Humble/Python 3.10 besteht derselbe Test in den 443. Nicht behoben, nicht gelöscht/übersprungen oder als Python-3.12-Erfolg gezählt; außerhalb AP-01 und kein Blocker dieses geprüften Zeitpfads.

### Grenzen, Rückfall und genau ein nächster Schritt

Keine Zielsystem-, aktive Last-, Sensor-/Start-/Geometrie- oder Fahrabnahme. Der historische Roboterabbruch ist nicht abschließend erklärt; nur das konkrete Projektionsgegenbeispiel ist behoben. Keine vollständige EKF-/Robotergrafabnahme behauptet; direkte echte Verbraucherkomponenten erfüllen den begrenzten Zeitvertrag. Keine private Wohnungsevidenz übernommen.

Rückfall: eigenen Softwarecommit `c797442` gezielt revertieren und Paket im getrennten Präfix neu bauen; der dokumentierte Originalfehler kehrt dabei zurück. Keine pauschale Branch-/Installrücksetzung. Dokumentübernahme ist unabhängig prüfbar. Laufende Roboterkopie und ROBOT_TRANSFER unverändert.

**Genau nächster Schritt:** den vorbereiteten begrenzten **AP-02-Auftrag** zu Kartenlebenszyklus/Quellenvertrag gemäß MASTERPLAN v1.3 beauftragen. Konkrete betroffene Pfade und Akzeptanzfälle stehen in der [AP-02-Übergabe am abgeschlossenen Auftrag](AGENTENAUFTRAG.md#ap-02-übergabe-vorbereitet-nicht-ausgeführt). Keine automatische Implementierung oder Fahrt.

Der folgende vollständige STATUS ist ausschließlich Historie bis `08a4b9a`; dortige „aktuelle“ Überschriften, Aufträge und Runtimeangaben gelten für den damaligen Stand.

---

# Wohnungserkundung – aktueller Status und nächster Auftrag

**WE-1 · Stand 01.10.2026 · MASTERPLAN v1.2 · Stufe 3 weiterhin OFFEN**

Maßgeblich: [MASTERPLAN](MASTERPLAN.md), [AGENTENAUFTRAG](AGENTENAUFTRAG.md), [LAB-1](../LABORMODUS.md), [MEILENSTEINE](MEILENSTEINE.md). Dies ist der einzige aktuelle WE-Iststand. Die ausführliche bisherige Statusdatei ist [bytegleich archiviert](archive/20260930-v1.1/STATUS.md); alte Abschnittsnummern und „nächste Schritte“ dort sind historische Referenzen.

**Aktueller Abschluss:** HWT-Entwicklungsvertrag und Start-Egress auf `a6f31bf`
implementiert; 1.564 Regressionen, gerätefreier Drei-Ziel- und HOLD-Produktgraph
bestanden. Kurzer Realstart: HEALTHY nach 36,379 s, terminale Messzeitprüfung
bei 54,880 s; aktuelle Geometrie verwirft alle 22 Kandidaten. Keine reale
Mission. Quellenzeit und konkrete Bewegungsgeometrie blockieren unabhängig.
ROS beendet, Rechner eingeschaltet; Einzelgrenzen im neuen Abschluss unter §4.

**Abschluss des vorigen Pakets 01.10.2026:** Adaptiver metrischer Bootstrap und begrenzte
Encoder-Timing-Recovery auf `fd883fd` softwareseitig geprüft. Gemeinsamer realer
Vorlauf negativ: dritte HWT-Störung erschöpft das Budget; unabhängig davon 33
unbekannte Startkonturzellen / 0,021089 m² Außenanteil, kein zulässiger Startkandidat.
Keine reale Mission. Einzelbelege, voller negativer Dauertest und Grenzen im
neuen Abschluss unter §4 sowie AGENTENAUFTRAG §10. **System bleibt eingeschaltet.**

## 1. Aktuelle Nutzerentscheidung

Normale Erkundung wird metrisch organisiert: beobachten → erreichbare Frontier-/Beobachtungsposition wählen → navigieren → neue Beobachtung und Ergebnis bewerten → nächste Aufgabe. Portal-/Raumsemantik ist keine Pflicht für normale metrisch sichere Ziele. Geometrie, Karte/Pose, Scope, Sensor-/Antriebsgesundheit und Schutzkette bleiben verbindlich.

**GRÜN: METRISCHER ERKUNDUNGSKERN – GERÄTEFREI INTEGRIERT BESTANDEN.** Implementiert als explizites `metric_frontier`-Backend im bestehenden Explorer. Default bleibt `existing`. Beim anschließend beauftragten Realnachweis wurden reale Sensor-/ROS-Prozesse im rein lesenden Vorlauf gestartet; dieser blieb blockiert, keine aktive Fahrt oder Mission, kein dauerhafter Installwechsel. Stufe 3 bleibt **OFFEN**. Konservative Geometrieprüfung bleibt verbindlich; reale Zielerreichung, Türpassage und Robustheit sind nicht aus den Softwaretests abgeleitet.

**Historischer Abschluss des vorigen Pakets (01.10.2026):** Ausgang `cf55cea`,
Funktionskandidat `8f5eeb4`, bestehender Branch/PR #105. 1.469 Regressionen
bestanden; Radübernahme, Uhrzuordnung und ganze Eigenkörperzellen gezielt
korrigiert. **Realer 720-s-Gesamtvorlauf negativ, keine Mission/Fahrt.**
Letzter Fehler nach zwei echten HWT-Recoveries: 120,874 ms verworfenes
Encoderpaar, anschließend 212,127 ms alte letzte zulässige Radprobe am Gate.
Unveränderte 120-/180-ms-Grenzen sperren richtig. Geometrie unabhängig davon:
211 unbekannte Rundblickzellen, 0,188420 m² Außenanteil; bereits Anfangskontur
unzulässig. Genaues Ergebnis und Restumfang im aktuellen Abschluss unter §4,
Auftragsabschluss in AGENTENAUFTRAG §9. Der folgende adaptive Auftrag hat diesen
Restumfang gezielt ersetzt; alte Messungen bleiben unverändert erhalten.

## 2. Belegter Ausgangspunkt

| Stand | Beleg / Grenze |
|---|---|
| Remote-Dokumentbasis vor v1.2 | PR #105, feature/hwt-hold-recovery-resume, `99d21c012dfe4c28d8263f7cd5e16505b07736d6`; keine Aussage über aktuelle lokale Runtime |
| Letzter ausgewerteter realer Kandidat | `492ef20`, Ergebnis `d480243`; vollständiger zweiter Lauf stage3-map-handoff-20260929/real-repeat |
| Historischer Funktionsvergleich | `1d91229dc10ff4bb791938d49aae8e9808a5dfff`; [WE_PARITY_RESET](../WE_PARITY_RESET.md) dokumentiert Frontierfahrten, verbundenen Türübergang und weitere Frontiers danach |
| Erster HWT-Recoveryfall | Gerätefreier aktiver Kindzielvertrag und reale Rundblick-HOLD/Recovery/Fortsetzung im dokumentierten Umfang akzeptiert; kein umfassender Robustheitsnachweis |
| Aktueller Erkundungserfolg | Kein bestandener zusammenhängender A/B/C-/Mehrraumlauf; kein Ziel- oder Türerfolg des letzten Laufs |
| Neues metrisches Backend | Software und Mast-/Encoderkorrekturen auf `8be0709` regressiert; gemeinsamer realer Vorlauf weiter negativ, kein Fahrnachweis |

Aktuelle und historische Modul-/Installpräfixe aus ROBOT_TRANSFER und den erhaltenen Manifesten ermitteln, nicht aus Branch-Namen ableiten. Bestehende Builds und unbekannte lokale Änderungen nicht überschreiben. Die Abnahme eines neu kombinierten Kandidaten wird nicht aus historischen Einzeltests zusammengesetzt.

## 3. Offene Befunde bleiben erhalten

Der letzte vollständige Lauf hielt ein autonomes Frontierkind bis zum Kindtimeout; kein SOURCE_INVALIDATED und kein HWT-first_fault. Keine erledigte Aufgabe, keine Portalquerung, kein Regionwechsel. SlowZone gab 30 % aus; kleine Bewegungen reichten im Offline-Progress-Checker-Replay, nicht für Zielerreichung. Nicht mit externer Bewegungsvermessung gleichsetzen.

Softwareseitig blieb der Portalbestand in 327 Statusmeldungen leer; 296 Gegenproben fanden ebenfalls keinen Kandidaten. Der aktive Analysepfad verwendete 0,20 m statt der separaten historischen Analyse bis 0,40 m. Das ist ein Vergleichsbefund, kein bewiesener alleiniger Auslöser und kein Auftrag, Grenzen blind anzugleichen. Die konkrete physische Tür ist dem Datensatz weiterhin nicht eindeutig zugeordnet.

Die SlowZone-Punkte lagen räumlich auch in den Costmaps. Ein sicherer physischer Ausweg ist damit nicht bewiesen. Warum der reale Timeout zu SYSTEM_FAILURE statt möglicher lokaler Aufgabenrückstellung führte, ist mangels interner Erstentscheidung nicht abschließend rekonstruiert. Positive Offline-Snapshots ersetzen nicht den damaligen Callbackzustand. Abweichungen von Drehsoll/-rückmeldung, Objektidentität und Shutdownfehler bleiben offen, nicht als harmlose Nebeneffekte wegdefiniert.

Originalwerte, Szenarien, Tests und Messgrenzen: [voriger STATUS, Abschnitt 7](archive/20260930-v1.1/STATUS.md#7-nächster-schritt-und-historie). Vollständige lokale Auswertung: `~/.local/share/amadeus/tests/stage3-door-obstacle-offline-20260930/`. Private Rohdaten bleiben lokal.

## 4. Softwareabschluss und Nachweise

Basis: veröffentlichter `1dbbdaa`, unabhängiger Checkout der bestehenden Integrationslinie; kein privater lokaler Bericht als Vorfahr. Änderungen: `explore_node.py`, neue `metric_frontier.py` und `metric_frontier_runtime.py`, explizites Overlay `metric_frontier_params.yaml`, Regression `test_metric_frontier.py` und verbundener Graph `tools/sensorfusion/metric_frontier_product_graph.py`. Modus-/Schnittstellen-/Wiederverwendungszuordnung: [Explore-README](../../src/explore/README.md#explizite-metrische-strategie-masterplan-v12).

Wiederverwendet: tatsächliche Frontiercluster, sichere Annäherungsziele, geodätische Distanz, freie Rastersegmentprüfung und vorhandene Bewertungsgewichte; aktuelle Kartenidentität/Scope, Quellenbeobachter, Nav2-Einzelkind, Scan/Vorausrichtung, HOLD/Stillstand/Gate-ACK. Kein zweiter Navigator und kein semantischer Aufgabenbesitzer im metrischen Modus. Der gepaddete asymmetrische Fahrzeugumriss wird einschließlich Drehungen auf Rohkarte **und** Costmap geprüft. Unbekannte Zellen bleiben gesperrt.

**Build:** sechs Pakete (`explore`, `robot_navigation`, `robot_state_estimation`, `mission_manager`, `robot_map_manager`, `amadeus_map_identity`) isoliert unter `~/.local/share/amadeus/tests/metric-frontier-20260930/software-final/install`, ROS Humble plus dokumentiertem Vollunderlay. BT läuft aus `hwt-child-scope-20260928-retry/install`; Graph protokolliert alle aufgelösten Präfixe. Kein Install in der laufenden Arbeitskopie.

**Regression:** 1.342 pytest-Tests bestanden; zusätzlich registrierte colcon-Tests: 1.242, null Fehler/Failures/Skips. Neue metrische Regression: 21 Tests, unter anderem räumliche Retries, unbekannte/enge Wege, asymmetrischer Footprint, Scope-/Owner-/Budget-Ablehnung, verspätete Actionannahme und alte Karten. Reale ROS-Node-Tests erzwingen localhost und Domain 200–230 vor Initialisierung. Ausführung hier Domain 226, Graph Domain 224; konfigurierte DDS-Peers entfernt.

Ein Neustart der Ausführungsumgebung verlor die temporären `/tmp`-Artefakte und unterbrach den Abschlusslauf. Der Kandidat wurde am dauerhaften lokalen Testpfad erneut gebaut; maßgeblich sind dessen abschließende Logs, nicht verlorene Zwischenläufe.

Ein erster wiederholter HOLD-Reiz vor frischer wiederhergestellter Yaw-Messung endete korrekt an zusätzlicher ungültiger Quelle. Die Fixture wartet jetzt auf gemessene Wiederherstellung vor dem zweiten Rohdatenreiz; Originallauf bleibt unter `graph-hold-before-stable-fixture` erhalten. Produktgrenzen wurden dafür nicht geändert.

Der zusätzliche Rundblickfall legte einen vorzeitigen Abbruch am gemessenen `vl53_triplet_unmatched`-Publikationsfenster offen (`graph-scan-first` und `graph-scan-diagnostic`). Dieses Fenster wird jetzt wie in der Navigation vom echten Gate gesperrt, ohne das gesamte Scanverfahren sofort als Fehler zu beenden; tatsächlich stale/ungültige Quellen bleiben terminal. `scan_route` prüft eine echte Rohkartensperre während des Scans ohne Nav2-Kind.

Der erste korrigierte Scan lief mit einem festen 10-ms-Synthesetakt und 12-s-Testbudget in Timeout (`graph-scan-fixed-tick-model`). Die Fixture integriert jetzt tatsächliche verstrichene Zeit aus den gegateten synthetischen Ausgängen; 0,3-rad-Scanbudget 28 s ausschließlich im Test. Produktprofil weiterhin 360°/280 s. Das ist synthetische Modellbewegung, keine externe Vermessung des Roboters.

**Verbundener Produktgraph (16 Fälle bestanden):** Mission Manager → tatsächlicher BT → Explorer → Nav2-Testgegenstelle; tatsächlicher Kartenmanager, HWT-Shadow und Mission-Gate. Synthetisch sind Raster, physische Eingangsmeldungen und Nav2-Gegenstelle. Kein Zielkandidat, Portal, Region oder Taskgesundheitsadapter wird eingespeist. Lokale Belege `~/.local/share/amadeus/tests/metric-frontier-20260930/software-final/graph-<Fall>/result.json` und Prozesslogs; Szenen sind gerätefrei.

| Pflichtfall aus AGENTENAUFTRAG §4 | Ausgeführter Beleg |
|---|---|
| 1 Ohne Semantik | `chain`: autonome Auswahl ohne Pflichtfeeds; widersprüchlicher optionaler Shadowstatus wirkungslos |
| 2 Beobachtungsschleife/offene Verbindung | `chain`: drei erreichte Aufgaben aus veränderten Rastern im selben Elternauftrag; maximal ein Kind, Verbindung ohne Türlabel |
| 3 Unerreichte Aufgabe/Alternative | `blocked`: tatsächliche erste Policywahl abortiert; terminales Kind, frischer Stillstand und Betriebssnapshot, danach anderes Rasterziel |
| 4 Kriechen/Budget | `budget`: kleine synthetische Drehbewegungen mit tatsächlich publizierten Gyro-/Odomeldungen setzen absolute Aufgabenfrist nicht zurück; gesunder Zustand erlaubt begrenzte Alternative |
| 5 Laufende Karte | `chain` erhält gültiges Kind trotz Updates; `route` storniert bei ungültigem Weg, `scan_route` beendet unzulässigen Scan; Unit-Regression verhindert Übernahme alter Raster/anderer Karte |
| 6 HOLD/Cancel | `hold`: wiederholte kurze Quellenausfälle, unveränderte HOLD-Frist, Bewegung sperrt Resume, Stillstand/Gate-ACK erlauben neues Kind derselben Aufgabe; `late`, `cancel_failed` |
| 7 Harte Gegenfälle | `estop`, `sensor`, `actuator`, `pose`, `map`, Nutzerabbruch, nicht terminales Kind; Scope/Footprint/Budget zusätzlich Regression und `empty`/`filtered` |
| 8 Abschluss/Migration | `empty`: vollständig bekannt nur metrischer Abschlusskandidat/Teilstand; `filtered`: unbekannter Rest ohne Abschlusskandidat; überall keine Speicherfreigabe und kein Gesamt-/Semantikerfolg |

Der abschließende `chain`-Lauf erreichte die ersten drei Aufgaben und nahm vor dem kontrollierten Testende noch ein viertes Kind an; dieses wurde terminal gecancelt. Beispiel der ersten drei Aufgaben (ausschließlich synthetische Koordinaten): `(1.05, 0.05)` → gemessene Zielerreichung/neue Karte → `(2.55, 0.05)` durch rastergeprüfte offene Verbindung → neue Karte → `(4.05, 0.05)`. In `blocked` lautet die erste Entscheidung `task_unreached_cause_unproven`, **kein** erfundenes Hindernis und kein pauschaler Hardwaredefekt; erst nach gesundem terminalem Zustand folgt die andere Aufgabe. Budget über HOLD/Kindwechsel erhalten; Retry erst nach Cooldown, geänderter Kartenevidenz und verbleibenden Versuchen. `scan` prüft begrenzten Initialscan und anschließende Vorausrichtung im verbundenen Pfad; Scan/Vorausrichtung bleiben vorhandene Verfahren mit laufender Konturprüfung.

**Offline-Grenze:** Historischer Erfolgsdatensatz und aktueller Fehllauf wurden lokal nur lesend anhand je drei Raster-/Pose-Snapshots verglichen. Historisch: alte Kandidaten 15/7/11, neue konservativ zulässige 0/4/11; aktueller Fehllauf: 10/13/12 gegenüber 0/0/0. Häufig liegt bereits die tatsächliche Fahrzeugkontur nicht vollständig im bekannten freien Rohkartenraum; zusätzlich Route/Costmap. Der Vergleich verwendet für die reine Kandidatenanalyse einen Rastergrenzen-Scope und beweist weder aktuellen Betreiber-Scope noch Live-Quellengesundheit. Diese Grenze wurde nicht durch Lockerung behoben. Positive Synthetik ist kein Nachweis realer Befahrbarkeit. Private Bags/Karten und Analyseergebnisse bleiben außerhalb Git.

### Realnachweis am 30.09.2026: Vorlauf blockiert, keine Mission

Exakter Kandidat `deb075e3f1a51a46bc00c2235a3068cfbe45d769`, derselbe isolierte Sechspaketinstall, Produktbasisprofil plus lokal vervollständigtes metrisches Overlay über `explore_params_overlay`. Reale Domain 42; kein Aktorschreibprozess. Live-Parameter und 324 Explorer-Statusmeldungen belegen `metric_frontier`; alte WE-Policy/Navigation false. Session/Startkarten-Fingerprint und LAB-1-Scope aus aktueller Karte/Pose zugeordnet; keine historischen Raumkoordinaten oder Dummy-Feeds. Bootstrap-Explorer endete zunächst erwartungsgemäß am ungebundenen Scope; nach Bindung alleiniger metrischer Explorer idle.

**Quellen:** direkte FC03-Startmessung im Stillstand; später passives Gate mit 189,166 ms Radsamplealter > 180 ms. Einmaliger passiver Gate-Neustart nach Sensorstart, tatsächliche kurze Rohquellen-Recovery separat beobachtet. Danach realer Encoderreader terminal verriegelt: `encoderpaar_zeitfenster_ueberschritten`, FC03-Paar 125,870 ms > 120 ms (Einzelreads 91,760/33,809 ms). Ursache der Zeitüberschreitung nicht bewiesen; kein pauschaler Hardwaredefekt. Keine Grenze gelockert und kein Quellenstatus gefälscht.

**Geometrie:** aktuelle Startzelle unbekannt (`-1`); volle gepaddete Kontur in Rohkarte und Costmap unzulässig, bereits erste Scanorientierung verworfen. Snapshotanalyse mit installiertem Kandidaten: 25 reale Frontiercluster, alle `no_known_free_route`, 0 akzeptiert. Kein pauschaler Tür-/Freigabebefund. Darstellung mit Kontur/Scope lokal; keine Fahrspur/Ziel-/Passageereignisse erfunden. Bekannter LAB-1-Rahmen, aktuelles beobachtetes Rasterenvelope; unbekannte Zellen bleiben gesperrt.

| Realnachweiskriterium | Ergebnis und Grenze |
|---|---|
| A: drei autonome Beobachtungen und räumlicher Kartenfortschritt | **nicht bestanden**: 0 Missionen/0 Aufgaben; 1.603 Kartenmanager-Meldungen mit unverändertem Fingerprint |
| B: Zielmisserfolg und sichere Folgeaufgabe | **nicht aufgetreten**: kein Nav2-Kind; passive Quellen-Recovery ist kein Aufgabenfortsetzungsbeleg |
| C: vollständige Passage und Aufgabe dahinter | **nicht bestanden**: keine Fahrt, kein Passagebeleg oder Beobachterzuordnung |

Kein regulärer aktiver Wechsel, weil Vorlauf nicht bestanden; kein zweiter Fahrversuch. Budgets live geladen: 900 s gesamt, 150 s Aufgabe, 6 Versuche/3 Fehler, Initialscan 280 s/0,08 rad/s. Keine Mission begonnen, daher keine Budget-/Timeoutabnahme. Recorder bis Ende aktiv; SQLite erst nach Ende ausgewertet: keine running-Mission, keine Navigate-Statuseinträge, alle aufgezeichneten Befehle null. Geordnete SIGINTs ausschließlich an Launchwurzeln; alle manifestierten Prozesse beendet und Gerätehandles frei. Nach Stackende zwölf frische FC03-Paare, beide Motorpositionen unverändert und 0 rpm. Keine Shutdownfehler im Abschlusslog; Bootstrap-Exit und Laufverriegelung getrennt geführt.

Private Belege ausschließlich `~/.local/share/amadeus/tests/metric-frontier-real-20260930/`: Runtime-Manifest mit Präfixen/Profil-/Modulhashes, Liveparameter/-status, Quellen-/Geometriesnapshots, lokale Darstellung, geschlossene Bag-Auswertung, FC03-Endmessung und Shutdownprüfung. Keine privaten Karten/Bags/Berichts-Vorfahren veröffentlicht. Softwareerfolg bleibt erhalten; kein Stufe-3-Gesamtgrün.

**Damals nächster Schritt, im folgenden Abschnitt ausgeführt:** gezielter Vorlauf-Korrekturauftrag für Startkarten-/Kontur- und FC03-Paarzeitblocker mit getrennten Nachweisen und unveränderten Schutzgrenzen. Aktuelle Voraussetzung ausschließlich im Abschluss vom 01.10.2026.

### Historisch bis cf55cea: Mast-/Eigenkörpervertrag und Encoderzeitpfad

Auftrag vom 30.09. auf veröffentlichtem `0efb7e4`, funktionaler Abschluss
`8be0709` in derselben PR-#105-Linie. **Softwarekorrekturen regressiert;
gemeinsamer realer Vorlauf negativ. Keine Mission und kein Fahrnachweis.**

**Mast:** Betreiberzuordnung OAK-Kameramast verbindlich übernommen. Vorhandene
native Maske 236–304°, NaN-Ausgabe und ROS-CCW bleiben unverändert. Im letzten
Vorlauf: 2.325 Rohscans / 2.287 normierte Scans; im robusten Sektorinneren
57–123° sind sämtliche 924.632 / 905.652 Bins NaN. Die 1° Randreserve dient
nur dieser Auswertung unterschiedlich diskretisierter Scans, verändert keinen
Filter. Tatsächlicher statischer TF aus der Bag: x 0,245, y 0, z 0,660 m,
yaw +1,5708. Manifest belegt Crop=true und tatsächlich gestartete Parameterdatei.
Der native Treiber beantwortete den Parameterdump nicht; deshalb kein erfundener
Live-Parameterbeleg. `/scan` → vorhandene Vereinheitlichung → `/scan_normiert`
→ SLAM/Explorer/HWT-Beobachter/Gate; Costmaps nutzen Rohkarte und ihre vorhandenen
VL53/OAK-Quellen. SLAM-Präfix `~/amadeus_slam_toolbox_ws/install/slam_toolbox`,
Patchparameter live true; installierte `libtoolbox_common.so` enthält den Patch.
Keine neue Drehfahrt oder Kalibrierung daraus ableiten.

**Startkorrektur:** `metric_self_body_enabled` erlaubt privat nur ganze unbekannte
Zellen im ungepaddeten gemessenen Körper x −0,11..0,31 / y ±0,23 m, einschließlich
Zellenecken und Scopeprüfung. Erste korrelierte Pose und Rohkarten-Fingerprint
fixieren den Beleg; er folgt keiner Bewegung und erlischt bei geändertem
Fingerprint. Frische Pose/Scan und passender planarer Montage-TF bleiben Pflicht.
Belegte Zellen, Costmap-Unknown, Außenkeil, Padding und Rasterreserve werden nicht
freigegeben. Rohkarte bleibt bytegleich; volle Kontur x −0,13..0,33 / y ±0,25 m
und ihr Bewegungs-/Drehsweep bleiben geprüft. Keine Garantie für einen Rundblick
allein aus belegtem Eigenkörper.

Der alte Startsnapshot bleibt reproduziert: unbekannte Startzelle, unzulässige
Kontur und 25 `no_known_free_route`. Bei 325 berührten Zellen: 88 ganz im Körper
liegende unbekannte Zellen, 4 Randzellen mit Körperüberschneidung, 16 im Padding,
18 in Rasterreserve; 0 Rohkartenhindernisse. Alte Costmap: 1 unbekannte Zelle in
Rasterreserve, 143 Inflationszellen, 0 Zellen mit Wert ≥100. Rasterkosten beweisen
keine bestimmte physische Objektidentität. Der neue Startsnapshot zeigt 78 ganze
Körperzellen, 16 Körperrand-, 16 Padding- und 18 Reservezellen weiter unbekannt;
Costmap 2 unbekannte Reservezellen, keine Kosten >0 in der berührten Kontur.
Die ganzen Körperzellen werden korrekt getrennt; der unzulässige Außenanteil
bleibt wirksam. Startzentrum nach Clearanceprüfung false, volle Roh-/Costkontur
false, bereits erste Scanorientierung false. 15 reale Cluster, 15
`no_known_free_route`, 0 akzeptiert. Keine freie 360°-Drehung nachgewiesen.

**Encoderkorrektur:** gemeinsame FC03-Blöcke Position/RPM erhalten. Instrumentiert
sind Alias/USB vor/nach Zugriff, Modbus, Antwortprüfung, Paar, Motorversatz,
Pollstart und Publikationsalter. Nur USB-Attributpfadsuche gespeichert; tatsächliche
Identität/tty-Gerätegeneration, Alias und Exklusivität vor/nach jeder Probe sowie
CRC/Antwortprüfung bleiben aktiv. Paarzeit 120 ms und Datenlücke 180 ms unverändert.
Nach ≥20 gesunden Paaren darf ein einzelnes vollständiges Timingpaar bei belegter
Kontinuität verworfen werden: Quelle unbereit, Transport weiter lesend, zwei neue
vollständige plausible Paare. Erstes gültiges Paar integriert sämtliche Zähler
und publiziert weiter unbereit; zweites stellt Readerbereitschaft wieder her.
Passives HWT geht dabei in den vorhandenen HOLD/Validierungsvertrag. Keine
Faultflag-Löschung, Pose-/Baseline-Nullung oder unterschlagene Bewegung.
Anhaltende Verzögerung, lange Lücke, unvollständige Antwort, Portwechsel/-verlust,
unplausible Zähler, Zeitrücklauf und harte Schutzfälle bleiben gesperrt.

Erster Vollstackstart vor der dritten Probe: Pollstart 197,695 ms, Paarzeit
97,920 ms. Terminal, `rebases=0`; keine automatische Heilung einer langen Lücke.
Passiver Readerstart nun 15 s nach den übrigen Starts; vor echten Proben bleibt
Fusion unbereit. Nur Startstaffelung, keine Messzeit-/Grenzverschiebung. Spätere
Verbraucherbeobachtung: frische aufgezeichnete Radprobe vorhanden, während Gate
189,800 ms alte Probe auswertete. Passive HWT-Quellen erhalten aktuelle DDS-Proben
und im Gate eine eigene serielle Callbackgruppe/zweiten Thread; gewöhnliche
Gate-/Not-Aus-/Befehlscallbacks bleiben seriell. Aktiver Basistreiber und aktiver
Gate-Quellenpfad unverändert und separat regressiert.

**Zeitmessung, Millisekunden (Median / p95 / p99 / Maximum):**

| Größe | Allein, 1.200 Paare | Letzter Vollstack, 4.284 Paare |
|---|---:|---:|
| Paar | 13,361 / 15,172 / 16,143 / 18,277 | 18,488 / 37,703 / 52,857 / 87,120 |
| Motorzeitversatz | 6,646 / 7,510 / 8,028 / 9,113 | 9,151 / 18,769 / 25,753 / 43,865 |
| USB/Alias vor Zugriff, je Motor | 0,719 / 1,463 / 1,858 / 4,276 | 1,093 / 4,133 / 10,838 / 33,057 |
| USB/Alias nach Zugriff, je Motor | 0,737 / 1,166 / 1,420 / 3,209 | 1,129 / 4,519 / 10,273 / 45,216 |
| Modbus, je Motor | 4,820 / 5,371 / 5,743 / 9,018 | 6,103 / 13,849 / 20,972 / 36,871 |
| Antwortprüfung, je Motor | 0,019 / 0,034 / 0,046 / 0,365 | 0,035 / 0,047 / 0,203 / 12,365 |
| Pollstartabstand | Standalone-Steuerintervall 50 ms, kein ROS-Publikationsbeleg | 50,000 / 57,173 / 72,622 / 132,552 |
| Publikationsalter ab echtem Paarmittelpunkt | Standalone publiziert nicht | 12,501 / 28,419 / 38,209 / 61,293 |

Je-Motor-Verteilungen haben n=2.400 bzw. 8.568. Null Paarüberschreitungen >120 ms
in beiden Reihen; im letzten Reader null Mittelpunktlücken oder beobachtete
Publikationsalter >180 ms. Keine kausale Last-/Kabelbehauptung aus diesen Maxima.
Voroptimierung ebenfalls 1.200 Alleinpaare: Median 14,020 / p95 16,027 / p99
17,868 / max 21,798 ms. Kein kontrollierter alleiniger Ursachenbeweis.
Zwei erhaltene ältere Vollstackreihen: 12.003 bzw. 3.360 Paare, ebenfalls keine
120-ms-Überschreitung; ihre Gateverriegelungen sind keine Reader-Paarfehler.

**Regression/Build:** acht Projektpakete isoliert, zwei betroffene Pakete nach
Gatekorrektur erneut gebaut; Quelle/Install bytegleich, kein Hauptinstallwechsel.
1.340 abschließende pytest-Tests bestanden, einschließlich aktivem Basistreiber,
passivem Kontinuitäts-/Recoveryvertrag, Not-Aus/Bewegungs-/HOLD-Gegenfällen und
Launch-Besitzprüfung einschließlich verzögertem Reader. Neue echte DDS-Regression
blockiert normalen Callback 350 ms: frische Quellen laufen weiter; tatsächlich
fehlende Radquelle >180 ms bleibt terminal. Ohne eigene Quellengruppe scheitert
die positive Gegenkontrolle erwartungsgemäß an unverändertem Radstempel.
Versetzter LiDAR/Mast, zulässiger Start und Nachbarhindernis/unbekannter
Schwenkraum/falscher TF/ungültige Pose getrennt regressiert. Verbundener
`mast_start`: drei synthetische Aufgaben erreicht, viertes Kind terminal
gecancelt, maximal ein Kind. Das ersetzt keinen realen Bewegungsbeleg.

**Gemeinsames reales Ergebnis:** erster korrigierter Quellenvorlauf 20 s gesund,
später Gate terminal an Radquellenalter; nächste Messung ohne Rendering ebenfalls
nicht durchgängig gesund. Nach gezielter passiver Callbackkorrektur im letzten
Vorlauf reale HWT-Kurzstörung → HOLD → Validierung → HEALTHY, danach weiterhin
terminal `wheel_missing_stale_or_invalid`. Reader selbst bis Ende ready,
4.284 vollständige Paare, keine FC03-Fehler/Reconnects/Recoveryausreißer/Rebases.
Der erste Fehler-Snapshot bleibt die frühere HWT-Störung; er ist kein numerischer
Snapshot der späteren terminalen Radentscheidung. Deren exaktes Verbraucher-
alter/Ursache wird nicht aus dem Bag oder späteren guten Paaren erfunden.
Die Callbackkorrektur behebt den gezielt regressierten seriellen Stau, beweist
aber **keine vollständige Beseitigung realer Verbraucherfrischefehler**.
Geometrie unabhängig davon weiterhin unzulässig. Deshalb kein aktiver Wechsel,
0 Missionen/0 Nav2-Kinder; A/B/C unverändert offen. Budgets 900/150 s, 6/3 live
belegt, nicht als ausgeführte Missionsabnahme gewertet. Alle vier Befehlsströme
null; Encoderpositionen/RPM unverändert null, Odom-v null. Alle manifestierten
Prozesse und Gerätebesitzer beendet; anschließend 12 frische Paare beider Motoren
mit 0 rpm/Position 0. Bootstrap-Scope-Exit getrennt, keine Shutdownfehler.

**Historische Voraussetzung bis cf55cea; durch den folgenden Abschluss konkretisiert:** ein
**gleichzeitig gültiger gemeinsamer Startnachweis**: vollständige gepaddete
Start-/Schwenkgeometrie samt zulässigem Rasterweg sensorisch belegt und tatsächliche
Quellen bis zum Verbraucher innerhalb ihrer unveränderten Frischegrenzen, ohne
terminale Verriegelung. Dieser eine Startvertrag ist aktuell an beiden getrennt
benannten Prädikaten ungültig; die Befunde dürfen nicht zu einem einzigen
angeblich behobenen Fehler zusammengezogen werden. Keine identische Wiederholung
oder erzwungene Bewegung ohne neue Geometrie-/Zeitbezugsevidenz.

Private Messungen/Scans/Karten/Bags/Manifeste ausschließlich unter
`~/.local/share/amadeus/tests/metric-start-encoder-20260930/`, Abschluss in
`common-gatefix/`. Keine Raumdaten oder private Berichts-Vorfahren veröffentlicht.
Rückfall: ohne Mission geordnet beenden, temporäres letztes Overlay weglassen;
Eigenkörperoption abwählen. Bei Kontinuitätsverlust neue belegte stationäre
Initialisierung mit neuem Karten-/Odometriebezug, kein Latch-Reset. Kein Merge,
kein permanenter Installwechsel und kein Stufe-3-Gesamtgrün.

### 01.10.2026 – Entscheider und reale Anfangsgeometrie, begrenztes Paket beendet

**Radpfad:** Eigener atomarer Snapshot je STARTUP-/HOLD-/Terminalübergang mit
Ereigniskennung, Zustand vorher/nachher, Originalnachricht (Header sec/ns,
Frames, Pose/Quaternion, Twist und beide Kovarianzen), tatsächlichem
Consumer-/Callbackeintritt, ROS-/Monotonic-Bracket, Mess-/Empfangsalter,
Grenze, erstem Prädikat und vorheriger erfolgreicher Recovery. Historisches
`first_fault` bleibt erhalten. Fehlend, ungültig und stale getrennt;
ältere Callbackübernahme ersetzt keine neuere Probe. Gate entscheidet einmal
unter dem bestehenden Quellenlock; bounded/latest Diagnose-JSON und DDS-Ausgabe
laufen separat, Stopptimer weiterhin 20 Hz. Ein vor der ROS-Uhrabfrage
präemptierter Callback wird nicht zusätzlich als Messalter gezählt;
Integer-ns-Differenz und konservativer gepaarter Monotonic-Bezug statt alter
Eintrittszeit. Dieser kontrollierte Uhrtest ist kein rückwirkender Beweis
für sämtliche historischen Radfehler.

Zweiter aktueller Realvorlauf: gültige Probe, 215,948 ms Messalter >180 ms,
162,131 ms seit Callback, drei neuere Originalmessungen vor Entscheidung im
Recorder. Reader fehlerfrei, Paarmaximum 93,291 ms. Recorderempfang ist kein
Gatecallback. Separate passive Radgruppe/dritter Thread allein reicht real
nicht: dritter Vorlauf 186,344 ms, neuere Probe mit 69,822 ms Messalter bereits
21,973 ms vorher im Recorder. Danach zusätzlich echte 170,104-ms-Paarverletzung.
Die nachgewiesene Empfangs-/Schedulinglücke wird am vorhandenen Gate geschlossen:
vor passiver Entscheidung nichtblockierender Take aus derselben zuverlässigen
Depth-1-DDS-Subscription unter ihrem Callbackgruppenschutz. Kein zweiter
Subscriber, Quellenpublisher oder Busbesitzer; Originalstempel unverändert.
Eine bereits laufende Subscription wird nicht verdrängt. Receive-Exception
macht die alte Probe ungültig, statt sie gesund weiterzuverwenden. Normaler
Befehl/Not-Aus bleibt seriell; aktive Quellen weiterhin bestehender serieller
Executor/QoS und separat regressiert.

**Reader:** Im ersten aktuellen Start war eine reale 129,184-ms-Paarverletzung
überwiegend in Alias-/USB-Prüfung gemessen (106,350 ms). Voller `/dev`-Pfadwalk
nun nur zur Bindung; beide Aliaslinks, tatsächliche Gerätegenerationen und
alle USB-Identitätswerte weiter vor/nach jeder FC03-Probe prüfen. Weder
120-ms-Paargrenze noch 180-ms-Kontinuität oder Recoverybedingungen gelockert.
1.200 korrigierte Alleinpaare: Median 13,895 / p95 16,593 / p99 19,135 /
Maximum 23,420 ms. Unterschiedliche Lastbedingungen sind kein alleiniger
Kausalvergleich. Die Optimierung garantiert keine reale Echtzeitdeadline.

**Geometrie:** Zellprojektion auf den tatsächlichen Körper durch
res/2·(|cos Δyaw|+|sin Δyaw|) statt immer res/√2. Bei einem erhaltenen aktuellen
Start 78→92 ganze Körperzellen; alle vier Ecken der 14 zusätzlich zugelassenen
Zellen wirklich innerhalb des unveränderten ungepaddeten Körpers. Erste
Anfangsablehnung 50→36 und volle Rundblickablehnung 231→217; körperfremder
Flächenanteil unverändert. Vorheriger C3-Start 78→78, keine rückwirkende Heilung.
Kein Rohkartenwechsel, keine partielle Zellenfreigabe, kein mitbewegter Beleg.
Frischer Scan, der während Kartenarbeit ankommt, wird gegen danach erfasste
Zeit geprüft; echtes Stale/Future/fehlender Scan weiter abgewiesen.

Finale Karte/Pose im selben letzten Vollstack gebunden: 92 unbekannte ganze
Körperzellen privat korrekt behandelt. Anfangskontur weiterhin 36 unbekannte
Zellen: 18 teilweise Körperrand, 1 Padding, 17 Reserve; Außenanteil
0,030920 m². Voller 360°-Sweep: 211 abgewiesene Zellen (18 Rand, 1 Padding,
192 Reserve/zusätzlicher Schwenkraum), Außenanteil **0,188420 m²**.
Dies ist die konservativ benötigte Rasterbeobachtung abzüglich exakter
Körperüberlappung, nicht eine vermeintlich exakte feste Fahrzeug-Sweepfläche.
Costmap: Anfang 2 unbekannte Zellen; volle Drehung 139 unbekannte Zellen /
0,125100 m², vollständig in obiger Rohkartenzellmenge. Flächen nicht addieren.
Keine Rohhindernisse oder Inflationskosten in diesem Beleg. Zentrum nach
Clearance 0,120 m < erforderlichen 0,295 m unzulässig, 0 sichere Kandidaten;
erstes Produktprädikat `initial_scan_footprint_invalid`. Ganze 360°-Kontur,
Vorausrichtungs-/Routenwahl und Costmap werden nicht durch eine freigegebene
Mittelpunktzelle ersetzt. Volle reale Kontur/Padding/Reserve unverändert.

**Regressionen und Grenzen:** Isolierter ursprünglicher Vierpaketbuild plus
abschließendes Zweipaketoverlay bestanden und Quelldateien bytegleich geprüft.
1.469 pytest inklusive A–D, aktiv/passiv, Reihenfolge, wartende echte DDS-Probe,
Receive-Exception, Not-Aus/HOLD/Stillstand/Einzelkind. Gerätefreier verbundener
`mast_start_scan` besteht: versetzter LiDAR/Mast-NaN, volle 360°-Konturzulassung,
bestehender 0,3-rad-Testscan, Vorausrichtung, drei autonome Beobachtungen,
viertes Kind gecancelt, maximal ein Kind. Kein voller physischer Rundblick
behauptet. Zusätzliche vollständige 2π-Dauerprobe nicht bestanden:
`initial_scan_no_progress`, gemessene synthetische Quellengaps bis 460,796 ms.
Diese erhaltene negative Probe wird nicht in die positiven Softwarebelege
umbenannt. Keine entsprechende reale Bewegungsprobe ausgeführt.

**Gemeinsamer Realvorlauf:** Vier klar begrenzte, jeweils nach neuer Evidenz
korrigierte Fenster, jeweils 720 s ab Launchwurzel, kein Gate-/Reader-Neustart
oder Latch-Reset innerhalb eines Fensters. Letzter Kandidat `8f5eeb4`, Sources
zuerst nach 33,328 s bereit; zwei reale HWT-HOLDs mit erfolgreicher Validierung.
Danach etwa 197,9 s: Wheelmessalter 212,127 ms, tatsächlicher Consumerabstand
165,445 ms, gültiger Inhalt, `measurement_age_out_of_bounds`. Historische erste
HWT-Störung und letzte Wheelentscheidung haben eigene Originalsnapshots;
vorherige erfolgreiche Recovery steht im Wheelereignis. Beim Reader:
3.552 akzeptierte Paare (Maximum 99,431 ms); letztes 64,649 ms,
folgendes verworfenes Paar **120,874 ms**,
kein Rebase/Reconnect, keine aktuelle zulässige Ersatzprobe. Geschlossener Bag:
keine neuere Radnachricht um den Entscheid; erster verriegelter Readerstatus
bereits 7,975 ms vor dessen gepaartem ROS-Zeitbezug im Recorder. Das ist ein neuer
echter Transport-/Deadlinegegenfall; keine alte Probe frisch bewerten.
Der spätere Status `ready=false` bleibt erhalten. Gesamtes Fenster negativ,
geometrisch zugleich unzulässig. Kein aktiver Buswechsel, 0 Missionen,
0 Nav2-Kinder; 900/150 s und 6/3 live geladen, keine Budgets gestartet/reset.

**Damals konkreter Restumfang (durch den folgenden Auftrag präzisiert):** Der aktuelle FC03-Pfad muss unter echter Vollstacklast
wieder zulässige Paare innerhalb 120 ms und lückenlos innerhalb 180 ms liefern.
Im letzten Paar sind 71,797 ms Alias/USB-Nachprüfung und 46,840 ms Modbus
beobachtet; aus diesen wall-clock-Phasen allein keine Kabel-/Encoder-/Kernel-
Ursache erfinden. Weitergehende Transport-/Runtime-Latenzabsicherung ist ein
separat zu begrenzender Umsetzungsschritt; dieses Paket startet keine weitere
Reparatur-/Vorlaufserie. Geometrisch genau eine notwendige äußere Handlung:
die private Liste der 211 Außen-/Schwenkzellen mit dem vorhandenen LiDAR von
einer separat hergestellten stationären Beobachtungsposition aufnehmen und
Karte/Pose neu gültig zuordnen. Dafür nötiges manuelles Umsetzen bei deaktivierten
Antrieben durch die anwesende Person liegt außerhalb dieses Softwarepakets.
Stationärer Mast-NaN-Blick und vorhandene OAK/VL53-Vorwärtssicht belegen diesen
gesamten rückwärtigen Bereich nicht. Keine allgemeine Platzfrage, Karten-
freigabe oder autonome Bewegung zur Umgehung.

Alle zugehörigen Wurzeln geordnet einzeln per SIGINT beendet, Gerätehandles frei,
abschließend 12 frische FC03-Paare beider Motoren: Position/RPM null. Elektrische
Motorstromfreiheit wurde daraus nicht behauptet. Befehlsströme und Shutdown-
Details im geschlossenen lokalen Bericht. Ungebundener Bootstrap-Explorer
beendet sich erwartungsgemäß mit Scope-/Sitzungsfehler (Exit 1); anschließend
gebundener Explorer regulär, kein Fehler beim geordneten Shutdown.
Private Messdaten, Zellkoordinaten,
Karten, Bags und Manifeste unter `~/.local/share/amadeus/tests/metric-gate-start-20261001/`,
finaler Lauf `decision-take-common/`, Runtime `final-runtime-env.sh`,
`final-build-identity.json` und `end-state-proof.json`. Keine privaten
Berichts-Vorfahren, Merge, Force-Push oder permanenter Installwechsel.
Rückfall: ohne Mission geordnet stoppen, beide temporären Overlays weglassen,
`active_drive=false`, `enable_auto_explore=false`. **Stufe 3 bleibt offen.**

### Historischer Abschluss: adaptiver Start und begrenzte Encoder-Recovery (01.10.2026)

Ausgang `d9894d268262f7f8e965f2f92aef72021df3245e`, Funktionskandidat
`fd883fdf35e004dff6b209fffff9118c71161cd3`, derselbe Branch/PR #105.
Getrennte Funktionscommits: `a8aa3f3` Encoder/aktive Basis/Fusion/Gate,
`b36d412` adaptiver Start/Controllergeometrie, `fd883fd` typgerechte
Controllerklassen in der Graphfixture. Keine privaten Berichts-Vorfahren.

**Wirksamer Produktvertrag:** `exploration_strategy` bleibt standardmäßig
`existing`; metrisches Profil explizit `metric_frontier`, dessen unveränderlicher
Startparameter `metric_start_strategy=adaptive`. `initial_scan_enabled=true`
bleibt geladen. Ein zulässiger nützlicher Vollrundblick bleibt verfügbar; fehlt
seine Fläche, wird ein echtes Frontier-/Annäherungsziel gesucht. Fehlt schon
die sichere Anfangskontur oder jedes Ziel, folgt ein begründeter Teilstand.
Kein Pflichtscan für eine andere Bewegung, kein festes Fahrziel, kein neuer
Goal-Sender oder Supervisor. Bootstrap/HOLD zählen in 900/150 s und 6/3 hinein.

Vor vorhandener Nav2-Ausführung tatsächlichen `ComputePathToPose`-Plan und
13 Liveparameter von RPP/Goalchecker prüfen: genau `FollowPath`/RPP und
`general_goal_checker`/SimpleGoalChecker; Rotation true, Winkel 0,35 rad,
Lookahead 0,40 m, Geschwindigkeitsskalierung/Rückwärtsfahrt false,
Kollisionsprüfung/Interpolation true, XY-Toleranz 0,15 m/Yaw 0,40 rad.
Vorausrichtung, Controllerkorrektur, interpolierter Carrot/Kurvenraum, gesamte
Route und Zielrotation einschließlich XY-Toleranzdisk reservieren. Ungedeckter
weiter Carrot aus zu dünnem Plan wird verworfen; vorhandene Reserven bleiben.
Die zusätzliche Kurvenreserve ist abgeleitet, kein verkleinerter Footprint.
Startkörperbeleg bleibt im ursprünglichen Raum; harmlose Rasterupdates können
ihn nur verkleinern. Änderungen von Kontext/Raster/Karten-Odometriebezug lassen
ihn verfallen. Keine mitfahrende Freiraumblase, kein Überschreiben von Hindernissen.
Mastmaske, NaN-Semantik und Montage-TF erhalten.

**Encodervertrag:** gemeinsamer Core für passiven Reader und aktive HWT-Basis;
120 ms Paarvalidität und 180 ms Bewegungsfrische/Kontinuität unverändert.
Nach gesundem Vorlauf darf bei intakter Identität begrenzt diagnostisch weiter-
gelesen werden: maximal 2 s / zwei Versuche je Readerlebensdauer. Verworfenes
Paar bleibt unveröffentlicht, Stillstand/HOLD sofort. Neue gültige Paare können
nur bei belegter Kontinuität alle Zählerdifferenzen erhalten; keine Rebase,
Pose-Nullung oder Reconnect-Reparatur. Echte >180-ms-Lücke bleibt unbewiesen,
auch bei späteren 0 RPM/zwei guten Paaren. Verbraucher zusätzlich höchstens
5 s / zwei Wiederherstellungen je Quellenklasse HWT bzw. Rad, ohne Reset durch
Kindwechsel. Gültige Originalstempel, Stillstand, Fusion/Karte/Route, terminales
altes Kind und Gate-ACK vor Resume. Port/Identität/Zähler/Zeit/ESTOP/Cancel
und Aktuatorfehler bleiben hart. Details: [Encodervertrag](../ENCODER_ODOMETRIE_FIX.md)
und [Explore-README](../../src/explore/README.md).

**Alter echter Fehler exakt reproduziert:** native Paardauer 120,874265 ms,
letzte zulässige Radprobe am Gate 212,127149 ms. Erstgrund im ursprünglichen
Reader `encoderpaar_zeitfenster_ueberschritten`; keine wartende zulässige Probe.
Neuer Reader verwirft das Paar; danach >180 ms macht Kontinuität unbewiesen,
2-s-Endgrund `encoder_timing_continuity_unproven`. Historisch nicht aufgezeichnete
verworfene Zähler wurden im Replay mit null gegengetestet: sogar das heilt die
Zeitlücke nicht, beweist aber keinen historischen Stillstand. Kein rückwirkendes
Umdeuten der damaligen Sperre.

**Software und verbundene Nachweise:** 1.493 Regressionen bestanden, isolierter
Fünfpaketbuild erfolgreich. Zehn geänderte Laufzeitartefakte bytegleich mit dem
tatsächlich aufgelösten Install. MM, BT, Explorer, Kartenmanager, HWT-Shadow und
Gate tatsächlich ausgeführt; synthetisch sind Sensor-/Rastereingänge und
Nav2-Gegenstelle. Keine erfundenen Ziele/Gesundheitsadapter. Reale Zeitlücken
bleiben Zeitlücken, kein Fresh-Restamping. Unterschiedliche Graphfälle nicht
zu einer bestandenen durchgehenden Vollrundblickfahrt zusammensetzen.

| Pflichtfall | Ergebnis und Grenze |
|---|---|
| A adaptive Beobachtungsschleife | `adaptive_loop`: drei selbst berechnete Ziele, neue Rasterevidenz, offene Verbindung/weitere Ziele, 60,38 s im selben Elternauftrag, maximal ein Kind. Scanverfügbarkeit in diesem Loop-Test explizit false. Separater Fall unten prüft den tatsächlich eingeschalteten Scan. |
| A/B Scan optional, später zulässig | `adaptive_admission` mit `initial_scan_enabled=true` und voller 2π-Anforderung: rückwärtiger Schatten sperrt Scan; anderes berechnetes Ziel wird ausgeführt; erst neue Karte erlaubt Scan. Danach bewusster Testabbruch, **kein bestandener Vollscan**. Nach letzter Parametertypkorrektur erneut bestanden. |
| C keine sichere Erstbewegung | `adaptive_wait`: null Kinder und ausschließlich Nullbefehle bei unbekannter Startreserve; Vorausrichtung/seitliches Hindernis/Controller-/Zieltoleranz zusätzlich regressiert. |
| D/F Timing-HOLD und HWT davor | `encoder_hold`: tatsächlicher Core verwirft 120,874-ms-Paar bei noch belegter kurzer Kontinuität; HWT-Recovery zuvor separat; neuer gültiger Stillstand/Fusion/ACK, höchstens ein Kind; getrennte Originalereignisse am Explorer und Gate. |
| E echte Lücke | `encoder_gap` und Readerregression: >180 ms, spätere gute Paare/0 RPM ohne Rebase oder Weiterfahrt; begrenzte Diagnose endet gesperrt. |
| G harte Gegenfälle/Budget | `encoder_persistent`, `encoder_no_stop`, `encoder_estop`, `encoder_cancel`, `encoder_budget`, `cancel_failed`, `estop`: keine unerlaubte Fortsetzung; dritter Radfehler nach zwei Recoveries terminal. Aktiver Basisadapter/Identität/Uhrrücklauf/Zähler separat regressiert. |
| H Karten-/Körperbeleg | `route`, `mast_start`, `chain` sowie Körper-/Kontextregression: gültige Updates erhalten Aufgaben; neues Hindernis stoppt; alter Körperbeleg kann weder wandern noch neue Sperren freigeben. |

Sechs geometrie-/Controllerbetroffene Graphfälle nach finaler Kurven- und
Zielreserve erneut bestanden, zusätzlich typgerechte 13-Parameterprüfung und
Budgetfall. Lokales Nachweisregister `metric-adaptive-start-20261001/` mit
`regressions-publish-final.log`, `graph-controller-final-summary.json`,
`graph-suite-summary.json` und einzelnen `result.json`/Prozesslogs.

Nach Veröffentlichung erkannte Offline-CI einen ROS-Import im neuen aktiven
Adaptertest. Nur dessen Sammlung und die ROS-Uhrprüfung bei fehlendem `rclpy`
ausnehmen; vollständige Coretests bleiben offline aktiv. Nachweis in isolierter
Umgebung ohne ROS: 118 bestanden, zwei ROS-Abhängigkeitsskips, 63 Subtests;
zwölf Inbetriebnahmewerkzeugtests bestanden. Dieselben drei ROS-abhängigen
Adapter-/Uhrfälle mit echter ROS-Installation erneut bestanden. Produktbytes
des real geprüften Kandidaten bleiben unverändert, kein neuer Realstart.

**Volle Dauerprobe bleibt negativ:** historische 2π-Probe erhalten. Auch neuer
`graph-adaptive_start-final` nach 259,27 s negativ: Vollscan erst nach tatsächlich
erledigter erster Beobachtung zugelassen, dann Quellenpausen (größte rohe
Publikationslücke 515,70 ms), zwei HWT-Recoveries, absolute 150-s-Scanfrist
erschöpft; anschließend `post_child_state_or_standstill_unconfirmed` mit
`hwt_recovery_attempt_limit`. Gemessene synthetische Gesamt-Yaw 11,825 rad über
Unterbrechungen ist kein belegter abgeschlossener 2π-Scan. Diese Probe entstand
vor der zusätzlichen Kurven-/Zielreserve; die späteren positiven Kurzfälle
ersetzen ihre Laufzeit-/Quellengrenze nicht. Frühere negative Fixture-/Last-/
Geometrieversuche ebenfalls erhalten. Kein Vollrundblick-/Robustheitsgrün.

**Ein gemeinsamer realer Vorlauf:** derselbe isoliert kopiert gebaute Kandidat,
reale Domain 42, `active_drive=false`, passiver FC03-Reader als einziger
Basisbusbesitzer. Vorab FC03-Nullposition/-RPM und freie Handles geprüft.
Ungebundener Bootstrap endet erwartungsgemäß am Scope; im selben Stackfenster
Session/LAB-1-Scope an tatsächliche Karte/Pose gebunden und einziger gebundener
Explorer idle. Laufzeitpräfixe, Prozessbaum, geladene Parameterdateien, Modul-
und native RPP-Bibliothekshashes sowie alle 13 Controllerparameter manifestiert.
Tatsächliches metrisches/adaptives Profil, Scan weiterhin true, 900/150 s und
6/3 live; SLAM `check_min_dist_and_heading_precisely=true`.

Vorab festgelegtes Messfenster **720 s ab Launchwurzel**, gemessen 720,016 s.
Erstmals alle Vorlaufbedingungen außer Bewegungsgeometrie nach 35,858 s.
Am tatsächlichen Gate: HWT-HOLD nach 162,718 s → HEALTHY nach 164,263 s;
zweiter HOLD 401,729 s → HEALTHY 403,212 s. Dritte HWT-Störung nach 583,261 s
terminal `hwt_recovery_attempt_limit`. Eigener Originalzustand: Rawdriver
`ready=false`, `raw_data_ready=false`, `consecutive_errors=1`,
`Zeitueberschreitung nach 0/14 Bytes`; Rawalter dabei erst 37,327 ms.
Also echter Readiness-/Budgetgegenfall, keine erfundene stale-Wheelursache.
First-Fault und zweite erfolgreiche Recovery im späteren Fehler erhalten.
Keine bewiesene Hardware-/Kabel-/Kernelursache daraus ableiten.

Encoder am 720-s-Ende: **13.921 vollständige Paare**, null Timing-Recovery/
Rejects/Rebases/Reconnects, ursprünglicher Baselinezähler eins, Kontinuität
gültig. Größte diagnostizierte Paardauer 108,118 ms, unter 120 ms. Der aktuelle
Realfall ist **kein realer Encoder-Recovery-Nachweis**; dieser ist softwareseitig
verbunden geprüft. Gesundes Rad heilt keine terminale HWT-/Fusionquelle.

Aktuelle frühe und späte Geometrie unabhängig von Quellen negativ:
**33 unbekannte Startkonturzellen**, davon 16 teilweise Körperzellen und
17 Paddingzellen. Ganze Körperzellen privat 79; Außenanteil spät **0,021089 m²**
(früh 0,021069 m²). Eine unbekannte Costmap-Paddingzelle vollständig in dieser
Rohmenge; Flächen nicht addieren. Erster Produktgrund
`initial_contour_unknown_or_occupied`, **null adaptive Kandidaten**. Kein
unbenutzter Vollsweep als Gate: dennoch bleibt die beanspruchte Anfangskontur
unbelegt. Vollsweep nur Diagnose: 220 unbekannte Zellen / 0,189389 m²,
134 Costmap-Zellen vollständig darin. Letzter historischer Referenzfall bleibt
separat 36 Start-/211 Sweepzellen; weder manuelles Umsetzen noch Vorkartieren
wurde als positiver Bootstrap verwendet. Spätaufnahme nutzt aktuelle Daten
im selben laufenden Sensorstack, keine neue Karten-/Quellenfreigabe.

**Reale Mission nicht ausgeführt:** kein aktiver Buswechsel, kein MM-Auftrag,
kein Nav2-Kind. Quellenbudget UND Anfangskontur blockieren technisch; keine
fehlende allgemeine Nutzerfreigabe. Kein weiterer Vorlauf oder Fahrversuch.
Der 720-s-Probe endete automatisch; für abschließenden Snapshot und geordneten
Stopp liefen die rein lesenden Sensorprozesse anschließend noch **185,994 s**.
Dies ist Abschlussnachlauf außerhalb des Messfensters, kein zweites Fenster
und keine 900-s-Mission; eine exakte 720-s-Prozesslaufzeit wird nicht behauptet.
Geschlossene Bag erst nach Recorderende: 0 running-Missionen, 0 Navigate-
Statuseinträge, sämtliche vier aufgezeichneten Befehlsströme null. Radpositionen
durchgehend null; kleine gefilterte IMU-Winkelgeschwindigkeit ist kein Fahrbeleg.
Geschlossener Gesamtdatensatz einschließlich Nachlauf: 17.559 Readerpaare,
keine 120-ms-Verletzung, maximaler Messabstand 124,198 ms. Diese Statistik
nicht mit einem durchgehend gesunden Verbraucherzustand gleichsetzen.
Mast-NaN im robusten Sektorinneren 57–123° vollständig erhalten; Montage-TF
unverändert. Einzelne Raster-/Pose-/Zellbelege bleiben privat.

**Endzustand:** alle manifestierten Prozesse nach einzelnem SIGINT an ihren
Launchwurzeln beendet, beide Gerätealiases ohne Besitzer; anschließend zwölf
frische FC03-Paare je Position 0 / 0 RPM, keine elektrische Sperrstellung
behauptet. Hauptkopie sauber auf `23928d92f411473ed2644692a04aebdff0ffe803`,
kein dauerhafter Install-/Autostartwechsel. System eingeschaltet, kein geplanter
Shutdown. Private Belege ausschließlich
`~/.local/share/amadeus/tests/metric-adaptive-start-20261001/`, insbesondere
`common/passive-window-final.json`, `common/closed-preflight-analysis.json`,
`common/late-geometry-report.json`, `common/fullstack-timing.json`,
`common/scan-mask-proof.json`, `end-state-proof.json` und `end-encoder.json`.

**Belegte Restgrenze:** autonome reale Erkundung erst mit gleichzeitig gültigen
Quellen am Verbraucher innerhalb des unveränderten Recoverybudgets und
sensorisch belegter Anfangskontur/einer zulässigen berechneten Erstbewegung.
Der optionale Rundblick löst weder drei HWT-Störungen noch die 33 Startzellen.
Kein manueller Bootstrap als Ersatz. Weitere gezielte Quellen-/Beobachtungs-
arbeit braucht einen neuen begrenzten Auftrag, keine automatische Neustartserie.
Rückfall: ohne Mission geordnet stoppen und dieses temporäre Fünfpaketoverlay
weglassen; sichere Betriebsparameter `active_drive=false`,
`enable_auto_explore=false`. **Stufe 3 offen.**

### Aktueller Abschluss: HWT-Entwicklungsvertrag und Start-Egress (01.10.2026)

Ausgang `2a0e19d`, bestehender Branch/PR #105. Getrennte Funktionscommits:
`689cba3` (HWT-Vertrag), `acdfbeb` (gebundene Portgeneration), `577013d`
(weiter frisches korrigiertes Original nach verworfener Grenzmessung),
`a6f31bf` (bewegungsgerichteter Egress). Explizites Entwicklungsopt-in:
Antwortfrist 50 ms, Rohoriginalfrische 300 ms, maximal zwei echte HWT-HOLDs
im rollenden 60-s-Fenster. Einzel-Recovery weiterhin absolut 5 s; keine
Rücksetzung durch Aufgaben-/Kind-IDs. Legacy 30/200 ms und Encoder 120/180 ms
erhalten. Kein Restempeln, keine verspätete Antwort nachträglich nutzbar.

**Software:** 1.462 Pflichtregressionen in sieben betroffenen Paketen bestanden
(28,97 s), zusätzlich 102 unveränderte Mission-/BT-/Kartenprüfungen (5,00 s):
zusammen 1.564 Tests in getrennten, nicht überlappenden Testsammlungen.
Pflichtfälle A–F: Polltimeout ohne Budgetverbrauch, wirkliche Rohdatenlücke,
begrenztes Heilen/ACK/Resume, drittes HOLD innerhalb 60 s, drei zeitlich
verteilte Recoveries und harte Port-/Protokoll-/Zeitfehler. G–J: autonome
Vorwärtsausfahrt aus unbekanntem Startbestand, unzulässige Drehung, neues
Hindernis und spätere normale Entscheidung nach echter Beobachtung.
Zusätzlich Wiederbetreten/Annäherung, Kontextentzug und verbleibende
Drehkopplung nach nominalem Verlassen, sowie Not-Aus/Cancel/Einzelkind/
Encoder/Kartenprovenienz regressiert. Verbundener gerätefreier Produktgraph:
drei autonome erreichte Ziele mit neuen Kartenbeobachtungen und Weiterarbeit
über die synthetische Verbindung; maximal ein Nav2-Kind. Separater HOLD-Graph:
150-ms-Lücke ohne HOLD, echte >300-ms-Lücke, Stop/Validierung/ACK innerhalb
5 s und Wiederaufnahme desselben Ziels. Keine reale Recovery daraus ableiten.
Historische negative vollständige 2π-Dauerprobe bleibt unverändert negativ.

**Runtime:** Sechspaket-Copybuild außerhalb Git erfolgreich, letzter Build
von state/explore 8,58 s. 100 Quell-/Install-Dateien bytegleich. Tatsächliche
Prozessargumente, Parameterdateien, Präfixe und Modulhashes privat gesichert;
live Rawreader 50/300 ms, Encoder 120/180 ms und 13 native Controller-/
Goalcheckerparameter gelesen. Die einzelne Live-Explorer-Parameterabfrage
war während dessen verzögerter Initialisierung nicht verfügbar; gebundenes
Launchprofil und vier spätere `metric_frontier`-Statusmeldungen sind erhalten.
Keine vollständige Live-Parameterantwort dieses Nodes behaupten.

**A. Start-Egress:** Fester Ausgangsbestand in beiden Rastern, nur monoton
wegführender voller reservierter RPP-Sweep; Suchmaske ist keine Freigabe.
Aktueller Real-Snapshot: 42 unbekannte Roh-Startkonturzellen (16 teilweise
Körperrand-, 17 Padding-, 9 Reservezellen), 79 ganze Körperzellen privat;
Außenanteil 0,026895 m². Costmap zwei unbekannte Konturzellen. Das ist ein
neuer Snapshot, kein Ersatz des historischen 33-Zellen-Befunds. 22 autonome
Kandidaten, keiner zulässig: zehn nötige Anfangsdrehungen, sieben fehlende
freie Routen, eine ungültige Zielorientierung, vier ungültige Footprint-
Sweeps. Produktgrund `start_egress_no_admissible_motion`; optionaler Vollscan
ebenfalls unzulässig. Alle Zell-/Pose-/Kartenbelege und gerenderte Grafik
privat. Frühere virtuelle Hindernisdiagnose nicht als aktuelle Fahrt ausgeben.

**B. Reale autonome Ziele:** Null; kein aktiver Buswechsel, keine MM-Mission,
kein Nav2-Kind. Keine fehlende allgemeine Nutzerfreigabe: der harte Zeitfehler
und der fehlende zulässige Startkandidat verhindern den konditionierten Start.

**C. Karte:** Aktuelle reale Karte/Pose/Scope gebunden und unverändert
ausgewertet. Kein durch Fahrt erzielter Kartierungsfortschritt und kein
Abdeckungs-/Wohnungsabschluss. Drei neue Beobachtungen nur im Softwaregraph.

**D. HWT:** Erster kurzer Start vor der gemessenen Portprüfung-Optimierung
verbleibt STARTUP: wiederholte >100-ms-Lücken unterbrechen die unveränderte
800-Sample-Kalibrierung. Optimierung gemessen: voller USB-Abgleich im Mittel
1,065 ms, gebundene Geräteprüfung 0,031 ms; voller Ausschluss vor exklusivem
Öffnen, danach Gerätegeneration vor und nach Antwort. Finaler kurzer Start:
60,008-s-Messfenster, HEALTHY bei 36,379 s, terminal bei 54,880 s wegen
`HWT-Messzeit nicht monoton`. Dies betrifft die hostseitige Zuordnung des
Empfangs zu ROS-Zeit; keine bewiesene Sensor-/USB-/Kernelursache. Davor
zwei tatsächliche verworfene Transaktionen: Header 3 Bytes erst nach Frist,
Payload 0; anschließend Header 3/Payload 14 rechtzeitig empfangen, Verarbeitung
nach Frist. Rawdriver meldet dabei `transport_degraded`, letzte gültige
Messung 75,693 bzw. 71,024 ms alt, kein HWT-HOLD. Harte Zeitprüfung umgeht das
Recoverybudget nicht: unmittelbare Sperre, null Recoveryversuche. Keine
natürliche reale HOLD→Resume-Folge in diesem Lauf. Frozen Bias mit 800 Samples
belegt, keine Grenze dafür gelockert. Recorder 3.280 Rohframes gegenüber
Driverzähler 3.287; nicht als verlustfreie Aufzeichnung darstellen.

Encoder am Messfensterende 824 Paare, im geschlossenen Gesamtdatensatz 1.133;
maximal 114,879 ms, null Reject/Timing-Recovery/Rebase/Reconnect, Baseline eins.
Er ist auch hier kein nachgewiesener Blocker. Messfenster und Prozessdauer
getrennt: gesamte Orchestrierung einschließlich Bindung/Manifest/geordnetem
Stopp 83,709 s, Bag-Spanne 76,646 s. Kein 720-s-Vorlauf oder 900-s-Fahrversuch.

**E. Zielmisserfolg/Folgeaufgabe:** Kein reales Ziel gesendet, daher kein
reales Misserfolgs-/Alternativzielereignis. Bestehender Softwarevertrag bleibt
regressiert; die Drei-Ziel-Folge meldet drei `success/observed`, null Fehler.

**F. Passage/Weitererkundung:** Nur synthetisch im Produktgraph belegt;
keine reale Durchfahrt, keine Portal-ID als Voraussetzung eingeführt.

**Endzustand/Rückfall:** Geschlossene Bag mit Integritätsprüfung, null laufende
Missionen/Nav2-Statuseinträge und alle vier Befehlsströme null. Eigene
Launchwurzeln einzeln SIGINT, Recorder danach; sämtliche manifestierten
Prozesse beendet, beide Gerätealiases ohne Handles. Zwölf frische FC03-Paare
Position/RPM null; keine elektrische Motorstromstellung daraus behauptet.
Hauptkopie sauber auf `23928d92f411473ed2644692a04aebdff0ffe803`, kein permanenter
Install-/Autostartwechsel. Rückfall: isoliertes Overlay weglassen oder beide
Opt-ins beim gestoppten Neustart deaktivieren; ohne Mission
`active_drive=false`, `enable_auto_explore=false`. Private Nachweise ausschließlich
`~/.local/share/amadeus/tests/metric-egress-hwt-20261001/`, insbesondere
`runtime-byte-manifest-release.json`, `short-final/geometry-report.json`,
`short-final/passive-window-final.json`, `short-final/timing-analysis.json`,
`short-final/closed-preflight-analysis.json`, `end-state-proof.json` und
`end-encoder.json`. Kein automatischer weiterer Start. Konkrete offene
Grenzen: monotone originale Zeitzuordnung und eine tatsächlich zulässige
autonome erste Trajektorie. **Stufe 3 offen, ROS beendet, Rechner eingeschaltet.**

## 5. Erhaltener Umfang und nächste Meilensteine

Schritt 1/2 nicht neu beginnen; betroffene Wiederverwendung gezielt regressieren. Stufe 3: Softwareabschluss des metrischen Kerns erreicht; reale autonome Beobachtungsfolge, Hindernis-/Befreiungsfälle und vollständige Passage mit Weitererkundung weiterhin offen. Normale Fahrten benötigen keine Portal-ID mehr; physische Durchfahrt und freier Fahrweg bleiben nachzuweisen.

Danach metrischer WE-M4-Rundweg, WE-M5-Persistenz/Wiederaufnahme und WE-M6-Abschluss gemäß v1.2. Semantische Portal-/Regionskriterien werden separat geführt, nicht gelöscht oder rückwirkend erfüllt. Geparkter HWT-Kindziel-Injektionstest, optionale OAK-Türerkennung und zusätzliche Architekturvergleiche sind kein aktueller Parallelauftrag.

## 6. Git, Runtime und Rückfall

Ein Integrationsverantwortlicher, bestehender Branch/PR #105. Kein automatischer Merge, kein permanenter Installwechsel. LAB-1 ohne erneute Standardfreigabeschleifen anwenden. Gerätefreier Auftrag ist keine unbegrenzte Fahrerlaubnis.

Ein lokaler nicht veröffentlichter Berichtscommit mit Raumdaten wurde im Gespräch genannt. Die ausgehende Linie basiert direkt auf dem veröffentlichten Remote-Stand; private Berichtscommits sind keine Vorfahren. Auch bei späteren Pushes Vorfahren prüfen. Lokale Arbeit sichern und getrennt halten, keinen Force-Push oder destruktiven Reset ausführen. Der Funktionscommit basiert ausschließlich auf dem veröffentlichten Remote-Stand.

Rückfall: metrisches Overlay nicht aktivieren, `exploration_strategy: existing` beim geordneten Start ohne Mission; sicherer Betriebsrückfall `enable_auto_explore:=false`, `active_drive:=false`. Kein Branch-Rollback und keine bekannten offenen Befunde ausblenden. Bei Code-Revert auch die gemeinsame Absicherung verspäteter Nav2-Annahme berücksichtigen.

## 7. Historie und Nachweisregister

[Original-STATUS bis 99d21c0](archive/20260930-v1.1/STATUS.md), [Original-Agentenauftrag](archive/20260930-v1.1/AGENTENAUFTRAG.md), [Archivzuordnung und Originalpfade](archive/20260930-v1.1/README.md). Die Dateien sind unverändert erhalten. Maßgeblich für den jetzigen Auftrag sind Abschnitte 1–6 dieser Datei und der aktuelle AGENTENAUFTRAG, nicht ältere Aufträge aus dem Archiv.
