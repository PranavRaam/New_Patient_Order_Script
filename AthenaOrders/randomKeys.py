import pyautogui
import ReadConfig as rc
import CommonUtil as cu
import time

def keyPress(filepath):
    pyautogui.press('backspace')
    time.sleep(2)
    pyautogui.typewrite(filepath)
    time.sleep(1)
    pyautogui.press('enter')