import argparse
import logging
import multiprocessing as mp
from os import process_cpu_count  # type: ignore
from pathlib import Path

import dit.corpora
import dit.tests
from dit.commons import CORPORA_PATH, DIT_PATH


def configure_cli_logging(args):
    log = logging.getLogger()
    log.setLevel(logging.DEBUG if args.verbose else logging.INFO)
    log.addHandler(logging.StreamHandler())


def make_corpora_cmd_parser(parser):
    subcommands = parser.add_parser("corpora").add_subparsers()

    fetch_web_resources = subcommands.add_parser("fetch-web-resources")
    fetch_web_resources.set_defaults(func=dit.corpora.fetch_web_resources)
    fetch_web_resources.add_argument("--skip-existing", "-s", action="store_true")

    link_submodules = subcommands.add_parser("link-submodules")
    link_submodules.set_defaults(func=dit.corpora.cmd_link_submodules)

    _list = subcommands.add_parser("list")
    _list.set_defaults(func=dit.corpora.cmd_list)
    _list.add_argument("--json", action="store_true")

    normalize = subcommands.add_parser("normalize")
    normalize.set_defaults(func=dit.corpora.cmd_normalize)
    normalize.add_argument("submodule", nargs="*")

    summarize = subcommands.add_parser("summarize")
    summarize.set_defaults(func=dit.corpora.cmd_summarize)


def make_test_cmd_parser(parser):
    subcommands = parser.add_parser("tests").add_subparsers()

    _list = subcommands.add_parser("list")
    _list.set_defaults(func=dit.tests.cmd_list)
    _list.add_argument("--json", action="store_true")

    run = subcommands.add_parser("run")
    run.set_defaults(func=dit.tests.cmd_run)
    run.add_argument(
        "--corpus_path",
        "--src",
        type=Path,
        default=CORPORA_PATH,
        metavar="PATH",
    )
    run.add_argument("--cpus", type=int, default=process_cpu_count(), metavar="INTEGER")
    run.add_argument(
        "--results-path", "-r", type=Path, default=DIT_PATH / "results", metavar="PATH"
    )
    run.add_argument(
        "--sample-volume", "-s", type=float, default=100, metavar="PERCENT"
    )
    run.add_argument("item", nargs="*", metavar="CORPUS_OR_TEST")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("--verbose", "-v", action="store_true")
    commands_parser = parser.add_subparsers()
    make_corpora_cmd_parser(commands_parser)
    make_test_cmd_parser(commands_parser)
    return parser.parse_args()


def main():
    if mp.parent_process() is None:
        mp.set_start_method("forkserver")

    args = parse_args()
    configure_cli_logging(args)
    args.func(args)
