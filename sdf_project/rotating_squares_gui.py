"""
Rotating Squares Auxetic DXF Generator (Tkinter GUI)
Creates a laser-cuttable panel with a rotating-squares lattice.
"""

import math
import tkinter as tk
from tkinter import filedialog, messagebox

import ezdxf
import matplotlib

matplotlib.use("TkAgg")

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from matplotlib.patches import Polygon, Rectangle


def add_rect(msp, x, y, w, h, layer):
    points = [
        (x, y),
        (x + w, y),
        (x + w, y + h),
        (x, y + h),
    ]
    msp.add_lwpolyline(points, close=True, dxfattribs={"layer": layer})


def rotated_polygon_points(cx, cy, size, angle_deg, sides):
    radius = size / math.sqrt(2.0)
    angle = math.radians(angle_deg)
    points = []
    for i in range(sides):
        a = angle + (2.0 * math.pi * i / sides)
        points.append((cx + radius * math.cos(a), cy + radius * math.sin(a)))
    return points


def build_rotating_squares_dxf(
    out_path,
    width,
    height,
    margin,
    square_size,
    sides,
    gap,
    angle_deg,
    rows,
    cols,
    alternate,
):
    if width <= 0 or height <= 0:
        raise ValueError("width/height must be positive")
    if margin < 0 or gap < 0:
        raise ValueError("margin/gap must be >= 0")
    if square_size <= 0:
        raise ValueError("base size must be positive")
    if sides < 3:
        raise ValueError("sides must be >= 3")
    if square_size + gap <= 0:
        raise ValueError("invalid square/gap combination")

    avail_w = width - 2 * margin
    avail_h = height - 2 * margin
    if avail_w < square_size or avail_h < square_size:
        raise ValueError("margin too large for the given panel size")

    pitch = square_size + gap

    if cols is None or cols <= 0:
        cols = int(math.floor((avail_w - square_size) / pitch)) + 1
    if rows is None or rows <= 0:
        rows = int(math.floor((avail_h - square_size) / pitch)) + 1
    if cols <= 0 or rows <= 0:
        raise ValueError("panel too small for the given square/gap")

    used_w = (cols - 1) * pitch + square_size
    used_h = (rows - 1) * pitch + square_size
    offset_x = margin + (avail_w - used_w) / 2.0 + square_size / 2.0
    offset_y = margin + (avail_h - used_h) / 2.0 + square_size / 2.0

    doc = ezdxf.new(setup=True)
    msp = doc.modelspace()
    doc.layers.new(name="OUTLINE")
    doc.layers.new(name="CUTOUTS")

    add_rect(msp, 0, 0, width, height, layer="OUTLINE")

    for r in range(rows):
        for c in range(cols):
            cx = offset_x + c * pitch
            cy = offset_y + r * pitch
            if alternate:
                ang = angle_deg if (r + c) % 2 == 0 else -angle_deg
            else:
                ang = angle_deg
            pts = rotated_polygon_points(cx, cy, square_size, ang, sides)
            msp.add_lwpolyline(pts, close=True, dxfattribs={"layer": "CUTOUTS"})

    doc.saveas(out_path)


def parse_int_or_none(value):
    value = value.strip()
    if not value:
        return None
    return int(value)


def parse_float(value, name):
    try:
        return float(value)
    except ValueError as exc:
        raise ValueError(f"Invalid {name}") from exc


