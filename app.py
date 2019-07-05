import random
import string
import base64
import requests
import cv2
import numpy as np
import yaml
import json
import logging
from flask import Flask, render_template
app = Flask('whats-the-favorie-lang')

DEV_GITHUB_USER = 'philippnormann1337'
DEV_ACCESS_TOKEN = '***REMOVED***'

logging.basicConfig(level=logging.INFO)

frontal_face_cascade = cv2.CascadeClassifier(
    'resources/haarcascade_frontalface_default.xml')
profile_face_cascade = cv2.CascadeClassifier(
    'resources/haarcascade_profileface.xml')
# all_language = yaml.load('resources/languages.yml')
with open('resources/popularity.json') as f:
    popularity = json.loads(f.read())
    languages = [lang for lang, score in sorted(
        popularity.items(), key=lambda x: x[1], reverse=True)]


def detect_faces(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    frontal_faces = frontal_face_cascade.detectMultiScale(gray, 1.3, 5)
    profile_faces = profile_face_cascade.detectMultiScale(gray, 1.2, 4)
    return frontal_faces, profile_faces


def draw_faces(img, faces, color=(255, 0, 0)):
    for (x, y, w, h) in faces:
        cv2.rectangle(img, (x, y), (x+w, y+h), color, 2)
    return img


def decode_image(img_bytes):
    return cv2.imdecode(np.fromstring(img_bytes, np.uint8), cv2.IMREAD_COLOR)


def encode_image(img):
    return cv2.imencode('.jpg', img)[1]


def get_avatar(user):
    return requests.get(user['avatar_url'], stream=True).raw.read()


def get_repos(username):
    resp = requests.get(
        f'https://api.github.com/users/{username}/repos', auth=(DEV_GITHUB_USER, DEV_ACCESS_TOKEN))
    if resp.status_code == 403:
        raise ConnectionError('Quota exceeded!')
    if resp.status_code != 200:
        raise ConnectionError(f'Unexpected API Error: {resp.status_code}')
    return resp.json()


def get_random_users(min_followers=50, random_query_len=2):
    rand_letters = ''.join(random.choices(
        string.ascii_lowercase, k=random_query_len))
    url = f'https://api.github.com/search/users?q={rand_letters}+followers:%3E{min_followers}'
    resp = requests.get(url, auth=(DEV_GITHUB_USER, DEV_ACCESS_TOKEN))
    if resp.status_code == 403:
        raise ConnectionError('Quota exceeded!')
    if resp.status_code != 200:
        raise ConnectionError(f'Unexpected API Error: {resp.status_code}')
    users = resp.json()['items']
    logging.info(f'Got {len(users)} users for query: {rand_letters}')
    return users


def get_random_user_with_face():
    frontal_faces = []
    profile_faces = []
    logging.info('Looking for a random face...')
    while len(frontal_faces) <= 0 and len(profile_faces) <= 0:
        users = get_random_users()
        if len(users) > 0:
            rand_user = random.choice(users)
            img_bytes = get_avatar(rand_user)
            if len(img_bytes) > 0:
                img = decode_image(img_bytes)
                frontal_faces, profile_faces = detect_faces(img)
    return rand_user, img, frontal_faces, profile_faces


def get_languages(repos):
    languages = [repo['language']
                 for repo in repos if repo['language'] is not None]
    language_counts = {}
    for lang in languages:
        language_counts[lang] = language_counts.setdefault(lang, 0) + 1
    return sorted(language_counts.items(), key=lambda x: x[1], reverse=True)


@app.route('/')
def quiz():
    try:
        user, img, frontal_faces, profile_faces = get_random_user_with_face()
        repos = get_repos(user['login'])
        user['languages'] = get_languages(repos)
        user['top_language'] = user['languages'][0][0]
        img = draw_faces(img, frontal_faces, color=(255, 0, 0))
        img = draw_faces(img, profile_faces, color=(0, 0, 255))
        img_bytes = encode_image(img)
        img_base64 = base64.b64encode(img_bytes)
        user['avatar'] = img_base64.decode('utf-8')
        top_50_without_top = [
            lang for lang in languages[:50] if lang != user['top_language']]
        choices = random.sample(top_50_without_top, k=3)
        choices.append(user['top_language'])
        random.shuffle(choices)

        return render_template('index.html', user=user, choices=choices)
    except ConnectionError as err:
        return str(err)
