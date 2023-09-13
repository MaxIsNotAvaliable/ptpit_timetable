
class UserList:
    global __list
    
    def __init__(self) -> None:
        self.__list = []
    
    def IsInList(self, uid):
        if (uid in self.__list):
            return True
        return False

    def AddUser(self, uid):
        try:
            if (uid not in self.__list):
                self.__list.append(uid)
        except:
            return False
        return True

    def ResetUserList(self):
        self.__list.clear()
        
    def GetLen(self):
        return len(self.__list)
    
    
    
    