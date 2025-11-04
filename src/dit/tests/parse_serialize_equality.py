from __future__ import annotations

from os import sync as sync_disk
from pathlib import Path
from typing import Final, Optional, TypedDict, TYPE_CHECKING

from _delb.plugins.core_loaders import buffer_loader
from delb import Document, FormatOptions
from delb.exceptions import FailedDocumentLoading
from delb.parser import ParserOptions
from delb.utils import compare_trees
from fs.memoryfs import MemoryFS
from fs.osfs import OSFS

from dit.tests._test_base import TestCaseBase

if TYPE_CHECKING:
    from fs.base import FS


#


class CommonParserOptions(TypedDict):
    load_referenced_resources: bool
    preferred_parsers: str
    unplugged: bool


COMMON_PARSER_OPTIONS: Final[CommonParserOptions] = {
    "load_referenced_resources": True,
    "preferred_parsers": "expat",
    "unplugged": True,
}


class TestCase(TestCaseBase):
    def finalize(self):
        self.maintain()

    def load_file(self, filesystem: FS, path: Path, **options) -> Optional[Document]:
        try:
            with filesystem.open(str(path), mode="rb") as f:
                return Document(f, **options)
        except FailedDocumentLoading as e:
            self.error(f"Failed to load {path.name}: {e.excuses[buffer_loader]}")
            return None

    def maintain(self):
        for path in (f.path for f in self.work_fs.glob("**/*.xml")):
            target = self.results_path / path.removeprefix("/")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(self.work_fs.readbytes(path))
            self.work_fs.remove(path)

        sync_disk()

    def prepare(self):
        self.work_fs = MemoryFS()

    def save_and_compare_file(
        self,
        origin: Document,
        result_file: Path,
        format_options: None | FormatOptions,
        reduce_whitespace: bool,
    ):
        if not self.save_file(
            origin, self.work_fs, result_file, format_options=format_options
        ):
            return

        if (
            copy_ := self.load_file(
                self.work_fs,
                result_file,
                parser_options=ParserOptions(
                    reduce_whitespace=reduce_whitespace, **COMMON_PARSER_OPTIONS
                ),
                source_url=(self.args.corpus_path / result_file).as_uri(),
            )
        ) is None:
            return

        if comparison_result := compare_trees(origin.root, copy_.root):
            self.work_fs.remove(str(result_file))
        else:
            self.error(f"Unequal document produced: {result_file}\n{comparison_result}")

    def save_file(
        self, document: Document, filesystem: FS, path: Path, **options
    ) -> bool:
        try:
            with filesystem.open(str(path), mode="wb") as f:
                document.write(f, **options)  # type: ignore
        except Exception as e:
            self.log.error(f"Failed to save {path.name}:")
            self.error(e)
            return False
        else:
            return True

    def test(self, file: Path):
        corpus_path = self.args.corpus_path
        file = file.relative_to(corpus_path)
        self.src_fs = OSFS(str(corpus_path))

        # unaltered whitespace

        if (
            origin := self.load_file(
                self.src_fs,
                file,
                parser_options=ParserOptions(
                    reduce_whitespace=False, **COMMON_PARSER_OPTIONS
                ),
                source_url=(corpus_path / file).as_uri(),
            )
        ) is None:
            return

        result_file = file.with_stem(f"{file.stem}-plain")
        self.work_fs.makedirs(str(result_file.parent), recreate=True)
        self.save_and_compare_file(origin, result_file, None, False)

        # altered whitespace

        origin.reduce_whitespace()

        self.save_and_compare_file(
            origin,
            file.with_stem(f"{file.stem}-tabbed"),
            FormatOptions(align_attributes=False, indentation="\t", width=0),
            True,
        )

        self.save_and_compare_file(
            origin,
            file.with_stem(f"{file.stem}-wrapped"),
            FormatOptions(align_attributes=False, indentation="  ", width=77),
            True,
        )
