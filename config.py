# Для того чтобы поднять бота можно переписать базу (database.py) и файл конфига или заполнить данные своего сервера.



# Для отладки бота, без прерываний его работы, использовались 2 отдельных бота в телеграм.
# Получить токен можно у bot father.
TOKEN_RELEASE   =    'token1'
TOKEN_DEBUG     =    'token2'

TOKEN = TOKEN_DEBUG

def IsBotInDebug():
    return TOKEN==TOKEN_DEBUG

alphabet = ["а","б","в","г","д","е","ё","ж","з","и","й","к","л","м","н","о","п","р","с","т","у","ф","х","ц","ч","ш","щ","ъ","ы","ь","э","ю","я"]

# Здесь был список админов бота. Он был сделан в целях отладки и просмотра статистики.
# Айди пользователей брался из message.chat.id.
testers = [
# uid
]

# Бот имел собственную базу данных на отдельном сервере и для доступа к базе был написан интерфейс на php.
user_agent = "ua"
# tgbot_url - представляло собой основную ссылку для отправки запросов.
tgbot_url = "your_database.com/bot"
# bd_request - запрос для получения базы данных в json формате.
bd_request = f"{tgbot_url}/get"
# bd_url - запрос для отправки данных на сервер.
bd_url = f"{tgbot_url}/send"


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

# Это чисто в рофл скрафчено было, бот отвечал стикерами, если в сообщении пользователя было что-то из ViolentWords.
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
