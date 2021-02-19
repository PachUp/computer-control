import sqlite3
from shutil import copyfile
import getpass
user = getpass.getuser()
history = "C:\\Users\\" + user + "\\AppData\\Local\\Google\\Chrome\\User Data\\Default\\History"
copyfile(history, '.\\dis')
con = sqlite3.connect('.\\dis')
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
        print(i)
        if i.find("chrome-extension") == -1:
            print(i)