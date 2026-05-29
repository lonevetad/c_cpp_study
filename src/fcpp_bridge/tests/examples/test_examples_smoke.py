"""
Smoke tests for all fcpp_bridge example aggregate functions.

Each test validates and transpiles one @aggregate_function class.
No C++ compiler is required — only the Python DSL validator and transpiler.
"""

import pytest

from fcpp_bridge.python_dsl.validators import AggregateValidator
from fcpp_bridge.transpiler import Transpiler


def _smoke(cls) -> None:
    """Validate + transpile *cls*; assert both complete without exception."""
    AggregateValidator.validate(cls)
    code = Transpiler(cls).generate()
    assert isinstance(code, str) and len(code) > 0


def test_spreading_collection_smoke():
    from fcpp_bridge.examples.spreading_collection import SpreadingCollectionAggregate
    _smoke(SpreadingCollectionAggregate)


def test_chain_decaying_smoke():
    from fcpp_bridge.examples.chain_decaying import ChainDecayingAggregate
    _smoke(ChainDecayingAggregate)


def test_channel_broadcast_smoke():
    from fcpp_bridge.examples.channel_broadcast import ChannelBroadcastAggregate
    _smoke(ChannelBroadcastAggregate)


def test_collection_compare_smoke():
    from fcpp_bridge.examples.collection_compare import CollectionCompareAggregate
    _smoke(CollectionCompareAggregate)


def test_message_dispatch_smoke():
    from fcpp_bridge.examples.message_dispatch import MessageDispatchAggregate
    _smoke(MessageDispatchAggregate)


def test_worker_role_smoke():
    from fcpp_bridge.examples.worker_role_assignment import WorkerRoleAggregate
    _smoke(WorkerRoleAggregate)


def test_communication_roles_smoke():
    from fcpp_bridge.examples.communication_roles_assignment import CommunicationRolesAggregate
    _smoke(CommunicationRolesAggregate)


def test_scattered_database_smoke():
    from fcpp_bridge.examples.scattered_database import ScatteredDBAggregate
    _smoke(ScatteredDBAggregate)


def test_area_discovery_smoke():
    from fcpp_bridge.examples.area_discovery import AreaDiscoveryAggregate
    _smoke(AreaDiscoveryAggregate)


def test_iteratively_area_discovery_smoke():
    from fcpp_bridge.examples.iteratively_area_discovery import IterAreaDiscoveryAggregate
    _smoke(IterAreaDiscoveryAggregate)
