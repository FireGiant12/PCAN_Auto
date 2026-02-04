from types import SimpleNamespace
from typing import Callable, Optional, Dict, Any, List
import logging

logger = logging.getLogger(__name__)


class AutomationRuntime:
    """Runtime for automating CAN message handling with event-driven handlers.
    
    The runtime provides decorator-based event registration for RX/TX events
    and automatic message decoding with pluggable decoders.
    
    Example:
        runtime = AutomationRuntime(bus_mgr, decoders=[dbc_decoder])
        
        @runtime.on_rx
        def handle_msg(ctx):
            print(f"Got message: {ctx.msg.arbitration_id}")
            if ctx.decoded:
                print(f"Decoded: {ctx.decoded}")
        
        runtime.bind_channel("PCAN_USBBUS1")
    """
    def __init__(self, bus_mgr, decoders: Optional[List] = None):
        """Initialize runtime.
        
        Args:
            bus_mgr: BusManager instance to receive messages from
            decoders: List of decoder objects with decode(msg) method
        """
        self.bus_mgr = bus_mgr
        self.decoders = decoders or []
        self.handlers: Dict[str, List[Callable]] = {
            "on_rx": [], 
            "before_tx": [], 
            "after_tx": []
        }
        logger.debug(f"AutomationRuntime initialized with {len(self.decoders)} decoders")

    def on_rx(self, fn: Callable):
        """Decorator to register a message received handler.
        
        Args:
            fn: Callable(ctx) where ctx is SimpleNamespace with .msg and .decoded
            
        Returns:
            The function (for decorator use)
            
        Example:
            @runtime.on_rx
            def handle(ctx):
                print(ctx.msg)
        """
        self.handlers["on_rx"].append(fn)
        fn_name = getattr(fn, "__name__", repr(fn))
        logger.debug(f"Registered RX handler: {fn_name}")
        return fn
    
    def before_tx(self, fn: Callable):
        """Decorator to register a pre-transmission handler.
        
        Args:
            fn: Callable(ctx) invoked before sending
            
        Returns:
            The function (for decorator use)
        """
        self.handlers["before_tx"].append(fn)
        fn_name = getattr(fn, "__name__", repr(fn))
        logger.debug(f"Registered pre-TX handler: {fn_name}")
        return fn
    
    def after_tx(self, fn: Callable):
        """Decorator to register a post-transmission handler.
        
        Args:
            fn: Callable(ctx) invoked after sending
            
        Returns:
            The function (for decorator use)
        """
        self.handlers["after_tx"].append(fn)
        fn_name = getattr(fn, "__name__", repr(fn))
        logger.debug(f"Registered post-TX handler: {fn_name}")
        return fn

    def bind_channel(self, channel: str):
        """Bind a channel to receive message event callbacks.
        
        Args:
            channel: Channel name to listen on
        """
        logger.info(f"Binding channel {channel} to runtime")
        self.bus_mgr.add_listener(channel, self._rx_dispatch)

    def _rx_dispatch(self, msg):
        """Internal: dispatch received message to all RX handlers.
        
        Args:
            msg: can.Message instance
        """
        try:
            decoded = self._decode(msg)
            ctx = SimpleNamespace(msg=msg, decoded=decoded)
            
            for fn in self.handlers["on_rx"]:
                try:
                    fn(ctx)
                except Exception as e:
                    fn_name = getattr(fn, "__name__", repr(fn))
                    logger.error(f"RX handler {fn_name} failed: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"Error dispatching RX message: {e}", exc_info=True)

    def _decode(self, msg) -> Optional[Dict[str, Any]]:
        """Try to decode message with available decoders.
        
        Args:
            msg: can.Message to decode
            
        Returns:
            Decoded message dict if successful, None otherwise
        """
        for decoder in self.decoders:
            try:
                out = decoder.decode(msg)
                if out:
                    return out
            except Exception as e:
                logger.debug(f"Decoder {decoder.__class__.__name__} failed: {e}")
        return None
