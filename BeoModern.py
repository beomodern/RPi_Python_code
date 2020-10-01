################################################################################
# Code to run on Raspberry Pi to handle BeoModern operation
#
# RPi modes include :
#  - mp3/flac Player (called Player)
#  - Internet Radio Player (called iRadio)
#  - DAB Radio Receiver (called DAB)
#  - FM RDS Receiver (optional - called RDS)
#
# Main backbone of the code relies on Python State Machine functions.
# Code to be run in Python 3+
################################################################################


################################################################################
# Set to false to disable testing/tracing code
# Set to True to enable testing/tracing code (print state names)
TESTING = False#True

################################################################################
# Support functions

# Serial port port configuration
import time
import serial

# import system functions
import subprocess
import os
import re
import textwrap
import http.client as httplib
from mpd import MPDClient
import RPi.GPIO as GPIO

# function to handle nested dictionaries used to store DAB radio station 
# settings
from collections import defaultdict
sortet_stationlist = defaultdict(defaultdict)

ser = serial.Serial(
# RPi
    port='/dev/serial0',
# Windows
#    port='COM4',
    baudrate = 115200,#57600,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    bytesize=serial.EIGHTBITS,
    timeout=0#.1 #4CHANGE LATER ON - CHANGE LATER ON - CHANGE LATER ON
)


# testing/tracing function
def log(s):
    """Print the argument if testing/tracing is enabled."""
    if TESTING:
        print(s)
#        time.sleep(0.2)


# UART reading function
def command_read():
    if ser.inWaiting():             
# check if there is new data in UART buffer waiting to be read back
# read data from buffer untill '+' symbol is received or timeout is reached
#        command = ser.read_until('+'.encode('UTF-8')).decode('UTF-8')
# REMOVE REMOVE 
# read one caracter and compare it to its binary representaiton - temporary solution
        command =  ser.read(1)
        if command == b'w':
            command = "-UP+"
        elif command == b's':
            command = "-DOWN+"
        elif command == b'a':
            command = "-BACK+"
        elif command == b'd':
            command = "-NEXT+"
        elif command == b'o':
            command = "-GO+"
        elif command == b'p':
            command = "-STOP+"
        elif command == b'1':
            command = "-Player+"
        elif command == b'2':
            command = "-iRadio+"
        elif command == b'3':
            command = "-DAB+"
        elif command == b'4':
            command = "-RDS+"
        elif command == b'z':
            command = "-FM_01+"
        elif command == b'x':
            command = "-FM_02+"
        elif command == b'c':
            command = "-FM_03+"
        elif command == b'v':
            command = "-FM_04+"
        elif command == b'b':
            command = "-FM_05+"
        elif command == b'n':
            command = "-FM_06+"
        elif command == b'm':
            command = "-FM_07+"
        elif command == b',':
            command = "-FM_08+"
        elif command == b'.':
            command = "-FM_09+"
        elif command == b'y':
            command = "-SHUTDOWN+"
# REMOVE REMOVE 
#        log('UART read back = %s' % (command))
# REMOVE REMOVE 
        else:
            log('Wrong UART readback letter = %s' % (command))
            return False
# REMOVE REMOVE 
        if command.startswith('-') and command.endswith('+'): 
# check if start '-' and end '+' message symbols are as expected
            command = command[1:-1] 
# strip out start '-' and end '+' command symbol
            log('New command = %s' % (command))
            return command          
# return new command
        else:
            log('UART wrong start/stop')
            return False
    else:
#log('UART buffer empty')
        return False



# function responsible for correct formatting information sent over UART
# to be presented on 16 alphanumeric display
def display(mode, previous_time=0, **display_data):

    
# displaying DAB station browsing
    if mode == 'DAB_browsing':
# check if expected time passed and display needs to be updated
        if time.monotonic() <= previous_time + 1:
# if expected delay time didn't pass return the same time stamp and do nothing
            return (previous_time, display_data['rolling_station'])
        else:
# calculate size of radio station nubmers information
            space = (15 - len(str(display_data['station_number']) + '/'
              + str(display_data['number_of_stations'])))
# print over UART radio numbers info
            (ser.write(bytes(str(display_data['station_number']) 
              + '/'
              + str(display_data['number_of_stations']) 
              + ' ',
              'UTF-8')))
# wrap radio station name into space left after radio station nubmer info
            wrapper = textwrap.TextWrapper(width=space, break_on_hyphens = False)
            title_list = wrapper.wrap(text=display_data['rolling_station'])
# check if informaiton to display is shorter then available display space
            if len(title_list[0]) < space:
# if it is, fill reminig space with spaces
                to_display = title_list[0] + (' ' * (space - len(title_list[0])))
            else:
# if no issue with spaces, display whole line from list
                to_display = title_list[0]
# print over UART part of radio station name
            ser.write(bytes(to_display + ';D\r\n', 'UTF-8'))
# check if remining part of radio station name can fit into remining display space
            if len(title_list) > 1:
# if no, return new time stamp from which delay will be checked next time
# together with radio station data without first word
# check if reminig string contains spaces
                if len(display_data['rolling_station'].split(" ")) > 1:
# if spaces are in, return string without first word
                    return (time.monotonic(), display_data['rolling_station'].partition(' ')[2])
# if spaces are not present, return string minus nubmer of first characters 
# equal available display space
                else:
                    return (time.monotonic(), display_data['rolling_station'][space:])
            else:
# if yes, return new time stamp from which delay will be checked next time
# together with full radio station name to start rolling again
                return (time.monotonic(), display_data['station'])


        
    elif mode == 'DAB_listening':
# check if expected time passed and display needs to be updated
        if time.monotonic() <= previous_time + 1.5:
# if expected delay time didn't pass return the same time stamp and do nothing
            return (previous_time, display_data['rolling_station'])
        else:
# display space
            space = 16
# wrap file name into available space 
            wrapper = textwrap.TextWrapper(width=space, break_on_hyphens = False)
            title_list = wrapper.wrap(text=display_data['rolling_station'])
# check if informaiton to display is shorter then available display space
            if len(title_list[0]) < space:
# if it is, fill reminig space with spaces
                to_display = title_list[0] + (' ' * (space - len(title_list[0])))
            else:
# if no issue with spaces, display whole line from list
                to_display = title_list[0]
# print over UART part of radio station name
            ser.write(bytes(to_display + ';D\r\n', 'UTF-8'))
# check if remining part of radio station name can fit into remining display space
            if len(title_list) > 1:
# if no, return new time stamp from which delay will be checked next time
# together with radio station data without first word
# check if reminig string contains spaces
                if len(display_data['rolling_station'].split(" ")) > 1:
# if spaces are in, return string without first word
                    return (time.monotonic(), display_data['rolling_station'].partition(' ')[2])
# if spaces are not present, return string minus nubmer of first characters 
# equal available display space
                else:
                    return (time.monotonic(), display_data['rolling_station'][space:])
            else:
# if yes, return new time stamp from which delay will be checked next time
# together with full sradio station name to start rolling again
                return (time.monotonic(), display_data['station'])

        
    elif mode == 'Player_folder_browsing':
# check if expected time passed and display needs to be updated
        if time.monotonic() <= previous_time + 1:
# if expected delay time didn't pass return the same time stamp and do nothing
            return (previous_time, display_data['rolling_name'])
        else:
# calculate size of folder nubmers information
            space = (15 - len(str(display_data['folder_number']) + '/'
              + str(display_data['number_of_folders'])))
# print over UART folder numbers
            (ser.write(bytes(str(display_data['folder_number'])
              + '/'
              + str(display_data['number_of_folders'])
              + ' ',
              'UTF-8')))
# wrap folder name into space left after folder nubmer info
# change letters to upper characters
            wrapper = textwrap.TextWrapper(width=space)
            name_list = wrapper.wrap(text=display_data['rolling_name'].upper())
# check if informaiton to display is shorter then available display space
            if len(name_list[0]) < space:
# if it is, fill reminig space with spaces
                to_display = name_list[0] + (' ' * (space - len(name_list[0])))
            else:
# if no issue with spaces, display whole line from list
                to_display = name_list[0]
# print over UART part of folder name
            ser.write(bytes(to_display + ';P\r\n', 'UTF-8'))
# check if remining part of song title can fit into remining display space
            if len(name_list) > 1:
# if no, return new time stamp from which delay will be checked next time
# together with song title data without first word
# check if reminig string contains spaces
                if len(display_data['rolling_name'].split(" ")) > 1:
# if spaces are in, return string without first word
                    return (time.monotonic(), display_data['rolling_name'].partition(' ')[2])
# if spaces are not present, return string minus nubmer of first characters 
# equal available display space
                else:
                    return (time.monotonic(), display_data['rolling_name'][space:])
            else:
# if yes, return new time stamp from which delay will be checked next time
# together with full folder name to start rolling again
                return (time.monotonic(), display_data['name'])

          
    elif mode == 'Player_file_browsing':
# check if expected time passed and display needs to be updated
        if time.monotonic() <= previous_time + 1:
# if expected delay time didn't pass return the same time stamp and do nothing
            return (previous_time, display_data['rolling_title'])
        else:
