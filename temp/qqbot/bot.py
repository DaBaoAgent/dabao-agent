
#!/usr/bin/env python3
"""
QQ Bot WebSocket客户端 - 连接QQ开放平台
启动: python bot.py
功能: 接收私聊/群聊消息->inbox, 检查outbox->发送回复
"""
import os, sys, json, time, ssl, threading, logging, signal
import urllib.request

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
from msg_queue import put_inbox, list_outbox, mark_sent, get_pending, mark_done
sys.path.insert(0, os.path.dirname(BASE))
from email_sender import send_email
LOG_DIR = os.path.join(BASE, "logs")
HISTORY_FILE = os.path.join(BASE, "history.txt")

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler(os.path.join(LOG_DIR, "bot.log"), encoding="utf-8"),
              logging.StreamHandler()])
log = logging.getLogger("QQBot")

with open(os.path.join(BASE, "config.json")) as f:
    cfg = json.load(f)
APP_ID, APP_SECRET = cfg["appId"], cfg["clientSecret"]
API_BASE, AUTH_URL = cfg["apiBase"], cfg["authUrl"]

class TokenManager:
    def __init__(self):
        self.token, self.expires = None, 0
    def refresh(self):
        data = json.dumps({"appId": APP_ID, "clientSecret": APP_SECRET}).encode()
        req = urllib.request.Request(AUTH_URL, data=data, headers={"Content-Type": "application/json"})
        resp = urllib.request.urlopen(req, timeout=15, context=ssl.create_default_context())
        r = json.loads(resp.read())
        self.token = r["access_token"]
        self.expires = time.time() + int(r["expires_in"]) - 300
        log.info(f"Token刷新 OK, 有效期{r['expires_in']}s")
        return self.token
    def get(self):
        return self.token if (self.token and time.time() < self.expires) else self.refresh()

tm = TokenManager()

try:
    import websocket
except ImportError:
    import subprocess; subprocess.check_call([sys.executable, "-m", "pip", "install", "websocket-client", "-q"])
    import websocket

class QQBot:
    def __init__(self):
        self.ws, self.seq, self.session_id = None, 0, None
        self.running, self.heartbeat_interval = True, 30000

    def connect(self):
        token = tm.get()
        self.ws = websocket.WebSocketApp("wss://api.sgroup.qq.com/websocket",
            header={"Authorization": f"QQBot {token}"},
            on_open=lambda ws: (log.info("WS已连接"), ws.send(json.dumps({
                "op": 2, "d": {"token": f"QQBot {token}", "intents": (1<<0)|(1<<1)|(1<<9)|(1<<12)|(1<<25)|(1<<26)|(1<<27)|(1<<30), "shard": [0,1], "properties": {}}})), None)[0],
            on_message=self._on_msg,
            on_error=lambda ws,e: log.error(f"WS错误: {e}"),
            on_close=self._on_close)
        threading.Thread(target=self.ws.run_forever, kwargs={
            "sslopt": {"cert_reqs": ssl.CERT_NONE}, "ping_interval": 30}, daemon=True).start()

    def _on_msg(self, ws, msg):
        try:
            data = json.loads(msg)
            op = data.get("op")
            log.debug(f"WS收到 op={op} t={data.get('t','?')} raw={str(msg)[:200]}")
            if op == 10:
                self.heartbeat_interval = data["d"]["heartbeat_interval"]
                threading.Thread(target=self._heartbeat, daemon=True).start()
                log.info(f"Hello! heartbeat={self.heartbeat_interval}ms")
            elif op == 0:
                self.seq = data.get("s", self.seq)
                t, d = data.get("t"), data.get("d", {})
                log.info(f"EVENT: t={t} seq={self.seq}")
                if t == "READY":
                    self.session_id = d.get("session_id")
                    log.info(f"Bot就绪! user={d.get('user',{}).get('username')} session={self.session_id}")
                elif t == "C2C_MESSAGE_CREATE":
                    a = d.get("author", {})
                    log.info(f"私聊 [{a.get('username','?')}] {d.get('content','')[:40]}")
                    put_inbox({"type":"c2c","msg_id":d.get("id"),"openid":a.get("id"),
                        "username":a.get("username"),"content":d.get("content","").strip(),"timestamp":int(time.time())})
                elif t == "GROUP_AT_MESSAGE_CREATE":
                    a = d.get("author", {})
                    log.info(f"群聊 [{a.get('username','?')}] {d.get('content','')[:40]}")
                    put_inbox({"type":"group","msg_id":d.get("id"),"openid":a.get("id"),
                        "group_openid":d.get("group_openid"),"username":a.get("username"),
                        "content":d.get("content","").strip(),"timestamp":int(time.time())})
            elif op == 11:
                log.info(f"心跳ACK")
            else:
                log.info(f"未知op={op}: {str(msg)[:200]}")
        except Exception as e:
            log.error(f"消息解析错误: {e}")

    def _heartbeat(self):
        while self.running:
            time.sleep(self.heartbeat_interval/1000)
            if self.ws: self.ws.send(json.dumps({"op":1,"d":self.seq}))

    def _on_close(self, ws, code, msg):
        log.warning(f"WS断开 code={code}")
        if self.running:
            time.sleep(5); tm.refresh(); self.connect()

    def send(self, openid, content, mtype="c2c"):
        token = tm.get()
        url = f"{API_BASE}/v2/{'groups' if mtype=='group' else 'users'}/{openid}/messages"
        payload = json.dumps({"content": content, "msg_type": 0, "msg_id": str(int(time.time()*1000))}).encode()
        req = urllib.request.Request(url, data=payload, headers={"Authorization": f"QQBot {token}", "Content-Type": "application/json"})
        try:
            return json.loads(urllib.request.urlopen(req, timeout=10, context=ssl.create_default_context()).read())
        except Exception as e:
            return {"error": str(e)}

    def stop(self):
        self.running = False
        if self.ws: self.ws.close()

