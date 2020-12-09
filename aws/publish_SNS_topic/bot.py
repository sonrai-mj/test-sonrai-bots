import sonrai.platform.aws.arn
import logging
import re
import sys

def run(ctx):
    # Create AWS identity and access management client
    sns_client = ctx.get_client().get('sns')
    resource_id = ctx.resource_id

    topics = sns_client.list_topics()

    pattern = re.compile(r"arn:aws:sns:\S+:\d{12}:SendMeEmail")
    #pattern = re.compile(r"arn:aws:sns:\S+:\d{12}:sonrai")
    topicArn = None
    for arn in topics['Topics']:
        if re.match(pattern, arn['TopicArn']):
            topicArn = arn['TopicArn']

    if topicArn is None:
        logging.error("Did not find a valid sonrai Topic to publish")
        sys.exit(9)

    #topicArn = topics['Topics'][0]['TopicArn']

    message = "This is test message 2. This means that my SNS is working"
    subject = "Sonrai Alert - (Policy Name goes here)"


    exit (0)
    pubResponse = sns_client.publish (
        TopicArn = topicArn,
        Message = message,
        Subject = subject
    )

    print (pubResponse)

    exit (0)


    data = None
    user_name = None
    access_key_id = None

    data = ctx.get_policy_evidence()
    metadata_list = data.get('metadata')

    for metadata in metadata_list:
        if 'accessKey.userName:' in metadata:
            user_name = metadata.split(":")[1]
            access_key_id = data.get('name')

    logging.info('deleting accesskey: {} for user: {}'.format(access_key_id, user_name))
    iam_client.delete_access_key(UserName=user_name, AccessKeyId=access_key_id)
