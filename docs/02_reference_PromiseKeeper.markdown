Python PromiseKeeper Reference
==============================

This is the main reference documentation for the promise\_keeper module.  The
source maintains more up to date documentation in docstrings.  Check pydocs
for more information.


Class PromiseKeeper
-------------------
This class is the starting point you should use.  It as a number of constructor
arguments that you can specify that will taylor how it behaves.  There's also
a number of methods available that will allow you to interact with it.


### Constructor Arguments ###

The PromiseKeeper has the following constructor arguments.  They are specified
when you instantiate an instance of a PromiseKeeper.

__number\_threads__ - The PromiseKeeper defaults to 1 thread, but you can
specify more.

__auto\_start__ - This value defaults to _True_.  When it's _True_, the
PromiseKeeper will startup on it's own as soon as you submit a request to
it.  Sometimes you may want to instantiate a PromiseKeeper and delay it
beginning to work on the requests until a specific time or until a certain
number of requests have been submitted.  If you specify _False_ for this
parameter, you can start the PromiseKeeper later with the _start_ method.

__auto\_stop__ - This value also defaults to _True_.  When it's _True_, the
PromiseKeeper will stop on it's own when the request queue becomes empty.
This will allow your script to terminate properly without having to remember
to stop the PromiseKeeper.  If set this value to _False_, you will need to
remember to _stop_ the PromiseKeeper when you're done.  Otherwise, your
script will not terminate.

Example usages:

    from promise_keeper import PromiseKeeper

    pk = PromiseKeeper(10, False, False)
    pk = PromiseKeeper(number_threads=10)
    pk = PromiseKeeper(auto_start=False, auto_stop=True)


### Methods ###

The PromiseKeeper has the following methods for you to interact with.

__submit(task, args=[], kwargs={}, notify=None)__ - You use this method to
submit tasks to the PromiseKeeper's work queue.  __task__ is any Python
callable (i.e. a function or class method).  __args__ and __kwargs__ are the
arguments you want to pass to the __task__.  Notify should be a callable that
takes a single argument.  The PromiseKeeper will call the specified callable,
passing the promise associated with the given task when the task is
completed.  It's essentially a callback that get's called when the work
is done. Submit immediately returns a new Promise object.  This Promise
can be used to track the progress of the task and review the results.

    from promise_keeper import PromiseKeeper
    pk = PromiseKeeper()
    p = pk.submit(map, (lambda x: x*x, range(50)))

__submit\_promise(promise)__ - Submit the given Promise to the PromiseKeepers
work queue.  Does not return anything, but the Promise that is passed to this
method will be updated by the PromiseKeeper as the task is executed.

__start()__ - Starts the PromiseKeeper if it's not already started.  If the
PromiseKeeper was already running, this method will raise a
__PromiseKeeperStateError__ exception.

    from promise_keeper import PromiseKeeper
    pk = PromiseKeeper(auto_start=False)
    # submit a bunch of requests
    pk.start()

__stop(block=True)__ - Stops the PromiseKeeper if it's running.  What this means
is that it will finish up any tasks that are already running, but not start any
new ones.  If __block__ is __True__ (default), this method will block until all
currently running tasks complete.  If it's __False__, this method will return
immediately even though some tasks might still be running.

    from promise_keeper import PromiseKeeper
    pk = PromiseKeeper(auto_stop=False)
    # submit a bunch of requests
    # use their results
    pk.stop(False)

__is\_running()__ - Returns __True__ if the PromiseKeeper is running.  Returns
__False__ otherwise.

    def some_method(promise_keeper):
        if not promise_keeper.is_running():
            promise_keeper.start()

Copyright (c) 2017, Steve Brettschneider.
License: MIT (see LICENSE for details)
