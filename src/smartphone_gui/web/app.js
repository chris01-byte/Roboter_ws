// =====================================================================
//  app.js - Smartphone GUI (WP-4)
// =====================================================================
//  Keine externe Library: spricht rosbridge direkt per WebSocket.
//  Topics: command/status (mission_manager) + Not-Aus (safety_monitor, K4).
// =====================================================================
const commandTopic = '/mission_manager/command_json';
const statusTopic = '/mission_manager/status_json';
const estopRequestTopic = '/safety/estop_request';   // -> safety_monitor (K4)
const estopTopic = '/safety/estop';                  // Ist-Zustand (latched)

const fallbackRooms = ['Wohnzimmer', 'Kueche', 'Flur'];
const fallbackTargets = ['Tisch', 'Regal', 'Arbeitsplatte'];
const fallbackObjects = ['Tasse', 'Flasche', 'Fernbedienung'];

let ws = null;
let connected = false;
let lastStatus = null;
let estopActive = null;      // null = unbekannt (kein safety_monitor gesehen)
let lastRejection = '';      // zuletzt gemeldete Auftrags-Ablehnung

const el = (id) => document.getElementById(id);

function defaultBridgeUrl() {
  const host = window.location.hostname || 'localhost';
  return `ws://${host}:9090`;
}

function log(message) {
  const item = document.createElement('li');
  const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  item.textContent = `${time}  ${message}`;
  el('logList').prepend(item);
  while (el('logList').children.length > 40) {
    el('logList').lastElementChild.remove();
  }
}

function setConnectionState(ok, text) {
  connected = ok;
  const badge = el('rosState');
  badge.textContent = text;
  badge.className = `pill ${ok ? 'connected' : 'disconnected'}`;
}

function sendRosbridge(payload) {
  if (!ws || ws.readyState !== WebSocket.OPEN) {
    log('Keine rosbridge-Verbindung');
    return false;
  }
  ws.send(JSON.stringify(payload));
  return true;
}

function connect() {
  const url = el('bridgeUrl').value.trim() || defaultBridgeUrl();
  if (ws) {
    ws.close();
    ws = null;
  }

  setConnectionState(false, 'verbinde ...');
  log(`Verbinde ${url}`);
  ws = new WebSocket(url);

  ws.onopen = () => {
    setConnectionState(true, 'ROS verbunden');
    localStorage.setItem('robot_bridge_url', url);
    log('rosbridge verbunden');

    sendRosbridge({ op: 'advertise', topic: commandTopic, type: 'std_msgs/String' });
    sendRosbridge({ op: 'advertise', topic: estopRequestTopic, type: 'std_msgs/Bool' });
    sendRosbridge({ op: 'subscribe', topic: statusTopic, type: 'std_msgs/String' });
    sendRosbridge({ op: 'subscribe', topic: estopTopic, type: 'std_msgs/Bool' });
  };

  ws.onmessage = (event) => {
    let frame;
    try { frame = JSON.parse(event.data); } catch { return; }
    if (frame.op !== 'publish' || !frame.msg) { return; }
    if (frame.topic === statusTopic && frame.msg.data) {
      handleStatus(frame.msg.data);
    } else if (frame.topic === estopTopic) {
      updateEstop(frame.msg.data === true);
    }
  };

  ws.onclose = () => {
    setConnectionState(false, 'ROS getrennt');
    log('rosbridge getrennt');
  };

  ws.onerror = () => {
    setConnectionState(false, 'ROS Fehler');
    log('rosbridge Fehler');
  };
}

function publishCommand(command) {
  const ok = sendRosbridge({
    op: 'publish',
    topic: commandTopic,
    msg: { data: JSON.stringify(command) }
  });
  if (ok) {
    log(`Gesendet: ${describeCommand(command)}`);
  }
}

function describeCommand(command) {
  if (command.type === 'go_to_room') return `Fahre: ${command.room}`;
  if (command.type === 'pick_object') return `Greife: ${command.object}`;
  if (command.type === 'pick_and_place') return `Bringe ${command.object} nach ${command.room}/${command.target}`;
  if (command.type === 'explore') return 'Wohnung erkunden';
  if (command.type === 'cancel') return 'Mission stoppen';
  return command.type || 'Unbekannt';
}

// ---------------------- Not-Aus (safety_monitor, K4) -------------------
function updateEstop(active) {
  if (estopActive === active) { return; }
  estopActive = active;
  const btn = el('estopBtn');
  btn.classList.toggle('active', active);
  btn.textContent = active ? 'NOT-AUS FREIGEBEN' : 'NOT-AUS';
  log(active ? 'NOT-AUS AKTIV - Roboter angehalten' : 'Not-Aus freigegeben');
}

