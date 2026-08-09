"""Osculating orbits and physical apsis/node searches."""

from dataclasses import dataclass
from enum import Enum

from .position import (
    ApparentFrame,
    Body,
    EphemerisResult,
    PositionFlag,
    Vector3,
    _diagnostic,
)


_REVERSE_MASK = 1 << 32
_SUPPORTED_BODIES = frozenset(
    {
        Body.mercury_barycenter,
        Body.venus_barycenter,
        Body.emb,
        Body.mars_barycenter,
        Body.jupiter_barycenter,
        Body.saturn_barycenter,
        Body.uranus_barycenter,
        Body.neptune_barycenter,
        Body.pluto_barycenter,
        Body.mercury,
        Body.venus,
        Body.moon,
        Body.earth,
        Body.mars,
        Body.jupiter,
        Body.saturn,
        Body.uranus,
        Body.neptune,
        Body.pluto,
    }
)


class ApsisKind(Enum):
    pericenter = 0
    apocenter = 1

    @property
    def id(self):
        return self.value


class PlaneNodeKind(Enum):
    ascending = 0
    descending = 1

    @property
    def id(self):
        return self.value


class OrbitalSearchDirection(Enum):
    forward = 0
    reverse = 1

    @property
    def id(self):
        return self.value


class OrbitReferencePointModel(Enum):
    osculating = 0
    unknown = -1

    @property
    def id(self):
        return self.value

    @classmethod
    def from_id(cls, value):
        try:
            return cls(value)
        except ValueError:
            return cls.unknown


@dataclass(frozen=True)
class OrbitReferencePoint:
    positionAu: Vector3
    longitudeRadians: float
    latitudeRadians: float
    distanceAu: float


@dataclass(frozen=True)
class OsculatingOrbit:
    body: Body
    center: Body
    referenceFrame: ApparentFrame
    rawReferenceFrameId: int
    gravitationalParameterAu3PerDay2: float
    semiMajorAxisAu: float
    eccentricity: float
    inclinationRadians: float
    longitudeOfAscendingNodeRadians: float
    argumentOfPeriapsisRadians: float
    trueAnomalyRadians: float
    meanAnomalyRadians: float
    periapsisDistanceAu: float
    apoapsisDistanceAu: float
    osculatingPeriodDays: float
    currentDistanceAu: float
    radialVelocityAuPerDay: float
    allowBarycenterApproximation: bool


@dataclass(frozen=True)
class OrbitReferencePoints:
    body: Body
    center: Body
    referenceFrame: ApparentFrame
    rawReferenceFrameId: int
    model: OrbitReferencePointModel
    rawModelId: int
    ascendingNode: OrbitReferencePoint
    descendingNode: OrbitReferencePoint
    periapsis: OrbitReferencePoint
    apoapsis: OrbitReferencePoint
    secondFocus: OrbitReferencePoint
    allowBarycenterApproximation: bool


@dataclass(frozen=True)
class ApsisEvent:
    body: Body
    center: Body
    kind: ApsisKind
    coordinate: object
    distanceAu: float
    radialVelocityAuPerDay: float
    iterationCount: int
    evaluationCount: int
    direction: OrbitalSearchDirection
    allowBarycenterApproximation: bool


@dataclass(frozen=True)
class PlaneNodeEvent:
    body: Body
    center: Body
    referenceFrame: ApparentFrame
    rawReferenceFrameId: int
    kind: PlaneNodeKind
    coordinate: object
    referencePlaneAngleRadians: float
    distanceAu: float
    iterationCount: int
    evaluationCount: int
    direction: OrbitalSearchDirection
    allowBarycenterApproximation: bool


