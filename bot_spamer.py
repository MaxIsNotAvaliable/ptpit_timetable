import database as db
import pair_manager
import bot_messages
import config
import localtime

from threading import Thread
from datetime import datetime
from datetime import date

import time
import pytz as pytz


def SpammingThread(row):
    if (row["spam_stats"] == "1" and db.UserValidAuto(row)):
        bot_messages.SendTimeTable(row["user_id"], False)
    else:
        print(f'Skipped {row["username"]}')

def SpamTesters():
    bot_messages.SendTimeTable(834602791, False)
    return 1

def SpamAllUsers():
    sended = 0
    threadList = list()
    for row in db.DataBaseTable:
        thread = Thread(target = SpammingThread, args= (row,))
        thread.start()
        threadList.append(thread)
        sended += 1
    for t in threadList:
        t.join()
    threadList.clear()
    return sended
    
def SpamStart():
    if (config.IsBotInDebug()): return SpamTesters()
    else: return SpamAllUsers()

def cycleThread():
    today = date.today()
    prevDay = today
    prevWeekday = today.weekday()
    while (True):
        try:
            today = date.today()
            weekday = today.weekday()
            
            CheckDayActivity(today, prevDay, prevWeekday, weekday)
            
            prevDay = today
            prevWeekday = weekday

            pairList = pair_manager.GetPairTimeList(date.today())
            pairTimes = list()
            
            pairTimes.insert(0, pair_manager.PairTime("0:0:0", "8:30:00")) # Исключение для первой пары
            for item in pairList:
                pairTimes.append(item)
            
            timeNow = localtime.GetLocalTime()
            closestTimeToPair = GetClosestTimeToPair(pairTimes, timeNow)
            
            needSpam = closestTimeToPair <= 5 and closestTimeToPair >= 0
                        
            if (needSpam):
                if (SpamStart() > 0): 
                    closestTimeToPair = GetClosestTimeToPair(pairTimes, localtime.GetLocalTime()) + 15
            
            print(f'Time {timeNow.strftime("%H:%M")} -> {str(closestTimeToPair)[0:5]} mins')
            time.sleep(int(closestTimeToPair * 60))
            
        except Exception as e:
            db.ulActiveDay.ResetUserList()
            db.todaySended = 0
            db.ulActiveWeek.ResetUserList()
            print(f"SpamTh exception: {e}")

def CheckDayActivity(today, prevDay, prevWeekday, weekday):
    try:
        if (today.day != prevDay.day):
            db.ulActiveDay.ResetUserList()
            db.todaySended = 0
                    
        if (weekday < prevWeekday):
            db.ulActiveWeek.ResetUserList()
    except: pass

def GetClosestTimeToPair(pairTimes, timeNow):
    closestTimeToPair = 60
    for pairTime in pairTimes:
        times = pairTime.end
        #timeprint = times.strftime("%H:%M")
        # print(f"GetClosestTimeToPair: {timeprint}")
        #timeDifference = (times - timeNow).total_seconds() / 60 - 5
        timeDifference = (times - timeNow).total_seconds() / 60
        if (timeDifference >= 0 and timeDifference < closestTimeToPair):
            closestTimeToPair = timeDifference
    print(f"\tclosestTimeToPair: {int(closestTimeToPair)} min")
    return closestTimeToPair