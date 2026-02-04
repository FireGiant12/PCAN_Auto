# PCAN_Auto - Quick Start Guide

## Installation

```bash
# Clone the repository
git clone <repo-url>
cd PCAN_Auto

# Install dependencies
pip install -r requirements.txt
```

## Running Tests

```bash
# Quick smoke test (validates all core components)
python -m app.examples.smoke

# Full test suite with pytest
pytest tests/ -v

# Test with coverage report
pytest tests/ --cov=app --cov-report=html
```

## Basic Usage

### 1. Load Configuration

```python
from app.config import load_config

# Load from config.json or use defaults
config = load_config()
```

### 2. Create Bus Manager

```python
from app.core.can_backend import BusManager, ChannelConfig
from app.core.trace import CsvTracer

# Use context manager for automatic cleanup
with BusManager() as bus:
    # Open channels
    for ch_config in config.channels:
        cfg = ChannelConfig(**vars(ch_config))
        bus.open(cfg)
    
    # Start tracing
    with CsvTracer("trace.csv") as tracer:
        # Add listener to record messages
        bus.add_listener("PCAN_USBBUS1", 
            lambda msg: tracer.write("CH1", msg))
        
        # Do work...
        time.sleep(10)
```

### 3. Use Automation Runtime

```python
from app.automation.runtime import AutomationRuntime
from app.core.decoder.dbc_decoder import DbcDecoder

# Create runtime with decoders
decoder = DbcDecoder("database.dbc")
runtime = AutomationRuntime(bus, decoders=[decoder])

# Register RX handler
@runtime.on_rx
def handle_message(ctx):
    if ctx.decoded:
        print(f"Decoded: {ctx.decoded}")
    else:
        print(f"Raw ID: 0x{ctx.msg.arbitration_id:X}")

# Bind channel to runtime
runtime.bind_channel("PCAN_USBBUS1")
```

### 4. Send Messages

```python
# Send a CAN message
bus.send(
    channel="PCAN_USBBUS1",
    arbitration_id=0x123,
    data=b'\x01\x02\x03\x04',
    is_extended_id=False
)
```

## Configuration File

Create `config.json`:

```json
{
  "channels": [
    {
      "channel": "PCAN_USBBUS1",
      "bitrate": 500000,
      "fd": false,
      "listen_only": false
    }
  ],
  "log_level": "INFO",
  "log_file": "pcan_auto.log",
  "enable_trace": true,
  "trace_file": "trace.csv"
}
```

## Logging

```python
from app.logging_config import configure_logging
import logging

# Setup logging
configure_logging(log_level=logging.DEBUG)

# Get logger for your module
logger = logging.getLogger(__name__)
logger.info("Application started")
```

## Periodic Tasks

```python
from app.core.scheduler import PeriodicTask

def send_periodic_message():
    bus.send("PCAN_USBBUS1", 0x100, b'\x01\x02')

# Execute every 100ms
task = PeriodicTask(interval_ms=100, fn=send_periodic_message)
task.start()

# ... later ...
task.stop()
```

## Message Filtering

```python
from app.core.filters import IdFilter

# Create a filter for standard IDs 0x100-0x200
filter_obj = IdFilter(min_id=0x100, max_id=0x200, extended=False)
filter_dict = filter_obj.to_python_can()

# Apply to bus (if supported by interface)
bus.buses["PCAN_USBBUS1"].set_filters([filter_dict])
```

## Playback Recorded Traces

```python
from app.core.trace import CsvTracePlayer

player = CsvTracePlayer("trace.csv")
# Playback at 1x speed
player.play(bus, channel="PCAN_USBBUS1", loop=False, speed=1.0)
```

## UI Application

```bash
# Launch Qt-based UI (requires PySide6 and hardware)
python -m app.ui.main
```

## Environment Variables

Set configuration via environment variables:

```bash
# Windows
set PCAN_LOG_LEVEL=DEBUG
set PCAN_ENABLE_TRACE=true
set PCAN_CHANNELS=[{"channel":"PCAN_USBBUS1","bitrate":500000}]

# Linux/Mac
export PCAN_LOG_LEVEL=DEBUG
export PCAN_ENABLE_TRACE=true
export PCAN_CHANNELS='[{"channel":"PCAN_USBBUS1","bitrate":500000}]'
```

## Documentation

- [ANALYSIS.md](ANALYSIS.md) - Detailed analysis of improvements
- [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) - Summary of all changes
- [config.example.json](config.example.json) - Example configuration
- API documentation in docstrings

## Project Structure

```
PCAN_Auto/
├── app/
│   ├── core/              # Core CAN functionality
│   │   ├── can_backend.py # BusManager and ChannelConfig
│   │   ├── trace.py       # CSV trace recording/playback
│   │   ├── scheduler.py   # Periodic task scheduling
│   │   ├── filters.py     # CAN message filtering
│   │   └── decoder/       # Message decoders (DBC, .sym)
│   ├── automation/        # Event-driven automation
│   │   └── runtime.py     # AutomationRuntime
│   ├── ui/                # Qt-based UI (in progress)
│   ├── plugins/           # Extensible plugins
│   ├── examples/          # Example scripts
│   ├── config.py          # Configuration management
│   └── logging_config.py  # Logging setup
├── tests/                 # Unit tests
├── .github/workflows/     # CI/CD pipeline
├── config.example.json    # Example configuration
└── requirements.txt       # Python dependencies
```

## Troubleshooting

### No Hardware Connected
The framework works without hardware - messages won't be sent/received but the API is functional.

### Import Errors
Ensure PCAN_Auto is on your Python path:
```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
```

### Test Failures
Run smoke test first to validate setup:
```bash
python -m app.examples.smoke
```

### Logging Not Working
Ensure logging is configured before creating managers:
```python
from app.logging_config import configure_logging
configure_logging()  # Before creating BusManager
```

## Contributing

1. Run tests: `pytest tests/ -v`
2. Check code style: `flake8 app/`
3. Create feature branch and submit PR

## License

[Add your license here]

## Support

For issues and questions, see [ANALYSIS.md](ANALYSIS.md) and [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) for detailed technical information.