class OrbitalApi:
    """Orbital calculations sharing an owning ephemeris context."""

    def __init__(self, context):
        self._context = context

    def osculating_at_tt(
        self,
        body,
        tt,
        *,
        reference_frame=ApparentFrame.j2000_ecliptic,
        allow_barycenter_approximation=False,
    ):
        return self._orbit(
            "osculating_orbit_at_tt",
            body,
            tt,
            reference_frame,
            allow_barycenter_approximation,
        )

    def osculating_at_ut1(
        self,
        body,
        ut1,
        *,
        reference_frame=ApparentFrame.j2000_ecliptic,
        allow_barycenter_approximation=False,
    ):
        return self._orbit(
            "osculating_orbit_at_ut1",
            body,
            ut1,
            reference_frame,
            allow_barycenter_approximation,
        )

    def reference_points_at_tt(
        self,
        body,
        tt,
        *,
        reference_frame=ApparentFrame.j2000_ecliptic,
        allow_barycenter_approximation=False,
    ):
        return self._reference_points(
            "orbit_reference_points_at_tt",
            body,
            tt,
            reference_frame,
            allow_barycenter_approximation,
        )

    def reference_points_at_ut1(
        self,
        body,
        ut1,
        *,
        reference_frame=ApparentFrame.j2000_ecliptic,
        allow_barycenter_approximation=False,
    ):
        return self._reference_points(
            "orbit_reference_points_at_ut1",
            body,
            ut1,
            reference_frame,
            allow_barycenter_approximation,
        )

    def search_apsis_from_tt(
        self,
        body,
        kind,
        start,
        *,
        direction=OrbitalSearchDirection.forward,
        allow_barycenter_approximation=False,
    ):
        return self._apsis(
            "search_body_apsis_from_tt",
            body,
            kind,
            start,
            direction,
            allow_barycenter_approximation,
        )

    def search_apsis_from_ut1(
        self,
        body,
        kind,
        start,
        *,
        direction=OrbitalSearchDirection.forward,
        allow_barycenter_approximation=False,
    ):
        return self._apsis(
            "search_body_apsis_from_ut1",
            body,
            kind,
            start,
            direction,
            allow_barycenter_approximation,
        )

    def search_plane_node_from_tt(
        self,
        body,
        kind,
        start,
        *,
        reference_frame=ApparentFrame.j2000_ecliptic,
        direction=OrbitalSearchDirection.forward,
        allow_barycenter_approximation=False,
    ):
        return self._plane_node(
            "search_body_plane_node_from_tt",
            body,
            kind,
            start,
            reference_frame,
            direction,
            allow_barycenter_approximation,
        )

    def search_plane_node_from_ut1(
        self,
        body,
        kind,
        start,
        *,
        reference_frame=ApparentFrame.j2000_ecliptic,
        direction=OrbitalSearchDirection.forward,
        allow_barycenter_approximation=False,
    ):
        return self._plane_node(
            "search_body_plane_node_from_ut1",
            body,
            kind,
            start,
            reference_frame,
            direction,
            allow_barycenter_approximation,
        )

    def _orbit(self, native_name, body, coordinate, frame, allow_approximation):
        self._context._ensure_open()
        _require_body(body)
        _require_frame(frame)
        value = getattr(self._context._native_context, native_name)(
            body.id, coordinate, frame.value, _flags(allow_approximation)
        )
        return EphemerisResult(_orbit(value, allow_approximation), _diagnostic(value["diagnostic"]))

    def _reference_points(
        self, native_name, body, coordinate, frame, allow_approximation
    ):
        self._context._ensure_open()
        _require_body(body)
        _require_frame(frame)
        value = getattr(self._context._native_context, native_name)(
            body.id, coordinate, frame.value, _flags(allow_approximation)
        )
        return EphemerisResult(
            _reference_points(value, allow_approximation),
            _diagnostic(value["diagnostic"]),
        )

    def _apsis(self, native_name, body, kind, start, direction, allow_approximation):
        self._context._ensure_open()
        _require_body(body)
        if not isinstance(kind, ApsisKind):
            raise ValueError("kind must be an ApsisKind")
        _require_direction(direction)
        value = getattr(self._context._native_context, native_name)(
            body.id, kind.id, start, _flags(allow_approximation, direction)
        )
        event = ApsisEvent(
            body=Body(value["body_id"]),
            center=Body(value["center_id"]),
            kind=ApsisKind(value["kind"]),
            coordinate=value["coordinate"],
            distanceAu=value["distance_au"],
            radialVelocityAuPerDay=value["radial_velocity_au_per_day"],
            iterationCount=value["iteration_count"],
            evaluationCount=value["evaluation_count"],
            direction=direction,
            allowBarycenterApproximation=allow_approximation,
        )
        return EphemerisResult(event, _diagnostic(value["diagnostic"]))

    def _plane_node(
        self, native_name, body, kind, start, frame, direction, allow_approximation
    ):
        self._context._ensure_open()
        _require_body(body)
        if not isinstance(kind, PlaneNodeKind):
            raise ValueError("kind must be a PlaneNodeKind")
        _require_frame(frame)
        _require_direction(direction)
        value = getattr(self._context._native_context, native_name)(
            body.id,
            kind.id,
            start,
            frame.value,
            _flags(allow_approximation, direction),
        )
        event = PlaneNodeEvent(
            body=Body(value["body_id"]),
            center=Body(value["center_id"]),
            referenceFrame=ApparentFrame.from_id(value["reference_frame_id"]),
            rawReferenceFrameId=value["reference_frame_id"],
            kind=PlaneNodeKind(value["kind"]),
            coordinate=value["coordinate"],
            referencePlaneAngleRadians=value["reference_plane_angle_radians"],
            distanceAu=value["distance_au"],
            iterationCount=value["iteration_count"],
            evaluationCount=value["evaluation_count"],
            direction=direction,
            allowBarycenterApproximation=allow_approximation,
        )
        return EphemerisResult(event, _diagnostic(value["diagnostic"]))


