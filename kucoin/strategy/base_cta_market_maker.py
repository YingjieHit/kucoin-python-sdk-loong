import asyncio
from kucoin.strategy.base_market_maker import BaseMarketMaker
from kucoin.market.async_market import MarketDataAsync
from kucoin.ws_client import KucoinWsClient
from kucoin.strategy.enums import Subject
from kucoin.comm.utils import utils
from kucoin_futures.strategy.utils import utils as strategy_utils
from kucoin_futures.strategy.event import (
    EventType,
    TickerEvent, BarEvent,
    TraderOrderEvent, CreateMarketMakerOrderEvent,
    CreateOrderEvent,
    CancelAllOrderEvent, CancelOrderEvent,
    AccountBalanceEvent
)
from kucoin_futures.strategy.object import Bar
from kucoin.strategy.kline import Kline
from kucoin_futures.common.app_logger import app_logger


class BaseCtaMarketMaker(BaseMarketMaker):
    def __init__(self, symbol, key, secret, passphrase, kline_frequency, kline_size):
        """
        :param symbol: str
        :param key: str
        :param secret: str
        :param passphrase: str
        :param kline_frequency: str  1min, 3min, 15min, 30min, 1hour, 2hour, 4hour, 6hour, 8hour, 12hour, 1day, 1week
        """
        super().__init__(symbol, key, secret, passphrase)
        self.kline_frequency = kline_frequency
        self.kline_size = kline_size
        self.kline: Kline|None = None # = Kline(self.kline_size)
        self.updating_bar: Bar|None = None  # 正在更新的bar
        self.market_client = MarketDataAsync()

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

        # 订阅K线
        await self.ws_public_client.subscribe(f'/market/candles:{self.symbol}_{self.kline_frequency}')
        # 获取最新K线
        kline_source_list = await self.market_client.get_last_n_kline(
            self.symbol,
            self.kline_frequency,
            self.kline_size,
            end_at=utils.get_cur_timestamp() - utils.calc_second_by_freq(self.kline_frequency, 1)
        )
        kline_source_list = kline_source_list['data']
        # 转换为标准形式
        bars = strategy_utils.spot_candles_2_bars(self.symbol, kline_source_list)
        self.kline.updates(bars)
        self.enable = True
        while True:
            await asyncio.sleep(60 * 60 * 24)
        # await super().run()

    async def deal_public_msg(self, msg):
        data = msg.get('data')
        if msg.get('subject') == Subject.level2:
            ticker = strategy_utils.spot_level2_2_ticker(data)
            ticker.symbol = self.symbol  # TODO: 暂时这么写，不太严谨
            await self.event_queue.put(TickerEvent(ticker))

        elif msg.get('subject') in [Subject.tradeCandlesAdd, Subject.tradeCandlesUpdate]:
            bar = strategy_utils.spot_candle_2_bar(data)
            await self.event_queue.put(BarEvent(bar))

    async def process_event(self):
        """处理事件"""
        while True:
            try:
                event = await self.event_queue.get()
                if event.type == EventType.TICKER:
                    # 处理ticker
                    await self.on_tick(event.data)
                elif event.type == EventType.TRADE_ORDER:
                    # 处理order回报
                    await self.on_order(event.data)
                elif event.type == EventType.ACCOUNT_BALANCE:
                    # 处理账户余额更变
                    await self.on_account_balance(event.data)
                elif event.type == EventType.BAR:
                    # 处理K线
                    await self.on_bar(event.data)

            except Exception as e:
                await app_logger.error(f"process_event Error {str(e)}")

    async def on_bar(self, bar: Bar):
        raise NotImplementedError("需要实现on_bar")
