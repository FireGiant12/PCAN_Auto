from dataclasses import dataclass
from typing import Optional


@dataclass
class IdFilter:
    """CAN message ID filter for hardware-level filtering.
    
    Filters CAN messages by arbitration ID range, reducing bus load.
    
    Attributes:
        min_id: Minimum CAN ID to accept (inclusive)
        max_id: Maximum CAN ID to accept (inclusive)
        extended: Filter type - None (any), True (extended 29-bit), False (standard 11-bit)
    
    Example:
        # Accept only standard IDs 0x100-0x200
        f = IdFilter(min_id=0x100, max_id=0x200, extended=False)
    """
    min_id: int
    max_id: int
    extended: Optional[bool] = None

    def __post_init__(self):
        """Validate filter configuration."""
        if self.min_id < 0:
            raise ValueError(f"min_id must be non-negative, got {self.min_id}")
        if self.max_id < self.min_id:
            raise ValueError(f"max_id ({self.max_id}) must be >= min_id ({self.min_id})")
        
        max_std_id = 0x7FF  # 11-bit
        max_ext_id = 0x1FFFFFFF  # 29-bit
        
        if self.extended is False and self.max_id > max_std_id:
            raise ValueError(f"Standard ID must be <= 0x{max_std_id:X}, got 0x{self.max_id:X}")
        if self.extended is True and self.max_id > max_ext_id:
            raise ValueError(f"Extended ID must be <= 0x{max_ext_id:X}, got 0x{self.max_id:X}")

    def to_python_can(self):
        """Convert to python-can filter format.
        
        Returns:
            Dictionary with 'can_id' and 'can_mask' for python-can's set_filters()
        """
        # Create mask that matches the range
        # For a range, we need to find common bits and create appropriate mask
        range_size = self.max_id - self.min_id + 1
        
        if range_size == 1:
            # Single ID - exact match
            mask = 0x1FFFFFFF if self.extended else 0x7FF
        else:
            # Find the highest bit set in the range
            highest_bit = range_size.bit_length() - 1
            # Create mask that covers this range
            mask = ~((1 << highest_bit) - 1) & (0x1FFFFFFF if self.extended else 0x7FF)
        
        return {
            "can_id": self.min_id,
            "can_mask": mask
        }
