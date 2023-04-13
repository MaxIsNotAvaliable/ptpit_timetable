from tracemalloc import start
import config
import requests
import database as db
import localtime

import json

from datetime import datetime, timedelta
from datetime import date
import pytz as pytz

pairSep = "\n⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯"

def GetSecs(t):
    return int(timedelta(hours=t.hour, minutes=t.minute, seconds=t.second).total_seconds())

def MapValue(valueLeft, valueRight, value):
    return (value - valueLeft) / (valueRight - valueLeft)

def MapTime(timeLeft, timeRight, currentTime):
    return MapValue(GetSecs(timeLeft), GetSecs(timeRight), GetSecs(currentTime))

class PairTime:
    start : str
    end : str
    def __init__(self, start_time, end_time):
        self.start = datetime.strptime(start_time, "%H:%M:%S")
        self.end = datetime.strptime(end_time, "%H:%M:%S")

PairTimeArr = list()
PairTimeArr.append(PairTime("8:30:00",  "10:05:00"))
PairTimeArr.append(PairTime("10:25:00", "12:00:00"))
PairTimeArr.append(PairTime("12:20:00", "14:10:00"))
PairTimeArr.append(PairTime("14:15:00", "15:50:00"))
PairTimeArr.append(PairTime("16:10:00", "17:55:00"))
PairTimeArr.append(PairTime("18:00:00", "19:35:00"))

PairTimeArrShort = list()
PairTimeArrShort.append(PairTime("8:30:00",  "9:30:00"))
PairTimeArrShort.append(PairTime("09:40:00", "10:40:00"))
PairTimeArrShort.append(PairTime("11:00:00", "12:00:00"))
PairTimeArrShort.append(PairTime("12:20:00", "13:20:00"))
PairTimeArrShort.append(PairTime("13:30:00", "14:30:00"))
PairTimeArrShort.append(PairTime("14:40:00", "15:40:00"))
PairTimeArrShort.append(PairTime("15:50:00", "16:50:00"))

PairTimeArrHalfShort = list() # 4+ is shorted
PairTimeArrHalfShort.append(PairTime("8:30:00",  "10:05:00"))
PairTimeArrHalfShort.append(PairTime("10:25:00", "12:00:00"))
PairTimeArrHalfShort.append(PairTime("12:20:00", "14:10:00"))
PairTimeArrHalfShort.append(PairTime("14:15:00", "15:50:00"))
PairTimeArrHalfShort.append(PairTime("16:10:00", "17:15:00")) # EXTRA
PairTimeArrHalfShort.append(PairTime("17:20:00", "18:25:00")) # EXTRA
PairTimeArrHalfShort.append(PairTime("18:30:00", "19:35:00")) # EXTRA

PairTimeArrSpecialDay = list()
PairTimeArrSpecialDay.append(PairTime("8:30:00",  "9:30:00"))
PairTimeArrSpecialDay.append(PairTime("09:40:00", "10:40:00"))
PairTimeArrSpecialDay.append(PairTime("11:00:00", "12:00:00"))
PairTimeArrSpecialDay.append(PairTime("12:10:00", "13:10:00"))
PairTimeArrSpecialDay.append(PairTime("14:30:00", "15:30:00"))
PairTimeArrSpecialDay.append(PairTime("15:50:00", "16:50:00"))
PairTimeArrSpecialDay.append(PairTime("17:00:00", "18:00:00"))
PairTimeArrSpecialDay.append(PairTime("18:10:00", "19:10:00"))

def ParseJsTime(vTableIndex : int):
    url = "https://timetable.ptpit.ru/assets/timetable.js"
    foo_list = requests.get(url).text.split('function ')
    idx = -1
    for i, foo in enumerate(foo_list):
        if "getTime(lessonId, date = ''" in foo:
            idx = i
            break
    if idx == -1:
        return []

    dates = foo_list[idx].split('switch')[vTableIndex+1].split('date ===')
    dates.pop(0)
    dates = [d[2:12] for d in dates]
    return dates

def IsDayShortened(data):
    shortDays = ParseJsTime(0)
    if (data in shortDays):
        return True
    return False

def IsDayHalfShortened(data):
    shortDays = ParseJsTime(1)
    if (data in shortDays):
        return True
    return False

