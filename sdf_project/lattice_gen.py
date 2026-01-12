"""
DXF Lattice Generator
Creates a lattice panel with square or triangle cutouts for laser cutting.

Example:
    python lattice_gen.py panel.dxf --pattern square --width 200 --height 120 --margin 10 --cell 20 --strut 4
    python lattice_gen.py panel.dxf --pattern triangle --width 200 --height 120 --margin 10 --cell 20 --strut 4
"""

import argparse
import math
import ezdxf


def add_rect(msp, x, y, w, h, layer):
    """Add a closed rectangle polyline with lower-left at (x, y)."""
    points = [
        (x, y),
        (x + w, y),
        (x + w, y + h),
        (x, y + h),
    ]
    msp.add_lwpolyline(points, close=True, dxfattribs={"layer": layer})


def add_triangle(msp, x, y, side, up, layer):
    """Add an equilateral triangle with bounding box lower-left at (x, y)."""
    h = side * math.sqrt(3) / 2.0
    if up:
        points = [
            (x, y),
            (x + side, y),
            (x + side / 2.0, y + h),
        ]
    else:
        points = [
            (x, y + h),
            (x + side, y + h),
            (x + side / 2.0, y),
        ]
    msp.add_lwpolyline(points, close=True, dxfattribs={"layer": layer})


def build_lattice(width, height, margin, cell, strut, out_path, pattern):
    if width <= 0 or height <= 0:
        raise ValueError("width/height must be positive")
    if margin < 0:
        raise ValueError("margin must be >= 0")
    if cell <= 0 or strut <= 0:
        raise ValueError("cell/strut must be positive")
    if cell <= strut:
        raise ValueError("cell must be larger than strut")

    hole = cell - strut
    avail_w = width - 2 * margin
    avail_h = height - 2 * margin
    if avail_w <= hole or avail_h <= hole:
        raise ValueError("margin too large for the given panel size")

    if pattern == "square":
        cols = int(math.floor((avail_w + strut) / cell))
        rows = int(math.floor((avail_h + strut) / cell))
        used_w = cols * cell - strut
        used_h = rows * cell - strut
    elif pattern == "triangle":
        tri_h = hole * math.sqrt(3) / 2.0
        cols = int(math.floor((avail_w - hole) / cell)) + 1
        rows = int(math.floor((avail_h - tri_h) / (cell * math.sqrt(3) / 2.0))) + 1
        used_w = (cols - 1) * cell + hole
        used_h = (rows - 1) * (cell * math.sqrt(3) / 2.0) + tri_h
    else:
        raise ValueError("pattern must be 'square' or 'triangle'")

    if cols <= 0 or rows <= 0:
        raise ValueError("panel too small for the given cell/strut")

    offset_x = margin + (avail_w - used_w) / 2.0
    offset_y = margin + (avail_h - used_h) / 2.0

    doc = ezdxf.new(setup=True)
    msp = doc.modelspace()
    doc.layers.new(name="OUTLINE")
    doc.layers.new(name="CUTOUTS")

    # Outer boundary
    add_rect(msp, 0, 0, width, height, layer="OUTLINE")

    # Cutout grid
    if pattern == "square":
        for r in range(rows):
            for c in range(cols):
                x = offset_x + c * cell
                y = offset_y + r * cell
                add_rect(msp, x, y, hole, hole, layer="CUTOUTS")
    else:
        tri_h = hole * math.sqrt(3) / 2.0
        pitch_y = cell * math.sqrt(3) / 2.0
        for r in range(rows):
            for c in range(cols):
                x = offset_x + c * cell
                y = offset_y + r * pitch_y
                up = (r + c) % 2 == 0
                add_triangle(msp, x, y, hole, up=up, layer="CUTOUTS")

    doc.saveas(out_path)


def main():
    parser = argparse.ArgumentParser(description="Generate a lattice DXF panel.")
    parser.add_argument("output", help="Output DXF path")
    parser.add_argument(
        "--pattern",
        choices=["square", "triangle"],
        default="square",
        help="Cutout pattern type",
    )
    parser.add_argument("--width", type=float, default=200.0, help="Panel width (mm)")
    parser.add_argument("--height", type=float, default=120.0, help="Panel height (mm)")
    parser.add_argument("--margin", type=float, default=10.0, help="Outer margin (mm)")
    parser.add_argument("--cell", type=float, default=20.0, help="Cell pitch (mm)")
    parser.add_argument("--strut", type=float, default=4.0, help="Strut thickness (mm)")
    args = parser.parse_args()

    build_lattice(
        width=args.width,
        height=args.height,
        margin=args.margin,
        cell=args.cell,
        strut=args.strut,
        out_path=args.output,
        pattern=args.pattern,
    )


if __name__ == "__main__":
    main()
