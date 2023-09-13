import bot_messages
from bot_messages import dayArray, dayCompareArray, startMessage, getGroupSelectedMessage
import database as db
from database import User
import pair_manager as pm
import config
from printer import PrintEx


from threading import Thread
import numpy as np
import telebot
from telebot import types
from random import randrange
from datetime import date, timedelta
from datetime import datetime
import pytz as pytz


bot = bot_messages.bot
def cycleThread():
    while(True):
        try: bot_messages.bot.polling(none_stop = True)
        except: pass

# 
# Структура callback'ов:
# 'button_callback_'    - пометка что это ответ с кнопки;
# 'callback_name_'      - имя ответа, например 'set_student_';
# 'callback_from_'      - откуда пришел callback, чтобы вернуть его назад
# 'callback_origin'     - откуда пришел callback, в большем масштабе
#
# ------------------------
#
# P.s. заменять для 'callback_from' оригинальный 'button_callback_' на 'callback_from_',
# чтобы получилось по итогу: 
# button_callback_ + callback_name_ + callback_from_ + [callback_from_name_ + callback_origin_ + [callback_origin_name]]
#
# пример: 'button_callback_set_student_callback_from_set_teacher'
#                                                    ^^^^^^^^^^^
#                             оригинальное имя функции - 'button_callback_set_teacher'
#
# ------------------------
#
# проверка вызова будет проходить по типу: 
#       (func=lambda call: 'button_callback_callback_name' in call.data)
# замена в истории с 'button_callback_callback_name' на 'callback_from_callback_name'
# нужна для того чтобы други проверки не проходили ложно.
# ... + [callback_from_name_ + [callback_origin_ + callback_origin_name]]
# 
# таким образом можно сделать "историю", единственный вопрос только в том, как ограничить ее?
# Т.е. иметь связь по типу: "button_callback_ + callback_name_ + callback_from_ + callback_name_ + callback_from_ ..." - абсурд
# 
# Для этого можно сделать просто 2 варианта кнопки "Назад":
# 1) просто возвращает назад по истории - предыдущую вкладку
# 2) возвращает в оригинальную точку - т.е. если пользователь нажал: /start -> я студент -> 3 курс -> НАЗАД
# тогда его вернет на вкладку "я студент" и теперь он будет находиться по пути: /start -> я студент -> НАЗАД
# таким образом его вернет второй раз - в начало пути - на вкладку "/start" (из имени callback_origin_ + callback_origin_name)
# 
# ------------------------
# 
# 'callback_origin' будет использоваться для возврата в истории более масштабно;
# Т.е. вызов был изначально из расписания / помощи / старта
#
#
#

btnCallbackPrefix = 'b_cb_'

# prefixes:
# s - set
# g - get
# f - find
# c - change
# m - main page / root page

def HistoryCutTo(callHistory : str, page : str):
    pageData = page.replace(btnCallbackPrefix, '')
    data = callHistory.split('/')
    index = 0
    for i in reversed(range(len(data))):
        if (pageData in data[i]):
            index = i + 1
            break
    result = btnCallbackPrefix + '/'.join(str(i) for i in data[index:])
    return result

def HistoryGenerate(callHistory : str, nextPage : str): 
    callHistory = HistoryCutTo(callHistory, nextPage)
    result = f"{btnCallbackPrefix}{nextPage}/{callHistory.replace(btnCallbackPrefix, '')}"
    if (len(result) >= 59):
        print(f"Expecting error by calldata lenght, current: {len(result)}, max: 60. \t {result}")
    return result

def HistoryGenerateWithReset(nextPage : str): 
    result = f"{btnCallbackPrefix}{HistoryCurrentPage(nextPage)}"
    if (len(result) >= 59):
        print(f"Expecting error by calldata lenght, current: {len(result)}, max: 60. \t {result}")
    return result

def HistoryPrevPage(callHistory : str):
    data = callHistory.split('/', 1)
    if (len(data) <= 1 or data[1] == None): 
        return callHistory
    return f"{btnCallbackPrefix}{''.join(data[1:])}"

def HistoryCurrentPage(callHistory : str):
    data = callHistory.split('/', 1)
    return data[0]

def HistoryIsInTop(callHistory : str, page : str):
    parsed = HistoryCurrentPage(callHistory) 
   
    v = f'{btnCallbackPrefix}{page}' in parsed
    if (v and config.IsBotInDebug()): 
        print(f'{HistoryCurrentPage(HistoryPrevPage(callHistory))}\t\t->\t{page}')
    return v

def HistoryReplaceLastPage(callHistory : str, nextPage : str): 
    return HistoryGenerate(HistoryPrevPage(callHistory), nextPage)

def GetSettingsPageContent(message):
    callHistory = 'm_settings'
        
    markup_inline = types.InlineKeyboardMarkup()

    user = db.GetUserById(message.chat.id)
    if (user == None): 
        item1 = types.InlineKeyboardButton('Выбрать роль', callback_data=HistoryGenerate(callHistory, 'c_role'))
        markup_inline.add(item1)
        return markup_inline
    
    isUserStudent = user.IsStudent()
    if (user.UserValidAuto()): changeText = 'Сменить'
    else: changeText = 'Выбрать'
    item1 = types.InlineKeyboardButton(f'{changeText} роль', callback_data=HistoryGenerate(callHistory, 'c_role'))
    
    if (isUserStudent): 
        item2 = types.InlineKeyboardButton(f'{changeText} группу', callback_data=HistoryGenerate(callHistory, 'c_group'))
    else: 
        item2 = types.InlineKeyboardButton('Выбрать ФИО', callback_data=HistoryGenerate(callHistory, 'c_name'))
    markup_inline.add(item1, item2)
    
    item3 = types.InlineKeyboardButton('Авторасписание', callback_data=HistoryGenerate(callHistory, 'c_spam'))
    markup_inline.add(item3)
    
    if (user.UserValidAuto()):
        item4 = types.InlineKeyboardButton(text = 'Перейти к расписанию', callback_data=HistoryGenerateWithReset('m_timetable'))
        markup_inline.add(item4)

    return markup_inline


