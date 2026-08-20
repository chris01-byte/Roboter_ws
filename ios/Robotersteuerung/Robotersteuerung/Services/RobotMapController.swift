import CoreGraphics
import Foundation

enum RobotMapStreamState: Equatable {
    case inactive
    case connecting
    case waitingForMap
    case live
    case failed(String)
    case waitingToReconnect(seconds: Int)

    var label: String {
        switch self {
        case .inactive:
            return "Karte inaktiv"
        case .connecting:
            return "verbinde …"
        case .waitingForMap:
            return "warte auf /map"
        case .live:
            return "Karte live"
        case .failed:
            return "Kartenfehler"
        case let .waitingToReconnect(seconds):
            return "erneut in \(seconds) s"
        }
    }

    var isSocketConnected: Bool {
        switch self {
        case .waitingForMap, .live:
            return true
        default:
            return false
        }
    }

    var isLive: Bool {
        if case .live = self {
            return true
        }
        return false
    }

    var errorMessage: String? {
        if case let .failed(message) = self {
            return message
        }
        return nil
    }
}

enum SemanticMapWriteState: Equatable {
    case idle
    case pending(String)
    case succeeded(String)
    case failed(String)
    case revisionConflict(String)
    case statusUnknown(String)

    var isPending: Bool {
        if case .pending = self { return true }
        return false
    }

    var message: String? {
        switch self {
        case .idle:
            return nil
        case let .pending(message), let .succeeded(message),
             let .failed(message), let .revisionConflict(message),
             let .statusUnknown(message):
            return message
        }
    }
}

enum MapSaveState: Equatable {
    case idle
    case pending
    case succeeded(String)
    case failed(String)
    case statusUnknown(String)

    var isPending: Bool {
        if case .pending = self { return true }
        return false
    }
}

@MainActor
final class RobotMapController: NSObject, ObservableObject {
    private static let maximumMessageSize = 32 * 1_024 * 1_024
    private static let offlineSnapshotMinimumSaveInterval: TimeInterval = 15


    @Published private(set) var streamState: RobotMapStreamState = .inactive
    @Published private(set) var map: RobotMapSnapshot?
    @Published private(set) var mapImage: CGImage?
    @Published private(set) var lastMapReceivedAt: Date?
    @Published private(set) var lastProtocolError: String?
    @Published private(set) var mapManagerStatus: RobotMapManagerStatusEnvelope?
    @Published private(set) var semanticStatus: SemanticMapStatusEnvelope?
    @Published private(set) var semanticWriteState: SemanticMapWriteState = .idle
    @Published private(set) var mapSaveState: MapSaveState = .idle

    private var session: URLSession?
    private var socketTask: URLSessionWebSocketTask?
    private var receiveLoopTask: Task<Void, Never>?
    private var pingLoopTask: Task<Void, Never>?
    private var mapDiscoveryTask: Task<Void, Never>?
    private var mapProcessingTask: Task<Void, Never>?
    private var reconnectTask: Task<Void, Never>?
    private var semanticRequestTimeoutTask: Task<Void, Never>?
    private var mapSaveTimeoutTask: Task<Void, Never>?
    private var pendingMapText: String?
    private var mapProcessingGeneration = 0
    private var requestedBridgeURL = ""
    private var reconnectAttempt = 0
    private var shouldStream = false
    private var pendingSemanticRequestID: String?
    private var pendingSemanticBaseRevision: Int?
    private var pendingSemanticFingerprint: String?
    private var pendingSemanticExpectation: SemanticMutationExpectation?
    private var pendingMapSaveRequestID: String?
    private let snapshotStore = RobotMapSnapshotStore()
    private var lastPersistedMapFingerprint: String?
    private var lastMapSnapshotPersistedAt: Date?

    var displayedRooms: [SemanticRoom] {
        matchedSemanticMap?.rooms ?? []
    }

    var semanticRevision: Int? {
        matchedSemanticMap?.revision
    }

    var canEditRooms: Bool {
        SemanticMapClientPolicy.canEditRooms(
            mapIsLive: streamState.isLive,
            currentMap: map,
            managerStatus: mapManagerStatus,
            semanticStatus: semanticStatus,
            mutationIsPending: pendingSemanticRequestID != nil || semanticWriteState.isPending ||
                pendingMapSaveRequestID != nil || mapSaveState.isPending,
            reloadIsRequired: semanticWriteRequiresReload || mapSaveResultIsUnknown
        )
    }

