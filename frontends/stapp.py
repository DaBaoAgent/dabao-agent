import os, sys, subprocess
from urllib.request import urlopen
from urllib.parse import quote
if sys.stdout is None: sys.stdout = open(os.devnull, "w")
if sys.stderr is None: sys.stderr = open(os.devnull, "w")
try: sys.stdout.reconfigure(errors='replace')
except: pass
try: sys.stderr.reconfigure(errors='replace')
except: pass
script_dir = os.path.dirname(__file__)
sys.path.append(os.path.abspath(os.path.join(script_dir, '..')))
sys.path.append(os.path.abspath(script_dir))

import streamlit as st
import time, json, re, threading, queue
from agentmain import GeneraticAgent
import chatapp_common  # activate /continue command (monkey patches GeneraticAgent)
from continue_cmd import handle_frontend_command, reset_conversation, list_sessions, extract_ui_messages

st.set_page_config(page_title="DabaoAgent", layout="wide")

@st.cache_resource
def init():
    try:
        agent = GeneraticAgent()
    except Exception:
        return None
    if agent.llmclient is None:
        return None
    threading.Thread(target=agent.run, daemon=True).start()
    return agent

agent = init()

st.title("🖥️ DabaoAgent")

st.session_state.setdefault('autonomous_enabled', False)

if agent is None:
    st.warning("⚠️ 未配置任何可用的 LLM 接口，请在侧边栏打开 🔑 API 密钥设置，填入信息后点击保存。")

