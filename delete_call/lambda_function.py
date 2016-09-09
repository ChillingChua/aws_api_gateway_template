# -*- coding: utf-8 -*-
import json
import logging
import traceback

from httplib import BAD_REQUEST, INTERNAL_SERVER_ERROR

from config import LOG_LEVEL
from utils import get_error_message

log = logging.getLogger('delete_call')
log.setLevel(getattr(logging, LOG_LEVEL.upper()))


class DeleteCallException(Exception):
    """
        generic "DeleteCallException" with error messages for AWS API Gateway HTTP response code regex'ing
        the messages are kept non specific, so they can be passed 1:1 to users without exposing anything
        crucial, more detailed information should be logged for error investigation
    """


def validate_request_params(request):
    """
        Validates the incoming request to match the minimum
        requirements to be able to handle this request.

    :param request: JSON/dict
        {
            'modifier_id': ''
        }

    :return: Boolean
    """
    try:
        # just a small test if the needed parameter is there and not an empty string
        if not request.get('modifier_id') or not str(request.get('modifier_id')).strip():
            raise AssertionError
        return True
    except AssertionError:
        log.warning('Request validation failed for: {0}'.format(request))
        return False


def delete_handler(request, context):
    log.info('delete_call - got request: {0}'.format(request))
    response = dict(success=False,
                    message='')

    if isinstance(request, str) or isinstance(request, unicode):
        try:
            log.info('Got string request, converting to JSON.')
            request = json.loads(request)
        except ValueError:
            log.warning('got malformed JSON request: {0}'.format(request))
            msg = get_error_message(BAD_REQUEST, 'Malformed JSON in request.')
            raise DeleteCallException(msg)

    if not validate_request_params(request):
        msg = get_error_message(BAD_REQUEST, 'Parameter mismatch, validation failed.')
        raise DeleteCallException(msg)

    try:
        # do some stuff to delete an entry in the system here
        # maybe send AMQP message, do database work, etc ...
        response['message'] = 'delete call successful'
        return response

    except DeleteCallException:
        log.info('Error response')
        log.info('response was: {0}'.format(response))
        msg = get_error_message(BAD_REQUEST, response['message'])
        raise DeleteCallException(msg)

    except:
        log.error('exception in delete call: {0}'.format(request))
        log.error(traceback.print_exc())
        msg = get_error_message(INTERNAL_SERVER_ERROR, 'Error in delete call request !')
        raise DeleteCallException(msg)

