import logging
import sonrai.platform.aws.arn

log = logging.getLogger()

def run(ctx):
    ticket = ctx.config
    log.info(ticket)
    exit(0)
    for item in ctx.resourceSRN:
        print (item)
    exit(0)
    user_arn = sonrai.platform.aws.arn.parse(ctx.resource_id)
    user_name = user_arn \
        .assert_service("iam") \
        .assert_type("user") \
        .name
    # Delete login profile
    log.info("[{}] Deleting login profile, if any".format(user_arn))
    try:
        client.delete_login_profile(UserName=user_name,)
    except botocore.exceptions.ClientError as e:
        error = e.response.get("Error")
        # AWS User may not have a login profile already
        if not error or error.get("Code") != "NoSuchEntity":
            raise e

    # Delete access keys
    for response in _responses(client.list_access_keys, UserName=user_name):
        for access_key in response['AccessKeyMetadata']:
            access_key_id = access_key['AccessKeyId']
            log.info("[{}] Deleting access key: {}".format(user_arn, access_key_id))
            client.delete_access_key(UserName=user_name, AccessKeyId=access_key_id)

    log.info("[{}] User disabled".format(user_arn))
