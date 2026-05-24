import json
import threading
from typing import Any, Callable, Dict, Optional

from .ipc_backend import IpcBackend
from .node_state import NodeState
from .swarm_snapshot import SwarmSnapshot


class GrpcBackend(IpcBackend):
    """gRPC backend for streaming state updates."""

    def __init__(self, host: str = "localhost", port: int = 50051, timeout: float = 5.0):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.channel = None
        self.stub = None
        self._stream_thread: Optional[threading.Thread] = None
        self._stream_running = False
        self._connect()

    def _connect(self) -> None:
        """Open gRPC channel and create service stub."""
        try:
            import grpc

            self.channel = grpc.insecure_channel(f"{self.host}:{self.port}")

            try:
                from fcpp_bridge.ipc import (  # type: ignore[attr-defined]
                    fcpp_swarm_pb2_grpc as _grpc_stub,
                )
                self.stub = _grpc_stub.SwarmServiceStub(self.channel)
            except ImportError:
                self.stub = None

        except ImportError:
            raise RuntimeError(
                "grpcio not installed. Install with: pip install grpcio grpcio-tools"
            )

    def _require_stub(self) -> None:
        if self.stub is None:
            raise RuntimeError(
                "gRPC stubs not generated. Run:\n"
                "  python -m grpc_tools.protoc "
                "-I src/fcpp_bridge/ipc "
                "--python_out=src/fcpp_bridge/ipc "
                "--grpc_python_out=src/fcpp_bridge/ipc "
                "src/fcpp_bridge/ipc/fcpp_swarm.proto"
            )

    def send_command(self, cmd: Dict[str, Any]) -> Dict[str, Any]:
        """Send a control command to the swarm via gRPC."""
        self._require_stub()

        try:
            from fcpp_bridge.ipc import fcpp_swarm_pb2 as _pb2  # type: ignore[attr-defined]

            request = _pb2.CommandRequest(
                cmd=cmd.get("cmd", ""),
                count=cmd.get("count", 0),
                data=json.dumps(cmd).encode() if cmd else b"",
            )
            response = self.stub.SendCommand(request, timeout=self.timeout)
            result = {"success": response.success, "message": response.message}
            if response.data:
                result.update(json.loads(response.data))
            return result
        except Exception as e:
            raise RuntimeError(f"gRPC send_command failed: {e}") from e

    def get_state(self) -> SwarmSnapshot:
        """Retrieve the current swarm state via gRPC unary call."""
        self._require_stub()

        try:
            from fcpp_bridge.ipc import fcpp_swarm_pb2 as _pb2  # type: ignore[attr-defined]

            request = _pb2.StateRequest(from_round=0)
            response = self.stub.GetState(request, timeout=self.timeout)
            return self._proto_to_snapshot(response)
        except Exception as e:
            raise RuntimeError(f"gRPC get_state failed: {e}") from e

    def subscribe_state_updates(
        self, callback: Callable[[SwarmSnapshot], None]
    ) -> None:
        """Start a background thread that streams state updates via gRPC."""
        self._require_stub()

        def _stream() -> None:
            try:
                from fcpp_bridge.ipc import fcpp_swarm_pb2 as _pb2  # type: ignore[attr-defined]

                request = _pb2.StateRequest(from_round=0)
                for response in self.stub.StreamState(request):
                    if not self._stream_running:
                        break
                    callback(self._proto_to_snapshot(response))
            except Exception:
                pass

        self._stream_running = True
        self._stream_thread = threading.Thread(target=_stream, daemon=True)
        self._stream_thread.start()

    def _proto_to_snapshot(self, response: Any) -> SwarmSnapshot:
        """Convert a SwarmStateResponse protobuf message to a SwarmSnapshot."""
        nodes = []
        for n in response.nodes:
            try:
                state_data = json.loads(n.state_json) if n.state_json else None
            except (json.JSONDecodeError, ValueError):
                state_data = n.state_json
            nodes.append(NodeState(
                node_id=n.id,
                state_data=state_data,
                timestamp=n.timestamp,
            ))
        return SwarmSnapshot(
            round_number=response.round_number,
            time=response.sim_time,
            nodes=nodes,
        )

    def close(self) -> None:
        """Stop streaming thread and close gRPC channel."""
        self._stream_running = False
        if self._stream_thread and self._stream_thread.is_alive():
            self._stream_thread.join(timeout=2.0)
        if self.channel:
            self.channel.close()
            self.channel = None
