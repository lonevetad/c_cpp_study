"""Core FCPP DSL primitives — Field, Neighborhood, OldValue, etc."""

from typing import TypeVar, Generic, Any, List, Callable

T = TypeVar("T")


class Field(Generic[T]):
    """Represents an FCPP field<T> — spatially-distributed value across all nodes."""

    def __init__(self, value: T):
        self.value = value

    def __repr__(self) -> str:
        return f"Field({self.value!r})"

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Field):
            return False
        return self.value == other.value


class Neighborhood(Generic[T]):
    """Represents nbr<T> — neighbor values in current round."""

    def __init__(self, values: List[T]):
        self.values = values if values else []

    def __repr__(self) -> str:
        return f"Neighborhood({self.values!r})"

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Neighborhood):
            return False
        return self.values == other.values

    def __bool__(self) -> bool:
        """Empty neighborhood evaluates to False."""
        return len(self.values) > 0

    def __len__(self) -> int:
        return len(self.values)


class OldValue(Generic[T]):
    """Represents old<T> — value from previous round."""

    def __init__(self, value: T):
        self.value = value

    def __repr__(self) -> str:
        return f"OldValue({self.value!r})"

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, OldValue):
            return False
        return self.value == other.value


class StateValue:
    """Marker for current node's own state value."""

    def __repr__(self) -> str:
        return "StateValue()"

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, StateValue)


class FoldHood(Generic[T]):
    """Represents fold_hood(init, expr) — tree reduction over neighborhood."""

    def __init__(self, init: T, expr: Callable[[T, T], T]):
        self.init = init
        self.expr = expr

    def __repr__(self) -> str:
        return f"FoldHood(init={self.init!r}, expr=<lambda>)"


class MinHood(Generic[T]):
    """Represents min_hood(expr) — minimum across neighborhood."""

    def __init__(self, expr: Any):
        self.expr = expr

    def __repr__(self) -> str:
        return f"MinHood({self.expr!r})"


class MaxHood(Generic[T]):
    """Represents max_hood(expr) — maximum across neighborhood."""

    def __init__(self, expr: Any):
        self.expr = expr

    def __repr__(self) -> str:
        return f"MaxHood({self.expr!r})"


class CountHood:
    """Represents count_hood() — count of neighbors."""

    def __repr__(self) -> str:
        return "CountHood()"

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, CountHood)


class Spawn(Generic[T]):
    """Represents spawn(f) — parallel sub-computation."""

    def __init__(self, func: Callable[..., T]):
        self.func = func

    def __repr__(self) -> str:
        return f"Spawn({self.func.__name__})"


class Broadcast(Generic[T]):
    """Represents broadcast(source, expr) — multi-source dissemination."""

    def __init__(self, source_expr: Any, value_expr: Any):
        self.source = source_expr
        self.value = value_expr

    def __repr__(self) -> str:
        return f"Broadcast(source={self.source!r}, value={self.value!r})"


class Distance:
    """Represents distance from source — used in distance-based broadcasts."""

    def __init__(self, source_id: int):
        self.source_id = source_id

    def __repr__(self) -> str:
        return f"Distance(source={self.source_id})"


class HopCount:
    """Represents hop count from source in multi-hop propagation."""

    def __init__(self):
        pass

    def __repr__(self) -> str:
        return "HopCount()"


class Gossip(Generic[T]):
    """Represents gossip(value, accumulate) — distributed gossip aggregation."""

    def __init__(self, value: T, accumulate: Callable[[T, T], T]):
        self.value = value
        self.accumulate = accumulate

    def __repr__(self) -> str:
        return f"Gossip(value={self.value!r})"


class SpCollection(Generic[T]):
    """Represents sp_collection(distance, value, null, accumulate) — single-path collection."""

    def __init__(self, distance: Any, value: T, null: T, accumulate: Callable[[T, T], T]):
        self.distance = distance
        self.value = value
        self.null = null
        self.accumulate = accumulate

    def __repr__(self) -> str:
        return f"SpCollection(distance={self.distance!r}, value={self.value!r})"


class MpCollection(Generic[T]):
    """Represents mp_collection(distance, value, null, accumulate, divide) — multi-path collection."""

    def __init__(self, distance: Any, value: T, null: T, accumulate: Callable[[T, T], T], divide: Callable):
        self.distance = distance
        self.value = value
        self.null = null
        self.accumulate = accumulate
        self.divide = divide

    def __repr__(self) -> str:
        return f"MpCollection(distance={self.distance!r}, value={self.value!r})"


