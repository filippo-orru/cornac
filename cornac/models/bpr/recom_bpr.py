# -*- coding: utf-8 -*-
"""
@author: Guo Jingyao
"""

import numpy as np
from .bpr import *
from ..recommender import Recommender
from ...exception import ScoreException


class BPR(Recommender):
    """Bayesian Personalized Ranking.

    Parameters
    ----------
    k: int, optional, default: 5
        The dimension of the latent factors.

    max_iter: int, optional, default: 100
        Maximum number of iterations or the number of epochs for SGD.

    learning_rate: float, optional, default: 0.001
        The learning rate for SGD.

    lamda: float, optional, default: 0.001
        The regularization parameter.

    batch_size: int, optional, default: 100
        The batch size for SGD.

    name: string, optional, default: 'BRP'
        The name of the recommender model.

    trainable: boolean, optional, default: True
        When False, the model is not trained and Cornac assumes that the model already \
        pre-trained (U and V are not None).
        
    verbose: boolean, optional, default: False
        When True, some running logs are displayed.

    init_params: dictionary, optional, default: {'U':None,'V':None}
        List of initial parameters, e.g., init_params = {'U':U, 'V':V}. \
        U: a csc_matrix of shape (n_users,k), containing the user latent factors. \
        V: a csc_matrix of shape (n_items,k), containing the item latent factors.

    References
    ----------
    * Rendle, Steffen, Christoph Freudenthaler, Zeno Gantner, and Lars Schmidt-Thieme. \
    BPR: Bayesian personalized ranking from implicit feedback. In UAI, pp. 452-461. 2009.
    """

    def __init__(self, k=5, max_iter=100, learning_rate=0.001, lamda=0.001, batch_size=100, name="bpr", trainable=True,
                 verbose=False, init_params={'U': None, 'V': None}):
        Recommender.__init__(self, name=name, trainable=trainable, verbose = verbose)
        self.k = k
        self.init_params = init_params
        self.max_iter = max_iter
        self.name = name
        self.learning_rate = learning_rate
        self.lamda = lamda
        self.batch_size = batch_size

        self.U = init_params['U']  # matrix of user factors
        self.V = init_params['V']  # matrix of item factors

    # fit the recommender model to the traning data
    def fit(self, train_set):
        """Fit the model to observations.

        Parameters
        ----------
        train_set: object of type TrainSet, required
            An object contraining the user-item preference in csr scipy sparse format,\
            as well as some useful attributes such as mappings to the original user/item ids.\
            Please refer to the class TrainSet in the "data" module for details.
        """
        
        Recommender.fit(self, train_set)

        X = self.train_set.matrix
        
        if self.trainable:
            # change the data to original user Id item Id and rating format
            cooX = X.tocoo()
            data = np.ndarray(shape=(len(cooX.data), 3), dtype=float)
            data[:, 0] = cooX.row
            data[:, 1] = cooX.col
            data[:, 2] = cooX.data

            if self.verbose:
                print('Learning...')
            res = bpr(X, data, k=self.k, n_epochs=self.max_iter, lamda=self.lamda, learning_rate=self.learning_rate,
                      batch_size=self.batch_size, init_params=self.init_params)
            self.U = np.asarray(res['U'])
            self.V = np.asarray(res['V'])
            
            if self.verbose:
                print('Learning completed')
        elif self.verbose:
            print('%s is trained already (trainable = False)' % (self.name))


    def score(self, user_id, item_id):
        """Predict the scores/ratings of a user for a list of items.

        Parameters
        ----------
        user_id: int, required
            The index of the user for whom to perform score predictions.
            
        item_id: int, required
            The index of the item to be scored by the user.

        Returns
        -------
        A scalar
            The estimated score (e.g., rating) for the user and item of interest
        """
        
        if self.train_set.is_unk_user(user_id) or self.train_set.is_unk_item(item_id):
            raise ScoreException("Can't make score prediction for (user_id=%d, item_id=%d)" % (user_id, item_id))        
         
        user_pred = self.V[item_id, :].dot(self.U[user_id, :])

        return user_pred



    def rank(self, user_id, candidate_item_ids=None):
        """Rank all test items for a given user.

        Parameters
        ----------
        user_id: int, required
            The index of the user for whom to perform item raking.

        candidate_item_ids: 1d array, optional, default: None
            A list of item indices to be ranked by the user.
            If `None`, list of ranked known item indices will be returned

        Returns
        -------
        Numpy 1d array
            Array of item indices sorted (in decreasing order) relative to some user preference scores.
        """ 
        
        if self.train_set.is_unk_user(user_id):
            if candidate_item_ids is None:
                return np.arange(self.train_set.num_items)
            return candidate_item_ids

        known_item_scores = self.V.dot(self.U[user_id, :])
        
        if candidate_item_ids is None:
            ranked_item_ids = known_item_scores.argsort()[::-1]
            return ranked_item_ids
        else:
            num_items = max(self.train_set.num_items, max(candidate_item_ids) + 1)
            user_pref_scores = np.ones(num_items) * self.default_score()
            user_pref_scores[:self.train_set.num_items] = known_item_scores

            ranked_item_ids = user_pref_scores.argsort()[::-1]
            mask = np.in1d(ranked_item_ids, candidate_item_ids)
            ranked_item_ids = ranked_item_ids[mask]

            return ranked_item_ids        
              
        