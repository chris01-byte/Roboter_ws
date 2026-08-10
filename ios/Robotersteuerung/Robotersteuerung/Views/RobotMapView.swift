import SwiftUI
import UIKit

struct RobotMapView: View {
    @EnvironmentObject private var robotController: RobotController
    @Environment(\.scenePhase) private var scenePhase

    @StateObject private var mapController = RobotMapController()
    @State private var isVisible = false
    @State private var showEstopReleaseConfirmation = false

    var body: some View {
        ZStack {
            RobotPalette.background
                .ignoresSafeArea()

            ScrollView {
                LazyVStack(spacing: 12) {
                    header
                    connectionNotice
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

    private var mapCard: some View {
        RobotCard {
            RobotMapCanvas(
                image: mapController.mapImage,
                contentID: mapController.map.map {
                    "\($0.width)x\($0.height)"
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
                            Text("Empfangen \(date.formatted(date: .omitted, time: .standard))")
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
        return "\(map.width) × \(map.height) Zellen · letzte gültige Karte bleibt sichtbar"
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

    private func warningHaptic() {
        UINotificationFeedbackGenerator().notificationOccurred(.warning)
    }

    private func emergencyHaptic() {
        UINotificationFeedbackGenerator().notificationOccurred(.error)
    }
}

private struct RobotMapCanvas: View {
    let image: CGImage?
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

                VStack {
                    Spacer()
                    HStack(spacing: 8) {
                        Spacer()
                        mapControlButton(
                            icon: "minus.magnifyingglass",
                            label: "Verkleinern"
                        ) {
                            setScale(scale / 1.5, in: proxy.size)
                        }
                        mapControlButton(icon: "arrow.counterclockwise", label: "Ansicht zurücksetzen") {
                            withAnimation(.easeOut(duration: 0.2)) {
                                scale = 1
                                offset = .zero
                            }
                        }
                        mapControlButton(
                            icon: "plus.magnifyingglass",
                            label: "Vergrößern"
                        ) {
                            setScale(scale * 1.5, in: proxy.size)
                        }
                    }
                }
                .padding(10)
            }
            .contentShape(Rectangle())
            .clipShape(RoundedRectangle(cornerRadius: 9, style: .continuous))
            .overlay {
                RoundedRectangle(cornerRadius: 9, style: .continuous)
                    .stroke(RobotPalette.line, lineWidth: 1)
            }
            .gesture(combinedGesture(in: proxy.size))
            .onTapGesture(count: 2) {
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

    private func mapControlButton(
        icon: String,
        label: String,
        action: @escaping () -> Void
    ) -> some View {
        Button(action: action) {
            Image(systemName: icon)
                .font(.body.weight(.semibold))
                .frame(width: 44, height: 44)
                .foregroundStyle(RobotPalette.text)
                .background(RobotPalette.surfaceRaised.opacity(0.94))
                .overlay {
                    RoundedRectangle(cornerRadius: 9, style: .continuous)
                        .stroke(RobotPalette.line, lineWidth: 1)
                }
                .clipShape(RoundedRectangle(cornerRadius: 9, style: .continuous))
        }
        .buttonStyle(.plain)
        .accessibilityLabel(label)
    }
}

#Preview {
    RobotMapView()
        .environmentObject(RobotController())
}
