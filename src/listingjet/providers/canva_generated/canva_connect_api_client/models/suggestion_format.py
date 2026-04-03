from enum import Enum


class SuggestionFormat(str, Enum):
    BACKGROUND_COLOR = "background_color"
    COLOR = "color"
    DECORATION = "decoration"
    DIRECTION = "direction"
    FONT_FAMILY = "font_family"
    FONT_SIZE = "font_size"
    FONT_SIZE_MODIFIER = "font_size_modifier"
    FONT_STYLE = "font_style"
    FONT_WEIGHT = "font_weight"
    LETTER_SPACING = "letter_spacing"
    LINE_HEIGHT = "line_height"
    LINK = "link"
    LIST_LEVEL = "list_level"
    LIST_MARKER = "list_marker"
    MARGIN_INLINE_START = "margin_inline_start"
    STRIKETHROUGH = "strikethrough"
    TEXT_ALIGN = "text_align"
    TEXT_INDENT = "text_indent"
    VERTICAL_ALIGN = "vertical_align"

    def __str__(self) -> str:
        return str(self.value)
