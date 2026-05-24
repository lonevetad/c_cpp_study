"""Core FCPP DSL primitives — Field, Neighborhood, OldValue, etc."""

import copy
from typing import TypeVar, Generic, Any, List, Callable

T = TypeVar("T")


class Primitive:
    """Base class for all FCPP DSL primitives.

    Provides a shared interface for introspection, default equality/hashing,
    and the *Prototype* design-pattern methods :meth:`clone` and
    :meth:`clone_with`.

    Class attributes (override in subclasses as needed)
    ---------------------------------------------------
    has_callable_args : bool
        ``True`` when one or more constructor arguments are callables (C++
        ``G&&`` forwarding-reference parameters).
    callable_arg_positions : tuple[int, ...]
        Zero-based indices of constructor parameters that are callables.
        Documented so the transpiler can emit the correct C++ lambda syntax.
    """

    has_callable_args: bool = False
    callable_arg_positions: tuple = ()

    # ------------------------------------------------------------------
    # Default __repr__: ClassName(attr=value, …)
    # Subclasses that define their own __repr__ take precedence via MRO.
    # ------------------------------------------------------------------
    def __repr__(self) -> str:
        attrs = {k: v for k, v in self.__dict__.items() if not k.startswith("_")}
        if not attrs:
            return f"{type(self).__name__}()"
        parts = ", ".join(
            f"{k}=<callable>" if callable(v) else f"{k}={v!r}"
            for k, v in attrs.items()
        )
        return f"{type(self).__name__}({parts})"

    # ------------------------------------------------------------------
    # Default __eq__: compare type + all instance attrs; callables by identity.
    # ------------------------------------------------------------------
    def __eq__(self, other: object) -> bool:
        if type(self) is not type(other):
            return NotImplemented
        for k, self_v in self.__dict__.items():
            other_v = getattr(other, k, _MISSING)
            if other_v is _MISSING:
                return False
            if callable(self_v) or callable(other_v):
                if self_v is not other_v:
                    return False
            elif self_v != other_v:
                return False
        return True

    def __hash__(self) -> int:
        return hash(type(self).__name__)

    # ------------------------------------------------------------------
    # Prototype pattern
    # ------------------------------------------------------------------
    def clone(self) -> "Primitive":
        """Return a shallow copy of this primitive (Prototype pattern)."""
        return copy.copy(self)

    def clone_with(self, **changes: Any) -> "Primitive":
        """Return a shallow copy with selected attributes overridden.

        Raises ``AttributeError`` if a key in *changes* does not correspond
        to an existing instance attribute.
        """
        obj = copy.copy(self)
        for key, value in changes.items():
            if not hasattr(obj, key):
                raise AttributeError(
                    f"{type(self).__name__!r} has no attribute {key!r}")
            setattr(obj, key, value)
        return obj


_MISSING = object()  # sentinel for missing attributes in __eq__


class Field(Primitive, Generic[T]):
    """Represents an FCPP field<T> — spatially-distributed value across all nodes."""

    def __init__(self, value: T) -> None:
        self.value = value

    def __repr__(self) -> str:
        return f"Field({self.value!r})"

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Field):
            return False
        return self.value == other.value


class Neighborhood(Primitive, Generic[T]):
    """Represents nbr<T> — neighbor values in current round."""

    def __init__(self, values: List[T]) -> None:
        self.values = values if values else []

    def __repr__(self) -> str:
        return f"Neighborhood({self.values!r})"

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Neighborhood):
            return False
        return self.values == other.values

    def __bool__(self) -> bool:
        return len(self.values) > 0

    def __len__(self) -> int:
        return len(self.values)


class OldValue(Primitive, Generic[T]):
    """Represents old<T> — value from previous round."""

    def __init__(self, value: T) -> None:
        self.value = value

    def __repr__(self) -> str:
        return f"OldValue({self.value!r})"

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, OldValue):
            return False
        return self.value == other.value


class StateValue(Primitive):
    """Marker for current node's own state value."""

    def __init__(self) -> None:
        pass

    def __repr__(self) -> str:
        return "StateValue()"

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, StateValue)