@bot.callback_query_handler(func=lambda call: HistoryIsInTop(call.data, 'm_settings'))
def handle_button_pressed(call):
    message = call.message
    user = db.GetUserById(message.chat.id)
    if (user == None):
        bot_messages.NewSendMessage(message.chat.id, 'Выберите роль.', markup_inline)
        return
    markup_inline = GetSettingsPageContent(call.message)
    messageToReply = GetSettingsMessageText(user)
    bot_messages.NewEditMessage(call.message.chat.id, call.message.message_id, messageToReply, markup_inline)
    
@bot.message_handler(commands = ['settings', 'params', 'param', ' settings', ' params', ' param',])
def SettingsCommand(message):
    markup_inline = GetSettingsPageContent(message)
    user = db.GetUserById(message.chat.id)
    if (user == None):
        bot_messages.NewSendMessage(message.chat.id, 'Выберите роль.', markup_inline)
        return
    
    messageToReply = GetSettingsMessageText(user)
    bot_messages.NewSendMessage(message.chat.id, messageToReply, markup_inline)

def GetSettingsMessageText(user : User):
    if (user == None):
        return 'Выберите роль.'
    
    if (user.IsTeacher()): 
        roleName = 'преподаватель'
        if (user.UserValidAsTeacher()):
            selectedRoleName = db.GetTeacherNameById(user.TeacherID())
        else:
            selectedRoleName = 'не найдено'
        prefixRole = 'ФИО'
        extraMessage = "ваше ФИО"
    else: 
        roleName = 'студент'
        if (user.UserValidAsStudent()):
            selectedRoleName = db.getGroupNameById(user.GroupID())
        else:
            selectedRoleName = 'не найдена'
        prefixRole = 'Группа'
        extraMessage = "вашу группу"
        
    if (user.SpamStatus()): spamStatus = "включено" 
    else: spamStatus = "выключено"
        
    messageToReply = '🧑‍💻Текущие настройки профиля:\n\n'
    messageToReply += f'Роль: {roleName}\n'
    messageToReply += f'{prefixRole}: {selectedRoleName}\n'
    messageToReply += f'Авторасписание: {spamStatus}\n'
    if(not user.UserValidAuto()):
        messageToReply += f'\n<strong>Пожалуйста, укажите {extraMessage}!</strong>\nДля дальнейшей работы бота это необходимо.'
    return messageToReply
    
@bot.callback_query_handler(func=lambda call: HistoryIsInTop(call.data, 'm_timetable'))
def handle_button_pressed(call):
    goToRaspisanie(call.message, 'Расписание.')

def c_group_callback_context(message, callback):
    callbackBack = HistoryPrevPage(callback)
    user = db.GetUserById(message.chat.id)
    item0 = types.InlineKeyboardButton(text = 'Назад', callback_data=callbackBack)
    item1 = types.InlineKeyboardButton(text = 'Первый курс', callback_data=HistoryGenerate(callback, 'f_course0'))
    item2 = types.InlineKeyboardButton(text = 'Второй курс', callback_data=HistoryGenerate(callback, 'f_course1'))
    item3 = types.InlineKeyboardButton(text = 'Третий курс', callback_data=HistoryGenerate(callback, 'f_course2'))
    item4 = types.InlineKeyboardButton(text = 'Четвертый курс', callback_data=HistoryGenerate(callback, 'f_course3'))
    
    markup_inline = types.InlineKeyboardMarkup()
    markup_inline.add(item0)
    markup_inline.add(item1, item2)
    markup_inline.add(item3, item4)
    
    if (user.UserValidAuto()):
        item6 = types.InlineKeyboardButton(text = 'Перейти к расписанию', callback_data=HistoryGenerateWithReset('m_timetable'))
        markup_inline.add(item6)
    
    if (user == None or user.GroupID() == None or user.GroupID() == 0):
        messageToReply = "Ваша группа не указана.\nВыберите свой курс:"
    else:
        messageToReply = f'Ваша группа: {db.getGroupNameById(user.GroupID())}\nВыберите свой курс:'
    return messageToReply, markup_inline

@bot.callback_query_handler(func=lambda call: HistoryIsInTop(call.data, 'c_group'))
def handle_button_pressed(call):
    message = call.message
    messageToReply, markup_inline = c_group_callback_context(message, call.data)
    bot_messages.NewEditMessage(message.chat.id, message.message_id, messageToReply, markup_inline)
    
def c_name_callback_context(message, callback):
    user = db.GetUserById(message.chat.id)
    callbackBack = HistoryPrevPage(callback)
    item0 = types.InlineKeyboardButton(text = 'Назад', callback_data=callbackBack)
    item1 = types.InlineKeyboardButton(text = 'Автоматический поиск', callback_data=HistoryGenerate(callback, 'f_name'))
    item2 = types.InlineKeyboardButton(text = 'Поиск по фамилии', callback_data=HistoryGenerate(callback, 'f_nlist0'))
    
    
    markup_inline = types.InlineKeyboardMarkup()
    markup_inline.add(item0)
    markup_inline.add(item1, item2)
    
    messageToReply = f'''Прикрепленное ФИО: {db.GetTeacherNameById(user.TeacherID())}
    
Если в вашем профиле Telegram присутствует ваша фамилия, то вы можете воспользоваться <em>"автоматическим поиском"</em>. 

В ином случае вы можете использовать <em>"поиск по фамилии"</em>, он предназначен для поиска пользователей по списку фамилий в алфавитном порядке.
'''
    return messageToReply, markup_inline 
        

