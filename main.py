import hashlib
import logging
import os
import re
from functools import wraps

from flask import Flask, abort, jsonify, make_response, redirect, request
from flask_cors import CORS
from redpie import Redpie

SALT = os.environ['SALT']


def encode_p(p):
    return hashlib.sha256((p + SALT).encode('utf-8')).hexdigest()


app = Flask('myFus')
CORS(app)
db = Redpie(
    int(os.environ.get('REDIS_DB', 0)),
    os.environ.get('REDIS_HOST', 'localhost'),
    int(os.environ.get('REDIS_PORT', 6379))
)
if '_last_key' not in db:
    db['_last_key'] = 'a'
db['_admin'] = encode_p(os.environ['ADMIN_PASSWORD'])
LOGGER = logging.getLogger()
base = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
with open('upload.html', 'r') as f:
    upload_html = f.read()

with open('admin.html', 'r') as f:
    admin_html = f.read()


def admin(f):
    @wraps(f)
    def w(*args, **kwargs):
        if 'p' in request.cookies and '_admin' in db and request.cookies['p'] == db['_admin']:
            return f(*args, **kwargs)
        else:
            return redirect('/admin/login')
    return w


def to_code(n):
    b = len(base)
    if n == 0:
        return base[0]
    digits = []
    while n > 0:
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


def previous_code(code):
    return to_code(to_n(code) - 1)


@app.route('/', methods=['GET'])
def get_index():
    first_available = db['_last_key']
    while first_available in db:
        first_available = next_code(first_available)
    return upload_html.format(short_code=first_available)


@app.route('/short', methods=['POST', 'GET'])
def make_short():
    if request.method == 'POST':
        data = request.json
    else:
        data = request.args

    short_code = data.get('shortCode')
    if short_code is None:
        short_code = next_code(db['_last_key'])
        while short_code in db:
            short_code = next_code(short_code)

    long_url = data['longUrl']
    for char in short_code:
        if char not in base:
            return jsonify({'result': 'SHORT_CODE_NOT_VALID'})
    if short_code in db:
        return jsonify({'result': 'CODE_ALREADY_EXISTS'})
    db[short_code] = long_url
    if short_code == next_code(db['_last_key']):
        db['_last_key'] = short_code
    return jsonify({'result': 'OK', 'short': short_code})


@app.route('/admin/login', methods=['POST', 'GET'])
def admin_login():
    if request.method=='GET':
        return '<form action="/admin/login" method="POST"><input name="password" type="password"><button>Send</button></form>'
    else:
        response = redirect('/admin')
        if 'password' in request.form:
            response.set_cookie('p', value=encode_p(request.form['password']))
        return response


@app.route('/admin', methods=['POST', 'GET'])
@admin
def show_admin():
    return admin_html


@app.route('/api/<short_code>', methods=['GET', 'DELETE'])
@app.route('/api', methods=['GET'])
@admin
def api(short_code=None):
    if request.method == 'DELETE':
        try:
            del(db[short_code])
            return jsonify({'result': 'OK'})
        except Exception as e:
            return jsonify({'result': 'FAILED'})
    else:
        results = []
        if short_code:
            if short_code in db:
                results.append([short_code, db[short_code]])
        else:
            from_code = request.args.get('f', False)
            to_code = request.args.get('t', False)
            rows_per_page = min(int(request.args.get('n', 20)), 20)
            if from_code:
                tries = 0
                while rows_per_page > 0 and tries < 500: # and from_code != next_code(db['_last_key']):
                    from_code = next_code(from_code)
                    if from_code in db:
                        rows_per_page -= 1
                        results.append([from_code, db[from_code]])
                    else:
                        tries += 1
            elif to_code:
                while rows_per_page > 0 and to_code != previous_code('a'):
                    to_code = previous_code(to_code)
                    if to_code in db:
                        rows_per_page -= 1
                        results.insert(0, [to_code, db[to_code]])

        return jsonify(results)



@app.route('/<short_code>', methods=['GET'])
def make_redirect(short_code):
    if short_code in db:
        return redirect(db[short_code])
    else:
        return redirect('/')


if __name__ == "__main__":
    app.run('0.0.0.0', 8000, True)
