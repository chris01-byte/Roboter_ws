import SwiftUI
import UIKit

struct DashboardView: View {
    @EnvironmentObject private var controller: RobotController
    @Environment(\.scenePhase) private var scenePhase

    @State private var selectedMission: MissionKind = .room
    @State private var showEstopReleaseConfirmation = false
    @FocusState private var bridgeFieldFocused: Bool

    private let tabColumns = Array(repeating: GridItem(.flexible(), spacing: 6), count: 4)

    var body: some View {
        ZStack {
            RobotPalette.background
                .ignoresSafeArea()

            ScrollView {
                LazyVStack(spacing: 12) {
                    header
                    connectionCard
                    statusCard
                    missionTabs
                    missionCard
                    emergencySection
                    quickActions
                    logCard
                    safetyFootnote
                }
                .padding(.horizontal, 14)
                .padding(.top, 12)
                .padding(.bottom, 24)
                .frame(maxWidth: 560)
                .frame(maxWidth: .infinity)
            }
            .scrollDismissesKeyboard(.interactively)
        }
        .preferredColorScheme(.dark)
        .task {
            controller.start()
        }
        .onChange(of: scenePhase) { phase in
            switch phase {
            case .active:
                controller.appDidBecomeActive()
            case .background:
                controller.appDidEnterBackground()
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
                controller.requestEstop(active: false)
            }
        } message: {
            Text(
                "Nur freigeben, wenn der Gefahrenbereich kontrolliert wurde. "
                    + "Der Roboter erhält anschließend wieder die Software-Freigabe."
            )
        }
    }

    private var header: some View {
        HStack(alignment: .top, spacing: 12) {
            VStack(alignment: .leading, spacing: 4) {
                Label {
                    Text("Amadeus")
                } icon: {
                    Image(systemName: "cpu")
                        .foregroundStyle(RobotPalette.accent)
                }
                .font(.title2.weight(.bold))

                Text(controller.missionLine)
                    .font(.subheadline)
                    .foregroundStyle(RobotPalette.muted)
                    .lineLimit(3)
                    .animation(.default, value: controller.missionLine)
            }
            .frame(maxWidth: .infinity, alignment: .leading)

            VStack(alignment: .trailing, spacing: 6) {
                StatusPill(
                    text: controller.connectionState.label,
                    tone: controller.connectionState.isConnected ? .success : .error
                )
                StatusPill(
                    text: controller.missionState,
                    tone: .mission(controller.missionState)
                )
                StatusPill(
                    text: aiStatus.text,
                    tone: aiStatus.tone
                )
            }
        }
        .accessibilityElement(children: .contain)
    }

    private var connectionCard: some View {
        RobotCard {
            VStack(alignment: .leading, spacing: 8) {
                HStack {
                    Label("rosbridge", systemImage: "network")
                        .font(.caption)
                        .foregroundStyle(RobotPalette.muted)
                    Spacer()
                    Circle()
                        .fill(controller.connectionState.isConnected
                              ? RobotPalette.success
                              : RobotPalette.danger)
                        .frame(width: 8, height: 8)
                    Text(controller.connectionState.isConnected ? "online" : "offline")
                        .font(.caption2)
                        .foregroundStyle(RobotPalette.muted)
                }

                HStack(spacing: 8) {
                    TextField("ws://JETSON-IP:9090/", text: $controller.bridgeURL)
                        .keyboardType(.URL)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                        .submitLabel(.go)
                        .focused($bridgeFieldFocused)
                        .onSubmit {
                            bridgeFieldFocused = false
                            controller.connectNow()
                        }
                        .padding(.horizontal, 12)
                        .frame(minHeight: 48)
                        .background(RobotPalette.surfaceRaised)
                        .overlay {
                            RoundedRectangle(cornerRadius: 9, style: .continuous)
                                .stroke(RobotPalette.line, lineWidth: 1)
                        }
                        .clipShape(RoundedRectangle(cornerRadius: 9, style: .continuous))

                    Button {
                        bridgeFieldFocused = false
                        controller.connectNow()
                    } label: {
                        Group {
                            if case .connecting = controller.connectionState {
                                ProgressView()
                                    .tint(RobotPalette.text)
                            } else {
                                Image(systemName: "power")
                            }
                        }
                        .font(.title3.weight(.semibold))
                        .frame(width: 48, height: 48)
                        .foregroundStyle(RobotPalette.text)
                        .background(RobotPalette.surfaceRaised)
                        .overlay {
                            RoundedRectangle(cornerRadius: 9, style: .continuous)
                                .stroke(RobotPalette.line, lineWidth: 1)
                        }
                        .clipShape(RoundedRectangle(cornerRadius: 9, style: .continuous))
                    }
                    .buttonStyle(.plain)
                    .accessibilityLabel("Mit rosbridge verbinden")
                }

                if let error = controller.lastConnectionError {
                    Label(error, systemImage: "exclamationmark.triangle.fill")
                        .font(.caption)
                        .foregroundStyle(RobotPalette.danger)
                        .fixedSize(horizontal: false, vertical: true)
                }

                if controller.connectionState.isConnected {
                    Button("Verbindung trennen") {
                        controller.disconnect()
                    }
                    .font(.caption)
                    .foregroundStyle(RobotPalette.muted)
                }
            }
        }
    }