@bot.callback_query_handler(func=lambda call: HistoryIsInTop(call.data, 'c_name'))
def handle_button_pressed(call):
    message = call.message
    messageToReply, markup_inline = c_name_callback_context(message, call.data)
    bot_messages.NewEditMessage(message.chat.id, message.message_id, messageToReply, markup_inline)

def sendSpamContext(call):
    message = call.message
    callbackBack = HistoryPrevPage(call.data)
    
    markup_inline = types.InlineKeyboardMarkup()
    itemBack = types.InlineKeyboardButton(text = 'Назад', callback_data=callbackBack)
    markup_inline.add(itemBack)
    
    messageToReply = 'Авторасписание'

    user = db.GetUserById(message.chat.id)
    if (user == None):
        messageToReply = "Для настройки авторасписания вам нужно зарегистрироваться в боте как студент или преподаватель."
        bot_messages.NewEditMessage(message.chat.id, message.message_id, messageToReply, markup_inline)
        return 
    
    
    if (user.SpamStatus()):
        messageToReply = "✅ Авторасписание включено." 
        item1 = types.InlineKeyboardButton(text = '❌ Отключить', callback_data=HistoryReplaceLastPage(call.data, f"s_spam0"))
        markup_inline.add(item1)
    else:
        messageToReply = "❌ Авторасписание выключено."
        item1 = types.InlineKeyboardButton(text = '✅ Включить', callback_data=HistoryReplaceLastPage(call.data, f"s_spam1"))
        markup_inline.add(item1)
    
    bot_messages.NewEditMessage(message.chat.id, message.message_id, messageToReply, markup_inline)

@bot.callback_query_handler(func=lambda call: HistoryIsInTop(call.data,'c_spam'))
def handle_button_pressed(call):
    sendSpamContext(call)

@bot.callback_query_handler(func=lambda call: HistoryIsInTop(call.data,'s_spam'))
def handle_button_pressed(call):
    message = call.message
    
    currentPage = HistoryCurrentPage(call.data)
    strLen = len(currentPage) - 1
    setSpam = int(currentPage[strLen:])
    
    user = db.GetUserById(message.chat.id)
    
    if (user != None):
        username = db.GetUsernameByMessage(message)
        db.AddToDb(user.UserID(), username, None, setSpam, None, None)
            
    sendSpamContext(call)



        
def getCourseYearDelta(courseId):
    isStudYearOver = datetime.now(pytz.timezone('Asia/Yekaterinburg')).month >= 7
    thisYear = datetime.now(pytz.timezone('Asia/Yekaterinburg')).year - courseId
    if (not isStudYearOver): thisYear -= 1
    return str(thisYear)[2:]

def createGroupSelectionButtons(courseId, call):
    dirNames = np.array(db.getGroupsDirName(courseId))
    
    markup_inline = types.InlineKeyboardMarkup()
    
    item_back = types.InlineKeyboardButton(text = 'Назад', callback_data=HistoryPrevPage(call.data))
    markup_inline.add(item_back)
    i = 0
    while(i < len(dirNames)):
        #groupId = db.groupchecker(f'{courseId}{dirNames[i]}')
        item1 = types.InlineKeyboardButton(text = dirNames[i], callback_data=HistoryGenerate(call.data, f'f_group_{courseId}{dirNames[i]}'))
        i += 1
        if (i == len(dirNames)):
            markup_inline.add(item1)
            continue
        
        item2 = types.InlineKeyboardButton(text = dirNames[i], callback_data= HistoryGenerate(call.data, f'f_group_{courseId}{dirNames[i]}'))
        i += 1
        if(i == len(dirNames)):
            markup_inline.add(item1, item2)
            continue
        
        item3 = types.InlineKeyboardButton(text = dirNames[i], callback_data= HistoryGenerate(call.data, f'f_group_{courseId}{dirNames[i]}'))
        markup_inline.add(item1, item2, item3)
        i += 1
        
    itemNotFound = types.InlineKeyboardButton(text = 'Здесь нет моей специальности', callback_data=HistoryGenerate(call.data, f'e_gr'))
    markup_inline.add(itemNotFound)
    return markup_inline
    
def shortcutGroupSelection(message, courseId):
    messageToReply = f"Ваш курс - {courseId + 1}, выберите свою специальность."
    courseId = getCourseYearDelta(courseId)
    markup_inline = createGroupSelectionButtons(courseId) # ERROR
    bot_messages.NewEditMessage(message.chat.id, message.message_id, messageToReply, markup_inline)

@bot.callback_query_handler(func=lambda call: HistoryIsInTop(call.data,'f_course'))
def handle_button_pressed(call):
    currentPage = HistoryCurrentPage(call.data)
    strLen = len(btnCallbackPrefix) + len('f_course')
    courseName = currentPage[strLen:]
    courseNum = int(courseName)
    message = call.message
    messageToReply = f"Ваш курс - {courseNum + 1}, выберите свою специальность."
    courseNum = getCourseYearDelta(courseNum)
    markup_inline = createGroupSelectionButtons(courseNum, call)
    bot_messages.NewEditMessage(message.chat.id, message.message_id, messageToReply, markup_inline)
    
