# SPDX-FileCopyrightText: 2021 ladyada for Adafruit Industries
# SPDX-License-Identifier: MIT

# Update 01-01-2023

"""Simple test script for 2.9" 296x128 grayscale display.

Supported products:
    * Adafruit 2.9" Grayscale
    * https://www.adafruit.com/product/4777
    * Adafruit ESP32-S2
    * https://www.adafruit.com/product/5303
"""

import time
import ssl
import busio
import board
import alarm
import displayio
import adafruit_il0373
import terminalio
import wifi
import socketpool
import digitalio
import neopixel
import adafruit_requests as requests
from adafruit_display_text import label
from adafruit_bitmap_font import bitmap_font
from adafruit_bme280 import basic as adafruit_bme280
from adafruit_lc709203f import LC709203F, PackSize
from adafruit_datetime import datetime, date

displayio.release_displays()

# Set Standard time or Military Time
OPEN_SM_TIME = 9  # Stock Exchange opens at 9:30 AM
CLOSE_SM_TIME = 15  # Stock Exchange cloes at 4 PM
USE_AMPM_TIME = True
GBHoliday = False
TIME_CHECK = True
GBMARKET_STATUS = True
DISPLAY_WAIT = 5
# Set Day of Week
WEEK_DAY_DICT = {1: "Mon", 2: "Tue", 3: "Wed", 4: "Thr", 5: "Fri", 6: "Sat", 7: "Sun"}
# Set Time Zone in US only
TIME_ZONE_DICT = {
    "UTC": -6,
    "EST": -0,
    "EDT": -0,
    "CST": -1,
    "CDT": -1,
    "MST": -2,
    "MDT": -2,
    "PST": -3,
    "PDT": -3,
}

# --------------------------------------------------------------
#                        Subroutines
# --------------------------------------------------------------
def find_holiday(holidays):
    HOLIDAY = {
        "01-02": True, # New Years Day
        "01-16": True, # Martin Luther King Day
        "02-20": True, # President Day
        "04-07": True, # Good Friday
        "05-29": True, # Memorial Day
        "06-19": True, # Juneteenth Day
        "07-04": True, # July 4th
        # "07-05": True,  #used for testing purpose
        "09-04": True, # Labor Day
        "10-09": True, # Columbus Day
        "11-10": True, # Veterans Days
        "11-23": True, # Thanksgiving Day
        "12-25": True, # Christmas Day
    }
    global GBHoliday
    GBHoliday = HOLIDAY[holidays]
    return

def hh_mm(time_struct, time_struct_min, twelve_hour=False):
    """Given a time.struct_time, return a string as H:MM or HH:MM, either
    12- or 24-hour style depending on twelve_hour flag.
    """
    global GBMARKET_STATUS
    postfix = ""
    try:
        find_holiday(check_holiday)

    except KeyError:
        pass


    if GBHoliday == False:
        GBMARKET_STATUS = True
        if (time_struct >= OPEN_SM_TIME + MARKET_ZONE
            and time_struct <= CLOSE_SM_TIME + MARKET_ZONE):
            GBMARKET_STATUS = True
            print(time_struct)
        else:
            GBMARKET_STATUS = False
            print(time_struct)
    else:
        GBMARKET_STATUS = False
    print(GBMARKET_STATUS)

    if twelve_hour:
        if time_struct > 12:
            hour_string = str(time_struct - 12)  # 13-23 -> 1-11 (pm)
            postfix = "pm"
        elif time_struct > 0:
            hour_string = str(time_struct)  # 1-12
            postfix = "am"
            if time_struct == 12:
                postfix = "pm"  # 12 -> 12 (pm)
        else:
            hour_string = "12"  # 0 -> 12 (am)
            postfix = "am"
    else:
        hour_string = "{hh:02d}".format(hh=time_struct)


    return hour_string + ":{mm:02d}".format(mm=time_struct_min) + postfix


