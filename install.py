"""Install the three reference packages into one isolated directory (Python 3.11+)."""
import argparse
import os
import subprocess
import sys
import venv
from pathlib import Path


def run(*args):
    subprocess.run([str(a) for a in args], check=True)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--directory", required=True)
    p.add_argument("--gemini-cli", action="store_true", help="Also install official Gemini CLI 0.50.0 through npm")
    a = p.parse_args()
    if sys.version_info < (3, 11): p.error("Python 3.11+ required")
    root = Path(a.directory).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    repositories = []
    versions = {"axionorm": "v0.1.0", "parabiont-protocol": "v0.1.1", "paralax-mcp": "v0.1.1"}
    for name, version in versions.items():
        dest = root / "repos" / name
        if dest.exists():
            p.error(f"Refusing to overwrite {dest}; choose a fresh installation directory")
        dest.parent.mkdir(parents=True, exist_ok=True)
        run("git", "clone", "--depth", "1", "--branch", version, f"https://github.com/amiencoy/{name}.git", dest)
        repositories.append(dest)
    env = root / "venv"
    venv.EnvBuilder(with_pip=True).create(env)
    binary = env / ("Scripts" if os.name == "nt" else "bin")
    python = binary / ("python.exe" if os.name == "nt" else "python")
    constraints = repositories[2] / "constraints-tested.txt"
    # A new venv may inherit an old bundled pip; upgrade it before resolving packages.
    run(python, "-m", "pip", "install", "--upgrade", "--constraint", constraints, "pip")
    run(python, "-m", "pip", "install", "--constraint", constraints, *repositories)
    axionorm = binary / ("axionorm.exe" if os.name == "nt" else "axionorm")
    run(axionorm, "install-opa", "--directory", root / "runtime/opa")
    for name in ("runtime", "exports", "artifacts"):
        (root / name).mkdir(exist_ok=True)
    if a.gemini_cli:
        run("npm", "install", "--prefix", root / "client", "--save-exact", "@google/gemini-cli@0.50.0")
    print(f"Installed. Activate {binary}; then follow repos/paralax-mcp/docs/DESKTOP.md.")
    if a.gemini_cli:
        print(f"Add {root / 'client/node_modules/.bin'} to PATH before launching Gemini or AionUi.")


if __name__ == "__main__": main()
