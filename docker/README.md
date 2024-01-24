Update Linode DNS records with your local IPv4 and IPv6 addresses.

# Environment Variables

**Required**
- ``LINODE_ACCESS_TOKEN`` - Linode API token
- ``LINODE_DNS_DOMAIN`` - Domain name
- ``LINODE_DNS_HOSTNAME`` - Host name (aka subdomain)

**Optional**
- ``FREQUENCY`` - Number of minutes to wait between updates (default 15).

# Usage

```
$ docker run \
    -e LINODE_ACCESS_TOKEN=apitoken \
    -e LINODE_DNS_DOMAIN=yourdomain.com \
    -e LINODE_DNS_HOSTNAME=www \
    nvllsvm/linode-dynamic-dns
```
