FROM alpine:edge

RUN apk update && \
    apk add python3 && \
    pip3 install linode-dynamic-dns

ENV FREQUENCY=15

ADD run.sh /run.sh
CMD /run.sh
