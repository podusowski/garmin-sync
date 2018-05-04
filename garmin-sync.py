#!/usr/bin/env python3

import logging
import requests
import os

from passlocker import Secrets


class Device:
    def __init__(self):
        self._path = self._find_garmin_device()

    @property
    def path(self):
        return self._path

    def _find_garmin_device(self):
        path = os.path.join('/media', os.environ.get('USER'), 'GARMIN')

        if os.path.exists(path):
            logging.debug('Found garmin device at {}'.format(path))
            return path

        raise RuntimeError("no Garmin device found")

    @property
    def epo_path(self):
        possible_path = os.path.join(self.path, 'Garmin/GPS/EPO.BIN')

        if os.path.exists(possible_path):
            return possible_path

        raise RuntimeError("can not find EPO on the device")

    @property
    def activities(self):
        root = os.path.join(self.path, "Garmin", "Activity")
        return [os.path.join(root, activity) for activity in os.listdir(root)]


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
    logging.debug('Getting EPO')

    url = 'http://omt.garmin.com/Rce/ProtobufApi/EphemerisService/GetEphemerisData'
    headers = {'Garmin-Client-Name': 'CoreService', 'Content-Type': 'application/octet-stream'}

    with open(os.path.join(os.path.dirname(__file__), 'garmin-postdata'), 'rb') as f:
        data = f.read()

    response = requests.post(url, headers=headers, data=data)

    data = fix_epo(response.content)

    with open(out, 'wb') as f:
        f.write(data)

    logging.debug('EPO written to {}'.format(out))


class GarminConnect:
    URL_LOGIN = 'https://sso.garmin.com/sso/login?service=https%3A%2F%2Fconnect.garmin.com%2Fpost-auth%2Flogin&webhost=olaxpw-connect04&source=https%3A%2F%2Fconnect.garmin.com%2Fen-US%2Fsignin&redirectAfterAccountLoginUrl=https%3A%2F%2Fconnect.garmin.com%2Fpost-auth%2Flogin&redirectAfterAccountCreationUrl=https%3A%2F%2Fconnect.garmin.com%2Fpost-auth%2Flogin&gauthHost=https%3A%2F%2Fsso.garmin.com%2Fsso&locale=en_US&id=gauth-widget&cssUrl=https%3A%2F%2Fstatic.garmincdn.com%2Fcom.garmin.connect%2Fui%2Fcss%2Fgauth-custom-v1.1-min.css&clientId=GarminConnect&rememberMeShown=true&rememberMeChecked=false&createAccountShown=true&openCreateAccount=false&usernameShown=false&displayNameShown=false&consumeServiceTicket=false&initialFocus=true&embedWidget=false&generateExtraServiceTicket=false'
    URL_MAIN_PAGE = 'https://connect.garmin.com/modern/'
    URL_UPLOAD = 'https://connect.garmin.com/modern/proxy/upload-service/upload/.fit'

    def __init__(self, username, password):
        self._session = requests.Session()

        post_data = {'username': username,
                     'password': password,
                     'embed': 'true', 'lt': 'e1s1',
                     '_eventId': 'submit', 'displayNameRequired': 'false'}

        r = self._session.post(GarminConnect.URL_LOGIN, post_data)

        if "CASTGC" not in self._session.cookies:
            raise RuntimeError("login error")

        # need to request this one to get proper session cookies
        login_ticket = self._session.cookies["CASTGC"]
        r = self._session.get(GarminConnect.URL_MAIN_PAGE, params={"ticket": login_ticket})

        if r.status_code != 200:
            raise RuntimeError("Something bad happened: {}".format(r.content))

    def upload_activity(self, activity):
        with open(activity, "rb") as f:
            files = {"file": ('activity.fit', f, "application/octet-stream")}
            data = {"NK": "NT"}
            r = self._session.post(GarminConnect.URL_UPLOAD, files=files, headers=data)

        def extract_messages(result):
            report = r.json()['detailedImportResult']

            for item in report['successes'] + report['failures']:
                if 'messages' in item and item['messages'] is not None:
                    for message in item['messages']:
                        yield message['content']

        logging.info("%s: %s", os.path.basename(activity), ', '.join(extract_messages(r)))


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
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logging.getLogger("requests").setLevel(logging.WARN)

    device = Device()

    logging.info("Updating EPO")
    download_epo(device.epo_path)

    logging.info("Uploading %d activities", len(device.activities))

    gc = connect_to_gc()

    for activity in device.activities:
        gc.upload_activity(activity)


if __name__ == "__main__":
    main()
