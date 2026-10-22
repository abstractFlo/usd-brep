"""Pack a macOS usd-brep build into a wheel laid out like the official Linux/Windows ones.

    python3 cadler/macos-wheel.py <this checkout> <OpenUSD install> <out dir>

Everything sits flat in usd_brep/: the module, its libraries, the OpenUSD libraries it needs,
OpenUSD's plugin resources (usd/) and the omniSolid schema. The build links libpython by its
absolute build path; that becomes @rpath, found next to the interpreter (bin/../lib) or three
levels up in a relocatable Python (lib/python3.12/site-packages/usd_brep -> lib).
"""

from __future__ import annotations

import base64
import hashlib
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

TAG = "cp312-cp312-macosx_12_0_arm64"
RPATHS = ["@loader_path", "@executable_path/../lib", "@loader_path/../../.."]


def otool(args: list[str], path: Path) -> list[str]:
    return subprocess.run(["otool", *args, str(path)], check=True, capture_output=True, text=True).stdout.splitlines()


def deps(path: Path) -> list[str]:
    return [line.split(" (compatibility")[0].strip() for line in otool(["-L"], path)[1:]]


def rpaths(path: Path) -> list[str]:
    lines = otool(["-l"], path)
    return [lines[i + 2].split()[1] for i, line in enumerate(lines) if line.strip() == "cmd LC_RPATH"]


def closure(release: Path, start: Path) -> list[Path]:
    seen: dict[str, Path] = {}
    todo = [start]
    while todo:
        for dep in deps(todo.pop()):
            name = dep.removeprefix("@rpath/")
            if dep.startswith("@rpath/") and name not in seen and (release / name).is_file():
                seen[name] = release / name
                todo.append(release / name)
    return sorted(seen.values())


def install_name_tool(args: list[str], path: Path) -> None:
    if args:
        subprocess.run(["install_name_tool", *args, str(path)], check=True)


def fix_macho(path: Path) -> None:
    args: list[str] = []
    linked = deps(path)[1:]  # [0] is the library's own id
    for dep in linked:
        if dep.endswith("/libpython3.12.dylib") and not dep.startswith("@"):
            args += ["-change", dep, "@rpath/libpython3.12.dylib"]
    # delete and add in separate runs: install_name_tool refuses a path that is in both lists
    for rp in rpaths(path):
        args += ["-delete_rpath", rp]
    install_name_tool(args, path)
    if any(d.endswith("/libpython3.12.dylib") for d in linked):
        needed = RPATHS
    elif any(d.startswith("@rpath/") for d in linked):
        needed = RPATHS[:1]
    else:
        needed = []
    install_name_tool([a for rp in needed for a in ("-add_rpath", rp)], path)
    subprocess.run(["strip", "-x", str(path)], check=True)
    subprocess.run(["codesign", "--force", "--sign", "-", str(path)], check=True, capture_output=True)
    for dep in deps(path):
        if not dep.startswith(("@rpath/", "/usr/lib/", "/System/")):
            sys.exit(f"{path.name} still links {dep}")


def record_line(root: Path, path: Path) -> str:
    data = path.read_bytes()
    digest = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=").decode()
    return f"{path.relative_to(root).as_posix()},sha256={digest},{len(data)}"


def main() -> None:
    repo, usd, out = (Path(a).resolve() for a in sys.argv[1:4])
    version = (repo / "VERSION").read_text().strip()  # upstream's; wheel-version.py adds cadler's label
    release = repo / "_build/macos-universal/release"
    module = release / "_omni_solid.cpython-312-darwin.so"

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        pkg = root / "usd_brep"
        shutil.copytree(release / "usd_brep", pkg)
        for lib in [module, *closure(release, module)]:
            shutil.copy2(lib, pkg / lib.name)
            fix_macho(pkg / lib.name)
        # usdShaders is a plugin library of its own (needs libraries we do not ship)
        shutil.copytree(release / "usd", pkg / "usd", ignore=shutil.ignore_patterns("usdShaders*"))
        shutil.copytree(repo / "source/schema/omniSolid/resources", pkg / "omniSolid/resources",
                        ignore=shutil.ignore_patterns("schema.usda"))

        info = root / f"usd_brep-{version}.dist-info"
        (info / "licenses").mkdir(parents=True)
        shutil.copy2(repo / "LICENSE", info / "licenses/LICENSE")
        shutil.copy2(repo / "THIRD_PARTY_NOTICES.md", info / "licenses/THIRD_PARTY_NOTICES.md")
        shutil.copy2(usd / "LICENSE.txt", info / "licenses/OpenUSD-LICENSE.txt")
        (info / "METADATA").write_text(
            "Metadata-Version: 2.4\nName: usd-brep\nVersion: " + version + "\n"
            "Summary: BRep solid modeling with native OpenUSD import and export (macOS build for cadler).\n"
            "Home-page: https://github.com/abstractFlo/usd-brep\nLicense-Expression: Apache-2.0\n"
            "Requires-Python: <3.13,>=3.12\n"
        )
        (info / "WHEEL").write_text(f"Wheel-Version: 1.0\nGenerator: cadler\nRoot-Is-Purelib: false\nTag: {TAG}\n")
        (info / "top_level.txt").write_text("usd_brep\n")

        files = sorted(p for p in root.rglob("*") if p.is_file())
        record = info / "RECORD"
        record.write_text("\n".join([*(record_line(root, p) for p in files), f"{record.relative_to(root).as_posix()},,"]) + "\n")

        out.mkdir(parents=True, exist_ok=True)
        wheel = out / f"usd_brep-{version}-{TAG}.whl"
        with zipfile.ZipFile(wheel, "w", zipfile.ZIP_DEFLATED) as zf:
            for p in [*files, record]:
                zf.write(p, p.relative_to(root).as_posix())
    print(wheel)


if __name__ == "__main__":
    main()
