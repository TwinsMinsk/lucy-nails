"""
Email-сервис: отправка писем через Resend HTTP API (основной путь) либо SMTP (fallback).

Railway блокирует исходящий SMTP на планах ниже Pro, поэтому в production письма
уходят через Resend (HTTPS/443). Локально, если RESEND_API_KEY не задан, отправка
идёт через SMTP. Любой транспорт вызывается с жёстким таймаутом, чтобы медленная или
недоступная почта никогда не подвешивала HTTP-запрос (сброс пароля, вебхук оплаты).
"""

import base64
import logging
from dataclasses import dataclass
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from html import escape

import aiosmtplib
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

# Ни одна отправка письма не должна висеть дольше этого времени внутри запроса.
EMAIL_TIMEOUT_SECONDS = 10.0
# Вложения (например, PDF-сертификат) кодируются в base64 и могут занимать
# несколько мегабайт — обычного таймаута может не хватить на передачу.
EMAIL_ATTACHMENT_TIMEOUT_SECONDS = 30.0
RESEND_ENDPOINT = "https://api.resend.com/emails"


@dataclass
class EmailAttachment:
    filename: str
    content: bytes
    mime_type: str = "application/pdf"


class EmailService:
    @staticmethod
    def is_configured() -> bool:
        """Returns whether an email transport (Resend or SMTP) is available."""
        return bool(
            settings.RESEND_API_KEY or (settings.SMTP_USER and settings.SMTP_PASSWORD)
        )

    @staticmethod
    def _from_address() -> str:
        """From-заголовок письма: EMAIL_FROM, иначе '<SMTP_FROM_NAME> <SMTP_USER>'."""
        if settings.EMAIL_FROM:
            return settings.EMAIL_FROM
        return f"{settings.SMTP_FROM_NAME} <{settings.SMTP_USER}>"

    @staticmethod
    async def _send(
        email: str,
        subject: str,
        html: str,
        attachments: list[EmailAttachment] | None = None,
    ) -> None:
        """Отправляет письмо через Resend (если задан ключ) или SMTP. С таймаутом."""
        if not EmailService.is_configured():
            logger.warning("Email transport not configured — skipping email to %s", email)
            return

        from_address = EmailService._from_address()
        if settings.RESEND_API_KEY:
            await EmailService._send_via_resend(from_address, email, subject, html, attachments)
        else:
            await EmailService._send_via_smtp(from_address, email, subject, html, attachments)

    @staticmethod
    async def _send_via_resend(
        from_address: str,
        email: str,
        subject: str,
        html: str,
        attachments: list[EmailAttachment] | None = None,
    ) -> None:
        payload: dict = {"from": from_address, "to": [email], "subject": subject, "html": html}
        timeout = EMAIL_TIMEOUT_SECONDS
        if attachments:
            payload["attachments"] = [
                {"filename": a.filename, "content": base64.b64encode(a.content).decode("ascii")}
                for a in attachments
            ]
            timeout = EMAIL_ATTACHMENT_TIMEOUT_SECONDS

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                RESEND_ENDPOINT,
                headers={"Authorization": f"Bearer {settings.RESEND_API_KEY}"},
                json=payload,
            )
        if response.status_code >= 400:
            logger.error(
                "Resend rejected email to %s: %s %s", email, response.status_code, response.text
            )
            response.raise_for_status()
        logger.info("Email sent to %s via Resend", email)

    @staticmethod
    def _build_mime_message(
        from_address: str,
        email: str,
        subject: str,
        html: str,
        attachments: list[EmailAttachment] | None = None,
    ) -> MIMEMultipart:
        """Строит MIME-сообщение: alternative (html) без вложений, mixed (alternative + files) с ними."""
        alternative = MIMEMultipart("alternative")
        alternative.attach(MIMEText(html, "html", "utf-8"))

        if not attachments:
            msg = alternative
        else:
            msg = MIMEMultipart("mixed")
            msg.attach(alternative)
            for a in attachments:
                subtype = a.mime_type.split("/", 1)[-1]
                part = MIMEApplication(a.content, _subtype=subtype)
                part.add_header(
                    "Content-Disposition", "attachment", filename=a.filename
                )
                msg.attach(part)

        msg["Subject"] = subject
        msg["From"] = from_address
        msg["To"] = email
        return msg

    @staticmethod
    async def _send_via_smtp(
        from_address: str,
        email: str,
        subject: str,
        html: str,
        attachments: list[EmailAttachment] | None = None,
    ) -> None:
        msg = EmailService._build_mime_message(from_address, email, subject, html, attachments)
        await aiosmtplib.send(
            msg,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USER,
            password=settings.SMTP_PASSWORD,
            start_tls=True,
            timeout=EMAIL_TIMEOUT_SECONDS,
        )
        logger.info("Email sent to %s via SMTP", email)

    @staticmethod
    def _build_credentials_html(email: str, password: str) -> str:
        login_url = f"{settings.FRONTEND_URL}/auth/login"
        safe_email = escape(email)
        safe_password = escape(password)
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
      <p>🔑 <strong>Логин (email):</strong> {safe_email}</p>
      <p>🔒 <strong>Пароль:</strong> {safe_password}</p>
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
        html = EmailService._build_credentials_html(email, password)
        await EmailService._send(email, "🎉 Ваш доступ к курсу — Lucy Nails Academy", html)

    @staticmethod
    def _build_reset_html(reset_url: str) -> str:
        safe_url = escape(reset_url, quote=True)
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
    .header h1 {{ color: #fff; margin: 0; font-size: 24px; letter-spacing: 0.5px; }}
    .body {{ padding: 36px 32px; }}
    .body p {{ color: #444; font-size: 15px; line-height: 1.6; }}
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
    <h1>Сброс пароля — Lucy Nails Academy</h1>
  </div>
  <div class="body">
    <p>Вы запросили сброс пароля. Нажмите кнопку ниже, чтобы задать новый пароль. Ссылка действует ограниченное время.</p>
    <p style="text-align:center; margin-top:28px;">
      <a href="{safe_url}" class="btn">Сбросить пароль →</a>
    </p>
    <p style="color:#999; font-size:13px; margin-top:24px;">Если вы не запрашивали сброс — просто проигнорируйте это письмо, пароль останется прежним.</p>
  </div>
  <div class="footer">
    Lucy Nails Academy
  </div>
</div>
</body>
</html>
"""

    @staticmethod
    async def send_password_reset(email: str, reset_url: str) -> None:
        """Отправляет письмо со ссылкой на сброс пароля."""
        html = EmailService._build_reset_html(reset_url)
        await EmailService._send(email, "Сброс пароля — Lucy Nails Academy", html)

    @staticmethod
    def _build_certificate_html(
        student_name: str, course_title: str, certificate_number: str, verify_url: str
    ) -> str:
        safe_name = escape(student_name)
        safe_course_title = escape(course_title)
        safe_certificate_number = escape(certificate_number)
        safe_verify_url = escape(verify_url, quote=True)
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
    <h1>🎓 Поздравляем, {safe_name}!</h1>
    <p>Вы прошли курс до конца</p>
  </div>
  <div class="body">
    <p>Вы успешно прошли курс «{safe_course_title}». Ваш именной сертификат готов!</p>
    <div class="creds">
      <p>🏆 <strong>Сертификат № {safe_certificate_number}</strong></p>
    </div>
    <p style="text-align:center; margin-top:28px;">
      <a href="{safe_verify_url}" class="btn">Посмотреть сертификат →</a>
    </p>
    <p style="color:#999; font-size:13px; margin-top:24px;">PDF-версия сертификата — во вложении к этому письму. Поделитесь достижением в соцсетях!</p>
  </div>
  <div class="footer">
    © 2025 Lucy Nails Academy
  </div>
</div>
</body>
</html>
"""

    @staticmethod
    async def send_certificate(
        email: str,
        student_name: str,
        course_title: str,
        certificate_number: str,
        verify_url: str,
        pdf_bytes: bytes,
    ) -> None:
        """Отправляет письмо с поздравлением и PDF-сертификатом во вложении."""
        html = EmailService._build_certificate_html(
            student_name, course_title, certificate_number, verify_url
        )
        attachment = EmailAttachment(
            filename=f"Lucy-Nails-Certificate-{certificate_number}.pdf", content=pdf_bytes
        )
        await EmailService._send(
            email, "🎓 Ваш сертификат — Lucy Nails Academy", html, [attachment]
        )