def build_preview(ax, params):
    ax.clear()
    ax.set_aspect("equal", adjustable="box")
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_facecolor("#f7f4ef")

    width = params["width"]
    height = params["height"]
    margin = params["margin"]
    square_size = params["square_size"]
    sides = params["sides"]
    gap = params["gap"]
    angle = params["angle"]
    rows = params["rows"]
    cols = params["cols"]
    alternate = params["alternate"]

    pitch = square_size + gap
    avail_w = width - 2 * margin
    avail_h = height - 2 * margin

    if cols is None or cols <= 0:
        cols = int(math.floor((avail_w - square_size) / pitch)) + 1
    if rows is None or rows <= 0:
        rows = int(math.floor((avail_h - square_size) / pitch)) + 1

    used_w = (cols - 1) * pitch + square_size
    used_h = (rows - 1) * pitch + square_size
    offset_x = margin + (avail_w - used_w) / 2.0 + square_size / 2.0
    offset_y = margin + (avail_h - used_h) / 2.0 + square_size / 2.0

    ax.add_patch(
        Rectangle(
            (0, 0),
            width,
            height,
            fill=False,
            lw=1.0,
            edgecolor="#2a2a2a",
        )
    )

    for r in range(rows):
        for c in range(cols):
            cx = offset_x + c * pitch
            cy = offset_y + r * pitch
            if cx - square_size / 2.0 < margin or cx + square_size / 2.0 > width - margin:
                continue
            if cy - square_size / 2.0 < margin or cy + square_size / 2.0 > height - margin:
                continue
            ang = angle if (not alternate or (r + c) % 2 == 0) else -angle
            pts = rotated_polygon_points(cx, cy, square_size, ang, sides)
            ax.add_patch(Polygon(pts, closed=True, fill=True, facecolor="#1f6f5f", alpha=0.85))

    ax.set_xlim(-width * 0.02, width * 1.02)
    ax.set_ylim(-height * 0.02, height * 1.02)


