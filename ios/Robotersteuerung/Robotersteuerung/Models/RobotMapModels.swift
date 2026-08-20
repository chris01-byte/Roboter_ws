import CryptoKit
import Foundation

enum SemanticMapLimits {
    static let maximumRooms = 256
    static let maximumPolygonPointsPerRoom = 64
    static let maximumTotalPolygonPoints = 4_096
}

struct RobotMapOrigin: Sendable, Equatable, Codable {
    let positionX: Double
    let positionY: Double
    let positionZ: Double
    let orientationX: Double
    let orientationY: Double
    let orientationZ: Double
    let orientationW: Double

    var yaw: Double {
        atan2(
            2 * (orientationW * orientationZ + orientationX * orientationY),
            1 - 2 * (orientationY * orientationY + orientationZ * orientationZ)
        )
    }

    fileprivate var isValid: Bool {
        let components = [
            positionX,
            positionY,
            positionZ,
            orientationX,
            orientationY,
            orientationZ,
            orientationW
        ]
        guard components.allSatisfy(\.isFinite) else { return false }

        let quaternionLengthSquared =
            orientationX * orientationX +
            orientationY * orientationY +
            orientationZ * orientationZ +
            orientationW * orientationW
        guard quaternionLengthSquared.isFinite && quaternionLengthSquared > 1e-12 else {
            return false
        }
        return abs(sqrt(quaternionLengthSquared) - 1) <= 1e-3
    }

    private enum CodingKeys: String, CodingKey {
        case position
        case orientation
    }

    private struct Position: Codable {
        let x: Double
        let y: Double
        let z: Double
    }

    private struct Orientation: Codable {
        let x: Double
        let y: Double
        let z: Double
        let w: Double
    }

    init(
        positionX: Double,
        positionY: Double,
        positionZ: Double,
        orientationX: Double,
        orientationY: Double,
        orientationZ: Double,
        orientationW: Double
    ) {
        self.positionX = positionX
        self.positionY = positionY
        self.positionZ = positionZ
        self.orientationX = orientationX
        self.orientationY = orientationY
        self.orientationZ = orientationZ
        self.orientationW = orientationW
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        let position = try container.decode(Position.self, forKey: .position)
        let orientation = try container.decode(Orientation.self, forKey: .orientation)
        self.init(
            positionX: position.x,
            positionY: position.y,
            positionZ: position.z,
            orientationX: orientation.x,
            orientationY: orientation.y,
            orientationZ: orientation.z,
            orientationW: orientation.w
        )
        guard isValid else {
            throw DecodingError.dataCorruptedError(
                forKey: .orientation,
                in: container,
                debugDescription: "Der Kartenursprung ist nicht endlich oder enthält kein Quaternion."
            )
        }
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        try container.encode(
            Position(x: positionX, y: positionY, z: positionZ),
            forKey: .position
        )
        try container.encode(
            Orientation(
                x: orientationX,
                y: orientationY,
                z: orientationZ,
                w: orientationW
            ),
            forKey: .orientation
        )
    }
}

struct RobotMapSnapshot: Sendable, Equatable, Codable {
    static let maximumCellCount = 4_000_000

    let width: Int
    let height: Int
    let resolution: Double
    let origin: RobotMapOrigin
    let frameID: String
    let cells: [Int8]
    let contentFingerprint: String

    private enum CodingKeys: String, CodingKey {
        case width
        case height
        case resolution
        case origin
        case frameID
        case cells
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        try self.init(
            width: try container.decode(Int.self, forKey: .width),
            height: try container.decode(Int.self, forKey: .height),
            resolution: try container.decode(Double.self, forKey: .resolution),
            origin: try container.decode(RobotMapOrigin.self, forKey: .origin),
            frameID: try container.decode(String.self, forKey: .frameID),
            cells: try container.decode([Int].self, forKey: .cells)
        )
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        try container.encode(width, forKey: .width)
        try container.encode(height, forKey: .height)
        try container.encode(resolution, forKey: .resolution)
        try container.encode(origin, forKey: .origin)
        try container.encode(frameID, forKey: .frameID)
        try container.encode(cells.map(Int.init), forKey: .cells)
    }

