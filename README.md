Python PromiseKeeper
===================

This module creates a multi-threaded system that you can submit work to, to be
executed asynchronously.  It will return immediately with a promise that you
can periodically check to see if the work is done.

The main idea is to instantiate an instance of the PromiseKeeper and then
submit requests for it to do work on your behalf.  It will schedule your
request to be executed on a thread and return a Promise instance to you.
You can look at the promise to determine the status of the execution.

The promise keeper will track the results (return value) of your requested
work and include it in the Promise that it returned to you when you submitted
the request.  If your work request raises an exception, the PromiseKeeper
will capture the exception and include that in the Promise as well.

Here's a quick example:

    #!/usr/bin/env python

    from promise_keeper import PromiseKeeper
    from random import random
    from time import sleep

    def slow_square(x: int) -> int:
        sleep(random() * 3)
        return x*x

    pk = PromiseKeeper()

    # doesn't block
    promise = pk.submit(slow_square, (10,))

    # while the promise is being processed
    # you can go on and do other work.

    while not promise.is_ready():
        # do other work here.
        print('.')

    # Check the result of your work
    print(promise.get_result())

The PromiseKeeper maintains an internal queue of tasks to be completed.  This
means you can submit lots of requests for work and it will complete the
requests in the order that it recieved them.  Here's another example:

    #!/usr/bin/env python

    from promise_keeper import PromiseKeeper
    from random import random
    from time import sleep

    def slow_square(x: int) -> int:
        sleep(random() * 3)
        return x*x

    pk = PromiseKeeper(2)  # use 2 threads this time! (defaults to 1)

    # doesn't block
    promises = [pk.submit(slow_square, (i,)) for i in range(10)]

    # while the promise is being processed
    # you can go on and do other work.

    while pk.is_running():
        # Again, you can go off and do other things while the tasks are being
        # worked on.
        pass

    # Check the result of your work
    for promise in promises:
        print(promise.get_result())

As mentioned earlier, the PromiseKeeper will even keep track of exceptions
thrown by your code, so you don't have to worry about a crash.

    #!/usr/bin/env python

    from promise_keeper import PromiseKeeper
    from random import random
    from time import sleep

    def slow_div(x: int, y: int) -> int:
        sleep(random() * 1)
        return x / y

    pk = PromiseKeeper(3)
    promises = [pk.submit(slow_div, (200, i)) for i in range(-3, 4)]

    while pk.is_running():
        pass

    for promise in promises:
        if promise.get_exception() is None:
            print(promise.get_result())
        else:
            print(promise.get_exception())

You can even have the PromiseKeeper notify you when your promise is completed
rather than having to poll the promises to see when they're done.


    #!/usr/bin/env python

    from promise_keeper import PromiseKeeper, Promise
    from random import random
    from time import sleep

    def slow_div(x: int, y: int) -> int:
        sleep(random() * 1)
        return x / y

    def promise_completed(promise: Promise) -> None:
        if promise.get_exception() is None:
            print("Result", promise.get_result())
        else:
            print("Error", promise.get_exception())

    pk = PromiseKeeper(3)
    promises = [pk.submit(slow_div, (200, i), notify=promise_completed) \
        for i in range(-3, 4)]

    while pk.is_running():
        pass

