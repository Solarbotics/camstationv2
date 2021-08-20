"""Classes designed for reading values from some source.

Provides common utilities for context-managed readers,
seperate-thread single instance readers,
etc.
"""

import logging
import time
import threading
import typing as t

logger = logging.Logger(__name__)
logger.addHandler(logging.NullHandler())

T = t.TypeVar("T")


class SelfContext:
    """Simple minimum context implementation.

    Designed for objects that are opened on construction
    and can then be closed.

    Returns self on entry,
    and calls self.close on exit.

    Default self.close is implemented to be empty.
    """

    def close(self) -> None:
        """Close this object."""

    def __enter__(self: T) -> T:
        """Create context manager view, i.e. self."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the context by closing this object."""
        self.close()


class Reader(t.Generic[T]):
    """Type that can read and return a value."""

    def read(self) -> T:
        """Read a single value."""
        raise NotImplementedError


class Obtainer(t.Generic[T]):
    """Type that returns a value based on a calibration base."""

    def obtain(self, base: T) -> T:
        """Produce a calibrated value."""
        raise NotImplementedError


class ReaderContext(SelfContext, Reader[T]):
    """Reader that is also a context manager.

    Returns self on entry and calls an empty close() on exit,
    and has an abstract methods for reading a value.
    """


class Device(ReaderContext[T], Obtainer[T]):
    """Readable device that also has calibration capabilities."""


class ThreadObjects(t.NamedTuple):
    """Various threading objects used by ThreadedReader.

    Composed into a single class since they either all exist
    or none exist.
    """

    thread: threading.Thread
    condition: threading.Condition
    stop_flag: threading.Event


class ThreadedReader(Reader[T]):
    """Compose and imitate a single Reader instance that runs in a different thread.

    By default, lazily constructs the thread and instance upon first request,
    and automatically tears down after a period of inactivity.
    """

    def __init__(
        self,
        factory: t.Callable[[], ReaderContext[T]],
        *,
        lazy: bool = True,
        timeout: t.Optional[float] = None
    ) -> None:
        """Construct a new ThreadedReader.

        Constructs a Reader in a seperate thread using the provided factory.

        If lazy is False, a thread is created upon initialization of this class,
        otherwise it is created upon the first read call.

        If timeout is not None, the thread will be torn down after no read
        is requested for `timeout` seconds
        (minimum; actual time before teardown may be longer).

        Calls post_init before returning but before creating the thread
        if not lazy.
        """
        self.factory = factory
        self.timeout = timeout
        self.lazy = lazy

        self.thread_objects: t.Optional[ThreadObjects] = None

        self.last_read: float = 0
        self.value: t.Optional[T] = None

        if not self.lazy:
            self.activate()

        self.post_init()

    def post_init(self) -> None:
        """Run initialization logic after the default init.

        Provided to allow easy constant / default setting / etc
        without having to duplicate the init signature.
        """

    def activate(self) -> threading.Condition:
        """Activate this ThreadedReader, starting a new thread if neccesary."""
        if self.thread_objects is None:
            lock = threading.Lock()
            condition = threading.Condition(lock)
            # Event defaults to false
            stop = threading.Event()
            thread = threading.Thread(target=self.operate, args=(condition, stop))
            self.thread_objects = ThreadObjects(thread, condition, stop)
            thread.start()
            return condition
        else:
            return self.thread_objects.condition

    def operate(self, condition: threading.Condition, stop: threading.Event) -> None:
        """Run seperate thread logic.
        Should not be called manually, is instead called by
        constructing a thread on this function from self.activate.

        Constructs a new Reader using the factory,
        and then runs a loop until stopped.

        The loop will stop if the time since a read exceeds the timeout.

        The loop calls self.update with the constructed Reader,
        and then calls notify_all on the condition returned by self.activate.

        This condition variable is waited upon by .read if
        no value has been written, .update should usually
        write a value to self.value.
        """
        with self.factory() as reader:
            self.last_read = time.time()
            # If self.timeout is None, the left hand of `or`
            # succeeds and the condition automatically passes without
            # checking the right side
            # If its not None, the right side must be true for the loop
            # to continue to execute
            while not stop.is_set() and (
                self.timeout is None or time.time() - self.last_read <= self.timeout
            ):
                value = self.get_value(reader)
                with condition:
                    self.value = value
                    condition.notify_all()
        # Clear thread objects before stopping
        # so other threads can tell that the thread stopped.
        self.thread_objects = None

    def get_value(self, reader: Reader[T]) -> T:
        """Implementation dependent update behaviour that happens on every loop of the thread.

        Must return a value to be saved in self.value in order
        to semantically fit with the default .operate.

        Default implementation simply returns the value read from the reader.
        """
        return reader.read()

    def read(self) -> T:
        """Provide the last value read by the thread.

        Starts a new thread if neccesary,
        and blocks until a value is available.
        """
        condition = self.activate()
        with condition:
            while self.value is None:
                condition.wait()
            value = self.value
            self.last_read = time.time()
        return value

    def stop(self) -> None:
        """Stops the ThreadedReader, stopping the contained thread.

        Blocks until the thread stops.

        If no thread was running, returns instantly"""
        if self.thread_objects is not None:
            self.thread_objects.stop_flag.set()
            self.thread_objects.thread.join()
            self.thread_objects = None
