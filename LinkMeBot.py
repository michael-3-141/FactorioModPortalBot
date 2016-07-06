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
#web
import urllib
import html
import requests
#mine
import Config

#Mod class
class Mod():
    name = None
    author = None
    link = None
    game_versions = None
    
    def __init__(self):
        pass

#Searches the mod portal with keyword "keyword" and returns an array of "count" mods.
def search(keyword, count):

    logger.info("Searching for '" + keyword + "'")
    encoded_name = urllib.parse.quote_plus(keyword.encode('utf-8')) #we encode the name to a valid string for a url, replacing spaces with "+" and and & with &amp; for example 
    
    #Request mods from mod portal API
    logger.debug("Sending request for search")
    json = requests.get("https://mods.factorio.com/api/mods?q=" + encoded_name + "&page_size=" + str(count) + "&page=1").json();
    
    modlist = []
    
    if(json["results"] == []):
        logger.warning("Could not find mod " + keyword + " on the mod portal!")
    else:
        for result in json["results"]:
            mod = Mod();
            mod.name = result["title"];
            mod.author = result["owner"]
            mod.link = "https://mods.factorio.com/mods/" + result["owner"] + "/" + result["name"]
            mod.game_versions = result["game_versions"]
            modlist.append(mod)
    
    return modlist

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

#Generates a reply string based on requests made, returns none if no requests could be found
def generateReply(link_me_requests):
    my_reply = ""
    
    
    nOfFoundMods = 0
    
    for request in link_me_requests:
        #Seperate amount of mod results requested and search keyword
        request_name = request[0]
        request_keyword = request[1].strip()
        
        if len(request_keyword) > 0:
            #HTML encoding to normal encoding
            request_keyword = html.unescape(request_keyword)
            #Get request_name search results for request_keyword
            modlist = search(request_keyword, request_name)
            #If results were found
            if len(modlist) > 0:
                #For each result found
                for mod in modlist:
                    #Update found mod counter
                    nOfFoundMods += 1
                    #Make sure mod request limit hasn't been reached
                    if nOfFoundMods <= Config.maxModsPerComment:
                        #Add mod to reply
                        my_reply += "[**" + mod.name + "**](" + mod.link + ") - By: " + mod.author + " - Game Version: " + mod.game_versions[0] + "\n\n"
                        logger.info("'" + request_keyword + "' found. Name: " + mod.name)
            else:
                #If mod wasn't found, add a message to the reply
                my_reply +="I am sorry, I can't find any mods named '" + request_keyword + "'.\n\n"
                logger.info("Can't find any mods named '" + request_keyword + "'")
    
    #If mod limit was exceeded, add a message to the reply
    if nOfFoundMods > Config.maxModsPerComment:
        my_reply = "You requested more than " + str(Config.maxModsPerComment) + " mods. I will only link to the first " + str(Config.maxModsPerComment) + " mods.\n\n" + my_reply
    
    #Add the closing text
    my_reply += Config.closingFormula

    #The bot doesn't reply if it found none of the mods requested.
    if nOfFoundMods == 0:
        my_reply = None

    return my_reply

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
#The magic matching regex. Explanation here: https://regex101.com/r/uT1gQ0/
#Has 2 capture groups. 1st for number of mods requested (for a single keyword), and 2nd for the keyword.
link_me_regex = re.compile("\\blink\s*(\d*)\s*mods?\s*:\s*(.*?)$", re.M | re.I)

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
        #Find requests in the comment using magic regex.
        link_me_requests = link_me_regex.findall(clean_comment)
        #If match found
        if len(link_me_requests) > 0:
            #If we have not already answered to the comment
            if not isDone(comment): 
                #Generate reply
                logger.debug("Generating reply to '" + comment.id + "'")
                reply = generateReply(link_me_requests)
                if reply is not None:
                    doReply(comment,reply)
                else: #If generateReply() returns None, no mods have been found.
                    logger.info("No Mods found for comment '" + comment.id + "'. Ignoring reply.")
    
    logger.info("Done. Rechecking in 60 seconds.")
    time.sleep(60);