    var canSaveCurrentMapForRooms: Bool {
        SemanticMapClientPolicy.canOfferInitialMapSave(
            mapIsLive: streamState.isLive,
            currentMap: map,
            managerStatus: mapManagerStatus,
            semanticStatus: semanticStatus,
            saveIsPending: pendingMapSaveRequestID != nil || mapSaveState.isPending,
            previousSaveResultIsUnknown: mapSaveResultIsUnknown
        )
    }

    var semanticBindingIssue: String? {
        guard streamState.isLive else {
            return "Die Karte ist nicht live. Raumänderungen bleiben gesperrt."
        }
        guard let map else {
            return "Noch keine gültige OccupancyGrid-Karte empfangen."
        }
        guard let manager = mapManagerStatus,
              manager.map.snapshotAvailable,
              let summary = manager.map.summary else {
            return "Warte auf den Status des Kartenmanagers."
        }
        guard summary.matches(map) else {
            return "Die Live-Karte und der Kartenmanager melden unterschiedliche Fingerabdrücke."
        }
        if pendingMapSaveRequestID != nil || mapSaveState.isPending {
            return "Die Karte wird gerade gespeichert. Räume bleiben bis zur eindeutigen Bestätigung gesperrt."
        }
        if mapSaveResultIsUnknown {
            return "Das Ergebnis des Kartenspeicherns ist unbekannt. Kartenstand neu laden."
        }
        guard let semanticMap = semanticStatus?.semanticMap else {
            if manager.storage.lastSaved?.matches(map) == true {
                return "Warte auf die semantische Karte."
            }
            return "Diese Live-Karte ist noch nicht als identische Version gespeichert."
        }
        guard let mapRef = semanticMap.mapRef, mapRef.matches(map) else {
            return "Die Raumbeschriftungen gehören zu einer anderen Kartenversion."
        }
        guard semanticMap.editable else {
            return "Der Roboter hat diese semantische Karte nicht zum Bearbeiten freigegeben."
        }
        if case .revisionConflict = semanticWriteState {
            return "Die Revision hat sich geändert. Kartenverbindung neu laden, bevor weiter bearbeitet wird."
        }
        if case .statusUnknown = semanticWriteState {
            return "Das Ergebnis der letzten Änderung ist unbekannt. Kartenstand neu laden."
        }
        return nil
    }

    private var matchedSemanticMap: SemanticMapSnapshot? {
        SemanticMapClientPolicy.matchedSnapshot(
            mapIsLive: streamState.isLive,
            currentMap: map,
            managerStatus: mapManagerStatus,
            semanticStatus: semanticStatus
        )
    }

    private var semanticWriteRequiresReload: Bool {
        if case .revisionConflict = semanticWriteState { return true }
        if case .statusUnknown = semanticWriteState { return true }
        return false
    }

    private var mapSaveResultIsUnknown: Bool {
        if case .statusUnknown = mapSaveState { return true }
        return false
    }

    func restoreOfflineSnapshot() {
        guard map == nil,
              let cached = snapshotStore.load(),
              let image = Self.makeImage(
                  from: RenderedRobotMap(
                      map: cached.map,
                      pixels: cached.map.rgbaPixels()
                  )
              )
        else {
            return
        }

        map = cached.map
        mapImage = image
        lastMapReceivedAt = cached.savedAt
        lastPersistedMapFingerprint = cached.map.contentFingerprint
        lastMapSnapshotPersistedAt = cached.savedAt
    }

    func start(bridgeURL: String) {
        let trimmedURL = bridgeURL.trimmingCharacters(in: .whitespacesAndNewlines)
        if shouldStream,
           trimmedURL == requestedBridgeURL,
           socketTask != nil {
            return
        }

        shouldStream = true
        requestedBridgeURL = trimmedURL
        reconnectAttempt = 0
        cancelReconnect()
        openConnection()
    }

    func retry() {
        guard shouldStream else { return }
        reconnectAttempt = 0
        semanticWriteState = .idle
        mapSaveState = .idle
        clearPendingSemanticRequest()
        mapSaveTimeoutTask?.cancel()
        mapSaveTimeoutTask = nil
        pendingMapSaveRequestID = nil
        cancelReconnect()
        openConnection()
    }

