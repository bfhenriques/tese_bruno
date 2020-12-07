import os
import imghdr
import PyPDF2
import pdf2image
import logging
import coloredlogs
import pptx
import subprocess
from ffmpy import FFmpeg
from ..models import Timeline, View
from moviepy.editor import VideoFileClip
import json

logger = logging.getLogger('File Manager Logger')
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s.%(msecs)03d - %(name)s - %(levelname)s - %(message)s', datefmt="%H:%M:%S")
ch.setFormatter(formatter)
logger.addHandler(ch)
coloredlogs.install(level='DEBUG', logger=logger, fmt='%(asctime)s.%(msecs)03d - %(name)s - %(levelname)s - '
                                                      '%(message)s', datefmt="%H:%M:%S")
fileHandler = logging.FileHandler("interface/logs/{}.log".format('filemanager'))
fileHandler.setFormatter(formatter)
logger.addHandler(fileHandler)
logger.propagate = False

IMAGE_FORMATS = ['jpeg', 'png']
VIDEO_FORMATS = ['avi', 'mp4']
PPT_FORMATS = ['ppt', 'pptx']


def handle_uploaded_content(f, pk):
    file_path = 'interface/media/Contents/%s.%s' % (pk, f.name.split('.')[-1])
    duration = 0

    with open(file_path, 'wb+') as destination:
        for chunk in f.chunks():
            destination.write(chunk)
    destination.close()

    # validate image
    if imghdr.what(file_path) in IMAGE_FORMATS:
        file_type = 'image'

    elif f.name.split('.')[-1] in VIDEO_FORMATS:
        duration = int(VideoFileClip(file_path).duration)
        file_type = 'video'

    elif f.name.split('.')[-1] in PPT_FORMATS:
        format = f.name.split('.')[-1]
        file_type = 'ppt'

        if format == 'pptx':
            try:
                ppt = pptx.Presentation(file_path)
            except:
                logging.error('Error reading PowerPoint file.')
                os.remove(file_path)
                return False, 'Invalid PPT file', 'ERROR', 0

        elif format == 'ppt':
            cmd = ['catppt', file_path]
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
            out, err = p.communicate()

            if err.decode('utf-8') != '':
                logging.error('Error reading PowerPoint file.')
                os.remove(file_path)
                return False, 'Invalid PPT file', 'ERROR', 0

    elif f.name.split('.')[-1] == 'pdf':
        file_type = 'pdf'
        try:
            PyPDF2.PdfFileReader(open(file_path, "rb"))
        except IOError:
            logging.warning('Invalid PDF file')
            os.remove(file_path)
            return False, 'Invalid PDF file', 'ERROR', 0

    else:
        os.remove(file_path)
        logging.error('Unsupported file format: %s' % f.name.split('.')[-1])
        return False, 'Unsupported file format', 'ERROR', 0

    return True, file_path, file_type, duration


def delete_file(file_path):
    try:
        os.remove(file_path)
    except:
        return


def create_pdf_video(content_pk, path, pdf_path, slide_duration, resolution):
    logging.info('Creating pdf preview')
    images = pdf2image.convert_from_path(pdf_path)
    all_paths = []
    tmp_path = ''
    num_slides = 0
    file = open('pdf_%s.txt' % (os.getpid()), 'w')
    for image in images:
        tmp_path = path + 'tmp/pdf_%s_%s.png' % (os.getpid(), str(num_slides))
        image.save(tmp_path)

        all_paths.append(tmp_path)
        file.write('file %s \nduration %d\n' % (tmp_path, slide_duration))

        num_slides += 1
    file.write('file ' + tmp_path)
    file.close()

    # ffmpeg -y -f concat -safe 0 -i images.txt -c:v libx264 -vf "fps=25,format=yuv420p" -strict -2 out.mp4
    ff = FFmpeg(
        inputs={'pdf_%s.txt' % (os.getpid()): '-y -f concat -safe 0'},
        outputs={path + 'tmp/%s_%s_%s.mp4' % (os.getpid(), content_pk, slide_duration):
                     '-vf "scale=%s:force_original_aspect_ratio=decrease,pad=%s:(ow-iw)/2:(oh-ih)/2"'
                     ' -c:v libx264 -pix_fmt yuv420p -strict -2' % (resolution, resolution)}
    )
    ff.run()
    for tmp in all_paths:
        try:
            os.remove(tmp)
        except:
            continue
    os.remove('pdf_%s.txt' % (os.getpid()))

    return path + 'tmp/%s_%s_%s.mp4' % (os.getpid(), content_pk, slide_duration), num_slides