@bot.callback_query_handler(func=lambda call: HistoryIsInTop(call.data, 'e_gr'))
def handle_button_pressed(call):
    markup_inline = types.InlineKeyboardMarkup()
    callbackBack = HistoryPrevPage(call.data)
    itemBack = types.InlineKeyboardButton(text = 'Назад', callback_data=callbackBack)
    markup_inline.add(itemBack)
    
    messageToReply = 'Перепроверьте свой курс и направление, если вы все еще не можете найти свою группу свяжитесь с <a href="https://vk.com/ptpitras" target="_blank">разработчиками</a>.'
    bot_messages.NewEditMessage(call.message.chat.id, call.message.message_id, messageToReply, markup_inline)


def searchForGroup(call):
    callbackLen = len('f_group_')
    courseId = call.data[callbackLen: callbackLen + 2]
    selectedGroup = call.data[callbackLen + 2:]
    
    callbackBack = HistoryPrevPage(call.data)
    markup_inline = types.InlineKeyboardMarkup()
    itemBack = types.InlineKeyboardButton(text = 'Назад', callback_data=callbackBack)
    markup_inline.add(itemBack)
    allGroups = np.array(db.getGroupListFilterByYear(courseId, selectedGroup)) # 19, СЗИ-1
    i = 0
    while(i < len(allGroups)):
        item1 = types.InlineKeyboardButton(text = allGroups[i], callback_data= HistoryGenerate(call.data, f's_group_{allGroups[i]}'))
        i += 1
        if (i == len(allGroups)):
            markup_inline.add(item1)
            continue
            
        item2 = types.InlineKeyboardButton(text = allGroups[i], callback_data= HistoryGenerate(call.data, f's_group_{allGroups[i]}'))
        markup_inline.add(item1, item2)
        i += 1
    itemNotFound = types.InlineKeyboardButton(text = 'Здесь нет моей группы', callback_data=HistoryGenerate(call.data, f'e_gr'))
    markup_inline.add(itemNotFound)
    
    messageToReply = "Выберите группу:"
    bot_messages.NewEditMessage(call.message.chat.id, call.message.message_id, messageToReply, markup_inline)
    
    
@bot.callback_query_handler(func=lambda call: HistoryIsInTop(call.data,'f_group'))
def handle_button_pressed(call):
    message = call.message
    callbackLen = len(btnCallbackPrefix) + len('f_group_')
    currentCallback = HistoryCurrentPage(call.data)
    courseId = currentCallback[callbackLen: callbackLen + 2]
    selectedGroup = currentCallback[callbackLen + 2:]
    callbackBack = HistoryPrevPage(call.data)
    
    markup_inline = types.InlineKeyboardMarkup()
    itemBack = types.InlineKeyboardButton(text = 'Назад', callback_data=callbackBack)
    markup_inline.add(itemBack)
    allGroups = np.array(db.getGroupListFilterByYear(courseId, selectedGroup)) # 19, СЗИ-1
    i = 0
    while(i < len(allGroups)):
        item1 = types.InlineKeyboardButton(text = allGroups[i], callback_data=HistoryGenerateWithReset(f's_groups_{db.getGroupIdByName(allGroups[i])}'))
        i += 1
        if (i != len(allGroups)):
            item2 = types.InlineKeyboardButton(text = allGroups[i], callback_data=HistoryGenerateWithReset(f's_groups_{db.getGroupIdByName(allGroups[i])}'))
            markup_inline.add(item1, item2)
        else:
            markup_inline.add(item1)
        i += 1
    itemNotFound = types.InlineKeyboardButton(text = 'Здесь нет моей группы', callback_data=HistoryGenerate(call.data, f'e_gr'))
    markup_inline.add(itemNotFound)
    
    messageToReply = "Выберите группу:"
    bot_messages.NewEditMessage(message.chat.id, message.message_id, messageToReply, markup_inline)
    
@bot.callback_query_handler(func=lambda call: HistoryIsInTop(call.data,'f_name'))
def handle_button_pressed(call):
    message = call.message
    callbackBack = HistoryPrevPage(call.data)
    
    userLastName = message.chat.last_name
    teacherList = db.GetTeacherNamesList()
    
    filteredList = list()
    if (userLastName != None and len(str(userLastName)) > 4):
        for item in teacherList:
            if (userLastName.lower() in item.lower()):
                filteredList.append(item)
    isFound = len(filteredList) > 0
    # isFound = userLastName != None and str(userLastName) in teacherList
    
    markup_inline = types.InlineKeyboardMarkup()
    itemBack = types.InlineKeyboardButton(text = 'Назад', callback_data=callbackBack)
    markup_inline.add(itemBack)
        
    # allGroups = np.array(db.getGroupListFilterByYear(courseId, selectedGroup))
    if (isFound):
        i = 0
        while(i < len(filteredList)):
            abd = db.GetTeacherIdByLastname(filteredList[i])
            dd = db.GetTeacherNameById(abd)
            item1 = types.InlineKeyboardButton(text = filteredList[i], callback_data=HistoryGenerateWithReset(f's_name_{abd}'))
            i += 1
            if (i != len(filteredList)):
                item2 = types.InlineKeyboardButton(text = filteredList[i], callback_data=HistoryGenerateWithReset(f's_name_{db.GetTeacherIdByLastname(filteredList[i])}'))
                markup_inline.add(item1, item2)
            else:
                markup_inline.add(item1)
            i += 1
    
    item2 = types.InlineKeyboardButton(text = 'Поиск по фамилии', callback_data=HistoryGenerate(call.data, 'f_nlist0'))
    if (isFound):
        messageToReply = "Если вашего имени здесь нет, попробуйте использовать <em>\"Поиск по фамилии\"</em>."
        markup_inline.add(item2)
    else:
        messageToReply = 'Профиль не найден, попробуйте изменить фамилию в Telegram и попробовать снова или используйте <em>"поиск по фамилии"</em>.'
    
        item1 = types.InlineKeyboardButton(text = 'Повторить поиск', callback_data=callbackBack)
        markup_inline.add(item1, item2)
    
    
    bot_messages.NewEditMessage(message.chat.id, message.message_id, messageToReply, markup_inline)
    
