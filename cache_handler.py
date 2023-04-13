from datetime import date, timedelta
from time import sleep
import database as db
import datetime

def HandleEventNewDay():
    db.ulActiveDay.ResetUserList()
    db.todaySended = 0
    db.CachedData.UpdateAll()
    print("\t Data cache event [day]")

def HandleEventNewWeek():
    db.ulActiveWeek.ResetUserList()
    print("\t Data cache event [week]")

def CheckDayActivity(today, prevDay, prevWeekday, weekday):
    try:
        if (today.day != prevDay.day):
            HandleEventNewDay()
                    
        if (weekday < prevWeekday):
            HandleEventNewWeek()
    except: pass

def cycleThread():
    HandleEventNewDay()
    HandleEventNewWeek()
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
            
            now = datetime.datetime.now()
            next_day = now.date() + timedelta(days=1)
            time_left = datetime.datetime.combine(next_day, datetime.time.min) - now
            seconds_left = time_left.total_seconds()
            
            sleep(seconds_left + 60)

        except Exception as e:
            print(f'cache_th exception: {e}')