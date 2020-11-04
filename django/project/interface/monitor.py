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


def new_monitor(request):
    view = View.objects.filter(mac=request.POST['mac'])

    if len(view) == 0:
        view = View()
        view.resolution = request.POST['resolution']
        view.mac = request.POST['mac']

        view.name = '(new)'
        view.creation_date = timezone.now()
        view.last_modified = timezone.now()
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

    if view.has_changed:
        view.has_changed = False
        view.save()
        return JsonResponse({
            'has_changed': True
        })

    return JsonResponse({
        'has_changed': False
    })


def report(request):
    view = View.objects.get(mac=request.POST['mac'])
    view_pk = view.pk
    viewing_time = request.POST['viewingtime']

    try:
        current_json = json.loads(open('report-data/' + str(view_pk) + '.json', 'r').read())
        current_json['viewing_time'] = current_json['viewing_time'] + float(viewing_time)

        with open('report-data/' + str(view_pk) + '.json', 'w') as outfile:
            json.dump(current_json, outfile, ensure_ascii=False, indent=4)

    except FileNotFoundError:
        print('File not found')

    return JsonResponse({
        'ack': True
    })


def image_upload(request):
    view = View.objects.get(mac=request.POST['mac'])
    view_pk = view.pk
    faces = json.loads(request.POST['faces'])

    try:
        current_json = json.loads(open('report-data/' + str(view_pk) + '.json', 'r').read())

        if len(current_json) > 0:
            for face in faces['faces']:
                current_json['faces'].append(face)
        else:
            current_json['faces'] = faces['faces']

        with open('report-data/' + str(view_pk) + '.json', 'w') as outfile:
            json.dump(current_json, outfile, ensure_ascii=False, indent=4)

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
