"""
Email-сервис: отправка писем через SMTP (aiosmtplib).
"""

import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aiosmtplib

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailService:

    @staticmethod
    def _build_credentials_html(email: str, password: str) -> str:
        login_url = f"{settings.FRONTEND_URL}/auth/login"
        return f"""
<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8"/>
  <style>
    body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #f9f0f4; margin: 0; padding: 0; }}
    .wrapper {{ max-width: 560px; margin: 40px auto; background: #fff; border-radius: 16px;
                box-shadow: 0 4px 24px rgba(200,80,120,.10); overflow: hidden; }}
    .header {{ background: linear-gradient(135deg, #e75480 0%, #b5006e 100%);
               padding: 36px 32px; text-align: center; }}
    .header h1 {{ color: #fff; margin: 0; font-size: 26px; letter-spacing: 0.5px; }}
    .header p  {{ color: rgba(255,255,255,.85); margin: 8px 0 0; font-size: 14px; }}
    .body {{ padding: 36px 32px; }}
    .body p {{ color: #444; font-size: 15px; line-height: 1.6; }}
    .creds {{ background: #fdf2f7; border: 2px solid #e75480; border-radius: 12px;
              padding: 20px 24px; margin: 24px 0; }}
    .creds p {{ margin: 6px 0; color: #333; font-size: 15px; }}
    .creds strong {{ color: #b5006e; }}
    .btn {{ display: inline-block; background: linear-gradient(135deg, #e75480, #b5006e);
            color: #fff !important; text-decoration: none; padding: 14px 32px;
            border-radius: 50px; font-size: 16px; font-weight: 600; margin-top: 8px; }}
    .footer {{ background: #f3e6ec; text-align: center; padding: 18px 32px;
               color: #999; font-size: 12px; }}
  </style>
</head>
<body>
<div class="wrapper">
  <div class="header">
    <h1>💅 Lucy Nails Academy</h1>
    <p>Добро пожаловать в мир идеального маникюра!</p>
  </div>
  <div class="body">
    <p>Поздравляем! Ваш заказ успешно оплачен. Вот ваши данные для входа:</p>
    <div class="creds">
      <p>🔑 <strong>Логин (email):</strong> {email}</p>
      <p>🔒 <strong>Пароль:</strong> {password}</p>
    </div>
    <p>Сохраните пароль — после первого входа вы сможете его изменить в личном кабинете.</p>
    <p style="text-align:center; margin-top:28px;">
      <a href="{login_url}" class="btn">Войти в кабинет →</a>
    </p>
  </div>
  <div class="footer">
    © 2025 Lucy Nails Academy · Если вы не совершали эту покупку, напишите нам в поддержку.
  </div>
</div>
</body>
</html>
"""

    @staticmethod
    async def send_credentials(email: str, password: str) -> None:
        """Отправляет email с логином и сгенерированным паролем."""
        if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
            logger.warning("SMTP credentials not configured — skipping email to %s", email)
            return

        msg = MIMEMultipart("alternative")
        msg["Subject"] = "🎉 Ваш доступ к курсу — Lucy Nails Academy"
        msg["From"]    = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_USER}>"
        msg["To"]      = email

        html = EmailService._build_credentials_html(email, password)
        msg.attach(MIMEText(html, "html", "utf-8"))

        try:
            await aiosmtplib.send(
                msg,
                hostname=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                username=settings.SMTP_USER,
                password=settings.SMTP_PASSWORD,
                start_tls=True,
            )
            logger.info("Credentials email sent to %s", email)
        except Exception as exc:
            logger.error("Failed to send email to %s: %s", email, exc)
            raise
