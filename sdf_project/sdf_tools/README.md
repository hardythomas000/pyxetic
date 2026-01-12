# SDF Tools

Small toolkit for implicit SDF experiments and STL export.

## Files
- `sdf_3d.py` - CLI gyroid STL generator (marching cubes)
- `sdf_3d_gui.py` - Tkinter GUI with 3D preview (Matplotlib)
- `sdf_3d_pyvista.py` - PyVista/VTK interactive viewer with in-viewport sliders
- `requirements-sdf.txt` - numpy + scikit-image for `sdf_3d.py`
- `requirements-sdf-pyvista.txt` - numpy + pyvista + vtk for `sdf_3d_pyvista.py`

## Quick start

### 1) CLI (scikit-image)
```powershell
pip install -r sdf_tools/requirements-sdf.txt
python sdf_tools/sdf_3d.py gyroid.stl --size 60 --res 120 --scale 0.18 --iso 0.0
```

### 2) GUI (Matplotlib)
```powershell
pip install -r sdf_tools/requirements-sdf.txt
python sdf_tools/sdf_3d_gui.py
```

### 3) PyVista (fast 3D viewport)
Use Python 3.12+ for `vtk` wheels.
```powershell
pip install -r sdf_tools/requirements-sdf-pyvista.txt
python sdf_tools/sdf_3d_pyvista.py
```

## PyVista controls
- Mouse: scroll = zoom, drag = orbit, right-drag = pan
- Sliders in viewport: size, preview res, export res, scale, iso
- Press `S` to export `sdf_pyvista.stl`
