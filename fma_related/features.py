import os
import numpy as np
import pandas as pd
from scipy import stats
import librosa


def make_feature_series(file_name):
    feature_sizes = dict(
        chroma_stft=12,
        chroma_cqt=12,
        chroma_cens=12,
        tonnetz=6,
        mfcc=20,
        rmse=1,
        zcr=1,
        spectral_centroid=1,
        spectral_bandwidth=1,
        spectral_contrast=7,
        spectral_rolloff=1,
    )
    moments = ("mean", "std", "skew", "kurtosis", "median", "min", "max")

    columns = []
    for name, size in feature_sizes.items():
        for moment in moments:
            it = ((name, moment, "{:02d}".format(i + 1)) for i in range(size))
            columns.extend(it)

    names = ("feature", "statistics", "number")
    columns = pd.MultiIndex.from_tuples(columns, names=names).sort_values()
    feature_series = pd.Series(index=columns, dtype=np.float32, name=file_name)
    return feature_series


def feature_stats(feature_series, name, values):
    feature_series[name, "mean"] = np.mean(values, axis=1)
    feature_series[name, "std"] = np.std(values, axis=1)
    feature_series[name, "skew"] = stats.skew(values, axis=1)
    feature_series[name, "kurtosis"] = stats.kurtosis(values, axis=1)
    feature_series[name, "median"] = np.median(values, axis=1)
    feature_series[name, "min"] = np.min(values, axis=1)
    feature_series[name, "max"] = np.max(values, axis=1)
    return feature_series


def append_features(feature_series, x, sr):
    f = librosa.feature.zero_crossing_rate(x, frame_length=2048, hop_length=512)
    feature_series = feature_stats(feature_series, "zcr", f)

    # cqt required stuff
    cqt = np.abs(
        librosa.cqt(x, sr=sr, hop_length=512, bins_per_octave=12, n_bins=7 * 12, tuning=None)
    )
    f = librosa.feature.chroma_cqt(C=cqt, n_chroma=12, n_octaves=7)
    feature_series = feature_stats(feature_series, "chroma_cqt", f)
    f = librosa.feature.chroma_cens(C=cqt, n_chroma=12, n_octaves=7)
    feature_series = feature_stats(feature_series, "chroma_cens", f)
    f = librosa.feature.tonnetz(chroma=f)
    feature_series = feature_stats(feature_series, "tonnetz", f)

    # stft required stuff
    stft = np.abs(librosa.stft(x, n_fft=2048, hop_length=512))
    f = librosa.feature.chroma_stft(S=stft**2, n_chroma=12)
    feature_series = feature_stats(feature_series, "chroma_stft", f)
    f = librosa.feature.spectral_centroid(S=stft)
    feature_series = feature_stats(feature_series, "spectral_centroid", f)
    f = librosa.feature.spectral_bandwidth(S=stft)
    feature_series = feature_stats(feature_series, "spectral_bandwidth", f)
    f = librosa.feature.spectral_contrast(S=stft, n_bands=6)
    feature_series = feature_stats(feature_series, "spectral_contrast", f)
    f = librosa.feature.spectral_rolloff(S=stft)
    feature_series = feature_stats(feature_series, "spectral_rolloff", f)
    
    # mel required stuff
    mel = librosa.feature.melspectrogram(sr=sr, S=stft**2)
    f = librosa.feature.mfcc(S=librosa.power_to_db(mel), n_mfcc=20)
    feature_series = feature_stats(feature_series, "mfcc", f)
    return feature_series


class FeatureExtractor:
    def __init__(self, x, sr, file_path) -> None:
        self.x = x
        self.sr = sr
        self.file_name = os.path.basename(file_path).rstrip(".mp3")

    def __call__(self):
        feature_series = make_feature_series(self.file_name)
        feature_series = append_features(feature_series, self.x, self.sr)
        feature_df = feature_series.to_frame().T
        return feature_df
