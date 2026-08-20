import SwiftUI
import UIKit

struct RobotMapView: View {
    private enum RoomEditorPhase: Equatable {
        case inactive
        case polygon
        case navigationGoal
    }

    @EnvironmentObject private var robotController: RobotController
    @Environment(\.scenePhase) private var scenePhase

    @StateObject private var mapController = RobotMapController()
    @State private var isVisible = false
    @State private var showEstopReleaseConfirmation = false
    @State private var roomEditorPhase: RoomEditorPhase = .inactive
    @State private var roomName = ""
    @State private var roomPoints: [MapPoint] = []
    @State private var navigationGoal: MapPoint?
    @State private var navigationYaw = 0.0
    @State private var roomEditorError: String?
    @State private var selectedRoomID: String?
    @State private var roomPendingDeletion: SemanticRoom?

    var body: some View {
        ZStack {
            RobotPalette.background
                .ignoresSafeArea()

            ScrollView {
                LazyVStack(spacing: 12) {
                    header
                    connectionNotice
                    semanticControls
                    mapCard
                    mapInformation
                    emergencySection
                    safetyFootnote
                }
                .padding(.horizontal, 14)
                .padding(.top, 12)
                .padding(.bottom, 24)
                .frame(maxWidth: 760)
                .frame(maxWidth: .infinity)
            }
        }
        .preferredColorScheme(.dark)
        .onAppear {
            isVisible = true
            mapController.restoreOfflineSnapshot()
            mapController.start(bridgeURL: robotController.bridgeURL)
        }
        .onDisappear {
            isVisible = false
            mapController.stop()
        }
        .onChange(of: robotController.bridgeURL) { newValue in
            guard isVisible else { return }
            mapController.start(bridgeURL: newValue)
        }
        .onChange(of: scenePhase) { phase in
            guard isVisible else { return }
            switch phase {
            case .active:
                mapController.start(bridgeURL: robotController.bridgeURL)
            case .background:
                mapController.stop()
            case .inactive:
                break
            @unknown default:
                break
            }
        }
        .onChange(of: mapController.map?.contentFingerprint) { _ in
            guard roomEditorPhase != .inactive else { return }
            cancelRoomEditing(
                message: "Die Kartenbasis hat sich geändert. Der Raumentwurf wurde verworfen."
            )
        }
        .onChange(of: mapController.semanticWriteState) { state in
            if case .succeeded = state {
                resetRoomEditor()
            }
        }
        .alert("NOT-AUS freigeben?", isPresented: $showEstopReleaseConfirmation) {
            Button("Abbrechen", role: .cancel) {}
            Button("Freigeben", role: .destructive) {
                warningHaptic()
                robotController.requestEstop(active: false)
            }
        } message: {
            Text(
                "Nur freigeben, wenn der Gefahrenbereich kontrolliert wurde. "
                + "Der Roboter erhält anschließend wieder die Software-Freigabe."
            )
        }
        .confirmationDialog(
            "Raum löschen?",
            isPresented: Binding(
                get: { roomPendingDeletion != nil },
                set: { if !$0 { roomPendingDeletion = nil } }
            ),
            titleVisibility: .visible
        ) {
            if let room = roomPendingDeletion {
                Button("„\(room.name)“ löschen", role: .destructive) {
                    mapController.deleteRoom(id: room.id)
                    roomPendingDeletion = nil
                }
            }
            Button("Abbrechen", role: .cancel) {
                roomPendingDeletion = nil
            }
        } message: {
            Text("Nur die Beschriftung wird gelöscht. Die metrische Wohnungskarte bleibt unverändert.")
        }
    }

    private var header: some View {
        HStack(alignment: .center, spacing: 12) {
            VStack(alignment: .leading, spacing: 4) {
                Label("Wohnungskarte", systemImage: "map.fill")
                    .font(.title2.weight(.bold))
                    .foregroundStyle(RobotPalette.text)

                Text(mapSubtitle)
                    .font(.subheadline)
                    .foregroundStyle(RobotPalette.muted)
                    .lineLimit(2)
            }
            .frame(maxWidth: .infinity, alignment: .leading)

            StatusPill(
                text: mapController.streamState.label,
                tone: mapStatusTone
            )
        }
    }

