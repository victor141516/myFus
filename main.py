from flask import Flask, request, redirect, make_response, abort, jsonify
import logging
import os
import re
from redpie import Redpie


app = Flask('myFus')
db = Redpie(
    int(os.environ.get('REDIS_DB', 0)),
    os.environ.get('REDIS_HOST', 'localhost'),
    int(os.environ.get('REDIS_PORT', 6379))
)
if '_last_key' not in db:
    db['_last_key'] = 'a'
LOGGER = logging.getLogger()
base = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
url_regex = re.compile('^http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+$')
with open('upload.html', 'r') as f:
    upload_html = f.read()


def to_code(n):
    b = len(base)
    if n == 0:
        return base[0]
    digits = []
    while n:
        digits.append(int(n % b))
        n //= b
    res = ''
    for e in digits[::-1]:
        res += base[e]
    return res


def to_n(code):
    res = 0
    rev_code = code[::-1]
    for i in range(0, len(code)):
        c = rev_code[i]
        res += base.index(c) * (len(base) ** i)
    return res


def next_code(code):
    return to_code(to_n(code) + 1)


@app.route('/', methods=['GET'])
def get_index():
    last_code = db['_last_key']
    return upload_html.format(short_code=next_code(last_code))


@app.route('/short', methods=['POST', 'GET'])
def make_short():
    if request.method == 'POST':
        data = request.json
    else:
        data = request.args

    short_code = data['shortCode']
    long_url = data['longUrl']
    if not url_regex.match(long_url):
        return jsonify({'result': 'URL_NOT_VALID'})
    for char in short_code:
        if char not in base:
            return jsonify({'result': 'SHORT_CODE_NOT_VALID'})
    if short_code in db:
        return jsonify({'result': 'CODE_ALREADY_EXISTS'})
    db[short_code] = long_url
    db['_last_key'] = short_code
    return jsonify({'result': 'OK'})


@app.route('/<short_code>', methods=['GET'])
def make_redirect(short_code):
    if short_code in db:
        return redirect(db[short_code])
    else:
        return redirect('/')


if __name__ == "__main__":
    app.run('0.0.0.0', 12121, True)
