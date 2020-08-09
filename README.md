http-tarpit
===========

Web-server which produces infinite chunked-encoded responses

---

:heart: :heart: :heart:

You can say thanks to the author by donations to these wallets:

- ETH: `0xB71250010e8beC90C5f9ddF408251eBA9dD7320e`
- BTC:
  - Legacy: `1N89PRvG1CSsUk9sxKwBwudN6TjTPQ1N8a`
  - Segwit: `bc1qc0hcyxc000qf0ketv4r44ld7dlgmmu73rtlntw`

---

## Requirements

* Python 3.5.3+
* aiohttp 3.4.4+

## Installation

Standard Python package installation. This package is available on PyPI:

```
pip3 install http-tarpit
```

### Docker

Run following command to pull image and print options help:

```bash
docker run -it yarmak/http-tarpit --help
```

Use following command with required options to run daemon in background (example):

```bash
docker run -dit \
    -p 8080:8080 \
    --restart unless-stopped \
    --name http-tarpit \
    yarmak/http-tarpit -m null
```

TLS example:

```bash
docker run -dit \
    -p 8443:8080 \
    -v /etc/letsencrypt:/srv/certs:ro \
    --restart unless-stopped \
    --name http-tarpit \
    yarmak/http-tarpit \
    -c /srv/certs/live/example.com/fullchain.pem \
    -k /srv/certs/live/example.com/privkey.pem
```

## Usage

Synopsis:

```
$ http-tarpit --help
usage: http-tarpit [-h] [--disable-uvloop] [-v {debug,info,warn,error,fatal}]
                   [-m {clock,newline,urandom,null,slow_newline}]
                   [-a BIND_ADDRESS] [-p BIND_PORT] [-c CERT] [-k KEY]

Web-server which produces infinite chunked-encoded responses

optional arguments:
  -h, --help            show this help message and exit
  --disable-uvloop      do not use uvloop even if it is available (default:
                        False)
  -v {debug,info,warn,error,fatal}, --verbosity {debug,info,warn,error,fatal}
                        logging verbosity (default: info)
  -m {clock,newline,urandom,null,slow_newline}, --mode {clock,newline,urandom,null,slow_newline}
                        operation mode (default: clock)

listen options:
  -a BIND_ADDRESS, --bind-address BIND_ADDRESS
                        bind address (default: 0.0.0.0)
  -p BIND_PORT, --bind-port BIND_PORT
                        bind port (default: 8080)

TLS options:
  -c CERT, --cert CERT  enable TLS and use certificate (default: None)
  -k KEY, --key KEY     key for TLS certificate (default: None)

```

### Modes of operation

* `clock` - feed client with current time string every second
* `newline` - feed client with newlines as fast as possible
* `urandom` - feed client with random bytes as fast as possible
* `null` - feed client with zero bytes as fast as possible
* `slow_newline` - feed client with newline character every second
