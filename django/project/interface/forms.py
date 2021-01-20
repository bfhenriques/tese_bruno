from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import Content, Timeline, View, UserProfile


class UserCreateForm(UserCreationForm):
    email = forms.EmailField(required=True)
    contents = forms.BooleanField(initial=False, required=False)
    timelines = forms.BooleanField(initial=False, required=False)
    views = forms.BooleanField(initial=False, required=False)

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'username', 'email', 'password1', 'password2')

    def save(self, commit=True):
        user = super(UserCreateForm, self).save(commit=False)
        user.email = self.cleaned_data["email"]
        contents = self.cleaned_data["contents"]
        timelines = self.cleaned_data["timelines"]
        views = self.cleaned_data["views"]

        if commit:
            user.save()
            user_profile = UserProfile(contents=contents, timelines=timelines, views=views, user=user)
            user_profile.save()
            print(user_profile)

        return user


class UserEditForm(UserChangeForm):
    email = forms.EmailField(required=True)
    contents = forms.BooleanField(initial=False, required=False)
    timelines = forms.BooleanField(initial=False, required=False)
    views = forms.BooleanField(initial=False, required=False)

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'username', 'email', )

    def clean_password(self):
        return ""


class ContentForm(forms.ModelForm):
    name = forms.CharField()
    file = forms.FileField()

    class Meta:
        model = Content
        fields = ('name', 'file', )


class ContentEditForm(forms.ModelForm):
    name = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    file = forms.FileField(required=False)

    class Meta:
        model = Content
        fields = ('name', 'file', )


class TimelineForm(forms.ModelForm):
    name = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))

    class Meta:
        model = Timeline
        fields = ('name',)
        exclude = {'creation_date', 'last_modified', 'duration', 'creator'}

    def save(self, commit=True):
        timeline = super(TimelineForm, self).save(commit=False)
        if commit:
            timeline.save()

        return timeline


class ViewForm(forms.ModelForm):
    name = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    recognition_confidence = forms.FloatField(widget=forms.TextInput(attrs={'class': 'form-control'}))

    class Meta:
        model = View
        fields = ('name', 'recognition_confidence')
        exclude = {'creation_date', 'last_modified', 'duration', 'resolution', 'mac'}


class ViewInfoForm(forms.Form):
    start_time = forms.FloatField(label="Start Time", widget=forms.NumberInput(attrs={'class': 'form-control'}))
    stage1_end_time = forms.FloatField(label="Stage 1 End Time", widget=forms.NumberInput(attrs={'class': 'form-control'}))
    stage2_end_time = forms.FloatField(label="Stage 2 End Time", widget=forms.NumberInput(attrs={'class': 'form-control'}))
    stage3_end_time = forms.FloatField(label="Stage 3 End Time", widget=forms.NumberInput(attrs={'class': 'form-control'}))
    end_time = forms.FloatField(label="End Time", widget=forms.NumberInput(attrs={'class': 'form-control'}))
