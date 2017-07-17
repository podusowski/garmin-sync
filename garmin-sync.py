#!/usr/bin/env python3

import logging
import requests
import os


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


def main():
    logging.basicConfig(level=logging.DEBUG)

    device_path = find_garmin_device()

    if not device_path:
        logging.error("no device")
        return

    epo_path = locate_epo_on_device(device_path)
    download_epo(epo_path)


if __name__ == "__main__":
    main()
