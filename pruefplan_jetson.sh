#!/usr/bin/env bash
# ============================================================================
#  pruefplan_jetson.sh  -  Ausfuehrbare Fassung des Roboter_Pruefplan.md/.html
#  ---------------------------------------------------------------------------
#  ZWECK:
#    Interaktiver Testlauf DIREKT auf dem Jetson (Terminal statt Browser).
#    Automatisiert, was gefahrlos automatisierbar ist (Build, Topic-/Log-
#    Pruefungen mit Timeout); fragt bei allem, das ein Mensch sehen/hoeren
#    muss (RViz, Radbewegung, Handy-Verbindung), per klarer Ja/Nein-Frage.
#
#  SICHERHEIT (wichtig):
#    Dieses Skript SCHALTET NIE SELBSTAENDIG allow_rs485 EIN und sendet NIE
#    selbst Motorkommandos. Fuer den scharfen RS485-Test (Stufe B2-RS485)
#    verlangt es eine woertliche Sicherheits-Bestaetigung und ueberlaesst
#    das eigentliche Kommando dann DIR im Terminal - siehe Kommentar dort.
#
#  BENUTZUNG:
#    chmod +x pruefplan_jetson.sh
#    ./pruefplan_jetson.sh --software # FINALER Software-Durchlauf (ohne
#                                     #   Hardware, vollautomatisch, ~10 min)
#    ./pruefplan_jetson.sh            # Menue (alle Stufen einzeln)
#    ./pruefplan_jetson.sh --alle     # alles inkl. Hardware-Stufen
#    ./pruefplan_jetson.sh --stage B0 # nur eine Stufe direkt ausfuehren
#
#  ERGEBNISPROTOKOLL:
#    Jeder Lauf haengt an  ~/pruefplan_ergebnisse.md  an (Zeitstempel,
#    OK/FEHLER/UEBERSPRUNGEN je Stufe) - so bleibt eine Historie erhalten.
#
#  Begleitdokument (der EINE finale Plan): Roboter_Pruefplan.md
# ============================================================================
set -uo pipefail

# --------------------------------------------------------------------------
#  Grundeinstellungen
# --------------------------------------------------------------------------
WS_DIR="${ROBOTER_WS:-$HOME/roboter_ws}"
REPORT="${PRUEFPLAN_REPORT:-$HOME/pruefplan_ergebnisse.md}"
LOGDIR="/tmp/pruefplan_logs"
mkdir -p "$LOGDIR"

if [ -t 1 ]; then
  GRN='\033[0;32m'; RED='\033[0;31m'; YEL='\033[1;33m'; BLU='\033[0;34m'
  BOLD='\033[1m'; NC='\033[0m'
else
  GRN=''; RED=''; YEL=''; BLU=''; BOLD=''; NC=''
fi

BG_PIDS=()

cleanup() {
  local pid
  for pid in "${BG_PIDS[@]:-}"; do
    [ -n "$pid" ] && kill -- "-$pid" >/dev/null 2>&1
  done
}
trap cleanup EXIT INT TERM

banner() {
  echo
  echo -e "${BLU}${BOLD}=== $* ===${NC}"
}

info()  { echo -e "${BLU}i${NC}  $*"; }
ok()    { echo -e "${GRN}[OK]${NC} $*"; }
bad()   { echo -e "${RED}[FEHLER]${NC} $*"; }
warn()  { echo -e "${YEL}[HINWEIS]${NC} $*"; }

record() {
  # record STUFE ERGEBNIS DETAIL
  local stufe="$1" ergebnis="$2" detail="${3:-}"
  {
    printf -- '- [%s] %s -> %s' \
      "$( [ "$ergebnis" = "OK" ] && echo x || echo ' ' )" "$stufe" "$ergebnis"
    [ -n "$detail" ] && printf ' (%s)' "$detail"
    printf '\n'
  } >> "$REPORT"
}

ask_jn() {
  # ask_jn "Frage" -> 0 = ja, 1 = nein
  local antwort
  while true; do
    read -r -p "$(echo -e "${YEL}?${NC}") $1 (j/n) " antwort
    case "$antwort" in
      j|J|ja|Ja) return 0 ;;
      n|N|nein|Nein) return 1 ;;
      *) echo "  bitte j oder n eingeben" ;;
    esac
  done
}

pause() { read -r -p "$(echo -e "${BLU}...weiter mit ENTER...${NC}")" _; }

# --------------------------------------------------------------------------
#  ROS-Hilfsfunktionen
# --------------------------------------------------------------------------
need_ros() {
  if ! command -v ros2 >/dev/null 2>&1; then
    bad "ros2 nicht gefunden. Zuerst: source /opt/ros/humble/setup.bash"
    return 1
  fi
  if [ -f "$WS_DIR/install/setup.bash" ]; then
    # shellcheck disable=SC1091
    # colcon/ament setup.bash referenziert Variablen ungeschuetzt -> unter
    # 'set -u' (nounset) kurz deaktivieren, sonst "COLCON_TRACE: unbound variable".
    set +u; source "$WS_DIR/install/setup.bash"; set -u
  else
    warn "$WS_DIR/install/setup.bash fehlt noch - erst Stufe B0 (Build) ausfuehren."
  fi
  return 0
}

# launch_bg LOGDATEI KOMMANDO...   -> gibt PID zurueck (eigene Prozessgruppe)
launch_bg() {
  local log="$1"; shift
  setsid "$@" >"$log" 2>&1 &
  local pid=$!
  BG_PIDS+=("$pid")
  echo "$pid"
}

# stop_bg PID
stop_bg() {
  local pid="$1"
  [ -z "$pid" ] && return 0
  kill -- "-$pid" >/dev/null 2>&1
  sleep 1
  kill -9 -- "-$pid" >/dev/null 2>&1 || true
}

# wait_log_contains LOGDATEI MUSTER TIMEOUT_S
wait_log_contains() {
  local log="$1" pattern="$2" timeout_s="${3:-30}" waited=0
  while [ "$waited" -lt "$timeout_s" ]; do
    if [ -f "$log" ] && grep -q -- "$pattern" "$log" 2>/dev/null; then
      return 0
    fi
    sleep 1
    waited=$((waited + 1))
  done
  return 1
}

# wait_topic_contains TOPIC MUSTER TIMEOUT_S
wait_topic_contains() {
  local topic="$1" pattern="$2" timeout_s="${3:-10}" hit
  # Treffer in einer Variablen einfangen: 'grep -m1' beendet die Pipe nach dem
  # ersten Treffer und schickt 'ros2 topic echo' ein SIGPIPE -> unter
  # 'set -o pipefail' waere der Pipeline-Exit sonst !=0 trotz Treffer.
  hit=$(timeout "$timeout_s" ros2 topic echo "$topic" 2>/dev/null | grep -m1 -- "$pattern" || true)
  [ -n "$hit" ]
}