def outbox_worker(bot):
    log.info("Outbox检查器启动")
    while bot.running:
        try:
            for r in list_outbox():
                d = r["data"]
                bot.send(d.get("target_openid"), d.get("content"), d.get("type","c2c"))
                mark_sent(r["file"])
        except Exception as e:
            log.error(f"Outbox错误: {e}")
        time.sleep(2)

def inbox_worker(bot):
    """轮询inbox → 自动回复（暂时echo，后续接入AI）"""
    log.info("Inbox检查器启动")
    while bot.running:
        try:
            for r in get_pending():
                d = r["data"]
                openid = d.get("openid", "")
                content = d.get("content", "")
                username = d.get("username", "") or f"用户({openid[-8:]})"
                log.info(f"处理inbox: [{username}] {content[:30]}")
                # 记录历史
                with open(HISTORY_FILE, "a", encoding="utf-8") as f:
                    f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [{username}] {content}\n")
                # 生成回复
                if "发邮件" in content:
                    img_dir = os.path.join(BASE, "serve")
                    imgs = sorted([os.path.join(img_dir, f) for f in os.listdir(img_dir)
                                   if f.lower().endswith(('.png','.jpg','.jpeg'))])
                    if imgs:
                        result = send_email(to="120112121@qq.com", subject="QQ Bot发来的图片",
                                           body=f"<p>来自QQ用户 {username} 的请求</p>", attachments=imgs[:5])
                        reply_text = f"✅ 邮件发送结果：{result.get('msg','未知')}"
                    else:
                        reply_text = "❌ 未找到可发送的图片"
                else:
                    reply_text = f"收到！你说的是：{content}\n\n（这是自动回复，后续将接入AI助手）"
                log.info(f"回复 {username}: {reply_text[:40]}")
                bot.send(openid, reply_text)
                mark_done(r["file"])
                log.info(f"已处理 {username}")
        except Exception as e:
            log.error(f"Inbox错误: {e}")
        time.sleep(3)

def main():
    log.info(f"QQ Bot v1.0 | AppID={APP_ID}")
    tm.refresh()
    bot = QQBot()
    threading.Thread(target=outbox_worker, args=(bot,), daemon=True).start()
    threading.Thread(target=inbox_worker, args=(bot,), daemon=True).start()
    bot.connect()
    signal.signal(signal.SIGINT, lambda s,f: bot.stop())
    signal.signal(signal.SIGTERM, lambda s,f: bot.stop())
    try:
        while bot.running: time.sleep(1)
    except KeyboardInterrupt: bot.stop()
    log.info("已退出")

if __name__ == "__main__":
    main()