    init(
        width: Int,
        height: Int,
        resolution: Double,
        origin: RobotMapOrigin,
        frameID: String,
        cells: [Int]
    ) throws {
        guard width > 0, height > 0 else {
            throw RobotMapValidationError.invalidDimensions(width: width, height: height)
        }

        let (cellCount, overflow) = width.multipliedReportingOverflow(by: height)
        guard !overflow else {
            throw RobotMapValidationError.cellCountOverflow(width: width, height: height)
        }
        guard cellCount <= RobotMapSnapshot.maximumCellCount else {
            throw RobotMapValidationError.cellLimitExceeded(
                actual: cellCount,
                maximum: RobotMapSnapshot.maximumCellCount
            )
        }
        guard resolution.isFinite, resolution > 0 else {
            throw RobotMapValidationError.invalidResolution(resolution)
        }
        guard origin.isValid else {
            throw RobotMapValidationError.invalidOrigin
        }

        let cleanedFrameID = frameID.trimmingCharacters(in: .whitespacesAndNewlines)
        let frameBytes = Data(cleanedFrameID.utf8)
        guard !cleanedFrameID.isEmpty,
              cleanedFrameID.unicodeScalars.count <= 128,
              frameBytes.count <= Int(UInt16.max),
              cleanedFrameID.unicodeScalars.allSatisfy({ scalar in
                  scalar.value >= 0x20 && scalar.value != 0x7F
              }) else {
            throw RobotMapValidationError.invalidFrameID
        }
        guard cells.count == cellCount else {
            throw RobotMapValidationError.invalidDataLength(
                expected: cellCount,
                actual: cells.count
            )
        }

        for (index, value) in cells.enumerated() where !(-1...100).contains(value) {
            throw RobotMapValidationError.invalidOccupancyValue(index: index, value: value)
        }

        self.width = width
        self.height = height
        self.resolution = resolution
        self.origin = origin
        self.frameID = cleanedFrameID
        self.cells = cells.map { Int8($0) }
        self.contentFingerprint = Self.makeContentFingerprint(
            width: width,
            height: height,
            resolution: resolution,
            frameID: cleanedFrameID,
            origin: origin,
            cells: self.cells
        )
    }

    /// Liefert RGBA8888-Pixel in Bildkoordinaten (erste Zeile oben).
    ///
    /// `OccupancyGrid.data` beginnt dagegen links unten. Deshalb werden die
    /// Zeilen beim Rendern vertikal gespiegelt. Unbekannte Zellen sind grau,
    /// freie weiß und vollständig belegte schwarz. Zwischenwerte werden
    /// deterministisch als Graustufen interpoliert.
    func rgbaPixels() -> [UInt8] {
        var pixels = [UInt8](repeating: 0, count: cells.count * 4)

        for imageY in 0..<height {
            let sourceY = height - 1 - imageY
            for x in 0..<width {
                let sourceIndex = sourceY * width + x
                let destinationOffset = (imageY * width + x) * 4
                let pixel = Self.rgba(for: cells[sourceIndex])

                pixels[destinationOffset] = pixel.red
                pixels[destinationOffset + 1] = pixel.green
                pixels[destinationOffset + 2] = pixel.blue
                pixels[destinationOffset + 3] = pixel.alpha
            }
        }

        return pixels
    }

    private static func rgba(for occupancy: Int8) -> (
        red: UInt8,
        green: UInt8,
        blue: UInt8,
        alpha: UInt8
    ) {
        guard occupancy >= 0 else {
            return (127, 127, 127, 255)
        }

        let value = Int(occupancy)
        let gray = UInt8(((100 - value) * 255 + 50) / 100)
        return (gray, gray, gray, 255)
    }

    /// Derselbe inhaltsbasierte SHA-256 wie `robot_map_manager.MapSnapshot`.
    /// ROS-Zeitstempel sind absichtlich nicht enthalten. Dadurch kann die App
    /// fail-closed prüfen, dass Bitmap, gespeicherte Karte und Semantik exakt
    /// dieselbe Kartenbasis verwenden.
    private static func makeContentFingerprint(
        width: Int,
        height: Int,
        resolution: Double,
        frameID: String,
        origin: RobotMapOrigin,
        cells: [Int8]
    ) -> String {
        var hasher = SHA256()

        func update<Integer: FixedWidthInteger>(_ value: Integer) {
            var bigEndian = value.bigEndian
            withUnsafeBytes(of: &bigEndian) { bytes in
                hasher.update(data: Data(bytes))
            }
        }

        func update(_ value: Double) {
            update(value.bitPattern)
        }

        update(UInt32(width))
        update(UInt32(height))
        update(resolution)

        // Der Initializer begrenzt die Bytezahl bereits, bevor diese
        // verlustfrei in das Backendformat (UInt16) konvertiert wird.
        let frameBytes = Data(frameID.utf8)
        update(UInt16(frameBytes.count))
        hasher.update(data: frameBytes)

        update(origin.positionX)
        update(origin.positionY)
        update(origin.positionZ)
        update(origin.orientationX)
        update(origin.orientationY)
        update(origin.orientationZ)
        update(origin.orientationW)

        cells.withUnsafeBytes { bytes in
            hasher.update(data: Data(bytes))
        }

        return hasher.finalize().map { String(format: "%02x", $0) }.joined()
    }
}

