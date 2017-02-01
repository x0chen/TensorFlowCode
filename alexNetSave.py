################################################################################
#Michael Guerzhoy, 2016
#AlexNet implementation in TensorFlow, with weights
#with changes by Isabel Schwende
#Details: 
#http://www.cs.toronto.edu/~guerzhoy/tf_alexnet/
#
#With code from https://github.com/ethereon/caffe-tensorflow
#Model from  https://github.com/BVLC/caffe/tree/master/models/bvlc_alexnet
#Weights from Caffe converted using https://github.com/ethereon/caffe-tensorflow
#
################################################################################

from numpy import *
import os
import os.path
from pylab import *
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.cbook as cbook
import time
from scipy.misc import imread
from scipy.misc import imresize
import matplotlib.image as mpimg
from scipy.ndimage import filters
import urllib
from numpy import random
from tensorflow.python.training import saver as saver_lib

import tensorflow as tf
from tensorflow.python.platform import gfile
from tensorflow.core.protobuf import saver_pb2
#from tensorflow.python.framework import graph_io

from caffe_classes import class_names

train_x = zeros((1, 227,227,3)).astype(float32)
train_y = zeros((1, 1000))
xdim = train_x.shape[1:]
ydim = train_y.shape[1]

LOG_DIR = '/tmp/alex_log'#adapt 
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

################################################################################
#Read Image

x_dummy = (random.random((1,)+ xdim)/255.).astype(float32)
i = x_dummy.copy()
i[0,:,:,:] = (imread("poodle.png")[:,:,:3]).astype(float32)
i = i-mean(i)

################################################################################

# AlexNet structure
#         .conv(11, 11, 96, 4, 4, padding='VALID', name='conv1')
#         .lrn(2, 2e-05, 0.75, name='norm1')
#         .max_pool(3, 3, 2, 2, padding='VALID', name='pool1')
#         .conv(5, 5, 256, 1, 1, group=2, name='conv2')
#         .lrn(2, 2e-05, 0.75, name='norm2')
#         .max_pool(3, 3, 2, 2, padding='VALID', name='pool2')
#         .conv(3, 3, 384, 1, 1, name='conv3')
#         .conv(3, 3, 384, 1, 1, group=2, name='conv4')
#         .conv(3, 3, 256, 1, 1, group=2, name='conv5')
#         .fc(4096, name='fc6')
#         .fc(4096, name='fc7')
#         .fc(1000, relu=False, name='fc8')
#         .softmax(name='prob'))

# loading trained weights
net_data = load("bvlc_alexnet.npy").item()

def conv(input, kernel, biases, k_h, k_w, c_o, s_h, s_w,  padding="VALID", group=1):
    '''From https://github.com/ethereon/caffe-tensorflow
    '''
    c_i = input.get_shape()[-1]
    assert c_i%group==0
    assert c_o%group==0
    convolve = lambda i, k: tf.nn.conv2d(i, k, [1, s_h, s_w, 1], padding=padding)
    
    
    if group==1:
        conv = convolve(input, kernel)
    else:
        input_groups = tf.split(3, group, input)
        kernel_groups = tf.split(3, group, kernel)
        output_groups = [convolve(i, k) for i,k in zip(input_groups, kernel_groups)]
        conv = tf.concat(3, output_groups)
    return  tf.reshape(tf.nn.bias_add(conv, biases), conv.get_shape().as_list())

