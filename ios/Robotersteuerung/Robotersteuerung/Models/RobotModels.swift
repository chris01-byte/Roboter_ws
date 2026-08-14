import Foundation

enum MissionKind: String, CaseIterable, Identifiable {
    case room
    case pick
    case carry
    case explore

    var id: String { rawValue }

    var title: String {
        switch self {
        case .room: "Raum"
        case .pick: "Greifen"
        case .carry: "Bringen"
        case .explore: "Erkunden"
        }
    }

    var systemImage: String {
        switch self {
        case .room: "location.fill"
        case .pick: "hand.point.up.left.fill"
        case .carry: "shippingbox.fill"
        case .explore: "map.fill"
        }
    }
}

struct RobotCommand: Codable, Equatable {
    let type: String?
    let object: String?
    let room: String?
    let target: String?

    init(type: String, object: String? = nil, room: String? = nil, target: String? = nil) {
        self.type = type
        self.object = object
        self.room = room
        self.target = target
    }

    var description: String {
        switch type {
        case "go_to_room":
            return room.map { "Fahre: \($0)" } ?? "Fahre"
        case "pick_object":
            return object.map { "Greife: \($0)" } ?? "Greifen"
        case "pick_and_place":
            let objectName = object ?? "Objekt"
            let destination = [room, target].compactMap { $0 }.joined(separator: "/")
            return destination.isEmpty ? "Bringe \(objectName)" : "Bringe \(objectName) nach \(destination)"
        case "explore":
            return "Wohnung erkunden"
        case "cancel":
            return "Mission stoppen"
        case .none:
            return "-"
        default:
            return type ?? "Unbekannt"
        }
    }

    private enum CodingKeys: String, CodingKey {
        case type
        case object
        case room
        case target
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        try container.encodeIfPresent(type, forKey: .type)
        try container.encodeIfPresent(object, forKey: .object)
        try container.encodeIfPresent(room, forKey: .room)
        try container.encodeIfPresent(target, forKey: .target)
    }
}

struct MissionStatus: Decodable, Equatable {
    private static let knownStates = Set([
        "idle",
        "running",
        "success",
        "failed",
        "canceled"
    ])

    let state: String?
    let phase: String?
    let message: String?
    let progress: Double?
    let activeCommand: RobotCommand?
    let rooms: [String]?
    let pickAndPlaceRooms: [String]?
    let targets: [String]?
    let objects: [String]?
    let offboardAvailable: Bool?
    let cancelPending: Bool?
    let lastRejection: String?
    let time: Double?

    enum CodingKeys: String, CodingKey {
        case state
        case phase
        case message
        case progress
        case activeCommand = "active_command"
        case rooms
        case pickAndPlaceRooms = "pick_and_place_rooms"
        case targets
        case objects
        case offboardAvailable = "offboard_available"
        case cancelPending = "cancel_pending"
        case lastRejection = "last_rejection"
        case time
    }

    var normalizedProgress: Double {
        min(1, max(0, progress ?? 0))
    }

    var isCompleteSnapshot: Bool {
        guard
            let state,
            MissionStatus.knownStates.contains(state),
            phase != nil,
            message != nil,
            let progress,
            progress.isFinite,
            activeCommand != nil,
            rooms != nil,
            targets != nil,
            objects != nil,
            lastRejection != nil,
            let time,
            time.isFinite
        else {
            return false
        }
        return true
    }
}

enum EstopRequestPolicy {
    static func allows(
        requestedActive: Bool,
        telemetryIsFresh: Bool,
        currentActive: Bool?
    ) -> Bool {
        requestedActive || (telemetryIsFresh && currentActive == true)
    }
}

enum RobotConnectionState: Equatable {
    case disconnected
    case connecting
    case connected
    case failed(String)
    case waitingToReconnect(seconds: Int)

    var isConnected: Bool {
        if case .connected = self {
            return true
        }
        return false
    }

    var label: String {
        switch self {
        case .disconnected:
            return "ROS getrennt"
        case .connecting:
            return "verbinde …"
        case .connected:
            return "ROS verbunden"
        case .failed:
            return "ROS Fehler"
        case let .waitingToReconnect(seconds):
            return "erneut in \(seconds) s"
        }
    }

    var errorMessage: String? {
        if case let .failed(message) = self {
            return message
        }
        return nil
    }
}

enum RobotLogKind {
    case info
    case success
    case warning
    case error
    case emergency
}

struct RobotLogEntry: Identifiable {
    let id = UUID()
    let date: Date
    let message: String
    let kind: RobotLogKind
}
