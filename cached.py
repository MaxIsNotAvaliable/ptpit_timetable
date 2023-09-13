import requests

class CachedData:
    global __data
    global __url
    global __lambda
    
    instances = [] 
    def UpdateAll():
        for item in CachedData.instances:
            item.UpdateCache()
    
    def __init__(self, url = None, lambdaFunc = None) -> None:
        if (lambdaFunc != None):
            self.__lambda = lambdaFunc
        else:
            self.__url = url
        self.UpdateCache()
        self.__class__.instances.append(self)
    
    def __del__(self):
        self.__class__.instances.remove(self)
        
    def GetUrl(self):
        if (self.__lambda != None):
            return self.__lambda()
        else:
            return self.__url
        
    def UpdateCache(self):
        url = self.GetUrl()
        
        try:
            self.__data = requests.get(url)
            self.__data.raise_for_status()
        except: pass
        
    def GetCachedData(self):
        if (self.__data == None): self.UpdateCache()
        return self.__data