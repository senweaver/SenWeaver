from fastapi import APIRouter, Request

from senweaver.utils.response import ResponseBase, success_response

from ..logic.dashboard_logic import DashboardLogic
from ..model import LoginLog, OperationLog, User
from ..system import module

router = APIRouter(
    tags=["面板统计"], prefix="/dashboard", route_class=module.route_class
)


@router.get("/user-total", summary="用户人数")
async def user_total(
    request: Request,
) -> ResponseBase:
    results, percent, total_count = await DashboardLogic.trend_info(request, User, 7)
    return success_response(results=results, percent=percent, count=total_count)


@router.get("/user-login-trend", summary="登录报表")
async def user_login_trend(
    request: Request,
) -> ResponseBase:
    results, _, _ = await DashboardLogic.trend_info(request, LoginLog)
    return success_response(data=results)


@router.get("/user-login-total", summary="用户登录")
async def user_login_total(
    request: Request,
) -> ResponseBase:
    results, percent, total_count = await DashboardLogic.trend_info(
        request, LoginLog, 7
    )
    return success_response(results=results, percent=percent, count=total_count)


@router.get("/today-operate-total", summary="最近操作日志")
async def today_operate_total(
    request: Request,
) -> ResponseBase:
    results, percent, total_count = await DashboardLogic.trend_info(
        request, OperationLog, 7
    )
    return success_response(results=results, percent=percent, count=total_count)


@router.get("/user-active")
async def user_active(
    request: Request,
) -> ResponseBase:
    results = await DashboardLogic.get_active_users(request, User)
    return success_response(results)


@router.get("/user-registered-trend")
async def user_registered_trend(
    request: Request,
) -> ResponseBase:
    results, percent, total_count = await DashboardLogic.trend_info(request, User)
    return success_response(data=results, percent=percent, count=total_count)