@st.fragment
def render_sidebar():
    st.session_state.setdefault('autonomous_enabled', False)
    if agent is not None:
        llm_options = agent.list_llms()
        current_idx = agent.llm_no
        llm_labels = {idx: f"{idx}: {(name or '').strip()}" for idx, name, _ in llm_options}
        st.caption(f"当前模型: {llm_labels.get(current_idx, str(current_idx))}", help="下拉切换备用链路")
        selected_idx = st.selectbox("备用链路", [idx for idx, _, _ in llm_options], index=next((i for i, (idx, _, _) in enumerate(llm_options) if idx == current_idx), 0), format_func=llm_labels.get, label_visibility="collapsed", key="sidebar_llm_select")
        if selected_idx != current_idx:
            agent.next_llm(selected_idx); st.rerun(scope="fragment")
    else:
        st.caption("🔴 未加载 LLM 配置")

    last_reply_time = st.session_state.get('last_reply_time', 0)
    if last_reply_time > 0 and agent is not None:
        st.caption(f"空闲时间：{int(time.time()) - last_reply_time}秒", help="当超过30分钟未收到回复时，系统会自动任务")
    if agent is not None:
        if st.button("强行停止任务"):
            agent.abort(); st.toast("已发送停止信号"); st.rerun()
        if st.button("重新注入工具"):
            agent.llmclient.last_tools = ''
            try:
                hist_path = os.path.join(script_dir, '..', 'assets', 'tool_usable_history.json')
                with open(hist_path, 'r', encoding='utf-8') as f: tool_hist = json.load(f)
                agent.llmclient.backend.history.extend(tool_hist)
                st.toast(f"已重新注入工具，追加了 {len(tool_hist)} 条示范记录")
            except Exception as e: st.toast(f"注入工具示范失败: {e}")
        if st.button("🐱 桌面宠物"):
            kwargs = {'creationflags': 0x08} if sys.platform == 'win32' else {}
            pet_script = os.path.join(script_dir, 'desktop_pet_v2.pyw')
            if not os.path.exists(pet_script): pet_script = os.path.join(script_dir, 'desktop_pet.pyw')
            subprocess.Popen([sys.executable, pet_script], **kwargs)
            def _pet_req(q):
                def _do():
                    try: urlopen(f'http://127.0.0.1:41983/?{q}', timeout=2)
                    except Exception: pass
                threading.Thread(target=_do, daemon=True).start()
            agent._pet_req = _pet_req
            if not hasattr(agent, '_turn_end_hooks'): agent._turn_end_hooks = {}
            def _pet_hook(ctx):
                parts = [f"Turn {ctx.get('turn','?')}"]
                if ctx.get('summary'): parts.append(ctx['summary'])
                if ctx.get('exit_reason'): parts.append('任务已完成')
                _pet_req(f'msg={quote(chr(10).join(parts))}')
                if ctx.get('exit_reason'): _pet_req('state=idle')
            agent._turn_end_hooks['pet'] = _pet_hook
            st.toast("桌面宠物已启动")

    st.divider()
    with st.expander("🔑 API 密钥设置", expanded=(agent is None)):
        api_key = st.text_input("API Key", type="password", placeholder="sk-...", key="sidebar_api_key")
        api_base = st.text_input("API Base URL", placeholder="https://api.openai.com/v1", key="sidebar_api_base")
        model_name = st.text_input("模型名称", placeholder="gpt-5.4", key="sidebar_api_model")
        cfg_name = st.text_input("配置标识", placeholder="ui-config", key="sidebar_api_cfg_name")
        if st.button("💾 保存并加载", key="sidebar_save_api"):
            if not api_key or not api_base or not model_name:
                st.toast("❌ 请填写 API Key、Base URL 和模型名称")
            else:
                try:
                    import json as _json
                    json_path = os.path.join(script_dir, "..", "mykey.json")
                    existing = {}
                    if os.path.exists(json_path):
                        with open(json_path, "r", encoding="utf-8") as _f:
                            existing = _json.load(_f)
                    cfg_key = "native_oai_ui_config_sidebar"
                    existing[cfg_key] = {
                        "name": cfg_name or "UI配置",
                        "apikey": api_key,
                        "apibase": api_base,
                        "model": model_name,
                    }
                    with open(json_path, "w", encoding="utf-8") as _f:
                        _json.dump(existing, _f, indent=2, ensure_ascii=False)
                    import llmcore as _lm
                    _lm._mykey_mtime = None
                    if agent is not None:
                        agent.load_llm_sessions()
                    else:
                        st.cache_resource.clear()
                    st.toast("✅ API 配置已保存并加载")
                    st.rerun()
                except Exception as e:
                    st.toast(f"❌ 保存失败: {e}")

    st.divider()
    if st.button("开始空闲自主行动"):
        st.session_state.last_reply_time = int(time.time()) - 1800
        st.toast("已将上次回复时间设为1800秒前"); st.rerun()
    if st.session_state.autonomous_enabled:
        if st.button("⏸️ 禁止自主行动"):
            st.session_state.autonomous_enabled = False
            st.toast("⏸️ 已禁止自主行动"); st.rerun()
        st.caption("🟢 自主行动运行中，会在你离开它30分钟后自动进行")
    else:
        if st.button("▶️ 允许自主行动", type="primary"):
            st.session_state.autonomous_enabled = True
            st.toast("✅ 已允许自主行动"); st.rerun()
        st.caption("🔴 自主行动已停止")
with st.sidebar: render_sidebar()

def fold_turns(text):
    """Return list of segments: [{'type':'text','content':...}, {'type':'fold','title':...,'content':...}]"""
    # 先把4+反引号块替换为占位符，避免误切子agent嵌套的 LLM Running
    _ph = []
    safe = re.sub(r'`{4,}.*?`{4,}', lambda m: (_ph.append(m.group(0)), f'\x00PH{len(_ph)-1}\x00')[1], text, flags=re.DOTALL)
    # 流式中间态：末尾可能有未闭合的4+反引号块，也需保护
    safe = re.sub(r'`{4,}[^`].*$', lambda m: (_ph.append(m.group(0)), f'\x00PH{len(_ph)-1}\x00')[1], safe, flags=re.DOTALL)
    parts = re.split(r'(\**LLM Running \(Turn \d+\) \.\.\.\*\**)', safe)
    parts = [re.sub(r'\x00PH(\d+)\x00', lambda m: _ph[int(m.group(1))], p) for p in parts]
    if len(parts) < 4: return [{'type': 'text', 'content': text}]
    segments = []
    if parts[0].strip(): segments.append({'type': 'text', 'content': parts[0]})
    turns = []
    for i in range(1, len(parts), 2):
        marker = parts[i]
        content = parts[i+1] if i+1 < len(parts) else ''
        turns.append((marker, content))
    for idx, (marker, content) in enumerate(turns):
        if idx < len(turns) - 1:
            _c = re.sub(r'`{3,}.*?`{3,}|<thinking>.*?</thinking>', '', content, flags=re.DOTALL)
            matches = re.findall(r'<summary>\s*((?:(?!<summary>).)*?)\s*</summary>', _c, re.DOTALL)
            if matches:
                title = matches[0].strip()
                title = title.split('\n')[0]
                if len(title) > 50: title = title[:50] + '...'
            else: title = marker.strip('*')
            segments.append({'type': 'fold', 'title': title, 'content': content})
        else: segments.append({'type': 'text', 'content': marker + content})
    return segments
