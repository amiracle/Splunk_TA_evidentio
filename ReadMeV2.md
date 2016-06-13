# Splunk_TA_evidentio
Splunk Technology Add-on for Evident.io Version 2.0

This Technology Add-on (TA) is for people who have an account with Evident.io (http://www.evident.io) and want to gather their alerts into their on-premis Splunk or Splunk Cloud instance.  Unlike the previous version, you will no longer need to have the App for AWS installed in order to pull the data from Evident. This solution will now use an AWS lambda function and the Splunk HTTP Event Collector (HEC). 

Here is what you will need in order to get this solution up and running in your AWS environment:
    
    AWS CLI tools (http://docs.aws.amazon.com/cli/latest/userguide/installing.html) 
    KMS Key (https://aws.amazon.com/blogs/aws/new-key-management-service/) 
    Access to creating a Lambda function in your AWS account
    Splunk Token from the HTTP Event Collector (See below for links to documentation on HTTP Event Collector)

    
Reference Material :

    http://dev.splunk.com/view/event-collector/SP-CAAAE7T - Video on setting up a Lambda function with Splunk.
    https://aws.amazon.com/blogs/aws/new-key-management-service/ - Setup Splunk HTTP Event Collector 
    https://aws.amazon.com/blogs/aws/new-key-management-service/ - Walk through for HTTP Event Collector (Splunk Cloud)


Here's a list of files that are added to your $SPLUNK_HOME/etc/apps/Splunk_TA_evidentio folder:

    default/props.conf
    default/inputs.conf
    
Here's a list of the configuration files:

props.conf
-------------
    ##################################
    ###         AWS Evidentio      ###
    ##################################
    [aws:evidentio]
    INDEXED_EXTRACTIONS = JSON
    #SHOULD_LINEMERGE = false
    #TRUNCATE = 8388608
    TIME_PREFIX = \"TimeStamp\"\s*\:\s*\"
    TIME_FORMAT = %Y-%m-%dT%H:%M:%S%Z
    MAX_TIMESTAMP_LOOKAHEAD = 28
    #KV_MODE = json
    
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

