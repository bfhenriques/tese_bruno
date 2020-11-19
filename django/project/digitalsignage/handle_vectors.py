import cv2
import numpy as np
import os
import time
import scipy.misc

def load_vectors_from_folder(folder):
    decriptors_saved = []
    try:
	    for filename in os.listdir(folder):
	    	if os.path.isfile(folder+filename) is True:
		        descriptor = np.load(os.path.join(folder,filename))
		        if descriptor is not None:
		            decriptors_saved.append(descriptor)            
    except OSError:
    	print("This folder does not exist")
    return decriptors_saved


def update_face_descriptors(fr, face_descriptor, identifier):

	folder_name = fr.path_to_vectors + "Person" + str(identifier) + "/"
	i=0
	for filename in os.listdir(folder_name):
		if os.path.isfile(folder_name + filename) is True:
			i+=1

	if os.path.exists(folder_name) is True and i < 30:
		filename_rep = folder_name + "Vector" + str(i) 
		np.save(filename_rep, face_descriptor)
	

		
def new_face_descriptors(fr, face_descriptor, identifier):
	folder_name = fr.path_to_vectors + "Person" + str(identifier) + "/"
	
	try:
		os.mkdir(folder_name)
		filename_rep = folder_name + "Vector0" 
		np.save(filename_rep, face_descriptor)
	except OSError:
		pass

def save_face(fr, face, identifier):
	folder_name = fr.path_to_vectors + "Person" + str(identifier) + "/"
	image_folder = folder_name + "Face/"
	face = cv2.cvtColor(face, cv2.COLOR_BGR2RGB)

	try:
		os.mkdir(image_folder)
		image = image_folder + "face.jpg"
		scipy.misc.toimage(face).save(image)
	except OSError:
		pass

def print_ID(identifier,x,y,frame):
	box_text = "ID " + str(identifier)
	pos_x = x - 10
	pos_y = y - 10
	cv2.putText(frame, box_text, (pos_x,pos_y), cv2.FONT_HERSHEY_SIMPLEX, 1, (200,255,155), 2)


def save_img(img,i):
	img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
	folder_name = "Results/"
	image = folder_name + "image"+str(i)+".jpg"
	scipy.misc.toimage(img).save(image)


def compare_descriptors(fr, person_folder, rep):
	descriptors_saved = load_vectors_from_folder(person_folder)

	d_values = []
	for x in range(0, len(descriptors_saved)):
		d = fr.compare(rep, descriptors_saved[x])
		d_values.append(d)
	try:					 
		d_average = sum(d_values)/len(d_values)

	except ZeroDivisionError:
		print("There were no comparisions made!")
		return 0

	return d_average


