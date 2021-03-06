from django.http import FileResponse, Http404
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.utils import timezone
from .models import View, Timeline, Content, TimelineContents, ViewTimelines, UserProfile
from .forms import UserCreateForm, UserEditForm, ContentForm, ContentEditForm, TimelineForm, ViewForm, ViewInfoForm
from .scripts import file_manager
import json
import threading
from django.http import FileResponse
from .digitalsignageimproved import demo
import datetime
from datetime import datetime
import matplotlib.pyplot as plt
import base64
from matplotlib.dates import (YEARLY, DateFormatter, rrulewrapper, RRuleLocator, drange)


def get_user_permissions(pk):
    if pk == 1:
        return {'pk': 1, 'contents': True, 'timelines': True, 'views': True, 'users': True, 'rec_conf': True}
    else:
        return UserProfile.objects.get(user_id=pk).as_dict()


def login(request):
    return render(request, 'registration/login.html')


@login_required
def index(request):
    return render(request, 'interface/home.html', {'permission': get_user_permissions(request.user.pk)})


#### VIEWS ####
@login_required
def views(request):
    if not get_user_permissions(request.user.pk)['views']:
        return render(request, 'error/access_denied.html')

    if request.user.pk == 1:
        views_list = View.objects.order_by('creation_date').all()
    else:
        views_list = View.objects.filter(permissions__user_id=request.user.pk)

    ret = []
    for view in views_list:
        ret.append(view.as_dict())

    context = {'views_list': ret, 'permission': get_user_permissions(request.user.pk)}
    return render(request, 'interface/View/view_views.html', context)


@login_required
def add_view(request):
    if not get_user_permissions(request.user.pk)['views']:
        return render(request, 'error/access_denied.html')

    if request.method == "POST":
        form = ViewForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            post.creation_date = timezone.now()
            post.last_modified = timezone.now()
            post.has_changed = True
            post.configured = False

            post.creator = request.user

            post.save()

            if request.user.pk != 1:
                view = View.objects.get(pk=post.pk)
                view.permissions.add(UserProfile.objects.get(user_id=request.user.pk))

            pks = request.POST.getlist('pks')

            for index in range(0, len(pks)):
                ViewTimelines.objects.create(view_id=post.id, timeline_id=pks[index], orderindex=index + 1)

            return redirect('view_views')
        return render(request, 'interface/View/add_view.html', {'form': form, 'permission': get_user_permissions(request.user.pk)})

    else:
        form = ViewForm()
        all_timelines = [timeline.as_dict() for timeline in Timeline.objects.order_by('creation_date')]
        context = {"form": form,
                   "all_timelines": json.dumps({"data": all_timelines}),
                   "table_timelines": json.dumps({"data": {}}),
                   'permission': get_user_permissions(request.user.pk)}
        return render(request, 'interface/View/add_view.html', context)


@login_required
def edit_view(request, pk):
    if not get_user_permissions(request.user.pk)['views']:
        return render(request, 'error/access_denied.html')

    if request.method == "POST":
        view = View.objects.get(pk=pk)
        form = ViewForm(request.POST, instance=view)
        if form.is_valid():
            post = form.save(commit=False)
            post.last_modified = timezone.now()
            post.has_changed = False
            post.configured = True
            post.save()

            ViewTimelines.objects.filter(view_id=pk).delete()

            pks = request.POST.getlist('pks')

            for index in range(0, len(pks)):
                ViewTimelines.objects.create(view_id=post.id, timeline_id=pks[index], orderindex=index + 1)

            thread = threading.Thread(target=file_manager.create_view, args=(view.pk, view.resolution, view.configured, ))
            thread.daemon = False
            thread.start()

            return redirect('view_views')
        return render(request, 'interface/View/edit_view.html', {'form': form, 'permission': get_user_permissions(request.user.pk)})

    else:
        view = View.objects.get(pk=pk)
        form = ViewForm(initial={
            'name': view.name,
            'recognition_confidence': view.recognition_confidence,
            'resolution': view.resolution,
            'mac': view.mac
        })

        table_timelines = []
        for timeline in ViewTimelines.objects.filter(view_id=pk).order_by("orderindex"):
            table_timelines.append(Timeline.objects.get(pk=timeline.timeline.pk).as_dict())

        all_timelines = [timeline.as_dict() for timeline in Timeline.objects.order_by('creation_date')]

        context = {"form": form,
                   "all_timelines": json.dumps({"data": all_timelines}),
                   "table_timelines": json.dumps({"data": table_timelines}),
                   'permission': get_user_permissions(request.user.pk),
                   'video_path': 'interface/media/Views/%s.mp4' % pk}
        return render(request, 'interface/View/edit_view.html', context)


