"""
Snowflake util to generate unique id

Reference: https://github.com/yitter/IdGenerator
"""

import threading
import time
from functools import lru_cache


class IdGeneratorOptions:
    """
    ID生成器配置
    - worker_id 全局唯一id, 区分不同uuid生成器实例
    - worker_id_bit_length 生成的uuid中worker_id占用的位数
    - seq_bit_length 生成的uuid中序列号占用的位数
    """

    def __init__(self, worker_id=0, worker_id_bit_length=6, seq_bit_length=6):

        # 雪花计算方法,（1-漂移算法|2-传统算法）, 默认1。目前只实现了1。
        self.method = 1

        # 基础时间（ms单位）, 不能超过当前系统时间
        self.base_time = 1704067688000

        # 机器码, 必须由外部设定, 最大值 2^worker_id_bit_length-1
        self.worker_id = worker_id

        # 机器码位长, 默认值6, 取值范围 [1, 15]（要求：序列数位长+机器码位长不超过22）
        self.worker_id_bit_length = worker_id_bit_length

        # 序列数位长, 默认值6, 取值范围 [3, 21]（要求：序列数位长+机器码位长不超过22）
        self.seq_bit_length = seq_bit_length

        # 最大序列数（含）, 设置范围 [max_seq_number, 2^seq_bit_length-1]
        # 默认值0, 表示最大序列数取最大值（2^seq_bit_length-1]）
        self.max_seq_number = 0

        # 最小序列数（含）, 默认值5, 取值范围 [5, max_seq_number], 每毫秒的前5个序列数对应编号0-4是保留位
        # 其中1-4是时间回拨相应预留位, 0是手工新值预留位
        self.min_seq_number = 5

        # 最大漂移次数（含）, 默认2000, 推荐范围500-10000（与计算能力有关）
        self.top_over_cost_count = 2000


class SnowFlake:
    """
    M1规则ID生成器配置
    """

    def __init__(self, options: IdGeneratorOptions):
        # 1.base_time
        self.base_time = 1582136402000
        if options.base_time != 0:
            self.base_time = int(options.base_time)

        # 2.worker_id_bit_length
        self.worker_id_bit_length = 6
        if options.worker_id_bit_length != 0:
            self.worker_id_bit_length = int(options.worker_id_bit_length)

        # 3.worker_id
        self.worker_id = options.worker_id

        # 4.seq_bit_length
        self.seq_bit_length = 6
        if options.seq_bit_length != 0:
            self.seq_bit_length = int(options.seq_bit_length)

        # 5.max_seq_number
        self.max_seq_number = int(options.max_seq_number)
        if options.max_seq_number <= 0:
            self.max_seq_number = (1 << self.seq_bit_length) - 1

        # 6.min_seq_number
        self.min_seq_number = int(options.min_seq_number)

        # 7.top_over_cost_count
        self.top_over_cost_count = int(options.top_over_cost_count)

        # 8.Others
        self.__timestamp_shift = self.worker_id_bit_length + self.seq_bit_length
        self.__current_seq_number = self.min_seq_number
        self.__last_time_tick: int = 0
        self.__turn_back_time_tick: int = 0
        self.__turn_back_index: int = 0
        self.__is_over_cost = False
        self.___over_cost_count_in_one_term: int = 0
        self.__id_lock = threading.Lock()

    def __next_over_cost_id(self) -> int:
        current_time_tick = self.__get_current_time_tick()
        if current_time_tick > self.__last_time_tick:
            self.__last_time_tick = current_time_tick
            self.__current_seq_number = self.min_seq_number
            self.__is_over_cost = False
            self.___over_cost_count_in_one_term = 0
            return self.__calc_id(self.__last_time_tick)

        if self.___over_cost_count_in_one_term >= self.top_over_cost_count:
            self.__last_time_tick = self.__get_next_time_tick()
            self.__current_seq_number = self.min_seq_number
            self.__is_over_cost = False
            self.___over_cost_count_in_one_term = 0
            return self.__calc_id(self.__last_time_tick)

        if self.__current_seq_number > self.max_seq_number:
            self.__last_time_tick += 1
            self.__current_seq_number = self.min_seq_number
            self.__is_over_cost = True
            self.___over_cost_count_in_one_term += 1
            return self.__calc_id(self.__last_time_tick)

        return self.__calc_id(self.__last_time_tick)

    def __next_normal_id(self) -> int:
        current_time_tick = self.__get_current_time_tick()
        if current_time_tick < self.__last_time_tick:
            if self.__turn_back_time_tick < 1:
                self.__turn_back_time_tick = self.__last_time_tick - 1
                self.__turn_back_index += 1
                # 每毫秒序列数的前5位是预留位, 0用于手工新值, 1-4是时间回拨次序
                # 支持4次回拨次序（避免回拨重叠导致ID重复）, 可无限次回拨（次序循环使用）。
                if self.__turn_back_index > 4:
                    self.__turn_back_index = 1

            return self.__calc_turn_back_id(self.__turn_back_time_tick)

        # 时间追平时, _TurnBackTimeTick清零
        self.__turn_back_time_tick = min(self.__turn_back_time_tick, 0)

        if current_time_tick > self.__last_time_tick:
            self.__last_time_tick = current_time_tick
            self.__current_seq_number = self.min_seq_number
            return self.__calc_id(self.__last_time_tick)

        if self.__current_seq_number > self.max_seq_number:
            self.__last_time_tick += 1
            self.__current_seq_number = self.min_seq_number
            self.__is_over_cost = True
            self.___over_cost_count_in_one_term = 1
            return self.__calc_id(self.__last_time_tick)

        return self.__calc_id(self.__last_time_tick)

    def __calc_id(self, use_time_tick) -> int:
        self.__current_seq_number += 1
        return (
            (use_time_tick << self.__timestamp_shift)
            + (self.worker_id << self.seq_bit_length)
            + self.__current_seq_number
        ) % int(1e64)

    def __calc_turn_back_id(self, use_time_tick) -> int:
        self.__turn_back_time_tick -= 1
        return (
            (use_time_tick << self.__timestamp_shift)
            + (self.worker_id << self.seq_bit_length)
            + self.__turn_back_index
        ) % int(1e64)

    def __get_current_time_tick(self) -> int:
        return int((time.time_ns() / 1e6) - self.base_time)

    def __get_next_time_tick(self) -> int:
        temp_time_ticker = self.__get_current_time_tick()
        while temp_time_ticker <= self.__last_time_tick:
            # 0.001 = 1 mili sec
            time.sleep(0.001)
            temp_time_ticker = self.__get_current_time_tick()
        return temp_time_ticker

    def next_id(self) -> int:
        with self.__id_lock:
            if self.__is_over_cost:
                nextid = self.__next_over_cost_id()
            else:
                nextid = self.__next_normal_id()
            return nextid


@lru_cache
def get_snowflake() -> SnowFlake:
    options = IdGeneratorOptions(worker_id=1)
    return SnowFlake(options)


def snowflake_id() -> int:
    idgen = get_snowflake()
    return idgen.next_id()
