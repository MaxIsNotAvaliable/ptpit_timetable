import pair_manager
import config

import json
import telebot
import requests
from datetime import date, datetime, timedelta
import pytz as pytz
import database as db

helpMessage = """
<a href= "https://ptpit.ru/?page_id=84">Официальный сайт с расписанием</a>.

/settings - панель с настройками.
/user - информация о пользователе.

Связь с <a href= "https://vk.com/ptpitras">разработчиками</a>.

P.s. бот в тестовом режиме, рекомендуется перепроверять расписание с официального сайта.
"""

startMessage = """
Привет, я бот Игорь, Ваш помощник с расписанием в ПТПИТ'е.

Для начала работы мне нужно узнать кто вы - преподаватель или студент?

P.s. бот в тестовом режиме, советую перепроверять расписание с <a href= "https://ptpit.ru/?page_id=84">официального сайта</a>.
"""

needToRegister = "Вам нужно зарегистрироваться в боте как студент или преподаватель - /settings."

# use "x = dayArray % 7"
dayArray = [ 
    "пон",
    "втор",
    "сред",
    "четв",
    "пят",
    "суб",
    "вос",
    "пн",
    "вт",
    "ср",
    "чт",
    "пт",
    "сб",
    "вс",
]

dayArrayExceptions = [
    "курс",
    "авто"
    #"втр", # компенсация для "ВТОРник"
]

dayCompareArray = [
    "день",
    "дня",
    "дня",
    "дня",
    "дней",
    "дней",
    "дней",
]

bot = telebot.TeleBot(config.TOKEN)
def NewSendMessage(uid, messageText, reply_markup=None):
    try:
        result = None
        if (reply_markup != None):
            result = bot.send_message(uid, messageText, parse_mode="HTML", reply_markup=reply_markup, disable_web_page_preview=True)
        else:
            result = bot.send_message(uid, messageText, parse_mode="HTML", disable_web_page_preview=True)
            
        db.ulActiveDay.AddUser(uid)
        db.ulActiveWeek.AddUser(uid)
        db.todaySended += 1
        return result
        
    except telebot.apihelper.ApiException as e:
        if (e.error_code == 403):
            print(str(db.GetUserById(uid)) + " blocked bot")
            db.ulBlocked.AddUser(uid)
        elif (e.error_code == 400):
            print(str(db.GetUserById(uid)) + " user not found")
        else:
            print(str(db.GetUserById(uid)) + str(e))

def NewEditMessage(uid, mid, messageText, reply_markup=None):
    try:
        result = None
        if (reply_markup != None):
            result = bot.edit_message_text(chat_id=uid, message_id=mid, text=messageText, reply_markup=reply_markup, parse_mode="HTML", disable_web_page_preview=True)
        else:
            result = bot.edit_message_text(chat_id=uid, message_id=mid, text=messageText, parse_mode="HTML", disable_web_page_preview=True)
            
        db.ulActiveDay.AddUser(uid)
        db.ulActiveWeek.AddUser(uid)
        db.todaySended += 1
        return result
        
    except telebot.apihelper.ApiException as e:
        if (e.error_code == 403):
            print(str(db.GetUserById(uid)) + " blocked bot")
            db.ulBlocked.AddUser(uid)
        elif (e.error_code == 400):
            print(e)
        else:
            print(str(db.GetUserById(uid)) + str(e))

