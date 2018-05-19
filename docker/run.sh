#!/bin/sh
CRON_SCRIPT=/dynamic-dns.sh
cat > $CRON_SCRIPT<<EOF
export HOST=$HOST
export DOMAIN=$DOMAIN
export TOKEN=$TOKEN
linode-dynamic-dns
EOF
chmod +x $CRON_SCRIPT

echo "*/$FREQUENCY * * * * $CRON_SCRIPT" | crontab -
crond -f
