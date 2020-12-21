import logging
import sys
import re
import time

def run(ctx):
    # Get the ticket data from the context
    ticket = ctx.config.get('data').get('ticket')
    currentTime = round(time.time() * 1000)

    # Create GraphQL client
    graphql_client = ctx.graphql_client()

    tenant_id = None
    collector_srn = None

    # Loop through each of the custom fields and set the values that we need
    for customField in ticket.get('customFields'):
        if 'value' not in customField.keys():
            continue

        name = customField['name']
        value = customField['value']

        if name == 'Tenant':
            tenant_id = value
        elif name == 'Collector':
            collector_srn = value

    #GraphQL query for the subscriptions
    queryAllSubscriptions = ('''
    query Subscriptions ($tenant: String) {
  Subscriptions (where: {account: {value:$tenant}}){
    count
    items {
      type
      cloudType
      account
      resourceId
    }
  }
}
    ''')

    variables = ( '{"tenant": "' + tenant_id +'"}')
    logging.info('Searching for all subscriptions for tenant id : {}'.format(tenant_id))
    r_subscriptions = graphql_client.query(queryAllSubscriptions, variables)

    # GraphQL to get monitored subscriptions on collector already
    queryPlatformSubscriptions = ('''query CloudAccounts ($srn: String){
  PlatformCloudAccounts 
  (where:
    {
      containedByAccount: {items: {srn: {value:$srn}}}
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
    variables = ( '{"srn": "'+collector_srn+'"}')
    logging.info('Searching for already monitored accounts on collector: {}'.format(collector_srn))
    r_platform_subscriptions = graphql_client.query(queryPlatformSubscriptions, variables)

    # invite user mutation
    mutation_add_subscription = ''' mutation createSubAccount($account: PlatformcloudaccountCreator!) {
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


    for resourceId in r_subscriptions['Subscriptions']['items']:
        #step through all subscriptions to see if it is already added to a collector
        add_subscription = True
        subscriptionToAdd = re.sub("\/subscriptions\/","", resourceId['resourceId'])

        #check if the subscriptionToAdd is already added
        for existing_subscriptions in r_platform_subscriptions['PlatformCloudAccounts']['items']:
            subscriptionId = existing_subscriptions['blob']['subscriptionId']
            if subscriptionToAdd == subscriptionId:
                add_subscription = False

        if add_subscription:
            # Subscription doesn't exist on the collector. Adding it here
            variables =  ('{"account": {"containedByAccount":' +
                                         '{"add": "' + collector_srn + '"},' +
                                     '"cloudType": "azure",' +
                                     '"blob": {'  +
                                         '"subscriptionId": "' + subscriptionToAdd +'",'+
                                         '"tenantId": "' + tenant_id + '",' +
                                         '"runDateTime": ' + str(currentTime) +
                                         '}'+
                                     '}'+
                         '}')
            logging.info('Adding Subscription {}'.format(subscriptionToAdd))
            r_add_subscription = graphql_client.query(mutation_add_subscription, variables)