function toggleEstop() {
  // Unbekannter Zustand (kein safety_monitor sichtbar) -> sicherheitshalber ausloesen.
  const request = !(estopActive === true);
  const ok = sendRosbridge({
    op: 'publish',
    topic: estopRequestTopic,
    msg: { data: request }
  });
  if (ok) {
    log(request ? 'NOT-AUS gesendet' : 'Freigabe gesendet');
  }
}

function handleStatus(data) {
  let status;
  try { status = JSON.parse(data); } catch { return; }
  lastStatus = status;

  const state = status.state || 'unknown';
  const phase = status.phase || '-';
  const message = status.message || '';
  const progress = Math.max(0, Math.min(1, Number(status.progress || 0)));

  el('missionLine').textContent = message || phase;
  el('phaseText').textContent = phase;
  el('missionState').textContent = state;
  el('missionState').className = `pill ${state}`;
  el('progressBar').style.width = `${Math.round(progress * 100)}%`;
  el('activeCommand').textContent = describeCommand(status.active_command || {}) || '-';

  // KI-Server-Anzeige (link_monitor via mission_manager, Befund A4).
  const ki = el('kiState');
  if (status.offboard_available === true) {
    ki.textContent = 'KI verbunden';
    ki.className = 'pill connected';
  } else if (status.offboard_available === false) {
    ki.textContent = 'KI getrennt';
    ki.className = 'pill disconnected';
  } else {
    ki.textContent = 'KI unbekannt';
    ki.className = 'pill';
  }

  // Abgelehnte Auftraege sichtbar machen (S1: Ablehnung != Missionsfehler).
  const rejection = status.last_rejection || '';
  if (rejection && rejection !== lastRejection) {
    lastRejection = rejection;
    log(`Abgelehnt: ${rejection}`);
  }

  fillSelects(status.rooms || fallbackRooms, status.objects || fallbackObjects, status.targets || fallbackTargets);
}

function fillSelect(selectEl, values) {
  const old = selectEl.value;
  const cleaned = [...new Set(values.filter(Boolean))];
  selectEl.innerHTML = '';
  for (const value of cleaned) {
    const opt = document.createElement('option');
    opt.value = value;
    opt.textContent = value;
    selectEl.appendChild(opt);
  }
  if (cleaned.includes(old)) selectEl.value = old;
}

function fillSelects(rooms, objects, targets) {
  fillSelect(el('roomSelect'), rooms);
  fillSelect(el('carryRoomSelect'), rooms);
  fillSelect(el('pickObjectSelect'), objects);
  fillSelect(el('carryObjectSelect'), objects);
  fillSelect(el('targetSelect'), targets);
}

function setupTabs() {
  document.querySelectorAll('.tab').forEach((tab) => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.tab').forEach((t) => t.classList.remove('active'));
      document.querySelectorAll('.mission-card').forEach((p) => p.classList.remove('active'));
      tab.classList.add('active');
      el(`panel-${tab.dataset.tab}`).classList.add('active');
    });
  });
}

function setupButtons() {
  el('connectBtn').addEventListener('click', connect);
  el('goRoomBtn').addEventListener('click', () => publishCommand({
    type: 'go_to_room',
    room: el('roomSelect').value
  }));
  el('pickBtn').addEventListener('click', () => publishCommand({
    type: 'pick_object',
    object: el('pickObjectSelect').value
  }));
  el('carryBtn').addEventListener('click', () => publishCommand({
    type: 'pick_and_place',
    object: el('carryObjectSelect').value,
    room: el('carryRoomSelect').value,
    target: el('targetSelect').value
  }));
  el('exploreBtn').addEventListener('click', () => publishCommand({ type: 'explore' }));
  el('estopBtn').addEventListener('click', toggleEstop);
  el('cancelBtn').addEventListener('click', () => publishCommand({ type: 'cancel' }));
  el('refreshBtn').addEventListener('click', () => {
    if (lastStatus) handleStatus(JSON.stringify(lastStatus));
    log('Status aktualisiert');
  });
}

function init() {
  el('bridgeUrl').value = localStorage.getItem('robot_bridge_url') || defaultBridgeUrl();
  fillSelects(fallbackRooms, fallbackObjects, fallbackTargets);
  setupTabs();
  setupButtons();
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('sw.js').catch(() => {});
  }
  connect();
}

window.addEventListener('DOMContentLoaded', init);
