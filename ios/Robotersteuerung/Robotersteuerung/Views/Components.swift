import SwiftUI

enum RobotPalette {
    static let background = Color(hex: 0x0F1419)
    static let surface = Color(hex: 0x17202A)
    static let surfaceRaised = Color(hex: 0x1F2A35)
    static let line = Color(hex: 0x334251)
    static let text = Color(hex: 0xF4F7FB)
    static let muted = Color(hex: 0xAAB7C4)
    static let accent = Color(hex: 0x4FB3A5)
    static let highlight = Color(hex: 0xF2B84B)
    static let danger = Color(hex: 0xE05A47)
    static let dangerDark = Color(hex: 0x6E1D13)
    static let success = Color(hex: 0x4EB06A)
}

extension Color {
    init(hex: UInt32) {
        self.init(
            red: Double((hex >> 16) & 0xFF) / 255,
            green: Double((hex >> 8) & 0xFF) / 255,
            blue: Double(hex & 0xFF) / 255
        )
    }
}

struct RobotCard<Content: View>: View {
    @ViewBuilder let content: Content

    var body: some View {
        content
            .padding(14)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(RobotPalette.surface)
            .overlay {
                RoundedRectangle(cornerRadius: 12, style: .continuous)
                    .stroke(RobotPalette.line, lineWidth: 1)
            }
            .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
    }
}

struct StatusPill: View {
    enum Tone {
        case neutral
        case success
        case warning
        case error

        var color: Color {
            switch self {
            case .neutral: RobotPalette.muted
            case .success: RobotPalette.success
            case .warning: RobotPalette.highlight
            case .error: RobotPalette.danger
            }
        }
    }

    let text: String
    let tone: Tone

    var body: some View {
        Text(text)
            .font(.caption.weight(.medium))
            .lineLimit(1)
            .foregroundStyle(tone.color)
            .padding(.horizontal, 10)
            .frame(minHeight: 27)
            .background(tone.color.opacity(0.08))
            .overlay {
                Capsule().stroke(tone.color.opacity(0.72), lineWidth: 1)
            }
            .clipShape(Capsule())
    }
}

struct CatalogPicker: View {
    let title: String
    let values: [String]
    @Binding var selection: String

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(title)
                .font(.caption)
                .foregroundStyle(RobotPalette.muted)

            if values.isEmpty {
                Text("Keine Einträge")
                    .foregroundStyle(RobotPalette.danger)
                    .frame(maxWidth: .infinity, minHeight: 46, alignment: .leading)
                    .padding(.horizontal, 12)
                    .background(RobotPalette.surfaceRaised)
                    .clipShape(RoundedRectangle(cornerRadius: 9, style: .continuous))
            } else {
                Picker(title, selection: $selection) {
                    ForEach(values, id: \.self) { value in
                        Text(value).tag(value)
                    }
                }
                .labelsHidden()
                .pickerStyle(.menu)
                .tint(RobotPalette.text)
                .frame(maxWidth: .infinity, minHeight: 46, alignment: .leading)
                .padding(.horizontal, 4)
                .background(RobotPalette.surfaceRaised)
                .overlay {
                    RoundedRectangle(cornerRadius: 9, style: .continuous)
                        .stroke(RobotPalette.line, lineWidth: 1)
                }
                .clipShape(RoundedRectangle(cornerRadius: 9, style: .continuous))
            }
        }
    }
}

struct PrimaryActionButton: View {
    let title: String
    let systemImage: String
    let enabled: Bool
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            Label(title, systemImage: systemImage)
                .font(.body.weight(.bold))
                .frame(maxWidth: .infinity, minHeight: 50)
                .foregroundStyle(Color(hex: 0x061412))
                .background(RobotPalette.accent)
                .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
        }
        .buttonStyle(.plain)
        .disabled(!enabled)
        .opacity(enabled ? 1 : 0.42)
    }
}

struct EmergencyStopButton: View {
    let active: Bool?
    let pending: Bool
    let enabled: Bool
    let action: () -> Void

    @State private var pulse = false

    var body: some View {
        Button(action: action) {
            HStack(spacing: 10) {
                if pending {
                    ProgressView()
                        .tint(.white)
                } else {
                    Image(systemName: active == true ? "lock.open.fill" : "stop.fill")
                }
                Text(active == true ? "NOT-AUS FREIGEBEN" : "NOT-AUS")
                    .lineLimit(1)
            }
            .font(.headline.weight(.heavy))
            .tracking(1.1)
            .frame(maxWidth: .infinity, minHeight: 64)
            .foregroundStyle(.white)
            .background(active == true ? RobotPalette.dangerDark : RobotPalette.danger)
            .overlay {
                RoundedRectangle(cornerRadius: 12, style: .continuous)
                    .stroke(
                        Color.white.opacity(active == true ? (pulse ? 0.25 : 0.9) : 0.3),
                        lineWidth: active == true ? (pulse ? 2 : 5) : 2
                    )
            }
            .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
            .shadow(
                color: active == true ? RobotPalette.danger.opacity(pulse ? 0.2 : 0.8) : .clear,
                radius: active == true ? (pulse ? 3 : 10) : 0
            )
        }
        .buttonStyle(.plain)
        .disabled(!enabled || pending)
        .opacity(enabled ? 1 : 0.48)
        .onAppear {
            updatePulse(active: active == true)
        }
        .onChange(of: active) { value in
            updatePulse(active: value == true)
        }
        .accessibilityHint(
            active == true
                ? "Öffnet eine Bestätigung zum Freigeben des Software-Not-Aus."
                : "Fordert den sofortigen Software-Not-Aus an."
        )
    }

    private func updatePulse(active: Bool) {
        guard active else {
            pulse = false
            return
        }
        pulse = false
        withAnimation(.easeInOut(duration: 0.9).repeatForever(autoreverses: true)) {
            pulse = true
        }
    }
}

extension StatusPill.Tone {
    static func mission(_ state: String) -> Self {
        switch state {
        case "success": .success
        case "running": .warning
        case "failed", "canceled": .error
        default: .neutral
        }
    }
}
