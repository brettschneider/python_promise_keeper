#!/usr/bin/env python
"""
promise_keeper module provides the PromiseKeeper class.  The PromiseKeeper
class makes asynchronous programming easier by managing threads and
execution for the developer.  Sample usage:

    >>> from promise_keeper import PromiseKeeper
    >>> from time import sleep
    >>> from random import random
    >>> def slow_add(x, y):
    ...     sleep(random() * 2)
    ...     return x+y
    ...
    >>> pc = PromiseKeeper()
    >>> p = pc.submit(slow_add, (200, 50))
    >>> while not p.is_ready():
    ...     sleep(0.01)
    ...
    >>> print p.get_result()
    250
    >>>

Copyright (c) 2017, Steve Brettschneider.
License: MIT (see LICENSE for details)
"""

__author__ = "Steve Brettschneider"
__version__ = "0.3"
__license__ = "MIT"

from typing import List, Any, Dict, Callable, Optional

from threading import Event, Lock, Thread
from queue import Queue, Empty
from datetime import datetime, timedelta
from time import sleep


class PromiseKeeper:
    """
    Provides asyncronous execution via threads.
    """

    def __init__(
        self,
        number_threads: int = 1,
        auto_start: bool = True,
        auto_stop: bool = True,
        iterator=None,
    ) -> None:
        self._number_threads = number_threads
        self._threads: List[Thread] = []
        self._work_queue = Queue()
        self._auto_start = auto_start
        self._auto_stop = auto_stop
        self._auto_stop_monitor: Optional[_PromiseKeeperAutoStopMonitor] = None
        self._stop_event = Event()
        if iterator is not None:
            self._iterator_pump = _PromiseIteratorPump(self, iterator)
            self._iterator_pump.start()

    def submit(
        self, task, args: List[Any] = None, kwargs: Dict = None, notify=None
    ) -> "Promise":
        """
        Submit a task to be scheduled in the PromiseKeeper's thread pool.
        """
        args = [] if args is None else args
        kwargs = {} if kwargs is None else kwargs
        promise = Promise(task, args, kwargs, notify)
        self.submit_promise(promise)
        return promise

    def submit_promise(self, promise: "Promise") -> None:
        """
        Submit a promise to be scheduled in the thread pool.
        """
        if not isinstance(promise, Promise):
            raise TypeError("submit_promise requires a Promise argument")
        self._work_queue.put(promise)
        if self._auto_start and not self.is_running():
            self.start()

    def start(self) -> None:
        """
        Start the PromiseKeeper
        """
        if self.is_running():
            raise PromiseKeeperStateError("PromiseKeeper already running.")
        self._threads = [
            _PromiseWorkerThread(self._work_queue, self._stop_event, self)
            for _ in range(self._number_threads)
        ]
        [t.start() for t in self._threads]  # pylint: disable=expression-not-assigned
        if self._auto_stop:
            self._auto_stop_monitor = _PromiseKeeperAutoStopMonitor(
                self._work_queue, self
            )
            self._auto_stop_monitor.start()

    def stop(self, block: bool = True) -> None:
        """
        Stop the PromiseKeeper.  If block is True (defaut), then this method
        will block until all running tasks complete.
        """
        if not self.is_running():
            raise PromiseKeeperStateError("PromiseKeeper isn't running.")
        self._stop_event.set()
        if block:
            [t.join() for t in self._threads]  # pylint: disable=expression-not-assigned
        self._threads = []
        self._auto_stop_monitor = None

    def is_running(self) -> bool:
        """
        Indicates if the PromiseKeeper has been started.
        """
        return len(self._threads) > 0


class _PromiseWorkerThread(Thread):
    """Executes the promises"""

    def __init__(self, work_queue, stop_event, parent_pk):
        Thread.__init__(self)
        self._work_queue = work_queue
        self._stop_event = stop_event
        self._parent_pk = parent_pk

    def run(self) -> None:
        while not self._stop_event.is_set():
            try:
                promise = self._work_queue.get_nowait()
            except Empty:
                continue
            promise._set_started_on(datetime.now())  # pylint: disable=protected-access
            try:
                promise._set_result(
                    promise.get_task()(*promise.get_args(), **promise.get_kwargs())
                )  # pylint: disable=protected-access
            except Exception as exp:  # pylint: disable=broad-except
                promise._set_exception(exp)  # pylint: disable=protected-access
            promise._set_completed_on(
                datetime.now()
            )  # pylint: disable=protected-access
            if promise._notify is not None:  # pylint: disable=protected-access
                try:
                    promise._notify(promise)  # pylint: disable=protected-access
                except:  # pylint: disable=bare-except
                    pass
            next_promise = promise._get_next_promise()
            if next_promise is not None:
                next_promise._args = (promise,)
                self._parent_pk.submit_promise(next_promise)
            self._work_queue.task_done()