class FoldHood(Primitive, Generic[T]):
    """Represents fold_hood(init, expr) — tree reduction over neighborhood.
    ``expr`` is a callable (C++ ``G&&``)."""

    has_callable_args = True
    callable_arg_positions = (1,)   # expr at constructor index 1

    def __init__(self, init: T, expr: Callable[[T, T], T]) -> None:
        self.init = init
        self.expr = expr

    def __repr__(self) -> str:
        return f"FoldHood(init={self.init!r}, expr=<callable>)"


class MinHood(Primitive, Generic[T]):
    """Represents min_hood(expr) — minimum across neighborhood."""

    def __init__(self, expr: Any) -> None:
        self.expr = expr

    def __repr__(self) -> str:
        return f"MinHood({self.expr!r})"


class MaxHood(Primitive, Generic[T]):
    """Represents max_hood(expr) — maximum across neighborhood."""

    def __init__(self, expr: Any) -> None:
        self.expr = expr

    def __repr__(self) -> str:
        return f"MaxHood({self.expr!r})"


class CountHood(Primitive):
    """Represents count_hood() — count of neighbors."""

    def __init__(self) -> None:
        pass

    def __repr__(self) -> str:
        return "CountHood()"

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, CountHood)


class Spawn(Primitive, Generic[T]):
    """Represents spawn(f) — parallel sub-computation.
    ``func`` is a callable (C++ ``G&&``)."""

    has_callable_args = True
    callable_arg_positions = (0,)   # func at constructor index 0

    def __init__(self, func: Callable[..., T]) -> None:
        self.func = func

    def __repr__(self) -> str:
        return f"Spawn({self.func.__name__})"


class Broadcast(Primitive, Generic[T]):
    """Represents broadcast(source, expr) — multi-source dissemination."""

    def __init__(self, source_expr: Any, value_expr: Any) -> None:
        self.source = source_expr
        self.value = value_expr

    def __repr__(self) -> str:
        return f"Broadcast(source={self.source!r}, value={self.value!r})"


class Distance(Primitive):
    """Represents distance from source — used in distance-based broadcasts."""

    def __init__(self, source_id: int) -> None:
        self.source_id = source_id

    def __repr__(self) -> str:
        return f"Distance(source={self.source_id})"


class HopCount(Primitive):
    """Represents hop count from source in multi-hop propagation."""

    def __init__(self) -> None:
        pass

    def __repr__(self) -> str:
        return "HopCount()"


class Gossip(Primitive, Generic[T]):
    """Represents gossip(value, accumulate) — distributed gossip aggregation.
    ``accumulate`` is a callable (C++ ``G&&``)."""

    has_callable_args = True
    callable_arg_positions = (1,)   # accumulate at constructor index 1

    def __init__(self, value: T, accumulate: Callable[[T, T], T]) -> None:
        self.value = value
        self.accumulate = accumulate

    def __repr__(self) -> str:
        return f"Gossip(value={self.value!r}, accumulate=<callable>)"


class SpCollection(Primitive, Generic[T]):
    """Represents sp_collection(distance, value, null, accumulate) — single-path collection.
    ``accumulate`` is a callable (C++ ``G&&``)."""

    has_callable_args = True
    callable_arg_positions = (3,)   # accumulate at constructor index 3

    def __init__(self, distance: Any, value: T, null: T, accumulate: Callable[[T, T], T]) -> None:
        self.distance = distance
        self.value = value
        self.null = null
        self.accumulate = accumulate

    def __repr__(self) -> str:
        return f"SpCollection(distance={self.distance!r}, value={self.value!r}, accumulate=<callable>)"


class MpCollection(Primitive, Generic[T]):
    """Represents mp_collection(distance, value, null, accumulate, divide) — multi-path collection.
    ``accumulate`` and ``divide`` are callables (C++ ``G&&``)."""

    has_callable_args = True
    callable_arg_positions = (3, 4)   # accumulate, divide

    def __init__(self, distance: Any, value: T, null: T,
                 accumulate: Callable[[T, T], T], divide: Callable) -> None:
        self.distance = distance
        self.value = value
        self.null = null
        self.accumulate = accumulate
        self.divide = divide

    def __repr__(self) -> str:
        return f"MpCollection(distance={self.distance!r}, value={self.value!r}, accumulate=<callable>)"