@login_required
def info_view(request, pk):
    if not get_user_permissions(request.user.pk)['views']:
        return render(request, 'error/access_denied.html')

    view = View.objects.get(pk=pk)
    view_as_dict = view.as_dict()

    period_attention_chart = ''
    period_emotions_chart = ''
    period_recognitions = 0
    period_average_attention = 0
    period_cumulative_attention = 0
    period_emotions = {
        "Neutral": 0,
        "Happiness": 0,
        "Surprise": 0,
        "Sadness": 0,
        "Anger": 0,
        "Disgust": 0,
        "Fear": 0,
        "Contempt": 0
    }
    period_frames = 0

    if request.method == 'POST':
        start_time_ms = int(request.POST['start_time'])
        start_time = int(start_time_ms/1000)
        '''stage1_end_time_ms = int(request.POST['stage1_end_time'])
        stage1_end_time = int(stage1_end_time_ms / 1000)
        stage2_end_time_ms = int(request.POST['stage2_end_time'])
        stage2_end_time = int(stage2_end_time_ms / 1000)
        stage3_end_time_ms = int(request.POST['stage3_end_time'])
        stage3_end_time = int(stage3_end_time_ms / 1000)'''
        end_time_ms = int(request.POST['end_time'])
        end_time = int(end_time_ms / 1000)

        '''attention_array = [0 for i in list(range(0, start_time - end_time, 1))]
        emotions_array = ["" for i in list(range(0, start_time - end_time, 1))]
        time_array = list(range(start_time, end_time, 1))

        total_records = 0
        full_valid_data = []
        stage1_data = []
        stage2_data = []
        stage3_data = []
        stage4_data = []'''

        view_data = view_as_dict['average_attention']
        data = [i for i in range(0, len(view_data.keys()))]

        index = 0
        for key in view_data.keys():
            data[index] = view_data[key]
            index += 1

        total_timestamps = []
        total_attention_values = []
        total_emotions = []

        index = 0
        for subject in data:
            subject_valid_timestamps = []
            for timestamp in subject['timestamps']:
                if datetime.fromtimestamp(start_time) < datetime.fromtimestamp(int(timestamp) / 1000) \
                        < datetime.fromtimestamp(end_time):
                    subject_valid_timestamps.append(timestamp)

            if len(subject_valid_timestamps) > 0:
                period_recognitions += 1
                period_frames += len(subject_valid_timestamps)

            for timestamp in subject_valid_timestamps:
                total_attention_values.append(data[index]['average_attention'][subject['timestamps'].index(timestamp)])
                if data[index]['emotions_list'][subject['timestamps'].index(timestamp)] == 'Neutral':
                    period_emotions['Neutral'] += 1
                elif data[index]['emotions_list'][subject['timestamps'].index(timestamp)] == 'Happiness':
                    period_emotions['Happiness'] += 1
                elif data[index]['emotions_list'][subject['timestamps'].index(timestamp)] == 'Surprise':
                    period_emotions['Surprise'] += 1
                elif data[index]['emotions_list'][subject['timestamps'].index(timestamp)] == 'Sadness':
                    period_emotions['Sadness'] += 1
                elif data[index]['emotions_list'][subject['timestamps'].index(timestamp)] == 'Anger':
                    period_emotions['Anger'] += 1
                elif data[index]['emotions_list'][subject['timestamps'].index(timestamp)] == 'Disgust':
                    period_emotions['Disgust'] += 1
                elif data[index]['emotions_list'][subject['timestamps'].index(timestamp)] == 'Fear':
                    period_emotions['Fear'] += 1
                elif data[index]['emotions_list'][subject['timestamps'].index(timestamp)] == 'Contempt':
                    period_emotions['Contempt'] += 1

            index += 1

            '''total_timestamps += subject['timestamps']
            total_attention_values += subject['average_attention']
            total_emotions += subject['emotions_list']
            total_timestamps = [int(i) for i in total_timestamps]
            valid_timestamps = []
            stage1_timestamps = []
            stage2_timestamps = []
            stage3_timestamps = []
            stage4_timestamps = []
            for timestamp in total_timestamps:
                if datetime.fromtimestamp(start_time) < datetime.fromtimestamp(int(timestamp) / 1000) \
                        < datetime.fromtimestamp(end_time):
                    valid_timestamps.append(timestamp)
                if datetime.fromtimestamp(start_time) < datetime.fromtimestamp(int(timestamp) / 1000) \
                        < datetime.fromtimestamp(stage1_end_time):
                    stage1_timestamps.append(timestamp)
                if datetime.fromtimestamp(stage1_end_time) < datetime.fromtimestamp(int(timestamp) / 1000) \
                        < datetime.fromtimestamp(stage2_end_time):
                    stage2_timestamps.append(timestamp)
                if datetime.fromtimestamp(stage2_end_time) < datetime.fromtimestamp(int(timestamp) / 1000) \
                        < datetime.fromtimestamp(stage3_end_time):
                    stage3_timestamps.append(timestamp)
                if datetime.fromtimestamp(stage3_end_time) < datetime.fromtimestamp(int(timestamp) / 1000) \
                        < datetime.fromtimestamp(end_time):
                    stage4_timestamps.append(timestamp)

            valid_timestamps.sort()
            stage1_timestamps.sort()
            stage2_timestamps.sort()
            stage3_timestamps.sort()
            stage4_timestamps.sort()

            count = 0
            inner_count = 0
            missed_count = 0
            for timestamp in valid_timestamps:
                count += 1
                if round(timestamp / 1000) in time_array:
                    inner_count += 1
                    attention_array[time_array.index(round(timestamp / 1000))] = total_attention_values[
                        total_timestamps.index(timestamp)]
                    emotions_array[time_array.index(round(timestamp / 1000))] = total_emotions[
                        total_timestamps.index(timestamp)]
                else:
                    missed_count += 1

        plt.figure(figsize=(10, 6))
        plt.title(view_as_dict['name'] + ' Attention over time')
        plt.stem(list(range(0, start_time - end_time, 1)), attention_array)
        plt.xticks([0, 120, 240, 360, 480],
                   ['stage 1', 'stage 2', 'stage 3', 'stage4', 'end'])

        plt.savefig('interface/digitalsignageimproved/graphs/View_Attention_' + str(pk) + '.png')

        with open('interface/digitalsignageimproved/graphs/View_Attention_' + str(pk) + '.png',
                  "rb") as chart:
            attention_chart_as_text = base64.b64encode(chart.read())
            period_attention_chart = 'data:image/png;base64,' + attention_chart_as_text.decode('utf-8')

        plt.figure(figsize=(10, 6))
        plt.title(view_as_dict['name'] + ' Emotions over time')
        plt.stem(list(range(0, start_time - end_time, 1)), emotions_array)
        plt.xticks([0, 120, 240, 360, 480],
                   ['stage 1', 'stage 2', 'stage 3', 'stage4', 'end'])

        plt.savefig('interface/digitalsignageimproved/graphs/View_Emotions_' + str(pk) + '.png')

        with open('interface/digitalsignageimproved/graphs/View_Emotions_' + str(pk) + '.png',
                  "rb") as chart:
            emotions_chart_as_text = base64.b64encode(chart.read())
            period_emotions_chart = 'data:image/png;base64,' + emotions_chart_as_text.decode('utf-8')'''

        if len(total_attention_values) > 0:
            period_average_attention = sum(total_attention_values) / len(total_attention_values)
            period_cumulative_attention = sum(total_attention_values)

        form = ViewInfoForm(request.POST)
        period_active = True
    else:
        form = ViewInfoForm()
        period_active = False

    average_attention = json.loads(view.average_attention)
    attention_values = []
    average_attention_value = 0
    cumulative_attention_value = 0.0
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
    attention_chart = ''
    emotions_chart = ''
    entries_count = 0
    if len(average_attention.keys()) > 0:
        entries_count = 0
        for person in average_attention:
            attention_values += average_attention[person]['average_attention']
            entries_count += len(average_attention[person]['average_attention'])
            cumulative_attention_value += sum(average_attention[person]['average_attention'])
            emotions['Neutral'] += average_attention[person]['emotions']['Neutral']
            emotions['Happiness'] += average_attention[person]['emotions']['Happiness']
            emotions['Surprise'] += average_attention[person]['emotions']['Surprise']
            emotions['Sadness'] += average_attention[person]['emotions']['Sadness']
            emotions['Anger'] += average_attention[person]['emotions']['Anger']
            emotions['Disgust'] += average_attention[person]['emotions']['Disgust']
            emotions['Fear'] += average_attention[person]['emotions']['Fear']
            emotions['Contempt'] += average_attention[person]['emotions']['Contempt']

        average_attention_value = cumulative_attention_value / entries_count
        attention_chart = demo.attention_graphic('View', pk, attention_values)
        emotions_chart = demo.emotions_graphic('View', pk, emotions)

    if view.attention_time == 0 or view.display_time == 0:
        attention_percentage = 0.0
    else:
        attention_percentage = round(view.attention_time * 100 / view.display_time, 2)

    info = {
        'view': view_as_dict,
        'display_time': demo.hms(view.display_time),
        'attention_time': demo.hms(view.attention_time),
        'attention_percentage': attention_percentage,
        'average_attention': round(average_attention_value, 2),
        'cumulative_attention': round(cumulative_attention_value, 2),
        'attention_chart': attention_chart,
        'emotions_chart': emotions_chart,
        'number_of_recognitions': len(average_attention.keys()),
        'number_of_frames': entries_count,
        'period_active': period_active,
        'period_recognitions': period_recognitions,
        'period_frames': period_frames,
        'period_average_attention': round(period_average_attention, 2),
        'period_cumulative_attention': round(period_cumulative_attention, 2),
        'period_emotions': period_emotions,
        'period_attention_chart': '',
        'period_emotions_chart': ''
    }

    context = {'info': info,
               'form': form,
               'permission': get_user_permissions(request.user.pk)}

    return render(request, 'interface/View/info_view.html', context)


