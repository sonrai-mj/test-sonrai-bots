import logging
import json

import add_comment

def run(ctx):
    #CONSTANTS

    # Get the ticket data from the context
    #logging.info (ctx)
    w = ctx.config.get('data')
    print (json.dumps(w, indent=4))
    logging.info("testing log")
    logging.info (json.dumps(w))
    comment = "Adding the following accounts to the collector \n123123234\n23234234\n234234234"
    ac = add_comment.add_ticket_comment(ctx, comment)
