#!/usr/bin/env bash
# Holt den gepinnten WCH-Treiber fuer den CH341A-USB-I2C-Adapter und baut ihn.
# Die Schritte mit root-Rechten werden NICHT ausgefuehrt, sondern am Ende
# ausgegeben - Kernelmodule zu installieren ist ein Eingriff ins System und
# gehoert in die Hand der anwesenden Person.
#
# WOZU: Ueber diesen Adapter haengen die beiden VL53L7CX des
# Nahbereichsschutzes. Ohne das Modul gibt es keinen CH341-I2C-Bus,
# vl53_near_field stirbt beim Start, und der collision_monitor reicht ohne
# Sensordaten jeden Fahrbefehl durch - ein Ausfall, der am 14.08.2026 voellig
# lautlos blieb.
#
# Kein "set -u": nicht noetig, und es bricht sonst an leeren Variablen.
set -eo pipefail

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
MANIFEST="${REPO_ROOT}/vendor_ch34x_mphsi.repos"
ZIEL="${CH34X_QUELLE:-$HOME/ch34x_mphsi_master_linux}"
PAKET="ch34x-mphsi"
VERSION="1.0"
GEPINNT="f33863fbbf322a85f960b1701e7148db0b7b2d85"

sag() { printf '%s\n' "$*"; }
fehler() { printf 'FEHLER: %s\n' "$*" >&2; exit 1; }

[ -r "$MANIFEST" ] || fehler "Manifest fehlt: $MANIFEST"
command -v git >/dev/null || fehler "git fehlt"
[ -d "/lib/modules/$(uname -r)/build" ] \
  || fehler "Kernel-Header fehlen: /lib/modules/$(uname -r)/build"

# --- Quelle holen oder pruefen -------------------------------------------
if [ ! -d "$ZIEL/.git" ]; then
    sag ">>> Hole Treiberquelle nach $ZIEL"
    if command -v vcs >/dev/null; then
        mkdir -p "$(dirname "$ZIEL")"
        vcs import "$(dirname "$ZIEL")" < "$MANIFEST"
    else
        git clone https://github.com/WCHSoftGroup/ch34x_mphsi_master_linux.git "$ZIEL"
        git -C "$ZIEL" checkout --quiet "$GEPINNT"
    fi
else
    sag ">>> Treiberquelle vorhanden: $ZIEL"
fi

IST="$(git -C "$ZIEL" rev-parse HEAD)"
if [ "$IST" != "$GEPINNT" ]; then
    fehler "Quelle steht auf $IST, erwartet ist $GEPINNT.
Nichts wurde zurueckgesetzt - Stand klaeren, bevor gebaut wird."
fi
if ! git -C "$ZIEL" diff --quiet; then
    fehler "Der Treiberquellcode ist veraendert. Vendor-Code bleibt unberuehrt;
bitte die Aenderungen klaeren."
fi
sag ">>> Gepinnter Stand bestaetigt: $GEPINNT"

# --- dkms.conf bereitstellen ---------------------------------------------
VORLAGE="${REPO_ROOT}/src/vl53_near_field/config/ch34x_dkms.conf.example"
if [ ! -f "$ZIEL/driver/dkms.conf" ] && [ -r "$VORLAGE" ]; then
    cp "$VORLAGE" "$ZIEL/driver/dkms.conf"
    sag ">>> dkms.conf aus dem Repo uebernommen"
fi

# --- Bauen (ohne root) ----------------------------------------------------
sag ">>> Baue gegen $(uname -r)"
make -C "$ZIEL/driver" clean >/dev/null 2>&1 || true
make -C "$ZIEL/driver" >/dev/null
MODUL="$ZIEL/driver/ch34x_mphsi_master.ko"
[ -f "$MODUL" ] || fehler "Modul wurde nicht erzeugt"
VM="$(modinfo "$MODUL" | awk '/^vermagic/{print $2}')"
[ "$VM" = "$(uname -r)" ] \
  || fehler "Modul hat vermagic $VM, laufender Kernel ist $(uname -r)"
sag ">>> Gebaut, vermagic $VM"

# --- Was root braucht, nur ausgeben --------------------------------------
cat <<ANLEITUNG

Der Rest braucht root und wird hier bewusst NICHT ausgefuehrt.

Einmalig, damit das Modul jedes Kernel-Update ueberlebt:

  sudo apt install -y dkms
  sudo ln -sfn $ZIEL/driver /usr/src/${PAKET}-${VERSION}
  sudo dkms add     -m $PAKET -v $VERSION
  sudo dkms build   -m $PAKET -v $VERSION
  sudo dkms install -m $PAKET -v $VERSION --force
  dkms status

Erwartet: "${PAKET}/${VERSION}, $(uname -r), $(uname -m): installed"
ohne Klammerzusatz. Ein "(WARNING! Diff between built and installed module!)"
heisst, dass in /lib/modules noch ein handgebautes Modul liegt; --force raeumt
das auf.

Danach pruefen - das ist der eigentliche Nachweis:

  python3 ${REPO_ROOT}/tools/kartierung/nahbereich_pruefen.py

ANLEITUNG
