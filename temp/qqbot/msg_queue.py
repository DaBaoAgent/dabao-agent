
# QQ Bot 消息队列模块
import os, json, time, glob

BASE = os.path.dirname(os.path.abspath(__file__))
INBOX = os.path.join(BASE, "inbox")
OUTBOX = os.path.join(BASE, "outbox")

def put_inbox(msg: dict) -> str:
    ts = int(time.time() * 1000)
    fpath = os.path.join(INBOX, f"msg_{ts}.json")
    with open(fpath, "w", encoding="utf-8") as f:
        json.dump(msg, f, ensure_ascii=False, indent=2)
    return fpath

def list_inbox() -> list:
    files = sorted(glob.glob(os.path.join(INBOX, "msg_*.json")))
    return [{"file": f, "data": json.load(open(f, encoding="utf-8"))} for f in files]

def mark_done(fpath: str):
    os.rename(fpath, fpath.replace(".json", ".done"))

def put_outbox(reply: dict) -> str:
    ts = int(time.time() * 1000)
    fpath = os.path.join(OUTBOX, f"reply_{ts}.json")
    with open(fpath, "w", encoding="utf-8") as f:
        json.dump(reply, f, ensure_ascii=False, indent=2)
    return fpath

def list_outbox() -> list:
    files = sorted(glob.glob(os.path.join(OUTBOX, "reply_*.json")))
    return [{"file": f, "data": json.load(open(f, encoding="utf-8"))} for f in files]

def mark_sent(fpath: str):
    os.rename(fpath, fpath.replace(".json", ".sent"))

def get_pending() -> list:
    return list_inbox()

def reply(openid: str, content: str, msg_id: str = "", msg_type: str = "c2c", group_openid: str = ""):
    return put_outbox({
        "target_openid": openid,
        "content": content,
        "reply_to": msg_id,
        "type": msg_type,
        "group_openid": group_openid,
        "timestamp": int(time.time())
    })
