"""Tests for AbstractExample toolchain bridge (Step E).

All tests mock the heavy pipeline components (Transpiler, Compiler, SwarmProcess,
AggregateValidator) to verify the run() lifecycle without a C++ toolchain.
"""

import pytest
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Type
from unittest.mock import MagicMock, call, patch

from fcpp_bridge.examples.abstract_example import AbstractExample
from fcpp_bridge.ipc.swarm_snapshot import SwarmSnapshot
from fcpp_bridge.ipc.node_state import NodeState


# ── Fake aggregate class ──────────────────────────────────────────────────────

class _FakeAggregate:
    """Stub @aggregate_function class used as aggregate_class in tests."""


# ── Concrete subclass used in every test ─────────────────────────────────────

class _ConcreteExample(AbstractExample):
    """Minimal concrete subclass with tracking hooks for lifecycle assertions."""

    def __init__(self, tmp_path: Path) -> None:
        self._tmp = tmp_path
        self.start_called = False
        self.end_called = False
        self.rounds_completed: list = []

    # required properties
    @property
    def aggregate_class(self) -> Type:
        return _FakeAggregate

    @property
    def log_prefix(self) -> str:
        return "test"

    # override directories to stay inside tmp_path
    @property
    def log_dir(self) -> Path:
        return self._tmp / "logs"

    @property
    def build_dir(self) -> Path:
        return self._tmp / "build"

    @property
    def cpp_dir(self) -> Path:
        return self._tmp / "cpp"

    def initial_positions(self) -> Dict[int, Tuple[float, ...]]:
        return {1: (0.0, 0.0), 2: (1.0, 0.0)}

    def log_header(self, node_id: int, state_data: Any) -> str:
        return f"# node {node_id}\n"

    def log_line(self, round_num: int, node_id: int, state_data: Any) -> str:
        return f"{round_num},{node_id},{state_data}\n"

    def on_simulation_start(self) -> None:
        self.start_called = True

    def on_simulation_end(self) -> None:
        self.end_called = True

    def on_round_complete(self, round_num: int, snapshot: Optional[SwarmSnapshot]) -> None:
        self.rounds_completed.append((round_num, snapshot))


# ── Shared mock-SwarmProcess factory ─────────────────────────────────────────

def _make_mock_swarm(nodes_per_step=None):
    """Return a mock SwarmProcess that fires _on_snapshot synchronously on step()."""
    if nodes_per_step is None:
        nodes_per_step = [
            NodeState(node_id=1, state_data={"v": 1}, timestamp=0.0),
            NodeState(node_id=2, state_data={"v": 2}, timestamp=0.0),
        ]

    mock_swarm = MagicMock()
    captured_listeners: list = []
    step_count = [0]

    def _add_listener(fn):
        captured_listeners.append(fn)
        return 0

    def _step():
        snap = SwarmSnapshot(
            round_number=step_count[0], time=float(step_count[0]), nodes=nodes_per_step
        )
        step_count[0] += 1
        for fn in captured_listeners:
            fn(snap)

    def _latest_snapshot():
        if step_count[0] == 0:
            return None
        return SwarmSnapshot(
            round_number=step_count[0] - 1,
            time=float(step_count[0] - 1),
            nodes=nodes_per_step,
        )

    mock_swarm.add_listener.side_effect = _add_listener
    mock_swarm.step.side_effect = _step
    mock_swarm.latest_snapshot.side_effect = _latest_snapshot
    return mock_swarm


# ── Shared patching context ───────────────────────────────────────────────────