struct CachedRobotMapSnapshot: Codable, Equatable, Sendable {
    let map: RobotMapSnapshot
    let savedAt: Date
}

struct RobotMapSnapshotStore: Sendable {
    private let fileURL: URL

    init(fileURL: URL = Self.defaultFileURL()) {
        self.fileURL = fileURL
    }

    func load() -> CachedRobotMapSnapshot? {
        guard let data = try? Data(contentsOf: fileURL) else { return nil }
        return try? PropertyListDecoder().decode(CachedRobotMapSnapshot.self, from: data)
    }

    func save(_ snapshot: CachedRobotMapSnapshot) throws {
        try FileManager.default.createDirectory(
            at: fileURL.deletingLastPathComponent(),
            withIntermediateDirectories: true
        )
        let encoder = PropertyListEncoder()
        encoder.outputFormat = .binary
        try encoder.encode(snapshot).write(to: fileURL, options: .atomic)
    }

    private static func defaultFileURL() -> URL {
        let directory = FileManager.default.urls(
            for: .applicationSupportDirectory,
            in: .userDomainMask
        ).first ?? FileManager.default.temporaryDirectory
        return directory
            .appendingPathComponent("Robotersteuerung", isDirectory: true)
            .appendingPathComponent("last-robot-map.plist", isDirectory: false)
    }
}

struct MapPoint: Codable, Hashable, Sendable {
    let x: Double
    let y: Double

    var isFinite: Bool { x.isFinite && y.isFinite }
}

struct SemanticNavigationGoal: Codable, Equatable, Sendable {
    let x: Double
    let y: Double
    let yaw: Double

    var point: MapPoint { MapPoint(x: x, y: y) }
    var isFinite: Bool { x.isFinite && y.isFinite && yaw.isFinite }
}

struct SemanticRoom: Codable, Equatable, Identifiable, Sendable {
    let id: String
    let name: String
    let color: String?
    let polygon: [MapPoint]
    let navigationGoal: SemanticNavigationGoal?

    enum CodingKeys: String, CodingKey {
        case id
        case name
        case color
        case polygon
        case navigationGoal = "navigation_goal"
    }

    init(
        id: String,
        name: String,
        color: String?,
        polygon: [MapPoint],
        navigationGoal: SemanticNavigationGoal? = nil
    ) throws {
        let cleanID = id
        let cleanName = name.precomposedStringWithCanonicalMapping
            .trimmingCharacters(in: .whitespacesAndNewlines)
        guard Self.isValidID(cleanID) else {
            throw SemanticMapValidationError.invalidRoomID
        }
        guard !cleanName.isEmpty, cleanName.unicodeScalars.count <= 80,
              cleanName.unicodeScalars.allSatisfy({ scalar in
                  scalar.value >= 0x20 && scalar.value != 0x7F
              }) else {
            throw SemanticMapValidationError.invalidRoomName
        }
        guard polygon.count >= 3,
              polygon.count <= SemanticMapLimits.maximumPolygonPointsPerRoom,
              polygon.allSatisfy(\.isFinite) else {
            throw SemanticMapValidationError.invalidPolygon
        }
        guard SemanticGeometry.isSimplePolygon(polygon) else {
            throw SemanticMapValidationError.invalidPolygon
        }
        if let navigationGoal {
            guard navigationGoal.isFinite,
                  (-Double.pi...Double.pi).contains(navigationGoal.yaw),
                  SemanticGeometry.strictlyContains(navigationGoal.point, in: polygon) else {
                throw SemanticMapValidationError.navigationGoalOutsideRoom
            }
        }
        if let color, !SemanticRoom.isValidColor(color) {
            throw SemanticMapValidationError.invalidColor
        }

        self.id = cleanID
        self.name = cleanName
        self.color = color
        self.polygon = polygon
        self.navigationGoal = navigationGoal
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        try self.init(
            id: container.decode(String.self, forKey: .id),
            name: container.decode(String.self, forKey: .name),
            color: container.decodeIfPresent(String.self, forKey: .color),
            polygon: container.decode([MapPoint].self, forKey: .polygon),
            navigationGoal: container.decodeIfPresent(
                SemanticNavigationGoal.self,
                forKey: .navigationGoal
            )
        )
    }

    static func isValidID(_ value: String) -> Bool {
        let bytes = Array(value.utf8)
        guard value.count == bytes.count, (1...64).contains(bytes.count),
              let firstByte = bytes.first,
              (97...122).contains(firstByte) || (48...57).contains(firstByte) else {
            return false
        }
        return bytes.allSatisfy { byte in
            (97...122).contains(byte) || (48...57).contains(byte) ||
                byte == 95 || byte == 45
        }
    }

