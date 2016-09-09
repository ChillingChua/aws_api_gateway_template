# -*- coding: utf-8 -*-
import json
import logging
import traceback

from httplib import BAD_REQUEST, INTERNAL_SERVER_ERROR

from config import *
from utils import get_error_message


log = logging.getLogger('post_call')
log.setLevel(getattr(logging, LOG_LEVEL.upper()))


class PostCallException(Exception):
    """
    generic "PostCallException" with specific error messages for AWS API Gateway HTTP response code regex'ing
             the messages are kept non specific, so they can be passed 1:1 to users without exposing anything
             crucial, more detailed information should be logged for error investigation
    """


def validate_request_params(request):
    """
        :param request:
        :return: Boolean
    """
    try:
        # again just a minimal stub for testing and completeness
        return True

    except AssertionError:
        log.warning('POST request not validated: {0}'.format(request))
        return False


def add_something_handler(request, context):
    log.info('POST call - got request: {0}'.format(request))
    response = dict(success=False,
                    message='')

    if isinstance(request, str) or isinstance(request, unicode):
        try:
            log.info('Got string request, converting to JSON.')
            request = json.loads(request)
        except ValueError:
            log.warning('got malformed JSON request: {0}'.format(request))
            raise PostCallException('Malformed JSON in request.')

    # special no op call, if noop is the only key in the request, just return the context
    # and a short message
    if 'noop' in request and request.get('noop'):
        if not request.get('skiplog'):
            log.info('NoOp called !')
            log.info('Nothing else was called, just Ping-Pong.')
        response = dict(message='No Op call successful',
                        context=context,
                        success=True)
        return response

    if not validate_request_params(request):
        msg = get_error_message(BAD_REQUEST, 'Parameter mismatch: validation failed.')
        raise PostCallException(msg)

    try:
        response['message'] = json.loads(request.update(dict(called='POST')))

    except PostCallException:
        log.info('Error returned.')
        log.info('response was: {0}'.format(response))
        msg = get_error_message(BAD_REQUEST, response['message'])
        raise PostCallException(msg)

    except:
        log.error('exception in a post call: {0}'.format(request))
        log.error(traceback.print_exc())
        msg = get_error_message(INTERNAL_SERVER_ERROR, 'Error in POST request !')
        raise PostCallException(msg)

    return response
