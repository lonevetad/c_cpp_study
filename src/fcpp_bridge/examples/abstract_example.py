"""AbstractExample — base class for fcpp_bridge demo simulations.

Every main example subclasses ``AbstractExample`` and overrides the abstract
methods listed below.  The concrete ``run()`` method handles:

- Creating the log directory.
- Calling ``initial_positions()`` and ``initial_states()`` once before the loop.
- Iterating over rounds, calling ``round_step()`` each time.
- Managing per-node log files: opening a file when a node appears in the states
  dict for the first time, closing it when the node leaves the dict.
- Calling the optional hook methods at the appropriate points.

Nodes are represented throughout as ``dict[int, state]`` keys — there is no
fixed "number of nodes" constant.  A node joins the simulation when its ID
is added to the dict returned by ``round_step``; it leaves when its ID is
absent from the returned dict.  This makes dynamic swarm scenarios (join /
leave / failure) a first-class concept rather than an afterthought.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Tuple


class AbstractExample(ABC):
    """Template Method base class for fcpp_bridge demo simulations.

    Subclasses implement the algorithm-specific methods; ``run()`` provides
    the common simulation loop and log-file lifecycle.

    Required overrides
    ------------------
    log_prefix          str property — used in log file names
    initial_positions() → dict[int, tuple]   — starting (x, y) per node
    initial_states(positions) → dict[int, Any] — starting state per node
    round_step(round_num, positions, states) → (positions, states)
    log_header(node_id, state) → str         — CSV header line
    log_line(round_num, node_id, state) → str — one CSV data line

    Optional hooks
    --------------
    on_simulation_start()                    — open extra log files
    on_simulation_end()                      — close extra log files, print summary
    on_round_complete(round_num, pos, states) — write extra per-round data
    """

    # ── Required properties / abstract methods ────────────────────────────────

    @property
    @abstractmethod
    def log_prefix(self) -> str:
        """Suffix used in node log file names: ``node_<id>_<log_prefix>.log``."""

    @property
    def log_dir(self) -> Path:
        """Directory for log files.  Default: ``examples/logs/``."""
        return Path(__file__).parent / "logs"

    @abstractmethod
    def initial_positions(self) -> Dict[int, Tuple[float, ...]]:
        """Return ``{node_id: (x, y)}`` for every node in the initial swarm.

        The keys of this dict define the initial node set.  There is no
        requirement that IDs are consecutive or start from zero.
        """

    @abstractmethod
    def initial_states(self, positions: Dict[int, Tuple[float, ...]]) -> Dict[int, Any]:
        """Return the initial state for every node given their positions.

        ``positions`` is the dict returned by ``initial_positions()``.  It is
        provided so states that depend on spatial layout (e.g. role assignment
        based on distance to a target) can be initialised correctly.

        Returns ``{node_id: state}`` for every node_id in *positions*.
        """

    @abstractmethod
    def round_step(
        self,
        round_num: int,
        positions: Dict[int, Tuple[float, ...]],
        states: Dict[int, Any],
    ) -> Tuple[Dict[int, Tuple[float, ...]], Dict[int, Any]]:
        """Execute one simulation round.

        Parameters
        ----------
        round_num:
            Zero-based round index.
        positions:
            Current ``{node_id: (x, y)}`` dict.
        states:
            Current ``{node_id: state}`` dict.

        Returns
        -------
        (new_positions, new_states)
            New positions and states after this round.  Nodes may be added to
            or removed from the returned dicts to simulate join / leave events.
        """

    @abstractmethod
    def log_header(self, node_id: int, state: Any) -> str:
        """Return the CSV header line for *node_id*'s log file.

        Called once when a node's log file is first opened.  The returned
        string should end with ``\\n``.  Lines starting with ``#`` are treated
        as comments by most CSV readers.
        """

    @abstractmethod
    def log_line(self, round_num: int, node_id: int, state: Any) -> str:
        """Return one CSV data line for *round_num* / *node_id*.

        Called every round for every node that is currently active.  The
        returned string should end with ``\\n``.
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
        positions: Dict[int, Tuple[float, ...]],
        states: Dict[int, Any],
    ) -> None:
        """Hook called after per-node log lines are written for this round.

        Use this to write round-level aggregates, receiver message logs, or
        any data that is not per-node.
        """

    # ── Concrete simulation driver ────────────────────────────────────────────

    def run(self, num_rounds: int) -> None:
        """Execute the simulation and write per-node log files.

        For each round:
        1. ``round_step()`` is called to advance the simulation.
        2. For every node in the returned states:
           - If it is new, its log file is opened and the header is written.
           - A data line is appended.
        3. Nodes that were active last round but are absent from the new states
           dict have their log files closed (they left the simulation).
        4. ``on_round_complete()`` is called.

        After all rounds, remaining open log files are closed and
        ``on_simulation_end()`` is called.
        """
        log_dir = self.log_dir
        log_dir.mkdir(exist_ok=True)

        self.on_simulation_start()

        positions = self.initial_positions()
        states = self.initial_states(positions)
        log_files: Dict[int, Any] = {}

        for round_num in range(num_rounds):
            positions, states = self.round_step(round_num, positions, states)

            for node_id in sorted(states):
                state = states[node_id]
                if node_id not in log_files:
                    path = log_dir / f"node_{node_id}_{self.log_prefix}.log"
                    lf = open(path, "w")  # noqa: SIM115 — closed in the loop below
                    lf.write(self.log_header(node_id, state))
                    log_files[node_id] = lf
                log_files[node_id].write(self.log_line(round_num, node_id, state))

            # Close files for nodes that left the simulation this round
            for node_id in set(log_files) - set(states):
                log_files.pop(node_id).close()

            self.on_round_complete(round_num, positions, states)

        for lf in log_files.values():
            lf.close()

        self.on_simulation_end()
