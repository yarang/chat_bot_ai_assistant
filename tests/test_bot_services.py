import pytest

from bot import Bot


class DummyService:
    def __init__(self):
        self.called = False

    def action(self):
        self.called = True


def test_register_and_get_service():
    b = Bot()
    svc = DummyService()
    b.register_service('dummy', svc)
    got = b.get_service('dummy')
    assert got is svc
    assert hasattr(b, 'dummy')


def test_unregister_service():
    b = Bot()
    svc = DummyService()
    b.register_service('dummy', svc)
    b.unregister_service('dummy')
    assert b.get_service('dummy') is None
    assert not hasattr(b, 'dummy')


def test_list_services():
    b = Bot()
    b.register_service('a', 1)
    b.register_service('b', 2)
    d = b.list_services()
    assert d == {'a': 1, 'b': 2}
