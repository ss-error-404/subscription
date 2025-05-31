# Facebook Auto Register CLI Tool with Proxy Support and CSV Export

import argparse
import threading
from queue import Queue
import requests
import random
import string
import json
import hashlib
from faker import Faker
import sys
import csv
import os

fake = Faker()
session = requests.Session()

BANNER = """
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓           
> › Github :- @jatintiwari0 
> › By      :- JATIN TIWARI
> › Proxy Support Added by @coopers-lab
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛                
"""

def generate_random_string(length):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def get_mail_domains(proxy=None):
    try:
        resp = session.get("https://api.mail.tm/domains", proxies=proxy, timeout=10)
        if resp.ok:
            return resp.json().get('hydra:member', [])
    except Exception as e:
        print(f"[×] Mail domain error: {e}")
    return []

def create_mail_tm_account(proxy=None):
    domains = get_mail_domains(proxy)
    if not domains:
        return [None] * 5
    domain = random.choice(domains).get("domain")
    username = generate_random_string(10)
    password = fake.password()
    first_name = fake.first_name()
    last_name = fake.last_name()
    birthday = fake.date_of_birth(minimum_age=18, maximum_age=45)
    payload = {"address": f"{username}@{domain}", "password": password}
    try:
        resp = session.post("https://api.mail.tm/accounts", json=payload, proxies=proxy, timeout=10)
        if resp.status_code == 201:
            return f"{username}@{domain}", password, first_name, last_name, birthday
        else:
            print(f"[×] Account creation failed: {resp.text}")
    except Exception as e:
        print(f"[×] Account creation error: {e}")
    return [None] * 5

def register_facebook_account(email, password, first_name, last_name, birthday, proxy=None):
    api_key = '882a8490361da98702bf97a021ddc14d'
    secret = '62f8ce9f74b12f84c123cc23437a4a32'
    gender = random.choice(['M', 'F'])
    params = {
        'api_key': api_key,
        'attempt_login': True,
        'birthday': birthday.strftime('%Y-%m-%d'),
        'client_country_code': 'EN',
        'fb_api_caller_class': 'com.facebook.registration.protocol.RegisterAccountMethod',
        'fb_api_req_friendly_name': 'registerAccount',
        'firstname': first_name,
        'format': 'json',
        'gender': gender,
        'lastname': last_name,
        'email': email,
        'locale': 'en_US',
        'method': 'user.register',
        'password': password,
        'reg_instance': generate_random_string(32),
        'return_multiple_errors': True
    }
    sorted_items = sorted(params.items())
    base_str = ''.join(f"{k}={v}" for k, v in sorted_items)
    params['sig'] = hashlib.md5((base_str + secret).encode()).hexdigest()
    try:
        headers = {
            'User-Agent': '[FBAN/FB4A;FBAV/35.0.0.48.273;FBLC/en_US;FBPN/com.facebook.katana]'
        }
        response = session.post("https://b-api.facebook.com/method/user.register", data=params, headers=headers, proxies=proxy, timeout=15)
        data = response.json()
        if 'new_user_id' in data:
            user_data = {
                "email": email,
                "id": data['new_user_id'],
                "password": password,
                "name": f"{first_name} {last_name}",
                "birthday": str(birthday),
                "gender": gender,
                "token": data['session_info']['access_token']
            }
            print("""
----------- GENERATED -----------
EMAIL     : {email}
ID        : {id}
PASSWORD  : {password}
NAME      : {name}
BIRTHDAY  : {birthday}
GENDER    : {gender}
TOKEN     : {token}
----------- GENERATED -----------
""".format(**user_data))
            return user_data
        else:
            print(f"[×] Facebook Registration Failed: {data}")
    except Exception as e:
        print(f"[×] Facebook Registration Error: {e}")
    return None

def load_proxies(file_path):
    try:
        with open(file_path) as f:
            return [{'http': f'http://{line.strip()}', 'https': f'http://{line.strip()}'} for line in f if line.strip()]
    except FileNotFoundError:
        print("[×] proxies.txt not found.")
        return []

def test_proxy(proxy, q, valid):
    try:
        r = session.get('https://api.mail.tm', proxies=proxy, timeout=5)
        if r.ok:
            valid.append(proxy)
    except:
        pass
    finally:
        q.task_done()

def get_working_proxies(proxy_list, threads=10):
    valid = []
    q = Queue()
    for proxy in proxy_list:
        q.put(proxy)
    for _ in range(min(threads, len(proxy_list))):
        threading.Thread(target=worker_test_proxy, args=(q, valid), daemon=True).start()
    q.join()
    return valid

def worker_test_proxy(q, valid):
    while not q.empty():
        proxy = q.get()
        test_proxy(proxy, q, valid)

def save_to_csv(data, filename='accounts.csv'):
    file_exists = os.path.isfile(filename)
    with open(filename, 'a', newline='') as csvfile:
        fieldnames = ['email', 'id', 'password', 'name', 'birthday', 'gender', 'token']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow(data)

# Main CLI entrypoint
def main():
    parser = argparse.ArgumentParser(description="Facebook Account Generator with Proxy Support and CSV Export")
    parser.add_argument('--count', type=int, default=1, help='Number of accounts to generate')
    parser.add_argument('--proxies', type=str, default='proxies.txt', help='Path to proxies.txt file')
    parser.add_argument('--output', type=str, default='accounts.csv', help='CSV file to save output')
    args = parser.parse_args()

    print(BANNER)
    proxies = load_proxies(args.proxies)
    working_proxies = get_working_proxies(proxies)

    if not working_proxies:
        print('[×] No working proxies found.')
        sys.exit(1)

    for _ in range(args.count):
        proxy = random.choice(working_proxies)
        email, pwd, fname, lname, bday = create_mail_tm_account(proxy)
        if all([email, pwd, fname, lname, bday]):
            data = register_facebook_account(email, pwd, fname, lname, bday, proxy)
            if data:
                save_to_csv(data, args.output)

if __name__ == '__main__':
    main()

