"""
使用 browser-use 的错误日志分析 Agent

通过操作真实浏览器来获取和分析日志：
1. 打开浏览器，访问日志页面
2. AI 自动处理登录鉴权（点击确认按钮）
3. 等待日志加载，使用 AI 视觉能力分析页面内容
4. 生成结构化分析报告
"""

import asyncio
import os
import sys
import json
from typing import Optional
from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Browser-Use (使用 browser-use 自带的 LLM 类)
from browser_use import Agent, Browser
from browser_use.llm.openai.chat import ChatOpenAI

load_dotenv()


# ============ 配置 ============
LOG_PAGE_URL = "http://help.ied.com/helpv2/html/showInfo_v2.html"


# ============ 数据模型 ============
class LogAnalysisResult(BaseModel):
    """日志分析结果"""
    event_id: str = Field(description="事件ID/流水号")
    error_code: str = Field(description="从日志中提取的错误码")
    error_summary: str = Field(description="错误摘要：什么模块、什么错误、影响什么功能")
    affected_module: str = Field(description="受影响的模块名")
    user_info: Optional[str] = Field(default=None, description="用户信息（QQ号等）")
    risk_level: str = Field(description="风险等级: low/medium/high/critical")
    recommendation: str = Field(description="处理建议")
    raw_error_logs: Optional[str] = Field(default=None, description="原始错误日志片段")


# ============ Browser-Use Agent ============
class LogAnalyzerBrowserAgent:
    """
    使用 browser-use 的日志分析 Agent
    
    工作流程：
    1. 启动浏览器，导航到日志页面
    2. AI 自动处理登录鉴权（点击确认按钮）
    3. 等待日志加载完成
    4. 使用 AI 视觉分析页面内容
    5. 提取错误信息，生成报告
    """
    
    def __init__(self, debug: bool = True):
        self.debug = debug
        
        model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        
        # 初始化 LLM (使用 browser-use 自带的 ChatOpenAI)
        self.llm = ChatOpenAI(
            model=model_name,
            base_url=os.getenv("OPENAI_BASE_URL"),
            api_key=os.getenv("OPENAI_API_KEY"),
            temperature=0.3
        )
        
        # 初始化 Browser-Use 的 Browser
        # browser-use 0.11.x 直接传参数，不需要 BrowserConfig
        self.browser = Browser(
            headless=False,  # 显示浏览器窗口，便于观察
            disable_security=True,  # 允许访问 http 页面
        )
        
        self._log(f"LLM 初始化: {model_name}")
    
    def _log(self, message: str):
        """打印调试日志"""
        if self.debug:
            print(f"  [DEBUG] {message}")
    
    async def analyze(self, event_id: str) -> LogAnalysisResult:
        """
        分析指定 EventID 的错误日志
        
        Args:
            event_id: 错误事件ID，如 "DJC-CF-1211212348-8RJKIC-529-425718"
        
        Returns:
            LogAnalysisResult: 结构化的分析结果
        """
        print(f"\n{'='*60}")
        print(f"🔍 开始分析 EventID: {event_id}")
        print(f"{'='*60}")
        
        # 构建日志页面 URL
        page_url = f"{LOG_PAGE_URL}?p={event_id}"
        self._log(f"目标页面: {page_url}")
        
        try:
            # 创建 Agent 执行完整任务
            # browser-use 的 Agent 会自动：
            # 1. 导航到页面
            # 2. 处理登录弹窗（点击确认按钮）
            # 3. 等待页面加载
            # 4. 分析页面内容
            
            task_prompt = f"""
你是一个专业的错误日志分析专家。请完成以下任务：

1. 导航到日志页面: {page_url}

2. 如果出现登录或鉴权弹窗/页面，点击"确认"、"登录"或类似的按钮完成鉴权

3. 等待页面加载完成，确保日志内容已显示

4. 仔细阅读页面上的日志内容，分析错误信息

日志格式说明：
- 格式: [F:IP地址|QQ:QQ号]日期 时间|日志级别||[源文件:行号][流水号][模块名][OPENID:]日志内容
- 日志级别：INF(信息)、ER(错误)、WRN(警告)
- 重点关注 ER（ERROR）级别的日志

5. 分析完成后，请以 JSON 格式输出分析结果：

```json
{{
    "event_id": "{event_id}",
    "error_code": "从日志中提取的错误码（如 -6712）",
    "error_summary": "一句话概括：什么模块、什么错误、影响什么功能",
    "affected_module": "受影响的模块名（如 app.coupon.available）",
    "user_info": "用户信息（如QQ号）",
    "risk_level": "low/medium/high/critical",
    "recommendation": "具体可执行的处理建议",
    "raw_error_logs": "关键错误日志片段（前200字符）"
}}
```

风险等级判断：
- critical: 支付相关错误、大面积服务不可用
- high: 核心功能（如优惠券、登录）失败  
- medium: 非核心功能异常、偶发错误
- low: 可忽略的警告、已自动恢复
"""
            
            print("\n📌 启动 Browser-Use Agent...")
            print("   - AI 将自动打开浏览器")
            print("   - 处理登录鉴权（如有）")
            print("   - 分析日志内容")
            
            agent = Agent(
                task=task_prompt,
                llm=self.llm,
                browser=self.browser,
                use_vision=True  # 启用视觉能力，AI 可以"看到"页面
            )
            
            # 运行 Agent
            result = await agent.run()
            
            self._log(f"Agent 执行完成")
            self._log(f"Agent 输出: {result}")
            
            # 解析 Agent 的输出
            return self._parse_agent_result(result, event_id)
            
        except Exception as e:
            self._log(f"Agent 执行失败: {e}")
            raise
    
    def _parse_agent_result(self, result, event_id: str) -> LogAnalysisResult:
        """解析 Agent 的输出结果"""
        try:
            # Agent 返回的结果可能是字符串或对象
            content = str(result)
            
            # 查找 JSON 块
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                json_str = content.split("```")[1].split("```")[0]
            elif "{" in content and "}" in content:
                # 尝试提取 JSON 对象
                start = content.find("{")
                end = content.rfind("}") + 1
                json_str = content[start:end]
            else:
                json_str = content
            
            data = json.loads(json_str.strip())
            return LogAnalysisResult(**data)
            
        except Exception as e:
            self._log(f"结果解析失败: {e}")
            # 返回默认结果
            return LogAnalysisResult(
                event_id=event_id,
                error_code="PARSE_ERROR",
                error_summary=str(result)[:200] if result else "无法解析 Agent 输出",
                affected_module="未知",
                risk_level="medium",
                recommendation="请检查日志页面是否正常加载，或手动查看浏览器窗口"
            )


