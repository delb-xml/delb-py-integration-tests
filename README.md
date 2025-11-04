# *delb* integration tests

This repository serves several tests for delb against a variety of XML
documents, mostly TEI encodings. They are supposed to validate major code
change proposals and ensure functionality before releases.

All test corpora preparations and tests are stuffed into a cli application
`dit`, use its `--help` output and the [`Justfile`](https://just.systems)
recipes as references to get acquainted (Just run `just` for a recipes list).

## Getting started

The `get-ready` recipe installs the application and fetches the tests that are
included as git submodules.

It doesn't install the *delb* package / source tree that is supposed to be
tested.


## Test corpora

### Not yet included

- https://www.deutschestextarchiv.de/media/download/dta_kernkorpus_2021-05-13.zip
  - to be used in tests, the corpus must be fixed regarding the `lb`-bug
- https://github.com/Brown-University-Library/usep-data/tree/master/xml_inscriptions/transcribed
- https://github.com/simondschweitzer/aed-tei/tree/master/files
  - includes hieroglyhs and encoding errors
- https://github.com/orgs/erc-dharma/repositories
  - several repos w/ south asian epigraphics, still growing
- https://gams.uni-graz.at/archive/objects/container:mws-gesamt/methods/sdef:Context/get?locale=fr&mode=&context=
  - requires a web crawler


## Tests

All tests can be invoked with `just run-tests`.

### location-paths

This verifies that an XPath query that targets a `TagNode.location_path`
attribute yields exactly that `TagNode` instance.
In order to save time the default `--sample-volume` is 25, like in percent.
It affects both the number of used random files and tested nodes.

### lxml-model-concordance

The same document is parsed to a *delb* and an *lxml* representation. Both are
then compared to have identical contents.
This relies on the assumption that *lxml* / *libxml2* are parsing correctly.

### parse-serialize-equality

This validates that different serializations are parsed back to the identical
document representation.
See *delb*'s `test_serialization::test_transparency` test for a more elaborated
description.