    @ViewBuilder
    private var connectionNotice: some View {
        if let message = mapController.lastProtocolError {
            RobotCard {
                HStack(alignment: .top, spacing: 10) {
                    Image(systemName: "exclamationmark.triangle.fill")
                        .foregroundStyle(RobotPalette.highlight)
                    Text(message)
                        .font(.caption)
                        .foregroundStyle(RobotPalette.muted)
                        .frame(maxWidth: .infinity, alignment: .leading)
                    Button("Erneut") {
                        mapController.retry()
                    }
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(RobotPalette.accent)
                }
            }
        } else if mapController.streamState == .waitingForMap {
            RobotCard {
                HStack(spacing: 10) {
                    ProgressView()
                        .tint(RobotPalette.accent)
                    Text("Verbunden. Amadeus wartet auf eine Karte vom Topic /map.")
                        .font(.caption)
                        .foregroundStyle(RobotPalette.muted)
                }
            }
        }
    }

    private var semanticControls: some View {
        RobotCard {
            VStack(alignment: .leading, spacing: 12) {
                HStack(spacing: 8) {
                    Label("Räume", systemImage: "square.3.layers.3d")
                        .font(.subheadline.weight(.semibold))
                    Spacer()
                    if let revision = mapController.semanticRevision {
                        Text("Revision \(revision)")
                            .font(.caption2.monospacedDigit())
                            .foregroundStyle(RobotPalette.muted)
                    }
                }

                if roomEditorPhase == .inactive {
                    roomOverviewControls
                } else {
                    roomEditorControls
                }

                semanticOperationNotice
                if roomEditorPhase == .inactive, let error = roomEditorError {
                    Label(error, systemImage: "exclamationmark.triangle.fill")
                        .font(.caption)
                        .foregroundStyle(RobotPalette.highlight)
                }
            }
        }
    }

    @ViewBuilder
    private var roomOverviewControls: some View {
        if mapController.canEditRooms {
            HStack(spacing: 10) {
                Button {
                    beginRoomEditing()
                } label: {
                    Label("Raum hinzufügen", systemImage: "plus")
                }
                .buttonStyle(.borderedProminent)
                .tint(RobotPalette.accent)

                Text("\(mapController.displayedRooms.count) gespeichert")
                    .font(.caption)
                    .foregroundStyle(RobotPalette.muted)
            }
        } else if mapController.canSaveCurrentMapForRooms || mapController.mapSaveState.isPending {
            Button {
                mapController.saveCurrentMapForRooms()
            } label: {
                HStack(spacing: 8) {
                    if mapController.mapSaveState.isPending {
                        ProgressView().tint(.white)
                    } else {
                        Image(systemName: "externaldrive.badge.plus")
                    }
                    Text(
                        mapController.mapSaveState.isPending
                            ? "Karte wird gespeichert …"
                            : "Karte für Räume speichern"
                    )
                }
                .frame(maxWidth: .infinity)
            }
            .buttonStyle(.borderedProminent)
            .tint(RobotPalette.accent)
            .disabled(mapController.mapSaveState.isPending)
        }

        if let room = selectedRoom {
            HStack(spacing: 10) {
                Circle()
                    .fill(roomColor(room.color))
                    .frame(width: 12, height: 12)
                VStack(alignment: .leading, spacing: 2) {
                    Text(room.name)
                        .font(.subheadline.weight(.semibold))
                    Text("Auf der Karte ausgewählt")
                        .font(.caption2)
                        .foregroundStyle(RobotPalette.muted)
                }
                Spacer()
                Button(role: .destructive) {
                    roomPendingDeletion = room
                } label: {
                    Label("Löschen", systemImage: "trash")
                        .labelStyle(.iconOnly)
                }
                .disabled(!mapController.canEditRooms)
                .accessibilityLabel("Raum \(room.name) löschen")
            }
            .padding(10)
            .background(RobotPalette.surfaceRaised)
            .clipShape(RoundedRectangle(cornerRadius: 9, style: .continuous))
        }

        if let issue = mapController.semanticBindingIssue {
            Label(issue, systemImage: "lock.trianglebadge.exclamationmark")
                .font(.caption)
                .foregroundStyle(RobotPalette.highlight)
        } else {
            Label(
                "Raumflächen sind Beschriftungen. Sie lösen keine Fahrt aus.",
                systemImage: "checkmark.shield"
            )
            .font(.caption)
            .foregroundStyle(RobotPalette.muted)
        }
    }

