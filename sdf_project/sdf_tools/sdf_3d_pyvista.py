"""
SDF 3D Generator (PyVista interactive preview + STL export)
Controls are slider widgets inside the 3D viewport.

Keys:
  s = export STL to sdf_pyvista.stl
  r = reset camera
"""

import argparse
import math
from typing import Dict

import numpy as np
import pyvista as pv


def gyroid(x, y, z):
    return (
        np.sin(x) * np.cos(y)
        + np.sin(y) * np.cos(z)
        + np.sin(z) * np.cos(x)
    )


def build_field(size, res, scale, iso):
    lin = np.linspace(-size / 2.0, size / 2.0, res, dtype=np.float32)
    x, y, z = np.meshgrid(lin, lin, lin, indexing="ij")
    field = gyroid(x * scale, y * scale, z * scale) - iso
    spacing = (lin[1] - lin[0],) * 3
    origin = (lin[0], lin[0], lin[0])
    return field, spacing, origin


def field_to_mesh(field, spacing, origin):
    grid = pv.ImageData()
    grid.dimensions = field.shape
    grid.origin = origin
    grid.spacing = spacing
    grid.point_data["values"] = field.ravel(order="F")
    return grid.contour([0.0])


def export_stl(state: Dict[str, float], out_path: str):
    field, spacing, origin = build_field(
        size=state["size"],
        res=int(state["export_res"]),
        scale=state["scale"],
        iso=state["iso"],
    )
    mesh = field_to_mesh(field, spacing, origin)
    mesh.save(out_path)


def main():
    parser = argparse.ArgumentParser(description="PyVista SDF preview and STL export.")
    parser.add_argument("--size", type=float, default=60.0, help="Size (mm)")
    parser.add_argument("--preview-res", type=int, default=60, help="Preview resolution")
    parser.add_argument("--export-res", type=int, default=140, help="Export resolution")
    parser.add_argument("--scale", type=float, default=0.18, help="Gyroid scale factor")
    parser.add_argument("--iso", type=float, default=0.0, help="Iso level")
    args = parser.parse_args()

    state = {
        "size": float(args.size),
        "preview_res": int(args.preview_res),
        "export_res": int(args.export_res),
        "scale": float(args.scale),
        "iso": float(args.iso),
    }

    plotter = pv.Plotter()
    plotter.set_background("#f7f4ef")
    sdf_actor = {"actor": None}

    def update_mesh(*_args, reset_camera=False):
        field, spacing, origin = build_field(
            size=state["size"],
            res=int(state["preview_res"]),
            scale=state["scale"],
            iso=state["iso"],
        )
        mesh = field_to_mesh(field, spacing, origin)
        if sdf_actor["actor"] is None:
            sdf_actor["actor"] = plotter.add_mesh(
                mesh,
                color="#1f6f5f",
                smooth_shading=True,
                name="sdf",
            )
        else:
            sdf_actor["actor"].mapper.SetInputData(mesh)
            sdf_actor["actor"].mapper.Update()
        if reset_camera:
            plotter.reset_camera()
        plotter.render()

    def on_size(value):
        state["size"] = max(10.0, float(value))
        update_mesh()

    def on_preview_res(value):
        state["preview_res"] = max(20, int(value))
        update_mesh()

    def on_scale(value):
        state["scale"] = float(value)
        update_mesh()

    def on_iso(value):
        state["iso"] = float(value)
        update_mesh()

    def on_export_res(value):
        state["export_res"] = max(30, int(value))

    def on_key_s():
        out_path = "sdf_pyvista.stl"
        export_stl(state, out_path)
        plotter.add_text(f"Saved {out_path}", position="lower_left", font_size=10, name="status")

    plotter.add_text("Scroll=zoom, drag=orbit, right-drag=pan | S=save STL", font_size=10)

    plotter.add_slider_widget(
        on_size, [20.0, 200.0], value=state["size"], title="Size (mm)", interaction_event="end"
    )
    plotter.add_slider_widget(
        on_preview_res,
        [20, 120],
        value=state["preview_res"],
        title="Preview Res",
        interaction_event="end",
        pointa=(0.02, 0.12),
        pointb=(0.32, 0.12),
    )
    plotter.add_slider_widget(
        on_export_res,
        [40, 220],
        value=state["export_res"],
        title="Export Res",
        interaction_event="end",
        pointa=(0.02, 0.18),
        pointb=(0.32, 0.18),
    )
    plotter.add_slider_widget(
        on_scale,
        [0.05, 0.6],
        value=state["scale"],
        title="Scale",
        interaction_event="always",
        pointa=(0.02, 0.24),
        pointb=(0.32, 0.24),
    )
    plotter.add_slider_widget(
        on_iso,
        [-1.0, 1.0],
        value=state["iso"],
        title="Iso",
        interaction_event="always",
        pointa=(0.02, 0.30),
        pointb=(0.32, 0.30),
    )

    plotter.add_key_event("s", on_key_s)

    update_mesh(reset_camera=True)
    plotter.show()


if __name__ == "__main__":
    main()