def get_sleep_time():
    #try:
    #    find_holiday(check_holiday)
    #except KeyError:
    #    pass

    print("Holiday is ", GBHoliday)
    MY_HOUR = int(mytime[3])
    MY_MINS = int(mytime[4])

    if GBHoliday == True:
        sleep_timer_hour_sec = 82800 - (3600 * MY_HOUR)
        sleep_timer_min_sec = 3600 - (60 * MY_MINS)
        print("Sleep for the Holiday")
    else:
        print("Today is: ", WEEK_DAY_DICT[week])
        if week == 6 or week == 7:
            print("week-end")
            sleep_timer_hour_sec = 82800 - (3600 * MY_HOUR)
            sleep_timer_min_sec = 3600 - (60 * MY_MINS)
            print("Sleep for the Week-end")
        else:
            print("week-day")
            if (MY_HOUR >= (OPEN_SM_TIME + MARKET_ZONE)) and (
                MY_HOUR <= (CLOSE_SM_TIME + MARKET_ZONE)
            ):
                sleep_timer_hour_sec = 0
                sleep_timer_min_sec = 60 * DISPLAY_WAIT
            else:
                print("Stock Market is closing")
                if MY_HOUR >= (CLOSE_SM_TIME + MARKET_ZONE):
                    print("Stock Market closed for the day")
                    sleep_timer_hour_sec = 82800 - (3600 * MY_HOUR)
                    sleep_timer_min_sec = 3600 - (60 * MY_MINS)

                elif MY_HOUR <= (OPEN_SM_TIME + MARKET_ZONE):
                    print("Stock Market opening soon")
                    # sleep_timer_hour_sec = ((3600 * MY_HOUR) - (3600 * 6))
                    sleep_timer_hour_sec = (3600 * 6) - (3600 * MY_HOUR)
                    sleep_timer_min_sec = 3600 - (60 * MY_MINS)

    hours = int(sleep_timer_hour_sec / 60 / 60)
    minutes = int(sleep_timer_min_sec / 60)

    sleep_timer = sleep_timer_hour_sec + sleep_timer_min_sec
    print("TOTAL Sleep Time in Seconds: ", sleep_timer)
    print("TOTAL Sleep HOURS: ", hours)
    print("TOTAL Sleep MINUTES: ", minutes)
    return sleep_timer


# Define Deep Sleep Routine
def go_to_sleep(sleep_period):
    print("going to sleep")
    if sleep_period <= 0:
        pixel.fill((50, 0, 50))
        time.sleep(2)
        print("sleeping error for: ", sleep_period)
        sleep_period = 360
    print("sleeping normal for: ", sleep_period)
    # Create a an alarm that will trigger sleep_period number of seconds from now.
    time_alarm = alarm.time.TimeAlarm(monotonic_time=time.monotonic() + sleep_period)
    # Exit and deep sleep until the alarm wakes us.
    alarm.exit_and_deep_sleep_until_alarms(time_alarm)


# --------------------------------------------------------------
#                          End Subroutines
# --------------------------------------------------------------

i2c = board.I2C()
# Create sensor object, using the board's default I2C bus.
battery_monitor = LC709203F(i2c)
# Update to match the mAh of your battery for more accurate readings.
# Can be MAH100, MAH200, MAH400, MAH500, MAH1000, MAH2000, MAH3000.
# Choose the closest match. Include "PackSize." before it, as shown.
battery_monitor.pack_size = PackSize.MAH2000

pixel = neopixel.NeoPixel(board.NEOPIXEL, 1)
pixel.brightness = 0.3

# status LED Yellow accessing internet
pixel.fill((50, 50, 0))
time.sleep(0.5)
# Add a secrets.py to your filesystem that has a dictionary called secrets with "ssid" and
# "password" keys with your WiFi credentials. DO NOT share that file or commit it into Git or other
# source control.
# pylint: disable=no-name-in-module,wrong-import-order
try:
    from secrets import secrets
