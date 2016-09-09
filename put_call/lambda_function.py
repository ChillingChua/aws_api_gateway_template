# -*- coding: utf-8 -*-
import json
import logging
import traceback

from httplib import BAD_REQUEST, INTERNAL_SERVER_ERROR

from config import *
from utils.rpc_client import RpcClient, AmqpRpcError
from utils import get_error_message

log = logging.getLogger('put_call')
log.setLevel(getattr(logging, LOG_LEVEL.upper()))


class PutCallException(Exception):
    """
    generic "PutCallException" with specific error messages for AWS API Gateway HTTP response code regex'ing
             the messages are kept non specific, so they can be passed 1:1 to users without exposing anything
             crucial, more detailed information should be logged for error investigation
    """


def validate_request_params(request):
    """
        Validates the incoming request to match the minimum
        requirements to be able to handle this request.

    :param request: JSON/dict
    :return: Boolean

    """
    try:
        return True

    except AssertionError:
        log.warning('Request validation failed for: {0}'.format(request))
        return False


def update_entry_handler(request, context):
    log.info('put call got request: {0}'.format(request))
    response = dict(success=False,
                    message='')

    if isinstance(request, str) or isinstance(request, unicode):
        try:
            log.info('Got string request, converting to JSON.')
            request = json.loads(request)
        except ValueError:
            log.warning('got malformed JSON request: {0}'.format(request))
            msg = get_error_message(BAD_REQUEST, 'Malformed JSON in request.')
            raise PutCallException(msg)

    if not validate_request_params(request):
        msg = get_error_message(BAD_REQUEST, 'Parameter mismatch: validation failed.')
        raise PutCallException(msg)

    try:
        # this time return JSON, not stringified
        response = request.update(dict(calles='PUT'))
        return response

    except PutCallException:
        log.info('Error on response')
        log.info('response was {0}'.format(response))
        msg = get_error_message(BAD_REQUEST, response['message'])
        raise PutCallException(msg)

    except:
        log.error('exception in update: {0}'.format(request))
        log.error(traceback.print_exc())
        msg = get_error_message(INTERNAL_SERVER_ERROR, 'Error in PUT call request !')
        raise PutCallException(msg)
