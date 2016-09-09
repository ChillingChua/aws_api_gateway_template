# -*- coding: utf-8 -*-
import json
import logging
import re
import traceback

from httplib import BAD_REQUEST, INTERNAL_SERVER_ERROR

from config import *
from utils.rpc_client import RpcClient, AmqpRpcError

from utils import get_error_message

log = logging.getLogger('get_call')
log.setLevel(getattr(logging, LOG_LEVEL.upper()))


class GetCallException(Exception):
    """
    generic "GetCallException" with specific error messages for AWS API Gateway HTTP response code regex'ing
             the messages are kept non specific, so they can be passed 1:1 to users without exposing anything
             crucial, more detailed information should be logged for error investigation
    """
    pass


class GetStuffViaAMQPClient(RpcClient):
    service = 'get_stuff'
    response_routing_key = 'get_stuff_response'
    send_exchange_name = AMQP_EXCHANGE
    send_exchange_type = 'topic'

    def process_response(self, response):
        """ overwrite the process response, we just need a pass-through here """
        log.debug('got response from AMQP: {0}'.format(response))
        return response


def validate_request_params(request):
    """
        Validates the incoming request to match the minimum
        requirements to be able to handle this request.

    :param request: dict
        { }

    :return: Boolean

    """
    try:
        return True

    except AssertionError:
        log.warning('get call request not validated: {0}'.format(request))
        return False

    except:
        log.error('error in validation: {0}'.format(request))
        log.error(traceback.print_exc())
        return False


def get_stuff_handler(request, context):
    """
    Main function to be called as lambda handler.
    The parameters are specified in the AWS mapping in AWS Gateway and are the sum of
    request parameters from specification and the parsed headers.

    special call available for test purpose:
    this returns a message with the context used in the call, logging can be skipped if
    "skiplog" is ste to True, so even the connection with Cloudwatch can be switched
        {
            "noop": True,
            "skiplog": False
        }

    :param request: JSON
        {
            "value1": "something",
            "value2": "something else",
            "value3": "foo"
        }

    :param context: request context from AWS lambda

    :raises: GetCallException

    :return: JSON
    """

    if isinstance(request, str):
        try:
            log.info('Got string request, converting to JSON.')
            request = json.loads(request)
        except ValueError:
            log.warning('Malformed Json in request: {0}'.format(request))
            msg = get_error_message(BAD_REQUEST, 'Malformed JSON in request.')
            raise GetCallException(msg)

    # special no op call, if noop is the only key in the request, just return the context
    # and a short message
    # this can be used in 'keep warm' calls to keep the lambda function from being "scaled down', 'hibernated',
    # whatever ...
    # this way the calls can be easily distinguished from 'real' requests
    if 'noop' in request and request.get('noop'):
        if not request.get('skiplog'):
            log.info('NoOp called !')
            log.info('context returned: {0}'.format(context))
        response = dict(message='No Op call successful',
                        context=context,
                        success=True)
        return response

    log.debug('got request: {0}'.format(request))
    response = dict(success=False,
                    message='')

    if not validate_request_params(request):
        # we need to use exceptions here now, so we can match the
        # errorMessage in the context response for HTTP response types
        msg = get_error_message(BAD_REQUEST, 'Parameter mismatch: validation failed.')
        raise GetCallException(msg)

    try:
        client = GetStuffViaAMQPClient()
        response = client.call(request, routing_key=ROUTING_KEY)
        log.info('found stuff with ID: {0}'.format(request.get('stuff_id')))

        if not response['success']:
            raise GetCallException()

        return response

    except AmqpRpcError:
        log.error('Error connecting to AMQP exchange: {0}'.format(AMQP_EXCHANGE))
        msg = get_error_message(INTERNAL_SERVER_ERROR, 'Error in request for GET call!')
        raise GetCallException(msg)

    except GetCallException:
        log.info('Error response from VREG.')
        log.info('response was: {0}'.format(response))
        msg = get_error_message(BAD_REQUEST, response['message'])
        raise GetCallException(msg)

    except:
        log.error('unexpected exception in get call: {0}'.format(request))
        log.error(traceback.print_exc())
        msg = get_error_message(INTERNAL_SERVER_ERROR, 'Error in request for GET call!')
        raise GetCallException(msg)

