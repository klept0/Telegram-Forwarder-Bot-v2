import asyncio

from source.utils.Console import Terminal

console = Terminal.console


class MessageQueue:
    """Rate-limited async queue for Telegram messages."""

    def __init__(self, max_concurrent=1, delay=1.0):
        """
        Args:
            max_concurrent: Max concurrent message forwarding (Telegram recommends 1-2 per second).
            delay: Delay in seconds between sending messages.
        """
        self.queue = asyncio.Queue()
        self.max_concurrent = max_concurrent
        self.delay = delay
        self.current_task = None
        self._workers = []
        self._running = False

    async def start(self):
        """Start the worker(s) to process the queue."""
        if self._running:
            return
        self._running = True
        for _ in range(self.max_concurrent):
            worker = asyncio.create_task(self._worker())
            self._workers.append(worker)

    async def stop(self):
        """Stop all workers gracefully."""
        self._running = False
        for worker in self._workers:
            worker.cancel()
        await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers.clear()

    async def _worker(self):
        while self._running:
            got_item = False
            try:
                func, args = await self.queue.get()
                got_item = True
                self.current_task = self._format_task_name(args)
                await func(*args)
                await asyncio.sleep(self.delay)  # rate limit
            except asyncio.CancelledError:
                break
            except Exception as e:
                console.print(f"[bold red]Queue Worker Error:[/bold red] {e}")
            finally:
                if got_item:
                    self.queue.task_done()
                self.current_task = None

    def _format_task_name(self, args):
        """Build a compact human-readable task label for queue status output."""
        if len(args) < 2:
            return "unknown"

        payload = args[1]
        if isinstance(payload, list):
            count = len(payload)
            first_id = getattr(payload[0], "id", "?") if payload else "?"
            return f"album(count={count}, first_id={first_id})"

        message_id = getattr(payload, "id", "?")
        chat_id = getattr(payload, "chat_id", "?")
        return f"message(chat={chat_id}, id={message_id})"

    async def put(self, item):
        """Add a function with args to the queue.
        Args:
            item: Tuple (function, args)
        """
        await self.queue.put(item)
        await self.start()  # ensure the worker is running

    def qsize(self):
        return self.queue.qsize()
