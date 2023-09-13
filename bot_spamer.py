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
from database import User

def SpammingThread(user_id, pairList):
    bot_messages.SendTimeTableWithPairList(user_id, False, pairList)

def SpamTesters():
    bot_messages.SendTimeTable(834602791, False)
    return 1

def SpamAllUsers():
    sended = 0
    threadList = list()
    pairList = pair_manager.GetPairTimeList(date.today())

    rows = db.udb.Execute(f'SELECT user_id FROM {db.udb.tableName} WHERE spam_status = 1')

    for row in rows:
        uid = row[0]
        thread = Thread(target = SpammingThread, args= (uid, pairList,))
        thread.start()
        threadList.append(thread)
        sended += 1
    for t in threadList:
        t.join()
    threadList.clear()
    return sended
    
def SpamStart():
    print("Spam activated")
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
            
            pairTimes.insert(0, pair_manager.PairTime("0:0", "8:30")) # Исключение для первой пары
            for item in pairList:
                pairTimes.append(item)
            
            timeNow = localtime.GetLocalTime()
            closestTimeToPair = GetClosestTimeToPair(pairTimes, timeNow)
            
            needSpam = closestTimeToPair <= 5 and closestTimeToPair >= 0
            
            if (needSpam): 
                startTime = localtime.GetLocalTime()
                if (SpamStart() > 0):
                    closestTimeToPair = GetClosestTimeToPair(pairTimes, localtime.GetLocalTime()) + 10
                    endTime = localtime.GetLocalTime()
                    db.lastSpamDuration = str(endTime - startTime)
                    db.lastSpamTime = startTime.strftime("%H:%M:%S")
                    print(f'Spammed time: {endTime - startTime}')

            closestTimeToPair -= 5
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
    closestTimeToPair = 65
    for pairTime in pairTimes:
        times = pairTime.end
        #timeprint = times.strftime("%H:%M")
        # print(f"GetClosestTimeToPair: {timeprint}")
        #timeDifference = (times - timeNow).total_seconds() / 60 - 5
        timeDifference = (times - timeNow).total_seconds() / 60
        if (timeDifference >= 0 and timeDifference < closestTimeToPair):
            closestTimeToPair = timeDifference
    print(f"\tPair end in {int(closestTimeToPair)} mins")
    return closestTimeToPair