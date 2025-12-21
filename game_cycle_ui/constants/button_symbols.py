"""Button symbol constants for consistent UI theming."""

# Navigation/Action symbols
ARROW_RIGHT = "▶"  # Used for forward actions (Continue, Next, View, Simulate)
ARROW_LEFT = "◀"   # Used for back actions (Back, Previous)
ARROW_THIN = "→"   # Used for transitions (Complete Wave → Draft)
DIVIDER = "•"      # Used for separators in button text

def format_button_text(text: str, symbol: str = ARROW_RIGHT) -> str:
    """Format button text with symbol (ensures consistent spacing)."""
    return f"{text} {symbol}"
