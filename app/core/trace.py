import csv
import time
import logging
from typing import Optional
import can

logger = logging.getLogger(__name__)


class CsvTracer:
    """CSV trace writer for recording CAN messages to file.
    
    Records timestamped CAN messages with all metadata to a CSV file
    for later analysis or playback.
    
    CSV Format: ts, ch, id, ext, fd, brs, len, data
    
    Example:
        with CsvTracer("/tmp/trace.csv") as tracer:
            tracer.write("CH1", msg)
    """
    def __init__(self, path: str):
        """Initialize tracer.
        
        Args:
            path: Output file path
        """
        self.path = path
        try:
            self._f = open(path, "w", newline="")
            self._w = csv.writer(self._f)
            self._w.writerow(["ts", "ch", "id", "ext", "fd", "brs", "len", "data"])
            logger.info(f"CsvTracer opened: {path}")
        except Exception as e:
            logger.error(f"Failed to open trace file {path}: {e}", exc_info=True)
            raise

    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
        return False

    def write(self, channel: str, msg: can.Message):
        """Write a received message to trace.
        
        Args:
            channel: Channel name
            msg: can.Message to record
        """
        try:
            self._w.writerow([
                getattr(msg, "timestamp", time.time()),
                channel,
                hex(msg.arbitration_id),
                int(msg.is_extended_id),
                int(getattr(msg, "is_fd", False)),
                int(getattr(msg, "bitrate_switch", False)),
                getattr(msg, "dlc", len(msg.data) if msg.data is not None else 0),
                msg.data.hex() if msg.data else ""
            ])
            self._f.flush()
        except Exception as e:
            logger.error(f"Error writing trace record: {e}", exc_info=True)

    def close(self):
        """Close trace file."""
        try:
            if self._f:
                self._f.close()
                logger.info(f"CsvTracer closed: {self.path}")
        except Exception as e:
            logger.error(f"Error closing trace file: {e}", exc_info=True)


class CsvTracePlayer:
    """CSV trace playback - replays recorded messages to a bus.
    
    Reads trace file and sends messages with timing preserved.
    
    Example:
        player = CsvTracePlayer("/tmp/trace.csv")
        player.play(bus_mgr, channel="CH1", speed=1.0)
    """
    def __init__(self, path: str):
        """Initialize player.
        
        Args:
            path: Input trace file path
        """
        self.path = path
        logger.info(f"CsvTracePlayer initialized: {path}")

    def play(self, bus_mgr, channel: str, loop: bool = False, speed: float = 1.0):
        """Play trace file to a bus channel.
        
        Args:
            bus_mgr: BusManager to send on
            channel: Target channel
            loop: Repeat indefinitely (default: False)
            speed: Playback speed multiplier (default: 1.0)
            
        Raises:
            FileNotFoundError: If trace file doesn't exist
            ValueError: If trace file is malformed
        """
        iteration = 0
        while True:
            iteration += 1
            logger.info(f"Playing trace (iteration {iteration}): {self.path}")
            msg_count = 0
            
            try:
                with open(self.path, newline="") as f:
                    r = csv.DictReader(f)
                    if not r.fieldnames or r.fieldnames[0] != "ts":
                        raise ValueError(f"Invalid trace file format: {self.path}")
                    
                    last_ts = None
                    for row_num, row in enumerate(r, start=2):  # Skip header
                        try:
                            ts = float(row["ts"])
                            if last_ts is not None:
                                time.sleep(max(0, (ts - last_ts) / speed))
                            last_ts = ts
                            
                            arb_id = int(row["id"], 16)
                            data = bytes.fromhex(row.get("data", "")) if row.get("data") else b""
                            ext = bool(int(row["ext"]))
                            fd = bool(int(row["fd"]))
                            brs = bool(int(row["brs"]))
                            
                            bus_mgr.send(channel, arb_id, data, is_extended_id=ext, 
                                       is_fd=fd, bitrate_switch=brs)
                            msg_count += 1
                            
                        except (ValueError, KeyError) as e:
                            logger.error(f"Error parsing trace row {row_num}: {e}")
                            raise
                
                logger.info(f"Playback complete: {msg_count} messages")
                
            except FileNotFoundError as e:
                logger.error(f"Trace file not found: {self.path}", exc_info=True)
                raise
            except Exception as e:
                logger.error(f"Error during playback: {e}", exc_info=True)
                raise
            
            if not loop:
                break
