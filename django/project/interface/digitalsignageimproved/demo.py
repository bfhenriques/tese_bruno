import numpy as np
import cv2
import dlib
import math
import json
import onnxruntime as rt
import matplotlib.pyplot as plt
import base64

# Confidence threshold for Face Recognition
RECOGNITION_CONFIDENCE = 0.5

# Maximum angle of face rotation for estimating attention since dlib can't keep detecting the face after a certain point 
MAX_ANGLE = 30

# Emotions
EMOTION_CLASSES = {0: "Neutral", 1: "Happiness", 2: "Surprise", 3: "Sadness", 4: "Anger", 5: "Disgust", 6: "Fear", 7: "Contempt"}

# load models
detector = dlib.get_frontal_face_detector()
predictor = dlib.shape_predictor('interface/digitalsignageimproved/shape_predictor_68_face_landmarks.dat')
# CUDA is required to use this model for face recognition
facerec = dlib.face_recognition_model_v1("interface/digitalsignageimproved/dlib_face_recognition_resnet_model_v1.dat")
# Model for emotion recognition: Barsoum, Emad, et al.
# "Training deep networks for facial expression recognition with crowd-sourced label distribution."
sess = rt.InferenceSession('interface/digitalsignageimproved/emotions.onnx')
input_name = sess.get_inputs()[0].name
output_name = sess.get_outputs()[0].name


# Converts dlib format to numpy format
def shape_to_np(shape):
	landmarks = np.zeros((68,2), dtype = int)
	for i in range(0,68):
		landmarks[i] = (shape.part(i).x, shape.part(i).y)

	return landmarks


# Converts dlib format to opencv format
def rect_to_bb(rect):
	x = rect.left()
	y = rect.top()
	w = rect.right() - x
	h = rect.bottom() - y
	
	return (x, y, w, h)


# Face Detection
def detect_face(image):
	gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
	rects = detector(gray_image, 1)
	shape = []
	bb = []
	raw_shape = []

	for (z, rect) in enumerate(rects):
		if rect is not None and rect.top() >= 0 and rect.right() < gray_image.shape[1] and rect.bottom() < gray_image.shape[0] and rect.left() >= 0:
			predicted = predictor(gray_image, rect)
			shape.append(shape_to_np(predicted))
			(x, y, w, h) = rect_to_bb(rect)
			bb.append((x, y, x+w, y+h))
			raw_shape.append(predicted)

	return shape, bb, raw_shape


# Initializes a new dictionary for each ID
def init_dict(ids, key, candidate_descriptor):
	ids[key] = {}
	ids[key]['Descriptor'] = candidate_descriptor
	ids[key]['Attention'] = 0
	ids[key]['Emotions'] = {}
	for i in EMOTION_CLASSES:
		ids[key]['Emotions'][EMOTION_CLASSES[i]] = 0
	ids[key]['Frames'] = 1


# Face Recognition
# Stores descriptors to a dictionary everytime a new person appears 
def face_recognition(frame, shape, ids, recognition_confidence):
	candidate = dlib.get_face_chip(frame, shape)   
	candidate = facerec.compute_face_descriptor(candidate)
	candidate_descriptor = np.asarray(candidate)
	person = 'ID ' + str(len(ids))

	if len(ids) == 0:
		init_dict(ids, person, candidate_descriptor.tolist())
		return person

	else:
		d_values = {}
		for reference in ids:
			dist = np.linalg.norm(np.asarray(ids[reference]['Descriptor']) - candidate_descriptor)
			d_values[reference] = dist

		best_comparison = min(d_values, key=d_values.get)
		confidence = d_values[best_comparison]

		if confidence < recognition_confidence:
			print("11111111")
			ids[best_comparison]['Frames'] += 1
			return best_comparison
		else:
			print("22222222")
			init_dict(ids, person, candidate_descriptor.tolist())
			return person


# Estimates head pose by transforming the 2D facial landmarks into 3D world coordinates and calculating the Euler angles
def head_pose(size, features):
	image_points = np.array([
							features[30],     # Nose 
							features[36],     # Left eye 
							features[45],     # Right eye
							features[48],     # Left Mouth corner
							features[54],     # Right mouth corner
							features[8]		  # Chin
							], dtype="double")

	# 3D model points.
	model_points = np.array([
							(0.0, 0.0, 0.0),             # Nose
							(-165.0, 170.0, -135.0),     # Left eye
							(165.0, 170.0, -135.0),      # Right eye 
							(-150.0, -150.0, -125.0),    # Left Mouth corner
							(150.0, -150.0, -125.0),     # Right mouth corner
							(0.0, -330.0, -65.0)		 # Chin
							])

	# Camera internals
	focal_length = size[1]
	center = (size[1]/2, size[0]/2)
	camera_matrix = np.array(
							[[focal_length, 0, center[0]],
							[0, focal_length, center[1]],
							[0, 0, 1]], dtype = "double"
							)

	dist_coeffs = np.zeros((4,1)) # Assuming no lens distortion
	(success, rotation_vector, translation_vector) = cv2.solvePnP(model_points, image_points, camera_matrix, dist_coeffs, flags=cv2.SOLVEPNP_ITERATIVE)

	rv_matrix = cv2.Rodrigues(rotation_vector)[0]

	proj_matrix = np.hstack((rv_matrix, translation_vector))
	eulerAngles = cv2.decomposeProjectionMatrix(proj_matrix)[6] 

	pitch, yaw, roll = [math.radians(x) for x in eulerAngles]
	pitch = math.degrees(math.asin(math.sin(pitch)))
	roll = -math.degrees(math.asin(math.sin(roll)))
	yaw = math.degrees(math.asin(math.sin(yaw)))

	return (pitch, roll, yaw)


