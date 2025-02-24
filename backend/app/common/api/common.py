import re
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, Path, Request, status
from fastapi.requests import Request
from fastapi.responses import StreamingResponse

from app.common.core.schemas import IResourceCache
from app.system.model.attachment import Attachment
from config.settings import settings
from senweaver import senweaver_router
from senweaver.core.senweaver_crud import SenweaverCRUD
from senweaver.exception.http_exception import ForbiddenException, NotFoundException
from senweaver.utils.response import ResponseBase, error_response, success_response

from ..common import module

router = APIRouter(tags=["common"], route_class=module.route_class)
open_router = APIRouter(tags=["common"], route_class=module.route_class)


@open_router.get("/download/{path:path}", summary="下载文件")
async def download(request: Request, path: Optional[str]):
    # 正则表达式允许合法路径，包括中文，但禁止包含 ".."、"/./"、"//" 等不安全符号
    if (
        not path
        or not re.match(r"^[\w\-\u4e00-\u9fff\/]+(\.[a-zA-Z0-9]+)?$", path)
        or "/./" in path
        or "//" in path
        or path.startswith("/")
    ):
        raise ForbiddenException("Invalid path format")
    file_path = settings.UPLOAD_PATH / path
    # 检查路径是否超出根目录范围
    # 确保 file_path 是 base_directory 的子目录，防止路径遍历攻击
    file_path.resolve().relative_to(settings.UPLOAD_PATH.resolve())
    # 检查文件是否存在
    if not file_path.exists() or not file_path.is_file():
        raise NotFoundException("File not found")
    file_data: Attachment = await SenweaverCRUD(Attachment).get(
        request.auth.db.session,
        schema_to_select=Attachment,
        return_as_model=True,
        filepath=path,
    )
    if not file_data:
        raise NotFoundException("File not found")
    try:

        def file_stream():
            with open(file_path, "rb") as resp_file:
                yield from resp_file

        # 检查文件 MIME 类型是否是图片
        if file_data.mime_type.startswith("image/"):
            # 对于图片类型，将 Content-Disposition 设置为 inline
            content_disposition = f"inline; filename={file_data.filename}"
        else:
            # 其他类型则作为附件下载
            content_disposition = f"attachment; filename={file_data.filename}"
        return StreamingResponse(
            file_stream(),
            status_code=status.HTTP_200_OK,
            media_type=f"{file_data.mime_type}",
            headers={"Content-Disposition": f"{content_disposition}"},
        )
    except Exception as e:
        return error_response(str(e))


@router.get("/api/health", summary="获取服务健康状态")
async def get_health(request: Request):
    data = {
        "status": False,
        "db_status": False,
        "redis_status": True,
        "time": 1730255402,
        "db_time": 0.35871315002441406,
        "redis_time": 0.0009968280792236328,
    }
    return data