# calculate size of song nubmers information
            space = (15 - len(str(display_data['song_number']) + '/'
              + str(display_data['number_of_songs'])))
# print over UART song numbers
            (ser.write(bytes(str(display_data['song_number']) 
              + '/'
              + str(display_data['number_of_songs']) 
              + ' ',
              'UTF-8')))
# wrap file name into space left after file nubmer info
            wrapper = textwrap.TextWrapper(width=space, break_on_hyphens = False)
            title_list = wrapper.wrap(text=display_data['rolling_title'])
# check if informaiton to display is shorter then available display space
            if len(title_list[0]) < space:
# if it is, fill reminig space with spaces
                to_display = title_list[0] + (' ' * (space - len(title_list[0])))
            else:
# if no issue with spaces, display whole line from list
                to_display = title_list[0]
# print over UART part of file name
            ser.write(bytes(to_display + ';P\r\n', 'UTF-8'))
# check if remining part of song title can fit into remining display space
            if len(title_list) > 1:
# if no, return new time stamp from which delay will be checked next time
# together with song title data without first word
# check if reminig string contains spaces
                if len(display_data['rolling_title'].split(" ")) > 1:
# if spaces are in, return string without first word
                    return (time.monotonic(), display_data['rolling_title'].partition(' ')[2])
# if spaces are not present, return string minus nubmer of first characters 
# equal available display space
                else:
                    return (time.monotonic(), display_data['rolling_title'][space:])
            else:
# if yes, return new time stamp from which delay will be checked next time
# together with full song title to start rolling again
                return (time.monotonic(), display_data['title'])

          
    elif mode == 'Player_listening':
# check if expected time passed and display needs to be updated
        if time.monotonic() <= previous_time + 1:
# if expected delay time didn't pass return the same time stamp and do nothing
            return (previous_time, display_data['rolling_title'])
        else:
# calculate size of song remaining time information
            space = 15 - len(str(display_data['remaining_time']))
# wrap file name into space left after remiaining time info
            wrapper = textwrap.TextWrapper(width=space, break_on_hyphens = False)
            title_list = wrapper.wrap(text=display_data['rolling_title'])
# check if informaiton to display is shorter then available display space
            if len(title_list[0]) < space:
# if it is, fill reminig space with spaces
                to_display = title_list[0] + (' ' * (space - len(title_list[0])))
            else:
# if no issue with spaces, display whole line from list
                to_display = title_list[0]
# print over UART part of file name and remining time in seconds
            ser.write(bytes(to_display + ' ' + str(display_data['remaining_time']) + ';P\r\n', 'UTF-8'))
# check if remining part of song title can fit into remining display space
            if len(title_list) > 1:
# if no, return new time stamp from which delay will be checked next time
# together with song title data without first word
# check if reminig string contains spaces
                if len(display_data['rolling_title'].split(" ")) > 1:
# if spaces are in, return string without first word
                    return (time.monotonic(), display_data['rolling_title'].partition(' ')[2])
# if spaces are not present, return string minus nubmer of first characters 
# equal available display space
                else:
                    return (time.monotonic(), display_data['rolling_title'][space:])
            else:
# if yes, return new time stamp from which delay will be checked next time
# together with full song title to start rolling again
                return (time.monotonic(), display_data['title'])
 
        
    elif mode == 'iRadio_browsing':
# check if expected time passed and display needs to be updated
        if time.monotonic() <= previous_time + 1:
# if expected delay time didn't pass return the same time stamp and do nothing
            return (previous_time, display_data['rolling_station'])
        else:
# calculate size of radio station nubmers information
            space = (15 - len(str(display_data['iRadio_station_number']) + '/'
              + str(display_data['number_of_iRadio_stations'])))
# print over UART radio numbers info
            (ser.write(bytes(str(display_data['iRadio_station_number']) 
              + '/'
              + str(display_data['number_of_iRadio_stations']) 
              + ' ',
              'UTF-8')))
# wrap radio station name into space left after iRadio station nubmer info
            wrapper = textwrap.TextWrapper(width=space, break_on_hyphens = False)
            title_list = wrapper.wrap(text=display_data['rolling_station'])
# check if informaiton to display is shorter then available display space
            if len(title_list[0]) < space:
# if it is, fill reminig space with spaces
                to_display = title_list[0] + (' ' * (space - len(title_list[0])))
            else:
# if no issue with spaces, display whole line from list
                to_display = title_list[0]
# check and display current connection status
            if display_data['connection_state'] == 1:
                connection_status = ";O"
            else:
                connection_status = ";F"
# print over UART part of iRadio station name together with conenction status
            ser.write(bytes(to_display + connection_status +'\r\n', 'UTF-8'))
# check if remining part of iRadio station name can fit into remining display space
            if len(title_list) > 1:
# if no, return new time stamp from which delay will be checked next time
# together with iRadio station data without first word
# check if reminig string contains spaces
                if len(display_data['rolling_station'].split(" ")) > 1:
# if spaces are in, return string without first word
                    return (time.monotonic(), display_data['rolling_station'].partition(' ')[2])
# if spaces are not present, return string minus nubmer of first characters 
# equal available display space
                else:
                    return (time.monotonic(), display_data['rolling_station'][space:])
            else:
# if yes, return new time stamp from which delay will be checked next time
# together with full iRadio station name to start rolling again
                return (time.monotonic(), display_data['station'])


        
    elif mode == 'iRadio_listening':
# check if expected time passed and display needs to be updated
        if time.monotonic() <= previous_time + 1.5:
# if expected delay time didn't pass return the same time stamp and do nothing
            return (previous_time, display_data['rolling_station'])
        else:
# display space
            space = 16
# wrap file name into available space 
            wrapper = textwrap.TextWrapper(width=space, break_on_hyphens = False)
            title_list = wrapper.wrap(text=display_data['rolling_station'])
# check if informaiton to display is shorter then available display space
            if len(title_list[0]) < space:
# if it is, fill reminig space with spaces
                to_display = title_list[0] + (' ' * (space - len(title_list[0])))
            else:
# if no issue with spaces, display whole line from list
                to_display = title_list[0]
# check and display current connection status
            if display_data['connection_state'] == 1:
                connection_status = ";O"
            else:
                connection_status = ";F"
# print over UART part of iRadio station name together with conenction status
            ser.write(bytes(to_display + connection_status + '\r\n', 'UTF-8'))
# check if remining part of radio station name can fit into remining display space
            if len(title_list) > 1:
# if no, return new time stamp from which delay will be checked next time
# together with iRadio station data without first word
# check if reminig string contains spaces
                if len(display_data['rolling_station'].split(" ")) > 1:
# if spaces are in, return string without first word
                    return (time.monotonic(), display_data['rolling_station'].partition(' ')[2])
# if spaces are not present, return string minus nubmer of first characters 
# equal available display space
                else:
                    return (time.monotonic(), display_data['rolling_station'][space:])
            else:
# if yes, return new time stamp from which delay will be checked next time
# together with full iRadio station name to start rolling again
                return (time.monotonic(), display_data['station'])

    elif mode == 'RDS_info':
# check if expected time passed and display needs to be updated
        if time.monotonic() <= previous_time + 1.5:
# if expected delay time didn't pass return the same time stamp and do nothing
            return (previous_time, display_data['rolling_station'])
        else:
# display space
            space = 16
# wrap file name into available space 
            wrapper = textwrap.TextWrapper(width=space, break_on_hyphens = False)
            title_list = wrapper.wrap(text=display_data['rolling_station'])
# check if informaiton to display is shorter then available display space
            if len(title_list[0]) < space:
# if it is, fill reminig space with spaces
                to_display = title_list[0] + (' ' * (space - len(title_list[0])))
            else:
# if no issue with spaces, display whole line from list
                to_display = title_list[0]
# check and display current connection status
            if display_data['RDS_or_name'] == 1:
                RDS_or_name = ";R"
            else:
                RDS_or_name = ";N"
# print over UART part of radio station name or RDS data
            ser.write(bytes(to_display + RDS_or_name + '\r\n', 'UTF-8'))
# check if remining part of radio station name or RDS data can fit into remining 
# display space
            if len(title_list) > 1:
# if no, return new time stamp from which delay will be checked next time
# together with radio station or RDS data without first word
# check if reminig string contains spaces
                if len(display_data['rolling_station'].split(" ")) > 1:
# if spaces are in, return string without first word
                    return (time.monotonic(), display_data['rolling_station'].partition(' ')[2])
# if spaces are not present, return string minus nubmer of first characters 
# equal available display space
                else:
                    return (time.monotonic(), display_data['rolling_station'][space:])
            else:
# if yes, return new time stamp from which delay will be checked next time
# together with full radio station name or RDS data to start rolling again
                return (time.monotonic(), display_data['station'])
        
    elif mode == 'message':
# simply sent to display message         
        space = 16
# wrap file name into available space 
        wrapper = textwrap.TextWrapper(width=space, break_on_hyphens = False)
        title_list = wrapper.wrap(text=display_data['info'])
# check if informaiton to display is shorter then available display space
        if len(title_list[0]) < space:
# if it is, fill reminig space with spaces
            to_display = title_list[0] + (' ' * (space - len(title_list[0])))
        else:
# if no issue with spaces, display whole line from list
            to_display = title_list[0]
# print over UART part of radio station name or RDS data
        ser.write(bytes(to_display + ';M\r\n', 'UTF-8'))
        return 
              




# function to store and recall Player, iRadio and DAB settings
# all settigns are stored in BeoModern_init_settings.txt text file
# File format used:
#   first line -> DAB radio
#   second line -> mp3/flac Player
#   third line -> iRadio
# function parameters:
#   mode:
#        DAB - for DAB opearation
#        Player - for mp3/flac Player operation
#        iRadio - for iRadio opearation
#   opearion:
#        store - for storing latest data of selected mode
#        recall - for recalling latest data of selected mode
#   **to_store:
#        pointer to a dynamic nubmers of parameters
# when function is correctly called to readback data it returns list with 
# information read back from text file
# when function is correctly called to store latest data and it succedes, it
# returns True otherwise it returns False

def store_recall(mode, operation, **to_store):


# check if function shoudl restore
    if operation == 'recall':
# open and read back last settings from BeoModern_init_settings.txt file. 
        with open('BeoModern_init_settings.txt', 'r') as saved_settings:
            lines = saved_settings.readlines()
# close BeoModern_init_settings.txt file
        saved_settings.close()

                        
# check if restorign DAB parameters        
        if mode == 'DAB':
# DAB radio data format: first;;second;;....
#    first = number of all detected stations
#    second = last tuned station
#    third = Frequency Index for last tuned station
#    forth = Component ID for last tuned station
#    fifth = Service ID for last tuned station
#    sixth = Label for last tuned station
            dab_settings = lines[0].split(';;')
# return list with last Player settigns 
            return (dab_settings)


# check if restorign iRadio parameters        
        elif mode == 'iRadio':
# iRadio radio data format: first;;second;;....
#    first = internet Radio station name
#    second = internet radio station address
            iRadio_settings = lines[2].split(';;')
# return list with last Player settigns 
            return (iRadio_settings)

            
# check if restorign Player parameters
        elif mode == 'Player':
# Player data format in second line: first;;second;;....
#    first = path to folder with files played last
#    second = file that was played last
#    third = position in the file where playing stopped
            Player_settings = lines[1].split(';;')
# return list with last Player settigns 
            return (Player_settings)

            
        else:
            return False
 
            
# check if function shoudl save        
    if operation == "store":
# open and read back BeoModern_init_settings.txt file into variable lines 
        with open('BeoModern_init_settings.txt', 'r') as saved_settings:
            lines = saved_settings.readlines()
# close BeoModern_init_settings.txt file
        saved_settings.close()


# check if saving DAB parameters
        if mode == 'DAB':
# save current DAB settings into BeoModern_init_settings.txt file
# format: first;;second;;....
#   first = number of all detected stations
#   second = current station
#   third = Frequency Index for current station
#   forth = Component ID for current station
#   fifth = Service ID for current station#
#   sixth = Label for current station
            lines[0] = (
             str(to_store['number_of_stations']) + ';;' +
             str(to_store['current_station']) + ';;' +
             str(to_store['Freq_Index']) + ';;' +
             str(to_store['Comp_ID']) + ';;' +
             str(to_store['Service_ID']) + ';;' +
             str(to_store['Label']) + '\n')
# open and write back BeoModern_init_settings.txt file with new line 0 content         
            with open('BeoModern_init_settings.txt', 'w') as saved_settings:
                saved_settings.writelines(lines)
# close BeoModern_init_settings.txt file
            saved_settings.close()
            return True


# check if saving iRadio parameters
        elif mode == 'iRadio':
# prepare new line content with latest settings
            lines[2] = (
             str(to_store['iRadio_name']) + ';;' +
             str(to_store['iRadio_address']) + '\n')
# open and write back BeoModern_init_settings.txt file with new line 2 content         
            with open('BeoModern_init_settings.txt', 'w') as saved_settings:
                saved_settings.writelines(lines)
# close BeoModern_init_settings.txt file
            saved_settings.close()
            return True


# check if saving Player parameters
        elif mode == 'Player':
# prepare new line content with latest settings
            lines[1] = (
             str(to_store['path']) + ';;' +
             str(to_store['file_name']) + ';;' +
             str(to_store['position']) + '\n')
# open and write back BeoModern_init_settings.txt file with new line 1 content         
            with open('BeoModern_init_settings.txt', 'w') as saved_settings:
                saved_settings.writelines(lines)
# close BeoModern_init_settings.txt file
            saved_settings.close()
            return True


        else:
            return False
        



################################################################################
# Main State Machine
################################################################################

class StateMachine(object):
    """ Main state machine handles UART command interpretation 
        and movement between states """
    def __init__(self):
        self.state = None
        self.states = {}
        self.paused_state = None
        self.last_command = False

    def add_state(self, state):
        self.states[state.name] = state
        log('state_Main = Adding state')
    """ Gentle movement between states """
    def go_to_state(self, state_name):
        if self.state:
            log('state_Main = Exiting %s' % (self.state.name))
            self.state.exit(self)
        self.state = self.states[state_name]
        log('state_Main = Entering %s' % (self.state.name))
        self.state.enter(self)
    """ Checking UART status and interpretting comamnds """
    def update(self):
        self.last_command = command_read()
        if self.last_command:
            log('state_Main = update = command = %s' % (self.last_command))
            if (self.last_command == 'Player' 
                  or self.last_command == 'iRadio' 
                  or self.last_command == 'DAB' 
                  or self.last_command == 'RDS'
                  or self.last_command == 'SHUTDOWN'):
                log('state_Main = update = go to = %s' % (self.state.name))
                self.go_to_state(self.last_command)
        if self.state:
            log('state_Main = Updating %s' % (self.state.name))
            self.state.update(self)




################################################################################
# Sub States
################################################################################



################################################################################
# Abstract parent state class.
################################################################################
class State(object):

    def __init__(self):
        pass

    @property
    def name(self):
        return ''

    def enter(self, machine):
        pass

    def exit(self, machine):
        pass

    def update(self, machine):
        pass




################################################################################
# mp3/flac Player sub-state machine

################################################################################
class Player(State):
    def __init__(self):
        super().__init__()
# initialize general variables
        self.PATH = '/home/pi/BeoModern/Player' 
        self.folder_file_combo = 0      
# initialize varibles for active song names and their locations
        self.CURRENT_PATH = []
        self.current_position = 1.0
        self.now_playing = []
        self.now_playing_number = 0 
        self.folder_list = []
        self.file_list = []
# initialize varibles for temporary selected song names and their locations
        self.NEW_PATH = []
        self.new_folder_number = 0
        self.new_song_number = 0
        self.new_folder_list = [] 
        self.new_file_list = []
# provide variable for wait time when switching radio staiton
        self.start_time = 0
# provide variable for pause/resume flag
        self.pause_flag = 0
# display variables
        self.display_time = 0
        self.rolling_title = 'rolling_title'
        self.display_flag = 0
        self.to_display = 'to_display'
# variables to store song informaitons
        self.song_artist = ''
        self.song_album = ''
        self.song_title = ''
        self.song_info = {}
# flag to indicate new song info
        self.song_info_flag = 0
  
 
    
    @property
    def name(self):
        log('state_Player = Name')
        return 'Player'



    def enter(self, machine):
        log('state_Player = Enter')

# restore last Player settings from disk file
        self.stored_settings = store_recall("Player", "recall")

# check if folder read back from file is still there in SD file structure       
        if (os.path.isdir(self.stored_settings[0])):
# if it is set to current path
            self.CURRENT_PATH = self.stored_settings[0]
# restore song position
            self.current_position = float(self.stored_settings[2])
        else:
# if it is not there any more set to default main Player path
            self.CURRENT_PATH = self.PATH
# set song position to beginning of the song
            self.current_position = 0

# call function to check and sort provided path
# returns sorted folder and file list
        (self.folder_list, self.file_list) = (
         Player.folder_check_and_sort(
         self.CURRENT_PATH))

# check file_name nubmer in the file folder. If exists return its index. 
# If does not exists return 0 (first file in forlder)
        for token in self.file_list:
            if token == self.stored_settings[1]:
                self.now_playing_number = self.file_list.index(token)


# check if there are playable files in the folder. 
# If there are set path to selected one            
        if (len(self.file_list) > 0):
            (self.now_playing.append(
              os.path.join(self.CURRENT_PATH, 
              self.file_list[self.now_playing_number])
              ))
            log (self.now_playing[0])


# calculate song nubmer based on current song + nubmer of sub-folders               
        self.folder_file_combo = self.now_playing_number + 1 + len(self.folder_list)
# set new song nubmer to current playing nubmer        
        self.new_song_number = self.now_playing_number
# set new foler list to current folder list
        self.new_folder_list = self.folder_list 
# set new file list to current file list
        self.new_file_list = self.file_list
# set new path to current path - this is for folder/song browsing
        self.NEW_PATH = self.CURRENT_PATH
       
