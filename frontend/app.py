import streamlit as st
import requests
import json

API_BASE = "http://localhost:8000"

# 页面配置
st.set_page_config(
    page_title="智问 - AI知识库问答",
    page_icon="🤖",
    layout="wide"
)

# 初始化 session state
if "token" not in st.session_state:
    st.session_state.token = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "current_kb" not in st.session_state:
    st.session_state.current_kb = None

# 侧边栏：认证
with st.sidebar:
    st.title("智问 🤖")

    if not st.session_state.token:
        st.subheader("登录")
        username = st.text_input("用户名")
        password = st.text_input("密码", type="password")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("登录"):
                resp = requests.post(
                    f"{API_BASE}/auth/login",
                    data={"username": username, "password": password}
                )
                if resp.status_code == 200:
                    st.session_state.token = resp.json()["access_token"]
                    st.success("登录成功")
                    st.rerun()
                else:
                    st.error("登录失败")

        with col2:
            if st.button("注册"):
                resp = requests.post(
                    f"{API_BASE}/auth/register",
                    json={"username": username, "password": password}
                )
                if resp.status_code == 200:
                    st.success("注册成功，请登录")
                else:
                    st.error("注册失败")
    else:
        st.success("已登录")
        if st.button("退出"):
            st.session_state.token = None
            st.session_state.messages = []
            st.session_state.current_kb = None
            st.rerun()

        # 知识库管理
        st.subheader("知识库")

        headers = {"Authorization": f"Bearer {st.session_state.token}"}

        # 创建知识库
        with st.expander("创建知识库"):
            kb_name = st.text_input("名称")
            kb_desc = st.text_area("描述", height=68)
            if st.button("创建"):
                resp = requests.post(
                    f"{API_BASE}/kbs/",
                    json={"name": kb_name, "description": kb_desc},
                    headers=headers
                )
                if resp.status_code == 200:
                    st.success("创建成功")
                    st.rerun()
                else:
                    st.error("创建失败")

        # 列表知识库
        resp = requests.get(f"{API_BASE}/kbs/", headers=headers)
        if resp.status_code == 200:
            kbs = resp.json()
            for kb in kbs:
                col1, col2 = st.columns([3, 1])
                with col1:
                    if st.button(kb["name"], key=f"kb_{kb['id']}"):
                        st.session_state.current_kb = kb["id"]
                        st.session_state.messages = []
                        st.rerun()
                with col2:
                    if st.button("🗑️", key=f"del_{kb['id']}"):
                        requests.delete(f"{API_BASE}/kbs/{kb['id']}", headers=headers)
                        st.rerun()

        # 上传文档
        if st.session_state.current_kb:
            st.subheader("上传文档")
            uploaded = st.file_uploader("选择文件", type=["pdf", "docx", "txt"])
            if uploaded:
                files = {"file": (uploaded.name, uploaded.getvalue(), uploaded.type)}
                resp = requests.post(
                    f"{API_BASE}/documents/upload/{st.session_state.current_kb}",
                    files=files,
                    headers=headers
                )
                if resp.status_code == 200:
                    result = resp.json()
                    st.success(f"上传成功！切分 {result['chunk_count']} 块")
                else:
                    st.error("上传失败")

# 主界面：对话
if st.session_state.token and st.session_state.current_kb:
    st.title("💬 智能问答")

    # 显示历史消息
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
            if msg.get("sources"):
                st.caption(f"📚 来源：{', '.join(msg['sources'])}")

    # 输入框
    if question := st.chat_input("请输入问题..."):
        # 添加用户消息
        st.session_state.messages.append({"role": "user", "content": question})

        # 显示用户消息
        with st.chat_message("user"):
            st.write(question)

        # 调用流式接口
        with st.chat_message("assistant"):
            placeholder = st.empty()
            full_response = ""
            sources = []

            headers = {"Authorization": f"Bearer {st.session_state.token}"}

            resp = requests.post(
                f"{API_BASE}/chat/ask/stream/{st.session_state.current_kb}",
                params={"question": question},
                headers=headers,
                stream=True
            )

            if resp.status_code == 200:
                for line in resp.iter_lines():
                    if line:
                        line = line.decode('utf-8')
                        if line.startswith('data: '):
                            data = json.loads(line[6:])
                            if data.get("done"):
                                sources = data.get("sources", [])
                                break
                            token = data.get("token", "")
                            full_response += token
                            placeholder.markdown(full_response + "▌")

                placeholder.markdown(full_response)
                if sources:
                    st.caption(f"📚 来源：{', '.join(sources)}")

                # 保存到历史
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": full_response,
                    "sources": sources
                })
            else:
                st.error(f"请求失败: {resp.status_code}")

elif not st.session_state.token:
    st.info("👈 请先登录")
else:
    st.info("👈 请选择知识库")