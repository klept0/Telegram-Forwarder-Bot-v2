import asyncio
import time
from collections import deque


class RateLimitedQueue:
    def __init__(self, rate: int, per: float, batch_size: int = 1):
        """
        Async rate-limiting queue for outbound messages.

        :param rate: Max number of messages allowed per window.
        :param per: Duration of the window in seconds.
        :param batch_size: Messages to send at once (burst).
        """
        self.rate = rate
        self.per = per
        self.batch_size = batch_size
        self.queue = deque()
        self.last_reset = time.monotonic()
        self.sent = 0
        self._worker_task = None

    def add(self, message):
        """Enqueue a message for sending."""
        self.queue.append(message)

    async def _worker(self, send_func):
        """Background task to process queue respecting rate limit."""
        while True:
            now = time.monotonic()

            # Reset counters when window expires
            if now - self.last_reset >= self.per:
                self.last_reset = now
                self.sent = 0

            if self.queue and self.sent < self.rate:
                # Grab up to batch_size messages
                batch = [
                    self.queue.popleft()
                    for _ in range(min(self.batch_size, len(self.queue)))
                ]
                try:
                    await send_func(batch)
                except Exception as e:
                    # Handle RetryAfter or generic errors
                    if hasattr(e, "retry_after"):
                        await asyncio.sleep(e.retry_after)
                    else:
                        print(f"[RateLimiter] Send error: {e}")
                self.sent += len(batch)
            else:
                await asyncio.sleep(0.5)

    def start(self, send_func):
        """Start worker loop with a send function (async)."""
        if not self._worker_task:
            self._worker_task = asyncio.create_task(self._worker(send_func))

    async def stop(self):
        """Cancel worker gracefully."""
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
