import argparse
import functools
import ipaddress
import logging
import os
import pkg_resources

import requests

VERSION = pkg_resources.get_distribution('linode_dynamic_dns').version

LOGGER = logging.getLogger(__name__)

TIMEOUT = 15

IP_URLS = {4: os.environ.get('IPV4_URL', 'https://ipv4.icanhazip.com'),
           6: os.environ.get('IPV6_URL', 'https://ipv6.icanhazip.com')}

LINODE_API_URL = 'https://api.linode.com/api'


class LinodeAPI:
    def __init__(self, key):
        self.session = requests.Session()
        self.session.auth = (' ', key)

    def get(self, params):
        response = self.session.get(LINODE_API_URL, params=params,
                                    timeout=TIMEOUT)
        response.raise_for_status()
        data = response.json()

        if data['ERRORARRAY']:
            LOGGER.error(data['ERRORARRAY'])
            raise requests.RequestException

        return data["DATA"]

    def get_domain_id(self, target_domain):
        for domain in self.get({'api_action': 'domain.list'}):
            if domain['DOMAIN'] == target_domain:
                return domain['DOMAINID']

    def get_resources(self, domain, host):
        domain_id = self.get_domain_id(domain)
        if domain_id is None:
            raise KeyError('Cannot determine domain ID.')

        resources = self.get(
            {'api_action': 'domain.resource.list',
             'DomainId': domain_id})
        for resource in resources:
            if resource['NAME'] == host:
                yield LinodeResource(self, resource)


class LinodeResource:
    def __init__(self, api, data):
        self.api = api
        self.id = data['RESOURCEID']
        self.ip = ipaddress.ip_address(data['TARGET'])

    def update_ip(self, new_ip):
        if new_ip != self.ip:
            LOGGER.info(f'New IP: {new_ip}')
            self.ip = new_ip
            self.api.get({'api_action': 'domain.resource.update',
                          'ResourceID': self.id,
                          'Target': new_ip.exploded})


@functools.lru_cache()
def get_ip(version):
    url = IP_URLS[version]
    response = requests.get(url, timeout=TIMEOUT)
    response.raise_for_status()
    ip = ipaddress.ip_address(response.text.strip())
    if ip and ip.version == version:
        LOGGER.info(f'Local IPv{version}: {ip}')
        return ip
    else:
        LOGGER.info(f'No local IPv{version}.')
        return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--version', action='store_const',
                        const=True)
    args = parser.parse_args()

    if args.version:
        print(VERSION)
        return

    logging.basicConfig(level=logging.INFO)

    DOMAIN = os.environ['DOMAIN']
    HOST = os.environ['HOST']
    TOKEN = os.environ['TOKEN']

    api = LinodeAPI(TOKEN)

    for resource in api.get_resources(DOMAIN, HOST):
        resource.update_ip(get_ip(resource.ip.version))


if __name__ == "__main__":
    main()
