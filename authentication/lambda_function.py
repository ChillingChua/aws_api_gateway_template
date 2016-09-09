# -*- coding: utf-8 -*-
"""
    Copyright 2015-2016 Amazon.com, Inc. or its affiliates. All Rights Reserved.

    Licensed under the Apache License, Version 2.0 (the "License").
    You may not use this file except in compliance with the License. A copy of the License is located at

         http://aws.amazon.com/apache2.0/

    or in the "license" file accompanying this file. This file is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
    the specific language governing permissions and limitations under the License.

    shamelessly copied and used from:
    https://github.com/awslabs/aws-apigateway-lambda-authorizer-blueprints

"""
from __future__ import print_function

import logging
import re

from config import *


log = logging.getLogger('authentication')
log.setLevel(getattr(logging, LOG_LEVEL.upper()))


class AuthFailedException(Exception):
    pass


def lambda_handler(request, context):
    log.info('authorizationToken: {0}'.format(request.get('authorizationToken', '')))
    log.info('Method ARN: {0}'.format(request['methodArn']))
    """validate the incoming token"""
    """and produce the principal user identifier associated with the token"""

    """this could be accomplished in a number of ways:"""
    """1. Call out to OAuth provider"""
    """2. Decode a JWT token inline"""
    """3. Lookup in a self-managed DB"""
    principal_id = "*"

    """you can send a 401 Unauthorized response to the client by failing like so:"""
    """raise Exception('Unauthorized')"""

    """if the token is valid, a policy must be generated which will allow or deny access to the client"""

    """if access is denied, the client will recieve a 403 Access Denied response"""
    """if access is allowed,
        API Gateway will proceed with the backend integration configured on the method that was called"""

    """this function must generate a policy that is associated with the recognized principal user identifier."""
    """depending on your use case, you might store policies in a DB, or generate them on the fly"""

    """keep in mind, the policy is cached for 5 minutes by default (TTL is configurable in the authorizer)"""
    """and will apply to subsequent calls to any method/resource in the RestApi"""
    """made with the same token"""

    """the example policy below denies access to all resources in the RestApi"""

    tmp = request['methodArn'].split(':')
    api_gateway_arn_tmp = tmp[5].split('/')
    aws_account_id = tmp[4]

    policy = AuthPolicy(principal_id, aws_account_id)
    policy.restApiId = api_gateway_arn_tmp[0]
    policy.region = tmp[3]
    policy.stage = api_gateway_arn_tmp[1]

    _token = request.get('authorizationToken')
    if _token:
        try:
            # do some authentication here
            # here just set to true if token is equal to a special string
            # for demonstration purposes
            # you can be as specific as you need, or just binary authentication
            auth_success = _token == 'somethingsomethingsomethingsomething'
            if not auth_success:
                log.error('Authentication failure.')
                raise AuthFailedException
            else:
                log.debug('token authorized, allowing all methods for now')
                policy.allow_all_methods()

        except AuthFailedException:
            log.error('Authentication error, denying all method access')
            log.error('request: {0}'.format(request))
            log.error('context: {0}'.format(context))
            policy.deny_all_methods()
        except:
            log.error('Error in auth process !')
            log.error('request: {0}'.format(request))
            log.error('context: {0}'.format(context))
            policy.deny_all_methods()
    else:
        log.warning('no token in request, returning DENY on all policy')
        log.warning('request: {0}'.format(request))
        policy.deny_all_methods()

    """finally, build the policy and exit the function using return"""
    return policy.build()


class HttpVerb:
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    HEAD = "HEAD"
    DELETE = "DELETE"
    # OPTIONS = "OPTIONS"
    ALL = "*"


