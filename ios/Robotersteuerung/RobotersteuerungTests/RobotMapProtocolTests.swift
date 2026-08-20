import Foundation
import Testing
@testable import Robotersteuerung

struct RobotMapProtocolTests {
    @Test
    func mapSubscriptionFramesContainOnlyTheRequiredFields() throws {
        let subscribe = try jsonObject(MapRosbridgeProtocol.subscribeFrame())
        #expect(Set(subscribe.keys) == [
            "op",
            "id",
            "topic",
            "throttle_rate",
            "queue_length"
        ])
        #expect(subscribe["op"] as? String == "subscribe")
        #expect(subscribe["id"] as? String == "amadeus-map")
        #expect(subscribe["topic"] as? String == "/map")
        #expect(subscribe["throttle_rate"] as? Int == 1_000)
        #expect(subscribe["queue_length"] as? Int == 1)

        let unsubscribe = try jsonObject(MapRosbridgeProtocol.unsubscribeFrame())
        #expect(Set(unsubscribe.keys) == ["op", "id", "topic"])
        #expect(unsubscribe["op"] as? String == "unsubscribe")
        #expect(unsubscribe["id"] as? String == "amadeus-map")
        #expect(unsubscribe["topic"] as? String == "/map")
    }

    @Test
    func decodesValidOccupancyGridPublish() throws {
        let frame = try mapFrame(
            width: 3,
            height: 2,
            resolution: 0.05,
            frameID: "map",
            cells: [-1, 0, 10, 50, 99, 100]
        )

        let decoded = try MapRosbridgeProtocol.decodeMap(from: frame)
        let map = try #require(decoded)
        #expect(map.width == 3)
        #expect(map.height == 2)
        #expect(abs(map.resolution - 0.05) < 0.000_001)
        #expect(map.frameID == "map")
        #expect(map.origin.positionX == -1.25)
        #expect(map.origin.positionY == 2.5)
        #expect(map.origin.orientationW == 1)
        #expect(map.cells == [-1, 0, 10, 50, 99, 100])
        #expect(
            map.contentFingerprint ==
                "0fd6cc5cb9d7a1afa477a651f8ecc247ebd85d24cddea8ad98fc71fdb773c4ac"
        )
        #expect(map.rgbaPixels().count == 3 * 2 * 4)
    }

    @Test
    func mapSocketRegistersSemanticAndMapManagerTopics() throws {
        let frames = try MapRosbridgeProtocol.connectionSetupFrames().map(jsonObject)
        #expect(frames.count == 5)
        #expect(frames.map { $0["op"] as? String } == [
            "advertise", "advertise", "subscribe", "subscribe", "subscribe"
        ])
        #expect(frames[0]["topic"] as? String == "/robot_map_manager/command_json")
        #expect(frames[1]["topic"] as? String == "/semantic_map/command_json")
        #expect(frames[2]["topic"] as? String == "/map")
        #expect(frames[3]["topic"] as? String == "/robot_map_manager/status_json")
        #expect(frames[4]["topic"] as? String == "/semantic_map/status_json")
        #expect(frames[0]["type"] as? String == "std_msgs/String")
        #expect(frames[3]["id"] as? String == "amadeus-map-manager-status")
        #expect(frames[4]["id"] as? String == "amadeus-semantic-map-status")
    }

    @Test
    func mapSocketTearsDownAllSemanticAndManagerRegistrations() throws {
        let frames = try MapRosbridgeProtocol.connectionTeardownFrames().map(jsonObject)
        #expect(frames.count == 5)
        #expect(frames.map { $0["op"] as? String } == [
            "unsubscribe", "unsubscribe", "unsubscribe", "unadvertise", "unadvertise"
        ])
        #expect(frames.map { $0["topic"] as? String } == [
            "/map",
            "/robot_map_manager/status_json",
            "/semantic_map/status_json",
            "/robot_map_manager/command_json",
            "/semantic_map/command_json"
        ])
    }

    @Test
    func decodesMapManagerAndSemanticStatusBoundToSameFingerprint() throws {
        let fingerprint = String(repeating: "a", count: 64)
        let mapManagerInner: [String: Any] = [
            "schema_version": 1,
            "event": "save_result",
            "ok": true,
            "request_id": "ios-map-1",
            "message": "Karte gespeichert",
            "map": [
                "snapshot_available": true,
                "summary": mapReference(fingerprint: fingerprint)
            ],
            "storage": [
                "last_saved": [
                    "name": "wohnung",
                    "version": "20260814T070000123456Z-aaaaaaaaaaaa",
                    "width": 48,
                    "height": 36,
                    "resolution": 0.1,
                    "frame_id": "map",
                    "fingerprint": fingerprint
                ]
            ]
        ]
        let manager = try #require(MapRosbridgeProtocol.decodeMapManagerStatus(
            from: try stringTopicFrame(
                topic: "/robot_map_manager/status_json",
                inner: mapManagerInner
            )
        ))
        #expect(manager.event == "save_result")
        #expect(manager.storage.lastSaved?.name == "wohnung")
        #expect(manager.map.summary?.fingerprint == fingerprint)

        let semanticInner: [String: Any] = [
            "schema_version": 1,
            "event": "snapshot",
            "ok": true,
            "request_id": NSNull(),
            "message": "Semantische Karte bereit",
            "semantic_map": [
                "map_ref": mapReference(
                    fingerprint: fingerprint,
                    name: "wohnung",
                    version: "20260814T070000123456Z-aaaaaaaaaaaa"
                ),
                "revision": 4,
                "editable": true,
                "rooms": [roomObject()]
            ]
        ]
        let semantic = try #require(MapRosbridgeProtocol.decodeSemanticMapStatus(
            from: try stringTopicFrame(
                topic: "/semantic_map/status_json",
                inner: semanticInner
            )
        ))
        #expect(semantic.semanticMap?.revision == 4)
        #expect(semantic.semanticMap?.rooms.first?.name == "Wohnzimmer")
        #expect(semantic.semanticMap?.mapRef?.fingerprint == fingerprint)
    }

    @Test
    func semanticCommandsHaveExactInnerContract() throws {
        let fingerprint = String(repeating: "b", count: 64)
        let room = try SemanticRoom(
            id: "room-1",
            name: "Wohnzimmer",
            color: "#4FC3F7",
            polygon: [
                MapPoint(x: 0, y: 0),
                MapPoint(x: 2, y: 0),
                MapPoint(x: 2, y: 2),
                MapPoint(x: 0, y: 2)
            ],
            navigationGoal: SemanticNavigationGoal(x: 1, y: 1, yaw: 0)
        )

        let upsertFrame = try MapRosbridgeProtocol.upsertRoomFrame(
            room: room,
            mapFingerprint: fingerprint,
            baseRevision: 7,
            requestID: "ios-room-1"
        )
        #expect(try jsonObject(upsertFrame)["topic"] as? String == "/semantic_map/command_json")
        let upsert = try innerCommand(upsertFrame)
        #expect(Set(upsert.keys) == [
            "command", "request_id", "map_fingerprint", "base_revision", "room"
        ])
        #expect(upsert["command"] as? String == "upsert_room")
        #expect(upsert["base_revision"] as? Int == 7)
        #expect((upsert["room"] as? [String: Any])?["navigation_goal"] != nil)

        let deleteFrame = try MapRosbridgeProtocol.deleteRoomFrame(
            roomID: "room-1",
            mapFingerprint: fingerprint,
            baseRevision: 8,
            requestID: "ios-room-2"
        )
        #expect(try jsonObject(deleteFrame)["topic"] as? String == "/semantic_map/command_json")
        let delete = try innerCommand(deleteFrame)
        #expect(Set(delete.keys) == [
            "command", "request_id", "map_fingerprint", "base_revision", "room_id"
        ])
        #expect(delete["command"] as? String == "delete_room")
        #expect(delete["room_id"] as? String == "room-1")

        let saveFrame = try MapRosbridgeProtocol.saveMapFrame(
            name: "wohnung",
            requestID: "ios-map-1"
        )
        #expect(
            try jsonObject(saveFrame)["topic"] as? String ==
                "/robot_map_manager/command_json"
        )
        let save = try innerCommand(saveFrame)
        #expect(Set(save.keys) == ["command", "name", "request_id"])
        #expect(save["command"] as? String == "save")
        #expect(save["name"] as? String == "wohnung")
    }

    @Test(arguments: [
        "Room-1",
        "room.1",
        "raum 1",
        " room-1",
        "room-1 ",
        "_raum",
        "-raum",
        String(repeating: "r", count: 65)
    ])
    func rejectsDeleteCommandsWithBackendInvalidRoomID(roomID: String) {
        #expect(throws: MapRosbridgeProtocolError.invalidCommand) {
            try MapRosbridgeProtocol.deleteRoomFrame(
                roomID: roomID,
                mapFingerprint: String(repeating: "b", count: 64),
                baseRevision: 1,
                requestID: "ios-room-delete-invalid"
            )
        }
    }

    @Test
    func acceptsFailClosedSemanticStatusBeforeFirstMapSave() throws {
        let inner: [String: Any] = [
            "schema_version": 1,
            "event": "status",
            "ok": false,
            "request_id": NSNull(),
            "message": "Zuerst Karte speichern",
            "semantic_map": [
                "map_ref": NSNull(),
                "revision": NSNull(),
                "rooms": [],
                "editable": false,
                "edit_block_reason": "Keine gespeicherte Version"
            ]
        ]
        let status = try #require(MapRosbridgeProtocol.decodeSemanticMapStatus(
            from: try stringTopicFrame(topic: "/semantic_map/status_json", inner: inner)
        ))
        #expect(status.semanticMap?.mapRef == nil)
        #expect(status.semanticMap?.revision == nil)
        #expect(status.semanticMap?.rooms.isEmpty == true)
        #expect(status.semanticMap?.editable == false)
    }

    @Test
    func rejectsSemanticStatusWithoutRequiredSnapshotObject() throws {
        let inner: [String: Any] = [
            "schema_version": 1,
            "event": "status",
            "ok": false,
            "request_id": NSNull(),
            "message": "Semantischer Status fehlt",
            "semantic_map": NSNull()
        ]
        #expect(throws: MapRosbridgeProtocolError.invalidSemanticMapStatus) {
            try MapRosbridgeProtocol.decodeSemanticMapStatus(
                from: try stringTopicFrame(topic: "/semantic_map/status_json", inner: inner)
            )
        }
    }

    @Test
    func semanticClientPolicySeparatesFirstSaveFromRestartResume() throws {
        let map = try policyMap()
        let managerWithoutLastSaved = policyManager(for: map, hasLastSaved: false)
        let unbound = SemanticMapStatusEnvelope(
            schemaVersion: 1,
            event: "status",
            ok: false,
            requestID: nil,
            message: "Zuerst Karte speichern",
            semanticMap: SemanticMapSnapshot(
                mapRef: nil,
                revision: nil,
                rooms: [],
                editable: false
            )
        )
        #expect(SemanticMapClientPolicy.canOfferInitialMapSave(
            mapIsLive: true,
            currentMap: map,
            managerStatus: managerWithoutLastSaved,
            semanticStatus: unbound,
            saveIsPending: false,
            previousSaveResultIsUnknown: false
        ))
        #expect(!SemanticMapClientPolicy.canOfferInitialMapSave(
            mapIsLive: true,
            currentMap: map,
            managerStatus: managerWithoutLastSaved,
            semanticStatus: nil,
            saveIsPending: false,
            previousSaveResultIsUnknown: false
        ))
        #expect(!SemanticMapClientPolicy.canOfferInitialMapSave(
            mapIsLive: true,
            currentMap: map,
            managerStatus: managerWithoutLastSaved,
            semanticStatus: unbound,
            saveIsPending: false,
            previousSaveResultIsUnknown: true
        ))

        let matchingButLocked = policySemanticStatus(
            for: map,
            revision: 3,
            editable: false,
            rooms: []
        )
        #expect(!SemanticMapClientPolicy.canOfferInitialMapSave(
            mapIsLive: true,
            currentMap: map,
            managerStatus: managerWithoutLastSaved,
            semanticStatus: matchingButLocked,
            saveIsPending: false,
            previousSaveResultIsUnknown: false
        ))
        #expect(!SemanticMapClientPolicy.canEditRooms(
            mapIsLive: true,
            currentMap: map,
            managerStatus: managerWithoutLastSaved,
            semanticStatus: matchingButLocked,
            mutationIsPending: false,
            reloadIsRequired: false
        ))

        // Nach Backend-Neustart kann last_saved fehlen. Eine passende,
        // freigegebene persistierte Semantik bleibt dennoch bearbeitbar.
        let resumed = policySemanticStatus(
            for: map,
            revision: 3,
            editable: true,
            rooms: []
        )
        #expect(SemanticMapClientPolicy.canEditRooms(
            mapIsLive: true,
            currentMap: map,
            managerStatus: managerWithoutLastSaved,
            semanticStatus: resumed,
            mutationIsPending: false,
            reloadIsRequired: false
        ))
        #expect(!SemanticMapClientPolicy.canEditRooms(
            mapIsLive: true,
            currentMap: map,
            managerStatus: managerWithoutLastSaved,
            semanticStatus: resumed,
            mutationIsPending: true,
            reloadIsRequired: false
        ))
        #expect(!SemanticMapClientPolicy.canEditRooms(
            mapIsLive: true,
            currentMap: map,
            managerStatus: managerWithoutLastSaved,
            semanticStatus: resumed,
            mutationIsPending: false,
            reloadIsRequired: true
        ))
        #expect(SemanticMapClientPolicy.matchedSnapshot(
            mapIsLive: true,
            currentMap: map,
            managerStatus: managerWithoutLastSaved,
            semanticStatus: resumed
        )?.revision == 3)
    }

    @Test
    func semanticClientPolicyRejectsCurrentMapManagerError() throws {
        let map = try policyMap()
        let failedManager = policyManager(
            for: map,
            hasLastSaved: false,
            ok: false
        )
        let unbound = SemanticMapStatusEnvelope(
            schemaVersion: 1,
            event: "status",
            ok: false,
            requestID: nil,
            message: "Zuerst Karte speichern",
            semanticMap: SemanticMapSnapshot(
                mapRef: nil,
                revision: nil,
                rooms: [],
                editable: false
            )
        )
        let editable = policySemanticStatus(
            for: map,
            revision: 1,
            editable: true,
            rooms: []
        )
        #expect(!SemanticMapClientPolicy.canOfferInitialMapSave(
            mapIsLive: true,
            currentMap: map,
            managerStatus: failedManager,
            semanticStatus: unbound,
            saveIsPending: false,
            previousSaveResultIsUnknown: false
        ))
        #expect(!SemanticMapClientPolicy.canEditRooms(
            mapIsLive: true,
            currentMap: map,
            managerStatus: failedManager,
            semanticStatus: editable,
            mutationIsPending: false,
            reloadIsRequired: false
        ))
        #expect(SemanticMapClientPolicy.matchedSnapshot(
            mapIsLive: true,
            currentMap: map,
            managerStatus: failedManager,
            semanticStatus: editable
        ) == nil)
    }

    @Test
    func semanticClientPolicyRejectsAmbiguousMutationAcknowledgements() throws {
        let map = try policyMap()
        let manager = policyManager(for: map, hasLastSaved: false)
        let room = try policyRoom()
        let requestID = "ios-room-policy"

        let accepted = policySemanticStatus(
            for: map,
            revision: 4,
            editable: true,
            rooms: [room],
            requestID: requestID
        )
        #expect(SemanticMapClientPolicy.validateMutationAcknowledgement(
            accepted,
            expectedRequestID: requestID,
            mapIsLive: true,
            currentMap: map,
            managerStatus: manager,
            expectedFingerprint: map.contentFingerprint,
            baseRevision: 3,
            expectation: .upsert(roomID: room.id)
        ) == .accepted)

        let sameRevision = policySemanticStatus(
            for: map,
            revision: 3,
            editable: true,
            rooms: [room],
            requestID: requestID
        )
        #expect(SemanticMapClientPolicy.validateMutationAcknowledgement(
            sameRevision,
            expectedRequestID: requestID,
            mapIsLive: true,
            currentMap: map,
            managerStatus: manager,
            expectedFingerprint: map.contentFingerprint,
            baseRevision: 3,
            expectation: .upsert(roomID: room.id)
        ) == .revisionDidNotAdvance)

        let foreignMap = policySemanticStatus(
            for: map,
            fingerprint: String(repeating: "c", count: 64),
            revision: 4,
            editable: true,
            rooms: [room],
            requestID: requestID
        )
        #expect(SemanticMapClientPolicy.validateMutationAcknowledgement(
            foreignMap,
            expectedRequestID: requestID,
            mapIsLive: true,
            currentMap: map,
            managerStatus: manager,
            expectedFingerprint: map.contentFingerprint,
            baseRevision: 3,
            expectation: .upsert(roomID: room.id)
        ) == .invalidBinding)

        let missingRoom = policySemanticStatus(
            for: map,
            revision: 4,
            editable: true,
            rooms: [],
            requestID: requestID
        )
        #expect(SemanticMapClientPolicy.validateMutationAcknowledgement(
            missingRoom,
            expectedRequestID: requestID,
            mapIsLive: true,
            currentMap: map,
            managerStatus: manager,
            expectedFingerprint: map.contentFingerprint,
            baseRevision: 3,
            expectation: .upsert(roomID: room.id)
        ) == .expectedRoomMissing)
        #expect(SemanticMapClientPolicy.validateMutationAcknowledgement(
            accepted,
            expectedRequestID: requestID,
            mapIsLive: true,
            currentMap: map,
            managerStatus: manager,
            expectedFingerprint: map.contentFingerprint,
            baseRevision: 3,
            expectation: .delete(roomID: room.id)
        ) == .deletedRoomStillPresent)
    }

    @Test
    func boundedTimeoutResolutionNeverRequestsAnAutomaticRetry() {
        #expect(SemanticMapClientPolicy.responseTimeoutNanoseconds == 12_000_000_000)
        #expect(SemanticMapClientPolicy.timeoutResolution(
            pendingRequestID: "ios-room-1",
            firedRequestID: "ios-room-1"
        ) == .statusUnknownNoRetry)
        #expect(SemanticMapClientPolicy.timeoutResolution(
            pendingRequestID: "ios-room-new",
            firedRequestID: "ios-room-old"
        ) == .ignore)
    }

    @Test
    func semanticSnapshotEnforcesBackendLimitOf256Rooms() throws {
        let map = try policyMap()
        let reference = try #require(policySemanticStatus(
            for: map,
            revision: 0,
            editable: true,
            rooms: []
        ).semanticMap?.mapRef)
        let rooms = try (0..<257).map { index in
            try SemanticRoom(
                id: "room-\(index)",
                name: "Testraum \(index)",
                color: nil,
                polygon: [
                    MapPoint(x: 1, y: 1),
                    MapPoint(x: 5, y: 1),
                    MapPoint(x: 5, y: 5),
                    MapPoint(x: 1, y: 5)
                ],
                navigationGoal: SemanticNavigationGoal(x: 3, y: 3, yaw: 0)
            )
        }
        #expect(SemanticMapSnapshot(
            mapRef: reference,
            revision: 1,
            rooms: Array(rooms.prefix(256)),
            editable: true
        ).isValid)
        #expect(!SemanticMapSnapshot(
            mapRef: reference,
            revision: 1,
            rooms: rooms,
            editable: true
        ).isValid)
    }

    @Test
    func semanticPolygonComplexityMatchesBackendLimits() throws {
        let tooManyPoints = (0..<65).map { index in
            let angle = 2 * Double.pi * Double(index) / 65
            return MapPoint(x: 3 + cos(angle), y: 3 + sin(angle))
        }
        do {
            _ = try SemanticRoom(
                id: "room-too-complex",
                name: "Zu komplex",
                color: nil,
                polygon: tooManyPoints,
                navigationGoal: SemanticNavigationGoal(x: 3, y: 3, yaw: 0)
            )
            Issue.record("65 Polygonpunkte hätten abgelehnt werden müssen")
        } catch let error as SemanticMapValidationError {
            #expect(error == .invalidPolygon)
        }

        let map = try policyMap()
        let reference = try #require(policySemanticStatus(
            for: map,
            revision: 0,
            editable: true,
            rooms: []
        ).semanticMap?.mapRef)
        let polygon = (0..<17).map { index in
            let angle = 2 * Double.pi * Double(index) / 17
            return MapPoint(x: 3 + cos(angle), y: 3 + sin(angle))
        }
        let rooms = try (0..<242).map { index in
            try SemanticRoom(
                id: "room-complex-\(index)",
                name: "Komplex \(index)",
                color: nil,
                polygon: polygon,
                navigationGoal: SemanticNavigationGoal(x: 3, y: 3, yaw: 0)
            )
        }
        #expect(!SemanticMapSnapshot(
            mapRef: reference,
            revision: 1,
            rooms: rooms,
            editable: true
        ).isValid)
    }

    @Test
    func rejectsSemanticRoomWhoseGoalIsOutsidePolygon() throws {
        do {
            _ = try SemanticRoom(
                id: "room-1",
                name: "Flur",
                color: nil,
                polygon: [
                    MapPoint(x: 0, y: 0),
                    MapPoint(x: 1, y: 0),
                    MapPoint(x: 1, y: 1)
                ],
                navigationGoal: SemanticNavigationGoal(x: 5, y: 5, yaw: 0)
            )
            Issue.record("Ein Ziel außerhalb des Raums hätte abgelehnt werden müssen")
        } catch let error as SemanticMapValidationError {
            #expect(error == .navigationGoalOutsideRoom)
        }
    }

    @Test(arguments: ["Wohn\nzimmer", "Kueche\tNord", "Flur\u{7F}West"])
    func rejectsRoomNamesWithBackendForbiddenControlCharacters(name: String) {
        #expect(throws: SemanticMapValidationError.invalidRoomName) {
            try SemanticRoom(
                id: "room-1",
                name: name,
                color: nil,
                polygon: [
                    MapPoint(x: 0, y: 0),
                    MapPoint(x: 2, y: 0),
                    MapPoint(x: 1, y: 2)
                ],
                navigationGoal: SemanticNavigationGoal(x: 1, y: 1, yaw: 0)
            )
        }
        let oversizedCodePointName = "W" + String(repeating: "\u{0301}", count: 81)
        #expect(throws: SemanticMapValidationError.invalidRoomName) {
            try SemanticRoom(
                id: "room-1",
                name: oversizedCodePointName,
                color: nil,
                polygon: [
                    MapPoint(x: 0, y: 0),
                    MapPoint(x: 2, y: 0),
                    MapPoint(x: 1, y: 2)
                ],
                navigationGoal: SemanticNavigationGoal(x: 1, y: 1, yaw: 0)
            )
        }
    }

    @Test
    func rejectsSelfIntersectingRoomPolygon() {
        let bowTie = [
            MapPoint(x: 0, y: 0),
            MapPoint(x: 2, y: 2),
            MapPoint(x: 0, y: 2),
            MapPoint(x: 2, y: 0)
        ]
        #expect(!SemanticGeometry.isSimplePolygon(bowTie))
        #expect(!SemanticGeometry.isSimplePolygon([
            MapPoint(x: 0, y: 0),
            MapPoint(x: 0.001, y: 0),
            MapPoint(x: 0, y: 0.001)
        ]))
    }

    @Test
    func viewportTransformHandlesYawMirrorAspectFitZoomAndPan() throws {
        let halfSqrt = sqrt(0.5)
        let map = try RobotMapSnapshot(
            width: 100,
            height: 50,
            resolution: 0.1,
            origin: RobotMapOrigin(
                positionX: 1,
                positionY: 2,
                positionZ: 0,
                orientationX: 0,
                orientationY: 0,
                orientationZ: halfSqrt,
                orientationW: halfSqrt
            ),
            frameID: "map",
            cells: [Int](repeating: 0, count: 5_000)
        )
        let transform = RobotMapViewportTransform(
            map: map,
            viewportWidth: 300,
            viewportHeight: 300,
            scale: 2,
            offsetX: 10,
            offsetY: -20
        )

        // Lokaler Kartenpunkt (2, 1) wird durch origin-yaw=90° zu (0, 4).
        let worldPoint = MapPoint(x: 0, y: 4)
        let screen = transform.screenPoint(for: worldPoint)
        #expect(abs(screen.x - (-20)) < 0.000_001)
        #expect(abs(screen.y - 220) < 0.000_001)
        let roundTrip = try #require(transform.mapPoint(forScreenPoint: screen))
        #expect(abs(roundTrip.x - worldPoint.x) < 0.000_001)
        #expect(abs(roundTrip.y - worldPoint.y) < 0.000_001)

        let bottomLocalWorld = MapPoint(x: 1, y: 2)
        let bottom = transform.screenPoint(for: bottomLocalWorld)
        let topLocalWorld = MapPoint(x: -4, y: 2)
        let top = transform.screenPoint(for: topLocalWorld)
        #expect(bottom.y > top.y) // OccupancyGrid-Y wird im Bild gespiegelt.
    }

    @Test
    func rgbaRenderingMirrorsRowsVertically() throws {
        let frame = try mapFrame(
            width: 2,
            height: 2,
            cells: [
                -1, 0,   // untere OccupancyGrid-Zeile
                50, 100  // obere OccupancyGrid-Zeile
            ]
        )
        let decoded = try MapRosbridgeProtocol.decodeMap(from: frame)
        let map = try #require(decoded)

        #expect(map.rgbaPixels() == [
            128, 128, 128, 255, // 50 %, obere Bildzeile
            0, 0, 0, 255,       // belegt
            127, 127, 127, 255, // unbekannt, untere Bildzeile
            255, 255, 255, 255  // frei
        ])
    }

    @Test
    func rejectsWrongDataLength() throws {
        let frame = try mapFrame(width: 3, height: 2, cells: [0, 0, 0])

        do {
            _ = try MapRosbridgeProtocol.decodeMap(from: frame)
            Issue.record("Eine Karte mit falscher Datenlänge hätte abgelehnt werden müssen")
        } catch let error as RobotMapValidationError {
            #expect(error == .invalidDataLength(expected: 6, actual: 3))
            #expect(error.localizedDescription.contains("erwartet 6 Zellwerte"))
        }
    }

    @Test
    func rejectsFrameIDsAboveBackendCodePointLimitBeforeFingerprintEncoding() {
        // Swift zaehlt die gesamte Kombination sonst als ein Character. Der
        // Backendvertrag und der UInt16-Fingerprintcodec muessen dennoch vor
        // der Konvertierung begrenzen.
        let oversizedFrameID = "m" + String(repeating: "\u{0301}", count: 65_536)
        #expect(throws: RobotMapValidationError.invalidFrameID) {
            try RobotMapSnapshot(
                width: 1,
                height: 1,
                resolution: 0.05,
                origin: RobotMapOrigin(
                    positionX: 0,
                    positionY: 0,
                    positionZ: 0,
                    orientationX: 0,
                    orientationY: 0,
                    orientationZ: 0,
                    orientationW: 1
                ),
                frameID: oversizedFrameID,
                cells: [0]
            )
        }
    }

    @Test
    func rejectsInvalidResolution() throws {
        let frame = try mapFrame(
            width: 1,
            height: 1,
            resolution: 0,
            cells: [0]
        )

        do {
            _ = try MapRosbridgeProtocol.decodeMap(from: frame)
            Issue.record("Eine Karte ohne positive Auflösung hätte abgelehnt werden müssen")
        } catch let error as RobotMapValidationError {
            #expect(error == .invalidResolution(0))
            #expect(error.localizedDescription.contains("Kartenauflösung"))
        }
    }

    @Test
    func rejectsMapsAboveCellLimitBeforeCheckingPayloadLength() throws {
        let frame = try mapFrame(
            width: 2_001,
            height: 2_000,
            cells: []
        )

        do {
            _ = try MapRosbridgeProtocol.decodeMap(from: frame)
            Issue.record("Eine Karte oberhalb des Größenlimits hätte abgelehnt werden müssen")
        } catch let error as RobotMapValidationError {
            #expect(
                error == .cellLimitExceeded(
                    actual: 4_002_000,
                    maximum: RobotMapSnapshot.maximumCellCount
                )
            )
        }
    }

    @Test
    func rejectsCellCountOverflow() throws {
        do {
            _ = try RobotMapSnapshot(
                width: Int.max,
                height: 2,
                resolution: 0.05,
                origin: validOrigin,
                frameID: "map",
                cells: []
            )
            Issue.record("Überlaufende Kartenabmessungen hätten abgelehnt werden müssen")
        } catch let error as RobotMapValidationError {
            #expect(error == .cellCountOverflow(width: Int.max, height: 2))
        }
    }

    @Test(arguments: [-2, 101])
    func rejectsOccupancyValuesOutsideRosRange(value: Int) throws {
        let frame = try mapFrame(width: 1, height: 1, cells: [value])

        do {
            _ = try MapRosbridgeProtocol.decodeMap(from: frame)
            Issue.record("Der ungültige Kartenwert \(value) hätte abgelehnt werden müssen")
        } catch let error as RobotMapValidationError {
            #expect(error == .invalidOccupancyValue(index: 0, value: value))
            #expect(error.localizedDescription.contains("-1 und 100"))
        }
    }

    @Test
    func rejectsOriginWithZeroQuaternion() throws {
        let frame = try mapFrame(
            width: 1,
            height: 1,
            cells: [0],
            orientationW: 0
        )

        do {
            _ = try MapRosbridgeProtocol.decodeMap(from: frame)
            Issue.record("Ein Kartenursprung ohne gültige Orientierung hätte abgelehnt werden müssen")
        } catch let error as RobotMapValidationError {
            #expect(error == .invalidOrigin)
        }

        let nonNormalized = try mapFrame(
            width: 1,
            height: 1,
            cells: [0],
            orientationW: 2
        )
        #expect(throws: RobotMapValidationError.invalidOrigin) {
            try MapRosbridgeProtocol.decodeMap(from: nonNormalized)
        }
    }

    @Test
    func ignoresUnrelatedRosbridgePublish() throws {
        let frame = """
        {"op":"publish","topic":"/other","msg":{"anything":true}}
        """
        #expect(try MapRosbridgeProtocol.decodeMap(from: frame) == nil)
    }

    @Test
    func offlineMapSnapshotStoreRoundTripsValidatedMap() throws {
        let directory = FileManager.default.temporaryDirectory
            .appendingPathComponent(UUID().uuidString, isDirectory: true)
        let fileURL = directory.appendingPathComponent("last-robot-map.plist")
        defer { try? FileManager.default.removeItem(at: directory) }

        let stored = CachedRobotMapSnapshot(
            map: try policyMap(),
            savedAt: Date(timeIntervalSinceReferenceDate: 123_456)
        )
        let store = RobotMapSnapshotStore(fileURL: fileURL)

        try store.save(stored)
        let loaded = try #require(store.load())

        #expect(loaded == stored)
    }

    private var validOrigin: RobotMapOrigin {
        RobotMapOrigin(
            positionX: -1.25,
            positionY: 2.5,
            positionZ: 0,
            orientationX: 0,
            orientationY: 0,
            orientationZ: 0,
            orientationW: 1
        )
    }

    private func mapFrame(
        width: Int,
        height: Int,
        resolution: Double = 0.05,
        frameID: String = "map",
        cells: [Int],
        orientationW: Double = 1
    ) throws -> String {
        let object: [String: Any] = [
            "op": "publish",
            "topic": "/map",
            "msg": [
                "header": [
                    "stamp": ["sec": 123, "nanosec": 456],
                    "frame_id": frameID
                ],
                "info": [
                    "map_load_time": ["sec": 100, "nanosec": 0],
                    "resolution": resolution,
                    "width": width,
                    "height": height,
                    "origin": [
                        "position": ["x": -1.25, "y": 2.5, "z": 0],
                        "orientation": ["x": 0, "y": 0, "z": 0, "w": orientationW]
                    ]
                ],
                "data": cells
            ]
        ]
        let data = try JSONSerialization.data(withJSONObject: object, options: [.sortedKeys])
        return try #require(String(data: data, encoding: .utf8))
    }

    private func jsonObject(_ text: String) throws -> [String: Any] {
        let data = try #require(text.data(using: .utf8))
        return try #require(
            JSONSerialization.jsonObject(with: data) as? [String: Any]
        )
    }

    private func innerCommand(_ frame: String) throws -> [String: Any] {
        let outer = try jsonObject(frame)
        let message = try #require(outer["msg"] as? [String: Any])
        let text = try #require(message["data"] as? String)
        return try jsonObject(text)
    }

    private func stringTopicFrame(
        topic: String,
        inner: [String: Any]
    ) throws -> String {
        let innerData = try JSONSerialization.data(withJSONObject: inner, options: [.sortedKeys])
        let innerText = try #require(String(data: innerData, encoding: .utf8))
        let outer: [String: Any] = [
            "op": "publish",
            "topic": topic,
            "msg": ["data": innerText]
        ]
        let outerData = try JSONSerialization.data(withJSONObject: outer, options: [.sortedKeys])
        return try #require(String(data: outerData, encoding: .utf8))
    }

    private func mapReference(
        fingerprint: String,
        name: String? = nil,
        version: String? = nil
    ) -> [String: Any] {
        var value: [String: Any] = [
            "width": 48,
            "height": 36,
            "resolution": 0.1,
            "frame_id": "map",
            "fingerprint": fingerprint,
            "origin": [
                "position": ["x": -2.4, "y": -1.8, "z": 0.0],
                "orientation": ["x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0]
            ]
        ]
        if let name { value["name"] = name }
        if let version { value["version"] = version }
        return value
    }

    private func roomObject() -> [String: Any] {
        [
            "id": "room-wohnzimmer",
            "name": "Wohnzimmer",
            "color": "#4FC3F7",
            "polygon": [
                ["x": -2.0, "y": -1.0],
                ["x": -0.2, "y": -1.0],
                ["x": -0.2, "y": 0.8],
                ["x": -2.0, "y": 0.8]
            ],
            "navigation_goal": ["x": -1.0, "y": 0.0, "yaw": 0.0]
        ]
    }

    private func policyMap() throws -> RobotMapSnapshot {
        try RobotMapSnapshot(
            width: 10,
            height: 10,
            resolution: 1,
            origin: RobotMapOrigin(
                positionX: 0,
                positionY: 0,
                positionZ: 0,
                orientationX: 0,
                orientationY: 0,
                orientationZ: 0,
                orientationW: 1
            ),
            frameID: "map",
            cells: [Int](repeating: 0, count: 100)
        )
    }

    private func policyManager(
        for map: RobotMapSnapshot,
        hasLastSaved: Bool,
        ok: Bool = true
    ) -> RobotMapManagerStatusEnvelope {
        let saved = hasLastSaved ? RobotMapManagerStatusEnvelope.SavedMap(
            name: "wohnung",
            version: "20260814T070000123456Z-\(map.contentFingerprint.prefix(12))",
            width: map.width,
            height: map.height,
            resolution: map.resolution,
            frameID: map.frameID,
            fingerprint: map.contentFingerprint
        ) : nil
        return RobotMapManagerStatusEnvelope(
            schemaVersion: 1,
            event: "status",
            ok: ok,
            requestID: nil,
            message: "Kartenmanager bereit",
            map: .init(
                snapshotAvailable: true,
                summary: .init(
                    width: map.width,
                    height: map.height,
                    resolution: map.resolution,
                    frameID: map.frameID,
                    origin: map.origin,
                    fingerprint: map.contentFingerprint
                )
            ),
            storage: .init(lastSaved: saved)
        )
    }

    private func policySemanticStatus(
        for map: RobotMapSnapshot,
        fingerprint: String? = nil,
        revision: Int,
        editable: Bool,
        rooms: [SemanticRoom],
        requestID: String? = nil
    ) -> SemanticMapStatusEnvelope {
        let fingerprint = fingerprint ?? map.contentFingerprint
        let reference = SemanticMapReference(
            name: "wohnung",
            version: "20260814T070000123456Z-\(fingerprint.prefix(12))",
            fingerprint: fingerprint,
            frameID: map.frameID,
            width: map.width,
            height: map.height,
            resolution: map.resolution,
            origin: map.origin
        )
        return SemanticMapStatusEnvelope(
            schemaVersion: 1,
            event: "room_created",
            ok: true,
            requestID: requestID,
            message: "Semantische Karte bereit",
            semanticMap: SemanticMapSnapshot(
                mapRef: reference,
                revision: revision,
                rooms: rooms,
                editable: editable
            )
        )
    }

    private func policyRoom() throws -> SemanticRoom {
        try SemanticRoom(
            id: "room-policy",
            name: "Testraum",
            color: "#4FB3A5",
            polygon: [
                MapPoint(x: 1, y: 1),
                MapPoint(x: 5, y: 1),
                MapPoint(x: 5, y: 5),
                MapPoint(x: 1, y: 5)
            ],
            navigationGoal: SemanticNavigationGoal(x: 3, y: 3, yaw: 0)
        )
    }
}
