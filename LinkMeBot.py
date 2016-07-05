"""
/u/FactorioModPortalBot

A Reddit Bot made by /u/michael________ based on a bot by /u/cris9696

General workflow:

* login
* get comments
* analyze comments
* reply to valid comments
* shutdown


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
#mine
import Config
import ModPortal


def stopBot():
    logger.info("Shutting down")

    if os.path.isfile(Config.botRunningFile):
        logger.debug("Deleting lock file")
        os.remove(Config.botRunningFile)

    sys.exit(0)

def removeRedditFormatting(text):
    return text.replace("*", "").replace("~", "").replace("^", "").replace(">","").replace("[","").replace("]","").replace("(","").replace(")","")


def isDone(comment):
    #TODO check if in the database
    comment.refresh()
    for reply in comment.replies:
        if reply.author.name.lower() == Config.username.lower():
            logging.debug("Already replied to \"" + comment.id + "\"")
            return True

    return False

def generateReply(link_me_requests):
    my_reply = ""

    nOfRequestedMods = 0
    nOfFoundMods = 0
    for link_me_request in link_me_requests:    #for each linkme command
        requested_mods = link_me_request.split(",") #split the mods by ,

        for mod_name in requested_mods:
            mod_name = mod_name.strip()

            if len(mod_name) > 0:
                mod_name = html.unescape(mod_name)  #html encoding to normal encoding 
                nOfRequestedMods += 1
                
                if nOfRequestedMods <= Config.maxModsPerComment:
                    mod = ModPortal.search(mod_name)

                    if mod:
                        nOfFoundMods += 1
                        my_reply += "[**" + mod.name + "**](" + mod.link + ") - By: " + mod.author + " - Game Version: " + mod.game_versions[0] + "\n\n"
                        
                        logger.info("'" + mod_name + "' found. Name: " + mod.name)
                    else:
                        my_reply +="I am sorry, I can't find any mod named '" + mod_name + "'.\n\n"
                        logger.info("Can't find any mod named '" + mod_name + "'")

    if nOfRequestedMods > Config.maxModsPerComment:
        my_reply = "You requested more than " + str(Config.maxModsPerComment) + " mods. I will only link to the first " + str(Config.maxModsPerComment) + " mods.\n\n" + my_reply
    
    my_reply += Config.closingFormula

    if nOfFoundMods == 0:   #return None because we don't want to answer
        my_reply = None

    return my_reply

def doReply(comment,myReply):
    logger.debug("Replying to '" + comment.id + "'")
    
    tryAgain = True
    while tryAgain:
        tryAgain = False
        try:
            comment.reply(myReply)
            logger.info("Successfully replied to comment '" + comment.id + "'\n")
            break
        except praw.errors.RateLimitExceeded as timeError:
            logger.warning("Doing too much, sleeping for " + str(timeError.sleep_time))
            time.sleep(timeError.sleep_time)
            tryAgain = True
        except Exception as e:
            logger.error("Exception '" + str(e) + "' occured while replying to '" + comment.id + "'!")
            stopBot()


#building the logger
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

#main method
if __name__ == "__main__":

    logger.info("Starting up")

    if os.path.isfile("/tmp/botRunning"):
        logger.warning("Bot is already running!")
        stopBot(False)
    else:
        with open(Config.botRunningFile, 'a'):
            pass

    logger.debug("Logging in")


    try:
        r = praw.Reddit(user_agent = "/u/FactorioModPortalBot by /u/michael________ V1.0")
        r.login(Config.username, Config.password, disable_warning=True)
        logger.info("Successfully logged in")

    except praw.errors.RateLimitExceeded as error:
        logger.error("The Bot is doing too much! Sleeping for " + str(error.sleep_time) + " and then shutting down!")
        time.sleep(error.sleep_time)
        stopBot()

    except Exception as e:
        logger.error("Exception '" + str(e) + "' occured on login!")
        stopBot()


    subreddits = r.get_subreddit("+".join(Config.subreddits))

    link_me_regex = re.compile("\\blink\s*mod\s*:\s*(.*?)(?:\.|;|$)", re.M | re.I)

    try:
        logger.debug("Getting the comments")
        comments = subreddits.get_comments()
        logger.info("Comments successfully downloaded")
    except Exception as e:
        logger.error("Exception '" + str(e) + "' occured while getting comments!")
        stopBot()

    for comment in comments:

        #to avoid injection of stuff
        clean_comment = removeRedditFormatting(comment.body)
        #match the request
        link_me_requests = link_me_regex.findall(clean_comment)
        #if it matches
        if len(link_me_requests) > 0:
            if not isDone(comment): #we check if we have not already answered to the comment
                logger.debug("Generating reply to '" + comment.id + "'")
                reply = generateReply(link_me_requests)
                if reply is not None:
                    doReply(comment,reply)
                else:
                    logger.info("No Mods found for comment '" + comment.id + "'. Ignoring reply.")
    stopBot()
