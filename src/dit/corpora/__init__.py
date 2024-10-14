import argparse
import json
import statistics
from typing import Final

from dit.commons import CORPORA_PATH, SUBMODULES_PATH
from dit.corpora.fetch_web_resources import cmd_fetch_web_resources
from dit.corpora.normalize import cmd_normalize

CORPORA: Final = tuple(
    sorted(p.name for p in CORPORA_PATH.iterdir() if p.is_dir() or p.is_symlink())
)
DATA_SIZE_SUFFIXES: Final = ("B", "KB", "MB", "GB", "TB")
ELTEC: Final = CORPORA_PATH / "ELTeC"


def cmd_link_submodules(*_):
    ELTEC.mkdir(exist_ok=True, parents=True)

    for directory in (CORPORA_PATH, ELTEC):
        for link in (p for p in directory.iterdir() if p.is_symlink()):
            link.unlink()

    for submodule in (p for p in SUBMODULES_PATH.iterdir() if p.is_dir()):
        if submodule.name.startswith("ELTeC-"):
            link = ELTEC / submodule.name.removeprefix("ELTeC-")
        else:
            link = CORPORA_PATH / submodule.name

        link.symlink_to(submodule)


def cmd_list(args: argparse.Namespace):
    if args.json:
        print(json.dumps(CORPORA))
    else:
        print("Available corpora:")
        for name in CORPORA:
            print(f"- {name}")


def fmt_ds(size: float | int):
    _size = float(size)
    exponent = 0
    while _size > 1024:
        _size /= 1024
        exponent += 1
    return f"{_size:.2f} {DATA_SIZE_SUFFIXES[exponent]}"


def cmd_summarize(*_):
    file_sizes: list[int] = []

    for directory, __, files in CORPORA_PATH.walk(follow_symlinks=True):
        for file in (directory / f for f in files if f.endswith(".xml")):
            file_sizes.append(file.stat().st_size)

    print(f"{len(file_sizes):,} XML documents amounting to {fmt_ds(sum(file_sizes))}.")
    print(f"Smallest document size: {fmt_ds(min(file_sizes))}")
    print(f"Largest document size: {fmt_ds(max(file_sizes))}")
    mean = statistics.mean(file_sizes)
    print(f"Average file size: {fmt_ds(mean)}")
    print(f"Median file size: {fmt_ds(statistics.median(file_sizes))}")
    print(f"File size stdev: {fmt_ds(statistics.pstdev(file_sizes, mu=mean))}")

    # TODO? unicode points
    # TODO? xml:lang and similar


__all__ = (
    "cmd_fetch_web_resources",
    cmd_link_submodules.__name__,
    cmd_list.__name__,
    cmd_normalize.__name__,
    cmd_summarize.__name__,
)
