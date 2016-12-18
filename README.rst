linode-dynamic-dns
==================

A small utility to update Linode DNS records with your local IPv4 and IPv6 addresses.

Configuration
-------------

linode-dynamic-dns will look for a config at ``/etc/linode_dynamic_dns/config.ini`` though another path can be specified with the ``-c`` or ``--config`` argument.

All options are required, with the expection of ``ipv4_url`` and ``ipv6_url``. When excluded, icanhazip.com will be used.

::

    [linode_dynamic_dns]
    domain = domain.com
    host = test
    key = YOUR_KEY
    ipv4_url = https://ipv4.icanhazip.com/
    ipv6_url = https://ipv6.icanhazip.com/