# wait_action_server NAME TIMEOUT_S - aktiv warten statt fester Schlafzeit
# (Nav2-Lifecycle braucht beim Kaltstart unterschiedlich lange; fixes Warten
# machte N1 beim ersten Lauf flakey).
wait_action_server() {
  local name="$1" timeout_s="${2:-60}" waited=0 hit
  while [ "$waited" -lt "$timeout_s" ]; do
    hit=$(timeout 5 ros2 action list 2>/dev/null | grep -m1 -- "$name" || true)
    if [ -n "$hit" ]; then
      sleep 3   # kurze Karenz: Server gelistet != vollstaendig aktiv
      return 0
    fi
    sleep 3; waited=$((waited + 8))
  done
  return 1
}

# --------------------------------------------------------------------------
#  Stufe B0 - Workspace bauen
# --------------------------------------------------------------------------
stage_B0() {
  banner "B0 - Grundinstallation: Workspace bauen"
  if [ ! -d "$WS_DIR" ]; then
    bad "Workspace-Ordner $WS_DIR nicht gefunden. ROBOTER_WS setzen oder Pfad pruefen."
    record "B0 Workspace bauen" "FEHLER" "Ordner $WS_DIR fehlt"
    return
  fi
  if ! command -v colcon >/dev/null 2>&1; then
    bad "colcon nicht gefunden. ROS-2-Umgebung zuerst laden: source /opt/ros/humble/setup.bash"
    record "B0 Workspace bauen" "FEHLER" "colcon fehlt"
    return
  fi
  # macOS-Metadatenreste vom USB-Stick entfernen (._*, .DS_Store):
  # entstehen bei jedem Kopieren vom Mac auf exFAT und stoeren Globs/Builds.
  find "$WS_DIR/src" \( -name '._*' -o -name '.DS_Store' \) -delete 2>/dev/null

  # exFAT (USB-Stick) unterstuetzt KEINE Symlinks -> dort scheitert
  # --symlink-install zwingend. Faehigkeit testen und Flag automatisch waehlen.
  local build_opts=(--symlink-install)
  if ! ln -s src "$WS_DIR/.symlink_test" 2>/dev/null; then
    warn "Dateisystem ohne Symlinks (exFAT/USB?) -> Build OHNE --symlink-install."
    build_opts=()
  fi
  rm -f "$WS_DIR/.symlink_test" 2>/dev/null

  info "cd $WS_DIR && rm -rf build install log && colcon build ${build_opts[*]:-}"
  ( cd "$WS_DIR" && rm -rf build install log && colcon build "${build_opts[@]}" )
  local rc=$?
  if [ $rc -eq 0 ]; then
    ok "Build durchgelaufen (exit 0)."
    # shellcheck disable=SC1091
    set +u; source "$WS_DIR/install/setup.bash"; set -u
    local n
    n=$(ros2 pkg list 2>/dev/null | wc -l)
    record "B0 Workspace bauen" "OK" "$n Pakete in ros2 pkg list"
  else
    bad "Build fehlgeschlagen (exit $rc). Ausgabe oben pruefen."
    record "B0 Workspace bauen" "FEHLER" "colcon exit $rc"
  fi
}

