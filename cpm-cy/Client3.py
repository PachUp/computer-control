import mss
import mss.tools
import requests
from time import sleep
from sys import exit
import psutil
import threading
import sqlite3
from shutil import copyfile
from io import BytesIO
from getmac import get_mac_address
import getpass
from PIL import Image
import socket
import json
import win32api, win32con
from ctypes import windll



SERVER_IP = input("Enter the server's IP address: ")
SERVER_URL = f"http://{SERVER_IP}:5000"
SOCKET_PORT = 12341
RECV_DEFAULT = 1024

class ProcessDetails:
    def __init__(self):
        pass

    def get_running_processes(self):
        """
        Returning a list of the current running processes in the computer
        """
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

    def pre_screenshot(self, computer_id):
        """
        :param computer_id: the id of the current computer

        Sending the screenshots to the server as long as the picture actually changes
        """
        prev_img = ""
        with mss.mss() as sct:
            while True:
                # Use the 1st monitor
                sct.compression_level = 1
                monitor = sct.monitors[1]
                # Grab the picture
                im = sct.grab(monitor)
                img_obj = Image.frombytes("RGB", im.size, im.bgra, "raw", "BGRX") # Create a PIL image object.
                bytes_stream = BytesIO()
                img_obj.save(bytes_stream, "jpeg", quality=15)
                bytes_stream.seek(0)
                compressed_img = bytes_stream.read()
                if compressed_img != prev_img:
                    self.send_screenshot(computer_id, compressed_img)
                prev_img = compressed_img
    
    def send_screenshot(self, computer_id, raw_bytes):
        requests.post(SERVER_URL + '/get_file/' + computer_id, data=raw_bytes,
                                  headers={'Content-Type': 'application/octet-stream'})



class SendToServer:
    def __init__(self, send_request_to):
        self.send_request_to = send_request_to

    def send_computer_details(self, running_proc, com_history):
        """
        :param running_proc: the object of the class "ProcessDetails"

        send the data of the computer (without the screenshot)
        """
        while True:
            requests.post(self.send_request_to, json={"running processes": running_proc.get_running_processes()[0], "chrome history": com_history.get_chrome_history()})
            sleep(5)  # sending the data every 5 seconds so I wouldn't DDOS myself


class GetHistory:
    def __init__(self):
        pass

    def get_chrome_history(self):
        ###
        """
        Getting the user's chrome history from the DB and returning the 10 most recent history searches
        """

        user = getpass.getuser()
        history = "C:\\Users\\" + user + "\\AppData\\Local\\Google\\Chrome\\User Data\\Default\\History"
        try:
            copyfile(history, '.\\ChromeHistoryCopy')
        except:
            pass
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
        con.close()
        return chrome_hisory


class ComputerAction:
    def __init__(self):
        self.s = socket.socket()
        self.s.connect((SERVER_IP, SOCKET_PORT))
    
    def click(self, x, y):
        """
        :param x: the X coordinates 
        :param y: the Y coordinates

        The function clicks on the X & Y coordinates on the screen.
        """
        win32api.SetCursorPos((x,y))
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN,x,y,0,0)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP,x,y,0,0)

    def check_mouse_click(self, computer_id):
        """
        :param computer_id the id of the current computer

        the function executes the commands that the server sent to it
        """
        self.s.send(str(computer_id).encode())
        while True:
            server_command = self.s.recv(RECV_DEFAULT)
            try:
                pos = json.loads(server_command.decode())
                pos_x = int(float(pos[0]))
                pos_y = int(float(pos[1]))
                self.click(pos_x, pos_y)
            except:
                lock_key = server_command.decode()
                if lock_key == "Lock" or lock_key == "Unlock":
                    if lock_key == "Lock": # only works if the client is activated in administrator mode
                        windll.user32.BlockInput(True)
                    else:
                        windll.user32.BlockInput(False)
                else:
                    win32api.keybd_event(int(lock_key),0,0,0)
                    win32api.keybd_event (int(lock_key),0, win32con.KEYEVENTF_KEYUP, 0) # key is released


class InitServer():
    def __init__(self):
        pass

    def init_server_conn(self):
        address_link = f'{SERVER_URL}/computers/verify_login'
        try:
            response = requests.get(address_link)
            status_code = response.status_code
            if status_code == 200:
                return self.get_client_id()
            else:
                print("--- There was a some problem with the server! Closing program... ---")
                exit()
        except:
            print("--- The server is offline! Are you sure this is the correct IP address? Closing program... ---")
            exit()
    
    def get_client_id(self):
        req_id = requests.post(f'{SERVER_URL}/computers/verify_login',
                            json={"mac_address": get_mac_address()})
        computer_id = req_id.content.decode()
        return computer_id


def main():
    init_conn = InitServer()
    computer_id = init_conn.init_server_conn()
    screen = ScreenShot()
    running_proc = ProcessDetails()
    server_send = SendToServer(SERVER_URL + "/info/" + computer_id)
    com_history = GetHistory()
    mouse = ComputerAction()
    send_details = threading.Thread(target=server_send.send_computer_details, args=[running_proc, com_history])
    send_screenshots = threading.Thread(target=screen.pre_screenshot, args=[computer_id])
    send_action = threading.Thread(target=mouse.check_mouse_click, args=[computer_id])
    send_screenshots.setDaemon(True)
    send_details.start()
    send_screenshots.start()
    send_action.start()


if __name__ == "__main__":
    main()
