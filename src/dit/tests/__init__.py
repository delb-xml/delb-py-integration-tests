import argparse
import ctypes
import json
import logging
import multiprocessing as mp
import signal
from datetime import datetime
from importlib import import_module
from logging.handlers import QueueListener
from multiprocessing.managers import DictProxy
from pathlib import Path
from pprint import pformat
from random import randrange
from time import sleep
from typing import Final, Iterator

from tqdm import tqdm

from dit.commons import LOGS_PATH
from dit.corpora import CORPORA
from dit.tests._test_base import TestCaseBase, WorkerState

TEST_NAMES: Final = tuple(
    p.name.removesuffix(".py").replace("_", "-")
    for p in Path(__file__).parent.glob("*.py")
    if not p.name.startswith("_")
)


log = logging.getLogger(__name__)


#


def cmd_list(args: argparse.Namespace):
    if args.json:
        print(json.dumps(TEST_NAMES))
    else:
        print("Available tests:")
        for name in TEST_NAMES:
            print(f"- {name}")


#


def collect_files(args: argparse.Namespace) -> list[Path]:
    def file_size(p: Path) -> int:
        return p.stat().st_size

    log.debug("Collecting files.")

    paths: list[Path] = []
    for corpus in args.selected_corpora:
        for directory_path, _, names in (args.corpus_path / corpus).walk(
            follow_symlinks=True
        ):
            paths.extend(directory_path / f for f in names if f.endswith(".xml"))

    return sorted(paths, key=file_size)


def get_file(args: argparse.Namespace) -> Iterator[Path | None]:
    files: Final = args.files[:]

    if args.sample_volume == 100:
        while files:
            yield files.pop()
    else:
        quantile_size: Final = (
            files_size if (files_size := len(files)) < 48 else int(files_size / 24)
        )

        high = len(files)
        low = high - quantile_size
        while low > 0 and files:

            counter = int(quantile_size / 100 * args.sample_volume)
            while counter and files:
                yield files.pop(randrange(low, high))
                counter -= 1
                high -= 1
                if high == low:
                    break

            low, high = low - quantile_size, low


def get_log_filehandler(args: argparse.Namespace, name: str) -> logging.Handler:
    handler = logging.FileHandler(
        LOGS_PATH / f"{name}-{datetime.now().isoformat(timespec="minutes")}.log"
    )
    handler.setFormatter(
        logging.Formatter("[{process}]{levelname}::{message}", style="{")
    )
    handler.setLevel(logging.DEBUG if args.verbose else logging.INFO)
    return handler


def prepare_args(args: argparse.Namespace):
    selected_corpora: set[str] = set()
    selected_tests: set[str] = set()

    for item in args.item:
        if item in CORPORA:
            selected_corpora.add(item)
        elif item in TEST_NAMES:
            selected_tests.add(item)
        else:
            log.critical(f"Ignoring unknown corpus / test: {item}")

    if not selected_corpora:
        selected_corpora.update(CORPORA)
    if not selected_tests:
        selected_tests.update(TEST_NAMES)

    args.selected_corpora = selected_corpora
    args.selected_tests = selected_tests

    args.files = collect_files(args)
    args.sample_size = int(len(args.files) / 100 * args.sample_volume)


def run_tests(
    name: str,
    args: argparse.Namespace,
) -> bool:
    file_queue: mp.JoinableQueue[Path | None] = mp.JoinableQueue(args.cpus)
    progressbar = tqdm(total=args.sample_size, mininterval=1, unit_scale=True)
    test_module = import_module(f"{__name__}.{name.replace('-', '_')}")

    log_writer = QueueListener(
        mp.Queue(), get_log_filehandler(args, name), respect_handler_level=True
    )
    log_writer.start()

    with mp.Manager() as shared_data:
        errors = mp.Value(ctypes.c_uint)
        processes = start_workers(
            args, errors, file_queue, log_writer.queue, shared_data, test_module
        )

        for file in get_file(args):
            file_queue.put(file)
            progressbar.update(1)

        progressbar.refresh()
        progressbar.close()
        log.debug("Finished filling the test file queue.")

        terminate_workers(file_queue, processes)

        if result := errors.value:
            log.error(f"{result} errors encountered.")

    log_writer.stop()
    return bool(result)


def set_signal_handlers(
    file_queue: "mp.JoinableQueue[Path | None]", processes: list[TestCaseBase]
):
    def int_handler(signum, _):
        log.info(f"{signal.strsignal(signum)} received.")
        for process in processes:
            process.kill()
        raise SystemExit(2)

    def term_handler(signum, _):
        log.info(f"{signal.strsignal(signum)} received.")
        terminate_workers(file_queue, processes)
        raise SystemExit(2)

    def usr1_handler(signum, _):
        log.info(f"{signal.strsignal(signum)} received.")
        for process in processes:
            pid = process.pid if process.is_alive() else "terminated"
            log.info(f"[{process.name}/{pid}] {process.state}")

    signal.signal(signal.SIGINT, int_handler)
    signal.signal(signal.SIGTERM, term_handler)
    signal.signal(signal.SIGUSR1, usr1_handler)


def start_workers(args, errors, file_queue, log_queue, shared_data, test_module):
    worker_states = shared_data.dict()
    processes = [
        test_module.TestCase(
            args,
            file_queue,
            log_queue,
            errors,
            worker_states,
        )
        for _ in range(args.cpus)
    ]
    for process in processes:
        process.start()
        assert isinstance(process.pid, int)
        assert isinstance(worker_states, DictProxy)
        worker_states[process.name] = WorkerState.STARTED

    set_signal_handlers(file_queue, processes)

    return processes


def terminate_workers(
    file_queue: "mp.JoinableQueue[Path | None]", processes: list[TestCaseBase]
):
    for _ in range(len(processes)):
        file_queue.put(None)
    log.info("Waiting for task queue to empty.")
    file_queue.join()
    while any(p.is_alive() for p in processes):
        sleep(1)


def cmd_run(args: argparse.Namespace) -> None:
    log.debug("delb integration tests invoked with these options:")
    log.debug(pformat(vars(args)))

    errors = False
    prepare_args(args)

    for name in args.selected_tests:
        log.info(f"Invoking test '{name}'.")
        tests = run_tests(name, args=args)
        if tests:
            errors = True

    if args.sample_volume == 100:
        log.info(f"Tested against {len(args.files):,} documents.")
    else:
        log.info(
            f"Tested against {args.sample_size:,} randomly selected out of "
            f"{len(args.files):,} documents."
        )
    if errors:
        log.error("Tests did not pass.")
    raise SystemExit(errors)
