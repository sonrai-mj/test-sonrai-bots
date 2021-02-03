import logging
import sonrai.platform.aws.arn
from datetime import datetime
import socket
import json
import os
import jwt
from urllib.parse import urlencode

log = logging.getLogger()

class syslogHandler:
    #_TICKET_VIEW_PATH = 'App/TicketDetails?'


    def __init__(self):
        self.syslog_host = os.environ.get('SYSLOGHOST', '159.2.178.229')
        self.syslogheader_hostname = os.getenv('SYSLOGHEADERHOSTNAME', 'sonraialerts-lambdafunction')
        self.syslog_port = int(os.getenv('SYSLOGPORT', 514))
        self.sonraiMessageFormat = os.getenv("MESSAGEFORMAT", "json")
        self._ENV_KEY = 'https://sonraisecurity.com/env'
        self._TICKET_URL_FMT = 'https://{}.sonraisecurity.com/App/TicketDetails?{}'


    def syslogDestinationSendMessage(self, msg):
        syslogheader = datetime.now().strftime( "%b %d %H:%M:%S") + " " + self.syslogheader_hostname
        sonraiSyslogMessage = syslogheader + " " + msg

        # Send UDP - will eventually hit limits with this when using JSON
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as send_syslog:
            send_syslog.sendto(sonraiSyslogMessage.encode('utf-8'), (self.syslog_host, self.syslog_port))

    def build_ticket_link(self, client, srn):
        token = client._token.get()
        decoded=jwt.decode(token, verify=False)
        env = decoded[self._ENV_KEY]
        if not env:
            raise ValueError("No env present in token")
        if env == 'dev':
            sub = 'dev.de'
        elif env == 'stage':
            sub = 'stage.s'
        elif env == 'crc':
            sub = 'crc'
        else:
            raise ValueError("Unsupported env: {}".format(env))
        return self._TICKET_URL_FMT.format(sub, urlencode({"srn":srn}) )

    def get_ticket_details(self, graphql_client, ticket_srn):
        #grab the extra fields in the ticket that aren't sent to the bot
        q_ticket = ('''query TicketDetails ($srn: String) { 
                Tickets ( where: 
                      { 
                      srn: { op: EQ value: $srn }
                      }
                    ) {
                      items {
                        srn
                        firstSeen
                        lastSeen
                        severityNumeric
                        resourceSRN
                        policy {
                          ControlPolicyTitle: title
                        }
                        resource {
                          ResourceName: name
                          ResourceLabel: label
                          ResourceType: serviceType
                          ResourceCloudAccount: account
                        }
                      }
                    }
                  }
                  ''')
        variables = ('{"srn":"'+ticket_srn+'"}')
        response =  graphql_client.query(q_ticket, variables)
        return response


    def process_alert(self, context):
        #get ticket data
        ticket = context.config['data']['ticket']
        # get the ticket's SRN
        ticket_srn = ticket['srn']
        #generate the link to the ticket
        qraphql_client = context.graphql_client()
        node_link = self.build_ticket_link(qraphql_client, ticket_srn)
        ticket_items = self.get_ticket_details(qraphql_client,ticket_srn)

        ticket = ticket_items['Tickets']['items'][0]

        if ticket['severityNumeric'] is None:
            severity = "n/a"
        else:
            severity = str(ticket['severityNumeric'])

        syslogPayload = ""

        if self.sonraiMessageFormat == "text":
            syslogPayload = (" [sonrai-ticketAlert]  " +
                             "policyName=" + str( ticket['policy']['ControlPolicyTitle']) +
                             "|firstSeen" + str(ticket['firstSeen']) +
                             "|lastSeen" + str(ticket['lastSeen']) +
                             "|severity=" + str(severity) +
                             "|account=" + str(ticket['resource']['account']) +
                             "|resourceName=" + str(ticket['resource']['ResourceName']) +
                             "|resourceLabel=" + str(ticket['resource']['ResourceLabel']) +
                             "|resourceType=" + str(ticket['resource']['ResourceType']) +
                             "|resourceSRN=" + str(ticket['resourceSRN']) +
                             "|details_url=" + str(node_link) +
                             "\n")
        elif self.sonraiMessageFormat == "json":
            # json to string
            alertobject = self.alertJSON(ticket, node_link, severity)
            syslogPayload = json.dumps(alertobject)

        self.syslogDestinationSendMessage(syslogPayload)

    # Generate alert json object
    def alertJSON(self, ticket, node_link, severity):
        sonraiEvent = {
            'policyName': ticket['policy']['ControlPolicyTitle'],
            'source': 'Sonrai Security Control Policy',
            'firstSeen': ticket['firstSeen'],
            'lastSeen': ticket['lastSeen'],
            'severity': severity,
            'account': ticket['resource']['ResourceCloudAccount'],
            'resourceName': ticket['resource']['ResourceName'],
            'resourceLabel': ticket['resource']['ResourceLabel'],
            'resourceType': ticket['resource']['ResourceType'],
            'resourceSRN': ticket['resourceSRN'],
            'custom_details': {
                'details_url': node_link,
            }
        }

        data = {
            "client": "Sonrai Security Platform Alert",
            'payload': sonraiEvent,
        }
        return data

def run(ctx):
    handler = syslogHandler()
    handler.process_alert(ctx)
