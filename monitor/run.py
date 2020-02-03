#!/usr/bin/python3

from time import sleep
from screeninfo import get_monitors
import os
import netifaces
from subprocess import Popen
import requests
import logging
import coloredlogs

logger = logging.getLogger('Monitor Logger')
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s.%(msecs)03d - %(name)s - %(levelname)s - %(message)s', datefmt="%H:%M:%S")
ch.setFormatter(formatter)
logger.addHandler(ch)
coloredlogs.install(level='DEBUG', logger=logger, fmt='%(asctime)s.%(msecs)03d - %(name)s - %(levelname)s - '
                                                      '%(message)s', datefmt="%H:%M:%S")
fileHandler = logging.FileHandler("{}.log".format('monitor'))
fileHandler.setFormatter(formatter)
logger.addHandler(fileHandler)
logger.propagate = False

SERVER_URL = 'http://dmmd.ieeta.pt/'
#SERVER_URL = 'http://localhost/'

class Monitor():
    resolution = ''
    mac = ''
    file_path = ''

    def __init__(self):
        logger.info('Initializing monitor')

        success = False
        while (not success):
            try:
                self.resolution = '%s:%s' % (get_monitors()[0].width, get_monitors()[0].height)
                success = True
            except:
                logger.info('Resolution not available. Retrying in 30s...')
                sleep(30)

        self.mac = self.get_mac()

        success = False
        while(not success):
            try:
                success = self.send_init_info()
            except:
                logger.info('Server offline. Retrying in 30s...')
                sleep(30)

        success = False
        while (not success):
            try:
                success = self.get_video()
                if not success:
                    logger.info('Video unavailable. Retrying in 30s...')
                    sleep(30)
            except:
                logger.info('Video unavailable. Retrying in 30s...')
                sleep(30)

        logger.info('Video download complete')

        omxp = Popen(['omxplayer','-g','-b','--no-osd','--loop','/home/pi/dmmd/monitor/view.mp4'])

        self.polling()


    def send_init_info(self):
        logger.info('Sending initial info to server')
        client = requests.session()

        client.get('%slogin' % SERVER_URL)
        csrftoken = client.cookies['csrftoken']

        login_data = dict(csrfmiddlewaretoken=csrftoken)

        client.post('%slogin/' % SERVER_URL, data=login_data)
        csrftoken = client.cookies['csrftoken']

        data = {
            'mac': self.mac,
            'resolution': self.resolution,
            'csrfmiddlewaretoken': csrftoken
        }

        response = client.post('%smonitor/new_monitor/' % SERVER_URL, data=data)

        client.close()

        if 'ack' in response.json():
            self.file_path = response.json()['file_path']
            return response.json()['ack']
        else:
            return False


    def get_video(self):
        logging.info('Getting video')
        client = requests.session()

        client.get('%slogin' % SERVER_URL)
        csrftoken = client.cookies['csrftoken']

        login_data = dict(csrfmiddlewaretoken=csrftoken)

        client.post('%slogin/' % SERVER_URL, data=login_data)
        csrftoken = client.cookies['csrftoken']

        data = {
            'csrfmiddlewaretoken': csrftoken
        }

        response = client.get(SERVER_URL + self.file_path, data=data, stream=True)

        if response.status_code == 404:
            client.close()
            return False

        handle = open('view.%s' % self.file_path.split('.')[-1] , 'wb')
        for chunk in response.iter_content(chunk_size=512):
            if chunk:
                handle.write(chunk)
        client.close()
        return True

    def check_for_changes(self):
        logging.info('Checking for changes')
        client = requests.session()

        client.get('%slogin' % SERVER_URL)
        csrftoken = client.cookies['csrftoken']

        login_data = dict(csrfmiddlewaretoken=csrftoken)

        client.post('%slogin/' % SERVER_URL, data=login_data)
        csrftoken = client.cookies['csrftoken']

        data = {
            'mac': self.mac,
            'csrfmiddlewaretoken': csrftoken
        }

        response = client.post(SERVER_URL + 'monitor/check_for_changes/', data=data)

        if response.status_code == 404:
            client.close()
            return False

        client.close()
        return response.json()['has_changed']

    def polling(self):
        while (True):
            try:
                sleep(60)
                has_changed = self.check_for_changes()
                if not has_changed:
                    logger.info('No changes detected. Retrying in 60s...')
                    continue

                logger.info('Changes detected. Downloading new video...')
                success = False
                while (not success):
                    try:
                        success = self.get_video()
                        if not success:
                            logger.info('Video unavailable. Retrying in 30s...')
                            sleep(30)
                    except:
                        logger.info('Video unavailable. Retrying in 30s...')
                        sleep(30)

                logger.info('Video download complete')

            except:
                logger.info('Server offline. Retrying in 60s...')
                sleep(60)

    def get_mac(self):
        ifaces = netifaces.interfaces()
        # find ethernet mac addr
        for iface in ifaces:
            if 'en' in iface:
                try:
                    mac = netifaces.ifaddresses(iface)[netifaces.AF_LINK][0]['addr'].upper()
                    logger.info('Found suitable MAC address from interface %s : %s' % (iface,mac))
                    return mac
                except:
                    logger.info('Ethernet MAC address not available')
                    break
        # find wlan0 mac addr
        try:
            mac = netifaces.ifaddresses('wlan0')[netifaces.AF_LINK][0]['addr'].upper()
            logger.info('Found suitable MAC address from interface %s : %s' % ('wlan0', mac))
            return mac
        except:
            logger.info('Wlan0 MAC address not available')
        for iface in ifaces:
            if iface[0] == 'w':
                try:
                    mac = netifaces.ifaddresses(iface)[netifaces.AF_LINK][0]['addr'].upper()
                    logger.info('Found suitable MAC address from interface %s : %s' % (iface, mac))
                    return mac
                except:
                    logger.info('%s MAC address not available' % iface)

Monitor()
