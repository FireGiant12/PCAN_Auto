import cantools
import logging
from typing import Optional, Dict, Any
import can

logger = logging.getLogger(__name__)


class DbcDecoder:
    """Decode CAN messages using a DBC (CAN database) file.
    
    Uses cantools library to load DBC format and decode raw CAN data
    into human-readable signal names and values.
    
    Example:
        decoder = DbcDecoder("vehicles.dbc")
        msg = can.Message(arbitration_id=0x123, data=b'\\x01\\x02...')
        decoded = decoder.decode(msg)
        if decoded:
            print(decoded)  # {'Signal1': 10, 'Signal2': 20}
    """
    def __init__(self, dbc_path: str):
        """Initialize decoder with DBC file.
        
        Args:
            dbc_path: Path to .dbc file
            
        Raises:
            FileNotFoundError: If DBC file not found
            Exception: If DBC file is invalid
        """
        try:
            self.db = cantools.database.load_file(dbc_path)
            logger.info(f"DbcDecoder loaded: {dbc_path} ({len(self.db.messages)} messages)")
        except Exception as e:
            logger.error(f"Failed to load DBC file {dbc_path}: {e}", exc_info=True)
            raise

    def decode(self, msg: can.Message) -> Optional[Dict[str, Any]]:
        """Decode a CAN message.
        
        Args:
            msg: can.Message to decode
            
        Returns:
            Dictionary of signal names to values if message found in database, None otherwise
        """
        try:
            m = self.db.get_message_by_frame_id(msg.arbitration_id)
            decoded = m.decode(msg.data)
            logger.debug(f"Decoded message 0x{msg.arbitration_id:X}: {list(decoded.keys())}")
            return decoded
        except KeyError:
            # Message not in database - this is normal
            return None
        except Exception as e:
            logger.warning(f"Failed to decode message 0x{msg.arbitration_id:X}: {e}")
            return None
