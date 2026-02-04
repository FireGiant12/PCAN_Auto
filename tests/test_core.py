"""Unit tests for PCAN_Auto core modules."""

import pytest
import tempfile
import os
from unittest.mock import Mock, MagicMock, patch
import can

from app.core.can_backend import BusManager, ChannelConfig
from app.core.trace import CsvTracer, CsvTracePlayer
from app.core.scheduler import PeriodicTask
from app.core.filters import IdFilter
from app.automation.runtime import AutomationRuntime
from app.core.decoder.dbc_decoder import DbcDecoder


class TestChannelConfig:
    """Tests for ChannelConfig validation."""
    
    def test_valid_config(self):
        """Test valid channel configuration."""
        cfg = ChannelConfig(channel="PCAN_USBBUS1", bitrate=500000)
        assert cfg.channel == "PCAN_USBBUS1"
        assert cfg.bitrate == 500000
    
    def test_invalid_channel_empty(self):
        """Test that empty channel raises ValueError."""
        with pytest.raises(ValueError):
            ChannelConfig(channel="")
    
    def test_invalid_channel_none(self):
        """Test that None channel raises ValueError."""
        with pytest.raises(ValueError):
            ChannelConfig(channel=None)
    
    def test_invalid_bitrate_zero(self):
        """Test that zero bitrate raises ValueError."""
        with pytest.raises(ValueError):
            ChannelConfig(channel="CH1", bitrate=0)
    
    def test_invalid_bitrate_negative(self):
        """Test that negative bitrate raises ValueError."""
        with pytest.raises(ValueError):
            ChannelConfig(channel="CH1", bitrate=-100)
    
    def test_invalid_data_bitrate(self):
        """Test that invalid data bitrate raises ValueError."""
        with pytest.raises(ValueError):
            ChannelConfig(channel="CH1", fd=True, data_bitrate=-1000)


class TestCsvTracer:
    """Tests for CsvTracer."""
    
    def test_context_manager(self):
        """Test context manager interface."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "trace.csv")
            with CsvTracer(path) as tracer:
                assert os.path.exists(path)
            # File should still exist after close
            assert os.path.exists(path)
    
    def test_write_message(self):
        """Test writing a CAN message to trace."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "trace.csv")
            with CsvTracer(path) as tracer:
                msg = can.Message(arbitration_id=0x123, data=b'\x01\x02\x03')
                tracer.write("CH1", msg)
            
            # Verify file contents
            with open(path) as f:
                lines = f.readlines()
                assert len(lines) == 2  # Header + 1 message
                assert "0x123" in lines[1]
                assert "010203" in lines[1]


class TestIdFilter:
    """Tests for IdFilter."""
    
    def test_valid_range(self):
        """Test valid ID range."""
        f = IdFilter(min_id=0x100, max_id=0x200)
        assert f.min_id == 0x100
        assert f.max_id == 0x200
    
    def test_invalid_range(self):
        """Test that max_id < min_id raises ValueError."""
        with pytest.raises(ValueError):
            IdFilter(min_id=0x200, max_id=0x100)
    
    def test_negative_min_id(self):
        """Test that negative min_id raises ValueError."""
        with pytest.raises(ValueError):
            IdFilter(min_id=-1, max_id=100)
    
    def test_standard_id_bounds(self):
        """Test standard ID bounds validation."""
        with pytest.raises(ValueError):
            IdFilter(min_id=0x700, max_id=0x800, extended=False)
    
    def test_extended_id_bounds(self):
        """Test extended ID bounds validation."""
        with pytest.raises(ValueError):
            IdFilter(min_id=0x1FFFFFFE, max_id=0x20000000, extended=True)
    
    def test_to_python_can_exact_match(self):
        """Test filter conversion for single ID."""
        f = IdFilter(min_id=0x100, max_id=0x100)
        result = f.to_python_can()
        assert result["can_id"] == 0x100


class TestPeriodicTask:
    """Tests for PeriodicTask."""
    
    def test_invalid_interval_zero(self):
        """Test that zero interval raises ValueError."""
        with pytest.raises(ValueError):
            PeriodicTask(interval_ms=0, fn=lambda: None)
    
    def test_invalid_interval_negative(self):
        """Test that negative interval raises ValueError."""
        with pytest.raises(ValueError):
            PeriodicTask(interval_ms=-100, fn=lambda: None)
    
    def test_valid_task_creation(self):
        """Test valid periodic task creation."""
        counter = Mock()
        task = PeriodicTask(interval_ms=100, fn=counter)
        task.start()
        # Give it a moment to execute at least once
        import time
        time.sleep(0.2)
        task.stop()
        assert counter.call_count >= 1


class TestAutomationRuntime:
    """Tests for AutomationRuntime."""
    
    def test_initialization(self):
        """Test runtime initialization."""
        bus_mgr = Mock()
        decoders = []
        runtime = AutomationRuntime(bus_mgr, decoders)
        assert runtime.bus_mgr == bus_mgr
        assert runtime.decoders == decoders
    
    def test_handler_registration(self):
        """Test registering RX handlers."""
        bus_mgr = Mock()
        runtime = AutomationRuntime(bus_mgr)
        
        handler = Mock()
        runtime.on_rx(handler)
        
        assert handler in runtime.handlers["on_rx"]
    
    def test_rx_dispatch_with_decoder(self):
        """Test RX dispatch with message decoding."""
        bus_mgr = Mock()
        decoder = Mock()
        decoder.decode.return_value = {"signal": 42}
        
        runtime = AutomationRuntime(bus_mgr, [decoder])
        handler = Mock()
        runtime.on_rx(handler)
        
        msg = can.Message(arbitration_id=0x100, data=b'\x01\x02')
        runtime._rx_dispatch(msg)
        
        handler.assert_called_once()
        ctx = handler.call_args[0][0]
        assert ctx.msg == msg
        assert ctx.decoded == {"signal": 42}


class TestBusManager:
    """Tests for BusManager."""
    
    def test_context_manager(self):
        """Test context manager interface."""
        with BusManager() as mgr:
            assert isinstance(mgr, BusManager)
    
    def test_initialization(self):
        """Test manager initialization."""
        mgr = BusManager()
        assert len(mgr.buses) == 0
        assert len(mgr.listeners) == 0


class TestIntegration:
    """Integration tests."""
    
    def test_trace_roundtrip(self):
        """Test writing and reading trace file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            trace_path = os.path.join(tmpdir, "test.csv")
            
            # Write trace
            with CsvTracer(trace_path) as tracer:
                for i in range(3):
                    msg = can.Message(
                        arbitration_id=0x100 + i,
                        data=bytes([i, i+1, i+2])
                    )
                    tracer.write("CH1", msg)
            
            # Read trace
            with open(trace_path) as f:
                lines = f.readlines()
                assert len(lines) == 4  # Header + 3 messages


# Run with: pytest tests/test_core.py
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
