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
import getmac
import getpass
import socket
import json
import win32api, win32con
from ctypes import windll
import time

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

    def send_screenshot(self, computer_id):
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
                raw_bytes = mss.tools.to_png(im.rgb, im.size, level=7)
                if raw_bytes != prev_img:
                    requests.post(SERVER_URL + '/get_file' + computer_id, data=raw_bytes,
                                  headers={'Content-Type': 'application/octet-stream'})
                prev_img = raw_bytes


class SendToServer:
    def __init__(self, send_request_to):
        self.send_request_to = send_request_to

    def send_computer_details(self, running_proc, com_history):
        """send the data of the computer (without the screenshot)
        running_proc -- the object of the class "ProcessDetails"
        """
        while True:
            requests.post(self.send_request_to, json={"running processes": running_proc.get_running_processes()[0], "chrome history": com_history.get_chrome_history()})
            sleep(5)  # sending the data every 5 seconds so I wouldn't DDOS myself


class GetHistory:
    def __init__(self):
        pass

    def get_chrome_history(self):
        ###
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
        chrome_hisory = []
        for url in urls:
            show_rec_10 = show_rec_10 + 1
            if show_rec_10 <= 10:
                if str(url).find("chrome-extension") == -1: # the user dosen't search extensions. Sometimes chrome logs it.
                    chrome_hisory.append(url)
        return chrome_hisory

    def get_dns_records(self):
        """TD if I find it necessary"""
        pass


class ComputerAction:
    def __init__(self):
        self.s = socket.socket()
        port = 12345 
        self.s.connect(('127.0.0.1', port))
    
    def click(self, x, y):
        win32api.SetCursorPos((x,y))
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN,x,y,0,0)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP,x,y,0,0)

    def check_mouse_click(self):
        while True:
            server_command = self.s.recv(1024)
            try:
                pos = json.loads(server_command.decode())
                print(pos)
                pos_x = int(pos[0])
                pos_y = int(pos[1])
                self.click(pos_x, pos_y)
            except:
                lock_or_not = server_command.decode()
                print(lock_or_not)
                if lock_or_not == "Lock":
                    windll.user32.BlockInput(True)
                else:
                    windll.user32.BlockInput(False)


def computer_mac_address():
    return getmac.get_mac_address()

def main():
    status_code = 200
    address_link = 'http://admin-monitor.herokuapp.com/computers/verify_login'
    response = requests.get(address_link)
    status_code = response.status_code
    print(status_code)
    computer_id = ""
    send_request_to = ""
    print(computer_mac_address())
    if status_code == 200:
        send_request_to = "http://admin-monitor.herokuapp.com/computers"
        req_id = requests.post('http://admin-monitor.herokuapp.com/computers/verify_login',
                            json={"mac_address": computer_mac_address()})
        computer_id = req_id.content.decode()
        print("computer id: " + computer_id)
        print(type(computer_id))
        if computer_id != "":
            send_request_to = send_request_to + "/" + computer_id
    screen = ScreenShot()
    running_proc = ProcessDetails()
    server_send = SendToServer(SERVER_URL + "/info" + computer_id)
    com_history = GetHistory()
    mouse = ComputerAction()
    send_details = threading.Thread(target=server_send.send_computer_details, args=[running_proc, com_history])
    send_screenshots = threading.Thread(target=screen.send_screenshot, args=[computer_id])
    send_action = threading.Thread(target=mouse.check_mouse_click)
    send_screenshots.setDaemon(True)
    send_details.start()
    send_screenshots.start()
    send_action.start()


if __name__ == "__main__":
    main()
