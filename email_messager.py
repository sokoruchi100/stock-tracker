import os
from dotenv import load_dotenv
import smtplib
from email.mime.text import MIMEText

load_dotenv()

def determine_risk_message(risk_score):
    risk_score = float(risk_score)
    if risk_score >= 8:
        return "🚨 High Risk: Reduce aggressively (raise cash, hedge)"
    elif risk_score >= 7:
        return "🔴 Reduce Risk: Trim positions, no new buys"
    elif risk_score >= 5:
        return "🟠 Neutral: Hold, selective buying only"
    elif risk_score >= 3:
        return "🟡 Accumulate: Start adding gradually"
    else:
        return "🟢 Aggressive Buy: Deploy cash heavily"

def determine_valued_message(valued_score):
    valued_score = float(valued_score)
    if valued_score > 40:
        return "🚨 Extremely Overvalued: Reduce aggressively"
    elif valued_score > 25:
        return "🔴 Overvalued: Trim risk, avoid new buys"
    elif valued_score > 10:
        return "🟠 Slightly Overvalued: Be selective"
    elif valued_score > -10:
        return "🟡 Fair Value: Neutral positioning"
    elif valued_score > -25:
        return "🟢 Undervalued: Start adding"
    else:
        return "💰 Deep Value: Aggressive buying zone"

def send_alert(risk_score, overvalued_score):
    risk_message = determine_risk_message(risk_score)
    valued_message = determine_valued_message(overvalued_score)
    msg = MIMEText(f"You have a new notification from the Stock Tracker!\n\nRisk Score: {risk_score}\nRisk Message: {risk_message}\n\nValued Score: {overvalued_score}\nValued Message: {valued_message}")
    msg["Subject"] = "Stock Tracker Notification!"
    msg["From"] = os.environ["PERSONAL_EMAIL_ADDRESS"]
    msg["To"] = os.environ["TARGET_EMAIL_ADDRESS"]

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(
            os.environ["PERSONAL_EMAIL_ADDRESS"],
            os.environ["PERSONAL_EMAIL_APP_PASSWORD"]
        )
        server.send_message(msg)

if __name__ == "__main__":
    send_alert(0.65, 75)