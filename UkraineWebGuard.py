import requests
from bs4 import BeautifulSoup
import argparse
import subprocess
import os
import re
from colorama import Fore, Style
from tqdm import tqdm
import time
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from concurrent.futures import ThreadPoolExecutor, TimeoutError, as_completed

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

# Limit the scraping time per website to 60 seconds
SCRAPING_TIMEOUT = 60

# Function to perform Google search and collect URLs based on the domain and keyword
def search_google(domain, keyword):
    unique_urls = []
    for page in range(2, 4):
        url = f'https://www.google.com/search?q=site%3A"{domain}"%20inurl%3Awp-content%2F%20intext%3A{keyword}&start={page * 10}'
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        search_results = soup.find_all('a')
        for result in search_results:
            url = result['href']
            if url.startswith('/url?q='):
                url = url[7:]
                url = url.split('&')[0]
                if not url.startswith('http'):
                    continue
                url = url.split('wp-content')[0]
                if 'google' not in url and url not in unique_urls:
                    unique_urls.append(url)
        time.sleep(2)

    print(Fore.GREEN + "\nScanning websites..." + Style.RESET_ALL)
    emails_by_url = {}

    # Using ThreadPoolExecutor to parallelize the scraping process
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_url = {executor.submit(scrape_site, url): url for url in unique_urls}
        
        for future in tqdm(as_completed(future_to_url), total=len(future_to_url), desc="Progress", unit="website"):
            url = future_to_url[future]
            try:
                emails = future.result(timeout=SCRAPING_TIMEOUT)  # Limits scraping time per site
                if emails:
                    emails_by_url[url] = emails
            except TimeoutError:
                print(Fore.RED + f"\nScraping timed out for website {url}, skipping..." + Style.RESET_ALL)
            except Exception as e:
                print(Fore.RED + f"\nFailed to scrape {url}: {str(e)}" + Style.RESET_ALL)

    return emails_by_url

# Function to scrape emails from a given site
def scrape_site(site_url):
    if not site_url.startswith("http"):
        return []
    
    site_name = site_url.split('//')[1].split('/')[0]
    output_file = f'{site_name}.txt'
    
    with open(output_file, 'w') as file:
        subprocess.run(['curl', '-s', site_url], stdout=file)
    
    emails = []
    with open(output_file, 'r', encoding='utf-8', errors='ignore') as file:
        file_content = file.read()
        emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b', file_content)
        emails = [email for email in emails if len(email) > 14 and not email.startswith('cached@')]
    
    os.remove(output_file)
    
    return emails

# Function to run WPScan for a given site
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
        '-o', output_file
    ])

# Function to scan a site, check for vulnerabilities, and send an email if vulnerabilities are found
def scan_and_email(site_url, emails, token):
    site_name = site_url.split('//')[1].split('/')[0]
    output_file = f'{site_name}_report.txt'
    print(Fore.GREEN + f"\nRunning WPScan on website {site_url}..." + Style.RESET_ALL)
    run_wpscan(site_url, output_file, token)
    if os.path.exists(output_file):
        with open(output_file, 'r', encoding='utf-8', errors='ignore') as file:
            file_content = file.read()
            if any(vuln in file_content for vuln in ['vulnerability', 'vulnerabilities', 'Directory listing is enabled']):
                for email in emails:
                    send_email(site_url, email, output_file)
            else:
                print(Fore.RED + f"No vulnerabilities found for website {site_url}. Skipping..." + Style.RESET_ALL)

# Function to send email with the vulnerability report
def send_email(site_url, recipient_email, output_file):
    sender_email = 'your-email@example.com'  # Replace with your email
    sender_password = 'your-password'  # Replace with your email password
    subject = 'Potential Vulnerabilities Identified on Your Website'

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Subject'] = subject

    body = f"""Dear Website Owner,

I hope this message finds you well. As part of my efforts to enhance online security, I have identified some potential vulnerabilities on your website {site_url}. 

Attached to this email is a report that contains the vulnerabilities found during the scan. My intention is to provide you with valuable insights that can help protect your website and users from possible cyber threats.

Please note that this analysis was conducted using publicly available information, and all findings were obtained legally. 

If you would like assistance in resolving these issues or have any questions, feel free to reply to this email.

Best regards,
Security Researcher
"""
    msg.attach(MIMEText(body, 'plain'))

    with open(output_file, 'rb') as attachment:
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(attachment.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f"attachment; filename= {output_file}")
        msg.attach(part)
    
    try:
        server = smtplib.SMTP('your-smtp-server.com', 587)  # Replace with your SMTP server
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, recipient_email, msg.as_string())
        server.quit()
        print(f"Email sent successfully to {recipient_email} for website {site_url}")
    except smtplib.SMTPException as e:
        print(f"Failed to send email to {recipient_email} for website {site_url}. Error: {str(e)}")

# Main function to parse arguments and initiate the scanning and email process
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Scan websites for vulnerabilities.')
    parser.add_argument('-d', '--domain', required=True, help='The domain to scan')
    parser.add_argument('-k', '--keyword', required=True, help='The keyword to look for')
    args = parser.parse_args()

    emails_by_url = search_google(args.domain, args.keyword)

    with ThreadPoolExecutor(max_workers=3) as executor:
        for site_url, emails in emails_by_url.items():
            token = TOKENS[0]  # Using the first token for simplicity, you can rotate them
            executor.submit(scan_and_email, site_url, emails, token)