    private var statusCard: some View {
        RobotCard {
            VStack(spacing: 12) {
                HStack {
                    Label("Missionsstatus", systemImage: "waveform.path.ecg")
                        .font(.subheadline.weight(.semibold))
                    Spacer()
                    Label(
                        controller.statusIsFresh ? "live" : "veraltet",
                        systemImage: controller.statusIsFresh
                            ? "checkmark.circle.fill"
                            : "clock.badge.exclamationmark"
                    )
                    .font(.caption)
                    .foregroundStyle(
                        controller.statusIsFresh ? RobotPalette.success : RobotPalette.muted
                    )
                }

                ProgressView(value: controller.progress)
                    .tint(RobotPalette.accent)
                    .animation(.easeOut(duration: 0.18), value: controller.progress)
                    .accessibilityLabel("Missionsfortschritt")
                    .accessibilityValue("\(Int((controller.progress * 100).rounded())) Prozent")

                HStack(alignment: .top, spacing: 12) {
                    statusValue(title: "Phase", value: controller.phase)
                    Divider().overlay(RobotPalette.line)
                    statusValue(title: "Auftrag", value: controller.activeCommandDescription)
                }
            }
        }
    }

    private var missionTabs: some View {
        LazyVGrid(columns: tabColumns, spacing: 6) {
            ForEach(MissionKind.allCases) { mission in
                Button {
                    selectedMission = mission
                    selectionHaptic()
                } label: {
                    VStack(spacing: 5) {
                        Image(systemName: mission.systemImage)
                        Text(mission.title)
                            .font(.caption.weight(.semibold))
                            .minimumScaleFactor(0.75)
                    }
                    .frame(maxWidth: .infinity, minHeight: 55)
                    .foregroundStyle(
                        selectedMission == mission
                            ? Color(hex: 0x15100A)
                            : RobotPalette.muted
                    )
                    .background(
                        selectedMission == mission
                            ? RobotPalette.highlight
                            : RobotPalette.surfaceRaised
                    )
                    .overlay {
                        RoundedRectangle(cornerRadius: 9, style: .continuous)
                            .stroke(
                                selectedMission == mission ? .clear : RobotPalette.line,
                                lineWidth: 1
                            )
                    }
                    .clipShape(RoundedRectangle(cornerRadius: 9, style: .continuous))
                }
                .buttonStyle(.plain)
            }
        }
        .accessibilityElement(children: .contain)
        .accessibilityLabel("Missionstyp")
    }