@bot.callback_query_handler(func=lambda call: HistoryIsInTop(call.data,'f_nlist'))
def handle_button_pressed(call):
    message = call.message
    callbackBack = HistoryPrevPage(call.data)
    
    currentPage = HistoryCurrentPage(call.data)
    strLen = len(currentPage) - 1
    pageName = currentPage[strLen:]
    pageNum = int(pageName)
    
    teacherList = db.GetTeacherNamesList()
    
    markup_inline = types.InlineKeyboardMarkup()
    itemBack = types.InlineKeyboardButton(text = 'Назад', callback_data=callbackBack)
    markup_inline.add(itemBack)
    
    itemLimit = 20
    startIndex = pageNum * itemLimit
    maxPages = int(len(teacherList) / itemLimit) + 1
    
    i = startIndex
    try:
        limit = min(startIndex + itemLimit, len(teacherList))
        while(i < limit):
            item1 = types.InlineKeyboardButton(text = teacherList[i], callback_data=HistoryGenerateWithReset(f's_name_{db.GetTeacherIdByLastname(teacherList[i])}'))
            i += 1
            if (i != limit):
                item2 = types.InlineKeyboardButton(text = teacherList[i], callback_data=HistoryGenerateWithReset(f's_name_{db.GetTeacherIdByLastname(teacherList[i])}'))
                markup_inline.add(item1, item2)
            else:
                markup_inline.add(item1)
            i += 1
    except Exception as e: PrintEx(e) 
    
    messageToReply = 'Нажмите на преподавателя, расписание которого вы хотели бы получать.'
    
    noPageAv = '----  X  ----'
    prevText = f'{max(1, pageNum)}        <-'
    pageText = f'[{pageNum + 1} / {maxPages}]'
    nextText = f'->        {min(maxPages, pageNum + 2)}'
    
    callbackEmpty = 'bebraaoaoaoaoao'
    callbackPrev = HistoryReplaceLastPage(call.data, f'f_nlist{max(0, pageNum - 1)}')
    callbackNext = HistoryReplaceLastPage(call.data, f'f_nlist{pageNum + 1}')
    
    if (pageNum == 0): 
        prevText = noPageAv
        callbackPrev = callbackEmpty
    if (pageNum == maxPages - 1): 
        nextText = noPageAv
        callbackNext = callbackEmpty
    
    item1 = types.InlineKeyboardButton(text = prevText, callback_data=callbackPrev)
    item2 = types.InlineKeyboardButton(text = pageText, callback_data=callbackEmpty)
    item3 = types.InlineKeyboardButton(text = nextText, callback_data=callbackNext)
    markup_inline.add(item1, item2, item3)
    #markup_inline.add(item1, item3)
    
    bot_messages.NewEditMessage(message.chat.id, message.message_id, messageToReply, markup_inline)

@bot.callback_query_handler(func=lambda call: HistoryIsInTop(call.data, 's_name'))
def handle_button_pressed(call):
    message = call.message
    callbackLen = len(btnCallbackPrefix) + len('s_name')
    teacherId = call.data[callbackLen + 1: ]
    
    markup_inline = types.InlineKeyboardMarkup()

    itemBack = types.InlineKeyboardButton(text = 'Изменить выбор', callback_data=HistoryGenerate(call.data, 'c_name'))
    itemRetry= types.InlineKeyboardButton(text = 'Настройки', callback_data=HistoryGenerateWithReset('m_settings'))

    markup_inline.add(itemBack)
    markup_inline.add(itemRetry)
    
    userId = message.chat.id
    username = db.GetUsernameByMessage(message)
    user = db.GetUserById(userId)
    if (teacherId == None or int(teacherId) < 1): return False
    if (db.AddToDb(userId, username, None, 1, 1, teacherId) == False):
        messageToReply = "Не удалось установить соединение, попробуйте позже."
    else:
        messageToReply = bot_messages.getTeacherSelectedMessage(teacherId, user.SpamStatus())
    
    if (user.UserValidAsTeacher()):
        item4 = types.InlineKeyboardButton(text = 'Перейти к расписанию', callback_data=HistoryGenerateWithReset('m_timetable'))
        markup_inline.add(item4)
    
    bot_messages.NewEditMessage(message.chat.id, message.message_id, messageToReply, markup_inline)


@bot.callback_query_handler(func=lambda call: HistoryIsInTop(call.data, 's_groups'))
def handle_button_pressed(call):
    message = call.message
    callbackLen = len(btnCallbackPrefix) + len('s_groups')
    groupId = call.data[callbackLen + 1: ]
    print(db.udb.Execute(f"SELECT * FROM {db.udb.tableName}")) 
    if (groupId == None or len(groupId) <= 1): return False
    
    
    callbackBack = HistoryPrevPage(call.data)
    userId = message.chat.id
    user = db.GetUserById(message.chat.id)
    username = db.GetUsernameByMessage(message)
    if (db.AddToDb(userId, username, groupId, 1, 0, None) == False):
        markup_inline = types.InlineKeyboardMarkup()
        itemBack = types.InlineKeyboardButton(text = 'Назад', callback_data=callbackBack)
        markup_inline.add(itemBack)
        #markup_inline.add(itemRetry)
        messageToReply = "Не удалось установить соединение, попробуйте позже."
        bot_messages.NewEditMessage(call.message.chat.id, call.message.message_id, messageToReply, markup_inline)
    else:
        markup_inline = types.InlineKeyboardMarkup()
        itemBack = types.InlineKeyboardButton(text = 'Выбрать другую группу', callback_data=HistoryGenerate(call.data, 'c_group'))
        itemRetry= types.InlineKeyboardButton(text = 'Настройки', callback_data=HistoryGenerateWithReset('m_settings'))
        markup_inline.add(itemBack)
        markup_inline.add(itemRetry)
        if (user.UserValidAuto()):
            item4 = types.InlineKeyboardButton(text = 'Перейти к расписанию', callback_data=HistoryGenerateWithReset('m_timetable'))
            markup_inline.add(item4)

        groupFullName = db.getGroupNameById(groupId)
        messageToReply = getGroupSelectedMessage(groupFullName, user.SpamStatus())
        bot_messages.NewEditMessage(call.message.chat.id, call.message.message_id, messageToReply, markup_inline)


