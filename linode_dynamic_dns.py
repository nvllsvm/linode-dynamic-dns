#!/usr/bin/env python3
import argparse
import http.client
import ipaddress
import json
import logging
import os
import sys
import time
import urllib.request

__version__ = '0.6.2'

APP_NAME = 'linode-dynamic-dns'
LOGGER = logging.getLogger(APP_NAME)

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
        if 'json' in kwargs:
            data = json.dumps(kwargs['json']).encode()
            headers['Content-Type'] = 'application/json'
        else:
            data = None

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

    def update_domain_record_target(self, domain_id, record_id, target,
                                    ttl_sec):
        status, _ = self.request(
            'PUT',
            f'domains/{domain_id}/records/{record_id}',
            json={'target': str(target),
                  'ttl_sec': ttl_sec}
        )
        if status != 200:
            raise http.client.HTTPException(f'status {status}')

    def create_domain_record(self, domain_id, host, record_type, target, ttl_sec):
        status, _ = self.request(
            'POST',
            f'domains/{domain_id}/records',
            json={
                'name': host,
                'type': record_type,
                'target': str(target),
                'ttl_sec': ttl_sec,
            }
        )
        if status != 200:
            raise http.client.HTTPException(f'status {status}')

    def delete_domain_record(self, domain_id, record_id):
        status, _ = self.request(
            'DELETE',
            f'domains/{domain_id}/records/{record_id}',
        )
        if status != 200:
            raise http.client.HTTPException(f'status {status}')


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


def update_dns(api, domain, host, disable_ipv4, disable_ipv6, ttl,
               local_ipv4=None, local_ipv6=None):
    domain_id = None
    for d in api.get_domains():
        if d['domain'] == domain:
            domain_id = d['id']
            break

    if domain_id is None:
        print(f'Error: Domain "{domain}" not found')
        sys.exit(1)

    record_a = []
    record_aaaa = []

    # TODO: Delete invalid records and duplicates
    for record in api.get_domain_records(domain_id):
        if record['name'] == host:
            record_type = record['type']
            if record_type == 'A':
                record_a.append(record)
            elif record_type == 'AAAA':
                record_aaaa.append(record)
            else:
                continue

    if disable_ipv4:
        for record in record_a:
            _delete_record(api, domain_id, record)
    else:
        local_ip = local_ipv4 or get_ip(4)
        if record_a:
            _update_record(api, domain_id, local_ip, ttl, record_a[0])
            for record in record_a[1:]:
                _delete_record(api, domain_id, record)
        else:
            _create_record(api, domain_id, host, local_ip, ttl, 'A')

    if disable_ipv6:
        for record in record_aaaa:
            _delete_record(api, domain_id, record)
    else:
        local_ip = local_ipv6 or get_ip(6)
        if record_aaaa:
            _update_record(api, domain_id, local_ip, ttl, record_aaaa[0])
            for record in record_aaaa[1:]:
                _delete_record(api, domain_id, record)
        else:
            _create_record(api, domain_id, host, local_ip, ttl, 'AAAA')


def _create_record(api, domain_id, host, local_ip, ttl, record_type):
    log_suffix = (
        f'IPv{local_ip.version} '
        f'"{local_ip}" (TTL {ttl})')
    LOGGER.info(f'Creating {log_suffix}')
    api.create_domain_record(
        domain_id, host, record_type, local_ip, ttl_sec=ttl)
    LOGGER.info(f'Successful creation of {log_suffix}')


def _update_record(api, domain_id, local_ip, ttl, record):
    record_ip = ipaddress.ip_address(record['target'])
    record_ttl = record['ttl_sec']
    LOGGER.info(
        f'Remote IPv{record_ip.version} "{record_ip}" '
        f'(TTL {record_ttl})')

    should_update = False
    if local_ip and local_ip != record_ip:
        should_update = True
    if record_ttl != ttl:
        should_update = True

    if should_update:
        log_suffix = (
            f'IPv{local_ip.version} '
            f'"{record_ip}" (TTL {record_ttl}) '
            f'to "{local_ip}" (TTL {ttl})')
        LOGGER.info(f'Attempting update of {log_suffix}')
        api.update_domain_record_target(
            domain_id, record['id'], local_ip, ttl_sec=ttl)
        LOGGER.info(f'Successful update of {log_suffix}')


def _delete_record(api, domain_id, record):
    record_ip = ipaddress.ip_address(record['target'])
    LOGGER.info(f'Attempting deletion of IPv{record_ip.version}')
    api.delete_domain_record(domain_id, record['id'])
    LOGGER.info(f'Successful deletion of IPv{record_ip.version}')


_TRUE_VALUES = ('y', 'yes', 'true', '1')
_FALSE_VALUES = ('n', 'no', 'false', '0', '')


def strtobool(value):
    if value in _TRUE_VALUES:
        return True
    elif value in _FALSE_VALUES:
        return False
    else:
        raise ValueError(f'must be one of {_TRUE_VALUES + _FALSE_VALUES}')


# taken from https://www.linode.com/docs/api/domains/
_VALID_TTL = [
    300,
    3600,
    7200,
    14400,
    28800,
    57600,
    86400,
    172800,
    345600,
    604800,
    1209600,
    2419200,
]

_DEFAULT_TTL = 300


def _parse_ttl(value):
    if value:
        value = int(value)
        if value not in _VALID_TTL:
            raise ValueError(f'must be one of {_VALID_TTL}')
    else:
        value = _DEFAULT_TTL
    return value


def main():
    parser = argparse.ArgumentParser(APP_NAME)
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

    logging.basicConfig(format='%(message)s', level=logging.INFO)

    domain = os.environ['LINODE_DNS_DOMAIN']
    host = os.environ.get('LINODE_DNS_HOSTNAME', '')
    token = os.environ['LINODE_ACCESS_TOKEN']
    ttl = _parse_ttl(os.environ.get('LINODE_DNS_TTL'))
    disable_ipv4 = strtobool(os.environ.get('IPV4_DISABLE', ''))
    disable_ipv6 = strtobool(os.environ.get('IPV6_DISABLE', ''))
    local_ipv4 = os.environ.get('IPV4_ADDRESS')
    local_ipv6 = os.environ.get('IPV6_ADDRESS')
    if local_ipv4 is not None:
        local_ipv4 = ipaddress.ip_address(local_ipv4)
        if local_ipv4.version != 4:
            raise ValueError('invalid IPv4 address')
    if local_ipv6 is not None:
        local_ipv6 = ipaddress.ip_address(local_ipv6)
        if local_ipv6.version != 6:
            raise ValueError('invalid IPv6 address')

    api = LinodeAPI(token)

    while True:
        update_dns(
            api,
            domain,
            host,
            disable_ipv4=disable_ipv4,
            disable_ipv6=disable_ipv6,
            ttl=ttl,
            local_ipv4=local_ipv4,
            local_ipv6=local_ipv6,
        )
        if args.sleep is None:
            break
        time.sleep(args.sleep)


if __name__ == "__main__":
    main()
