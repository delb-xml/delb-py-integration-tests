from __future__ import annotations

from pathlib import Path

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

from dit.tests._test_base import TestCaseBase


#


class TestCase(TestCaseBase):
    def compare_attributes(self):
        for name, value in self.element.attrib.items():
            assert isinstance(self.reference, TagNode)  # type narrowing
            attribute = self.reference.attributes[
                (
                    name
                    if name.startswith("{")
                    else (self.element.nsmap.get(None, ""), name)
                )
            ]
            assert attribute is not None, f"Missing attribute: {name}"
            assert value == attribute.value, f"Mismatching attribute value: {name}"

    def compare_element(self, element: etree._Element):
        self.element = element
        reference: NodeBase = self.next_reference()

        if element.tag is etree.Comment:
            assert isinstance(reference, CommentNode), "Mismatching node type"
            assert element.text == reference.content, "Mismatching content"

        elif element.tag is etree.ProcessingInstruction:
            assert isinstance(
                reference, ProcessingInstructionNode
            ), "Mismatching node type"
            assert (
                element.target == reference.target  # type: ignore
            ), "Mismatching target"
            assert element.text == reference.content, "Mismatching content"

        else:
            assert isinstance(reference, TagNode), "Mismatching node type"

            qname = etree.QName(element)
            assert qname.namespace == reference.namespace, "Mismatching namespace"
            assert qname.localname == reference.local_name, "Mismatching local name"

            self.compare_attributes()

            if (text := element.text) is not None:
                self.compare_text(text)

            for child_element in element:
                self.compare_element(child_element)

        if (tail := element.tail) is not None:
            self.compare_text(tail)

    def compare_text(self, text: str):
        reference = self.next_reference()
        assert isinstance(reference, TextNode), "Mismatching node type"
        assert text == reference.content, "Mismatching content"

    def error(self, message: str, exception: bool = False):
        super().error(message, exception)
        self.log.error(f"Element: {self.element!r}, {self.element.attrib}")
        self.log.error(f"Node: {self.reference!r}")

    def next_reference(self) -> NodeBase:
        self.reference: NodeBase = next(self.traverser)
        return self.reference

    def test(self, file: Path):
        # fwiw, etree.iterparse isn't being used as it also emits the comments included
        # in external DTDs. thus there's no effort put here into verifying prologue and
        # epilogue elements here.
        with altered_default_filters():
            self.traverser = get_traverser(
                from_left=True, depth_first=True, from_top=True
            )(Document(file).root)
            self.compare_element(element=etree.parse(file).getroot())

        try:
            node = self.next_reference()
        except StopIteration:
            pass
        else:
            raise AssertionError(f"Unexpected node in the delb Document: {node!r}")
