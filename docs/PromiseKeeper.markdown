PromiseKeeper
=============

The PromiseKeeper is a class that can be used to run tasks asynchrounously.
The main idea is to instaniate an instance of the PromiseKeeper and then
submit requests for it to do work on your behalf.  It will schedule your
request to be executed on a thread and return a Promise isntance to you.
You can look at the promise to determine the status of the execution.

The promise keeper will track the results (return value) of your requested
work and include it in the Promise that it returned to you when you submitted
the request.  If your work request throws an exception, the PromiseKeeper
will capture the exception and include that in the Promise as well.

Here's a quick example:

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

The PromiseKeeper maintains an internal queue of tasks to be completed.  This
means you can submit lots of requests for work and it will complete the
requests in the order that it recieved them.  Here's another example:

    #!/usr/bin/env python

    from promise_keeper import PromiseKeeper
    from random import random
    from time import sleep

    def slow_square(x):
        sleep(random() * 3)
        return x*x

    pk = PromiseKeeper(2)  # use 2 threads this time (defaults to 1)!

    # doesn't block
    promises = [pk.submit(slow_square, (i,)) for i in range(10)]

    # while the promise is being processed
    # you can go on and do other work.

    while pk.is_running():
        # Again, you can do off and do other things while there
        # tasks are being worked on.
        pass

    # Check the result of your work
    for promise in promises:
        print promise.get_result()

