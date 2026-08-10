import SwiftUI

@main
struct RobotersteuerungApp: App {
    @StateObject private var controller = RobotController()

    var body: some Scene {
        WindowGroup {
            AmadeusRootView()
                .environmentObject(controller)
        }
    }
}
