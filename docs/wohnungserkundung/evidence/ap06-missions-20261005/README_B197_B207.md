# AP-06: Aufwand der tatsächlichen Folgeauswahl

Basis `4497d0c`, exakte Arithmetikkorrektur `8e6cbbe`. Originalmanifest,
MASTERPLAN, Schutzkette und Budgets unverändert; ausschließlich Software.

B197 startet wegen tatsächlicher Encoderlücke von 337,7 ms nicht; ursprüngliche
180-ms-Kontinuitätsgrenze bleibt wirksam. Keine ausgewählte Mission und kein
Auswahl-Snapshot. B199 erreicht eine Ankunft, scheitert vor Beobachtungsreceipt
an `self_body_scan_stale_after_processing`; nur initiale Auswahl erfasst.
Beide Negativnachweise bleiben erhalten, nicht als Qualifikation verwendet.

B201 begrenzt die Diagnose auf den Eintritt in die Auswahl nach erster Ankunft
und Beobachtung. Vollständige damalige Eingaben, Startinventar und ursprüngliche
Aufgabenhistorie bleiben erhalten. Serialisierung erfolgt nach der Entscheidung;
kein Profiling während des Gesamtablaufs. Der originale Auswahlpfad braucht
**5,55 s** und verletzt seine unveränderte **5-s-Grenze**.

Im isolierten B202-Profil auf denselben Eingaben wird ein Kandidat in **3,818 s**
gefunden. Die damalige Live-Fristüberschreitung wird nicht rückwirkend aufgehoben.
Der Aufwand liegt hauptsächlich in privater Schnittprüfung und oft wiederholter
Zellprojektion. B203/B205 messen den korrigierten Pfad mit identischem Kandidat
`metric-task-3`, Ziel (1,0749467806859438; 0,00035714735956282655) und unveränderter
Historie: **2,208 bzw. 2,191 s**. Nur Komponentenzeit, kein Missionsreceipt.

`8e6cbbe` verwirft streng disjunkte Polygon-/Zell-Boundingboxpaare vor der
unveränderten exakten Schnittrechnung. Berührende Boxen bleiben vollständig
geprüft, einschließlich ihrer flächenlosen Kontaktpunkte für die Subsetprüfung.
Lokale Evidenz projiziert die begrenzte Zellfläche gesammelt; Python-Abstand,
Rundung, Sortierung und Hashformat bleiben gleich. Kein Quellen-/Fahrtschutzcache,
keine neue freie Fläche und keine Fristverlängerung.

25 neue synthetische Vergleichsfälle prüfen Rotation, Raster, Randkontakt und
unveränderte Evidenzhashes. Drei weitere Fälle verwenden die tatsächlichen
B201-Rohkarten-/Kostenkarten-Startinventare, Bewegungen und commitierte Historie,
vergleichen alte/neue Ergebnisse und erhalten das Rückkehrverbot. NPZ enthält
nur sichere synthetische Arrays/CDR; ursprüngliche lokale Pickles bleiben außerhalb
Git. Erste Testspies unterstützten den neuen optionalen Keywordparameter nicht;
vier Fehler erhalten und Spyweiterleitung korrigiert. Der Export enthält zwei
feste Ledgers, nicht vier frische/feste Zwischenaufrufe; die falsche Zählerannahme
im neuen Test wurde korrigiert. Endgültige gezielte Prüfung: **117 bestanden**.

V40: Zwölfpaketbuild **7,23 s**, **2282 direkte Tests** in 159,17 s,
**2264 registrierte Tests**, null Fehler/Failures/Skips, **9/9 native Komponenten**.
Regulärer B207 erzielt drei Ankünfte/drei Beobachtungen und vollständigen Rundblick,
endet aber nach 1,4018 m vor einer Passage erneut am Auswahlbudget. 74,62 %
Referenzboden beobachtet, maximaler Wandfehler 3,5 cm, null Fahrfehler. Ein
Fernvorschlag zuvor korrekt an `native_stop_has_no_candidate_view` verworfen.
Save/exakter Checkpoint, keine aktiven Aktionen und vier Nullbefehle bestätigt.
196.188.604 Originalereignisbytes beim B208-Auslesen gegen den ursprünglichen
SHA-/Längennachweis geprüft.

B203/B205 luden den Quellpfad, dessen optionaler nativer Arithmetikkern dort nicht
installiert ist. Ihre Zeiten sind daher nicht als exakt gleiche Binärbindung zu
B202 zu lesen. B210 wiederholt die gleiche Entscheidung am vollständig gebauten
V40-Installpfad mit demselben nativen Kern wie B202: **1,862 s**, identischer
Kandidat und Historie. Die vorherigen Profile bleiben unverändert erhalten.
Bindung: 483 Quellen, 137 bytegleiche installierte Produktdateien, neun native
Artefakte. Gesamtstatus bis zu vollständigen neuen Positivmissionen weiterhin 0/3.
