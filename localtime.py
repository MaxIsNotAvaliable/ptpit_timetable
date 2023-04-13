from datetime import datetime

import pytz
import config

def GetLocalTime():
    timeNow = datetime.strptime(datetime.now(pytz.timezone('Asia/Yekaterinburg')).strftime("%H:%M:%S"),"%H:%M:%S")
    if(config.IsBotInDebug()):
        # timeNow = datetime.strptime("9:59","%H:%M")
        # print(f"USING DEBUG TIME -> CHECK \"localtime.py\" -> {timeNow}")
        pass
    return timeNow