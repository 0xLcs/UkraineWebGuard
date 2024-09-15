import requests
from bs4 import BeautifulSoup
import argparse
import subprocess
import os
import re
import logging
from tqdm import tqdm
import time
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from concurrent.futures import ThreadPoolExecutor, TimeoutError, as_completed
from email.utils import parseaddr
import json
from colorama import init, Fore, Style

# Initialize colorama
init(autoreset=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,  # Change to DEBUG for more detailed output
    format='%(asctime)s - %(levelname)s - %(message)s'
)

print('\n' * 3)
print("  _    _ _              _             __          __  _      _____                     _ ")
print(" | |  | | |            (_)            \ \        / / | |    / ____|                   | |")
print(" | |  | | | ___ __ __ _ _ _ __   ___   \ \  /\  / /__| |__ | |  __ _   _  __ _ _ __ __| |")
print(" | |  | | |/ / '__/ _` | | '_ \ / _ \   \ \/  \/ / _ \ '_ \| | |_ | | | |/ _` | '__/ _` |")
print(" | |__| |   <| | | (_| | | | | |  __/    \  /\  /  __/ |_) | |__| | |_| | (_| | | | (_| |")
print("  \____/|_|\_\_|  \__,_|_|_| |_|\___|     \/  \/ \___|_.__/ \_____|\__,_|\__,_|_|  \__,_|")
print('\n' * 3)
print('by Lucas F. Morato')
print('Version 2.0\n')

# Replace these tokens with your actual WPScan API tokens (Get in https://wpscan.com/pricing/)
TOKENS = [
    'PUT_YOUR_TOKENS_HERE',
    'PUT_YOUR_TOKENS_HERE',
    'PUT_YOUR_TOKENS_HERE'
]

# Time limit for scraping in seconds
SCRAPING_TIMEOUT = 60

# Email pattern and invalid extensions
EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b')
INVALID_EMAIL_EXTENSIONS = ['.png', '.jpg', '.jpeg', '.webp']

def is_valid_email(email):
    """Check if an email is valid and does not have an invalid extension."""
    email_address = parseaddr(email)[1]
    if not email_address:
        return False
    local_part, _, domain_part = email_address.partition('@')
    if not domain_part:
        return False
    for ext in INVALID_EMAIL_EXTENSIONS:
        if domain_part.lower().endswith(ext):
            return False
    return True

def search_google(domain, keyword):
    unique_urls = []
    for page in range(2, 4):
        url = f'https://www.google.com/search?q=site%3A"{domain}"%20inurl%3Awp-content%2F%20intext%3A{keyword}&start={page * 10}'
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        search_results = soup.find_all('a')
        for result in search_results:
            url = result.get('href', '')
            if url.startswith('/url?q='):
                url = url[7:]
                url = url.split('&')[0]
                if not url.startswith('http'):
                    continue
                url = url.split('wp-content')[0]
                if 'google' not in url and url not in unique_urls:
                    unique_urls.append(url)
        time.sleep(2)

    print(Fore.GREEN + "\nScanning websites...\n" + Style.RESET_ALL)
    emails_by_url = {}

    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_url = {executor.submit(scrape_site, url): url for url in unique_urls}

        for future in tqdm(as_completed(future_to_url), total=len(future_to_url), desc=Fore.YELLOW + "Progress" + Style.RESET_ALL, unit="website"):
            url = future_to_url[future]
            try:
                emails = future.result(timeout=SCRAPING_TIMEOUT)
                if emails:
                    valid_emails = list(set([email for email in emails if is_valid_email(email)]))
                    if valid_emails:
                        emails_by_url[url] = valid_emails
                        print(Fore.BLUE + f"\nEmails found for {url}:\n" + Style.RESET_ALL)
                        for email in valid_emails:
                            print(Fore.CYAN + email + Style.RESET_ALL)
                else:
                    print(Fore.YELLOW + f"\nNo emails found for {url}." + Style.RESET_ALL)
            except TimeoutError:
                print(Fore.RED + f"\nScraping timed out for website {url}, skipping..." + Style.RESET_ALL)
            except Exception as e:
                print(Fore.RED + f"\nFailed to scrape {url}: {str(e)}" + Style.RESET_ALL)

    return emails_by_url

def scrape_site(site_url):
    emails = []
    if not site_url.startswith("http"):
        return emails
    try:
        logging.info(f"Scraping site: {site_url}")
        response = requests.get(site_url, timeout=10)
        response.raise_for_status()
        emails = EMAIL_PATTERN.findall(response.text)
        return emails
    except requests.RequestException as e:
        logging.error(f"Failed to scrape {site_url}: {e}")
        return emails

