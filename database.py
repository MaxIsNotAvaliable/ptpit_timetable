import config
from config import DirName
import json
import requests
import re
from datetime import datetime
import numpy as np
import userslist
from cached import CachedData
import os
from datetime import datetime

def BotSetup():
    SetUpdateDate()
    UpdateLocalTable()
    GetTimeTableUrl()

mainTimeTableUrl = "https://api.ptpit.ru"
extraTimeTableUrl = "http://46.146.221.190" 

timeTableUrlCached = None

def CacheTimeTableUrl():
    global timeTableUrlCached
    try:
        requests.get(mainTimeTableUrl)
        timeTableUrlCached = mainTimeTableUrl
        print("Timetable from main url")
        return 
    except:
        pass
    
    try:
        requests.get(extraTimeTableUrl)
        timeTableUrlCached = extraTimeTableUrl
        print("Timetable from extra url")
        return
    except:
        pass
    
def HandlePtpitUrl():
    while(True):
        try:
            CacheTimeTableUrl()
            #time.sleep(300)
        except: pass
    
def GetTimeTableUrl():
    global timeTableUrlCached
    if (timeTableUrlCached == None): CacheTimeTableUrl()
    return timeTableUrlCached

# Простое кэширования для того чтобы не отправлять каждый раз запрос на сервер.
DataBaseTable = None
def UpdateLocalTable():
    try:
        global DataBaseTable 
        DataBaseTable = json.loads("[" + requests.get(config.bd_request, headers = {'user-agent': config.user_agent}).text.replace("}{","},{") + "]")
    except:
        return False
    return True

dateOfLastUpdate = 'None'
def SetUpdateDate():
    try:
        global dateOfLastUpdate 
        dateOfLastUpdate = datetime.fromtimestamp(os.path.getmtime('main.py')).strftime('%d.%m.%Y')
    except:
        return False
    return True

def GetUpdateDate():
    global dateOfLastUpdate 
    return dateOfLastUpdate

def UserValidAsStudent(user) -> bool:
    if (user == None): return False
    if (user['groupid'] == None): return False
    if (user['groupid'] == '0'): return False
    return True

def UserValidAsTeacher(user) -> bool:
    if (user == None): return False
    if (user['teacher_id'] == None): return False
    if (user['teacher_id'] == '0'): return False
    return True

def UserValidAuto(user) -> bool:
    if (user == None): return False
    if (user['is_teacher'] == '0'): return UserValidAsStudent(user)
    else: return UserValidAsTeacher(user)

def GetUserById(uid):
    if (DataBaseTable != None):
        for row in np.array(DataBaseTable):
            if ( str(row["user_id"]) == str(uid)):
                return row
    return None

def GetUidByChatId(uid):
    if (DataBaseTable != None):
        for row in range(len(np.array(DataBaseTable))):
            if ( str(DataBaseTable[row]["user_id"]) == str(uid)):
                return row
    return None
                
def IsUserTester(uid):
    for id in config.testers:
        if (id == uid):
            return True
    return False

def GetTesters():
    return config.testers

def GetUsernameByMessage(message):
    username = message.chat.username
    if (message.chat.username == None):
        username = message.chat.first_name
        if (message.chat.last_name != None):
            username = f"{username}_{message.chat.last_name}"
    return username


# Основной метод, использовавшийся для отправки запроса на сервер.
# БД на сервере состояла из:
#
# id : bigint(255)
# username : text
# groupid : int
# spam_stats : int
# is_teacher : tinyint
# teacher_id : int
#
def AddToDb(uid, username, gid, isspam, is_teacher, teacher_id):
    print('add user')
    try:
        user = GetUserById(uid)
        if (user == None and username == None):
            username = 'UNKNOWN_USER'
        else:
            if (username == None):
                username = user["username"]
            if (gid == None):
                gid = user["groupid"]
            if (isspam == None):
                isspam = user["spam_stats"]
            if (is_teacher == None):
                is_teacher = user["is_teacher"]
            if (teacher_id == None):
                teacher_id = user["teacher_id"]
        link = f"{config.bd_url}?id={uid}&username={username}&groupid={gid}&stats={isspam}&is_teacher={is_teacher}&teacher_id={teacher_id}".replace('None', '0')
        requests.get(link, headers = {'user-agent': config.user_agent})
        UpdateLocalTable() # Кэширования данных.
    except:
        return False
    return True

# group

cachedGroupsJson = CachedData(lambdaFunc=lambda : f'{GetTimeTableUrl()}/groups')

def groupchecker(grpName : str):
    try:
        grpName = grpName.replace("-", "").replace(" ", "")
        reqgroup = cachedGroupsJson.GetCachedData()
        jsonResponse = np.array(reqgroup.json())
        for i in range(len(jsonResponse)):
            name = jsonResponse[i]['name']
            id_gr = jsonResponse[i]['id']
            if(name.lower() == grpName.lower()):
                return str(id_gr)
    except:
        pass
    
