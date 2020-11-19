import numpy as np
import os
import cv2
import math
import dlib
import matplotlib.pyplot as plt

#TODO: Face Frontalization

refPt = []
clahe = cv2.createCLAHE(clipLimit=2, tileGridSize=(2,2))

# Preprocessing block
def hist_eq(img):
    return clahe.apply(img)

def smooth(img):
	return cv2.GaussianBlur(img,(3,3),0)

def to_grayscale(image):
	return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

def rect_to_bb(rect):
	x = rect.left()
	y = rect.top()
	w = rect.right() - x
	h = rect.bottom() - y
	
	return (x, y, w, h)

def shape_to_np(shape):
	landmarks = np.zeros((68,2), dtype = int)

	for i in range(0,68):
		landmarks[i] = (shape.part(i).x, shape.part(i).y)

	return landmarks

# Face detection
def detect_face(image, detector, predictor):
	gray_image = to_grayscale(image)
	rects = detector(gray_image, 1)
	shape = []
	bb = []

	for (z, rect) in enumerate(rects):
		if rect is not None and rect.top()>0 and rect.right() < gray_image.shape[1] and rect.bottom() < gray_image.shape[0] and rect.left()>0:
			predicted = predictor(gray_image, rect)
			shape.append(shape_to_np(predicted))
			(x, y, w, h) = rect_to_bb(rect)
			bb.append((x, y, x+w, y+h))
			#cv2.rectangle(image, (x, y), (x + w, y + h), (0, 255, 0), 2)
		#for (x, y) in shape:
		#	cv2.circle(image, (x, y), 1, (0, 0, 255), -1)

	return shape, bb

# Cropping block
def rotate(gray_image, shape):
	dY = shape[36][1] - shape[45][1]
	dX = shape[36][0] - shape[45][0]
	angle = np.degrees(np.arctan2(dY, dX)) - 180

	rows,cols = gray_image.shape
	M = cv2.getRotationMatrix2D((cols/2,rows/2),angle,1)
	dst = cv2.warpAffine(gray_image,M,(cols,rows))

	#transform points
	ones = np.ones(shape=(len(shape), 1))
	points_ones = np.hstack([shape, ones])
	new_shape  = M.dot(points_ones.T).T
	new_shape = new_shape.astype(int)

	return dst, new_shape


def reference_point(event, x, y, flags, param):
	global refPt
	if event == cv2.EVENT_LBUTTONDOWN:
		refPt = (x, y)

def estimate_attention(p1, p2):

	aux_p1 = np.array([p1[0], p1[1]])
	aux_p2 = np.array([p2[0], p2[1]])
	aux_refPt = np.array([refPt[0], refPt[1]])
	p2_p1 = aux_p2 - aux_p1
	refPt_p1 = aux_refPt - aux_p1

	cosine_angle = np.dot(p2_p1, refPt_p1) / (np.linalg.norm(p2_p1) * np.linalg.norm(refPt_p1))
	radian_angle = np.arccos(cosine_angle)

	degrees_angle = np.degrees(radian_angle)
	attention = (-10/18)*degrees_angle + 100
	return attention


def rotation(features):
	nose = features[33]
	left = features[36]
	right = features[45]

	nose_to_left = abs(nose[0]-left[0])
	nose_to_right = abs(nose[0]-right[0])


	if nose_to_left > nose_to_right:
		rotation = (nose_to_right/nose_to_left)*100
	else:
		rotation = (nose_to_left/nose_to_right)*100

	return rotation

def head_pose(im, features):
	size = im.shape


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
							(-225.0, 170.0, -135.0),     # Left eye
							(225.0, 170.0, -135.0),      # Right eye 
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

	(nose_end_point2D, jacobian) = cv2.projectPoints(np.array([(0.0, 0.0, 1000.0)]), rotation_vector, translation_vector, camera_matrix, dist_coeffs)

	#for p in image_points:
	#	cv2.circle(im, (int(p[0]), int(p[1])), 3, (0,0,255), -1)

	p1 = ( int(image_points[0][0]), int(image_points[0][1]))
	p2 = ( int(nose_end_point2D[0][0][0]), int(nose_end_point2D[0][0][1]))

	cv2.line(im, p1, p2, (255,0,0), 2)

	return estimate_attention(p1,p2)



def save_data(average_attention):
	save_average = {}
	for i in range(0,len(average_attention)):
		if len(average_attention[i]) > 0:
			average = sum(average_attention[i])/len(average_attention[i])
			save_average[i] = average

	f = open('Graphs/data.txt', 'w')

	for y, z in save_average.items():
		f.write('ID ' + str(y) + '\n' )
		if z <= 25:
			f.write('Attention: ' + str(z) + '% (Distracted)' + '\n' )
		elif z > 25 and z <= 50:
			f.write('Attention: ' + str(z) + '% (Partially engaged)' + '\n' )
		elif z > 50 and z <= 75:
			f.write('Attention: ' + str(z) + '% (Engaged)' + '\n' )
		elif z > 75 and z <= 100:
			f.write('Attention: ' + str(z) + '% (Emotionally engaged)' + '\n' )
	f.close()


def save_attention_levels(average_attention):
	f = open('attention_levels.txt', 'w')
	for y, z in average_attention.items():
		f.write('ID ' + str(y) + '\n' )
		f.write(str(z) + '\n' + '\n')
	f.close()

def store(frame, i):
	filename = "Results/image" + str(i) + ".png"
	cv2.imwrite(filename, frame)

def graphics(y_values):
	for x, z in y_values.items():
		z_aux = []
		for i in range(len(z)):
			if z[i] > 50:
				z_aux.append(1)
			else:
				z_aux.append(0)

		if len(z_aux) > 0:
			rand_x = np.arange(0,len(z_aux))
			fig = plt.figure()
			plt.ylabel('Focus')
			plt.xlabel('Frames')
			plt.ylim(-0.5, 1.5)
			plt.step(rand_x, z_aux)
			plt.savefig('Graphs/ID_'+ str(x) +'.png')
			plt.close(fig)
