linode-dynamic-dns
==================

|Version| |License|

Update Linode DNS records with your local IPv4 and IPv6 addresses.

Environment Variables
---------------------

+---------------------+-----------------------------------------------------------------------------------------+
| Name                | Description                                                                             |
+=====================+=========================================================================================+
| LINODE_ACCESS_TOKEN | Your Linode API access token.                                                           |
+---------------------+-----------------------------------------------------------------------------------------+
| LINODE_DNS_DOMAIN   | The domain the host is a part of.                                                       |
+---------------------+-----------------------------------------------------------------------------------------+
| LINODE_DNS_HOSTNAME | The host record to update.                                                              |
+---------------------+-----------------------------------------------------------------------------------------+
| IPV4_URL | The URL which returns your local IPv4 address (default ``https://ipv4.icanhazip.com/``) |
+---------------------+-----------------------------------------------------------------------------------------+
| IPV6_URL | The URL which returns your local IPv6 address (default ``https://ipv6.icanhazip.com/``) |
+---------------------+-----------------------------------------------------------------------------------------+


Installation
------------

* `Arch Linux`_
* `Docker`_
* `PyPI`_

Systemd Service
---------------

Example files for a systemd service and timer are in the ``systemd`` directory.

#. Copy the ``.service`` and ``.timer`` files into ``/etc/systemd/system`` and the ``.conf`` into ``/etc``.
#. Edit the config file as required.
#. Run the following to enable the service: ::

    systemctl daemon-reload
    systemctl enable linode-dynamic-dns.timer
    systemctl start linode-dynamic-dns.timer
    systemctl start linode-dynamic-dns.service





.. |Version| image:: https://img.shields.io/pypi/v/linode-dynamic-dns.svg?
   :target: https://pypi.org/pypi/linode-dynamic-dns

.. |License| image:: https://img.shields.io/github/license/nvllsvm/linode-dynamic-dns.svg?
   :target: https://github.com/nvllsvm/linode-dynamic-dns/blob/master/LICENSE

.. _Arch Linux: https://aur.archlinux.org/packages/linode-dynamic-dns/
.. _Docker: https://hub.docker.com/r/nvllsvm/linode-dynamic-dns/
.. _PyPI: https://pypi.org/pypi/linode-dynamic-dns