# format path for mpc - remove absolute path and format it in reference to 
# default '/home/pi/BeoModern/Player' mpc folder
        self.mpc_file_to_play = (re.sub(self.PATH, '', 
                                  os.path.join(self.CURRENT_PATH, 
                                  self.file_list[self.now_playing_number]))
                                  [1:])


# set pointer to MPD client
        self.client = MPDClient()
# set delay timeouts
        self.client.timeout = 15
        self.client.idletimeout = None
# establish conenction with MPD server
        self.client.connect("127.0.0.1", 6600)
# set mpd to play in single mode
        self.client.single(1)
# set mpd volume to 100%
        self.client.setvol(100)
# clear mpd queue       
        self.client.clear()
# add file to mpd queue
        self.client.add(self.mpc_file_to_play)
# play first song in the playlist        
        self.client.play(0)
# move inside song to the time position read from stored file
        self.client.seek(0, self.current_position)
#        print(self.client.currentsong())
#        print(self.client.status())

# read current song info to display available data 
        self.song_info = self.client.currentsong()

# go to "Update" state of Player state machine
        State.update(self, machine)



    def exit(self, machine):
# store Player settings into disk file
        (store_recall("Player", "store", 
         path = self.CURRENT_PATH, 
         file_name = self.mpc_file_to_play, 
         position = float(self.client.status()["elapsed"])))
# stop playing song        
        self.client.stop()
# close mpd client
        self.client.close()
# disconnect from mpd server
        self.client.disconnect()
# print log message that informs about current state
        log('state_Player = Exit')
# move to main state machine exit state
        State.exit(self, machine)



    def update(self, machine):
        log('state_Player = Update')
# listen for UP or DOWN command. When received:
#   - increase/decrease index for current song/folder index. If exceeding nubmer 
#     of songs wrapp arround and brows thru sub-folder names
#   - if song -> sent over UART song number / number of all songs
#   - if folder -> sent over UART folder  number / number of folders
#   - set time start for wait time for GO command

# check if new command is UP
        if machine.last_command == 'UP':
            log('Player update = UP')
# increas folder_file index
            self.folder_file_combo += 1
# set display flag - reset rolling name
            self.display_flag = 1
# start timer                    
            self.start_time = time.monotonic()
            
# check if new command is DOWN
        if machine.last_command == 'DOWN':
            log('Player update = DOWN')
# decrease folder_file index
            self.folder_file_combo -= 1
# set display flag - reset rolling name
            self.display_flag = 1
# start timer                    
            self.start_time = time.monotonic()


# check if new pointer exceeds nubmer of files and sub-folders
# if exceeded - set new sub-folder to first one in main folder (value 0)
# set new song value to first song in catalog (value 0)
# wrap arround folder+file index (value 1)
        if self.folder_file_combo > (len(self.new_file_list) + len(self.new_folder_list)):
            self.new_folder_number = 0
            self.new_song_number = 0
            self.folder_file_combo = 1
# check if new pointer is less than zero
# if <= 0 wrap arround and point to last song in the folder
# set new folder number to number of sub-folders in main folder minus one
# set new file in the folder to nubmer of files in the folder minus one
# set folder+file index to sum of number of files and sub-folders in main folder
        elif self.folder_file_combo <= 0:
            self.new_folder_number = len(self.new_folder_list) - 1
            self.new_song_number = len(self.new_file_list) - 1 
            self.folder_file_combo = len(self.new_file_list) + len(self.new_folder_list)

# check if folder_file index points for folder list
# if so set new folder nubmer to folder+file index value minus one
        if self.folder_file_combo <= len(self.new_folder_list):
            self.new_folder_number = self.folder_file_combo - 1
            self.new_song_number = 0
            if self.display_flag == 1:
                self.rolling_title = self.new_folder_list[self.new_folder_number]
# reset display flag - continue rolling new name
                self.display_flag = 0
# check if folder_file index points for file list
# if so set new file nubmer to folder+file index value minus sub-folder nubmer minus one
# set new sub-folder nubmer ot nubmer of all subfolders in folder idicating that 
# now manipulaiton is with files not sub-folders
        elif self.folder_file_combo > len(self.new_folder_list):
            self.new_folder_number = len(self.new_folder_list)
            self.new_song_number = self.folder_file_combo - len(self.new_folder_list) - 1
            if self.display_flag == 1:
                self.rolling_title = self.new_file_list[self.new_song_number]
# reset display flag - continue rolling new name
                self.display_flag = 0

# check if current song is being played
        if (self.folder_file_combo == (self.now_playing_number + 1 + len(self.folder_list))
              and self.new_folder_list == self.folder_list 
              and self.new_file_list == self.file_list 
              ):

# check if artist data is supplied with song
# if so check if it is different to previus one
# if it is, update display information and set flag to display it 
# if not clear variable  
            if "artist" in self.song_info:
                if self.song_artist != self.song_info["artist"]:
                    self.song_artist = self.song_info["artist"]
                    self.song_info_flag = 1
            else:
                self.song_artist = ''
                
# check if album data is supplied with song
# if so check if it is different to previus one
# if it is, update display information and set flag to display it
# if not clear variable   
            if "album" in self.song_info:
                if self.song_album != self.song_info["album"]:
                    self.song_album = self.song_info["album"]
                    self.song_info_flag = 1
            else:
                self.song_album = ''

# check if title data is supplied with song
# if so check if it is different to previus one
# if it is, update display information and set flag to display it 
# if not clear variable            
            if "title" in self.song_info:
                if self.song_title != self.song_info["title"]: 
                    self.song_title = self.song_info["title"]
                    self.song_info_flag = 1
            else:
                self.song_title = ''

  
# check if all artist, album and title information are available with song 
# if they are check if this is new data
# if they are concatenate all 3 information and prepare them for display
# clear update flag
            if len(self.song_artist) > 0 and len(self.song_album) > 0 and len(self.song_title) > 0:
                if self.song_info_flag == 1:
                    self.to_display = self.song_artist + " - " + self.song_album + ": " + self.song_title
                    self.rolling_title = self.song_artist + " - " + self.song_album + ": " + self.song_title
                    self.song_info_flag = 0

# check if album and title information are available with song
# if they are, check if this is new data
# if they are concatenate both information and prepare them for display
# clear update flag
            elif len(self.song_artist) == 0 and len(self.song_album) > 0 and len(self.song_title) > 0:
                if self.song_info_flag == 1:
                    self.to_display = self.song_album + ": " + self.song_title
                    self.rolling_title = self.song_album + ": " + self.song_title
                    self.song_info_flag = 0

# if only album or only title data is available with song
# use file name only as song info displayed over UART
            else:
                self.to_display = self.new_file_list[self.new_song_number]

                
# write over UART file name and remining time in seconds   
            (self.display_time, self.rolling_title) = (display("Player_listening",
              self.display_time,
              remaining_time = int(float(self.client.currentsong()["duration"]) - float(self.client.status()["elapsed"])),
#              rolling_title = self.rolling_title,
#              title = self.new_file_list[self.new_song_number]))
              rolling_title = self.rolling_title,
              title = self.to_display))
# log currently player song name
            log(self.new_file_list[self.new_song_number])             

# check if new folder nubmer value equals number of folders in new location
# if that is the case means files are being browsed here
        elif self.new_folder_number == len(self.new_folder_list):
# write over UART file nubmer and its name   
            (self.display_time, self.rolling_title) = (display("Player_file_browsing",
              self.display_time,
              song_number = self.new_song_number+1,
              number_of_songs = len(self.new_file_list),
              rolling_title = self.rolling_title,
              title = self.new_file_list[self.new_song_number]))
# log new song name             
            log(self.new_file_list[self.new_song_number])                 

        else:
# write over UART folder number and its name
            (self.display_time, self.rolling_title) = (display("Player_folder_browsing",
              self.display_time,
              folder_number = self.new_folder_number+1,
              number_of_folders = len(self.new_folder_list),
              rolling_name = self.rolling_title,
              name = self.new_folder_list[self.new_folder_number]))
# log new folder name
            log(self.new_folder_list[self.new_folder_number])                

 
 
# - check if NEXT command is received. If YES:
#     - check if in folder/file combo shows activity. 
#       If YES check:
#         - check if timer is still below 5 seconds
#              - check if in folder refion of sub-folder content (files). 
#                if in folder region
#                   - check if now in dummy folder region. 
#                     If Not:
#                       - set new folder path location
#                       - re-check folder content lookign for sorted folder and file list
#                       - print content (debug) and start timer
#       If NO:
#           - advance current song by 10 seconds

# check if received comman was NEXT -> go down into folder tree
        if machine.last_command == 'NEXT':
# check if folder file combo value is differnet than current song plus nubmer 
# of subfolders. If it is, user started browsing folder structure. 
            if self.folder_file_combo != self.now_playing_number + len(self.folder_list) + 1:
# check if 5 seconds didn't pass yet
                if time.monotonic() <= self.start_time + 5:
# check if folder/file combo points to folder list
# by checking folder/file combo is less/equal nubmer of folders in directory 
# check if there are any folders in directory itself
                    if (0 < self.folder_file_combo) and (self.folder_file_combo <= len(self.new_folder_list)):
