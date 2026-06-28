#!/usr/bin/env python3
"""Bump or set semver versions across packages and Docker image tags."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# SDK runtime version must match pyproject (see AGENTS.md).
SDK_INIT_VERSION = REPO_ROOT / "python/sdk/src/experiment_tracker_sdk/__init__.py"
SDK_INIT_VERSION_RE = re.compile(
    r'^(__version__\s*=\s*)"([^"]+)"\s*$',
    re.MULTILINE,
)
DOCKER_COMPOSE = REPO_ROOT / "docker-compose.yml"
DOCKER_IMAGE_TAG_RE = re.compile(
    r"^([ \t]*x-image-tag:[ \t]*&image-tag[ \t]+)(\S+)[ \t]*$",
    re.MULTILINE,
)
DOCKER_IMAGE_TAG_DEFAULT_RE = re.compile(r"(\$\{IMAGE_TAG:-)([^}]+)(\})")

PYPROJECT_VERSION_RE = re.compile(
    r'^(version\s*=\s*)"([^"]+)"\s*$',
    re.MULTILINE,
)


@dataclass(frozen=True)
class Package:
    path: Path
    kind: str  # "npm" | "pyproject"
    label: str


def discover_packages(*, include_examples: bool) -> list[Package]:
    packages: list[Package] = []

    for path in sorted(REPO_ROOT.glob("apps/*/package.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data.get("version"), str):
            packages.append(Package(path, "npm", path.parent.name))

    for path in sorted(REPO_ROOT.glob("python/*/pyproject.toml")):
        packages.append(
            Package(path, "pyproject", path.parent.relative_to(REPO_ROOT).as_posix())
        )

    if include_examples:
        for path in sorted(REPO_ROOT.glob("examples/*/pyproject.toml")):
            packages.append(
                Package(
                    path,
                    "pyproject",
                    path.parent.relative_to(REPO_ROOT).as_posix(),
                )
            )

    return packages


def read_version(pkg: Package) -> str:
    if pkg.kind == "npm":
        return json.loads(pkg.path.read_text(encoding="utf-8"))["version"]
    match = PYPROJECT_VERSION_RE.search(pkg.path.read_text(encoding="utf-8"))
    if not match:
        raise ValueError(f"No version = in {pkg.path}")
    return match.group(2)


def is_docker_image_package(pkg: Package) -> bool:
    rel_parts = pkg.path.relative_to(REPO_ROOT).parts
    return rel_parts[:2] in {
        ("apps", "web"),
        ("python", "backend"),
        ("python", "object_storage"),
        ("python", "scalars_service"),
    }


def read_docker_compose_version() -> str | None:
    if not DOCKER_COMPOSE.is_file():
        return None
    text = DOCKER_COMPOSE.read_text(encoding="utf-8")
    versions: list[str] = []
    anchor_match = DOCKER_IMAGE_TAG_RE.search(text)
    if anchor_match:
        versions.append(anchor_match.group(2))
    versions.extend(
        match.group(2) for match in DOCKER_IMAGE_TAG_DEFAULT_RE.finditer(text)
    )
    unique_versions = sorted(set(versions))
    if not unique_versions:
        return None
    if len(unique_versions) != 1:
        rel = DOCKER_COMPOSE.relative_to(REPO_ROOT)
        raise ValueError(
            f"Multiple IMAGE_TAG defaults in {rel}: {', '.join(unique_versions)}"
        )
    return unique_versions[0]


def parse_semver(version: str) -> tuple[int, int, int, str]:
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)(.*)", version)
    if not match:
        raise ValueError(f"Not semver X.Y.Z: {version!r}")
    major, minor, patch, suffix = match.groups()
    if suffix and not suffix.startswith("-"):
        raise ValueError(f"Unsupported suffix (use -prerelease only): {version!r}")
    return int(major), int(minor), int(patch), suffix


def bump_semver(version: str, part: str) -> str:
    major, minor, patch, suffix = parse_semver(version)
    if suffix:
        raise ValueError(f"Cannot bump version with suffix: {version!r}")
    if part == "major":
        return f"{major + 1}.0.0"
    if part == "minor":
        return f"{major}.{minor + 1}.0"
    if part == "patch":
        return f"{major}.{minor}.{patch + 1}"
    raise ValueError(f"Unknown bump part: {part!r}")


def write_npm_version(path: Path, version: str) -> None:
    text = path.read_text(encoding="utf-8")
    data = json.loads(text)
    data["version"] = version
    newline = "\n" if text.endswith("\n") else ""
    indent = 4 if text.lstrip().startswith("{\n    ") else 2
    path.write_text(json.dumps(data, indent=indent) + newline, encoding="utf-8")


def write_pyproject_version(path: Path, version: str) -> None:
    text = path.read_text(encoding="utf-8")
    if not PYPROJECT_VERSION_RE.search(text):
        raise ValueError(f"No version = in {path}")
    updated, count = PYPROJECT_VERSION_RE.subn(
        rf'\1"{version}"',
        text,
        count=1,
    )
    if count != 1:
        raise ValueError(f"Expected one version line in {path}")
    path.write_text(updated, encoding="utf-8")


def sync_docker_compose(version: str, *, dry_run: bool) -> bool:
    current = read_docker_compose_version()
    if current is None:
        return False
    rel = DOCKER_COMPOSE.relative_to(REPO_ROOT)
    if current == version:
        print(f"  {rel}: unchanged ({version})")
        return False
    if dry_run:
        print(f"  would update {rel}: {current} -> {version}")
        return True

    text = DOCKER_COMPOSE.read_text(encoding="utf-8")
    updated, anchor_count = DOCKER_IMAGE_TAG_RE.subn(
        rf"\g<1>{version}",
        text,
        count=1,
    )
    updated, default_count = DOCKER_IMAGE_TAG_DEFAULT_RE.subn(
        rf"\g<1>{version}\g<3>",
        updated,
    )
    if anchor_count != 1:
        raise ValueError(f"Expected one x-image-tag anchor in {rel}")
    if default_count < 1:
        raise ValueError(f"Expected at least one IMAGE_TAG default in {rel}")
    DOCKER_COMPOSE.write_text(updated, encoding="utf-8")
    print(f"  updated {rel}: {current} -> {version}")
    return True


def sync_sdk_init(version: str, *, dry_run: bool) -> bool:
    if not SDK_INIT_VERSION.is_file():
        return False
    text = SDK_INIT_VERSION.read_text(encoding="utf-8")
    match = SDK_INIT_VERSION_RE.search(text)
    if not match:
        raise ValueError(f"No __version__ in {SDK_INIT_VERSION}")
    current = match.group(2)
    if current == version:
        return False
    if dry_run:
        print(f"  would update {SDK_INIT_VERSION.relative_to(REPO_ROOT)}: {current} -> {version}")
        return True
    updated, count = SDK_INIT_VERSION_RE.subn(
        rf'\1"{version}"',
        text,
        count=1,
    )
    SDK_INIT_VERSION.write_text(updated, encoding="utf-8")
    print(f"  updated {SDK_INIT_VERSION.relative_to(REPO_ROOT)}: {current} -> {version}")
    return True


def apply_version(pkg: Package, version: str, *, dry_run: bool) -> None:
    current = read_version(pkg)
    rel = pkg.path.relative_to(REPO_ROOT)
    if current == version:
        print(f"  {rel}: unchanged ({version})")
        return
    print(f"  {rel}: {current} -> {version}")
    if dry_run:
        return
    if pkg.kind == "npm":
        write_npm_version(pkg.path, version)
    else:
        write_pyproject_version(pkg.path, version)


def cmd_list(packages: list[Package]) -> int:
    if not packages:
        print("No packages found.", file=sys.stderr)
        return 1
    width = max(len(p.label) for p in packages)
    for pkg in packages:
        print(f"{pkg.label:<{width}}  {read_version(pkg)}")
    docker_version = read_docker_compose_version()
    if docker_version is not None:
        print(f"{'docker-compose':<{width}}  {docker_version}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Update versions in apps/*/package.json, python/*/pyproject.toml, "
            "and docker-compose.yml."
        ),
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--list",
        action="store_true",
        help="Print current versions and exit.",
    )
    group.add_argument(
        "--set",
        metavar="VERSION",
        help='Set every package to this semver (e.g. "1.2.3").',
    )
    group.add_argument(
        "--bump",
        choices=("major", "minor", "patch"),
        help="Bump each package from its current version.",
    )
    parser.add_argument(
        "--include-examples",
        action="store_true",
        help="Also update examples/*/pyproject.toml.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned changes without writing files.",
    )
    args = parser.parse_args()

    packages = discover_packages(include_examples=args.include_examples)
    if not packages:
        print("No packages found.", file=sys.stderr)
        return 1

    if args.list:
        return cmd_list(packages)

    if args.set:
        try:
            parse_semver(args.set)
        except ValueError as exc:
            print(exc, file=sys.stderr)
            return 1
        target_for_all = args.set
    else:
        target_for_all = None

    sdk_pyproject = REPO_ROOT / "python/sdk/pyproject.toml"
    sdk_target_version: str | None = None
    package_targets: list[tuple[Package, str]] = []

    for pkg in packages:
        if target_for_all is not None:
            new_version = target_for_all
        else:
            new_version = bump_semver(read_version(pkg), args.bump)
        package_targets.append((pkg, new_version))
        if pkg.path == sdk_pyproject:
            sdk_target_version = new_version

    docker_target_versions = sorted(
        {
            version
            for pkg, version in package_targets
            if is_docker_image_package(pkg)
        }
    )
    if len(docker_target_versions) != 1:
        print(
            "Cannot update docker-compose.yml because packages target multiple versions: "
            + ", ".join(docker_target_versions),
            file=sys.stderr,
        )
        return 1

    prefix = "Would update" if args.dry_run else "Updating"
    print(f"{prefix} {len(packages)} package(s):")

    for pkg, new_version in package_targets:
        apply_version(pkg, new_version, dry_run=args.dry_run)

    if sdk_target_version is not None:
        sync_sdk_init(sdk_target_version, dry_run=args.dry_run)
    sync_docker_compose(docker_target_versions[0], dry_run=args.dry_run)

    if args.dry_run:
        print("(dry run — no files written)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
