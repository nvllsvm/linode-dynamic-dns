import argparse
import functools
import ipaddress
import logging
import os
import sys

import pkg_resources
import requests

VERSION = pkg_resources.get_distribution('linode_dynamic_dns').version

LOGGER = logging.getLogger(__name__)

TIMEOUT = 15

IP_URLS = {4: os.environ.get('IPV4_URL', 'https://ipv4.icanhazip.com'),
           6: os.environ.get('IPV6_URL', 'https://ipv6.icanhazip.com')}

LINODE_API_URL = 'https://api.linode.com/v4'


class LinodeAPI:
    def __init__(self, key):
        self.session = requests.Session()
        self.session.headers = {'Authorization': f'Bearer {key}'}

    def request(self, method, path, **kwargs):
        return self.session.request(
            method, f'{LINODE_API_URL}/{path}', **kwargs)

    def get_domains(self):
        response = self.request('GET', 'domains')
        # TODO: Support pagination
        yield from response.json()['data']

    def get_domain_records(self, domain_id):
        response = self.request('GET', f'domains/{domain_id}/records')
        yield from response.json()['data']

    def update_domain_record_target(self, domain_id, record_id, target):
        LOGGER.info(f'Updating IPv{target.version} record')
        response = self.request(
            'PUT',
            f'domains/{domain_id}/records/{record_id}',
            json={'target': str(target)}
        )
        if response.status_code != 200:
            raise requests.HTTPError('Unexpected response', response=response)


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

    domain = os.environ['DOMAIN']
    host = os.environ['HOST']
    token = os.environ['TOKEN']

    api = LinodeAPI(token)

    domain_id = None
    for d in api.get_domains():
        if d['domain'] == domain:
            domain_id = d['id']
            break

    if domain_id is None:
        print(f'Error: Domain "{domain}" not found')
        sys.exit(1)

    # TODO: Delete invalid records and duplicates
    for record in api.get_domain_records(domain_id):
        if record['name'] == host:
            local_ip = None
            record_type = record['type']
            if record_type == 'A':
                local_ip = get_ip(4)
            elif record_type == 'AAAA':
                local_ip = get_ip(6)

            record_ip = ipaddress.ip_address(record['target'])
            if local_ip and local_ip != record_ip:
                api.update_domain_record_target(
                    domain_id, record['id'], local_ip)


if __name__ == "__main__":
    main()
