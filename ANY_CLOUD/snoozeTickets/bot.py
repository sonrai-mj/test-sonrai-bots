import sonrai.platform.aws.arn

def run(ctx):
	ticket = ctx.config.get('data').get('ticket')

	ticket_srn = ticket.get("srn")

	query = '''
            mutation snoozeTicket($srn: String, $snoozedUntil: DateTime) {
              SnoozeTickets(input: {srns: [$srn]}, snoozedUntil: $snoozedUntil) {
                successCount
                failureCount
                __typename
              }
            }
	'''
	ticket_snoozeUntil = "2020-12-25"
	variables = { "srn": ticket_srn, "snoozedUntil": ticket_snoozeUntil }
	response = ctx.graphql_client().query(query, variables)