    func stop() {
        persistCurrentMapIfNeeded(force: true)
        shouldStream = false
        cancelReconnect()
        closeCurrentSocket(sendUnsubscribe: true)
        streamState = .inactive
    }

    func saveCurrentMapForRooms() {
        guard canSaveCurrentMapForRooms, let task = socketTask else {
            mapSaveState = .failed(
                "Speichern ist nur für die passende, live empfangene Karte möglich."
            )
            return
        }
        let requestID = "ios-map-\(UUID().uuidString.lowercased())"
        pendingMapSaveRequestID = requestID
        mapSaveState = .pending
        startMapSaveTimeout(requestID: requestID)

        Task { [weak self, task, requestID] in
            do {
                try await task.send(.string(
                    try MapRosbridgeProtocol.saveMapFrame(
                        name: "wohnung",
                        requestID: requestID
                    )
                ))
            } catch {
                guard let self, self.pendingMapSaveRequestID == requestID else { return }
                self.mapSaveTimeoutTask?.cancel()
                self.mapSaveTimeoutTask = nil
                self.pendingMapSaveRequestID = nil
                self.mapSaveState = .statusUnknown(
                    "Karte konnte nicht gespeichert werden: \(error.localizedDescription)"
                )
            }
        }
    }

    func upsertRoom(_ room: SemanticRoom) {
        guard canEditRooms,
              let task = socketTask,
              let semanticMap = semanticStatus?.semanticMap,
              let map,
              let mapRef = semanticMap.mapRef,
              let revision = semanticMap.revision,
              mapRef.matches(map) else {
            semanticWriteState = .failed(
                "Der Raum wurde nicht gesendet, weil die Kartenbindung nicht mehr gültig ist."
            )
            return
        }

        let requestID = "ios-room-\(UUID().uuidString.lowercased())"
        pendingSemanticRequestID = requestID
        pendingSemanticBaseRevision = revision
        pendingSemanticFingerprint = mapRef.fingerprint
        pendingSemanticExpectation = .upsert(roomID: room.id)
        semanticWriteState = .pending("Raum wird gespeichert …")
        startSemanticRequestTimeout(requestID: requestID)
        Task { [weak self, task, requestID] in
            do {
                try await task.send(.string(
                    try MapRosbridgeProtocol.upsertRoomFrame(
                        room: room,
                        mapFingerprint: mapRef.fingerprint,
                        baseRevision: revision,
                        requestID: requestID
                    )
                ))
            } catch {
                guard let self, self.pendingSemanticRequestID == requestID else { return }
                self.clearPendingSemanticRequest()
                self.semanticWriteState = .statusUnknown(
                    "Raum konnte nicht gespeichert werden: \(error.localizedDescription)"
                )
            }
        }
    }

    func deleteRoom(id roomID: String) {
        guard canEditRooms,
              let task = socketTask,
              let semanticMap = semanticStatus?.semanticMap,
              let map,
              let mapRef = semanticMap.mapRef,
              let revision = semanticMap.revision,
              mapRef.matches(map),
              semanticMap.rooms.contains(where: { $0.id == roomID }) else {
            semanticWriteState = .failed(
                "Der Raum wurde nicht gelöscht, weil die Kartenbindung nicht mehr gültig ist."
            )
            return
        }

        let requestID = "ios-room-\(UUID().uuidString.lowercased())"
        pendingSemanticRequestID = requestID
        pendingSemanticBaseRevision = revision
        pendingSemanticFingerprint = mapRef.fingerprint
        pendingSemanticExpectation = .delete(roomID: roomID)
        semanticWriteState = .pending("Raum wird gelöscht …")
        startSemanticRequestTimeout(requestID: requestID)
        Task { [weak self, task, requestID] in
            do {
                try await task.send(.string(
                    try MapRosbridgeProtocol.deleteRoomFrame(
                        roomID: roomID,
                        mapFingerprint: mapRef.fingerprint,
                        baseRevision: revision,
                        requestID: requestID
                    )
                ))
            } catch {
                guard let self, self.pendingSemanticRequestID == requestID else { return }
                self.clearPendingSemanticRequest()
                self.semanticWriteState = .statusUnknown(
                    "Raum konnte nicht gelöscht werden: \(error.localizedDescription)"
                )
            }
        }
    }

