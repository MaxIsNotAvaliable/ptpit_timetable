import config
import userslist
from cached import CachedData
from printer import PrintEx

import threading
import json
import requests
import re
from datetime import datetime
import numpy as np
import os
from os import path
import sqlite3
from datetime import datetime


mutex = threading.Lock()

class Database:
  # db file info
  filename = 'database\\base.db'
  dbPath = path.join(path.dirname(__file__), filename)
  __isTableExist = False
  # db info
  tableName = 'usersTable'

  struct = '''id INTEGER PRIMARY KEY AUTOINCREMENT, 
  user_id BIGINT(255),
  username TEXT,
  group_id INTEGER,
  spam_status INTEGER,
  is_teacher INTEGER,
  teacher_id INTEGER
'''

  # access
  cursor : sqlite3.Cursor
  conn : sqlite3.Connection

  # status
  #initialized = False
  connected = False
  
  def Connect(self) -> None:
    directory = path.dirname(self.dbPath)
    if not os.path.exists(directory):
        os.makedirs(directory)
    self.conn = sqlite3.connect(self.dbPath, check_same_thread=False)
    self.connected = True

  def Disconnect(self) -> None:
    self.conn.close()
    self.connected = False

  def __TableExists(self) -> bool:
    if (not self.__isTableExist):
        self.cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{self.tableName}'")
        self.__isTableExist = self.cursor.fetchone()
    return self.__isTableExist
     
  def IsTableExists(self) -> bool: 
    mutex.acquire()
    result = None

    try:
        self.__TableExists()
    except Exception as e:
        PrintEx(e)
        mutex.release()

    mutex.release()
    return result
    
  def Execute(self, request : str):
    mutex.acquire()
    result = None

    try:
        self.cursor.execute(request)
        self.conn.commit()
        result = self.cursor.fetchall()
    except Exception as e:
        PrintEx(e)

    mutex.release()
    return result
    #return self.cursor.fetchone()
  
  def __init__(self) -> None:
    mutex.acquire()
    try:
        self.Connect()
        self.cursor = self.conn.cursor()
        if (not self.__TableExists()):
            self.cursor.execute(f'CREATE TABLE {self.tableName} ({self.struct})')
        #self.initialized = True
    except Exception as e:
        PrintEx(e)
        #print(f'Unable to initialize database {e}')
    mutex.release()

class UserDatabase (Database): 
  def __Insert(self, uid, username, gid, is_spam, is_teacher, teacher_id):
    if (uid == None): return

    if (gid == None): gid = 0
    if (is_spam == None): is_spam = 0
    if (is_teacher == None): is_teacher = 0
    if (teacher_id == None): teacher_id = 0


    values = []
    values2 = []

    values.append("user_id")
    values2.append(str(uid))

    if username is not None:
      values.append("username")
      values2.append(f"'{username}'")
    if gid is not None:
      values.append("group_id")
      values2.append(f"{gid}")
    if is_spam is not None:
      values.append("spam_status")
      values2.append(f"{is_spam}")
    if is_teacher is not None:
      values.append("is_teacher")
      values2.append(f"{is_teacher}")
    if teacher_id is not None:
      values.append("teacher_id")
      values2.append(f"{teacher_id}")

    reqNames = ', '.join(values)
    reqValues = ', '.join(values2)

    s = f"""INSERT INTO {self.tableName} ({reqNames}) VALUES ({reqValues})""".replace('\n', '')
    self.Execute(s)

  def Delete(self, uid : int):
    self.Execute(f"DELETE FROM {self.tableName} WHERE user_id={uid}")

  def __Update(self, uid, username, gid, is_spam, is_teacher, teacher_id):
    if (uid == None): return
    
    values = []
    if username is not None:
      values.append(f"username = '{username}'")
    if gid is not None:
      values.append(f"group_id = {gid}")
    if is_spam is not None:
      values.append(f"spam_status = {is_spam}")
    if is_teacher is not None:
      values.append(f"is_teacher = {is_teacher}")
    if teacher_id is not None:
      values.append(f"teacher_id = {teacher_id}")

    s = ', '.join(values)
    s = f"UPDATE {self.tableName} SET {s} WHERE user_id = {uid}"

    self.Execute(s)

  def Add(self, uid, username = '#Unknown-user', gid = 0, is_spam = 0, is_teacher = 0, teacher_id = 0):
    if (self.IsUserExist(uid)):
      self.__Update(uid, username, gid, is_spam, is_teacher, teacher_id)
    else:
      self.__Insert(uid=uid, username=username, gid=gid, is_spam=is_spam, is_teacher=is_teacher, teacher_id=teacher_id)

  def GetUser(self, uid):
    return self.Execute(f"SELECT * FROM {self.tableName} WHERE user_id = '{uid}'")
  
  def IsUserExist(self, uid):
    user = self.GetUser(uid)
    return user != None and len(user) > 0
  
