# -*- coding: utf-8 -*-

import json
import logging
from uuid import uuid4

import config
from kombu import Connection, Consumer, Exchange, Producer, Queue
from kombu.pools import connections

log = logging.getLogger()
log.setLevel(getattr(logging, config.LOG_LEVEL.upper()))


class AmqpRpcError(Exception):
    """ Raised if there is an error making an RPC call over AMQP. """
    pass


class ValidationError(Exception):
    """ Raised if incoming data fails validation for some reason. The message will be rejected. """
    pass


class RpcClient(object):
    """
    A client Which makes an RPC call over AMQP and handles the response.

    """
    # Subclasses should override these fields as appropriate.
    response_routing_key = 'OVERRIDE ME'
    "Routing key for responses from the invoked service."

    send_exchange_name = 'OVERRIDE ME'
    "The name of the exchange to which messages are sent."

    send_exchange_type = 'topic'
    "The type of the exchange to which messages are sent."

    send_routing_key = 'OVERRIDE ME'
    "Routing key for messages to the invoked service."

    service = 'OVERRIDE ME'
    "Name of the service being called (for use in log messages)"

    def __init__(self, logger=None):
        """
        Set up the client..
        """
        if logger:
            self.logger = logger
        else:
            self.logger = logging.getLogger(__name__)

        self.amqp_timeout = int(config.AMQP_TIMEOUT)

        # definitions for conventions
        self.got_error_response = None
        self.result = None
        self.correlation_id = None

        log.debug('{0} client initialised'.format(self.service))

    def __repr__(self):
        return '<{0}Client timeout={1}s>'.format(self.service, self.amqp_timeout)

    def callback(self, message_body, message):
        """
        Handle the RPC response. If successful, the result of the call will be
        stored in :py:attr:`self.result`.

        :param message_body:
            A dictionary containing the body of the message.

        :param message:
            The AMQP message.

        """
        self.result = None
        self.got_error_response = 'x-death' in message.headers

        # Check this message relates to the request we just sent.
        message_correlation_id = message.properties.get('correlation_id')
        if message_correlation_id == self.correlation_id:
            log.debug('Message received')
            message.ack()
        else:
            # Not for us, but another client may want it.
            log.debug('Message requeued')
            message.reject(requeue=True)
            return

        if isinstance(message_body, dict):
            self.result = message_body
        else:
            try:
                self.result = json.loads(message_body)
            except ValueError as err:
                log.exception('Failed to decode response')
                raise ValidationError(str(err))

        log.debug('Result of call: {0}'.format(self.result))

    def get_publisher(self, connection, exchange):
        """
        Create and return a publisher.

        :param connection:
           A Kombu Connection instance.

        :param exchange:
            The Kombu `Exchange <https://kombu.readthedocs.org/en/latest/
            reference/kombu.html#exchange>`_ instance to which messages will
            be sent.

        :return:
            A Kombu `Producer <http://docs.celeryproject.org/projects/kombu/
            en/latest/reference/kombu.html#message-producer>`_ instance.

        """
        return Producer(connection, exchange=exchange)

    def get_send_exchange(self, connection):
        """
        Return the exchange to be used for publishing messages.

        :param connection:
           A Kombu Connection instance.

        """
        return get_exchange(connection, self.send_exchange_name, self.send_exchange_type)

    def send_request(self, connection, routing_key, message_body, correlation_id):
        """
        Send an API request.

        :param connection:
           A Kombu Connection instance.

        :param routing_key:
            The routing key on which the mwessage is to be sent.

        :param message_body:
            A dictionary containing data to be sent to the target service.

        :param correlation_id:
            A unique identifier for the request which should be present on the
            response.

        """
        self.correlation_id = correlation_id
        exchange = self.get_send_exchange(connection)
        log.debug('Using exchange: {0}'.format(exchange))
        publisher = self.get_publisher(connection, exchange)
        publisher.publish(message_body,
                          routing_key=routing_key,
                          correlation_id=correlation_id,
                          reply_to=self.response_routing_key)
        log.debug('Message published: {0}'.format(routing_key))

    def get_response_queue(self, connection, name=None):
        """
        Set up the queue on which to listen for responses.

        :param connection:
           A Kombu Connection instance.

        :param name:
            Name of the queue (detaults to routing key).

        :return:
            A Kombu `Queue <https://kombu.readthedocs.org/en/latest/reference/
            kombu.html#queue>`_ instance.

        """
        if name is None:
            name = self.response_routing_key

        exchange = get_exchange(connection)
        queue = Queue(name, exchange, self.response_routing_key, connection.default_channel)
        queue.maybe_bind(connection)

        log.debug('Created queue: {0}'.format(queue))
        return queue

    def listen_for_response(self, connection):
        """
        Set up a consumer and listen for a response. If successful, this will
        return the contents of :py:attr:`self.result` which will have been set
        up by the callback.

        :param connection:
           A Kombu Connection instance.

        :return:
            A dictionary containing the result, or None if the request failed.

        """
        self.result = None
        queue = self.get_response_queue(connection)
        with Consumer(connection, queue, callbacks=[self.callback]):
            while self.result is None:
                connection.drain_events(timeout=self.amqp_timeout)

        return self.process_response(self.result)

    def call(self, message, response_required=True, reraise_exceptions=True, routing_key=None):
        """
        The public API for the client.

        :param message:
            A dictionary containing the data to be sent.

        :param response_required:
            If True, listen for and return a response from the invoked service.

        :param reraise_exceptions:
            If ``False``, errors will be suppressed and ``None`` returned.

        :param routing_key:
            If supplied will be used in preference to the class attribute.

        :raises:
            :py:exc:`~grackle.exceptions.AmqpRpcError` by default,
            unless *reraise_exceptions* is set to ``False``.

        :return:
            The result of the call.

        """
        if response_required:
            correlation_id = uuid4().hex
        else:
            correlation_id = None

        routing_key = routing_key or self.send_routing_key

        with get_amqp_connection() as connection:
            try:
                self.send_request(connection, routing_key, message, correlation_id)
                if response_required:
                    return self.listen_for_response(connection)
            except:
                log.exception('Error in AMQP RPC call')
                if reraise_exceptions:
                    raise

    def process_response(self, response):
        """
        Enables subclasses to perform processing on the raw response from the
        calleee before it is returned.

        The default implementation expects to see the keys ``_status`` and
        optionally ``_response`` in the response, and if the status is OK
        returns the contents of the ``_response`` key (or an empty dictionary
        if not present). This is standard behaviour for most services, in so
        far as standard behaviour is a thing.

        :param response:
            The message body returned from the callee.

        :return:
            The processed message.

        """
        log.debug('Raw response from {0}'.format(self.service))

        if self.got_error_response:
            # We don't want to requeue this message.
            raise ValidationError('{0} rejected the message'.format(self.service))

        if '_status' not in response:
            raise ValidationError('Malformed response from {0}'.format(
                self.service)
            )

        status_code = response['_status'].get('code')
        if status_code != 'ok':
            log.error('Bad status from {0}'.format(self.service), status_code=status_code)
            raise AmqpRpcError('{0} returned error code: {1}'.format(self.service, status_code))

        data = response.get('_response', {})
        log.debug('Data from {0}'.format(self.service))
        log.debug('Data: {0}'.format(data))
        return data


def get_amqp_connection():
    """
    Create a Kombu Connection instance based on the application configuration.

    :return:
        The connection.

    """

    connection = Connection(hostname=config.AMQP_HOST, port=config.AMQP_PORT,
                            userid=config.AMQP_USER, password=config.AMQP_PASS,
                            virtual_host=config.AMQP_VHOST)
    return connections[connection].acquire(block=True)


def get_exchange(connection, exchange_name='', exchange_type='direct', **args):
    """
    Create a Kombu `Exchange <https://kombu.readthedocs.org/en/latest/
    reference/kombu.html#exchange>`_ instance. If called with the default
    arguments, this will return the default exchange.

    :param connection:
        A Kombu `Connection <https://kombu.readthedocs.org/en/latest/
        reference/kombu.html#connection>`_ instance.

    :param exchange_name:
        The name of the exchange.

    :param exchange_type:
        The type of the exchange. See the Kombu documentation <https://kombu.
        readthedocs.org/en/latest/reference/kombu.html#exchange>`_ for more
        information.

    :param args:
        Any additional arguments to be passed.

    :return:
        The exchange.

    """
    return Exchange(exchange_name,
                    type=exchange_type,
                    connection=connection,
                    arguments=args)
