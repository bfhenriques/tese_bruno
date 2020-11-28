import os
from . import FaceRecognition as df
from . import processing as pr
from . import handle_vectors as aux
import numpy as np
import cv2
import sys
# import dlib
import math


def recognition(fr, shape, bb, frame, rep, average_attention, id_size, full_frame):
	# Database empty --------------------------------------------------------------------------------------
	if id_size == 0:
		aux.new_face_descriptors(fr, rep[0], id_size)
		average_attention[str(id_size)] = []

		if(len(pr.refPt)==2):
			attention = pr.head_pose(full_frame, shape)
			if math.isnan(attention) == False:
				average_attention[str(id_size)].append(attention)
				att_text = "Focus: " + str(round(attention)) + "%"
				att_x = bb[0]-10
				att_y = bb[3]+20
				cv2.putText(full_frame, att_text, (att_x, att_y), cv2.FONT_HERSHEY_COMPLEX_SMALL, 1, (0, 0, 255), thickness=1, lineType=2)

		box_text = "New ID " + str(id_size)
		pos_x = bb[0]-10
		pos_y = bb[1]-10
		cv2.putText(full_frame, box_text, (pos_x, pos_y), cv2.FONT_HERSHEY_COMPLEX_SMALL, 1, (0, 0, 255), thickness=1, lineType=2)

		pr.store(full_frame, str(id_size))

	elif id_size > 0: 
		d_values = {}
		#Recognition block --------------------------------------------------
		for person in range(0, id_size):
			folder = fr.path_to_vectors + "Person" + str(person) + "/"
			d = aux.compare_descriptors(fr, folder, rep)
			d_values[person] = d

		best_comparison = min(d_values, key=d_values.get)
		confidence = d_values[best_comparison]

		print('Prediction: ' + str(best_comparison))
		print('Confidence:' + str(confidence))

		#The candidate might be in the database
		if(confidence <= fr.threshold):
			aux.update_face_descriptors(fr, rep[0], best_comparison)
			box_text = 'ID ' + str(best_comparison)
			pos_x = bb[0]-10
			pos_y = bb[1]-10
			cv2.putText(full_frame, box_text, (pos_x, pos_y), cv2.FONT_HERSHEY_COMPLEX_SMALL, 1, (0, 0, 255), thickness=1, lineType=2)

			if(len(pr.refPt)==2):
				attention = pr.head_pose(full_frame, shape)
				if math.isnan(attention) == False:
					average_attention[str(best_comparison)].append(attention)
					att_text = "Focus: " + str(round(attention)) + "%"
					att_x = 0
					att_y = 40
					cv2.putText(full_frame, att_text, (att_x, att_y), cv2.FONT_HERSHEY_COMPLEX_SMALL, 0.5, (0, 0, 255), thickness=1, lineType=1)

			pr.store(full_frame, str(best_comparison))


		#The candidate might not be in the database
		else:
			aux.new_face_descriptors(fr, rep[0], id_size)
			average_attention[str(id_size)] = []

			box_text = 'New ID ' + str(id_size)
			pos_x = bb[0]-10
			pos_y = bb[1]-10
			cv2.putText(full_frame, box_text, (pos_x, pos_y), cv2.FONT_HERSHEY_COMPLEX_SMALL, 1, (0, 0, 255), thickness=1, lineType=2)

			if(len(pr.refPt)==2):
				attention = pr.head_pose(full_frame, shape)
				if math.isnan(attention) == False:
					average_attention[str(id_size)].append(attention)
					att_text = "Focus: " + str(round(attention)) + "%"
					att_x = bb[0]-10
					att_y = bb[3]+20
					cv2.putText(full_frame, att_text, (att_x, att_y), cv2.FONT_HERSHEY_COMPLEX_SMALL, 1, (0, 0, 255), thickness=1, lineType=2)

			pr.store(full_frame, str(id_size))


'''try:
	np.seterr(divide='ignore', invalid='ignore')
	fr = df.FaceNet()
	detector = dlib.get_frontal_face_detector()
	predictor = dlib.shape_predictor('shape_predictor_68_face_landmarks.dat')

	video_capture = cv2.VideoCapture(0)

	average_attention = {}

	path = fr.path_to_vectors
	list_files = os.listdir(path)
	id_size = len(list_files)

	for i in range(0, id_size):
		average_attention[i] = []

	while True:
		ret, frame = video_capture.read()

		if len(pr.refPt) == 2:
			cv2.circle(frame, (pr.refPt[0], pr.refPt[1]), 10, (0, 0, 255), -1)

		shape, bb = pr.detect_face(frame, detector, predictor)
		rep = []
		for i in range(len(bb)):
			rep.append(fr.calc_face_descriptor(frame, bb[i]))

		recognition(fr, shape, bb, frame, rep, average_attention)

		for i in range(len(bb)):
			cv2.rectangle(frame, (bb[i][0], bb[i][1]), (bb[i][2], bb[i][3]), (0, 255, 0), 2)

		cv2.namedWindow('Frame', cv2.WINDOW_NORMAL)
		cv2.resizeWindow('Frame', 1280, 720)
		cv2.setMouseCallback('Frame', pr.reference_point)
		cv2.imshow('Frame', frame)

		if cv2.waitKey(30) & 0xFF == ord('q'):
			if len(pr.refPt) == 2:
				pr.graphics(average_attention)
				pr.save_data(average_attention)
			break

except KeyboardInterrupt:
	if len(pr.refPt) == 2:
		pr.graphics(average_attention)
		pr.save_data(average_attention)
	sys.exit()

video_capture.release()
cv2.destroyAllWindows()'''
