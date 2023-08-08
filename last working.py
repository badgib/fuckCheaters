import os
import re
import sys
import time
import json
import winsound
import threading
import configparser

import cv2
import pyttsx3
import keyboard
import pyautogui
import pytesseract
import cloudscraper

import numpy as np
from bs4 import BeautifulSoup

ver = 'v0.7.2'

ding_wav = 'ding.wav'
error_wav = 'error.wav'
conf_file = 'conf.ini'
output_file = 'output.txt'

custom_config = r'--oem 1 --psm 7'
networks = ['atvi', 'battlenet', 'psn', 'xbl']
last_stats = []
attempts = 3

# load config from file
if os.path.exists(conf_file):

    config = configparser.ConfigParser()
    config.read(conf_file)
    get_cheater_key = config.get('keys', 'capture')
    repeat_last_key = config.get('keys', 'repeat')
    manual_input_key = config.get('keys', 'manual')
    do_the_speech = config.getboolean('tts', 'enable')
    tts_rate = config.getint('tts', 'rate')
    volume = config.getfloat('tts', 'volume')
    x_reg = config.getint('cap', 'x')
    y_reg = config.getint('cap', 'y')
    w_reg = config.getint('cap', 'w')
    h_reg = config.getint('cap', 'h')
    burst = config.getint('cap', 'burst')
    im0pos = config.getint('pos', 'p0')
    im1pos = config.getint('pos', 'p1')
    im2pos = config.getint('pos', 'p2')
    main_delay = config.getfloat('delay', 'main')
    cap_delay = config.getfloat('delay', 'burst')
    thread_delay = config.getfloat('delay', 'thread')
    tess_path = config.get('files', 'tess')
    output_folder = config.get('files', 'out')

# well... if user deletes conf.ini it's his own damn fault...
else:

    print('conf.ini missing, exiting')
    sys.exit()

# if tesseract.exe can't be found in specified path ask user for input (until valid)
while not os.path.exists(tess_path):

    tess_path = input(f'tesseract-ocr not found in: {tess_path}. check your conf.ini and put valid path\nplease specify\
                        path to tesseract.exe: ')

# pass valid (hopefully) path to tesseract
pytesseract.pytesseract.tesseract_cmd = tess_path

# initiate cloudscraper
scraper = cloudscraper.create_scraper()

# clear screen for nicer experience
os.system('cls')

# print logo
print(f'''    ____           __   ________               __     {ver}
   / __/_  _______/ /__/ ____/ /_  ___  ____ _/ /____  __________
  / /_/ / / / ___/ //_/ /   / __ \\/ _ \\/ __ `/ __/ _ \\/ ___/ ___/
 / __/ /_/ / /__/ ,< / /___/ / / /  __/ /_/ / /_/  __/ /  (__  ) 
/_/  \\__,_/\\___/_/|_|\\____/_/ /_/\\___/\\__,_/\\__/\\___/_/  /____/  
               fuck them all to death!\t\tTtS: {do_the_speech}''')
print(f'capture: {get_cheater_key}\t\trepeat: {repeat_last_key}\t\tmanual: {manual_input_key}')
print('-----------------------------------------------------------------')

# TODO: THREADED SPEECH!
#       na razie na szczescie nie powinno to sprawiac klopotow,
#       dingami i errorami informuje o stanie a na koniec tylko
#       czyta na glos wynik poszukiwan.
#       winsound jest async, wieeeec fuckyeah

# if requested initiate tts
if do_the_speech:

    engine = pyttsx3.init()
    engine.setProperty('rate', tts_rate)
    engine.setProperty('volume', volume)
    engine.say('ready')
    engine.runAndWait()


# now with all the tasty threading
class ThreadedCrap(threading.Thread):

    def __init__(self):

        threading.Thread.__init__(self)

    def run(self):

        getCheaterID()


# OCR stuff is here - grab part of screen, then three parts of that grab and try to find something
def getCheaterID():

    global last_stats
    grabbed = []
    still_nothing = True

    # grab a bunch of images to maximize the chance of success
    for _ in range(burst):

        # grab a screenshot (specified part of it to be exact) and save copy to output folder
        grabbed.append(pyautogui.screenshot(f'{output_folder}{time.strftime("%d-%m.%H-%M-%S")}.png',
                                            region=(x_reg, y_reg, w_reg, h_reg)))
        pyautogui.sleep(cap_delay)

    # go through grabbed images and process them
    for grab in grabbed:

        try:

            # manipulate grabbed screenshot to make it readable for tesseract
            # make it gray, resize by 50%, save temp file, make it b/w and apply bilateral filter
            shot = np.array(grab)
            gray_img = cv2.cvtColor(shot, cv2.COLOR_BGR2GRAY)
            res_img = cv2.resize(gray_img, None, fx=1.5, fy=1.5, interpolation=cv2.INTER_CUBIC)
            cv2.imwrite('tmp.png', res_img)
            threshold_img = cv2.threshold(res_img, 0, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C | cv2.THRESH_OTSU)[1]
            bilat_img = cv2.bilateralFilter(threshold_img, 15, 80, 80, cv2.BORDER_DEFAULT)

            # extract three possible text locations from our screenshot
            sub0img = bilat_img[im0pos:im0pos + 30, 0:int(h_reg * 1.5)]
            sub1img = bilat_img[im1pos:im1pos + 30, 0:int(h_reg * 1.5)]
            sub2img = bilat_img[im2pos:im2pos + 30, 0:int(h_reg * 1.5)]

            # and add borders for OCR (it doesn't like text to close to border)
            bor0img = cv2.copyMakeBorder(sub0img, 20, 20, 20, 20, cv2.BORDER_CONSTANT, value=(255, 255, 255))
            bor1img = cv2.copyMakeBorder(sub1img, 20, 20, 20, 20, cv2.BORDER_CONSTANT, value=(255, 255, 255))
            bor2img = cv2.copyMakeBorder(sub2img, 20, 20, 20, 20, cv2.BORDER_CONSTANT, value=(255, 255, 255))

            # make list for ease of iteration
            images = [bor0img, bor1img, bor2img]

            # check all possible text locations
            for im in images:

                # try to read from image
                details = pytesseract.image_to_string(im, config=custom_config)[:-2]

                # if something was found check if it complies with regex
                if len(details) > 1:

                    # using regex find known nickname format
                    matched = re.search(r'[ \w!]+[#]\d+', details)

                    # if found fix damn space (if borked) and pass it to check for data
                    if matched:

                        nick = matched.group(0).replace(' #', '#')
                        winsound.PlaySound(ding_wav, winsound.SND_ASYNC)
                        last_stats = checkNetworks(nick)
                        still_nothing = False
                        break

        # handle exceptions
        except IOError:

            print('error reading image!')

        except UnicodeEncodeError:

            print('UnicodeEncodeError!')

    # if OCR couldn't find nickname in image inform user
    if still_nothing:
        winsound.PlaySound(error_wav, winsound.SND_ASYNC)
        print('error - query empty or broken')


