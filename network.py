#!/usr/bin/python

import yaml
import random
import datetime

# Use numpy and matices to speed up the processing
import numpy as np

from lib.regularization import RegularizationFunction
from lib.activation import ActivationFunction
from lib.cost import CostFunction
from lib import utils

# NOTE: This allows us to always use the same random numbers. used for debug
np.random.seed(1)


class Network:
    def __init__(self, struct, \
            activation='sigmoid', cost='quadratic', regularization='none', \
            learning_rate=3.0, momentum=0.5, lambda_=0.1):
        """Generate the network's architecture based on a list.

        ex: [2, 3, 1]
        this will generate a 2 layer network with 2 input, 3 neurons on the
        hidden layer and one output.

        The input is assumed to be a (n, 1) array where n is the number of
        inputs of the network

        notation:
        we'll use w^l_{jk} to denote the weight of the connection from the k^th
        neuron in the (l-1)^th layer to the j^th neuron in the l^th layer
         * `lambda_` is the regularization parameter.
        """

        if cost == 'cross-entropy' and activation != 'sigmoid':
            raise Exception("cross-entropy can only be used with a sigmoid activation")

        self.n_layers = len(struct)
        self.struct = struct
        self.regularization = RegularizationFunction(func=regularization)
        self.activation     = ActivationFunction(func=activation)
        self.cost           = CostFunction(func=cost)
        self.eta     = learning_rate
        self.alpha   = momentum
        self.lambda_ = lambda_

        self.a = [ np.random.randn(layer,1) for layer in struct ]
        self.z = [ np.random.randn(layer,1) for layer in struct ]

        self.biases  = [ np.random.randn(y, 1) for y in struct[1:] ]
        self.weights = [ np.random.randn(y, x) / np.sqrt(x) \
                        for x, y in zip(struct[:-1], struct[1:]) ]


    def __repr__(self):
        """Returns a representation of the Network."""
        ret  = "Neural Network      : {}\n".format(self.struct)
        ret += "Activation function : {}\n".format(self.activation.type)
        ret += "Cost function       : {}\n\n".format(self.cost.type)
        if max(self.struct) <= 35:
            for idx, val in enumerate(self.struct):
                ret += 'L{:>0{n}} {:^{num}}\n'.format(str(idx), \
                        '* '*val, n=len(str(len(self.struct))), \
                        num=2*max(self.struct))
        return ret


    def __call__(self, X):
        """Propagate input data through the network."""
        return self.feedforward(X)


    def save(self, filename):
        """Save the current state of the Network to a YAML file.
        YAML format is convenient since it has no dependency on python and can
        be edited by hand."""
        data = {
                "struct"     : self.struct,
                "activation" : self.activation.type,
                "cost"       : self.cost.type,
                "eta"        : self.eta,
                "weights"    : [ w.tolist() for w in self.weights ],
                "biases"     : [ b.tolist() for b in self.biases  ],
                }
        with open(filename, 'wb') as f:
            yaml.dump(data, f)


    def load(self, filename):
        """Load a Network configuration from a YAML file."""
        with open(filename, 'rb') as f:
            data = yaml.load(f)

            self.struct = data['struct']
            self.activation = ActivationFunction(func=data['activation'])
            self.cost = CostFunction(func=data['cost'])
            self.eta = data['eta']

            self.biases  = [ np.array(b) for b in data['biases']  ]
            self.weights = [ np.array(w) for w in data['weights'] ]


    def feedforward(self, X):
        """Propagate input data through the network and store z and a values."""
        act = X
        z_list = []
        a_list = [act]

        for (b, w) in zip(self.biases, self.weights):
            z = np.dot(w, act) + b
            z_list.append(z)
            act = self.activation(z)
            a_list.append(act)

        self.a = a_list
        self.z = z_list
        return self.a[-1]


    def train(self, tr_d, epochs, batch_size, \
            va_d=None, monitoring={'accuracy':True, 'error':True, 'cost':True}):
        """Train the network using mini-batch stochastic gradient descent.

        Mini-batch stochastic gradient descent is based on the fact that
        provided `batch_size` is large enough, the average value of nabla_wC
        and nabla_bC over the mini-batch is roughly equal to the average over
        all the training input. Note that if `batch_size=1` this performs a
        regular stochastic gradient descent.
         * `epochs` is the number of epochs which should be done.
         * `tr_d` and `va_d` are lists of (Input, Output) tuples
         * `monitoring` is a list of strings."""


        tr_acc, tr_err, tr_cost = [], [], []
        va_acc, va_err, va_cost = [], [], []

        self.learn_time = datetime.datetime.now()

        for i in xrange(epochs):
            # Select a random mini batch in the training dataset
            random.shuffle(tr_d)

            # NOTE: `zip(*[iter(tr_d)]*batch_size)` is used to cut
            #       tr_d into n batch_size elements.
            for mini_batch in zip(*[iter(tr_d)]*batch_size):
                # Create copies of the weights and biases and init to 0.
                nabla_bC = np.multiply(np.array(self.biases,  copy=True), 0)
                nabla_wC = np.multiply(np.array(self.weights, copy=True), 0)

                for x, y in mini_batch:
                    # Sum all the derivatives over the mini-batch
                    nabla_bC_i, nabla_wC_i = self.backpropagation(x, y)
                    nabla_bC = np.add(nabla_bC, nabla_bC_i)
                    nabla_wC = np.add(nabla_wC, nabla_wC_i)

                # Update weights and biases
                # NOTE: the weights and biases should be averaged over the size
                #       of the mini-batch here but since it is done in the cost
                #       function so there is no need for it.
                self.biases  = [ b - self.eta * nb \
                        for b, nb in zip(self.biases, nabla_bC) ]
                self.weights = [ w - self.eta * (nw + \
                    self.regularization.derivative(w, self.lambda_, len(tr_d))) \
                        for w, nw in zip(self.weights, nabla_wC) ]

            print "Epoch {} training done.".format(i)

            if monitoring['accuracy']:
                print " * Training   set accuracy   : {}/{}".format( \
                        self.eval_accuracy(tr_d), len(tr_d))
                tr_acc.append(float(self.eval_accuracy(tr_d)) / len(tr_d))
                if va_d:
                    print " * Validation set accuracy   : {}/{}".format( \
                            self.eval_accuracy(va_d), len(va_d))
                    va_acc.append(float(self.eval_accuracy(va_d)) / len(va_d))

            if monitoring['error']:
                print " * Training   set error rate : {:.3%}".format( \
                        self.eval_error_rate(tr_d))
                tr_err.append(self.eval_error_rate(tr_d))
                if va_d:
                    print " * Validation set error rate : {:.3%}".format( \
                            self.eval_error_rate(va_d))
                    va_err.append(self.eval_error_rate(va_d))

            if monitoring['cost']:
                print " * Training   set cost       : {}".format( \
                        self.eval_cost(tr_d))
                tr_cost.append(self.eval_cost(tr_d))
                if va_d:
                    print " * Validation set cost       : {}".format( \
                        self.eval_cost(va_d))
                    va_cost.append(self.eval_cost(va_d))

            # Print empty line if monitoring for easy reading
            if monitoring:
                print

        self.learn_time = datetime.datetime.now() - self.learn_time
        return tr_acc, tr_err, tr_cost, va_acc, va_err, va_cost


    def backpropagation(self, X, y):
        """This returns a tuple of matrices of derivatives of the cost function
        with respect to biases and weights.
        Here, nabla_wC is used to refer to dCdW, the derivative of the cost
        function with respect to the weights (same for nabla_bC).

        https://en.wikipedia.org/wiki/Matrix_calculus
        """
        # Create copies of the weights and biases and init to 0.
        nabla_bC = np.multiply(np.array(self.biases,  copy=True), 0)
        nabla_wC = np.multiply(np.array(self.weights, copy=True), 0)

        self.feedforward(X)

        # Before the for loop, delta = delta_L, the error on the last layer
        # NOTE: array[-1] refers to the last element.
        if self.cost.type == 'cross-entropy':
            delta = self.cost.derivative(self.a[-1], y)
        else:
            delta = self.cost.derivative(self.a[-1], y) * \
                    self.activation.derivative(self.z[-1])

        nabla_bC[-1] = delta
        nabla_wC[-1] = np.dot(delta, self.a[-2].transpose())

        # Compute delta vectors and derivatives starting from layer (L-1)
        for l in xrange(2, self.n_layers):
            delta = np.dot(self.weights[-l+1].transpose(), delta) * \
                    self.activation.derivative(self.z[-l])

            nabla_bC[-l] = delta
            nabla_wC[-l] = np.dot(delta, self.a[-l-1].transpose())

        return (nabla_bC, nabla_wC)


    def eval_accuracy(self, data):
        count = 0
        for (x, y) in data:
            # If y is a vector get the index of it's max
            # this assumes a one-hot vector !!
            if isinstance(y, (np.ndarray, list)):
                y = np.argmax(y)

            if np.argmax(self.feedforward(x)) == y:
                count += 1

        return count


    def eval_error_rate(self, data, vectorize=False):
        return 1.0 - float(self.eval_accuracy(data)) / len(data)


    # FIXME
    def eval_cost(self, data):
        # C = C_0 + reg(w)
        return 0




# vim: set cc=80:
