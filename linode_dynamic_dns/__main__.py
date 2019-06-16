import argparse
import http.client
import ipaddress
import json
import logging
import os
import sys
import time
import urllib.request

__version__ = '0.6.0'

LOGGER = logging.getLogger(__name__)

TIMEOUT = 15

IP_URLS = {4: os.environ.get('IPV4_URL', 'https://ipv4.icanhazip.com'),
           6: os.environ.get('IPV6_URL', 'https://ipv6.icanhazip.com')}

LINODE_API_URL = 'https://api.linode.com/v4'


class LinodeAPI:
    def __init__(self, key):
        self._key = key

    def request(self, method, path, **kwargs):
        headers = {
            'Accept': 'application/json',
            'Authorization': f'Bearer {self._key}'
        }
        data = json.dumps(kwargs['json']) if 'json' in kwargs else None
        request = urllib.request.Request(
            url=f'{LINODE_API_URL}/{path}',
            headers=headers,
            method=method,
            data=data
        )
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            return response.status, json.loads(response.read())

    def get_domains(self):
        status, content = self.request('GET', 'domains')
        # TODO: Support pagination
        yield from content['data']

    def get_domain_records(self, domain_id):
        status, content = self.request('GET', f'domains/{domain_id}/records')
        yield from content['data']

    def update_domain_record_target(self, domain_id, record_id, target):
        response = self.request(
            'PUT',
            f'domains/{domain_id}/records/{record_id}',
            json={'target': str(target)}
        )
        if response.status != 200:
            raise http.client.HTTPException(f'status {response.status}')


def get_ip(version):
    url = IP_URLS[version]
    with urllib.request.urlopen(url, timeout=TIMEOUT) as response:
        if response.status >= 400:
            raise http.client.HTTPException(f'status {response.status}')
        content = response.read()
    ip = ipaddress.ip_address(content.decode().strip())
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
        version=__version__
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
