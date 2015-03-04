# Splunk_TA_evidentio
Splunk Technology Add-on for Evident.io

This Technology Add-on (TA) is for people who have an account with Evident.io (http://www.evident.io) and want to gather their alerts into their Splunk instance.  This TA requires both the Splunk App for AWS (https://apps.splunk.com/app/1274/) AND the Splunk Add-on for Amazon Web Services (https://apps.splunk.com/app/1876/). 

Here's a list of files that are added to your $SPLUNK_HOME/etc/apps/Splunk_TA_evidentio folder:

    bin/aws_evidentio.py
    default/data/ui/manager/data_inputs_aws-evidentio.xml
    default/props.conf
    default/inputs.conf
    README/inputs.conf.spec

##You'll need to manually create the aws-evidentio index

Here's a list of the configuration files:

props.conf
-------------
    ##################################
    ###         AWS Evidentio      ###
    ##################################
    [aws:evidentio]
    SHOULD_LINEMERGE = false
    TRUNCATE = 8388608
    TIME_PREFIX = \"eventTime\"\s*\:\s*\"
    TIME_FORMAT = %Y-%m-%dT%H:%M:%S%Z
    MAX_TIMESTAMP_LOOKAHEAD = 28
    KV_MODE = json
    
    # Notifications/Diff Payloads
    [source::aws:evidentio:notification]
    sourcetype = aws:evidentio
    #SHOULD_LINEMERGE = false
    #TRUNCATE = 8388608
    #TIME_PREFIX = \"eventTime\"\s*\:\s*\"
    #TIME_FORMAT = %Y-%m-%dT%H:%M:%S.%3NZ
    #TZ = GMT
    #MAX_TIMESTAMP_LOOKAHEAD = 28
    #KV_MODE = json
    #ANNOTATE_PUNCT = false

inputs.conf
-------------
    [aws_evidentio]
    aws_account =
    sourcetype = aws:evidentio
    #exclude_describe_events = true
    enable_additional_notifications = false
    queueSize = 128KB
    persistentQueueSize = 24MB
    interval = 30
  
indexes.conf
--------------
    [aws-evidentio]
    coldPath = $SPLUNK_DB/aws-evidentio/colddb
    homePath = $SPLUNK_DB/aws-evidentio/db
    thawedPath = $SPLUNK_DB/aws-evidentio/thaweddb

README\inputs.conf.spec
-------------------------
    [aws_evidentio://<name>]
    aws_account = AWS account used to connect to AWS
    aws_region = AWS region of log notification SQS queue
    sqs_queue = Starling Notification SQS queue
    enable_additional_notifications = Enable collection of additional helper notifications