# check if new folder is not "BACK" foler used to get back from folder without sub-folders 
                        if (self.new_folder_list[0] != "BACK"):
# set candidate to new path based on new folder name
                            self.NEW_PATH = os.path.join(self.NEW_PATH, self.new_folder_list[self.new_folder_number])
# call function to check and sort provided path
# returns sorted folder and file list
                            (self.new_folder_list, self.new_file_list) = (
                             Player.folder_check_and_sort(
                             self.NEW_PATH))
# start timer                    
                            self.start_time = time.monotonic()
            else:
# advance current song by 10 seconds 
# check if position in curent song is no further than 10 seconds before end
# if it is do nothing
                if float(self.client.status()["elapsed"]) > (float(self.client.currentsong()["duration"]) - 10):
                    pass
                else:
# if not move by 10 seonds (advance)
                    self.client.seek(0, float(self.client.status()["elapsed"])+10)

 
 
# - check if NEXT command is received. If YES:
#     - check if in folder/file combo shows activity. 
#       If YES check:
#         - check if timer is still below 5 seconds
#              - check if in folder region of sub-folder content (files). 
#                if in folder region
#                   - set new folder path location
#                       - check if not in root folder. If so do not change path.
#                   - re-check folder content lookign for sorted folder and file list
#                   - print content (debug) and start timer
#       If NO:
#           - step back current song by 10 seconds
            
# check if received comman was BACK -> go up within folder tree
        if machine.last_command == 'BACK':
# check if folder file combo value is differnet than current song plus nubmer 
# of subfolders. If it is, user started browsing folder structure. 
            if self.folder_file_combo != self.now_playing_number + len(self.folder_list) + 1:
# check if 5 seconds didn't pass yet
                if time.monotonic() <= self.start_time + 5:
# check if folder/file combo points to folder list
# by checking folder/file combo is less/equal nubmer of folders in directory 
# check if there are any folders in directory itself
                    if (0 < self.folder_file_combo) and (self.folder_file_combo <= len(self.new_folder_list)):
# check if already in root directory. If so, can't go up. 
                        if self.NEW_PATH != self.PATH:
# set candidate to new path based on new folder name (one folder up)
                            self.NEW_PATH = os.path.split(self.NEW_PATH)[0]
                        else:
                            self.NEW_PATH = self.PATH
# call function to check and sort provided path
# returns sorted folder and file list
                        (self.new_folder_list, self.new_file_list) = (
                         Player.folder_check_and_sort(
                         self.NEW_PATH))
# start timer                    
                        self.start_time = time.monotonic()
            else:
# back current song by 10 seconds  
# check if position in curent song is at least 10 seconds in
# if it is not, start from beginning 
                if float(self.client.status()["elapsed"]) < 10:
                    self.client.seek(0, 0)
                    pass
# if it is, move back by in song 10 seconds
                else:
                    self.client.seek(0, float(self.client.status()["elapsed"])-10)



# check if new path is different to current path -> user browse folder tree 
        if ((self.NEW_PATH != self.CURRENT_PATH) 
              or (self.new_song_number != self.now_playing_number) 
              or (self.new_folder_number != len(self.new_folder_list))
              ):
# check if 5 seconds didn't pass yet
            if time.monotonic() <= self.start_time + 5:
# check if last vommand was GO
                if machine.last_command == 'GO':
# check if new folder is not "BACK" foler used to get back from folder 
# without sub-folders and prevent from executing GO when just browsing folders
                    if (((self.new_folder_list[0] == "BACK") 
                          and (self.folder_file_combo == 1)) 
                          or (self.new_folder_number != len(self.new_folder_list))
                          ):
                        return
                    else:
# check if new path is different to current path. 
# If yes browsing thru subfolders. If no browsing thru files. 
                        if (self.NEW_PATH != self.CURRENT_PATH):
# set new path to current path
                            self.CURRENT_PATH = self.NEW_PATH
# set new foler list to current folder list
                            self.folder_list = self.new_folder_list 
# set new file list to current file list
                            self.file_list = self.new_file_list                   
# set current song nubmer to new nubmer        
                        self.now_playing_number = self.new_song_number
# calculate song/file combo based on current song + nubmer of sub-folders               
                        self.folder_file_combo = self.now_playing_number + 1 + len(self.folder_list)
# format path for mpc - remove absolute path and format it in reference to 
# mpc path forlder set by default to '/home/pi/BeoModern/Player' folder
                        self.mpc_file_to_play = re.sub(self.PATH, '', os.path.join(self.CURRENT_PATH, self.file_list[self.now_playing_number]))[1:]
# clear mpd queue       
                        self.client.clear()
# add file to mpd queue
                        self.client.add(self.mpc_file_to_play)
# play first song in the playlist        
                        self.client.play()
# read current song info to display available data 
                        self.song_info = self.client.currentsong()


# clear all temporary changes
            else:
# set new path to current path
                self.NEW_PATH = self.CURRENT_PATH
# set new song nubmer to current playing nubmer        
                self.new_song_number = self.now_playing_number
# set new foler list to current folder list
                self.new_folder_list = self.folder_list 
# set new file list to current file list
                self.new_file_list = self.file_list               
# calculate song nubmer based on current song + nubmer of sub-folders               
                self.folder_file_combo = self.now_playing_number + 1 + len(self.folder_list)
# set display flag - reset rolling name
                self.display_flag = 1  


# NEED TO OPTIMIZE 1 SECOND STOP BEFORE SONG END
        if float(self.client.status()["elapsed"]) > (float(self.client.currentsong()["duration"]) - 1):
# NEED TO OPTIMIZE 1 SECOND STOP BEFORE SONG END
            self.client.pause(1)
# increment song nubmer to be played to next one in the folder
            self.now_playing_number += 1
# set current song nubmer to new nubmer        
            if self.now_playing_number >= len(self.file_list):
# if increment exceeds nubmer of songs, start playing first song again
                self.now_playing_number = 0
# calculate song/file combo based on current song + nubmer of sub-folders               
            self.folder_file_combo = self.now_playing_number + 1 + len(self.folder_list)  
# set display flag - reset rolling name
            self.display_flag = 1             
# format path for mpc - remove absolute path and format it in reference to 
# mpc path forlder set by default to '/home/pi/BeoModern/Player' folder
            self.mpc_file_to_play = re.sub(self.PATH, '', os.path.join(self.CURRENT_PATH, self.file_list[self.now_playing_number]))[1:]
# clear mpd queue       
            self.client.clear()
# add file to mpd queue
            self.client.add(self.mpc_file_to_play)
# play first song in the playlist        
            self.client.play()
# read current song info to display available data 
            self.song_info = self.client.currentsong()



# check if new command is STOP pause currently played song
        if machine.last_command == 'STOP':
            log('Player update = STOP')
# chekc if not in PAUSE state
            if self.pause_flag == 0:
# if no, pause current song
                self.client.pause(1)
# set pause flag to 1 - song paused - will be cleared next time when press STOP
                self.pause_flag = 1
            else:
# if yes, resume play of current song
                self.client.pause(0)
# clear pause flag to 0 - indicate song being played
                self.pause_flag = 0

# check if new command is GO while in pause state
        if (machine.last_command == 'GO') and (self.pause_flag == 1):
            log('Player update = GO')
# if yes, resume play of current song
            self.client.pause(0)
# clear pause flag to 0 - indicate song being played
            self.pause_flag = 0


# helps with sorting playlists following natural order
    def natural_key(el):
        """See http://www.codinghorror.com/blog/archives/001018.html"""
        return [int(s) if s.isdigit() else s for s in re.split(r'(\d+)', el)]  


# define function to check and sort folders and file in at indicated folder path
# returns sorted list of folders and files 
    def folder_check_and_sort (folder_path):
        folder_list = []
        file_list = []
# remove hidden files (i.e. ".thumb") possibly located in current folder
        raw_list = list(filter(lambda element: not element.startswith('.'), os.listdir(folder_path)))
# sort current folder following natural order
        raw_list = sorted(raw_list, key=Player.natural_key, reverse=False)
# prepeare list of folders and files in current folder         
        for file in raw_list:
            if (os.path.isdir(os.path.join(folder_path, file))):
                folder_list.append(file)
            else:
                file_list.append(file)
        if len(folder_list) == 0:
            folder_list.append("BACK")
# from list of files remove all files except mp3 and flac
# mp3 and flac files only list
        file_list = list(filter(lambda element: element.endswith('.mp3') | element.endswith('.flac'), file_list))
# sort current folder following natural order
        file_list = sorted(file_list, key=Player.natural_key, reverse=False)
# return sorted folder list and sorted file list     
        return (folder_list, file_list)




################################################################################
# Internet Radio Player sub-state machine

################################################################################
class iRadio(State):
    """Internet Radio Player state machine"""
    def __init__(self):
        super().__init__()
# initialize varibles for active and selected radio stations
        self.current_istation = 0
        self.new_istation = 0
        self.number_of_istation = 0
        self.current_istation_name = ''
        self.current_istation_address = ''
        self.iRadio_stations = []       
