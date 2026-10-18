#!/usr/bin/env python3
"""Download and restore the frozen project records behind SciPIvot cases.

Each case points at one snapshot: the project exactly as it stood at the case's
commit, with no git history.  Snapshots live in the Hugging Face dataset
sun1245/SciPIvot as `snapshots/<project>/<commit>.tar.zst`; several cases can
share one.  This script downloads the snapshots a set of cases needs, checks
the archive's sha256, unpacks it, and checks the unpacked tree against the
`tree_sha256` recorded in data/snapshots.jsonl.

The dataset is gated: accept the terms once at
https://huggingface.co/datasets/sun1245/SciPIvot, then log in with
`hf auth login` (or set HF_TOKEN).

Example:
    python scripts/fetch_records.py --id case_000 --out records
    python scripts/fetch_records.py --all --out records
    python scripts/fetch_records.py --all --out records --remove-after-verify
"""
import argparse
import hashlib
import json
import os
import shutil
import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QUESTIONS = ROOT / "data" / "questions.json"
MANIFEST = ROOT / "data" / "snapshots.jsonl"
REPO_ID = "sun1245/SciPIvot"
CHUNK = 1 << 20


def _sha256_stream(handle) -> str:
    digest = hashlib.sha256()
    for chunk in iter(lambda: handle.read(CHUNK), b""):
        digest.update(chunk)
    return digest.hexdigest()


def _tree_line(kind: str, path: str, extra: str = "", content: str = "") -> bytes:
    return f"{kind}\t{path}\t{extra}\t{content}\n".encode("utf-8", "surrogateescape")


def _tree_sha256(lines: list) -> str:
    digest = hashlib.sha256()
    for line in sorted(lines):
        digest.update(line)
    return digest.hexdigest()


def tree_sha256_dir(directory: Path) -> tuple:
    """Digest of an unpacked tree: every directory, file and link under it.

    A file contributes its path, whether its owner may execute it, and the
    sha256 of its content; a link its target; a directory its path.  Times and
    owners are left out, so two unpackings of one archive always agree.
    Returns (tree_sha256, number of files).
    """
    directory = Path(directory)
    lines, files = [], 0
    for base, dirs, names in os.walk(directory):
        for name in dirs + names:
            full = Path(base) / name
            rel = full.relative_to(directory).as_posix()
            st = full.lstat()
            if full.is_symlink():
                lines.append(_tree_line("l", rel, os.readlink(full)))
                files += 1
            elif full.is_dir():
                lines.append(_tree_line("d", rel))
            else:
                with full.open("rb") as handle:
                    content = _sha256_stream(handle)
                lines.append(_tree_line("f", rel, "1" if st.st_mode & 0o100 else "0", content))
                files += 1
    return _tree_sha256(lines), files


class TarTree:
    """The same digest, computed from tar members as they stream past."""

    def __init__(self) -> None:
        self.lines, self.files = [], 0

    def add(self, member: tarfile.TarInfo, content_sha256: str = "") -> None:
        name = member.name.rstrip("/")
        if member.issym():
            self.lines.append(_tree_line("l", name, member.linkname))
            self.files += 1
        elif member.isdir():
            self.lines.append(_tree_line("d", name))
        elif member.isreg():
            self.lines.append(_tree_line("f", name, "1" if member.mode & 0o100 else "0",
                                         content_sha256))
            self.files += 1

    def digest(self) -> str:
        return _tree_sha256(self.lines)


def _zstd_reader(handle):
    try:
        import zstandard
    except ImportError:
        try:
            from compression import zstd  # Python 3.14+
        except ImportError:
            raise SystemExit("needs the zstandard package: pip install zstandard") from None
        return zstd.ZstdFile(handle)
    return zstandard.ZstdDecompressor().stream_reader(handle)


def unpack(archive: Path, target: Path) -> None:
    """Unpack one snapshot archive into `target`, which must not exist."""
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_name(target.name + ".partial")
    shutil.rmtree(partial, ignore_errors=True)
    partial.mkdir()
    with archive.open("rb") as raw, tarfile.open(fileobj=_zstd_reader(raw), mode="r|") as tar:
        tar.extractall(partial, filter="data")
    partial.rename(target)


def load_manifest(path: Path = MANIFEST) -> dict:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return {row["snapshot"]: row for row in rows}


def download(snapshot: str, revision: str | None = None) -> Path:
    try:
        from huggingface_hub import hf_hub_download
        from huggingface_hub.errors import GatedRepoError
    except ImportError:
        raise SystemExit("needs the huggingface_hub package: pip install huggingface_hub") from None
    try:
        return Path(hf_hub_download(REPO_ID, snapshot, repo_type="dataset", revision=revision))
    except GatedRepoError:
        raise SystemExit(
            f"no access to {REPO_ID}: accept the terms at "
            f"https://huggingface.co/datasets/{REPO_ID} and log in with `hf auth login`"
        ) from None


def restore(row: dict, out: Path, revision: str | None = None, keep_archive: bool = True) -> Path:
    """Download, check and unpack one snapshot; return its directory."""
    target = out / row["snapshot"].removeprefix("snapshots/").removesuffix(".tar.zst")
    if target.is_dir():
        return target
    archive = download(row["snapshot"], revision)
    with archive.open("rb") as handle:
        got = _sha256_stream(handle)
    if got != row["sha256"]:
        raise SystemExit(f"{row['snapshot']}: archive sha256 {got} != {row['sha256']}")
    unpack(archive, target)
    tree, files = tree_sha256_dir(target)
    if tree != row["tree_sha256"] or files != row["files"]:
        shutil.rmtree(target, ignore_errors=True)
        raise SystemExit(f"{row['snapshot']}: unpacked tree does not match the manifest")
    if not keep_archive:
        archive.resolve().unlink(missing_ok=True)
    return target


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--id", action="append", help="case id, e.g. case_000 (repeatable)")
    ap.add_argument("--all", action="store_true", help="every case")
    ap.add_argument("--out", default="records", help="where snapshots are unpacked")
    ap.add_argument("--revision", help="dataset revision (default: main)")
    ap.add_argument("--remove-after-verify", action="store_true",
                    help="delete each unpacked tree and its download after it checks out "
                         "(to verify all 248 cases on a small disk)")
    ap.add_argument("--questions", default=str(QUESTIONS))
    args = ap.parse_args()

    cases = json.loads(Path(args.questions).read_text(encoding="utf-8"))
    if args.all:
        selected = cases
    elif args.id:
        wanted = set(args.id)
        selected = [c for c in cases if c["id"] in wanted]
        missing = wanted - {c["id"] for c in selected}
        if missing:
            raise SystemExit(f"unknown case id: {', '.join(sorted(missing))}")
    else:
        ap.error("give --id CASE or --all")

    manifest = load_manifest()
    out = Path(args.out)
    snapshots = sorted({c["snapshot"] for c in selected})
    for i, snapshot in enumerate(snapshots, 1):
        row = manifest[snapshot]
        target = restore(row, out, args.revision, keep_archive=not args.remove_after_verify)
        print(f"[{i}/{len(snapshots)}] ok {snapshot} -> {target}", flush=True)
        if args.remove_after_verify:
            shutil.rmtree(target)
    if not args.remove_after_verify:
        for case in selected:
            path = out / case["snapshot"].removeprefix("snapshots/").removesuffix(".tar.zst")
            print(f"{case['id']}\t{path}")


if __name__ == "__main__":
    sys.exit(main())