@login_required
def delete_view(request, pk):
    if not get_user_permissions(request.user.pk)['views']:
        return render(request, 'error/access_denied.html')

    view = View.objects.get(pk=pk)
    if view.configured and len(view.as_dict()['timelines']) > 0:
        file_manager.delete_file('interface/media/Views/%s.mp4' % view.pk)
    view.delete()

    return redirect('view_views')


#### TIMELINES ####
@login_required
def timelines(request):
    if not get_user_permissions(request.user.pk)['timelines']:
        return render(request, 'error/access_denied.html')

    if request.user.pk == 1:
        timelines_list = Timeline.objects.order_by('creation_date').all()
    else:
        timelines_list = Timeline.objects.filter(permissions__user_id=request.user.pk)

    ret = []
    for timeline in timelines_list:
        ret.append(timeline.as_dict())

    context = {'timelines_list': ret, 'permission': get_user_permissions(request.user.pk)}
    return render(request, 'interface/Timeline/view_timelines.html', context)


@login_required
def add_timeline(request):
    if not get_user_permissions(request.user.pk)['timelines']:
        return render(request, 'error/access_denied.html')

    if request.method == "POST":
        form = TimelineForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            post.creation_date = timezone.now()
            post.last_modified = timezone.now()
            post.has_changed = True
            post.duration = 0
            post.average_attention = {}
            post.attention_time = 0

            post.creator = request.user

            post.save()

            if request.user.pk != 1:
                timeline = Timeline.objects.get(pk=post.pk)
                timeline.permissions.add(UserProfile.objects.get(user_id=request.user.pk))

            pks = request.POST.getlist('pks')
            durations = request.POST.getlist('durations')

            for index in range(0, len(pks)):
                TimelineContents.objects.create(timeline_id=post.id, content_id=pks[index], orderindex=index+1,
                                                duration=durations[index], num_slides=1)

            if len(pks) > 0:
                thread = threading.Thread(target=file_manager.create_timeline, args=(post.pk,))
                thread.daemon = False
                thread.start()

            return redirect('view_timelines')
        return render(request, 'interface/Timeline/add_timeline.html', {'form': form, 'permission': get_user_permissions(request.user.pk)})

    else:
        form = TimelineForm()
        all_contents = [content.as_dict() for content in Content.objects.all()]
        for content in all_contents:
            if content['file_type'] == 'image':
                content['duration'] = 0

        context = {'form': form,
                   'all_contents': json.dumps({"data": all_contents}),
                   'table_contents': json.dumps({"data": {}}),
                   'permission': get_user_permissions(request.user.pk)}
        return render(request, 'interface/Timeline/add_timeline.html', context)


