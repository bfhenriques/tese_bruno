#!/usr/bin/python3

import base64
from time import time, sleep
from datetime import datetime
from screeninfo import get_monitors
import os
import netifaces
from subprocess import Popen
import requests
import logging
import coloredlogs
import picamera
import numpy as np
import cv2
import threading
from threading import Thread, Event
import json
from omxplayer.player import OMXPlayer
import dlib


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

# SERVER_URL = 'http://dmmd.ieeta.pt/'
SERVER_URL = 'http://192.168.1.103/'

viewer_flag = Event()


class SharedSpace:
    detector = dlib.get_frontal_face_detector()
    predictor = dlib.shape_predictor('shape_predictor_68_face_landmarks.dat')
    resolution = ''
    mac = ''
    file_path = ''
    omxp = OMXPlayer

    def detect_face(self, image):
        gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        rects = self.detector(gray_image, 1)
        shape = []
        bb = []

        for (z, rect) in enumerate(rects):
            if rect is not None and rect.top() > 0 and rect.right() < gray_image.shape[1] and rect.bottom() < \
                    gray_image.shape[0] and rect.left() > 0:
                predicted = self.predictor(gray_image, rect)
                shape.append(self.shape_to_np(self, predicted))
                (x, y, w, h) = self.rect_to_bb(self, rect)
                bb.append((x, y, x + w, y + h))

        return shape, bb

    def shape_to_np(self, shape):
        landmarks = np.zeros((68, 2), dtype=int)

        for i in range(0, 68):
            landmarks[i] = (shape.part(i).x, shape.part(i).y)

        return landmarks

    def rect_to_bb(self, rect):
        x = rect.left()
        y = rect.top()
        w = rect.right() - x
        h = rect.bottom() - y

        return x, y, w, h

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

        handle = open('view.%s' % self.file_path.split('.')[-1], 'wb')
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
            'csrfmiddlewaretoken': csrftoken,
            'timestamp': int(round(time() * 1000))
        }

        response = client.post(SERVER_URL + 'monitor/check_for_changes/', data=data)

        if response.status_code == 404:
            client.close()
            return False

        client.close()
        return response.json()['has_changed']

    def report_view_start(self):
        logging.info('Reporting view start.')
        client = requests.session()

        client.get('%slogin' % SERVER_URL)
        csrftoken = client.cookies['csrftoken']

        login_data = dict(csrfmiddlewaretoken=csrftoken)

        client.post('%slogin/' % SERVER_URL, data=login_data)
        csrftoken = client.cookies['csrftoken']

        data = {
            'mac': self.mac,
            'csrfmiddlewaretoken': csrftoken,
            'start_time': int(round(time() * 1000))
        }

        response = client.post(SERVER_URL + 'monitor/view_start/', data=data)

        if response.status_code == 404:
            client.close()
            return False

        client.close()
        return True

    def viewer_detected(self, frame, shape, bb):
        logger.info('Viewer(s) detection start - absolute: {} - relative: {}'.format(time(), self.omxp.position()))

        success = False
        while not success:
            try:
                success = self.report_viewer_detected(self, frame, shape, bb)
                if not success:
                    logger.info('Problem reporting attention start')

            except:
                logger.info('Problem reporting attention start')

    def report_viewer_detected(self, frame, shape, bb):
        logging.info('Reporting attention start')
        client = requests.session()

        client.get('%slogin' % SERVER_URL)
        csrftoken = client.cookies['csrftoken']

        login_data = dict(csrfmiddlewaretoken=csrftoken)

        client.post('%slogin/' % SERVER_URL, data=login_data)
        csrftoken = client.cookies['csrftoken']

        data = {
            'mac': self.mac,
            'csrfmiddlewaretoken': csrftoken,
            'absolute_time': int(round(time() * 1000)),
            'relative_time': self.omxp.position(),
            'shape': str(shape),
            'bb': str(bb),
            'frame': frame
        }

        response = client.post(SERVER_URL + 'monitor/viewer_detected/', data=data)

        if response.status_code == 404:
            client.close()
            return False

        client.close()
        return True


class CameraThread(Thread):
    def __init__(self, shared, *args, **kwargs):
        super(CameraThread, self).__init__(*args, **kwargs)
        self.shared = shared

    def run(self):
        logger.info('Initializing Camera')

        with picamera.PiCamera() as camera:
            camera.resolution = (320, 240)
            camera.framerate = 24

            while True:
                frame = np.empty((240, 320, 3), dtype=np.uint8)
                camera.capture(frame, 'bgr')

                shape, bb = self.shared.detect_face(self.shared, frame)

                if len(shape) > 0:
                    for i in range(len(bb)):
                        # cropped_frame = frame[bb[i][1]:bb[i][3], bb[i][0]:bb[i][2]]
                        retval, buffer = cv2.imencode('.jpg', frame)
                        frame_as_text = base64.b64encode(buffer)
                        self.shared.viewer_detected(self.shared, frame_as_text, shape, bb[i])


class MonitorThread(Thread):
    def __init__(self, shared, *args, **kwargs):
        super(MonitorThread, self).__init__(*args, **kwargs)
        self.shared = shared

    def run(self):
        logger.info('Initializing Monitor')

        success = False
        while not success:
            try:
                self.shared.resolution = '%s:%s' % (get_monitors()[0].width, get_monitors()[0].height)
                success = True
            except:
                logger.info('Resolution not available. Retrying in 30s...')
                sleep(30)

        self.shared.mac = self.shared.get_mac(self.shared)

        success = False
        while not success:
            try:
                success = self.shared.send_init_info(self.shared)
            except:
                logger.info('Server offline. Retrying in 30s...')
                sleep(30)

        success = False
        while not success:
            try:
                success = self.shared.get_video(self.shared)
                if not success:
                    logger.info('Video unavailable. Retrying in 30s...')
                    sleep(30)
            except:
                logger.info('Video unavailable. Retrying in 30s...')
                sleep(30)

        logger.info('Video download complete')

        self.shared.omxp = OMXPlayer('/home/pi/dmmd/monitor/view.mp4', args=['-g', '-b', '--no-osd', '--loop'])

        self.shared.report_view_start(self.shared)

        while True:
            try:
                has_changed = self.shared.check_for_changes(self.shared)
                if not has_changed:
                    logger.info('No changes detected. Retrying in 60s...')
                    sleep(60)
                    continue

                logger.info('Changes detected. Downloading new video...')
                success = False
                while not success:
                    try:
                        success = self.shared.get_video(self.shared)
                        if not success:
                            logger.info('Video unavailable. Retrying in 30s...')
                            sleep(30)
                    except:
                        logger.info('Video unavailable. Retrying in 30s...')
                        sleep(30)

                logger.info('Video download complete')

                self.shared.omxp.load('/home/pi/dmmd/monitor/view.mp4')

                self.shared.report_view_start(self.shared)
            except:
                logger.info('Server offline. Retrying in 60s...')
                sleep(60)


threads = [
    CameraThread(SharedSpace),
    MonitorThread(SharedSpace)
]

for th in threads:
    th.start()
