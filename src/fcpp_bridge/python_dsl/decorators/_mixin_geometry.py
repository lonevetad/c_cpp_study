from typing import Any, Callable, Optional


class _MixinGeometry:
    """Spatial geometry methods for location-aware aggregation."""

    def abf_distance(self, source: bool,
                     metric: Optional[Callable] = None) -> Any:
        """Adaptive Bellman-Ford distance from sources."""
        from ..primitives import AbfDistance
        return AbfDistance(source, metric)

    def bis_distance(self, source: bool, period: float, speed: float,
                     metric: Optional[Callable] = None) -> Any:
        """Bounded Information Speeds distance from sources."""
        from ..primitives import BisDistance
        return BisDistance(source, period, speed, metric)

    def follow_target(self, target: Any, max_v: float, period: float) -> Any:
        """Move toward a spatial target point at fixed speed."""
        from ..primitives import FollowTarget
        return FollowTarget(target, max_v, period)

    def rectangle_walk(self, low: Any, hi: Any, max_v: float,
                       period: float) -> Any:
        """Random walk bounded to a rectangle."""
        from ..primitives import RectangleWalk
        return RectangleWalk(low, hi, max_v, period)

    def distance_to_nodes(self, target_ids: Any) -> Any:
        """Compute distances to target node IDs."""
        return 0.0

    def nearest_k_neighbors(self, k: int) -> Any:
        """Select k nearest neighbors."""
        return []

    def follow_gradient(self, target_location: Any) -> Any:
        """Follow gradient toward target location."""
        return target_location

    def follow_path(self, path: Any, max_v: float, period: float) -> Any:
        """Follow a sequence of waypoints."""
        from ..primitives import FollowPath
        return FollowPath(path, max_v, period)

    def follow_track(self, trace: Any) -> Any:
        """Follow a GPS trace."""
        from ..primitives import FollowTrack
        return FollowTrack(trace)

    def random_rectangle_target(self, low: Any, hi: Any,
                                 reach: float = None) -> Any:
        """Pick a random target point inside a rectangle."""
        from ..primitives import RandomRectangleTarget
        return RandomRectangleTarget(low, hi, reach)

    def neighbour_elastic_force(self, length: Any, strength: Any) -> Any:
        """Elastic spring force from neighbours."""
        from ..primitives import NeighbourElasticForce
        return NeighbourElasticForce(length, strength)

    def neighbour_gravitational_force(self, mass: float) -> Any:
        """Gravitational force from neighbours."""
        from ..primitives import NeighbourGravitationalForce
        return NeighbourGravitationalForce(mass)

    def neighbour_charged_force(self, mass: float, charge: float) -> Any:
        """Electrostatic force from neighbours."""
        from ..primitives import NeighbourChargedForce
        return NeighbourChargedForce(mass, charge)

    def point_elastic_force(self, point: Any, length: float,
                             strength: float) -> Any:
        """Elastic force from a point attractor."""
        from ..primitives import PointElasticForce
        return PointElasticForce(point, length, strength)

    def point_gravitational_force(self, point: Any, mass: float) -> Any:
        """Gravitational force from a point."""
        from ..primitives import PointGravitationalForce
        return PointGravitationalForce(point, mass)
