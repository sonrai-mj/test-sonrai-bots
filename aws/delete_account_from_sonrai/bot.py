import logging
import sys
import re
import time

def run(ctx):
    object_srn = ctx.resource_srn
    #extract the account from the SRN
    pattern = re.compile(r"\d{12}")
    accountToDelete = re.sub("srn:aws:account::\d+\/Account\/","", object_srn)

    if not re.match(pattern, accountToDelete):
      logging.error("Invalid account format for account {}".format(accountToDelete))
      sys.exit(0)

    # Create GraphQL client
    graphql_client = ctx.graphql_client()

    # GraphQL query to CloundAccounts SRN
    # If account exists more than once, Log and fail the bot
    query = '''
            query CloudAccounts ($account:String) {
              PlatformCloudAccounts(where: { cloudType: { value: "aws" },
                blob: {op:CONTAINS, value:$account}
              }) {
                count
                items {
                  srn
                }
              }
            }
        '''
    # Account to search for
    variables = {"account": accountToDelete}
    logging.info('Searching for account srn')
    r = graphql_client.query(query, variables)

    # now check to see if there is more than one collector
    count = r['PlatformCloudAccounts']['count']

    if not count == 1:
        # Account exists too many times
        logging.error("Found {} account exists {} times in the platform, can't delete".format(accountToDelete, count))
        sys.exit()

    # all good, so we can proceed with the delete

    print (accountToDelete)
    # build the new roleARN and botRoleARN based on accountToAdd
    srnToDelete = r['PlatformCloudAccounts']['items'][0]['srn']
    print (srnToDelete)
    query = ( "mutation deletePlatformCloudAccount  {" +
            " DeletePlatformcloudaccount(" +
            '    srn: "' + srnToDelete + '"' +
            "  ) } " )
    variables = { }

    # Deleting account from platform
    logging.info('Deleting Account {} from platform'.format(accountToDelete))
    graphql_client.query(query, variables)