class WmpCollection(Primitive, Generic[T]):
    """Represents wmp_collection(distance, radius, value, accumulate, multiply) — weighted multi-path collection.
    ``accumulate`` and ``multiply`` are callables (C++ ``G&&``)."""

    has_callable_args = True
    callable_arg_positions = (3, 4)   # accumulate, multiply

    def __init__(self, distance: float, radius: float, value: T,
                 accumulate: Callable[[T, T], T], multiply: Callable) -> None:
        self.distance = distance
        self.radius = radius
        self.value = value
        self.accumulate = accumulate
        self.multiply = multiply

    def __repr__(self) -> str:
        return (
            f"WmpCollection(distance={self.distance!r}, radius={self.radius!r}, "
            f"value={self.value!r}, accumulate=<callable>)"
        )


class BisDistance(Primitive):
    """Represents bis_distance(source, period, speed[, metric]) — Bounded Information Speeds distance.
    ``metric`` is an optional callable (C++ ``G&&``)."""

    has_callable_args = True
    callable_arg_positions = (3,)   # metric at constructor index 3

    def __init__(self, source: bool, period: float, speed: float,
                 metric: Callable = None) -> None:
        self.source = source
        self.period = period
        self.speed = speed
        self.metric = metric

    def __repr__(self) -> str:
        return f"BisDistance(source={self.source!r}, period={self.period!r}, speed={self.speed!r})"


class AbfDistance(Primitive):
    """Represents abf_distance(source[, metric]) — Adaptive Bellman-Ford distance.
    ``metric`` is an optional callable (C++ ``G&&``)."""

    has_callable_args = True
    callable_arg_positions = (1,)   # metric at constructor index 1

    def __init__(self, source: bool, metric: Callable = None) -> None:
        self.source = source
        self.metric = metric

    def __repr__(self) -> str:
        return f"AbfDistance(source={self.source!r})"


class RectangleWalk(Primitive):
    """Represents rectangle_walk(low, hi, max_v, period) — random walk bounded to a rectangle."""

    def __init__(self, low: Any, hi: Any, max_v: float, period: float) -> None:
        self.low = low
        self.hi = hi
        self.max_v = max_v
        self.period = period

    def __repr__(self) -> str:
        return f"RectangleWalk(low={self.low!r}, hi={self.hi!r}, max_v={self.max_v!r})"


class FollowTarget(Primitive):
    """Represents follow_target(target, max_v, period) — move toward a spatial target point."""

    def __init__(self, target: Any, max_v: float, period: float) -> None:
        self.target = target
        self.max_v = max_v
        self.period = period

    def __repr__(self) -> str:
        return f"FollowTarget(target={self.target!r}, max_v={self.max_v!r})"


# ─── basics.hpp additions ─────────────────────────────────────────────────────

class NbrUid(Primitive):
    """Represents nbr_uid() — field of neighbour device identifiers."""

    def __init__(self) -> None:
        pass

    def __repr__(self) -> str:
        return "NbrUid()"

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, NbrUid)


class OldNbr(Primitive, Generic[T]):
    """Represents oldnbr(f0, op) — combined old + nbr (rep + share).
    ``op`` is a callable (C++ ``G&&``)."""

    has_callable_args = True
    callable_arg_positions = (1,)   # op at constructor index 1

    def __init__(self, initial: T, op: Callable) -> None:
        self.initial = initial
        self.op = op

    def __repr__(self) -> str:
        return f"OldNbr(initial={self.initial!r}, op=<callable>)"


class Align(Primitive, Generic[T]):
    """Represents align(x) — align a field to the current call point."""

    def __init__(self, value: T) -> None:
        self.value = value

    def __repr__(self) -> str:
        return f"Align({self.value!r})"


class AlignInplace(Primitive, Generic[T]):
    """Represents align_inplace(x) — align a field in-place."""

    def __init__(self, value: T) -> None:
        self.value = value

    def __repr__(self) -> str:
        return f"AlignInplace({self.value!r})"


