import logging
import logging.handlers
import sys
import re
import time

def run(ctx):
    object_srn = ctx.resource_srn
    object_config = ctx.config

    object_ticketKey = object_config.get('data').get('ticket').get('ticketKey')

    print (object_ticketKey)
    print (object_srn)

    # Create GraphQL client
    graphql_client = ctx.graphql_client()

    # GraphQL query to Map the Ticket's Policy to a framework
    query = '''
            query cp ($srn: String) {
                  ControlPolicies(
                    where: {
                      srn: {
                        value: $srn
                      }
                    }
                  ) {
                    count
                    items {
                      title
                      srn
                      containedByControlFramework {
                        items {
                          title
                          description
                          srn
                          enabled
                        }
                      }
                    }
                  }
                }
        '''

    # SRN is ticketKey
    variables = {"srn": object_ticketKey}
    logging.info('Searching for ticketKey srn: {}'.format(object_ticketKey))
    r = graphql_client.query(query, variables)

    # now check to see if there is more than one collector
    count = r['ControlPolicies']['count']
    description = r['ControlPolicies']['items'][0]['containedByControlFramework']['items'][0]['description']

    for line in description.split('\n'):
        if 'SYSLOG_DESTINATION' in line:
            syslogDst = line

    if syslogDst is None:
        Exception

    exit (0)

    # build the new roleARN and botRoleARN based on accountToAdd
    # srnToDelete = r['PlatformCloudAccounts']['items'][0]['srn']
    # print (srnToDelete)
    # query = ( "mutation deletePlatformCloudAccount  {" +
    #         " DeletePlatformcloudaccount(" +
    #         '    srn: "' + srnToDelete + '"' +
    #         "  ) } " )
    # variables = { }
    #
    # # Deleting account from platform
    # logging.info('Deleting Account {} from platform'.format(accountToDelete))
    # graphql_client.query(query, variables)