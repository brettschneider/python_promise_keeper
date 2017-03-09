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

__author__ = 'Steve Brettschneider'
__version__ = '0.2'
__license__ = 'MIT'


from threading import Event, Lock, Thread
from Queue import Queue, Empty
from datetime import datetime
from time import sleep


class PromiseKeeper(object):
    """
    Provides asyncronous execution via threads.
    """

    def __init__(self, number_threads=1, auto_start=True, auto_stop=True, \
                 iterator=None):
        self._number_threads = number_threads
        self._threads = []
        self._work_queue = Queue()
        self._auto_start = auto_start
        self._auto_stop = auto_stop
        self._auto_stop_monitor = None
        self._stop_event = None
        if iterator is not None:
            self._iterator_pump = _PromiseIteratorPump(self, iterator)
            self._iterator_pump.start()

    def submit(self, task, args=[], kwargs={}, notify=None):
        """
        Submit a task to be scheduled in the PromiseKeeper's thread pool.
        """
        promise = Promise(task, args, kwargs, notify)
        self.submit_promise(promise)
        return promise

    def submit_promise(self, promise):
        """
        Submit a promise to be scheduled in the thread pool.
        """
        if not isinstance(promise, Promise):
            raise TypeError('submit_promise requires a Promise argument')
        self._work_queue.put(promise)
        if self._auto_start and not self.is_running():
            self.start()

    def start(self):
        """
        Start the PromiseKeeper
        """
        if self.is_running():
            raise PromiseKeeperStateError("PromiseKeeper already running.")
        self._stop_event = Event()
        self._threads = [ \
            _PromiseWorkerThread(self._work_queue, self._stop_event) \
            for _ in range(self._number_threads) \
        ]
        [t.start() for t in self._threads] # pylint: disable=expression-not-assigned
        if self._auto_stop:
            self._auto_stop_monitor = _PromiseKeeperAutoStopMonitor( \
                self._work_queue, self)
            self._auto_stop_monitor.start()


    def stop(self, block=True):
        """
        Stop the PromiseKeeper.  If block is True (defaut), then this method
        will block until all running tasks complete.
        """
        if not self.is_running():
            raise PromiseKeeperStateError("PromiseKeeper isn't running.")
        self._stop_event.set()
        if block:
            [t.join() for t in self._threads] # pylint: disable=expression-not-assigned
        self._threads = []
        self._auto_stop_monitor = None

    def is_running(self):
        """
        Indicates if the PromiseKeeper has been started.
        """
        return len(self._threads) > 0


class _PromiseWorkerThread(Thread):
    """Executes the promises"""

    def __init__(self, work_queue, stop_event):
        Thread.__init__(self)
        self._work_queue = work_queue
        self._stop_event = stop_event

    def run(self):
        while not self._stop_event.is_set():
            try:
                promise = self._work_queue.get_nowait()
            except Empty:
                continue
            promise._set_started_on(datetime.now()) # pylint: disable=protected-access
            try:
                promise._set_result(promise.get_task()(*promise.get_args(), \
                    **promise.get_kwargs()))  # pylint: disable=protected-access
            except Exception as exp: # pylint: disable=broad-except
                promise._set_exception(exp)  # pylint: disable=protected-access
            promise._set_completed_on(datetime.now()) # pylint: disable=protected-access
            if promise._notify is not None:  # pylint: disable=protected-access
                try:
                    promise._notify(promise) # pylint: disable=protected-access
                except: # pylint: disable=bare-except
                    pass
            self._work_queue.task_done()


class _PromiseKeeperAutoStopMonitor(Thread):
    """
    Checks to see if the task queue is empty for a while, then shuts down the
    PromiseKeeper.
    """

    def __init__(self, work_queue, promise_keeper):
        Thread.__init__(self)
        self._work_queue = work_queue
        self._promise_keeper = promise_keeper

    def run(self):
        sleep(0.1)
        self._work_queue.join()
        self._promise_keeper.stop()


class _PromiseIteratorPump(Thread):
    """
    Iterates over the iterator, submitting the Promises that the iterator
    generates
    """

    def __init__(self, promise_keeper, iterator):
        Thread.__init__(self)
        self._promise_keeper = promise_keeper
        self._iterator = iterator

    def run(self):
        for promise in self._iterator:
            if not isinstance(promise, Promise):
                raise TypeError('Iterator needs to be of type Promise')
            self._promise_keeper.submit_promise(promise)


class Promise(object):
    """A promise of future results"""

    def __init__(self, task, args=[], kwargs={}, notify=None):
        self._task = task
        self._args = args
        self._kwargs = kwargs
        self._exception = None
        self._result = None
        self._started_on = None
        self._completed_on = None
        self._notify = notify
        self._lock = Lock()

    def __repr__(self):
        if self.is_ready():
            return "<Promise: result=%s, exception=%s>" % \
                (self._result, self._exception)
        if self.has_started():
            return "<Promise: running since %s>" % self._started_on
        else:
            return "<Promise: waiting>"

    def is_ready(self):
        """
        Returns True if this promise has been executed in the thead pool and
        has either resulted in a result or an exception.  Otherwise returns
        False
        """
        self._lock.acquire()
        completed_on = self._completed_on
        self._lock.release()
        return completed_on is not None

    def has_started(self):
        """
        Returns True if this promise has begun processing in the thread pool.
        """
        return self.get_started_on() is not None

    def get_task(self):
        """Returns the task for this promise."""
        return self._task

    def get_args(self):
        """Returns the args for this promise."""
        return self._args

    def get_kwargs(self):
        """Returns the kwargs for this promise."""
        return self._kwargs

    def get_execution_time(self):
        """
        Returns the time_delta for execution if completed.  Otherwise returns
        None.
        """
        if not self.is_ready():
            return None
        else:
            self._lock.acquire()
            exec_time = self._completed_on - self._started_on
            self._lock.release()
            return exec_time

    def get_started_on(self):
        """
        Returns the datetime of when the task was started, or None if it's still
        waiting.
        """
        self._lock.acquire()
        started_on = self._started_on
        self._lock.release()
        return started_on

    def _set_started_on(self, started_on):
        """Used by the worker thread to set the started_on value."""
        self._lock.acquire()
        self._started_on = started_on
        self._lock.release()

    def get_completed_on(self):
        """
        Returns the datetime of when the task was completed, or None if it's
        still waiting or running.
        """
        self._lock.acquire()
        completed_on = self._completed_on
        self._lock.release()
        return completed_on

    def _set_completed_on(self, completed_on):
        """Used by the worker thread to set the completed_on value."""
        self._lock.acquire()
        self._completed_on = completed_on
        self._lock.release()

    def get_result(self):
        """Returns the result or None if it's not ready."""
        self._lock.acquire()
        result = self._result
        self._lock.release()
        return result

    def _set_result(self, result):
        """Used by the worker thread to set the result."""
        self._lock.acquire()
        self._result = result
        self._lock.release()

    def get_exception(self):
        """Returns the exception or None if there isn't one."""
        self._lock.acquire()
        exception = self._exception
        self._lock.release()
        return exception

    def _set_exception(self, exception):
        """Used by the worker thread to set the exception."""
        self._lock.acquire()
        self._exception = exception
        self._lock.release()


class PromiseKeeperStateError(Exception):
    """
    Thrown if the PromiseKeeper is in an invalid state for a given method call.
    """