@login_required
def edit_timeline(request, pk):
    if not get_user_permissions(request.user.pk)['timelines']:
        return render(request, 'error/access_denied.html')

    if request.method == "POST":
        timeline = Timeline.objects.get(pk=pk)
        form = TimelineForm(request.POST, instance=timeline)
        if form.is_valid():
            post = form.save(commit=False)
            post.last_modified = timezone.now()
            post.has_changed = True
            post.save()

            TimelineContents.objects.filter(timeline_id=pk).delete()

            pks = request.POST.getlist('pks')
            durations = request.POST.getlist('durations')

            for index in range(0, len(pks)):
                TimelineContents.objects.create(timeline_id=post.id, content_id=pks[index], orderindex=index + 1,
                                                duration=durations[index], num_slides=1)

            if len(pks) > 0:
                thread = threading.Thread(target=file_manager.create_timeline, args=(post.pk,))
                thread.daemon = False
                thread.start()

            return redirect('view_timelines')
        return render(request, 'interface/Timeline/edit_timeline.html', {'form': form, 'permission': get_user_permissions(request.user.pk)})

    else:
        timeline = Timeline.objects.get(pk=pk)
        form = TimelineForm(initial={'name': timeline.name})

        table_contents = []
        for content in TimelineContents.objects.filter(timeline_id=pk).order_by("orderindex"):
            aux = content.content.as_dict()
            aux["duration"] = content.duration
            table_contents.append(aux)

        all_contents = [content.as_dict() for content in Content.objects.order_by('creation_date')]

        context = {"form": form,
                   "all_contents": json.dumps({"data": all_contents}),
                   "table_contents": json.dumps({"data": table_contents}),
                   'permission': get_user_permissions(request.user.pk),
                   'video_path': 'interface/media/Timelines/%s.mp4' % pk}
        return render(request, 'interface/Timeline/edit_timeline.html', context)