def render_segments(segments, suffix=''):
    # 整块重画：调用方用 slot.container() 包裹，保证 DOM 路径稳定、跨 rerun 对齐（消除"灰色重影"）。
    # heartbeat 空转时 segments 不变 → Streamlit 后端 diff 无变化 → 前端零闪烁；
    # 但 container/markdown 本身是 API 调用，StopException 仍会被抛出（abort 照常起作用）。
    for seg in segments:
        if seg['type'] == 'fold':
            with st.expander(seg['title'], expanded=False): st.markdown(seg['content'])
        else:
            st.markdown(seg['content'] + suffix)

def agent_backend_stream(prompt):
    display_queue = agent.put_task(prompt, source="user")
    response = ''
    try:
        while True:
            try: item = display_queue.get(timeout=1)
            except queue.Empty:
                yield response   # heartbeat: let outer st.markdown() run → Streamlit checks StopException
                continue
            if 'next' in item:
                response = item['next']; yield response
            if 'done' in item:
                yield item['done']; break
    finally: agent.abort()

if "messages" not in st.session_state: st.session_state.messages = []
if agent is not None:
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            # 用 slot=st.empty() + with slot.container(): ... 的外壳，DOM 路径和流式渲染完全一致，跨 rerun 对齐
            slot = st.empty()
            with slot.container():
                if msg["role"] == "assistant": render_segments(fold_turns(msg["content"]))
                else: st.markdown(msg["content"])

# Scroll-height ghost fix: during streaming, expander open/close mid-animation can leave
# phantom height → scrollbar long but can't scroll to bottom. Periodically detect & reflow.
try:
    from streamlit import html as _st_html  # 1.57+
    def _embed_html(body, **kw):
        if any(k in kw for k in ("width", "height")):
            from streamlit.components.v1 import html as _comp_html
            _comp_html(body, **kw)
        else:
            _st_html(body)
except (ImportError, AttributeError):
    from streamlit.components.v1 import html as _embed_html  # ≤1.55
_js_scroll_fix = (
    "!function(){var p=window.parent;if(p.__sfx2)return;p.__sfx2=1;var d=p.document;"
    "function f(){var m=d.querySelector('section.main');if(!m)return;"
    "var s=m.scrollTop;m.style.minHeight=m.scrollHeight+1+'px';void m.offsetHeight;"
    "m.style.minHeight='';void m.offsetHeight;m.scrollTop=s}"
    "d.addEventListener('transitionend',function(e){"
    "e.target.closest&&e.target.closest('details')&&setTimeout(f,60)},!0);"
    "new MutationObserver(function(){setTimeout(f,80)})"
    ".observe(d.body,{subtree:1,attributes:1,attributeFilter:['open']});"
    "setInterval(f,5000)}()"
)
# IME composition fix (macOS only) - prevents Enter from submitting during CJK input
_js_ime_fix = ("" if os.name == 'nt' else
    "!function(){if(window.parent.__imeFix)return;window.parent.__imeFix=1;"
    "var d=window.parent.document,c=0;"
    "d.addEventListener('compositionstart',()=>c=1,!0);"
    "d.addEventListener('compositionend',()=>c=0,!0);"
    "function f(){d.querySelectorAll('textarea[data-testid=stChatInputTextArea]')"
    ".forEach(t=>{t.__imeFix||(t.__imeFix=1,t.addEventListener('keydown',e=>{"
    "e.key==='Enter'&&!e.shiftKey&&(e.isComposing||c||e.keyCode===229)&&"
    "(e.stopImmediatePropagation(),e.preventDefault())},!0))})}"
    "f();new MutationObserver(f).observe(d.body,{childList:1,subtree:1})}()")
