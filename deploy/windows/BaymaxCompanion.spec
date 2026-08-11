from pathlib import Path

root = Path(SPECPATH).parents[1]
a = Analysis(
    [str(root / "deploy" / "windows" / "entrypoint.py")],
    pathex=[str(root / "src")],
    datas=[(str(root / "config" / "voice-models.toml"), "config")],
    hiddenimports=[],
    excludes=[],
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="BaymaxCompanion",
    console=True,
    icon=None,
)
