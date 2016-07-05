import requests
import urllib

class Mod():
    name = None
    author = None
    link = None
    game_versions = None
    
    def __init__(self):
        pass

#debug and logging
import logging
logger = logging.getLogger('PlayStore')
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
console_logger = logging.StreamHandler()
console_logger.setFormatter(formatter)
console_logger.setLevel(logging.DEBUG)
logger.addHandler(console_logger)

def search(mod_name):
    logger.info("Searching for '" + mod_name + "'")
    encoded_name = urllib.parse.quote_plus(mod_name.encode('utf-8')) #we encode the name to a valid string for a url, replacing spaces with "+" and and & with &amp; for example 

    logger.debug("Sending request for seach")
    page = requests.get("https://mods.factorio.com/api/mods?q=" + encoded_name + "&page_size=1&page=1");

    mod = parseMod(page.json());
    
    if mod is None:
        #If mod wasn't found
        logger.warning("Could not find mod " + mod_name + " on the mod portal!")
    
    logger.info("App was found")
    return mod

def parseMod(json):
    if(json["results"] == []):
        return None; #No results found, return.
    
    result = json["results"][0];
	
    mod = Mod();
    mod.name = result["title"];
    mod.author = result["owner"]
    mod.link = "https://mods.factorio.com/mods/" + result["owner"] + "/" + result["name"]
    mod.game_versions = result["game_versions"]
    
    return mod