# provide variable for wait time when switching radio staiton
        self.start_time = 0
# flag to indicate that user is browsing available radio stations
        self.station_change_flag = 0
# internet conenction check time interval
        self.internet_conenciton_check_interval = 0
# internet conneciton status
        self.internet_connection_state = 0
# iRadio status
        self.iRadio_status = {}
        self.display_name = ''
        self.display_title = ''
        self.title_update = 0
        self.name_update = 0
# display variables
        self.display_time = 0
        self.rolling_station = 'START iRADIO'
        self.to_display = 'START iRADIO'

        
    @property
    def name(self):
        log('state_iRadio = Name')
        return 'iRadio'

    def enter(self, machine):
# log indicator that iRadio enter state was executed       
        log('state_iRadio = Enter')
# at entering iRadio, parse iRadio_stations.txt file searching for number of 
# available internet radio stations
        with open('/home/pi/BeoModern/iRadio/iRadio_stations.txt', 'r') as iRadio_station_list:
            self.iRadio_stations = iRadio_station_list.readlines()
# close iRadio_stations.txt file
        iRadio_station_list.close()
        
# restore last DAB settings from disk file
        iRadio_settings = store_recall("iRadio", "recall")
        
# look for index of iRadio station name read from file 
        station_number = 0
        for token in self.iRadio_stations:
            station_number += 1
            if token.split(';;')[0] == iRadio_settings[0]:
                self.current_istation = station_number - 1
        
# set new station index to current station index        
        self.new_istation = self.current_istation
# set number of stations based on number of iRadio staions in iRadio_stations.txt file
        self.number_of_istation = len(self.iRadio_stations)
# set current and new iRadio station name to one read from the file
        self.current_istation_name = self.iRadio_stations[self.current_istation].split(';;')[0]
# set current and new iRadio station address to one read from the file 
# and remove new line character from the end
        self.current_istation_address = (self.iRadio_stations[self.current_istation].split(';;')[1])[:-1]
        
# DEBUG REMOVE DEBUG REMOVE
#        print(self.number_of_istation)    # number of all detected stations
#        print(self.current_istation)    # number of current station (starting from 0)
#        print(self.current_istation_name)    # name of current iRadio station
#        print(self.current_istation_address)    # address of current iRadio staiton
# DEBUG REMOVE DEBUG REMOVE


# check if internet connection is alive
        if iRadio.internet_connection_check():
# set pointer to MPD client
            self.client = MPDClient()
# set delay timeouts
            self.client.timeout = 20
            self.client.idletimeout = None
# establish conenction with MPD server
            self.client.connect("127.0.0.1", 6600)
# set mpd to play in single mode
            self.client.single(1)
# set mpd volume to 100%
            self.client.setvol(100)
# clear mpd queue       
            self.client.clear()
# add iRadio station address to mpd queue
            self.client.add(self.current_istation_address)

# play first song which is iRadio station address 
            self.client.play(0)
# set display parameters to restored iRadio station name
            self.rolling_station = self.current_istation_name
            self.to_display = self.current_istation_name
            self.internet_connection_state = 1
            # go to "Update" state of iRadio state machine
            State.update(self, machine)
        else:
            self.internet_connection_state = 0
# display information about offline status
            self.to_display = "OFFLINE"
            self.rolling_station = "OFFLINE"
# move to main state machine exit state
            State.exit(self, machine)



    def exit(self, machine):
# store current iRadio settings into disk file
        (store_recall("iRadio", "store", 
          iRadio_name = self.current_istation_name, 
          iRadio_address = self.current_istation_address))
# check if internet conneciton is alive before killing server        
        if iRadio.internet_connection_check():
# stop playing iRadio        
            self.client.stop()
# close mpd client
            self.client.close()
# disconnect from mpd server
            self.client.disconnect()
# print log message that informs about current state
        log('state_iRadio = Exit')
# move to main state machine exit state
        State.exit(self, machine)


# respond to UP/DOWN/GO commands and update display informaiton based on 
# received iRradio station name and data
    def update(self, machine):
#        log('state_iRadio = Update')
#        print(self.client.currentsong())
#        print(self.client.status())

# listen for UP command. When received:
#   - increase index for new iRadio staiton,
#   - sent over UART new station (upper) / all stations
#   - sent over UART new station name
#   - set time start for wait time for GO command
        if machine.last_command == 'UP':
            self.new_istation += 1
            if self.new_istation >= self.number_of_istation:
                self.new_istation = 0
            log('iRadio update = UP')
# update display info with proposed station name
            self.to_display = self.iRadio_stations[self.new_istation].split(';;')[0]
            self.rolling_station = self.to_display
# start timer for GO command
            self.start_time = time.monotonic()
# set browsing flag indicating that user started to browse available radio stations
            self.station_change_flag = 1
            log(self.new_istation)

# listen for DOWN command. When received:
#   - decrease index for new iRadio staiton,
#   - sent over UART new station (lower) / all stations
#   - sent over UART new station name
#   - set time start for wait time for GO command
        if machine.last_command == 'DOWN':
            self.new_istation -= 1
            if self.new_istation < 0: 
                self.new_istation = self.number_of_istation-1
            log('iRadio update = DOWN')
# update display info with proposed station name
            self.to_display = self.iRadio_stations[self.new_istation].split(';;')[0]
            self.rolling_station = self.to_display
# start timer for GO command
            self.start_time = time.monotonic()
# set browsing flag indicating that user started to browse available radio stations
            self.station_change_flag = 1
            log(self.new_istation)


# check if new station browsing flag is set. If so:
#   - check if 5 second didn't pass since new station was indicated. If not:
#        - check if GO command was recived
#              - if it was received:
#                    - select new iRadio station indicator as current iRadio station
#                    - set new iRadio station name to be updated over UART
#              - if it wasn't:
#                    - set new iRadio station indicator to current indicator
#                    - set new iRadio station name to be updated over UART 
#        if self.new_istation != self.current_istation:
        if self.station_change_flag == 1:
            if time.monotonic() <= self.start_time + 5:
                if machine.last_command == 'GO' and self.internet_connection_state == 1:
                    log('receive GO command')
                    self.current_istation = self.new_istation
# set current iRadio station name to new one indicated by new number
                    self.current_istation_name = self.iRadio_stations[self.current_istation].split(';;')[0]
# set current iRadio station address to new one indicated by new number
# and remove new line character from the end
                    self.current_istation_address = (self.iRadio_stations[self.current_istation].split(';;')[1])[:-1]
# clear mpd queue       
                    self.client.clear()
# add new iRadio address to mpd queue
                    self.client.add(self.current_istation_address)
# play new iRadio address         
                    self.client.play()
# clear browsing flag indicating that user finished browsing available radio stations                    
                    self.station_change_flag = 0
# assign current iRadio station name to display
                    self.to_display = self.current_istation_name
                    self.rolling_station = self.current_istation_name
# reset song/title info to re-display it
                    self.display_title = ''
                    self.display_name = ''                    

            else:
# revert back to currently playing radio station name to be displayed
                self.new_istation = self.current_istation
# clear browsing flag indicating that user finished browsing available radio stations 
                self.station_change_flag = 0
# assign current iRadio station name to display
                self.to_display = self.current_istation_name
                self.rolling_station = self.current_istation_name
# reset song/title info to re-display it
                self.display_title = ''
                self.display_name = ''
            
            
# check if internet conneciton is alive
        if time.monotonic() > self.internet_conenciton_check_interval + 2:
            if iRadio.internet_connection_check():
                self.internet_connection_state = 1
            else:
                self.internet_connection_state = 0
# display information about offline status
                self.to_display = "OFFLINE"
                self.rolling_station = "OFFLINE"
# reset song/title info 
                self.display_title = ''
                self.display_name = '' 
# reset internet conenciton timeout                
            self.internet_conenciton_check_interval = time.monotonic()


# check if iRadio station browsing or listening 
        if self.new_istation == self.current_istation and self.internet_connection_state == 1:
# read current song info
            self.iRadio_status = self.client.currentsong()
#            print (self.iRadio_status)
# check if title data exists
# if so check if it is different to previus one
# if it is, update display information and set flag to display it             
            if "title" in self.iRadio_status:
                if self.display_title != self.iRadio_status["title"]: 
                    self.display_title = self.iRadio_status["title"]
                    self.title_update = 1
            else:
                self.display_title = ''
# check if name data exists
# if so check if it is different to previus one
# if it is, update display information and set flag to display it   
            if "name" in self.iRadio_status:
                if self.display_name != self.iRadio_status["name"]:
                    self.display_name = self.iRadio_status["name"]
                    self.name_update = 1
            else:
                self.display_name = ''
