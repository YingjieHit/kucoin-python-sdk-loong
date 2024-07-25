from kucoin.client import Market
from datetime import datetime, timedelta
from pytz import timezone

def main():
    symbol = "BTC-USDT"
    frequency = "5min"

    market = Market()
    data = market.get_kline(
        symbol=symbol,
        kline_type=frequency,
        startAt=int((datetime.now() - timedelta(minutes=20)).timestamp()),
        endAt=int(datetime.now().timestamp()) // 5 * 5 - 5,
    )
    for k in data:
        # 开始时间、开 收 高 低 成交量 成交额
        ts = int(k[0])
        tz_beijing = timezone('Asia/Shanghai')
        dt = datetime.fromtimestamp(ts, tz=tz_beijing)
        open = float(k[1])
        close = float(k[2])
        high = float(k[3])
        low = float(k[4])
        volume = float(k[5])
        amount = float(k[6])
        print(f"dt={dt},open={open},close={close},high={high},low={low},volume={volume},amount={amount}")

    print(data)
    print(len(data))

if __name__ == '__main__':
    main()