except ImportError:
    print("Credentials and tokens are kept in secrets.py, please add them there!")
    raise

# Get Secret Data from secret file
print("Connecting to %s" % secrets["ssid"])
wifi.radio.connect(secrets["ssid"], secrets["password"])
print("Connected to %s!" % secrets["ssid"])
stock = secrets["stock"]
# Connect to Internet
pool = socketpool.SocketPool(wifi.radio)

pixel.fill((50, 0, 50))
time.sleep(1)
requests = requests.Session(pool, ssl.create_default_context())
pixel.fill((10, 10, 50))
time.sleep(1)
# Get our Adafruit IO username, key and desired Stock Market Key
aio_username = secrets["aio_username"]
aio_key = secrets["aio_key"]
stock_token = secrets["stock_token_key"]

# Stock Quote Web Site
# Access Stock Web site example output
# "https://finnhub.io/api/v1/quote?symbol=WSO&token=c7o805qad3idf06moreg"
# output of finnhub.io
# {"c":278.9,"d":-8.56,"dp":-2.9778,"h":284.03,"l":274.91,"o":284.03,"pc":287.46,"t":1643144402}
DATA_SOURCE = ("https://finnhub.io/api/v1/quote?symbol=" + stock + "&token=" + stock_token
)
# Time from Adafruit io Web site
TIME_URL = (
    "https://io.adafruit.com/api/v2/%s/integrations/time/strftime?x-aio-key=%s"
    % (aio_username, aio_key)
)
# TIME_URL += "&fmt=%25Y-%25m-%25d+%25H%3A%25M%3A%25S.%25L+%25j+%25u+%25z+%25Z" Example
TIME_URL += "&fmt=%25Y%3A%25m%3A%25d%3A%25H%3A%25M%3A%25Z"

while TIME_CHECK:
    # Test for weak internet access
    try:
        time_response = requests.get(TIME_URL)

        time.sleep(1)
        TIME_CHECK = False
    except RuntimeError as e:
        print("could not get the time, retrying: ", e)
        pixel.fill((50, 0, 0))
        time.sleep(1)
        TIME_CHECK = True
    continue

mytime = str(time_response.text)  # <== commit out for testing

# Use line below to test date & time
#mytime = "2023:01:17:06:00:MDT" # <=== use for testing purposes

# Break up date and time string
mytime = mytime.split(":")

# Get Month and Day for Holiday check
check_holiday = (mytime[1]) + "-" + (mytime[2])

# Set up Time Zone
MARKET_ZONE = TIME_ZONE_DICT[mytime[5]]
print("Market Time Zone")
print(MARKET_ZONE)
mytime[3] = str(int(mytime[3]))
# Get Year, Month, Day
dt = datetime(
    int(mytime[0]), int(mytime[1]), int(mytime[2]), int(mytime[3]), int(mytime[4])
)
week = dt.isoweekday()
print("Week day: ", week)
print("My Time: ", mytime)
print(mytime[5])
# Get Time stamp, weather and setup for displaying
# Status LED BLUE getting Stock Data from Internet
pixel.fill((0, 0, 50))
time.sleep(2)
ipaddr = "My IP address is", wifi.radio.ipv4_address
print(ipaddr)

# Collect BME280 Data and setup display
bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c)

bme280_D = str("{:.1f}° F".format(((bme280.temperature) * 9 / 5) + 32))
humidity = str("{:.2f} %".format(bme280.relative_humidity))
pressure = str("{:.2f} hPa".format(bme280.pressure))
battery = str("{:.2f} %".format(battery_monitor.cell_percent))

# Get Stock Quotes and setup for displaying
Data_response = requests.get(DATA_SOURCE)

# Display Current Stock Price
text = str(Data_response.json()["c"])
text = "$ " + text + " " + stock

# Display Current Stock Price High for the day
text1 = str(Data_response.json()["h"])
text1 = "$ " + text1 + " High"