# cehck if both name and title variables contains data
# check if both flags are set.
# if they are concatenate both information and prepare them for display
# if only one data got updated (like song name but not title) update
# coresponding part of the message displayed over UART
# clear relevant update flag/flags
            if len(self.display_name) > 0 and len(self.display_title) > 0:
                if self.name_update == 1 and self.title_update == 1:
                    self.to_display = self.display_name + ": " + self.display_title
                    self.rolling_station = self.display_name + ": " + self.display_title
                    self.title_update = 0
                    self.name_update = 0
                if self.name_update == 0 and self.title_update == 1:
                    self.to_display = self.display_name + ": " + self.display_title
                    self.rolling_station = self.display_name + ": " + self.display_title
                    self.title_update = 0
                if self.name_update == 1 and self.title_update == 0:
                    self.to_display = self.display_name + ": " + self.display_title
                    self.rolling_station = self.display_name + ": " + self.display_title
                    self.name_update = 0
# check if only title variable have data and name variable is empty (no name data)
# check if only title flag is set and name data flag is cleared (new title data)
# if it is sent title data to display variable. 
# Rolling display variable needs to be flushed out.
# do not clear flag leaving ability to add name to display later on
            elif len(self.display_name) == 0 and len(self.display_title) > 0:
                if self.name_update == 0 and self.title_update == 1:
                    self.to_display = self.display_title
# check if only name variable have data and title variable is empty (no title data)
# check if only name flag is set and title data flag is cleared (new name data)
# if it is sent name data to display variable
# Rolling display variable needs to be flushed out.
# do not clear flag leaving ability to add title to display later on
            elif len(self.display_name) > 0 and len(self.display_title) == 0:
                if self.name_update == 1 and self.title_update == 0:
                    self.to_display = self.display_name
            else:
                pass

# write over UART iRadio station name   
            (self.display_time, self.rolling_station) = (display("iRadio_listening",
              self.display_time,
              connection_state = self.internet_connection_state,
              rolling_station = self.rolling_station,
              station = self.to_display))
# log currently played iRadio station name
            log(self.to_display) 
            
        else:
# write over UART iRadio station number info and iRadio station name  
            (self.display_time, self.rolling_station) = (display("iRadio_browsing",
              self.display_time,
              connection_state = self.internet_connection_state,
              iRadio_station_number = self.new_istation+1,
              number_of_iRadio_stations = self.number_of_istation,
              rolling_station = self.rolling_station,
              station = self.to_display))
# log new song name             
            log(self.to_display)  
        pass


# check if internet conenciton is alive by pinging google and requesting HEAD.
# return True if alive. Return False if no connection.
    def internet_connection_check():
        conn = httplib.HTTPConnection("www.google.com", timeout = 3)
        try:
            conn.request("HEAD", "/")
            conn.close()
            return True
        except:
            conn.close()
            return False




################################################################################
# DAB Radio sub-state machine

################################################################################
class DAB(State):
    """DAB Radio Player state machine"""
    def __init__(self):
        super().__init__()
# initialize varibles for active and selected radio stations
        self.current_station = 0
        self.new_station = 0
        self.number_of_station = 0
# provide variable for wait time when switching radio staiton
        self.start_time = 0
# display variables
        self.display_time = 0
        self.rolling_station = 'START DAB'
        self.to_display = 'START DAB'
        
    @property
    def name(self):
        log('state_DAB = Name')
        return 'DAB'

    def enter(self, machine):
# at entering DAB radio, parse stationlist.txt file searching for DAB
# radio station informaion used by radio_cli software.
# Use nested dictionaries to store data
# Implementation utilize Service Number as radio station indicator
# This scan function assumes only one Frequency Index for channel list

        with open('/home/pi/BeoModern/DAB/stationlist.txt', 'r') as self.dab_station_list:
            for row in self.dab_station_list:
                if 'Freq. Index:' in row:
                    Freq_Index = row.strip('Freq. Index: \t\n\r')
                    
                if 'Service No.' in row:
                    Service_No = int(row.strip('Service No. \t\n\r'))
                    sortet_stationlist[Service_No]['Freq_Index'] = Freq_Index
                                
                if 'Service ID.' in row:
                    Service_ID = row.strip('Service ID. \t\n\r')
                    sortet_stationlist[Service_No]['Service_ID'] = Service_ID

                if 'Label' in row:
                    Label = row.strip('Label \t\n\r')
                    sortet_stationlist[Service_No]['Label'] = Label
                    
                if 'Comp ID' in row:
                    Comp_ID = row.strip('Comp ID \t\n\r')
                    sortet_stationlist[Service_No]['Comp_ID'] = Comp_ID

# restore last DAB settings from disk file
        dab_settings = store_recall("DAB", "recall")
# set DAB radio to restored settings
        self.number_of_station = int(dab_settings[0])
        self.current_station = int(dab_settings[1])
        self.new_station = self.current_station
        
# DEBUG REMOVE DEBUG REMOVE
#        print(dab_settings[0])    # pull number of all detected stations
#        print(dab_settings[1])    # pull last tuned station number
#        print(dab_settings[2])    # pull Frequency Index for last tuned station
#        print(dab_settings[3])    # pull Component ID for last tuned station
#        print(dab_settings[4])    # pull Service ID for last tuned station
#        print(dab_settings[5])    # pull Label for last tuned station
# DEBUG REMOVE DEBUG REMOVE

# start DAB radio software with restored parameters
        output, error = (subprocess.Popen(['sudo', 
          '/home/pi/BeoModern/DAB/radio_cli_v1.4.0', 
          '-b', 'D', 
          '-o', '1', 
          '-c', dab_settings[3], 
          '-e', dab_settings[4], 
          '-f', dab_settings[2], 
          '-p'], 
          shell=False, 
          stdout=subprocess.PIPE).communicate())
        log(error)    # print error message
        
# set display parameters to restored radio station data
        self.rolling_station = dab_settings[5]
        self.to_display = dab_settings[5]
        
        log('state_DAB = Enter')
# move to update state
        State.update(self, machine)


    def exit(self, machine):
# save current DAB settings into BeoModern_init_settings.txt file on disk
        (store_recall("DAB", "store", 
          number_of_stations = len(sortet_stationlist),
          current_station = self.current_station,
          Freq_Index = sortet_stationlist[self.current_station]['Freq_Index'],
          Comp_ID = sortet_stationlist[self.current_station]['Comp_ID'],
          Service_ID = sortet_stationlist[self.current_station]['Service_ID'],
          Label = sortet_stationlist[self.current_station]['Label']))
        log('state_DAB = Exit')
# close DAB radio software 
        output, error = (subprocess.Popen(['sudo', 
          '/home/pi/BeoModern/DAB/radio_cli_v1.4.0', 
          '-k'], 
          shell=False, 
          stdout=subprocess.PIPE).communicate())
        log(error)    # print error message
# exit DAB state machine
        State.exit(self, machine)


# respond to UP/DOWN/GO commands and update display informaiton based on 
# received radio station name and data
    def update(self, machine):
        log('state_DAB = Update')

# listen for UP command. When received:
#   - increase index for new radio staiton,
#   - sent over UART new station (upper) / all stations
#   - sent over UART new station name
#   - set time start for wait time for GO command
        if machine.last_command == 'UP':
            self.new_station += 1
            if self.new_station >= self.number_of_station:
                self.new_station = 0
            log('DAB update = UP')
# update display info with proposed station name
            self.rolling_station = str(sortet_stationlist[self.new_station]['Label'])
# start timer for GO command
            self.start_time = time.monotonic()
            log(self.new_station)

# listen for DOWN command. When received:
#   - decrease index for new radio staiton,
#   - sent over UART new station (lower) / all stations
#   - sent over UART new station name
#   - set time start for wait time for GO command
        if machine.last_command == 'DOWN':
            self.new_station -= 1
            if self.new_station < 0: 
                self.new_station = self.number_of_station-1
            log('DAB update = DOWN')
# update display info with proposed station name
            self.rolling_station = str(sortet_stationlist[self.new_station]['Label'])
# start timer for GO command
            self.start_time = time.monotonic()
            log(self.new_station)

# check if new station command was received. If so:
#   - check if 5 second didn't pass since new station was indicated. If not:
#        - check if GO command was recived
#              - if it was received:
#                    - select new radio station indicator as current radio station
#                    - set new radio station name to be updated over UART
#              - if it wasn't:
#                    - set new radio station indicator to current indicator
#                    - set new radio station name to be updated over UART 
        if self.new_station != self.current_station:
            log('self.new_station != self.current_station')
            if time.monotonic() <= self.start_time + 5:
                log('time.monotonic() <= self.start_time + 5')
                log(self.new_station)
                if machine.last_command == 'GO':
                    self.current_station = self.new_station
                    log('receive GO command')
                    output, error = (subprocess.Popen(['sudo', 
                      '/home/pi/BeoModern/DAB/radio_cli_v1.4.0', 
                      '-b', 'D', 
                      '-o', '1', 
                      '-c', sortet_stationlist[self.current_station]['Comp_ID'] , 
                      '-e', sortet_stationlist[self.current_station]['Service_ID'] , 
                      '-f', sortet_stationlist[self.current_station]['Freq_Index'] , 
                      '-p'], 
                      shell=False, 
                      stdout=subprocess.PIPE).communicate())
                    self.to_display = str(sortet_stationlist[self.current_station]['Label'])
                    self.rolling_station = str(sortet_stationlist[self.current_station]['Label'])
                    log(error)    # print error message
            else:
                self.new_station = self.current_station
                self.rolling_station = str(sortet_stationlist[self.current_station]['Label'])
                self.to_display = str(sortet_stationlist[self.current_station]['Label'])
                log(self.new_station)

