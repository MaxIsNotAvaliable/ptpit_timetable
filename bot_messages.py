import pair_manager
import config
import database as db

import json
import telebot
import requests
from datetime import date, datetime, timedelta
import pytz as pytz

helpMessage = """
<a href= "https://ptpit.ru/?page_id=84">Официальный сайт с расписанием</a>.

/settings - панель с настройками.
/group - выбор группы.
/teacher - расписание для преподавателя.
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
            print(f"{db.GetUserById(uid)} user not found\n{e}")
        else:
            print(f"{db.GetUserById(uid)} - {e}")

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

def SendTimeTable(user_id, isSendClosest):
    messageToReply = pair_manager.GetFullTimeTable(user_id, isSendClosest)
    if (messageToReply == None): return False
    NewSendMessage(user_id, messageToReply)
    return True

def SendTimeTableWithPairList(user_id, isSendClosest, pairList):
    messageToReply = pair_manager.GetFullTimeTable(user_id, isSendClosest, pairList)
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
Если у вас возникли трудности - свяжитесь с <a href="https://vk.com/ptpitras" target="_blank">разработчиками</a>.
'''
    
    messageToReply = selectedGroupName
    if (isSpamMode): messageToReply += spamMessage
    messageToReply += helperMessage
    if (grpFullName != None and grpFullName[-1] == "п"): messageToReply += attentionMessage
    return messageToReply

def getTeacherSelectedMessage(teacherId : str, isSpamMode = False):
    
    selectedTeacherName = f"Прикреплено расписание для {db.GetTeacherNameById(teacherId)}\n"
    helperMessage = '\nЧтобы узнать следующую пару используйте кнопку "Куда идти?" или напишите боту "куда".'
    spamMessage ="\n\nТеперь вы будете получать оповещения, которые будут содержать информацию о вашей следующей паре за 5 минут до окончания текущей пары, эту функцию можно отключить в настройках - /settings"

    messageToReply = selectedTeacherName
    if (isSpamMode): messageToReply += spamMessage
    messageToReply += helperMessage
    return messageToReply