def _run_with_mocks(example, num_rounds=2):
    """Call example.run() with all pipeline components mocked.

    Returns (mock_swarm, mock_validator, mock_transpiler_cls, mock_compiler_cls).
    """
    mock_swarm = _make_mock_swarm()
    fake_binary = Path("/tmp/fake_binary")

    with (
        patch("fcpp_bridge.python_dsl.validators.AggregateValidator.validate") as mv,
        patch("fcpp_bridge.transpiler.Transpiler") as mt_cls,
        patch("fcpp_bridge.compiler.Compiler") as mc_cls,
        patch("fcpp_bridge.ipc.swarm_process.SwarmProcess", return_value=mock_swarm),
    ):
        mt_cls.return_value.generate.return_value = "// fake cpp"
        mc_cls.return_value.get_or_compile.return_value = fake_binary

        example.run(num_rounds)

    return mock_swarm, mv, mt_cls, mc_cls


# ═══════════════════════════════════════════════════════════════════════════════
# Tests
# ═══════════════════════════════════════════════════════════════════════════════


def test_run_validates_aggregate_class(tmp_path):
    """AggregateValidator.validate is called with the aggregate_class."""
    ex = _ConcreteExample(tmp_path)
    _, mv, _, _ = _run_with_mocks(ex)
    mv.assert_called_once_with(_FakeAggregate)


def test_run_transpiles_aggregate_class(tmp_path):
    """Transpiler is constructed with aggregate_class and generate() is called."""
    ex = _ConcreteExample(tmp_path)
    _, _, mt_cls, _ = _run_with_mocks(ex)
    mt_cls.assert_called_once_with(_FakeAggregate)
    mt_cls.return_value.generate.assert_called_once()


def test_run_compiles_cpp_code(tmp_path):
    """Compiler.get_or_compile is called with (cpp_code, log_prefix)."""
    ex = _ConcreteExample(tmp_path)
    _, _, mt_cls, mc_cls = _run_with_mocks(ex)
    mc_cls.return_value.get_or_compile.assert_called_once_with(
        "// fake cpp", "test"
    )


def test_run_starts_swarm_process(tmp_path):
    """SwarmProcess.start() is called exactly once."""
    ex = _ConcreteExample(tmp_path)
    mock_swarm, _, _, _ = _run_with_mocks(ex)
    mock_swarm.start.assert_called_once()


def test_run_adds_nodes_from_initial_positions(tmp_path):
    """add_node_explicit is called once per position in initial_positions()."""
    ex = _ConcreteExample(tmp_path)
    mock_swarm, _, _, _ = _run_with_mocks(ex)
    assert mock_swarm.add_node_explicit.call_count == 2
    calls = {c.args for c in mock_swarm.add_node_explicit.call_args_list}
    assert (1, (0.0, 0.0)) in calls
    assert (2, (1.0, 0.0)) in calls


def test_run_calls_on_simulation_start(tmp_path):
    """on_simulation_start hook is called exactly once."""
    ex = _ConcreteExample(tmp_path)
    _run_with_mocks(ex)
    assert ex.start_called is True


def test_run_calls_on_simulation_end(tmp_path):
    """on_simulation_end hook is called exactly once."""
    ex = _ConcreteExample(tmp_path)
    _run_with_mocks(ex)
    assert ex.end_called is True


def test_run_step_count_matches_num_rounds(tmp_path):
    """swarm.step() is called exactly num_rounds times."""
    ex = _ConcreteExample(tmp_path)
    mock_swarm, _, _, _ = _run_with_mocks(ex, num_rounds=5)
    assert mock_swarm.step.call_count == 5


def test_run_on_round_complete_called_per_round(tmp_path):
    """on_round_complete is called once per round with the correct round_num."""
    ex = _ConcreteExample(tmp_path)
    _run_with_mocks(ex, num_rounds=3)
    round_nums = [r for r, _ in ex.rounds_completed]
    assert round_nums == [0, 1, 2]


def test_run_closes_swarm_on_completion(tmp_path):
    """swarm.close() is called after the round loop finishes."""
    ex = _ConcreteExample(tmp_path)
    mock_swarm, _, _, _ = _run_with_mocks(ex)
    mock_swarm.close.assert_called_once()
