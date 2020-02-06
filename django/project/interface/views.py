from django.http import FileResponse, Http404
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.utils import timezone
from .models import View, Timeline, Content, TimelineContents, ViewTimelines, UserProfile
from .forms import UserCreateForm, UserEditForm, ContentForm, ContentEditForm, TimelineForm, ViewForm
from .scripts import file_manager
import json
import threading

def get_user_permissions(pk):
    if pk == 1:
        return {'pk': 1, 'contents': True, 'timelines': True, 'views': True, 'users': True}
    else:
        return UserProfile.objects.get(user_id=pk).as_dict()

def login(request):
    return render(request, 'registration/login.html')

@login_required
def index(request):
    return render(request, 'interface/home.html', {'permission': get_user_permissions(request.user.pk)})

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
                   'permission': get_user_permissions(request.user.pk)}
        return render(request, 'interface/View/edit_view.html', context)


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

            post.creator = request.user

            post.save()

            if request.user.pk != 1:
                timeline = Timeline.objects.get(pk=post.pk)
                timeline.permissions.add(UserProfile.objects.get(user_id=request.user.pk))

            pks = request.POST.getlist('pks')
            durations = request.POST.getlist('durations')

            for index in range(0, len(pks)):
                TimelineContents.objects.create(timeline_id=post.id, content_id=pks[index], orderindex=index+1, duration=durations[index])

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
                                                duration=durations[index])

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
        context = {'form': form, 'content': content, 'permission': get_user_permissions(request.user.pk)}
        return render(request, 'interface/Content/edit_content.html', context)

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
                   'content'   : content,
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
                   'timeline'   : timeline,
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
                   'view'   : view,
                   'permission': get_user_permissions(request.user.pk),
                   'users_json': json.dumps({"data": users_list})}
        return render(request, 'interface/Permissions/views.html', context)
