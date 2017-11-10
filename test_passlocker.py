from passlocker import Secrets


def test_secrets():
    s = Secrets("secrets-test")
    s.store("login", "pass")
    del s

    s = Secrets("secrets-test")
    assert "login", "pass" == s.get()
