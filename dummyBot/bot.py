import logging
from sonrai import gql_loader
import sys
import re
import time
from datetime import datetime, timedelta

def run(ctx):
    #CONSTANTS

    # Get the ticket data from the context
    logging.info (ctx)