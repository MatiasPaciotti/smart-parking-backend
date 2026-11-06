import logging
import os

import httpx

logger = logging.getLogger(__name__)

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"
SENDER_NAME = "Smart Parking UNSAM"
SENDER_EMAIL = "smart.parking.unsam@gmail.com"


class EmailDeliveryError(Exception):
    pass


def enviar_codigo_verificacion(destino: str, codigo: str) -> None:
    api_key = os.getenv("BREVO_API_KEY")
    if not api_key:
        raise EmailDeliveryError("Falta configurar BREVO_API_KEY")

    payload = {
        "sender": {"name": SENDER_NAME, "email": SENDER_EMAIL},
        "to": [{"email": destino}],
        "subject": "Verificá tu cuenta de Smart Parking UNSAM",
        "textContent": (
            f"Tu código de verificación es: {codigo}\n\n"
            "Ingresalo en Smart Parking UNSAM dentro de los próximos 10 minutos. "
            "Si no creaste una cuenta, podés ignorar este correo."
        ),
        "htmlContent": (
            "<html><body>"
            "<p>¡Hola! Para verificar tu cuenta de Smart Parking UNSAM, ingresá este código:</p>"
            f"<p style='font-size: 24px; font-weight: bold'>{codigo}</p>"
            "<p>El código vence en 10 minutos. Si no creaste una cuenta, podés ignorar este correo.</p>"
            "</body></html>"
        ),
    }

    try:
        logger.info(f"Intentando enviar email de verificación a {destino}")
        response = httpx.post(
            BREVO_API_URL,
            headers={"api-key": api_key, "accept": "application/json"},
            json=payload,
            timeout=15,
        )
        response.raise_for_status()
        logger.info(f"Email enviado exitosamente a {destino}")
    except httpx.HTTPError as error:
        logger.error(f"Error al enviar email: {error}", exc_info=True)
        if isinstance(error, httpx.HTTPStatusError):
            logger.error(f"Respuesta de Brevo: {error.response.text}")
        raise EmailDeliveryError("No se pudo enviar el correo de verificación") from error
