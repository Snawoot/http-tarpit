#!/usr/bin/env python3

import asyncio
from aiohttp import web
import time
import datetime




class EternalServer:
    SHUTDOWN_TIMEOUT=5

    def __init__(self):
        self._int_fut = asyncio.Future()
        self._shutdown = asyncio.ensure_future(self._int_fut)

    async def stop(self):
        try:
            self._int_fut.set_result(None)
        except:
            pass
        else:
            await self.server.shutdown(SHUTDOWN_TIMEOUT)
            await self.site.stop()
            await self.runner.cleanup()

    async def _guarded_run(self, awaitable):
        task = asyncio.ensure_future(awaitable)
        done, pending = await asyncio.wait((self._shutdown, task),
                                           return_when=asyncio.FIRST_COMPLETED)
        if task in pending:
            task.cancel()
            return None
        else:
            return task.result()

    async def handler(self, request):
        resp = web.StreamResponse(headers={'Content-Type': 'text/plain'})
        resp.enable_chunked_encoding()
        await resp.prepare(request)
        while not self._shutdown.done():
            text = datetime.datetime.utcnow().strftime("%m %b %H:%M:%S\n").encode('ascii')
            await self._guarded_run(resp.write(text))
            await self._guarded_run(asyncio.sleep(1))
        return resp


    async def setup(self):
        self.server = web.Server(self.handler)
        self.runner = web.ServerRunner(self.server)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, None, 8080)
        await self.site.start()
        print("======= Serving on http://0.0.0.0:8080/ ======")



def main():
    loop = asyncio.get_event_loop()
    server = EternalServer()
    loop.run_until_complete(server.setup())

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        loop.run_until_complete(server.stop())
    loop.close()


if __name__ == '__main__':
    main()
