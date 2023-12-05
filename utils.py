from shillelagh.backends.apsw.db import connect
from functools import wraps
from collections import defaultdict
from time import time
import re
import requests
from retry import retry
import pandas as pd
import streamlit as st
from datetime import datetime

sheet_url = st.secrets["doc_sheet_url"]

with open('free_email_domains.txt', 'r') as f:
    free_email_domains = f.read().splitlines()
    
## cache management
def cached(timeout=3600):
    # thread safe cache
    cache = defaultdict()

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            key = str(args) + str(kwargs)
            if key not in cache or time() - cache[key]['time'] > timeout:
                result = func(*args, **kwargs)
                cache[key] = {'result': result, 'time': time()}
            return cache[key]['result']

        wrapper.cache = cache
        # f.clear_cache() to clear the cache
        wrapper.clear_cache = cache.clear
        # f.delete_cache(key) to delete the cache of key
        wrapper.delete_cache = cache.pop
        return wrapper

    return decorator


# google sheet
@cached(timeout=36000)
@retry(tries=3, delay=2, backoff=2)
def get_db():
    conn = connect(":memory:")
    cursor = conn.cursor()
    query = f'SELECT * FROM "{sheet_url}"'
    rows = cursor.execute(query)
    rows = rows.fetchall()
    df = pd.DataFrame(rows, columns=['name', 'description', 'url', 'expires'])
    df.set_index('name', inplace=True)
    print(f'Fetched {len(df)} records')
    return df


def get_doc_url(doc_name):
    df = get_db()
    try:
        url = df.loc[doc_name, 'url']
        exipres = df.loc[doc_name, 'expires']
    except:
        return None
    if datetime.now().date() > exipres:
        return None
    return url


# validation
def is_valid_email(email):
    email_regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    email_found = re.findall(email_regex, email)
    if not email_found:
        return False
    email = email_found[0]
    # check if email is in company domain
    domain = email.split('@')[1]
    if domain in free_email_domains:
        return False
    return True

@cached(timeout=3600)
def gen_code(email, doc):
    return str(abs(hash(email + doc + str(time()))))[:6]

def is_valid_code(code, email, doc):
    code0 = gen_code(email, doc)
    return code == code0

## mailgun sending service
mail_key = st.secrets['mail_key']
sender = "Morning Star <hello@morningstar.works>"
domain = 'morningstar.works'
mailfun_url = f"https://api.mailgun.net/v3/{domain}/messages"


@retry(tries=3, delay=2)
def send_email_via_mailgun(to, doc):
    code = gen_code(to, doc)
    print(code)
    data = {
        "from": sender,
        "to": [to],
        "subject": f'Your verification code is {code}',
        "text": f'Please use code {code} to activate your downloading: {doc}. Code exipires in 1 hour.'
    }
    response = requests.post(mailfun_url, auth=("api", mail_key), data=data)
    if not response.ok:
        print(response.text)
        return False
    return True

if __name__ == '__main__':
    email = 'abc@xyz.com'
    doc = '星尘数据文档'
    code = gen_code(email, doc)
    print(code)
    correct = is_valid_code(code, email, doc)
    print(correct)