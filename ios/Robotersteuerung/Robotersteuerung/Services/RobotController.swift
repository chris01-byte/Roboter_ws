import Foundation

@MainActor
final class RobotController: NSObject, ObservableObject {
    static let defaultBridgeURL = "ws://p-desktop.local:9090/"

    private static let bridgeURLDefaultsKey = "robot_bridge_url"
    private static let fallbackRooms = ["Wohnzimmer", "Kueche", "Flur"]
    private static let fallbackTargets = ["Tisch", "Regal", "Arbeitsplatte"]
    private static let fallbackObjects = ["Tasse", "Flasche", "Fernbedienung"]
    private static let staleAfter: TimeInterval = 2.5

    @Published var bridgeURL: String
    @Published private(set) var connectionState: RobotConnectionState = .disconnected
    @Published private(set) var missionStatus: MissionStatus?
    @Published private(set) var statusIsFresh = false
    @Published private(set) var exploreStatus: ExploreStatus?
    @Published private(set) var exploreStatusIsFresh = false
    @Published private(set) var estopActive: Bool?
    @Published private(set) var estopIsFresh = false
    @Published private(set) var estopRequestPending = false
    @Published private(set) var missionRequestPending = false
    @Published private(set) var missionCancelRequestPending = false
    @Published private(set) var lastConnectionError: String?
    @Published private(set) var logEntries: [RobotLogEntry] = []

    @Published private(set) var rooms = RobotController.fallbackRooms
    @Published private(set) var pickAndPlaceRooms = RobotController.fallbackRooms
    @Published private(set) var targets = RobotController.fallbackTargets
    @Published private(set) var objects = RobotController.fallbackObjects
    @Published var selectedRoom = RobotController.fallbackRooms[0]
    @Published var selectedPickObject = RobotController.fallbackObjects[0]
    @Published var selectedCarryObject = RobotController.fallbackObjects[0]
    @Published var selectedCarryRoom = RobotController.fallbackRooms[0]
    @Published var selectedTarget = RobotController.fallbackTargets[0]

    private var session: URLSession?
    private var socketTask: URLSessionWebSocketTask?
    private var activeBridgeURL: String?
    private var receiveLoopTask: Task<Void, Never>?
    private var pingLoopTask: Task<Void, Never>?
    private var reconnectTask: Task<Void, Never>?
    private var staleMonitorTask: Task<Void, Never>?
    private var lastStatusReceivedAt: Date?
    private var lastExploreStatusReceivedAt: Date?
    private var lastEstopReceivedAt: Date?
    private var estopRequestSentAt: Date?
    private var requestedEstopValue: Bool?
    private var missionRequestSentAt: Date?
    private var requestedMission: RobotCommand?
    private var missionCancelRequestSentAt: Date?
    private var lastRejection = ""
    private var lastProtocolErrorAt: Date?
    private var reconnectAttempt = 0
    private var shouldReconnect = false
    private var hasStarted = false

    override init() {
        bridgeURL = UserDefaults.standard.string(
            forKey: RobotController.bridgeURLDefaultsKey
        ) ?? RobotController.defaultBridgeURL
        super.init()
    }

    var missionLine: String {
        let message = missionStatus?.message?.trimmingCharacters(in: .whitespacesAndNewlines)
        if let message, !message.isEmpty {
            return message
        }
        return missionStatus?.phase ?? "Bereit"
    }

    var missionState: String {
        missionStatus?.state ?? "idle"
    }

    var phase: String {
        missionStatus?.phase ?? "-"
    }

    var activeCommandDescription: String {
        missionStatus?.activeCommand?.description ?? "-"
    }

    var progress: Double {
        missionStatus?.normalizedProgress ?? 0
    }

    var explorationProgress: Double {
        exploreStatus?.normalizedCoverage ?? 0
    }

    var explorationPhase: String {
        exploreStatus?.phase ?? "-"
    }

    var explorationMessage: String {
        exploreStatus?.message ?? "Warte auf den Explorer."
    }

    var explorationBackendReady: Bool {
        connectionState.isConnected &&
            statusIsFresh &&
            exploreStatusIsFresh &&
            missionStatus?.exploreExecution == "bt_explicit_opt_in" &&
            exploreStatus?.backendReady == true
    }

    var offboardAvailable: Bool? {
        guard connectionState.isConnected, statusIsFresh else { return nil }
        return missionStatus?.offboardAvailable
    }

