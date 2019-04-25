FROM python:3-slim
LABEL maintainer="Vladislav Yarmak <vladislav-ex-src@vm-0.com>"

VOLUME [ "/srv/certs" ]
COPY . /build
RUN pip3 install --no-cache-dir /build && \
    pip3 install --no-cache-dir uvloop && \
    rm -rf /build

EXPOSE 8080/tcp
ENTRYPOINT [ "http-tarpit" ]