# ============ 主函数 ============
async def main():
    """主函数"""
    print("""
╔══════════════════════════════════════════════════════════════╗
║       Browser-Use 日志分析 Agent                              ║
║                                                              ║
║  工作原理：                                                   ║
║  1. 启动真实浏览器，访问日志页面                               ║
║  2. AI 自动处理登录鉴权（点击确认按钮）                        ║
║  3. 使用 AI 视觉能力分析页面上的日志内容                       ║
║  4. 生成结构化分析报告                                        ║
╚══════════════════════════════════════════════════════════════╝
""")
    
    # 检查配置
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ 错误: 请在 .env 文件中配置 OPENAI_API_KEY")
        return
    
    # 创建 Agent
    agent = LogAnalyzerBrowserAgent(debug=True)
    
    # 默认测试 EventID
    test_event_id = "DJC-CF-1211212348-8RJKIC-529-425718"
    
    # 允许从命令行参数传入 EventID
    if len(sys.argv) > 1:
        test_event_id = sys.argv[1]
    
    try:
        result = await agent.analyze(test_event_id)
        
        print("\n" + "=" * 60)
        print("📊 分析报告:")
        print("=" * 60)
        print(f"Event ID:      {result.event_id}")
        print(f"错误码:        {result.error_code}")
        print(f"错误摘要:      {result.error_summary}")
        print(f"受影响模块:    {result.affected_module}")
        print(f"用户信息:      {result.user_info or '未知'}")
        print(f"风险等级:      {result.risk_level}")
        print(f"处理建议:      {result.recommendation}")
        if result.raw_error_logs:
            print(f"\n原始错误日志片段:")
            print(f"  {result.raw_error_logs[:300]}...")
        
    except Exception as e:
        print(f"❌ 分析失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