class ModOther(Primitive, Generic[T]):
    """Represents mod_other(x[, y]) — modify neighbour-side values of a field."""

    def __init__(self, value: T, modifier: Any = None) -> None:
        self.value = value
        self.modifier = modifier

    def __repr__(self) -> str:
        return f"ModOther({self.value!r})"


class Split(Primitive):
    """Represents split(key, func) — partition computation by key.
    ``func`` is a callable (C++ ``G&&``)."""

    has_callable_args = True
    callable_arg_positions = (1,)   # func at constructor index 1

    def __init__(self, key: Any, func: Callable) -> None:
        self.key = key
        self.func = func

    def __repr__(self) -> str:
        return f"Split(key={self.key!r}, func=<callable>)"


# ─── utils.hpp additions ──────────────────────────────────────────────────────

class SumHood(Primitive, Generic[T]):
    """Represents sum_hood(a[, self_val]) — neighbourhood sum."""

    def __init__(self, expr: Any, self_value: Any = None) -> None:
        self.expr = expr
        self.self_value = self_value

    def __repr__(self) -> str:
        return f"SumHood({self.expr!r})"


class MeanHood(Primitive, Generic[T]):
    """Represents mean_hood(a[, self_val]) — neighbourhood mean."""

    def __init__(self, expr: Any, self_value: Any = None) -> None:
        self.expr = expr
        self.self_value = self_value

    def __repr__(self) -> str:
        return f"MeanHood({self.expr!r})"


class AllHood(Primitive, Generic[T]):
    """Represents all_hood(a[, self_val]) — neighbourhood logical AND."""

    def __init__(self, expr: Any, self_value: Any = None) -> None:
        self.expr = expr
        self.self_value = self_value

    def __repr__(self) -> str:
        return f"AllHood({self.expr!r})"


class AnyHood(Primitive, Generic[T]):
    """Represents any_hood(a[, self_val]) — neighbourhood logical OR."""

    def __init__(self, expr: Any, self_value: Any = None) -> None:
        self.expr = expr
        self.self_value = self_value

    def __repr__(self) -> str:
        return f"AnyHood({self.expr!r})"


class ListHood(Primitive, Generic[T]):
    """Represents list_hood(container, a[, self_val]) — collect neighbourhood into container."""

    def __init__(self, container: Any, expr: Any, self_value: Any = None) -> None:
        self.container = container
        self.expr = expr
        self.self_value = self_value

    def __repr__(self) -> str:
        return f"ListHood(expr={self.expr!r})"


# ─── spreading.hpp additions ──────────────────────────────────────────────────

class AbfHops(Primitive):
    """Represents abf_hops(source) — hop-count distance via Adaptive Bellman-Ford."""

    def __init__(self, source: bool) -> None:
        self.source = source

    def __repr__(self) -> str:
        return f"AbfHops(source={self.source!r})"


class FlexDistance(Primitive):
    """Represents flex_distance(source, epsilon, radius, distortion, frequency[, metric]).
    ``metric`` is an optional callable (C++ ``G&&``)."""

    has_callable_args = True
    callable_arg_positions = (5,)   # metric at constructor index 5

    def __init__(self, source: bool, epsilon: float, radius: float,
                 distortion: float, frequency: int, metric: Callable = None) -> None:
        self.source = source
        self.epsilon = epsilon
        self.radius = radius
        self.distortion = distortion
        self.frequency = frequency
        self.metric = metric

    def __repr__(self) -> str:
        return f"FlexDistance(source={self.source!r}, radius={self.radius!r})"


class BisKsourceBroadcast(Primitive, Generic[T]):
    """Represents bis_ksource_broadcast(source, value, k, period, speed[, metric]).
    ``metric`` is an optional callable (C++ ``G&&``)."""

    has_callable_args = True
    callable_arg_positions = (5,)   # metric at constructor index 5

    def __init__(self, source: bool, value: T, k: int, period: float,
                 speed: float, metric: Callable = None) -> None:
        self.source = source
        self.value = value
        self.k = k
        self.period = period
        self.speed = speed
        self.metric = metric

    def __repr__(self) -> str:
        return f"BisKsourceBroadcast(source={self.source!r}, k={self.k!r}, value={self.value!r})"