def create_timeline(timeline_pk, path='interface/media/Timelines/', view_pk=0, resolution='400:300'):
    # create preview
    if view_pk == 0:
        all_paths = []
        contents = Timeline.objects.get(pk=timeline_pk).as_dict()['contents']
        file = open('%s.txt' % (os.getpid()), 'w')
        duration = 0
        for content in contents:
            if content['file_type'] == 'image':
                tmp_path = path + 'tmp/%s_%s_%s.mp4' % (os.getpid(), content['pk'], content['duration'])
                # if timeline_content has already been created
                if os.path.isfile(tmp_path):
                    file.write('file ' + tmp_path + '\n')
                    continue
                ff = FFmpeg(
                    inputs={content['path']: '-loop 1'},
                    outputs={tmp_path:
                                 '-vf "scale=%s:force_original_aspect_ratio=decrease,pad=%s:(ow-iw)/2:(oh-ih)/2"'
                                 ' -c:v libx264 -t %s -pix_fmt yuv420p -strict -2' % (resolution, resolution, content['duration'])}
                )
                ff.run()
            elif content['file_type'] == 'video':
                tmp_path = path + 'tmp/%s_%s.mp4' % (os.getpid(), content['pk'])
                # if timeline_content has already been created
                if os.path.isfile(tmp_path):
                    file.write('file ' + tmp_path + '\n')
                    continue
                ff = FFmpeg(
                    inputs={content['path']: ''},
                    outputs={
                        tmp_path: '-vf "scale=%s:force_original_aspect_ratio=decrease,pad=%s:(ow-iw)/2:(oh-ih)/2"'
                                  ' -c:v libx264 -pix_fmt yuv420p -strict -2' % (resolution, resolution)}
                )
                ff.run()
            elif content['file_type'] == 'ppt':
                tmp_path = path + 'tmp/%s_%s_%s.mp4' % (os.getpid(), content['pk'], content['duration'])
                # if timeline_content has already been created
                if os.path.isfile(tmp_path):
                    file.write('file ' + tmp_path + '\n')
                    continue

                # convert from ppt to pdf
                os.system('libreoffice --headless --convert-to pdf %s --outdir %s' % (content['path'], path + 'tmp/'))
                os.system('mv %s %s' % (path + 'tmp/%s.pdf' % (content['pk']),
                                        path + 'tmp/ppt%s_%s_%s.pdf' % (os.getpid(), content['pk'], content['duration'])))

                x, num_slides = create_pdf_video(content['pk'], path,
                                 path + 'tmp/ppt%s_%s_%s.pdf' % (os.getpid(), content['pk'], content['duration']),
                                 content['duration'], resolution)
                os.remove(path + 'tmp/ppt%s_%s_%s.pdf' % (os.getpid(), content['pk'], content['duration']))

            elif content['file_type'] == 'pdf':
                tmp_path = path + 'tmp/%s_%s_%s.mp4' % (os.getpid(), content['pk'], content['duration'])
                # if timeline_content has already been created
                if os.path.isfile(tmp_path):
                    file.write('file ' + tmp_path + '\n')
                    continue
                x, num_slides = create_pdf_video(content['pk'], path, content['path'], content['duration'], resolution)
            else:
                tmp_path = ""
                print("create_timeline")
            all_paths.append(tmp_path)
            file.write('file ' + tmp_path + '\n')

            if (content['file_type'] == 'ppt' or content['file_type'] == 'pdf'):
                duration += content['duration'] * num_slides
            else :
                duration += content['duration']

        file.close()
        # ffmpeg -i concat:"helicopter.avi|helicopter.avi" test.avi
        ff = FFmpeg(
            inputs={'%s.txt' % (os.getpid()): '-y -f concat'},
            outputs={path + '%s.mp4' % timeline_pk: '-c copy -strict -2'}
        )
        ff.run()
        for tmp in all_paths:
            try:
                os.remove(tmp)
            except:
                continue
        os.remove('%s.txt' % (os.getpid()))

        timeline = Timeline.objects.get(pk=timeline_pk)
        timeline.duration = duration
        timeline.average_attention = json.dumps(dict())
        timeline.save()


    else:
        all_paths = []
        contents = Timeline.objects.get(pk=timeline_pk).as_dict()['contents']
        file = open('%s.txt' % (os.getpid()), 'w')

        for content in contents:

            if content['file_type'] == 'image':
                tmp_path = path + 'tmp/%s_%s_%s.mp4' % (os.getpid(), content['pk'], content['duration'])

                # if timeline_content has already been created
                if os.path.isfile(tmp_path):
                    all_paths.append(tmp_path)
                    file.write('file ' + tmp_path + '\n')
                    continue

                ff = FFmpeg(
                    inputs={content['path']: '-loop 1'},
                    outputs={tmp_path:
                                 '-vf "scale=%s:force_original_aspect_ratio=decrease,pad=%s:(ow-iw)/2:(oh-ih)/2"'
                                 ' -c:v libx264 -t %s -pix_fmt yuv420p -strict -2' % (resolution, resolution, content['duration'])
                             }
                )
                ff.run()
            elif content['file_type'] == 'video':
                tmp_path = path + 'tmp/%s_%s.mp4' % (os.getpid(), content['pk'])

                # if timeline_content has already been created
                if os.path.isfile(tmp_path):
                    all_paths.append(tmp_path)
                    file.write('file ' + tmp_path + '\n')
                    continue

                ff = FFmpeg(
                    inputs={content['path']: ''},
                    outputs={
                        tmp_path: '-vf "scale=%s:force_original_aspect_ratio=decrease,pad=%s:(ow-iw)/2:(oh-ih)/2" '
                                  '-c:v libx264 -pix_fmt yuv420p -strict -2' % (resolution, resolution)
                    }
                )
                ff.run()
            elif content['file_type'] == 'ppt':
                tmp_path = path + 'tmp/%s_%s_%s.mp4' % (os.getpid(), content['pk'], content['duration'])
                # if timeline_content has already been created
                if os.path.isfile(tmp_path):
                    file.write('file ' + tmp_path + '\n')
                    continue

                # convert from ppt to pdf
                os.system('libreoffice --headless --convert-to pdf %s --outdir %s' % (content['path'], path + 'tmp/'))
                os.system('mv %s %s' % (path + 'tmp/%s.pdf' % (content['pk']),
                                        path + 'tmp/ppt%s_%s_%s.pdf' % (
                                        os.getpid(), content['pk'], content['duration'])))

                create_pdf_video(content['pk'], path,
                                 path + 'tmp/ppt%s_%s_%s.pdf' % (os.getpid(), content['pk'], content['duration']),
                                 content['duration'], resolution)
                os.remove(path + 'tmp/ppt%s_%s_%s.pdf' % (os.getpid(), content['pk'], content['duration']))

            elif content['file_type'] == 'pdf':
                tmp_path, x = create_pdf_video(content['pk'], path, content['path'], content['duration'], resolution)
            else:
                tmp_path = ""
                print("create_timeline")

            all_paths.append(tmp_path)
            file.write('file ' + tmp_path + '\n')

        file.close()

        # ffmpeg -i concat:"helicopter.avi|helicopter.avi" test.avi
        ff = FFmpeg(
            inputs={'%s.txt' % (os.getpid()): '-y -f concat'},
            outputs={path + 'tmp/%s_%s.mp4' % (view_pk, timeline_pk): '-c copy -strict -2'}
        )
        ff.run()

        for tmp in all_paths:
            try:
                os.remove(tmp)
            except:
                continue
        os.remove('%s.txt' % (os.getpid()))


