import abc
import pandas as pd
from utils import GLMcorrection, load_data
import numpy as np
import os
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

__author__ = "Junhao Wen"
__copyright__ = "Copyright 2019-2020 The CBICA & SBIA Lab"
__credits__ = ["Junhao Wen"]
__license__ = "See LICENSE file"
__version__ = "0.1.0"
__maintainer__ = "Junhao Wen"
__email__ = "junhao.wen89@gmail.com"
__status__ = "Development"

class WorkFlow:
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def run(self):
        pass


class Input:
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def get_x(self):
        pass

    @abc.abstractmethod
    def get_y(self):
        pass

    @abc.abstractmethod
    def get_y_raw(self):
        pass

    @abc.abstractmethod
    def get_kernel(self):
        pass
    @abc.abstractmethod
    def get_image(self):
        pass

class ClassificationAlgorithm:
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def evaluate(self, train_index, test_index):
        pass

    @abc.abstractmethod
    def save_classifier(self, classifier, output_dir):
        pass

    @abc.abstractmethod
    def save_parameters(self, parameters, output_dir):
        pass

class ClassificationValidation:
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def validate(self, y):
        pass

class RB_Input(Input):
    """
    The main class to grab the input ROI-based features.
    """

    def __init__(self, feature_tsv, covariate_tsv=None):
        self._feature_tsv = feature_tsv
        self._covariate_tsv = covariate_tsv
        self._x = None
        self._y = None
        self._y_raw = None
        self._kernel = None

        ## check the feature_tsv & covariate_tsv, the header, the order of the columns, etc
        self._df_feature = pd.read_csv(feature_tsv, sep='\t')
        if ('participant_id' != list(self._df_feature.columns.values)[0]) or (
                'session_id' != list(self._df_feature.columns.values)[1]) or \
                ('diagnosis' != list(self._df_feature.columns.values)[2]):
            raise Exception("the data file is not in the correct format."
                            "Columns should include ['participant_id', 'session_id', 'diagnosis']")
        self._subjects = list(self._df_feature['participant_id'])
        self._sessions = list(self._df_feature['session_id'])
        self._diagnosis = list(self._df_feature['diagnosis'])

    def get_x(self):
        ## get the ROI data
        data_feature = self._df_feature.iloc[:, 3:].to_numpy()
        scaler = StandardScaler()
        data_feature = scaler.fit_transform(data_feature)

        if self._covariate_tsv == None:
            self._x = data_feature
        else:
            df_covariate = pd.read_csv(self._covariate_tsv, sep='\t')
            if ('participant_id' != list(self._df_feature.columns.values)[0]) or (
                    'session_id' != list(self._df_feature.columns.values)[1]) or \
                    ('diagnosis' != list(self._df_feature.columns.values)[2]):
                raise Exception("the data file is not in the correct format."
                                "Columns should include ['participant_id', 'session_id', 'diagnosis']")
            participant_covariate = list(df_covariate['participant_id'])
            session_covariate = list(df_covariate['session_id'])
            label_covariate = list(df_covariate['diagnosis'])

            # check that the feature_tsv and covariate_tsv have the same orders for the first three column
            if (not self._subjects == participant_covariate) or (not self._sessions == session_covariate) or (
            not self._diagnosis == label_covariate):
                raise Exception(
                    "the first three columns in the feature csv and covariate csv should be exactly the same.")

            ## normalize the covariate z-scoring
            data_covariate = df_covariate.iloc[:, 3:]
            data_covariate = ((data_covariate - data_covariate.mean()) / data_covariate.std()).values

            ## correction for the covariate, only retain the pathodological correspondance
            self._x, _ = GLMcorrection(data_feature, np.asarray(self._diagnosis), data_covariate, data_feature, data_covariate)
            
        return self._x

    def get_x_raw(self):
        "Get the raw input without correction with covariate for classification"
        ## get the ROI data
        self._x = self._df_feature.iloc[:, 3:].to_numpy()
        return self._x

    def get_y(self):
        "Get the lable converted from -1 to 0, 1 to 1 for classification"
        if self._y is not None:
            return self._y

        unique = sorted(list(set(self._diagnosis)))
        self._y = np.array([unique.index(x) for x in self._diagnosis])
        return self._y

    def get_y_raw(self):
        """
        Do not change the label's representation for clustering
        :return:
        """

        if self._y_raw is not None:
            return self._y_raw

        self._y_raw = np.array(self._diagnosis)
        return self._y_raw

    def get_kernel(self):
        """
        Calculate the linear kernel
        :return:
        """
        if self._kernel is not None:
            return self._kernel
        if self._x is None:
            self.get_x()

        self._kernel = np.matmul(self._x, self._x.transpose())

        return self._kernel