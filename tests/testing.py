import unittest

from tests.test_main import main_module


def all_test():
    suite = unittest.TestSuite()
    suite.addTests(main_module())

    return suite


if __name__ == '__main__':
    runner = unittest.TextTestRunner()
    runner.run(all_test())
