#!/usr/bin/env python3

import logging
import requests
import os
import json
import codecs


def find_garmin_device():
    path = os.path.join('/media', os.environ.get('USER'), 'GARMIN')

    if os.path.exists(path):
        logging.info('got garmin device at {}'.format(path))
        return path

    logging.error('garmin device is not mounted or I do not know how to find it')


def locate_epo_on_device(device_path):
    possible_path = os.path.join(device_path, 'Garmin/GPS/EPO.BIN')

    if os.path.exists(possible_path):
        return possible_path

    logging.error('can not find EPO on the device')


def find_activities(device_path):
    return os.listdir(os.path.join(device_path, "Garmin/Activity"))


def fix_epo(data):
    logging.debug('original EPO: {}'.format(len(data)))

    ret = bytes()

    while data:
        data = data[3:]
        ret += data[:2304]
        data = data[2304:]

    logging.debug('after fix: {}'.format(len(ret)))

    return ret


def download_epo(out='EPO.BIN'):
    # curl -H "Garmin-Client-Name: CoreService" -H "Content-Type: application/octet-stream" --data-binary @garmin-postdata http://omt.garmin.com/Rce/ProtobufApi/EphemerisService/GetEphemerisData
    logging.info('getting EPO')

    url = 'http://omt.garmin.com/Rce/ProtobufApi/EphemerisService/GetEphemerisData'
    headers = {'Garmin-Client-Name': 'CoreService', 'Content-Type': 'application/octet-stream'}

    with open(os.path.join(os.path.dirname(__file__), 'garmin-postdata'), 'rb') as f:
        data = f.read()

    response = requests.post(url, headers=headers, data=data)

    data = fix_epo(response.content)

    with open(out, 'wb') as f:
        f.write(data)

    logging.info('EPO written to {}'.format(out))


class GarminConnect:
    URL_LOGIN = 'https://sso.garmin.com/sso/login?service=https%3A%2F%2Fconnect.garmin.com%2Fpost-auth%2Flogin&webhost=olaxpw-connect04&source=https%3A%2F%2Fconnect.garmin.com%2Fen-US%2Fsignin&redirectAfterAccountLoginUrl=https%3A%2F%2Fconnect.garmin.com%2Fpost-auth%2Flogin&redirectAfterAccountCreationUrl=https%3A%2F%2Fconnect.garmin.com%2Fpost-auth%2Flogin&gauthHost=https%3A%2F%2Fsso.garmin.com%2Fsso&locale=en_US&id=gauth-widget&cssUrl=https%3A%2F%2Fstatic.garmincdn.com%2Fcom.garmin.connect%2Fui%2Fcss%2Fgauth-custom-v1.1-min.css&clientId=GarminConnect&rememberMeShown=true&rememberMeChecked=false&createAccountShown=true&openCreateAccount=false&usernameShown=false&displayNameShown=false&consumeServiceTicket=false&initialFocus=true&embedWidget=false&generateExtraServiceTicket=false'

    def __init__(self, username, password):
        self._session = requests.Session()

        post_data = {'username': username,
                     'password': password,
                     'embed': 'true', 'lt': 'e1s1',
                     '_eventId': 'submit', 'displayNameRequired': 'false'}

        r = self._session.post(GarminConnect.URL_LOGIN, post_data)

        print(r.content)

        if "CASTGC" not in self._session.cookies:
            raise RuntimeError("login error")


class Secrets:
    """Store obfuscated username and password.

    IMPORTANT NOTE: keep in mind that this has nothing to do with encryption! It only prevents
                    from non-tech person know your password immidiatelly after looking from
                    you shoulder.
    """

    def __init__(self, filename):
        self._data = {}
        self._filename = filename

        if os.path.exists(filename):
            with open(filename, "r") as f:
                self._data = json.load(f)

    def _encode(self, s: str) -> str:
        s = s.encode("utf-8")
        s = codecs.encode(s, "base64")
        return s.decode("utf-8")

    def _decode(self, s: str) -> str:
        s = s.encode("utf-8")
        s = codecs.decode(s, "base64")
        return s.decode("utf-8")

    def store(self, username, password: str):
        self._data["username"] = username
        self._data["password"] = self._encode(password)

        with open(self._filename, "w") as f:
             json.dump(self._data, f)

    def get(self):
        return self._data["username"], self._decode(self._data["password"])

    def __bool__(self):
        return bool(self._data)


def test_secrets():
    s = Secrets("secrets-test")
    s.store("login", "pass")
    del s

    s = Secrets("secrets-test")
    assert "login", "pass" == s.get()


def connect_to_gc():
    secrets = Secrets(os.path.expanduser("~/.garmin-sync"))

    if secrets:
        username, password = secrets.get()
    else:
        from getpass import getpass
        username = input('Garmin connect username: ')
        password = getpass()

    gc = GarminConnect(username, password)
    secrets.store(username, password)
    return gc


def main():
    logging.basicConfig(level=logging.DEBUG)

    device_path = find_garmin_device()

    if not device_path:
        logging.error("no device")
        return

    epo_path = locate_epo_on_device(device_path)
    download_epo(epo_path)

    logging.info("Activities: %s", find_activities(device_path))

    gc = connect_to_gc()


if __name__ == "__main__":
    main()
