"""Smoke test for PCAN_Auto core components.

This script validates basic functionality without requiring hardware.
Useful for import/syntax checks and basic integration testing.
"""

import tempfile
import os
import sys
import logging
from pathlib import Path

# Ensure app root is on path
p = Path(__file__).resolve().parents[2]
if str(p) not in sys.path:
    sys.path.insert(0, str(p))

from app.core.can_backend import BusManager, ChannelConfig
from app.core.trace import CsvTracer, CsvTracePlayer
from app.core.scheduler import PeriodicTask
from app.core.filters import IdFilter
from app.automation.runtime import AutomationRuntime
from app.logging_config import configure_logging
from app.config import create_default_config
import can


def test_imports():
    """Verify all core modules import correctly."""
    print("✓ All imports successful")


def test_channel_config():
    """Test ChannelConfig validation."""
    # Valid config
    cfg = ChannelConfig(channel="TEST", bitrate=500000)
    assert cfg.bitrate == 500000
    
    # Invalid configs
    try:
        ChannelConfig(channel="", bitrate=500000)
        assert False, "Should reject empty channel"
    except ValueError:
        pass
    
    try:
        ChannelConfig(channel="TEST", bitrate=0)
        assert False, "Should reject zero bitrate"
    except ValueError:
        pass
    
    print("✓ ChannelConfig validation working")


def test_bus_manager():
    """Test BusManager initialization and context manager."""
    with BusManager() as bus:
        assert len(bus.buses) == 0
        assert len(bus.listeners) == 0
    print("✓ BusManager context manager working")


def test_csv_tracer():
    """Test CsvTracer file operations."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "test_trace.csv")
        
        # Write trace
        with CsvTracer(path) as tracer:
            # Create a mock message
            msg = can.Message(
                arbitration_id=0x123,
                data=b'\x01\x02\x03\x04\x05\x06\x07\x08',
                timestamp=1234567890.0
            )
            tracer.write("TEST_CH", msg)
        
        # Verify file was created
        assert os.path.exists(path)
        
        # Verify contents
        with open(path) as f:
            lines = f.readlines()
            assert len(lines) == 2  # Header + message
            assert "0x123" in lines[1]
            assert "0102030405060708" in lines[1]
    
    print("✓ CsvTracer working")


def test_periodic_task():
    """Test PeriodicTask execution."""
    counter = {"count": 0}
    
    def increment():
        counter["count"] += 1
    
    # Validate invalid intervals
    try:
        PeriodicTask(interval_ms=0, fn=increment)
        assert False, "Should reject zero interval"
    except ValueError:
        pass
    
    # Test valid task
    task = PeriodicTask(interval_ms=50, fn=increment)
    task.start()
    
    import time
    time.sleep(0.2)
    task.stop()
    
    assert counter["count"] >= 3, f"Expected at least 3 executions, got {counter['count']}"
    print(f"✓ PeriodicTask working ({counter['count']} executions)")


def test_id_filter():
    """Test IdFilter validation and conversion."""
    # Valid filter
    f = IdFilter(min_id=0x100, max_id=0x200, extended=False)
    result = f.to_python_can()
    assert "can_id" in result
    assert "can_mask" in result
    
    # Invalid filters
    try:
        IdFilter(min_id=0x200, max_id=0x100)
        assert False, "Should reject max < min"
    except ValueError:
        pass
    
    try:
        IdFilter(min_id=-1, max_id=100)
        assert False, "Should reject negative ID"
    except ValueError:
        pass
    
    print("✓ IdFilter working")


def test_automation_runtime():
    """Test AutomationRuntime handler registration."""
    bus = BusManager()
    runtime = AutomationRuntime(bus, decoders=[])
    
    handler_called = {"count": 0}
    
    @runtime.on_rx
    def my_handler(ctx):
        handler_called["count"] += 1
    
    assert len(runtime.handlers["on_rx"]) == 1
    
    # Simulate message dispatch
    msg = can.Message(arbitration_id=0x100, data=b'\x01\x02')
    runtime._rx_dispatch(msg)
    
    assert handler_called["count"] == 1
    print("✓ AutomationRuntime working")


def test_configuration():
    """Test configuration system."""
    config = create_default_config()
    assert len(config.channels) > 0
    assert config.log_level == "INFO"
    
    # Test serialization
    config_dict = config.to_dict()
    assert "channels" in config_dict
    
    print("✓ Configuration system working")


def smoke():
    """Run all smoke tests."""
    configure_logging(log_level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    logger.info("=" * 60)
    logger.info("PCAN_Auto Smoke Test Suite")
    logger.info("=" * 60)
    
    tests = [
        ("Imports", test_imports),
        ("ChannelConfig", test_channel_config),
        ("BusManager", test_bus_manager),
        ("CsvTracer", test_csv_tracer),
        ("PeriodicTask", test_periodic_task),
        ("IdFilter", test_id_filter),
        ("AutomationRuntime", test_automation_runtime),
        ("Configuration", test_configuration),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_fn in tests:
        try:
            logger.info(f"\nTesting {name}...")
            test_fn()
            passed += 1
        except Exception as e:
            logger.error(f"✗ {name} failed: {e}", exc_info=True)
            failed += 1
    
    logger.info("\n" + "=" * 60)
    logger.info(f"Results: {passed} passed, {failed} failed")
    logger.info("=" * 60)
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(smoke())