@login_required
def info_timeline(request, pk):
    if not get_user_permissions(request.user.pk)['timelines']:
        return render(request, 'error/access_denied.html')

    timeline = Timeline.objects.get(pk=pk)
    timeline_as_dict = timeline.as_dict()

    average_attention = json.loads(timeline.average_attention)
    attention_values = []
    average_attention_value = 0
    cumulative_attention_value = 0.0
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
    attention_chart = ''
    emotions_chart = ''
    entries_count = 0
    if len(average_attention.keys()) > 0:
        entries_count = 0
        for person in average_attention:
            attention_values += average_attention[person]['average_attention']
            entries_count += len(average_attention[person]['average_attention'])
            cumulative_attention_value += sum(average_attention[person]['average_attention'])
            emotions['Neutral'] += average_attention[person]['emotions']['Neutral']
            emotions['Happiness'] += average_attention[person]['emotions']['Happiness']
            emotions['Surprise'] += average_attention[person]['emotions']['Surprise']
            emotions['Sadness'] += average_attention[person]['emotions']['Sadness']
            emotions['Anger'] += average_attention[person]['emotions']['Anger']
            emotions['Disgust'] += average_attention[person]['emotions']['Disgust']
            emotions['Fear'] += average_attention[person]['emotions']['Fear']
            emotions['Contempt'] += average_attention[person]['emotions']['Contempt']

        average_attention_value = cumulative_attention_value / entries_count
        attention_chart = demo.attention_graphic('Timeline', pk, attention_values)
        emotions_chart = demo.emotions_graphic('Timeline', pk, emotions)

    info = {
        'timeline': timeline_as_dict,
        # 'display_time': demo.hms(view.display_time),
        'attention_time': demo.hms(timeline.attention_time),
        # 'attention_percentage': round(view.attention_time * 100 / view.display_time, 2),
        'average_attention': round(average_attention_value, 2),
        'cumulative_attention': round(cumulative_attention_value, 2),
        'attention_chart': attention_chart,
        'emotions_chart': emotions_chart,
        'number_of_recognitions': len(average_attention.keys()),
        'number_of_frames': entries_count
    }

    context = {'info': info,
               'permission': get_user_permissions(request.user.pk)}

    return render(request, 'interface/Timeline/info_timeline.html', context)


