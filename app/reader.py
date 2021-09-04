"""Classes designed for reading values from some source.

Provides common utilities for context-managed readers,
seperate-thread single instance readers,
etc.
"""

import logging
import time
import threading
import typing as t

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

T = t.TypeVar("T")
V = t.TypeVar("V")


class Context(t.Generic[T]):
    """Context interface."""

    def __enter__(self) -> T:
        """Create context manager view."""
        raise NotImplementedError()

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the context."""
        raise NotImplementedError()


class SelfContext(Context):
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


class Threader(t.Generic[T]):
    """Class that manages a seperate thread that can be used e.g. for IO.

    By default, lazily constructs the thread and instance upon first request,
    and automatically tears down after a period of inactivity.

    Must be subclassed with an implemented .operate method.
    """

    def __init__(
        self,
        factory: t.Callable[[], Context[T]],
        *,
        lazy: bool = True,
        timeout: t.Optional[float] = None
    ) -> None:
        """Construct a new Threader.

        Constructs an object in a seperate thread using the provided factory.

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

        self.post_init()

        if not self.lazy:
            self.activate()

    def post_init(self) -> None:
        """Run initialization logic after the default init.

        Provided to allow easy constant / default setting / etc
        without having to duplicate the init signature.
        """

    def activate(self) -> threading.Condition:
        """Activate this Threader, starting a new thread if neccesary."""
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

        Constructs a new instance using the factory,
        and then calls the .body method on it within a context.

        Returns once .body returns.
        """
        with self.factory() as instance:
            self.body(instance, condition, stop)
        # Clear thread objects before stopping
        # so other threads can tell that the thread stopped.
        self.thread_objects = None

    def body(
        self, instance: T, condition: threading.Condition, stop: threading.Event
    ) -> None:
        """Method called on the context of an instance constructed from the factory.

        Allows subclasses to implement a thread loop
        without worrying about setup or teardown.

        Must be implemented.

        An object is provided, and once the function returns the thread will be closed.

        Similar to operate, should not be called manually.
        """
        raise NotImplementedError

    def stop(self) -> None:
        """Stops the Threader, stopping the contained thread.

        Blocks until the thread stops.

        If no thread was running, returns instantly"""
        if self.thread_objects is not None:
            condition = self.thread_objects.condition
            with condition:
                self.thread_objects.stop_flag.set()
                condition.notify_all()
            self.thread_objects.thread.join()
            self.thread_objects = None


class ThreadedReader(Threader[Reader[T]], Reader[T]):
    """Compose and imitate a single Reader instance that runs in a different thread.

    By default, lazily constructs the thread and instance upon first request,
    and automatically tears down after a period of inactivity.
    """

    def post_init(self) -> None:
        """Run initialization logic after the default init.

        Provided to allow easy constant / default setting / etc
        without having to duplicate the init signature.
        """
        self.last_read: float = 0
        self.value: t.Optional[T] = None

    def body(
        self, instance: Reader[T], condition: threading.Condition, stop: threading.Event
    ) -> None:
        """Run seperate thread logic.
        Should not be called manually, is instead automatically by operate.

        Runs a loop until stopped.

        The loop will stop if the time since a read exceeds the timeout.

        The loop calls self.update with the constructed Reader,
        and then calls notify_all on the condition returned by self.activate.

        This condition variable is waited upon by .read if
        no value has been written.
        """
        reader = instance
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


class Manager(Threader[T], t.Generic[T, V]):
    """Class that manages an instance of a context class."""

    def post_init(self) -> None:
        """Run initialization logic after the default init.

        Provided to allow easy constant / default setting / etc
        without having to duplicate the init signature.
        """
        self.action: t.Optional[t.Callable[[T], V]] = None

        self.last_request: float = 0
        self.result: t.Optional[V] = None

    def body(
        self, instance: T, condition: threading.Condition, stop: threading.Event
    ) -> None:
        """Method called on the context of an instance constructed from the factory.

        Allows subclasses to implement a thread loop
        without worrying about setup or teardown.

        An object is provided, and once the function returns the thread will be closed.

        Similar to operate, should not be called manually.
        """
        self.last_request = time.time()

        # Only reloop if the .wait broke for a reason
        # other than timing out, and if a stop hasn't been requested
        was_notified = True
        while not stop.is_set() and was_notified:
            logger.debug("%s, getting lock in loop", self)
            with condition:
                logger.debug("%s, got lock in loop", self)
                if self.action is None:
                    timeout: t.Optional[float]
                    if self.timeout is not None:
                        timeout = self.last_request + self.timeout - time.time()
                    else:
                        timeout = None
                    logger.debug("%s, waiting on cvariable in loop", self)
                    was_notified = condition.wait(timeout=timeout)
                if self.action is not None:
                    action = self.action
                    self.action = None
                    logger.debug("%s, Running action", self)
                    try:
                        self.result = action(instance)
                    except Exception as e:
                        raise e
                    finally:
                        condition.notify_all()
                    self.last_request = time.time()
            logger.debug("%s, released lock in loop", self)

    def request_action(self, action: t.Callable[[T], V]) -> None:
        """Implementation dependent update behaviour that happens on every loop of the thread.

        Must return a value to be saved in self.value in order
        to semantically fit with the default .operate.

        Default implementation simply returns the value read from the reader.
        """
        condition = self.activate()
        logger.debug("%s, getting lock in request", self)
        with condition:
            logger.debug("%s, acquired lock in request", self)
            self.result = None
            self.action = action
            condition.notify_all()
            logger.debug("%s, notified in request", self)
        logger.debug("%s, released lock in request", self)

    def get_result(self, grace_wait: t.Optional[float] = None) -> V:
        """Obtain the value produced by an action that was previously requested.

        Starts a new thread if neccesary,
        and blocks until a value is available.

        If called before an action is requested,
        will block indefinitely.
        """
        condition = self.activate()
        logger.debug("%s, getting lock for result", self)
        with condition:
            logger.debug("%s, got lock in result", self)
            while self.result is None:
                logger.debug("%s, waiting for result", self)
                # Timeout in case something happened to the thread
                notified = condition.wait(timeout=grace_wait)
                if self.thread_objects is None:
                    raise RuntimeError("Thread unexpectedly quit.")
            logger.debug("%s, got result", self)
            result = self.result
            self.result = None
        logger.debug("%s, released lock in result", self)
        return result
