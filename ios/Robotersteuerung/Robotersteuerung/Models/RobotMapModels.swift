import Foundation

struct RobotMapOrigin: Sendable, Equatable {
    let positionX: Double
    let positionY: Double
    let positionZ: Double
    let orientationX: Double
    let orientationY: Double
    let orientationZ: Double
    let orientationW: Double

    var yaw: Double {
        atan2(
            2 * (orientationW * orientationZ + orientationX * orientationY),
            1 - 2 * (orientationY * orientationY + orientationZ * orientationZ)
        )
    }

    fileprivate var isValid: Bool {
        let components = [
            positionX,
            positionY,
            positionZ,
            orientationX,
            orientationY,
            orientationZ,
            orientationW
        ]
        guard components.allSatisfy(\.isFinite) else { return false }

        let quaternionLengthSquared =
            orientationX * orientationX +
            orientationY * orientationY +
            orientationZ * orientationZ +
            orientationW * orientationW
        return quaternionLengthSquared.isFinite && quaternionLengthSquared > 1e-12
    }
}

struct RobotMapSnapshot: Sendable, Equatable {
    static let maximumCellCount = 4_000_000

    let width: Int
    let height: Int
    let resolution: Double
    let origin: RobotMapOrigin
    let frameID: String
    let cells: [Int8]

    init(
        width: Int,
        height: Int,
        resolution: Double,
        origin: RobotMapOrigin,
        frameID: String,
        cells: [Int]
    ) throws {
        guard width > 0, height > 0 else {
            throw RobotMapValidationError.invalidDimensions(width: width, height: height)
        }

        let (cellCount, overflow) = width.multipliedReportingOverflow(by: height)
        guard !overflow else {
            throw RobotMapValidationError.cellCountOverflow(width: width, height: height)
        }
        guard cellCount <= RobotMapSnapshot.maximumCellCount else {
            throw RobotMapValidationError.cellLimitExceeded(
                actual: cellCount,
                maximum: RobotMapSnapshot.maximumCellCount
            )
        }
        guard resolution.isFinite, resolution > 0 else {
            throw RobotMapValidationError.invalidResolution(resolution)
        }
        guard origin.isValid else {
            throw RobotMapValidationError.invalidOrigin
        }

        let cleanedFrameID = frameID.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !cleanedFrameID.isEmpty else {
            throw RobotMapValidationError.invalidFrameID
        }
        guard cells.count == cellCount else {
            throw RobotMapValidationError.invalidDataLength(
                expected: cellCount,
                actual: cells.count
            )
        }

        for (index, value) in cells.enumerated() where !(-1...100).contains(value) {
            throw RobotMapValidationError.invalidOccupancyValue(index: index, value: value)
        }

        self.width = width
        self.height = height
        self.resolution = resolution
        self.origin = origin
        self.frameID = cleanedFrameID
        self.cells = cells.map { Int8($0) }
    }

    /// Liefert RGBA8888-Pixel in Bildkoordinaten (erste Zeile oben).
    ///
    /// `OccupancyGrid.data` beginnt dagegen links unten. Deshalb werden die
    /// Zeilen beim Rendern vertikal gespiegelt. Unbekannte Zellen sind grau,
    /// freie weiß und vollständig belegte schwarz. Zwischenwerte werden
    /// deterministisch als Graustufen interpoliert.
    func rgbaPixels() -> [UInt8] {
        var pixels = [UInt8](repeating: 0, count: cells.count * 4)

        for imageY in 0..<height {
            let sourceY = height - 1 - imageY
            for x in 0..<width {
                let sourceIndex = sourceY * width + x
                let destinationOffset = (imageY * width + x) * 4
                let pixel = Self.rgba(for: cells[sourceIndex])

                pixels[destinationOffset] = pixel.red
                pixels[destinationOffset + 1] = pixel.green
                pixels[destinationOffset + 2] = pixel.blue
                pixels[destinationOffset + 3] = pixel.alpha
            }
        }

        return pixels
    }

    private static func rgba(for occupancy: Int8) -> (
        red: UInt8,
        green: UInt8,
        blue: UInt8,
        alpha: UInt8
    ) {
        guard occupancy >= 0 else {
            return (127, 127, 127, 255)
        }

        let value = Int(occupancy)
        let gray = UInt8(((100 - value) * 255 + 50) / 100)
        return (gray, gray, gray, 255)
    }
}

enum RobotMapValidationError: Error, LocalizedError, Sendable, Equatable {
    case invalidDimensions(width: Int, height: Int)
    case cellCountOverflow(width: Int, height: Int)
    case cellLimitExceeded(actual: Int, maximum: Int)
    case invalidResolution(Double)
    case invalidOrigin
    case invalidFrameID
    case invalidDataLength(expected: Int, actual: Int)
    case invalidOccupancyValue(index: Int, value: Int)

    var errorDescription: String? {
        switch self {
        case let .invalidDimensions(width, height):
            return "Die Karte hat ungültige Abmessungen (\(width) × \(height))."
        case let .cellCountOverflow(width, height):
            return "Die Zellzahl der Karte \(width) × \(height) ist nicht darstellbar."
        case let .cellLimitExceeded(actual, maximum):
            return "Die Karte enthält \(actual) Zellen; erlaubt sind höchstens \(maximum)."
        case let .invalidResolution(resolution):
            return "Die Kartenauflösung \(resolution) ist ungültig."
        case .invalidOrigin:
            return "Der Kartenursprung enthält keine gültige endliche Pose."
        case .invalidFrameID:
            return "Die Karte enthält keine gültige ROS-Frame-ID."
        case let .invalidDataLength(expected, actual):
            return "Die Karte erwartet \(expected) Zellwerte, enthält aber \(actual)."
        case let .invalidOccupancyValue(index, value):
            return "Der Kartenwert \(value) an Position \(index) liegt nicht zwischen -1 und 100."
        }
    }
}
