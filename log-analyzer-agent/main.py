"""
错误日志分析 Agent
- 根据 EventID 获取错误日志详情
- 解析错误码，查询服务器稳定状况
- 生成结构化分析报告
"""

import os
import json
import asyncio
import requests
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

# ============ 配置 ============
LOG_SERVICE_URL = "http://help.ied.com/logplat/curl2.php"

# 认证 Cookie（从浏览器复制）
# 在浏览器登录后，F12 -> Network -> 找到 curl2.php 请求 -> 复制 Cookie
AUTH_COOKIE = os.getenv("LOG_SERVICE_COOKIE", "")


# ============ 数据模型 ============
class LogDetail(BaseModel):
    """错误日志详情"""
    event_id: str
    error_code: str
    error_message: str
    timestamp: str
    stack_trace: str
    service_name: str


class ServerStatus(BaseModel):
    """服务器状态"""
    server_name: str
    status: str  # healthy / degraded / down
    error_rate: float
    last_incident: Optional[str]
    today_incidents: int


class AnalysisReport(BaseModel):
    """分析报告"""
    event_id: str
    error_code: str
    error_summary: str
    server_status: str
    risk_level: str  # low / medium / high / critical
    recommendation: str


# ============ 工具函数 ============
def fetch_error_log(event_id: str) -> str:
    """
    根据 EventID 从日志服务获取原始错误日志
    
    EventID 格式: DJC-CF-1211212348-8RJKIC-529-425718
    - 前缀(如 DJC)表示平台名
    """
    # 解析平台名（取第一个 - 之前的部分）
    plat_name = event_id.split("-")[0] if "-" in event_id else "AMS"
    
    # 构建请求参数
    params = {
        "url": f"plat_name={plat_name}&serial_num={event_id}&source_charset=utf8",
        "set": "",
        "referer": "http://help.ied.com/helpv2/html/showInfo_v2.html"
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Referer": "http://help.ied.com/helpv2/html/showInfo_v2.html"
    }
    
    # 添加认证 Cookie
    if AUTH_COOKIE:
        headers["Cookie"] = AUTH_COOKIE
    
    try:
        print(f"  📡 请求日志服务: {LOG_SERVICE_URL}")
        print(f"     EventID: {event_id}, Platform: {plat_name}")
        
        response = requests.get(LOG_SERVICE_URL, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        
        content = response.text
        
        # 检查是否需要登录
        if "未找到登录" in content or "urlJump" in content:
            return f"[ERROR] 需要登录认证。请在 .env 文件中设置 LOG_SERVICE_COOKIE\n原始响应: {content[:500]}"
        
        # 解析返回的 JavaScript 变量 (var log_result={...})
        if content.startswith("var log_result="):
            json_str = content[len("var log_result="):]
            try:
                log_data = json.loads(json_str)
                # 提取实际日志内容
                if "result" in log_data and isinstance(log_data["result"], list):
                    logs = []
                    for item in log_data["result"]:
                        if "content" in item:
                            logs.append(item["content"])
                        elif "jsonHeader" in item:
                            logs.append(json.dumps(item, ensure_ascii=False))
                    return "\n".join(logs) if logs else json.dumps(log_data, ensure_ascii=False, indent=2)
                return json.dumps(log_data, ensure_ascii=False, indent=2)
            except json.JSONDecodeError:
                return content
        
        return content
        
    except requests.exceptions.RequestException as e:
        return f"[ERROR] 获取日志失败: {str(e)}"


def check_server_status(service_name: str) -> str:
    """
    根据服务名查询服务器今日稳定状况
    
    TODO: 替换为真实 API 调用
    示例: response = requests.get(f"{MONITOR_SERVICE_URL}/api/status/{service_name}")
    返回的是监控系统的原始文本报告
    """
    # 模拟监控系统返回的文本报告
    mock_status = {
        "order-service": f"""
=== Service Health Report: order-service ===
Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

[Infrastructure]
- Primary DB: db-primary-01 (MySQL 8.0)
- Replica DB: db-replica-01, db-replica-02
- Cache: redis-cluster-01

[Current Status: DEGRADED]
- Service uptime: 99.2% (last 24h)
- Current error rate: 2.5%
- Avg response time: 450ms (normal: 120ms)
- Active connections: 1,247

[Today's Incidents]
- 09:15 - Database connection pool exhaustion (resolved)
- 10:30 - High latency detected, auto-scaling triggered
- 10:45 - Connection pool size increased from 50 to 100
Total incidents today: 15

[Resource Usage]
- CPU: 78% (warning threshold: 80%)
- Memory: 6.2GB / 8GB (77.5%)
- DB Connections: 95/100 (95% - CRITICAL)

[Recommendations]
- Consider increasing connection pool size
- Review slow queries in the last hour
- Monitor for potential memory leak
""",
        "auth-service": f"""
=== Service Health Report: auth-service ===
Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

[Infrastructure]
- Auth servers: auth-01, auth-02, auth-03 (load balanced)
- Token store: Redis Sentinel cluster

[Current Status: HEALTHY]
- Service uptime: 99.99% (last 24h)
- Current error rate: 0.1%
- Avg response time: 45ms
- Active sessions: 23,456

[Today's Incidents]
- 08:30 - Routine certificate rotation (planned)
- 09:15 - 2 expired token rejections (normal behavior)
Total incidents today: 2

[Resource Usage]
- CPU: 25%
- Memory: 2.1GB / 4GB (52.5%)
- Redis connections: 45/200 (22.5%)

[Notes]
- All systems operating normally
- No action required
""",
        "payment-service": f"""
=== Service Health Report: payment-service ===
Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

[Infrastructure]
- Payment gateway: Stripe API
- Fallback gateway: PayPal API (inactive)
- Transaction DB: payment-db-01

[Current Status: DOWN - CRITICAL]
- Service uptime: 54.8% (last 24h)
- Current error rate: 45.2%
- Avg response time: TIMEOUT
- Failed transactions: 1,247 (last hour)

[Today's Incidents]
- 12:00 - Stripe API intermittent failures started
- 13:30 - Error rate exceeded 10%, alerts triggered
- 14:00 - Circuit breaker activated
- 14:15 - Stripe status page confirms outage
- 14:22 - All payment requests failing
Total incidents today: 128

[External Dependencies]
- Stripe API Status: MAJOR OUTAGE (https://status.stripe.com)
- Estimated recovery: Unknown

[URGENT ACTIONS REQUIRED]
1. Consider activating PayPal fallback gateway
2. Notify customers of payment delays
3. Queue failed transactions for retry
4. Contact Stripe support for ETA
"""
    }
    
    return mock_status.get(service_name, f"""
=== Service Health Report: {service_name} ===
Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

[Status: UNKNOWN]
Service not found in monitoring system.
Please verify the service name and try again.
""")


# ============ 工具定义（OpenAI Function Calling 格式） ============
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "fetch_error_log",
            "description": "根据 EventID 获取原始错误日志文本。返回的是非结构化的日志文本，包含时间戳、错误堆栈、上下文信息等，需要自行解析提取关键信息。",
            "parameters": {
                "type": "object",
                "properties": {
                    "event_id": {
                        "type": "string",
                        "description": "错误事件的唯一标识符，如 EVT-2025121800042"
                    }
                },
                "required": ["event_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_server_status",
            "description": "根据服务名查询该服务今日的稳定状况报告。返回监控系统的文本报告，包含服务状态、错误率、今日事故、资源使用等信息。",
            "parameters": {
                "type": "object",
                "properties": {
                    "service_name": {
                        "type": "string",
                        "description": "服务名称，从日志中解析得到，如 order-service, auth-service, payment-service"
                    }
                },
                "required": ["service_name"]
            }
        }
    }
]