# ─── collection.hpp additions ─────────────────────────────────────────────────

class GossipMin(Primitive, Generic[T]):
    """Represents gossip_min(value) — gossip the minimum."""

    def __init__(self, value: T) -> None:
        self.value = value

    def __repr__(self) -> str:
        return f"GossipMin({self.value!r})"


class GossipMax(Primitive, Generic[T]):
    """Represents gossip_max(value) — gossip the maximum."""

    def __init__(self, value: T) -> None:
        self.value = value

    def __repr__(self) -> str:
        return f"GossipMax({self.value!r})"


class GossipMean(Primitive, Generic[T]):
    """Represents gossip_mean(value) — gossip the mean."""

    def __init__(self, value: T) -> None:
        self.value = value

    def __repr__(self) -> str:
        return f"GossipMean({self.value!r})"


class ListIdemCollection(Primitive, Generic[T]):
    """Represents list_idem_collection(distance, value, radius, speed, null, epsilon, accumulate).
    ``accumulate`` is a callable (C++ ``G&&``)."""

    has_callable_args = True
    callable_arg_positions = (6,)   # accumulate at constructor index 6

    def __init__(self, distance: float, value: T, radius: float, speed: float,
                 null: T, epsilon: float, accumulate: Callable) -> None:
        self.distance = distance
        self.value = value
        self.radius = radius
        self.speed = speed
        self.null = null
        self.epsilon = epsilon
        self.accumulate = accumulate

    def __repr__(self) -> str:
        return f"ListIdemCollection(distance={self.distance!r}, value={self.value!r}, accumulate=<callable>)"


class ListArithCollection(Primitive, Generic[T]):
    """Represents list_arith_collection(distance, value, radius, speed, null, epsilon, accumulate).
    ``accumulate`` is a callable (C++ ``G&&``)."""

    has_callable_args = True
    callable_arg_positions = (6,)   # accumulate at constructor index 6

    def __init__(self, distance: float, value: T, radius: float, speed: float,
                 null: T, epsilon: float, accumulate: Callable) -> None:
        self.distance = distance
        self.value = value
        self.radius = radius
        self.speed = speed
        self.null = null
        self.epsilon = epsilon
        self.accumulate = accumulate

    def __repr__(self) -> str:
        return f"ListArithCollection(distance={self.distance!r}, value={self.value!r}, accumulate=<callable>)"


# ─── geometry.hpp additions ───────────────────────────────────────────────────

class FollowPath(Primitive, Generic[T]):
    """Represents follow_path(path, max_v, period) — follow a sequence of waypoints."""

    def __init__(self, path: T, max_v: float, period: float) -> None:
        self.path = path
        self.max_v = max_v
        self.period = period

    def __repr__(self) -> str:
        return f"FollowPath(max_v={self.max_v!r})"


class FollowTrack(Primitive):
    """Represents follow_track(trace) — follow a GPS trace."""

    def __init__(self, trace: Any) -> None:
        self.trace = trace

    def __repr__(self) -> str:
        return f"FollowTrack(trace={self.trace!r})"


class RandomRectangleTarget(Primitive):
    """Represents random_rectangle_target(low, hi[, reach]) — pick a random target in a rectangle."""

    def __init__(self, low: Any, hi: Any, reach: float = None) -> None:
        self.low = low
        self.hi = hi
        self.reach = reach

    def __repr__(self) -> str:
        return f"RandomRectangleTarget(low={self.low!r}, hi={self.hi!r})"


class NeighbourElasticForce(Primitive):
    """Represents neighbour_elastic_force(length, strength) — elastic spring force from neighbours."""

    def __init__(self, length: Any, strength: Any) -> None:
        self.length = length
        self.strength = strength

    def __repr__(self) -> str:
        return f"NeighbourElasticForce(length={self.length!r})"


class NeighbourGravitationalForce(Primitive):
    """Represents neighbour_gravitational_force(mass) — gravitational force from neighbours."""

    def __init__(self, mass: float) -> None:
        self.mass = mass

    def __repr__(self) -> str:
        return f"NeighbourGravitationalForce(mass={self.mass!r})"


