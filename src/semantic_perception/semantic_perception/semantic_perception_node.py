#!/usr/bin/env python3
# ============================================================================
#  semantic_perception_node.py  -  Open-Vocabulary-Wahrnehmung (WP-5 Baustein B)
#  ---------------------------------------------------------------------------
#  ZWECK:
#    Erkennt Objekte per TEXT-Anfrage ("finde die Tasse") ohne Neutraining und
#    liefert ihre 3D-Pose ueber den BESTEHENDEN Service GetObjectPose. Damit
#    bleibt der Behavior-Tree UNVERAENDERT - er ruft weiter get_object_pose auf.
#    Optional publiziert der Node einen getrennten Wahrnehmungs-Diagnosekatalog;
#    er darf den manuellen Raumkatalog nicht ueberschreiben.
#
#  ARCHITEKTUR:
#    - Kann OFFBOARD (RTX-3090-Server) oder perspektivisch auf der OAK-NPU laufen.
#    - Ersetzt/ergaenzt das object_world_model aus der Gesamtdoku.
#
#  MODELL-BACKEND (Parameter model_backend):
#    "stub"      -> simulierte Erkennung fuer den Trockentest (Standard).
#    "yoloworld" -> YOLO-World (open-vocabulary) via ultralytics, IMPLEMENTIERT.
#    "owlvit"    -> Platzhalter fuer OWL-ViT / NanoOWL; meldet keine Treffer.
#    yoloworld benoetigt: pip install ultralytics + RGB/Depth/CameraInfo-Topics.
#    WICHTIG: Nur das explizite Backend "stub" darf simulierte Posen liefern.
#
#  SCHNITTSTELLEN:
#    Service : <service_name> (Standard /world_model/get_object_pose)  GetObjectPose
#    Subscribe: komprimiertes RGB, 16-Bit-Tiefen-PNG und CameraInfo
#    Publish : <catalog_topic> (std_msgs/String)  dynamischer Katalog (optional)
#    TF      : <camera_frame> -> <global_frame>    [fuer echte 3D-Projektion]
#
#  ALLE PARAMETER -> config/semantic_perception_params.yaml.
# ============================================================================

from collections import deque
import json
import time
from typing import Optional, Tuple

import rclpy
from rclpy.node import Node
from rclpy.duration import Duration
from rclpy.qos import (
    QoSHistoryPolicy,
    QoSProfile,
    QoSDurabilityPolicy,
    QoSReliabilityPolicy,
)

from sensor_msgs.msg import CameraInfo, CompressedImage, Image
from geometry_msgs.msg import PoseStamped, PointStamped
from std_msgs.msg import String
from robot_interfaces.srv import GetObjectPose

import tf2_ros
import tf2_geometry_msgs  # noqa: F401  (registriert do_transform fuer PointStamped)

from .stream_codec import (
    decode_depth_png,
    decode_rgb_jpeg,
    select_freshest_pair,
    stamp_seconds,
)
from .semantic_state import (
    SemanticStateError,
    bounded_object_status,
    localization_is_live,
    parse_localization_status,
)


DEFAULT_CLASS_QUERIES = [
    'Tasse', 'Flasche', 'Fernbedienung', 'Werkzeug', 'Schluessel']
DEFAULT_MODEL_CLASS_PROMPTS = [
    'cup', 'bottle', 'remote control', 'tool', 'key']


