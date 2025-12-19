"""
测试日志获取功能
用法: python test_fetch.py <event_id>
示例: python test_fetch.py DJC-CF-1211212348-8RJKIC-529-425718
"""

import os
import sys
import json
import requests
from dotenv import load_dotenv

load_dotenv()

LOG_SERVICE_URL = "http://help.ied.com/logplat/curl2.php"
AUTH_COOKIE = os.getenv("LOG_SERVICE_COOKIE", "")


def fetch_error_log(event_id: str) -> str:
    """根据 EventID 获取日志"""
    # 解析平台名
    plat_name = event_id.split("-")[0] if "-" in event_id else "AMS"
    
    params = {
        "url": f"plat_name={plat_name}&serial_num={event_id}&source_charset=utf8",
        "set": "",
        "referer": "http://help.ied.com/helpv2/html/showInfo_v2.html"
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Referer": "http://help.ied.com/helpv2/html/showInfo_v2.html"
    }
    
    if AUTH_COOKIE:
        headers["Cookie"] = AUTH_COOKIE
        print(f"✅ 使用 Cookie 认证 (长度: {len(AUTH_COOKIE)})")
    else:
        print("⚠️  未设置 LOG_SERVICE_COOKIE，可能需要登录")
    
    print(f"📡 请求 URL: {LOG_SERVICE_URL}")
    print(f"   EventID: {event_id}")
    print(f"   Platform: {plat_name}")
    print("-" * 60)
    
    try:
        response = requests.get(LOG_SERVICE_URL, params=params, headers=headers, timeout=30)
        print(f"状态码: {response.status_code}")
        print("-" * 60)
        
        content = response.text
        
        # 检查登录状态
        if "未找到登录" in content or '"ret":-10' in content:
            print("❌ 需要登录认证！")
            print("请在 .env 文件中设置 LOG_SERVICE_COOKIE")
            print("\n获取方式：")
            print("1. 浏览器打开日志页面并登录")
            print("2. F12 -> Network -> 找到 curl2.php 请求")
            print("3. 复制 Cookie 值到 .env")
            return content
        
        # 解析 JavaScript 变量
        if content.startswith("var log_result="):
            json_str = content[len("var log_result="):]
            try:
                log_data = json.loads(json_str)
                print("✅ 成功解析日志数据")
                print(f"返回码: {log_data.get('ret', 'N/A')}")
                print(f"消息: {log_data.get('msg', 'N/A')}")
                
                if "result" in log_data:
                    print(f"日志条数: {len(log_data['result'])}")
                    print("-" * 60)
                    print("日志内容预览:")
                    for i, item in enumerate(log_data["result"][:3]):  # 只显示前3条
                        print(f"\n--- 第 {i+1} 条 ---")
                        if "content" in item:
                            print(item["content"][:500])
                        else:
                            print(json.dumps(item, ensure_ascii=False, indent=2)[:500])
                
                return json.dumps(log_data, ensure_ascii=False, indent=2)
            except json.JSONDecodeError as e:
                print(f"JSON 解析失败: {e}")
                return content
        
        print("响应内容:")
        print(content[:2000])
        return content
        
    except requests.exceptions.RequestException as e:
        print(f"❌ 请求失败: {e}")
        return ""


if __name__ == "__main__":
    if len(sys.argv) < 2:
        event_id = "DJC-CF-1211212348-8RJKIC-529-425718"
        print(f"使用默认 EventID: {event_id}\n")
    else:
        event_id = sys.argv[1]
    
    fetch_error_log(event_id)