    private var roomEditorControls: some View {
        VStack(alignment: .leading, spacing: 11) {
            TextField("Raumname, z. B. Wohnzimmer", text: $roomName)
                .textInputAutocapitalization(.words)
                .autocorrectionDisabled(false)
                .padding(.horizontal, 11)
                .frame(minHeight: 44)
                .background(RobotPalette.surfaceRaised)
                .overlay {
                    RoundedRectangle(cornerRadius: 9, style: .continuous)
                        .stroke(RobotPalette.line, lineWidth: 1)
                }
                .clipShape(RoundedRectangle(cornerRadius: 9, style: .continuous))
                .disabled(mapController.semanticWriteState.isPending)

            if roomEditorPhase == .polygon {
                Text(
                    "Tippe mindestens drei Eckpunkte der Raumgrenze in Reihenfolge an. "
                        + "Zoomen und Verschieben bleiben möglich."
                )
                .font(.caption)
                .foregroundStyle(RobotPalette.muted)

                HStack(spacing: 9) {
                    Button("Abbrechen") { resetRoomEditor() }
                        .buttonStyle(.bordered)
                    Button {
                        if !roomPoints.isEmpty { roomPoints.removeLast() }
                        roomEditorError = nil
                    } label: {
                        Label("Rückgängig", systemImage: "arrow.uturn.backward")
                    }
                    .buttonStyle(.bordered)
                    .disabled(roomPoints.isEmpty)
                    Spacer()
                    Button("Fläche fertig") {
                        if SemanticGeometry.isSimplePolygon(roomPoints) {
                            roomEditorPhase = .navigationGoal
                            roomEditorError = nil
                        } else {
                            roomEditorError = SemanticMapValidationError.invalidPolygon.localizedDescription
                        }
                    }
                    .buttonStyle(.borderedProminent)
                    .tint(RobotPalette.accent)
                    .disabled(!SemanticGeometry.isSimplePolygon(roomPoints))
                }
            } else {
                Text(
                    "Tippe jetzt innerhalb der Fläche auf einen freien, sicher erreichbaren "
                        + "Navigationspunkt."
                )
                .font(.caption)
                .foregroundStyle(RobotPalette.muted)

                HStack {
                    Text("Blickrichtung")
                        .font(.caption)
                    Slider(value: $navigationYaw, in: -Double.pi...Double.pi)
                        .tint(RobotPalette.accent)
                    Text("\(Int(navigationYaw * 180 / .pi))°")
                        .font(.caption.monospacedDigit())
                        .frame(width: 42, alignment: .trailing)
                }
                .disabled(mapController.semanticWriteState.isPending)

                HStack(spacing: 9) {
                    Button("Abbrechen") { resetRoomEditor() }
                        .buttonStyle(.bordered)
                    Button("Grenze ändern") {
                        navigationGoal = nil
                        roomEditorPhase = .polygon
                    }
                    .buttonStyle(.bordered)
                    Spacer()
                    Button {
                        saveRoom()
                    } label: {
                        if mapController.semanticWriteState.isPending {
                            ProgressView().tint(.white)
                        } else {
                            Text("Raum speichern")
                        }
                    }
                    .buttonStyle(.borderedProminent)
                    .tint(RobotPalette.accent)
                    .disabled(
                        navigationGoal == nil ||
                            roomName.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ||
                            !mapController.canEditRooms
                    )
                }
            }

            if let error = roomEditorError {
                Label(error, systemImage: "exclamationmark.triangle.fill")
                    .font(.caption)
                    .foregroundStyle(RobotPalette.danger)
            }
        }
    }

