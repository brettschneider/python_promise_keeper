#!/usr/bin/env python

from threading import Event, Lock, Thread
from Queue import Queue, Empty
from datetime import datetime

class PromiseKeeper(object):

    def __init__(self, number_threads=1):
        self._number_threads = number_threads
        self._threads = []
        self._work_queue = Queue()

    def submit(self, task, args=[], kwargs={}, notify=None):
        """
        Submit a task to be scheduled in the PromiseKeeper
        """
        promise = Promise(task, args, kwargs, notify)
        self._work_queue.put(promise)
        return promise

    def start(self):
        """
        Start the PromiseKeeper
        """
        if self.is_running():
            raise PromiseKeeperStateError("PromiseKeeper already running.")
        self._stop_event = Event()
        self._threads = [ \
            _PromiseWorkerThread(self._work_queue, self._stop_event) \
            for i in range(self._number_threads) \
        ]
        [t.start() for t in self._threads]

    def stop(self, block=True):
        """
        Stop the PromiseKeeper.  If block is True (defaut), then this method
        will block until all running tasks complete.
        """
        if not self.is_running():
            raise PromiseKeeperStateError("PromiseKeeper isn't running.")
        self._stop_event.set()
        [t.join() for t in self._threads]
        self._threads = []

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
            promise._set_started_on(datetime.now())
            try:
                promise._set_result(promise._task(*promise._args, **promise._kwargs))
            except Exception as e:
                promise._set_exception(e)
            if promise._notify is not None:
                try:
                    promise._notify(promise)
                except:
                    pass
            promise._set_completed_on(datetime.now())
            self._work_queue.task_done()


class Promise(object):
    """A promise of future results"""

    def __init__(self, task, args, kwargs, notify):
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
        self._lock.acquire()
        completed_on = self._completed_on
        self._lock.release()
        return completed_on is not None

    def has_started(self):
        return self.get_started_on() is not None

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
