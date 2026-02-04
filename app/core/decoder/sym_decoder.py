# Minimal .sym parser supporting messages and bit fields
import re
import logging
from typing import Dict, Any, Optional
import can

logger = logging.getLogger(__name__)


class SymDecoder:
    """Decode CAN messages using PEAK .sym (symbol) files.
    
    Parser for PEAK's .sym format which defines CAN messages and signals
    with bit layout information.
    
    Example:
        decoder = SymDecoder("database.sym")
        decoded = decoder.decode(msg)
    """
    def __init__(self, sym_path: str):
        """Initialize decoder with .sym file.
        
        Args:
            sym_path: Path to .sym file
            
        Raises:
            FileNotFoundError: If .sym file not found
        """
        self.messages = {}  # msg_id -> spec
        try:
            self._load(sym_path)
            logger.info(f"SymDecoder loaded: {sym_path} ({len(self.messages)} messages)")
        except Exception as e:
            logger.error(f"Failed to load .sym file {sym_path}: {e}", exc_info=True)
            raise

    def _load(self, path: str):
        """Internal: load and parse .sym file."""
        cur = None
        with open(path, "r", encoding="latin1") as f:
            for line_num, line in enumerate(f, start=1):
                line = line.strip()
                try:
                    if line.startswith("ID ="):
                        # Example: ID = 0x123
                        cur = int(line.split("=")[1].strip(), 16)
                        self.messages[cur] = {"signals": []}
                    elif line.startswith("Var =") and cur is not None:
                        # Example: Var = Name, startbit, length, endian, signed, factor, offset
                        parts = [p.strip() for p in line.split("=")[1].split(",")]
                        if len(parts) < 7:
                            logger.warning(f"Malformed signal line {line_num}: {line}")
                            continue
                        
                        self.messages[cur]["signals"].append({
                            "name": parts[0],
                            "start": int(parts[1]),
                            "length": int(parts[2]),
                            "signed": parts[4].lower() == "signed",
                            "factor": float(parts[5]),
                            "offset": float(parts[6])
                        })
                except (ValueError, IndexError) as e:
                    logger.warning(f"Error parsing .sym line {line_num}: {line} - {e}")

    def decode(self, msg: can.Message) -> Optional[Dict[str, Any]]:
        """Decode a CAN message.
        
        Args:
            msg: can.Message to decode
            
        Returns:
            Dictionary of signal names to values if message found, None otherwise
        """
        spec = self.messages.get(msg.arbitration_id)
        if not spec:
            return None
        
        try:
            val = int.from_bytes(msg.data, "little")
            out: Dict[str, Any] = {}
            for s in spec["signals"]:
                try:
                    mask = (1 << s["length"]) - 1
                    raw = (val >> s["start"]) & mask
                    if s["signed"] and (raw & (1 << (s["length"] - 1))):
                        raw = raw - (1 << s["length"])
                    phys = raw * s["factor"] + s["offset"]
                    out[s["name"]] = phys
                except Exception as e:
                    logger.debug(f"Error decoding signal {s.get('name')}: {e}")
            return out
        except Exception as e:
            logger.warning(f"Failed to decode message 0x{msg.arbitration_id:X}: {e}")
            return None
