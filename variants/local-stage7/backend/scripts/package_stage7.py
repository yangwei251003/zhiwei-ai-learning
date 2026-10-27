"""Build stage-7 release archives from explicit, safe file sets."""

from __future__ import annotations

import hashlib
import shutil
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "output" / "stage-7"
STAGING = OUT / "staging"
SENSITIVE_PARTS = {".env", ".git", ".venv", "node_modules", "__pycache__"}
SENSITIVE_SUFFIXES = {".db", ".faiss", ".journal"}


def unsafe(relative: Path) -> bool:
    return (
        any(part.lower() in SENSITIVE_PARTS for part in relative.parts)
        or relative.suffix.lower() in SENSITIVE_SUFFIXES
        or relative.name.startswith("~$")
    )


def copy_tree(source: Path, destination: Path, include=None) -> None:
    for file in source.rglob("*"):
        if not file.is_file():
            continue
        relative = file.relative_to(source)
        if unsafe(relative) or (include is not None and not include(relative)):
            continue
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file, target)


def add_tree(archive: zipfile.ZipFile, source: Path, prefix: str, include=None) -> None:
    for file in source.rglob("*"):
        if not file.is_file():
            continue
        relative = file.relative_to(source)
        if unsafe(relative) or (include is not None and not include(relative)):
            continue
        archive.write(file, f"{prefix}/{relative.as_posix()}")


def verify_zip(path: Path) -> None:
    with zipfile.ZipFile(path) as archive:
        broken = archive.testzip()
        if broken:
            raise RuntimeError(f"ZIP integrity failure: {broken}")
        for name in archive.namelist():
            member = Path(name)
            if member.is_absolute() or ".." in member.parts or unsafe(member):
                raise RuntimeError(f"Unsafe archive member: {name}")


def write_sha256(path: Path) -> str:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    path.with_suffix(path.suffix + ".sha256").write_text(
        f"{digest}  {path.name}\n", encoding="utf-8"
    )
    return digest


def source_package() -> Path:
    target = OUT / "小智析析-作品源码.zip"
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED, allowZip64=True) as archive:
        for name in (
            "README.md",
            "SPEC.md",
            "PRODUCT.md",
            "DESIGN.md",
            "启动小智析析.bat",
            ".gitignore",
            ".gitattributes",
        ):
            archive.write(ROOT / name, f"小智析析/{name}")
        add_tree(
            archive,
            ROOT / "backend",
            "小智析析/backend",
            lambda p: (
                p.parts[0] in {"app", "alembic", "scripts", "tests"}
                or p.name
                in {
                    "requirements.txt",
                    "requirements-dev.txt",
                    "alembic.ini",
                    "pytest.ini",
                    ".env.example",
                }
            ),
        )
        add_tree(
            archive,
            ROOT / "frontend",
            "小智析析/frontend",
            lambda p: (
                p.parts[0] in {"src", "public", "tests", "e2e"}
                or p.name
                in {
                    "package.json",
                    "package-lock.json",
                    "vite.config.js",
                    "playwright.config.js",
                    "index.html",
                }
            ),
        )
        add_tree(
            archive,
            ROOT / "documents",
            "小智析析/documents",
            lambda p: p.suffix.lower() in {".docx", ".pptx", ".mp4"},
        )
        add_tree(
            archive,
            ROOT / "research",
            "小智析析/research",
            lambda p: p.suffix.lower() in {".md", ".json"},
        )
    return target


def materials_package() -> Path:
    target = OUT / "小智析析-PPT视频文档.zip"
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED, allowZip64=True) as archive:
        for file in sorted((ROOT / "documents").iterdir()):
            if file.name == "PPT.pptx":
                continue
            if unsafe(Path(file.name)):
                continue
            if file.suffix.lower() in {".docx", ".pptx", ".mp4"}:
                archive.write(file, f"小智析析-比赛材料/{file.name}")
        archive.writestr(
            "小智析析-比赛材料/README.txt",
            "本包为阶段 6 真实证据生成的比赛材料。PPT 请使用 PPT-修复版.pptx。\n",
        )
    return target


def installer_package() -> Path:
    bundle = STAGING / "小智析析-安装包"
    (bundle / "backend").mkdir(parents=True, exist_ok=True)
    copy_tree(ROOT / "backend" / "app", bundle / "backend" / "app")
    copy_tree(
        ROOT / "backend" / "scripts",
        bundle / "backend" / "scripts",
        lambda p: p.name == "portable_server.py",
    )
    for name in ("requirements.txt", ".env.example"):
        shutil.copy2(ROOT / "backend" / name, bundle / "backend" / name)
    copy_tree(ROOT / "frontend" / "dist", bundle / "frontend_dist")
    start = bundle / "启动小智析析.bat"
    start.write_text(
        "@echo off\r\n"
        'cd /d "%~dp0"\r\n'
        "if not exist .env (\r\n"
        "  echo 请先将 backend\\.env.example 复制为 .env，并填写本机部署所需配置。\r\n"
        "  pause\r\n"
        "  exit /b 1\r\n"
        ")\r\n"
        "if not exist .venv\\Scripts\\python.exe (\r\n"
        "  py -3.13 -m venv .venv\r\n"
        "  call .venv\\Scripts\\python.exe -m pip install -r backend\\requirements.txt\r\n"
        ")\r\n"
        "set PYTHONPATH=%CD%\\backend\r\n"
        'start "小智析析" /B .venv\\Scripts\\python.exe backend\\scripts\\portable_server.py\r\n'
        "timeout /t 3 /nobreak >nul\r\n"
        'start "小智析析" http://127.0.0.1:8000\r\n',
        encoding="utf-8",
    )
    target = OUT / "小智析析-作品安装包.zip"
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED, allowZip64=True) as archive:
        add_tree(archive, bundle, "小智析析")
    return target


def registration_placeholder() -> Path:
    target = OUT / "报名表与学生证-待补充.txt"
    target.write_text(
        "报名表与学生证由参赛队自行提供。本项目不会生成或伪造个人证件。\n",
        encoding="utf-8",
    )
    return target


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    expected = {
        "installer": OUT / "小智析析-作品安装包.zip",
        "source": OUT / "小智析析-作品源码.zip",
        "materials": OUT / "小智析析-PPT视频文档.zip",
        "registration": OUT / "报名表与学生证-待补充.txt",
    }
    packages = []
    if not expected["installer"].exists():
        packages.append(installer_package())
    if not expected["source"].exists():
        packages.append(source_package())
    if not expected["materials"].exists():
        packages.append(materials_package())
    if not expected["registration"].exists():
        packages.append(registration_placeholder())
    packages.extend(path for path in expected.values() if path.exists())
    for package in dict.fromkeys(packages):
        if package.suffix == ".zip":
            verify_zip(package)
            print(f"{package.name} {write_sha256(package)}")
        else:
            print(package.name)


if __name__ == "__main__":
    main()
