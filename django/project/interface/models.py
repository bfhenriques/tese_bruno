from django.db import models
from django.contrib.auth.models import User
import json


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    contents = models.BooleanField()
    timelines = models.BooleanField()
    views = models.BooleanField()

    def as_dict(self):
        return {
            "pk": self.user.pk,
            "first_name": self.user.first_name,
            "last_name": self.user.last_name,
            "username": self.user.username,
            "email": self.user.email,
            "contents": self.contents,
            "timelines": self.timelines,
            "views": self.views
        }


class Content(models.Model):
    name = models.CharField(max_length=140)
    creation_date = models.DateTimeField()
    last_modified = models.DateTimeField()
    path = models.CharField(max_length=140, null=True)
    file_type = models.CharField(max_length=5, null=True)
    video_duration = models.PositiveIntegerField(null=True)
    permissions = models.ManyToManyField(UserProfile)
    has_changed = models.BooleanField()
    average_attention = models.TextField()
    attention_time = models.IntegerField()

    creator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return self.name

    def as_dict(self):
        return {
            "pk": self.pk,
            "name": self.name,
            "creation_date": self.creation_date.strftime('%c'),
            "last_modified": self.last_modified.strftime('%c'),
            "path": self.path,
            "file_type": self.file_type,
            "duration": 0 if self.file_type == 'image' else self.video_duration,
            "creator": "None" if self.creator is None else self.creator.username,
            "permissions": [user.as_dict() for user in self.permissions.all()],
            "average_attention": json.loads(self.average_attention),
            "attention_time": self.attention_time
        }


class Timeline(models.Model):
    name = models.CharField(max_length=140)
    creation_date = models.DateTimeField()
    last_modified = models.DateTimeField()
    permissions = models.ManyToManyField(UserProfile)
    has_changed = models.BooleanField()
    duration = models.PositiveIntegerField()
    average_attention = models.TextField()
    attention_time = models.IntegerField()

    creator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return self.name

    def as_dict(self):
        contents = []
        for content in TimelineContents.objects.filter(timeline_id=self.pk).order_by('orderindex'):
            aux_content = Content.objects.get(pk=content.content.pk).as_dict()
            aux_content['pk'] = content.content.pk
            aux_content['duration'] = content.duration
            aux_content['num_slides'] = content.num_slides
            contents.append(aux_content)
        return {
            "pk": self.pk,
            "name": self.name,
            "creation_date": self.creation_date.strftime('%c'),
            "last_modified": self.last_modified.strftime('%c'),
            "duration": self.duration,
            "contents": contents,
            "creator": "None" if self.creator is None else self.creator.username,
            "permissions": [user.as_dict() for user in self.permissions.all()],
            "average_attention": json.loads(self.average_attention),
            "attention_time": self.attention_time
        }


class View(models.Model):
    name = models.CharField(max_length=140)
    resolution = models.CharField(max_length=15)
    mac = models.CharField(max_length=20, unique=True)
    creation_date = models.DateTimeField()
    last_modified = models.DateTimeField()
    configured = models.BooleanField()
    permissions = models.ManyToManyField(UserProfile)
    has_changed = models.BooleanField()
    display_time = models.IntegerField()
    last_start = models.IntegerField()
    last_check = models.IntegerField()
    average_attention = models.TextField()
    attention_time = models.IntegerField()
    last_detection = models.IntegerField()
    recognition_confidence = models.FloatField()

    def __str__(self):
        return self.name

    def as_dict(self):
        duration = 0
        timelines = []
        for timeline in ViewTimelines.objects.filter(view_id=self.pk).order_by('orderindex'):
            aux_timeline = timeline.timeline.as_dict()
            aux_timeline['orderindex'] = timeline.orderindex
            timelines.append(aux_timeline)
            duration += aux_timeline['duration']

        return {
            "pk": self.pk,
            "name": self.name,
            "creation_date": self.creation_date.strftime('%c'),
            "last_modified": self.last_modified.strftime('%c'),
            "resolution": self.resolution,
            "mac": self.mac,
            "configured": self.configured,
            "duration": duration,
            "timelines": timelines,
            "permissions": [user.as_dict() for user in self.permissions.all()],
            "display_time": self.display_time,
            "last_start": self.last_start,
            "last_check": self.last_check,
            "average_attention": json.loads(self.average_attention),
            "attention_time": self.attention_time,
            "recognition_confidence": self.recognition_confidence
        }


class TimelineContents(models.Model):
    timeline = models.ForeignKey(Timeline, on_delete=models.CASCADE)
    content = models.ForeignKey(Content, on_delete=models.CASCADE)
    orderindex = models.PositiveIntegerField()
    duration = models.PositiveIntegerField()
    num_slides = models.PositiveIntegerField()

    def __str__(self):
        return " ".join([self.content.__str__(), self.timeline.__str__(), str(self.orderindex), str(self.duration)])

    def as_dict(self):
        return {
            "pk": self.pk,
            "timeline": self.timeline,
            "content": self.content,
            "orderindex": self.orderindex,
            "duration": self.duration,
            "num_slides": self.num_slides
        }


class ViewTimelines(models.Model):
    view = models.ForeignKey(View, on_delete=models.CASCADE)
    timeline = models.ForeignKey(Timeline, on_delete=models.CASCADE)
    orderindex = models.PositiveIntegerField()

    def __str__(self):
        return " ".join([self.timeline.__str__(), self.view.__str__(), str(self.orderindex)])

    def as_dict(self):
        return {
            "pk": self.pk,
            "view": self.view,
            "timeline": self.timeline,
            "orderindex": self.orderindex,
        }
