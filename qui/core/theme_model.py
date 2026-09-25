"""Theme model: the single source of truth, serializable to JSON (``.qui.json``).

Pure Python (no Qt) so it can be tested and reused anywhere. ``None`` always means
"not set": nothing is emitted for it and the base UI theme shows through.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Union

SCHEMA_VERSION = 1
# Also the QSS rule order: later rules win ties, so "disabled" must come last.
STATES = ("normal", "hover", "pressed", "selected", "checked", "disabled")
ACCENT_REF = "@accent"

_HEX_RE = re.compile(r"#([0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})")


def parse_color(value: str) -> tuple[int, int, int, int]:
    """Parse ``#RGB``, ``#RRGGBB`` or ``#RRGGBBAA`` into an ``(r, g, b, a)`` tuple."""
    match = _HEX_RE.fullmatch(value) if isinstance(value, str) else None
    if match is None:
        raise ValueError(f"Invalid color {value!r}; expected #RGB, #RRGGBB or #RRGGBBAA")
    digits = match.group(1)
    if len(digits) == 3:
        digits = "".join(c * 2 for c in digits)
    if len(digits) == 6:
        digits += "ff"
    r, g, b, a = (int(digits[i : i + 2], 16) for i in range(0, 8, 2))
    return r, g, b, a


def _color(value: Any) -> str | None:
    """Validate an optional color field (hex or the accent token)."""
    if value is not None and value != ACCENT_REF:
        parse_color(value)
    return value


def _length(value: Any) -> int | None:
    """Validate an optional non-negative pixel length."""
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"Invalid length {value!r}; expected a non-negative integer (px)")
    return value


@dataclass
class GradientStop:
    position: float
    color: str


@dataclass
class Gradient:
    """Linear gradient in ``qlineargradient`` coordinates (0..1 of the widget's box)."""

    stops: list[GradientStop]
    x1: float = 0.0
    y1: float = 0.0
    x2: float = 0.0
    y2: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "x1": self.x1,
            "y1": self.y1,
            "x2": self.x2,
            "y2": self.y2,
            "stops": [[s.position, s.color] for s in self.stops],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Gradient:
        stops = [GradientStop(float(pos), _color(color)) for pos, color in data["stops"]]
        if len(stops) < 2:
            raise ValueError("A gradient needs at least two stops")
        coords = (float(data.get(k, d)) for k, d in (("x1", 0), ("y1", 0), ("x2", 0), ("y2", 1)))
        return cls(stops, *coords)


Background = Union[str, Gradient]


@dataclass
class Padding:
    top: int = 0
    right: int = 0
    bottom: int = 0
    left: int = 0

    def to_list(self) -> list[int]:
        return [self.top, self.right, self.bottom, self.left]

    @classmethod
    def from_list(cls, values: list[int]) -> Padding:
        if len(values) != 4:
            raise ValueError("Padding needs four values: top, right, bottom, left")
        return cls(*(_length(v) for v in values))


@dataclass
class StateStyle:
    """Style of one component in one state (normal, hover, ...)."""

    background: Background | None = None
    color: str | None = None
    border_color: str | None = None
    border_width: int | None = None
    border_radius: int | None = None
    padding: Padding | None = None

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {}
        if isinstance(self.background, Gradient):
            data["background"] = self.background.to_dict()
        elif self.background is not None:
            data["background"] = self.background
        for key in ("color", "border_color", "border_width", "border_radius"):
            if (value := getattr(self, key)) is not None:
                data[key] = value
        if self.padding is not None:
            data["padding"] = self.padding.to_list()
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StateStyle:
        background = data.get("background")
        background = Gradient.from_dict(background) if isinstance(background, dict) else _color(background)
        padding = data.get("padding")
        return cls(
            background=background,
            color=_color(data.get("color")),
            border_color=_color(data.get("border_color")),
            border_width=_length(data.get("border_width")),
            border_radius=_length(data.get("border_radius")),
            padding=None if padding is None else Padding.from_list(padding),
        )


@dataclass
class ComponentStyle:
    """Per-state styles of one component from the selector registry."""

    states: dict[str, StateStyle] = field(default_factory=dict)

    def state(self, name: str) -> StateStyle:
        """Return the style for *name*, creating an empty one if needed."""
        if name not in STATES:
            raise ValueError(f"Unknown state {name!r}")
        return self.states.setdefault(name, StateStyle())

    def to_dict(self) -> dict[str, Any]:
        return {name: d for name, s in self.states.items() if (d := s.to_dict())}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ComponentStyle:
        unknown = set(data) - set(STATES)
        if unknown:
            raise ValueError(f"Unknown state(s): {', '.join(sorted(unknown))}")
        return cls({name: StateStyle.from_dict(d) for name, d in data.items()})


@dataclass
class GlobalStyle:
    """Theme-wide values: ``@accent`` in any color field resolves to ``accent``;
    ``opacity`` multiplies the alpha of every background; ``radius`` is the value
    "apply global to all components" copies into components."""

    accent: str = "#3b82f6"
    radius: int = 4
    opacity: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return {"accent": self.accent, "radius": self.radius, "opacity": self.opacity}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GlobalStyle:
        opacity = float(data.get("opacity", 1.0))
        if not 0.0 <= opacity <= 1.0:
            raise ValueError(f"Invalid opacity {opacity!r}; expected 0..1")
        accent = data.get("accent", cls.accent)
        parse_color(accent)
        return cls(accent=accent, radius=_length(data.get("radius", cls.radius)), opacity=opacity)


@dataclass
class FontSpec:
    """Global program font; ``None`` keeps QGIS's own value."""

    family: str | None = None
    point_size: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in (("family", self.family), ("point_size", self.point_size)) if v is not None}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FontSpec:
        size = data.get("point_size")
        if size is not None and float(size) <= 0:
            raise ValueError(f"Invalid font size {size!r}")
        return cls(family=data.get("family"), point_size=None if size is None else float(size))


@dataclass
class Theme:
    """A complete QUI theme."""

    name: str = "Untitled"
    base_ui_theme: str = "default"
    global_style: GlobalStyle = field(default_factory=GlobalStyle)
    font: FontSpec = field(default_factory=FontSpec)
    components: dict[str, ComponentStyle] = field(default_factory=dict)

    def component(self, component_id: str) -> ComponentStyle:
        """Return the style of *component_id*, creating an empty one if needed."""
        return self.components.setdefault(component_id, ComponentStyle())

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA_VERSION,
            "name": self.name,
            "base_ui_theme": self.base_ui_theme,
            "global": self.global_style.to_dict(),
            "font": self.font.to_dict(),
            "components": {cid: d for cid, c in self.components.items() if (d := c.to_dict())},
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Theme:
        schema = data.get("schema", SCHEMA_VERSION)
        if schema > SCHEMA_VERSION:
            raise ValueError(f"Theme uses schema {schema}; this QUI supports up to {SCHEMA_VERSION}")
        return cls(
            name=data.get("name", "Untitled"),
            base_ui_theme=data.get("base_ui_theme", "default"),
            global_style=GlobalStyle.from_dict(data.get("global", {})),
            font=FontSpec.from_dict(data.get("font", {})),
            components={cid: ComponentStyle.from_dict(c) for cid, c in data.get("components", {}).items()},
        )
