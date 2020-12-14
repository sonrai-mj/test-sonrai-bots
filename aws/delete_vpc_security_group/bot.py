import sonrai.platform.aws.arn

import logging
import re

def run(ctx):
    # Delete AWS VPC Security Group
    sg_client = ctx.get_client().get('ec2')
    object_srn = ctx.resource_srn
    sgId = re.sub("srn:aws:ec2::\d+\/NetworkPolicy\/","",object_srn)

    exit (0)

    data = None
    user_name = None
    access_key_id = None

    data = ctx.get_policy_evidence()
    metadata_list = data.get('metadata')

    for metadata in metadata_list:
        if 'accessKey.userName:' in metadata:
            user_name = metadata.split(":")[1
            ]
            access_key_id = data.get('name')

    logging.info('deleting accesskey: {} for user: {}'.format(access_key_id, user_name))
    iam_client.delete_access_key(UserName=user_name, AccessKeyId=access_key_id)