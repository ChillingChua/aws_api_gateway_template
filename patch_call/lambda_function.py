# -*- coding: utf-8 -*-
import json
import logging
import traceback

from httplib import BAD_REQUEST, INTERNAL_SERVER_ERROR

from config import *
from utils import get_error_message

log = logging.getLogger('patch_call')
log.setLevel(getattr(logging, LOG_LEVEL.upper()))


class PatchCallException(Exception):
    """
    generic "PatchCallException" with specific error messages for AWS API Gateway HTTP response code regex'ing
             the messages are kept non specific, so they can be passed 1:1 to users without exposing anything
             crucial, more detailed information should be logged for error investigation
    """


def validate_request_params(request):
    """
        Validates the incoming request to match the minimum
        requirements to be able to handle this request.
        Just a stub here, no validation at this time needed.

    :param request: JSON/dict
        {}

    :return: Boolean

    """
    return True


def patch_handler(request, context):
    log.debug('got patch request: {0}'.format(request))
    response = dict(success=False,
                    message='')

    if isinstance(request, str) or isinstance(request, unicode):
        try:
            log.info('Got string request, converting to JSON.')
            request = json.loads(request)
        except ValueError:
            log.warning('got malformed JSON request: {0}'.format(request))
            msg = get_error_message(BAD_REQUEST, 'Malformed JSON in request.')
            raise PatchCallException(msg)

    if not validate_request_params(request):
        log.warning('Request validation failed.')
        msg = get_error_message(BAD_REQUEST, 'Parameter mismatch: please see documentation.')
        raise PatchCallException(msg)

    try:
        response['message'] = json.dumps(request.update(dict(called='PATCH')))
        return response

    except PatchCallException:
        log.info('Error response from VREG.')
        log.info('response was: {0}'.format(response))
        msg = get_error_message(BAD_REQUEST, response['message'])
        raise PatchCallException(msg)

    except:
        log.error('exception in reset: {0}'.format(request))
        log.error(traceback.print_exc())
        msg = get_error_message(INTERNAL_SERVER_ERROR, 'Error in patch request !')
        raise PatchCallException(msg)