# --------------------------------------------------------------------------
#  Stufe B0b - Paket-/AMENT-Hook-Check
# --------------------------------------------------------------------------
stage_B0b() {
  banner "B0b - Paket-/AMENT-Hooks pruefen"
  need_ros || { record "B0b Paket-Check" "UEBERSPRUNGEN" "ros2 fehlt"; return; }

  local pkgs=(robot_interfaces bt_orchestrator mock_servers vl53_near_field
              robot_description mission_manager smartphone_gui base_hardware
              explore robot_bringup llm_planner semantic_perception
              robot_face handeye_calibration safety_monitor robot_navigation)
  info "colcon list | grep -E \"explore|llm_planner|robot_bringup|semantic_perception\""
  ( cd "$WS_DIR" && colcon list 2>/dev/null | grep -E "explore|llm_planner|robot_bringup|semantic_perception" ) || true

  local fehlt=() gefunden=0
  for p in "${pkgs[@]}"; do
    local prefix
    prefix=$(ros2 pkg prefix "$p" 2>/dev/null)
    if [[ "$prefix" == *"/install"* ]]; then
      ok "$p -> $prefix"
      gefunden=$((gefunden + 1))
    else
      bad "$p nicht gefunden (Build fehlt, oder package.xml hat XML-Fehler - siehe README 'Wenn etwas nicht geht')."
      fehlt+=("$p")
    fi
  done

  if [ ${#fehlt[@]} -eq 0 ]; then
    record "B0b Paket-/AMENT-Check" "OK" "$gefunden/${#pkgs[@]} Pakete gefunden"
  else
    record "B0b Paket-/AMENT-Check" "FEHLER" "fehlend: ${fehlt[*]}"
  fi
}

# --------------------------------------------------------------------------
#  Stufe A1 - Pick&Place-Trockenlauf (Mocks, kein Risiko, laeuft auch auf dem
#  Jetson ohne RTX-3090/Modelle - deshalb hier statt nur auf dem Server)
# --------------------------------------------------------------------------
stage_A1() {
  banner "A1 - Pick&Place-Trockenlauf (mock_servers dry_run.launch.py)"
  need_ros || { record "A1 Pick&Place-Trockenlauf" "UEBERSPRUNGEN" "ros2 fehlt"; return; }

  local log="$LOGDIR/a1_dryrun.log"
  info "Starte im Hintergrund: ros2 launch mock_servers dry_run.launch.py"
  local pid
  pid=$(launch_bg "$log" ros2 launch mock_servers dry_run.launch.py)
  info "Warte bis zu 90 s auf 'Mission beendet mit Status: SUCCESS' im Log ..."

  if wait_log_contains "$log" "Mission beendet mit Status: SUCCESS" 90; then
    ok "Trockenlauf endete mit SUCCESS."
    record "A1 Pick&Place-Trockenlauf" "OK" "SUCCESS im Log erkannt"
  elif wait_log_contains "$log" "Mission beendet mit Status:" 1; then
    local status
    status=$(grep -m1 "Mission beendet mit Status:" "$log")
    bad "Mission endete NICHT mit SUCCESS: $status"
    record "A1 Pick&Place-Trockenlauf" "FEHLER" "$status"
  else
    bad "Kein Missionsende innerhalb 90 s. Log: $log"
    record "A1 Pick&Place-Trockenlauf" "FEHLER" "Timeout, siehe $log"
  fi
  stop_bg "$pid"
}

# --------------------------------------------------------------------------
#  Stufe B1-RViz - Dummy-URDF / TF-Baum (visuell, braucht Display)
# --------------------------------------------------------------------------
stage_B1_rviz() {
  banner "B1 - Dummy-URDF / TF-Baum in RViz (visuelle Pruefung)"
  need_ros || { record "B1 Dummy-URDF/RViz" "UEBERSPRUNGEN" "ros2 fehlt"; return; }

  if [ -z "${DISPLAY:-}" ]; then
    warn "Keine DISPLAY-Variable gesetzt - RViz braucht einen Bildschirm/X11."
    if ! ask_jn "Trotzdem versuchen (z.B. per VNC/HDMI-Display angeschlossen)?"; then
      record "B1 Dummy-URDF/RViz" "UEBERSPRUNGEN" "kein Display"
      return
    fi
  fi
  info "ros2 launch robot_description display_dummy.launch.py use_rviz:=true"
  info "(Fenster schliessen oder Strg+C hier im Terminal, wenn fertig geprueft)"
  ( cd "$WS_DIR" && ros2 launch robot_description display_dummy.launch.py use_rviz:=true )

  if ask_jn "RViz zeigte Basis, Raeder, OAK, VL53, 6-Achs-Arm und gripper_tcp korrekt?"; then
    ok "Bestaetigt."
    record "B1 Dummy-URDF/RViz" "OK" "manuell bestaetigt"
  else
    bad "Nicht bestaetigt."
    record "B1 Dummy-URDF/RViz" "FEHLER" "manuell verneint"
  fi
}

# --------------------------------------------------------------------------
#  Stufe B1-Basis - Basisantrieb Dry-run (automatisch, KEIN Motorstrom)
# --------------------------------------------------------------------------
stage_B1_basis() {
  banner "B1 - Basisantrieb im Dry-run (rechnet nur, dreht keine Motoren)"
  need_ros || { record "B1 Basisantrieb Dry-run" "UEBERSPRUNGEN" "ros2 fehlt"; return; }

  local log="$LOGDIR/b1_basis.log"
  local pid
  pid=$(launch_bg "$log" ros2 launch base_hardware base_hardware.launch.py)
  info "Warte 3 s auf Nodestart ..."; sleep 3

  info "Sende 3 s lang /cmd_vel (0.10 m/s) - dry_run bleibt aktiv, kein Motorlauf."
  timeout 3 ros2 topic pub /cmd_vel geometry_msgs/msg/Twist \
    "{linear: {x: 0.10}}" -r 10 >/dev/null 2>&1

  local odom_ok=1
  wait_topic_contains "/odom" "frame_id" 5 || odom_ok=0
  local state_ok=1
  wait_topic_contains "/base_hardware/state_json" "dry_run" 5 || state_ok=0

  if [ $odom_ok -eq 1 ] && [ $state_ok -eq 1 ]; then
    ok "/odom und /base_hardware/state_json liefern Daten, dry_run aktiv."
    record "B1 Basisantrieb Dry-run" "OK" "/odom + state_json liefern"
  else
    bad "Erwartete Topics kamen nicht (odom_ok=$odom_ok state_ok=$state_ok)."
    record "B1 Basisantrieb Dry-run" "FEHLER" "odom_ok=$odom_ok state_ok=$state_ok"
  fi
  stop_bg "$pid"
}

# --------------------------------------------------------------------------
#  Stufe B1-VL53 - Nahbereichssensoren (echtes I2C, aber KEIN Motor -
#  halbautomatisch: Skript zeichnet auf, DU haeltst die Hand davor)
# --------------------------------------------------------------------------
stage_B1_vl53() {
  banner "B1 - VL53-Nahbereichssensoren (echtes I2C-Auslesen)"
  need_ros || { record "B1 VL53" "UEBERSPRUNGEN" "ros2 fehlt"; return; }

  local log="$LOGDIR/b1_vl53_launch.log"
  local pid
  pid=$(launch_bg "$log" ros2 launch vl53_near_field vl53_near_field.launch.py)
  info "Warte 4 s auf Sensorstart ..."; sleep 4

  local capture="$LOGDIR/b1_vl53_status.log"
  warn "JETZT 8 Sekunden lang abwechselnd die Hand vor linken/rechten/mittleren Sensor halten!"
  timeout 8 ros2 topic echo /near_field/status > "$capture" 2>&1

  if grep -q "true" "$capture" 2>/dev/null; then
    ok "Mindestens ein Bereich hat ein Hindernis erkannt (true in /near_field/status)."
    record "B1 VL53 Nahbereich" "OK" "Hindernis erkannt"
  else
    bad "Kein 'true' im Status erkannt - Hand zu kurz/weit weg, oder Sensoren pruefen."
    record "B1 VL53 Nahbereich" "FEHLER" "kein Hindernis im Fenster erkannt"
  fi
  stop_bg "$pid"
}

# --------------------------------------------------------------------------
#  Stufe B2-OAK - Kamera-Topics (lesend, keine Bewegung -> automatisierbar)
# --------------------------------------------------------------------------
stage_B2_oak() {
  banner "B2 - OAK-Kamera-Topics (depthai-Treiber muss laufen)"
  need_ros || { record "B2 OAK-Kamera" "UEBERSPRUNGEN" "ros2 fehlt"; return; }

  info "ros2 topic echo /oak/rgb --once  (Timeout 10 s)"
  local rgb_ok=1 pts_ok=1
  wait_topic_contains "/oak/rgb" "encoding" 10 || rgb_ok=0
  info "ros2 topic hz /oak/points  (Timeout 10 s)"
  timeout 10 ros2 topic hz /oak/points 2>/dev/null | grep -qm1 "average rate" || pts_ok=0

  if [ $rgb_ok -eq 1 ] && [ $pts_ok -eq 1 ]; then
    ok "Bild- und Punktwolken-Topics liefern Daten."
    record "B2 OAK-Kamera" "OK" "rgb+points liefern"
  else
    bad "Kein Signal (rgb_ok=$rgb_ok points_ok=$pts_ok). Laeuft der depthai-Treiber schon?"
    record "B2 OAK-Kamera" "FEHLER" "rgb_ok=$rgb_ok points_ok=$pts_ok - Treiber noch Platzhalter (siehe robot.launch.py)"
  fi
}

# --------------------------------------------------------------------------
#  Stufe B2-RS485 - Basisantrieb SCHARF (echte Motoren!) - NUR Sicherheits-
#  Checkliste + Bestaetigung. Das Skript sendet SELBST NIE Motorkommandos.
# --------------------------------------------------------------------------
stage_B2_rs485() {
  banner "B2 - Basisantrieb SCHARF (RS485, ECHTE MOTOREN)"
  echo -e "${RED}${BOLD}Sicherheit - alle Punkte muessen erfuellt sein, BEVOR du fortfaehrst:${NC}"
  cat <<'EOF'
  [ ] Not-Aus ist erreichbar UND getestet.
  [ ] Roboter steht AUFGEBOCKT, beide Raeder drehen frei (kein Bodenkontakt).
  [ ] config/base_hardware_params.yaml: dry_run:false, allow_rs485:true
      NUR jetzt gesetzt, sonst bleibt dry_run:true.
  [ ] rs485_port, Motor-IDs und Register wurden mit dem NEMA23-Manual abgeglichen.
  [ ] pymodbus ist installiert (python3 -m pip install pymodbus).
  [ ] Sehr kleine Geschwindigkeit vorgesehen (x: 0.03, NICHT 0.10).
EOF
  echo
  local phrase="AUFGEBOCKT UND NOTAUS BEREIT"
  info "Zum Fortfahren exakt eintippen: $phrase"
  read -r -p "> " eingabe
  if [ "$eingabe" != "$phrase" ]; then
    warn "Nicht bestaetigt - Stufe wird uebersprungen (nichts wurde ausgefuehrt)."
    record "B2 Basisantrieb SCHARF (RS485)" "UEBERSPRUNGEN" "Sicherheitsphrase nicht bestaetigt"
    return
  fi

  echo
  warn "Ab hier fuehrst DU die Befehle selbst aus (das Skript startet hier NICHTS automatisch):"
  cat <<'EOF'
    ros2 launch base_hardware base_hardware.launch.py
    # zweites Terminal:
    ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.03}}" -r 10
EOF
  pause
  if ask_jn "Raeder drehen kontrolliert/langsam, Timeout/Stop UND Not-Aus greifen wie erwartet?"; then
    ok "Bestaetigt."
    record "B2 Basisantrieb SCHARF (RS485)" "OK" "manuell bestaetigt"
  else
    bad "Nicht bestaetigt - siehe README 'invert_left/invert_right' bei falscher Richtung."
    record "B2 Basisantrieb SCHARF (RS485)" "FEHLER" "manuell verneint"
  fi
}

