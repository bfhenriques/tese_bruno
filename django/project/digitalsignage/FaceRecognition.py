import facenet
import tensorflow as tf
import numpy as np
import cv2
import os

class FaceNet(object):
	def __init__(self):
		self.modeldir = 'models/20170511-185253.pb'
		facenet.load_model(self.modeldir) 
		self.path_to_vectors = "Vectors/"
		
		#Create the folder to store the database descriptors
		if not os.path.exists(self.path_to_vectors):
			os.makedirs(self.path_to_vectors)
		
		self.threshold = 0.85
		#TensorFlow initializations
		self.input_image_size = 160
		self.embeddings = tf.get_default_graph().get_tensor_by_name("embeddings:0")
		self.embedding_size = self.embeddings.get_shape()[1]
		self.images_placeholder = tf.get_default_graph().get_tensor_by_name("input:0")
		self.phase_train_placeholder = tf.get_default_graph().get_tensor_by_name("phase_train:0")
		gpu_options = tf.GPUOptions(per_process_gpu_memory_fraction=0.6)
		self.sess = tf.Session(config=tf.ConfigProto(gpu_options=gpu_options, log_device_placement=False))

	def calc_face_descriptor(self, img, bb):
		emb_array = np.zeros((1, self.embedding_size))
		cropped = img[bb[1]:bb[3], bb[0]:bb[2]]
		cropped = facenet.flip(cropped, False)
		scaled  = cv2.resize(cropped, (self.input_image_size,self.input_image_size), interpolation=cv2.INTER_CUBIC)
		scaled = facenet.prewhiten(scaled)
		scaled_reshape = scaled.reshape(-1,self.input_image_size,self.input_image_size,3)
		feed_dict = {self.images_placeholder: scaled_reshape, self.phase_train_placeholder: False}
		emb_array[0, :] = self.sess.run(self.embeddings, feed_dict=feed_dict)
		return emb_array[0, :]

	def compare(self, rep1, rep2):
		d = np.linalg.norm(rep1 - rep2)
		return d