    var cancelIsPending: Bool {
        missionCancelRequestPending || missionStatus?.cancelPending == true
    }

    var canSendMission: Bool {
        connectionState.isConnected &&
            statusIsFresh &&
            estopIsFresh &&
            estopActive == false &&
            !missionRequestPending &&
            ["idle", "success", "failed", "canceled"].contains(missionState) &&
            !cancelIsPending
    }

    var canStartExploration: Bool {
        canSendMission &&
            explorationBackendReady &&
            exploreStatus?.state != "running"
    }

    var canSendEmergencyRequest: Bool {
        connectionState.isConnected
    }

    var canCancelMission: Bool {
            connectionState.isConnected &&
            missionState == "running" &&
            !cancelIsPending
    }

    func start() {
        guard !hasStarted else { return }
        hasStarted = true
        shouldReconnect = true
        startStaleMonitor()
        openConnection(resetBackoff: true)
    }

    func toggleConnection() {
        switch connectionState {
        case .connected, .connecting, .waitingToReconnect:
            disconnect()
        case .disconnected, .failed:
            shouldReconnect = true
            cancelReconnect()
            openConnection(resetBackoff: true)
        }
    }

    func connectNow() {
        shouldReconnect = true
        cancelReconnect()
        openConnection(resetBackoff: true)
    }

    func disconnect() {
        shouldReconnect = false
        cancelReconnect()
        closeCurrentSocket(closeCode: .normalClosure)
        connectionState = .disconnected
        lastConnectionError = nil
        markTelemetryUnknown()
        addLog("Verbindung manuell getrennt", kind: .info)
    }

    func appDidEnterBackground() {
        guard shouldReconnect else { return }
        cancelReconnect()
        closeCurrentSocket(closeCode: .goingAway)
        connectionState = .disconnected
        markTelemetryUnknown()
    }

    func appDidBecomeActive() {
        guard hasStarted, shouldReconnect, socketTask == nil, reconnectTask == nil else {
            return
        }
        openConnection(resetBackoff: false)
    }

    func goToSelectedRoom() {
        publishCommand(RobotCommand(type: "go_to_room", room: selectedRoom))
    }

    func pickSelectedObject() {
        publishCommand(RobotCommand(type: "pick_object", object: selectedPickObject))
    }

    func carrySelectedObject() {
        publishCommand(RobotCommand(
            type: "pick_and_place",
            object: selectedCarryObject,
            room: selectedCarryRoom,
            target: selectedTarget
        ))
    }

    func startExploration() {
        guard canStartExploration else {
            addLog(
                "Erkundung gesperrt: echtes Explorer-Backend ist nicht vollständig bereit.",
                kind: .warning
            )
            return
        }
        publishCommand(RobotCommand(type: "explore"))
    }

    func cancelMission() {
        publishCommand(RobotCommand(type: "cancel"))
    }

    func requestEstop(active: Bool) {
        guard !estopRequestPending else { return }
        guard EstopRequestPolicy.allows(
            requestedActive: active,
            telemetryIsFresh: estopIsFresh,
            currentActive: estopActive
        ) else {
            addLog(
                "Freigabe blockiert: Sicherheitsstatus ist nicht mehr aktuell.",
                kind: .warning
            )
            return
        }
        guard let task = readySocket() else { return }
        do {
            let frame = try RosbridgeProtocol.estopFrame(active: active)
            estopRequestPending = true
            estopRequestSentAt = Date()
            requestedEstopValue = active
            transmit(
                frame,
                through: task,
                successMessage: active ? "NOT-AUS gesendet" : "Freigabe gesendet",
                successKind: active ? .emergency : .warning
            )
        } catch {
            estopRequestPending = false
            addLog(error.localizedDescription, kind: .error)
        }
    }

    func refreshDisplayedStatus() {
        guard let missionStatus else {
            addLog("Noch kein Status vom Roboter empfangen", kind: .warning)
            return
        }
        self.missionStatus = missionStatus
        addLog(
            statusIsFresh ? "Statusanzeige aktualisiert" : "Letzter Status ist veraltet",
            kind: statusIsFresh ? .info : .warning
        )
    }

