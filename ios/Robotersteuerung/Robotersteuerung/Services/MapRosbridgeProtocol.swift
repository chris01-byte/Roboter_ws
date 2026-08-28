import Foundation

enum MapRosbridgeProtocolError: Error, LocalizedError, Sendable, Equatable {
    case invalidTextFrame
    case invalidMapPayload
    case invalidMapManagerStatus
    case invalidSemanticMapStatus
    case invalidRobotPose
    case invalidLocalizationStatus
    case invalidSemanticObjectMap
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
        case .invalidRobotPose:
            return "Die Roboterpose ist unvollständig oder ungültig."
        case .invalidLocalizationStatus:
            return "Der Lokalisierungsstatus ist unvollständig oder ungültig."
        case .invalidSemanticObjectMap:
            return "Die semantischen Objektmarker sind unvollständig oder ungültig."
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
    static let robotPoseTopic = "/robot_map_manager/robot_pose"
    static let robotPoseSubscriptionID = "amadeus-robot-map-pose"
    static let localizationStatusTopic = "/localization/status_json"
    static let localizationStatusSubscriptionID = "amadeus-localization-status"
    static let semanticObjectMapTopic = "/semantic/object_map_json"
    static let semanticObjectMapSubscriptionID = "amadeus-semantic-object-map"

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
                id: robotPoseSubscriptionID,
                topic: robotPoseTopic,
                type: "geometry_msgs/PoseStamped",
                throttleRate: 1_000,
                queueLength: 1
            )),
            try encode(SubscribeFrame(
                op: "subscribe",
                id: localizationStatusSubscriptionID,
                topic: localizationStatusTopic,
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
            )),
            try encode(SubscribeFrame(
                op: "subscribe",
                id: semanticObjectMapSubscriptionID,
                topic: semanticObjectMapTopic,
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
                id: robotPoseSubscriptionID,
                topic: robotPoseTopic
            )),
            try encode(UnsubscribeFrame(
                op: "unsubscribe",
                id: localizationStatusSubscriptionID,
                topic: localizationStatusTopic
            )),
            try encode(UnsubscribeFrame(
                op: "unsubscribe",
                id: semanticStatusSubscriptionID,
                topic: semanticStatusTopic
            )),
            try encode(UnsubscribeFrame(
                op: "unsubscribe",
                id: semanticObjectMapSubscriptionID,
                topic: semanticObjectMapTopic
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
            if let pose = status.pose, !pose.isValid {
                throw MapRosbridgeProtocolError.invalidMapManagerStatus
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

    static func decodeRobotPose(
        from text: String,
        receivedAt: Date = Date(),
        socketGeneration: UInt64 = 0
    ) throws -> RobotPoseSample? {
        guard let data = text.data(using: .utf8) else {
            throw MapRosbridgeProtocolError.invalidTextFrame
        }
        let route: IncomingRoute
        do {
            route = try decoder.decode(IncomingRoute.self, from: data)
        } catch {
            throw MapRosbridgeProtocolError.invalidTextFrame
        }
        guard route.op == "publish", route.topic == robotPoseTopic else {
            return nil
        }
        do {
            let frame = try decoder.decode(PosePublishFrame.self, from: data)
            let message = frame.msg
            let frameID = message.header.frameID.trimmingCharacters(
                in: .whitespacesAndNewlines
            )
            let values = [
                message.pose.position.x, message.pose.position.y,
                message.pose.position.z, message.pose.orientation.x,
                message.pose.orientation.y, message.pose.orientation.z,
                message.pose.orientation.w
            ]
            guard RobotFrameID.isValid(frameID), values.allSatisfy(\.isFinite),
                  message.header.stamp.sec >= 0,
                  (0..<1_000_000_000).contains(message.header.stamp.nanosec)
            else {
                throw MapRosbridgeProtocolError.invalidRobotPose
            }
            let quaternionLength = sqrt(
                message.pose.orientation.x * message.pose.orientation.x +
                message.pose.orientation.y * message.pose.orientation.y +
                message.pose.orientation.z * message.pose.orientation.z +
                message.pose.orientation.w * message.pose.orientation.w
            )
            guard quaternionLength.isFinite,
                  abs(quaternionLength - 1) <= 1e-3 else {
                throw MapRosbridgeProtocolError.invalidRobotPose
            }
            let (secondsNanoseconds, secondsOverflow) =
                message.header.stamp.sec.multipliedReportingOverflow(
                    by: 1_000_000_000
                )
            let (stampNanoseconds, additionOverflow) =
                secondsNanoseconds.addingReportingOverflow(
                    Int64(message.header.stamp.nanosec)
                )
            guard !secondsOverflow, !additionOverflow else {
                throw MapRosbridgeProtocolError.invalidRobotPose
            }
            let orientation = message.pose.orientation
            let yaw = atan2(
                2 * (orientation.w * orientation.z +
                     orientation.x * orientation.y),
                1 - 2 * (orientation.y * orientation.y +
                         orientation.z * orientation.z)
            )
            return RobotPoseSample(
                point: MapPoint(
                    x: message.pose.position.x,
                    y: message.pose.position.y
                ),
                z: message.pose.position.z,
                yaw: yaw,
                frameID: frameID,
                sourceStampNanoseconds: stampNanoseconds,
                receivedAt: receivedAt,
                socketGeneration: socketGeneration
            )
        } catch let error as MapRosbridgeProtocolError {
            throw error
        } catch {
            throw MapRosbridgeProtocolError.invalidRobotPose
        }
    }

    static func decodeLocalizationStatus(
        from text: String
    ) throws -> LocalizationStatusEnvelope? {
        guard let innerData = try decodeStringMessage(
            from: text,
            expectedTopic: localizationStatusTopic
        ) else { return nil }
        do {
            let status = try decoder.decode(
                LocalizationStatusEnvelope.self, from: innerData
            )
            guard status.isValid else {
                throw MapRosbridgeProtocolError.invalidLocalizationStatus
            }
            return status
        } catch let error as MapRosbridgeProtocolError {
            throw error
        } catch {
            throw MapRosbridgeProtocolError.invalidLocalizationStatus
        }
    }

    static func decodeSemanticObjectMap(
        from text: String
    ) throws -> SemanticObjectMapEnvelope? {
        guard let innerData = try decodeStringMessage(
            from: text,
            expectedTopic: semanticObjectMapTopic
        ) else { return nil }
        do {
            let status = try decoder.decode(
                SemanticObjectMapEnvelope.self, from: innerData
            )
            guard status.isValid else {
                throw MapRosbridgeProtocolError.invalidSemanticObjectMap
            }
            return status
        } catch let error as MapRosbridgeProtocolError {
            throw error
        } catch {
            throw MapRosbridgeProtocolError.invalidSemanticObjectMap
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

private struct PosePublishFrame: Decodable {
    let msg: PoseStampedMessage
}

private struct PoseStampedMessage: Decodable {
    let header: Header
    let pose: Pose

    struct Header: Decodable {
        let stamp: Stamp
        let frameID: String

        enum CodingKeys: String, CodingKey {
            case stamp
            case frameID = "frame_id"
        }
    }

    struct Stamp: Decodable {
        let sec: Int64
        let nanosec: Int
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