def mygraph(g_n,input_data):
	x = tf.Variable(input_data)

	#conv1
	#conv(11, 11, 96, 4, 4, padding='VALID', name='conv1')
	k_h = 11; k_w = 11; c_o = 96; s_h = 4; s_w = 4
	conv1W = tf.Variable(net_data["conv1"][0])
	conv1b = tf.Variable(net_data["conv1"][1])
	conv1_in = conv(x, conv1W, conv1b, k_h, k_w, c_o, s_h, s_w, padding="SAME", group=1)
	conv1 = tf.nn.relu(conv1_in)

	#lrn1
	#lrn(2, 2e-05, 0.75, name='norm1')
	radius = 2; alpha = 2e-05; beta = 0.75; bias = 1.0
	lrn1 = tf.nn.local_response_normalization(conv1,depth_radius=radius,alpha=alpha,beta=beta,bias=bias)

	#maxpool1
	#max_pool(3, 3, 2, 2, padding='VALID', name='pool1')
	k_h = 3; k_w = 3; s_h = 2; s_w = 2; padding = 'VALID'
	maxpool1 = tf.nn.max_pool(lrn1, ksize=[1, k_h, k_w, 1], strides=[1, s_h, s_w, 1], padding=padding)

	#conv2
	#conv(5, 5, 256, 1, 1, group=2, name='conv2')
	k_h = 5; k_w = 5; c_o = 256; s_h = 1; s_w = 1; group = 2
	conv2W = tf.Variable(net_data["conv2"][0])
	conv2b = tf.Variable(net_data["conv2"][1])
	conv2_in = conv(maxpool1, conv2W, conv2b, k_h, k_w, c_o, s_h, s_w, padding="SAME", group=group)
	conv2 = tf.nn.relu(conv2_in)

	#lrn2
	#lrn(2, 2e-05, 0.75, name='norm2')
	radius = 2; alpha = 2e-05; beta = 0.75; bias = 1.0
	lrn2 = tf.nn.local_response_normalization(conv2,depth_radius=radius,alpha=alpha,beta=beta,bias=bias)

	#maxpool2
	#max_pool(3, 3, 2, 2, padding='VALID', name='pool2')                                                  
	k_h = 3; k_w = 3; s_h = 2; s_w = 2; padding = 'VALID'
	maxpool2 = tf.nn.max_pool(lrn2, ksize=[1, k_h, k_w, 1], strides=[1, s_h, s_w, 1], padding=padding)

	#conv3
	#conv(3, 3, 384, 1, 1, name='conv3')
	k_h = 3; k_w = 3; c_o = 384; s_h = 1; s_w = 1; group = 1
	conv3W = tf.Variable(net_data["conv3"][0])
	conv3b = tf.Variable(net_data["conv3"][1])
	conv3_in = conv(maxpool2, conv3W, conv3b, k_h, k_w, c_o, s_h, s_w, padding="SAME", group=group)
	conv3 = tf.nn.relu(conv3_in)

	#conv4
	#conv(3, 3, 384, 1, 1, group=2, name='conv4')
	k_h = 3; k_w = 3; c_o = 384; s_h = 1; s_w = 1; group = 2
	conv4W = tf.Variable(net_data["conv4"][0])
	conv4b = tf.Variable(net_data["conv4"][1])
	conv4_in = conv(conv3, conv4W, conv4b, k_h, k_w, c_o, s_h, s_w, padding="SAME", group=group)
	conv4 = tf.nn.relu(conv4_in)

	#conv5
	#conv(3, 3, 256, 1, 1, group=2, name='conv5')
	k_h = 3; k_w = 3; c_o = 256; s_h = 1; s_w = 1; group = 2
	conv5W = tf.Variable(net_data["conv5"][0])
	conv5b = tf.Variable(net_data["conv5"][1])
	conv5_in = conv(conv4, conv5W, conv5b, k_h, k_w, c_o, s_h, s_w, padding="SAME", group=group)
	conv5 = tf.nn.relu(conv5_in)

	#maxpool5
	#max_pool(3, 3, 2, 2, padding='VALID', name='pool5')
	k_h = 3; k_w = 3; s_h = 2; s_w = 2; padding = 'VALID'
	maxpool5 = tf.nn.max_pool(conv5, ksize=[1, k_h, k_w, 1], strides=[1, s_h, s_w, 1], padding=padding)

	#fc6
	#fc(4096, name='fc6')
	fc6W = tf.Variable(net_data["fc6"][0])
	fc6b = tf.Variable(net_data["fc6"][1])
	fc6 = tf.nn.relu_layer(tf.reshape(maxpool5, [1, int(prod(maxpool5.get_shape()[1:]))]), fc6W, fc6b)

	#fc7
	#fc(4096, name='fc7')
	fc7W = tf.Variable(net_data["fc7"][0])
	fc7b = tf.Variable(net_data["fc7"][1])
	fc7 = tf.nn.relu_layer(fc6, fc7W, fc7b)

	#fc8
	#fc(1000, relu=False, name='fc8')
	fc8W = tf.Variable(net_data["fc8"][0])
	fc8b = tf.Variable(net_data["fc8"][1])
	fc8 = tf.nn.xw_plus_b(fc7, fc8W, fc8b)
	#prob
	#softmax(name='prob'))
	prob = tf.nn.softmax(fc8)
	#### End network design ####
	return g_n,prob 	
	
with tf.Graph().as_default() as g_1:	
	#### Initialize network and finalize graph1
	g_1,prob = mygraph(g_1,i)
	init = tf.global_variables_initializer()
	with tf.Session() as sess:
		sess.run(init)
		#Test output:
		output = sess.run(prob)
		inds = argsort(output)[0,:]
		for i in range(5):
			print class_names[inds[-1-i]], output[0, inds[-1-i]]
		#### End network test ####
	
		#### Saving network data ####
		checkpoint_prefix = os.path.join(LOG_DIR, "saved_checkpoint")
    		checkpoint_state_name = "checkpoint_state"
    		input_graph_name = "input_graph.pb"
    		output_graph_name = "output_graph.pb"
	
		saver = saver_lib.Saver(write_version=saver_pb2.SaverDef.V2)
		checkpoint_path = saver.save(
		  sess,
		  checkpoint_prefix,
		  global_step=0,
		  latest_filename=checkpoint_state_name)
		tf.train.write_graph(g_1, LOG_DIR, input_graph_name)
	
