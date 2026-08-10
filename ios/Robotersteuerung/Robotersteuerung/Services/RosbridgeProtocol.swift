import Foundation

enum RosbridgeTopics {
    static let command = "/mission_manager/command_json"
    static let status = "/mission_manager/status_json"
    static let estopRequest = "/safety/estop_request"
    static let estop = "/safety/estop"
}

enum RosbridgeEvent: Equatable {
    case status(MissionStatus)
    case estop(Bool)
}

enum RosbridgeProtocolError: LocalizedError {
    case invalidTextFrame
    case invalidStatusPayload

    var errorDescription: String? {
        switch self {
        case .invalidTextFrame:
            return "Ungültiger rosbridge-Datenrahmen."
        case .invalidStatusPayload:
            return "Der Missionsstatus enthält kein gültiges JSON."
        }
    }
}

enum RosbridgeProtocol {
    private static let encoder: JSONEncoder = {
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.sortedKeys]
        return encoder
    }()

    private static let decoder = JSONDecoder()

    static func setupFrames() throws -> [String] {
        try [
            encode(TopicFrame(
                op: "advertise",
                topic: RosbridgeTopics.command,
                type: "std_msgs/String"
            )),
            encode(TopicFrame(
                op: "advertise",
                topic: RosbridgeTopics.estopRequest,
                type: "std_msgs/Bool"
            )),
            encode(TopicFrame(
                op: "subscribe",
                topic: RosbridgeTopics.status,
                type: "std_msgs/String"
            )),
            encode(TopicFrame(
                op: "subscribe",
                topic: RosbridgeTopics.estop,
                type: "std_msgs/Bool"
            ))
        ]
    }

    static func commandFrame(_ command: RobotCommand) throws -> String {
        let commandData = try encoder.encode(command)
        guard let commandJSON = String(data: commandData, encoding: .utf8) else {
            throw RosbridgeProtocolError.invalidTextFrame
        }
        return try encode(StringPublishFrame(
            op: "publish",
            topic: RosbridgeTopics.command,
            msg: .init(data: commandJSON)
        ))
    }

    static func estopFrame(active: Bool) throws -> String {
        try encode(BoolPublishFrame(
            op: "publish",
            topic: RosbridgeTopics.estopRequest,
            msg: .init(data: active)
        ))
    }

    static func decodeEvent(from text: String) throws -> RosbridgeEvent? {
        guard let data = text.data(using: .utf8) else {
            throw RosbridgeProtocolError.invalidTextFrame
        }
        let frame = try decoder.decode(IncomingFrame.self, from: data)
        guard frame.op == "publish", let topic = frame.topic, let value = frame.msg?.data else {
            return nil
        }

        switch (topic, value) {
        case let (RosbridgeTopics.status, .string(statusJSON)):
            guard let statusData = statusJSON.data(using: .utf8) else {
                throw RosbridgeProtocolError.invalidStatusPayload
            }
            do {
                let status = try decoder.decode(MissionStatus.self, from: statusData)
                guard status.isCompleteSnapshot else {
                    throw RosbridgeProtocolError.invalidStatusPayload
                }
                return .status(status)
            } catch {
                throw RosbridgeProtocolError.invalidStatusPayload
            }
        case let (RosbridgeTopics.estop, .bool(active)):
            return .estop(active)
        default:
            return nil
        }
    }

    private static func encode<Value: Encodable>(_ value: Value) throws -> String {
        let data = try encoder.encode(value)
        guard let text = String(data: data, encoding: .utf8) else {
            throw RosbridgeProtocolError.invalidTextFrame
        }
        return text
    }
}

private struct TopicFrame: Encodable {
    let op: String
    let topic: String
    let type: String
}

private struct StringPublishFrame: Encodable {
    struct Message: Encodable {
        let data: String
    }

    let op: String
    let topic: String
    let msg: Message
}

private struct BoolPublishFrame: Encodable {
    struct Message: Encodable {
        let data: Bool
    }

    let op: String
    let topic: String
    let msg: Message
}

private struct IncomingFrame: Decodable {
    let op: String?
    let topic: String?
    let msg: IncomingMessage?
}

private struct IncomingMessage: Decodable {
    let data: RosbridgeScalar
}

private enum RosbridgeScalar: Decodable {
    case string(String)
    case bool(Bool)
    case number(Double)
    case null

    init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        if container.decodeNil() {
            self = .null
        } else if let bool = try? container.decode(Bool.self) {
            self = .bool(bool)
        } else if let string = try? container.decode(String.self) {
            self = .string(string)
        } else if let number = try? container.decode(Double.self) {
            self = .number(number)
        } else {
            throw DecodingError.typeMismatch(
                RosbridgeScalar.self,
                .init(
                    codingPath: decoder.codingPath,
                    debugDescription: "rosbridge msg.data muss String, Bool, Zahl oder null sein."
                )
            )
        }
    }
}
