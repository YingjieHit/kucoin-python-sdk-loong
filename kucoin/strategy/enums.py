class Subject:
    """订阅到的主题"""
    tradeTicker = 'trade.ticker'
    level2 = 'level2'  # l2数据
    tradeL3Match = 'trade.l3match'  # 市场成交数据
    orderChange = 'orderChange'  # 私有订单变化
    accountBalance = 'account.balance'  # 账户余额变化
    tradeCandlesUpdate = 'trade.candles.update'  # K线更新
    tradeCandlesAdd = 'trade.candles.add'  # K线新增