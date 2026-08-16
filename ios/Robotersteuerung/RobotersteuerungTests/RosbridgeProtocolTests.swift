import Foundation
import Testing
@testable import Robotersteuerung

struct RosbridgeProtocolTests {
    @Test
    func setupFramesMatchExistingBrowserProtocol() throws {
        let frames = try RosbridgeProtocol.setupFrames()
        #expect(frames.count == 5)

        let decoded = try frames.map(jsonObject)
        #expect(decoded[0]["op"] as? String == "advertise")
        #expect(decoded[0]["topic"] as? String == RosbridgeTopics.command)
        #expect(decoded[0]["type"] as? String == "std_msgs/String")
        #expect(decoded[1]["topic"] as? String == RosbridgeTopics.estopRequest)
        #expect(decoded[1]["type"] as? String == "std_msgs/Bool")
        #expect(decoded[2]["op"] as? String == "subscribe")
        #expect(decoded[2]["topic"] as? String == RosbridgeTopics.status)
        #expect(decoded[3]["topic"] as? String == RosbridgeTopics.exploreStatus)
        #expect(decoded[4]["topic"] as? String == RosbridgeTopics.estop)
    }

    @Test
    func commandIsJSONEncodedInsideStdMsgsString() throws {
        let command = RobotCommand(
            type: "pick_and_place",
            object: "Tasse",
            room: "Kueche",
            target: "Tisch"
        )
        let outer = try jsonObject(RosbridgeProtocol.commandFrame(command))

        #expect(outer["op"] as? String == "publish")
        #expect(outer["topic"] as? String == RosbridgeTopics.command)

        let message = try #require(outer["msg"] as? [String: Any])
        let nestedText = try #require(message["data"] as? String)
        let nested = try jsonObject(nestedText)
        #expect(nested["type"] as? String == "pick_and_place")
        #expect(nested["object"] as? String == "Tasse")
        #expect(nested["room"] as? String == "Kueche")
        #expect(nested["target"] as? String == "Tisch")
    }

