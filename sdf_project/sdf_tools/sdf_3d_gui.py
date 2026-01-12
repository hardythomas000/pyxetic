"""
SDF 3D Generator GUI (Tkinter + sliders)
Live preview of a gyroid slice and STL export.
"""

import tkinter as tk
from tkinter import filedialog, messagebox

import numpy as np
import matplotlib

matplotlib.use("TkAgg")

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

from skimage import measure


def gyroid(x, y, z):
    return (
        np.sin(x) * np.cos(y)
        + np.sin(y) * np.cos(z)
        + np.sin(z) * np.cos(x)
    )


def sdf_field(x, y, z, scale, iso):
    return gyroid(x * scale, y * scale, z * scale) - iso


def marching_cubes_to_stl(verts, faces, out_path):
    with open(out_path, "w", encoding="ascii") as f:
        f.write("solid sdf\n")
        for face in faces:
            a = verts[face[0]]
            b = verts[face[1]]
            c = verts[face[2]]
            n = np.cross(b - a, c - a)
            n_norm = np.linalg.norm(n)
            if n_norm > 1e-9:
                n = n / n_norm
            else:
                n = np.array([0.0, 0.0, 0.0])
            f.write(
                "  facet normal {:.6e} {:.6e} {:.6e}\n".format(n[0], n[1], n[2])
            )
            f.write("    outer loop\n")
            f.write(
                "      vertex {:.6e} {:.6e} {:.6e}\n".format(a[0], a[1], a[2])
            )
            f.write(
                "      vertex {:.6e} {:.6e} {:.6e}\n".format(b[0], b[1], b[2])
            )
            f.write(
                "      vertex {:.6e} {:.6e} {:.6e}\n".format(c[0], c[1], c[2])
            )
            f.write("    endloop\n")
            f.write("  endfacet\n")
        f.write("endsolid sdf\n")