    private func persistCurrentMapIfNeeded(force: Bool) {
        guard let map, let receivedAt = lastMapReceivedAt,
              map.contentFingerprint != lastPersistedMapFingerprint
        else {
            return
        }

        if !force,
           let lastPersistedAt = lastMapSnapshotPersistedAt,
           receivedAt.timeIntervalSince(lastPersistedAt) <
               Self.offlineSnapshotMinimumSaveInterval {
            return
        }

        let snapshot = CachedRobotMapSnapshot(map: map, savedAt: receivedAt)
        let store = snapshotStore
        lastPersistedMapFingerprint = map.contentFingerprint
        lastMapSnapshotPersistedAt = receivedAt

        Task.detached(priority: .utility) {
            try? store.save(snapshot)
        }
    }

    private func openConnection() {
        guard let url = normalizedBridgeURL(from: requestedBridgeURL) else {
            let message = "Ungültige rosbridge-Adresse. Bitte die Adresse im Tab „Steuerung“ prüfen."
            streamState = .failed(message)
            lastProtocolError = message
            return
        }

        closeCurrentSocket(sendUnsubscribe: false)
        streamState = .connecting
        lastProtocolError = nil

        let configuration = URLSessionConfiguration.ephemeral
        configuration.timeoutIntervalForRequest = 12
        configuration.requestCachePolicy = .reloadIgnoringLocalCacheData

        let session = URLSession(
            configuration: configuration,
            delegate: self,
            delegateQueue: nil
        )
        var request = URLRequest(url: url)
        request.timeoutInterval = 12
        let task = session.webSocketTask(with: request)
        task.maximumMessageSize = RobotMapController.maximumMessageSize

        self.session = session
        socketTask = task
        task.resume()
    }

    private func socketDidOpen(_ task: URLSessionWebSocketTask) {
        guard socketTask === task, shouldStream else { return }
        reconnectAttempt = 0
        streamState = .waitingForMap
        mapManagerStatus = nil
        semanticStatus = nil

        startReceiveLoop(for: task)
        startPingLoop(for: task)

        Task { [weak self, task] in
            do {
                for frame in try MapRosbridgeProtocol.connectionSetupFrames() {
                    try await task.send(.string(frame))
                }
                guard
                    let self,
                    self.socketTask === task,
                    self.streamState == .waitingForMap
                else {
                    return
                }
                self.startMapDiscoveryLoop(for: task)
            } catch {
                guard let self else { return }
                self.handleSocketFailure(task, error: error)
            }
        }
    }

    private func startMapDiscoveryLoop(for task: URLSessionWebSocketTask) {
        mapDiscoveryTask?.cancel()
        mapDiscoveryTask = Task { [weak self, task] in
            while !Task.isCancelled {
                guard
                    let self,
                    self.socketTask === task,
                    self.streamState == .waitingForMap
                else {
                    return
                }

                do {
                    try await Task.sleep(nanoseconds: 4_000_000_000)
                } catch {
                    return
                }

                guard
                    self.socketTask === task,
                    self.streamState == .waitingForMap
                else {
                    return
                }

                do {
                    // rosbridge kann einen untypisierten Subscribe nicht
                    // auflösen, solange der SLAM-Publisher noch nicht
                    // existiert. Neu registrieren, bis /map verfügbar ist.
                    try await task.send(
                        .string(try MapRosbridgeProtocol.unsubscribeFrame())
                    )
                    // Nach begonnenem Unsubscribe immer neu subscriben. Eine
                    // genau jetzt eintreffende Karte setzt den Zustand auf
                    // live, darf den Socket aber nicht abgemeldet lassen.
                    try await task.send(
                        .string(try MapRosbridgeProtocol.subscribeFrame())
                    )
                } catch is CancellationError {
                    return
                } catch {
                    self.handleSocketFailure(task, error: error)
                    return
                }
            }
        }
    }

    private func startReceiveLoop(for task: URLSessionWebSocketTask) {
        receiveLoopTask?.cancel()
        receiveLoopTask = Task { [weak self, task] in
            do {
                while !Task.isCancelled {
                    let message = try await task.receive()
                    guard let self, self.socketTask === task else { return }
                    self.handleIncomingMessage(message, from: task)
                }
            } catch is CancellationError {
                return
            } catch {
                guard let self else { return }
                self.handleSocketFailure(task, error: error)
            }
        }
    }

