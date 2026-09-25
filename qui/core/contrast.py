"""WCAG 2.x contrast between a component's text and background colors."""

from __future__ import annotations

from .selector_registry import COMPONENTS
from .theme_model import ACCENT_REF, Gradient, Theme, parse_color

AA_NORMAL = 4.5  # WCAG 2.x SC 1.4.3, normal-size text
AAA_NORMAL = 7.0  # SC 1.4.6
WHITE = (255, 255, 255)

RGB = tuple[int, int, int]


def relative_luminance(rgb: RGB) -> float:
    def channel(value: int) -> float:
        c = value / 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (channel(v) for v in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(a: RGB, b: RGB) -> float:
    la, lb = sorted((relative_luminance(a), relative_luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def composite(rgba: tuple[int, int, int, int], backdrop: RGB) -> RGB:
    """*rgba* (possibly translucent) painted over an opaque *backdrop*."""
    *rgb, a = rgba
    alpha = a / 255
    return tuple(round(c * alpha + d * (1 - alpha)) for c, d in zip(rgb, backdrop))


class _Colors:
    """Resolves theme colors the way the generated QSS does (accent token, opacity)."""

    def __init__(self, theme: Theme) -> None:
        self.theme = theme

    def rgba(self, color: str, is_background: bool) -> tuple[int, int, int, int]:
        r, g, b, a = parse_color(self.theme.global_style.accent if color == ACCENT_REF else color)
        if is_background:  # global opacity scales background alpha only
            a = round(a * self.theme.global_style.opacity)
        return r, g, b, a

    def normal_background(self, component_id: str):
        style = self.theme.components.get(component_id)
        normal = style.states.get("normal") if style else None
        return normal.background if normal else None

    def backdrop(self, component_id: str) -> RGB:
        """What shows through a translucent background: the ancestors' backgrounds, outermost
        first, over the main window (registry parents stand in for the widget hierarchy)."""
        chain, parent = [], COMPONENTS[component_id].parent if component_id in COMPONENTS else None
        while parent is not None:
            chain.append(parent)
            parent = COMPONENTS[parent].parent
        if "main_window" not in chain:
            chain.append("main_window")
        rgb = WHITE
        for ancestor in reversed(chain):
            background = self.normal_background(ancestor)
            if isinstance(background, Gradient):
                background = background.stops[0].color
            if background is not None:
                rgb = composite(self.rgba(background, True), rgb)
        return rgb


def text_contrast(theme: Theme, component_id: str, state: str) -> float | None:
    """Worst-case contrast of text over background for *state*, or None if either is unset.

    Unset values in *state* fall back to the component's normal state. Gradients use
    their worst stop.
    """
    style = theme.components.get(component_id)
    if style is None:
        return None
    states = [s for s in (style.states.get(state), style.states.get("normal")) if s is not None]
    text = next((s.color for s in states if s.color is not None), None)
    background = next((s.background for s in states if s.background is not None), None)
    if text is None or background is None:
        return None
    colors = _Colors(theme)
    backdrop = colors.backdrop(component_id)
    stops = [s.color for s in background.stops] if isinstance(background, Gradient) else [background]
    ratios = []
    for stop in stops:
        bg = composite(colors.rgba(stop, True), backdrop)
        ratios.append(contrast_ratio(composite(colors.rgba(text, False), bg), bg))
    return min(ratios)
