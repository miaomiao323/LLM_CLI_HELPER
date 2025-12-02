#!/usr/bin/env python3
# cli_helper.py
import os
import click
import requests
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text

# 加载 .env 文件中的环境变量
load_dotenv()

# 初始化 rich console
console = Console()

# 从环境变量中获取 API 密钥
# 建议在 .env 文件中使用 API_KEY
API_KEY = os.getenv("API_KEY") 

if not API_KEY:
    console.print(Panel("[bold red]错误：[/bold red]未找到 API 密钥。\n请在项目根目录下创建 '.env' 文件并设置 SILICONFLOW_API_KEY='你的API密钥'。",
                      title="[bold yellow]配置警告[/bold yellow]", border_style="red"), style="red")
    exit(1)

# SiliconFlow API 地址
API_BASE_URL = "https://api.siliconflow.cn/v1/chat/completions"
# 指定模型名称
MODEL_NAME = "Qwen/Qwen2.5-7B-Instruct"

def get_llm_response(prompt: str) -> dict:
    """
    向大型语言模型发送请求并获取响应。
    返回一个字典，包含 'code' (代码) 和 'explanation' (解释)。
    """
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    # 系统提示词：引导 LLM 输出特定格式
    system_prompt = (
        "你是一个专业的命令行(CLI)助手。用户会告诉你他们想做什么，你需要提供相应的 Linux/macOS 命令行指令。\n"
        "请严格遵守以下规则：\n"
        "1. 如果用户意图不明确，请给出最常用的命令。\n"
        "2. 如果操作有危险（如 rm -rf），请在解释中明确警告。\n"
        "3. 输出格式必须严格如下，不要包含其他无关的寒暄：\n"
        "```bash\n"
        "<此处写具体的命令行指令>\n"
        "```\n"
        "说明：<此处写简短的中文解释，说明命令的作用和参数含义>"
    )

    data = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3, # 降低温度，让输出更稳定、准确
        "max_tokens": 512,
        "stream": False
    }

    try:
        console.print(Text("正在思考中...", style="italic cyan"))
        response = requests.post(API_BASE_URL, headers=headers, json=data, timeout=30)
        
        # 打印状态码以便调试（可选）
        # print(f"Status Code: {response.status_code}")
        
        if response.status_code != 200:
             error_msg = f"API请求失败: {response.status_code} - {response.text}"
             console.print(Panel(error_msg, title="[bold red]API 错误[/bold red]", border_style="red"))
             return {"code": "", "explanation": "API 请求出错，请检查 Key 或网络。"}

        result = response.json()
        
        # 提取内容
        if "choices" in result and len(result["choices"]) > 0:
            raw_content = result['choices'][0]['message']['content'].strip()
            return parse_response(raw_content)
        else:
            return {"code": "", "explanation": "模型未返回有效内容。"}

    except requests.exceptions.RequestException as e:
        console.print(Panel(f"[bold red]网络错误：[/bold red]{e}", title="[bold red]连接错误[/bold red]", border_style="red"))
        return {"code": "", "explanation": "网络连接失败。"}
    except Exception as e:
        console.print(Panel(f"[bold red]未知错误：[/bold red]{e}", title="[bold red]程序错误[/bold red]", border_style="red"))
        return {"code": "", "explanation": f"发生内部错误: {str(e)}"}

def parse_response(content: str) -> dict:
    """
    解析 LLM 返回的文本，提取代码块和说明。
    """
    code_block = ""
    explanation = ""

    # 尝试提取 Markdown 代码块
    if "```bash" in content:
        parts = content.split("```bash", 1)
        if len(parts) > 1:
            rest = parts[1]
            if "```" in rest:
                code_part, text_part = rest.split("```", 1)
                code_block = code_part.strip()
                explanation = text_part.strip()
    elif "```" in content: # 兼容有些模型可能只写 ``` 而不写 bash
        parts = content.split("```", 1)
        if len(parts) > 1:
            rest = parts[1]
            if "```" in rest:
                code_part, text_part = rest.split("```", 1)
                code_block = code_part.strip()
                explanation = text_part.strip()
    
    # 如果没找到代码块，假设整个返回都是解释，或者尝试智能提取
    if not code_block and not explanation:
        explanation = content

    # 清理“说明：”前缀，使其更整洁
    explanation = explanation.replace("说明：", "").replace("说明:", "").strip()

    return {
        "code": code_block,
        "explanation": explanation,
        "raw": content # 保留原始文本以备用
    }

@click.group()
def cli():
    """
    🤖 AI 驱动的 Linux 命令行助手
    """
    pass

@cli.command()
@click.argument('task', nargs=-1)
def ask(task):
    """
    提问模式：输入你的任务描述。
    示例: python cli_helper.py ask 如何解压 tar.gz 文件
    """
    if not task:
        console.print("[yellow]用法提示: python cli_helper.py ask <你的问题>[/yellow]")
        return

    user_query = " ".join(task)
    handle_query(user_query)

@cli.command()
def interactive():
    """
    交互模式：像聊天一样连续提问。
    """
    console.print(Panel("[bold green]进入交互模式[/bold green]\n输入 'exit', 'quit' 或 'q' 退出。", 
                        title="CLI Helper", border_style="green"))
    
    while True:
        try:
            # 使用 rich 的 input 可能会有显示问题，使用标准 input 配合 rich print
            user_input = console.input("[bold cyan]>>> [/bold cyan]")
            
            if user_input.lower() in ["exit", "quit", "q", "退出"]:
                console.print("[yellow]再见！[/yellow]")
                break
            
            if not user_input.strip():
                continue

            handle_query(user_input)
            console.print() # 空一行

        except (KeyboardInterrupt, EOFError):
            console.print("\n[yellow]用户中断，退出程序。[/yellow]")
            break

def handle_query(query: str):
    """
    处理单个查询的逻辑
    """
    # 打印用户问题面板
    # console.print(Panel(f"{query}", title="[bold blue]你的任务[/bold blue]", border_style="blue"))

    # 获取结果
    result = get_llm_response(query)

    # 打印结果面板
    if result["code"]:
        # 1. 显示代码块
        console.print(Panel(
            Syntax(result["code"], "bash", theme="monokai", line_numbers=False, word_wrap=True),
            title="[bold green]建议命令[/bold green]",
            border_style="green"
        ))
        
        # 2. 显示解释
        if result["explanation"]:
            console.print(Panel(
                Text(result["explanation"], style="white"),
                title="[bold yellow]解释说明[/bold yellow]",
                border_style="yellow"
            ))
    else:
        # 如果没有代码块，可能是闲聊或者错误信息，直接显示
        console.print(Panel(
            Text(result["explanation"] or result.get("raw", ""), style="white"),
            title="[bold red]回复[/bold red]",
            border_style="red"
        ))

if __name__ == '__main__':
    cli()