    private func startPingLoop(for task: URLSessionWebSocketTask) {
        pingLoopTask?.cancel()
        pingLoopTask = Task { [weak self, task] in
            while !Task.isCancelled {
                do {
                    try await Task.sleep(nanoseconds: 15_000_000_000)
                    try await self?.sendPing(on: task)
                } catch is CancellationError {
                    return
                } catch {
                    guard let self else { return }
                    self.handleSocketFailure(task, error: error)
                    return
                }
            }
        }
    }

    private func sendPing(on task: URLSessionWebSocketTask) async throws {
        try await withCheckedThrowingContinuation {
            (continuation: CheckedContinuation<Void, Error>) in
            task.sendPing { error in
                if let error {
                    continuation.resume(throwing: error)
                } else {
                    continuation.resume()
                }
            }
        }
    }

    private func handleIncomingMessage(
        _ message: URLSessionWebSocketTask.Message,
        from task: URLSessionWebSocketTask
    ) {
        let text: String?
        switch message {
        case let .string(value):
            text = value
        case let .data(data):
            text = String(data: data, encoding: .utf8)
        @unknown default:
            text = nil
        }

        guard let text else {
            lastProtocolError = "Binäre Kartennachricht ist kein UTF-8."
            return
        }

        do {
            switch try MapRosbridgeProtocol.incomingTopic(from: text) {
            case MapRosbridgeProtocol.mapTopic:
                enqueueMapText(text, from: task)
            case MapRosbridgeProtocol.mapManagerStatusTopic:
                do {
                    if let status = try MapRosbridgeProtocol.decodeMapManagerStatus(from: text) {
                        handleMapManagerStatus(status)
                    }
                } catch {
                    mapManagerStatus = nil
                    if pendingMapSaveRequestID != nil {
                        mapSaveTimeoutTask?.cancel()
                        mapSaveTimeoutTask = nil
                        pendingMapSaveRequestID = nil
                    }
                    mapSaveState = .statusUnknown(
                        "Ungültiger Kartenmanager-Status. Kartenstand neu laden."
                    )
                    lastProtocolError = error.localizedDescription
                }
            case MapRosbridgeProtocol.semanticStatusTopic:
                do {
                    if let status = try MapRosbridgeProtocol.decodeSemanticMapStatus(from: text) {
                        handleSemanticStatus(status)
                    }
                } catch {
                    semanticStatus = nil
                    clearPendingSemanticRequest()
                    semanticWriteState = .statusUnknown(
                        "Ungültiger semantischer Kartenstatus. Kartenstand neu laden."
                    )
                    lastProtocolError = error.localizedDescription
                }
            case .none:
                break
            default:
                break
            }
        } catch {
            lastProtocolError = error.localizedDescription
        }
    }

    private func enqueueMapText(
        _ text: String,
        from task: URLSessionWebSocketTask
    ) {
        pendingMapText = text
        guard mapProcessingTask == nil else { return }

        mapProcessingGeneration &+= 1
        let generation = mapProcessingGeneration
        mapProcessingTask = Task { [weak self, task] in
            defer {
                if self?.mapProcessingGeneration == generation {
                    self?.mapProcessingTask = nil
                }
            }

            while !Task.isCancelled {
                guard
                    let self,
                    self.socketTask === task,
                    self.mapProcessingGeneration == generation,
                    let nextText = self.pendingMapText
                else {
                    return
                }
                self.pendingMapText = nil

                do {
                    let rendered = try await Task.detached(priority: .userInitiated) {
                        guard let map = try MapRosbridgeProtocol.decodeMap(from: nextText) else {
                            return Optional<RenderedRobotMap>.none
                        }
                        return RenderedRobotMap(map: map, pixels: map.rgbaPixels())
                    }.value
                    try Task.checkCancellation()

                    guard
                        self.socketTask === task,
                        self.mapProcessingGeneration == generation
                    else {
                        return
                    }
                    guard let rendered else { continue }

                    guard let image = Self.makeImage(from: rendered) else {
                        self.lastProtocolError =
                            "Die Kartenpixel konnten nicht dargestellt werden."
                        continue
                    }

                    let receivedAt = Date()
                    self.map = rendered.map
                    self.mapImage = image
                    self.lastMapReceivedAt = receivedAt
                    self.lastProtocolError = nil
                    self.streamState = .live
                    self.persistCurrentMapIfNeeded(force: false)
                } catch is CancellationError {
                    return
                } catch {
                    guard
                        self.socketTask === task,
                        self.mapProcessingGeneration == generation
                    else {
                        return
                    }
                    self.lastProtocolError = error.localizedDescription
                }
            }
        }
    }