#///////////////////////////////////////////////
def sendRoleContext(call):
    message = call.message
    callbackBack = HistoryPrevPage(call.data)
    
    markup_inline = types.InlineKeyboardMarkup()
    itemBack = types.InlineKeyboardButton(text = 'Назад', callback_data=callbackBack)
    markup_inline.add(itemBack)
    
    user = db.GetUserById(message.chat.id)
    if (user == None):
        username = db.GetUsernameByMessage(message)
        if (db.AddToDb(message.chat.id, username, None, 1, 0, None) == False):
            messageToReply = "Ошибка подключения. Повторите попытку позже."
            bot_messages.NewEditMessage(call.message.chat.id, call.message.message_id, messageToReply)
            return
    
    user = db.GetUserById(message.chat.id)
    if (user != None):
        if (user.IsTeacher()):
            messageToReply = "Выбрана роль: преподаватель." 
            item1 = types.InlineKeyboardButton(text = 'Стать студентом', callback_data=HistoryReplaceLastPage(call.data, f"s_role0"))
            markup_inline.add(item1)
        else:
            messageToReply = "Выбрана роль: студент."
            item1 = types.InlineKeyboardButton(text = 'Стать преподавателем', callback_data=HistoryReplaceLastPage(call.data, f"s_role1"))
            markup_inline.add(item1)
    else:
        messageToReply = "По неизвестной причине, вас не удается добавить в базу данных. Попробуйте снова - '/start'."
    
    bot_messages.NewEditMessage(message.chat.id, message.message_id, messageToReply, markup_inline)

@bot.callback_query_handler(func=lambda call: HistoryIsInTop(call.data,'c_role'))
def handle_button_pressed(call):
    sendRoleContext(call)

@bot.callback_query_handler(func=lambda call: HistoryIsInTop(call.data,'s_role'))
def handle_button_pressed(call):
    message = call.message
    
    currentPage = HistoryCurrentPage(call.data)
    strLen = len(currentPage) - 1
    setRole = int(currentPage[strLen:])
    
    user = db.GetUserById(message.chat.id)
    
    if (user != None):
        username = db.GetUsernameByMessage(message)
        db.AddToDb(message.chat.id, username, None, None, setRole, None)
            
    sendRoleContext(call)

@bot.callback_query_handler(func=lambda call: HistoryIsInTop(call.data,'m_register'))
def handle_button_pressed(call):
    message = call.message
    
    currentPage = HistoryCurrentPage(call.data)
    strLen = len(currentPage) - 1
    setRole = int(currentPage[strLen:])
    
    username = db.GetUsernameByMessage(message)
    if (db.AddToDb(message.chat.id, username, None, 1, setRole, None) == False):
        messageToReply = "Ошибка подключения. Повторите попытку позже."
        bot_messages.NewEditMessage(call.message.chat.id, call.message.message_id, messageToReply)
        return
    markup_inline = GetSettingsPageContent(call.message)
    messageToReply = GetSettingsMessageText(db.GetUserById(call.message.chat.id))
    bot_messages.NewEditMessage(call.message.chat.id, call.message.message_id, messageToReply, markup_inline)

@bot.message_handler(commands = ['start'])
def StartCommand(message):
    # user = db.GetUserById(message.chat.id)
    # if (user == None or True):
    # messageToReply = "Выберите роль:"
    markup_inline = types.InlineKeyboardMarkup()
    callHistory = 'm_settings'
    
    extraMsg = ""
    if (db.GetUserById(message.chat.id) == None):
        username = db.GetUsernameByMessage(message)
        if (db.AddToDb(message.chat.id, username, 0, 0, 0, 0) == False):
            extraMsg = "\n\nНе удается получить доступ к базе данных."
    
    item1 = types.InlineKeyboardButton(text = 'Преподаватель', callback_data=HistoryGenerate(callHistory, 'm_register1'))
    item2 = types.InlineKeyboardButton(text = 'Студент', callback_data=HistoryGenerate(callHistory, 'm_register0'))
    
    markup_inline.add(item1, item2)
    bot_messages.NewSendMessage(message.chat.id, f'{bot_messages.startMessage}{extraMsg}', markup_inline)
    # return
    
    # messageToReply = 'start'
    # bot_messages.NewSendMessage(message.chat.id, messageToReply)

def ThStartCommand(message):
    if ("начать" in message.text.lower() or "старт" in message.text.lower() or "start" in message.text.lower()):
        StartCommand(message) 

@bot.message_handler(commands = ['me'])
def GetMeCommand(message):
    if (db.IsUserTester(message.chat.id) == False):
        return
    
    user = db.GetUserById(message.chat.id)
    if (user == None):
        return
        
    messageToReply = f'''Пользователь: {str(user.Name())}
ID : {user.UserID()}

Номер группы: {user.GroupID()}
Рассылка: {user.SpamStatus()}
Роль учителя: {user.IsTeacher()}
Номер преподавателя: {user.TeacherID()}

/stats - для статистики'''
    bot_messages.NewSendMessage(message.chat.id, messageToReply)