class NeighbourChargedForce(Primitive):
    """Represents neighbour_charged_force(mass, charge) — electrostatic force from neighbours."""

    def __init__(self, mass: float, charge: float) -> None:
        self.mass = mass
        self.charge = charge

    def __repr__(self) -> str:
        return f"NeighbourChargedForce(mass={self.mass!r}, charge={self.charge!r})"


class LineElasticForce(Primitive):
    """Represents line_elastic_force(p, q, length, strength) — elastic force from a line attractor."""

    def __init__(self, p: Any, q: Any, length: float, strength: float) -> None:
        self.p = p
        self.q = q
        self.length = length
        self.strength = strength

    def __repr__(self) -> str:
        return f"LineElasticForce(length={self.length!r})"


class PlaneElasticForce(Primitive):
    """Represents plane_elastic_force(p, q, length, strength) — elastic force from a plane."""

    def __init__(self, p: Any, q: Any, length: float, strength: float) -> None:
        self.p = p
        self.q = q
        self.length = length
        self.strength = strength

    def __repr__(self) -> str:
        return f"PlaneElasticForce(length={self.length!r})"


class PointElasticForce(Primitive):
    """Represents point_elastic_force(point, length, strength) — elastic force from a point attractor."""

    def __init__(self, point: Any, length: float, strength: float) -> None:
        self.point = point
        self.length = length
        self.strength = strength

    def __repr__(self) -> str:
        return f"PointElasticForce(point={self.point!r})"


class PointGravitationalForce(Primitive):
    """Represents point_gravitational_force(point, mass) — gravitational force from a point."""

    def __init__(self, point: Any, mass: float) -> None:
        self.point = point
        self.mass = mass

    def __repr__(self) -> str:
        return f"PointGravitationalForce(point={self.point!r}, mass={self.mass!r})"


# ─── election.hpp additions ───────────────────────────────────────────────────

class DiameterElection(Primitive, Generic[T]):
    """Represents diameter_election(value, diameter) — elect node by maximum diameter."""

    def __init__(self, value: T, diameter: int) -> None:
        self.value = value
        self.diameter = diameter

    def __repr__(self) -> str:
        return f"DiameterElection(value={self.value!r}, diameter={self.diameter!r})"


class DiameterElectionDistance(Primitive, Generic[T]):
    """Represents diameter_election_distance(value, diameter) — diameter election with distance tracking."""

    def __init__(self, value: T, diameter: int) -> None:
        self.value = value
        self.diameter = diameter

    def __repr__(self) -> str:
        return f"DiameterElectionDistance(value={self.value!r}, diameter={self.diameter!r})"


class ColorElection(Primitive, Generic[T]):
    """Represents color_election([value]) — color-based leader election."""

    def __init__(self, value: T = None) -> None:
        self.value = value

    def __repr__(self) -> str:
        return f"ColorElection(value={self.value!r})"


class ColorElectionDistance(Primitive, Generic[T]):
    """Represents color_election_distance([value]) — color election with distance tracking."""

    def __init__(self, value: T = None) -> None:
        self.value = value

    def __repr__(self) -> str:
        return f"ColorElectionDistance(value={self.value!r})"


class WaveElection(Primitive, Generic[T]):
    """Represents wave_election([value[, expansion]]) — wave-based leader election.
    ``expansion`` is an optional callable (C++ ``G&&``)."""

    has_callable_args = True
    callable_arg_positions = (1,)   # expansion at constructor index 1

    def __init__(self, value: T = None, expansion: Callable = None) -> None:
        self.value = value
        self.expansion = expansion

    def __repr__(self) -> str:
        return f"WaveElection(value={self.value!r})"


class WaveElectionDistance(Primitive, Generic[T]):
    """Represents wave_election_distance([value[, expansion]]) — wave election with distance tracking.
    ``expansion`` is an optional callable (C++ ``G&&``)."""

    has_callable_args = True
    callable_arg_positions = (1,)   # expansion at constructor index 1

    def __init__(self, value: T = None, expansion: Callable = None) -> None:
        self.value = value
        self.expansion = expansion

    def __repr__(self) -> str:
        return f"WaveElectionDistance(value={self.value!r})"


