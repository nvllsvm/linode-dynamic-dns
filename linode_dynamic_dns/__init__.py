import argparse
import functools
import ipaddress
import logging
import os
import pkg_resources

import requests

VERSION = pkg_resources.get_distribution('linode_dynamic_dns').version

TIMEOUT = 15

IP_URLS = {4: os.environ.get('IPV4_URL', 'https://ipv4.icanhazip.com'),
           6: os.environ.get('IPV6_URL', 'https://ipv6.icanhazip.com')}


class LinodeAPI(object):
    api_url = 'https://api.linode.com/api/'

    def __init__(self, key):
        self.key = key
        self.default_parameters = {'api_key': self.key}

    def get(self, parameters):
        params = self.default_parameters
        params.update(parameters)

        response = requests.get(self.api_url, params=params, timeout=TIMEOUT)
        response.raise_for_status()
        data = response.json()

        if data['ERRORARRAY']:
            logging.error(data['ERRORARRAY'])
            raise Exception('Error making get.')

        return data["DATA"]

    def find_domain_id(self, target_domain):
        domains = self.get({'api_action': 'domain.list'})

        domain_id = None
        for domain in domains:
            if domain['DOMAIN'] == target_domain:
                domain_id = domain['DOMAINID']
                break

        if not domain_id:
            raise Exception('Domain not found.')

        return domain_id

    def get_resources(self, domain, host):
        domain_id = self.find_domain_id(domain)

        params = {'api_action': 'domain.resource.list',
                  'DomainId': domain_id}

        resources = self.get(params)
        for resource in resources:
            if resource['NAME'] == host:
                yield LinodeResource(self, resource)


class LinodeResource(object):
    def __init__(self, api, data):
        self.id = data['RESOURCEID']
        self.api = api

        self._ip_address = ipaddress.ip_address(data['TARGET'])

    @property
    def ip(self):
        return self._ip_address.exploded

    @ip.setter
    def ip(self, value):
        # validate new IP
        new_ip = ipaddress.ip_address(value)
        if new_ip.version != self.version:
            raise Exception('Unable to set IP')

        if new_ip.exploded != self.ip:
            logging.info('New IP: {}'.format(new_ip.exploded))
            self.api.get({'api_action': 'domain.resource.update',
                          'ResourceID': self.id,
                          'Target': new_ip.exploded})

    @property
    def version(self):
        return self._ip_address.version


@functools.lru_cache()
def get_ip(version):
    url = IP_URLS[version]
    response = requests.get(url, timeout=TIMEOUT)
    response.raise_for_status()
    ip = ipaddress.ip_address(response.text.strip())
    if ip and ip.version == version:
        logging.info('Local IPv{}: {}'.format(version, ip))
        return ip
    else:
        logging.info('No local IPv{}.'.format(version))
        return None


def update_dns(key, domain, host):
    api = LinodeAPI(key)

    for resource in api.get_resources(domain, host):
        resource.ip = get_ip(resource.version)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--version', action='store_const',
                        const=True)
    args = parser.parse_args()

    if args.version:
        print(VERSION)
        exit()

    logging.basicConfig(level=logging.INFO)

    DOMAIN = os.environ['DOMAIN']
    HOST = os.environ['HOST']
    TOKEN = os.environ['TOKEN']

    update_dns(key=TOKEN, domain=DOMAIN, host=HOST)


if __name__ == "__main__":
    main()