    private func publishCommand(_ command: RobotCommand) {
        if command.type == "cancel" {
            guard canCancelMission else {
                addLog("Kein abbrechbarer Auftrag aktiv", kind: .warning)
                return
            }
        } else {
            guard canSendMission else {
                addLog("Neuer Auftrag ist derzeit gesperrt", kind: .warning)
                return
            }
        }
        guard let task = readySocket() else { return }
        do {
            let frame = try RosbridgeProtocol.commandFrame(command)
            if command.type == "cancel" {
                missionCancelRequestPending = true
                missionCancelRequestSentAt = Date()
            } else {
                missionRequestPending = true
                missionRequestSentAt = Date()
                requestedMission = command
            }
            transmit(
                frame,
                through: task,
                successMessage: "Gesendet: \(command.description) – warte auf Bestätigung",
                successKind: .info
            )
        } catch {
            addLog(error.localizedDescription, kind: .error)
        }
    }

    private func readySocket() -> URLSessionWebSocketTask? {
        guard connectionState.isConnected, let socketTask else {
            addLog("Keine rosbridge-Verbindung", kind: .error)
            return nil
        }
        return socketTask
    }

    private func transmit(
        _ text: String,
        through task: URLSessionWebSocketTask,
        successMessage: String,
        successKind: RobotLogKind
    ) {
        Task { [weak self, task] in
            do {
                try await task.send(.string(text))
                guard let self, self.socketTask === task else { return }
                self.addLog(successMessage, kind: successKind)
            } catch {
                guard let self else { return }
                self.handleSocketFailure(task, error: error)
            }
        }
    }

