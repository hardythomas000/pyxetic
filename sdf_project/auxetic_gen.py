"""
DXF Auxetic Lattice Generator (Re-entrant Hex Cutouts)
Builds a panel with concave hex cutouts to create an auxetic-style lattice.

Example:
    python auxetic_gen.py auxetic.dxf --width 200 --height 120 --cell-w 24 --cell-h 16 --strut 3 --reentrant 6
    python auxetic_gen.py auxetic.dxf --curve --curve-steps 20
"""

import argparse
import math
from typing import List, Tuple

import ezdxf
from scipy.interpolate import CubicSpline
from scipy.optimize import brentq


Point = Tuple[float, float]


def polygon_area(points: List[Point]) -> float:
    """Signed area of a polygon."""
    area = 0.0
    for i, (x1, y1) in enumerate(points):
        x2, y2 = points[(i + 1) % len(points)]
        area += x1 * y2 - x2 * y1
    return 0.5 * area


def add_poly(msp, points: List[Point], layer: str):
    """Add a closed polyline."""
    msp.add_lwpolyline(points, close=True, dxfattribs={"layer": layer})


def add_rect(msp, x, y, w, h, layer):
    """Add a closed rectangle polyline with lower-left at (x, y)."""
    points = [
        (x, y),
        (x + w, y),
        (x + w, y + h),
        (x, y + h),
    ]
    add_poly(msp, points, layer)


def build_cell_points(
    w: float,
    h: float,
    r: float,
    curve: bool,
    curve_steps: int,
) -> List[Point]:
    """Build local points for a concave hex cutout."""
    if not curve:
        return [
            (0.0, 0.0),
            (w, 0.0),
            (w - r, h / 2.0),
            (w, h),
            (0.0, h),
            (r, h / 2.0),
        ]

    ys = [0.0, h / 2.0, h]
    right_xs = [w, w - r, w]
    left_xs = [0.0, r, 0.0]

    right_curve = CubicSpline(ys, right_xs, bc_type="natural")
    left_curve = CubicSpline(ys, left_xs, bc_type="natural")

    samples = max(6, curve_steps)
    y_vals = [h * i / (samples - 1) for i in range(samples)]
    right_pts = [(right_curve(y), y) for y in y_vals]
    left_pts = [(left_curve(y), y) for y in y_vals]

    points = []
    points.append((0.0, 0.0))
    points.append((w, 0.0))
    points.extend(right_pts[1:-1])
    points.append((w, h))
    points.append((0.0, h))
    points.extend(reversed(left_pts[1:-1]))
    return points


def hole_area(w: float, h: float, r: float) -> float:
    """Area of the straight-edge concave hex cutout."""
    pts = build_cell_points(w, h, r, curve=False, curve_steps=0)
    return abs(polygon_area(pts))


def solve_reentrant_for_open_ratio(
    w: float,
    h: float,
    target_ratio: float,
) -> float:
    """Solve for re-entrant offset to reach target open ratio for a single cell."""
    min_r = 0.0
    max_r = min(w / 2.0 - 1e-6, w - 1e-6)

    def f(r):
        return hole_area(w, h, r) / (w * h) - target_ratio

    return brentq(f, min_r + 1e-6, max_r)


def build_auxetic(
    out_path: str,
    width: float,
    height: float,
    margin: float,
    cell_w: float,
    cell_h: float,
    strut: float,
    reentrant: float,
    rows: int,
    cols: int,
    stagger: bool,
    curve: bool,
    curve_steps: int,
    open_ratio: float,
):
    if width <= 0 or height <= 0:
        raise ValueError("width/height must be positive")
    if margin < 0:
        raise ValueError("margin must be >= 0")
    if cell_w <= 0 or cell_h <= 0:
        raise ValueError("cell size must be positive")
    if strut <= 0:
        raise ValueError("strut must be positive")

    if open_ratio is not None:
        reentrant = solve_reentrant_for_open_ratio(cell_w, cell_h, open_ratio)

    if not (0.0 <= reentrant < cell_w / 2.0):
        raise ValueError("reentrant must be in [0, cell_w/2)")

    pitch_x = cell_w + strut
    pitch_y = cell_h + strut

    avail_w = width - 2 * margin
    avail_h = height - 2 * margin
    if avail_w <= cell_w or avail_h <= cell_h:
        raise ValueError("margin too large for the given panel size")

    if cols is None:
        cols = int(math.floor((avail_w + strut) / pitch_x))
    if rows is None:
        rows = int(math.floor((avail_h + strut) / pitch_y))
    if cols <= 0 or rows <= 0:
        raise ValueError("panel too small for the given cell/strut")

    used_w = cols * pitch_x - strut
    used_h = rows * pitch_y - strut
    offset_x = margin + (avail_w - used_w) / 2.0
    offset_y = margin + (avail_h - used_h) / 2.0

    doc = ezdxf.new(setup=True)
    msp = doc.modelspace()
    doc.layers.new(name="OUTLINE")
    doc.layers.new(name="CUTOUTS")

    add_rect(msp, 0, 0, width, height, layer="OUTLINE")

    cell_pts = build_cell_points(cell_w, cell_h, reentrant, curve, curve_steps)

    for r in range(rows):
        row_offset = (pitch_x / 2.0) if (stagger and r % 2 == 1) else 0.0
        for c in range(cols):
            x = offset_x + c * pitch_x + row_offset
            y = offset_y + r * pitch_y
            if x + cell_w > width - margin:
                continue
            if y + cell_h > height - margin:
                continue
            shifted = [(x + px, y + py) for (px, py) in cell_pts]
            add_poly(msp, shifted, layer="CUTOUTS")

    doc.saveas(out_path)


def main():
    parser = argparse.ArgumentParser(
        description="Generate an auxetic-style DXF lattice with re-entrant hex cutouts."
    )
    parser.add_argument("output", help="Output DXF path")
    parser.add_argument("--width", type=float, default=200.0, help="Panel width (mm)")
    parser.add_argument("--height", type=float, default=120.0, help="Panel height (mm)")
    parser.add_argument("--margin", type=float, default=10.0, help="Outer margin (mm)")
    parser.add_argument("--cell-w", type=float, default=24.0, help="Cell width (mm)")
    parser.add_argument("--cell-h", type=float, default=16.0, help="Cell height (mm)")
    parser.add_argument("--strut", type=float, default=3.0, help="Strut thickness (mm)")
    parser.add_argument("--reentrant", type=float, default=6.0, help="Re-entrant offset (mm)")
    parser.add_argument("--rows", type=int, default=None, help="Row count override")
    parser.add_argument("--cols", type=int, default=None, help="Column count override")
    parser.add_argument("--stagger", action="store_true", help="Stagger odd rows")
    parser.add_argument("--curve", action="store_true", help="Use curved concave edges")
    parser.add_argument("--curve-steps", type=int, default=18, help="Points per curved side")
    parser.add_argument(
        "--open-ratio",
        type=float,
        default=None,
        help="Target hole area ratio per cell (0-1), overrides --reentrant",
    )
    args = parser.parse_args()

    build_auxetic(
        out_path=args.output,
        width=args.width,
        height=args.height,
        margin=args.margin,
        cell_w=args.cell_w,
        cell_h=args.cell_h,
        strut=args.strut,
        reentrant=args.reentrant,
        rows=args.rows,
        cols=args.cols,
        stagger=args.stagger,
        curve=args.curve,
        curve_steps=args.curve_steps,
        open_ratio=args.open_ratio,
    )


if __name__ == "__main__":
    main()
