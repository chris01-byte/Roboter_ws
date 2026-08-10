import SwiftUI

struct AmadeusRootView: View {
    var body: some View {
        TabView {
            DashboardView()
                .tabItem {
                    Label("Steuerung", systemImage: "gamecontroller.fill")
                }

            RobotMapView()
                .tabItem {
                    Label("Karte", systemImage: "map.fill")
                }
        }
        .tint(RobotPalette.accent)
        .preferredColorScheme(.dark)
    }
}

#Preview {
    AmadeusRootView()
        .environmentObject(RobotController())
}