@login_required
def delete_timeline(request, pk):
    if not get_user_permissions(request.user.pk)['timelines']:
        return render(request, 'error/access_denied.html')

    timeline = Timeline.objects.get(pk=pk)
    file_manager.delete_file('interface/media/Timelines/%s.mp4' % timeline.pk)
    timeline.delete()
    return redirect('view_timelines')


#### CONTENTS ####
@login_required
def contents(request):
    if not get_user_permissions(request.user.pk)['contents']:
        return render(request, 'error/access_denied.html')

    if request.user.pk == 1:
        contents_list = Content.objects.order_by('creation_date').all()
    else:
        contents_list = Content.objects.filter(permissions__user_id=request.user.pk).all()

    ret = []
    for content in contents_list:
        ret.append(content.as_dict())

    context = {'contents_list': ret, 'permission': get_user_permissions(request.user.pk)}
    return render(request, 'interface/Content/view_contents.html', context)


@login_required
def add_content(request):
    if not get_user_permissions(request.user.pk)['contents']:
        return render(request, 'error/access_denied.html')

    if request.method == "POST":
        form = ContentForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.creation_date = timezone.now()
            post.last_modified = timezone.now()
            post.has_changed = True

            post.creator = request.user

            post.save()

            valid, path, file_type, duration = file_manager.handle_uploaded_content(request.FILES['file'], post.pk)

            content = Content.objects.get(pk=post.pk)
            if valid:
                content.path = path
                content.file_type = file_type
                if duration != 0:
                    content.video_duration = duration
                if request.user.pk != 1:
                    content.permissions.add(UserProfile.objects.get(user_id=request.user.pk))
                content.average_attention = json.dumps(dict())
                content.attention_time = 0
                content.save()
            else:
                content.delete()
                return render(request, 'error/file_error.html')

            return redirect('view_contents')
        return render(request, 'interface/Content/add_content.html', {'form': form, 'permission': get_user_permissions(request.user.pk)})

    else:
        form = ContentForm()
        return render(request, 'interface/Content/add_content.html', {'form': form, 'permission': get_user_permissions(request.user.pk)})


@login_required
def edit_content(request, pk):
    if not get_user_permissions(request.user.pk)['contents']:
        return render(request, 'error/access_denied.html')

    if request.method == "POST":
        content = Content.objects.get(pk=pk)
        old_name = content.name
        form = ContentEditForm(request.POST, request.FILES, instance=content)

        if form.is_valid() or 'file' not in request.FILES:
            post = form.save(commit=False)
            post.last_modified = timezone.now()
            post.has_changed = True
            post.save()

            if 'file' in request.FILES:
                valid, path, file_type = file_manager.handle_uploaded_content(request.FILES['file'], post.pk)
                if valid:
                    content.path = path
                    content.file_type = file_type
                    content.save()
                else: # revert
                    content.name = old_name
                    content.save()
                    return render(request, 'error/file_error.html')

            return redirect('view_contents')
        return render(request, 'interface/Content/edit_content.html', {'form': form, 'permission': get_user_permissions(request.user.pk)})

    else:
        form = ContentEditForm()
        content = Content.objects.get(pk=pk)
        ''' print(content.path)
        cache_path = '/tmp/preview_cache'
        pdf_or_odt_to_preview_path = content.path

        manager = PreviewManager(cache_path, create_folder=True)
        path_to_preview_image = manager.get_jpeg_preview(pdf_or_odt_to_preview_path) '''

        context = {'form': form,
                   'content': content,
                   'permission': get_user_permissions(request.user.pk)}

        return render(request, 'interface/Content/edit_content.html', context)
        # return FileResponse(open(content.path, 'rb'), content_type='application/pdf')


