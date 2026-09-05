"""Resolve the shared native pin without duplicating it in workflow YAML."""

import os
from pathlib import Path
import re


def read_core_pin(root: Path) -> str:
    pins = []
    for relative in (
        "CMakeLists.txt",
        "packages/taiyin-bazi/CMakeLists.txt",
        "packages/taiyin-ziwei/CMakeLists.txt",
    ):
        text = (root / relative).read_text(encoding="utf-8")
        values = []
        for name in ("TAIYIN_CORE_REVISION", "TAIYIN_CORE_ARCHIVE_SHA256"):
            matches = re.findall(r'set\(\s*' + name + r'\s+"([^"\r\n]+)"\s*\)', text)
            if len(matches) != 1:
                raise ValueError(f"{relative}: expected exactly one literal {name}")
            values.append(matches[0])
        revision, checksum = values
        if not re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+(?:-[A-Za-z0-9.-]+)?", revision):
            raise ValueError(f"{relative}: release core revision must be a version tag")
        if not re.fullmatch(r"[0-9a-f]{64}", checksum):
            raise ValueError(f"{relative}: invalid core archive SHA-256")
        pins.append(tuple(values))
    if len(set(pins)) != 1:
        raise ValueError(f"C++ revision/archive pins differ across packages: {pins}")
    return pins[0][0]


if __name__ == "__main__":
    revision = read_core_pin(Path.cwd())
    print(f"Validated shared C++ pin: {revision}")
    if "GITHUB_OUTPUT" in os.environ:
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
            output.write(f"revision={revision}\n")