def GetTimeTable(user_id, isSendClosest):
    today = date.today()
    pairList = pair_manager.GetPairTimeList(today)
    
    bestPair = pair_manager.GetBestPair(pairList) # pair_manager.GetCurrentPair(pairList)
    if (bestPair == None):
       return None
    
    targetPairNum = bestPair[0]
    
    if (bestPair[1]):
        messageToReply = "\nВаша следующая пара:\n"
    else:
        messageToReply = "\nВаша текущая пара:\n"
   
    user = db.GetUserById(user_id)
    if(user == None or user["groupid"] == None):
        return "Зарегистрируйтесь как преподаватель или студент."
    
    userIsStudent = user['is_teacher'] == '0'
    gid = user['groupid']
    tid = user['teacher_id']
    if (userIsStudent):
        data = requests.get(f'{db.GetTimeTableUrl()}/timetable/groups/{gid}/{today.strftime("%Y-%m-%d")}').json()
    else:
        data = requests.get(f'{db.GetTimeTableUrl()}/timetable/teachers/{tid}/{today.strftime("%Y-%m-%d")}').json()
    
    pairArray = []
    while(len(pairArray) == 0 and targetPairNum < len(pairList)): 
        targetPairNum += 1
        for x in range(len(data)):
            datax = data[x]
            OneSep = True
            
            if (today.strftime("%Y-%m-%d") != datax["date"]):   
                continue             
            if(targetPairNum != datax["num"]): # "datax["num"] - 1" - for next pair
                continue
            
            Pair = config.pair()
            
            Pair.GroupName = datax["group_name"]
            Pair.Num = datax["num"]
            Pair.Name = datax["subject_name"]
            Pair.Room = datax["room_name"]
            moodle = datax["moodle"]
            if (moodle != None):
                moodle = json.loads(moodle)
                for k in moodle:
                    if (OneSep == False):
                        Pair.Moodle += "\n"
                    OneSep = False
                    if (k["type"] == 'task'):
                        Pair.Moodle += "Задача: "
                    if (k["type"] == 'meeting'):
                        Pair.Moodle += "Конференция: "
                    if (k["type"] == 'resource'):
                        Pair.Moodle += "Ресурс: "
                    Pair.Moodle += k["url"]
            Pair.Subgroup = datax["subgroup"]
            pairArray.append(Pair)
            
        if (not isSendClosest): break
    pairArray = pair_manager.FilterPairs(pairArray)
    if(len(pairArray) != 0 and targetPairNum < len(pairList)):
        OneMessage = True
        for pairs in pairArray:
            if (OneMessage == True):
                messageToReply += "Время: " + pairList[targetPairNum - 1].start.strftime("%H:%M")
            else:
                messageToReply += pair_manager.pairSep
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
    return None

def SendTimeTable(user_id, isSendClosest):
    messageToReply = GetTimeTable(user_id, isSendClosest)
    if (messageToReply == None): return False
    NewSendMessage(user_id, messageToReply)
    return True

def SendTeacherTimeTable(user_id, isHlCurrentPair):
    today = date.today()
    messageToReply = pair_manager.GetByTeacher(today, user_id, isHlCurrentPair)
    if (messageToReply == None): return False
    NewSendMessage(user_id, messageToReply)
    return True

def GetGroupMessage(arg):
    splited = arg.split(" ")
    if (len(splited) > 1):
        return splited[1]
    else:
        return -1
    
def getGroupSelectedMessage(groupName : str, isSpamMode = False):
    grpFullName = db.getGroupFullName(groupName)
    
    selectedGroupName = f"Выбрана группа {grpFullName}\n"
    helperMessage = '\nЧтобы узнать следующую пару используйте кнопку "Куда идти?" или напишите боту "куда".'
    spamMessage ="\n\nТеперь вы будете получать оповещения, которые будут содержать информацию о вашей следующей паре за 5 минут до окончания текущей пары, эту функцию можно отключить в настройках - /settings"
    attentionMessage ='''\n\n<b>Внимание!</b>\n
Была выбрана платная группа (п), только некоторые платные группы в ПТПИТ'е имеют свое расписание, если такого нет попробуйте выбрать основноую группу (Т.е. вместо <b>"' +grpFullName+ '" "'+grpFullName[:-1:]+'"</b>).
Если у вас возникли трудности - свяжитесь с <a href="https://vk.com/ptpitras" target="_blank">администрацией</a>.
'''
    
    messageToReply = selectedGroupName
    if (isSpamMode): messageToReply += spamMessage
    messageToReply += helperMessage
    if (grpFullName != None and grpFullName[-1] == "п"): messageToReply += attentionMessage
    return messageToReply

def getTeacherSelectedMessage(teacherId : str, isSpamMode = False):
    
    selectedTeacherName = f"Прикреплено расписания для {db.GetTeacherNameById(teacherId)}\n"
    helperMessage = '\nЧтобы узнать следующую пару используйте кнопку "Куда идти?" или напишите боту "куда".'
    spamMessage ="\n\nТеперь вы будете получать оповещения, которые будут содержать информацию о вашей следующей паре за 5 минут до окончания текущей пары, эту функцию можно отключить в настройках - /settings"

    messageToReply = selectedTeacherName
    if (isSpamMode): messageToReply += spamMessage
    messageToReply += helperMessage
    return messageToReply