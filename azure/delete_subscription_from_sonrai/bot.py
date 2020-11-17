import logging
import sys
import re
import time

def run(ctx):
    object_srn = ctx.resource_srn
    #extract the subscription from the SRN
    pattern = re.compile(r"[0-9a-f\-]{36}")
    subscriptionToDelete = re.sub("srn:azure:Microsoft.Subscription::[0-9a-f\-]+\/Subscription\/","", object_srn)
    tenantToDelete = re.sub("srn:azure:Microsoft.Subscription::([0-9a-f\-]+)\/Subscription\/.*",r"\1", object_srn)

    if not re.match(pattern, subscriptionToDelete):
      logging.error("Invalid subscription format: {}".format(subscriptionToDelete))
      sys.exit(0)
    if not re.match(pattern, tenantToDelete):
      logging.error("Invalid tenant format: {}".format(tenantToDelete))
      sys.exit(0)

    # Create GraphQL client
    graphql_client = ctx.graphql_client()

    # GraphQL query to CloundSubscriptions SRN
    # If subscription exists more than once, Log and fail the bot
    query = '''
            query CloudAccounts ($subscription:String) {
              PlatformCloudAccounts(where: { cloudType: { value: "azure" },
                blob: {op:CONTAINS, value:$subscription}
              }) {
                count
                items {
                  srn
                }
              }
            }
        '''
    # Subscription to search for
    variables = {"subscription": subscriptionToDelete}
    logging.info('Searching for subscription srn')
    r = graphql_client.query(query, variables)

    # now check to see if there is more than one collector
    count = r['PlatformCloudAccounts']['count']

    if not count == 1:
        # Subscription exists too many times
        logging.error("Found {} subscription exists {} times in the platform, can't delete".format(subscriptionToDelete, count))
        sys.exit()

    # all good, so we can proceed with the delete

    # build the new roleARN and botRoleARN based on subscriptionToDelete
    srnToDelete = r['PlatformCloudAccounts']['items'][0]['srn']
    query = ( "mutation deletePlatformCloudAccount  {" +
            " DeletePlatformcloudaccount(" +
            '    srn: "' + srnToDelete + '"' +
            "  ) } " )
    variables = { }

    # Deleting subscription from platform
    logging.info('Deleting Subscription {} from platform'.format(subscriptionToDelete))
    graphql_client.query(query, variables)