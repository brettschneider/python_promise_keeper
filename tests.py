#!/usr/bin/env python
"""
Some simple tests for the promise_keeper module.
"""

from promise_keeper import Promise, PromiseKeeper
from time import sleep
from random import random
from unittest import TestCase


def slow_add(x, y):
    sleep(random() * 1)
    return x+y


def slow_div(x, y):
    sleep(random() * 1)
    return x/y


def get_longest(item_1='', item_2=''):
    if len(item_1) > len(item_2):
        return item_1
    else:
        return item_2


class TestPromiseKeeper(TestCase):
    """
    A few simple tests to be used for sanity checks.
    """

    def setUp(self):
        self.pk = PromiseKeeper(3)

    def test_should_complete_a_single_task_by_promise(self):
        """Should complete a single task (Promise)."""
        # Implies that auto-stop is functioning properly.
        p = Promise(slow_add, (7, 3))
        self.pk.submit_promise(p)
        while not p.is_ready():
            sleep(0.01)
        self.assertEqual(10, p.get_result())
        self.assertIsNone(p.get_exception())

    def test_should_enforce_submit_promise_takes_a_Promise(self):
        """Should enfore submit_promise requires a Promise"""
        self.assertRaises(TypeError, self.pk.submit_promise, ('do it',))

    def test_should_complete_a_single_task_with_kwargs(self):
        """Should complete a Promise using kwargs."""
        # Implies that auto-stop is functioning properly.
        p = self.pk.submit(get_longest, kwargs={ \
            'item_1': 'Python', 'item_2': 'Rocks'})
        while not p.is_ready():
            sleep(0.01)
        self.assertEqual('Python', p.get_result())
        self.assertIsNone(p.get_exception())

    def test_should_complete_a_single_task_by_args(self):
        """Should complete a single task (args)."""
        # Implies that auto-stop is functioning properly.
        p = self.pk.submit(slow_add, (5, 2))
        while not p.is_ready():
            sleep(0.01)
        self.assertEqual(7, p.get_result())
        self.assertIsNone(p.get_exception())

    def test_should_complete_multiple_tasks(self):
        """Should complete a multiple tasks."""
        # Implies that auto-stop is functioning properly.
        ps = [self.pk.submit(slow_add, (i, 1000)) for i in range(5)]
        while self.pk.is_running():
            sleep(0.01)
        for i in range(5):
            self.assertEqual(i+1000, ps[i].get_result())
            self.assertIsNone(ps[i].get_exception())
            self.assertTrue(ps[i].is_ready())

    def test_should_call_notify_delegate_when_done(self):
        """Should call the notify delegate when the task is done."""
        # Implies that auto-stop is functioning properly.
        notify_tracker = {'called': False}

        def notify(promise):
            self.assertTrue(promise.is_ready())
            self.assertEqual(7, promise.get_result())
            self.assertIsNone(promise.get_exception())
            notify_tracker['called'] = True

        p = self.pk.submit(slow_add, (5, 2), notify=notify)
        while self.pk.is_running():
            sleep(0.01)

        self.assertEqual(7, p.get_result())
        self.assertEqual(notify, p._notify)
        self.assertIsNone(p.get_exception())
        self.assertTrue(notify_tracker['called'])

    def test_should_populate_exception_when_bad_things_happen(self):
        """Should catch and record exceptions in tasks."""
        # Impleies that auto-stop is functioning properly.
        p = self.pk.submit(slow_div, (10, 0))
        while not p.is_ready():
            sleep(0.01)
        self.assertIsNone(p.get_result())
        self.assertIsInstance(p.get_exception(), ZeroDivisionError)

    def test_should_not_stop_if_auto_stop_false(self):
        """PromiseKeeper should keep running if auto-stop is False."""
        pk = PromiseKeeper(auto_stop=False)
        p = pk.submit(slow_add, (1, 2))
        while not p.is_ready():
            sleep(0.01)
        self.assertTrue(pk.is_running())
        pk.stop(True)

    def test_should_not_auto_start_if_auto_start_set_to_False(self):
        """PromiseKeeper shouldn't automatically start if not configured to."""
        pk = PromiseKeeper(auto_start=False)
        p = pk.submit(slow_add, (1, 2))
        self.assertFalse(pk.is_running())

    def test_should_run_results_of_iterator(self):
        """Should run iterate over all promises in iterator."""

        class test_class(object):
            def __init__(self):
                self.promises = []

            def square(self, x):
                sleep(random() * 0.1)
                return x*x

            def generator(self):
                for i in range(5):
                    promise = Promise(self.square, (i,))
                    self.promises.append(promise)
                    yield promise

        tester = test_class()
        pk = PromiseKeeper(iterator=tester.generator())
        
        while pk.is_running():
            x = filter(lambda x: x.is_ready(), tester.promises)
            print len(x), x

        self.assertEqual(5, len(tester.promises))
        for i in range(5):
            self.assertEqual(i*i, tester.promises[i].get_result())

    def test_should_enforce_iterator_generates_Promises(self):
        """Should enforce iterator generates Promises"""

        iterator = iter([1, 2, 3])
        self.assertRaises(TypeError, PromiseKeeper, kwds={'iterator':iterator})

    def test_then_do(self):
        """Should perform chainged tasks via then_do."""
        pk = PromiseKeeper(auto_start=False, auto_stop=False)
        p = pk.submit(lambda x: -x, (5,)) \
            .then_do(lambda x: x.get_result() * 5) \
            .then_do(lambda x: x.get_result() - 5)
        pk.start()
        while not p.is_ready():
            pass
        pk.stop()
        self.assertEqual(p.get_result(), -30)

