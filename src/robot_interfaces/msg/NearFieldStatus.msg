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
