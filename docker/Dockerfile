FROM alpine:edge

RUN apk add --no-cache python3 && \
    pip3 install --no-cache-dir linode-dynamic-dns

ENV FREQUENCY=15

CMD echo "*/$FREQUENCY * * * * linode-dynamic-dns" | crontab - && \
    crond -f