    @ViewBuilder
    private var missionCard: some View {
        RobotCard {
            VStack(spacing: 12) {
                switch selectedMission {
                case .room:
                    CatalogPicker(
                        title: "Raum",
                        values: controller.rooms,
                        selection: $controller.selectedRoom
                    )
                    PrimaryActionButton(
                        title: "Fahren",
                        systemImage: "location.fill",
                        enabled: controller.canSendMission && !controller.rooms.isEmpty
                    ) {
                        commandHaptic()
                        controller.goToSelectedRoom()
                    }

                case .pick:
                    CatalogPicker(
                        title: "Objekt",
                        values: controller.objects,
                        selection: $controller.selectedPickObject
                    )
                    PrimaryActionButton(
                        title: "Greifen",
                        systemImage: "hand.point.up.left.fill",
                        enabled: controller.canSendMission && !controller.objects.isEmpty
                    ) {
                        commandHaptic()
                        controller.pickSelectedObject()
                    }

                case .carry:
                    CatalogPicker(
                        title: "Objekt",
                        values: controller.objects,
                        selection: $controller.selectedCarryObject
                    )
                    HStack(alignment: .top, spacing: 10) {
                        CatalogPicker(
                            title: "Zielraum",
                            values: controller.rooms,
                            selection: $controller.selectedCarryRoom
                        )
                        CatalogPicker(
                            title: "Ablage",
                            values: controller.targets,
                            selection: $controller.selectedTarget
                        )
                    }
                    PrimaryActionButton(
                        title: "Bringen",
                        systemImage: "shippingbox.fill",
                        enabled: controller.canSendMission &&
                            !controller.objects.isEmpty &&
                            !controller.rooms.isEmpty &&
                            !controller.targets.isEmpty
                    ) {
                        commandHaptic()
                        controller.carrySelectedObject()
                    }

                case .explore:
                    Text(
                        "Der Roboter erkundet die Wohnung selbstständig mit der "
                            + "Frontier-Methode und baut dabei sein Objektgedächtnis auf."
                    )
                    .font(.subheadline)
                    .foregroundStyle(RobotPalette.muted)
                    .frame(maxWidth: .infinity, alignment: .leading)

                    PrimaryActionButton(
                        title: "Erkundung starten",
                        systemImage: "map.fill",
                        enabled: controller.canSendMission
                    ) {
                        commandHaptic()
                        controller.startExploration()
                    }
                }

                if let disabledReason = missionDisabledReason {
                    Label(disabledReason, systemImage: "info.circle")
                        .font(.caption)
                        .foregroundStyle(RobotPalette.muted)
                        .frame(maxWidth: .infinity, alignment: .leading)
                }
            }
        }
    }

