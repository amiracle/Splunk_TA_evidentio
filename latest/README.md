When installing the Evident.io TA for Splunk, you'll need to copy the tgz file (Splunk_TA_evidentio.tgz) to the $SPLUNK_HOME/etc/apps/ directory then simply run the command "tar xzvf Splunk_TA_evidentio.tgz -C Splunk_TA_aws  .  This will expand the following files into the Splunk_TA_aws folder:

bin/aws_evidentio.py
default/data/ui/manager/data_inputs_aws-evidentio.xml
default/props.conf
default/inputs.conf
README/inputs.conf.spec

Once you're done, restart your Splunk instance and you'll see the Evident.io input show up in your Data Inputs Screen.

Thanks,
Kam
kam@splunk.com
