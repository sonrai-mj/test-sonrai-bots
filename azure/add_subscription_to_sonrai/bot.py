import logging
import sys
import re
import time

def run(ctx):
    object_srn = ctx.resource_srn
    #extract the account from the SRN
    pattern = re.compile(r"[0-9a-f\-]{36}")
    subscriptionToAdd = re.sub("srn:azure:Microsoft.Subscription::[0-9a-f\-]+\/Subscription\/","", object_srn)
    tenantToAdd = re.sub("srn:azure:Microsoft.Subscription::([0-9a-f\-]+)\/Subscription\/.*",r"\1", object_srn)

    if not re.match(pattern, subscriptionToAdd):
      logging.error("Invalid subscription format: {}".format(subscriptionToAdd))
      sys.exit(0)
    if not re.match(pattern, tenantToAdd):
      logging.error("Invalid tenant format: {}".format(tenantToAdd))
      sys.exit(0)

    # Create GraphQL client
    graphql_client = ctx.graphql_client()

    # GraphQL query to find collectors and roles
    # This will find the collector SRN and the roleARN that is currently in user
    # If there are more than one collectors we don't know which one to assign it to
    # Log and fail the bot
    query = '''
        query PlatFormAccounts
           ($name: String)
            { PlatformAccounts(
              where: {
                name: { op:CONTAINS, value: $name}
                cloudType: { value: "azure" }
              } ) 
              { count
                items {
                  srn
                  containsCloudAccount {
                  items {
                    srn
                    blob
                  }
                }
              }
            }
          }
        '''
    # Leaving the variable "name" blank, but if someone wanted to specify
    # the name of a specific collector they could do that here
    variables = {"name": ""}
    logging.info('Finding Azure Collector')
    r = graphql_client.query(query, variables)

    # first check to see if the account is already on that collector
    for items in r['PlatformAccounts']['items']:
      for accounts in items['containsCloudAccount']['items']:
        existingSubscription = accounts['blob']['subscriptionId']
        if existingSubscription == subscriptionToAdd:
          logging.error("Subscription {} is already added to this collector".format(subscriptionToAdd))
          sys.exit()

    # now check to see if there is more than one collector
    count = r['PlatformAccounts']['count']

    if count > 1:
        #found too many collectors
        logging.error("Found {} collectors, but can only add account to 1 collector. Uncertain how proceed, so stopping".format(count))
        sys.exit()

    # all good, so no we can pull out the parts we need to add the new account
    collectorSRN = r['PlatformAccounts']['items'][0]['srn']

    currentTime = round(time.time()*1000)
    query = ''' mutation createSubAccount($account: PlatformcloudaccountCreator!) {
                  CreatePlatformcloudaccount(value: $account) {
                    srn
                    blob
                    cloudType
                    name
                    organizationId
                    resourceId
                    __typename
                  }
                } '''
    variables = {"account":{"containedByAccount":
                                  {"add":collectorSRN},
                              "cloudType":"azure",
                              "blob":{"subscriptionId":subscriptionToAdd,
                                      "tenantId":tenantToAdd,
                                      "runDateTime":currentTime,
                                      }
                              }
                  }

    # Adding account to collector
    logging.info('Adding Subscription {} to collector {}'.format(subscriptionToAdd, collectorSRN))
    graphql_client.query(query, variables)