from PyInstaller.utils.hooks import collect_data_files

a = Analysis(["../../src/baymax/cli.py"], pathex=["../../src"], datas=collect_data_files("baymax"), hiddenimports=[], excludes=[])
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name="BaymaxCompanion", console=True, icon=None)
