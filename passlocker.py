import os
import json
import codecs


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