# Display Current Stock Price Low for the day
text2 = str(Data_response.json()["l"])
text2 = "$ " + text2 + " Low"

# Display Day and time of last access to Internet
text3 = (
    WEEK_DAY_DICT[week]
    + "  "
    + (str(hh_mm(int(mytime[3]), int(mytime[4]), USE_AMPM_TIME)))
    + "  "
    + mytime[5]
)

# Display Temp, Humidity, Pressure, and Battery life
text4 = (bme280_D) + "    " + (humidity) + "    " + (pressure) + "    " + (battery)

# Display Yesterday Closing Stock Price
text5 = str(Data_response.json()["pc"])
if GBMARKET_STATUS == True:
    text5 = "$ " + text5 + " prv Close"
else:
    text5 = "   Market Closed"

# Status LED GREEN Loading screen with stock quote
pixel.fill((0, 50, 0))
time.sleep(0.5)

# Font Selection
font = bitmap_font.load_font("/fonts/LeagueGothic-Regular-36.pcf")
font1 = bitmap_font.load_font("/fonts/Arial-Bold-12.pcf")
font2 = bitmap_font.load_font("/fonts/Arial-Italic-12.pcf")
font3 = bitmap_font.load_font("/fonts/SerifPro-Regular-12.bdf")
# Set text color
color = 0x000000
redcolor = 0xFF0000

# =======================================================
# Build Display
# =======================================================
# Current Stock price
text_area = label.Label(font, text=text, color=color)
# Set the location
text_area.x = 65
text_area.y = 20

# Current High
text_area1 = label.Label(font1, text=text1, color=color)
# Set the location
text_area1.x = 30
text_area1.y = 60

# Current Low
text_area2 = label.Label(font2, text=text2, color=color)
# Set the location
text_area2.x = 165
text_area2.y = 60

# Display Date and Time
text_area3 = label.Label(font3, text=text3, color=color)
# Set the location
text_area3.x = 100
text_area3.y = 80

# Display Temp Humdity Battery
text_area4 = label.Label(font3, text=text4, color=redcolor)
# Set the location
text_area4.x = 40
text_area4.y = 98

# Display Yesterday Closing Price
text_area5 = label.Label(font1, text=text5, color=color)
# Set the location
text_area5.x = 80
text_area5.y = 117

# =======================================================

# Create Display Connection for E-Ink 2.9 Gray Display
spi = busio.SPI(board.SCK, board.MOSI)  # Uses SCK and MOSI
epd_cs = board.D9
epd_dc = board.D10

# for TRICOLOR screen
epd_busy = board.D6

display_bus = displayio.FourWire(
    spi, command=epd_dc, chip_select=epd_cs, baudrate=1000000
)
time.sleep(0.5)

# E-paper settings
display = adafruit_il0373.IL0373(
    display_bus,
    width=296,
    height=128,
    rotation=270,
    black_bits_inverted=False,
    color_bits_inverted=False,
    grayscale=True,
    refresh_time=1,
)

# Create Group called g
g = displayio.Group()

# Display Frame and text
with open("/bmps/quotes_bg.bmp", "rb") as f:
    pic = displayio.OnDiskBitmap(f)
    # CircuitPython 6 & 7 compatible
    t = displayio.TileGrid(
        pic, pixel_shader=getattr(pic, "pixel_shader", displayio.ColorConverter())
    )
    # CircuitPython 7 compatible only
    # t = displayio.TileGrid(pic, pixel_shader=pic.pixel_shader)
    g.append(t)
    g.append(text_area)
    g.append(text_area1)
    g.append(text_area2)
    g.append(text_area3)
    g.append(text_area4)
    g.append(text_area5)
    display.show(g)

    display.refresh()

    print("refreshed")

# Call Deep sleep timer when Market Closes and when it Opens set refresh time
go_to_sleep(get_sleep_time())
