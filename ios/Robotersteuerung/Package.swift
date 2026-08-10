// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "RobotersteuerungProtocolChecks",
    platforms: [
        .macOS(.v13)
    ],
    targets: [
        .target(
            name: "Robotersteuerung",
            path: "Robotersteuerung",
            exclude: [
                "Assets.xcassets",
                "Info.plist",
                "PrivacyInfo.xcprivacy",
                "RobotersteuerungApp.swift",
                "Services/RobotController.swift",
                "Services/RobotMapController.swift",
                "Views"
            ],
            sources: [
                "Models/RobotModels.swift",
                "Models/RobotMapModels.swift",
                "Services/RosbridgeProtocol.swift",
                "Services/MapRosbridgeProtocol.swift"
            ]
        ),
        .testTarget(
            name: "RobotersteuerungTests",
            dependencies: ["Robotersteuerung"],
            path: "RobotersteuerungTests"
        )
    ]
)
