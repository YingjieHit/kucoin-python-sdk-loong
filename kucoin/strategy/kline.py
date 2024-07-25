import numpy as np


class Kline:
    def __init__(self, max_size: int):
        self.max_size = max_size
        self.ts = np.zeros(self.max_size, dtype=np.int64)
        self.open = np.zeros(self.max_size, dtype=np.float64)
        self.high = np.zeros(self.max_size, dtype=np.float64)
        self.low = np.zeros(self.max_size, dtype=np.float64)
        self.close = np.zeros(self.max_size, dtype=np.float64)
        self.volume = np.zeros(self.max_size, dtype=np.float64)
        self.turnover = np.zeros(self.max_size, dtype=np.float64)
        # 记录更新的bar数
        self.size = 0

    def update(self, bar):
        # 所有数据左移一位
        self.ts[:-1] = self.ts[1:]
        self.open[:-1] = self.open[1:]
        self.high[:-1] = self.high[1:]
        self.low[:-1] = self.low[1:]
        self.close[:-1] = self.close[1:]
        self.volume[:-1] = self.volume[1:]
        self.turnover[:-1] = self.turnover[1:]

        # 更新最新数据
        self.ts[-1] = bar.ts
        self.open[-1] = bar.open
        self.high[-1] = bar.high
        self.low[-1] = bar.low
        self.close[-1] = bar.close
        self.volume[-1] = bar.volume
        self.turnover[-1] = bar.turnover

        if self.size < self.max_size:
            self.size += 1

    def updates(self, bars):
        for bar in bars:
            self.update(bar)