# --------------------------------------------------------------------------
#  Stufe B3 - robot_bringup Gesamtstart (onboard)
# --------------------------------------------------------------------------
stage_B3() {
  banner "B3 - Onboard-Stack gesamt (robot_bringup robot.launch.py)"
  need_ros || { record "B3 robot_bringup" "UEBERSPRUNGEN" "ros2 fehlt"; return; }

  export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-42}"
  info "ROS_DOMAIN_ID=$ROS_DOMAIN_ID"
  local log="$LOGDIR/b3_bringup.log"
  local pid
  pid=$(launch_bg "$log" ros2 launch robot_bringup robot.launch.py)
  info "Warte 8 s auf Nodestart ..."; sleep 8

  local nodes
  nodes=$(timeout 5 ros2 node list 2>/dev/null)
  echo "$nodes"
  # Kern-ROS-Nodes, die ohne Zusatzhardware laufen muessen:
  local kern=(base_hardware explore mission_manager link_monitor face_controller safety_monitor)
  local fehlt=()
  for n in "${kern[@]}"; do
    echo "$nodes" | grep -q "$n" || fehlt+=("$n")
  done
  # vl53_near_field braucht die echten I2C-Sensoren -> Fehlen = Hinweis, kein Fehler.
  echo "$nodes" | grep -q "vl53_near_field" \
    && ok "vl53_near_field aktiv (Sensoren angeschlossen)." \
    || warn "vl53_near_field nicht aktiv - erwartet ohne angeschlossene I2C-Sensoren."
  # robot_face_server ist ein reiner HTTP-Server (KEIN ROS-Node) -> per Port pruefen.
  if curl -s -o /dev/null --max-time 3 http://localhost:8081/ 2>/dev/null; then
    ok "robot_face HTTP-Anzeige erreichbar (Port 8081)."
  else
    warn "robot_face HTTP-Anzeige (Port 8081) nicht erreichbar."
  fi

  if [ ${#fehlt[@]} -eq 0 ]; then
    ok "Alle Kern-Nodes sichtbar."
    record "B3 robot_bringup Gesamtstart" "OK" "Kern-Nodes sichtbar (vl53 hardware-abhaengig)"
  else
    bad "Fehlende Kern-Nodes: ${fehlt[*]}"
    record "B3 robot_bringup Gesamtstart" "FEHLER" "fehlend: ${fehlt[*]}"
  fi
  info "(explore faehrt erst richtig mit SLAM/Nav2 - hier nur Node-Praesenz geprueft.)"
  stop_bg "$pid"
}

# --------------------------------------------------------------------------
#  Stufe B4 - Smartphone-GUI + rosbridge
# --------------------------------------------------------------------------
stage_B4() {
  banner "B4 - Smartphone-GUI auf dem Jetson"
  need_ros || { record "B4 Smartphone-GUI" "UEBERSPRUNGEN" "ros2 fehlt"; return; }

  local log="$LOGDIR/b4_gui.log"
  local pid
  pid=$(launch_bg "$log" ros2 launch smartphone_gui smartphone_gui.launch.py)
  info "Warte 4 s ..."; sleep 4

  local ip
  ip=$(hostname -I 2>/dev/null | awk '{print $1}')
  info "Am Handy im gleichen WLAN oeffnen: http://${ip:-JETSON-IP}:8080"
  pause
  if ask_jn "Handy zeigt Status/Listen und ein gesendeter Auftrag laeuft bis success durch?"; then
    ok "Bestaetigt."
    record "B4 Smartphone-GUI" "OK" "manuell bestaetigt"
  else
    bad "Nicht bestaetigt."
    record "B4 Smartphone-GUI" "FEHLER" "manuell verneint"
  fi
  stop_bg "$pid"
}

# --------------------------------------------------------------------------
#  Stufe C1 - Netzwerk / Offboard-Erreichbarkeit
# --------------------------------------------------------------------------
stage_C1() {
  banner "C1 - Netzwerk-Verbindung Jetson <-> Server"
  need_ros || { record "C1 Netzwerk" "UEBERSPRUNGEN" "ros2 fehlt"; return; }

  info "ROS_DOMAIN_ID hier: ${ROS_DOMAIN_ID:-<nicht gesetzt, Standard 0!>}"
  if [ -z "${ROS_DOMAIN_ID:-}" ]; then
    warn "ROS_DOMAIN_ID ist nicht gesetzt - auf beiden Rechnern gleich setzen (z.B. 42)."
  fi
  info "Server muss dort bereits laufen: ros2 launch robot_bringup server.launch.py"
  local nodes
  nodes=$(timeout 5 ros2 node list 2>/dev/null)
  if echo "$nodes" | grep -q "llm_planner" && echo "$nodes" | grep -q "semantic_perception"; then
    ok "llm_planner und semantic_perception vom Server sichtbar."
    record "C1 Netzwerk/Offboard" "OK" "Server-Nodes sichtbar"
  else
    bad "Server-Nodes NICHT sichtbar. Gleiche ROS_DOMAIN_ID? Firewall? Feste Peer-IPs im DDS-Profil?"
    record "C1 Netzwerk/Offboard" "FEHLER" "Server-Nodes fehlen in ros2 node list"
  fi

  info "Zusatz: /offboard/available beobachten (5 s) ..."
  if wait_topic_contains "/offboard/available" "true" 5; then
    ok "/offboard/available meldet true."
  else
    warn "/offboard/available meldete in 5 s kein 'true' (link_monitor braucht ggf. laenger)."
  fi
}

# --------------------------------------------------------------------------
#  Stufe C2 - Gesamtkette Sprache -> Auftrag (Server muss bereits laufen)
# --------------------------------------------------------------------------
stage_C2() {
  banner "C2 - Sprachbefehl an den Server, Roboter beobachten"
  need_ros || { record "C2 Gesamtkette" "UEBERSPRUNGEN" "ros2 fehlt"; return; }

  info "Sende Testanweisung an /llm_planner/instruction (laeuft auf dem SERVER) ..."
  # Nicht --once: ein einzelner Publish erreicht einen gerade erst per DDS
  # entdeckten Subscriber oft nicht. Kurz wiederholt senden (Hintergrund),
  # damit die Zustellung sicher ankommt; timeout beendet den Publisher.
  timeout 4 ros2 topic pub -r 2 /llm_planner/instruction std_msgs/msg/String \
    "{data: 'Erkunde die Wohnung'}" >/dev/null 2>&1 &

  if wait_topic_contains "/mission_manager/status_json" "explore" 15; then
    ok "mission_manager hat den Auftrag uebernommen (explore erkannt)."
    record "C2 Gesamtkette Sprache->Auftrag" "OK" "explore im status_json erkannt"
  else
    bad "Kein passender Auftrag im status_json innerhalb 15 s."
    record "C2 Gesamtkette Sprache->Auftrag" "FEHLER" "Timeout - laeuft der Server-Planer?"
  fi
}

# --------------------------------------------------------------------------
#  Stufe C3 - Smartphone -> mission_manager (visuell)
# --------------------------------------------------------------------------
stage_C3() {
  banner "C3 - Auftrag aus der Smartphone-App beobachten"
  need_ros || { record "C3 Smartphone->BT" "UEBERSPRUNGEN" "ros2 fehlt"; return; }

  info "Am Handy jetzt 'Bringen' mit Objekt/Raum/Ablage starten."
  warn "Seit K1 laeuft 'Bringen' ECHT ueber den bt_orchestrator - der muss laufen"
  warn "(z.B. dry_run_mission.launch.py ODER robot.launch.py start_bt:=true + Mocks)."
  info "Hier laeuft mit: ros2 topic echo /mission_manager/status_json  (20 s Fenster)"
  timeout 20 ros2 topic echo /mission_manager/status_json 2>/dev/null | tail -40

  if ask_jn "Status zeigte aktiven Auftrag, Phasen und endete mit success?"; then
    ok "Bestaetigt."
    record "C3 Smartphone->mission_manager" "OK" "manuell bestaetigt"
  else
    bad "Nicht bestaetigt."
    record "C3 Smartphone->mission_manager" "FEHLER" "manuell verneint"
  fi
}

# --------------------------------------------------------------------------
#  Stufe C4 - Nav2-Kette Vorbereitung (Basis-Unterbau)
# --------------------------------------------------------------------------
stage_C4() {
  banner "C4 - Nav2-Kette bis Basis-Unterbau (Vorbereitung)"
  need_ros || { record "C4 Nav2-Vorbereitung" "UEBERSPRUNGEN" "ros2 fehlt"; return; }

  info "Erwartung: /cmd_vel kommt an, /base_hardware/state_json rechnet RPM."
  local cmdvel_ok=1
  wait_topic_contains "/cmd_vel" "linear" 8 || cmdvel_ok=0
  if [ $cmdvel_ok -eq 1 ]; then
    ok "/cmd_vel liefert Daten (Nav2/Controller aktiv)."
    record "C4 Nav2-Kette Vorbereitung" "OK" "/cmd_vel liefert"
  else
    warn "/cmd_vel noch leer - erwartungsgemaess, solange Nav2/SLAM noch nicht integriert sind (siehe README 'Offen')."
    record "C4 Nav2-Kette Vorbereitung" "UEBERSPRUNGEN" "Nav2/SLAM noch nicht integriert (bekannt offen)"
  fi
}

# --------------------------------------------------------------------------
#  Stufe K1 [NEU] - Missionsbruecke: Auftrag -> mission_manager -> BT -> Mocks
#  Nachweis, dass eine Mission WIRKLICH ausgefuehrt wird (nicht simuliert).
#  Nutzt dry_run_mission.launch.py (Mock + bt_orchestrator + mission_manager).
# --------------------------------------------------------------------------
stage_K1() {
  banner "K1 [NEU] - Missionsbruecke echt (mission_manager -> bt_orchestrator)"
  need_ros || { record "K1 Missionsbruecke" "UEBERSPRUNGEN" "ros2 fehlt"; return; }

  local log="$LOGDIR/k1_mission.log"
  info "Starte Mock + BT-Action-Server + mission_manager (dry_run_mission.launch.py) ..."
  local pid
  pid=$(launch_bg "$log" ros2 launch mock_servers dry_run_mission.launch.py)
  info "Warte 8 s auf Hochlauf ..."; sleep 8

  info "Sende echten Auftrag (pick_and_place) an /mission_manager/command_json ..."
  timeout 4 ros2 topic pub -r 2 /mission_manager/command_json std_msgs/msg/String \
    "{data: '{\"type\":\"pick_and_place\",\"object\":\"Tasse\",\"room\":\"Kueche\",\"target\":\"Tisch\"}'}" \
    >/dev/null 2>&1 &

  # Beweis 1: der BT-Action-Server meldet echten Missionsabschluss.
  local bt_ok=1
  wait_log_contains "$log" "Mission beendet mit Status: SUCCESS" 90 || bt_ok=0
  # Beweis 2: der mission_manager-Status erreicht success (echte Kette).
  local mm_ok=1
  wait_topic_contains "/mission_manager/status_json" '"state": "success"' 10 || mm_ok=0

  if [ $bt_ok -eq 1 ] && [ $mm_ok -eq 1 ]; then
    ok "Auftrag lief ECHT durch: BT meldet SUCCESS und mission_manager-Status = success."
    record "K1 Missionsbruecke echt" "OK" "BT SUCCESS + mission_manager success"
  elif [ $bt_ok -eq 1 ]; then
    warn "BT lief durch, aber mission_manager-Status erreichte 'success' nicht in der Zeit."
    record "K1 Missionsbruecke echt" "FEHLER" "BT SUCCESS, aber mission_manager-Status nicht success"
  else
    bad "Keine echte Ausfuehrung erkannt. Log: $log"
    record "K1 Missionsbruecke echt" "FEHLER" "kein 'Mission beendet mit Status: SUCCESS' in 90 s"
  fi
  stop_bg "$pid"
}

# --------------------------------------------------------------------------
#  Stufe K2 [NEU] - Objekt-Gedaechtnis (semantic_perception als Weltmodell)
#  Beweist: get_object_pose liefert ein Objekt AUS DEM GEDAECHTNIS (auch wenn
#  es gerade nicht "live" im Bild ist) - Voraussetzung fuer erkunden-dann-suchen.
# --------------------------------------------------------------------------
stage_K2() {
  banner "K2 [NEU] - Objekt-Gedaechtnis (semantic_perception, Weltmodell)"
  need_ros || { record "K2 Objekt-Gedaechtnis" "UEBERSPRUNGEN" "ros2 fehlt"; return; }

  local log="$LOGDIR/k2_memory.log"
  info "Starte semantic_perception (Backend stub) ..."
  local pid
  pid=$(launch_bg "$log" ros2 launch semantic_perception semantic_perception.launch.py)
  info "Warte 6 s, bis der Hintergrund-Scan das Gedaechtnis gefuellt hat ..."; sleep 6

  info "Frage get_object_pose('Tasse') ab ..."
  local out
  out=$(timeout 10 ros2 service call /world_model/get_object_pose \
        robot_interfaces/srv/GetObjectPose "{class_name: 'Tasse'}" 2>&1)
  local found=1;    echo "$out" | grep -q "found=True" || found=0
  local from_mem=1; grep -q "aus Gedaechtnis" "$log" 2>/dev/null || from_mem=0

  if [ $found -eq 1 ] && [ $from_mem -eq 1 ]; then
    ok "Objekt aus dem Gedaechtnis geliefert (found=True + 'aus Gedaechtnis' im Log)."
    record "K2 Objekt-Gedaechtnis" "OK" "found + aus Gedaechtnis"
  elif [ $found -eq 1 ]; then
    warn "Gefunden, aber nicht nachweislich aus dem Gedaechtnis (Log-Zeile fehlt)."
    record "K2 Objekt-Gedaechtnis" "FEHLER" "found, aber Gedaechtnis-Pfad nicht belegt"
  else
    bad "get_object_pose lieferte kein found=True. Ausgabe: $(echo "$out" | tail -3)"
    record "K2 Objekt-Gedaechtnis" "FEHLER" "kein found=True"
  fi
  stop_bg "$pid"
}

# --------------------------------------------------------------------------
#  Stufe K4 [NEU] - Not-Aus-Waechter (safety_monitor): hebt den K1-Blocker
#  Beweist: /safety/estop wird publiziert (frei by default -> Missionen
#  koennen laufen) UND reagiert auf eine Not-Aus-Anforderung.
# --------------------------------------------------------------------------
stage_K4() {
  banner "K4 [NEU] - Onboard-Not-Aus-Waechter (safety_monitor)"
  need_ros || { record "K4 safety_monitor" "UEBERSPRUNGEN" "ros2 fehlt"; return; }

  local log="$LOGDIR/k4_safety.log"
  info "Starte safety_monitor ..."
  local pid
  pid=$(launch_bg "$log" ros2 launch safety_monitor safety_monitor.launch.py)
  info "Warte 3 s ..."; sleep 3

  # 1) Grundzustand: /safety/estop muss "frei" (data: false) melden -
  #    sonst wuerde jede echte Mission sofort scheitern (genau der K1-Blocker).
  local clear_ok=1
  wait_topic_contains "/safety/estop" "data: false" 5 || clear_ok=0
  if [ $clear_ok -eq 1 ]; then
    ok "/safety/estop meldet 'frei' (data: false) - Missionen koennen laufen."
  else
    bad "/safety/estop meldet nicht 'frei' - Missionen wuerden blockiert."
  fi

  # 2) Not-Aus ausloesen -> muss auf data: true kippen.
  info "Loese Not-Aus aus (/safety/estop_request true) ..."
  timeout 3 ros2 topic pub -r 2 /safety/estop_request std_msgs/msg/Bool \
    "{data: true}" >/dev/null 2>&1 &
  local trip_ok=1
  wait_topic_contains "/safety/estop" "data: true" 6 || trip_ok=0
  [ $trip_ok -eq 1 ] && ok "Not-Aus wirkt: /safety/estop -> true." \
                     || bad "Not-Aus-Anforderung kam nicht durch (/safety/estop blieb false)."

  # 3) Zuruecksetzen -> muss wieder frei werden.
  info "Setze Not-Aus zurueck (/safety/estop_request false) ..."
  timeout 3 ros2 topic pub -r 2 /safety/estop_request std_msgs/msg/Bool \
    "{data: false}" >/dev/null 2>&1 &
  local reset_ok=1
  wait_topic_contains "/safety/estop" "data: false" 6 || reset_ok=0
  [ $reset_ok -eq 1 ] && ok "Zuruecksetzen wirkt: /safety/estop -> false." \
                      || warn "Zuruecksetzen nicht bestaetigt (evtl. Timing)."

  if [ $clear_ok -eq 1 ] && [ $trip_ok -eq 1 ]; then
    record "K4 safety_monitor" "OK" "estop frei by default + Not-Aus wirkt"
  else
    record "K4 safety_monitor" "FEHLER" "clear=$clear_ok trip=$trip_ok reset=$reset_ok"
  fi
  info "Tiefer testen (Not-Aus haelt echte Mission an): dry_run_safety.launch.py (manuell)."
  stop_bg "$pid"
}

# --------------------------------------------------------------------------
#  Stufe K5 [NEU] - Offboard-Guard: WLAN-/Serverausfall loest KEINE
#  ungewollte Erkundung aus. Objekt "nicht gefunden" + kein /offboard/available
#  -> FindTarget scheitert OHNE zu erkunden (ExploreArea wird NICHT gerufen).
# --------------------------------------------------------------------------
stage_K5() {
  banner "K5 [NEU] - Offboard-Guard (keine Erkundung bei Serverausfall)"
  need_ros || { record "K5 Offboard-Guard" "UEBERSPRUNGEN" "ros2 fehlt"; return; }

  local log="$LOGDIR/k5_guard.log"
  info "Starte dry_run.launch.py mit object_found:=false (kein link_monitor -> Offboard 'unbekannt')."
  local pid
  pid=$(launch_bg "$log" ros2 launch mock_servers dry_run.launch.py object_found:=false)

  # Mission muss scheitern (Objekt nie gefunden) - bis zu 60 s.
  local failed_ok=1
  wait_log_contains "$log" "Mission beendet mit Status: FAILURE" 60 || failed_ok=0

  # Entscheidend: ExploreArea darf dabei NICHT gerufen worden sein.
  local explored=1
  grep -q "\[mock\] ExploreArea" "$log" 2>/dev/null || explored=0

  if [ $failed_ok -eq 1 ] && [ $explored -eq 0 ]; then
    ok "Guard wirkt: Mission scheitert sauber, KEINE Erkundung ausgeloest."
    record "K5 Offboard-Guard" "OK" "FAILURE ohne ExploreArea-Aufruf"
  elif [ $explored -eq 1 ]; then
    bad "Guard wirkungslos: ExploreArea wurde trotz fehlendem Offboard gerufen."
    record "K5 Offboard-Guard" "FEHLER" "ExploreArea trotz Serverausfall gerufen"
  else
    bad "Mission endete nicht wie erwartet mit FAILURE. Log: $log"
    record "K5 Offboard-Guard" "FEHLER" "kein FAILURE in 60 s"
  fi
  info "Gegenprobe (Offboard da -> Erkundung erlaubt): dry_run_mission + /offboard/available true (manuell)."
  stop_bg "$pid"
}

# --------------------------------------------------------------------------
#  Stufe N1 [NEU] - ECHTES Nav2 ohne Hardware (Testkarte + virtuelle Basis)
#  Beweist: Nav2 plant/regelt wirklich; die Dry-Run-Basis "faehrt" das Ziel an.
# --------------------------------------------------------------------------
stage_N1() {
  banner "N1 [NEU] - Nav2 real, ohne Hardware (Testwohnung + virtuelle Basis)"
  need_ros || { record "N1 Nav2 virtuell" "UEBERSPRUNGEN" "ros2 fehlt"; return; }
  if ! ros2 pkg prefix nav2_bt_navigator >/dev/null 2>&1; then
    warn "Nav2 nicht installiert: sudo apt install ros-humble-navigation2"
    record "N1 Nav2 virtuell" "UEBERSPRUNGEN" "ros-humble-navigation2 fehlt"
    return
  fi

  local log="$LOGDIR/n1_nav.log"
  info "Starte nav_test.launch.py (Karte + Nav2 + Dry-Run-Basis) ..."
  local pid
  pid=$(launch_bg "$log" ros2 launch robot_navigation nav_test.launch.py)
  info "Warte aktiv auf den Nav2-Action-Server (max 90 s, Kaltstart dauert) ..."
  if ! wait_action_server "navigate_to_pose" 90; then
    bad "Nav2-Action-Server kam nicht hoch. Log: $log"
    record "N1 Nav2 virtuell" "FEHLER" "navigate_to_pose nicht verfuegbar"
    stop_bg "$pid"
    return
  fi

  info "Sende Navigationsziel (1.5, 0.0) im map-Frame (Timeout 90 s) ..."
  local out
  out=$(timeout 90 ros2 action send_goal /navigate_to_pose \
        nav2_msgs/action/NavigateToPose \
        "{pose: {header: {frame_id: map}, pose: {position: {x: 1.5, y: 0.0}, orientation: {w: 1.0}}}}" 2>&1)

  if echo "$out" | grep -q "SUCCEEDED"; then
    ok "Nav2 hat das Ziel erreicht (SUCCEEDED) - echte Planung + virtuelle Fahrt."
    record "N1 Nav2 virtuell" "OK" "navigate_to_pose SUCCEEDED"
  else
    bad "Ziel nicht erreicht. Letzte Ausgabe: $(echo "$out" | tail -3)"
    record "N1 Nav2 virtuell" "FEHLER" "kein SUCCEEDED (Log: $log)"
  fi
  stop_bg "$pid"
}

# --------------------------------------------------------------------------
#  Stufe N2 [NEU] - Koenigstest: komplette Mission mit ECHTEM Nav2
#  iPhone-/LLM-Kette in echt: Auftrag -> mission_manager -> BT ->
#  Nav2 faehrt (virtuell), Arm/Wahrnehmung als Mock -> success.
# --------------------------------------------------------------------------
stage_N2() {
  banner "N2 [NEU] - Mission mit echtem Nav2 (Koenigstest ohne Hardware)"
  need_ros || { record "N2 Mission+Nav2" "UEBERSPRUNGEN" "ros2 fehlt"; return; }
  if ! ros2 pkg prefix nav2_bt_navigator >/dev/null 2>&1; then
    record "N2 Mission+Nav2" "UEBERSPRUNGEN" "ros-humble-navigation2 fehlt"
    return
  fi

  local log="$LOGDIR/n2_nav_mission.log"
  info "Starte dry_run_nav_mission.launch.py (Nav2 + Mocks ohne Nav + BT + mission_manager) ..."
  local pid
  pid=$(launch_bg "$log" ros2 launch mock_servers dry_run_nav_mission.launch.py)
  info "Warte aktiv auf Nav2 + Missions-Kette (max 90 s) ..."
  if ! wait_action_server "navigate_to_pose" 90; then
    bad "Nav2-Action-Server kam nicht hoch. Log: $log"
    record "N2 Mission+Nav2" "FEHLER" "navigate_to_pose nicht verfuegbar"
    stop_bg "$pid"
    return
  fi
  sleep 3   # mission_manager/BT nachziehen lassen

  info "Sende pick_and_place (Ablage 'Tisch' aus dem Pose-Katalog) ..."
  timeout 4 ros2 topic pub -r 2 /mission_manager/command_json std_msgs/msg/String \
    "{data: '{\"type\":\"pick_and_place\",\"object\":\"Tasse\",\"room\":\"Kueche\",\"target\":\"Tisch\"}'}" \
    >/dev/null 2>&1 &

  # Fahrtwege + Mock-Phasen: grosszuegig 180 s.
  local bt_ok=1
  wait_log_contains "$log" "Mission beendet mit Status: SUCCESS" 180 || bt_ok=0
  local mm_ok=1
  wait_topic_contains "/mission_manager/status_json" '"state": "success"' 10 || mm_ok=0
  # Beweis "echtes Nav2": der Nav-Mock darf NICHT gelaufen sein.
  local mock_nav=0
  grep -q "\[mock\] NavigateToPose" "$log" 2>/dev/null && mock_nav=1

  if [ $bt_ok -eq 1 ] && [ $mm_ok -eq 1 ] && [ $mock_nav -eq 0 ]; then
    ok "Mission success MIT echtem Nav2 (kein Mock-Nav im Log)."
    record "N2 Mission+Nav2" "OK" "BT SUCCESS + status success + Nav2 real"
  elif [ $mock_nav -eq 1 ]; then
    bad "Mock-Navigation wurde benutzt - provide_navigation-Schalter pruefen."
    record "N2 Mission+Nav2" "FEHLER" "Mock-Nav statt Nav2 gelaufen"
  else
    bad "Mission nicht erfolgreich (bt=$bt_ok mm=$mm_ok). Log: $log"
    record "N2 Mission+Nav2" "FEHLER" "bt=$bt_ok mm=$mm_ok"
  fi
  stop_bg "$pid"
}

# --------------------------------------------------------------------------
#  Stufe D1 - robot_face (NEU): Gesichts-Controller + Anzeige
# --------------------------------------------------------------------------
stage_D1() {
  banner "D1 [NEU] - robot_face: Gesichts-Controller + 7-Zoll-Anzeige"
  need_ros || { record "D1 robot_face" "UEBERSPRUNGEN" "ros2 fehlt"; return; }

  local log="$LOGDIR/d1_face.log"
  local pid
  pid=$(launch_bg "$log" ros2 launch robot_face robot_face.launch.py with_rosbridge:=true)
  info "Warte 4 s auf Nodestart ..."; sleep 4

  if wait_topic_contains "/face/state_json" "expression" 10; then
    ok "/face/state_json liefert Ausdruck-Daten."
  else
    bad "/face/state_json lieferte nichts - face_controller gestartet?"
    record "D1 robot_face" "FEHLER" "/face/state_json ohne Daten"
    stop_bg "$pid"
    return
  fi

  info "Anzeige testen: http://localhost:8081 (auf dem 7-Zoll-Display bzw. Kiosk-Browser)"
  info "Testereignis senden: alarm fuer 3 s"
  ros2 topic pub --once /face/event std_msgs/msg/String \
    "{data: '{\"expression\": \"alarm\", \"prio\": 90, \"ttl_s\": 3}'}" >/dev/null 2>&1
  pause

  if ask_jn "Zeigt das Display ein passendes, sauber animiertes Gesicht (inkl. Alarm-Test eben)?"; then
    ok "Bestaetigt."
    record "D1 robot_face" "OK" "manuell bestaetigt, /face/state_json aktiv"
  else
    bad "Nicht bestaetigt."
    record "D1 robot_face" "FEHLER" "manuell verneint"
  fi
  stop_bg "$pid"
}

# --------------------------------------------------------------------------
#  Stufe D2 - handeye_calibration (NEU): Paket-Grundcheck
#  (volle Kalibrierung erst sinnvoll, wenn der echte Arm dran ist - siehe
#   KONZEPT_KALIBRIERUNG_OAK_ARM.md, Stufe A)
# --------------------------------------------------------------------------
stage_D2() {
  banner "D2 [NEU] - handeye_calibration: Paket-Grundcheck"
  need_ros || { record "D2 handeye_calibration" "UEBERSPRUNGEN" "ros2 fehlt"; return; }

  local prefix
  prefix=$(ros2 pkg prefix handeye_calibration 2>/dev/null)
  if [[ "$prefix" != *"/install"* ]]; then
    bad "Paket handeye_calibration nicht gefunden (Build fehlt?)."
    record "D2 handeye_calibration" "FEHLER" "pkg prefix leer"
    return
  fi
  ok "Paket gefunden: $prefix"

  # ament_python installiert console_scripts unter lib/<pkg>/ (nicht im PATH) ->
  # korrekt ueber 'ros2 run' aufrufen; Fallback auf ein evtl. im PATH liegendes.
  if ros2 run handeye_calibration handeye_solve --help >/dev/null 2>&1 \
     || { command -v handeye_solve >/dev/null 2>&1 && handeye_solve --help >/dev/null 2>&1; }; then
    ok "handeye_solve laeuft (--help ok, OpenCV/numpy vorhanden, keine ROS-Abhaengigkeit fuer diesen Teil)."
  else
    warn "handeye_solve --help lieferte einen Fehler (OpenCV/numpy pruefen, siehe Paket-README)."
  fi

  warn "Vollstaendiger Kalibrierlauf braucht den ECHTEN Arm (/joint_states) - siehe"
  warn "KONZEPT_KALIBRIERUNG_OAK_ARM.md Stufe A. Hier nur Grundcheck, kein Datensammeln."
  record "D2 handeye_calibration" "OK" "Paket vorhanden, Kalibrierlauf folgt nach Arm-Integration (Stufe A)"
}

# --------------------------------------------------------------------------
#  Menue
# --------------------------------------------------------------------------
declare -A STAGE_FN=(
  [B0]=stage_B0 [B0b]=stage_B0b [A1]=stage_A1
  [B1-RViz]=stage_B1_rviz [B1-Basis]=stage_B1_basis [B1-VL53]=stage_B1_vl53
  [B2-OAK]=stage_B2_oak [B2-RS485]=stage_B2_rs485
  [B3]=stage_B3 [B4]=stage_B4
  [C1]=stage_C1 [C2]=stage_C2 [C3]=stage_C3 [C4]=stage_C4
  [K1]=stage_K1 [K2]=stage_K2 [K4]=stage_K4 [K5]=stage_K5
  [N1]=stage_N1 [N2]=stage_N2 [D1]=stage_D1 [D2]=stage_D2
)
STAGE_ORDER=(B0 B0b A1 K1 K2 K4 K5 N1 N2 B1-RViz B1-Basis B1-VL53 B2-OAK B2-RS485 B3 B4 C1 C2 C3 C4 D1 D2)
# Vollautomatischer Software-Finaldurchlauf (keine Hardware, keine Rueckfragen):
SOFTWARE_ORDER=(B0 B0b A1 K1 K2 K4 K5 N1 N2 D2)

run_stage_by_id() {
  local id="$1"
  local fn="${STAGE_FN[$id]:-}"
  if [ -z "$fn" ]; then
    bad "Unbekannte Stufe: $id"
    return 1
  fi
  echo "## Lauf $(date '+%Y-%m-%d %H:%M') - Stufe $id" >> "$REPORT"
  "$fn"
}

run_all() {
  echo "## Lauf $(date '+%Y-%m-%d %H:%M') - alle Stufen" >> "$REPORT"
  local id
  for id in "${STAGE_ORDER[@]}"; do
    "${STAGE_FN[$id]}"
  done
  print_summary
}

# Der FINALE Software-Durchlauf: vollautomatisch, keine Hardware noetig.
run_software() {
  echo "## Lauf $(date '+%Y-%m-%d %H:%M') - SOFTWARE-FINAL (${SOFTWARE_ORDER[*]})" >> "$REPORT"
  local id
  for id in "${SOFTWARE_ORDER[@]}"; do
    "${STAGE_FN[$id]}"
  done
  print_summary
}

print_summary() {
  banner "Ergebnisprotokoll: $REPORT"
  tail -40 "$REPORT"
}

show_menu() {
  echo
  echo -e "${BOLD}Pruefplan Jetson - Stufen (Kuerzel wie in Roboter_Pruefplan.md):${NC}"
  local i=1 id
  for id in "${STAGE_ORDER[@]}"; do
    printf '  %2d) %s\n' "$i" "$id"
    i=$((i + 1))
  done
  echo "   S) SOFTWARE-FINAL: ${SOFTWARE_ORDER[*]} (vollautomatisch)"
  echo "   A) Alle der Reihe nach (B2-RS485 bleibt einzeln abgesichert)"
  echo "   R) Ergebnisprotokoll anzeigen"
  echo "   Q) Beenden"
}

main_menu() {
  while true; do
    show_menu
    read -r -p "Auswahl: " wahl
    case "$wahl" in
      [Qq]) break ;;
      [Rr]) print_summary ;;
      [Aa]) run_all ;;
      [Ss]) run_software ;;
      ''|*[!0-9]*)
        if [ -n "${STAGE_FN[$wahl]:-}" ]; then
          run_stage_by_id "$wahl"
        else
          echo "Bitte Zahl, Kuerzel, A, R oder Q eingeben."
        fi
        ;;
      *)
        local idx=$((wahl - 1))
        if [ "$idx" -ge 0 ] && [ "$idx" -lt "${#STAGE_ORDER[@]}" ]; then
          run_stage_by_id "${STAGE_ORDER[$idx]}"
        else
          echo "Ungueltige Nummer."
        fi
        ;;
    esac
  done
}

# --------------------------------------------------------------------------
#  Einstiegspunkt
# --------------------------------------------------------------------------
[ -f "$REPORT" ] || echo "# Pruefplan-Ergebnisse roboter_ws" > "$REPORT"

case "${1:-}" in
  --software) run_software ;;
  --alle) run_all ;;
  --stage) run_stage_by_id "${2:-}" ;;
  --hilfe|--help|-h)
    echo "Benutzung: $0 [--software | --alle | --stage KUERZEL | (kein Argument = Menue)]"
    echo "  --software = FINALER vollautomatischer Durchlauf ohne Hardware:"
    echo "               ${SOFTWARE_ORDER[*]}"
    echo "Alle Stufen: ${STAGE_ORDER[*]}"
    ;;
  *) main_menu ;;
esac
