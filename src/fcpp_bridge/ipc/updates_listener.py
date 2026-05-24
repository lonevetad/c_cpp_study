from typing import Callable

from .swarm_snapshot import SwarmSnapshot

# Callable type for receiving swarm state updates.
UpdatesListener = Callable[["SwarmSnapshot"], None]
