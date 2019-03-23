import asyncio
import datetime
import logging
import os

from aiohttp import web
from .constants import *


class EternalServer:
    SHUTDOWN_TIMEOUT = 5

    def __init__(self, *, address=None, port=8080, ssl_context=None,
                 mode=OperationMode.clock, buffer_size=128*2**10, loop=None):
        self._loop = loop if loop is not None else asyncio.get_event_loop()
        self._logger = logging.getLogger(self.__class__.__name__)
        self._address = address
        self._port = port
        self._ssl_context = ssl_context
        self._mode = mode
        self._int_fut = self._loop.create_future()
        self._shutdown = asyncio.ensure_future(self._int_fut, loop=self._loop)
        self._handler = {
            OperationMode.clock: self.handler_clock,
            OperationMode.null: self.handler_null,
            OperationMode.newline: self.handler_newline,
            OperationMode.urandom: self.handler_urandom,
            OperationMode.slow_newline: self.handler_slow_newline,
        }[self._mode]
        self.ZEROES=bytearray(buffer_size)
        self.NEWLINES=bytearray(0xA for _ in range(buffer_size))

    async def stop(self):
        try:
            self._int_fut.set_result(None)
        except asyncio.InvalidStateError:
            pass
        else:
            await self._server.shutdown()
            await self._site.stop()
            await self._runner.cleanup()

    async def run(self):
        await self._shutdown

    async def _guarded_run(self, awaitable):
        task = asyncio.ensure_future(awaitable)
        try:
            _, pending = await asyncio.wait((self._shutdown, task),
                                            return_when=asyncio.FIRST_COMPLETED)
        except asyncio.CancelledError:
            task.cancel()
            raise
        if task in pending:
            task.cancel()
            return None
        else:
            return task.result()

    async def common_handler(self, request):
        peer_addr = request.transport.get_extra_info('peername')
        self._logger.info("Client %s connected.", str(peer_addr))
        try:
            return await self._handler(request)
        finally:
            self._logger.info("Client %s disconnected.", str(peer_addr))

    async def handler_clock(self, request):
        resp = web.StreamResponse(headers={'Content-Type': 'text/plain'})
        resp.enable_chunked_encoding()
        await resp.prepare(request)
        while not self._shutdown.done():
            dt = datetime.datetime.utcnow()
            text = dt.strftime("%m %b %H:%M:%S.%f\n").encode('ascii')
            await self._guarded_run(resp.write(text))
            ts = dt.timestamp()
            sleep_time = max(0, 1 - datetime.datetime.utcnow().timestamp() + ts)
            await self._guarded_run(asyncio.sleep(sleep_time))
        return resp

    async def handler_null(self, request):
        resp = web.StreamResponse(
            headers={'Content-Type': 'application/octet-stream'})
        resp.enable_chunked_encoding()
        await resp.prepare(request)
        while not self._shutdown.done():
            await self._guarded_run(resp.write(self.ZEROES))
        return resp

    async def handler_newline(self, request):
        resp = web.StreamResponse(
            headers={'Content-Type': 'text/plain'})
        resp.enable_chunked_encoding()
        await resp.prepare(request)
        while not self._shutdown.done():
            await self._guarded_run(resp.write(self.NEWLINES))
        return resp

    async def handler_urandom(self, request):
        resp = web.StreamResponse(
            headers={'Content-Type': 'application/octet-stream'})
        resp.enable_chunked_encoding()
        await resp.prepare(request)
        while not self._shutdown.done():
            await self._guarded_run(resp.write(os.urandom(BUF_SIZE)))
        return resp

    async def handler_slow_newline(self, request):
        resp = web.StreamResponse(headers={'Content-Type': 'text/plain'})
        resp.enable_chunked_encoding()
        await resp.prepare(request)
        while not self._shutdown.done():
            dt = datetime.datetime.utcnow()
            await self._guarded_run(resp.write(b'\n'))
            ts = dt.timestamp()
            sleep_time = max(0, 1 - datetime.datetime.utcnow().timestamp() + ts)
            await self._guarded_run(asyncio.sleep(sleep_time))
        return resp

    async def setup(self):
        self._server = web.Server(self.common_handler)
        self._runner = web.ServerRunner(self._server)
        await self._runner.setup()
        self._site = web.TCPSite(self._runner, self._address, self._port,
                                 ssl_context=self._ssl_context,
                                 shutdown_timeout=self.SHUTDOWN_TIMEOUT)
        await self._site.start()
        self._logger.info("Server ready.")
