#! /usr/bin/env python

from __future__ import print_function

import argh
import os


@argh.dispatch_command
@argh.arg('-p', '--playbook', help='which playbook to run', default='playbook.yml', type=str)
@argh.arg('-e', '--environment', help='environment to deploy to', default='dev', type=str)
@argh.arg('-v', '--verbose', help='enable verbose output', default=False, action='store_true')
def deploy(*args, **kwargs):
    command = 'ansible-playbook %s -i hosts --extra-vars \'{\"environ\": \"%s\"}\'' % (kwargs['playbook'],
                                                                                       kwargs['environment'])

    if kwargs['verbose']:
        command += ' -vvvv'
        print(command)

    os.system(command)
