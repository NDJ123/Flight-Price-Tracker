"""
Email notification service for price alerts.
Uses Resend (resend.com) to deliver alert emails.

Setup:
  1. Sign up at resend.com
  2. Get your API key
  3. Set RESEND_API_KEY environment variable
  4. Set RESEND_FROM_EMAIL to your verified sender (or use default onboarding address)
"""

import os
import logging
import resend

logger = logging.getLogger(__name__)

# Configure Resend
resend.api_key = os.getenv("RESEND_API_KEY", "")
FROM_EMAIL = os.getenv("RESEND_FROM_EMAIL", "onboarding@resend.dev")


def is_configured() -> bool:
    """Check if email service is configured."""
    return bool(resend.api_key)


def send_price_alert(
    to_email: str,
    origin_city: str,
    destination_city: str,
    origin_code: str,
    destination_code: str,
    target_price: float,
    current_price: float,
    airline_name: str = None,
) -> bool:
    """
    Send a price alert email notification.

    Returns True if sent successfully, False otherwise.
    """
    if not is_configured():
        logger.warning("Resend API key not configured — skipping email send")
        return False

    savings = target_price - current_price
    airline_text = f" on {airline_name}" if airline_name else ""

    subject = f"Price Alert: {origin_code} to {destination_code} dropped to ${current_price:.0f}!"

    html_body = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="background: linear-gradient(135deg, #0a3560, #0f4c81, #1a6bb5); padding: 24px; border-radius: 12px 12px 0 0; text-align: center;">
            <h1 style="color: white; margin: 0; font-size: 24px;">SkyWatch</h1>
            <p style="color: rgba(255,255,255,0.8); margin: 4px 0 0; font-size: 14px;">Flight Price Alert</p>
        </div>

        <div style="background: white; padding: 32px; border: 1px solid #e2e8f0; border-top: none;">
            <div style="background: #f0fff4; border: 1px solid #c6f6d5; border-radius: 8px; padding: 20px; margin-bottom: 24px; text-align: center;">
                <p style="color: #38a169; font-size: 14px; margin: 0 0 8px; font-weight: 600;">PRICE DROP DETECTED</p>
                <p style="color: #2d3748; font-size: 32px; font-weight: 700; margin: 0;">${current_price:.0f}</p>
                <p style="color: #38a169; font-size: 14px; margin: 4px 0 0;">${savings:.0f} below your target of ${target_price:.0f}</p>
            </div>

            <table style="width: 100%; border-collapse: collapse; margin-bottom: 24px;">
                <tr>
                    <td style="padding: 12px 0; border-bottom: 1px solid #e2e8f0; color: #718096; font-size: 14px;">Route</td>
                    <td style="padding: 12px 0; border-bottom: 1px solid #e2e8f0; font-weight: 600; text-align: right;">
                        {origin_city} ({origin_code}) &rarr; {destination_city} ({destination_code})
                    </td>
                </tr>
                <tr>
                    <td style="padding: 12px 0; border-bottom: 1px solid #e2e8f0; color: #718096; font-size: 14px;">Current Price</td>
                    <td style="padding: 12px 0; border-bottom: 1px solid #e2e8f0; font-weight: 700; color: #38a169; text-align: right;">${current_price:.2f}</td>
                </tr>
                <tr>
                    <td style="padding: 12px 0; border-bottom: 1px solid #e2e8f0; color: #718096; font-size: 14px;">Your Target</td>
                    <td style="padding: 12px 0; border-bottom: 1px solid #e2e8f0; font-weight: 600; text-align: right;">${target_price:.2f}</td>
                </tr>
                {"<tr><td style='padding: 12px 0; border-bottom: 1px solid #e2e8f0; color: #718096; font-size: 14px;'>Airline</td><td style='padding: 12px 0; border-bottom: 1px solid #e2e8f0; font-weight: 600; text-align: right;'>" + airline_name + "</td></tr>" if airline_name else ""}
            </table>

            <p style="color: #718096; font-size: 13px; line-height: 1.6;">
                This alert was triggered because the price for your watched route dropped below your target price.
                Prices can change quickly, so we recommend booking soon if this fare works for you.
            </p>
        </div>

        <div style="background: #f8fafc; padding: 16px; border-radius: 0 0 12px 12px; border: 1px solid #e2e8f0; border-top: none; text-align: center;">
            <p style="color: #a0aec0; font-size: 12px; margin: 0;">
                SkyWatch Flight Price Monitor &mdash; Monitoring oneworld Alliance Airlines
            </p>
        </div>
    </div>
    """

    try:
        params = {
            "from": f"SkyWatch Alerts <{FROM_EMAIL}>",
            "to": [to_email],
            "subject": subject,
            "html": html_body,
        }

        email = resend.Emails.send(params)
        logger.info(f"Price alert email sent to {to_email} (id: {email.get('id', 'unknown')})")
        return True

    except Exception as e:
        logger.error(f"Failed to send alert email to {to_email}: {e}")
        return False


def send_alert_confirmation(
    to_email: str,
    origin_city: str,
    destination_city: str,
    origin_code: str,
    destination_code: str,
    target_price: float,
) -> bool:
    """
    Send a confirmation email when a user creates a new price alert.

    Returns True if sent successfully, False otherwise.
    """
    if not is_configured():
        logger.warning("Resend API key not configured — skipping confirmation email")
        return False

    subject = f"Alert Confirmed: {origin_code} to {destination_code} under ${target_price:.0f}"

    html_body = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="background: linear-gradient(135deg, #0a3560, #0f4c81, #1a6bb5); padding: 24px; border-radius: 12px 12px 0 0; text-align: center;">
            <h1 style="color: white; margin: 0; font-size: 24px;">SkyWatch</h1>
            <p style="color: rgba(255,255,255,0.8); margin: 4px 0 0; font-size: 14px;">Alert Confirmation</p>
        </div>

        <div style="background: white; padding: 32px; border: 1px solid #e2e8f0; border-top: none;">
            <div style="background: #ebf5ff; border: 1px solid #bee3f8; border-radius: 8px; padding: 20px; margin-bottom: 24px; text-align: center;">
                <p style="color: #0f4c81; font-size: 14px; margin: 0 0 8px; font-weight: 600;">ALERT CREATED</p>
                <p style="color: #2d3748; font-size: 20px; font-weight: 700; margin: 0;">
                    {origin_city} ({origin_code}) &rarr; {destination_city} ({destination_code})
                </p>
            </div>

            <table style="width: 100%; border-collapse: collapse; margin-bottom: 24px;">
                <tr>
                    <td style="padding: 12px 0; border-bottom: 1px solid #e2e8f0; color: #718096; font-size: 14px;">Route</td>
                    <td style="padding: 12px 0; border-bottom: 1px solid #e2e8f0; font-weight: 600; text-align: right;">
                        {origin_city} ({origin_code}) &rarr; {destination_city} ({destination_code})
                    </td>
                </tr>
                <tr>
                    <td style="padding: 12px 0; border-bottom: 1px solid #e2e8f0; color: #718096; font-size: 14px;">Target Price</td>
                    <td style="padding: 12px 0; border-bottom: 1px solid #e2e8f0; font-weight: 700; color: #0f4c81; text-align: right;">${target_price:.2f}</td>
                </tr>
                <tr>
                    <td style="padding: 12px 0; border-bottom: 1px solid #e2e8f0; color: #718096; font-size: 14px;">Status</td>
                    <td style="padding: 12px 0; border-bottom: 1px solid #e2e8f0; font-weight: 600; color: #38a169; text-align: right;">Active — Monitoring</td>
                </tr>
            </table>

            <p style="color: #718096; font-size: 13px; line-height: 1.6;">
                Your price alert is now active. We check prices every hour and will email you as soon as
                the fare for this route drops to <strong>${target_price:.0f}</strong> or below.
            </p>
        </div>

        <div style="background: #f8fafc; padding: 16px; border-radius: 0 0 12px 12px; border: 1px solid #e2e8f0; border-top: none; text-align: center;">
            <p style="color: #a0aec0; font-size: 12px; margin: 0;">
                SkyWatch Flight Price Monitor &mdash; Monitoring oneworld Alliance Airlines
            </p>
        </div>
    </div>
    """

    try:
        params = {
            "from": f"SkyWatch Alerts <{FROM_EMAIL}>",
            "to": [to_email],
            "subject": subject,
            "html": html_body,
        }

        email = resend.Emails.send(params)
        logger.info(f"Alert confirmation email sent to {to_email} (id: {email.get('id', 'unknown')})")
        return True

    except Exception as e:
        logger.error(f"Failed to send confirmation email to {to_email}: {e}")
        return False
