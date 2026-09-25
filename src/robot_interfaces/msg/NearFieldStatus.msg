# =====================================================================
#  NearFieldStatus.msg
#  Zusammengefasster Nahbereich-Status der beiden VL53L7CX-Sensoren.
#  Wird vom Node vl53_near_field (WP-1b) publiziert und vom
#  safety_monitor + Behavior-Tree ausgewertet.
# =====================================================================
std_msgs/Header header

# Hindernis erkannt im jeweiligen Bereich (true = Objekt naeher als Schwelle)
bool left
bool right
bool middle

# Kleinste gemessene Distanz je Bereich [m] (zur Diagnose / Geschwindigkeitsskalierung)
float32 min_dist_left
float32 min_dist_right
float32 min_dist_middle

# Messqualitaet vor dem 0,50-m-Nahbereichsfilter. Die beiden Punktwolken
# derselben Messung tragen exakt header.stamp; ein Subscriber muss beides
# korrelieren. Alte Publisher liefern hier 0 und werden fail-closed behandelt.
uint8 QUALITY_UNKNOWN=0
uint8 QUALITY_VALID_NEAR=1
uint8 QUALITY_VALID_FAR=2
uint8 QUALITY_PARTIAL=3
uint8 QUALITY_INVALID=4
uint8 left_quality
uint8 right_quality
# Bit c besagt: alle acht Hoehenzonen der horizontalen Spalte c sind gueltig.
# Bei 8x8-Aufloesung bedeutet 255 vollstaendige beobachtete Abdeckung.
uint8 left_observed_columns
uint8 right_observed_columns

# Technischer Framezustand, unabhaengig von Targetanzahl/Spaltenabdeckung.
# true: aktueller Treiberabruf erfolgreich, vollstaendiges 8x8-Raster und
# alle konfigurierten Qualitaetsfelder vorhanden/lesbar. QUALITY_INVALID
# bedeutet nur: kein verwertbarer Target-Return; kein Freiraumbeleg.
# Default false sperrt Verbraucher mit alten oder ausgefallenen Publishern.
bool left_frame_healthy
bool right_frame_healthy
