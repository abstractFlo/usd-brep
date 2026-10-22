"""Give a built usd-brep wheel cadler's version, e.g. 1.0.1+cadler.1.

    python3 cadler/wheel-version.py <wheel> <version>

NVIDIA's wheel tooling refuses local version labels, so the wheels are built with upstream's version and
renamed afterwards: the .dist-info folder, `Version:` in METADATA, RECORD (paths and hashes)
and the file name. The new wheel is written next to the old one, which is removed; its path is
printed.
"""

from __future__ import annotations

import base64
import hashlib
import re
import sys
import zipfile
from pathlib import Path


def record_line(name: str, data: bytes) -> str:
    digest = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=").decode()
    return f"{name},sha256={digest},{len(data)}"


def main() -> None:
    src, version = Path(sys.argv[1]).resolve(), sys.argv[2]
    dist, old, tags = src.stem.split("-", 2)
    if old == version:
        print(src)
        return
    old_info, new_info = f"{dist}-{old}.dist-info/", f"{dist}-{version}.dist-info/"
    dst = src.with_name(f"{dist}-{version}-{tags}.whl")

    with zipfile.ZipFile(src) as zin, zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as zout:
        record = []
        for info in zin.infolist():
            name = info.filename
            if name == old_info + "RECORD":
                continue
            data = zin.read(info)
            if name.startswith(old_info):
                name = new_info + name[len(old_info) :]
            if name == new_info + "METADATA":
                data, n = re.subn(rb"^Version: .*$", f"Version: {version}".encode(), data, count=1, flags=re.M)
                if n != 1:
                    sys.exit(f"{src.name}: no Version line in METADATA")
            info.filename = name
            zout.writestr(info, data)
            if not name.endswith("/"):
                record.append(record_line(name, data))
        record.append(f"{new_info}RECORD,,")
        zout.writestr(new_info + "RECORD", "\n".join(record) + "\n")
    src.unlink()
    print(dst)


if __name__ == "__main__":
    main()