@router.get("/countries", summary="获取城市手机号列表")
async def get_health(request: Request) -> ResponseBase:
    data = [
        {"name": "不丹", "phone_code": "+975", "flag": "🇧🇹", "code": "BT"},
        {"name": "东帝汶", "phone_code": "+670", "flag": "🇹🇱", "code": "TL"},
        {"name": "中国", "phone_code": "+86", "flag": "🇨🇳", "code": "CN"},
        {"name": "中非", "phone_code": "+236", "flag": "🇨🇫", "code": "CF"},
        {"name": "丹麦", "phone_code": "+45", "flag": "🇩🇰", "code": "DK"},
        {"name": "乌克兰", "phone_code": "+380", "flag": "🇺🇦", "code": "UA"},
        {"name": "乌兹别克斯坦", "phone_code": "+998", "flag": "🇺🇿", "code": "UZ"},
        {"name": "乌干达", "phone_code": "+256", "flag": "🇺🇬", "code": "UG"},
        {"name": "乌拉圭", "phone_code": "+598", "flag": "🇺🇾", "code": "UY"},
        {"name": "乍得", "phone_code": "+235", "flag": "🇹🇩", "code": "TD"},
        {"name": "也门", "phone_code": "+967", "flag": "🇾🇪", "code": "YE"},
        {"name": "亚美尼亚", "phone_code": "+374", "flag": "🇦🇲", "code": "AM"},
        {"name": "以色列", "phone_code": "+972", "flag": "🇮🇱", "code": "IL"},
        {"name": "伊拉克", "phone_code": "+964", "flag": "🇮🇶", "code": "IQ"},
        {"name": "伊朗伊斯兰共和国", "phone_code": "+98", "flag": "🇮🇷", "code": "IR"},
        {"name": "伯利兹", "phone_code": "+501", "flag": "🇧🇿", "code": "BZ"},
        {"name": "佛得角", "phone_code": "+238", "flag": "🇨🇻", "code": "CV"},
        {"name": "俄罗斯", "phone_code": "+7", "flag": "🇷🇺", "code": "RU"},
        {"name": "保加利亚", "phone_code": "+359", "flag": "🇧🇬", "code": "BG"},
        {"name": "克罗地亚", "phone_code": "+385", "flag": "🇭🇷", "code": "HR"},
        {"name": "关岛", "phone_code": "+1", "flag": "🇬🇺", "code": "GU"},
        {"name": "冈比亚", "phone_code": "+220", "flag": "🇬🇲", "code": "GM"},
        {"name": "冰岛", "phone_code": "+354", "flag": "🇮🇸", "code": "IS"},
        {"name": "几内亚", "phone_code": "+224", "flag": "🇬🇳", "code": "GN"},
        {"name": "几内亚比绍", "phone_code": "+245", "flag": "🇬🇼", "code": "GW"},
        {"name": "列支敦士登", "phone_code": "+423", "flag": "🇱🇮", "code": "LI"},
        {"name": "刚果", "phone_code": "+242", "flag": "🇨🇬", "code": "CG"},
        {"name": "刚果民主共和国", "phone_code": "+243", "flag": "🇨🇩", "code": "CD"},
        {"name": "利比亚", "phone_code": "+218", "flag": "🇱🇾", "code": "LY"},
        {"name": "利比里亚", "phone_code": "+231", "flag": "🇱🇷", "code": "LR"},
        {"name": "加拿大", "phone_code": "+1", "flag": "🇨🇦", "code": "CA"},
        {"name": "加纳", "phone_code": "+233", "flag": "🇬🇭", "code": "GH"},
        {"name": "加蓬", "phone_code": "+241", "flag": "🇬🇦", "code": "GA"},
        {"name": "匈牙利", "phone_code": "+36", "flag": "🇭🇺", "code": "HU"},
        {"name": "北马其顿", "phone_code": "+389", "flag": "🇲🇰", "code": "MK"},
        {"name": "北马里亚纳群岛", "phone_code": "+1", "flag": "🇲🇵", "code": "MP"},
        {"name": "南苏丹", "phone_code": "+211", "flag": "🇸🇸", "code": "SS"},
        {"name": "南非", "phone_code": "+27", "flag": "🇿🇦", "code": "ZA"},
        {"name": "博兹瓦那", "phone_code": "+267", "flag": "🇧🇼", "code": "BW"},
        {
            "name": "博奈尔、圣尤斯特歇斯岛和萨巴",
            "phone_code": "+599",
            "flag": "🇧🇶",
            "code": "BQ",
        },
        {"name": "卡塔尔", "phone_code": "+974", "flag": "🇶🇦", "code": "QA"},
        {"name": "卢旺达", "phone_code": "+250", "flag": "🇷🇼", "code": "RW"},
        {"name": "卢森堡", "phone_code": "+352", "flag": "🇱🇺", "code": "LU"},
        {"name": "印度", "phone_code": "+91", "flag": "🇮🇳", "code": "IN"},
        {"name": "印度尼西亚", "phone_code": "+62", "flag": "🇮🇩", "code": "ID"},
        {"name": "厄瓜多尔", "phone_code": "+593", "flag": "🇪🇨", "code": "EC"},
        {"name": "厄立特里亚", "phone_code": "+291", "flag": "🇪🇷", "code": "ER"},
        {"name": "古巴", "phone_code": "+53", "flag": "🇨🇺", "code": "CU"},
        {"name": "台湾", "phone_code": "+886", "flag": "🇨🇳", "code": "TW"},
        {"name": "吉尔吉斯坦", "phone_code": "+996", "flag": "🇰🇬", "code": "KG"},
        {"name": "吉布提", "phone_code": "+253", "flag": "🇩🇯", "code": "DJ"},
        {"name": "哈萨克斯坦", "phone_code": "+7", "flag": "🇰🇿", "code": "KZ"},
        {"name": "哥伦比亚", "phone_code": "+57", "flag": "🇨🇴", "code": "CO"},
        {"name": "哥斯达黎加", "phone_code": "+506", "flag": "🇨🇷", "code": "CR"},
        {"name": "喀麦隆", "phone_code": "+237", "flag": "🇨🇲", "code": "CM"},
        {"name": "图瓦卢", "phone_code": "+688", "flag": "🇹🇻", "code": "TV"},
        {"name": "土库曼斯坦", "phone_code": "+993", "flag": "🇹🇲", "code": "TM"},
        {"name": "土耳其", "phone_code": "+90", "flag": "🇹🇷", "code": "TR"},
        {"name": "圣基茨和尼维斯", "phone_code": "+1", "flag": "🇰🇳", "code": "KN"},
        {"name": "圣多美和普林西比", "phone_code": "+239", "flag": "🇸🇹", "code": "ST"},
        {"name": "圣巴泰勒米岛", "phone_code": "+590", "flag": "🇧🇱", "code": "BL"},
        {
            "name": "圣文森特和格林纳丁斯",
            "phone_code": "+1",
            "flag": "🇻🇨",
            "code": "VC",
        },
        {"name": "圣皮埃尔和密克隆", "phone_code": "+508", "flag": "🇵🇲", "code": "PM"},
        {"name": "圣诞岛", "phone_code": "+61", "flag": "🇨🇽", "code": "CX"},
        {
            "name": "圣赫勒拿-阿森松-特里斯坦达库尼亚",
            "phone_code": "+290",
            "flag": "🇸🇭",
            "code": "SH",
        },
        {"name": "圣路西亚", "phone_code": "+1", "flag": "🇱🇨", "code": "LC"},
        {"name": "圣马力诺市", "phone_code": "+378", "flag": "🇸🇲", "code": "SM"},
        {"name": "圭亚那", "phone_code": "+592", "flag": "🇬🇾", "code": "GY"},
        {"name": "坦桑尼亚", "phone_code": "+255", "flag": "🇹🇿", "code": "TZ"},
        {"name": "埃及", "phone_code": "+20", "flag": "🇪🇬", "code": "EG"},
        {"name": "埃塞俄比亚", "phone_code": "+251", "flag": "🇪🇹", "code": "ET"},
        {"name": "基里巴斯", "phone_code": "+686", "flag": "🇰🇮", "code": "KI"},
        {"name": "塔吉克斯坦", "phone_code": "+992", "flag": "🇹🇯", "code": "TJ"},
        {"name": "塞内加尔", "phone_code": "+221", "flag": "🇸🇳", "code": "SN"},
        {"name": "塞尔维亚", "phone_code": "+381", "flag": "🇷🇸", "code": "RS"},
        {"name": "塞拉利昂", "phone_code": "+232", "flag": "🇸🇱", "code": "SL"},
        {"name": "塞浦路斯", "phone_code": "+357", "flag": "🇨🇾", "code": "CY"},
        {"name": "塞舌尔", "phone_code": "+248", "flag": "🇸🇨", "code": "SC"},
        {"name": "墨西哥", "phone_code": "+52", "flag": "🇲🇽", "code": "MX"},
        {"name": "多哥", "phone_code": "+228", "flag": "🇹🇬", "code": "TG"},
        {"name": "多米尼克", "phone_code": "+1", "flag": "🇩🇲", "code": "DM"},
        {"name": "多米尼加共和国", "phone_code": "+1", "flag": "🇩🇴", "code": "DO"},
        {"name": "大韩民国", "phone_code": "+82", "flag": "🇰🇷", "code": "KR"},
        {"name": "奥兰群岛", "phone_code": "+358", "flag": "🇦🇽", "code": "AX"},
        {"name": "奥地利", "phone_code": "+43", "flag": "🇦🇹", "code": "AT"},
        {
            "name": "委内瑞拉玻利瓦尔共和国",
            "phone_code": "+58",
            "flag": "🇻🇪",
            "code": "VE",
        },
        {"name": "孟加拉", "phone_code": "+880", "flag": "🇧🇩", "code": "BD"},
        {"name": "安哥拉", "phone_code": "+244", "flag": "🇦🇴", "code": "AO"},
        {"name": "安圭拉", "phone_code": "+1", "flag": "🇦🇮", "code": "AI"},
        {"name": "安提瓜和巴布达", "phone_code": "+1", "flag": "🇦🇬", "code": "AG"},
        {"name": "安道尔", "phone_code": "+376", "flag": "🇦🇩", "code": "AD"},
        {"name": "密克罗尼西亚", "phone_code": "+691", "flag": "🇫🇲", "code": "FM"},
        {"name": "尼加拉瓜", "phone_code": "+505", "flag": "🇳🇮", "code": "NI"},
        {"name": "尼日利亚", "phone_code": "+234", "flag": "🇳🇬", "code": "NG"},
        {"name": "尼日尔", "phone_code": "+227", "flag": "🇳🇪", "code": "NE"},
        {"name": "尼泊尔", "phone_code": "+977", "flag": "🇳🇵", "code": "NP"},
        {"name": "巴勒斯坦", "phone_code": "+970", "flag": "🇵🇸", "code": "PS"},
        {"name": "巴哈马", "phone_code": "+1", "flag": "🇧🇸", "code": "BS"},
        {"name": "巴基斯坦", "phone_code": "+92", "flag": "🇵🇰", "code": "PK"},
        {"name": "巴巴多斯", "phone_code": "+1", "flag": "🇧🇧", "code": "BB"},
        {"name": "巴布亚新几内亚", "phone_code": "+675", "flag": "🇵🇬", "code": "PG"},
        {"name": "巴拉圭", "phone_code": "+595", "flag": "🇵🇾", "code": "PY"},
        {"name": "巴拿马", "phone_code": "+507", "flag": "🇵🇦", "code": "PA"},
        {"name": "巴林", "phone_code": "+973", "flag": "🇧🇭", "code": "BH"},
        {"name": "巴西", "phone_code": "+55", "flag": "🇧🇷", "code": "BR"},
        {"name": "布基纳法索", "phone_code": "+226", "flag": "🇧🇫", "code": "BF"},
        {"name": "布隆迪", "phone_code": "+257", "flag": "🇧🇮", "code": "BI"},
        {"name": "希腊", "phone_code": "+30", "flag": "🇬🇷", "code": "GR"},
        {"name": "帕劳", "phone_code": "+680", "flag": "🇵🇼", "code": "PW"},
        {"name": "库克群岛", "phone_code": "+682", "flag": "🇨🇰", "code": "CK"},
        {"name": "库拉索", "phone_code": "+599", "flag": "🇨🇼", "code": "CW"},
        {"name": "开曼群岛", "phone_code": "+1", "flag": "🇰🇾", "code": "KY"},
        {"name": "德国", "phone_code": "+49", "flag": "🇩🇪", "code": "DE"},
        {"name": "意大利", "phone_code": "+39", "flag": "🇮🇹", "code": "IT"},
        {"name": "所罗门群岛", "phone_code": "+677", "flag": "🇸🇧", "code": "SB"},
        {"name": "托克劳", "phone_code": "+690", "flag": "🇹🇰", "code": "TK"},
        {"name": "拉脱维亚", "phone_code": "+371", "flag": "🇱🇻", "code": "LV"},
        {"name": "挪威", "phone_code": "+47", "flag": "🇳🇴", "code": "NO"},
        {"name": "捷克", "phone_code": "+420", "flag": "🇨🇿", "code": "CZ"},
        {"name": "摩尔多瓦共和国", "phone_code": "+373", "flag": "🇲🇩", "code": "MD"},
        {"name": "摩洛哥", "phone_code": "+212", "flag": "🇲🇦", "code": "MA"},
        {"name": "摩纳哥", "phone_code": "+377", "flag": "🇲🇨", "code": "MC"},
        {"name": "文莱", "phone_code": "+673", "flag": "🇧🇳", "code": "BN"},
        {"name": "斐济", "phone_code": "+679", "flag": "🇫🇯", "code": "FJ"},
        {"name": "斯威士兰", "phone_code": "+268", "flag": "🇸🇿", "code": "SZ"},
        {"name": "斯洛伐克", "phone_code": "+421", "flag": "🇸🇰", "code": "SK"},
        {"name": "斯洛文尼亚", "phone_code": "+386", "flag": "🇸🇮", "code": "SI"},
        {
            "name": "斯瓦尔巴特和扬马延岛",
            "phone_code": "+47",
            "flag": "🇸🇯",
            "code": "SJ",
        },
        {"name": "斯里兰卡", "phone_code": "+94", "flag": "🇱🇰", "code": "LK"},
        {"name": "新加坡", "phone_code": "+65", "flag": "🇸🇬", "code": "SG"},
        {"name": "新喀里多尼亚", "phone_code": "+687", "flag": "🇳🇨", "code": "NC"},
        {"name": "新西兰", "phone_code": "+64", "flag": "🇳🇿", "code": "NZ"},
        {"name": "日本", "phone_code": "+81", "flag": "🇯🇵", "code": "JP"},
        {"name": "智利", "phone_code": "+56", "flag": "🇨🇱", "code": "CL"},
        {"name": "曼岛", "phone_code": "+44", "flag": "🇮🇲", "code": "IM"},
        {
            "name": "朝鲜民主主义人民共和国",
            "phone_code": "+850",
            "flag": "🇰🇵",
            "code": "KP",
        },
        {"name": "柬埔塞", "phone_code": "+855", "flag": "🇰🇭", "code": "KH"},
        {"name": "根西岛", "phone_code": "+44", "flag": "🇬🇬", "code": "GG"},
        {"name": "格林纳达", "phone_code": "+1", "flag": "🇬🇩", "code": "GD"},
        {"name": "格陵兰", "phone_code": "+299", "flag": "🇬🇱", "code": "GL"},
        {"name": "格鲁吉亚", "phone_code": "+995", "flag": "🇬🇪", "code": "GE"},
        {"name": "梵地冈", "phone_code": "+39", "flag": "🇻🇦", "code": "VA"},
        {"name": "比利时", "phone_code": "+32", "flag": "🇧🇪", "code": "BE"},
        {"name": "毛里塔尼亚", "phone_code": "+222", "flag": "🇲🇷", "code": "MR"},
        {"name": "毛里求斯", "phone_code": "+230", "flag": "🇲🇺", "code": "MU"},
        {"name": "汤加", "phone_code": "+676", "flag": "🇹🇴", "code": "TO"},
        {"name": "沙特阿拉伯", "phone_code": "+966", "flag": "🇸🇦", "code": "SA"},
        {"name": "法国", "phone_code": "+33", "flag": "🇫🇷", "code": "FR"},
        {"name": "法属圣马丁", "phone_code": "+590", "flag": "🇲🇫", "code": "MF"},
        {"name": "法属圭亚那", "phone_code": "+594", "flag": "🇬🇫", "code": "GF"},
        {"name": "法属玻利尼西亚", "phone_code": "+689", "flag": "🇵🇫", "code": "PF"},
        {"name": "法罗群岛", "phone_code": "+298", "flag": "🇫🇴", "code": "FO"},
        {"name": "波兰", "phone_code": "+48", "flag": "🇵🇱", "code": "PL"},
        {"name": "波多黎各", "phone_code": "+1", "flag": "🇵🇷", "code": "PR"},
        {
            "name": "波斯尼亚和黑塞哥维那",
            "phone_code": "+387",
            "flag": "🇧🇦",
            "code": "BA",
        },
        {"name": "泰国", "phone_code": "+66", "flag": "🇹🇭", "code": "TH"},
        {"name": "泽西岛", "phone_code": "+44", "flag": "🇯🇪", "code": "JE"},
        {"name": "津巴布韦", "phone_code": "+263", "flag": "🇿🇼", "code": "ZW"},
        {"name": "洪都拉斯", "phone_code": "+504", "flag": "🇭🇳", "code": "HN"},
        {"name": "海地", "phone_code": "+509", "flag": "🇭🇹", "code": "HT"},
        {"name": "澳大利亚", "phone_code": "+61", "flag": "🇦🇺", "code": "AU"},
        {"name": "澳门", "phone_code": "+853", "flag": "🇲🇴", "code": "MO"},
        {"name": "爱尔兰", "phone_code": "+353", "flag": "🇮🇪", "code": "IE"},
        {"name": "爱沙尼亚", "phone_code": "+372", "flag": "🇪🇪", "code": "EE"},
        {"name": "牙买加", "phone_code": "+1", "flag": "🇯🇲", "code": "JM"},
        {"name": "特克斯和凯科斯群岛", "phone_code": "+1", "flag": "🇹🇨", "code": "TC"},
        {"name": "特里尼达和多巴哥", "phone_code": "+1", "flag": "🇹🇹", "code": "TT"},
        {"name": "玻利维亚共和国", "phone_code": "+591", "flag": "🇧🇴", "code": "BO"},
        {"name": "瑙鲁", "phone_code": "+674", "flag": "🇳🇷", "code": "NR"},
        {"name": "瑞典", "phone_code": "+46", "flag": "🇸🇪", "code": "SE"},
        {"name": "瑞士", "phone_code": "+41", "flag": "🇨🇭", "code": "CH"},
        {"name": "瓜地马拉", "phone_code": "+502", "flag": "🇬🇹", "code": "GT"},
        {"name": "瓜德罗普", "phone_code": "+590", "flag": "🇬🇵", "code": "GP"},
        {"name": "瓦利斯和富图纳", "phone_code": "+681", "flag": "🇼🇫", "code": "WF"},
        {"name": "瓦努阿图", "phone_code": "+678", "flag": "🇻🇺", "code": "VU"},
        {"name": "留尼汪", "phone_code": "+262", "flag": "🇷🇪", "code": "RE"},
        {"name": "白俄罗斯", "phone_code": "+375", "flag": "🇧🇾", "code": "BY"},
        {"name": "百慕大", "phone_code": "+1", "flag": "🇧🇲", "code": "BM"},
        {"name": "直布罗陀", "phone_code": "+350", "flag": "🇬🇮", "code": "GI"},
        {
            "name": "福克兰群岛(马尔维纳斯)",
            "phone_code": "+500",
            "flag": "🇫🇰",
            "code": "FK",
        },
        {"name": "科威特", "phone_code": "+965", "flag": "🇰🇼", "code": "KW"},
        {"name": "科摩罗", "phone_code": "+269", "flag": "🇰🇲", "code": "KM"},
        {"name": "科特迪瓦", "phone_code": "+225", "flag": "🇨🇮", "code": "CI"},
        {"name": "科科斯群岛", "phone_code": "+61", "flag": "🇨🇨", "code": "CC"},
        {"name": "秘鲁", "phone_code": "+51", "flag": "🇵🇪", "code": "PE"},
        {"name": "突尼斯", "phone_code": "+216", "flag": "🇹🇳", "code": "TN"},
        {"name": "立陶宛", "phone_code": "+370", "flag": "🇱🇹", "code": "LT"},
        {"name": "索马里", "phone_code": "+252", "flag": "🇸🇴", "code": "SO"},
        {"name": "约旦", "phone_code": "+962", "flag": "🇯🇴", "code": "JO"},
        {"name": "纳米比亚", "phone_code": "+264", "flag": "🇳🇦", "code": "NA"},
        {"name": "纽埃", "phone_code": "+683", "flag": "🇳🇺", "code": "NU"},
        {"name": "缅甸", "phone_code": "+95", "flag": "🇲🇲", "code": "MM"},
        {"name": "罗马尼亚", "phone_code": "+40", "flag": "🇷🇴", "code": "RO"},
        {"name": "美国", "phone_code": "+1", "flag": "🇺🇸", "code": "US"},
        {"name": "美属维尔京群岛", "phone_code": "+1", "flag": "🇻🇮", "code": "VI"},
        {"name": "美属萨摩亚", "phone_code": "+1", "flag": "🇦🇸", "code": "AS"},
        {
            "name": "老挝人民民主共和国",
            "phone_code": "+856",
            "flag": "🇱🇦",
            "code": "LA",
        },
        {"name": "肯尼亚", "phone_code": "+254", "flag": "🇰🇪", "code": "KE"},
        {"name": "芬兰", "phone_code": "+358", "flag": "🇫🇮", "code": "FI"},
        {"name": "苏丹", "phone_code": "+249", "flag": "🇸🇩", "code": "SD"},
        {"name": "苏里南", "phone_code": "+597", "flag": "🇸🇷", "code": "SR"},
        {"name": "英国", "phone_code": "+44", "flag": "🇬🇧", "code": "GB"},
        {"name": "英属印度洋领地", "phone_code": "+246", "flag": "🇮🇴", "code": "IO"},
        {"name": "英属维尔京群岛", "phone_code": "+1", "flag": "🇻🇬", "code": "VG"},
        {"name": "荷兰", "phone_code": "+31", "flag": "🇳🇱", "code": "NL"},
        {"name": "荷属圣马丁", "phone_code": "+1", "flag": "🇸🇽", "code": "SX"},
        {"name": "莫桑比克", "phone_code": "+258", "flag": "🇲🇿", "code": "MZ"},
        {"name": "莱索托", "phone_code": "+266", "flag": "🇱🇸", "code": "LS"},
        {"name": "菲律宾", "phone_code": "+63", "flag": "🇵🇭", "code": "PH"},
        {"name": "萨尔瓦多", "phone_code": "+503", "flag": "🇸🇻", "code": "SV"},
        {"name": "萨摩亚", "phone_code": "+685", "flag": "🇼🇸", "code": "WS"},
        {"name": "葡萄牙", "phone_code": "+351", "flag": "🇵🇹", "code": "PT"},
        {"name": "蒙古", "phone_code": "+976", "flag": "🇲🇳", "code": "MN"},
        {"name": "蒙塞拉特岛", "phone_code": "+1", "flag": "🇲🇸", "code": "MS"},
        {"name": "西撒哈拉", "phone_code": "+212", "flag": "🇪🇭", "code": "EH"},
        {"name": "西班牙", "phone_code": "+34", "flag": "🇪🇸", "code": "ES"},
        {"name": "诺福克岛", "phone_code": "+672", "flag": "🇳🇫", "code": "NF"},
        {"name": "贝宁", "phone_code": "+229", "flag": "🇧🇯", "code": "BJ"},
        {"name": "赞比亚", "phone_code": "+260", "flag": "🇿🇲", "code": "ZM"},
        {"name": "赤道几内亚", "phone_code": "+240", "flag": "🇬🇶", "code": "GQ"},
        {"name": "越南", "phone_code": "+84", "flag": "🇻🇳", "code": "VN"},
        {"name": "阿塞拜疆", "phone_code": "+994", "flag": "🇦🇿", "code": "AZ"},
        {"name": "阿富汗", "phone_code": "+93", "flag": "🇦🇫", "code": "AF"},
        {"name": "阿尔及利亚", "phone_code": "+213", "flag": "🇩🇿", "code": "DZ"},
        {"name": "阿尔巴尼亚", "phone_code": "+355", "flag": "🇦🇱", "code": "AL"},
        {
            "name": "阿拉伯叙利亚共和国",
            "phone_code": "+963",
            "flag": "🇸🇾",
            "code": "SY",
        },
        {"name": "阿曼", "phone_code": "+968", "flag": "🇴🇲", "code": "OM"},
        {"name": "阿根廷", "phone_code": "+54", "flag": "🇦🇷", "code": "AR"},
        {"name": "阿联酋", "phone_code": "+971", "flag": "🇦🇪", "code": "AE"},
        {"name": "阿鲁巴", "phone_code": "+297", "flag": "🇦🇼", "code": "AW"},
        {"name": "香港", "phone_code": "+852", "flag": "🇭🇰", "code": "HK"},
        {"name": "马尔他", "phone_code": "+356", "flag": "🇲🇹", "code": "MT"},
        {"name": "马尔代夫", "phone_code": "+960", "flag": "🇲🇻", "code": "MV"},
        {"name": "马拉维", "phone_code": "+265", "flag": "🇲🇼", "code": "MW"},
        {"name": "马提尼克", "phone_code": "+596", "flag": "🇲🇶", "code": "MQ"},
        {"name": "马来西亚", "phone_code": "+60", "flag": "🇲🇾", "code": "MY"},
        {"name": "马约特", "phone_code": "+262", "flag": "🇾🇹", "code": "YT"},
        {"name": "马绍尔群岛", "phone_code": "+692", "flag": "🇲🇭", "code": "MH"},
        {"name": "马达加斯加", "phone_code": "+261", "flag": "🇲🇬", "code": "MG"},
        {"name": "马里", "phone_code": "+223", "flag": "🇲🇱", "code": "ML"},
        {"name": "黎巴嫩", "phone_code": "+961", "flag": "🇱🇧", "code": "LB"},
        {"name": "黑山", "phone_code": "+382", "flag": "🇲🇪", "code": "ME"},
    ]
    return success_response(data)


@router.post("/resources/cache", summary="将资源数据临时保存到服务器")
async def resource_cache(request: Request, resources: IResourceCache) -> ResponseBase:
    spm = str(uuid.uuid4())
    # TODO
    if resources is not None:
        # CommonResourceIDsCache(spm).set_storage_cache(resources, 300)
        print("cache")
    return success_response(spm=spm)