udb = UserDatabase()
def BotSetup():
    SetUpdateDate()
    GetTimeTableUrl()

def BotDestroy():
    udb.Disconnect()

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
    except Exception as e:
        PrintEx(e)
    
    try:
        requests.get(extraTimeTableUrl)
        timeTableUrlCached = extraTimeTableUrl
        print("Timetable from extra url")
        return
    except Exception as e:
        PrintEx(e)
    
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

dateOfLastUpdate = 'None'
def SetUpdateDate():
    try:
        global dateOfLastUpdate 
        dateOfLastUpdate = datetime.fromtimestamp(os.path.getmtime('main.py')).strftime('%d.%m.%Y %H:%M:%S')
    except:
        return False
    return True

def GetUpdateDate():
    global dateOfLastUpdate 
    return dateOfLastUpdate

class User:    
    data = None
    
    __username = ''
    __dbid = 0
    __uid = 0
    __gid = 0
    __tid = 0
    __spam_status = False
    __is_teacher = False
    
    def Name(self): return self.__username
    def DBID(self): return self.__dbid
    def UserID(self): return self.__uid
    def GroupID(self): return self.__gid
    def TeacherID(self): return self.__tid
    def SpamStatus(self): return self.__spam_status
    def IsTeacher(self): return self.__is_teacher
    def IsStudent(self): return not self.__is_teacher
    
    def __ctor(self, userInfo) -> None:
        user = userInfo
        if (user == None): return
        self.data = user
        self.__fill()
        
    
    def __init__(self, userInfo = None) -> None:
        if (userInfo == None): return
        self.__ctor(userInfo)

    def __fill(self):
        try:
            self.__dbid = int(self.data[0])
            self.__uid = int(self.data[1])
            self.__username = self.data[2]
            self.__gid = int(self.data[3])
            self.__spam_status = self.data[4] == 1
            self.__is_teacher = self.data[5] == 1
            self.__tid = int(self.data[6])
        except Exception as e:
            PrintEx(e)


    def ParseMessage(self, message) -> None:
        self.__ctor(message.chat.id)    
        
    def ParseCall(self, call) -> None:
        self.__ctor(call.message.chat.id)    
    
    
    def UserValidAsStudent(self) -> bool:
        if (self.data == None): return False
        if (self.__gid == 0): return False
        return True
    
    def UserValidAsTeacher(self) -> bool:
        if (self.data == None): return False
        if (self.__tid == 0): return False
        return True
    
    def UserValidAuto(self) -> bool:
        if (self.data == None): return False
        if (self.__is_teacher): return self.UserValidAsTeacher()
        else: return self.UserValidAsStudent()

    def UserValidAny(self) -> bool:
        if (self.data == None): return False
        return self.UserValidAsTeacher() or self.UserValidAsStudent()

    def IsTester(self) -> bool:
        return self.__uid in config.testers

def GetUserById(uid):
    u = udb.GetUser(uid)
    if (len(u) == 0): 
        return None
    return User(u[0])

#returns index (data base id)
def GetUidByChatId(uid):
    return GetUserById(uid).DBID()
                
def IsUserTester(uid):
    return uid in config.testers
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

def AddToDb(uid, username, gid, isspam, is_teacher, teacher_id):
    print('add user')
    udb.Add(uid=uid, username=username, gid=gid, is_spam=isspam, is_teacher=is_teacher, teacher_id=teacher_id)
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

# def getGroupsDirectionName():
#     reqgroup = cachedGroupsJson.GetCachedData()
#     jsonResponse = np.array(reqgroup.json())
#     todaycheck = datetime.now().strftime('%Y-%m-%d')
#     waylist = list()
#     for currentGroup in jsonResponse:
#         name = currentGroup['name']
#         if(todaycheck < currentGroup['end_date']):
#             name = name[2:]
#             intfound = re.findall("[0-9]+", name)
#             ret_index = name.find(''.join(intfound))
#             set_name = name[:ret_index:].replace("-", "")
#             waylist.append(set_name)
#         waylist = list(set(waylist))
#     waylist.sort()
#     return waylist

def getGroupsDirName(startYear):
    reqgroup = cachedGroupsJson.GetCachedData()
    jsonResponse = np.array(reqgroup.json())
    todaycheck = datetime.now().strftime('%Y-%m-%d')
    waylist = list()
    for currentGroup in jsonResponse:
        year = currentGroup['name'][:2]
        if(year == startYear and todaycheck < currentGroup['end_date']):
            name = currentGroup['name'][2:]
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
    
ulBlocked = userslist.UserList()
ulActiveDay = userslist.UserList()
ulActiveWeek = userslist.UserList()
todaySended = 0
lastSpamTime = None
lastSpamDuration = "None"