def getGroupNameById(grpId : int):
    reqgroup = cachedGroupsJson.GetCachedData()
    jsonResponse = np.array(reqgroup.json())
    todaycheck = datetime.now().strftime('%Y-%m-%d')
    
    for item in jsonResponse:
        if (item['end_date'] > todaycheck and str(grpId) == str(item['id'])):
            return str(item['name'])
    return "не найдена"

def getGroupIdByName(grpName : str):
    reqgroup = cachedGroupsJson.GetCachedData()
    jsonResponse = np.array(reqgroup.json())
    for item in jsonResponse:
        if (grpName.lower() in str(item['name']).lower()):
            return item['id']
    return 0
    
def getGroupFullName(grpName : str):
    groupId = groupchecker(grpName)
    reqgroup = cachedGroupsJson.GetCachedData()
    jsonResponse = np.array(reqgroup.json())
    for item in jsonResponse:
        if(groupId != None and int(groupId) == int(item['id'])):
            return str(item['name'])
        
def getGroupList():
    groupList = list()
    reqgroup = cachedGroupsJson.GetCachedData()
    reqgroup.raise_for_status()
    jsonResponse = np.array(reqgroup.json())
    for item in jsonResponse:
        name = item['name']
        groupList.append(name)
    return groupList
        
def getGroupListFilterByYear(startedYear : str, filterByName = None):
    groupList = np.array(getGroupList())
    listFiltered = list()
    for item in groupList:
        check = item[0] + item[1]
        if (check != startedYear):
            continue
        if (filterByName == None):
            listFiltered.append(item)
        else:
            name = item[2:]
            intfound = re.findall("[0-9]+", name)
            ret_index = name.find(''.join(intfound))
            set_name = name[:ret_index:].replace("-", "")
            if (set_name.lower() == filterByName.lower()):
                listFiltered.append(item)
    return listFiltered

def getGroupsDirectionName():
    reqgroup = cachedGroupsJson.GetCachedData()
    jsonResponse = np.array(reqgroup.json())
    todaycheck = datetime.now().strftime('%Y-%m-%d')
    waylist = list()
    for res in jsonResponse:
        name = res['name']
        if(res['end_date'] > todaycheck):
            name = name[2:]
            intfound = re.findall("[0-9]+", name)
            ret_index = name.find(''.join(intfound))
            set_name = name[:ret_index:].replace("-", "")
            waylist.append(set_name)
        waylist = list(set(waylist))
    waylist.sort()
    return waylist



teachersJson = None

cachedTeachersJson = CachedData(lambdaFunc=lambda : f'{GetTimeTableUrl()}/persons/teachers')

def GetTeacherList():
    reqteacher = cachedTeachersJson.GetCachedData()
    jsonResponse = np.array(reqteacher.json())
    waylist = list()
    for res in jsonResponse:
        if(res['is_teacher'] == True):
            waylist.append(res)
    waylist = sorted(waylist, key=lambda x: x["name"])
    return waylist

def GetTeacherNamesList():
    reqteacher = cachedTeachersJson.GetCachedData()
    jsonResponse = np.array(reqteacher.json())
    waylist = list()
    for res in jsonResponse:
        if(res['is_teacher'] == True):
            waylist.append(res['name'])
    waylist.sort()
    return waylist

def GetTeacherById(id : str):
    teacherList = GetTeacherList()
    for teacher in teacherList:
        if (str(teacher['id']) == id):
            return teacher
        
def GetTeacherIdByLastname(lastname : str):
    teacherList = GetTeacherList()
    for teacher in teacherList:
        if (lastname in teacher['name']):
            return teacher['id']
    return None
        
def GetTeacherNameById(id : str):
    teacher = GetTeacherById(id)
    if (teacher == None): return 'не найдено'
    return teacher['name']
    
selectedDirNameArr = list()

def updateSelectedDirList(uid, courseYear : str, isDelete = False):
    dName = DirName
    dName.uid = uid
    dName.courseYr = courseYear
    if (isDelete):
        for i in range(len(selectedDirNameArr)):
            if (uid == selectedDirNameArr[i].uid):
                selectedDirNameArr.pop(i)
                return
    for elem in selectedDirNameArr:
        if (elem == dName):
            elem.courseYr = courseYear
            break
    else:
        selectedDirNameArr.append(dName)
        
def getSelectedDirList(uid):
    for elem in selectedDirNameArr:
        if (elem.uid == uid):
            return elem.courseYr

ulBlocked = userslist.UserList()
ulActiveDay = userslist.UserList()
ulActiveWeek = userslist.UserList()
todaySended = 0