class _PromiseKeeperAutoStopMonitor(Thread):
    """
    Checks to see if the task queue is empty for a while, then shuts down the
    PromiseKeeper.
    """

    def __init__(self, work_queue: Queue, promise_keeper: PromiseKeeper) -> None:
        Thread.__init__(self)
        self._work_queue = work_queue
        self._promise_keeper = promise_keeper

    def run(self) -> None:
        sleep(0.1)
        self._work_queue.join()
        self._promise_keeper.stop()


class _PromiseIteratorPump(Thread):
    """
    Iterates over the iterator, submitting the Promises that the iterator
    generates
    """

    def __init__(self, promise_keeper: PromiseKeeper, iterator) -> None:
        Thread.__init__(self)
        self._promise_keeper = promise_keeper
        self._iterator = iterator

    def run(self) -> None:
        for promise in self._iterator:
            if not isinstance(promise, Promise):
                raise TypeError("Iterator needs to be of type Promise")
            self._promise_keeper.submit_promise(promise)


class Promise:
    """A promise of future results"""

    def __init__(
        self, task: Callable, args: List[Any] = None, kwargs: Dict = None, notify=None
    ) -> None:
        self._task = task
        self._args = [] if args is None else args
        self._kwargs = {} if kwargs is None else kwargs
        self._exception = None
        self._result = None
        self._started_on = None
        self._completed_on = None
        self._notify = notify
        self._lock = Lock()
        self._next_promise = None

    def __repr__(self) -> str:
        if self.is_ready():
            return "<Promise: result=%s, exception=%s>" % (
                self._result,
                self._exception,
            )
        if self.has_started():
            return "<Promise: running since %s>" % self._started_on
        else:
            return "<Promise: waiting>"

    def is_ready(self) -> bool:
        """
        Returns True if this promise has been executed in the thead pool and
        has either resulted in a result or an exception.  Otherwise returns
        False
        """
        with self._lock:
            completed_on = self._completed_on
            return completed_on is not None

    def has_started(self) -> bool:
        """
        Returns True if this promise has begun processing in the thread pool.
        """
        return self.get_started_on() is not None

    def get_task(self) -> Callable:
        """Returns the task for this promise."""
        return self._task

    def get_args(self) -> List:
        """Returns the args for this promise."""
        return self._args

    def get_kwargs(self) -> Dict:
        """Returns the kwargs for this promise."""
        return self._kwargs

    def get_execution_time(self) -> Optional[timedelta]:
        """
        Returns the time_delta for execution if completed.  Otherwise returns
        None.
        """
        if not self.is_ready():
            return None
        else:
            with self._lock:
                exec_time = self._completed_on - self._started_on
            return exec_time

    def get_started_on(self) -> datetime:
        """
        Returns the datetime of when the task was started, or None if it's still
        waiting.
        """
        with self._lock:
            started_on = self._started_on
            return started_on

    def _set_started_on(self, started_on) -> datetime:
        """Used by the worker thread to set the started_on value."""
        with self._lock:
            self._started_on = started_on

    def get_completed_on(self) -> Optional[datetime]:
        """
        Returns the datetime of when the task was completed, or None if it's
        still waiting or running.
        """
        with self._lock:
            completed_on = self._completed_on
            return completed_on

    def _set_completed_on(self, completed_on: datetime):
        """Used by the worker thread to set the completed_on value."""
        with self._lock:
            self._completed_on = completed_on

    def get_result(self) -> Any:
        """Returns the result or None if it's not ready."""
        with self._lock:
            result = self._result
            return result

    def _set_result(self, result: Any) -> None:
        """Used by the worker thread to set the result."""
        with self._lock:
            self._result = result

    def get_exception(self) -> Optional[Exception]:
        """Returns the exception or None if there isn't one."""
        with self._lock:
            exception = self._exception
            return exception

    def _set_exception(self, exception: Exception) -> None:
        """Used by the worker thread to set the exception."""
        with self._lock:
            self._exception = exception

    def _get_next_promise(self) -> "Promise":
        """Usef by worker thread to submit another promise to teh queue."""
        return self._next_promise

    def then_do(self, task: Callable) -> "Promise":
        """Allow promise chaining"""
        if self.get_started_on() != None:
            raise PromiseStateError()
        self._next_promise = Promise(task)
        return self._next_promise  # mypy: ignore


class PromiseKeeperStateError(Exception):
    """
    Raised if the PromiseKeeper is in an invalid state for a given method call.
    """


class PromiseStateError(Exception):
    """
    Raised if a Promise is in an invalidate state got a given operation.
    """