# ─── time.hpp additions ───────────────────────────────────────────────────────

class Constant(Primitive, Generic[T]):
    """Represents constant(value) — freeze a value across rounds."""

    def __init__(self, value: T) -> None:
        self.value = value

    def __repr__(self) -> str:
        return f"Constant({self.value!r})"


class ConstantAfter(Primitive, Generic[T]):
    """Represents constant_after(value, t) — freeze value after time t."""

    def __init__(self, value: T, t: float) -> None:
        self.value = value
        self.t = t

    def __repr__(self) -> str:
        return f"ConstantAfter({self.value!r}, t={self.t!r})"


class Counter(Primitive):
    """Represents counter([start[, increment]]) — increment counter each round."""

    def __init__(self, start: Any = None, increment: Any = None) -> None:
        self.start = start
        self.increment = increment

    def __repr__(self) -> str:
        return f"Counter(start={self.start!r})"

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, Counter) and self.start == other.start


class Delay(Primitive, Generic[T]):
    """Represents delay(value, n) — delay a value by n rounds."""

    def __init__(self, value: T, n: int) -> None:
        self.value = value
        self.n = n

    def __repr__(self) -> str:
        return f"Delay({self.value!r}, n={self.n!r})"


class RoundSince(Primitive):
    """Represents round_since(condition) — rounds elapsed since condition was true."""

    def __init__(self, condition: Any) -> None:
        self.condition = condition

    def __repr__(self) -> str:
        return f"RoundSince({self.condition!r})"


class TimeSince(Primitive):
    """Represents time_since(condition) — time elapsed since condition was true."""

    def __init__(self, condition: Any) -> None:
        self.condition = condition

    def __repr__(self) -> str:
        return f"TimeSince({self.condition!r})"


class TimedDecay(Primitive, Generic[T]):
    """Represents timed_decay(value, null, dt) — value that decays to null over time dt."""

    def __init__(self, value: T, null: T, dt: float) -> None:
        self.value = value
        self.null = null
        self.dt = dt

    def __repr__(self) -> str:
        return f"TimedDecay({self.value!r}, null={self.null!r}, dt={self.dt!r})"


class ExponentialFilter(Primitive, Generic[T]):
    """Represents exponential_filter(value, factor[, initial]) — exponential smoothing."""

    def __init__(self, value: T, factor: float, initial: T = None) -> None:
        self.value = value
        self.factor = factor
        self.initial = initial

    def __repr__(self) -> str:
        return f"ExponentialFilter({self.value!r}, factor={self.factor!r})"


class SharedClock(Primitive):
    """Represents shared_clock() — synchronized network-wide clock."""

    def __init__(self) -> None:
        pass

    def __repr__(self) -> str:
        return "SharedClock()"

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, SharedClock)


class SharedDecay(Primitive, Generic[T]):
    """Represents shared_decay(value, factor[, initial]) — network-wide decaying value."""

    def __init__(self, value: T, factor: float, initial: T = None) -> None:
        self.value = value
        self.factor = factor
        self.initial = initial

    def __repr__(self) -> str:
        return f"SharedDecay({self.value!r}, factor={self.factor!r})"


class SharedFilter(Primitive, Generic[T]):
    """Represents shared_filter(value, factor[, initial]) — network-wide filtered value."""

    def __init__(self, value: T, factor: float, initial: T = None) -> None:
        self.value = value
        self.factor = factor
        self.initial = initial

    def __repr__(self) -> str:
        return f"SharedFilter({self.value!r}, factor={self.factor!r})"


class Toggle(Primitive):
    """Represents toggle(change[, start]) — toggles a boolean on each change event."""

    def __init__(self, change: Any, start: bool = False) -> None:
        self.change = change
        self.start = start

    def __repr__(self) -> str:
        return f"Toggle({self.change!r}, start={self.start!r})"


class ToggleFilter(Primitive):
    """Represents toggle_filter(change[, start]) — filtered version of toggle."""

    def __init__(self, change: Any, start: bool = False) -> None:
        self.change = change
        self.start = start

    def __repr__(self) -> str:
        return f"ToggleFilter({self.change!r}, start={self.start!r})"
