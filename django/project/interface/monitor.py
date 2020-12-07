from django.utils import timezone
from django.http import JsonResponse
from .models import View, ViewTimelines, Timeline, TimelineContents, Content
from .scripts import file_manager
import os
import threading
import cv2
import base64
import numpy as np
import json
import ast
from datetime import datetime
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
        view.average_attention = json.dumps(dict())
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
    timestamp = int(request.POST['timestamp'])
    last_check = view.last_check

    view.display_time = view.display_time + ((timestamp - last_check) // 1000)
    view.last_check = timestamp

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
    view.last_start = int(request.POST['start_time'])
    view.last_check = int(request.POST['start_time'])

    view.save()
    return JsonResponse({
        'ack': True
    })


def viewer_detected(request):
    data = request.POST
    thread = threading.Thread(target=process_viewer, args=(data, ))
    thread.daemon = False
    thread.start()

    return JsonResponse({
        'ack': True
    })


def process_viewer(data):
    view = View.objects.get(mac=data['mac'])
    view_dict = view.as_dict()
    pr.refPt = (int(view.resolution.split(':')[0]) / 2, int(view.resolution.split(':')[1]) / 2)
    fr = df.FaceNet()

    path = fr.path_to_vectors
    list_files = os.listdir(path)
    id_size = len(list_files)

    frame_as_np = np.frombuffer(base64.b64decode(data['frame']), dtype=np.uint8)
    frame = cv2.imdecode(frame_as_np, flags=1)
    shape = ast.literal_eval(data['shape'][7:-2])
    bb = tuple(map(int, data['bb'][1:-1].split(', ')))
    rep = []

    rep.append(fr.calc_face_descriptor(frame, bb))

    calculated_attention = rc.recognition(fr, shape, bb, frame, rep, id_size)

    relative_time = float(data['relative_time'])
    for timeline in view_dict['timelines']:
        if timeline['duration'] < relative_time:
            relative_time -= timeline['duration']
            if relative_time < 0:
                relative_time = 0
            continue

        db_timeline = Timeline.objects.get(pk=timeline['pk'])
        timeline_average_attention = json.loads(db_timeline.average_attention)
        if timeline_average_attention == {}:
            timeline_average_attention = {calculated_attention['person']: [calculated_attention['value']]}
        else:
            if calculated_attention['person'] in timeline_average_attention.keys():
                timeline_average_attention[calculated_attention['person']].append(calculated_attention['value'])
            else:
                timeline_average_attention[calculated_attention['person']] = [calculated_attention['value']]

        db_timeline.average_attention = json.dumps(timeline_average_attention)
        db_timeline.save()

        break_flag = False
        for content in timeline['contents']:
            if content['duration'] < relative_time:
                relative_time -= content['duration']
                if relative_time < 0:
                    relative_time = 0
                continue

            db_content = Content.objects.get(pk=content['pk'])
            content_average_attention = json.loads(db_content.average_attention)
            if content_average_attention == {}:
                content_average_attention = {calculated_attention['person']: [calculated_attention['value']]}
            else:
                if calculated_attention['person'] in content_average_attention.keys():
                    content_average_attention[calculated_attention['person']].append(calculated_attention['value'])
                else:
                    content_average_attention[calculated_attention['person']] = [calculated_attention['value']]

            db_content.average_attention = json.dumps(content_average_attention)
            db_content.save()
            break_flag = True
            break

        if break_flag is True:
            break

    average_attention = json.loads(view.average_attention)
    if average_attention == {}:
        average_attention = {calculated_attention['person']: [calculated_attention['value']]}
    else:
        if calculated_attention['person'] in average_attention.keys():
            average_attention[calculated_attention['person']].append(calculated_attention['value'])
        else:
            average_attention[calculated_attention['person']] = [calculated_attention['value']]

    view.average_attention = json.dumps(average_attention)
    view.save()

    # pr.graphics(average_attention)
    # pr.save_data(average_attention)


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
