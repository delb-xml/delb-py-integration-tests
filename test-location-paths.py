from __future__ import annotations

import argparse
import multiprocessing as mp
import random
from itertools import batched
from pathlib import Path
from typing import TYPE_CHECKING, Final

from tqdm import tqdm

from _delb.plugins.core_loaders import path_loader
from delb import (
    get_traverser,
    is_tag_node,
    Document,
    FailedDocumentLoading,
    ParserOptions,
    TagNode,
)

if TYPE_CHECKING:
    from collections.abc import Iterable


DIT_PATH: Final = Path(__file__).parent


traverse = get_traverser(True, True, True)


def verify_location_paths(file: Path, sample_volume: int):
    try:
        document = Document(
            file,
            parser_options=ParserOptions(
                reduce_whitespace=False, resolve_entities=False, unplugged=True
            ),
        )
    except FailedDocumentLoading as exc:
        print(
            f"\nFailed to load {file.name}: {exc.excuses[path_loader]}",
            end="",
        )
        return

    root = document.root
    for node in traverse(root, is_tag_node):
        if random.randint(1, 100) > sample_volume:
            continue

        assert isinstance(node, TagNode)
        query_results = document.xpath(node.location_path)
        if not (query_results.size == 1 and query_results.first is node):
            print(
                f"\nXPath query `{node.location_path}` in {file} yielded unexpected "
                "results."
            )


def dispatch_batch(files: Iterable[Path], sample_volume: int):
    for file in files:
        try:
            verify_location_paths(file, sample_volume)
        except Exception as e:
            print(f"\nUnhandled exception while testing {file}: {e}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-size", "-b", type=int, default=128)
    parser.add_argument("--cpus", type=int, default=mp.cpu_count())
    parser.add_argument("--sample-volume", "-s", type=int, default=25)
    parser.add_argument(
        "--corpus_path", "--src", type=Path, default=DIT_PATH / "corpora"
    )
    return parser.parse_args()


def main():
    mp.set_start_method("forkserver")
    args = parse_args()

    all_files: list[Path] = []
    for directory_path, _, files in args.corpus_path.walk(follow_symlinks=True):
        all_files.extend(directory_path / f for f in files if f.endswith(".xml"))
    all_files_size = len(all_files)
    sample_size = int(all_files_size / 100 * args.sample_volume)
    selected_files = random.choices(all_files, k=sample_size)
    del all_files

    dispatched_tasks = []
    progressbar = tqdm(total=sample_size, mininterval=0.5, unit_scale=True)

    with mp.Pool(args.cpus) as pool:
        for batch in batched(selected_files, n=args.batch_size):
            dispatched_tasks.append(
                pool.apply_async(dispatch_batch, (batch, args.sample_volume))
            )
            while len(dispatched_tasks) >= args.cpus:
                for task in (t for t in dispatched_tasks if t.ready()):
                    dispatched_tasks.remove(task)
                    progressbar.update(n=args.batch_size)

    print(
        f"\n\nTested against {sample_size} *randomly* selected out of {all_files_size} "
        f"documents."
        f"\n{args.sample_volume}% of the tag nodes' `location_path` "
        f"attribute were verified per document."
    )


if __name__ == "__main__":
    main()