class WmpCollection(Generic[T]):
    """Represents wmp_collection(distance, radius, value, accumulate, multiply) — weighted multi-path collection."""

    def __init__(self, distance: float, radius: float, value: T, accumulate: Callable[[T, T], T], multiply: Callable):
        self.distance = distance
        self.radius = radius
        self.value = value
        self.accumulate = accumulate
        self.multiply = multiply

    def __repr__(self) -> str:
        return f"WmpCollection(distance={self.distance!r}, radius={self.radius!r}, value={self.value!r})"


class BisDistance:
    """Represents bis_distance(source, period, speed) — Bounded Information Speeds distance estimation."""

    def __init__(self, source: bool, period: float, speed: float, metric: Callable = None):
        self.source = source
        self.period = period
        self.speed = speed
        self.metric = metric

    def __repr__(self) -> str:
        return f"BisDistance(source={self.source!r}, period={self.period!r}, speed={self.speed!r})"


class AbfDistance:
    """Represents abf_distance(source) — Adaptive Bellman-Ford distance estimation."""

    def __init__(self, source: bool, metric: Callable = None):
        self.source = source
        self.metric = metric

    def __repr__(self) -> str:
        return f"AbfDistance(source={self.source!r})"


class RectangleWalk:
    """Represents rectangle_walk(low, hi, max_v, period) — random walk bounded to a rectangle."""

    def __init__(self, low: Any, hi: Any, max_v: float, period: float):
        self.low = low
        self.hi = hi
        self.max_v = max_v
        self.period = period

    def __repr__(self) -> str:
        return f"RectangleWalk(low={self.low!r}, hi={self.hi!r}, max_v={self.max_v!r})"


class FollowTarget:
    """Represents follow_target(target, max_v, period) — move toward a spatial target point."""

    def __init__(self, target: Any, max_v: float, period: float):
        self.target = target
        self.max_v = max_v
        self.period = period

    def __repr__(self) -> str:
        return f"FollowTarget(target={self.target!r}, max_v={self.max_v!r})"


# ─── basics.hpp additions ─────────────────────────────────────────────────────

class NbrUid:
    """Represents nbr_uid() — field of neighbour device identifiers."""
    def __repr__(self) -> str:
        return "NbrUid()"
    def __eq__(self, other: Any) -> bool:
        return isinstance(other, NbrUid)


class OldNbr(Generic[T]):
    """Represents oldnbr(f0, op) — combined old + nbr (rep + share)."""
    def __init__(self, initial: T, op: Callable):
        self.initial = initial
        self.op = op
    def __repr__(self) -> str:
        return f"OldNbr(initial={self.initial!r})"


class Align(Generic[T]):
    """Represents align(x) — align a field to the current call point."""
    def __init__(self, value: T):
        self.value = value
    def __repr__(self) -> str:
        return f"Align({self.value!r})"


class AlignInplace(Generic[T]):
    """Represents align_inplace(x) — align a field in-place."""
    def __init__(self, value: T):
        self.value = value
    def __repr__(self) -> str:
        return f"AlignInplace({self.value!r})"


class ModOther(Generic[T]):
    """Represents mod_other(x[, y]) — modify neighbour-side values of a field."""
    def __init__(self, value: T, modifier: Any = None):
        self.value = value
        self.modifier = modifier
    def __repr__(self) -> str:
        return f"ModOther({self.value!r})"


class Split:
    """Represents split(key, func) — partition computation by key."""
    def __init__(self, key: Any, func: Callable):
        self.key = key
        self.func = func
    def __repr__(self) -> str:
        return f"Split(key={self.key!r})"


# ─── utils.hpp additions ──────────────────────────────────────────────────────

class SumHood(Generic[T]):
    """Represents sum_hood(a[, self_val]) — neighbourhood sum."""
    def __init__(self, expr: Any, self_value: Any = None):
        self.expr = expr
        self.self_value = self_value
    def __repr__(self) -> str:
        return f"SumHood({self.expr!r})"


class MeanHood(Generic[T]):
    """Represents mean_hood(a[, self_val]) — neighbourhood mean."""
    def __init__(self, expr: Any, self_value: Any = None):
        self.expr = expr
        self.self_value = self_value
    def __repr__(self) -> str:
        return f"MeanHood({self.expr!r})"


