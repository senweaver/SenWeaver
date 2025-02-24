from datetime import datetime, timedelta

from fastapi import Request
from sqlalchemy import desc, func
from sqlalchemy.future import select

from senweaver.db.types import ModelType


class DashboardLogic:
    @classmethod
    async def trend_info(cls, request: Request, model: type[ModelType], limit_day=30):
        db = request.auth.db.session
        # 获取今天的开始时间
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        limit_time = today - timedelta(days=limit_day)

        # 构造SQLAlchemy查询以获取过去 limit_day 天内每天的数据量
        query = (
            select(
                func.date(model.created_time).label("created_time_day"),
                func.count(model.id).label("count"),
            )
            .filter(model.created_time >= limit_time)
            .group_by("created_time_day")
            .order_by(desc("created_time_day"))
        )

        result = await db.execute(query)
        data_count = result.all()

        # 将数据转换为字典形式，方便后续查找
        dict_count = {d.created_time_day.strftime("%m-%d"): d.count for d in data_count}

        # 创建结果列表
        results = []
        for i in range(limit_day, -1, -1):
            date = (today - timedelta(days=i)).strftime("%m-%d")
            results.append({"day": date, "count": dict_count.get(date, 0)})

        percent_change = 0
        # 确保有两天的数据且前一天的数据不为零
        if len(results) > 1 and results[-2]["count"] != 0:
            current_day_count = results[-1]["count"]
            previous_day_count = results[-2]["count"]
            percent_change = round(
                100 * (current_day_count - previous_day_count) / previous_day_count
            )

        # 计算总记录数
        total_count_query = select(func.count(model.id))
        total_result = await db.execute(total_count_query)
        total_count = total_result.scalar_one()

        return results, percent_change, total_count

    @classmethod
    async def get_active_users(cls, request: Request, model: type[ModelType]):
        db = request.auth.db.session
        # 获取当前时间，并设置为当天的开始时间
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        active_date_list = [1, 3, 7, 30]
        results = []

        for date in active_date_list:
            x_day = today - timedelta(days=date)

            # 计算过去 date 天内注册的用户数量
            register_user_query = (
                select(func.count())
                .select_from(model)
                .where(model.created_time >= x_day)
            )

            # 计算过去 date 天内活跃（登录）的用户数量
            active_user_query = (
                select(func.count(func.distinct(model.id)))
                .select_from(model)
                .where(model.last_login >= x_day)
            )
            register_count_result = await db.execute(register_user_query)
            active_count_result = await db.execute(active_user_query)

            x_day_register_user = register_count_result.scalar_one()
            x_day_active_user = active_count_result.scalar_one()

            results.append([date, x_day_register_user, x_day_active_user])

        return results


dashboard_logic = DashboardLogic()