    private var emergencySection: some View {
        VStack(spacing: 7) {
            EmergencyStopButton(
                active: controller.estopActive,
                pending: controller.estopRequestPending,
                enabled: controller.canSendEmergencyRequest
            ) {
                if controller.estopActive == true {
                    showEstopReleaseConfirmation = true
                } else {
                    emergencyHaptic()
                    controller.requestEstop(active: true)
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

    private var quickActions: some View {
        HStack(spacing: 8) {
            Button {
                warningHaptic()
                controller.cancelMission()
            } label: {
                Label("Mission stoppen", systemImage: "xmark.octagon.fill")
                    .font(.subheadline.weight(.bold))
                    .frame(maxWidth: .infinity, minHeight: 48)
                    .foregroundStyle(.white)
                    .background(RobotPalette.danger)
                    .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
            }
            .buttonStyle(.plain)
            .disabled(!controller.canCancelMission)
            .opacity(controller.canCancelMission ? 1 : 0.42)

            Button {
                controller.refreshDisplayedStatus()
            } label: {
                Label("Status", systemImage: "arrow.clockwise")
                    .font(.subheadline.weight(.semibold))
                    .frame(maxWidth: .infinity, minHeight: 48)
                    .foregroundStyle(RobotPalette.text)
                    .background(RobotPalette.surfaceRaised)
                    .overlay {
                        RoundedRectangle(cornerRadius: 10, style: .continuous)
                            .stroke(RobotPalette.line, lineWidth: 1)
                    }
                    .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
            }
            .buttonStyle(.plain)
        }
    }

    private var logCard: some View {
        RobotCard {
            VStack(alignment: .leading, spacing: 9) {
                Label("Log", systemImage: "list.bullet.rectangle")
                    .font(.subheadline.weight(.semibold))

                if controller.logEntries.isEmpty {
                    Text("Noch keine Ereignisse")
                        .font(.caption)
                        .foregroundStyle(RobotPalette.muted)
                        .frame(maxWidth: .infinity, minHeight: 56)
                } else {
                    ScrollView {
                        LazyVStack(alignment: .leading, spacing: 8) {
                            ForEach(controller.logEntries) { entry in
                                HStack(alignment: .firstTextBaseline, spacing: 7) {
                                    Circle()
                                        .fill(logColor(entry.kind))
                                        .frame(width: 7, height: 7)
                                    Text(entry.date, style: .time)
                                        .font(.caption2.monospacedDigit())
                                        .foregroundStyle(RobotPalette.muted)
                                    Text(entry.message)
                                        .font(.caption)
                                        .foregroundStyle(RobotPalette.muted)
                                        .frame(maxWidth: .infinity, alignment: .leading)
                                }
                            }
                        }
                    }
                    .frame(maxHeight: 220)
                }
            }
        }
    }

    private var safetyFootnote: some View {
        Label(
            "Der Software-Not-Aus ersetzt nicht den verdrahteten Hardware-Not-Aus.",
            systemImage: "exclamationmark.shield.fill"
        )
        .font(.caption2)
        .foregroundStyle(RobotPalette.muted)
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.horizontal, 2)
    }

    private func statusValue(title: String, value: String) -> some View {
        VStack(alignment: .leading, spacing: 3) {
            Text(title)
                .font(.caption2)
                .foregroundStyle(RobotPalette.muted)
            Text(value)
                .font(.subheadline.weight(.semibold))
                .lineLimit(3)
                .frame(maxWidth: .infinity, minHeight: 22, alignment: .topLeading)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private var aiStatus: (text: String, tone: StatusPill.Tone) {
        switch controller.offboardAvailable {
        case true:
            return ("KI verbunden", .success)
        case false:
            return ("KI getrennt", .error)
        case nil:
            return ("KI unbekannt", .neutral)
        }
    }

    private var safetyStatus: (text: String, icon: String, color: Color) {
        guard controller.connectionState.isConnected else {
            return ("Software-Not-Aus offline", "wifi.slash", RobotPalette.danger)
        }
        guard controller.estopIsFresh, let active = controller.estopActive else {
            return ("Warte auf Sicherheitsstatus", "questionmark.circle", RobotPalette.highlight)
        }
        return active
            ? ("Software-Not-Aus ist aktiv", "exclamationmark.octagon.fill", RobotPalette.danger)
            : ("Sicherheitsstatus frei", "checkmark.shield.fill", RobotPalette.success)
    }

    private var missionDisabledReason: String? {
        guard controller.connectionState.isConnected else {
            return "Missionen sind ohne rosbridge-Verbindung gesperrt."
        }
        guard controller.statusIsFresh else {
            return "Warte auf einen aktuellen Missionsstatus."
        }
        guard controller.estopIsFresh else {
            return "Warte auf den Sicherheitsstatus."
        }
        if controller.estopActive == true {
            return "Missionen sind bei aktivem NOT-AUS gesperrt."
        }
        if controller.missionRequestPending {
            return "Auftrag gesendet – warte auf Bestätigung des Roboters."
        }
        if controller.cancelIsPending {
            return "Der Missionsabbruch wird vom Roboter bestätigt."
        }
        if controller.missionState == "running" {
            return "Eine Mission läuft; neue Aufträge bleiben bis zum Abschluss gesperrt."
        }
        return nil
    }

    private func logColor(_ kind: RobotLogKind) -> Color {
        switch kind {
        case .info: RobotPalette.muted
        case .success: RobotPalette.success
        case .warning: RobotPalette.highlight
        case .error, .emergency: RobotPalette.danger
        }
    }

    private func selectionHaptic() {
        UISelectionFeedbackGenerator().selectionChanged()
    }

    private func commandHaptic() {
        UIImpactFeedbackGenerator(style: .medium).impactOccurred()
    }

    private func warningHaptic() {
        UINotificationFeedbackGenerator().notificationOccurred(.warning)
    }

    private func emergencyHaptic() {
        UINotificationFeedbackGenerator().notificationOccurred(.error)
    }
}

#Preview {
    DashboardView()
        .environmentObject(RobotController())
}
