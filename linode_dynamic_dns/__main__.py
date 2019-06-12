import argparse
import ipaddress
import logging
import os
import sys
import time

import pkg_resources
import requests

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
        response = self.request(
            'PUT',
            f'domains/{domain_id}/records/{record_id}',
            json={'target': str(target)}
        )
        if response.status_code != 200:
            raise requests.HTTPError('Unexpected response', response=response)


def get_ip(version):
    url = IP_URLS[version]
    response = requests.get(url, timeout=TIMEOUT)
    response.raise_for_status()
    ip = ipaddress.ip_address(response.text.strip())
    if ip and ip.version == version:
        LOGGER.info(f'Local IPv{version} "{ip}"')
        return ip
    else:
        LOGGER.info(f'No local IPv{version}.')
        return None


def update_dns(api, domain, host):
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
            LOGGER.info(f'Remote IPv{record_ip.version} "{record_ip}"')
            if local_ip and local_ip != record_ip:
                log_suffix = (f'IPv{local_ip.version} '
                              f'"{record_ip}" to "{local_ip}"')
                LOGGER.info(f'Attempting update of {log_suffix}')
                api.update_domain_record_target(
                    domain_id, record['id'], local_ip)
                LOGGER.info(f'Successful update of {log_suffix}')


def main():
    parser = argparse.ArgumentParser('linode-dynamic-dns')
    parser.add_argument(
        '--version',
        action='version',
        version=pkg_resources.get_distribution('linode_dynamic_dns').version
    )
    parser.add_argument(
        '-s',
        type=int,
        dest='sleep',
        default=None,
        help='Run continuously and sleep the specified number of seconds'
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    domain = os.environ['DOMAIN']
    host = os.environ['HOST']
    token = os.environ['TOKEN']

    api = LinodeAPI(token)

    if args.sleep is not None:
        while True:
            update_dns(api, domain, host)
            time.sleep(args.sleep)
    else:
        update_dns(api, domain, host)


if __name__ == "__main__":
    main()
