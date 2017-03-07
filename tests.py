#!/usr/bin/env python
"""
Some simple tests for the promise_keeper module.
"""

from promise_keeper import PromiseKeeper
from time import sleep
from random import random
from unittest import TestCase


def slow_add(x, y):
    sleep(random() * 1)
    return x+y


def slow_div(x, y):
    sleep(random() * 1)
    return x/y


class TestPromiseKeeper(TestCase):
    """
    A few simple tests to be used for sanity checks.
    """

    def setUp(self):
        self.pk = PromiseKeeper(3)

    def test_should_complete_a_task(self):
        """Should complete a single task."""
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