class AuthPolicy(object):
    aws_account_id = ""
    """The AWS account id the policy will be generated for. This is used to create the method ARNs."""
    principal_id = ""
    """The principal used for the policy, this should be a unique identifier for the end user."""
    version = "2012-10-17"
    """The policy version used for the evaluation. This should always be '2012-10-17'"""
    pathRegex = "^[/.a-zA-Z0-9-\*]+$"
    """The regular expression used to validate resource paths for the policy"""

    """these are the internal lists of allowed and denied methods. These are lists
    of objects and each object has 2 properties: A resource ARN and a nullable
    conditions statement.
    the build method processes these lists and generates the approriate
    statements for the final policy"""
    allow_methods = []
    deny_methods = []

    restApiId = "*"
    """The API Gateway API id. By default this is set to '*'"""
    region = "*"
    """The region where the API is deployed. By default this is set to '*'"""
    stage = "*"
    """The name of the stage used in the policy. By default this is set to '*'"""

    def __init__(self, principal, aws_account_id):
        self.aws_account_id = aws_account_id
        self.principal_id = principal
        self.allow_methods = []
        self.deny_methods = []

    def _add_method(self, effect, verb, resource, conditions):
        """Adds a method to the internal lists of allowed or denied methods. Each object in
        the internal list contains a resource ARN and a condition statement. The condition
        statement can be null."""
        if verb != "*" and not hasattr(HttpVerb, verb):
            raise NameError("Invalid HTTP verb " + verb + ". Allowed verbs in HttpVerb class")
        resource_pattern = re.compile(self.pathRegex)
        if not resource_pattern.match(resource):
            raise NameError("Invalid resource path: " + resource + ". Path should match " + self.pathRegex)

        if resource[:1] == "/":
            resource = resource[1:]

        resource_arn = ("arn:aws:execute-api:" +
                        self.region + ":" +
                        self.aws_account_id + ":" +
                        self.restApiId + "/" +
                        self.stage + "/" +
                        verb + "/" +
                        resource)

        if effect.lower() == "allow":
            self.allow_methods.append({
                'resourceArn': resource_arn,
                'conditions': conditions
            })
        elif effect.lower() == "deny":
            self.deny_methods.append({
                'resourceArn': resource_arn,
                'conditions': conditions
            })

    @classmethod
    def _get_empty_statement(cls, effect):
        """Returns an empty statement object prepopulated with the correct action and the
        desired effect."""
        statement = {
            'Action': 'execute-api:Invoke',
            'Effect': effect[:1].upper() + effect[1:].lower(),
            'Resource': []
        }
        return statement

    def _get_statement_for_effect(self, effect, methods):
        """This function loops over an array of objects containing a resourceArn and
        conditions statement and generates the array of statements for the policy."""
        statements = []

        if len(methods) > 0:
            statement = self._get_empty_statement(effect)

            for cur_method in methods:
                if cur_method['conditions'] is None or len(cur_method['conditions']) == 0:
                    statement['Resource'].append(cur_method['resourceArn'])
                else:
                    conditional_statement = self._get_empty_statement(effect)
                    conditional_statement['Resource'].append(cur_method['resourceArn'])
                    conditional_statement['Condition'] = cur_method['conditions']
                    statements.append(conditional_statement)

            statements.append(statement)

        return statements

    def allow_all_methods(self):
        """Adds a '*' allow to the policy to authorize access to all methods of an API"""
        self._add_method("Allow", HttpVerb.ALL, "*", [])

    def deny_all_methods(self):
        """Adds a '*' allow to the policy to deny access to all methods of an API"""
        self._add_method("Deny", HttpVerb.ALL, "*", [])

    def allow_method(self, verb, resource):
        """Adds an API Gateway method (Http verb + Resource path) to the list of allowed
        methods for the policy"""
        self._add_method("Allow", verb, resource, [])

    def deny_method(self, verb, resource):
        """Adds an API Gateway method (Http verb + Resource path) to the list of denied
        methods for the policy"""
        self._add_method("Deny", verb, resource, [])

    def allow_method_with_conditions(self, verb, resource, conditions):
        """Adds an API Gateway method (Http verb + Resource path) to the list of allowed
        methods and includes a condition for the policy statement. More on AWS policy
        conditions here: http://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_elements.html#Condition"""
        self._add_method("Allow", verb, resource, conditions)

    def deny_method_with_conditions(self, verb, resource, conditions):
        """Adds an API Gateway method (Http verb + Resource path) to the list of denied
        methods and includes a condition for the policy statement. More on AWS policy
        conditions here: http://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_elements.html#Condition"""
        self._add_method("Deny", verb, resource, conditions)

    def build(self):
        """Generates the policy document based on the internal lists of allowed and denied
        conditions. This will generate a policy with two main statements for the effect:
        one statement for Allow and one statement for Deny.
        Methods that includes conditions will have their own statement in the policy."""
        if ((self.allow_methods is None or len(self.allow_methods) == 0) and
                (self.deny_methods is None or len(self.deny_methods) == 0)):
            raise NameError("No statements defined for the policy")

        policy = {
            'principalId': self.principal_id,
            'policyDocument': {
                'Version': self.version,
                'Statement': []
            }
        }

        policy['policyDocument']['Statement'].extend(self._get_statement_for_effect("Allow", self.allow_methods))
        policy['policyDocument']['Statement'].extend(self._get_statement_for_effect("Deny", self.deny_methods))

        return policy


if __name__ == '__main__':
    from pprint import pformat
    test_data = {'username': 'tester',
                 'password': 'blub'}
    stage = 'dev'  # simple quick setup for ad-hoc testing
    test_token = 'somethingsomethingsomethingsomething'

    sample_event = {
        "type": "TOKEN",
        "authorizationToken": test_token,
        "methodArn": "arn:aws:execute-api:eu-west-1:xxxxxx:xxxxxxxx/{0}/get/GET/".format(stage)
    }
    handler_response = lambda_handler(sample_event, {})
    print(pformat(handler_response))
