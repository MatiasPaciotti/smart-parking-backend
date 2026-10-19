import logging
import os
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr

logger = logging.getLogger(__name__)


class EmailDeliveryError(Exception):
    pass


def enviar_codigo_verificacion(destino: str, codigo: str) -> None:
    mail_user = os.getenv("MAIL_USER")
    mail_pass = os.getenv("MAIL_PASS")
    if not mail_user or not mail_pass:
        raise EmailDeliveryError("Falta configurar MAIL_USER o MAIL_PASS")

    message = EmailMessage()
    message["Subject"] = "Verificá tu cuenta de Smart Parking UNSAM"
    message["From"] = formataddr(
        ("Smart Parking UNSAM", "smart.parking.unsam@gmail.com")
    )
    message["To"] = destino
    message.set_content(
        f"Tu código de verificación es: {codigo}\n\n"
        "Ingresalo en Smart Parking UNSAM dentro de los próximos 10 minutos. "
        "Si no creaste una cuenta, podés ignorar este correo."
    )
    message.add_alternative(
        "<html><body>"
        "<p>¡Hola! Para verificar tu cuenta de Smart Parking UNSAM, ingresá este código:</p>"
        f"<p style='font-size: 24px; font-weight: bold'>{codigo}</p>"
        "<p>El código vence en 10 minutos. Si no creaste una cuenta, podés ignorar este correo.</p>"
        "</body></html>",
        subtype="html",
    )

    try:
        logger.info(f"Intentando enviar email de verificación a {destino}")
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=15) as server:
            server.starttls(context=ssl.create_default_context())
            server.login(mail_user, mail_pass)
            server.send_message(message)
        logger.info(f"Email enviado exitosamente a {destino}")
    except (OSError, smtplib.SMTPException) as error:
        logger.error(f"Error al enviar email: {error}", exc_info=True)
        raise EmailDeliveryError("No se pudo enviar el correo de verificación") from error