# 工具执行映射
TOOL_FUNCTIONS = {
    "fetch_error_log": fetch_error_log,
    "check_server_status": check_server_status
}


# ============ Agent 核心逻辑 ============
class LogAnalyzerAgent:
    """错误日志分析 Agent"""
    
    def __init__(self, debug: bool = True):
        self.client = AsyncOpenAI(
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            api_key=os.getenv("OPENAI_API_KEY")
        )
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.debug = debug  # 是否打印调试日志
        self.system_prompt = """你是一个专业的错误日志分析专家，专门分析道聚城(DJC)等腾讯游戏服务的日志。

你的工作流程：
1. 从用户输入中识别 EventID（格式如 DJC-CF-1211212348-8RJKIC-529-425718、AMS-H2-xxx 等）
2. 调用 fetch_error_log 获取原始日志文本
3. **仔细解析日志内容**，从日志中提取关键信息
4. 综合分析，生成报告

EventID 识别规则：
- 通常以平台名开头：DJC-、AMS-、LotteryV31- 等
- 包含多个用 - 分隔的部分
- 用户可能说"我遇到问题了，流水号是xxx"或直接给出ID

日志格式说明：
```
[F:IP地址|QQ:QQ号]日期 时间|日志级别||[源文件:行号][流水号][模块名][OPENID:]日志内容
```

日志级别：
- INF = INFO（信息）
- ER = ERROR（错误）  ← 重点关注
- WRN = WARN（警告）

解析要点：
1. 找出所有 ER（ERROR）级别的日志行
2. 提取错误码（如 -6712）和错误信息
3. 识别模块名（如 [app.coupon.available]）
4. 分析调用链路和失败原因
5. 提取关键上下文（QQ号、订单号、请求参数等）

常见错误码含义：
- 负数错误码通常表示后端服务返回的业务错误
- "系统繁忙" 通常表示后端服务过载或超时

输出要求：
最终输出 JSON 格式的分析报告：
```json
{
    "event_id": "事件ID",
    "error_code": "从日志中提取的错误码，如 -6712",
    "error_summary": "一句话概括：什么模块、什么错误、影响什么功能",
    "server_status": "根据日志推断的服务状态",
    "risk_level": "low/medium/high/critical",
    "recommendation": "具体可执行的处理建议"
}
```

风险等级判断：
- critical: 支付相关错误、大面积服务不可用
- high: 核心功能（如优惠券、登录）失败
- medium: 非核心功能异常、偶发错误
- low: 可忽略的警告、已自动恢复
"""
    
    def _log(self, message: str):
        """打印调试日志"""
        if self.debug:
            print(f"  [DEBUG] {message}")
    
    async def execute_tool(self, tool_name: str, arguments: dict) -> str:
        """执行工具调用，返回字符串结果"""
        if tool_name in TOOL_FUNCTIONS:
            result = TOOL_FUNCTIONS[tool_name](**arguments)
            # 工具返回的已经是字符串，直接返回
            if isinstance(result, str):
                return result
            return json.dumps(result, ensure_ascii=False, indent=2)
        return f"Error: Unknown tool '{tool_name}'"
    
    async def analyze(self, user_input: str) -> AnalysisReport:
        """
        分析错误日志
        
        Args:
            user_input: 用户输入，可以是纯 EventID，也可以是包含 EventID 的自然语言
                       例如: "我遇到问题了，流水号 DJC-CF-1211212348-8RJKIC-529-425718"
        """
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_input}
        ]
        
        self._log(f"用户输入: {user_input}")
        self._log(f"使用模型: {self.model}")
        
        # Agent 循环：持续调用工具直到完成分析
        max_iterations = 10
        for iteration in range(max_iterations):
            self._log(f"--- 迭代 {iteration + 1} ---")
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=TOOLS,
                tool_choice="auto"
            )
            
            assistant_message = response.choices[0].message
            
            # 打印模型输出
            self._log(f"模型响应:")
            if assistant_message.content:
                self._log(f"  内容: {assistant_message.content[:500]}...")
            if assistant_message.tool_calls:
                self._log(f"  工具调用: {len(assistant_message.tool_calls)} 个")
            
            messages.append(assistant_message.model_dump())
            
            # 检查是否有工具调用
            if assistant_message.tool_calls:
                for tool_call in assistant_message.tool_calls:
                    tool_name = tool_call.function.name
                    arguments = json.loads(tool_call.function.arguments)
                    
                    print(f"  🔧 调用工具: {tool_name}")
                    print(f"     参数: {arguments}")
                    
                    result = await self.execute_tool(tool_name, arguments)
                    
                    # 打印工具返回结果（截断显示）
                    self._log(f"  工具返回 ({len(result)} 字符):")
                    self._log(f"    {result[:300]}...")
                    
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result
                    })
            else:
                # 没有工具调用，说明分析完成
                content = assistant_message.content or ""
                self._log(f"分析完成，模型最终输出:")
                self._log(f"{content}")
                
                # 尝试从回复中提取 JSON
                try:
                    # 查找 JSON 块
                    if "```json" in content:
                        json_str = content.split("```json")[1].split("```")[0]
                    elif "```" in content:
                        json_str = content.split("```")[1].split("```")[0]
                    else:
                        json_str = content
                    
                    report_data = json.loads(json_str.strip())
                    return AnalysisReport(**report_data)
                except (json.JSONDecodeError, IndexError, KeyError) as e:
                    self._log(f"JSON 解析失败: {e}")
                    # 如果解析失败，返回原始内容作为摘要
                    return AnalysisReport(
                        event_id="UNKNOWN",
                        error_code="PARSE_ERROR",
                        error_summary=content[:200] if content else "无法解析模型输出",
                        server_status="未知",
                        risk_level="medium",
                        recommendation="请检查 Agent 输出格式"
                    )
        
        raise RuntimeError("Agent 达到最大迭代次数，未能完成分析")


