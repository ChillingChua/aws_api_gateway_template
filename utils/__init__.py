# -*- coding: utf-8 -*-


def get_error_message(error_code, message, *args):
    items = [error_code, message] + list(args)
    return '--'.join([str(x) for x in items])
