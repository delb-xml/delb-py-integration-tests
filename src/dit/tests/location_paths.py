from __future__ import annotations

import random
from pathlib import Path

from _delb.plugins.core_loaders import path_loader
from delb import (
    Document,
    FailedDocumentLoading,
    ParserOptions,
    TagNode,
    get_traverser,
    is_tag_node,
)

from dit.tests._test_base import TestCaseBase

traverse = get_traverser(from_left=True, depth_first=True, from_top=True)


class TestCase(TestCaseBase):
    def test(self, file: Path):
        sample_volume = self.args.sample_volume

        try:
            document = Document(
                file,
                parser_options=ParserOptions(
                    reduce_whitespace=False, resolve_entities=False, unplugged=True
                ),
            )
        except FailedDocumentLoading as exc:
            self.error(f"Failed to load {file.name}: {exc.excuses[path_loader]}")
            return

        document_clone = document.clone()

        for node in traverse(document.root, is_tag_node):
            if random.randint(1, 100) > sample_volume:
                continue

            assert isinstance(node, TagNode)
            query_results = document.xpath(node.location_path, namespaces={})
            if not (query_results.size == 1 and query_results.first is node):
                self.error(
                    f"XPath query `{node.location_path}` in {file} yielded unexpected "
                    "results."
                )

            query_results = document_clone.xpath(node.location_path, namespaces={})
            if not (
                query_results.size == 1
                and isinstance(node := query_results.first, TagNode)
                and node.universal_name == node.universal_name
                and node.attributes == node.attributes
            ):
                self.error(
                    f"XPath query `{node.location_path}` in a clone of {file} yielded "
                    "unexpected results."
                )

    def finalize(self):
        self.log.info(
            f"{self.args.sample_volume}% of the tag nodes' `location_path` attribute "
            "were verified per document.",
        )
