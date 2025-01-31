import json
import jwt
import hashlib
import os
import requests
import uuid
from urllib.parse import urlencode, unquote
from argparse import ArgumentParser


def get_order_possible_info(access_key, secret_key, server_url, market_codes):
    params = {'market': market_codes[0]}
    query_string = unquote(urlencode(params, doseq=True)).encode("utf-8")

    m = hashlib.sha512()
    m.update(query_string)
    query_hash = m.hexdigest()

    payload = {
        'access_key': access_key,
        'nonce': str(uuid.uuid4()),
        'query_hash': query_hash,
        'query_hash_alg': 'SHA512',
    }

    jwt_token = jwt.encode(payload, secret_key)
    authorization = 'Bearer {}'.format(jwt_token)
    headers = {'Authorization': authorization}

    res = requests.get(server_url + '/v1/orders/chance', params=params, headers=headers)
    return res.json()


def main(args):
    with open(os.path.join(args.config_path, 'upbit_access.txt'), 'r') as f:
        for line in f.readlines():
            access_key = line
            break
    with open(os.path.join(args.config_path, 'upbit_secret.txt'), 'r') as f:
        for line in f.readlines():
            secret_key = line
            break
    with open(os.path.join(args.config_path, 'upbit_server_url.txt'), 'r') as f:
        for line in f.readlines():
            server_url = line
            break

    with open(args.market_codes_path, 'r') as f:
        market_codes = json.load(f)

    order_possible_info = get_order_possible_info(access_key, secret_key, server_url, market_codes)
    min_order = float(order_possible_info['market']['bid']['min_total'])

    if args.order_type == 'bid':
        order_possible_bal = float(order_possible_info['bid_account']['balance'])
        params = {'market': market_codes[0],
                  'side': 'bid',
                  'ord_type': 'price',
                  'price': max(min_order, order_possible_bal*0.01),
                  }
    else:
        max_sell_bal = order_possible_info['ask_account']['balance']
        params = {'market': market_codes[0],
                  'side': 'ask',
                  'ord_type': 'market',
                  'volume': max_sell_bal,
                  }        
    query_string = unquote(urlencode(params, doseq=True)).encode("utf-8")

    m = hashlib.sha512()
    m.update(query_string)
    query_hash = m.hexdigest()

    payload = {
        'access_key': access_key,
        'nonce': str(uuid.uuid4()),
        'query_hash': query_hash,
        'query_hash_alg': 'SHA512',
    }

    jwt_token = jwt.encode(payload, secret_key)
    authorization = 'Bearer {}'.format(jwt_token)
    headers = {'Authorization': authorization}

    res = requests.post(server_url + '/v1/orders', json=params, headers=headers)
    print(res.json())


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('--order_type', type=str, default='bid', choices=['bid', 'ask'])
    parser.add_argument('--config_path', type=str, default='./config')
    parser.add_argument('--market_codes_path', type=str, default='./result/top_market_codes.json')
    args = parser.parse_args()
    main(args)