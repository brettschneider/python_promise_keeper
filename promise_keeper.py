#!/usr/bin/env python

from threading import Event, Thread
from Queue import Queue, Empty
from datetime import datetime

class PromiseKeeper(object):

    def __init__(self, number_threads=1):
        self._number_threads = number_threads
        self._threads = []
        self._work_queue = Queue()

    def submit(self, task, args=[], kwargs={}, callback=None):
        """
        Submit a task to be scheduled in the PromiseKeeper
        """
        promise = Promise(task, args, kwargs, callback)
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
            promise.started_on = datetime.now()
            try:
                promise.result = promise.task(*promise.args, **promise.kwargs)
            except Exception as e:
                promise.exception = e
            if promise.callback is not None:
                try:
                    promise.callback(promise)
                except:
                    pass
            promise.completed_on = datetime.now()
            self._work_queue.task_done()


class Promise(object):
    """A promise of future results"""

    def __init__(self, task, args, kwargs, callback):
        self.task = task
        self.args = args
        self.kwargs = kwargs
        self.exception = None
        self.result = None
        self.started_on = None
        self.completed_on = None
        self.callback = callback

    def __repr__(self):
        if self.is_ready():
            return "<Promise: result=%s, exception=%s>" % \
                (self.result, self.exception)
        if self.has_started():
            return "<Promise: running since %s>" % self.started_on
        else:
            return "<Promise: waiting>"

    def is_ready(self):
        return self.completed_on is not None

    def has_started(self):
        return self.started_on is not None

    def execution_time(self):
        if self.completed_on is None:
            return None
        else:
            return self.completed_on - self.started_on


class PromiseKeeperStateError(Exception):
    """
    Thrown if the PromiseKeeper is in an invalid state for a given method call.
    """
