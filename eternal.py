#!/usr/bin/env python3

import enum
import argparse
import asyncio
import datetime
import logging
import ssl

from aiohttp import web


def enable_uvloop():
    try:
        import uvloop
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    except ImportError:
        return False
    else:
        return True


class LogLevel(enum.IntEnum):
    debug = logging.DEBUG
    info = logging.INFO
    warn = logging.WARN
    error = logging.ERROR
    fatal = logging.FATAL
    crit = logging.CRITICAL

    def __str__(self):
        return self.name

    def __contains__(self, e):
        return e in self.__members__


class EternalServer:
    SHUTDOWN_TIMEOUT = 5

    def __init__(self, *, address=None, port=8080, ssl_context=None):
        self._address = address
        self._port = port
        self._ssl_context = ssl_context
        self._int_fut = asyncio.Future()
        self._shutdown = asyncio.ensure_future(self._int_fut)

    async def stop(self):
        try:
            self._int_fut.set_result(None)
        except asyncio.InvalidStateError:
            pass
        else:
            await self._server.shutdown()
            await self._site.stop()
            await self._runner.cleanup()

    async def _guarded_run(self, awaitable):
        task = asyncio.ensure_future(awaitable)
        _, pending = await asyncio.wait((self._shutdown, task),
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
            dt = datetime.datetime.utcnow()
            text = dt.strftime("%m %b %H:%M:%S.%f\n").encode('ascii')
            await self._guarded_run(resp.write(text))
            ts = dt.timestamp()
            sleep_time = max(0, 1 - datetime.datetime.utcnow().timestamp() + ts)
            await self._guarded_run(asyncio.sleep(sleep_time))
        return resp


    async def setup(self):
        self._server = web.Server(self.handler)
        self._runner = web.ServerRunner(self._server)
        await self._runner.setup()
        self._site = web.TCPSite(self._runner, self._address, self._port,
                                 ssl_context=self._ssl_context,
                                 shutdown_timeout=self.SHUTDOWN_TIMEOUT)
        await self._site.start()



def setup_logger(name, verbosity):
    logger = logging.getLogger(name)
    logger.setLevel(verbosity)
    handler = logging.StreamHandler()
    handler.setLevel(verbosity)
    handler.setFormatter(logging.Formatter('%(asctime)s '
                                           '%(levelname)-8s '
                                           '%(name)s: %(message)s',
                                           '%Y-%m-%d %H:%M:%S'))
    logger.addHandler(handler)
    return logger


def parse_args():

    def check_port(value):
        ivalue = int(value)
        if not 0 < ivalue < 65536:
            raise argparse.ArgumentTypeError(
                "%s is not a valid port number" % value)
        return ivalue

    parser = argparse.ArgumentParser(
        description="Web-server which produces infinite chunked-encoded "
        "responses",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument("--disable-uvloop",
                        help="do not use uvloop even if it is available",
                        action="store_true")
    parser.add_argument("-v", "--verbosity",
                        help="logging verbosity",
                        type=LogLevel.__getitem__,
                        choices=list(LogLevel),
                        default=LogLevel.info)

    listen_group = parser.add_argument_group('listen options')
    listen_group.add_argument("-a", "--bind-address",
                              default="0.0.0.0",
                              help="bind address")
    listen_group.add_argument("-p", "--bind-port",
                              default=8080,
                              type=check_port,
                              help="bind port")

    tls_group = parser.add_argument_group('TLS options')
    tls_group.add_argument("-c", "--cert",
                           help="enable TLS and use certificate")
    tls_group.add_argument("-k", "--key",
                           help="key for TLS certificate")
    return parser.parse_args()


def main():
    args = parse_args()
    logger = setup_logger('MAIN', args.verbosity)
    setup_logger(EternalServer.__class__.__name__, args.verbosity)

    if not args.disable_uvloop:
        enable_uvloop()

    if args.cert:
        context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        context.load_cert_chain(certfile=args.cert, keyfile=args.key)
    else:
        context = None

    logger.debug("Starting server...")
    loop = asyncio.get_event_loop()
    server = EternalServer(address=args.bind_address,
                           port=args.bind_port,
                           ssl_context=context)
    loop.run_until_complete(server.setup())
    logger.info("Server startup completed.")

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        logger.info("Got interrupt signal. Shutting down server...")
        loop.run_until_complete(server.stop())
    loop.close()
    logger.info("Server stopped.")


if __name__ == '__main__':
    main()