def GetPairTimeList(data): # datetime.date --- yyyy-mm-dd
    strData = data.strftime('%Y-%m-%d')
    beginTime = datetime.now()
    if (data.weekday() == 0):
        return PairTimeArrSpecialDay
    if (IsDayShortened(strData)):
        return PairTimeArrShort
    if (IsDayHalfShortened(strData)):
        return PairTimeArrHalfShort
    print(f"\tOptimize???: {datetime.now() - beginTime } - cache by days")
    return PairTimeArr

def GetCurrentPair(pairList = None):
    pairNum = -1
    time = localtime.GetLocalTime()
    if (pairList == None):
        pairList = GetPairTimeList(date.today())

    if (time > pairList[-1].end): 
        return None
        
    for i in range(len(pairList)):
        if (time >= pairList[i].start):
            pairNum = i
            
    return pairNum

def GetBestPair(pairList = None):
    pairNum = 0
    isNext = True
    
    time = localtime.GetLocalTime()
    if (pairList == None):
        pairList = GetPairTimeList(date.today())

    if (time > pairList[-1].end): 
        return None
    
    for i in range(len(pairList)):
        timemap = MapTime(pairList[i].start, pairList[i].end, time)
        #print(f"[{i}] " + pairList[i].start.strftime("%H:%M") + " - " + pairList[i].end.strftime("%H:%M") + "\t{" + time.strftime("%H:%M") + "}" + f"\t{timemap}")
        
        if (timemap > -0.02 and timemap < 1.25):
            if (timemap > 0.5 and i + 1 != len(pairList)):
                pairNum = i + 1
                isNext = True
            else: 
                pairNum = i
                isNext = False
            if (isNext == True): m = "next"
            else : m = "current"
            #print(f"\t\tset as " + m)

    # if (isNext == True): m = "next"
    # else : m = "current"
    # print(f"pairnum: {pairNum}, {m}")
    
    return pairNum, isNext

def FilterPairs(pairArray : list):
    for id in range(len(pairArray)):
        if (id > 0 and pairArray[id] == pairArray[id - 1]):
            pairArray[id].Name = "DELETE-KEY"
            pairArray[id-1].Subgroup = 0
    for pair in pairArray:
        if (pair.Name == "DELETE-KEY"):
            pairArray.remove(pair)
            continue
    for pair in pairArray:
        parsed = str(pair.Moodle).replace("Конференция: ", "").replace("Задача: ", "").replace("Ресурс: ", "").split("\n")
        for element in parsed:
            try:
                if (not (bool(set(config.alphabet).intersection(set(element.lower()))) or " " in element or element == '')):
                    elemented = '<a href="' + element + '"><strong>ссылка</strong></a>'
                    pair.Moodle = str(pair.Moodle).replace(element, elemented)
            except:
                pass
    return pairArray

def ParseTimetableJson(date, data):
    pairArray = []
    for x in range(len(data)):
        if (date.strftime("%Y-%m-%d") == data[x]["date"]):
            Pair = config.pair()
            Pair.Num = data[x]["num"]
            Pair.Name = data[x]["subject_name"]
            Pair.GroupName = data[x]["group_name"]
            if (data[x]["teacher_surname"] != None and data[x]["teacher_name"] != None and data[x]["teacher_secondname"] != None):
                Pair.TeacherName = data[x]["teacher_surname"] + " " + data[x]["teacher_name"][0] + ". " + data[x]["teacher_secondname"][0] + "."
            
            try:
                if (data[x]["note"] != None and data[x]["note"] != ""):
                    Pair.Name += " <strong>(" + data[x]["note"] + ")</strong>"
            except:
                pass
            
            Pair.Room = data[x]["room_name"] 
            moodle = data[x]["moodle"]
            if (moodle != None):
                moodle = json.loads(moodle)
                for k in moodle:
                    if (k["type"] == 'meeting'):
                        if (Pair.Moodle != ''): Pair.Moodle += "\n"
                        Pair.Moodle += "Конференция: "
                    elif (k["type"] == 'task'):
                        if (Pair.Moodle != ''): Pair.Moodle += "\n"
                        Pair.Moodle += "Задача: "
                    elif (k["type"] == 'resource'):
                        if (Pair.Moodle != ''): Pair.Moodle += "\n"
                        Pair.Moodle += "Ресурс: "
                    if (not (bool(set(config.alphabet).intersection(set(k["url"].lower()))) or " " in k["url"])):
                        Pair.Moodle += k["url"] 
                    else: Pair.Moodle += k["url"]
            Pair.Subgroup = data[x]["subgroup"]
            pairArray.append(Pair)
        else: break
    
    return FilterPairs(pairArray)