def _orbit(value, allow_approximation):
    return OsculatingOrbit(
        body=Body(value["body_id"]),
        center=Body(value["center_id"]),
        referenceFrame=ApparentFrame.from_id(value["reference_frame_id"]),
        rawReferenceFrameId=value["reference_frame_id"],
        gravitationalParameterAu3PerDay2=value["gravitational_parameter_au3_per_day2"],
        semiMajorAxisAu=value["semi_major_axis_au"],
        eccentricity=value["eccentricity"],
        inclinationRadians=value["inclination_radians"],
        longitudeOfAscendingNodeRadians=value["longitude_of_ascending_node_radians"],
        argumentOfPeriapsisRadians=value["argument_of_periapsis_radians"],
        trueAnomalyRadians=value["true_anomaly_radians"],
        meanAnomalyRadians=value["mean_anomaly_radians"],
        periapsisDistanceAu=value["periapsis_distance_au"],
        apoapsisDistanceAu=value["apoapsis_distance_au"],
        osculatingPeriodDays=value["osculating_period_days"],
        currentDistanceAu=value["current_distance_au"],
        radialVelocityAuPerDay=value["radial_velocity_au_per_day"],
        allowBarycenterApproximation=allow_approximation,
    )


def _point(value):
    return OrbitReferencePoint(
        positionAu=Vector3(*value["position_au"]),
        longitudeRadians=value["longitude_radians"],
        latitudeRadians=value["latitude_radians"],
        distanceAu=value["distance_au"],
    )


def _reference_points(value, allow_approximation):
    return OrbitReferencePoints(
        body=Body(value["body_id"]),
        center=Body(value["center_id"]),
        referenceFrame=ApparentFrame.from_id(value["reference_frame_id"]),
        rawReferenceFrameId=value["reference_frame_id"],
        model=OrbitReferencePointModel.from_id(value["model_id"]),
        rawModelId=value["model_id"],
        ascendingNode=_point(value["ascending_node"]),
        descendingNode=_point(value["descending_node"]),
        periapsis=_point(value["periapsis"]),
        apoapsis=_point(value["apoapsis"]),
        secondFocus=_point(value["second_focus"]),
        allowBarycenterApproximation=allow_approximation,
    )


def _flags(allow_approximation, direction=OrbitalSearchDirection.forward):
    value = PositionFlag.allow_barycenter_approx.mask if allow_approximation else 0
    if direction is OrbitalSearchDirection.reverse:
        value |= _REVERSE_MASK
    return value


def _require_body(body):
    if body not in _SUPPORTED_BODIES:
        raise ValueError(
            "body must be the Moon, Earth/EMB, or a major planet or planet barycenter"
        )


def _require_frame(frame):
    if not isinstance(frame, ApparentFrame) or frame is ApparentFrame.unknown:
        raise ValueError("reference_frame must be a supported concrete reference frame")


def _require_direction(direction):
    if not isinstance(direction, OrbitalSearchDirection):
        raise ValueError("direction must be an OrbitalSearchDirection")
