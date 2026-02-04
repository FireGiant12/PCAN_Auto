"""PCAN_Auto UI - Qt-based CAN message viewer and automation interface."""

import sys
import logging
import time
from PySide6.QtCore import Qt, QObject, Signal
from PySide6.QtGui import QAction, QFont
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QSplitter,
    QStatusBar,
    QTableView,
    QToolBar,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtGui import QStandardItemModel, QStandardItem
from app.core.can_backend import BusManager, ChannelConfig
from app.automation.runtime import AutomationRuntime
from app.logging_config import configure_logging

logger = logging.getLogger(__name__)


class MessageBridge(QObject):
    """Thread-safe bridge to deliver CAN messages to the UI thread."""

    received = Signal(dict)


class MainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PCAN_Auto - CAN Explorer")
        self.setGeometry(80, 80, 1400, 860)
        self.setMinimumSize(1200, 760)
        
        self.bus_manager = BusManager()
        self.runtime = AutomationRuntime(self.bus_manager, decoders=[])
        self.message_bridge = MessageBridge()
        self.message_bridge.received.connect(self._append_message_row)
        self.connected_channel = None

        self._apply_theme()
        self._create_toolbar()
        self._build_ui()

        logger.info("MainWindow initialized")

    def closeEvent(self, event):
        """Handle application close."""
        logger.info("Closing application")
        self.bus_manager.stop()
        event.accept()

    def _apply_theme(self):
        """Apply a vibrant, modern theme for a PCAN-style UI."""
        self.setStyleSheet(
            """
            QMainWindow { background-color: #0e1116; }
            QWidget { color: #e6edf3; font-size: 12px; }

            QToolBar { background: #0f141b; border: 0px; spacing: 6px; padding: 6px; }
            QToolButton { background: #1b2430; border: 1px solid #263244; padding: 6px 10px; border-radius: 6px; }
            QToolButton:hover { background: #243145; border: 1px solid #3a4b66; }
            QToolButton:pressed { background: #1a2536; }

            QGroupBox { border: 1px solid #243145; border-radius: 8px; margin-top: 8px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; color: #9db5d1; }

            QLineEdit, QComboBox, QSpinBox { background: #111720; border: 1px solid #253247; border-radius: 6px; padding: 6px; }
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus { border: 1px solid #37b6ff; }

            QPushButton { background: #1b6ef3; border: 0px; padding: 8px 12px; border-radius: 6px; font-weight: 600; }
            QPushButton:hover { background: #2c7bff; }
            QPushButton:pressed { background: #165ac7; }

            QTableView { background: #0f141b; gridline-color: #1f2a3b; border: 1px solid #1f2a3b; }
            QHeaderView::section { background: #1a2230; color: #c5d3e6; padding: 6px; border: 0px; }
            QTableView::item { padding: 6px; }
            QTableView::item:selected { background: #2a3a54; color: #ffffff; }

            QCheckBox::indicator { width: 16px; height: 16px; }
            QCheckBox::indicator:unchecked { border: 1px solid #3b4b63; background: #0f141b; border-radius: 3px; }
            QCheckBox::indicator:checked { border: 1px solid #3b4b63; background: #37b6ff; border-radius: 3px; }

            QStatusBar { background: #0f141b; color: #8fa6c1; border-top: 1px solid #1f2a3b; }
            """
        )

    def _create_toolbar(self):
        """Create toolbar actions for quick access."""
        toolbar = QToolBar("Main")
        toolbar.setMovable(False)
        self.addToolBar(Qt.TopToolBarArea, toolbar)

        actions = [
            ("Connect", "Connect to selected channel", self._connect_channel),
            ("Disconnect", "Disconnect current channel", self._disconnect_channel),
            ("Refresh", "Detect CAN devices", self._refresh_channels),
            ("Start Trace", "Start recording CAN traffic", None),
            ("Stop Trace", "Stop recording", None),
            ("Play", "Playback a trace", None),
        ]

        for name, tip, handler in actions:
            action = QAction(name, self)
            action.setToolTip(tip)
            if handler:
                action.triggered.connect(handler)
            toolbar.addAction(action)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        toolbar.addWidget(spacer)

        live_badge = QLabel("LIVE")
        live_badge.setAlignment(Qt.AlignCenter)
        live_badge.setStyleSheet(
            "background: #15d38d; color: #08131a; font-weight: 700; padding: 4px 8px; border-radius: 6px;"
        )
        toolbar.addWidget(live_badge)

    def _build_ui(self):
        """Build the main layout with split panels."""
        container = QWidget()
        root_layout = QVBoxLayout(container)
        root_layout.setContentsMargins(10, 10, 10, 10)
        root_layout.setSpacing(10)

        header = self._build_header()
        root_layout.addWidget(header)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self._build_channel_panel())
        splitter.addWidget(self._build_message_panel())
        splitter.addWidget(self._build_detail_panel())
        splitter.setSizes([260, 780, 320])
        splitter.setHandleWidth(6)
        root_layout.addWidget(splitter)

        self.setCentralWidget(container)
        self.setStatusBar(self._build_status_bar())
        self._refresh_channels()

    def _build_header(self):
        header = QFrame()
        layout = QHBoxLayout(header)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(12)

        title = QLabel("PCAN_Auto Explorer")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title.setStyleSheet("color: #eaf2ff;")

        subtitle = QLabel("High-performance CAN monitoring and automation")
        subtitle.setStyleSheet("color: #8aa4c2;")

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addStretch(1)

        quick_filter = QLineEdit()
        quick_filter.setPlaceholderText("Filter by ID, channel, or data...")
        quick_filter.setMinimumWidth(280)
        layout.addWidget(quick_filter)

        return header

    def _build_channel_panel(self):
        panel = QGroupBox("Channels")
        layout = QVBoxLayout(panel)
        layout.setSpacing(10)

        self.channel_select = QComboBox()
        self.channel_select.setMinimumWidth(200)

        self.bitrate = QComboBox()
        self.bitrate.addItems(["125000", "250000", "500000", "1000000"])
        self.bitrate.setCurrentText("500000")

        self.fd_enabled = QCheckBox("Enable CAN-FD")
        self.data_bitrate = QComboBox()
        self.data_bitrate.addItems(["2000000", "4000000", "8000000"])
        self.data_bitrate.setCurrentText("2000000")

        layout.addWidget(QLabel("Channel"))
        layout.addWidget(self.channel_select)
        layout.addWidget(QLabel("Bitrate"))
        layout.addWidget(self.bitrate)
        layout.addWidget(self.fd_enabled)
        layout.addWidget(QLabel("Data Bitrate"))
        layout.addWidget(self.data_bitrate)

        controls = QHBoxLayout()
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self._connect_channel)
        self.disconnect_btn = QPushButton("Disconnect")
        self.disconnect_btn.clicked.connect(self._disconnect_channel)
        controls.addWidget(self.connect_btn)
        controls.addWidget(self.disconnect_btn)
        layout.addLayout(controls)

        layout.addStretch(1)

        trace_box = QGroupBox("Trace")
        trace_layout = QVBoxLayout(trace_box)
        trace_layout.addWidget(QPushButton("Start Recording"))
        trace_layout.addWidget(QPushButton("Stop Recording"))
        trace_layout.addWidget(QPushButton("Playback Trace"))
        layout.addWidget(trace_box)

        return panel

    def _build_message_panel(self):
        panel = QGroupBox("Live Messages")
        layout = QVBoxLayout(panel)
        layout.setSpacing(10)

        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("ID Filter"))
        id_filter = QLineEdit()
        id_filter.setPlaceholderText("e.g. 0x18FF, 100-1FF")
        filter_row.addWidget(id_filter)

        filter_row.addWidget(QLabel("Period"))
        period = QSpinBox()
        period.setRange(10, 5000)
        period.setValue(200)
        period.setSuffix(" ms")
        filter_row.addWidget(period)

        self.freeze_cb = QCheckBox("Freeze")
        self.autoscroll_cb = QCheckBox("Auto-scroll")
        self.autoscroll_cb.setChecked(True)
        filter_row.addWidget(self.freeze_cb)
        filter_row.addWidget(self.autoscroll_cb)
        filter_row.addStretch(1)
        layout.addLayout(filter_row)

        self.message_model = QStandardItemModel(0, 8)
        self.message_model.setHorizontalHeaderLabels(
            ["Time", "Ch", "ID", "Dir", "DLC", "Len", "Data", "Flags"]
        )

        table = QTableView()
        table.setModel(self.message_model)
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableView.SelectRows)
        table.setSelectionMode(QTableView.SingleSelection)
        table.horizontalHeader().setStretchLastSection(True)
        table.verticalHeader().setVisible(False)
        table.setSortingEnabled(True)
        self.message_table = table
        layout.addWidget(table)

        return panel

    def _build_detail_panel(self):
        panel = QGroupBox("Details")
        layout = QVBoxLayout(panel)
        layout.setSpacing(10)

        stats = QGroupBox("Statistics")
        stats_layout = QVBoxLayout(stats)
        stats_layout.addWidget(QLabel("Rx rate: 0 msg/s"))
        stats_layout.addWidget(QLabel("Tx rate: 0 msg/s"))
        stats_layout.addWidget(QLabel("Errors: 0"))
        layout.addWidget(stats)

        decode_box = QGroupBox("Decoded Signals")
        decode_layout = QVBoxLayout(decode_box)
        decode_layout.addWidget(QLabel("Select a message to view signals"))
        layout.addWidget(decode_box)

        plugin_box = QGroupBox("Instruments")
        plugin_layout = QVBoxLayout(plugin_box)
        plugin_layout.addWidget(QLabel("Add gauges, charts, and maps"))
        plugin_layout.addWidget(QPushButton("Open Instruments"))
        layout.addWidget(plugin_box)

        layout.addStretch(1)
        return panel

    def _build_status_bar(self):
        status = QStatusBar()
        status.showMessage("Ready · No channel connected")
        return status

    def _refresh_channels(self):
        channels = BusManager.detect_channels()
        self.channel_select.clear()
        self.channel_select.addItems(channels)
        if channels:
            self.statusBar().showMessage(f"Detected {len(channels)} CAN channel(s)")
        else:
            self.statusBar().showMessage("No CAN devices detected")

    def _connect_channel(self):
        if self.connected_channel:
            return

        channel = self.channel_select.currentText().strip()
        if not channel:
            self.statusBar().showMessage("Select a channel before connecting")
            return

        try:
            cfg = ChannelConfig(
                channel=channel,
                bitrate=int(self.bitrate.currentText()),
                fd=self.fd_enabled.isChecked(),
                data_bitrate=int(self.data_bitrate.currentText()) if self.fd_enabled.isChecked() else None,
                listen_only=True,
            )
            self.bus_manager.open(cfg)
            self.bus_manager.add_listener(channel, self._on_message)
            self.connected_channel = channel
            self.statusBar().showMessage(f"Connected · {channel}")
        except Exception as exc:
            self.statusBar().showMessage(f"Connect failed: {exc}")

    def _disconnect_channel(self):
        if not self.connected_channel:
            return
        channel = self.connected_channel
        self.bus_manager.close(channel)
        self.connected_channel = None
        self.statusBar().showMessage("Disconnected")

    def _on_message(self, msg):
        data = {
            "time": time.strftime("%H:%M:%S", time.localtime(msg.timestamp or time.time())),
            "channel": self.connected_channel or "",
            "arbitration_id": f"0x{msg.arbitration_id:X}",
            "direction": "RX",
            "dlc": str(msg.dlc),
            "length": str(len(msg.data)),
            "data": msg.data.hex(" ").upper(),
            "flags": "FD" if msg.is_fd else "STD",
        }
        self.message_bridge.received.emit(data)

    def _append_message_row(self, data: dict):
        if self.freeze_cb.isChecked():
            return
        row = [
            QStandardItem(data["time"]),
            QStandardItem(data["channel"]),
            QStandardItem(data["arbitration_id"]),
            QStandardItem(data["direction"]),
            QStandardItem(data["dlc"]),
            QStandardItem(data["length"]),
            QStandardItem(data["data"]),
            QStandardItem(data["flags"]),
        ]
        self.message_model.appendRow(row)
        if self.autoscroll_cb.isChecked():
            self.message_table.scrollToBottom()


def main():
    """Main entry point."""
    configure_logging(log_file=False)
    logger.info("Starting PCAN_Auto")
    
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.showMaximized()
    window.raise_()
    window.activateWindow()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
