**WP Ukraine WebGuard**  is an automation tool designed to search websites through Google, collect emails from those sites, scan for WordPress vulnerabilities using WPScan, and send email alerts to site administrators if vulnerabilities are found.

The script was developed not only for Ukraine but for any country, as it allows you to scan and secure any domain by simply specifying the domain. It is crucial to address vulnerabilities in websites because flaws such as Remote Code Execution (RCE), Cross-Site Scripting (XSS), and others can lead to critical services becoming unavailable, which is particularly devastating in a state of war. Moreover, a simple entry point for an attacker through an insecure website can grant lateral escalation into other devices and systems, including medical equipment, potentially disabling their operation and threatening lives.

## Main Features: 
 
- **Automated Google Search** : The script performs custom searches on Google to find websites with specific domains and keywords (e.g., ".au" and "university").
 
- **Email Collection** : It automatically extracts available emails from the identified websites.
 
- **Vulnerability Scanning** : WPScan is used to scan the websites for security vulnerabilities in plugins and configurations.
 
- **Email Alerts** : If vulnerabilities are found, the tool automatically sends an email to the administrators, offering assistance to fix the issues and alerting them to the security risks.

## How It Works: 

1. The script searches Google for sites using a specific domain and keyword.

2. For each website found, it collects available email addresses.

3. WPScan is run to check for vulnerabilities in WordPress installations.

4. If vulnerabilities are found, an email is sent to the website administrators with a report and suggestions for fixing the issues.

## Requirements: 
 
- **WPScan** : Make sure WPScan is installed and configured correctly.
 
- **Email Setup** : The email used for sending reports should not be a Gmail account due to Google's security policies. You should use a custom email server (like `email-ssl.com.br`).
 
- **Proxychains (Optional)** : To avoid Google blocking your requests, you can use proxies or Tor through Proxychains.

## Usage: 

1. Clone this repository.

2. Set up your environment variables, including your email and password in the code.
 
3. Run the script by providing a domain and keyword:

### Example Command: 


```Copiar código
python3 wpukrainewebguard.py --domain au --keyword university
```

### Using on Kali or Parrot OS 
If you're using **Kali Linux**  or **Parrot OS** , there's no need to install WPScan manually, as it comes pre-installed with these distributions. You can skip the WPScan installation step and proceed directly with running the script.
Here’s how to confirm WPScan is installed:
 
1. Open a terminal and check the WPScan version:


```Copiar código
wpscan --version
```
 
2. If WPScan is installed correctly, you should see the version number. You can now proceed with running the script without additional setup.

### Requirements 

For Python dependencies, run:


```Copiar código
pip install -r requirements.txt
```
Now you're ready to run the script using the pre-installed WPScan on **Kali Linux**  or **Parrot OS** !


## Important: 
 
- **Avoid Using Gmail** : Use a custom email provider for sending reports, as Google blocks automated email sending from Gmail.
 
- **CAPTCHA and Blocking** : To prevent Google from blocking requests or showing CAPTCHAs, it's recommended to space out your requests or use proxies.

## Contribution: 

Feel free to contribute by submitting pull requests or opening issues for any improvements.