    @ViewBuilder
    private var semanticOperationNotice: some View {
        switch mapController.mapSaveState {
        case let .succeeded(message):
            Label(message, systemImage: "checkmark.circle.fill")
                .font(.caption)
                .foregroundStyle(RobotPalette.success)
        case let .failed(message):
            Label(message, systemImage: "xmark.octagon.fill")
                .font(.caption)
                .foregroundStyle(RobotPalette.danger)
        case let .statusUnknown(message):
            VStack(alignment: .leading, spacing: 7) {
                Label(message, systemImage: "arrow.trianglehead.2.clockwise.rotate.90")
                    .font(.caption)
                    .foregroundStyle(RobotPalette.danger)
                Button("Kartenstand neu laden") {
                    mapController.retry()
                }
                .buttonStyle(.bordered)
            }
        case .idle, .pending:
            EmptyView()
        }

        switch mapController.semanticWriteState {
        case let .pending(message):
            Label(message, systemImage: "arrow.triangle.2.circlepath")
                .font(.caption)
                .foregroundStyle(RobotPalette.highlight)
        case let .succeeded(message):
            Label(message, systemImage: "checkmark.circle.fill")
                .font(.caption)
                .foregroundStyle(RobotPalette.success)
        case let .failed(message):
            Label(message, systemImage: "xmark.octagon.fill")
                .font(.caption)
                .foregroundStyle(RobotPalette.danger)
        case let .revisionConflict(message), let .statusUnknown(message):
            VStack(alignment: .leading, spacing: 7) {
                Label(message, systemImage: "arrow.trianglehead.2.clockwise.rotate.90")
                    .font(.caption)
                    .foregroundStyle(RobotPalette.danger)
                Button("Kartenstand neu laden") {
                    mapController.retry()
                }
                .buttonStyle(.bordered)
            }
        case .idle:
            EmptyView()
        }
    }

    private var mapCard: some View {
        RobotCard {
            RobotMapCanvas(
                image: mapController.mapImage,
                map: mapController.map,
                rooms: mapController.displayedRooms,
                selectedRoomID: selectedRoomID,
                draftPoints: roomPoints,
                draftNavigationGoal: navigationGoal,
                editorIsActive: roomEditorPhase != .inactive,
                onMapTap: handleMapTap,
                contentID: mapController.map.map {
                    $0.contentFingerprint
                } ?? "keine-karte",
                showsOfflineOverlay: mapController.map != nil && !mapController.streamState.isLive
            )
            .frame(minHeight: 330, idealHeight: 420, maxHeight: 470)
        }
    }

    @ViewBuilder
    private var mapInformation: some View {
        if let map = mapController.map {
            RobotCard {
                VStack(alignment: .leading, spacing: 12) {
                    HStack {
                        Label("Kartendaten", systemImage: "ruler")
                            .font(.subheadline.weight(.semibold))
                        Spacer()
                        if let date = mapController.lastMapReceivedAt {
                            Text(
                                mapController.streamState.isLive
                                    ? "Empfangen \(date.formatted(date: .omitted, time: .standard))"
                                    : "Offline-Stand \(date.formatted(date: .abbreviated, time: .shortened))"
                            )
                                .font(.caption2.monospacedDigit())
                                .foregroundStyle(RobotPalette.muted)
                        }
                    }

                    HStack(alignment: .top, spacing: 12) {
                        mapValue(
                            title: "Größe",
                            value: String(
                                format: "%.1f × %.1f m",
                                Double(map.width) * map.resolution,
                                Double(map.height) * map.resolution
                            )
                        )
                        Divider().overlay(RobotPalette.line)
                        mapValue(
                            title: "Auflösung",
                            value: String(format: "%.1f cm", map.resolution * 100)
                        )
                        Divider().overlay(RobotPalette.line)
                        mapValue(
                            title: "Koordinaten",
                            value: map.frameID.isEmpty ? "map" : map.frameID
                        )
                    }

                    HStack(spacing: 14) {
                        legendItem(color: Color(white: 0.94), text: "frei")
                        legendItem(color: Color(white: 0.10), text: "belegt")
                        legendItem(color: Color(white: 0.48), text: "unbekannt")
                    }
                    .accessibilityElement(children: .combine)
                    .accessibilityLabel("Legende: frei, belegt und unbekannt")
                }
            }
        } else {
            RobotCard {
                VStack(spacing: 10) {
                    Image(systemName: "map")
                        .font(.largeTitle)
                        .foregroundStyle(RobotPalette.muted)
                    Text("Noch keine Karte empfangen")
                        .font(.headline)
                    Text(
                        "Sobald die Roboter-Software eine OccupancyGrid-Karte auf /map "
                            + "veröffentlicht, erscheint sie automatisch hier."
                    )
                    .font(.caption)
                    .foregroundStyle(RobotPalette.muted)
                    .multilineTextAlignment(.center)
                }
                .frame(maxWidth: .infinity)
            }
        }
    }

