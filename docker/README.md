Update Linode DNS records with your local IPv4 and IPv6 addresses.

# Environment Variables

**Required**
- ``DOMAIN`` - Domain name
- ``HOST`` - Host name (aka subdomain)
- ``TOKEN`` - Linode API token

**Optional**
- ``FREQUENCY`` - Number of minutes to wait between updates (default 15).

# Usage

```
$ docker run \
    -e DOMAIN=yourdomain.com \
    -e HOST=www \
    -e TOKEN=apitoken \
    nvllsvm/linode-dynamic-dns
```