def create_view(view_pk, view_resolution, view_configured=False):
    timelines = View.objects.get(pk=view_pk).as_dict()['timelines']
    all_paths = []
    if len(timelines) > 0:
        file = open('%s_%s.txt' % (os.getpid(), view_pk), 'w')

        for timeline in timelines:
            create_timeline(timeline['pk'], path='interface/media/Views/', view_pk=view_pk,
                            resolution=view_resolution)

            tmp_path = 'interface/media/Views/tmp/%s_%s.mp4' % (view_pk, timeline['pk'])
            file.write('file %s' % tmp_path + '\n')
            all_paths.append(tmp_path)

        file.close()

        # ffmpeg -i concat:"helicopter.avi|helicopter.avi" test.avi
        ff = FFmpeg(
            inputs={'%s_%s.txt' % (os.getpid(), view_pk): '-y -f concat'},
            outputs={'interface/media/Views/%s.mp4' % view_pk: '-c copy -strict -2'}
        )
        ff.run()

        for tmp in all_paths:
            try:
                os.remove(tmp)
            except:
                continue
        os.remove('%s_%s.txt' % (os.getpid(), view_pk))

    if view_configured:
        view = View.objects.get(pk=view_pk)
        view.has_changed = True
        view.average_attention = json.dumps(dict())
        view.save()
