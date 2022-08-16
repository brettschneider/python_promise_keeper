"""Unit tests for the promise_keeper module"""
import time
from random import random
from time import sleep

import pytest

from promise_keeper import PromiseKeeper, Promise


@pytest.fixture
def sut():
    return PromiseKeeper(3)


def slow_add(x, y):
    sleep(random() * 1)
    return x + y


def slow_div(x, y):
    sleep(random() * 1)
    return x / y


def get_longest(item_1="", item_2=""):
    if len(item_1) > len(item_2):
        return item_1
    else:
        return item_2


def test_should_complete_a_single_task_by_promise(sut):
    """Should complete a single task (Promise)."""
    p = Promise(slow_add, [7, 3])
    sut.submit_promise(p)
    while not p.is_ready():
        sleep(0.01)
    assert 10 == p.get_result()
    assert p.get_exception() is None


def test_should_enforce_submit_promise_takes_a_promise(sut):
    """Should enfore submit_promise requires a Promise"""
    with pytest.raises(TypeError) as exc_info:
        sut.submit_promise("do it")
    assert exc_info.value.args[0] == 'submit_promise requires a Promise argument'


def test_should_complete_a_single_task_with_kwargs(sut):
    """Should complete a Promise using kwargs."""
    p = sut.submit(get_longest, kwargs={"item_1": "Python", "item_2": "Rocks"})
    while not p.is_ready():
        sleep(0.01)
    assert p.get_result() == 'Python'
    assert p.get_exception() is None


def test_should_complete_a_single_task_by_args(sut):
    """Should complete a single task (args)."""
    p = sut.submit(slow_add, [5, 2])
    while not p.is_ready():
        sleep(0.01)
    assert p.get_result() == 7
    assert p.get_exception() is None


def test_should_complete_multiple_tasks(sut):
    """Should complete a multiple tasks."""
    ps = [sut.submit(slow_add, [i, 1000]) for i in range(5)]
    while sut.is_running():
        sleep(0.01)
    for i in range(5):
        assert ps[i].get_result() == i + 1000
        assert ps[i].get_exception() is None
        assert ps[i].is_ready()


def test_should_call_notify_delegate_when_done(sut):
    """Should call the notify delegate when the task is done."""
    notify_tracker = {"called": False}

    def notify(promise):
        assert promise.is_ready()
        assert promise.get_result() == 7
        assert promise.get_exception() is None
        notify_tracker["called"] = True

    p = sut.submit(slow_add, [5, 2], notify=notify)
    while sut.is_running():
        sleep(0.01)

    assert p.get_result() == 7
    assert p._notify is notify
    assert p.get_exception() is None
    assert notify_tracker['called']


def test_should_populate_exception_when_bad_things_happen(sut):
    """Should catch and record exceptions in tasks."""
    p = sut.submit(slow_div, [10, 0])
    while not p.is_ready():
        sleep(0.01)
    assert p.get_result() is None
    assert isinstance(p.get_exception(), ZeroDivisionError)


def test_should_not_stop_if_auto_stop_false(sut):
    """PromiseKeeper should keep running if auto-stop is False."""
    pk = PromiseKeeper(auto_stop=False)
    p = pk.submit(slow_add, [1, 2])
    while not p.is_ready():
        sleep(0.01)
    assert pk.is_running()
    pk.stop(True)


def test_should_not_auto_start_if_auto_start_set_to_False(sut):
    """PromiseKeeper shouldn't automatically start if not configured to."""
    pk = PromiseKeeper(auto_start=False)
    _ = pk.submit(slow_add, [1, 2])
    assert not pk.is_running()


def test_should_run_results_of_iterator(sut):
    """Should run iterate over all promises in iterator."""

    class TestClass(object):
        def __init__(sut):
            sut.promises = []

        def square(self, x):
            sleep(random() * 0.1)
            return x * x

        def generator(self):
            for i in range(5):
                promise = Promise(self.square, [i, ])
                self.promises.append(promise)
                yield promise

    tester = TestClass()
    pk = PromiseKeeper(iterator=tester.generator())

    while pk.is_running():
        time.sleep(0)

    assert len(tester.promises) == 5
    for i in range(5):
        assert tester.promises[i].get_result() == i * i


def test_then_do():
    """Should perform chained tasks via then_do."""
    pk = PromiseKeeper(auto_start=False)
    p = (
        pk.submit(lambda x: -x, [5, ])
            .then_do(lambda x: x.get_result() * 5)
            .then_do(lambda x: x.get_result() - 5)
    )
    pk.start()
    while not p.is_ready():
        pass
    assert p.get_result() == -30
