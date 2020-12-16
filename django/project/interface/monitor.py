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
from .digitalsignageimproved import demo

attention_time_increment = 1


def new_monitor(request):
    view = View.objects.filter(mac=request.POST['mac'])

    if len(view) == 0:
        view = View()
        view.resolution = request.POST['resolution']
        view.mac = request.POST['mac']

        view.name = '(new)'
        view.creation_date = timezone.now()
        view.last_modified = timezone.now()
        view.display_time = 0
        view.attention_time = 0
        view.has_changed = False
        view.configured = False
        view.average_attention = json.dumps(dict())
        view.recognition_confidence = 0.5
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
    with open('interface/digitalsignageimproved/data.txt') as json_file:
        ids = json.load(json_file)

    view = View.objects.get(mac=data['mac'])
    view_dict = view.as_dict()

    frame_as_np = np.frombuffer(base64.b64decode(data['frame']), dtype=np.uint8)
    frame = cv2.imdecode(frame_as_np, flags=1)
    dims = frame.shape
    shape, bb, raw_shape = demo.detect_face(frame)

    for i in range(len(bb)):
        key = demo.face_recognition(frame, raw_shape[i], ids, view.recognition_confidence)
        eulerAngles = demo.head_pose(dims, shape[i])
        calculated_attention = demo.calculate_attention(ids, key, eulerAngles)
        # This is the face sent from the raspberry, needs to be converted to grayscale for emotion recognition
        face = cv2.cvtColor(frame[bb[i][1]:bb[i][3], bb[i][0]:bb[i][2]], cv2.COLOR_BGR2GRAY)
        emotion = demo.emotion_recognition(face, ids, key)
        # this function is just for visualization and debugging, should be commented
        # demo.display(key, bb[i], shape[i], emotion, frame)
        # cv2.imwrite('interface/digitalsignageimproved/'+key+'.jpg', frame)

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
                timeline_average_attention = new_average_attention(key, calculated_attention, emotion, data['absolute_time'])
            elif key in timeline_average_attention.keys():
                timeline_average_attention[key]['average_attention'].append(calculated_attention)
                timeline_average_attention[key]['cumulative_attention'] += 1
                timeline_average_attention[key]['emotions'][emotion] += 1
                timeline_average_attention[key]['emotions_list'].append(emotion)
                timeline_average_attention[key]['frames'] += 1
                timeline_average_attention[key]['timestamps'].append(data['absolute_time'])
            else:
                timeline_average_attention[key] = new_average_attention_id(calculated_attention, emotion, data['absolute_time'])

            db_timeline.average_attention = json.dumps(timeline_average_attention)
            if db_timeline.attention_time is None:
                db_timeline.attention_time = attention_time_increment
            else:
                db_timeline.attention_time = db_timeline.attention_time + attention_time_increment
            db_timeline.save()

            break_flag = False
            for content in timeline['contents']:
                if content['duration'] * content['num_slides'] < relative_time:
                    relative_time -= content['duration'] * content['num_slides']
                    if relative_time < 0:
                        relative_time = 0
                    continue

                db_content = Content.objects.get(pk=content['pk'])
                content_average_attention = json.loads(db_content.average_attention)
                if content_average_attention == {}:
                    content_average_attention = new_average_attention(key, calculated_attention, emotion, data['absolute_time'])
                elif key in content_average_attention.keys():
                    content_average_attention[key]['average_attention'].append(calculated_attention)
                    content_average_attention[key]['cumulative_attention'] += 1
                    content_average_attention[key]['emotions'][emotion] += 1
                    content_average_attention[key]['emotions_list'].append(emotion)
                    content_average_attention[key]['frames'] += 1
                    content_average_attention[key]['timestamps'].append(data['absolute_time'])
                else:
                    content_average_attention[key] = new_average_attention_id(calculated_attention, emotion, data['absolute_time'])

                db_content.average_attention = json.dumps(content_average_attention)
                if db_content.attention_time is None:
                    db_content.attention_time = attention_time_increment
                else:
                    db_content.attention_time = db_content.attention_time + attention_time_increment
                db_content.save()
                break_flag = True
                break

            if break_flag is True:
                break

        average_attention = json.loads(view.average_attention)
        if average_attention == {}:
            average_attention = new_average_attention(key, calculated_attention, emotion, data['absolute_time'])
        elif key in average_attention.keys():
            average_attention[key]['average_attention'].append(calculated_attention)
            average_attention[key]['cumulative_attention'] += 1
            average_attention[key]['emotions'][emotion] += 1
            average_attention[key]['emotions_list'].append(emotion)
            average_attention[key]['frames'] += 1
            average_attention[key]['timestamps'].append(data['absolute_time'])
        else:
            average_attention[key] = new_average_attention_id(calculated_attention, emotion, data['absolute_time'])

        view.average_attention = json.dumps(average_attention)
        view.attention_time = view.attention_time + attention_time_increment
        view.display_time = view.display_time + ((int(data['absolute_time']) - view.last_check) // 1000)
        view.last_check = int(data['absolute_time'])
        view.save()

    with open('interface/digitalsignageimproved/data.txt', 'w') as outfile:
        json.dump(ids, outfile)


def new_average_attention(key, calculated_attention, emotion, timestamp):
    emotions = {
        "Neutral": 0,
        "Happiness": 0,
        "Surprise": 0,
        "Sadness": 0,
        "Anger": 0,
        "Disgust": 0,
        "Fear": 0,
        "Contempt": 0
    }
    emotions[emotion] += 1

    return {
        key: {
            'average_attention': [calculated_attention],
            'cumulative_attention': calculated_attention,
            'emotions': emotions,
            'emotions_list': [emotion],
            'frames': 1,
            'timestamps': [timestamp]
        }
    }


def new_average_attention_id(calculated_attention, emotion, timestamp):
    emotions = {
        "Neutral": 0,
        "Happiness": 0,
        "Surprise": 0,
        "Sadness": 0,
        "Anger": 0,
        "Disgust": 0,
        "Fear": 0,
        "Contempt": 0
    }
    emotions[emotion] += 1

    return {
            'average_attention': [calculated_attention],
            'cumulative_attention': calculated_attention,
            'emotions': emotions,
            'emotions_list': [emotion],
            'frames': 1,
            'timestamps': [timestamp]
        }