def run_wpscan(site_url, output_file, token):
    subprocess.run([
        'wpscan',
        '--url', site_url,
        '--api-token', token,
        '--no-banner',
        '--random-user-agent',
        '--ignore-main-redirect',
        '--disable-tls-checks',
        '--no-update',
        '--request-timeout', '30',
        '--max-threads', '10',
        '--enumerate', 'p',
        '--format', 'json',
        '-o', output_file
    ])

def parse_wpscan_output(output_file):
    vulnerabilities = []
    try:
        with open(output_file, 'r', encoding='utf-8') as file:
            data = json.load(file)
        for plugin in data.get('plugins', {}).values():
            for vuln in plugin.get('vulnerabilities', []):
                vulnerabilities.append({
                    'title': vuln.get('title'),
                    'severity': vuln.get('cvss', {}).get('score', 'Unknown'),
                    'references': vuln.get('references', {})
                })
    except json.JSONDecodeError as e:
        logging.error(f"Error parsing WPScan output JSON: {e}")
    return vulnerabilities

def scan_and_email(site_url, emails, token):
    site_name = site_url.split('//')[1].split('/')[0]
    output_file = f'{site_name}_report.json'
    print(Fore.GREEN + f"\nRunning WPScan on website {site_url}...\n" + Style.RESET_ALL)
    run_wpscan(site_url, output_file, token)
    if os.path.exists(output_file):
        vulnerabilities = parse_wpscan_output(output_file)
        if vulnerabilities:
            print(Fore.RED + f"Vulnerabilities found on {site_url}!\n" + Style.RESET_ALL)
            for email in emails:
                send_email(site_url, email, output_file, vulnerabilities)
            print(Fore.GREEN + f"Emails sent for website {site_url}.\n" + Style.RESET_ALL)
        else:
            print(Fore.YELLOW + f"No vulnerabilities found for website {site_url}. Skipping email.\n" + Style.RESET_ALL)
        # Remove the output file
        os.remove(output_file)

def send_email(site_url, recipient_email, output_file, vulnerabilities):
    # Insert your email credentials here
    sender_email = 'your-email@example.com'
    sender_password = 'your-password'
    smtp_server = 'your-smtp-server.com'
    smtp_port = 587  # Use 465 if your SMTP server uses SSL

    subject = 'Potential Vulnerabilities Identified on Your Website'

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Subject'] = subject

    # Build the email body
    body = f"""Dear Website Owner,

I hope this message finds you well. As part of my efforts to enhance online security, I have identified some potential vulnerabilities on your website {site_url}.

Attached to this email is a report that contains the vulnerabilities found during the scan. My intention is to provide you with valuable insights that can help protect your website and users from possible cyber threats.

Please note that this analysis was conducted using publicly available information, and all findings were obtained legally.

If you would like assistance in resolving these issues or have any questions, feel free to reply to this email.

Best regards,
Security Researcher
"""
    msg.attach(MIMEText(body, 'plain'))

    # Attach the report
    with open(output_file, 'rb') as attachment:
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(attachment.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f"attachment; filename={output_file}")
        msg.attach(part)

    try:
        # Secure SMTP connection
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            # If using SSL on port 465, use smtplib.SMTP_SSL
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, recipient_email, msg.as_string())
        print(Fore.GREEN + f"Email successfully sent to {recipient_email} for website {site_url}\n" + Style.RESET_ALL)
    except smtplib.SMTPException as e:
        print(Fore.RED + f"Failed to send email to {recipient_email} for website {site_url}. Error: {str(e)}\n" + Style.RESET_ALL)

def get_next_token():
    get_next_token.counter = (get_next_token.counter + 1) % len(TOKENS)
    return TOKENS[get_next_token.counter]

get_next_token.counter = -1  # Initialize the counter

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Scan websites for vulnerabilities.')
    parser.add_argument('-d', '--domain', required=True, help='The domain to scan')
    parser.add_argument('-k', '--keyword', required=True, help='The keyword to look for')
    args = parser.parse_args()

    emails_by_url = search_google(args.domain, args.keyword)

    with ThreadPoolExecutor(max_workers=3) as executor:
        for site_url, emails in emails_by_url.items():
            token = get_next_token()
            executor.submit(scan_and_email, site_url, emails, token)
