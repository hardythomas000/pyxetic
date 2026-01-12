"""
SDF 3D Generator (Implicit Fields -> STL)
Builds a 3D implicit surface and exports an STL via marching cubes.

Example:
    python sdf_3d.py gyroid.stl --size 60 --res 120 --scale 0.18 --iso 0.0
"""

import argparse
import math
from typing import Tuple

import numpy as np
from skimage import measure


def gyroid(x, y, z):
    return (
        np.sin(x) * np.cos(y)
        + np.sin(y) * np.cos(z)
        + np.sin(z) * np.cos(x)
    )


def sdf_field(
    grid: Tuple[np.ndarray, np.ndarray, np.ndarray],
    scale: float,
    iso: float,
):
    x, y, z = grid
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
    parser = argparse.ArgumentParser(
        description="Generate a 3D implicit surface (gyroid) and export STL."
    )
    parser.add_argument("output", help="Output STL path")
    parser.add_argument("--size", type=float, default=60.0, help="Cube size (mm)")
    parser.add_argument("--res", type=int, default=120, help="Grid resolution per axis")
    parser.add_argument("--scale", type=float, default=0.18, help="Gyroid scale factor")
    parser.add_argument("--iso", type=float, default=0.0, help="Iso level")
    args = parser.parse_args()

    size = args.size
    res = args.res
    if res < 10:
        raise ValueError("res must be >= 10")

    lin = np.linspace(-size / 2.0, size / 2.0, res, dtype=np.float32)
    x, y, z = np.meshgrid(lin, lin, lin, indexing="ij")
    field = sdf_field((x, y, z), scale=args.scale, iso=args.iso)

    verts, faces, _, _ = measure.marching_cubes(field, level=0.0, spacing=(lin[1] - lin[0],) * 3)
    marching_cubes_to_stl(verts, faces, args.output)


if __name__ == "__main__":
    main()