_embed_html(f'<script>{_js_scroll_fix};{_js_ime_fix}</script>', height=0)

# Streamlit toolbar + settings full Chinese translation
_js_toolbar_zh = (
    "!function(){var p=window.parent;if(p.__tbzh)return;p.__tbzh=1;"
    "var M={Rerun:'重新运行',R:'R','Auto rerun':'自动重新运行','Always rerun':'始终自动运行',"
    "Running:'运行中','Please wait':'请稍候','Done!':'完成','Nada':'无',"
    "Deploy:'部署','Deploy now':'立即部署','Deploy this app':'部署此应用','Share this app':'分享应用',"
    "'Host on Community Cloud':'托管至社区云','Streamlit for Teams':'Streamlit团队版','Streamlit Cloud':'Streamlit云',"
    "'Streamlit Community Cloud':'Streamlit社区云',"
    "Settings:'设置',About:'关于',Print:'打印','Clear cache':'清除缓存',"
    "Community:'社区','Get help':'获取帮助','Report a bug':'报告问题',"
    "'Streamlit documentation':'Streamlit文档','Ask a question':'提问',"
    "'Rerun the app':'重新运行应用','Rerun the script':'重新运行脚本','Appearance':'外观','General':'通用',"
    "'Custom Theme':'自定义主题','Use system setting':'使用系统设置',"
    "Light:'浅色',Dark:'深色','Active theme':'当前主题',Font:'字体',"
    "'Font size':'字体大小','Base font size':'基础字体大小',Text:'文本',"
    "Headers:'标题','Code font':'代码字体','Show a button':'显示按钮',"
    "'Show \"Deploy\"':'显示部署按钮','Show the toolbar':'显示工具栏',"
    "'Editor settings':'编辑器设置','Run on save':'保存时运行',"
    "'Show sidebar':'显示侧边栏','Wide mode':'宽屏模式',"
    "Advanced:'高级',Theme:'主题',Server:'服务器',"
    "'Email for bug reports':'问题反馈邮箱','Save settings':'保存设置',"
    "Cancel:'取消','Primary color':'主色调','Background color':'背景色',"
    "'Secondary background color':'次要背景色','Text color':'文本颜色',"
    "'Font family':'字体',Default:'默认','Sans serif':'无衬线',"
    "Serif:'衬线',Monospace:'等宽','Update theme':'更新主题',"
    "'Run on save & auto':'保存时自动运行','Run on save &':'保存时运行',"
    "'Always rerun and show changes':'自动运行并显示变更',"
    "Stop:'停止','Stop recording':'停止录制','Record a screencast':'录制屏幕录像',"
    "'Configuration':'配置','The app is running':'应用正在运行'};"
    "function T(el){"
    "var w=p.document.createTreeWalker(el,NodeFilter.SHOW_TEXT),n=[];"
    "var nd;while(nd=w.nextNode())n.push(nd);"
    "for(var i=0;i<n.length;i++){"
    "var tx=n[i].textContent,t0=tx;"
    "for(var k in M){if(tx.indexOf(k)!==-1){tx=tx.replace(k,M[k])}}"
    "if(tx!==t0)n[i].textContent=tx;}}"
    "function S(){"
    "try{"
    "var tb=p.document.querySelector('[data-testid=\"stToolbar\"]');if(tb)T(tb);"
    "p.document.querySelectorAll('[data-testid=\"stMainMenu\"] *').forEach(function(e){"
    "var v=e.textContent.trim();if(M[v]&&e.childNodes.length===1)e.textContent=M[v];});"
    "p.document.querySelectorAll('[data-testid=\"stMainMenuList\"] *').forEach(function(e){"
    "var v=e.textContent.trim();if(M[v]&&e.childNodes.length===1)e.textContent=M[v];});"
    "p.document.querySelectorAll('[data-baseweb=\"popover\"] [role=\"dialog\"] *').forEach(function(e){"
    "var v=e.textContent.trim();if(M[v]&&e.childNodes.length===1)e.textContent=M[v];});"
    "p.document.querySelectorAll('[data-testid=\"stStatusWidget\"]').forEach(function(e){T(e);});"
    "p.document.querySelectorAll('[data-testid=\"stAppViewBlockContainer\"] [data-testid=\"stText\"]').forEach(function(e){"
    "var v=e.textContent.trim();if(v.indexOf('Running')===0||v.indexOf('Please wait')===0)T(e);});"
    "}catch(e){}}"
    "setTimeout(S,300);setTimeout(S,1500);setTimeout(S,4000);"
    "new MutationObserver(function(){setTimeout(S,300)}).observe(p.document.body,{childList:1,subtree:1});"
    "}()"
)
_embed_html(f'<script>{_js_toolbar_zh}</script>')