    private func handleMapManagerStatus(_ status: RobotMapManagerStatusEnvelope) {
        mapManagerStatus = status
        lastProtocolError = nil
        guard let requestID = pendingMapSaveRequestID,
              status.requestID == requestID,
              status.event == "save_result" else {
            return
        }

        mapSaveTimeoutTask?.cancel()
        mapSaveTimeoutTask = nil
        pendingMapSaveRequestID = nil
        guard status.ok else {
            mapSaveState = .failed(status.message)
            return
        }
        guard let map,
              status.storage.lastSaved?.matches(map) == true else {
            mapSaveState = .statusUnknown(
                "Der Kartenmanager bestätigte den Save ohne passende gespeicherte Version."
            )
            return
        }
        mapSaveState = .succeeded(status.message)
    }

    private func handleSemanticStatus(_ status: SemanticMapStatusEnvelope) {
        semanticStatus = status
        lastProtocolError = nil
        guard let requestID = pendingSemanticRequestID,
              status.requestID == requestID,
              let baseRevision = pendingSemanticBaseRevision,
              let expectedFingerprint = pendingSemanticFingerprint,
              let expectation = pendingSemanticExpectation else {
            return
        }

        guard status.ok else {
            let lowerEvent = status.event.lowercased()
            let lowerMessage = status.message.lowercased()
            clearPendingSemanticRequest()
            if lowerEvent.contains("conflict") || lowerMessage.contains("revision") {
                semanticWriteState = .revisionConflict(status.message)
            } else {
                semanticWriteState = .failed(status.message)
            }
            return
        }
        let acknowledgement = SemanticMapClientPolicy.validateMutationAcknowledgement(
            status,
            expectedRequestID: requestID,
            mapIsLive: streamState.isLive,
            currentMap: map,
            managerStatus: mapManagerStatus,
            expectedFingerprint: expectedFingerprint,
            baseRevision: baseRevision,
            expectation: expectation
        )
        guard acknowledgement == .accepted else {
            clearPendingSemanticRequest()
            switch acknowledgement {
            case .expectedRoomMissing:
                semanticWriteState = .statusUnknown(
                    "Die Bestätigung enthält den gespeicherten Raum nicht. Kartenstand neu laden."
                )
            case .deletedRoomStillPresent:
                semanticWriteState = .statusUnknown(
                    "Die Bestätigung enthält den gelöschten Raum weiterhin. Kartenstand neu laden."
                )
            case .revisionDidNotAdvance:
                semanticWriteState = .statusUnknown(
                    "Die Bestätigung enthält keine neuere Revision. Kartenstand neu laden."
                )
            case .invalidBinding, .accepted:
                semanticWriteState = .statusUnknown(
                    "Die Bestätigung gehört nicht eindeutig zur aktuellen Karte. Kartenstand neu laden."
                )
            }
            return
        }
        clearPendingSemanticRequest()
        semanticWriteState = .succeeded(status.message)
    }

    private static func makeImage(from rendered: RenderedRobotMap) -> CGImage? {
        let data = Data(rendered.pixels)
        guard let provider = CGDataProvider(data: data as CFData) else {
            return nil
        }

        let bitmapInfo = CGBitmapInfo(
            rawValue: CGImageAlphaInfo.last.rawValue
        )
        return CGImage(
            width: rendered.map.width,
            height: rendered.map.height,
            bitsPerComponent: 8,
            bitsPerPixel: 32,
            bytesPerRow: rendered.map.width * 4,
            space: CGColorSpaceCreateDeviceRGB(),
            bitmapInfo: bitmapInfo,
            provider: provider,
            decode: nil,
            shouldInterpolate: false,
            intent: .defaultIntent
        )
    }

