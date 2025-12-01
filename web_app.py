import streamlit as st
import requests
import os

# --- 配置部分 ---
# 页面标题
st.set_page_config(page_title="Linux 命令行助手", page_icon="🤖")

st.title("🤖 AI 命令行助手")
st.caption("输入你的需求，我来帮你写命令")

# 获取 API Key
# 在本地运行时，尝试从环境变量获取，或者在页面侧边栏输入
api_key = os.getenv("API_KEY")

# 如果没有环境变量，允许用户在侧边栏输入
if not api_key:
    with st.sidebar:
        api_key = st.text_input("请输入 SiliconFlow API Key", type="password")
        st.markdown("[去申请 Key](https://cloud.siliconflow.cn/)")

# API 配置
API_BASE_URL = "https://api.siliconflow.cn/v1/chat/completions"
MODEL_NAME = "Qwen/Qwen2.5-7B-Instruct"

# --- 核心逻辑函数 ---
def get_llm_response(prompt, key):
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }
    
    system_prompt = (
        "你是一个专业的命令行(CLI)助手。用户会告诉你他们想做什么，你需要提供相应的 Linux/macOS 命令行指令。\n"
        "请严格遵守以下规则：\n"
        "1. 如果用户意图不明确，请给出最常用的命令。\n"
        "2. 如果操作有危险（如 rm -rf），请在解释中明确警告。\n"
        "3. 输出格式必须严格如下：\n"
        "```bash\n"
        "<此处写具体的命令行指令>\n"
        "```\n"
        "说明：<此处写简短的中文解释>"
    )

    data = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3,
        "max_tokens": 512,
        "stream": False
    }

    try:
        response = requests.post(API_BASE_URL, headers=headers, json=data, timeout=30)
        if response.status_code == 200:
            result = response.json()
            return result['choices'][0]['message']['content']
        else:
            return f"API 请求失败: {response.status_code} - {response.text}"
    except Exception as e:
        return f"发生错误: {str(e)}"

# --- 聊天界面逻辑 ---

# 1. 初始化聊天记录
if "messages" not in st.session_state:
    st.session_state["messages"] = [{"role": "assistant", "content": "你好！请告诉我你想执行什么操作？例如：'解压 tar.gz 文件'"}]

# 2. 显示历史消息
for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

# 3. 处理用户输入
if prompt := st.chat_input():
    if not api_key:
        st.error("请先配置 API Key")
        st.stop()

    # 显示用户消息
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)

    # 获取 AI 回复
    with st.chat_message("assistant"):
        with st.spinner("思考中..."):
            response_text = get_llm_response(prompt, api_key)
            st.write(response_text)
    
    # 保存 AI 回复到历史
    st.session_state.messages.append({"role": "assistant", "content": response_text})
