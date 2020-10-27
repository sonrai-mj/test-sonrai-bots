import logging
import sys
import re
import time

def run(ctx):
    object_srn = ctx.resource_srn
    #extract the account from the SRN
    pattern = re.compile(r"\d{12}")
    accountToAdd = re.sub("srn:aws:account::\d+\/Account\/","", object_srn)

    if not re.match(pattern, accountToAdd):
      logging.error("Invalid account number {}".format(accountToAdd))
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
                cloudType: { value: "aws" }
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
    logging.info('Finding Collector, roleArn and botRoleArn')
    r = graphql_client.query(query, variables)

    # first check to see if the account is already on that collector
    for items in r['PlatformAccounts']['items']:
      for accounts in items['containsCloudAccount']['items']:
        existingAccount = accounts['blob']['accountNumber']
        if existingAccount == accountToAdd:
          logging.error("Account {} is already added to this collector".format(accountToAdd))
          sys.exit()

    # now check to see if there is more than one collector
    count = r['PlatformAccounts']['count']

    if count > 1:
        #found too many collectors
        logging.error("Found {} collectors, but can only add account to 1 collector. Uncertain how proceed, so stopping".format(count))
        sys.exit()

    # all good, so no we can pull out the parts we need to add the new account
    collectorSRN = r['PlatformAccounts']['items'][0]['srn']
    roleARN = r['PlatformAccounts']['items'][0]['containsCloudAccount']['items'][0]['blob']['roleArn']
    botRoleARN =  r['PlatformAccounts']['items'][0]['containsCloudAccount']['items'][0]['blob']['botRoleArn']

    # build the new roleARN and botRoleARN based on accountToAdd
    newRoleARN = re.sub("\d+", accountToAdd, roleARN)
    newBotRoleARN = ""
    if botRoleARN != "":
        # if there is a bot role, create new bot role ARN
        newBotRoleARN = re.sub("\d+", accountToAdd, botRoleARN)

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
    variables = { "account": {"containedByAccount":
                                  {"add":collectorSRN},
                              "cloudType":"aws",
                              "blob":{"accountNumber":accountToAdd,
                                      "roleArn":newRoleARN,
                                      "runDateTime": currentTime,
                                      "botRoleArn":newBotRoleARN}
                              }
                  }

    # Adding account to collector
    logging.info('Adding Account {} to collector {}'.format(accountToAdd, collectorSRN))
    graphql_client.query(query, variables)