# check if anything can be found for given nickname
def checkNetworks(who):

    global last_stats
    global attempts
    we_good = False

    # check all possible networks for information
    for network in networks:

        url = f'https://cod.tracker.gg/warzone/profile/{network}/{who.replace("#", "%23")}/detailed'
        try:

            # scraper rocks! used instead of requests because cloudflare
            response = scraper.get(url)

            # load all that html and make it beautiful
            soup = BeautifulSoup(response.content, 'html.parser')

            # find json location and get it parsed
            scripts = soup.findAll('script')
            jsonned = json.loads(str(scripts[1])[33:-131])

            # read interesting values
            kd = jsonned['stats-v2']['standardProfiles'][f'warzone|{network}|{who.lower()}']['segments'][0]['stats']['kdRatio']['value']
            hs = jsonned['stats-v2']['standardProfiles'][f'warzone|{network}|{who.lower()}']['segments'][0]['stats']['weeklyHeadshotPct']['value']
            lv = jsonned['stats-v2']['standardProfiles'][f'warzone|{network}|{who.lower()}']['segments'][0]['stats']['level']['value']

            # and save them for later
            last_stats = [kd, hs, lv]

            # log, print to console and possibly even speak out loud all that gathered data
            addOutputLine(f'{who} @ {network}: kd: {kd}, hs: {hs}%, level: {lv} \t\t{url}\n')
            print(f'{who} @ {network}: kd: {kd}, hs: {hs}%, level: {lv}')
            speakToMe(f'k d: {kd}, hedshot: {hs}%, level: {lv}')

            we_good = True
            attempts = 3
            break

        # safeguard for bazingy
        except ConnectionError as e:

            if attempts > 0:

                # try and try again... and then try some more...
                attempts -= 1
                print(f'connection error {e}, retrying in 1s... attempts left: {attempts}')
                pyautogui.sleep(1)
                checkNetworks(who)

            else:

                # if problem still occurs just save the url and exit...
                print('i tried and tried, but still no connection - quitting.\nFIX YA DAMN CONNECTION')
                addOutputLine(f'no connection while checking: \t\t{url}\n')
                sys.exit()

        # if no info can be found in specified place for specified network print to console
        except KeyError:

            print(f'no info on {network} for {who}')

    # if no info was found in all networks log found nickname
    if not we_good:

        addOutputLine(f'no info on {who}\n')
        speakToMe('no matches found')

    # if all went well return gathered data for possible future repeating
    return last_stats


# repeat last found data
def repeatLast():

    if last_stats:

        speakToMe(f'k d: {last_stats[0]}, hedshot: {last_stats[1]}%, level: {last_stats[2]}')

    else:

        winsound.PlaySound(error_wav, winsound.SND_ASYNC)


# if user wants to check by hand now he can!
def manualInput():

    # wait for user to type in the name
    user_input = input('pray tell - who to check (leave empty to abort): ')
    if user_input:

        checkNetworks(user_input)

    else:

        print('no input found, aborting')


# just speak
def speakToMe(what):

    global do_the_speech
    if do_the_speech:

        engine.say(what)
        engine.runAndWait()
        # engine.stop()


# logging handling
def addOutputLine(line):

    with open(output_file, 'a') as o:

        o.writelines(f'{time.strftime("%d.%m %H:%M:%S")}\t{line}')


# main infinite loop checking for keypress
while 1:

    try:

        if keyboard.is_pressed(get_cheater_key):

            thread = ThreadedCrap()
            thread.start()
            pyautogui.sleep(thread_delay)

        elif keyboard.is_pressed(repeat_last_key) and do_the_speech:

            repeatLast()

        elif keyboard.is_pressed(manual_input_key):

            manualInput()

        # because of high CPU usage (therefore hold button a bit longer)
        pyautogui.sleep(main_delay)

    # catch ctrl + c
    except KeyboardInterrupt:

        print('k, bye')
        sys.exit()
