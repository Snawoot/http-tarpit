#!/usr/bin/env python3

import argparse
import asyncio
import logging
import ssl
import os
import signal
from functools import partial

from .server import EternalServer
from .constants import OperationMode, LogLevel
from .utils import setup_logger, enable_uvloop


def parse_args():

    def check_port(value):
        ivalue = int(value)
        if not 0 < ivalue < 65536:
            raise argparse.ArgumentTypeError(
                "%s is not a valid port number" % value)
        return ivalue

    def check_positive_int(value):
        ivalue = int(value)
        if ivalue <= 0:
            raise argparse.ArgumentTypeError(
                "%s is not valid positive integer value" % value)
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
    parser.add_argument("-m", "--mode",
                        help="operation mode",
                        type=OperationMode.__getitem__,
                        choices=list(OperationMode),
                        default=OperationMode.clock)
    parser.add_argument("-b", "--buffer-size",
                        default=128*2**10,
                        type=check_positive_int,
                        help="send buffer size")

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


def exit_handler(exit_event, signum, frame):
    logger = logging.getLogger('MAIN')
    if exit_event.is_set():
        logger.warning("Got second exit signal! Terminating hard.")
        os._exit(1)
    else:
        logger.warning("Got first exit signal! Terminating gracefully.")
        exit_event.set()


async def heartbeat():
    while True:
        await asyncio.sleep(.5)


async def amain(args, context, loop):
    logger = logging.getLogger('MAIN')
    server = EternalServer(address=args.bind_address,
                           port=args.bind_port,
                           ssl_context=context,
                           mode=args.mode,
                           buffer_size=args.buffer_size,
                           loop=loop)
    await server.setup()
    logger.info("Server startup completed.")

    exit_event = asyncio.Event(loop=loop)
    beat = asyncio.ensure_future(heartbeat(), loop=loop)
    sig_handler = partial(exit_handler, exit_event)
    signal.signal(signal.SIGTERM, sig_handler)
    signal.signal(signal.SIGINT, sig_handler)
    await exit_event.wait()
    beat.cancel()
    logger.debug("Eventloop interrupted. Shutting down server...")
    await server.stop()


def main():
    args = parse_args()
    logger = setup_logger('MAIN', args.verbosity)
    setup_logger(EternalServer.__name__, args.verbosity)

    if not args.disable_uvloop:
        res = enable_uvloop()
        logger.info("uvloop" + ("" if res else " NOT") + " activated.")

    if args.cert:
        context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        context.load_cert_chain(certfile=args.cert, keyfile=args.key)
    else:
        context = None

    logger.debug("Starting server...")
    loop = asyncio.get_event_loop()
    loop.run_until_complete(amain(args, context, loop))
    loop.close()
    logger.info("Server stopped.")


if __name__ == '__main__':
    main()