    private func handleSocketFailure(
        _ task: URLSessionWebSocketTask,
        error: Error
    ) {
        guard socketTask === task else { return }
        let message = friendlyNetworkError(error)
        closeCurrentSocket(sendUnsubscribe: false)
        streamState = .failed(message)
        lastProtocolError = message
        scheduleReconnectIfNeeded()
    }

    private func socketDidClose(
        _ task: URLSessionWebSocketTask,
        closeCode: URLSessionWebSocketTask.CloseCode,
        reason: Data?
    ) {
        guard socketTask === task else { return }
        let reasonText = reason.flatMap { String(data: $0, encoding: .utf8) }
        closeCurrentSocket(sendUnsubscribe: false)

        guard shouldStream else {
            streamState = .inactive
            return
        }

        let suffix = reasonText.map { ": \($0)" } ?? ""
        let message = "Kartenverbindung wurde beendet\(suffix)."
        streamState = .failed(message)
        lastProtocolError = message
        scheduleReconnectIfNeeded()
    }

    private func closeCurrentSocket(sendUnsubscribe: Bool) {
        receiveLoopTask?.cancel()
        pingLoopTask?.cancel()
        mapDiscoveryTask?.cancel()
        mapProcessingTask?.cancel()
        receiveLoopTask = nil
        pingLoopTask = nil
        mapDiscoveryTask = nil
        mapProcessingTask = nil
        pendingMapText = nil
        mapProcessingGeneration &+= 1
        semanticRequestTimeoutTask?.cancel()
        mapSaveTimeoutTask?.cancel()
        semanticRequestTimeoutTask = nil
        mapSaveTimeoutTask = nil
        mapManagerStatus = nil
        semanticStatus = nil
        if pendingSemanticRequestID != nil {
            semanticWriteState = .statusUnknown(
                "Verbindung während der Raumänderung beendet. Vor einem neuen Versuch den Kartenstand neu laden."
            )
            clearPendingSemanticRequest()
        }
        if pendingMapSaveRequestID != nil {
            mapSaveState = .statusUnknown(
                "Verbindung während des Speicherns beendet. Status vor einem neuen Versuch prüfen."
            )
            pendingMapSaveRequestID = nil
        }

        let task = socketTask
        socketTask = nil
        let currentSession = session
        session = nil

        if
            sendUnsubscribe,
            let task,
            let frames = try? MapRosbridgeProtocol.connectionTeardownFrames()
        {
            Task { [task, currentSession, frames] in
                let closeDeadline = Task { [task, currentSession] in
                    do {
                        try await Task.sleep(nanoseconds: 250_000_000)
                    } catch {
                        return
                    }
                    task.cancel(with: .normalClosure, reason: nil)
                    currentSession?.invalidateAndCancel()
                }

                for frame in frames {
                    try? await task.send(.string(frame))
                }
                closeDeadline.cancel()
                task.cancel(with: .normalClosure, reason: nil)
                currentSession?.invalidateAndCancel()
            }
        } else {
            task?.cancel(with: .goingAway, reason: nil)
            currentSession?.invalidateAndCancel()
        }
    }

    private func scheduleReconnectIfNeeded() {
        guard shouldStream, reconnectTask == nil else { return }

        reconnectAttempt += 1
        let delay = min(15, 1 << min(reconnectAttempt, 4))
        reconnectTask = Task { [weak self] in
            for remaining in stride(from: delay, through: 1, by: -1) {
                guard let self, self.shouldStream else { return }
                self.streamState = .waitingToReconnect(seconds: remaining)
                do {
                    try await Task.sleep(nanoseconds: 1_000_000_000)
                } catch {
                    return
                }
            }

            guard let self, self.shouldStream else { return }
            self.reconnectTask = nil
            self.openConnection()
        }
    }

    private func cancelReconnect() {
        reconnectTask?.cancel()
        reconnectTask = nil
    }

    private func startSemanticRequestTimeout(requestID: String) {
        semanticRequestTimeoutTask?.cancel()
        semanticRequestTimeoutTask = Task { [weak self] in
            do {
                try await Task.sleep(
                    nanoseconds: SemanticMapClientPolicy.responseTimeoutNanoseconds
                )
            } catch {
                return
            }
            guard let self,
                  SemanticMapClientPolicy.timeoutResolution(
                    pendingRequestID: self.pendingSemanticRequestID,
                    firedRequestID: requestID
                  ) == .statusUnknownNoRetry else { return }
            self.clearPendingSemanticRequest()
            self.semanticWriteState = .statusUnknown(
                "Keine Bestätigung innerhalb von 12 Sekunden. Nichts wird automatisch wiederholt; Kartenstand neu laden."
            )
        }
    }

