import logging
import sys
import re
import time
from datetime import datetime, timedelta

def run(ctx):
    #CONSTANTS
    _maxAccountsToAdd = 10
    _snoozeInterval = 2 #hours

    # additional environments qar, stage and uat map to Non-Prod_All swimlane
    envToSwimlaneMapping = {"prod": "PROD_All",
                            "test": "Non-Prod_All",
                            "non-prod": "Non-Prod_All",
                            "nonprod": "Non-Prod_All",
                            "dev": "Non-Prod_All",
                            "qar": "Non-Prod_All",
                            "sit": "Non-Prod_All",
                            "stage": "Non-Prod_All",
                            "uat": "Non-Prod_All",
                            "lab": "LAB_All"}

    # Get the ticket data from the context
    ticket = ctx.config.get('data').get('ticket')
    currentTime = round(time.time() * 1000)
    now = datetime.now()
    dateStamp = now.strftime("%Y-%m-%dT%H:%M:%S")

    # Create Sonrai GraphQL client
    graphql_client = ctx.graphql_client()

    role_name = None
    bot_role_name = None
    default_collector_srn = None

    # Loop through each of the custom fields and set the values that we need
    for customField in ticket.get('customFields'):
        if 'value' not in customField.keys():
            continue

        name = customField['name']
        value = customField['value']

        if name == 'Role Name':
            role_name = value
        elif name == 'Bot Role Name':
            bot_role_name = value
        elif name == 'Collector':
            default_collector_srn = value

    #GraphQL query for the AWS accounts
    queryAllAccounts = ('''
    query Accounts { Accounts(
    where: {
      cloudType: { op: EQ, value: "aws" }
      and: [
        { tagSet: {
            op: NOT_CONTAINS
            value: "sonraiBotAdded"
            caseSensitive: false
        } }
        { tagSet: {
            op: CONTAINS
            value: "sonrai-monitoring:true"
            caseSensitive: false
        } }
      ]
    }
  ) {
    count
    items {
      account
      srn
      tagSet
    }
  }
}
    ''')

    variables = { }
    logging.info('Searching for all AWS accounts')
    r_accounts = graphql_client.query(queryAllAccounts, variables)

    # GraphQL to get monitored AWS accounts on collector already
    queryPlatformAccounts = ('''query CloudAccounts {
  PlatformCloudAccounts
  (where:
    {
      cloudType: {value:"aws"}
    }
  )
  {
    count
    items {
      cloudType
      blob
    }
  }
}''')
    variables = { }
    logging.info('Searching for already monitored accounts on collector: {}'.format(default_collector_srn))
    r_platform_accounts = graphql_client.query(queryPlatformAccounts, variables)

    # mutation to add account
    mutation_add_account = '''
    mutation createSubAccount($account: PlatformcloudaccountCreator!) {
    CreatePlatformcloudaccount(value: $account) {srn blob cloudType  name }}'''

    # mutation for adding a processed tag to the account
    mutation_add_tag  = '''
       mutation addTagsWithNoDuplicates($key: String, $value: String, $srn: ID) {
       AddTag(value: {key: $key, value: $value, tagsEntity: {add: [$srn]}}) {srn key value }}
    '''

    # query for collector's SRN
    query_collector_srn = ('''
        query collectorSRN($name: String){
          PlatformAccounts
            (where: { 
              cloudType: { value: "aws" } 
              name: {op:EQ value:$name}
            }) {
              count
              items {
                srn 
              }
            }
          }
    ''')

    accountCount = 0
    swimlaneAccountList = dict()

    for item in r_accounts['Accounts']['items']:
        if accountCount >= _maxAccountsToAdd:
            # only adding _maxAccountsToAdd with each pass to prevent too many discoveries at once
            logging.warning("maximum number of accounts added for this pass")
            break

        #step through all AWS accounts to see if it is already added to a collector
        add_account = True
        accountToAdd = item['account']
        account_srn = item['srn']

        #check if the accountToAdd is already added
        for existing_accounts in r_platform_accounts['PlatformCloudAccounts']['items']:
            account_number = existing_accounts['blob']['accountNumber']
            if accountToAdd == account_number:
                add_account = False

        #set default collector
        collector_srn=default_collector_srn

        if add_account:
            # new account prepare to add it

            accountCount += 1 # this is for maximum number of accounts to be added

            for tag in item['tagSet']:

                # using the environment tag to determine swimlane
                if "environment" in tag:
                    environment = tag.replace("environment:","")

                    # check to see if this is a valid environment in our mapping
                    if environment in envToSwimlaneMapping:
                        #valid
                        swimlane = envToSwimlaneMapping[environment]
                    else:
                        #invalid
                        swimlane = None
                        logging.warn('No valid environment ({}) to swimlane mapping for account {}; will not add to swimlane'.format(environment, accountToAdd))

                    if swimlane in swimlaneAccountList:
                        #add account to existing list
                        swimlaneAccountList[swimlane].append(accountToAdd)
                    else:
                        # first time seeing this swimlane create a new list for it
                        swimlaneAccountList[swimlane] = [accountToAdd]
                elif "workload" in tag:
                    swimlane = tag.replace("workload:","")
                    if swimlane in swimlaneAccountList:
                        swimlaneAccountList[swimlane].append(accountToAdd)
                    else:
                        swimlaneAccountList[swimlane] = [accountToAdd]
                elif "sonraiCollector" in tag:
                    # Account has a collector name tag, see if the name has a valid SRN
                    collectorName = tag.replace("sonraiCollector:","")
                    varCollector = ('{"name": "' + collectorName + '" }')
                    r_collector_srn = graphql_client.query(query_collector_srn, varCollector)
                    if r_collector_srn['PlatformAccounts']['count'] == 0:
                        # account doesn't have a valid collector name tag, use the default collector SRN from the custom ticket
                        collector_srn = default_collector_srn
                    else:
                        # account's tag has a valid collector name, use this SRN
                        collector_srn = r_collector_srn['PlatformAccounts']['items'][0]['srn']

            # AWS Account doesn't exist on the collector. Adding it here

            #building roles
            role_arn = ("arn:aws:iam::"+accountToAdd+":role/"+role_name)
            bot_role_arn = ("arn:aws:iam::"+accountToAdd+":role/"+bot_role_name)

            #build variable for graphql mutation
            variables1 =  ('{"account": {"containedByAccount":' +
                                         '{"add": "' + collector_srn + '"},' +
                                     '"cloudType": "aws",' +
                                     '"blob": {'  +
                                         '"accountNumber": "' + accountToAdd +'",'+
                                         '"roleArn": "' + role_arn + '",' +
                                         '"botRoleArn": "' + bot_role_arn + '",' +
                                         '"runDateTime": ' + str(currentTime) +
                                         '}'+
                                     '}'+
                         '}')
            #add account to collector
            logging.info('Adding Account {} to collector {}'.format(accountToAdd,collector_srn))
            r_add_account = graphql_client.query(mutation_add_account, variables1)

            #add sonrai tag to account to ignore it in the future
            variables2 = ('{"key":"sonraiBotAdded","value":"'+ dateStamp + '","srn":"'+account_srn+'"}')
            r_add_tag = graphql_client.query(mutation_add_tag, variables2)


    # section for adding accounts to swimlanes
    query_find_swimlane_SRN = ('''
        query SwimlaneSRN($title: String) {
          Swimlanes(where: { title: { op: EQ, value: $title } }) {
            count
            items {
              srn
            }
          }
        }
    ''')
    mutation_add_to_swimlane = ('''
       mutation updateSwimlane($swimlane: SwimlaneUpdater!, $srn: ID!) {
        UpdateSwimlane(srn: $srn, value: $swimlane) {
          srn
        }
      }
    ''' )
    mutation_create_and_add_to_swimlane = ('''
    mutation createSwimlane($swimlane: SwimlaneCreator!) {
      CreateSwimlane(value: $swimlane) {
            srn
        }
    }
    ''')

    for swimlane in swimlaneAccountList:
        # prepare to add accounts to swimlane
        if swimlane is None:
            # no swimlane for these accounts, so skip
            continue
        # find the swimlane's SRN from the swimlane's name
        variables1 = ('{"title": "' + swimlane + '" }')
        r_swimlane_srn = graphql_client.query(query_find_swimlane_SRN, variables1)

        # check if the swimlane exists
        if r_swimlane_srn['Swimlanes']['count'] == 0:
            # swimlane doesn't need to create one
            logging.warn(" Swimlane {} doesn't exist, creating it.".format(swimlane))
            # setting default importance to 1 so that the resources can get the importance level from the environment swimlanes
            # setting the environments to all of them since this could be a swimlane with resources across all environments
            tmp_variables2 = (
                '{"swimlane": ' +
                    '{"description":"' + swimlane + '",' +
                     '"defaultImportance":1,'
                     '"title":"' + swimlane + '",' +
                     '"accounts": ' + str(swimlaneAccountList[swimlane]) + ',' +
                     '"environments": [ "Sandbox", "Development", "Staging", "Production" ]' +
                 '}}'
            )
            print (mutation_create_and_add_to_swimlane)
            variables2 = tmp_variables2.replace("'", "\"")
            print (variables2)
            # create swimlane with list of accounts
            r_create_swimlane = graphql_client.query(mutation_create_and_add_to_swimlane, variables2)
        else:

            swimlaneSRN = r_swimlane_srn['Swimlanes']['items'][0]['srn']

            # build the variable for the add to swimlane mutation
            tmp_variables3 = ('{"srn": "' + swimlaneSRN + '",'+
                      '"swimlane": {' +
                            '"accounts": { "add": ' + str(swimlaneAccountList[swimlane]) + '}' +
                      '}' +
                      '}'
                      )
            variables3 = tmp_variables3.replace("'", "\"")

            # add the accounts to swimlane
            r_add_to_swimlane = graphql_client.query(mutation_add_to_swimlane, variables3)


    # un-snooze and re-snooze the ticket for a shorter time period
    mutation_reopen_ticket = ('''
      mutation openTicket($srn:String){
        ReopenTickets(input: {srns: [$srn]}) {
          successCount
          failureCount
        }
      }
    ''')
    mutation_snooze_ticket = ('''
        mutation snoozeTicket($srn: String, $snoozedUntil: DateTime) {
            SnoozeTickets(snoozedUntil: $snoozedUntil, input: {srns: [$srn]}) {
              successCount
              failureCount
              __typename
            }
          }
    ''')
    # calculate the snoozeUntil time
    snoozeUntil = datetime.now() + timedelta(hours=_snoozeInterval)
    variables = ('{"srn": "' + ticket['srn'] + '", "snoozedUntil": "' + str(snoozeUntil).replace(" ","T") + '" }')
    # re-open ticket so it can be snoozed again
    r_reopen_ticket = graphql_client.query(mutation_reopen_ticket, variables)
    # snooze ticket
    r_snooze_ticket = graphql_client.query(mutation_snooze_ticket, variables)

