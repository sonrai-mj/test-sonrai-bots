import logging
import sonrai.platform.aws.arn
from datetime import datetime
import socket
import json
import os
import jwt

log = logging.getLogger()

class syslogHandler:
    #_TICKET_VIEW_PATH = 'App/TicketDetails?'


    def __init__(self):
        self.syslog_host = os.environ.get('SYSLOGHOST', '159.2.178.229')
        self.syslogheader_hostname = os.getenv('SYSLOGHEADERHOSTNAME', 'sonraialerts-lambdafunction')
        self.syslog_port = int(os.getenv('SYSLOGPORT', 514))
        self.sonraiMessageFormat = os.getenv("MESSAGEFORMAT", "json")
        self.policyEvidenceMaxLength = int( os.getenv('POLICYEVIDENCEMAXLENGTH', 1000))
        self._ENV_KEY = 'https://sonraisecurity.com/env'
        self._TICKET_URL_FMT = 'https://{}.sonraisecurity.com/App/TicketDetails?srn={}'


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
        return self._TICKET_URL_FMT.format(sub, srn)

    def get_policy_title(self, client):
        #grab the title of the policy from the ticket
        pass


    def process_alert(self, context):
        #get ticket data
        alert = context.config['data']['ticket']
        # get the ticket's SRN
        TicketSRN = alert['srn']
        #generate the link to the ticket
        client = context.graphql_client()
        node_link = self.build_ticket_link(client, TicketSRN)
        #policy_title = self.get_policy_title(client)

        if alert['severityNumeric'] is None:
            severity = "n/a"
        else:
            severity = str(alert['severityNumeric'])

        syslogPayload = ""

        if self.sonraiMessageFormat == "text":
            syslogPayload = (" [sonrai-ticketAlert]  " +
                             "policyName=" + str( alert['policy']['ControlPolicyTitle']) +
                             "|policyid=" + str( alert['policy']['ControlPolicyId']) +
                             "|firstSeen" + str(alert['firstSeen']) +
                             "|lastSeen" + str(alert['lastSeen']) +
                             "|severity=" + str(severity) +
                             "|account=" + str(alert['account']) +
                             "|resourceLabel=" + str(alert['resourceLabel']) +
                             "|resourceType=" + str(alert['resourceType']) +
                             "|resourceSRN=" + str(alert['resourceSRN']) +
                             "|details_url=" + str(node_link) +
                             "\n")
        elif self.sonraiMessageFormat == "json":
            # json to string
            alertobject = self.alertJSON(alert, node_link, severity)
            syslogPayload = json.dumps(alertobject)

        self.syslogDestinationSendMessage(syslogPayload)

    # Generate alert json object
    def alertJSON(self, alert, node_link, severity):
        if len(json.dumps(
            alert['evidence']['policyEvidence'])) > self.policyEvidenceMaxLength:
            evidence = {
                "policyEvidence": "message too long, refer to Sonrai for full ticket details."}
        else:
            evidence = alert['evidence']['policyEvidence']

        sonraiEvent = {
            #'policyName': alert['policy']['ControlPolicyTitle'],
            'policyName': alert['policy']['title'],
            'source': 'Sonrai Security Control Policy',
            'firstSeen': alert['firstSeen'],
            'lastSeen': alert['lastSeen'],
            'severity': severity,
            'account': alert['account'],
            'resourceLabel': alert['resourceLabel'],
            'resourceType': alert['resourceType'],
            'resourceSRN': alert['resourceSRN'],
            'custom_details': {
                'details_url': node_link,
                'policyEvidence': evidence
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
