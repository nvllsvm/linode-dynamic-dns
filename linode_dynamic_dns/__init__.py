import argparse
import ipaddress
import logging
import os
import pkg_resources

import requests

TIMEOUT = 15
VERSION = pkg_resources.get_distribution('linode_dynamic_dns').version


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


class LocalIP(object):
    def __init__(self, ipv4_url, ipv6_url):
        self.ipv4_url = ipv4_url
        self.ipv6_url = ipv6_url
        self._retrieved_ipv4 = False
        self._retrieved_ipv6 = False
        self._ipv4 = None
        self._ipv6 = None

    def __retrieve_ip(self, url):
        try:
            response = requests.get(url, timeout=TIMEOUT)
            response.raise_for_status()
            return ipaddress.ip_address(response.text.strip())
        except:
            return None

    @property
    def ipv4(self):
        if not self._retrieved_ipv4:
            self._retrieved_ipv4 = True
            ip = self.__retrieve_ip(self.ipv4_url)
            if ip and ip.version == 4:
                self._ipv4 = ip.exploded
                logging.info('Local IPv4: {}'.format(self._ipv4))
            else:
                self._ipv4 = None
                logging.info('No local IPv4.')
        return self._ipv4

    @property
    def ipv6(self):
        if not self._retrieved_ipv6:
            self._retrieved_ipv6 = True
            ip = self.__retrieve_ip(self.ipv6_url)
            if ip and ip.version == 6:
                self._ipv6 = ip.exploded
                logging.info('Local IPv6: {}'.format(self._ipv6))
            else:
                self._ipv6 = None
                logging.info('No local IPv6.')
        return self._ipv6


def update_dns(key, domain, host, ipv4_url, ipv6_url):
    api = LinodeAPI(key)
    local_ip = LocalIP(ipv4_url, ipv6_url)

    for resource in api.get_resources(domain, host):
        if resource.version == 4:
            resource.ip = local_ip.ipv4
        elif resource.version == 6:
            resource.ip = local_ip.ipv6


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--version', action='store_const',
                        const=True)
    args = parser.parse_args()

    if args.version:
        print(VERSION)
        exit()

    logging.basicConfig(level=logging.INFO)

    IPV4_URL = os.environ.get(
        'IPV4_URL', 'https://ipv4.icanhazip.com')
    IPV6_URL = os.environ.get(
        'IPV6_URL', 'https://ipv6.icanhazip.com')

    DOMAIN = os.environ['DOMAIN']
    HOST = os.environ['HOST']
    TOKEN = os.environ['TOKEN']

    update_dns(key=TOKEN, domain=DOMAIN, host=HOST,
               ipv4_url=IPV4_URL, ipv6_url=IPV6_URL)


if __name__ == "__main__":
    main()