    private static func isValidColor(_ color: String) -> Bool {
        let bytes = Array(color.utf8)
        guard bytes.count == 7, bytes.first == 35 else { return false }
        return bytes.dropFirst().allSatisfy { byte in
            (48...57).contains(byte) || (65...70).contains(byte) ||
                (97...102).contains(byte)
        }
    }
}

struct SemanticMapReference: Codable, Equatable, Sendable {
    let name: String
    let version: String
    let fingerprint: String
    let frameID: String
    let width: Int
    let height: Int
    let resolution: Double
    let origin: RobotMapOrigin

    enum CodingKeys: String, CodingKey {
        case name
        case version
        case fingerprint
        case frameID = "frame_id"
        case width
        case height
        case resolution
        case origin
    }

    var isValid: Bool {
        SemanticRoom.isValidID(name) &&
            Self.isMapVersion(version) &&
            Self.isFingerprint(fingerprint) &&
            !frameID.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty &&
            width > 0 && height > 0 && resolution.isFinite && resolution > 0 &&
            origin.isValid
    }

    func matches(_ map: RobotMapSnapshot) -> Bool {
        isValid &&
            fingerprint == map.contentFingerprint &&
            frameID == map.frameID &&
            width == map.width &&
            height == map.height &&
            approximatelyEqual(resolution, map.resolution) &&
            origin.approximatelyEquals(map.origin)
    }

    static func isFingerprint(_ value: String) -> Bool {
        let bytes = Array(value.utf8)
        return value.count == bytes.count && bytes.count == 64 &&
            bytes.allSatisfy { byte in
                (48...57).contains(byte) || (97...102).contains(byte)
            }
    }

    private static func isMapVersion(_ value: String) -> Bool {
        let bytes = Array(value.utf8)
        guard bytes.count == 35 || bytes.count == 38 else { return false }
        func allDigits(_ range: Range<Int>) -> Bool {
            range.allSatisfy { (48...57).contains(bytes[$0]) }
        }
        func allLowerHex(_ range: Range<Int>) -> Bool {
            range.allSatisfy {
                (48...57).contains(bytes[$0]) || (97...102).contains(bytes[$0])
            }
        }
        guard allDigits(0..<8), bytes[8] == 84,
              allDigits(9..<21), bytes[21] == 90, bytes[22] == 45,
              allLowerHex(23..<35) else {
            return false
        }
        return bytes.count == 35 ||
            (bytes[35] == 45 && allDigits(36..<38))
    }
}

struct SemanticMapSnapshot: Codable, Equatable, Sendable {
    let mapRef: SemanticMapReference?
    let revision: Int?
    let rooms: [SemanticRoom]
    let editable: Bool

    enum CodingKeys: String, CodingKey {
        case mapRef = "map_ref"
        case revision
        case rooms
        case editable
    }

    var isValid: Bool {
        guard rooms.count <= SemanticMapLimits.maximumRooms,
              rooms.reduce(0, { $0 + $1.polygon.count }) <=
                SemanticMapLimits.maximumTotalPolygonPoints,
              Set(rooms.map(\.id)).count == rooms.count else { return false }
        guard let mapRef, let revision else {
            return mapRef == nil && revision == nil && rooms.isEmpty && !editable
        }
        return mapRef.isValid && revision >= 0 && rooms.allSatisfy { room in
            room.polygon.allSatisfy(mapRef.contains) &&
                (room.navigationGoal.map { mapRef.contains($0.point) } ?? true)
        }
    }
}

struct SemanticMapStatusEnvelope: Decodable, Equatable, Sendable {
    let schemaVersion: Int
    let event: String
    let ok: Bool
    let requestID: String?
    let message: String
    let semanticMap: SemanticMapSnapshot?

    enum CodingKeys: String, CodingKey {
        case schemaVersion = "schema_version"
        case event
        case ok
        case requestID = "request_id"
        case message
        case semanticMap = "semantic_map"
    }
}

struct RobotMapManagerStatusEnvelope: Decodable, Equatable, Sendable {
    let schemaVersion: Int
    let event: String
    let ok: Bool
    let requestID: String?
    let message: String
    let map: MapState
    let storage: StorageState

    enum CodingKeys: String, CodingKey {
        case schemaVersion = "schema_version"
        case event
        case ok
        case requestID = "request_id"
        case message
        case map
        case storage
    }

    struct MapState: Decodable, Equatable, Sendable {
        let snapshotAvailable: Bool
        let summary: Summary?

        enum CodingKeys: String, CodingKey {
            case snapshotAvailable = "snapshot_available"
            case summary
        }
    }

