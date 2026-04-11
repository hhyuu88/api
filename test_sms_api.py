#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
接码平台测试工具
用于快速测试接码 API 是否正常工作

用法:
  # 测试单个 API URL
  python test_sms_api.py "https://smsapis.com/api/get_sms?key=xxx"

  # 批量测试（读取 new_phones.txt 中所有 API）
  python test_sms_api.py input/new_phones.txt

  # 不传参数则使用默认的 input/new_phones.txt
  python test_sms_api.py
"""

import re
import sys
import time
from pathlib import Path

import requests
from colorama import Fore, Style, init

init(autoreset=True)


def mask_url_key(url: str) -> str:
    """掩码处理 URL 中的 key= 参数，避免打印时泄露 API 密钥"""
    return re.sub(r"(key=)[^&\s]+", r"\1***", url)


def test_single_api(sms_api_url: str) -> dict:
    """
    测试单个接码 API

    返回:
        dict: {
            "url_masked": str,
            "is_accessible": bool,
            "response_time": float,
            "status_code": int | None,
            "response_text": str,
            "health": "健康" | "正常" | "慢" | "失败",
            "error": str | None,
        }
    """
    result = {
        "url_masked": mask_url_key(sms_api_url),
        "is_accessible": False,
        "response_time": 0.0,
        "status_code": None,
        "response_text": "",
        "health": "失败",
        "error": None,
    }

    print(f"\n{'=' * 60}")
    print(f"测试 API: {result['url_masked']}")
    print(f"{'=' * 60}")

    try:
        start = time.time()
        response = requests.get(sms_api_url, timeout=10)
        elapsed = round(time.time() - start, 2)

        result["is_accessible"] = True
        result["response_time"] = elapsed
        result["status_code"] = response.status_code
        result["response_text"] = response.text.strip()[:300]

        # 评估健康状态
        if elapsed < 1:
            health = "健康 ✅"
            result["health"] = "健康"
        elif elapsed < 3:
            health = "正常 ⚠️"
            result["health"] = "正常"
        else:
            health = "慢 ❌"
            result["health"] = "慢"

        print(f"  {'✅' if result['is_accessible'] else '❌'} 可访问: {'是' if result['is_accessible'] else '否'}")
        print(f"  ⏱️  响应时间: {elapsed:.2f} 秒")
        print(f"  📋 HTTP 状态码: {response.status_code}")
        print(f"  📄 响应内容: {result['response_text']}")
        print(f"  🏥 健康状态: {health}")

    except requests.exceptions.ConnectionError as e:
        result["error"] = f"连接失败: {type(e).__name__}"
        print(f"  ❌ 可访问: 否")
        print(f"  ❌ 错误类型: 连接失败")
        print(f"  ❌ 详情: {result['error']}")
    except requests.exceptions.Timeout:
        result["error"] = "请求超时 (>10s)"
        print(f"  ❌ 可访问: 否")
        print(f"  ❌ 错误类型: 超时")
        result["health"] = "慢"
    except Exception as e:
        result["error"] = str(e)
        print(f"  ❌ 可访问: 否")
        print(f"  ❌ 错误: {e}")

    return result


def test_batch_from_file(phones_file: str) -> list:
    """
    读取 new_phones.txt 并批量测试所有接码 API

    文件格式：
        +8617800001234|https://smsapis.com/api/get_sms?key=xxx
        # 注释行以 # 开头，会被跳过
    """
    phones_path = Path(phones_file)
    if not phones_path.exists():
        print(f"❌ 文件不存在: {phones_file}")
        sys.exit(1)

    # 解析文件，提取唯一 API URL
    api_urls = []
    seen = set()
    with open(phones_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("|", 1)
            if len(parts) == 2:
                url = parts[1].strip()
                if url not in seen:
                    api_urls.append(url)
                    seen.add(url)
            else:
                print(f"⚠️ 格式错误，跳过: {line}")

    if not api_urls:
        print("❌ 未找到任何接码 API URL")
        sys.exit(1)

    print(f"\n🔍 共找到 {len(api_urls)} 个唯一接码 API，开始测试...")
    results = []
    for url in api_urls:
        r = test_single_api(url)
        results.append(r)

    return results


def print_summary(results: list):
    """打印测试汇总报告"""
    healthy = [r for r in results if r["health"] == "健康"]
    normal = [r for r in results if r["health"] == "正常"]
    slow = [r for r in results if r["health"] == "慢"]
    failed = [r for r in results if r["health"] == "失败"]

    print(f"\n{'━' * 44}")
    print(Fore.CYAN + Style.BRIGHT + "  API 测试报告")
    print(f"{'━' * 44}")
    print(Fore.GREEN + f"  ✅ 健康 (<1s):  {len(healthy)} 个")
    print(Fore.YELLOW + f"  ⚠️  正常 (1-3s): {len(normal)} 个")
    print(Fore.YELLOW + f"  🐢 慢 (>3s):   {len(slow)} 个")
    print(Fore.RED + f"  ❌ 失败:        {len(failed)} 个")
    print(f"{'━' * 44}")
    print(Fore.WHITE + f"  共测试: {len(results)} 个 API")

    if failed:
        print()
        print(Fore.RED + "  ❌ 失败的 API:")
        for r in failed:
            print(Fore.RED + f"    {r['url_masked']}  →  {r.get('error', '未知错误')}")

    if slow:
        print()
        print(Fore.YELLOW + "  🐢 响应慢的 API（可能导致超时）:")
        for r in slow:
            print(Fore.YELLOW + f"    {r['url_masked']}  →  {r['response_time']:.2f}s")

    print(f"{'━' * 44}\n")


def main():
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        # 判断是 URL 还是文件路径
        if arg.startswith("http://") or arg.startswith("https://"):
            # 测试单个 API
            result = test_single_api(arg)
            print_summary([result])
        else:
            # 批量测试文件中的 API
            results = test_batch_from_file(arg)
            print_summary(results)
    else:
        # 默认读取 input/new_phones.txt
        default_file = Path(__file__).parent / "input" / "new_phones.txt"
        if default_file.exists():
            results = test_batch_from_file(str(default_file))
            print_summary(results)
        else:
            print("用法:")
            print("  python test_sms_api.py <API_URL>")
            print("  python test_sms_api.py <phones_file>")
            print("  python test_sms_api.py          # 默认使用 input/new_phones.txt")
            sys.exit(0)


if __name__ == "__main__":
    main()
