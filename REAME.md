Python Promise Keeper
=====================

This module creates a multi-threaded system that you can submit work to be
asyncrhonously executed to.  It will return immediately with a promise that
you can periodically check to see if the work is done.

Example usage:

    >>> from promise_keeper import PromiseKeeper
    >>> pc = PromiseKeeper(5)  # 5 threads
    >>> pc.start()
    >>> multiply = lambda x, y : x*y
    >>> promise = pc.submit(multiply, (128, 2))
    >>> while not promise.is_ready()
    ...     continue
    >>> print promise.result
    256
    >>> pc.stop()