class AllHood(Generic[T]):
    """Represents all_hood(a[, self_val]) — neighbourhood logical AND."""
    def __init__(self, expr: Any, self_value: Any = None):
        self.expr = expr
        self.self_value = self_value
    def __repr__(self) -> str:
        return f"AllHood({self.expr!r})"


class AnyHood(Generic[T]):
    """Represents any_hood(a[, self_val]) — neighbourhood logical OR."""
    def __init__(self, expr: Any, self_value: Any = None):
        self.expr = expr
        self.self_value = self_value
    def __repr__(self) -> str:
        return f"AnyHood({self.expr!r})"


class ListHood(Generic[T]):
    """Represents list_hood(container, a[, self_val]) — collect neighbourhood into container."""
    def __init__(self, container: Any, expr: Any, self_value: Any = None):
        self.container = container
        self.expr = expr
        self.self_value = self_value
    def __repr__(self) -> str:
        return f"ListHood(expr={self.expr!r})"


# ─── spreading.hpp additions ──────────────────────────────────────────────────

class AbfHops:
    """Represents abf_hops(source) — hop-count distance via Adaptive Bellman-Ford."""
    def __init__(self, source: bool):
        self.source = source
    def __repr__(self) -> str:
        return f"AbfHops(source={self.source!r})"


class FlexDistance:
    """Represents flex_distance(source, epsilon, radius, distortion, frequency[, metric])."""
    def __init__(self, source: bool, epsilon: float, radius: float, distortion: float, frequency: int, metric: Callable = None):
        self.source = source
        self.epsilon = epsilon
        self.radius = radius
        self.distortion = distortion
        self.frequency = frequency
        self.metric = metric
    def __repr__(self) -> str:
        return f"FlexDistance(source={self.source!r}, radius={self.radius!r})"


class BisKsourceBroadcast(Generic[T]):
    """Represents bis_ksource_broadcast(source, value, k, period, speed[, metric])."""
    def __init__(self, source: bool, value: T, k: int, period: float, speed: float, metric: Callable = None):
        self.source = source
        self.value = value
        self.k = k
        self.period = period
        self.speed = speed
        self.metric = metric
    def __repr__(self) -> str:
        return f"BisKsourceBroadcast(source={self.source!r}, k={self.k!r}, value={self.value!r})"


# ─── collection.hpp additions ─────────────────────────────────────────────────

class GossipMin(Generic[T]):
    """Represents gossip_min(value) — gossip the minimum."""
    def __init__(self, value: T):
        self.value = value
    def __repr__(self) -> str:
        return f"GossipMin({self.value!r})"


class GossipMax(Generic[T]):
    """Represents gossip_max(value) — gossip the maximum."""
    def __init__(self, value: T):
        self.value = value
    def __repr__(self) -> str:
        return f"GossipMax({self.value!r})"


class GossipMean(Generic[T]):
    """Represents gossip_mean(value) — gossip the mean."""
    def __init__(self, value: T):
        self.value = value
    def __repr__(self) -> str:
        return f"GossipMean({self.value!r})"


class ListIdemCollection(Generic[T]):
    """Represents list_idem_collection(distance, value, radius, speed, null, epsilon, accumulate)."""
    def __init__(self, distance: float, value: T, radius: float, speed: float, null: T, epsilon: float, accumulate: Callable):
        self.distance = distance
        self.value = value
        self.radius = radius
        self.speed = speed
        self.null = null
        self.epsilon = epsilon
        self.accumulate = accumulate
    def __repr__(self) -> str:
        return f"ListIdemCollection(distance={self.distance!r}, value={self.value!r})"


class ListArithCollection(Generic[T]):
    """Represents list_arith_collection(distance, value, radius, speed, null, epsilon, accumulate)."""
    def __init__(self, distance: float, value: T, radius: float, speed: float, null: T, epsilon: float, accumulate: Callable):
        self.distance = distance
        self.value = value
        self.radius = radius
        self.speed = speed
        self.null = null
        self.epsilon = epsilon
        self.accumulate = accumulate
    def __repr__(self) -> str:
        return f"ListArithCollection(distance={self.distance!r}, value={self.value!r})"


# ─── geometry.hpp additions ───────────────────────────────────────────────────

class FollowPath(Generic[T]):
    """Represents follow_path(path, max_v, period) — follow a sequence of waypoints."""
    def __init__(self, path: T, max_v: float, period: float):
        self.path = path
        self.max_v = max_v
        self.period = period
    def __repr__(self) -> str:
        return f"FollowPath(max_v={self.max_v!r})"


