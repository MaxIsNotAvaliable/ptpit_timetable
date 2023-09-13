from tracemalloc import start
import config
import requests
import database as db
import localtime

import json

from printer import PrintEx
from datetime import datetime, timedelta
from datetime import date
import pytz as pytz

pairSep = "\n⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯"

class pair:
    Name = "Пары нет"
    Num : int
    TableID : int
    Room: int
    Subgroup : int
    Moodle = ""
    Note = ""
    GroupName = ""
    TeacherName = ""
    
    def parseData(self, data):
        self.GroupName = data["group_name"]
        self.Num = data["num"]
        self.Name = data["subject_name"]
        self.Room = data["room_name"]
        self.Subgroup = data["subgroup"]
        
        note = data["note"]
        if (note != None and len(note) > 1):
            self.Note = str(note)
        
        moodle = data["moodle"]
        if (moodle != None):
            moodle = json.loads(moodle)
            for k in moodle:
                if (len(self.Moodle) > 1):
                   self.Moodle += "\n"
                if (k["type"] == 'task'):
                    self.Moodle += "Задача: "
                elif (k["type"] == 'meeting'):
                    self.Moodle += "Конференция: "
                elif (k["type"] == 'resource'):
                    self.Moodle += "Ресурс: "
                    
                # if (not (bool(set(config.alphabet).intersection(set(k["url"].lower()))) or " " in k["url"])):
                #     self.Moodle += k["url"] 
                # else: self.Moodle += k["url"]
                self.Moodle += k["url"]

        try:
            if (data["teacher_surname"] != None and data["teacher_name"] != None and data["teacher_secondname"] != None):
                self.TeacherName = data["teacher_surname"] + " " + data["teacher_name"][0] + ". " + data["teacher_secondname"][0] + "."
        except Exception as e: PrintEx(e)
        return self
    
    def __eq__(self, other):
        return (self.Name == other.Name and self.Num == other.Num and self.Room == other.Room and self.Moodle == other.Moodle and self.GroupName == other.GroupName)
    
    def isPairNear(self, other):
        if (self.Name == other.Name 
        and self.Room == other.Room 
        and self.Subgroup == other.Subgroup 
        and self.GroupName == other.GroupName
        and self.Moodle == other.Moodle):
            numRes = self.Num - other.Num
            if (numRes <= 1 and numRes >= -1):
                return True
        return False

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
        self.start = datetime.strptime(start_time, "%H:%M")
        self.end = datetime.strptime(end_time, "%H:%M")
        
    def GetFormat(self) -> str:
        return f"{self.start.strftime('%H:%M')}-{self.end.strftime('%H:%M')}"


# Might be obsolete vvv
PairTimeArr = list()
PairTimeArr.append(PairTime("8:30",  "10:05"))
PairTimeArr.append(PairTime("10:25", "12:00"))
PairTimeArr.append(PairTime("12:20", "14:10"))
PairTimeArr.append(PairTime("14:15", "15:50"))
PairTimeArr.append(PairTime("16:10", "17:55"))
PairTimeArr.append(PairTime("18:00", "19:35"))

PairTimeArrShort = list()
PairTimeArrShort.append(PairTime("8:30",  "9:30"))
PairTimeArrShort.append(PairTime("09:40", "10:40"))
PairTimeArrShort.append(PairTime("11:00", "12:00"))
PairTimeArrShort.append(PairTime("12:20", "13:20"))
PairTimeArrShort.append(PairTime("13:30", "14:30"))
PairTimeArrShort.append(PairTime("14:40", "15:40"))
PairTimeArrShort.append(PairTime("15:50", "16:50"))

PairTimeArrHalfShort = list() # 4+ is shorted
PairTimeArrHalfShort.append(PairTime("8:30",  "10:05"))
PairTimeArrHalfShort.append(PairTime("10:25", "12:00"))
PairTimeArrHalfShort.append(PairTime("12:20", "14:10"))
PairTimeArrHalfShort.append(PairTime("14:15", "15:50"))
PairTimeArrHalfShort.append(PairTime("16:10", "17:15")) # EXTRA
PairTimeArrHalfShort.append(PairTime("17:20", "18:25")) # EXTRA
PairTimeArrHalfShort.append(PairTime("18:30", "19:35")) # EXTRA

PairTimeArrSpecialDay = list()
PairTimeArrSpecialDay.append(PairTime("8:30",  "9:30"))
PairTimeArrSpecialDay.append(PairTime("09:40", "10:40"))
PairTimeArrSpecialDay.append(PairTime("11:00", "12:00"))
PairTimeArrSpecialDay.append(PairTime("12:10", "13:10"))
PairTimeArrSpecialDay.append(PairTime("14:30", "15:30"))
PairTimeArrSpecialDay.append(PairTime("15:50", "16:50"))
PairTimeArrSpecialDay.append(PairTime("17:00", "18:00"))
PairTimeArrSpecialDay.append(PairTime("18:10", "19:10"))

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

