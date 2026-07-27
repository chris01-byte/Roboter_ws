#!/usr/bin/env python3
# ============================================================================
#  semantic_perception_node.py  -  Open-Vocabulary-Wahrnehmung (WP-5 Baustein B)
#  ---------------------------------------------------------------------------
#  ZWECK:
#    Erkennt Objekte per TEXT-Anfrage ("finde die Tasse") ohne Neutraining und
#    liefert ihre 3D-Pose ueber den BESTEHENDEN Service GetObjectPose. Damit
#    bleibt der Behavior-Tree UNVERAENDERT - er ruft weiter get_object_pose auf.
#    Optional fuellt der Node den Missionskatalog (Objekte/Raeume) dynamisch.
#
#  ARCHITEKTUR:
#    - Kann OFFBOARD (RTX-3090-Server) oder perspektivisch auf der OAK-NPU laufen.
#    - Ersetzt/ergaenzt das object_world_model aus der Gesamtdoku.
#
#  MODELL-BACKEND (Parameter model_backend):
#    "stub"      -> simulierte Erkennung fuer den Trockentest (Standard).
#    "yoloworld" -> YOLO-World (open-vocabulary) via ultralytics, IMPLEMENTIERT.
#    "owlvit"    -> Platzhalter fuer OWL-ViT / NanoOWL.
#    yoloworld benoetigt: pip install ultralytics + RGB/Depth/CameraInfo-Topics.
#
#  SCHNITTSTELLEN:
#    Service : <service_name> (Standard /world_model/get_object_pose)  GetObjectPose
#    Subscribe: <rgb_topic> (sensor_msgs/Image)   [fuer echte Modelle]
#    Publish : <catalog_topic> (std_msgs/String)  dynamischer Katalog (optional)
#    TF      : <camera_frame> -> <global_frame>    [fuer echte 3D-Projektion]
#
#  ALLE PARAMETER -> config/semantic_perception_params.yaml.
# ============================================================================

import json
from typing import List, Optional, Tuple

import rclpy
from rclpy.node import Node
from rclpy.duration import Duration
from rclpy.qos import QoSProfile, QoSDurabilityPolicy, QoSReliabilityPolicy

from sensor_msgs.msg import Image, CameraInfo
from geometry_msgs.msg import PoseStamped, PointStamped
from std_msgs.msg import String
from robot_interfaces.srv import GetObjectPose