class FollowTrack:
    """Represents follow_track(trace) — follow a GPS trace."""
    def __init__(self, trace: Any):
        self.trace = trace
    def __repr__(self) -> str:
        return f"FollowTrack(trace={self.trace!r})"


class RandomRectangleTarget:
    """Represents random_rectangle_target(low, hi[, reach]) — pick a random target in a rectangle."""
    def __init__(self, low: Any, hi: Any, reach: float = None):
        self.low = low
        self.hi = hi
        self.reach = reach
    def __repr__(self) -> str:
        return f"RandomRectangleTarget(low={self.low!r}, hi={self.hi!r})"


class NeighbourElasticForce:
    """Represents neighbour_elastic_force(length, strength) — elastic spring force from neighbours."""
    def __init__(self, length: Any, strength: Any):
        self.length = length
        self.strength = strength
    def __repr__(self) -> str:
        return f"NeighbourElasticForce(length={self.length!r})"


class NeighbourGravitationalForce:
    """Represents neighbour_gravitational_force(mass) — gravitational force from neighbours."""
    def __init__(self, mass: float):
        self.mass = mass
    def __repr__(self) -> str:
        return f"NeighbourGravitationalForce(mass={self.mass!r})"


class NeighbourChargedForce:
    """Represents neighbour_charged_force(mass, charge) — electrostatic force from neighbours."""
    def __init__(self, mass: float, charge: float):
        self.mass = mass
        self.charge = charge
    def __repr__(self) -> str:
        return f"NeighbourChargedForce(mass={self.mass!r}, charge={self.charge!r})"


class LineElasticForce:
    """Represents line_elastic_force(p, q, length, strength) — elastic force from a line attractor."""
    def __init__(self, p: Any, q: Any, length: float, strength: float):
        self.p = p
        self.q = q
        self.length = length
        self.strength = strength
    def __repr__(self) -> str:
        return f"LineElasticForce(length={self.length!r})"


class PlaneElasticForce:
    """Represents plane_elastic_force(p, q, length, strength) — elastic force from a plane."""
    def __init__(self, p: Any, q: Any, length: float, strength: float):
        self.p = p
        self.q = q
        self.length = length
        self.strength = strength
    def __repr__(self) -> str:
        return f"PlaneElasticForce(length={self.length!r})"


class PointElasticForce:
    """Represents point_elastic_force(point, length, strength) — elastic force from a point attractor."""
    def __init__(self, point: Any, length: float, strength: float):
        self.point = point
        self.length = length
        self.strength = strength
    def __repr__(self) -> str:
        return f"PointElasticForce(point={self.point!r})"


class PointGravitationalForce:
    """Represents point_gravitational_force(point, mass) — gravitational force from a point."""
    def __init__(self, point: Any, mass: float):
        self.point = point
        self.mass = mass
    def __repr__(self) -> str:
        return f"PointGravitationalForce(point={self.point!r}, mass={self.mass!r})"


# ─── election.hpp additions ───────────────────────────────────────────────────

class DiameterElection(Generic[T]):
    """Represents diameter_election(value, diameter) — elect node by maximum diameter."""
    def __init__(self, value: T, diameter: int):
        self.value = value
        self.diameter = diameter
    def __repr__(self) -> str:
        return f"DiameterElection(value={self.value!r}, diameter={self.diameter!r})"


class DiameterElectionDistance(Generic[T]):
    """Represents diameter_election_distance(value, diameter) — diameter election with distance tracking."""
    def __init__(self, value: T, diameter: int):
        self.value = value
        self.diameter = diameter
    def __repr__(self) -> str:
        return f"DiameterElectionDistance(value={self.value!r}, diameter={self.diameter!r})"


class ColorElection(Generic[T]):
    """Represents color_election([value]) — color-based leader election."""
    def __init__(self, value: T = None):
        self.value = value
    def __repr__(self) -> str:
        return f"ColorElection(value={self.value!r})"


class ColorElectionDistance(Generic[T]):
    """Represents color_election_distance([value]) — color election with distance tracking."""
    def __init__(self, value: T = None):
        self.value = value
    def __repr__(self) -> str:
        return f"ColorElectionDistance(value={self.value!r})"


class WaveElection(Generic[T]):
    """Represents wave_election([value[, expansion]]) — wave-based leader election."""
    def __init__(self, value: T = None, expansion: Callable = None):
        self.value = value
        self.expansion = expansion
    def __repr__(self) -> str:
        return f"WaveElection(value={self.value!r})"


