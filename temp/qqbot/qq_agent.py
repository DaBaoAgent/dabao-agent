
#!/usr/bin/env python3
"""
Agent端QQ消息处理 - 读取inbox、处理、写入outbox
被主Agent调用: python qq_agent.py
"""
import os, sys, json, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from msg_queue import get_pending, mark_done, reply, list_outbox

base = os.path.dirname(os.path.abspath(__file__))
INBOX = os.path.join(base, "inbox")
HISTORY = os.path.join(base, "history.txt")

def check_messages():
    """检查待处理消息，返回列表"""
    msgs = get_pending()
    return msgs

def process_and_reply(msg, response_text):
    """处理消息并回复"""
    data = msg["data"]
    openid = data.get("openid", "")
    username = data.get("username", "未知")
    content = data.get("content", "")
    msg_id = data.get("msg_id", "")
    msg_type = data.get("type", "c2c")
    group_openid = data.get("group_openid", "")
    
    # 写入历史
    with open(HISTORY, "a", encoding="utf-8") as f:
        f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [{msg_type}] {username}: {content}\n")
        f.write(f"  → Agent: {response_text}\n\n")
    
    # 发送回复
    target = group_openid if msg_type == "group" else openid
    reply(target, response_text, msg_id, msg_type, group_openid)
    
    # 标记已处理
    mark_done(msg["file"])
    
    return f"✅ 已回复 {username}"

if __name__ == "__main__":
    # 独立运行模式 - 列出待处理消息
    msgs = check_messages()
    if not msgs:
        print("📭 无待处理QQ消息")
        print("outbox待发:", len(list_outbox()))
    else:
        print(f"📩 {len(msgs)} 条待处理:")
        for m in msgs:
            d = m["data"]
            print(f"  [{d['username']}] {d['content'][:80]}")
