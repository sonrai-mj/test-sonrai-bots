import logging

def run(ctx):
    #CONSTANTS

    # Get the ticket data from the context
    #logging.info (ctx)
    for x in ctx.config.get('data'):
        logging.info(x)
        for y in ctx.config.get('data').get(x):
            logging.info(y)