# Assumes that frontal faces are paying attention using the pitch and yaw
def calculate_attention(ids, key, eulerAngles):
	angle_average = min((abs(eulerAngles[0]) + abs(eulerAngles[2]))/2, MAX_ANGLE) # Only pitch and yaw matter

	current_attention = (MAX_ANGLE - angle_average)/MAX_ANGLE # Normalization: [0, MAX_ANGLE] -> [0,1]
	ids[key]['Attention'] += current_attention

	return current_attention


# Performs emotion recognition
def emotion_recognition(face, ids, key):
	input_shape = (1, 1, 64, 64)
	img = cv2.resize(face, (64,64), cv2.INTER_AREA)
	img_data = np.array(img, dtype=np.float32)
	img_data = np.resize(img_data, input_shape)
	res = sess.run([output_name], {input_name: img_data})
	prediction = int(np.argmax(np.array(res).squeeze(), axis=0))
	emotion = EMOTION_CLASSES[prediction]
	ids[key]['Emotions'][emotion] += 1
	return emotion


# Displays bounding boxes, landmarks and the face recognition prediction on the frame
def display(key, bb, shape, emotion, frame):
	cv2.rectangle(frame, (bb[0], bb[1]), (bb[2], bb[3]), (0, 255, 0), 2)
	for (x, y) in shape:
		cv2.circle(frame, (x, y), 1, (0, 0, 255), -1)

	pos_x = bb[0]-10 
	pos_y = bb[1]-10
	cv2.putText(frame, str(key), (pos_x, pos_y), cv2.FONT_HERSHEY_COMPLEX_SMALL, 1, (0, 0, 255), thickness=1, lineType=2)

	pos_x = bb[0]-10 
	pos_y = bb[3]+20
	cv2.putText(frame, emotion, (pos_x, pos_y), cv2.FONT_HERSHEY_COMPLEX_SMALL, 1, (0, 0, 255), thickness=1, lineType=2)


# Stores data for each id to a json file
def save_data(ids):
	save_dict = {}
	for person in ids:
		save_dict[person] = {}
		save_dict[person]['Attention'] = ids[person]['Attention'] / ids[person]['Frames']
		save_dict[person]['Emotions'] = ids[person]['Emotions']
		for i in EMOTION_CLASSES:
			save_dict[person]['Emotions'][EMOTION_CLASSES[i]] /= ids[person]['Frames']

	with open('stats.json', 'w') as file:
		json.dump(save_dict, file,  indent=4)


def emotions_graphic(model_type, pk, emotions):
	fig, ax = plt.subplots(figsize=(6, 3), subplot_kw=dict(aspect="equal"))

	data = []
	legend = []
	for emotion in emotions:
		data.append(emotions[emotion])
		legend.append(str(emotions[emotion]) + ' - ' + emotion)

	wedges, texts, autotexts = ax.pie(data, autopct=lambda pct: func(pct, data), textprops=dict(color="w"))
	ax.legend(wedges, legend, title="Emotions by frames", loc="center left", bbox_to_anchor=(1, 0, 0.5, 1))
	# plt.setp(autotexts, size=8, weight="bold")

	# ax.set_title("")

	plt.savefig('interface/digitalsignageimproved/' + model_type + '_' + str(pk) + '.png')
	plt.close(fig)

	with open('interface/digitalsignageimproved/' + model_type + '_' + str(pk) + '.png', "rb") as chart:
		chart_as_text = base64.b64encode(chart.read())

	return 'data:image/png;base64,' + chart_as_text.decode('utf-8')


def func(pct, allvals):
	absolute = int(pct / 100. * np.sum(allvals))
	return


def hms(seconds):
	d = seconds // 86400
	h = seconds // 3600
	m = seconds % 3600 // 60
	s = seconds % 3600 % 60
	return '{:02d}d {:02d}h {:02d}m {:02d}s'.format(d, h, m, s)


'''def main():
	# load models
	detector = dlib.get_frontal_face_detector()
	predictor = dlib.shape_predictor('shape_predictor_68_face_landmarks.dat')
	# CUDA is required to use this model for face recognition
	facerec = dlib.face_recognition_model_v1("dlib_face_recognition_resnet_model_v1.dat")
	# Model for emotion recognition: Barsoum, Emad, et al. "Training deep networks for facial expression recognition with crowd-sourced label distribution."
	sess = rt.InferenceSession('emotions.onnx')
	input_name = sess.get_inputs()[0].name
	output_name = sess.get_outputs()[0].name

	# start capture for debugging, should be deleted since the data is coming from a raspberry
	video_capture = cv2.VideoCapture(0)

	ids = {}
	while True:
		ret, frame = video_capture.read() 
		dims = frame.shape # Replace dims for the image.shape sent from the raspberry (needed for head_pose())
		if ret:
			shape, bb, raw_shape = detect_face(frame, detector, predictor) # Shape and cropped face comes from the raspberry

			for i in range(len(bb)):
				key = face_recognition(frame, raw_shape[i], ids, facerec)
				eulerAngles = head_pose(dims, shape[i])
				calculate_attention(ids, key, eulerAngles)
				# This is the face sent from the raspberry, needs to be converted to grayscale for emotion recognition
				face = cv2.cvtColor(frame[bb[i][1]:bb[i][3], bb[i][0]:bb[i][2]], cv2.COLOR_BGR2GRAY)
				emotion = emotion_recognition(face, ids, key, sess, input_name, output_name)
				display(key, bb[i], shape[i], emotion, frame) # this function is just for visualization and debugging, should be commented 

			cv2.imshow('Frame',frame)
			if cv2.waitKey(30) & 0xFF == ord('q'):
				break

	save_data(ids)

if __name__ == "__main__":
	 main()'''
