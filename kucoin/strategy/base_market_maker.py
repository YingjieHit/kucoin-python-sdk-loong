import asyncio

from kucoin.client import WsToken
from kucoin.ws_client import KucoinWsClient
from kucoin.trade.async_trade import TradeDataAsync

from kucoin_futures.strategy.event import (EventType, TickerEvent, Level2Depth50Event,
                                           TraderOrderEvent, CreateMarketMakerOrderEvent,
                                           CreateOrderEvent,
                                           CancelAllOrderEvent, CancelOrderEvent,
                                           AccountBalanceEvent)
from kucoin.strategy.enums import Subject
from kucoin_futures.strategy.utils import utils
from kucoin_futures.strategy.object import Ticker, Level2Depth50, Order, MarketMakerCreateOrder, CreateOrder, CancelOrder, \
    AccountBalance
from kucoin_futures.common.app_logger import app_logger


class BaseMarketMaker(object):
    def __init__(self, symbol, key, secret, passphrase):
        self.symbol = symbol
        self.event_queue = asyncio.Queue()  # 用于存储数据计算因子
        self.order_task_queue = asyncio.Queue()  # 用于下单任务通讯
        self.cancel_order_task_queue = asyncio.Queue()  # 用于撤单任务通讯
        self.client = WsToken(
            key=key,
            secret=secret,
            passphrase=passphrase,
            # url='https://api.kucoin.com',
            url='https://spot-rest-colo.kucoin.com',
        )
        self.trade = TradeDataAsync(key=key, secret=secret, passphrase=passphrase,url='spot-rest-colo.kucoin.com')
        self.ws_public_client = None
        self.ws_private_client = None
        self.enable = False

    async def run(self):
        # 创建事件处理任务
        process_event_task = asyncio.create_task(self.process_event())
        # 创建交易执行任务
        execute_order_task = asyncio.create_task(self.execute_order())
        # 创建撤单执行任务
        cancel_order_task = asyncio.create_task(self.process_cancel_order())

        # 创建ws_client
        self.ws_public_client = await KucoinWsClient.create(None, self.client, self.deal_public_msg,
                                                            private=False)
        self.ws_private_client = await KucoinWsClient.create(None, self.client, self.deal_private_msg,
                                                             private=True)

        # 订阅orderbook  TODO: 这里需要改成通过接口选择订阅何种数据。
        # await self.ws_public_client.subscribe(f'/market/ticker:{self.symbol}')
        await self.ws_public_client.subscribe(f"/spotMarket/level2Depth50:{self.symbol}")

        # 订阅private tradeOrders
        await self.ws_private_client.subscribe('/spotMarket/tradeOrders')
        # 订阅private /account/balance
        await self.ws_private_client.subscribe('/account/balance')

        self.enable = True

        while True:
            await asyncio.sleep(60 * 60 * 24)

    async def execute_order(self):
        while True:
            try:
                event = await self.order_task_queue.get()
                if event.type == EventType.CREATE_MARKET_MAKER_ORDER:
                    # 发送做市单
                    mmo: MarketMakerCreateOrder = event.data
                    order_list = [
                        {
                            "clientOid": mmo.client_oid_buy,
                            "side": "buy",
                            "type": "limit",
                            "price": mmo.price_buy,
                            "size": mmo.size,
                            "postOnly": mmo.post_only,
                        },
                        {
                            "clientOid": mmo.client_oid_sell,
                            "side": "sell",
                            "type": "limit",
                            "price": mmo.price_sell,
                            "size": mmo.size,
                            "postOnly": mmo.post_only,
                        }
                    ]
                    if mmo.cancel_after > 0:
                        order_list[0]['timeInForce'] = 'GTT'
                        order_list[0]['cancelAfter'] = mmo.cancel_after
                        order_list[1]['timeInForce'] = 'GTT'
                        order_list[1]['cancelAfter'] = mmo.cancel_after

                    await self.trade.create_bulk_orders(mmo.symbol, orderList=order_list)
                    # TODO: 这里需要改成高频账号下单

                    # await app_logger.info_logger(f"订单执行结果{res}")
                elif event.type == EventType.CREATE_ORDER:
                    # 发送订单
                    co: CreateOrder = event.data
                    if co.type == 'limit':
                        params = {
                            'postOnly': co.post_only,
                        }
                        if co.cancel_after > 0:
                            params['timeInForce'] = 'GTT'
                            params['cancelAfter'] = co.cancel_after
                        await self.trade.create_limit_order(co.symbol, co.side, co.size, co.price, co.client_oid, **params)
                        # TODO: 这里需要改成高频账号下单

                    elif co.type == 'market':
                        params = {}
                        if co.cancel_after > 0:
                            params['timeInForce'] = 'GTT'
                            params['cancelAfter'] = co.cancel_after
                        await self.trade.create_market_order(co.symbol, co.side, co.client_oid, size=co.size, **params)
                        # TODO: 这里需要改成高频账号下单

            except Exception as e:
                await app_logger.error(f"execute_order_process Error {str(e)}")

    async def process_cancel_order(self):
        while True:
            try:
                event = await self.cancel_order_task_queue.get()

                if event.type == EventType.CANCEL_ALL_ORDER:
                    # 撤销所有订单
                    symbol = event.data
                    # TODO: 这里需要注意，目前只取消现货order，严谨的需考虑全仓杠杆交易和逐仓杠杆交易
                    await self.trade.cancel_all_orders(symbol=symbol, tradeType="TRADE")
                    # TODO: 这里需要改成高频账号撤单

                elif event.type == EventType.CANCEL_ORDER:
                    # 撤单
                    co: CancelOrder = event.data
                    if co.client_oid:
                        # res = await self.trade.cancel_order_by_clientOid(co.client_oid, co.symbol)
                        await self.trade.cancel_client_order(co.client_oid)
                        # TODO: 这里需要改成高频账号撤单
                    else:
                        await self.trade.cancel_order(co.order_id)
                        # TODO: 这里需要改成高频账号撤单

            except Exception as e:
                await app_logger.error(f"process_cancel_order Error {str(e)}")

    async def on_tick(self, ticker: Ticker):
        raise NotImplementedError("需要实现on_tick")

    async def on_level2_depth50(self, level2_depth50: Level2Depth50):
        raise NotImplementedError("需要实现on_level2_depth50")

    async def on_order(self, order: Order):
        raise NotImplementedError("需要实现on_order")

    async def on_account_balance(self, account_balance: AccountBalance):
        raise NotImplementedError("需要实现on_account_balance")

    async def process_event(self):
        """处理事件"""
        while True:
            try:
                event = await self.event_queue.get()
                if event.type == EventType.TICKER:
                    # 处理ticker
                    await self.on_tick(event.data)
                if event.type == EventType.LEVEL2DEPTH50:
                    # 处理level2depth50深度盘口数据
                    await self.on_level2_depth50(event.data)
                elif event.type == EventType.TRADE_ORDER:
                    # 处理order回报
                    await self.on_order(event.data)
                elif event.type == EventType.ACCOUNT_BALANCE:
                    # 处理账户余额更变
                    await self.on_account_balance(event.data)

            except Exception as e:
                await app_logger.error(f"process_event Error {str(e)}")

    async def deal_public_msg(self, msg):
        # data = msg.get('data')
        if msg.get('subject') == Subject.level2:
            # "topic": "/spotMarket/level2Depth50:BTC-USDT"
            # TODO: 未来多合约考虑推送多品种的level2数据
            if msg.get('topic') == f'/spotMarket/level2Depth50:{self.symbol}':
                level2_depth50 = utils.spot_msg_2_level2_depth50(msg)
                await self.event_queue.put(Level2Depth50Event(level2_depth50))

            # ticker暂时弃用，直接用level2，on_ticker方法将会收不到数据
            # ticker = utils.spot_level2_2_ticker(data)
            # ticker.symbol = self.symbol  # TODO: 暂时这么写，不太严谨
            # await self.event_queue.put(TickerEvent(ticker))

    async def deal_private_msg(self, msg):
        data = msg.get('data')
        if msg.get('subject') == Subject.orderChange and data.get('symbol') == self.symbol:
            order = utils.spot_dict_2_order(data)
            await self.event_queue.put(TraderOrderEvent(order))
        elif msg.get('subject') == Subject.accountBalance:
            account_balance = utils.spot_dict_2_account_balance(data)
            await self.event_queue.put(AccountBalanceEvent(account_balance))

    async def create_market_maker_order(
            self, symbol, size, price_buy, price_sell,
            client_oid_buy='', client_oid_sell='',
            post_only=True,
            cancel_after=-1,
            lever=1,
    ):
        mm_order = MarketMakerCreateOrder(
            symbol=symbol,
            lever=lever,
            size=size,
            price_buy=price_buy,
            price_sell=price_sell,
            client_oid_buy=client_oid_buy,
            client_oid_sell=client_oid_sell,
            post_only=post_only,
            cancel_after=cancel_after,
        )
        await self.order_task_queue.put(CreateMarketMakerOrderEvent(mm_order))

    async def create_order(self, symbol, side, size, type, price, client_oid='', post_only=True, cancel_after=-1, lever=1):
        co = CreateOrder(
            symbol=symbol,
            lever=lever,
            size=size,
            side=side,
            price=price,
            type=type,
            client_oid=client_oid,
            post_only=post_only,
            cancel_after=cancel_after,
        )
        await self.order_task_queue.put(CreateOrderEvent(co))

    async def cancel_all_order(self, symbol: str = None):
        if not symbol:
            symbol = self.symbol
        await self.cancel_order_task_queue.put(CancelAllOrderEvent(symbol))

    async def cancel_order_by_order_id(self, order_id: str):
        # await self.cancel_order_task_queue.put(CancelOrder(order_id=order_id))
        data = CancelOrder(order_id=order_id)
        await self.cancel_order_task_queue.put(CancelOrderEvent(data))

    async def cancel_order_by_client_oid(self, symbol, client_oid):
        # await self.cancel_order_task_queue.put(CancelOrder(symbol=symbol, client_oid=client_oid))
        data = CancelOrder(symbol=symbol, client_oid=client_oid)
        await self.cancel_order_task_queue.put(CancelOrderEvent(data))
