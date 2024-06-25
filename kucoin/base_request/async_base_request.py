import json
import hmac
import hashlib
import base64
import time
from uuid import uuid1
from urllib.parse import urljoin
import aiohttp


try:
    import pkg_resources

    version = 'v' + pkg_resources.get_distribution("kucoin-python").version
except (ModuleNotFoundError, pkg_resources.DistributionNotFound):
    version = 'v1.0.0'


class KucoinFuturesBaseRestApiAsync(object):
    def __init__(self, key='', secret='', passphrase='', url='', is_v1api=False):
        if url:
            self.url = url
        else:
            self.url = 'https://api.kucoin.com'
        self.key = key
        self.secret = secret
        self.passphrase = passphrase
        self.is_v1api = is_v1api
        # TODO: 该功能未实现
        self.TCP_NODELAY = 0

        self.session: aiohttp.ClientSession | None = None

        self.base_url = "https://api.kucoin.com"

    async def _request(self, method, endpoint, params=None):
        url = urljoin(self.base_url, endpoint)
        ts = str(int(time.time() * 1000))
        headers = self._create_headers(method, endpoint, ts, params)

        # data_json = ''
        # if method in ['GET', 'DELETE']:
        #     if params:
        #         strl = []
        #         for key in sorted(params):
        #             strl.append("{}={}".format(key, params[key]))
        #         data_json += '&'.join(strl)

        await self._create_session()
        if method in ['GET', 'DELETE']:
            async with self.session.request(method, url, headers=headers, params=params) as response:
                return await response.json()
        else:
            async with self.session.request(method, url, headers=headers, json=params) as response:
                return await response.json()

    async def _create_session(self):
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()

    async def close_session(self):
        if self.session:
            await self.session.close()
            self.session = None

    def _create_headers(self, method, endpoint, timestamp, params):
        # Create pre-sign string
        pre_sign_str = timestamp + method.upper() + endpoint
        if method in ['GET', 'DELETE'] and params:
            query_string = '&'.join([f"{key}={value}" for key, value in sorted(params.items())])
            pre_sign_str += f"?{query_string}"
        elif params:
            pre_sign_str += json.dumps(params)

        # Create signature
        signature = base64.b64encode(
            hmac.new(self.secret.encode('utf-8'), pre_sign_str.encode('utf-8'), hashlib.sha256).digest()).decode(
            'utf-8')

        # Create passphrase
        passphrase = base64.b64encode(hmac.new(self.secret.encode('utf-8'), self.passphrase.encode('utf-8'),
                                               hashlib.sha256).digest()).decode('utf-8')

        headers = {
            "KC-API-SIGN": signature,
            "KC-API-TIMESTAMP": timestamp,
            "KC-API-KEY": self.key,
            "KC-API-PASSPHRASE": passphrase,
            "KC-API-KEY-VERSION": "2",
            "Content-Type": "application/json",
            "User-Agent": "kucoin-python-sdk/" + version,
        }
        return headers

    @property
    def return_unique_id(self):
        return ''.join([each for each in str(uuid1()).split('-')])
