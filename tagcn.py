import tensorflow as tf
import numpy as np

from utils import *
from metrics import *
from inits import *

flags = tf.app.flags
FLAGS = flags.FLAGS
flags.DEFINE_string('dataset', 'cora', 'Dataset string.')  # 'cora', 'citeseer', 'pubmed'
flags.DEFINE_string('model', 'gcn', 'Model string.')  # 'gcn', 'gcn_cheby', 'dense'
flags.DEFINE_float('learning_rate', 0.01, 'Initial learning rate.')
flags.DEFINE_integer('epochs', 200, 'Number of epochs to train.')
flags.DEFINE_integer('hidden1', 16, 'Number of units in hidden layer 1.')
flags.DEFINE_float('dropout', 0.5, 'Dropout rate (1 - keep probability).')
flags.DEFINE_float('weight_decay', 5e-4, 'Weight for L2 loss on embedding matrix.')
flags.DEFINE_integer('early_stopping', 10, 'Tolerance for early stopping (# of epochs).')
flags.DEFINE_integer('max_degree', 3, 'Maximum Chebyshev polynomial degree.')

adj, features, y_train, y_val, y_test, train_mask, val_mask, test_mask = load_data(FLAGS.dataset)


features = features.todense()

# g = tf.get_default_graph()
# [op.name for op in g.get_operations()]

path_weight_matrix = np.load("path_weights.dat")
path_weight_matrix = path_weight_matrix.astype('float32')


from inits import *
# var_gs = {}
name = '01'
Fl = 8
Kl = 2
Cl = features.shape[1]
Nl = features.shape[0]
from tensorflow.python.framework.ops import reset_default_graph
reset_default_graph()


# define weights, biases

vars_F={}

with tf.variable_scope(name + '_vars'):

    for k in range(Kl):

        vars_F['weights_' + str(0) + '_' + str(k)] = glorot([Cl,Fl],name=('weights_' + str(0) + '_' + str(k)))
        # tf.get_variable(name=('weights_' + str(0) + '_' + str(k)),
        #                                                              initializer=tf.contrib.layers.xavier_initializer(),
        #                                                              shape=[Cl,Fl])
    initial = tf.zeros([Nl,Fl], dtype=tf.float32)
    vars_F['bias_' + str(0)] = tf.Variable(initial, name='bias')


    for k in range(Kl):

        vars_F['weights_' + str(1) + '_' + str(k)] = glorot([Fl,7],name=('weights_' + str(1) + '_' + str(k)))
        # tf.get_variable(name=('weights_' + str(1) + '_' + str(k)),
        #                                                              initializer=tf.contrib.layers.xavier_initializer(),
        #                                                              shape=[Fl,7]) # prev [Fl,Fl]
    initial = tf.zeros([Nl,7], dtype=tf.float32) # prev [Nl,Fl]
    vars_F['bias_' + str(1)] = tf.Variable(initial, name='bias')


features_m = tf.placeholder(tf.float32, shape=[features.shape[0], features.shape[1]])
pwm = tf.placeholder(tf.float32, [Nl, Nl, Kl])
outputs=[]



def layer(input_t,output_dim,num):

    # droupout
    input_t = tf.nn.dropout(input_t, 1-FLAGS.dropout)
    conv = np.zeros(output_dim,dtype=np.float32)

    for k in range(Kl):

        w_k = pwm[:,:,k]

        s = tf.matmul(w_k,input_t)

        G_k = vars_F['weights_' + str(num) + '_' + str(k)]

        res = tf.matmul(s,G_k)

        conv = tf.add(conv,res)

        print(conv.shape)

    # add bias
    bias = vars_F['bias_' + str(num)]

    conv = tf.add(conv,bias)

    # apply non-linearity to first layer
    if num == 0:
        conv = tf.nn.relu(conv)

    return conv



res = layer(features_m,output_dim=[Nl,Fl],num=0)
conv = layer(res,output_dim=[Nl,7],num=1)


# for training
accuracy1 = masked_accuracy(conv,y_train, train_mask)
loss1= 0
# weight decay loss
loss1 += FLAGS.weight_decay * tf.nn.l2_loss(vars_F['weights_' + str(0) + '_' + str(0)])
loss1 += FLAGS.weight_decay * tf.nn.l2_loss(vars_F['weights_' + str(0) + '_' + str(1)])
loss1 += FLAGS.weight_decay * tf.nn.l2_loss(vars_F['bias_' + str(0)])
loss1 += FLAGS.weight_decay * tf.nn.l2_loss(vars_F['weights_' + str(1) + '_' + str(0)])
loss1 += FLAGS.weight_decay * tf.nn.l2_loss(vars_F['weights_' + str(1) + '_' + str(1)])
loss1 += FLAGS.weight_decay * tf.nn.l2_loss(vars_F['bias_' + str(1)])
# Cross entropy error
loss1 += masked_softmax_cross_entropy(conv, y_train, train_mask)

optimizer = tf.train.AdamOptimizer(learning_rate=FLAGS.learning_rate)
opt_op = optimizer.minimize(loss1)

# for testing
accuracy2 = masked_accuracy(conv,y_test, test_mask)
loss2= 0
# weight decay loss
loss2 += FLAGS.weight_decay * tf.nn.l2_loss(vars_F['weights_' + str(0) + '_' + str(0)])
loss2 += FLAGS.weight_decay * tf.nn.l2_loss(vars_F['weights_' + str(0) + '_' + str(1)])
loss2 += FLAGS.weight_decay * tf.nn.l2_loss(vars_F['bias_' + str(0)])
loss2 += FLAGS.weight_decay * tf.nn.l2_loss(vars_F['weights_' + str(1) + '_' + str(0)])
loss2 += FLAGS.weight_decay * tf.nn.l2_loss(vars_F['weights_' + str(1) + '_' + str(1)])
loss2 += FLAGS.weight_decay * tf.nn.l2_loss(vars_F['bias_' + str(1)])
# Cross entropy error
loss2 += masked_softmax_cross_entropy(conv, y_test, test_mask)


# for validation
accuracy3 = masked_accuracy(conv,y_val, val_mask)
loss3= 0
# weight decay loss
loss3 += FLAGS.weight_decay * tf.nn.l2_loss(vars_F['weights_' + str(0) + '_' + str(0)])
loss3 += FLAGS.weight_decay * tf.nn.l2_loss(vars_F['weights_' + str(0) + '_' + str(1)])
loss3 += FLAGS.weight_decay * tf.nn.l2_loss(vars_F['bias_' + str(0)])
loss3 += FLAGS.weight_decay * tf.nn.l2_loss(vars_F['weights_' + str(1) + '_' + str(0)])
loss3 += FLAGS.weight_decay * tf.nn.l2_loss(vars_F['weights_' + str(1) + '_' + str(1)])
loss3 += FLAGS.weight_decay * tf.nn.l2_loss(vars_F['bias_' + str(1)])
# Cross entropy error
loss3 += masked_softmax_cross_entropy(conv, y_val, val_mask)

sess = tf.Session()
sess.run(tf.global_variables_initializer())

for epoch in range(FLAGS.epochs):

    evals = sess.run([opt_op,loss1,accuracy1],feed_dict={features_m:features,pwm:path_weight_matrix})
    evals2 = sess.run([loss3,accuracy3],feed_dict={features_m:features,pwm:path_weight_matrix})

    print("Test",evals[1], evals[2],"Validation",evals2[0], evals2[1])

outs_val = sess.run([loss2, accuracy2], feed_dict={features_m:features,pwm:path_weight_matrix})
print(outs_val[0], outs_val[1])