def main():
    root = tk.Tk()
    root.title("SDF Gyroid STL Generator")
    root.geometry("1000x600")

    size_var = tk.DoubleVar(value=60.0)
    res_var = tk.IntVar(value=120)
    scale_var = tk.DoubleVar(value=0.18)
    iso_var = tk.DoubleVar(value=0.0)
    status_var = tk.StringVar(value="Ready")

    root.columnconfigure(1, weight=1)
    root.rowconfigure(0, weight=1)

    form = tk.Frame(root, padx=12, pady=12)
    form.grid(row=0, column=0, sticky="nsew")
    preview = tk.Frame(root, padx=8, pady=8)
    preview.grid(row=0, column=1, sticky="nsew")
    preview.columnconfigure(0, weight=1)
    preview.rowconfigure(0, weight=1)

    fig = Figure(figsize=(6, 4), dpi=100)
    ax = fig.add_subplot(111, projection="3d")
    canvas = FigureCanvasTkAgg(fig, master=preview)
    canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")

    pending = {"after_id": None}
    nav = {"dragging": False, "button": None, "last": (0, 0)}

    def build_grid(size, res):
        lin = np.linspace(-size / 2.0, size / 2.0, res, dtype=np.float32)
        return np.meshgrid(lin, lin, lin, indexing="ij"), lin

    def update_preview():
        try:
            size = float(size_var.get())
            res = int(res_var.get())
            scale = float(scale_var.get())
            iso = float(iso_var.get())

            if size <= 0 or res < 10:
                raise ValueError("size must be > 0 and res >= 10")

            ax.clear()
            ax.set_aspect("equal", adjustable="box")
            ax.set_xticks([])
            ax.set_yticks([])
            ax.set_zticks([])
            ax.set_facecolor("#f7f4ef")

            res_preview = max(20, min(80, res // 2))
            lin = np.linspace(-size / 2.0, size / 2.0, res_preview, dtype=np.float32)
            x, y, z = np.meshgrid(lin, lin, lin, indexing="ij")
            field = sdf_field(x, y, z, scale, iso)
            spacing = (lin[1] - lin[0],) * 3
            verts, faces, _, _ = measure.marching_cubes(field, level=0.0, spacing=spacing)

            mesh = Poly3DCollection(verts[faces], alpha=0.7)
            mesh.set_facecolor("#1f6f5f")
            mesh.set_edgecolor("none")
            ax.add_collection3d(mesh)

            ax.set_xlim(lin[0], lin[-1])
            ax.set_ylim(lin[0], lin[-1])
            ax.set_zlim(lin[0], lin[-1])
            try:
                ax.set_box_aspect((1, 1, 1))
            except Exception:
                pass
            canvas.draw_idle()
            status_var.set("Preview updated")
        except Exception as exc:
            ax.clear()
            ax.set_xticks([])
            ax.set_yticks([])
            canvas.draw_idle()
            status_var.set(str(exc))

    def zoom_view(factor):
        xlim = ax.get_xlim()
        ylim = ax.get_ylim()
        zlim = ax.get_zlim()
        cx = (xlim[0] + xlim[1]) / 2.0
        cy = (ylim[0] + ylim[1]) / 2.0
        cz = (zlim[0] + zlim[1]) / 2.0
        dx = (xlim[1] - xlim[0]) * factor / 2.0
        dy = (ylim[1] - ylim[0]) * factor / 2.0
        dz = (zlim[1] - zlim[0]) * factor / 2.0
        ax.set_xlim(cx - dx, cx + dx)
        ax.set_ylim(cy - dy, cy + dy)
        ax.set_zlim(cz - dz, cz + dz)
        canvas.draw_idle()

    def on_scroll(event):
        if event.button == "up":
            zoom_view(0.9)
        elif event.button == "down":
            zoom_view(1.1)

    def on_press(event):
        if event.button in (1, 3):
            nav["dragging"] = True
            nav["button"] = event.button
            nav["last"] = (event.x, event.y)

    def on_release(event):
        nav["dragging"] = False
        nav["button"] = None

    def on_motion(event):
        if not nav["dragging"]:
            return
        last_x, last_y = nav["last"]
        dx = event.x - last_x
        dy = event.y - last_y
        nav["last"] = (event.x, event.y)

        if nav["button"] == 1:
            ax.view_init(elev=ax.elev - dy * 0.3, azim=ax.azim - dx * 0.3)
            canvas.draw_idle()
        elif nav["button"] == 3:
            bbox = ax.bbox
            if bbox.width == 0 or bbox.height == 0:
                return
            xlim = ax.get_xlim()
            ylim = ax.get_ylim()
            x_range = xlim[1] - xlim[0]
            y_range = ylim[1] - ylim[0]
            pan_x = -dx / bbox.width * x_range
            pan_y = dy / bbox.height * y_range
            ax.set_xlim(xlim[0] + pan_x, xlim[1] + pan_x)
            ax.set_ylim(ylim[0] + pan_y, ylim[1] + pan_y)
            canvas.draw_idle()

    def schedule_preview(*_args):
        if pending["after_id"] is not None:
            root.after_cancel(pending["after_id"])
        pending["after_id"] = root.after(120, update_preview)

    def save_stl():
        try:
            size = float(size_var.get())
            res = int(res_var.get())
            scale = float(scale_var.get())
            iso = float(iso_var.get())
            if size <= 0 or res < 10:
                raise ValueError("size must be > 0 and res >= 10")

            out_path = filedialog.asksaveasfilename(
                title="Save STL",
                defaultextension=".stl",
                filetypes=[("STL files", "*.stl")],
            )
            if not out_path:
                return

            grid, lin = build_grid(size, res)
            field = sdf_field(grid[0], grid[1], grid[2], scale, iso)
            spacing = (lin[1] - lin[0],) * 3
            verts, faces, _, _ = measure.marching_cubes(field, level=0.0, spacing=spacing)
            marching_cubes_to_stl(verts, faces, out_path)
            messagebox.showinfo("Done", f"Saved STL:\n{out_path}")
        except Exception as exc:
            messagebox.showerror("Error", str(exc))

    for var in (size_var, res_var, scale_var, iso_var):
        var.trace_add("write", schedule_preview)

    canvas.mpl_connect("scroll_event", on_scroll)
    canvas.mpl_connect("button_press_event", on_press)
    canvas.mpl_connect("button_release_event", on_release)
    canvas.mpl_connect("motion_notify_event", on_motion)

    def bind_wheel(scale_widget, step):
        def on_wheel(event):
            delta = 1 if event.delta > 0 else -1
            scale_widget.set(scale_widget.get() + delta * step)
            return "break"

        scale_widget.bind("<MouseWheel>", on_wheel)

    tk.Label(form, text="Size (mm)").grid(row=0, column=0, sticky="w")
    size_scale = tk.Scale(
        form, variable=size_var, from_=20.0, to=200.0, resolution=1.0, orient="horizontal"
    )
    size_scale.grid(row=0, column=1, sticky="ew")
    bind_wheel(size_scale, 1.0)

    tk.Label(form, text="Resolution").grid(row=1, column=0, sticky="w")
    res_scale = tk.Scale(
        form, variable=res_var, from_=40, to=200, resolution=1, orient="horizontal"
    )
    res_scale.grid(row=1, column=1, sticky="ew")
    bind_wheel(res_scale, 1)

    tk.Label(form, text="Scale").grid(row=2, column=0, sticky="w")
    scale_scale = tk.Scale(
        form, variable=scale_var, from_=0.05, to=0.6, resolution=0.01, orient="horizontal"
    )
    scale_scale.grid(row=2, column=1, sticky="ew")
    bind_wheel(scale_scale, 0.01)

    tk.Label(form, text="Iso").grid(row=3, column=0, sticky="w")
    iso_scale = tk.Scale(
        form, variable=iso_var, from_=-1.0, to=1.0, resolution=0.01, orient="horizontal"
    )
    iso_scale.grid(row=3, column=1, sticky="ew")
    bind_wheel(iso_scale, 0.01)

    tk.Button(form, text="Export STL", command=save_stl).grid(
        row=4, column=0, columnspan=2, pady=6
    )
    tk.Label(form, text="View: scroll=zoom, left-drag=rotate, right-drag=pan").grid(
        row=5, column=0, columnspan=2, sticky="w"
    )
    tk.Label(form, textvariable=status_var).grid(
        row=6, column=0, columnspan=2, sticky="w"
    )

    update_preview()
    root.mainloop()


if __name__ == "__main__":
    main()
