"""
/u/FactorioModPortalBot

A Reddit Bot made by /u/michael________ based on a bot by /u/cris9696

General workflow:

* Login
* Get comments
* Analyze comments
* Reply to valid comments
* Shutdown


"""

#reddit
import praw
#general
import sys
import time
import os
import re
import pickle
import signal
#web
import urllib
import html
import requests
#mine
import Config

#Searches the mod portal with keyword "keyword" and returns an array of "count" mods.
def search(keyword, count):
    logger.info("Searching for " + str(count) + " results for '" + keyword + "'")
    encoded_name = urllib.parse.quote_plus(keyword.encode('utf-8')) #we encode the name to a valid string for a url, replacing spaces with "+" and and & with &amp; for example 
    
    #Request mods from mod portal API
    logger.debug("Sending request for search")
    json = requests.get("https://mods.factorio.com/api/mods?q=" + encoded_name + "&page_size=30&page=1&order=top").json();
    
    response_list = []
    
    if(json["results"] == []):
        logger.warning("Could not find mod " + keyword + " on the mod portal!")
    else:
        #Two passes are done on the results. In the first pass only the exact matches are added. In the second, if needed, only non exact matches are added
        #First pass
        for result in json["results"]:
                #If the result's title contains an exact (case insensitive) match of the keyword
                if(keyword.lower() in result["title"].lower()):
                    #Add the result to the response list
                    response_list.append("[**" + result["title"] + "**](" +
                                        "https://mods.factorio.com/mods/" + result["owner"] + "/" + result["name"] + ") - By: " +
                                        result["owner"] + " - Game Version: " +
                                        result["latest_release"]["game_version"])
        #If enough results were found
        if(len(response_list) >= count):
            #Return response list truncated to count
            return response_list[:count]
        #Second pass
        for result in json["results"]:
                #If the result's title does not contains an exact (case insensitive) match of the keyword (this is needed so that results from the first pass are not duplicated in the second)
                if(not (keyword.lower() in result["title"].lower())):
                    #Add the result to the response list
                    response_list.append("[**" + result["title"] + "**](" +
                                        "https://mods.factorio.com/mods/" + result["owner"] + "/" + result["name"] + ") - By: " +
                                        result["owner"] + " - Game Version: " +
                                        result["latest_release"]["game_version"])
    return response_list[:count]

#Checks if an author of a mod exists    
def authorExists(author):
    encoded_name = urllib.parse.quote_plus(author.encode('utf-8')) #we encode the name to a valid string for a url, replacing spaces with "+" and and & with &amp; for example 
    json = requests.get("https://mods.factorio.com/api/mods?owner=" + encoded_name).json();
    return json["results"] != []
    

#Shut down function
def stopBot():
    logger.info("Shutting down")
    sys.exit(0)

#Removes all reddit formatting characters
def removeRedditFormatting(text):
    return text.replace("*", "").replace("~", "").replace("^", "").replace(">","").replace("[","").replace("]","").replace("(","").replace(")","")

#Checks if comment was already replied to by the bot
def isDone(comment):
    comment.refresh()
    for reply in comment.replies:
        #If username on one of the replies is equal to bot username
        if reply.author.name.lower() == os.environ['REDDIT_USER'].lower():
            logging.debug("Already replied to \"" + comment.id + "\"")
            return True
    return False

def generateReply(link_requests):
    #List of string responses
    responses = []
    #For each request
    for request in link_requests:
        #If it is an author request (1 capture group)
        if(type(request) is str):
            if(authorExists(request)):
                responses.append("[**" + request + "**](https://mods.factorio.com/mods/" + request + ")")
            else:    
                logger.info("Can't find author " + request)
        #If it is a mod request (2 capture groups)
        elif(type(request) is tuple):
            #Seperate amount of mod results requested and search keyword
            request_name = request[0] if len(request[0]) > 0 else 1
            request_keyword = html.unescape(request[1].strip())
            #Get request_name search results for request_keyword, and add them to responses
            responses += search(request_keyword, int(request_name))
    
    #The bot doesn't reply if it can't fulfil any of the requests.
    if(len(responses) == 0):
        return None
    
    #Build reply string
    reply = ""
    #If maximum link limit was exceeded, notify user
    if(len(responses) > Config.maxResponsesPerComment):
        reply += "You requested more than " + str(Config.maxResponsesPerComment) + " links. I will only link to the first " + str(Config.maxResponsesPerComment) + ".\n\n"
        del responses[Config.maxResponsesPerComment:]
    
    #Add responses to reply
    reply += "\n\n".join(responses)
    
    reply += Config.closingFormula
    return reply

