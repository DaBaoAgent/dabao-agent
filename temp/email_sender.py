#!/usr/bin/env python3
"""
邮件发送技能模块 - 可复用SMTP邮件发送器
支持: QQ邮箱/Gmail/163等, HTML正文, 多附件, 抄送/密送

调用方式:
    from email_sender import EmailSender
    sender = EmailSender()
    sender.send(to="xxx@qq.com", subject="标题", body="<h1>Hello</h1>", attachments=["图.png"])
    
或一行式:
    from email_sender import send_email
    send_email(to="120112121@qq.com", subject="主题", body="正文", attachments=["1.png"])
"""

import smtplib, ssl, os, mimetypes, json
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email import encoders
from email.utils import formataddr
from typing import List, Union
from dataclasses import dataclass

@dataclass
class EmailConfig:
    smtp_server: str = "smtp.qq.com"
    smtp_port: int = 465
    sender_email: str = "1361098634@qq.com"
    sender_name: str = "大宝Agent"
    auth_code: str = "scbfgcpzbcgbhjeb"
    use_ssl: bool = True

class EmailSender:
    """通用邮件发送器"""
    def __init__(self, config: EmailConfig = None, config_file: str = None):
        if config_file and os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            config = EmailConfig(**data)
        self.cfg = config or EmailConfig()

    def send(self, to: Union[str, List[str]], subject: str, body: str = "",
             html: bool = True, attachments: List[str] = None,
             cc: List[str] = None, bcc: List[str] = None) -> dict:
        """发送邮件
        :return: {"success": True/False, "msg": "..."}
        """
        try:
            msg = MIMEMultipart('mixed')
            msg['From'] = formataddr((self.cfg.sender_name, self.cfg.sender_email))
            to_list = [to] if isinstance(to, str) else to
            msg['To'] = ', '.join(to_list)
            msg['Subject'] = subject
            if cc:
                msg['Cc'] = ', '.join(cc)
                to_list.extend(cc)
            if bcc:
                to_list.extend(bcc)

            subtype = 'html' if html else 'plain'
            msg.attach(MIMEText(body, subtype, 'utf-8'))

            if attachments:
                for fp in attachments:
                    if not os.path.exists(fp):
                        continue
                    filename = os.path.basename(fp)
                    mime_type, _ = mimetypes.guess_type(fp)
                    if mime_type is None:
                        mime_type = 'application/octet-stream'
                    main, sub = mime_type.split('/', 1)
                    with open(fp, 'rb') as f:
                        if main == 'image':
                            part = MIMEImage(f.read(), _subtype=sub, name=filename)
                        else:
                            part = MIMEBase(main, sub)
                            part.set_payload(f.read())
                            encoders.encode_base64(part)
                    part.add_header('Content-Disposition', 'attachment', filename=('utf-8', '', filename))
                    msg.attach(part)

            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(self.cfg.smtp_server, self.cfg.smtp_port, context=context) as s:
                s.login(self.cfg.sender_email, self.cfg.auth_code)
                s.sendmail(self.cfg.sender_email, to_list, msg.as_string())
            return {"success": True, "msg": f"发送成功 -> {', '.join(to_list[:3])}"}
        except smtplib.SMTPAuthenticationError:
            return {"success": False, "msg": "认证失败: 检查授权码是否正确(不是QQ密码!)"}
        except Exception as e:
            return {"success": False, "msg": f"发送异常: {e}"}

def send_email(to: str, subject: str, body: str, attachments: List[str] = None,
               cc: List[str] = None, html: bool = True) -> dict:
    """一行式发送（使用默认QQ邮箱配置）"""
    sender = EmailSender()
    return sender.send(to=to, subject=subject, body=body, html=html,
                       attachments=attachments, cc=cc)
