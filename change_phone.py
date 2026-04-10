#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram 账号批量换绑脚本
功能：从旧手机号迁移账号到全新未注册的手机号
作者：hhyuu88
版本：1.0.0
"""

import asyncio
import hashlib
import json
import logging
import os
import random
import re
import shutil
import sys
import time
import zipfile
from datetime import datetime
from pathlib import Path

import requests
from colorama import Fore, Style, init
from telethon import TelegramClient
from telethon.errors import (
    PhoneCodeExpiredError,
    PhoneCodeInvalidError,
    SessionPasswordNeededError,
)
from telethon.tl.functions.account import ChangePhoneRequest, SendChangePhoneCodeRequest
from telethon.tl.types import CodeSettings
from tqdm import tqdm

# 初始化 colorama（Windows 终端颜色支持）
init(autoreset=True)

# ============================================================
# 常量配置
# ============================================================

# 默认 API 凭证（官方默认值）
DEFAULT_APP_ID = 4
DEFAULT_APP_HASH = "014b35b6184100b085b0d0572f9b5103"

# 代理配置（IPDeep）
# 可通过环境变量覆盖：PROXY_USERNAME, PROXY_PASSWORD, PROXY_SERVER, PROXY_PORT
PROXY_USERNAME_PREFIX = os.environ.get("PROXY_USERNAME", "d1561533000")
PROXY_PASSWORD = os.environ.get("PROXY_PASSWORD", "Qqesi3rN")
PROXY_SERVER = os.environ.get("PROXY_SERVER", "gate.ipdeep.com")
PROXY_PORT = int(os.environ.get("PROXY_PORT", "8082"))

# 路径配置
BASE_DIR = Path(__file__).parent
INPUT_DIR = BASE_DIR / "input"
SESSIONS_DIR = BASE_DIR / "sessions"
OUTPUT_DIR = BASE_DIR / "output"
LOGS_DIR = OUTPUT_DIR / "logs"

# 手机号国家代码映射表（手机号前缀 → 国家代码）
PHONE_TO_COUNTRY = {
    # 北美
    "+1": "us",
    # 中国及周边
    "+86": "cn",
    "+852": "hk",
    "+853": "mo",
    "+886": "tw",
    # 南亚
    "+880": "bd",
    "+91": "in",
    "+92": "pk",
    "+94": "lk",
    "+95": "mm",
    "+977": "np",
    # 东南亚
    "+60": "my",
    "+62": "id",
    "+63": "ph",
    "+65": "sg",
    "+66": "th",
    "+84": "vn",
    "+855": "kh",
    "+856": "la",
    # 欧洲
    "+44": "gb",
    "+33": "fr",
    "+49": "de",
    "+39": "it",
    "+34": "es",
    "+31": "nl",
    "+7": "ru",
    "+48": "pl",
    "+380": "ua",
    # 中东
    "+971": "ae",
    "+966": "sa",
    "+90": "tr",
    "+98": "ir",
    # 其他
    "+61": "au",
    "+64": "nz",
    "+55": "br",
    "+27": "za",
    "+234": "ng",
}

# 国家代码对应的国旗 emoji（用于日志美化）
COUNTRY_FLAGS = {
    "us": "🇺🇸",
    "cn": "🇨🇳",
    "hk": "🇭🇰",
    "mo": "🇲🇴",
    "tw": "🇹🇼",
    "bd": "🇧🇩",
    "in": "🇮🇳",
    "pk": "🇵🇰",
    "lk": "🇱🇰",
    "mm": "🇲🇲",
    "np": "🇳🇵",
    "my": "🇲🇾",
    "id": "🇮🇩",
    "ph": "🇵🇭",
    "sg": "🇸🇬",
    "th": "🇹🇭",
    "vn": "🇻🇳",
    "kh": "🇰🇭",
    "la": "🇱🇦",
    "gb": "🇬🇧",
    "fr": "🇫🇷",
    "de": "🇩🇪",
    "it": "🇮🇹",
    "es": "🇪🇸",
    "nl": "🇳🇱",
    "ru": "🇷🇺",
    "pl": "🇵🇱",
    "ua": "🇺🇦",
    "ae": "🇦🇪",
    "sa": "🇸🇦",
    "tr": "🇹🇷",
    "ir": "🇮🇷",
    "au": "🇦🇺",
    "nz": "🇳🇿",
    "br": "🇧🇷",
    "za": "🇿🇦",
    "ng": "🇳🇬",
}

# Android 设备池（真实设备，基于 2024 年市场份额）
ANDROID_DEVICES_POOL = [
    # Samsung（~20%）
    {
        "brand": "Samsung",
        "device_model": "Samsung SM-S908B",
        "model_name": "Galaxy S22 Ultra",
        "system_version": "SDK 33",
        "android_version": "13",
        "app_version": "10.14.5",
    },
    {
        "brand": "Samsung",
        "device_model": "Samsung SM-G998B",
        "model_name": "Galaxy S21 Ultra",
        "system_version": "SDK 33",
        "android_version": "13",
        "app_version": "10.14.4",
    },
    {
        "brand": "Samsung",
        "device_model": "Samsung SM-A536B",
        "model_name": "Galaxy A53 5G",
        "system_version": "SDK 33",
        "android_version": "13",
        "app_version": "10.14.5",
    },
    {
        "brand": "Samsung",
        "device_model": "Samsung SM-S911B",
        "model_name": "Galaxy S23",
        "system_version": "SDK 34",
        "android_version": "14",
        "app_version": "10.14.5",
    },
    # Xiaomi（~14%）
    {
        "brand": "Xiaomi",
        "device_model": "Xiaomi 2201123G",
        "model_name": "Xiaomi 12",
        "system_version": "SDK 33",
        "android_version": "13",
        "app_version": "10.14.4",
    },
    {
        "brand": "Xiaomi",
        "device_model": "Xiaomi 2211133G",
        "model_name": "Xiaomi 12T Pro",
        "system_version": "SDK 33",
        "android_version": "13",
        "app_version": "10.14.5",
    },
    {
        "brand": "Xiaomi",
        "device_model": "Xiaomi 23013RK75C",
        "model_name": "Redmi Note 12 Pro",
        "system_version": "SDK 33",
        "android_version": "13",
        "app_version": "10.14.4",
    },
    {
        "brand": "Xiaomi",
        "device_model": "Xiaomi 2304FPN6DG",
        "model_name": "Xiaomi 13",
        "system_version": "SDK 33",
        "android_version": "13",
        "app_version": "10.14.5",
    },
    # Google Pixel（信任度高）
    {
        "brand": "Google",
        "device_model": "Google Pixel 7 Pro",
        "model_name": "Pixel 7 Pro",
        "system_version": "SDK 34",
        "android_version": "14",
        "app_version": "10.14.5",
    },
    {
        "brand": "Google",
        "device_model": "Google Pixel 7",
        "model_name": "Pixel 7",
        "system_version": "SDK 33",
        "android_version": "13",
        "app_version": "10.14.5",
    },
    {
        "brand": "Google",
        "device_model": "Google Pixel 6a",
        "model_name": "Pixel 6a",
        "system_version": "SDK 33",
        "android_version": "13",
        "app_version": "10.14.4",
    },
    # OPPO（~10%）
    {
        "brand": "OPPO",
        "device_model": "OPPO CPH2451",
        "model_name": "Find X6",
        "system_version": "SDK 33",
        "android_version": "13",
        "app_version": "10.14.5",
    },
    {
        "brand": "OPPO",
        "device_model": "OPPO CPH2389",
        "model_name": "Reno 8 Pro",
        "system_version": "SDK 33",
        "android_version": "13",
        "app_version": "10.14.4",
    },
    # Vivo（~9%）
    {
        "brand": "Vivo",
        "device_model": "V2227A",
        "model_name": "Vivo X90 Pro",
        "system_version": "SDK 33",
        "android_version": "13",
        "app_version": "10.14.5",
    },
    {
        "brand": "Vivo",
        "device_model": "V2199A",
        "model_name": "Vivo X80",
        "system_version": "SDK 33",
        "android_version": "13",
        "app_version": "10.14.4",
    },
    # OnePlus
    {
        "brand": "OnePlus",
        "device_model": "OnePlus CPH2449",
        "model_name": "OnePlus 11",
        "system_version": "SDK 33",
        "android_version": "13",
        "app_version": "10.14.5",
    },
    {
        "brand": "OnePlus",
        "device_model": "OnePlus LE2123",
        "model_name": "OnePlus 9 Pro",
        "system_version": "SDK 33",
        "android_version": "13",
        "app_version": "10.14.4",
    },
    # Realme
    {
        "brand": "Realme",
        "device_model": "RMX3708",
        "model_name": "Realme GT Neo 5",
        "system_version": "SDK 33",
        "android_version": "13",
        "app_version": "10.14.5",
    },
    {
        "brand": "Realme",
        "device_model": "RMX3663",
        "model_name": "Realme 10 Pro+",
        "system_version": "SDK 33",
        "android_version": "13",
        "app_version": "10.14.4",
    },
    # Motorola
    {
        "brand": "Motorola",
        "device_model": "motorola edge 30 pro",
        "model_name": "Edge 30 Pro",
        "system_version": "SDK 33",
        "android_version": "13",
        "app_version": "10.14.4",
    },
    # Nothing Phone
    {
        "brand": "Nothing",
        "device_model": "Nothing A063",
        "model_name": "Nothing Phone (2)",
        "system_version": "SDK 33",
        "android_version": "13",
        "app_version": "10.14.5",
    },
]

# 国家语言映射表
COUNTRY_LANGUAGE_MAP = {
    "cn": {"lang_code": "zh-hans", "system_lang_code": "zh-hans", "lang_pack": "android"},
    "hk": {"lang_code": "zh-hant", "system_lang_code": "zh-hant", "lang_pack": "android"},
    "tw": {"lang_code": "zh-hant", "system_lang_code": "zh-hant", "lang_pack": "android"},
    "us": {"lang_code": "en", "system_lang_code": "en-us", "lang_pack": "android"},
    "gb": {"lang_code": "en", "system_lang_code": "en-gb", "lang_pack": "android"},
    "in": {"lang_code": "en", "system_lang_code": "en-in", "lang_pack": "android"},
    "bd": {"lang_code": "bn", "system_lang_code": "bn-bd", "lang_pack": "android"},
    "pk": {"lang_code": "ur", "system_lang_code": "ur-pk", "lang_pack": "android"},
    "ru": {"lang_code": "ru", "system_lang_code": "ru-ru", "lang_pack": "android"},
    "br": {"lang_code": "pt-br", "system_lang_code": "pt-br", "lang_pack": "android"},
    "de": {"lang_code": "de", "system_lang_code": "de-de", "lang_pack": "android"},
    "fr": {"lang_code": "fr", "system_lang_code": "fr-fr", "lang_pack": "android"},
    "es": {"lang_code": "es", "system_lang_code": "es-es", "lang_pack": "android"},
    "it": {"lang_code": "it", "system_lang_code": "it-it", "lang_pack": "android"},
    "jp": {"lang_code": "ja", "system_lang_code": "ja-jp", "lang_pack": "android"},
    "kr": {"lang_code": "ko", "system_lang_code": "ko-kr", "lang_pack": "android"},
    "vn": {"lang_code": "vi", "system_lang_code": "vi-vn", "lang_pack": "android"},
    "th": {"lang_code": "th", "system_lang_code": "th-th", "lang_pack": "android"},
    "id": {"lang_code": "id", "system_lang_code": "id-id", "lang_pack": "android"},
    "my": {"lang_code": "ms", "system_lang_code": "ms-my", "lang_pack": "android"},
    "ph": {"lang_code": "en", "system_lang_code": "en-ph", "lang_pack": "android"},
    "sg": {"lang_code": "en", "system_lang_code": "en-sg", "lang_pack": "android"},
    "tr": {"lang_code": "tr", "system_lang_code": "tr-tr", "lang_pack": "android"},
    "ae": {"lang_code": "ar", "system_lang_code": "ar-ae", "lang_pack": "android"},
    "sa": {"lang_code": "ar", "system_lang_code": "ar-sa", "lang_pack": "android"},
}


# ============================================================
# 日志配置
# ============================================================

class ColoredFormatter(logging.Formatter):
    """彩色日志格式化器"""

    COLORS = {
        "DEBUG": Fore.CYAN,
        "INFO": Fore.WHITE,
        "WARNING": Fore.YELLOW,
        "ERROR": Fore.RED,
        "CRITICAL": Fore.RED + Style.BRIGHT,
        "SUCCESS": Fore.GREEN,
    }

    def format(self, record):
        # 自定义 SUCCESS 级别
        if record.levelno == 25:
            color = Fore.GREEN + Style.BRIGHT
            level_name = "SUCCESS"
        else:
            color = self.COLORS.get(record.levelname, Fore.WHITE)
            level_name = record.levelname

        message = super().format(record)
        return f"{color}{message}{Style.RESET_ALL}"


def setup_logger():
    """初始化日志系统，同时输出到控制台和文件"""
    # 确保日志目录存在
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    # 添加自定义 SUCCESS 级别
    logging.SUCCESS = 25
    logging.addLevelName(25, "SUCCESS")

    def success(self, message, *args, **kwargs):
        if self.isEnabledFor(25):
            self._log(25, message, args, **kwargs)

    logging.Logger.success = success

    # 创建日志文件名（带时间戳）
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = LOGS_DIR / f"change_phone_{timestamp}.log"

    # 配置根日志器
    logger = logging.getLogger("change_phone")
    logger.setLevel(logging.DEBUG)

    # 控制台处理器（彩色输出）
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_formatter = ColoredFormatter(
        fmt="[%(levelname)s] %(message)s"
    )
    console_handler.setFormatter(console_formatter)

    # 文件处理器（纯文本）
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(file_formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger


logger = setup_logger()


# ============================================================
# 工具函数模块
# ============================================================

def load_config():
    """加载 config.json 配置文件"""
    config_path = BASE_DIR / "config.json"
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    # 返回默认配置
    return {
        "proxy": {
            "enabled": True,
            "username": PROXY_USERNAME_PREFIX,
            "password": PROXY_PASSWORD,
            "server": PROXY_SERVER,
            "port": PROXY_PORT,
            "type": "http",
            "auto_match_country": True,
        },
        "default_api": {
            "app_id": DEFAULT_APP_ID,
            "app_hash": DEFAULT_APP_HASH,
        },
        "intervals": {
            "between_accounts_min": 30,
            "between_accounts_max": 60,
            "sms_poll_interval": 5,
            "max_sms_wait_time": 300,
        },
        "sms": {
            "max_retry": 60,
            "retry_interval": 5,
        },
    }


def mask_url_key(url):
    """
    对 URL 中的 key= 参数进行掩码处理，避免日志中暴露 API 密钥
    例如：...?key=abcdef1234 → ...?key=***
    """
    return re.sub(r'(key=)[^&\s]+', r'\1***', url)


def extract_accounts_zip():
    """
    解压 input/accounts.zip 到 sessions/ 目录
    返回解压的文件列表
    """
    zip_path = INPUT_DIR / "accounts.zip"
    if not zip_path.exists():
        logger.error(f"❌ 找不到 accounts.zip: {zip_path}")
        sys.exit(1)

    # 先解压到临时目录，验证成功后再替换正式目录
    import tempfile
    tmp_dir = Path(tempfile.mkdtemp(prefix="tg_sessions_"))
    try:
        logger.info(f"📦 解压 {zip_path} → {SESSIONS_DIR}")
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(tmp_dir)
            extracted = zf.namelist()

        # 解压成功后，替换正式目录
        if SESSIONS_DIR.exists():
            shutil.rmtree(SESSIONS_DIR)
        shutil.copytree(str(tmp_dir), str(SESSIONS_DIR))
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    logger.info(f"✅ 解压完成，共 {len(extracted)} 个文件")
    return extracted


def pair_session_json_files():
    """
    配对 sessions/ 目录中的 .session 和 .json 文件
    返回配对列表 [(session_path, json_path, account_data), ...]
    """
    session_files = {f.stem: f for f in SESSIONS_DIR.glob("**/*.session")}
    json_files = {f.stem: f for f in SESSIONS_DIR.glob("**/*.json")}

    paired = []
    for name, session_path in session_files.items():
        if name in json_files:
            json_path = json_files[name]
            try:
                account_data = load_account_from_json(json_path)
                paired.append((session_path, json_path, account_data))
                logger.debug(f"配对成功: {name}.session ↔ {name}.json")
            except Exception as e:
                logger.error(f"❌ 读取 JSON 文件失败 {json_path}: {e}")
        else:
            logger.warning(f"⚠️ 找不到对应 JSON: {name}.session（跳过）")

    logger.info(f"✅ 成功配对 {len(paired)} 个账号")
    return paired


def load_account_from_json(json_path):
    """
    读取账号 JSON 文件，并自动替换为默认 API 凭证（如果非默认值）
    """
    with open(json_path, "r", encoding="utf-8") as f:
        account = json.load(f)

    # 检查并替换非默认的 app_id / app_hash
    original_app_id = account.get("app_id")
    original_app_hash = account.get("app_hash", "")

    if original_app_id != DEFAULT_APP_ID or original_app_hash != DEFAULT_APP_HASH:
        logger.warning(
            f"检测到非默认 API: app_id={original_app_id} → {DEFAULT_APP_ID}，"
            f"app_hash={original_app_hash[:8]}... → {DEFAULT_APP_HASH[:8]}... (已自动替换)"
        )
        account["app_id"] = DEFAULT_APP_ID
        account["app_hash"] = DEFAULT_APP_HASH

    return account


def load_new_phones(phones_file=None):
    """
    读取 input/new_phones.txt，返回 [(phone, sms_api_url), ...] 列表
    格式：+8617800001234|https://smsapis.com/api/get_sms?key=xxx
    """
    if phones_file is None:
        phones_file = INPUT_DIR / "new_phones.txt"

    if not Path(phones_file).exists():
        logger.error(f"❌ 找不到新号码文件: {phones_file}")
        sys.exit(1)

    phones = []
    with open(phones_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("|", 1)
            if len(parts) == 2:
                phone, sms_api = parts[0].strip(), parts[1].strip()
                phone = normalize_phone_number(phone)
                phones.append((phone, sms_api))
            else:
                logger.warning(f"⚠️ 格式错误，跳过: {line}")

    logger.info(f"✅ 读取到 {len(phones)} 个新号码")
    return phones


def normalize_phone_number(phone):
    """
    规范化手机号：确保以 + 开头
    如果没有 +，自动添加
    """
    phone = phone.strip()
    if not phone.startswith('+'):
        phone = '+' + phone
        logger.info(f"自动添加 + 前缀: {phone}")
    return phone


def generate_random_android_device(account_phone=None):
    """
    随机生成真实的 Android 设备信息

    参数:
        account_phone: 账号手机号（用于生成稳定的随机种子）

    返回:
        dict: 包含 device_model, system_version, app_version 等
    """
    # 使用手机号的 hash 作为随机种子（同一账号总是生成相同设备）
    if account_phone:
        seed = int(hashlib.sha256(account_phone.encode()).hexdigest()[:8], 16)
        random.seed(seed)

    # 随机选择一个设备
    device = random.choice(ANDROID_DEVICES_POOL)

    # 恢复随机状态
    if account_phone:
        random.seed()

    logger.info(
        f"🎲 随机生成设备: {device['brand']} {device['model_name']} "
        f"(Android {device['android_version']})"
    )

    return {
        "device_model": device["device_model"],
        "system_version": device["system_version"],
        "app_version": device["app_version"],
        "brand": device["brand"],
        "model_name": device["model_name"],
        "android_version": device["android_version"],
    }


def get_language_by_country(country_code):
    """根据国家代码返回语言配置"""
    return COUNTRY_LANGUAGE_MAP.get(
        country_code,
        {"lang_code": "en", "system_lang_code": "en-us", "lang_pack": "android"}
    )


# ============================================================
# 代理模块
# ============================================================

def get_country_from_phone(phone):
    """
    根据手机号提取国家代码
    例如：+8617800001234 → cn
    按最长前缀优先匹配
    """
    # 按前缀长度从长到短排序，优先匹配更精确的前缀
    sorted_prefixes = sorted(PHONE_TO_COUNTRY.keys(), key=len, reverse=True)
    for prefix in sorted_prefixes:
        if phone.startswith(prefix):
            return PHONE_TO_COUNTRY[prefix]
    return None


def build_proxy_string(country_code, config):
    """
    根据国家代码构建代理字符串
    格式：{用户名}-res-country-{国家代码}-session-{随机ID}:{密码}@{服务器}:{端口}
    """
    proxy_conf = config.get("proxy", {})
    username = proxy_conf.get("username", PROXY_USERNAME_PREFIX)
    password = proxy_conf.get("password", PROXY_PASSWORD)
    server = proxy_conf.get("server", PROXY_SERVER)
    port = proxy_conf.get("port", PROXY_PORT)

    # 生成随机会话 ID（2000000000-2999999999）
    session_id = random.randint(2000000000, 2999999999)

    proxy_user = f"{username}-res-country-{country_code}-session-{session_id}"
    return proxy_user, password, server, port, session_id


def get_proxy_for_phone(new_phone, config):
    """
    根据新手机号自动匹配代理配置
    返回 Telethon 格式的代理参数字典，或 None（如果不启用代理）
    """
    proxy_conf = config.get("proxy", {})
    if not proxy_conf.get("enabled", True):
        return None, None, None

    country_code = get_country_from_phone(new_phone)
    if not country_code:
        logger.warning(f"⚠️ 无法识别号码 {new_phone} 的国家，使用 US 代理")
        country_code = "us"

    proxy_user, password, server, port, session_id = build_proxy_string(
        country_code, config
    )

    flag = COUNTRY_FLAGS.get(country_code, "🌍")
    logger.info(
        f"新号码: {new_phone} → 国家: {country_code.upper()} {flag}"
    )
    logger.info(f"使用代理: {country_code.upper()} IP")
    logger.info(
        f"代理地址: {proxy_conf.get('username', PROXY_USERNAME_PREFIX)}"
        f"-res-country-{country_code}-session-***:***@{server}:{port}"
    )

    # Telethon HTTP 代理格式（通过 python-socks）
    proxy = {
        "proxy_type": "http",
        "addr": server,
        "port": port,
        "username": proxy_user,
        "password": password,
        "rdns": True,
    }

    return proxy, country_code, session_id


# ============================================================
# 接码平台模块
# ============================================================

async def poll_sms_code(sms_api_url, config, phone_hint=""):
    """
    轮询接码平台获取验证码
    最多尝试 max_retry 次，每次间隔 retry_interval 秒
    返回验证码字符串，或 None（超时）
    """
    sms_conf = config.get("sms", {})
    max_retry = sms_conf.get("max_retry", 60)
    retry_interval = sms_conf.get("retry_interval", 5)

    logger.info(f"开始轮询接码平台，最多等待 {max_retry * retry_interval} 秒...")

    for attempt in range(1, max_retry + 1):
        try:
            response = requests.get(sms_api_url, timeout=15)
            text = response.text.strip()

            logger.info(f"轮询接码平台... ({attempt}/{max_retry})")
            logger.debug(f"← {text}")

            # 判断是否收到验证码
            if not text or "no" in text.lower():
                logger.info(f"← {text} (继续等待)")
            else:
                # 提取纯数字验证码
                digits = "".join(filter(str.isdigit, text))
                if digits and len(digits) >= 4:
                    logger.info(f"← {text}")
                    logger.success(f"✅ 收到验证码: {digits}")
                    return digits
                else:
                    logger.warning(f"⚠️ 响应格式异常: {text}")

        except requests.RequestException as e:
            # 日志中不暴露含 API 密钥的 URL
            logger.warning(f"⚠️ 接码平台请求失败 ({attempt}/{max_retry}): {type(e).__name__}")

        # 等待下次轮询
        if attempt < max_retry:
            await asyncio.sleep(retry_interval)

    logger.error(f"❌ 验证码超时，等待了 {max_retry * retry_interval} 秒仍未收到")
    return None


# ============================================================
# 核心换绑模块
# ============================================================

async def change_phone_number(
    session_path, account_data, new_phone, sms_api_url, config
):
    """
    对单个账号执行完整的换绑流程

    参数：
        session_path: .session 文件路径
        account_data: 账号 JSON 数据
        new_phone: 新手机号（格式：+8617800001234）
        sms_api_url: 接码平台 API 地址
        config: 全局配置

    返回：
        dict: 包含 success, new_phone, error 等字段
    """
    # 获取代理配置
    proxy, country_code, session_id = get_proxy_for_phone(new_phone, config)

    # 确定 session 文件路径（去掉 .session 扩展名，Telethon 会自动加）
    session_name = str(session_path).replace(".session", "")

    # 🎲 生成随机 Android 设备信息
    old_phone = account_data.get("phone", "")
    device_info = generate_random_android_device(account_phone=old_phone)

    # 🌍 根据新号码的国家匹配语言
    lang_config = get_language_by_country(country_code or "us")

    # 创建 Telethon 客户端
    client_kwargs = {
        "api_id": account_data["app_id"],
        "api_hash": account_data["app_hash"],
        # ✅ 使用随机生成的 Android 设备信息
        "device_model": device_info["device_model"],
        "system_version": device_info["system_version"],
        "app_version": device_info["app_version"],
        # ✅ 使用匹配国家的语言配置
        "lang_code": lang_config["lang_code"],
        "system_lang_code": lang_config["system_lang_code"],
    }
    if proxy:
        client_kwargs["proxy"] = proxy

    client = TelegramClient(session_name, **client_kwargs)

    try:
        # 连接 Telegram
        logger.info("正在连接 Telegram...")
        await client.connect()

        # 验证 session 文件是否有效
        if not await client.is_user_authorized():
            raise Exception(f"Session 文件未授权或已过期: {session_path.name}")

        # 获取当前账号信息
        me = await client.get_me()
        logger.info(
            f"✅ 通过{'  ' + country_code.upper() + ' IP ' if country_code else ' '}连接成功"
        )
        logger.info(
            f"当前账号: +{me.phone} ({me.first_name or ''} {me.last_name or ''})"
        )

        # 🆕 显示设备和语言信息
        logger.info(
            f"📱 设备: {device_info['brand']} {device_info['model_name']} "
            f"(Android {device_info['android_version']}, 语言: {lang_config['lang_code']})"
        )

        # 发送验证码到新手机号
        logger.info(f"发送验证码到: {new_phone}")
        sent_code = await client(SendChangePhoneCodeRequest(
            phone_number=new_phone,
            settings=CodeSettings()
        ))
        logger.info("✅ 验证码已发送")

        # 🆕 显示验证码类型
        logger.debug(f"📋 验证码类型: {type(sent_code.type).__name__}")
        if hasattr(sent_code, 'timeout'):
            logger.debug(f"📋 超时时间: {sent_code.timeout} 秒")

        # 轮询接码平台获取验证码
        code = await poll_sms_code(sms_api_url, config, phone_hint=new_phone)
        if not code:
            raise Exception("验证码超时，未能从接码平台获取验证码")

        # 提交验证码完成换绑
        two_fa_used = False
        try:
            await client(ChangePhoneRequest(
                phone_number=new_phone,
                phone_code_hash=sent_code.phone_code_hash,
                phone_code=code,
            ))
        except SessionPasswordNeededError:
            # 需要两步验证密码
            two_fa_password = account_data.get("twoFA", "")
            if not two_fa_password:
                raise Exception("需要两步验证密码，但 JSON 文件中未提供 twoFA 字段")

            logger.info("检测到两步验证，提交密码...")
            sign_in_result = await client.sign_in(password=two_fa_password)
            # 验证 2FA 登录是否成功
            if not sign_in_result:
                raise Exception("两步验证失败，密码可能不正确")
            logger.info("✅ 两步验证通过")
            # 重新提交换绑
            await client(ChangePhoneRequest(
                phone_number=new_phone,
                phone_code_hash=sent_code.phone_code_hash,
                phone_code=code,
            ))
            two_fa_used = True

        except PhoneCodeInvalidError:
            raise Exception(f"验证码 {code} 无效，请检查接码平台")

        except PhoneCodeExpiredError:
            raise Exception("验证码已过期，请重新发起换绑")

        # 验证换绑成功
        me_new = await client.get_me()
        new_phone_clean = new_phone.removeprefix("+")

        if me_new.phone == new_phone_clean:
            logger.success(f"🎉 换绑成功！新号码: {new_phone}")
        else:
            logger.warning(
                f"⚠️ 换绑后号码验证：期望 {new_phone_clean}，实际 {me_new.phone}"
            )

        return {
            "success": True,
            "old_phone": account_data.get("phone", str(me.phone)),
            "new_phone": new_phone,
            "session_file": session_path.name,
            "twoFA": account_data.get("twoFA", ""),
            "user_id": str(account_data.get("user_id", me.id)),
            "first_name": me.first_name or "",
            "last_name": me.last_name or "",
            "changed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "country": country_code or "unknown",
            "two_fa_used": two_fa_used,
            "device_model": device_info["device_model"],
            "device_brand": device_info["brand"],
        }

    except Exception as e:
        logger.error(f"❌ 换绑失败: {e}")
        return {"success": False, "error": str(e), "new_phone": new_phone}

    finally:
        # 断开连接（session 文件会自动更新）
        try:
            await client.disconnect()
        except Exception:
            pass


# ============================================================
# 输出文件生成模块
# ============================================================

def save_success_result(successes, output_file):
    """
    保存成功换绑的号码和接码 API 到 success_result.txt
    格式：+8617800001234|https://smsapis.com/api/get_sms?key=xxx
    """
    with open(output_file, "w", encoding="utf-8") as f:
        for item in successes:
            f.write(f"{item['new_phone']}|{item['sms_api_url']}\n")
    logger.info(f"✅ 已保存成功结果: {output_file}")


def save_failed_phones(failures, output_file):
    """
    保存失败的号码和接码 API 到 failed_phones.txt（可重用）
    """
    with open(output_file, "w", encoding="utf-8") as f:
        for item in failures:
            f.write(f"{item['new_phone']}|{item['sms_api_url']}\n")
    logger.info(f"✅ 已保存失败号码: {output_file}")


def save_success_accounts_json(successes, output_file):
    """
    保存成功换绑的账号详细信息到 success_accounts.json
    """
    records = []
    for item in successes:
        records.append(
            {
                "old_phone": item.get("old_phone", ""),
                "new_phone": item["new_phone"],
                "session_file": item.get("session_file", ""),
                "twoFA": item.get("twoFA", ""),
                "user_id": item.get("user_id", ""),
                "first_name": item.get("first_name", ""),
                "last_name": item.get("last_name", ""),
                "changed_at": item.get("changed_at", ""),
                "country": item.get("country", ""),
            }
        )
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    logger.info(f"✅ 已保存成功账号信息: {output_file}")


def update_account_json(json_path, account_data, new_phone, country_code):
    """
    更新账号 JSON 文件（换绑后的新号码、默认 API、换绑时间）
    """
    updated = dict(account_data)
    updated["old_phone"] = account_data.get("phone", "")
    updated["phone"] = new_phone
    updated["app_id"] = DEFAULT_APP_ID
    updated["app_hash"] = DEFAULT_APP_HASH
    updated["changed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if country_code:
        updated["country"] = country_code

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(updated, f, ensure_ascii=False, indent=2)


def pack_updated_accounts(success_session_files, output_zip):
    """
    将更新后的 session 文件和 JSON 文件打包为 updated_accounts.zip
    """
    with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for session_path, json_path in success_session_files:
            # 只用文件名（不含路径）放入 zip
            if session_path.exists():
                zf.write(session_path, session_path.name)
            if json_path.exists():
                zf.write(json_path, json_path.name)
    logger.info(f"✅ 已打包更新后的账号文件: {output_zip}")


# ============================================================
# 主流程
# ============================================================

async def main():
    """主函数：批量换绑所有账号"""

    print(Fore.CYAN + Style.BRIGHT + "=" * 60)
    print(Fore.CYAN + Style.BRIGHT + "  Telegram 批量换绑脚本 v1.0.0")
    print(Fore.CYAN + Style.BRIGHT + "=" * 60)
    print()

    # 确保目录存在
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    # 加载配置
    config = load_config()
    logger.info("✅ 配置加载完成")

    # 解压 accounts.zip
    extract_accounts_zip()

    # 配对 session + json 文件
    paired_accounts = pair_session_json_files()
    if not paired_accounts:
        logger.error("❌ 没有找到有效的账号配对，退出")
        sys.exit(1)

    # 读取新号码列表
    new_phones = load_new_phones()
    if not new_phones:
        logger.error("❌ 新号码列表为空，退出")
        sys.exit(1)

    # 检查数量是否匹配
    if len(paired_accounts) > len(new_phones):
        logger.warning(
            f"⚠️ 账号数量({len(paired_accounts)})多于新号码数量({len(new_phones)})，"
            f"只处理前 {len(new_phones)} 个账号"
        )
        paired_accounts = paired_accounts[: len(new_phones)]
    elif len(new_phones) > len(paired_accounts):
        logger.warning(
            f"⚠️ 新号码数量({len(new_phones)})多于账号数量({len(paired_accounts)})，"
            f"多余的号码不会被使用"
        )
        new_phones = new_phones[: len(paired_accounts)]

    total = len(paired_accounts)
    logger.info(f"📊 共处理 {total} 个账号")

    # 结果记录
    successes = []        # 成功换绑的记录
    failures = []         # 失败的记录
    success_file_pairs = []    # 成功账号的 (session_path, json_path) 文件对

    # 获取等待时间配置
    intervals = config.get("intervals", {})
    wait_min = intervals.get("between_accounts_min", 30)
    wait_max = intervals.get("between_accounts_max", 60)

    # 逐个处理账号
    for index, ((session_path, json_path, account_data), (new_phone, sms_api_url)) in enumerate(
        zip(paired_accounts, new_phones), start=1
    ):
        print()
        print(Fore.CYAN + "=" * 60)
        print(
            Fore.CYAN + Style.BRIGHT
            + f"  开始处理账号 [{index}/{total}]: +{account_data.get('phone', '?')}"
        )
        print(Fore.CYAN + "=" * 60)

        result = await change_phone_number(
            session_path, account_data, new_phone, sms_api_url, config
        )

        if result["success"]:
            # 记录成功
            result["sms_api_url"] = sms_api_url
            successes.append(result)
            success_file_pairs.append((session_path, json_path))

            # 更新 JSON 文件（新号码、默认API等）
            update_account_json(
                json_path, account_data, new_phone, result.get("country")
            )
            logger.info(f"✅ JSON 文件已更新: {json_path.name}")

        else:
            # 记录失败
            failures.append(
                {
                    "new_phone": new_phone,
                    "sms_api_url": sms_api_url,
                    "error": result.get("error", "未知错误"),
                }
            )

        # 如果不是最后一个账号，等待一段时间（避免触发 TG 风控）
        if index < total:
            wait_time = random.randint(wait_min, wait_max)
            logger.info(f"⏳ 等待 {wait_time} 秒后处理下一个账号...")
            await asyncio.sleep(wait_time)

    # ============================================================
    # 生成输出文件
    # ============================================================

    print()
    print(Fore.CYAN + "=" * 60)
    print(Fore.CYAN + Style.BRIGHT + "  生成输出文件")
    print(Fore.CYAN + "=" * 60)

    success_result_file = OUTPUT_DIR / "success_result.txt"
    failed_phones_file = OUTPUT_DIR / "failed_phones.txt"
    success_accounts_file = OUTPUT_DIR / "success_accounts.json"
    updated_zip_file = OUTPUT_DIR / "updated_accounts.zip"

    # 保存成功结果
    if successes:
        save_success_result(successes, success_result_file)
        save_success_accounts_json(successes, success_accounts_file)
        pack_updated_accounts(success_file_pairs, updated_zip_file)
    else:
        logger.warning("⚠️ 没有成功换绑的账号")

    # 保存失败号码
    if failures:
        save_failed_phones(failures, failed_phones_file)

    # 最终统计
    print()
    print(Fore.CYAN + "=" * 60)
    print(Fore.CYAN + Style.BRIGHT + "  📊 执行完成统计")
    print(Fore.CYAN + "=" * 60)
    print(Fore.GREEN + f"  ✅ 成功换绑: {len(successes)} 个")
    print(Fore.RED + f"  ❌ 失败: {len(failures)} 个")
    print(Fore.WHITE + f"  📁 结果目录: {OUTPUT_DIR}")
    if successes:
        print(Fore.WHITE + f"  📄 成功结果: {success_result_file}")
        print(Fore.WHITE + f"  📦 更新后的账号包: {updated_zip_file}")
    if failures:
        print(Fore.WHITE + f"  📄 失败号码: {failed_phones_file}")
    print(Fore.CYAN + "=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
