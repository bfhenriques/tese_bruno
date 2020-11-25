from django.utils import timezone
from django.http import JsonResponse
from .models import View
from .scripts import file_manager
import os
import threading
import cv2
import base64
import numpy as np
import json
import ast
from .digitalsignage import FaceRecognition as df
from .digitalsignage import processing as pr
from .digitalsignage import main as rc


def new_monitor(request):
    view = View.objects.filter(mac=request.POST['mac'])

    if len(view) == 0:
        view = View()
        view.resolution = request.POST['resolution']
        view.mac = request.POST['mac']

        view.name = '(new)'
        view.creation_date = timezone.now()
        view.last_modified = timezone.now()
        view.display_time = 0.0
        view.has_changed = False
        view.configured = False

        view.save(force_insert=True)

        return JsonResponse({
            'ack': True,
            'file_path': 'interface/media/Views/%s.mp4' % view.pk
        })

    if view[0].resolution != request.POST['resolution']:
        os.remove('interface/media/Views/%s.mp4' % view[0].pk)

        view[0].resolution = request.POST['resolution']
        view[0].has_changed = False
        view[0].save()

        thread = threading.Thread(target=file_manager.create_view, args=(view[0].pk, view[0].resolution,))
        thread.daemon = False
        thread.start()

    return JsonResponse({
        'ack': True,
        'file_path': 'interface/media/Views/%s.mp4' % view[0].pk
    })


def check_for_changes(request):
    view = View.objects.get(mac=request.POST['mac'])
    view.display_time = view.display_time + 60

    '''try:
        info_json = json.loads(open('report-data/' + str(view.pk) + '.json', 'r').read())
        info_json['display_time'] = info_json['display_time'] + 60

        with open('report-data/' + str(view.pk) + '.json', 'w') as outfile:
            json.dump(info_json, outfile, ensure_ascii=False, indent=4)
    except FileNotFoundError:
        print('File not found')'''

    if view.has_changed:
        view.has_changed = False
        view.save()
        return JsonResponse({
            'has_changed': True
        })

    view.save()
    return JsonResponse({
        'has_changed': False
    })


def view_start(request):
    view = View.objects.get(mac=request.POST['mac'])
    view.last_start = request.POST['start_time']
    view.save()
    return JsonResponse({
        'ack': True
    })


def viewer_detected(request):
    print(request.POST['frame'])
    view = View.objects.get(mac=request.POST['mac'])
    pr.refPt = (int(view.resolution.split(':')[0]) / 2, int(view.resolution.split(':')[1]) / 2)
    fr = df.FaceNet()

    average_attention = {}

    path = fr.path_to_vectors
    list_files = os.listdir(path)
    id_size = len(list_files)

    for i in range(0, id_size):
        average_attention[i] = []

    frame_as_np = np.frombuffer(base64.b64decode(request.POST['frame']), dtype=np.uint8)
    frame = cv2.imdecode(frame_as_np, flags=1)
    shape = ast.literal_eval(request.POST['shape'][7:-2])
    bb = tuple(map(int, request.POST['bb'][1:-1].split(', ')))
    rep = []

    rep.append(fr.calc_face_descriptor(frame, bb))

    rc.recognition(fr, shape, bb, frame, rep, average_attention, id_size)

    pr.graphics(average_attention)
    pr.save_data(average_attention)

    return JsonResponse({
        'ack': True
    })


def report(request):
    print(request.POST)

    '''view = View.objects.get(mac=request.POST['mac'])
    viewing_time = request.POST['viewingtime']

    try:
        info_json = json.loads(open('report-data/' + str(view.pk) + '.json', 'r').read())
        info_json['viewing_time'] = info_json['viewing_time'] + float(viewing_time)

        with open('report-data/' + str(view.pk) + '.json', 'w') as outfile:
            json.dump(info_json, outfile, ensure_ascii=False, indent=4)

    except FileNotFoundError:
        print('File not found')'''

    return JsonResponse({
        'ack': True
    })


def image_upload(request):
    view = View.objects.get(mac=request.POST['mac'])
    faces = json.loads(request.POST['faces'])

    try:
        info_json = json.loads(open('report-data/' + str(view.pk) + '.json', 'r').read())
        if len(info_json['faces']) > 0:
            for face in faces['faces']:
                info_json['faces'].append(face)
        else:
            info_json['faces'] = faces['faces']

        with open('report-data/' + str(view.pk) + '.json', 'w') as outfile:
            json.dump(info_json, outfile, ensure_ascii=False, indent=4)

    except FileNotFoundError:
        print('File not found')

    '''index = 1
    for face in faces['faces']:
        image = base64.b64decode(face[2:-1])
        image_as_np = np.frombuffer(image, dtype=np.uint8)
        img = cv2.imdecode(image_as_np, flags=1)
        cv2.imwrite('./face'+str(index)+'.jpg', img)
        index += 1'''

    return JsonResponse({
        'ack': True
    })
