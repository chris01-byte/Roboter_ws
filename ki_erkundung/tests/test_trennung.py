"""Die Trennregeln der KI-Linie als Tests (README, MASTERPLAN §10).

* Der Lotse ist reines Python: Standardbibliothek, numpy, Pillow.
* Nichts in diesem Ordner sendet Fahrbefehle oder ruft Dienste und Aktionen.
* Nach außen spricht nur ``lotse/ki_rechner.py`` (mit dem KI-Rechner im Haus).
* Diese Linie hängt von keinem Paket der Hauptlinie ab.
* Im Ordner liegen keine Bilder, Scans oder Blickrunden.
"""
import ast
import sys
from pathlib import Path

WURZEL = Path(__file__).resolve().parents[1]
STANDARD = set(sys.stdlib_module_names)
NETZ = {'urllib', 'http', 'socket', 'requests', 'ftplib', 'smtplib', 'ssl', 'httpx',
        'aiohttp', 'websocket', 'websockets', 'paramiko'}


def einfuhren(datei: Path) -> set:
    """Oberste Modulnamen aller Einfuhren einer Datei (ohne relative)."""
    namen = set()
    for knoten in ast.walk(ast.parse(datei.read_text(encoding='utf-8'))):
        if isinstance(knoten, ast.Import):
            namen |= {alias.name.split('.')[0] for alias in knoten.names}
        elif isinstance(knoten, ast.ImportFrom) and knoten.level == 0 and knoten.module:
            namen.add(knoten.module.split('.')[0])
    return namen


def quelldateien(*unterordner):
    return sorted(p for name in unterordner for p in (WURZEL / name).rglob('*.py'))


def test_der_lotse_braucht_nur_standardbibliothek_numpy_und_pillow():
    assert quelldateien('lotse')
    for datei in quelldateien('lotse'):
        fremd = einfuhren(datei) - STANDARD - {'numpy', 'PIL', 'lotse'}
        assert not fremd, f'{datei.name} führt ein: {sorted(fremd)}'


def test_werkzeuge_haengen_von_keinem_paket_der_hauptlinie_ab():
    erlaubt = STANDARD | {'numpy', 'PIL', 'lotse', 'rclpy', 'sensor_msgs', 'nav_msgs',
                          'tf2_ros', 'beispielrunde_erzeugen'}
    for datei in quelldateien('werkzeuge'):
        fremd = einfuhren(datei) - erlaubt
        assert not fremd, f'{datei.name} führt ein: {sorted(fremd)}'


def test_nichts_sendet_fahrbefehle_oder_ruft_dienste_und_aktionen():
    verboten = ('create_publisher', 'ActionClient', 'create_client', 'cmd_vel',
                'set_parameters', 'ros2 topic pub')
    for datei in quelldateien('lotse', 'werkzeuge'):
        text = datei.read_text(encoding='utf-8')
        for wort in verboten:
            assert wort not in text, f'{datei.name} enthält {wort!r}'


def test_nach_aussen_spricht_nur_die_verbindung_zum_ki_rechner():
    for datei in quelldateien('lotse', 'werkzeuge'):
        netz = einfuhren(datei) & NETZ
        if datei.name == 'ki_rechner.py':
            assert netz == {'urllib', 'socket'}
            text = datei.read_text(encoding='utf-8')
            assert 'ProxyHandler({})' in text         # kein Umweg über einen Proxy
            assert "STANDARD_URL = 'http://localhost:11434'" in text
        else:
            assert not netz, f'{datei.name} führt ein: {sorted(netz)}'


def test_im_ordner_liegen_keine_bilder_scans_oder_blickrunden():
    verboten = {'.jpg', '.jpeg', '.png', '.bmp', '.npz', '.npy', '.bag', '.db3', '.mcap',
                '.pgm'}
    for datei in WURZEL.rglob('*'):
        if not datei.is_file() or '__pycache__' in datei.parts:
            continue
        assert datei.suffix.lower() not in verboten, datei
        assert datei.name not in ('meta.json', 'wahrheit.json', 'ergebnis.json'), datei
        assert not datei.name.startswith('scan_'), datei


def test_keine_ros_paketdatei_im_ordner():
    """Ohne package.xml sieht kein colcon-Build der Hauptlinie diesen Ordner."""
    assert not list(WURZEL.rglob('package.xml'))
    assert not list(WURZEL.rglob('setup.py'))