def main():
    root = tk.Tk()
    root.title("Rotating Squares Auxetic DXF")

    defaults = {
        "width": 200.0,
        "height": 120.0,
        "margin": 10.0,
        "square_size": 18.0,
        "gap": 4.0,
        "angle": 18.0,
        "sides": 4,
        "rows": "",
        "cols": "",
        "output": "rotating_squares.dxf",
    }

    vars_ = {}
    for key, value in defaults.items():
        if key in ("rows", "cols", "output"):
            vars_[key] = tk.StringVar(value=value)
        elif key == "sides":
            vars_[key] = tk.IntVar(value=value)
        else:
            vars_[key] = tk.DoubleVar(value=value)
    alternate_var = tk.BooleanVar(value=True)
    status_var = tk.StringVar(value="Ready")

    pending = {"after_id": None}

    def browse_output():
        path = filedialog.asksaveasfilename(
            title="Save DXF",
            defaultextension=".dxf",
            filetypes=[("DXF files", "*.dxf")],
        )
        if path:
            vars_["output"].set(path)

    def generate():
        try:
            width = parse_float(vars_["width"].get(), "width")
            height = parse_float(vars_["height"].get(), "height")
            margin = parse_float(vars_["margin"].get(), "margin")
            square_size = parse_float(vars_["square_size"].get(), "square size")
            gap = parse_float(vars_["gap"].get(), "gap")
            angle = parse_float(vars_["angle"].get(), "angle")
            sides = int(vars_["sides"].get())
            rows = parse_int_or_none(vars_["rows"].get())
            cols = parse_int_or_none(vars_["cols"].get())
            out_path = vars_["output"].get().strip()
            if not out_path:
                raise ValueError("Output path required")

            build_rotating_squares_dxf(
                out_path=out_path,
                width=width,
                height=height,
                margin=margin,
                square_size=square_size,
                gap=gap,
                angle_deg=angle,
                sides=sides,
                rows=rows,
                cols=cols,
                alternate=alternate_var.get(),
            )
            messagebox.showinfo("Done", f"Saved DXF:\n{out_path}")
        except Exception as exc:
            messagebox.showerror("Error", str(exc))

    def read_params():
        width = parse_float(vars_["width"].get(), "width")
        height = parse_float(vars_["height"].get(), "height")
        margin = parse_float(vars_["margin"].get(), "margin")
        square_size = parse_float(vars_["square_size"].get(), "square size")
        gap = parse_float(vars_["gap"].get(), "gap")
        angle = parse_float(vars_["angle"].get(), "angle")
        sides = int(vars_["sides"].get())
        rows = parse_int_or_none(vars_["rows"].get())
        cols = parse_int_or_none(vars_["cols"].get())
        return {
            "width": width,
            "height": height,
            "margin": margin,
            "square_size": square_size,
            "gap": gap,
            "angle": angle,
            "sides": sides,
            "rows": rows,
            "cols": cols,
            "alternate": alternate_var.get(),
        }

    def update_preview():
        try:
            params = read_params()
            if params["width"] <= 0 or params["height"] <= 0:
                raise ValueError("width/height must be positive")
            if params["margin"] < 0 or params["gap"] < 0:
                raise ValueError("margin/gap must be >= 0")
            if params["square_size"] <= 0:
                raise ValueError("square size must be positive")
            build_preview(ax, params)
            canvas.draw_idle()
            status_var.set("Preview updated")
        except Exception as exc:
            ax.clear()
            ax.set_xticks([])
            ax.set_yticks([])
            canvas.draw_idle()
            status_var.set(str(exc))

    def schedule_preview(*_args):
        if pending["after_id"] is not None:
            root.after_cancel(pending["after_id"])
        pending["after_id"] = root.after(120, update_preview)

    for key in vars_:
        vars_[key].trace_add("write", schedule_preview)
    alternate_var.trace_add("write", schedule_preview)

    root.geometry("1000x600")
    root.columnconfigure(0, weight=0)
    root.columnconfigure(1, weight=1)
    root.rowconfigure(0, weight=1)

    form = tk.Frame(root, padx=12, pady=12)
    form.grid(row=0, column=0, sticky="nsew")
    preview = tk.Frame(root, padx=8, pady=8)
    preview.grid(row=0, column=1, sticky="nsew")
    preview.columnconfigure(0, weight=1)
    preview.rowconfigure(0, weight=1)

    fig = Figure(figsize=(6, 4), dpi=100)
    ax = fig.add_subplot(111)
    canvas = FigureCanvasTkAgg(fig, master=preview)

    fields = [
        ("Panel width (mm)", "width", "spin", {"from_": 10.0, "to": 2000.0, "increment": 1.0}),
        ("Panel height (mm)", "height", "spin", {"from_": 10.0, "to": 2000.0, "increment": 1.0}),
        ("Margin (mm)", "margin", "spin", {"from_": 0.0, "to": 500.0, "increment": 0.5}),
        ("Square size (mm)", "square_size", "spin", {"from_": 1.0, "to": 500.0, "increment": 0.5}),
        ("Gap (mm)", "gap", "spin", {"from_": 0.0, "to": 200.0, "increment": 0.5}),
        ("Rotation angle (deg)", "angle", "spin", {"from_": -90.0, "to": 90.0, "increment": 1.0}),
        ("Sides (3-10)", "sides", "spin", {"from_": 3, "to": 10, "increment": 1}),
        ("Rows (blank = auto)", "rows", "entry", {}),
        ("Cols (blank = auto)", "cols", "entry", {}),
        ("Output DXF", "output", "entry", {}),
    ]

    row = 0
    for label, key, kind, cfg in fields:
        tk.Label(form, text=label).grid(row=row, column=0, sticky="w", pady=2)
        if kind == "spin":
            entry = tk.Spinbox(
                form,
                textvariable=vars_[key],
                width=10,
                **cfg,
            )
        else:
            entry = tk.Entry(form, textvariable=vars_[key], width=28)
        entry.grid(row=row, column=1, sticky="ew", pady=2)
        if key == "output":
            tk.Button(form, text="Browse", command=browse_output).grid(
                row=row, column=2, padx=6, pady=2
            )
        row += 1

    tk.Label(form, text="Angle slider").grid(row=row, column=0, sticky="w", pady=2)
    angle_slider = tk.Scale(
        form,
        from_=-90.0,
        to=90.0,
        resolution=1.0,
        orient="horizontal",
        length=180,
        variable=vars_["angle"],
        command=schedule_preview,
    )
    angle_slider.grid(row=row, column=1, sticky="ew", pady=2)
    row += 1

    tk.Checkbutton(
        form, text="Alternate rotation (+/- angle)", variable=alternate_var
    ).grid(row=row, column=0, columnspan=2, sticky="w", pady=6)

    tk.Button(form, text="Generate DXF", command=generate).grid(
        row=row + 1, column=0, columnspan=3, pady=6
    )

    tk.Label(form, textvariable=status_var).grid(
        row=row + 2, column=0, columnspan=3, sticky="w"
    )

    canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")

    root.after(0, update_preview)
    root.mainloop()


if __name__ == "__main__":
    main()
