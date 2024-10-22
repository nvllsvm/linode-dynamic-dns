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

__version__ = '0.7.0'

APP_NAME = 'linode-dynamic-dns'
LOGGER = logging.getLogger(APP_NAME)

DEFAULT_IPV4_URL = 'https://ipv4.icanhazip.com'
DEFAULT_IPV6_URL = 'https://ipv6.icanhazip.com'


class LinodeAPI:
    # taken from https://www.linode.com/docs/api/domains/
    VALID_DNS_TTL = [
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

    URL = 'https://api.linode.com'
    TIMEOUT = 15

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
            url=f'{self.URL}/{path}',
            headers=headers,
            method=method,
            data=data
        )
        with urllib.request.urlopen(request, timeout=self.TIMEOUT) as response:
            return response.status, json.loads(response.read())

    def get_domains(self):
        status, content = self.request('GET', 'v4/domains')
        # TODO: Support pagination
        yield from content['data']

    def get_domain_records(self, domain_id):
        status, content = self.request('GET', f'v4/domains/{domain_id}/records')
        yield from content['data']

    def update_domain_record_target(self, domain_id, record_id, target,
                                    ttl_sec):
        status, _ = self.request(
            'PUT',
            f'v4/domains/{domain_id}/records/{record_id}',
            json={'target': str(target),
                  'ttl_sec': ttl_sec}
        )
        if status != 200:
            raise http.client.HTTPException(f'status {status}')

    def create_domain_record(self, domain_id, host, record_type, target, ttl_sec):
        status, _ = self.request(
            'POST',
            f'v4/domains/{domain_id}/records',
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
            f'v4/domains/{domain_id}/records/{record_id}',
        )
        if status != 200:
            raise http.client.HTTPException(f'status {status}')


class IPLookup:
    TIMEOUT = 15

    def __init__(self, ipv4_url, ipv6_url):
        self.ipv4_url = ipv4_url
        self.ipv6_url = ipv6_url

    def _request(self, url, version):
        with urllib.request.urlopen(url, timeout=self.TIMEOUT) as response:
            if response.status >= 400:
                raise http.client.HTTPException(f'status {response.status}')
            content = response.read()
        ip = ipaddress.ip_address(content.decode().strip())
        if ip and ip.version == version:
            LOGGER.info(f'Local IPv{version} "{ip}"')
            return ip
        else:
            raise RuntimeError(f'No local IPv{version}')

    def get_ipv4(self):
        return self._request(self.ipv4_url, version=4)

    def get_ipv6(self):
        return self._request(self.ipv6_url, version=6)


def update_dns(api, domain, host, disable_ipv4, disable_ipv6, ttl, iplookup,
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
        local_ip = local_ipv4 or iplookup.get_ipv4()
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
        local_ip = local_ipv6 or iplookup.get_ipv6()
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


_DEFAULT_TTL = 300


def _parse_ttl(value):
    value = int(value)
    if value not in LinodeAPI.VALID_DNS_TTL:
        raise ValueError(f'must be one of {LinodeAPI.VALID_DNS_TTL}')
    return value


def main():
    parser = argparse.ArgumentParser(APP_NAME)
    parser.add_argument(
        '--access-token',
        default=os.environ.get('LINODE_ACCESS_TOKEN'),
        help='(env: LINODE_ACCESS_TOKEN)')
    parser.add_argument(
        '--update-interval',
        metavar='SECONDS',
        default=os.environ.get('UPDATE_INTERVAL'),
        help=('Run continuously and update the DNS record every n-seconds '
              '(env: UPDATE_INTERVAL)'),
    )
    parser.add_argument(
        '--version',
        action='version',
        version=__version__
    )

    linode_group = parser.add_argument_group('DNS options')
    linode_group.add_argument(
        '--dns-domain',
        default=os.environ.get('LINODE_DNS_DOMAIN'),
        help='(env: LINODE_DNS_DOMAIN)')
    linode_group.add_argument(
        '--dns-hostname',
        default=os.environ.get('LINODE_DNS_HOSTNAME') or '',
        help='(env: LINODE_DNS_HOSTNAME)')
    linode_group.add_argument(
        '--dns-ttl',
        default=os.environ.get('LINODE_DNS_TTL') or _DEFAULT_TTL,
        help=f'(env: LINODE_DNS_TTL) (default: {_DEFAULT_TTL})')

    ipv4_group = parser.add_argument_group('IPv4 options')
    ipv4_group.add_argument(
        '--ipv4-url',
        default=os.environ.get('IPV4_URL') or DEFAULT_IPV4_URL,
        help=f'(env: IPV4_URL) (default: {DEFAULT_IPV4_URL})')
    ipv4_group.add_argument(
        '--ipv4-disable',
        action='store_const',
        const='true',
        default=os.environ.get('IPV4_DISABLE', ''),
        help='(env: IPV4_DISABLE)')
    ipv4_group.add_argument(
        '--ipv4-address',
        default=os.environ.get('IPV4_ADDRESS'),
        help='(env: IPV4_ADDRESS)')

    ipv6_group = parser.add_argument_group('IPv6 options')
    ipv6_group.add_argument(
        '--ipv6-url',
        default=os.environ.get('IPV6_URL') or DEFAULT_IPV6_URL,
        help=f'(env: IPV6_URL) (default: {DEFAULT_IPV6_URL})')
    ipv6_group.add_argument(
        '--ipv6-disable',
        action='store_const',
        const='true',
        default=os.environ.get('IPV6_DISABLE', ''),
        help='(env: IPV6_DISABLE)')
    ipv6_group.add_argument(
        '--ipv6-address',
        default=os.environ.get('IPV6_ADDRESS'),
        help='(env: IPV6_ADDRESS)')

    args = parser.parse_args()

    logging.basicConfig(format='%(message)s', level=logging.INFO)

    if not args.dns_domain:
        parser.error('must specify DNS domain')

    if not args.access_token:
        parser.error('must specify access token')

    ttl = _parse_ttl(args.dns_ttl)

    disable_ipv4 = strtobool(args.ipv4_disable)
    disable_ipv6 = strtobool(args.ipv6_disable)

    local_ipv4 = args.ipv4_address
    local_ipv6 = args.ipv6_address

    if local_ipv4 is not None:
        local_ipv4 = ipaddress.ip_address(local_ipv4)
        if local_ipv4.version != 4:
            parser.error('invalid IPv4 address')
    if local_ipv6 is not None:
        local_ipv6 = ipaddress.ip_address(local_ipv6)
        if local_ipv6.version != 6:
            parser.error('invalid IPv6 address')

    api = LinodeAPI(args.access_token)
    iplookup = IPLookup(ipv4_url=args.ipv4_url, ipv6_url=args.ipv6_url)

    update_interval = args.update_interval
    if update_interval is not None:
        update_interval = int(update_interval)
    while True:
        update_dns(
            api,
            args.dns_domain,
            args.dns_hostname,
            disable_ipv4=disable_ipv4,
            disable_ipv6=disable_ipv6,
            ttl=ttl,
            iplookup=iplookup,
            local_ipv4=local_ipv4,
            local_ipv6=local_ipv6,
        )
        if update_interval is None:
            break
        time.sleep(update_interval)


if __name__ == "__main__":
    main()
