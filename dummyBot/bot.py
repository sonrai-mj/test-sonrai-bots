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
    comment = "Adding the following accounts to the collector\n- 333333333333\n- 222222222222\n- 1111111111111"
    ac = add_comment.add_ticket_comment(ctx, comment)
