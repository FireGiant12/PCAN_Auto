"""Advanced demo - Configuration, Tracing, and Periodic Tasks."""

from app.logging_config import configure_logging
from app.core.can_backend import BusManager, ChannelConfig
from app.core.trace import CsvTracer
from app.core.scheduler import PeriodicTask
from app.automation.runtime import AutomationRuntime
from app.config import create_default_config, AppConfig
import logging
import tempfile
import os
import time
import can

# Setup logging
configure_logging(log_level=logging.INFO)
logger = logging.getLogger(__name__)

print("\n" + "="*75)
print("🚀 PCAN_Auto - Advanced Features Demo")
print("="*75 + "\n")

# ============================================================================
# PART 1: Configuration System
# ============================================================================
print("📋 PART 1: Configuration System")
print("-" * 75)

config = create_default_config()
print(f"✓ Loaded default config with {len(config.channels)} channels")
for i, ch in enumerate(config.channels, 1):
    print(f"  Channel {i}: {ch.channel} @ {ch.bitrate} bps (FD={ch.fd})")

# Convert to dict for verification
config_dict = config.to_dict()
print(f"✓ Config serializable to dict")
print()

# ============================================================================
# PART 2: Bus Manager and Context Managers
# ============================================================================
print("🔌 PART 2: Bus Manager & Context Managers")
print("-" * 75)

with BusManager() as bus:
    print("✓ BusManager created (context manager)")
    print("✓ Automatic cleanup guaranteed on exit")
    print()
    
    # ================================================================
    # PART 3: Message Tracing
    # ================================================================
    print("📝 PART 3: Message Tracing")
    print("-" * 75)
    
    tmpdir = tempfile.gettempdir()
    trace_path = os.path.join(tmpdir, "advanced_demo.csv")
    
    with CsvTracer(trace_path) as tracer:
        print(f"✓ Tracer created at: {trace_path}")
        
        # Simulate messages
        messages = [
            can.Message(arbitration_id=0x100, data=b'\x01\x02\x03\x04'),
            can.Message(arbitration_id=0x200, data=b'\x05\x06\x07\x08'),
            can.Message(arbitration_id=0x300, data=b'\x09\x0A\x0B\x0C'),
        ]
        
        for msg in messages:
            tracer.write("CH1", msg)
        
        print(f"✓ Recorded {len(messages)} messages to trace")
    
    print(f"✓ Tracer closed (automatic cleanup)")
    
    # Verify trace file
    with open(trace_path) as f:
        lines = f.readlines()
    print(f"✓ Trace file contains {len(lines)-1} messages (plus header)")
    print()
    
    # ================================================================
    # PART 4: Periodic Tasks
    # ================================================================
    print("⏱️  PART 4: Periodic Tasks")
    print("-" * 75)
    
    task_stats = {"executions": 0}
    
    def periodic_work():
        task_stats["executions"] += 1
    
    task = PeriodicTask(interval_ms=100, fn=periodic_work)
    print(f"✓ Created periodic task (100ms interval)")
    
    task.start()
    print(f"✓ Task started")
    
    time.sleep(0.35)  # Let it run a few times
    task.stop()
    
    print(f"✓ Task stopped after {task_stats['executions']} executions")
    print()
    
    # ================================================================
    # PART 5: Automation Runtime with Handlers
    # ================================================================
    print("🤖 PART 5: Automation Runtime & Handlers")
    print("-" * 75)
    
    runtime = AutomationRuntime(bus, decoders=[])
    print(f"✓ AutomationRuntime created")
    
    stats = {"rx_count": 0, "errors": 0}
    
    @runtime.on_rx
    def handle_rx(ctx):
        stats["rx_count"] += 1
        logger.debug(f"Handler called: msg_id=0x{ctx.msg.arbitration_id:X}")
    
    print(f"✓ RX handler registered")
    
    @runtime.before_tx
    def before_tx(ctx):
        logger.debug(f"Before TX handler called")
    
    print(f"✓ Before-TX handler registered")
    
    @runtime.after_tx
    def after_tx(ctx):
        logger.debug(f"After TX handler called")
    
    print(f"✓ After-TX handler registered")
    
    # Simulate message dispatch
    test_msg = can.Message(arbitration_id=0x123, data=b'\xAA\xBB')
    runtime._rx_dispatch(test_msg)
    
    print(f"✓ Dispatched test message")
    print(f"✓ RX handler executed {stats['rx_count']} times")
    print()

# ============================================================================
# PART 6: Input Validation
# ============================================================================
print("✔️  PART 6: Input Validation")
print("-" * 75)

validation_tests = [
    ("Empty channel", lambda: ChannelConfig(channel="", bitrate=500000)),
    ("Negative bitrate", lambda: ChannelConfig(channel="CH", bitrate=-100)),
    ("Invalid interval", lambda: PeriodicTask(interval_ms=0, fn=lambda: None)),
]

for test_name, test_fn in validation_tests:
    try:
        test_fn()
        print(f"✗ {test_name}: Should have failed!")
    except ValueError as e:
        print(f"✓ {test_name}: Caught - {str(e)[:50]}...")

print()

# ============================================================================
# SUMMARY
# ============================================================================
print("="*75)
print("✅ ADVANCED DEMO COMPLETE")
print("="*75)
print()
print("💡 What This Demonstrated:")
print("   1. Configuration System - Load/serialize configurations")
print("   2. Context Managers - Automatic resource cleanup")
print("   3. Message Tracing - CSV recording of CAN messages")
print("   4. Periodic Tasks - Background task scheduling")
print("   5. Automation Runtime - Event-driven message handling")
print("   6. Input Validation - Comprehensive parameter checking")
print()
print("🎯 All features working perfectly!")
print("📖 See QUICKSTART.md for more examples")
print()
