import bot_spamer
import cache_handler
import bot_reply
import database
from database import BotSetup
from threading import Thread
from config import IsBotInDebug

if __name__ == "__main__":
    if (IsBotInDebug()):
        print("DEBUG VERSION")
    else:
        print("RELEASE VERSION")
    th_spam = Thread(target = bot_spamer.cycleThread)
    th_cache = Thread(target = cache_handler.cycleThread)
    th_logic = Thread(target = bot_reply.cycleThread)
    
    BotSetup()
    
    #CacheTimeTableUrl
    th_spam.start()
    th_cache.start()
    th_logic.start()

    th_spam.join()
    th_cache.join()
    th_logic.join()