    struct Summary: Decodable, Equatable, Sendable {
        let width: Int
        let height: Int
        let resolution: Double
        let frameID: String
        let origin: RobotMapOrigin
        let fingerprint: String

        enum CodingKeys: String, CodingKey {
            case width
            case height
            case resolution
            case frameID = "frame_id"
            case origin
            case fingerprint
        }

        func matches(_ map: RobotMapSnapshot) -> Bool {
            SemanticMapReference.isFingerprint(fingerprint) &&
                fingerprint == map.contentFingerprint &&
                width == map.width && height == map.height &&
                frameID == map.frameID &&
                approximatelyEqual(resolution, map.resolution) &&
                origin.approximatelyEquals(map.origin)
        }
    }

    struct StorageState: Decodable, Equatable, Sendable {
        let lastSaved: SavedMap?

        enum CodingKeys: String, CodingKey {
            case lastSaved = "last_saved"
        }
    }

    struct SavedMap: Decodable, Equatable, Sendable {
        let name: String
        let version: String
        let width: Int
        let height: Int
        let resolution: Double
        let frameID: String
        let fingerprint: String

        enum CodingKeys: String, CodingKey {
            case name
            case version
            case width
            case height
            case resolution
            case frameID = "frame_id"
            case fingerprint
        }

        func matches(_ map: RobotMapSnapshot) -> Bool {
            SemanticMapReference.isFingerprint(fingerprint) &&
                fingerprint == map.contentFingerprint &&
                width == map.width && height == map.height &&
                frameID == map.frameID &&
                approximatelyEqual(resolution, map.resolution)
        }
    }
}

enum SemanticMutationExpectation: Equatable, Sendable {
    case upsert(roomID: String)
    case delete(roomID: String)
}

enum SemanticMutationAcknowledgement: Equatable, Sendable {
    case accepted
    case invalidBinding
    case revisionDidNotAdvance
    case expectedRoomMissing
    case deletedRoomStillPresent
}

enum BoundedRequestTimeoutResolution: Equatable, Sendable {
    case ignore
    case statusUnknownNoRetry
}

/// Reine, testbare Entscheidungen für den semantischen Kartenclient.
/// Der Controller führt nur noch Netzwerk-I/O und Zustandsveröffentlichung aus.
enum SemanticMapClientPolicy {
    static let responseTimeoutNanoseconds: UInt64 = 12_000_000_000

    static func canOfferInitialMapSave(
        mapIsLive: Bool,
        currentMap: RobotMapSnapshot?,
        managerStatus: RobotMapManagerStatusEnvelope?,
        semanticStatus: SemanticMapStatusEnvelope?,
        saveIsPending: Bool,
        previousSaveResultIsUnknown: Bool
    ) -> Bool {
        guard mapIsLive, !saveIsPending, !previousSaveResultIsUnknown,
              let currentMap, let managerStatus,
              managerStatus.ok,
              managerStatus.map.snapshotAvailable,
              managerStatus.map.summary?.matches(currentMap) == true,
              managerStatus.storage.lastSaved?.matches(currentMap) != true,
              let semanticMap = semanticStatus?.semanticMap,
              semanticMap.isValid,
              semanticMap.mapRef == nil,
              semanticMap.revision == nil,
              semanticMap.rooms.isEmpty,
              !semanticMap.editable else {
            return false
        }
        return true
    }

    static func canEditRooms(
        mapIsLive: Bool,
        currentMap: RobotMapSnapshot?,
        managerStatus: RobotMapManagerStatusEnvelope?,
        semanticStatus: SemanticMapStatusEnvelope?,
        mutationIsPending: Bool,
        reloadIsRequired: Bool
    ) -> Bool {
        guard mapIsLive, !mutationIsPending, !reloadIsRequired,
              let currentMap, let managerStatus,
              managerStatus.ok,
              managerStatus.map.snapshotAvailable,
              managerStatus.map.summary?.matches(currentMap) == true,
              let semanticMap = semanticStatus?.semanticMap,
              semanticMap.isValid, semanticMap.editable,
              semanticMap.mapRef?.matches(currentMap) == true else {
            return false
        }
        return true
    }

    static func matchedSnapshot(
        mapIsLive: Bool,
        currentMap: RobotMapSnapshot?,
        managerStatus: RobotMapManagerStatusEnvelope?,
        semanticStatus: SemanticMapStatusEnvelope?
    ) -> SemanticMapSnapshot? {
        guard mapIsLive, let currentMap, let managerStatus, managerStatus.ok,
              managerStatus.map.snapshotAvailable,
              managerStatus.map.summary?.matches(currentMap) == true,
              let semanticMap = semanticStatus?.semanticMap,
              semanticMap.isValid,
              semanticMap.mapRef?.matches(currentMap) == true else {
            return nil
        }
        return semanticMap
    }

