"""AbstractExample — base class for fcpp_bridge demo simulations.

Every main example subclasses ``AbstractExample`` and overrides the abstract
methods listed below.  The concrete ``run()`` method handles the full toolchain:

- Validating the ``@aggregate_function`` class.
- Transpiling it to C++.
- Compiling the C++ (SHA-256 cached; recompiles only when source changes).
- Spawning a :class:`~fcpp_bridge.ipc.SwarmProcess` and seeding it with
  ``initial_positions()``.
- Iterating ``num_rounds`` steps, collecting :class:`~fcpp_bridge.ipc.SwarmSnapshot`
  objects from the IPC listener.
- Writing per-node log files from ``snapshot.nodes``.
- Calling the optional hook methods at the appropriate points.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Type

from fcpp_bridge.ipc.swarm_snapshot import SwarmSnapshot


class AbstractExample(ABC):
    """Template Method base class for fcpp_bridge demo simulations.

    Subclasses implement the algorithm-specific methods; ``run()`` provides
    the toolchain invocation (validate → transpile → compile → run C++ binary).

    Required overrides
    ------------------
    aggregate_class     @property → Type   — the @aggregate_function class to run
    log_prefix          @property → str    — used in log file names
    initial_positions() → dict[int, tuple] — starting (x, y) per node
    log_header(node_id, state_data) → str  — CSV header line
    log_line(round_num, node_id, state_data) → str — one CSV data line

    Optional hooks
    --------------
    on_simulation_start()                    — open extra log files / print header
    on_simulation_end()                      — close extra log files / print summary
    on_round_complete(round_num, snapshot)   — write extra per-round data
    """

    # ── Required properties / abstract methods ────────────────────────────────

    @property
    @abstractmethod
    def aggregate_class(self) -> Type:
        """The ``@aggregate_function`` class that defines the algorithm.

        This class is validated, transpiled to C++, and compiled before the
        simulation begins.  It must be decorated with ``@aggregate_function``.
        """

    @property
    @abstractmethod
    def log_prefix(self) -> str:
        """Suffix used in node log file names: ``node_<id>_<log_prefix>.log``."""

    @property
    def log_dir(self) -> Path:
        """Directory for log files.  Default: ``examples/logs/``."""
        return Path(__file__).parent / "logs"

    @property
    def build_dir(self) -> Path:
        """Cache directory for compiled C++ binaries.  Default: ``examples/.fcpp_build/``."""
        return Path(__file__).parent / ".fcpp_build"

    @property
    def cpp_dir(self) -> Path:
        """Directory where transpiled C++ source is written.  Default: ``examples/.fcpp_cpp/``."""
        return Path(__file__).parent / ".fcpp_cpp"

    @abstractmethod
    def initial_positions(self) -> Dict[int, Tuple[float, ...]]:
        """Return ``{node_id: (x, y)}`` for every node in the initial swarm.

        The keys of this dict define the initial node set.  There is no
        requirement that IDs are consecutive or start from zero.
        """

    @abstractmethod
    def log_header(self, node_id: int, state_data: Any) -> str:
        """Return the CSV header line for *node_id*'s log file.

        Called once when a node's log file is first opened.  The returned
        string should end with ``\\n``.  Lines starting with ``#`` are treated
        as comments by most CSV readers.
        """

    @abstractmethod
    def log_line(self, round_num: int, node_id: int, state_data: Any) -> str:
        """Return one CSV data line for *round_num* / *node_id*.

        Called every round for every node that is currently active.  The
        returned string should end with ``\\n``.  ``state_data`` comes from
        the FCPP snapshot (:attr:`~fcpp_bridge.ipc.NodeState.state_data`).
        """

    # ── Optional hooks ────────────────────────────────────────────────────────

    def on_simulation_start(self) -> None:
        """Hook called once before the simulation loop starts.

        Use this to open extra log files (e.g. a shared receiver log),
        initialise per-simulation data structures, or print a header.
        """

    def on_simulation_end(self) -> None:
        """Hook called once after the simulation loop ends.

        Use this to close extra log files, print summary statistics, or
        flush any buffered output.
        """

    def on_round_complete(
        self,
        round_num: int,
        snapshot: Optional[SwarmSnapshot],
    ) -> None:
        """Hook called after per-node log lines are written for this round.

        ``snapshot`` is the :class:`~fcpp_bridge.ipc.SwarmSnapshot` received
        from the C++ binary for this round, or ``None`` if no update arrived
        (e.g. when running with a non-blocking backend).

        Use this to write round-level aggregates, receiver message logs, or
        any data that is not per-node.
        """

    # ── Concrete simulation driver ────────────────────────────────────────────

    def run(self, num_rounds: int) -> None:
        """Validate, transpile, compile, and run the simulation.

        Invokes the full toolchain:

        1. :class:`~fcpp_bridge.python_dsl.validators.AggregateValidator` validates
           ``aggregate_class``.
        2. :class:`~fcpp_bridge.transpiler.Transpiler` transpiles it to C++.
        3. :class:`~fcpp_bridge.compiler.Compiler` compiles (SHA-256 cached).
        4. :class:`~fcpp_bridge.ipc.SwarmProcess` is started and seeded with
           ``initial_positions()``.
        5. For each round, ``step()`` fires the IPC listener:

           - New nodes get a log file opened with the header written.
           - All active nodes get a ``log_line`` appended.
           - Nodes absent from the snapshot have their log files closed.

        6. ``on_round_complete(round_num, snapshot)`` is called.
        7. After all rounds, remaining log files are closed and
           ``on_simulation_end()`` is called.

        Note: ``_on_snapshot`` fires when the C++ binary pushes a state update.
        With a synchronous backend this happens within ``step()``; with an
        asynchronous backend ``latest_snapshot()`` may lag by one round.
        """
        from fcpp_bridge.transpiler import Transpiler
        from fcpp_bridge.compiler import Compiler
        from fcpp_bridge.python_dsl.validators import AggregateValidator
        from fcpp_bridge.ipc.swarm_process import SwarmProcess

        # Validate
        AggregateValidator.validate(self.aggregate_class)

        # Transpile
        t = Transpiler(self.aggregate_class)
        cpp_code = t.generate()

        # Compile (cached by SHA-256)
        self.build_dir.mkdir(parents=True, exist_ok=True)
        self.cpp_dir.mkdir(parents=True, exist_ok=True)
        compiler = Compiler(cache_dir=self.build_dir, cpp_dir=self.cpp_dir)
        binary = compiler.get_or_compile(cpp_code, self.log_prefix)

        # Prepare log directory
        self.log_dir.mkdir(exist_ok=True)

        # Launch swarm
        positions = self.initial_positions()
        swarm = SwarmProcess(binary_path=binary, num_nodes=len(positions))

        log_files: Dict[int, Any] = {}

        def _on_snapshot(snapshot: SwarmSnapshot) -> None:
            for ns in snapshot.nodes:
                nid, state = ns.node_id, ns.state_data
                if nid not in log_files:
                    path = self.log_dir / f"node_{nid}_{self.log_prefix}.log"
                    lf = open(path, "w")  # noqa: SIM115 — closed in the loop below
                    lf.write(self.log_header(nid, state))
                    log_files[nid] = lf
                log_files[nid].write(self.log_line(snapshot.round_number, nid, state))
            live = {ns.node_id for ns in snapshot.nodes}
            for gone in set(log_files) - live:
                log_files.pop(gone).close()

        swarm.add_listener(_on_snapshot)
        swarm.start()

        for nid, pos in positions.items():
            swarm.add_node_explicit(nid, pos)

        self.on_simulation_start()

        for round_num in range(num_rounds):
            swarm.step()
            self.on_round_complete(round_num, swarm.latest_snapshot())

        for lf in log_files.values():
            lf.close()

        swarm.close()
        self.on_simulation_end()
