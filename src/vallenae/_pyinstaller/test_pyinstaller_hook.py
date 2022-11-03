import subprocess

from PyInstaller import __main__ as pyi_main

SCRIPT = """
import vallenae as vae

# creating databases require the SQL schemas added by the hook
pridb = vae.io.PriDatabase("test.pridb", mode="rwc")
tradb = vae.io.TraDatabase("test.tradb", mode="rwc")
trfdb = vae.io.TrfDatabase("test.trfdb", mode="rwc")
"""


def test_hook(tmp_path):
    app_name = "testapp"
    app_path = tmp_path / (app_name + ".py")
    app_path.write_text(SCRIPT)

    work_path = tmp_path / "build"
    dist_path = tmp_path / "dist"
    args = [
        "--workpath", str(work_path),
        "--distpath", str(dist_path),
        "--specpath", str(tmp_path),
        str(app_path),
    ]
    pyi_main.run(args)

    frozen_path = dist_path / app_name / app_name
    subprocess.run([str(frozen_path)], check=True, cwd=tmp_path)
