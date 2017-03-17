====================
Python PromiseKeeper
====================

This module creates a multi-threaded system that you can submit work to, to be
executed asynchronously.  It will return immediately with a Promise that you
can periodically check to see if the work is done.

The main idea is to instantiate an instance of the PromiseKeeper and then
submit requests for it to do work on your behalf.  It will schedule your
request to be executed on a thread and return a Promise instance to you.
You can look at the Promise to determine the status of the execution.

The PromiseKeeper will track the results (return value) of your requested
work and include it in the Promise that it returned to you.  If your work
request raises an exception, the PromiseKeeper will capture the exception
and include that in the Promise as well.

Here's a quick example:

::

    #!/usr/bin/env python

    from promise_keeper import PromiseKeeper
    from random import random
    from time import sleep

    def slow_square(x):
        sleep(random() * 3)
        return x*x

    pk = PromiseKeeper()

    # doesn't block
    promise = pk.submit(slow_square, (10,))

    # while the promise is being processed
    # you can go on and do other work.

    while not promise.is_ready():
        # do other work here.
        print '.',

    # Check the result of your work
    print promise.get_result()

More documentation and examples can be found
`here <https://github.com/brettschneider/python_promise_keeper/tree/master/docs>`_.

Copyright (c) 2017, Steve Brettschneider.
License: MIT (see LICENSE for details)
