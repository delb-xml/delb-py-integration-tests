import argparse
import logging
import multiprocessing as mp
from contextlib import contextmanager
from enum import Flag, auto
from logging.handlers import QueueHandler
from multiprocessing.managers import DictProxy
from multiprocessing.sharedctypes import Synchronized
from pathlib import Path


class WorkerState(Flag):
    STARTED = auto()
    PREPARING = auto()
    WAIT_FOR_FILE = auto()
    TESTING = auto()
    DOING_MAINTENANCE = auto()
    FINALIZING = auto()
    DONE = auto()
    STOPPED = auto()


class TestCaseBase(mp.Process):
    maintenance_interval = 10_000

    def __init__(
        self,
        args: argparse.Namespace,
        file_queue: "mp.JoinableQueue[Path | None]",
        log_queue: "mp.Queue[logging.LogRecord]",
        errors: "Synchronized[int]",
        worker_states: DictProxy[str, WorkerState],
    ):
        self.args = args
        self._errors = errors
        self._file_queue = file_queue
        self._log_queue = log_queue
        self.results_path = self.args.results_path / self.__class__.__module__.replace(
            "_", "-"
        )
        self._worker_states = worker_states
        super().__init__()

    def error(self, message: str, exception: bool = False):
        if exception:
            self.log.exception(message)
        else:
            self.log.error(message)
        assert self.pid is not None
        with self._errors.get_lock():
            self._errors.value += 1

    def finalize(self):
        pass

    def _get_file(self) -> Path | None:
        with self.__set_state(WorkerState.WAIT_FOR_FILE):
            return self._file_queue.get()

    def maintain(self):
        pass

    def prepare(self):
        pass

    def run(self):
        self._setup_logging()
        with self.__set_state(WorkerState.PREPARING):
            self.prepare()

        self.log.info("Starting test worker.")
        maintenance_counter = self.maintenance_interval

        while (file := self._get_file()) is not None:
            try:
                self.log.debug(f"Testing against {file}")
                with self.__set_state(WorkerState.TESTING):
                    self.test(file)
            except AssertionError as e:
                self.error(e.args[0])
            except Exception:
                self.error(f"Unhandled exception while testing {file}:", True)
            finally:
                self._file_queue.task_done()

            maintenance_counter -= 1
            if not maintenance_counter:
                with self.__set_state(WorkerState.DOING_MAINTENANCE):
                    self.maintain()
                maintenance_counter = self.maintenance_interval

        self.log.debug("No more work items on the queue.")
        with self.__set_state(WorkerState.FINALIZING):
            self.finalize()
        self._file_queue.task_done()
        self.log.info("Ending test worker.")
        assert self.pid is not None
        self._worker_states[self.name] |= WorkerState.DONE

    @contextmanager
    def __set_state(self, state):
        assert self.pid is not None
        self._worker_states[self.name] |= state
        yield
        self._worker_states[self.name] &= ~state

    @property
    def state(self):
        return self._worker_states[self.name]

    def test(self, file: Path):
        raise NotImplementedError

    def _setup_logging(self):
        self.log: logging.Logger = logging.getLogger(self.__class__.__module__)
        self.log.addHandler(QueueHandler(self._log_queue))
        self.log.setLevel(logging.DEBUG if self.args.verbose else logging.INFO)
