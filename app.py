import random
import string
import base64
import requests
import cv2
import numpy as np
import io
import os
import json
import logging
import time
from flask import Flask, render_template

DEV_GITHUB_USER = os.environ['DEV_GITHUB_USER']
DEV_ACCESS_TOKEN = os.environ['DEV_ACCESS_TOKEN']

logging.basicConfig(level=logging.INFO)
app = Flask('whats-the-favorite-lang')

frontal_face_cascade = cv2.CascadeClassifier(
    'resources/haarcascade_frontalface_default.xml')
profile_face_cascade = cv2.CascadeClassifier(
    'resources/haarcascade_profileface.xml')
eye_cascade = cv2.CascadeClassifier(
    'resources/haarcascade_eye.xml')

with open('resources/popularity.json') as f:
    popularity = json.loads(f.read())
    popularity = sorted(popularity.items(), key=lambda x: x[1], reverse=True)
    languages = [lang for lang, score in popularity]
    scores = np.array([score for lang, score in popularity])
    scores = np.sqrt(scores)
    scores = scores/np.sum(scores)


def detect_faces(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    frontal_faces = frontal_face_cascade.detectMultiScale(gray, 1.3, 5)
    profile_faces = profile_face_cascade.detectMultiScale(gray, 1.2, 4)
    eyes = eye_cascade.detectMultiScale(gray, 1.4, 5)
    return (len(frontal_faces) + len(profile_faces) + len(eyes)) > 0


def draw_faces(img, faces, color=(255, 0, 0)):
    for (x, y, w, h) in faces:
        cv2.rectangle(img, (x, y), (x+w, y+h), color, 2)
    return img


def decode_image(img_bytes):
    return cv2.imdecode(np.fromstring(img_bytes, np.uint8), cv2.IMREAD_COLOR)


def encode_image(img):
    img_bytes = cv2.imencode('.jpg', img)[1]
    base64_bytes = base64.b64encode(img_bytes)
    return base64_bytes.decode('utf-8')


def get_avatar(user):
    logging.info(f'Fetching avatar for {user["login"]}')
    resp = requests.get(user['avatar_url'], stream=True)
    img_bytes = resp.raw.read()
    if resp.status_code != 200 or len(img_bytes) < 0:
        raise ConnectionError(resp.text)
    return img_bytes


def get_repos(user):
    logging.info("Fetching repos for " + user["login"])
    resp = requests.get(f'https://api.github.com/users/{user["login"]}/repos',
                        auth=(DEV_GITHUB_USER, DEV_ACCESS_TOKEN))
    if resp.status_code == 403:
        raise ConnectionError('Quota exceeded!')
    if resp.status_code != 200:
        raise ConnectionError(
            f'Unexpected API Error: {resp.status_code} - {resp.text}')
    return resp.json()


def get_random_users(min_followers=50, random_query_len=2):
    rand_letters = ''.join(random.choices(
        string.ascii_lowercase, k=random_query_len))
    url = f'https://api.github.com/search/users?q={rand_letters}+followers:%3E{min_followers}'
    resp = requests.get(url, auth=(DEV_GITHUB_USER, DEV_ACCESS_TOKEN))
    if resp.status_code == 403:
        raise ConnectionError('Quota exceeded!')
    if resp.status_code != 200:
        raise ConnectionError(
            f'Unexpected API Error: {resp.status_code} - {resp.text}')
    users = resp.json()['items']
    logging.info(f'Got {len(users)} users for query: {rand_letters}')
    return users


def get_random_user_with_repos():
    rand_user = {}
    logging.info('Looking for a random user...')
    while True:
        users = get_random_users()
        random.shuffle(users)
        while 'avatar' not in rand_user and len(users) > 0:
            rand_user = users.pop()
            try:
                img_bytes = get_avatar(rand_user)
                img = decode_image(img_bytes)
                faces_detected = detect_faces(img)
                if faces_detected:
                    repos = get_repos(rand_user)
                    rand_user['languages'] = get_languages(repos)
                    if len(rand_user['languages']) > 0:
                        rand_user['top_language'] = rand_user['languages'][0][0]
                        rand_user['avatar'] = encode_image(img)
                        return rand_user, repos
            except Exception as e:
                logging.error(f'{type(e)} - {e}')
                pass


def get_languages(repos):
    languages = [repo['language'] for repo in repos
                 if repo['language'] is not None]
    language_counts = {}
    for lang in languages:
        language_counts[lang] = language_counts.setdefault(lang, 0) + 1
    return sorted(language_counts.items(), key=lambda x: x[1], reverse=True)


@app.route('/')
def quiz():
    start = time.time()
    try:
        user, _ = get_random_user_with_repos()
        choices = np.random.choice(languages, 4, p=scores, replace=False)
        choices = [lang for lang in choices
                   if lang != user['top_language']][:3]
        choices.append(user['top_language'])
        random.shuffle(choices)
        logging.info(f'Responded in {((time.time() - start) * 100):.2f} ms')
        return render_template('index.html', user=user, choices=choices)
    except ConnectionError as err:
        return str(err)
