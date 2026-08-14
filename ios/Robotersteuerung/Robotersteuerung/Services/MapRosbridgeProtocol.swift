import Foundation

enum MapRosbridgeProtocolError: Error, LocalizedError, Sendable, Equatable {
    case invalidTextFrame
    case invalidMapPayload
    case invalidMapManagerStatus
    case invalidSemanticMapStatus
    case invalidCommand

    var errorDescription: String? {
        switch self {
        case .invalidTextFrame:
            return "Der rosbridge-Kartenrahmen enthält kein gültiges JSON."
        case .invalidMapPayload:
            return "Die /map-Nachricht hat nicht die erwartete OccupancyGrid-Struktur."
        case .invalidMapManagerStatus:
            return "Der Status des Kartenmanagers ist unvollständig oder ungültig."
        case .invalidSemanticMapStatus:
            return "Der semantische Kartenstatus ist unvollständig oder ungültig."
        case .invalidCommand:
            return "Der Kartenbefehl enthält ungültige Werte."
        }
    }
}

enum MapRosbridgeProtocol {
    static let mapTopic = "/map"
    static let mapSubscriptionID = "amadeus-map"
    static let mapManagerStatusTopic = "/robot_map_manager/status_json"
    static let mapManagerStatusSubscriptionID = "amadeus-map-manager-status"
    static let mapManagerCommandTopic = "/robot_map_manager/command_json"
    static let semanticStatusTopic = "/semantic_map/status_json"
    static let semanticStatusSubscriptionID = "amadeus-semantic-map-status"
    static let semanticCommandTopic = "/semantic_map/command_json"

    // Alte Namen bleiben für bestehende Test- und Aufrufstellen kompatibel.
    static let topic = mapTopic
    static let subscriptionID = mapSubscriptionID