    @Test
    func unusedCommandFieldsAreNotSentAsNull() throws {
        let outer = try jsonObject(
            RosbridgeProtocol.commandFrame(RobotCommand(type: "explore"))
        )
        let message = try #require(outer["msg"] as? [String: Any])
        let nested = try jsonObject(try #require(message["data"] as? String))

        #expect(nested["type"] as? String == "explore")
        #expect(nested["object"] == nil)
        #expect(nested["room"] == nil)
        #expect(nested["target"] == nil)
    }

    @Test
    func estopRequestUsesRosBoolean() throws {
        let frame = try jsonObject(RosbridgeProtocol.estopFrame(active: true))
        let message = try #require(frame["msg"] as? [String: Any])

        #expect(frame["op"] as? String == "publish")
        #expect(frame["topic"] as? String == RosbridgeTopics.estopRequest)
        #expect(message["data"] as? Bool == true)
        #expect(message["data"] is String == false)
    }

    @Test
    func decodesMissionStatusEvent() throws {
        let status = """
        {
          "state":"running",
          "phase":"Navigation",
          "message":"Phase: Navigation",
          "progress":0.42,
          "active_command":{"type":"go_to_room","room":"Kueche"},
          "rooms":["Wohnzimmer","Kueche"],
          "pick_and_place_rooms":["Kueche"],
          "targets":["Tisch"],
          "objects":["Tasse"],
          "offboard_available":true,
          "cancel_pending":true,
          "last_rejection":"",
          "explore_execution":"bt_explicit_opt_in",
          "time":123.0
        }
        """
        let frame = try outerStringPublish(topic: RosbridgeTopics.status, data: status)
        let event = try RosbridgeProtocol.decodeEvent(from: frame)

        guard case let .status(decoded)? = event else {
            Issue.record("Status-Event erwartet")
            return
        }
        #expect(decoded.state == "running")
        #expect(decoded.phase == "Navigation")
        #expect(abs(decoded.normalizedProgress - 0.42) < 0.0001)
        #expect(decoded.activeCommand?.description == "Fahre: Kueche")
        #expect(decoded.pickAndPlaceRooms == ["Kueche"])
        #expect(decoded.offboardAvailable == true)
        #expect(decoded.cancelPending == true)
        #expect(decoded.exploreExecution == "bt_explicit_opt_in")
    }

    @Test
    func decodesCompleteExploreStatusEvent() throws {
        let status = """
        {
          "schema_version":1,
          "backend_ready":true,
          "state":"running",
          "phase":"coverage",
          "message":"Abdeckungsziel 3 wird angefahren",
          "strategy":"frontier_then_adaptive_coverage",
          "coverage_ratio":0.64,
          "coverage_percent":64.0,
          "target_coverage_percent":85.0,
          "reachable_area_m2":12.5,
          "covered_area_m2":8.0,
          "frontiers_visited":4,
          "coverage_goals_visited":2,
          "frontiers_remaining":0,
          "map_ready_to_save":false,
          "time":123.0
        }
        """
        let frame = try outerStringPublish(
            topic: RosbridgeTopics.exploreStatus,
            data: status
        )
        let event = try RosbridgeProtocol.decodeEvent(from: frame)

        guard case let .exploreStatus(decoded)? = event else {
            Issue.record("Erkundungsstatus erwartet")
            return
        }
        #expect(decoded.state == "running")
        #expect(decoded.phase == "coverage")
        #expect(abs(decoded.normalizedCoverage - 0.64) < 0.0001)
        #expect(decoded.coverageGoalsVisited == 2)
        #expect(decoded.mapReadyToSave == false)
    }

    @Test
    func rejectsIncompleteExploreStatus() throws {
        let frame = try outerStringPublish(
            topic: RosbridgeTopics.exploreStatus,
            data: "{\"state\":\"running\"}"
        )
        do {
            _ = try RosbridgeProtocol.decodeEvent(from: frame)
            Issue.record("Unvollständiger Erkundungsstatus hätte abgelehnt werden müssen")
        } catch RosbridgeProtocolError.invalidExploreStatusPayload {
            // Erwartet.
        }
    }

    @Test
    func progressIsClampedForDisplay() throws {
        let tooHigh = try decodeStatus(progress: 4.5)
        let negative = try decodeStatus(progress: -1)
        #expect(tooHigh.normalizedProgress == 1)
        #expect(negative.normalizedProgress == 0)
    }

    @Test
    func decodesEstopAsRealBoolean() throws {
        let activeFrame = """
        {"op":"publish","topic":"/safety/estop","msg":{"data":true}}
        """
        #expect(try RosbridgeProtocol.decodeEvent(from: activeFrame) == .estop(true))

        let stringFrame = """
        {"op":"publish","topic":"/safety/estop","msg":{"data":"true"}}
        """
        #expect(try RosbridgeProtocol.decodeEvent(from: stringFrame) == nil)
    }

    @Test
    func ignoresUnrelatedRosbridgeFrames() throws {
        let frame = """
        {"op":"publish","topic":"/unrelated","msg":{"data":true}}
        """
        #expect(try RosbridgeProtocol.decodeEvent(from: frame) == nil)
    }

    @Test
    func rejectsIncompleteMissionStatus() throws {
        let frame = try outerStringPublish(topic: RosbridgeTopics.status, data: "{}")
        do {
            _ = try RosbridgeProtocol.decodeEvent(from: frame)
            Issue.record("Unvollständiger Status hätte abgelehnt werden müssen")
        } catch RosbridgeProtocolError.invalidStatusPayload {
            // Erwartet.
        }
    }

    @Test
    func rejectsUnknownMissionState() throws {
        let status = """
        {
          "state":"mystery",
          "phase":"?",
          "message":"?",
          "progress":0,
          "active_command":{},
          "rooms":[],
          "targets":[],
          "objects":[],
          "offboard_available":null,
          "last_rejection":"",
          "time":123.0
        }
        """
        let frame = try outerStringPublish(topic: RosbridgeTopics.status, data: status)
        do {
            _ = try RosbridgeProtocol.decodeEvent(from: frame)
            Issue.record("Unbekannter Missionszustand hätte abgelehnt werden müssen")
        } catch RosbridgeProtocolError.invalidStatusPayload {
            // Erwartet.
        }
    }

    @Test
    func estopReleaseRequiresFreshActiveFeedback() {
        #expect(
            EstopRequestPolicy.allows(
                requestedActive: true,
                telemetryIsFresh: false,
                currentActive: nil
            )
        )
        #expect(
            EstopRequestPolicy.allows(
                requestedActive: false,
                telemetryIsFresh: true,
                currentActive: true
            )
        )
        #expect(
            !EstopRequestPolicy.allows(
                requestedActive: false,
                telemetryIsFresh: false,
                currentActive: true
            )
        )
        #expect(
            !EstopRequestPolicy.allows(
                requestedActive: false,
                telemetryIsFresh: true,
                currentActive: false
            )
        )
        #expect(
            !EstopRequestPolicy.allows(
                requestedActive: false,
                telemetryIsFresh: true,
                currentActive: nil
            )
        )
    }

    private func decodeStatus(progress: Double) throws -> MissionStatus {
        let status = """
        {
          "state":"running",
          "phase":"Test",
          "message":"Test",
          "progress":\(progress),
          "active_command":{},
          "rooms":[],
          "targets":[],
          "objects":[],
          "offboard_available":null,
          "last_rejection":"",
          "time":123.0
        }
        """
        let frame = try outerStringPublish(topic: RosbridgeTopics.status, data: status)
        guard case let .status(decoded)? = try RosbridgeProtocol.decodeEvent(from: frame) else {
            throw TestError.expectedStatus
        }
        return decoded
    }

    private func outerStringPublish(topic: String, data: String) throws -> String {
        let object: [String: Any] = [
            "op": "publish",
            "topic": topic,
            "msg": ["data": data]
        ]
        let encoded = try JSONSerialization.data(withJSONObject: object, options: [.sortedKeys])
        return try #require(String(data: encoded, encoding: .utf8))
    }

    private func jsonObject(_ text: String) throws -> [String: Any] {
        let data = try #require(text.data(using: .utf8))
        return try #require(
            JSONSerialization.jsonObject(with: data) as? [String: Any]
        )
    }

    private enum TestError: Error {
        case expectedStatus
    }
}