    private var emergencySection: some View {
        VStack(spacing: 7) {
            EmergencyStopButton(
                active: robotController.estopActive,
                pending: robotController.estopRequestPending,
                enabled: robotController.canSendEmergencyRequest
            ) {
                if robotController.estopActive == true {
                    showEstopReleaseConfirmation = true
                } else {
                    emergencyHaptic()
                    robotController.requestEstop(active: true)
                }
            }

            HStack(spacing: 5) {
                Image(systemName: safetyStatus.icon)
                Text(safetyStatus.text)
            }
            .font(.caption)
            .foregroundStyle(safetyStatus.color)
            .frame(maxWidth: .infinity, alignment: .leading)
        }
    }

    private var safetyFootnote: some View {
        Label(
            "Die Kartenansicht steuert keine Navigation. "
                + "Der Software-Not-Aus ersetzt nicht den Hardware-Not-Aus.",
            systemImage: "exclamationmark.shield.fill"
        )
        .font(.caption2)
        .foregroundStyle(RobotPalette.muted)
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.horizontal, 2)
    }

    private var mapSubtitle: String {
        guard let map = mapController.map else {
            return "Live-Ansicht des ROS-Topics /map"
        }
        let source = mapController.streamState.isLive
            ? "Live-Karte"
            : "gespeicherter Offline-Stand"
        return "\(map.width) × \(map.height) Zellen · \(source)"
    }

    private var mapStatusTone: StatusPill.Tone {
        switch mapController.streamState {
        case .live:
            return .success
        case .waitingForMap, .connecting, .waitingToReconnect:
            return .warning
        case .inactive:
            return .neutral
        case .failed:
            return .error
        }
    }

    private var safetyStatus: (text: String, icon: String, color: Color) {
        guard robotController.connectionState.isConnected else {
            return ("Software-Not-Aus offline", "wifi.slash", RobotPalette.danger)
        }
        guard robotController.estopIsFresh, let active = robotController.estopActive else {
            return ("Warte auf Sicherheitsstatus", "questionmark.circle", RobotPalette.highlight)
        }
        return active
            ? ("Software-Not-Aus ist aktiv", "exclamationmark.octagon.fill", RobotPalette.danger)
            : ("Sicherheitsstatus frei", "checkmark.shield.fill", RobotPalette.success)
    }

    private func mapValue(title: String, value: String) -> some View {
        VStack(alignment: .leading, spacing: 3) {
            Text(title)
                .font(.caption2)
                .foregroundStyle(RobotPalette.muted)
            Text(value)
                .font(.caption.weight(.semibold))
                .foregroundStyle(RobotPalette.text)
                .lineLimit(2)
                .minimumScaleFactor(0.7)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private func legendItem(color: Color, text: String) -> some View {
        HStack(spacing: 5) {
            RoundedRectangle(cornerRadius: 2)
                .fill(color)
                .frame(width: 14, height: 14)
                .overlay {
                    RoundedRectangle(cornerRadius: 2)
                        .stroke(RobotPalette.line, lineWidth: 1)
                }
            Text(text)
                .font(.caption2)
                .foregroundStyle(RobotPalette.muted)
        }
    }

    private var selectedRoom: SemanticRoom? {
        guard let selectedRoomID else { return nil }
        return mapController.displayedRooms.first { $0.id == selectedRoomID }
    }

    private func beginRoomEditing() {
        guard mapController.canEditRooms else { return }
        selectedRoomID = nil
        roomName = ""
        roomPoints = []
        navigationGoal = nil
        navigationYaw = 0
        roomEditorError = nil
        roomEditorPhase = .polygon
    }

    private func resetRoomEditor() {
        roomEditorPhase = .inactive
        roomName = ""
        roomPoints = []
        navigationGoal = nil
        navigationYaw = 0
        roomEditorError = nil
    }

    private func cancelRoomEditing(message: String) {
        resetRoomEditor()
        roomEditorError = message
    }

    private func handleMapTap(_ point: MapPoint) {
        guard !mapController.semanticWriteState.isPending else { return }
        switch roomEditorPhase {
        case .inactive:
            selectedRoomID = mapController.displayedRooms.reversed().first {
                SemanticGeometry.contains(point, in: $0.polygon)
            }?.id
        case .polygon:
            if let previous = roomPoints.last,
               hypot(point.x - previous.x, point.y - previous.y) < 0.01 {
                roomEditorError = "Der neue Eckpunkt liegt zu nah am vorherigen Punkt."
                return
            }
            roomPoints.append(point)
            roomEditorError = nil
        case .navigationGoal:
            guard SemanticGeometry.strictlyContains(point, in: roomPoints) else {
                roomEditorError = SemanticMapValidationError
                    .navigationGoalOutsideRoom.localizedDescription
                return
            }
            navigationGoal = point
            roomEditorError = nil
        }
    }

    private func saveRoom() {
        guard let navigationGoal else {
            roomEditorError = SemanticMapValidationError
                .navigationGoalOutsideRoom.localizedDescription
            return
        }
        do {
            let colors = [
                "#4FB3A5", "#F2B84B", "#6FA8FF", "#C77DFF",
                "#F57C93", "#70C1B3", "#FF9F68", "#8BC34A"
            ]
            let room = try SemanticRoom(
                id: "room-\(UUID().uuidString.lowercased())",
                name: roomName,
                color: colors[mapController.displayedRooms.count % colors.count],
                polygon: roomPoints,
                navigationGoal: SemanticNavigationGoal(
                    x: navigationGoal.x,
                    y: navigationGoal.y,
                    yaw: navigationYaw
                )
            )
            mapController.upsertRoom(room)
            roomEditorError = nil
        } catch {
            roomEditorError = error.localizedDescription
        }
    }

    private func roomColor(_ value: String?) -> Color {
        guard let value,
              value.count == 7,
              let parsed = UInt32(value.dropFirst(), radix: 16) else {
            return RobotPalette.accent
        }
        return Color(hex: parsed)
    }

    private func warningHaptic() {
        UINotificationFeedbackGenerator().notificationOccurred(.warning)
    }

    private func emergencyHaptic() {
        UINotificationFeedbackGenerator().notificationOccurred(.error)
    }
}

private struct RobotMapCanvas: View {
    let image: CGImage?
    let map: RobotMapSnapshot?
    let rooms: [SemanticRoom]
    let selectedRoomID: String?
    let draftPoints: [MapPoint]
    let draftNavigationGoal: MapPoint?
    let editorIsActive: Bool
    let onMapTap: (MapPoint) -> Void
    let contentID: String
    let showsOfflineOverlay: Bool

    @State private var scale: CGFloat = 1
    @State private var offset: CGSize = .zero
    @GestureState private var gestureScale: CGFloat = 1
    @GestureState private var gestureOffset: CGSize = .zero

    private var displayedScale: CGFloat {
        min(8, max(1, scale * gestureScale))
    }

    var body: some View {
        GeometryReader { proxy in
            ZStack {
                Color(hex: 0x0A0D10)

                if let image {
                    Image(image, scale: 1, label: Text("Wohnungskarte"))
                        .resizable()
                        .interpolation(.none)
                        .aspectRatio(contentMode: .fit)
                        .scaleEffect(displayedScale)
                        .offset(
                            x: offset.width + gestureOffset.width,
                            y: offset.height + gestureOffset.height
                        )

                    semanticOverlay(in: proxy.size)
                } else {
                    VStack(spacing: 10) {
                        ProgressView()
                            .tint(RobotPalette.accent)
                        Text("Warte auf Kartendaten …")
                            .font(.caption)
                            .foregroundStyle(RobotPalette.muted)
                    }
                }

                if showsOfflineOverlay {
                    VStack {
                        HStack {
                            Label("NICHT LIVE", systemImage: "wifi.slash")
                                .font(.caption.weight(.heavy))
                                .foregroundStyle(.white)
                                .padding(.horizontal, 9)
                                .frame(minHeight: 28)
                                .background(RobotPalette.danger.opacity(0.9))
                                .clipShape(Capsule())
                            Spacer()
                        }
                        Spacer()
                    }
                    .padding(10)
                }

            }
            .contentShape(Rectangle())
            .clipShape(RoundedRectangle(cornerRadius: 9, style: .continuous))
            .overlay {
                RoundedRectangle(cornerRadius: 9, style: .continuous)
                    .stroke(RobotPalette.line, lineWidth: 1)
            }
            .gesture(combinedGesture(in: proxy.size))
            .simultaneousGesture(
                SpatialTapGesture()
                    .onEnded { value in
                        guard let transform = viewportTransform(in: proxy.size),
                              let point = transform.mapPoint(
                                forScreenPoint: ViewportPoint(
                                    x: value.location.x,
                                    y: value.location.y
                                )
                              ) else {
                            return
                        }
                        onMapTap(point)
                    }
            )
            .onTapGesture(count: 2) {
                guard !editorIsActive else { return }
                withAnimation(.easeOut(duration: 0.2)) {
                    scale = 1
                    offset = .zero
                }
            }
            .onChange(of: contentID) { _ in
                scale = 1
                offset = .zero
            }
        }
    }

    private func semanticOverlay(in size: CGSize) -> some View {
        Canvas { context, canvasSize in
            guard let transform = viewportTransform(in: canvasSize) else { return }

            for room in rooms {
                let path = polygonPath(room.polygon, transform: transform)
                let color = roomColor(room.color)
                context.fill(path, with: .color(color.opacity(0.22)))
                context.stroke(
                    path,
                    with: .color(
                        room.id == selectedRoomID ? Color.white : color
                    ),
                    lineWidth: room.id == selectedRoomID ? 3 : 1.5
                )

                let goal = transform.screenPoint(for: room.navigationGoal.point)
                let goalRect = CGRect(
                    x: goal.x - 5,
                    y: goal.y - 5,
                    width: 10,
                    height: 10
                )
                context.fill(
                    Path(ellipseIn: goalRect),
                    with: .color(color)
                )
                context.stroke(
                    Path(ellipseIn: goalRect),
                    with: .color(.white),
                    lineWidth: 1.5
                )

                if let center = polygonCenter(room.polygon, transform: transform) {
                    context.draw(
                        Text(room.name)
                            .font(.caption2.weight(.bold))
                            .foregroundColor(.white),
                        at: center
                    )
                }
            }

            if !draftPoints.isEmpty {
                var draftPath = Path()
                let first = transform.screenPoint(for: draftPoints[0])
                draftPath.move(to: CGPoint(x: first.x, y: first.y))
                for point in draftPoints.dropFirst() {
                    let screen = transform.screenPoint(for: point)
                    draftPath.addLine(to: CGPoint(x: screen.x, y: screen.y))
                }
                if draftPoints.count >= 3 {
                    draftPath.closeSubpath()
                    context.fill(
                        draftPath,
                        with: .color(RobotPalette.highlight.opacity(0.18))
                    )
                }
                context.stroke(
                    draftPath,
                    with: .color(RobotPalette.highlight),
                    style: StrokeStyle(lineWidth: 2, dash: [7, 4])
                )

                for point in draftPoints {
                    let screen = transform.screenPoint(for: point)
                    let rect = CGRect(
                        x: screen.x - 5,
                        y: screen.y - 5,
                        width: 10,
                        height: 10
                    )
                    context.fill(Path(ellipseIn: rect), with: .color(RobotPalette.highlight))
                    context.stroke(Path(ellipseIn: rect), with: .color(.black), lineWidth: 1)
                }
            }

            if let draftNavigationGoal {
                let screen = transform.screenPoint(for: draftNavigationGoal)
                let outer = CGRect(
                    x: screen.x - 10,
                    y: screen.y - 10,
                    width: 20,
                    height: 20
                )
                context.fill(
                    Path(ellipseIn: outer),
                    with: .color(RobotPalette.success.opacity(0.9))
                )
                context.stroke(Path(ellipseIn: outer), with: .color(.white), lineWidth: 2)
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .allowsHitTesting(false)
    }

    private func polygonPath(
        _ polygon: [MapPoint],
        transform: RobotMapViewportTransform
    ) -> Path {
        var path = Path()
        guard let first = polygon.first else { return path }
        let firstScreen = transform.screenPoint(for: first)
        path.move(to: CGPoint(x: firstScreen.x, y: firstScreen.y))
        for point in polygon.dropFirst() {
            let screen = transform.screenPoint(for: point)
            path.addLine(to: CGPoint(x: screen.x, y: screen.y))
        }
        path.closeSubpath()
        return path
    }

    private func polygonCenter(
        _ polygon: [MapPoint],
        transform: RobotMapViewportTransform
    ) -> CGPoint? {
        guard !polygon.isEmpty else { return nil }
        let sum = polygon.reduce((x: 0.0, y: 0.0)) {
            ($0.x + $1.x, $0.y + $1.y)
        }
        let center = MapPoint(
            x: sum.x / Double(polygon.count),
            y: sum.y / Double(polygon.count)
        )
        let screen = transform.screenPoint(for: center)
        return CGPoint(x: screen.x, y: screen.y)
    }

    private func viewportTransform(in size: CGSize) -> RobotMapViewportTransform? {
        guard let map, size.width > 0, size.height > 0 else { return nil }
        return RobotMapViewportTransform(
            map: map,
            viewportWidth: size.width,
            viewportHeight: size.height,
            scale: displayedScale,
            offsetX: offset.width + gestureOffset.width,
            offsetY: offset.height + gestureOffset.height
        )
    }

    private func roomColor(_ value: String?) -> Color {
        guard let value,
              value.count == 7,
              let parsed = UInt32(value.dropFirst(), radix: 16) else {
            return RobotPalette.accent
        }
        return Color(hex: parsed)
    }

    private func combinedGesture(in size: CGSize) -> some Gesture {
        SimultaneousGesture(
            MagnificationGesture()
                .updating($gestureScale) { value, state, _ in
                    state = value
                }
                .onEnded { value in
                    setScale(scale * value, in: size)
                },
            DragGesture(minimumDistance: 4)
                .updating($gestureOffset) { value, state, _ in
                    guard displayedScale > 1 else {
                        state = .zero
                        return
                    }
                    state = value.translation
                }
                .onEnded { value in
                    guard scale > 1 else {
                        offset = .zero
                        return
                    }
                    let proposed = CGSize(
                        width: offset.width + value.translation.width,
                        height: offset.height + value.translation.height
                    )
                    offset = clampedOffset(proposed, in: size, scale: scale)
                }
        )
    }

    private func setScale(_ proposed: CGFloat, in size: CGSize) {
        let newScale = min(8, max(1, proposed))
        withAnimation(.easeOut(duration: 0.16)) {
            scale = newScale
            offset = newScale == 1
                ? .zero
                : clampedOffset(offset, in: size, scale: newScale)
        }
    }

    private func clampedOffset(
        _ proposed: CGSize,
        in size: CGSize,
        scale: CGFloat
    ) -> CGSize {
        let fittedSize = fittedImageSize(in: size)
        let maximumX = max(0, (fittedSize.width * scale - size.width) / 2)
        let maximumY = max(0, (fittedSize.height * scale - size.height) / 2)
        return CGSize(
            width: min(maximumX, max(-maximumX, proposed.width)),
            height: min(maximumY, max(-maximumY, proposed.height))
        )
    }

    private func fittedImageSize(in container: CGSize) -> CGSize {
        guard
            let image,
            image.width > 0,
            image.height > 0,
            container.width > 0,
            container.height > 0
        else {
            return container
        }

        let imageAspect = CGFloat(image.width) / CGFloat(image.height)
        let containerAspect = container.width / container.height
        if imageAspect > containerAspect {
            return CGSize(
                width: container.width,
                height: container.width / imageAspect
            )
        }
        return CGSize(
            width: container.height * imageAspect,
            height: container.height
        )
    }


}

#Preview {
    RobotMapView()
        .environmentObject(RobotController())
}