@login_required
def info_content(request, pk):
    if not get_user_permissions(request.user.pk)['contents']:
        return render(request, 'error/access_denied.html')

    content = Content.objects.get(pk=pk)
    content_as_dict = content.as_dict()

    average_attention = json.loads(content.average_attention)
    attention_values = []
    average_attention_value = 0
    cumulative_attention_value = 0
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
    attention_chart = ''
    emotions_chart = ''
    entries_count = 0
    if len(average_attention.keys()) > 0:
        entries_count = 0
        for person in average_attention:
            attention_values += average_attention[person]['average_attention']
            entries_count += len(average_attention[person]['average_attention'])
            cumulative_attention_value += sum(average_attention[person]['average_attention'])
            emotions['Neutral'] += average_attention[person]['emotions']['Neutral']
            emotions['Happiness'] += average_attention[person]['emotions']['Happiness']
            emotions['Surprise'] += average_attention[person]['emotions']['Surprise']
            emotions['Sadness'] += average_attention[person]['emotions']['Sadness']
            emotions['Anger'] += average_attention[person]['emotions']['Anger']
            emotions['Disgust'] += average_attention[person]['emotions']['Disgust']
            emotions['Fear'] += average_attention[person]['emotions']['Fear']
            emotions['Contempt'] += average_attention[person]['emotions']['Contempt']

        average_attention_value = cumulative_attention_value / entries_count
        attention_chart = demo.attention_graphic('Content', pk, attention_values)
        emotions_chart = demo.emotions_graphic('Content', pk, emotions)

    info = {
        'content': content_as_dict,
        # 'display_time': demo.hms(view.display_time),
        'attention_time': demo.hms(content.attention_time),
        # 'attention_percentage': round(view.attention_time * 100 / view.display_time, 2),
        'average_attention': round(average_attention_value, 2),
        'cumulative_attention': round(cumulative_attention_value, 2),
        'attention_chart': attention_chart,
        'emotions_chart': emotions_chart,
        'number_of_recognitions': len(average_attention.keys()),
        'number_of_frames': entries_count
    }

    context = {'info': info,
               'permission': get_user_permissions(request.user.pk)}

    return render(request, 'interface/Content/info_content.html', context)


@login_required
def download_content(request, pk):
    if not get_user_permissions(request.user.pk)['contents']:
        return render(request, 'error/access_denied.html')

    content = Content.objects.get(pk=pk)

    return FileResponse(open(content.path, 'rb'))


@login_required
def delete_content(request, pk):
    if not get_user_permissions(request.user.pk)['contents']:
        return render(request, 'error/access_denied.html')

    content = Content.objects.get(pk=pk)
    file_manager.delete_file(content.path)
    content.delete()
    return redirect('view_contents')


#### USERS ####
@login_required
def users(request):
    if not get_user_permissions(request.user.pk)['users']:
        return render(request, 'error/access_denied.html')

    users_list = []
    for user in UserProfile.objects.all().order_by('user__first_name'):
        users_list.append(user.as_dict())
    context = {'users_list': users_list, 'permission': get_user_permissions(request.user.pk)}
    return render(request, 'interface/User/view_users.html', context)


@login_required
def add_user(request):
    if not get_user_permissions(request.user.pk)['users']:
        return render(request, 'error/access_denied.html')

    if request.method == "POST":
        form = UserCreateForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('view_users')
    else:
        form = UserCreateForm()
        return render(request, 'interface/User/add_user.html', {'form': form, 'permission': get_user_permissions(request.user.pk)})