# ============ 主函数 ============
async def main():
    """主函数"""
    agent = LogAnalyzerAgent(debug=True)  # 开启调试日志
    
    # 测试不同类型的用户输入
    test_inputs = [
        # 测试1: 模糊指令，包含 EventID
        "我遇到问题了，流水号是 DJC-CF-1211212348-8RJKIC-529-425718，帮我看看",
        
        # 测试2: 直接给 EventID（可选，取消注释测试）
        # "DJC-CF-1211212348-8RJKIC-529-425718",
    ]
    
    for user_input in test_inputs:
        print("\n" + "=" * 60)
        print(f"🔍 用户输入: {user_input}")
        print("=" * 60)
        
        try:
            report = await agent.analyze(user_input)
            
            print("\n" + "=" * 60)
            print("📊 分析报告:")
            print("=" * 60)
            print(f"Event ID:    {report.event_id}")
            print(f"错误码:      {report.error_code}")
            print(f"错误摘要:    {report.error_summary}")
            print(f"服务器状态:  {report.server_status}")
            print(f"风险等级:    {report.risk_level}")
            print(f"处理建议:    {report.recommendation}")
            
        except Exception as e:
            print(f"❌ 分析失败: {e}")
            import traceback
            traceback.print_exc()
        
        print()


if __name__ == "__main__":
    asyncio.run(main())