def GetByDate(date, user_id, isHlCurrentPair):
    user = db.GetUserById(user_id)
    if(user == None or user["groupid"] == None or user['teacher_id'] == None):
        return "Зарегистрируйтесь в боте: <code>/settings</code>."
    
    if (date.weekday() == 6):
        if (date == date.today()):
            return "Сегодня воскресенье."
        else:
            return "Завтра воскресенье."
    
    userIsStudent = user['is_teacher'] == '0'
    if (userIsStudent):
        return GetByStudent(date, user["groupid"], isHlCurrentPair)
    else:
        return GetByTeacher(date, user["teacher_id"], isHlCurrentPair)

def studentPairFormat(pair, pairTimeList):
    pairNum = pair.Num
    timelist = pairTimeList[pairNum - 1]
    
    messageToReply = f"""
Пара: {pair.Num} <strong>[{(timelist.start).strftime("%H:%M")}-{(timelist.end).strftime("%H:%M")}]</strong> 
Предмет: {pair.Name}"""
    if (pair.Subgroup != 0):
        messageToReply += f" <strong>[{pair.Subgroup}пг]</strong>"
        
    if (pair.Room == None):
        messageToReply += "\nКабинет не указан"
        return timelist
    
    if (str(pair.Room) != "ДО"):
        messageToReply += "\nКабинет: " + str(pair.Room).replace('\n', '')
        return messageToReply
    
    if (pair.Moodle != ''):
        messageToReply += "\n" + str(pair.Moodle)
    else:
        messageToReply += "\nДистанционно"
    return messageToReply

def GetByStudent(date, group_id, isHlCurrentPair):   
    messageToReply = ""
    data = requests.get(f'{db.GetTimeTableUrl()}/timetable/groups/{group_id}/{date.strftime("%Y-%m-%d")}').json()
    
    pairArray = ParseTimetableJson(date, data)
    pairTimeList = GetPairTimeList(date)
    
    if (isHlCurrentPair):
        currentPair = GetCurrentPair(pairTimeList)
        if (currentPair != None):
            currentPair += 1

    OneMessage = True
    for ids in range(len(pairArray)):
        if (OneMessage != True):
            messageToReply += pairSep
        if (isHlCurrentPair and pairArray[ids].Num == currentPair):
            messageToReply += "\n<strong><em>[Текущая пара]</em></strong>"
        messageToReply += studentPairFormat(pairArray[ids], pairTimeList)
        OneMessage = False
    
    if (messageToReply == ''): 
        messageToReply += "Расписание не найдено."
        
    return messageToReply

def teacherPairFormat(pair, pairTimeList):
    pairTime = pairTimeList[pair.Num - 1]
    # pairArray[ids]
    messageToReply = f"""
Пара: {pair.Num} <strong>[{(pairTime.start).strftime("%H:%M")}-{(pairTime.end).strftime("%H:%M")}]</strong> 
Предмет: {pair.Name}
Группа: {pair.GroupName}"""
    
    if (pair.Subgroup != 0):
        messageToReply += f" <strong>[{str(pair.Subgroup)}пг]</strong>"
    
    if (pair.Room == None):
        messageToReply += "\nКабинет не указан"
        return messageToReply

    if (str(pair.Room) != "ДО"):
        messageToReply += f"\nКабинет: " + str(pair.Room).replace('\n', '')
        return messageToReply

    if (pair.Moodle != ''):
        messageToReply += "\n" + str(pair.Moodle)
    else:
        messageToReply += "\nДистанционно"
    return messageToReply

def GetByTeacher(date, teacher_id, isHlCurrentPair):
    messageToReply = ""
    data = requests.get(f'{db.GetTimeTableUrl()}/timetable/teachers/{teacher_id}/{date.strftime("%Y-%m-%d")}').json()
    
    pairArray = ParseTimetableJson(date, data)
    pairTimeList = GetPairTimeList(date)

    OneMessage = True
    if (isHlCurrentPair):
        currentPair = GetCurrentPair()
        if (currentPair != None):
            currentPair += 1
            
    for ids in range(len(pairArray)):
        if (OneMessage != True):
            messageToReply += pairSep
        if (isHlCurrentPair and pairArray[ids].Num == currentPair):
            messageToReply += "\n<strong><em>[Текущая пара]</em></strong>"
        messageToReply += teacherPairFormat(pairArray[ids], pairTimeList)
        OneMessage = False
    if (messageToReply == ''): messageToReply += "Расписание не найдено."
    return messageToReply