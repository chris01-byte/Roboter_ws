import Foundation
import Testing
@testable import Robotersteuerung

struct RobotMapProtocolTests {
    @Test
    func mapSubscriptionFramesContainOnlyTheRequiredFields() throws {
        let subscribe = try jsonObject(MapRosbridgeProtocol.subscribeFrame())
        #expect(Set(subscribe.keys) == [
            "op",
            "id",
            "topic",
            "throttle_rate",
            "queue_length"
        ])
        #expect(subscribe["op"] as? String == "subscribe")
        #expect(subscribe["id"] as? String == "amadeus-map")
        #expect(subscribe["topic"] as? String == "/map")
        #expect(subscribe["throttle_rate"] as? Int == 1_000)
        #expect(subscribe["queue_length"] as? Int == 1)

        let unsubscribe = try jsonObject(MapRosbridgeProtocol.unsubscribeFrame())
        #expect(Set(unsubscribe.keys) == ["op", "id", "topic"])
        #expect(unsubscribe["op"] as? String == "unsubscribe")
        #expect(unsubscribe["id"] as? String == "amadeus-map")
        #expect(unsubscribe["topic"] as? String == "/map")
    }

    @Test
    func decodesValidOccupancyGridPublish() throws {
        let frame = try mapFrame(
            width: 3,
            height: 2,
            resolution: 0.05,
            frameID: "map",
            cells: [-1, 0, 10, 50, 99, 100]
        )

        let decoded = try MapRosbridgeProtocol.decodeMap(from: frame)
        let map = try #require(decoded)
        #expect(map.width == 3)
        #expect(map.height == 2)
        #expect(abs(map.resolution - 0.05) < 0.000_001)
        #expect(map.frameID == "map")
        #expect(map.origin.positionX == -1.25)
        #expect(map.origin.positionY == 2.5)
        #expect(map.origin.orientationW == 1)
        #expect(map.cells == [-1, 0, 10, 50, 99, 100])
        #expect(map.rgbaPixels().count == 3 * 2 * 4)
    }

    @Test
    func rgbaRenderingMirrorsRowsVertically() throws {
        let frame = try mapFrame(
            width: 2,
            height: 2,
            cells: [
                -1, 0,   // untere OccupancyGrid-Zeile
                50, 100  // obere OccupancyGrid-Zeile
            ]
        )
        let decoded = try MapRosbridgeProtocol.decodeMap(from: frame)
        let map = try #require(decoded)

        #expect(map.rgbaPixels() == [
            128, 128, 128, 255, // 50 %, obere Bildzeile
            0, 0, 0, 255,       // belegt
            127, 127, 127, 255, // unbekannt, untere Bildzeile
            255, 255, 255, 255  // frei
        ])
    }

    @Test
    func rejectsWrongDataLength() throws {
        let frame = try mapFrame(width: 3, height: 2, cells: [0, 0, 0])

        do {
            _ = try MapRosbridgeProtocol.decodeMap(from: frame)
            Issue.record("Eine Karte mit falscher Datenlänge hätte abgelehnt werden müssen")
        } catch let error as RobotMapValidationError {
            #expect(error == .invalidDataLength(expected: 6, actual: 3))
            #expect(error.localizedDescription.contains("erwartet 6 Zellwerte"))
        }
    }

    @Test
    func rejectsInvalidResolution() throws {
        let frame = try mapFrame(
            width: 1,
            height: 1,
            resolution: 0,
            cells: [0]
        )

        do {
            _ = try MapRosbridgeProtocol.decodeMap(from: frame)
            Issue.record("Eine Karte ohne positive Auflösung hätte abgelehnt werden müssen")
        } catch let error as RobotMapValidationError {
            #expect(error == .invalidResolution(0))
            #expect(error.localizedDescription.contains("Kartenauflösung"))
        }
    }

    @Test
    func rejectsMapsAboveCellLimitBeforeCheckingPayloadLength() throws {
        let frame = try mapFrame(
            width: 2_001,
            height: 2_000,
            cells: []
        )

        do {
            _ = try MapRosbridgeProtocol.decodeMap(from: frame)
            Issue.record("Eine Karte oberhalb des Größenlimits hätte abgelehnt werden müssen")
        } catch let error as RobotMapValidationError {
            #expect(
                error == .cellLimitExceeded(
                    actual: 4_002_000,
                    maximum: RobotMapSnapshot.maximumCellCount
                )
            )
        }
    }

    @Test
    func rejectsCellCountOverflow() throws {
        do {
            _ = try RobotMapSnapshot(
                width: Int.max,
                height: 2,
                resolution: 0.05,
                origin: validOrigin,
                frameID: "map",
                cells: []
            )
            Issue.record("Überlaufende Kartenabmessungen hätten abgelehnt werden müssen")
        } catch let error as RobotMapValidationError {
            #expect(error == .cellCountOverflow(width: Int.max, height: 2))
        }
    }

    @Test(arguments: [-2, 101])
    func rejectsOccupancyValuesOutsideRosRange(value: Int) throws {
        let frame = try mapFrame(width: 1, height: 1, cells: [value])

        do {
            _ = try MapRosbridgeProtocol.decodeMap(from: frame)
            Issue.record("Der ungültige Kartenwert \(value) hätte abgelehnt werden müssen")
        } catch let error as RobotMapValidationError {
            #expect(error == .invalidOccupancyValue(index: 0, value: value))
            #expect(error.localizedDescription.contains("-1 und 100"))
        }
    }

    @Test
    func rejectsOriginWithZeroQuaternion() throws {
        let frame = try mapFrame(
            width: 1,
            height: 1,
            cells: [0],
            orientationW: 0
        )

        do {
            _ = try MapRosbridgeProtocol.decodeMap(from: frame)
            Issue.record("Ein Kartenursprung ohne gültige Orientierung hätte abgelehnt werden müssen")
        } catch let error as RobotMapValidationError {
            #expect(error == .invalidOrigin)
        }
    }

    @Test
    func ignoresUnrelatedRosbridgePublish() throws {
        let frame = """
        {"op":"publish","topic":"/other","msg":{"anything":true}}
        """
        #expect(try MapRosbridgeProtocol.decodeMap(from: frame) == nil)
    }

    private var validOrigin: RobotMapOrigin {
        RobotMapOrigin(
            positionX: -1.25,
            positionY: 2.5,
            positionZ: 0,
            orientationX: 0,
            orientationY: 0,
            orientationZ: 0,
            orientationW: 1
        )
    }

    private func mapFrame(
        width: Int,
        height: Int,
        resolution: Double = 0.05,
        frameID: String = "map",
        cells: [Int],
        orientationW: Double = 1
    ) throws -> String {
        let object: [String: Any] = [
            "op": "publish",
            "topic": "/map",
            "msg": [
                "header": [
                    "stamp": ["sec": 123, "nanosec": 456],
                    "frame_id": frameID
                ],
                "info": [
                    "map_load_time": ["sec": 100, "nanosec": 0],
                    "resolution": resolution,
                    "width": width,
                    "height": height,
                    "origin": [
                        "position": ["x": -1.25, "y": 2.5, "z": 0],
                        "orientation": ["x": 0, "y": 0, "z": 0, "w": orientationW]
                    ]
                ],
                "data": cells
            ]
        ]
        let data = try JSONSerialization.data(withJSONObject: object, options: [.sortedKeys])
        return try #require(String(data: data, encoding: .utf8))
    }

    private func jsonObject(_ text: String) throws -> [String: Any] {
        let data = try #require(text.data(using: .utf8))
        return try #require(
            JSONSerialization.jsonObject(with: data) as? [String: Any]
        )
    }
}
