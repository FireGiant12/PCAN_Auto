import threading
import time
import logging
from typing import Dict, Optional, Callable, List
import can

logger = logging.getLogger(__name__)


class ChannelConfig:
    """Configuration for a CAN bus channel.
    
    Attributes:
        channel: CAN channel identifier (e.g., "PCAN_USBBUS1")
        bitrate: Arbitration phase bitrate in bits per second (default: 500000)
        fd: Enable CAN FD mode (default: False)
        data_bitrate: Data phase bitrate for CAN FD in bps (default: 2000000 if fd=True)
        listen_only: Listen-only mode (no transmission) (default: False)
    
    Raises:
        ValueError: If channel is empty, bitrate is invalid, or data_bitrate is invalid
    """
    def __init__(self, channel: str, bitrate: int = 500000, fd: bool = False,
                 data_bitrate: Optional[int] = None, listen_only: bool = False):
        if not channel or not isinstance(channel, str):
            raise ValueError(f"Channel must be a non-empty string, got: {channel}")
        if bitrate <= 0:
            raise ValueError(f"Bitrate must be positive, got: {bitrate}")
        if fd and data_bitrate is not None and data_bitrate <= 0:
            raise ValueError(f"Data bitrate must be positive, got: {data_bitrate}")
        
        self.channel = channel
        self.bitrate = bitrate
        self.fd = fd
        self.data_bitrate = data_bitrate
        self.listen_only = listen_only