# ^^^ Might be obsolete

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
            Pair = pair().parseData(data[x])
            pairArray.append(Pair)
        else: break
    
    return FilterPairs(pairArray)

def GetByDate(date, user_id, isHlCurrentPair):
    user = db.GetUserById(user_id)
    if(user == None or not user.UserValidAny()):
        return "Зарегистрируйтесь в боте: <code>/settings</code>."
    if (date.weekday() == 6):
        if (date == date.today()):
            return "Сегодня воскресенье."
        else:
            return "Завтра воскресенье."
    
    userIsStudent = user.IsStudent()
    if (userIsStudent):
        return GetByStudent(date, user.GroupID(), isHlCurrentPair)
    else:
        return GetByTeacher(date, user.TeacherID(), isHlCurrentPair)

def studentPairFormat(pair, pairTimeList):
    pairNum = pair.Num
    timelist = pairTimeList[pairNum - 1]
    
    messageToReply = f"\nПара: {pair.Num} <strong>[{timelist.GetFormat()}]</strong>\n"
    
    messageToReply += f"Предмет: {pair.Name}"
    
    if (len(pair.Note) > 1):
        messageToReply += f" <strong>({pair.Note})</strong>"

    if (pair.Subgroup != 0):
        messageToReply += f" <strong>[{pair.Subgroup}пг]</strong>"
        
    if (pair.Room == None):
        messageToReply += "\nКабинет не указан"
        return messageToReply
    
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
        a = studentPairFormat(pairArray[ids], pairTimeList)
        messageToReply += a
        OneMessage = False
    
    if (messageToReply == ''): 
        messageToReply += "Расписание не найдено."
        
    return messageToReply

def teacherPairFormat(pair, pairTimeList):
    pairTime = pairTimeList[pair.Num - 1]
    messageToReply = f"\nПара: {pair.Num} <strong>[{pairTime.GetFormat()}]</strong>\n"
    
    messageToReply += f"Предмет: {pair.Name}"
    
    if (len(pair.Note) > 1):
        messageToReply += f" <strong>({pair.Note})</strong>"

    if (pair.Subgroup != 0):
        messageToReply += f" <strong>[{pair.Subgroup}пг]</strong>"
    
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
        currentPair = GetCurrentPair(pairTimeList)
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


def bestPairFormat(pairArray, pairList, targetPairNum, userIsStudent):
    OneMessage = True
    messageToReply = ''
    for pairs in pairArray:
        if (OneMessage == True):
            messageToReply += "Время: " + pairList[targetPairNum - 1].start.strftime("%H:%M")
        else:
            messageToReply += pairSep
        messageToReply += "\nПредмет: " + pairs.Name
        if (not userIsStudent):
            messageToReply += "\nГруппа: " + pairs.GroupName
        if (pairs.Room == None):
            messageToReply += "\nКабинет не указан"
        else:
            if (str(pairs.Room) != "ДО"):
                messageToReply += "\nКабинет: " + str(pairs.Room).replace('\n', '')
            else:
                messageToReply += "\nДистанционно"
                messageToReply += "\n" + str(pairs.Moodle)
        if (pairs.Subgroup != 0):
            messageToReply += "\nПодгруппа: " + str(pairs.Subgroup)
        OneMessage = False
    return messageToReply



def GetFullTimeTable(user_id, isSendClosest, pairList = None):
    today = date.today()
    if (pairList == None):
        pairList = GetPairTimeList(today)
    
    bestPair = GetBestPair(pairList) # pair_manager.GetCurrentPair(pairList)
    if (bestPair == None):
       return None
    
    targetPairNum = bestPair[0]
    
    user = db.GetUserById(user_id)
    if(user == None or not user.UserValidAny()):
        return "Зарегистрируйтесь как преподаватель или студент."
    
    userIsStudent = user.IsStudent()
    if (userIsStudent): data = requests.get(f"{db.GetTimeTableUrl()}/timetable/groups/{user.GroupID()}/{today.strftime('%Y-%m-%d')}").json()
    else: data = requests.get(f"{db.GetTimeTableUrl()}/timetable/teachers/{user.TeacherID()}/{today.strftime('%Y-%m-%d')}").json()
    
    pairArray = []
    while(len(pairArray) == 0 and targetPairNum < len(pairList)): 
        targetPairNum += 1
        for x in range(len(data)):
            datax = data[x]
            
            if (today.strftime("%Y-%m-%d") != datax["date"]): continue
            if(targetPairNum != datax["num"]): continue
            
            Pair = pair().parseData(datax)
            pairArray.append(Pair)
            
        if (not isSendClosest): break
    
    pairArray = FilterPairs(pairArray)
    if(len(pairArray) == 0 or targetPairNum >= len(pairList)):
        return None
    
    pairFormatted = bestPairFormat(pairArray, pairList, targetPairNum, userIsStudent)
    if (bestPair[1]):
        return f"\nВаша следующая пара:\n{pairFormatted}"
    else:
        return f"\nВаша текущая пара:\n{pairFormatted}"
