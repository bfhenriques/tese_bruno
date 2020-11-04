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
    viewing_time = request.POST['viewingtime']
    print('View got attention for {} seconds.'.format(viewing_time))

    return JsonResponse({
        'ack': True
    })


def image_upload(request):
    faces = json.loads(request.POST['faces'])
    print(faces)
    index = 1
    for face in faces['faces']:
        print(face)
        image = base64.b64decode(face)
        image_as_np = np.frombuffer(image, dtype=np.uint8)
        img = cv2.imdecode(image_as_np, flags=1)
        cv2.imshow('face'+str(index), img)
        index += 1

    return JsonResponse({
        'ack': True
    })