# check if station browsing or listening 
        if self.new_station == self.current_station:
# check if new DAB station update was received
            output, error = (subprocess.Popen(['sudo', 
              '/home/pi/BeoModern/DAB/radio_cli_v1.4.0', 
              '-D'], 
              stdout=subprocess.PIPE).communicate())
            log(error)
            last_lane = str(output).split('\\n\\n')[-1]
# if new update was received, format it and add it to displayed radio station name
            if (last_lane != 'Error getting service data ' and 
                  last_lane != 'SPI bus enabled.' and last_lane != "'"):
# DEBUG ONLY - not needed for normal operation
#                ser.write(bytes(last_lane[:-1] + '\r\n','UTF-8'))
# DEBUG ONLY - not needed for normal operation
                self.to_display = (str(
                  sortet_stationlist[self.current_station]['Label']) 
                  + ' -> ' + str(last_lane[:-1]))
                self.rolling_station = (str(
                  sortet_stationlist[self.current_station]['Label']) 
                  + ' -> ' + str(last_lane[:-1]))
# write over UART radio station name   
            (self.display_time, self.rolling_station) = (display("DAB_listening",
              self.display_time,
              rolling_station = self.rolling_station,
            station = self.to_display))
# log currently played radio station name
            log(self.to_display) 
            
        else:
# write over UART radio station number info and station name  
            (self.display_time, self.rolling_station) = (display("DAB_browsing",
              self.display_time,
              station_number = self.new_station+1,
              number_of_stations = self.number_of_station,
              rolling_station = self.rolling_station,
              station = str(sortet_stationlist[self.new_station]['Label'])))
# log new song name             
            log(str(sortet_stationlist[self.new_station]['Label']))  
        pass
            
            
            
            
################################################################################
# FM RDS Receiver sub-state machine
# used to display FM staion names read from file
# decoding of RDS data is not implemented something to play with in the future
# function tunes FM radio to radio stations selected from file
# audio data is available on I2S port (the same as DAB radio)

################################################################################
class RDS(State):
    """RF RDS receiver only state machine"""
    def __init__(self):
        super().__init__()
# display variables
        self.display_time = 0
        self.rolling_station = 'START RDS'
        self.to_display = 'START RDS'
        self.radio_tunned_flag = 0

    @property
    def name(self):
        log('state_RDS = Name')
        return 'RDS'


    def enter(self, machine):
        log('state_RDS = Enter')
# at entering RDS, parse RDS_stations.txt file to build array with 
# FM radio station numbers, frequencies and names separated by ";;"
# those names will be displayed in absence of RDS information
        with open('/home/pi/BeoModern/RDS/RDS_stations.txt', 'r') as RDS_station_list:
            self.RDS_stations = RDS_station_list.readlines()
# close RDS_stations.txt file
        RDS_station_list.close()
# move to update state        
        State.update(self, machine)
        

    def exit(self, machine):
        log('state_RDS = Exit')
        State.exit(self, machine)


# respond to FM_xx commands and update display informaiton based on 
# FM station names read from file or RDS data received and decoded 
    def update(self, machine):
        log('state_RDS = Update')

# listen for UART command. When received command starting with "FM_"
# decode number in follow up two digits
        command = machine.last_command
# check if there is new command
        if command != False:
# if it is, check if it startswith "FM_"
            if command[:-2] == 'FM_':
# if it does sent to UART name of th radio station extracted from RDS_Station.txt
# file. It is located after second set of ";;". New line character is removed 
# from end of the line. 
# Location in array is calculated based on command name (FM_xx) minus 1
                self.rolling_station = (self.RDS_stations[int(command[3:])-1].split(';;')[2])[:-1]
                self.to_display = (self.RDS_stations[int(command[3:])-1].split(';;')[2])[:-1]
                log((self.RDS_stations[int(command[3:])-1].split(';;')[2])[:-1])

# start FM radio software with freqeuncy read from file
# audio output in I2S format available on the same port as DAB radio
                output, error = (subprocess.Popen(['sudo', 
                  '/home/pi/BeoModern/RDS/radio_cli_v1.4.0', 
                  '-b', 'F', 
                  '-o', '1', 
                  '-F', str(int(float(self.RDS_stations[int(command[3:])-1].split(';;')[1]) * 1000)), 
                  '-p'], 
                  shell=False, 
                  stdout=subprocess.PIPE).communicate())
                log(str(int(float(self.RDS_stations[int(command[3:])-1].split(';;')[1]) * 1000)))
                log(error)    # print error message
# set flag indication radio station was tuned
                self.radio_tunned_flag = 1
# write over UART FM Radio station name   
        (self.display_time, self.rolling_station) = (display("RDS_info",
          self.display_time,
          RDS_or_name = 0,
          rolling_station = self.rolling_station,
          station = self.to_display))
# log currently played iRadio station name
        log(self.to_display) 
        
        
# check if radio statio is tuned to some FM frequency
        # if self.radio_tunned_flag == 1:
# # check if current FM station status and RDS data by reading message status
            # output, error = (subprocess.Popen(['sudo', 
              # '/home/pi/BeoModern/RDS/radio_cli_v1.4.0', 
              # '-r'], 
              # stdout=subprocess.PIPE).communicate())
            # log(error)
# check if there are any new RDS message flags set    
            # if (str(output).split('\\n')[-21])[-1] != '0' or (str(output).split('\\n')[-18])[-1] != '0' or (str(output).split('\\n')[-12])[-1] != '0':
                # print (str(output).split('\\n')[-22])        
                # print (str(output).split('\\n')[-21])
                # print (str(output).split('\\n')[-20])
                # print (str(output).split('\\n')[-19])        
                # print (str(output).split('\\n')[-18])
                # print (str(output).split('\\n')[-17])
                # print (str(output).split('\\n')[-16])        
                # print (str(output).split('\\n')[-15])
                # print (str(output).split('\\n')[-14])
                # print (str(output).split('\\n')[-13])        
                # print (str(output).split('\\n')[-12])
                # print (str(output).split('\\n')[-11])
                # print (str(output).split('\\n')[-10])        
                # print (str(output).split('\\n')[-9])
                # print (str(output).split('\\n')[-8])
                # print (str(output).split('\\n')[-7])        
                # print (str(output).split('\\n')[-6])
                # print (str(output).split('\\n')[-5])
                # print (str(output).split('\\n')[-4])
                # print (str(output).split('\\n')[-3])
# # write over UART RDS data - NOT IMPLEMENTED    
            # (self.display_time, self.rolling_station) = (display("RDS_info",
              # self.display_time,
              # RDS_or_name = 1,
              # rolling_station = self.rolling_station,
              # station = self.to_display))
        pass



################################################################################
# SHUTDOWN sub-state machine
# used to power off Raspberry Pi

################################################################################
class SHUTDOWN(State):
    """SHUTDOWN only state machine"""
    def __init__(self):
        super().__init__()


    @property
    def name(self):
        log('state_Shutdown = Name')
        return 'SHUTDOWN'


    def enter(self, machine):
        log('state_SHUTDOWN = Enter')
# at entering SHUTDOWN state sent SHUTDOWN informaiton over UART and 
# print it thru log function
        display("message", info = "SHUTDOWN RPi    ")
        log('SHUTDOWN RPi initiated...')
# then initialize Raspberry Pi shutdown procedure
        subprocess.Popen(['sudo', 'shutdown', '-h', 'now'], 
          shell=False, 
          stdout=subprocess.PIPE).communicate()
        



################################################################################
# Main code
# Create the state machine

################################################################################
BeoModern_machine = StateMachine()
BeoModern_machine.add_state(Player())
BeoModern_machine.add_state(iRadio())
BeoModern_machine.add_state(DAB())
BeoModern_machine.add_state(RDS())
BeoModern_machine.add_state(SHUTDOWN())

# configure RPi GPIO 27 as an output and set it high indicating to 
# main microprocessor that Raspberry Pi is up and ready to accept commands
GPIO.setmode (GPIO.BCM)
GPIO.setup (27,GPIO.OUT)
GPIO.output (27,1)

# initial loop that waits for selection of mode of operation for RPi
while True:
# listen for UART command. When received "Player", "iRadio", "DAB" or "RDS"
# start state machine and go to coresponding state
    command = command_read()
# check if there is new command
    if command != False:
# if it is, checkcommand type and go to coresponding state
        if command == 'Player':
            BeoModern_machine.go_to_state('Player')
            break
        elif command == 'iRadio':
            BeoModern_machine.go_to_state('iRadio')
            break
        elif command == 'DAB':
            BeoModern_machine.go_to_state('DAB')
            break
        elif command == 'RDS':
            BeoModern_machine.go_to_state('RDS')
            break
        elif command == 'SHUTDOWN':
            BeoModern_machine.go_to_state('SHUTDOWN')              
            break


while True:
    BeoModern_machine.update()
    
