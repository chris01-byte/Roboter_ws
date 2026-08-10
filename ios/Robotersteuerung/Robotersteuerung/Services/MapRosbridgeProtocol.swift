import Foundation

enum MapRosbridgeProtocolError: Error, LocalizedError, Sendable, Equatable {
    case invalidTextFrame
    case invalidMapPayload

    var errorDescription: String? {
        switch self {
        case .invalidTextFrame:
            return "Der rosbridge-Kartenrahmen enthält kein gültiges JSON."
        case .invalidMapPayload:
            return "Die /map-Nachricht hat nicht die erwartete OccupancyGrid-Struktur."
        }
    }
}

enum MapRosbridgeProtocol {
    static let topic = "/map"
    static let subscriptionID = "amadeus-map"

    private static let encoder: JSONEncoder = {
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.sortedKeys]
        return encoder
    }()

    private static let decoder = JSONDecoder()

    static func subscribeFrame() throws -> String {
        try encode(SubscribeFrame(
            op: "subscribe",
            id: subscriptionID,
            topic: topic,
            throttleRate: 1_000,
            queueLength: 1
        ))
    }

    static func unsubscribeFrame() throws -> String {
        try encode(UnsubscribeFrame(
            op: "unsubscribe",
            id: subscriptionID,
            topic: topic
        ))
    }

    static func decodeMap(from text: String) throws -> RobotMapSnapshot? {
        guard let data = text.data(using: .utf8) else {
            throw MapRosbridgeProtocolError.invalidTextFrame
        }

        let route: IncomingRoute
        do {
            route = try decoder.decode(IncomingRoute.self, from: data)
        } catch {
            throw MapRosbridgeProtocolError.invalidTextFrame
        }

        guard route.op == "publish", route.topic == topic else {
            return nil
        }

        do {
            let frame = try decoder.decode(MapPublishFrame.self, from: data)
            return try frame.msg.snapshot()
        } catch let error as RobotMapValidationError {
            throw error
        } catch {
            throw MapRosbridgeProtocolError.invalidMapPayload
        }
    }

    private static func encode<Value: Encodable>(_ value: Value) throws -> String {
        let data = try encoder.encode(value)
        guard let text = String(data: data, encoding: .utf8) else {
            throw MapRosbridgeProtocolError.invalidTextFrame
        }
        return text
    }
}

private struct SubscribeFrame: Encodable {
    let op: String
    let id: String
    let topic: String
    let throttleRate: Int
    let queueLength: Int

    enum CodingKeys: String, CodingKey {
        case op
        case id
        case topic
        case throttleRate = "throttle_rate"
        case queueLength = "queue_length"
    }
}

private struct UnsubscribeFrame: Encodable {
    let op: String
    let id: String
    let topic: String
}

private struct IncomingRoute: Decodable {
    let op: String?
    let topic: String?
}

private struct MapPublishFrame: Decodable {
    let msg: OccupancyGridMessage
}

private struct OccupancyGridMessage: Decodable {
    let header: Header
    let info: Metadata
    let data: [Int]

    struct Header: Decodable {
        let frameID: String

        enum CodingKeys: String, CodingKey {
            case frameID = "frame_id"
        }
    }

    struct Metadata: Decodable {
        let resolution: Double
        let width: Int
        let height: Int
        let origin: Pose
    }

    struct Pose: Decodable {
        let position: Point
        let orientation: Quaternion
    }

    struct Point: Decodable {
        let x: Double
        let y: Double
        let z: Double
    }

    struct Quaternion: Decodable {
        let x: Double
        let y: Double
        let z: Double
        let w: Double
    }

    func snapshot() throws -> RobotMapSnapshot {
        try RobotMapSnapshot(
            width: info.width,
            height: info.height,
            resolution: info.resolution,
            origin: RobotMapOrigin(
                positionX: info.origin.position.x,
                positionY: info.origin.position.y,
                positionZ: info.origin.position.z,
                orientationX: info.origin.orientation.x,
                orientationY: info.origin.orientation.y,
                orientationZ: info.origin.orientation.z,
                orientationW: info.origin.orientation.w
            ),
            frameID: header.frameID,
            cells: data
        )
    }
}
