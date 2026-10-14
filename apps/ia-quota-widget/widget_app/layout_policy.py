"""Pure geometry contract. All dimensions are logical pixels (Qt DIP)."""
from dataclasses import dataclass

HEIGHTS = (40, 72, 112)
DEFAULT_WIDTH = 800
DEFAULT_HEIGHT = 72
CONTROL_WIDTH = 44
NAV_WIDTH = 66
EDGE = 3  # two-pixel resize margin plus one-pixel panel border


@dataclass(frozen=True)
class StripPolicy:
    height: int
    minimum_width: int
    capacity: int
    inline: bool


def strip_policy(width, requested_height, count, cell_width=158, line_height=23, stack_height=50):
    requested_height = requested_height if isinstance(requested_height,int) and not isinstance(requested_height,bool) and 40<=requested_height<=10000 else DEFAULT_HEIGHT
    # Human decision 2026-10-11: the chosen strip height is EXACT. Fonts and
    # data never promote it; what does not fit scrolls inside each column.
    height = requested_height
    chrome = CONTROL_WIDTH + NAV_WIDTH + 2 * EDGE
    minimum_width = max(360, chrome + cell_width)
    capacity = max(1, int(max(0, width - chrome) // max(1, cell_width))) if count else 0
    return StripPolicy(height, minimum_width, min(count, capacity), stack_height + 12 > height)


def compact_header_px(inner_height, preferred_px):
    """Name size in the compact column header: the human preference, limited
    to a quarter of the strip so the scrolling body keeps the room. The saved
    preference is untouched; the header labels the adjustment."""
    return max(1, min(int(preferred_px), max(10, round(inner_height * 0.25))))


def inline_positions(cell_height, line_height):
    """Micro row reserves two pixels before the three-pixel track, no clipping."""
    text_y = max(0, (cell_height - line_height - 6) // 2)
    return text_y, text_y + line_height + 2
