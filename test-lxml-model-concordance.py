from __future__ import annotations

import argparse
import logging
import multiprocessing as mp
from datetime import datetime
from pathlib import Path
from random import randrange
from typing import Final, Iterable, Iterator

from delb import (
    CommentNode,
    Document,
    NodeBase,
    ProcessingInstructionNode,
    TagNode,
    TextNode,
    altered_default_filters,
    get_traverser,
)
from lxml import etree
from tqdm import tqdm

DIT_PATH: Final = Path(__file__).parent


log = logging.getLogger(Path(__file__).stem)


#


def _compare_attributes(element: etree._Element, reference: TagNode):
    for name, value in element.attrib.items():
        attribute = reference.attributes[name]
        assert attribute is not None, repr(attribute)
        assert value == attribute.value


def _compare_element(element: etree._Element, traverser: Iterator[NodeBase]):
    reference = next(traverser)

    if element.tag is etree.Comment:
        assert isinstance(reference, CommentNode), repr(reference)
        assert element.text == reference.content

    elif element.tag is etree.ProcessingInstruction:
        assert isinstance(reference, ProcessingInstructionNode), repr(reference)
        assert element.target == reference.target  # type: ignore
        assert element.text == reference.content

    else:
        assert isinstance(reference, TagNode), repr(reference)

        qname = etree.QName(element)
        assert qname.namespace == reference.namespace
        assert qname.localname == reference.local_name

        _compare_attributes(element, reference)

        if (text := element.text) is not None:
            _compare_text(text, traverser)

        for child_element in element:
            _compare_element(child_element, traverser)

    if (tail := element.tail) is not None:
        _compare_text(tail, traverser)


def _compare_text(text: str, traverser: Iterator[NodeBase]):
    reference = next(traverser)
    assert isinstance(reference, TextNode), repr(reference)
    assert text == reference.content, f"|{text}|!=|{reference.content}|"


def compare_to_lxml(document: Document, tree: etree._ElementTree):
    # fwiw, etree.iterparse isn't being used as it also emits the comments included in
    # external DTDs. thus there's no effort put here into verifying prologue and
    # epilogue elements here.
    with altered_default_filters():
        traverser = get_traverser(from_left=True, depth_first=True, from_top=True)(
            document.root
        )
        _compare_element(
            element=tree.getroot(),
            traverser=traverser,
        )

    try:
        node = next(traverser)
    except StopIteration:
        pass
    else:
        raise AssertionError(f"Unexpected node in the delb Document: {node!r}")


#


def dispatch_batch(files_list: Iterable[Path], source_root: Path):
    globals()["log"] = setup_logger()
    log.setLevel(logging.DEBUG)
    for path in files_list:
        try:
            compare_to_lxml(Document(path), etree.parse(path))
        except AssertionError as e:
            log.error(f"Mismatch detected with '{path}':")
            log.exception(e)
        except Exception as e:
            log.error(f"Unhandled exception while testing {path}:")
            log.exception(e)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("-b", "--batch-size", type=int, default=128)
    parser.add_argument("--cpus", type=int, default=mp.cpu_count())
    parser.add_argument(
        "--corpus_path", "--src", type=Path, default=DIT_PATH / "corpora"
    )
    return parser.parse_args()


def random_batch(all_files: list[Path], size: int) -> Iterator[Iterable[Path]]:
    # this distributes memory usage over batches as the name sorted file list have some
    # clusters with large files
    # also the progressbar behaves less stucky
    batch: list[Path] = []
    while all_files:
        batch.append(all_files.pop(randrange(len(all_files))))
        if len(batch) == size:
            yield tuple(batch)
            batch.clear()

    if batch:
        yield tuple(batch)


def setup_logger():
    logger = mp.get_logger()
    handler = logging.FileHandler(
        (
            DIT_PATH
            / "logs"
            / f"{log.name}-{datetime.now().isoformat(timespec='minutes')}.log"
        )
    )
    handler.setFormatter(logging.Formatter("[%(process)d] %(message)s"))
    if not len(logger.handlers):
        logger.addHandler(handler)

    return logger


def main():
    mp.set_start_method("forkserver")
    args = parse_args()
    globals()["log"] = setup_logger()
    log.setLevel(logging.INFO)

    all_files: list[Path] = []
    for directory_path, _, files in args.corpus_path.walk(follow_symlinks=True):
        all_files.extend(directory_path / f for f in files if f.endswith(".xml"))
    all_files_size: Final = len(all_files)
    dispatched_tasks = []
    progressbar = tqdm(total=all_files_size, mininterval=0.5, unit_scale=True)

    with mp.Pool(args.cpus) as pool:
        for file_batch in random_batch(all_files, args.batch_size):
            dispatched_tasks.append(
                pool.apply_async(
                    dispatch_batch,
                    (file_batch, args.corpus_path),
                )
            )

            while len(dispatched_tasks) >= args.cpus:
                for task in (t for t in dispatched_tasks if t.ready()):
                    dispatched_tasks.remove(task)
                    progressbar.update(n=args.batch_size)

    log.info(f"Tested against {all_files_size} documents.")

    # it's a mystery where the responsible log handler is configured
    for file in (
        f for f in (DIT_PATH / "logs").iterdir() if f.name.startswith("multiprocessing")
    ):
        file.unlink()


if __name__ == "__main__":
    main()