@login_required
def edit_user(request, pk):
    if pk == 0:
        pk = request.user.pk

    if request.user.pk != 1 and request.user.pk != pk:
        return render(request, 'error/access_denied.html')

    if request.method == "POST":
        user = User.objects.get(pk=pk)
        form = UserEditForm(request.POST, instance=user)
        if form.is_valid():
            user = form.save()
            user = UserProfile.objects.get(user=user)
            user.contents = form.cleaned_data['contents']
            user.timelines = form.cleaned_data['timelines']
            user.views = form.cleaned_data['views']
            user.save()
    else:
        form = UserEditForm()
        user = User.objects.get(pk=pk)
        user = UserProfile.objects.get(user=user).as_dict()
        context = {'form': form, 'user': user, 'permission': get_user_permissions(request.user.pk)}
        return render(request, 'interface/User/edit_user.html', context)

    return redirect('view_users')


@login_required
def delete_user(request, pk):
    if not get_user_permissions(request.user.pk)['users']:
        return render(request, 'error/access_denied.html')

    user = User.objects.get(pk=pk)
    user.delete()
    return redirect('view_users')


#### PERMISSIONS ####
@login_required
def permissions_contents(request, pk):
    if request.user.pk != 1:
        return render(request, 'error/access_denied.html')

    if request.method == 'POST':
        content = Content.objects.get(pk=pk)
        content.permissions.clear()

        users_pks = request.POST.getlist('permissions')

        for user_pk in users_pks:
            user = UserProfile.objects.get(user_id=user_pk)
            Content.objects.get(pk=pk).permissions.add(user)

        return redirect('view_contents')

    else:
        content = Content.objects.get(pk=pk).as_dict()
        users_list = []
        allowed_users = [user['pk'] for user in content['permissions']]
        for user in UserProfile.objects.all().order_by('user__first_name'):
            aux_user = user.as_dict()
            if aux_user['contents']:
                aux_user['permission'] = True if aux_user['pk'] in allowed_users else False
                users_list.append(aux_user)

        context = {'users_list': users_list,
                   'content': content,
                   'permission': get_user_permissions(request.user.pk),
                   'users_json': json.dumps({"data": users_list})}
        return render(request, 'interface/Permissions/contents.html', context)


@login_required
def permissions_timelines(request, pk):
    if request.user.pk != 1:
        return render(request, 'error/access_denied.html')

    if request.method == 'POST':
        timeline = Timeline.objects.get(pk=pk)
        timeline.permissions.clear()

        users_pks = request.POST.getlist('permissions')

        for user_pk in users_pks:
            user = UserProfile.objects.get(user_id=user_pk)
            timeline.permissions.add(user)

        return redirect('view_timelines')

    else:
        timeline = Timeline.objects.get(pk=pk).as_dict()
        users_list = []
        allowed_users = [user['pk'] for user in timeline['permissions']]
        for user in UserProfile.objects.all().order_by('user__first_name'):
            aux_user = user.as_dict()
            if aux_user['timelines']:
                aux_user['permission'] = True if aux_user['pk'] in allowed_users else False
                users_list.append(aux_user)

        context = {'users_list': users_list,
                   'timeline': timeline,
                   'permission': get_user_permissions(request.user.pk),
                   'users_json': json.dumps({"data": users_list})}
        return render(request, 'interface/Permissions/timelines.html', context)


@login_required
def permissions_views(request, pk):
    if request.user.pk != 1:
        return render(request, 'error/access_denied.html')

    if request.method == 'POST':

        view = View.objects.get(pk=pk)
        view.permissions.clear()

        users_pks = request.POST.getlist('permissions')

        for user_pk in users_pks:
            user = UserProfile.objects.get(user_id=user_pk)
            view.permissions.add(user)

        return redirect('view_views')

    else:
        view = View.objects.get(pk=pk).as_dict()
        users_list = []
        allowed_users = [user['pk'] for user in view['permissions']]
        for user in UserProfile.objects.all().order_by('user__first_name'):
            aux_user = user.as_dict()
            if aux_user['views']:
                aux_user['permission'] = True if aux_user['pk'] in allowed_users else False
                users_list.append(aux_user)

        context = {'users_list': users_list,
                   'view': view,
                   'permission': get_user_permissions(request.user.pk),
                   'users_json': json.dumps({"data": users_list})}
        return render(request, 'interface/Permissions/views.html', context)
