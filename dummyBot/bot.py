import logging
import json

def run(ctx):
    #CONSTANTS

    # Get the ticket data from the context
    #logging.info (ctx)
    w = ctx.config.get('data')
    print (json.dumps(w, indent=4))
    logging.info("testing log")
    logging.info (json.dumps(w))