    private func startMapSaveTimeout(requestID: String) {
        mapSaveTimeoutTask?.cancel()
        mapSaveTimeoutTask = Task { [weak self] in
            do {
                try await Task.sleep(
                    nanoseconds: SemanticMapClientPolicy.responseTimeoutNanoseconds
                )
            } catch {
                return
            }
            guard let self,
                  SemanticMapClientPolicy.timeoutResolution(
                    pendingRequestID: self.pendingMapSaveRequestID,
                    firedRequestID: requestID
                  ) == .statusUnknownNoRetry else { return }
            self.pendingMapSaveRequestID = nil
            self.mapSaveTimeoutTask = nil
            self.mapSaveState = .statusUnknown(
                "Keine Save-Bestätigung innerhalb von 12 Sekunden. Nichts wird automatisch wiederholt; Status neu laden."
            )
        }
    }

    private func clearPendingSemanticRequest() {
        semanticRequestTimeoutTask?.cancel()
        semanticRequestTimeoutTask = nil
        pendingSemanticRequestID = nil
        pendingSemanticBaseRevision = nil
        pendingSemanticFingerprint = nil
        pendingSemanticExpectation = nil
    }

    private func normalizedBridgeURL(from input: String) -> URL? {
        var value = input.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !value.isEmpty else { return nil }

        if !value.contains("://") {
            value = "ws://\(value)"
        }

        guard var components = URLComponents(string: value) else { return nil }
        switch components.scheme?.lowercased() {
        case "http":
            components.scheme = "ws"
        case "https":
            components.scheme = "wss"
        case "ws", "wss":
            break
        default:
            return nil
        }

        guard let host = components.host, !host.isEmpty else { return nil }
        if components.port == nil {
            components.port = 9090
        }
        if components.path.isEmpty {
            components.path = "/"
        }
        return components.url
    }

    private func friendlyNetworkError(_ error: Error) -> String {
        guard let urlError = error as? URLError else {
            return "Kartenverbindung fehlgeschlagen: \(error.localizedDescription)"
        }
        switch urlError.code {
        case .cannotConnectToHost, .cannotFindHost:
            return "Roboter nicht erreichbar. WLAN, Adresse und Port 9090 prüfen."
        case .timedOut:
            return "Der Aufbau der Kartenverbindung hat zu lange gedauert."
        case .notConnectedToInternet, .networkConnectionLost:
            return "Keine stabile WLAN-Verbindung für die Karte."
        case .appTransportSecurityRequiresSecureConnection:
            return "iOS blockiert die lokale Kartenverbindung."
        case .cancelled:
            return "Kartenverbindung wurde beendet."
        default:
            return "Kartenverbindung fehlgeschlagen: \(urlError.localizedDescription)"
        }
    }
}

private struct RenderedRobotMap: Sendable {
    let map: RobotMapSnapshot
    let pixels: [UInt8]
}

extension RobotMapController: URLSessionWebSocketDelegate {
    nonisolated func urlSession(
        _ session: URLSession,
        webSocketTask: URLSessionWebSocketTask,
        didOpenWithProtocol protocol: String?
    ) {
        Task { @MainActor [weak self] in
            self?.socketDidOpen(webSocketTask)
        }
    }

    nonisolated func urlSession(
        _ session: URLSession,
        webSocketTask: URLSessionWebSocketTask,
        didCloseWith closeCode: URLSessionWebSocketTask.CloseCode,
        reason: Data?
    ) {
        Task { @MainActor [weak self] in
            self?.socketDidClose(webSocketTask, closeCode: closeCode, reason: reason)
        }
    }

    nonisolated func urlSession(
        _ session: URLSession,
        task: URLSessionTask,
        didCompleteWithError error: Error?
    ) {
        guard let error, let webSocketTask = task as? URLSessionWebSocketTask else { return }
        Task { @MainActor [weak self] in
            self?.handleSocketFailure(webSocketTask, error: error)
        }
    }
}