    static func validateMutationAcknowledgement(
        _ status: SemanticMapStatusEnvelope,
        expectedRequestID: String,
        mapIsLive: Bool,
        currentMap: RobotMapSnapshot?,
        managerStatus: RobotMapManagerStatusEnvelope?,
        expectedFingerprint: String,
        baseRevision: Int,
        expectation: SemanticMutationExpectation
    ) -> SemanticMutationAcknowledgement {
        guard status.ok, status.requestID == expectedRequestID,
              mapIsLive, let currentMap, let managerStatus,
              managerStatus.ok,
              managerStatus.map.snapshotAvailable,
              managerStatus.map.summary?.matches(currentMap) == true,
              let semanticMap = status.semanticMap,
              semanticMap.isValid, semanticMap.editable,
              let mapRef = semanticMap.mapRef,
              mapRef.fingerprint == expectedFingerprint,
              mapRef.matches(currentMap) else {
            return .invalidBinding
        }
        guard let revision = semanticMap.revision,
              revision > baseRevision else {
            return .revisionDidNotAdvance
        }
        switch expectation {
        case let .upsert(roomID):
            return semanticMap.rooms.contains(where: { $0.id == roomID })
                ? .accepted : .expectedRoomMissing
        case let .delete(roomID):
            return semanticMap.rooms.contains(where: { $0.id == roomID })
                ? .deletedRoomStillPresent : .accepted
        }
    }

    static func timeoutResolution(
        pendingRequestID: String?,
        firedRequestID: String
    ) -> BoundedRequestTimeoutResolution {
        pendingRequestID == firedRequestID ? .statusUnknownNoRetry : .ignore
    }
}

enum SemanticMapValidationError: Error, LocalizedError, Sendable, Equatable {
    case invalidStatus
    case invalidRoomID
    case invalidRoomName
    case invalidColor
    case invalidPolygon
    case navigationGoalOutsideRoom
    case pointOutsideMap

    var errorDescription: String? {
        switch self {
        case .invalidStatus:
            return "Der semantische Kartenstatus ist unvollständig oder ungültig."
        case .invalidRoomID:
            return "Die Raum-ID ist ungültig."
        case .invalidRoomName:
            return "Bitte einen Raumnamen mit höchstens 80 Zeichen eingeben."
        case .invalidColor:
            return "Die Raumfarbe ist ungültig."
        case .invalidPolygon:
            return "Die Raumfläche benötigt 3 bis 64 Punkte und darf sich nicht kreuzen."
        case .navigationGoalOutsideRoom:
            return "Der Navigationspunkt muss innerhalb des Raums liegen."
        case .pointOutsideMap:
            return "Der gewählte Punkt liegt außerhalb der Karte."
        }
    }
}

enum SemanticGeometry {
    static func contains(_ point: MapPoint, in polygon: [MapPoint]) -> Bool {
        guard polygon.count >= 3, point.isFinite else { return false }
        var inside = false
        var previous = polygon[polygon.count - 1]

        for current in polygon {
            if pointLiesOnSegment(point, previous, current) {
                return true
            }
            if (current.y > point.y) != (previous.y > point.y) {
                let crossingX = (previous.x - current.x) *
                    (point.y - current.y) / (previous.y - current.y) + current.x
                if point.x < crossingX {
                    inside.toggle()
                }
            }
            previous = current
        }
        return inside
    }

    static func isSimplePolygon(_ polygon: [MapPoint]) -> Bool {
        guard polygon.count >= 3, polygon.allSatisfy(\.isFinite) else { return false }
        guard Set(polygon).count == polygon.count else { return false }
        let twiceArea = zip(polygon, polygon.dropFirst() + [polygon[0]])
            .reduce(0.0) { result, edge in
                result + edge.0.x * edge.1.y - edge.1.x * edge.0.y
            }
        // Backend-Minimum: |Polygonfläche| >= 1e-6 m².
        guard abs(twiceArea) >= 2e-6 else { return false }

        for firstIndex in polygon.indices {
            let firstNext = (firstIndex + 1) % polygon.count
            for secondIndex in polygon.indices where secondIndex > firstIndex {
                let secondNext = (secondIndex + 1) % polygon.count
                if firstIndex == secondIndex || firstNext == secondIndex ||
                    secondNext == firstIndex {
                    continue
                }
                if segmentsIntersect(
                    polygon[firstIndex], polygon[firstNext],
                    polygon[secondIndex], polygon[secondNext]
                ) {
                    return false
                }
            }
        }
        return true
    }