@bot.message_handler(commands = ['time'])
def GetMeCommand(message):
    pairlist = pm.GetPairTimeList(date.today())
    messageToReply = "Расписание на сегодня:\n"
    for i in range(len(pairlist)):
        messageToReply += f"[{i}] {pairlist[i].GetFormat()}\n"
    bot_messages.NewSendMessage(message.chat.id, messageToReply)

@bot.message_handler(commands = ['stats'])
def GetStatsCommand(message):
    if (db.IsUserTester(message.chat.id) == False):
        return
    
    user = db.GetUserById(message.chat.id)
    if (user == None):
        return

    total = len(db.udb.Execute(f"SELECT * FROM {db.udb.tableName}"))
    enabled = len(db.udb.Execute(f"SELECT * FROM {db.udb.tableName} WHERE spam_status = 1"))
    teachers = len(db.udb.Execute(f"SELECT * FROM {db.udb.tableName} WHERE is_teacher = 1"))
    
    messageToReply = f'''Сообщений за сегодня: {db.todaySended}
Писали боту сегодня: {db.ulActiveDay.GetLen()}
Писали боту на этой неделе: {db.ulActiveWeek.GetLen()}
Последняя рассылка длилась: {db.lastSpamDuration} начиная с {db.lastSpamTime}

Всего {total} пользователей
Включена рассылка у {enabled}
Преподавателей {teachers}

Заблокировали бота: {db.ulBlocked.GetLen()}
/me - информация о юзере'''
    bot_messages.NewSendMessage(message.chat.id, messageToReply)
    
@bot.message_handler(commands = ['reset'])
def ResetCommand(message):
    if (db.IsUserTester(message.chat.id) == False):
        return
    
    if(not config.IsBotInDebug()):
        bot_messages.NewSendMessage(message.chat.id, 'Эту команду можно использовать только в отладке.')
        return
    
    user = db.GetUserById(message.chat.id)
    if (user == None):
        return
    
    db.AddToDb(message.chat.id, None, 0, 0, 0, 0)
    bot_messages.NewSendMessage(message.chat.id, 'Профиль сброшен.\n/me')

def GetUserInfo(message):
    messageToReply = "Вы не были найдены в списке."
    user = db.GetUserById(message.chat.id)
    if (user == None):
        return messageToReply
    messageToReply = f"👤Имя пользователя: {user.Name()}"
    messageToReply += f" [id {db.GetUidByChatId(message.chat.id)}]"
    
    if (user.IsStudent()):
        messageToReply += f"\n🕵️‍♀️Роль: студент"
        messageToReply += f"\n👷Группа {db.getGroupNameById(user.GroupID())}"
    else:
        messageToReply += f"\n🕵️‍♀️Роль: преподаватель"
        messageToReply += f"\n🧑‍💻ФИО {db.GetTeacherNameById(user.TeacherID())}"
    
    if (user.SpamStatus()):
        messageToReply += "\n✅Авторасписание включено\n" 
    else:
        messageToReply += "\n❌Авторасписание выключено\n"
        
    enabled = len(db.udb.Execute(f"SELECT * FROM {db.udb.tableName} WHERE spam_status = 1"))
    total = len(db.udb.Execute(f"SELECT * FROM {db.udb.tableName}"))

    messageToReply += f"\n🐝Всего {str(total)} пользователей (с рассылкой {str(enabled)})\n"
    return messageToReply

@bot.callback_query_handler(func=lambda call: HistoryIsInTop(call.data,'m_profile'))
def handle_button_pressed(call):
    message = call.message
    messageToReply = GetUserInfo(message)
    bot_messages.NewEditMessage(message.chat.id, call.message.message_id, messageToReply)

@bot.message_handler(commands = ['user', 'info', 'account', 'profile'])
def SendUserInfo(message):
    messageToReply = GetUserInfo(message)
    bot_messages.NewSendMessage(message.chat.id, messageToReply)

@bot.message_handler(commands = ['сегодня', ' сегодня', 'td', 'today'])
def SendToday(message):
    if (not db.GetUserById(message.chat.id).UserValidAuto()):
        bot_messages.NewSendMessage(message.chat.id, bot_messages.needToRegister)
        return
    messageToReply = pm.GetByDate(date.today(), message.chat.id, True)
    bot_messages.NewSendMessage(message.chat.id, messageToReply)

@bot.message_handler(commands = ['завтра', ' завтра', 'tm', 'tomorrow'])
def SendTomorrow(message):
    if (not db.GetUserById(message.chat.id).UserValidAuto()):
        bot_messages.NewSendMessage(message.chat.id, bot_messages.needToRegister)
        return
    
    messageToReply = pm.GetByDate((date.today() + timedelta(days=1)), message.chat.id, False)
    if (len(messageToReply) > 30):
        messageToReply = f"Завтра:\n{messageToReply}"
    bot_messages.NewSendMessage(message.chat.id, messageToReply)

@bot.message_handler(commands = ['вчера', ' вчера', 'yd', 'yesterday'])
def SendYesterday(message):
    
    if (not db.GetUserById(message.chat.id).UserValidAuto()):
        bot_messages.NewSendMessage(message.chat.id, bot_messages.needToRegister)
        return
    
    messageToReply = pm.GetByDate((date.today() - timedelta(days=1)), message.chat.id, False)
    if (len(messageToReply) > 30):
        messageToReply = f"Вчера:\n{messageToReply}"
    bot_messages.NewSendMessage(message.chat.id, messageToReply)

