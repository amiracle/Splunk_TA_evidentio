"""
Modular Input for AWS Evidentio
"""

import sys
import os
import time
import calendar
import gzip
import io
import re
import json

try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET

from taaws.aws_accesskeys import APPNAME, KEY_NAMESPACE, KEY_OWNER

from taaws.aws_accesskeys import AwsAccessKeyManager
from splunklib import modularinput as smi

import boto.sqs
import boto.sqs.jsonmessage
import boto.s3.connection
import boto.exception

import logging
from taaws.log import setup_logger
logger = setup_logger(os.path.basename(__file__), level=logging.DEBUG)

import taaws.s3util


class MyScript(smi.Script):

    def __init__(self):

        super(MyScript, self).__init__()
        self._canceled = False
        self._ew = None

        self.input_name = None
        self.input_items = None
        self.enable_additional_notifications = False

        # self.remove_files_when_done = False
        # self.exclude_describe_events = True
        # self.blacklist = None
        # self.blacklist_pattern = None

    def get_scheme(self):
        """overloaded splunklib modularinput method"""

        scheme = smi.Scheme("AWS Evidentio")
        scheme.description = ("Collect notifications produced by AWS Evidentio."
                              "The feature must be enabled and its SNS topic must be subscribed to an SQS queue.")
        scheme.use_external_validation = True
        scheme.streaming_mode_xml = True
        scheme.use_single_instance = False
        # defaults != documented scheme defaults, so I'm being explicit.
        scheme.add_argument(smi.Argument("name", title="Name",
                                         description="Choose an ID or nickname for this configuration",
                                         required_on_create=True))
        scheme.add_argument(smi.Argument("aws_account", title="AWS Account",
                                         description="AWS account",
                                         required_on_create=True, required_on_edit=True))
        scheme.add_argument(smi.Argument("aws_region", title="SQS Queue Region",
                                         description=("Name of the AWS region in which the"
                                                      " notification queue is located. Regions should be entered as"
                                                      " e.g., us-east-1, us-west-2, eu-west-1, ap-southeast-1, etc."),
                                         required_on_create=True, required_on_edit=True))
        scheme.add_argument(smi.Argument("sqs_queue", title="SQS Queue Name",
                                         description=("Name of queue to which notifications of AWS Evident.io"
                                                      " are sent. The queue should be subscribed"
                                                      " to the AWS Evident.io SNS topic."),
                                         required_on_create=True, required_on_edit=True))
        scheme.add_argument(smi.Argument("enable_additional_notifications", title="Enable Debug",
                                         description=("Index additional SNS/SQS events to help with troubleshooting."),
                                         data_type=smi.Argument.data_type_boolean,
                                         required_on_create=False))

        return scheme

    @staticmethod
    def get_access_key_pwd_real(session_key="", aws_account_name="default"):
        if not AwsAccessKeyManager:
            raise Exception("Access Key Manager needed is not imported successfully")

        km = AwsAccessKeyManager(KEY_NAMESPACE, KEY_OWNER, session_key)

        logger.info("get account name: " + aws_account_name)

        acct = km.get_accesskey(name=aws_account_name)
        if not acct:
            # No recovering from this...
            logger.log(logging.FATAL, "No AWS Account is configured.")
            raise Exception("No AWS Account is configured.")

        return acct.key_id, acct.secret_key

    def validate_input(self, definition):
        """overloaded splunklib modularinput method"""

        self.input_items = definition.parameters
        # try:
        #     self.configure_blacklist()
        # except Exception as e:
        #     raise Exception("Exclude Describe Events Blacklist Configuration: {}: {}".format(type(e).__name__, e))

        session_key = definition.metadata['session_key']
        aws_account_name = self.input_items.get("aws_account") or "default"
        (key_id, secret_key) = self.get_access_key_pwd_real(session_key=session_key, aws_account_name=aws_account_name)

        sqs_conn = taaws.s3util.connect_sqs(self.input_items['aws_region'], key_id, secret_key, session_key)

        if sqs_conn is None:
            raise Exception("Invalid SQS Queue Region: {}".format(self.input_items['aws_region']))

        s3_conn = taaws.s3util.connect_s3(key_id, secret_key, session_key)

        logger.log(logging.DEBUG, "Connected to SQS and S3 successfully!")

        sqs_queue = sqs_conn.get_queue(self.input_items['sqs_queue'])

        if sqs_queue is None:
            try:
                # verify it isn't an auth issue
                sqs_queues = sqs_conn.get_all_queues()
            except boto.exception.SQSError as e:
                if e.status == 403 and e.reason == 'Forbidden':
                    if e.error_code == 'InvalidClientId':
                        raise Exception("Authentication Key ID is invalid. Check App Setup.")
                    elif e.error_code == 'SignatureDoesNotMatch':
                        raise Exception("Authentication Secret Key is invalid. Check App Setup.")
            except Exception as e:
                    raise Exception("Failed AWS Validation: {}: {} {} ({}): {}".format(
                        type(e).__name__, e.status, e.reason, e.error_code, e.error_message))

            else:
                raise Exception("Invalid SQS Queue Name: {}".format(self.input_items['sqs_queue']))

    def _exit_handler(self, signum, frame=None):
        self._canceled = True
        logger.log(logging.INFO, "Cancellation received.")

        if os.name == 'nt':
            return True


    def stream_events(self, inputs, ew):
        """overloaded splunklib modularinput method"""
        logger.log(logging.DEBUG, "Start streaming.")
        self._ew = ew

        if os.name == 'nt':
            import win32api
            win32api.SetConsoleCtrlHandler(self._exit_handler, True)
        else:
            import signal
            signal.signal(signal.SIGTERM, self._exit_handler)
            signal.signal(signal.SIGINT, self._exit_handler)

        # because we only support one stanza...
        self.input_name, self.input_items = inputs.inputs.popitem()

        self.enable_additional_notifications = (self.input_items.get('enable_additional_notifications')or 'false').lower() in (
             '1', 'true', 'yes', 'y', 'on')
        # self.configure_blacklist()

        # logger.log(logging.DEBUG, "blacklist regex for eventNames is {}".format(self.blacklist))

        session_key = self.service.token
        aws_account_name = self.input_items.get("aws_account") or "default"
        (key_id, secret_key) = self.get_access_key_pwd_real(session_key=session_key, aws_account_name=aws_account_name)

        # Try S3 Connection
        s3_conn = taaws.s3util.connect_s3(key_id, secret_key, session_key)

        # Create SQS Connection
        sqs_conn = taaws.s3util.connect_sqs(self.input_items['aws_region'], key_id, secret_key, session_key)

        if sqs_conn is None:
            # No recovering from this...
            logger.log(logging.FATAL, "Invalid SQS Queue Region: {}".format(self.input_items['aws_region']))
            raise Exception("Invalid SQS Queue Region: {}".format(self.input_items['aws_region']))
        else:
            logger.log(logging.DEBUG, "Connected to SQS successfully")

        try:

            while not self._canceled:

                #logger.log(logging.INFO, "The outer loop has started...")

                if self._canceled:
                    break

                sqs_queue = sqs_conn.get_queue(self.input_items['sqs_queue'])

                if sqs_queue is None:
                    try:
                        # verify it isn't an auth issue
                        sqs_queues = sqs_conn.get_all_queues()
                    except boto.exception.SQSError as e:
                        logger.log(logging.FATAL, "sqs_conn.get_all_queues(): {} {}: {} - {}".format(
                            e.status, e.reason, e.error_code, e.error_message))
                        raise
                    else:
                        logger.log(logging.FATAL, "sqs_conn.get_queue(): Invalid SQS Queue Name: {}".format(
                            self.input_items['sqs_queue']))
                        raise

                sqs_queue.set_message_class(boto.sqs.message.RawMessage)

                # num_messages=10 was chosen based on aws pricing faq.
                # see request batch pricing: http://aws.amazon.com/sqs/pricing/
                notifications = sqs_queue.get_messages(num_messages=10, visibility_timeout=20, wait_time_seconds=20)
                logger.log(logging.DEBUG, "Length of notifications is: %s" % len(notifications))

                start_time = time.time()
                completed = []
                failed = []

                stats = {'written': 0}

                # if not notifications or self._canceled:
                #     continue

                # Exit if SQS returns nothing. Wake up on interval as specified on inputs.conf
                if len(notifications) == 0:
                    self._canceled = True
                    break

                for notification in notifications:
                    if self._canceled:
                        break
                    try:
                        envelope = json.loads(notification.get_body())
                        message = json.loads(envelope.get('Message',''))

                        ## Process: config notifications, history and snapshot notifications (additional)

                        # Process pass notifications with payload, check status
                        if message.get('status', '') == 'pass':
                            logger.log(logging.DEBUG, "Consuming configuration change data in SQS payload.")
                            # determine _time for the event
			    risk_level = message.get('risk_level', '')
			    signature = message.get('signature','')
			    description = message.get('description','')
                            # write the event
                            event = smi.Event(data=json.dumps(message),
                                          time=time.time(),
                                          source="aws:evidentio:notification")
                            ew.write_event(event)
                            stats['written'] += 1
                            completed.append(notification)

			# Process fail notifications with payload, check status
                        elif message.get('status', '') == 'fail':
                            logger.log(logging.DEBUG, "Consuming configuration change data in SQS payload.")
                            # determine _time for the event
                            risk_level = message.get('risk_level', '')
                            signature = message.get('signature','')
                            description = message.get('description','')
                            # write the event
                            event = smi.Event(data=json.dumps(message),
                                          time=time.time(),
                                          source="aws:evidentio:notification")
                            ew.write_event(event)
                            stats['written'] += 1
                            completed.append(notification)

                        else:
                            logger.log(logging.ERROR, "None of the notification satisfy capture conditions for AWS Evident.io.")
                            continue

                    # What do we do with non JSON data? Leave them in the queue but recommend customer uses a SQS queue only for AWS Evident.io?
                    except Exception as e:
                        failed.append(notification)
                        logger.log(logging.ERROR, "Problems decoding JSON in notification: {} {}.".format(
                            type(e).__name__, e))
                        continue


                notification_delete_errors = 0
                # Delete ingested notifications
                if completed:
                    br = sqs_queue.delete_message_batch(completed)
                    if br.errors:
                        notification_delete_errors = len(br.errors)

                else:
                    logger.log(logging.INFO, ("{} completed, {} failed while processing a notification batch of {}"
                                              " [{} errors deleting {} notifications]"
                                              "  Elapsed: {:.3f}s").format(
                           len(completed), len(failed), len(notifications), notification_delete_errors, len(completed),
                           time.time() - start_time))

        except Exception as e:
            logger.log(logging.FATAL, "Outer catchall: %s: %s", type(e).__name__, e)
            raise


if __name__ == "__main__":

    logger.log(logging.INFO, "STARTED: {}".format(len(sys.argv) > 1 and sys.argv[1] or ''))
    exitcode = MyScript().run(sys.argv)
    logger.log(logging.INFO, "EXITED: {}".format(exitcode))
    sys.exit(exitcode)