    static func strictlyContains(_ point: MapPoint, in polygon: [MapPoint]) -> Bool {
        guard contains(point, in: polygon) else { return false }
        var previous = polygon[polygon.count - 1]
        for current in polygon {
            if pointLiesOnSegment(point, previous, current) { return false }
            previous = current
        }
        return true
    }

    private static func pointLiesOnSegment(
        _ point: MapPoint,
        _ start: MapPoint,
        _ end: MapPoint
    ) -> Bool {
        let cross = (point.y - start.y) * (end.x - start.x) -
            (point.x - start.x) * (end.y - start.y)
        guard abs(cross) <= 1e-8 else { return false }
        let dot = (point.x - start.x) * (end.x - start.x) +
            (point.y - start.y) * (end.y - start.y)
        guard dot >= -1e-8 else { return false }
        let lengthSquared = pow(end.x - start.x, 2) + pow(end.y - start.y, 2)
        return dot <= lengthSquared + 1e-8
    }

    private static func segmentsIntersect(
        _ firstStart: MapPoint,
        _ firstEnd: MapPoint,
        _ secondStart: MapPoint,
        _ secondEnd: MapPoint
    ) -> Bool {
        func orientation(_ a: MapPoint, _ b: MapPoint, _ c: MapPoint) -> Double {
            (b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x)
        }

        let o1 = orientation(firstStart, firstEnd, secondStart)
        let o2 = orientation(firstStart, firstEnd, secondEnd)
        let o3 = orientation(secondStart, secondEnd, firstStart)
        let o4 = orientation(secondStart, secondEnd, firstEnd)

        if o1 * o2 < 0, o3 * o4 < 0 { return true }
        if abs(o1) <= 1e-8,
           pointLiesOnSegment(secondStart, firstStart, firstEnd) { return true }
        if abs(o2) <= 1e-8,
           pointLiesOnSegment(secondEnd, firstStart, firstEnd) { return true }
        if abs(o3) <= 1e-8,
           pointLiesOnSegment(firstStart, secondStart, secondEnd) { return true }
        if abs(o4) <= 1e-8,
           pointLiesOnSegment(firstEnd, secondStart, secondEnd) { return true }
        return false
    }
}

struct ViewportPoint: Equatable, Sendable {
    let x: Double
    let y: Double
}

/// Reine, testbare Transformation zwischen SwiftUI-Bildschirm und ROS-map.
/// Enthalten sind aspect-fit, vertikale OccupancyGrid-Spiegelung, origin-yaw
/// sowie der aktuelle Zoom und Pan der Kartenansicht.
struct RobotMapViewportTransform: Equatable, Sendable {
    let map: RobotMapSnapshot
    let viewportWidth: Double
    let viewportHeight: Double
    let scale: Double
    let offsetX: Double
    let offsetY: Double
    let rotationRadians: Double

    init(
        map: RobotMapSnapshot,
        viewportWidth: Double,
        viewportHeight: Double,
        scale: Double,
        offsetX: Double,
        offsetY: Double,
        rotationRadians: Double = 0
    ) {
        self.map = map
        self.viewportWidth = viewportWidth
        self.viewportHeight = viewportHeight
        self.scale = scale
        self.offsetX = offsetX
        self.offsetY = offsetY
        self.rotationRadians = rotationRadians
    }

    private var fittedSize: (width: Double, height: Double) {
        let imageAspect = Double(map.width) / Double(map.height)
        let viewportAspect = viewportWidth / viewportHeight
        if imageAspect > viewportAspect {
            return (viewportWidth, viewportWidth / imageAspect)
        }
        return (viewportHeight * imageAspect, viewportHeight)
    }

    func screenPoint(for mapPoint: MapPoint) -> ViewportPoint {
        let dx = mapPoint.x - map.origin.positionX
        let dy = mapPoint.y - map.origin.positionY
        let mapCosine = cos(map.origin.yaw)
        let mapSine = sin(map.origin.yaw)
        let localX = mapCosine * dx + mapSine * dy
        let localY = -mapSine * dx + mapCosine * dy

        let fitted = fittedSize
        let originX = (viewportWidth - fitted.width) / 2
        let originY = (viewportHeight - fitted.height) / 2
        let unscaledX = originX + localX / (Double(map.width) * map.resolution) * fitted.width
        let unscaledY = originY +
            (1 - localY / (Double(map.height) * map.resolution)) * fitted.height
        let centerX = viewportWidth / 2
        let centerY = viewportHeight / 2
        let scaledX = (unscaledX - centerX) * scale
        let scaledY = (unscaledY - centerY) * scale
        let rotationCosine = cos(rotationRadians)
        let rotationSine = sin(rotationRadians)
        return ViewportPoint(
            x: centerX + rotationCosine * scaledX - rotationSine * scaledY + offsetX,
            y: centerY + rotationSine * scaledX + rotationCosine * scaledY + offsetY
        )
    }

