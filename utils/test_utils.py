# -*- coding: utf-8 -*-

import unittest

from httplib import BAD_REQUEST, INTERNAL_SERVER_ERROR

from utils import get_error_message


class UtilsTests(unittest.TestCase):

    def test_get_error_response(self):
        correct = '500--Error message'
        self.assertEqual(correct, get_error_message(INTERNAL_SERVER_ERROR, 'Error message'))

    def test_get_error_message_additional_args(self):
        correct = '400--some message--more information'
        self.assertEqual(correct, get_error_message(BAD_REQUEST, 'some message', 'more information'))