class SemanticPerception(Node):
    def __init__(self):
        super().__init__('semantic_perception')

        # -------------------------------------------------------------------
        #  Parameter
        # -------------------------------------------------------------------
        self._backend        = self.declare_parameter('model_backend', 'stub').value
        self._service_name   = self.declare_parameter('service_name', '/world_model/get_object_pose').value
        # [KORRIGIERT 27.07.2026] Defaults auf die real vom depthai_ros_driver
        # gelieferten Namen. Frueher '/oak/rgb' bzw. camera_rgb_optical_frame -
        # beides existiert im Betrieb nicht.
        self._compressed_input = bool(self.declare_parameter(
            'compressed_input', True).value)
        self._rgb_topic      = self.declare_parameter(
            'rgb_topic', '/oak/semantic/rgb/compressed').value
        self._global_frame   = self.declare_parameter('global_frame', 'map').value
        self._camera_frame   = self.declare_parameter('camera_frame', 'oak_rgb_camera_optical_frame').value
        self._base_frame     = self.declare_parameter('base_frame', 'base_link').value
        self._conf_threshold = float(self.declare_parameter('confidence_threshold', 0.35).value)
        self._class_queries  = list(self.declare_parameter(
            'class_queries', DEFAULT_CLASS_QUERIES).value)
        self._model_class_prompts = list(self.declare_parameter(
            'model_class_prompts', DEFAULT_MODEL_CLASS_PROMPTS).value)
        self._model_prompt_by_class = self._build_model_prompt_map(
            self._class_queries, self._model_class_prompts)
        self._publish_catalog = bool(self.declare_parameter('publish_catalog', True).value)
        self._catalog_topic = self.declare_parameter(
            'catalog_topic', '/semantic/perception_catalog_json').value
        self._catalog_period  = float(self.declare_parameter('catalog_period_s', 5.0).value)
        self._known_rooms     = list(self.declare_parameter(
            'known_rooms', ['Wohnzimmer', 'Kueche', 'Flur']).value)
        self._stub_position   = list(self.declare_parameter('stub_position', [1.0, 0.0, 0.5]).value)
        self._stub_confidence = float(self.declare_parameter('stub_confidence', 0.8).value)
        # --- Echtes Modell (YOLO-World) + 3D-Projektion ---
        self._depth_topic     = self.declare_parameter(
            'depth_topic', '/oak/semantic/depth/compressed').value
        self._caminfo_topic   = self.declare_parameter(
            'camera_info_topic', '/oak/semantic/camera_info').value
        self._model_path      = self.declare_parameter('model_path', 'yolov8s-worldv2.pt').value
        self._depth_scale     = float(self.declare_parameter('depth_scale', 0.001).value)  # mm -> m
        self._max_input_age_s = float(self.declare_parameter(
            'max_input_age_s', 2.0).value)
        self._max_rgb_depth_skew_s = float(self.declare_parameter(
            'max_rgb_depth_skew_s', 0.20).value)
        self._input_pair_queue_size = int(self.declare_parameter(
            'input_pair_queue_size', 10).value)
        if self._max_input_age_s <= 0.0 or self._max_rgb_depth_skew_s < 0.0:
            raise ValueError('Zeitgrenzen der Wahrnehmung sind ungueltig')
        if not 2 <= self._input_pair_queue_size <= 120:
            raise ValueError('input_pair_queue_size muss zwischen 2 und 120 liegen')
        # --- Objekt-Gedaechtnis / semantische Karte (Befund K2) ---
        # Ein Hintergrund-Scan erkennt laufend und merkt sich Objekte im map-Frame.
        # So findet get_object_pose ein Objekt auch, wenn es GERADE nicht im Bild
        # ist (z.B. nach dem Erkunden) - GetObjectPose ist als Weltmodell definiert.
        self._scan_period_s = float(self.declare_parameter('scan_period_s', 2.0).value)
        self._memory_ttl_s  = float(self.declare_parameter('memory_ttl_s', 0.0).value)  # 0 = nie verfallen
        self._live_fallback = bool(self.declare_parameter('live_fallback', True).value)
        self._localization_status_topic = self.declare_parameter(
            'localization_status_topic', '/localization/status_json').value
        self._localization_max_age_s = float(self.declare_parameter(
            'localization_max_age_s', 1.0).value)
        self._require_localization = bool(self.declare_parameter(
            'require_localization_for_map', True).value)
        self._object_map_topic = self.declare_parameter(
            'object_map_topic', '/semantic/object_map_json').value
        self._observation_topic = self.declare_parameter(
            'observation_status_topic',
            '/semantic/observation_status_json').value
        self._status_period_s = float(self.declare_parameter(
            'semantic_status_period_s', 1.0).value)
        self._observation_ttl_s = float(self.declare_parameter(
            'observation_ttl_s', 5.0).value)
        self._maximum_objects = int(self.declare_parameter(
            'maximum_object_markers', 64).value)
        if (
                self._localization_max_age_s <= 0.0 or
                self._status_period_s <= 0.0 or
                self._observation_ttl_s <= 0.0 or
                not 1 <= self._maximum_objects <= 256):
            raise ValueError('Semantik-/Lokalisierungsstatusparameter sind ungueltig')

        # -------------------------------------------------------------------
        #  Laufzeit-Zustand
        # -------------------------------------------------------------------
        self._last_image: Optional[Image] = None
        self._last_depth: Optional[Image] = None
        self._camera_info: Optional[CameraInfo] = None
        self._last_image_received_s = 0.0
        self._last_depth_received_s = 0.0
        self._image_frames = deque(maxlen=self._input_pair_queue_size)
        self._depth_frames = deque(maxlen=self._input_pair_queue_size)
        self._model = None            # lazy geladenes YOLO-World-Modell
        self._model_failed = False    # True, wenn Laden fehlschlug (kein Retry-Spam)
        # Objekt-Gedaechtnis: name.lower() -> {'name', 'pose'(map), 'conf', 'stamp'}
        self._memory = {}
        self._observations = {}
        self._localization_status = None
        self._localization_received_s = 0.0
        self._localization_last_backend_time = None
        self._localization_progress_count = 0
        self._localization_errors = 0
        self._active_map_fingerprint = None

        # TF fuer die 3D-Projektion (Kamera -> map) bei echten Modellen.
        self._tf_buffer = tf2_ros.Buffer()
        self._tf_listener = tf2_ros.TransformListener(self._tf_buffer, self)

        # -------------------------------------------------------------------
        #  ROS-Schnittstellen
        # -------------------------------------------------------------------
        sensor_qos = QoSProfile(
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=1,
            reliability=QoSReliabilityPolicy.BEST_EFFORT,
            durability=QoSDurabilityPolicy.VOLATILE,
        )
        image_type = CompressedImage if self._compressed_input else Image
        self.create_subscription(
            image_type, self._rgb_topic, self._on_image, sensor_qos)
        self.create_subscription(
            image_type, self._depth_topic, self._on_depth, sensor_qos)
        self.create_subscription(
            CameraInfo, self._caminfo_topic, self._on_caminfo, sensor_qos)
        localization_qos = QoSProfile(depth=1)
        localization_qos.reliability = QoSReliabilityPolicy.RELIABLE
        localization_qos.durability = QoSDurabilityPolicy.TRANSIENT_LOCAL
        self.create_subscription(
            String, self._localization_status_topic,
            self._on_localization_status, localization_qos)
        self._service = self.create_service(
            GetObjectPose, self._service_name, self._on_get_object_pose)

        # Hintergrund-Scan fuellt das Objekt-Gedaechtnis (K2).
        self.create_timer(self._scan_period_s, self._scan_cb)

        status_qos = QoSProfile(depth=1)
        status_qos.reliability = QoSReliabilityPolicy.RELIABLE
        status_qos.durability = QoSDurabilityPolicy.TRANSIENT_LOCAL
        self._object_map_pub = self.create_publisher(
            String, self._object_map_topic, status_qos)
        self._observation_pub = self.create_publisher(
            String, self._observation_topic, status_qos)
        self.create_timer(self._status_period_s, self._publish_semantic_status)

        if self._publish_catalog:
            latched = QoSProfile(depth=1)
            latched.reliability = QoSReliabilityPolicy.RELIABLE
            latched.durability = QoSDurabilityPolicy.TRANSIENT_LOCAL
            self._catalog_pub = self.create_publisher(String, self._catalog_topic, latched)
            self.create_timer(self._catalog_period, self._publish_catalog_cb)

        self.get_logger().info(
            f"semantic_perception bereit (Backend='{self._backend}'). "
            f"Service '{self._service_name}', erkennbar: {self._class_queries}")
        if self._backend == 'yoloworld':
            self.get_logger().info(
                "Backend 'yoloworld' aktiv - benoetigt ultralytics + Gewichte + Kamera "
                "(RGB/Depth/CameraInfo). Fehlende Voraussetzungen liefern keinen Treffer. "
                f"Eingang={'komprimiert' if self._compressed_input else 'roh'}, "
                f"Modell-Prompts: {self._model_class_prompts}")
        elif self._backend != 'stub':
            self.get_logger().warn(
                f"Backend '{self._backend}' ist nicht implementiert "
                "(nur stub/yoloworld). Erkennung bleibt fail-closed.")

    # ======================= Kamera-Eingang =============================
    def _on_image(self, msg: Image):
        self._image_frames.append((
            msg, time.monotonic(), stamp_seconds(msg.header.stamp)))
        self._refresh_input_pair()

    def _on_depth(self, msg: Image):
        self._depth_frames.append((
            msg, time.monotonic(), stamp_seconds(msg.header.stamp)))
        self._refresh_input_pair()

    def _on_caminfo(self, msg: CameraInfo):
        self._camera_info = msg  # Kamera-Intrinsics (K-Matrix)

    def _on_localization_status(self, msg: String):
        try:
            status = parse_localization_status(msg.data)
        except SemanticStateError as exc:
            self._localization_errors += 1
            self._localization_status = None
            self._localization_progress_count = 0
            self.get_logger().warn(
                f'Ungueltiger Lokalisierungsstatus ({exc}); Kartenposen gesperrt.')
            return

        old_fingerprint = self._active_map_fingerprint
        new_fingerprint = status.map_fingerprint
        if old_fingerprint != new_fingerprint:
            self._memory.clear()
            self._active_map_fingerprint = new_fingerprint
        previous_time = self._localization_last_backend_time
        if previous_time is None or status.backend_time < previous_time:
            self._localization_progress_count = 1
        elif status.backend_time > previous_time:
            self._localization_progress_count += 1
        self._localization_last_backend_time = status.backend_time
        self._localization_status = status
        self._localization_received_s = time.monotonic()

    def _localization_ready(self) -> bool:
        if not self._require_localization or self._global_frame != 'map':
            return True
        return localization_is_live(
            self._localization_status,
            received_s=self._localization_received_s,
            now_s=time.monotonic(),
            progress_count=self._localization_progress_count,
            maximum_age_s=self._localization_max_age_s,
        )

    # ======================= Service: GetObjectPose =====================
    def _on_get_object_pose(self, request, response):
        query = (request.class_name or '').strip()
        self.get_logger().info(f"GetObjectPose angefragt: '{query}'")
        response.pose = PoseStamped()
        response.pose.header.frame_id = self._global_frame

        # 1) Aus dem Gedaechtnis (Weltmodell): auch wenn das Objekt gerade
        #    NICHT im Bild ist, aber vorher schon einmal gesehen wurde.
        recalled = self._recall(query) if query else None
        if recalled is not None:
            pose, conf, age = recalled
            response.found = True
            response.pose = pose
            response.confidence = float(conf)
            self.get_logger().info(
                f"'{query}' aus Gedaechtnis bei ({pose.pose.position.x:.2f}, "
                f"{pose.pose.position.y:.2f}), conf={conf:.2f}, zuletzt vor {age:.1f}s.")
            return response

        # 2) Cache-Miss -> aktuelles Bild live pruefen und das Ergebnis merken.
        det = self._detect(query) if (query and self._live_fallback) else None
        if det is not None:
            pose, conf = det
            self._remember(query, pose, conf)
            response.found = True
            response.pose = pose
            response.confidence = float(conf)
            self.get_logger().info(
                f"'{query}' live erkannt + gemerkt bei ({pose.pose.position.x:.2f}, "
                f"{pose.pose.position.y:.2f}), conf={conf:.2f}.")
            return response

        response.found = False
        response.confidence = 0.0
        self.get_logger().info(f"'{query}' nicht gefunden (weder Gedaechtnis noch aktuell).")
        return response

    # ======================= Objekt-Gedaechtnis (K2) ====================
    def _scan_cb(self):
        """Hintergrund-Scan: erkennt die bekannten Klassen im aktuellen Bild
        und merkt sich Treffer im map-Frame. Baut so die semantische Karte auf,
        waehrend der Roboter faehrt/erkundet."""
        if self._backend == 'yoloworld':
            results = self._predict_current_image()
            if results is None:
                return
            for cls in self._class_queries:
                det = self._detection_from_results(cls, results)
                if det is not None:
                    self._remember(cls, det[0], det[1])
            return
        for cls in self._class_queries:
            det = self._detect(cls)
            if det is not None:
                self._remember(cls, det[0], det[1])

    def _remember(self, name: str, pose: PoseStamped, conf: float):
        if not self._localization_ready():
            return
        fingerprint = (
            None if self._localization_status is None
            else self._localization_status.map_fingerprint)
        self._memory[name.lower()] = {
            'name': name, 'pose': pose, 'conf': float(conf),
            'stamp': self.get_clock().now(),
            'last_seen_time': time.time(),
            'map_fingerprint': fingerprint,
        }

    def _recall(self, query: str):
        """Bestes (konfidentestes, frisches) Gedaechtnis-Objekt zur Anfrage.
        Rueckgabe (pose, conf, alter_s) oder None. Tolerant/teilstring."""
        if not self._localization_ready():
            return None
        q = query.lower()
        now = self.get_clock().now()
        fingerprint = (
            None if self._localization_status is None
            else self._localization_status.map_fingerprint)
        best = None
        for key, e in self._memory.items():
            if key not in q and q not in key:
                continue
            if e.get('map_fingerprint') != fingerprint:
                continue
            age = (now - e['stamp']).nanoseconds * 1e-9
            if self._memory_ttl_s > 0.0 and age > self._memory_ttl_s:
                continue   # veraltet -> ignorieren
            if best is None or e['conf'] > best[1]:
                best = (e['pose'], e['conf'], age)
        return best

    # ======================= Detektions-Dispatch ========================
    def _detect(self, query: str) -> Optional[Tuple[PoseStamped, float]]:
        if not query:
            return None
        if self._backend == 'stub':
            return self._detect_stub(query)
        if self._backend == 'yoloworld':
            return self._detect_with_model(query)
        # Ein reales oder unbekanntes Backend darf nie eine simulierte Pose
        # ausgeben. Fehlende Bilder, Tiefe, TF, Gewichte oder Implementierung
        # bedeuten deshalb immer "nicht gefunden".
        return None

    def _detect_stub(self, query: str) -> Optional[Tuple[PoseStamped, float]]:
        """Simulierte Erkennung fuer den Trockentest ohne echtes Modell.

        Liefert eine feste Pose (aus stub_position), wenn die Anfrage zu den
        bekannten class_queries passt (tolerant, case-insensitive).
        """
        if not self._matches_known(query):
            return None
        pose = PoseStamped()
        pose.header.frame_id = self._global_frame
        pose.header.stamp = self.get_clock().now().to_msg()
        pose.pose.position.x = float(self._stub_position[0])
        pose.pose.position.y = float(self._stub_position[1])
        pose.pose.position.z = float(self._stub_position[2])
        pose.pose.orientation.w = 1.0
        return pose, self._stub_confidence

    def _matches_known(self, query: str) -> bool:
        return self._canonical_class(query) is not None

    @staticmethod
    def _build_model_prompt_map(class_queries, model_class_prompts):
        """Build a fail-closed, one-to-one UI-class -> model-prompt map."""
        if len(class_queries) != len(model_class_prompts):
            raise ValueError(
                'class_queries und model_class_prompts muessen gleich lang sein')

        mapping = {}
        used_prompts = set()
        for canonical, prompt in zip(class_queries, model_class_prompts):
            canonical_key = str(canonical).strip().casefold()
            model_prompt = str(prompt).strip()
            prompt_key = model_prompt.casefold()
            if not canonical_key or not model_prompt:
                raise ValueError(
                    'class_queries und model_class_prompts duerfen nicht leer sein')
            if canonical_key in mapping:
                raise ValueError(f'Doppelte Objektklasse: {canonical}')
            if prompt_key in used_prompts:
                raise ValueError(f'Doppelter Modell-Prompt: {model_prompt}')
            mapping[canonical_key] = model_prompt
            used_prompts.add(prompt_key)
        return mapping

    def _canonical_class(self, query: str) -> Optional[str]:
        q = query.strip().casefold()
        if not q:
            return None
        for item in self._class_queries:
            normalized = item.strip().casefold()
            if normalized and (normalized in q or q in normalized):
                return item
        return None

    def _model_prompt_for_class(
            self, canonical_class: Optional[str]) -> Optional[str]:
        if not canonical_class:
            return None
        return self._model_prompt_by_class.get(
            canonical_class.strip().casefold())

    # ------------------------------------------------------------------
    #  ECHTE MODELL-INTEGRATION - YOLO-World (open-vocabulary)
    #  Alle schweren Importe sind LAZY -> Node laeuft auch ohne die
    #  Bibliotheken (dann fail-closed ohne Treffer). In ROS/GPU NICHT getestet;
    #  API-Stand: ultralytics YOLOWorld.
    # ------------------------------------------------------------------
    def _ensure_model(self):
        """Laedt das YOLO-World-Modell einmalig (lazy). None bei Fehler."""
        if self._model is not None or self._model_failed:
            return self._model
        try:
            from ultralytics import YOLOWorld   # pip install ultralytics
            model = YOLOWorld(self._model_path)
            # Einmal vor dem ersten predict() setzen. Ultralytics cached dabei
            # sein CLIP-Modell auf dem aktuellen Device. Wiederholtes
            # set_classes() nach dem automatischen CUDA-Wechsel mischt sonst
            # CPU-Tokens und GPU-Gewichte.
            model.set_classes(list(self._model_class_prompts))
            self._model = model
            self.get_logger().info(f"YOLO-World geladen: {self._model_path}")
        except Exception as exc:
            self._model_failed = True
            self.get_logger().error(
                f"YOLO-World nicht ladbar ({exc}) - 'pip install ultralytics' + Gewichte "
                "pruefen. Erkennung bleibt fail-closed.")
        return self._model

    def _input_is_fresh(self, received_s: float) -> bool:
        return (
            received_s > 0.0 and
            time.monotonic() - received_s <= self._max_input_age_s
        )

    def _refresh_input_pair(self) -> bool:
        """Atomically select matching RGB/depth messages from the WLAN stream."""
        pair = select_freshest_pair(
            self._image_frames,
            self._depth_frames,
            now_s=time.monotonic(),
            max_age_s=self._max_input_age_s,
            max_skew_s=self._max_rgb_depth_skew_s,
        )
        if pair is None:
            return False
        image_sample, depth_sample = pair
        self._last_image = image_sample[0]
        self._last_image_received_s = image_sample[1]
        self._last_depth = depth_sample[0]
        self._last_depth_received_s = depth_sample[1]
        return True

    def _rgb_array(self):
        if self._last_image is None:
            return None
        if self._compressed_input:
            return decode_rgb_jpeg(self._last_image.data)
        from cv_bridge import CvBridge
        return CvBridge().imgmsg_to_cv2(
            self._last_image, desired_encoding='bgr8')

    def _depth_array(self):
        if self._last_depth is None:
            return None
        if self._compressed_input:
            return decode_depth_png(self._last_depth.data)
        from cv_bridge import CvBridge
        return CvBridge().imgmsg_to_cv2(
            self._last_depth, desired_encoding='passthrough')

    def _predict_current_image(self):
        """Run YOLO exactly once for the newest fresh RGB frame."""
        if (
                not self._refresh_input_pair() or
                not self._input_is_fresh(self._last_image_received_s)):
            return None
        model = self._ensure_model()
        if model is None:
            return None
        try:
            rgb = self._rgb_array()
        except Exception as exc:
            self.get_logger().warn(f"Bildkonvertierung fehlgeschlagen ({exc}).")
            return None
        if rgb is None:
            return None
        try:
            return model.predict(
                rgb, conf=self._conf_threshold, verbose=False)
        except Exception as exc:
            self.get_logger().warn(f"YOLO-World-Inferenz fehlgeschlagen ({exc}).")
            return None

    def _detection_from_results(
            self, canonical_class: str, results
            ) -> Optional[Tuple[PoseStamped, float]]:
        target_prompt = self._model_prompt_for_class(canonical_class)
        if target_prompt is None:
            return None
        box = self._best_box(results, target_prompt)
        if box is None:
            return None
        u, v, conf = box
        point_cam = self._pixel_to_3d(u, v)
        if point_cam is None:
            return None
        self._record_observation(canonical_class, point_cam, conf, u, v)
        pose = self._to_global(point_cam)
        return (pose, conf) if pose is not None else None

    def _detect_with_model(self, query: str) -> Optional[Tuple[PoseStamped, float]]:
        """Open-Vocabulary-Erkennung: Text-Query -> 2D-Box -> 3D-Pose (map)."""
        if self._backend != 'yoloworld':
            return None   # owlvit / NanoOWL hier separat einhaengen
        canonical_class = self._canonical_class(query)
        if canonical_class is None:
            return None
        results = self._predict_current_image()
        if results is None:
            return None
        return self._detection_from_results(canonical_class, results)

    @staticmethod
    def _best_box(results, target_prompt: str):
        """Beste Box der angefragten Klasse als (u_mitte, v_mitte, conf)."""
        best = None
        wanted = target_prompt.strip().casefold()
        try:
            for r in results:
                if r.boxes is None:
                    continue
                for b in r.boxes:
                    class_index = int(b.cls[0])
                    if isinstance(r.names, dict):
                        detected_class = r.names.get(class_index, '')
                    else:
                        detected_class = r.names[class_index]
                    if str(detected_class).strip().casefold() != wanted:
                        continue
                    conf = float(b.conf[0])
                    x1, y1, x2, y2 = b.xyxy[0].tolist()
                    if best is None or conf > best[2]:
                        best = (0.5 * (x1 + x2), 0.5 * (y1 + y2), conf)
        except Exception:
            return None
        return best

    def _pixel_to_3d(self, u: float, v: float):
        """Pixel + Tiefe -> PointStamped im Kamera-Frame (Pinhole-Modell)."""
        if (
                self._last_depth is None or self._camera_info is None or
                not self._input_is_fresh(self._last_depth_received_s)):
            self.get_logger().warn("Tiefe/CameraInfo fehlt - keine 3D-Projektion.")
            return None
        try:
            import math
            if self._last_image is None:
                return None
            rgb_stamp = stamp_seconds(self._last_image.header.stamp)
            depth_stamp = stamp_seconds(self._last_depth.header.stamp)
            if abs(rgb_stamp - depth_stamp) > self._max_rgb_depth_skew_s:
                self.get_logger().warn(
                    "RGB/Tiefe zeitlich zu weit auseinander - keine 3D-Projektion.")
                return None
            depth = self._depth_array()
            if depth is None:
                return None
            di, dj = int(round(v)), int(round(u))
            if di < 0 or dj < 0 or di >= depth.shape[0] or dj >= depth.shape[1]:
                return None
            z = float(depth[di, dj]) * self._depth_scale
            if z <= 0.0 or not math.isfinite(z):
                return None
            k = self._camera_info.k          # 3x3 Intrinsics, row-major
            fx, fy, cx, cy = k[0], k[4], k[2], k[5]
            p = PointStamped()
            p.header.frame_id = self._camera_info.header.frame_id or self._camera_frame
            p.header.stamp = self._last_depth.header.stamp
            p.point.x = (u - cx) * z / fx
            p.point.y = (v - cy) * z / fy
            p.point.z = z
            return p
        except Exception as exc:
            self.get_logger().warn(f"3D-Projektion fehlgeschlagen ({exc}).")
            return None

    def _to_global(self, point_cam) -> Optional[PoseStamped]:
        """Transformiert einen Kamera-Punkt in den global_frame -> PoseStamped."""
        if not self._localization_ready():
            self.get_logger().warn(
                'Globale Lokalisierung nicht frisch bestaetigt; '
                'Objekt-Kartenpose bleibt gesperrt.')
            return None
        try:
            tp = self._tf_buffer.transform(
                point_cam, self._global_frame, timeout=Duration(seconds=0.5))
        except Exception as exc:
            self.get_logger().warn(
                f"TF {point_cam.header.frame_id}->{self._global_frame} fehlt ({exc}).")
            return None
        pose = PoseStamped()
        pose.header.frame_id = self._global_frame
        pose.header.stamp = self.get_clock().now().to_msg()
        pose.pose.position.x = tp.point.x
        pose.pose.position.y = tp.point.y
        pose.pose.position.z = tp.point.z
        pose.pose.orientation.w = 1.0
        return pose

    def _record_observation(
            self, canonical_class: str, point_cam: PointStamped,
            confidence: float, u: float, v: float) -> None:
        base_point = None
        try:
            base_point = self._tf_buffer.transform(
                point_cam, self._base_frame, timeout=Duration(seconds=0.5))
        except Exception:
            pass
        self._observations[canonical_class.casefold()] = {
            'name': canonical_class,
            'confidence': float(confidence),
            'pixel': [float(u), float(v)],
            'camera_frame': point_cam.header.frame_id,
            'camera_point': [
                float(point_cam.point.x), float(point_cam.point.y),
                float(point_cam.point.z)],
            'base_frame': self._base_frame,
            'base_point': None if base_point is None else [
                float(base_point.point.x), float(base_point.point.y),
                float(base_point.point.z)],
            'last_seen_time': time.time(),
        }

    def _publish_semantic_status(self):
        now = time.time()
        localization_ready = self._localization_ready()
        fingerprint = (
            None if self._localization_status is None
            else self._localization_status.map_fingerprint)
        try:
            object_payload = bounded_object_status(
                frame_id=self._global_frame,
                map_fingerprint=fingerprint,
                now=now,
                ready=localization_ready,
                memory=self._memory,
                maximum_objects=self._maximum_objects,
                memory_ttl_s=self._memory_ttl_s,
            )
        except SemanticStateError as exc:
            self.get_logger().warn(f'Objektkartenstatus nicht publizierbar ({exc}).')
            return
        object_payload['localization'] = {
            'required': self._require_localization and self._global_frame == 'map',
            'progress_count': self._localization_progress_count,
            'status_errors': self._localization_errors,
        }
        self._object_map_pub.publish(String(data=json.dumps(
            object_payload, ensure_ascii=False)))

        observations = []
        for entry in self._observations.values():
            age = max(0.0, now - entry['last_seen_time'])
            if age > self._observation_ttl_s:
                continue
            observation = dict(entry)
            observation['age_s'] = age
            observations.append(observation)
        observations.sort(
            key=lambda item: (-item['confidence'], item['name']))
        self._observation_pub.publish(String(data=json.dumps({
            'schema_version': 1,
            'ready': bool(observations),
            'time': now,
            'observations': observations[:self._maximum_objects],
        }, ensure_ascii=False)))

    # ======================= Dynamischer Katalog ========================
    def _publish_catalog_cb(self):
        """Publiziert die aktuell 'bekannten' Objekte/Raeume fuer den mission_manager.

        Im Stub sind das die konfigurierten Listen. Mit echtem Modell hier die
        tatsaechlich in der Szene erkannten Objekte/Raeume einsetzen.
        """
        seen = sorted({e['name'] for e in self._memory.values()})
        payload = {
            'objects': sorted(set(self._class_queries) | set(seen)),
            'seen': seen,                       # tatsaechlich erkannte Objekte (K2)
            'rooms': self._known_rooms,
            'source': f'semantic_perception:{self._backend}',
        }
        self._catalog_pub.publish(String(data=json.dumps(payload, ensure_ascii=False)))


def main(args=None):
    from rclpy.executors import ExternalShutdownException

    rclpy.init(args=args)
    node = SemanticPerception()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