    func mapPoint(forScreenPoint point: ViewportPoint) -> MapPoint? {
        guard viewportWidth > 0, viewportHeight > 0, scale >= 1,
              scale.isFinite, offsetX.isFinite, offsetY.isFinite,
              rotationRadians.isFinite else {
            return nil
        }

        let centerX = viewportWidth / 2
        let centerY = viewportHeight / 2
        let translatedX = point.x - offsetX - centerX
        let translatedY = point.y - offsetY - centerY
        let rotationCosine = cos(rotationRadians)
        let rotationSine = sin(rotationRadians)
        let unrotatedX = rotationCosine * translatedX + rotationSine * translatedY
        let unrotatedY = -rotationSine * translatedX + rotationCosine * translatedY
        let unscaledX = centerX + unrotatedX / scale
        let unscaledY = centerY + unrotatedY / scale
        let fitted = fittedSize
        let originX = (viewportWidth - fitted.width) / 2
        let originY = (viewportHeight - fitted.height) / 2
        guard unscaledX >= originX, unscaledX <= originX + fitted.width,
              unscaledY >= originY, unscaledY <= originY + fitted.height else {
            return nil
        }

        let localX = (unscaledX - originX) / fitted.width *
            Double(map.width) * map.resolution
        let localY = (1 - (unscaledY - originY) / fitted.height) *
            Double(map.height) * map.resolution
        let mapCosine = cos(map.origin.yaw)
        let mapSine = sin(map.origin.yaw)
        return MapPoint(
            x: map.origin.positionX + mapCosine * localX - mapSine * localY,
            y: map.origin.positionY + mapSine * localX + mapCosine * localY
        )
    }
}

private extension RobotMapOrigin {
    func approximatelyEquals(_ other: RobotMapOrigin) -> Bool {
        approximatelyEqual(positionX, other.positionX) &&
            approximatelyEqual(positionY, other.positionY) &&
            approximatelyEqual(positionZ, other.positionZ) &&
            approximatelyEqual(orientationX, other.orientationX) &&
            approximatelyEqual(orientationY, other.orientationY) &&
            approximatelyEqual(orientationZ, other.orientationZ) &&
            approximatelyEqual(orientationW, other.orientationW)
    }
}

private extension SemanticMapReference {
    func contains(_ point: MapPoint) -> Bool {
        guard point.isFinite else { return false }
        let dx = point.x - origin.positionX
        let dy = point.y - origin.positionY
        let cosine = cos(origin.yaw)
        let sine = sin(origin.yaw)
        let localX = cosine * dx + sine * dy
        let localY = -sine * dx + cosine * dy
        let epsilon = max(resolution * 1e-6, 1e-9)
        return localX >= -epsilon && localY >= -epsilon &&
            localX <= Double(width) * resolution + epsilon &&
            localY <= Double(height) * resolution + epsilon
    }
}

private func approximatelyEqual(_ first: Double, _ second: Double) -> Bool {
    abs(first - second) <= max(1e-12, max(abs(first), abs(second)) * 1e-12)
}

enum RobotMapValidationError: Error, LocalizedError, Sendable, Equatable {
    case invalidDimensions(width: Int, height: Int)
    case cellCountOverflow(width: Int, height: Int)
    case cellLimitExceeded(actual: Int, maximum: Int)
    case invalidResolution(Double)
    case invalidOrigin
    case invalidFrameID
    case invalidDataLength(expected: Int, actual: Int)
    case invalidOccupancyValue(index: Int, value: Int)

    var errorDescription: String? {
        switch self {
        case let .invalidDimensions(width, height):
            return "Die Karte hat ungültige Abmessungen (\(width) × \(height))."
        case let .cellCountOverflow(width, height):
            return "Die Zellzahl der Karte \(width) × \(height) ist nicht darstellbar."
        case let .cellLimitExceeded(actual, maximum):
            return "Die Karte enthält \(actual) Zellen; erlaubt sind höchstens \(maximum)."
        case let .invalidResolution(resolution):
            return "Die Kartenauflösung \(resolution) ist ungültig."
        case .invalidOrigin:
            return "Der Kartenursprung enthält keine gültige endliche Pose."
        case .invalidFrameID:
            return "Die Karte enthält keine gültige ROS-Frame-ID."
        case let .invalidDataLength(expected, actual):
            return "Die Karte erwartet \(expected) Zellwerte, enthält aber \(actual)."
        case let .invalidOccupancyValue(index, value):
            return "Der Kartenwert \(value) an Position \(index) liegt nicht zwischen -1 und 100."
        }
    }
}