import tf2_ros
import tf2_geometry_msgs  # noqa: F401  (registriert do_transform fuer PointStamped)


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
        self._rgb_topic      = self.declare_parameter('rgb_topic', '/oak/rgb/image_rect').value
        self._global_frame   = self.declare_parameter('global_frame', 'map').value
        self._camera_frame   = self.declare_parameter('camera_frame', 'oak_rgb_camera_optical_frame').value
        self._conf_threshold = float(self.declare_parameter('confidence_threshold', 0.35).value)
        self._class_queries  = list(self.declare_parameter(
            'class_queries', ['Tasse', 'Flasche', 'Fernbedienung', 'Werkzeug', 'Schluessel']).value)
        self._publish_catalog = bool(self.declare_parameter('publish_catalog', True).value)
        self._catalog_topic   = self.declare_parameter('catalog_topic', '/semantic/catalog_json').value
        self._catalog_period  = float(self.declare_parameter('catalog_period_s', 5.0).value)
        self._known_rooms     = list(self.declare_parameter(
            'known_rooms', ['Wohnzimmer', 'Kueche', 'Flur']).value)
        self._stub_position   = list(self.declare_parameter('stub_position', [1.0, 0.0, 0.5]).value)
        self._stub_confidence = float(self.declare_parameter('stub_confidence', 0.8).value)
        # --- Echtes Modell (YOLO-World) + 3D-Projektion ---
        self._depth_topic     = self.declare_parameter('depth_topic', '/oak/stereo/image_raw').value
        self._caminfo_topic   = self.declare_parameter('camera_info_topic', '/oak/rgb/camera_info').value
        self._model_path      = self.declare_parameter('model_path', 'yolov8s-worldv2.pt').value
        self._depth_scale     = float(self.declare_parameter('depth_scale', 0.001).value)  # mm -> m
        # --- Objekt-Gedaechtnis / semantische Karte (Befund K2) ---
        # Ein Hintergrund-Scan erkennt laufend und merkt sich Objekte im map-Frame.
        # So findet get_object_pose ein Objekt auch, wenn es GERADE nicht im Bild
        # ist (z.B. nach dem Erkunden) - GetObjectPose ist als Weltmodell definiert.
        self._scan_period_s = float(self.declare_parameter('scan_period_s', 2.0).value)
        self._memory_ttl_s  = float(self.declare_parameter('memory_ttl_s', 0.0).value)  # 0 = nie verfallen
        self._live_fallback = bool(self.declare_parameter('live_fallback', True).value)

        # -------------------------------------------------------------------
        #  Laufzeit-Zustand
        # -------------------------------------------------------------------
        self._last_image: Optional[Image] = None
        self._last_depth: Optional[Image] = None
        self._camera_info: Optional[CameraInfo] = None
        self._model = None            # lazy geladenes YOLO-World-Modell
        self._model_failed = False    # True, wenn Laden fehlschlug (kein Retry-Spam)
        # Objekt-Gedaechtnis: name.lower() -> {'name', 'pose'(map), 'conf', 'stamp'}
        self._memory = {}

        # TF fuer die 3D-Projektion (Kamera -> map) bei echten Modellen.
        self._tf_buffer = tf2_ros.Buffer()
        self._tf_listener = tf2_ros.TransformListener(self._tf_buffer, self)

        # -------------------------------------------------------------------
        #  ROS-Schnittstellen
        # -------------------------------------------------------------------
        self.create_subscription(Image, self._rgb_topic, self._on_image, 1)
        self.create_subscription(Image, self._depth_topic, self._on_depth, 1)
        self.create_subscription(CameraInfo, self._caminfo_topic, self._on_caminfo, 1)
        self._service = self.create_service(
            GetObjectPose, self._service_name, self._on_get_object_pose)

        # Hintergrund-Scan fuellt das Objekt-Gedaechtnis (K2).
        self.create_timer(self._scan_period_s, self._scan_cb)

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
                "(RGB/Depth/CameraInfo). Fehlt etwas, faellt der Node auf den Stub zurueck.")
        elif self._backend != 'stub':
            self.get_logger().warn(
                f"Backend '{self._backend}' ist noch ein PLATZHALTER (nur stub/yoloworld "
                "implementiert). -> Stub-Verhalten.")

    # ======================= Kamera-Eingang =============================
    def _on_image(self, msg: Image):
        self._last_image = msg   # letztes RGB-Bild fuer die Modell-Inferenz

    def _on_depth(self, msg: Image):
        self._last_depth = msg   # letztes Tiefenbild fuer die 3D-Projektion

    def _on_caminfo(self, msg: CameraInfo):
        self._camera_info = msg  # Kamera-Intrinsics (K-Matrix)

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
        for cls in self._class_queries:
            det = self._detect(cls)
            if det is not None:
                self._remember(cls, det[0], det[1])

    def _remember(self, name: str, pose: PoseStamped, conf: float):
        self._memory[name.lower()] = {
            'name': name, 'pose': pose, 'conf': float(conf),
            'stamp': self.get_clock().now()}

    def _recall(self, query: str):
        """Bestes (konfidentestes, frisches) Gedaechtnis-Objekt zur Anfrage.
        Rueckgabe (pose, conf, alter_s) oder None. Tolerant/teilstring."""
        q = query.lower()
        now = self.get_clock().now()
        best = None
        for key, e in self._memory.items():
            if key not in q and q not in key:
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
        # yoloworld / owlvit -> echtes Modell (aktuell Platzhalter -> Stub-Rueckfall)
        result = self._detect_with_model(query)
        return result if result is not None else self._detect_stub(query)

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
        q = query.lower()
        return any(item.lower() in q or q in item.lower() for item in self._class_queries)

    # ------------------------------------------------------------------
    #  ECHTE MODELL-INTEGRATION - YOLO-World (open-vocabulary)
    #  Alle schweren Importe sind LAZY -> Node laeuft auch ohne die
    #  Bibliotheken (dann Stub-Rueckfall). In ROS/GPU NICHT getestet;
    #  API-Stand: ultralytics YOLOWorld.
    # ------------------------------------------------------------------
    def _ensure_model(self):
        """Laedt das YOLO-World-Modell einmalig (lazy). None bei Fehler."""
        if self._model is not None or self._model_failed:
            return self._model
        try:
            from ultralytics import YOLOWorld   # pip install ultralytics
            self._model = YOLOWorld(self._model_path)
            self.get_logger().info(f"YOLO-World geladen: {self._model_path}")
        except Exception as exc:
            self._model_failed = True
            self.get_logger().error(
                f"YOLO-World nicht ladbar ({exc}) - 'pip install ultralytics' + Gewichte "
                "pruefen. -> Stub-Rueckfall.")
        return self._model

    def _detect_with_model(self, query: str) -> Optional[Tuple[PoseStamped, float]]:
        """Open-Vocabulary-Erkennung: Text-Query -> 2D-Box -> 3D-Pose (map)."""
        if self._backend != 'yoloworld':
            return None   # owlvit / NanoOWL hier separat einhaengen
        model = self._ensure_model()
        if model is None or self._last_image is None:
            return None
        try:
            from cv_bridge import CvBridge
            rgb = CvBridge().imgmsg_to_cv2(self._last_image, desired_encoding='bgr8')
        except Exception as exc:
            self.get_logger().warn(f"Bildkonvertierung fehlgeschlagen ({exc}).")
            return None
        try:
            model.set_classes([query])   # open-vocabulary Text-Prompt
            results = model.predict(rgb, conf=self._conf_threshold, verbose=False)
        except Exception as exc:
            self.get_logger().warn(f"YOLO-World-Inferenz fehlgeschlagen ({exc}).")
            return None

        box = self._best_box(results)
        if box is None:
            return None
        u, v, conf = box
        point_cam = self._pixel_to_3d(u, v)
        if point_cam is None:
            return None
        pose = self._to_global(point_cam)
        return (pose, conf) if pose is not None else None

    @staticmethod
    def _best_box(results):
        """Beste Detektion (hoechste Confidence) als (u_mitte, v_mitte, conf)."""
        best = None
        try:
            for r in results:
                if r.boxes is None:
                    continue
                for b in r.boxes:
                    conf = float(b.conf[0])
                    x1, y1, x2, y2 = b.xyxy[0].tolist()
                    if best is None or conf > best[2]:
                        best = (0.5 * (x1 + x2), 0.5 * (y1 + y2), conf)
        except Exception:
            return None
        return best

    def _pixel_to_3d(self, u: float, v: float):
        """Pixel + Tiefe -> PointStamped im Kamera-Frame (Pinhole-Modell)."""
        if self._last_depth is None or self._camera_info is None:
            self.get_logger().warn("Tiefe/CameraInfo fehlt - keine 3D-Projektion.")
            return None
        try:
            import math
            from cv_bridge import CvBridge
            depth = CvBridge().imgmsg_to_cv2(self._last_depth, desired_encoding='passthrough')
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
    rclpy.init(args=args)
    node = SemanticPerception()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