class WaveElectionDistance(Generic[T]):
    """Represents wave_election_distance([value[, expansion]]) — wave election with distance tracking."""
    def __init__(self, value: T = None, expansion: Callable = None):
        self.value = value
        self.expansion = expansion
    def __repr__(self) -> str:
        return f"WaveElectionDistance(value={self.value!r})"


# ─── time.hpp additions ───────────────────────────────────────────────────────

class Constant(Generic[T]):
    """Represents constant(value) — freeze a value across rounds."""
    def __init__(self, value: T):
        self.value = value
    def __repr__(self) -> str:
        return f"Constant({self.value!r})"


class ConstantAfter(Generic[T]):
    """Represents constant_after(value, t) — freeze value after time t."""
    def __init__(self, value: T, t: float):
        self.value = value
        self.t = t
    def __repr__(self) -> str:
        return f"ConstantAfter({self.value!r}, t={self.t!r})"


class Counter:
    """Represents counter([start[, increment]]) — increment counter each round."""
    def __init__(self, start: Any = None, increment: Any = None):
        self.start = start
        self.increment = increment
    def __repr__(self) -> str:
        return f"Counter(start={self.start!r})"
    def __eq__(self, other: Any) -> bool:
        return isinstance(other, Counter) and self.start == other.start


class Delay(Generic[T]):
    """Represents delay(value, n) — delay a value by n rounds."""
    def __init__(self, value: T, n: int):
        self.value = value
        self.n = n
    def __repr__(self) -> str:
        return f"Delay({self.value!r}, n={self.n!r})"


class RoundSince:
    """Represents round_since(condition) — rounds elapsed since condition was true."""
    def __init__(self, condition: Any):
        self.condition = condition
    def __repr__(self) -> str:
        return f"RoundSince({self.condition!r})"


class TimeSince:
    """Represents time_since(condition) — time elapsed since condition was true."""
    def __init__(self, condition: Any):
        self.condition = condition
    def __repr__(self) -> str:
        return f"TimeSince({self.condition!r})"


class TimedDecay(Generic[T]):
    """Represents timed_decay(value, null, dt) — value that decays to null over time dt."""
    def __init__(self, value: T, null: T, dt: float):
        self.value = value
        self.null = null
        self.dt = dt
    def __repr__(self) -> str:
        return f"TimedDecay({self.value!r}, null={self.null!r}, dt={self.dt!r})"


class ExponentialFilter(Generic[T]):
    """Represents exponential_filter(value, factor[, initial]) — exponential smoothing."""
    def __init__(self, value: T, factor: float, initial: T = None):
        self.value = value
        self.factor = factor
        self.initial = initial
    def __repr__(self) -> str:
        return f"ExponentialFilter({self.value!r}, factor={self.factor!r})"


class SharedClock:
    """Represents shared_clock() — synchronized network-wide clock."""
    def __repr__(self) -> str:
        return "SharedClock()"
    def __eq__(self, other: Any) -> bool:
        return isinstance(other, SharedClock)


class SharedDecay(Generic[T]):
    """Represents shared_decay(value, factor[, initial]) — network-wide decaying value."""
    def __init__(self, value: T, factor: float, initial: T = None):
        self.value = value
        self.factor = factor
        self.initial = initial
    def __repr__(self) -> str:
        return f"SharedDecay({self.value!r}, factor={self.factor!r})"


class SharedFilter(Generic[T]):
    """Represents shared_filter(value, factor[, initial]) — network-wide filtered value."""
    def __init__(self, value: T, factor: float, initial: T = None):
        self.value = value
        self.factor = factor
        self.initial = initial
    def __repr__(self) -> str:
        return f"SharedFilter({self.value!r}, factor={self.factor!r})"


class Toggle:
    """Represents toggle(change[, start]) — toggles a boolean on each change event."""
    def __init__(self, change: Any, start: bool = False):
        self.change = change
        self.start = start
    def __repr__(self) -> str:
        return f"Toggle({self.change!r}, start={self.start!r})"


class ToggleFilter:
    """Represents toggle_filter(change[, start]) — filtered version of toggle."""
    def __init__(self, change: Any, start: bool = False):
        self.change = change
        self.start = start
    def __repr__(self) -> str:
        return f"ToggleFilter({self.change!r}, start={self.start!r})"
