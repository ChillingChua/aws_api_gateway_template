AWS API Gateway deployment template
===================================

This is a small template to deploy different endpoints to an AWS API 
Gateway.
It is not intended to be used as is, it's not an out of the box system
to be used. All this is, is a template to get you started with a setup
for your own system, Too much is tailored to specific use cases to be
completely integrated into this setup.

_All mechanisms can most likely be done in multiple different ways using
the services provided inside AWS, but this is a template from a solution
used in one of my contracting projects, and it works at least ;)_

This template does NOT use the versioning for S3 files or any of the
stage features of the API Gateway. Every environment uses a separate
API with a different URL. This was done to have a complete separation 
of different environments as they might need access to resources which 
should not be mixed up.

All logging done with the default Python logging is stored in AWS 
CloudWatch logs.

The `requirements.txt` in the main source folder is a full set of needed
dependencies for every function used. This is used to conveniently
create virtual environments, NOT deployment. Separate `requirements.txt`
in each function folders must be maintained for deployment, as not all
dependencies are used in every function.

Example functions:

* add some information to the system (HTTP POST)
* authentication (custom authorizer lambda function)
* delete information from the system (HTTP DELETE)
* get information (HTTP GET)
* update some information (HTTP PUT)

Thanks to:
https://github.com/awslabs/aws-apigateway-lambda-authorizer-blueprints
https://github.com/YPlan/ansible-python-lambda

for inspiration and 'What the hell are they doing'-reference

TODO:
=====
* get rid of multiple requirements.txt
* change ARN building in 'create_CF_api_gateway', best with request to AWS
* build config.py files from parameters set in 'set_X_facts' not just substitution

Usage:
=======
`ansible-playbook playbook.yml --extra-vars '{"environ": "ENV"}`
with ENV being something like 'dev', 'staging', 'production', etc...

Shortcut script: `deploy.py`
```
usage: deploy.py [-h] [-p PLAYBOOK] [-e ENVIRONMENT] [-v]

optional arguments:
  -h, --help            show this help message and exit
  -p PLAYBOOK, --playbook PLAYBOOK
                        which playbook to run (default: 'playbook.yml')
  -e ENVIRONMENT, --environment ENVIRONMENT (default: 'dev')
  -v, --verbose         enable verbose output (default: False)
```

Build process:
==============

The deployment / build process is separated into smaller steps which
are executed in order to make sure everything is set up.

step 1:
=======
This build process creates a `workspace` directory and copies all needed
source code into folders for each lambda function. All needed libraries
are then installed into the new folders based on the `requirements.txt`
file in each subfolder. A configuration file is created for environment
setup, i.e. log level.

step 2:
=======
The files are then zip'ed and copied into the `build` folder, in case
they are needed at any point. The naming convention for these zip files
is `<environment>-<AWS function name>.zip`, i.e. `dev-getstuff.zip`.

step 3:
=======
The created zip files are then uploaded to a S3 bucket for usage in AWS.

step 4:
=======
Lambda functions are created with Cloudformation templates generated
from environment variables to in environment specific setup. This
is used for VPC settings etc 

step 5:
=======
In this step the API Gateway definitions are build from the template 
and applied. The API is NOT deployed at this stage, this has to be done
manually from the AWS UI.
The authorizer deployed is always names `lambda auth` here but
points to the environment specific lambda function via the ARN
definition.