    private static let encoder: JSONEncoder = {
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.sortedKeys]
        return encoder
    }()

    private static let decoder = JSONDecoder()

    static func subscribeFrame() throws -> String {
        try encode(SubscribeFrame(
            op: "subscribe",
            id: mapSubscriptionID,
            topic: mapTopic,
            type: nil,
            throttleRate: 1_000,
            queueLength: 1
        ))
    }

    static func unsubscribeFrame() throws -> String {
        try encode(UnsubscribeFrame(
            op: "unsubscribe",
            id: mapSubscriptionID,
            topic: mapTopic
        ))
    }

    static func connectionSetupFrames() throws -> [String] {
        [
            try encode(AdvertiseFrame(
                op: "advertise",
                topic: mapManagerCommandTopic,
                type: "std_msgs/String"
            )),
            try encode(AdvertiseFrame(
                op: "advertise",
                topic: semanticCommandTopic,
                type: "std_msgs/String"
            )),
            try subscribeFrame(),
            try encode(SubscribeFrame(
                op: "subscribe",
                id: mapManagerStatusSubscriptionID,
                topic: mapManagerStatusTopic,
                type: "std_msgs/String",
                throttleRate: nil,
                queueLength: 1
            )),
            try encode(SubscribeFrame(
                op: "subscribe",
                id: semanticStatusSubscriptionID,
                topic: semanticStatusTopic,
                type: "std_msgs/String",
                throttleRate: nil,
                queueLength: 1
            ))
        ]
    }

    static func connectionTeardownFrames() throws -> [String] {
        [
            try unsubscribeFrame(),
            try encode(UnsubscribeFrame(
                op: "unsubscribe",
                id: mapManagerStatusSubscriptionID,
                topic: mapManagerStatusTopic
            )),
            try encode(UnsubscribeFrame(
                op: "unsubscribe",
                id: semanticStatusSubscriptionID,
                topic: semanticStatusTopic
            )),
            try encode(UnadvertiseFrame(
                op: "unadvertise",
                topic: mapManagerCommandTopic
            )),
            try encode(UnadvertiseFrame(
                op: "unadvertise",
                topic: semanticCommandTopic
            ))
        ]
    }

    static func incomingTopic(from text: String) throws -> String? {
        guard let data = text.data(using: .utf8) else {
            throw MapRosbridgeProtocolError.invalidTextFrame
        }
        do {
            let route = try decoder.decode(IncomingRoute.self, from: data)
            guard route.op == "publish" else { return nil }
            return route.topic
        } catch {
            throw MapRosbridgeProtocolError.invalidTextFrame
        }
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

        guard route.op == "publish", route.topic == mapTopic else {
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

    static func decodeMapManagerStatus(
        from text: String
    ) throws -> RobotMapManagerStatusEnvelope? {
        guard let innerData = try decodeStringMessage(
            from: text,
            expectedTopic: mapManagerStatusTopic
        ) else {
            return nil
        }
        do {
            let status = try decoder.decode(
                RobotMapManagerStatusEnvelope.self,
                from: innerData
            )
            guard status.schemaVersion == 1,
                  !status.event.isEmpty,
                  !status.message.isEmpty else {
                throw MapRosbridgeProtocolError.invalidMapManagerStatus
            }
            if status.map.snapshotAvailable {
                guard let summary = status.map.summary,
                      SemanticMapReference.isFingerprint(summary.fingerprint),
                      summary.width > 0, summary.height > 0,
                      summary.resolution.isFinite, summary.resolution > 0 else {
                    throw MapRosbridgeProtocolError.invalidMapManagerStatus
                }
            }
            return status
        } catch let error as MapRosbridgeProtocolError {
            throw error
        } catch {
            throw MapRosbridgeProtocolError.invalidMapManagerStatus
        }
    }

    static func decodeSemanticMapStatus(
        from text: String
    ) throws -> SemanticMapStatusEnvelope? {
        guard let innerData = try decodeStringMessage(
            from: text,
            expectedTopic: semanticStatusTopic
        ) else {
            return nil
        }
        do {
            let status = try decoder.decode(
                SemanticMapStatusEnvelope.self,
                from: innerData
            )
            guard status.schemaVersion == 1,
                  !status.event.isEmpty,
                  !status.message.isEmpty,
                  let semanticMap = status.semanticMap,
                  semanticMap.isValid else {
                throw MapRosbridgeProtocolError.invalidSemanticMapStatus
            }
            return status
        } catch let error as MapRosbridgeProtocolError {
            throw error
        } catch {
            throw MapRosbridgeProtocolError.invalidSemanticMapStatus
        }
    }

    static func saveMapFrame(name: String, requestID: String) throws -> String {
        guard name == "wohnung", validRequestID(requestID) else {
            throw MapRosbridgeProtocolError.invalidCommand
        }
        return try stringPublishFrame(
            topic: mapManagerCommandTopic,
            command: SaveMapCommand(
                command: "save",
                name: name,
                requestID: requestID
            )
        )
    }

    static func upsertRoomFrame(
        room: SemanticRoom,
        mapFingerprint: String,
        baseRevision: Int,
        requestID: String
    ) throws -> String {
        guard SemanticMapReference.isFingerprint(mapFingerprint),
              baseRevision >= 0,
              validRequestID(requestID) else {
            throw MapRosbridgeProtocolError.invalidCommand
        }
        return try stringPublishFrame(
            topic: semanticCommandTopic,
            command: UpsertRoomCommand(
                command: "upsert_room",
                requestID: requestID,
                mapFingerprint: mapFingerprint,
                baseRevision: baseRevision,
                room: room
            )
        )
    }

    static func deleteRoomFrame(
        roomID: String,
        mapFingerprint: String,
        baseRevision: Int,
        requestID: String
    ) throws -> String {
        guard SemanticRoom.isValidID(roomID),
              SemanticMapReference.isFingerprint(mapFingerprint),
              baseRevision >= 0,
              validRequestID(requestID) else {
            throw MapRosbridgeProtocolError.invalidCommand
        }
        return try stringPublishFrame(
            topic: semanticCommandTopic,
            command: DeleteRoomCommand(
                command: "delete_room",
                requestID: requestID,
                mapFingerprint: mapFingerprint,
                baseRevision: baseRevision,
                roomID: roomID
            )
        )
    }

    private static func decodeStringMessage(
        from text: String,
        expectedTopic: String
    ) throws -> Data? {
        guard let data = text.data(using: .utf8) else {
            throw MapRosbridgeProtocolError.invalidTextFrame
        }
        let route: IncomingRoute
        do {
            route = try decoder.decode(IncomingRoute.self, from: data)
        } catch {
            throw MapRosbridgeProtocolError.invalidTextFrame
        }
        guard route.op == "publish", route.topic == expectedTopic else {
            return nil
        }
        do {
            let frame = try decoder.decode(StringPublishFrame.self, from: data)
            guard let innerData = frame.msg.data.data(using: .utf8) else {
                throw MapRosbridgeProtocolError.invalidTextFrame
            }
            return innerData
        } catch let error as MapRosbridgeProtocolError {
            throw error
        } catch {
            throw MapRosbridgeProtocolError.invalidTextFrame
        }
    }

    private static func stringPublishFrame<Command: Encodable>(
        topic: String,
        command: Command
    ) throws -> String {
        let innerData = try encoder.encode(command)
        guard let innerText = String(data: innerData, encoding: .utf8) else {
            throw MapRosbridgeProtocolError.invalidCommand
        }
        return try encode(OutgoingStringPublishFrame(
            op: "publish",
            topic: topic,
            msg: .init(data: innerText)
        ))
    }

    private static func validRequestID(_ value: String) -> Bool {
        guard !value.isEmpty, value.count <= 64,
              let first = value.utf8.first,
              (65...90).contains(first) || (97...122).contains(first) ||
                (48...57).contains(first) else {
            return false
        }
        return value.utf8.count == value.count && value.utf8.allSatisfy { byte in
            (65...90).contains(byte) || (97...122).contains(byte) ||
                (48...57).contains(byte) || byte == 95 || byte == 46 ||
                byte == 58 || byte == 45
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
    let type: String?
    let throttleRate: Int?
    let queueLength: Int?

    enum CodingKeys: String, CodingKey {
        case op
        case id
        case topic
        case type
        case throttleRate = "throttle_rate"
        case queueLength = "queue_length"
    }
}

private struct AdvertiseFrame: Encodable {
    let op: String
    let topic: String
    let type: String
}

private struct UnadvertiseFrame: Encodable {
    let op: String
    let topic: String
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

private struct StringPublishFrame: Decodable {
    let msg: Message

    struct Message: Decodable {
        let data: String
    }
}

private struct OutgoingStringPublishFrame: Encodable {
    let op: String
    let topic: String
    let msg: Message

    struct Message: Encodable {
        let data: String
    }
}

private struct SaveMapCommand: Encodable {
    let command: String
    let name: String
    let requestID: String

    enum CodingKeys: String, CodingKey {
        case command
        case name
        case requestID = "request_id"
    }
}

private struct UpsertRoomCommand: Encodable {
    let command: String
    let requestID: String
    let mapFingerprint: String
    let baseRevision: Int
    let room: SemanticRoom

    enum CodingKeys: String, CodingKey {
        case command
        case requestID = "request_id"
        case mapFingerprint = "map_fingerprint"
        case baseRevision = "base_revision"
        case room
    }
}

private struct DeleteRoomCommand: Encodable {
    let command: String
    let requestID: String
    let mapFingerprint: String
    let baseRevision: Int
    let roomID: String

    enum CodingKeys: String, CodingKey {
        case command
        case requestID = "request_id"
        case mapFingerprint = "map_fingerprint"
        case baseRevision = "base_revision"
        case roomID = "room_id"
    }
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
