def add_ticket_comment(ctx, body):
   #graphql_client = ctx.graphql_client()
   mutation_add_comment = ('''mutation addTicketComment($ticketSrn: String!, $body: String!, $createdBy: String!) {
  CreateTicketComment(
    input: {body: $body, ticketSrn: $ticketSrn, createdBy: $createdBy}
  ) {
    resourceId
    srn
    createdBy
    createdDate
    body
  }
}''' )
   ticket_srn = ctx.config.get('data').get('ticket').get('srn')
   org_name = ctx.config.get('data').get('ticket').get('orgName')
   user_srn = 'srn:' + org_name + '::SonraiUser/bot_user'
   variables = ('{"ticketSrn": "' + ticket_srn + '", "body": "' + body + '", "createdBy": "' + user_srn + '" }')
   print(mutation_add_comment)
   print(variables)
   graphql_client.query(mutation_add_comment, variables)

   
