def add_ticket_comment(ctx, body):
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
   ticket_srn = ctx.config.get('data').get('srn')
   org_name = ctx.config.get('data').get('orgName')
   user_srn = 'srn:' + org_name + '::SonraiUser/bot_user'
   variables = ('{"ticketSrn": "' + ticket_srn + '", "body": "' + body + '", "createdBy": "' + user_srn + '" }')
   graphql_client.query(mutation_add_comment, variables)

   