    private func openConnection(resetBackoff: Bool) {
        guard let url = normalizedBridgeURL(from: bridgeURL) else {
            shouldReconnect = false
            let message = "Bitte eine gültige WebSocket-Adresse eingeben, z. B. ws://192.168.1.50:9090/."
            connectionState = .failed(message)
            lastConnectionError = message
            addLog(message, kind: .error)
            return
        }

        if resetBackoff {
            reconnectAttempt = 0
        }

        closeCurrentSocket(closeCode: .goingAway)
        bridgeURL = url.absoluteString
        activeBridgeURL = url.absoluteString
        connectionState = .connecting
        lastConnectionError = nil
        markTelemetryUnknown()
        addLog("Verbinde \(url.absoluteString)", kind: .info)

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

        self.session = session
        socketTask = task
        task.maximumMessageSize = 1_048_576
        task.resume()
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

    private func socketDidOpen(_ task: URLSessionWebSocketTask) {
        guard socketTask === task else { return }
        connectionState = .connected
        reconnectAttempt = 0
        lastConnectionError = nil
        UserDefaults.standard.set(
            activeBridgeURL ?? bridgeURL,
            forKey: RobotController.bridgeURLDefaultsKey
        )
        addLog("rosbridge verbunden", kind: .success)

        startReceiveLoop(for: task)
        startPingLoop(for: task)

        Task { [weak self, task] in
            do {
                for frame in try RosbridgeProtocol.setupFrames() {
                    try await task.send(.string(frame))
                }
            } catch {
                guard let self else { return }
                self.handleSocketFailure(task, error: error)
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
                    self.handleIncomingMessage(message)
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

    private func handleIncomingMessage(_ message: URLSessionWebSocketTask.Message) {
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
            addProtocolError("Binäre rosbridge-Nachricht ist kein UTF-8.")
            return
        }

        do {
            guard let event = try RosbridgeProtocol.decodeEvent(from: text) else { return }
            switch event {
            case let .status(status):
                apply(status)
            case let .exploreStatus(status):
                applyExploreStatus(status)
            case let .estop(active):
                applyEstop(active)
            }
        } catch {
            addProtocolError(error.localizedDescription)
        }
    }

    private func apply(_ status: MissionStatus) {
        missionStatus = status
        lastStatusReceivedAt = Date()
        statusIsFresh = true

        rooms = cleanCatalog(status.rooms ?? RobotController.fallbackRooms)
        pickAndPlaceRooms = cleanCatalog(
            status.pickAndPlaceRooms ?? RobotController.fallbackRooms
        )
        targets = cleanCatalog(status.targets ?? RobotController.fallbackTargets)
        objects = cleanCatalog(status.objects ?? RobotController.fallbackObjects)

        preserveSelection(&selectedRoom, in: rooms)
        preserveSelection(&selectedCarryRoom, in: pickAndPlaceRooms)
        preserveSelection(&selectedPickObject, in: objects)
        preserveSelection(&selectedCarryObject, in: objects)
        preserveSelection(&selectedTarget, in: targets)

        let rejection = status.lastRejection ?? ""
        if missionCancelRequestPending {
            let terminalStates = ["success", "failed", "canceled"]
            if status.cancelPending == true ||
                terminalStates.contains(status.state ?? "") ||
                (!rejection.isEmpty && rejection != lastRejection) {
                clearMissionCancelRequestPending()
            }
        }
        if missionRequestPending,
           status.activeCommand == requestedMission,
           ["running", "success", "failed", "canceled"].contains(status.state ?? "") {
            clearMissionRequestPending()
        } else if missionRequestPending,
                  !rejection.isEmpty,
                  rejection != lastRejection {
            clearMissionRequestPending()
        }
        if !rejection.isEmpty, rejection != lastRejection {
            addLog("Abgelehnt: \(rejection)", kind: .warning)
        }
        lastRejection = rejection
    }

    private func applyExploreStatus(_ status: ExploreStatus) {
        exploreStatus = status
        lastExploreStatusReceivedAt = Date()
        exploreStatusIsFresh = true
    }

    private func applyEstop(_ active: Bool) {
        let previous = estopActive
        estopActive = active
        lastEstopReceivedAt = Date()
        estopIsFresh = true
        if requestedEstopValue == active {
            estopRequestPending = false
            estopRequestSentAt = nil
            requestedEstopValue = nil
        }
        guard previous != active else { return }
        // The first "false" sample is the initial safety snapshot, not a
        // transition that the operator initiated.
        guard previous != nil || active else { return }

        addLog(
            active ? "NOT-AUS AKTIV – Roboter angehalten" : "Not-Aus freigegeben",
            kind: active ? .emergency : .success
        )
    }

    private func cleanCatalog(_ values: [String]) -> [String] {
        var seen = Set<String>()
        return values.compactMap { value in
            let cleaned = value.trimmingCharacters(in: .whitespacesAndNewlines)
            guard !cleaned.isEmpty, seen.insert(cleaned).inserted else { return nil }
            return cleaned
        }
    }

    private func preserveSelection(_ selection: inout String, in values: [String]) {
        if !values.contains(selection) {
            selection = values.first ?? ""
        }
    }

    private func startStaleMonitor() {
        staleMonitorTask?.cancel()
        staleMonitorTask = Task { [weak self] in
            while !Task.isCancelled {
                do {
                    try await Task.sleep(nanoseconds: 1_000_000_000)
                } catch {
                    return
                }
                self?.updateFreshness()
            }
        }
    }

    private func updateFreshness(now: Date = Date()) {
        if missionCancelRequestPending,
           now.timeIntervalSince(missionCancelRequestSentAt ?? .distantPast) >
            RobotController.staleAfter {
            clearMissionCancelRequestPending()
            addLog("Keine Bestätigung des Missionsabbruchs erhalten", kind: .warning)
        }

        if missionRequestPending,
           now.timeIntervalSince(missionRequestSentAt ?? .distantPast) >
            RobotController.staleAfter {
            clearMissionRequestPending()
            addLog("Keine Auftragsbestätigung vom Roboter erhalten", kind: .warning)
        }

        if estopRequestPending,
           now.timeIntervalSince(estopRequestSentAt ?? .distantPast) > RobotController.staleAfter {
            estopRequestPending = false
            estopRequestSentAt = nil
            requestedEstopValue = nil
            addLog("Keine Bestätigung der NOT-AUS-Anforderung erhalten", kind: .error)
        }

        if statusIsFresh,
           now.timeIntervalSince(lastStatusReceivedAt ?? .distantPast) > RobotController.staleAfter {
            statusIsFresh = false
            addLog("Missionsstatus ist veraltet", kind: .warning)
        }

        if exploreStatusIsFresh,
           now.timeIntervalSince(lastExploreStatusReceivedAt ?? .distantPast) >
            RobotController.staleAfter {
            exploreStatusIsFresh = false
            addLog("Erkundungsstatus ist veraltet", kind: .warning)
        }

        if estopIsFresh,
           now.timeIntervalSince(lastEstopReceivedAt ?? .distantPast) > RobotController.staleAfter {
            estopIsFresh = false
            estopActive = nil
            estopRequestPending = false
            addLog("Sicherheitsstatus ist unbekannt", kind: .error)
        }
    }

    private func markTelemetryUnknown() {
        statusIsFresh = false
        exploreStatusIsFresh = false
        estopIsFresh = false
        estopActive = nil
        estopRequestPending = false
        estopRequestSentAt = nil
        requestedEstopValue = nil
        clearMissionRequestPending()
        clearMissionCancelRequestPending()
        lastStatusReceivedAt = nil
        lastExploreStatusReceivedAt = nil
        lastEstopReceivedAt = nil
    }

    private func clearMissionRequestPending() {
        missionRequestPending = false
        missionRequestSentAt = nil
        requestedMission = nil
    }

    private func clearMissionCancelRequestPending() {
        missionCancelRequestPending = false
        missionCancelRequestSentAt = nil
    }

    private func handleSocketFailure(_ task: URLSessionWebSocketTask, error: Error) {
        guard socketTask === task else { return }
        let message = friendlyNetworkError(error)
        closeCurrentSocket(closeCode: .goingAway)
        markTelemetryUnknown()
        lastConnectionError = message
        connectionState = .failed(message)
        addLog(message, kind: .error)
        scheduleReconnectIfNeeded()
    }

    private func socketDidClose(
        _ task: URLSessionWebSocketTask,
        closeCode: URLSessionWebSocketTask.CloseCode,
        reason: Data?
    ) {
        guard socketTask === task else { return }
        let reasonText = reason.flatMap { String(data: $0, encoding: .utf8) }
        closeCurrentSocket(closeCode: closeCode)
        markTelemetryUnknown()

        if shouldReconnect {
            let suffix = reasonText.map { ": \($0)" } ?? ""
            lastConnectionError = "rosbridge hat die Verbindung beendet\(suffix)."
            addLog("rosbridge getrennt\(suffix)", kind: .warning)
            scheduleReconnectIfNeeded()
        } else {
            connectionState = .disconnected
        }
    }

    private func closeCurrentSocket(closeCode: URLSessionWebSocketTask.CloseCode) {
        receiveLoopTask?.cancel()
        pingLoopTask?.cancel()
        receiveLoopTask = nil
        pingLoopTask = nil

        let task = socketTask
        socketTask = nil
        activeBridgeURL = nil
        task?.cancel(with: closeCode, reason: nil)

        let currentSession = session
        session = nil
        currentSession?.invalidateAndCancel()
    }

    private func scheduleReconnectIfNeeded() {
        guard shouldReconnect, reconnectTask == nil else {
            if !shouldReconnect {
                connectionState = .disconnected
            }
            return
        }

        reconnectAttempt += 1
        let delay = min(15, 1 << min(reconnectAttempt, 4))
        reconnectTask = Task { [weak self] in
            for remaining in stride(from: delay, through: 1, by: -1) {
                guard let self, self.shouldReconnect else { return }
                self.connectionState = .waitingToReconnect(seconds: remaining)
                do {
                    try await Task.sleep(nanoseconds: 1_000_000_000)
                } catch {
                    return
                }
            }

            guard let self, self.shouldReconnect else { return }
            self.reconnectTask = nil
            self.openConnection(resetBackoff: false)
        }
    }

    private func cancelReconnect() {
        reconnectTask?.cancel()
        reconnectTask = nil
    }

    private func friendlyNetworkError(_ error: Error) -> String {
        guard let urlError = error as? URLError else {
            return "rosbridge-Fehler: \(error.localizedDescription)"
        }
        switch urlError.code {
        case .cannotConnectToHost, .cannotFindHost:
            return "Roboter nicht erreichbar. IP/Hostname, WLAN und Port 9090 prüfen."
        case .timedOut:
            return "Verbindungsaufbau zu rosbridge hat zu lange gedauert."
        case .notConnectedToInternet, .networkConnectionLost:
            return "Keine stabile WLAN-Verbindung zum Roboter."
        case .appTransportSecurityRequiresSecureConnection:
            return "iOS blockiert die Verbindung. Für das lokale WLAN ist die App-Freigabe erforderlich."
        case .cancelled:
            return "rosbridge-Verbindung wurde beendet."
        default:
            return "rosbridge-Fehler: \(urlError.localizedDescription)"
        }
    }

    private func addProtocolError(_ message: String) {
        let now = Date()
        if let lastProtocolErrorAt, now.timeIntervalSince(lastProtocolErrorAt) < 5 {
            return
        }
        lastProtocolErrorAt = now
        addLog("Protokollfehler: \(message)", kind: .error)
    }

    private func addLog(_ message: String, kind: RobotLogKind) {
        logEntries.insert(
            RobotLogEntry(date: Date(), message: message, kind: kind),
            at: 0
        )
        if logEntries.count > 40 {
            logEntries.removeLast(logEntries.count - 40)
        }
    }
}

extension RobotController: URLSessionWebSocketDelegate {
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