#Replies to the specified comment with the specified reply.
def doReply(comment,myReply):
    logger.debug("Replying to '" + comment.id + "'")
    
    #Retry until reply succeeds
    tryAgain = True
    while tryAgain:
        tryAgain = False
        try:
            #Reply using PRAW
            comment.reply(myReply)
            logger.info("Successfully replied to comment '" + comment.id + "'\n")
            break
        except praw.errors.RateLimitExceeded as timeError:
            #Reddit API rate limit. Waits until rate limiting is lifted.
            logger.warning("Doing too much, sleeping for " + str(timeError.sleep_time))
            time.sleep(timeError.sleep_time)
            tryAgain = True
        except Exception as e:
            logger.error("Exception '" + str(e) + "' occured while replying to '" + comment.id + "'!")
            stopBot()


#Building the logger
import logging
logger = logging.getLogger('LinkMeBot')
logger.setLevel(Config.loggingLevel)
fh = logging.FileHandler(Config.logFile)
fh.setLevel(Config.loggingLevel)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
ch.setFormatter(formatter)
logger.addHandler(fh)
logger.addHandler(ch)

#Handle SIGTERM from Heroku
signal.signal(signal.SIGTERM, stopBot)

#Startup Code
logger.info("Starting up")
logger.debug("Logging in")
#Attempts to log in.
try:
    r = praw.Reddit(user_agent = "/u/FactorioModPortalBot by /u/michael________ V1.0")
    r.login(os.environ['REDDIT_USER'], os.environ['REDDIT_PASS'], disable_warning=True)
    logger.info("Successfully logged in")
except praw.errors.RateLimitExceeded as error:
    #Reddit API rate limit. Shuts down.
    logger.error("The Bot is doing too much! Sleeping for " + str(error.sleep_time) + " and then shutting down!")
    time.sleep(error.sleep_time)
    stopBot()
except Exception as e:
    logger.error("Exception '" + str(e) + "' occured on login!")
    stopBot()

#Request subreddits from PRAW
subreddits = r.get_subreddit("+".join(Config.subreddits))
#The magic matching regexs. Explanation here: https://regex101.com/r/uT1gQ0/
#1st regex. Matches mod requests. Has 2 capture groups. 1st for number of mods requested (for a single keyword), and 2nd for the keyword.
link_mod_regex = re.compile("\\blink\s*(\d*)\s*mods?\s*:\s*(.*?)$", re.M | re.I)
#2nd regex. Matches author requests. Has 1 capture group for author name.
link_author_regex = re.compile("\\blink\s*author\s*:\s*(.*?)$", re.M | re.I)


#Main Loop
while True:
    try:
        #Get all comments for selected subreddits.
        logger.debug("Getting the comments")
        comments = subreddits.get_comments()
        logger.info("Comments successfully downloaded")
    except Exception as e:
        logger.error("Exception '" + str(e) + "' occured while getting comments!")
        stopBot()

    for comment in comments:
        #Clean comment from reddit formatting
        clean_comment = removeRedditFormatting(comment.body)
        #Find requests in the comment using magic regexs.
        link_requests = link_mod_regex.findall(clean_comment)
        link_requests += link_author_regex.findall(clean_comment)
        #If match found
        if len(link_requests) > 0:
            #If we have not already answered to the comment
            if not isDone(comment): 
                #Generate reply
                logger.debug("Generating reply to '" + comment.id + "'")
                reply = generateReply(link_requests)
                if reply is not None:
                    doReply(comment,reply)
                else: #If generateReply() returns None, no mods have been found.
                    logger.info("No Mods found for comment '" + comment.id + "'. Ignoring reply.")
    
    logger.info("Done. Rechecking in 60 seconds.")
    time.sleep(60);