import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from app.config import settings

logger = logging.getLogger(__name__)


def send_magic_link_email(to_email: str, magic_url: str, pseudo: str = None) -> bool:
    """
    Envoie un email contenant le magic link de connexion.
    Retourne True si l'envoi a réussi, False sinon.
    """
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        logger.warning("SMTP non configuré — magic link non envoyé")
        return False

    name = pseudo or "citoyen"

    html_body = f"""
<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin:0;padding:0;background:#f4f4f4;font-family:'Courier New',monospace;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f4f4;padding:40px 0;">
    <tr>
      <td align="center">
        <table width="560" cellpadding="0" cellspacing="0" style="background:#ffffff;border:1px solid #e0e0e0;">

          <!-- Header -->
          <tr>
            <td style="background:#1a1a2e;padding:32px 40px;text-align:center;">
              <p style="margin:0;color:#c0392b;font-size:11px;letter-spacing:4px;text-transform:uppercase;font-weight:bold;">
                GoV Gen Z Madagascar
              </p>
              <h1 style="margin:8px 0 0;color:#ffffff;font-size:22px;letter-spacing:3px;text-transform:uppercase;">
                CIVITECH
              </h1>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding:40px;">
              <p style="color:#333;font-size:13px;line-height:1.8;margin:0 0 16px;">
                Bonjour <strong>{name}</strong>,
              </p>
              <p style="color:#333;font-size:13px;line-height:1.8;margin:0 0 32px;">
                Tu as demandé un lien de connexion à <strong>Civitech</strong>.<br>
                Clique sur le bouton ci-dessous pour accéder à ton compte.
              </p>

              <!-- CTA -->
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td align="center" style="padding:16px 0 32px;">
                    <a href="{magic_url}"
                       style="display:inline-block;background:#c0392b;color:#ffffff;
                              text-decoration:none;padding:14px 40px;
                              font-size:11px;letter-spacing:3px;text-transform:uppercase;
                              font-weight:bold;font-family:'Courier New',monospace;">
                      SE CONNECTER
                    </a>
                  </td>
                </tr>
              </table>

              <p style="color:#888;font-size:11px;line-height:1.8;margin:0 0 8px;">
                ⏱ Ce lien expire dans <strong>15 minutes</strong> et ne peut être utilisé qu'<strong>une seule fois</strong>.
              </p>
              <p style="color:#888;font-size:11px;line-height:1.8;margin:0 0 32px;">
                Si tu n'as pas demandé ce lien, ignore cet email. Ton compte est en sécurité.
              </p>

              <hr style="border:none;border-top:1px solid #e0e0e0;margin:0 0 24px;">

              <p style="color:#aaa;font-size:10px;line-height:1.6;margin:0;word-break:break-all;">
                Lien alternatif : <a href="{magic_url}" style="color:#c0392b;">{magic_url}</a>
              </p>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="background:#f9f9f9;padding:20px 40px;text-align:center;border-top:1px solid #e0e0e0;">
              <p style="margin:0;color:#aaa;font-size:10px;letter-spacing:1px;">
                CIVITECH — OBSERVATOIRE CITOYEN MADAGASCAR<br>
                <a href="https://civitech.genzgov.org" style="color:#aaa;">civitech.genzgov.org</a>
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""

    text_body = f"""Bonjour {name},

Tu as demandé un lien de connexion à Civitech.

Clique ici pour te connecter :
{magic_url}

Ce lien expire dans 15 minutes et ne peut être utilisé qu'une seule fois.

Si tu n'as pas demandé ce lien, ignore cet email.

— Civitech GoV Gen Z Madagascar
"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "🔐 Ton lien de connexion Civitech"
    msg["From"] = f"{settings.EMAIL_FROM_NAME} <{settings.SMTP_USER}>"
    msg["To"] = to_email

    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_USER, to_email, msg.as_string())
        logger.info(f"Magic link envoyé à {to_email}")
        return True
    except Exception as e:
        logger.error(f"Erreur envoi email à {to_email}: {e}")
        return False
