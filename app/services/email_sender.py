
import os
from html import escape

import resend


class EmailSendingError(Exception):
    pass


def send_verification_email(email: str, code: str) -> None:
    """Envía el código de verificación por correo usando Resend."""
    api_key = os.getenv("RESEND_API_KEY")
    sender = os.getenv("EMAIL_FROM")

    if not api_key or not sender:
        raise EmailSendingError(
            "Falta configurar el proveedor de correo"
        )

    resend.api_key = api_key

    safe_code = escape(code)

    params = {
        "from": sender,
        "to": [email],
        "subject": "Verificá tu correo - Smart Parking UNSAM",
        "html": f"""
            <div style="font-family: Arial, sans-serif;">
                <h2>Verificación de correo electrónico</h2>
                <p>Recibimos una solicitud para verificar tu cuenta
                de Smart Parking UNSAM.</p>
                <p>Tu código de verificación es:</p>
                <p style="font-size: 28px; font-weight: bold;
                          letter-spacing: 6px;">
                    {safe_code}
                </p>
                <p>El código vence en 10 minutos.</p>
                <p>Si no solicitaste este código, podés ignorar
                este mensaje.</p>
            </div>
        """,
    }

    try:
        resend.Emails.send(params)
    except Exception as error:
        # No registramos la clave API ni el código de verificación.
        raise EmailSendingError(
            "No se pudo enviar el correo de verificación"
        ) from error