class BusManager:
    """Manage multiple CAN buses and dispatch received messages to listeners.

    This manager handles opening/closing multiple CAN channels, sending messages,
    and distributing received messages to registered listener callbacks. It uses
    python-can's interface abstraction for hardware independence.
    
    Example:
        mgr = BusManager()
        mgr.open(ChannelConfig(channel="PCAN_USBBUS1", bitrate=500000))
        mgr.add_listener("PCAN_USBBUS1", lambda msg: print(f"Received: {msg.arbitration_id}"))
        # ... do work ...
        mgr.close("PCAN_USBBUS1")
    """

    def __init__(self):
        self.buses: Dict[str, can.BusABC] = {}
        self.listeners: Dict[str, List[Callable[[can.Message], None]]] = {}
        self.rx_threads: Dict[str, threading.Thread] = {}
        self._stop_event = threading.Event()
        self._buses_lock = threading.Lock()
        logger.debug("BusManager initialized")

    @staticmethod
    def detect_channels(interface: str = "pcan") -> List[str]:
        """Detect available CAN channels for a given interface.

        Args:
            interface: python-can interface name (default: "pcan")

        Returns:
            List of channel identifiers.
        """
        channels: List[str] = []
        try:
            configs = can.detect_available_configs()
            for cfg in configs:
                cfg_interface = str(cfg.get("interface") or "").lower()
                if interface and cfg_interface and cfg_interface != interface:
                    continue
                channel = cfg.get("channel")
                if channel:
                    channels.append(str(channel))
        except Exception as e:
            logger.warning(f"Channel detection failed for {interface}: {e}")

        if not channels and interface == "pcan":
            # Provide a sensible fallback list for PCAN USB devices
            channels = ["PCAN_USBBUS1", "PCAN_USBBUS2", "PCAN_USBBUS3", "PCAN_USBBUS4"]

        return channels

    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensures cleanup."""
        self.stop()
        return False

    def open(self, cfg: ChannelConfig):
        """Open a CAN bus channel.
        
        Args:
            cfg: ChannelConfig instance with channel settings
            
        Raises:
            ValueError: If channel configuration is invalid
            can.CanError: If bus initialization fails
        """
        try:
            logger.info(f"Opening channel: {cfg.channel} at {cfg.bitrate} bps (FD={cfg.fd})")
            
            if cfg.fd:
                bus = can.interface.Bus(
                    interface="pcan",
                    channel=cfg.channel,
                    fd=True,
                    bitrate=cfg.bitrate,
                    data_bitrate=cfg.data_bitrate or 2000000,
                    receive_own_messages=False,
                    f_clock=80000000
                )
            else:
                bus = can.interface.Bus(
                    interface="pcan",
                    channel=cfg.channel,
                    bitrate=cfg.bitrate,
                    receive_own_messages=False
                )
            
            # Try to apply empty filter (permissive)
            try:
                bus.set_filters([])
            except Exception as e:
                logger.warning(f"Could not set filters on {cfg.channel}: {e}")
            
            with self._buses_lock:
                self.buses[cfg.channel] = bus
                self.listeners[cfg.channel] = []
            
            # Start receive thread
            t = threading.Thread(target=self._rx_loop, args=(cfg.channel,), daemon=True)
            t.start()
            self.rx_threads[cfg.channel] = t
            logger.info(f"Channel {cfg.channel} opened successfully")
            
        except Exception as e:
            logger.error(f"Failed to open channel {cfg.channel}: {e}", exc_info=True)
            raise

    def close(self, channel: str):
        """Close a CAN bus channel.
        
        Args:
            channel: Channel name to close
        """
        try:
            logger.info(f"Closing channel: {channel}")
            with self._buses_lock:
                bus = self.buses.pop(channel, None)
                self.listeners.pop(channel, None)
            
            if bus:
                bus.shutdown()
                logger.info(f"Channel {channel} closed")
        except Exception as e:
            logger.error(f"Error closing channel {channel}: {e}", exc_info=True)

    def add_listener(self, channel: str, cb: Callable[[can.Message], None]):
        """Register a message listener for a channel.
        
        Args:
            channel: Channel name
            cb: Callback function(msg: can.Message) to invoke on received messages
        """
        with self._buses_lock:
            if channel in self.listeners:
                self.listeners[channel].append(cb)
                logger.debug(f"Listener added to {channel}")
            else:
                logger.warning(f"Channel {channel} not open, listener not added")

    def _rx_loop(self, channel: str):
        """Receive loop for a channel (runs in background thread).
        
        Args:
            channel: Channel to receive from
        """
        logger.debug(f"RX loop started for {channel}")
        bus = self.buses[channel]
        msg_count = 0
        
        while not self._stop_event.is_set() and channel in self.buses:
            try:
                msg = bus.recv(timeout=0.1)
                if msg:
                    msg_count += 1
                    with self._buses_lock:
                        listeners = list(self.listeners.get(channel, []))
                    
                    for cb in listeners:
                        try:
                            cb(msg)
                        except Exception as e:
                            logger.error(f"Listener error on {channel}: {e}", exc_info=True)
            except Exception as e:
                logger.error(f"RX loop error on {channel}: {e}", exc_info=True)
                break
        
        logger.debug(f"RX loop ended for {channel} ({msg_count} messages)")

    def send(self, channel: str, arbitration_id: int, data: bytes,
             is_extended_id: bool = False, is_fd: bool = False, bitrate_switch: bool = False, rtr: bool = False):
        """Send a CAN message on a channel.
        
        Args:
            channel: Target channel
            arbitration_id: CAN arbitration ID (11-bit or 29-bit)
            data: Message payload (0-8 bytes for CAN, 0-64 for CAN FD)
            is_extended_id: Use 29-bit extended ID (default: False)
            is_fd: Use CAN FD frame format (default: False)
            bitrate_switch: Enable bitrate switch for CAN FD (default: False)
            rtr: Send as remote transmission request (default: False)
            
        Raises:
            KeyError: If channel not open
            can.CanError: If transmission fails
        """
        try:
            msg = can.Message(
                arbitration_id=arbitration_id,
                data=data,
                is_extended_id=is_extended_id,
                is_fd=is_fd,
                bitrate_switch=bitrate_switch,
                is_remote_frame=rtr
            )
            self.buses[channel].send(msg)
            logger.debug(f"Sent on {channel}: ID=0x{arbitration_id:X} len={len(data)}")
        except KeyError:
            logger.error(f"Channel {channel} not open")
            raise
        except Exception as e:
            logger.error(f"Failed to send on {channel}: {e}", exc_info=True)
            raise

    def stop(self):
        """Stop all channels and shutdown manager."""
        logger.info("Stopping BusManager")
        self._stop_event.set()
        
        # Wait for RX threads briefly
        for ch in list(self.buses.keys()):
            self.close(ch)
        
        logger.info("BusManager stopped")
