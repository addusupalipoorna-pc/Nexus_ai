import threading
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class Notifier:
    # Class-level settings (can be updated dynamically from UI settings)
    telegram_token = ""
    telegram_chat_id = ""
    
    email_smtp_server = "smtp.gmail.com"
    email_smtp_port = 587
    email_sender = ""
    email_password = ""
    email_recipient = ""

    @classmethod
    def configure(cls, config: dict):
        """Updates notifier configuration parameters."""
        cls.telegram_token = config.get("telegram_token", cls.telegram_token)
        cls.telegram_chat_id = config.get("telegram_chat_id", cls.telegram_chat_id)
        
        cls.email_smtp_server = config.get("email_smtp_server", cls.email_smtp_server)
        cls.email_smtp_port = int(config.get("email_smtp_port", cls.email_smtp_port))
        cls.email_sender = config.get("email_sender", cls.email_sender)
        cls.email_password = config.get("email_password", cls.email_password)
        cls.email_recipient = config.get("email_recipient", cls.email_recipient)

    @classmethod
    def send_telegram(cls, message: str):
        """Dispatches a Telegram message in a background thread."""
        if not cls.telegram_token or not cls.telegram_chat_id:
            print("[Notifier] Telegram configuration incomplete. Logging message: ", message)
            return
            
        def dispatch():
            try:
                url = f"https://api.telegram.org/bot{cls.telegram_token}/sendMessage"
                payload = {
                    "chat_id": cls.telegram_chat_id,
                    "text": f"🚨 [NEXUS AI ALERT] 🚨\n\n{message}",
                    "parse_mode": "Markdown"
                }
                response = requests.post(url, json=payload, timeout=8.0)
                if response.status_code == 200:
                    print("[Notifier] Telegram alert sent successfully.")
                else:
                    print(f"[Notifier] Telegram dispatch failed: {response.text}")
            except Exception as e:
                print(f"[Notifier] Error sending Telegram alert: {e}")

        threading.Thread(target=dispatch, daemon=True).start()

    @classmethod
    def send_email(cls, subject: str, body: str):
        """Dispatches an SMTP email alert in a background thread."""
        if not cls.email_sender or not cls.email_recipient:
            print(f"[Notifier] Email configuration incomplete. Logging email subject='{subject}', body='{body}'")
            return
            
        def dispatch():
            try:
                msg = MIMEMultipart()
                msg['From'] = cls.email_sender
                msg['To'] = cls.email_recipient
                msg['Subject'] = f"🚨 NEXUS AI: {subject}"
                
                msg.attach(MIMEText(body, 'plain'))
                
                # Setup SMTP session
                server = smtplib.SMTP(cls.email_smtp_server, cls.email_smtp_port, timeout=10.0)
                server.starttls()
                if cls.email_password:
                    server.login(cls.email_sender, cls.email_password)
                server.sendmail(cls.email_sender, cls.email_recipient, msg.as_string())
                server.quit()
                print("[Notifier] Email alert sent successfully.")
            except Exception as e:
                print(f"[Notifier] Error sending Email alert: {e}")

        threading.Thread(target=dispatch, daemon=True).start()
