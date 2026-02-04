PCAN_Auto app/ - PCAN-Explorer-like blueprint

This folder contains a minimal, extensible blueprint implementation of a
PCAN-Explorer-like application using python-can and PCAN-Basic. It is a
starting point for building multi-channel CAN/CAN FD tools with tracing,
decoding and plugin-based add-ins.

See `app/requirements.txt` for dependencies. The UI entrypoint is
`app/ui/main.py` (requires PySide6). The core backend is in
`app/core/can_backend.py`.
