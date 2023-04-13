TOKEN_RELEASE   =    'token1'
TOKEN_DEBUG     =    'token2'

TOKEN = TOKEN_DEBUG

def IsBotInDebug():
    return TOKEN==TOKEN_DEBUG

alphabet = ["а","б","в","г","д","е","ё","ж","з","и","й","к","л","м","н","о","п","р","с","т","у","ф","х","ц","ч","ш","щ","ъ","ы","ь","э","ю","я"]

testers = [
# uid
]

user_agent = "ua"
tgbot_url = "bd"
bd_request = f"{tgbot_url}/1"
bd_url = f"{tgbot_url}/2"

table_name = "users_test"

class pair:
    Name = "Пары нет"
    Num : int
    TableID : int
    Room: int
    Subgroup : int
    Moodle = ""
    GroupName = ""
    TeacherName = ""
    
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
        
class DirName:
    uid : int
    courseYr : str
        
SwearStr = [
    'CAACAgEAAxkBAAICP2G3TPdddbdf0oLGyu9oT2Zbz7ORAAJuIwACePzGBZ8lB6a5wmkiIwQ',
    'CAACAgEAAxkBAAICQWG3TQWFxQzmz20PSoxWsdSCGlBYAAJpIwACePzGBQ9aaXLhnDlgIwQ',
    'CAACAgEAAxkBAAICS2G3TdW-2GmM0SbKrvlismlWmIZ7AAJ8IwACePzGBTUyksOCqNigIwQ',
]
ViolentWords = [
    'гей',
    'говно',
    'ужс',
    'ужас',
    'плохо',
    'дерьмо',
]
