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

@MainActor
final class RobotMapController: NSObject, ObservableObject {
    private static let maximumMessageSize = 32 * 1_024 * 1_024

    @Published private(set) var streamState: RobotMapStreamState = .inactive
    @Published private(set) var map: RobotMapSnapshot?
    @Published private(set) var mapImage: CGImage?
    @Published private(set) var lastMapReceivedAt: Date?
    @Published private(set) var lastProtocolError: String?

    private var session: URLSession?
    private var socketTask: URLSessionWebSocketTask?
    private var receiveLoopTask: Task<Void, Never>?
    private var pingLoopTask: Task<Void, Never>?
    private var mapDiscoveryTask: Task<Void, Never>?
    private var mapProcessingTask: Task<Void, Never>?
    private var reconnectTask: Task<Void, Never>?
    private var pendingMapText: String?
    private var mapProcessingGeneration = 0
    private var requestedBridgeURL = ""
    private var reconnectAttempt = 0
    private var shouldStream = false

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
        cancelReconnect()
        openConnection()
    }

    func stop() {
        shouldStream = false
        cancelReconnect()
        closeCurrentSocket(sendUnsubscribe: true)
        streamState = .inactive
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

        startReceiveLoop(for: task)
        startPingLoop(for: task)

        Task { [weak self, task] in
            do {
                try await task.send(.string(try MapRosbridgeProtocol.subscribeFrame()))
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

                    self.map = rendered.map
                    self.mapImage = image
                    self.lastMapReceivedAt = Date()
                    self.lastProtocolError = nil
                    self.streamState = .live
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

        let task = socketTask
        socketTask = nil
        let currentSession = session
        session = nil

        if
            sendUnsubscribe,
            let task,
            let frame = try? MapRosbridgeProtocol.unsubscribeFrame()
        {
            Task { [task, currentSession, frame] in
                let closeDeadline = Task { [task, currentSession] in
                    do {
                        try await Task.sleep(nanoseconds: 250_000_000)
                    } catch {
                        return
                    }
                    task.cancel(with: .normalClosure, reason: nil)
                    currentSession?.invalidateAndCancel()
                }

                try? await task.send(.string(frame))
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