@bot.message_handler(commands = ['help', 'menu', 'помощь', 'меню'])
def HelpCommand(message):
    markup_inline = types.InlineKeyboardMarkup()
    
    item0 = types.InlineKeyboardButton(text = 'Настройки', callback_data=HistoryGenerateWithReset('m_settings'))
    item1 = types.InlineKeyboardButton(text = 'Профиль', callback_data=HistoryGenerateWithReset('m_profile'))
    markup_inline.add(item0, item1)
        
    bot_messages.NewSendMessage(message.chat.id, bot_messages.helpMessage, markup_inline)

@bot.message_handler(commands = ['group'])
def ChangeGroupCommand(message):
    # textCommand = message.text.lower().split(' ', 1)
    # if (len(textCommand) > 1):
    #     textCommand = textCommand[1]
    # else: textCommand = None
    messageToReply, markup_inline = c_group_callback_context(message, HistoryGenerateWithReset('m_settings'))
    bot_messages.NewSendMessage(message.chat.id, messageToReply, markup_inline)

@bot.message_handler(commands = ['name', 'teacher'])
def ChangeNameCommand(message):
    # textCommand = message.text.lower().split(' ', 1)
    # if (len(textCommand) > 1):
    #     textCommand = textCommand[1]
    # else: textCommand = None
    messageToReply, markup_inline = c_name_callback_context(message, HistoryGenerateWithReset('m_settings'))
    bot_messages.NewSendMessage(message.chat.id, messageToReply, markup_inline)

#c_role
#c_spam

def ThHelpCommand(message):
    if ("помо" in message.text.lower() or "глав" in message.text.lower()):
        HelpCommand(message)

def ThViolentWords(message):
    for word in np.array(config.ViolentWords):
        if word in message.text.lower():
            try:
                bot.send_sticker(message.chat.id, config.SwearStr[randrange(3)])
            except telebot.apihelper.ApiException as e:
                pass

def ThOtherCommands(message):
    if(handleDayTextAnswer(message)): 
        return
    
    if ("распис" in message.text.lower()):
        goToRaspisanie(message, "Расписание") 
        return
    
    if("дал" in message.text.lower() or "след" in message.text.lower() or "куд" in message.text.lower()):
        if (bot_messages.SendTimeTable(message.chat.id, True) == False):
            bot_messages.NewSendMessage(message.chat.id, "Пар нет, отдыхаем. 😎")
        return 
    
    # TODO: Возможно стоит сделать разные команды на /now, /next, /best
    # if("сей" in message.text.lower()):
    #     if (bot_messages.SendTimeTable(message.chat.id, False) == False):
    #         bot_messages.NewSendMessage(message.chat.id, "Пары не найдены.")
    #     return

@bot.message_handler(content_types = ['text'])
def TextAnswer(message):
    try:
        print(f'Get message from {db.GetUsernameByMessage(message)}')
    except: pass
    
    ThStartCommand(message) 
    ThHelpCommand(message)
    ThViolentWords(message)  
    ThOtherCommands(message)
    
def raspisanieButtons():
    markup_inline = types.ReplyKeyboardMarkup(resize_keyboard=True)
    itemTd = types.KeyboardButton(text = 'Сегодня')
    itemTm = types.KeyboardButton(text = 'Завтра')
    item1 = types.KeyboardButton(text = 'Понедельник')
    item2 = types.KeyboardButton(text = 'Вторник')
    item3 = types.KeyboardButton(text = 'Среда')
    item4 = types.KeyboardButton(text = 'Четверг')
    item5 = types.KeyboardButton(text = 'Пятница')
    item6 = types.KeyboardButton(text = 'Суббота')
    itemHelp = types.KeyboardButton(text = 'Помощь')
    itemNext = types.KeyboardButton(text = 'Куда идти?')

    markup_inline.add(itemTd, itemTm)
    markup_inline.add(item1, item2, item3)
    markup_inline.add(item4, item5, item6)
    markup_inline.add(itemHelp, itemNext)
    return markup_inline

# КРАФТ КНОПОК НА НЕДЕЛЮ
def goToRaspisanie(message, msgText):
    if (db.GetUserById(message.chat.id) == None):
        return
    markup_inline = raspisanieButtons()
    messageToReply = msgText
    bot_messages.NewSendMessage(message.chat.id, messageToReply, markup_inline)

# РЕЗУЛЬТАТ РАСПИСАНИЕ НА ДЕНЬ
def handleDayTextAnswer(message):

    if ("сегодня" in message.text.lower()):
        SendToday(message)
        return True
    elif ("завтра" in message.text.lower()):
        SendTomorrow(message)
        return True
    elif ("вчера" in message.text.lower()):
        SendYesterday(message)
        return True
    
    dArray = np.array(dayArray)
    lowerMsg = message.text.lower()

    for targetWeekDay in range(len(dArray)):
        if (dArray[targetWeekDay] not in lowerMsg): continue
        
        if (targetWeekDay == 6):    
            bot_messages.NewSendMessage(message.chat.id, "Воскресенье? 🗿")
            return True
        
        todayWeekday = date.today().weekday()
        
        dayDelta = ((targetWeekDay + 7 - todayWeekday) % 7)
        
        if (dayDelta < 3):
            messageToReply = ["Сегодня\n", "Завтра\n", "Послезавтра\n"][dayDelta]
        else:
            messageToReply = f"Осталось {dayDelta} {dayCompareArray[dayDelta-1]}\n"
        
        messageToReply += pm.GetByDate((date.today() + timedelta(days=dayDelta)), message.chat.id, False)
        bot_messages.NewSendMessage(message.chat.id, messageToReply)
        return True
    return False