if prompt := st.chat_input("输入任务...", disabled=(agent is None)):
    if agent is None:
        st.toast("❌ 请先在侧边栏配置 API 密钥")
    else:
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        cmd = (prompt or "").strip()
        def _reset_and_rerun():
            st.session_state.streaming = False
            st.session_state.stopping = False
            st.session_state.display_queue = None
            st.session_state.partial_response = ""
            st.session_state.reply_ts = ""
            st.session_state.current_prompt = ""
            st.session_state.last_reply_time = int(time.time())
            st.rerun()
        if cmd == "/new":
            st.session_state.messages = [{"role": "assistant", "content": reset_conversation(agent), "time": ts}]
            _reset_and_rerun()
        if cmd.startswith("/continue"):
            m = re.match(r'/continue\s+(\d+)\s*$', cmd.strip())
            sessions = list_sessions(exclude_pid=os.getpid()) if m else []
            idx = int(m.group(1)) - 1 if m else -1
            # Resolve target path BEFORE handle (which snapshots current log, shifting indices).
            target = sessions[idx][0] if 0 <= idx < len(sessions) else None
            result = handle_frontend_command(agent, cmd)
            history = extract_ui_messages(target) if target and result.startswith('✅') else None
            tail = [{"role": "assistant", "content": result, "time": ts}]
            if history:
                st.session_state.messages = history + tail
            else:
                st.session_state.messages = list(st.session_state.messages) + \
                    [{"role": "user", "content": cmd, "time": ts}] + tail
            _reset_and_rerun()
        st.session_state.messages.append({"role": "user", "content": prompt})
        if hasattr(agent, '_pet_req') and not prompt.startswith('/'): agent._pet_req('state=walk')
        with st.chat_message("user"): st.markdown(prompt)

        with st.chat_message("assistant"):
            frozen = 0; live = st.empty(); response = ''
            CURSOR = ' ▌'
            for response in agent_backend_stream(prompt):
                segs = fold_turns(response)
                n_done = max(0, len(segs) - 1)
                while frozen < n_done:
                    with live.container(): render_segments([segs[frozen]])
                    live = st.empty(); frozen += 1
                with live.container(): render_segments([segs[-1]], suffix=CURSOR)   # live 区域
            segs = fold_turns(response)
            for i in range(frozen, len(segs)):
                with live.container(): render_segments([segs[i]])
                if i < len(segs) - 1: live = st.empty()
        st.session_state.messages.append({"role": "assistant", "content": response})
        st.session_state.last_reply_time = int(time.time())

if agent is not None and st.session_state.autonomous_enabled:
    st.markdown(f"""<div id="last-reply-time" style="display:none">{st.session_state.get('last_reply_time', int(time.time()))}</div>""", unsafe_allow_html=True)
