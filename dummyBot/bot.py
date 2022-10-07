import logging
from sonrai import gql_loader
import sys
import re
import time
from datetime import datetime, timedelta

def run(ctx):
    #CONSTANTS
    _maxAccountsToAdd = 10
    # create gql_loader queries
    # gql = gql_loader.queries()


    # Get the ticket data from the context
    logging.info (ctx)