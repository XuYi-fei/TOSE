"""Default parameters for ASE-style baseline detectors."""

from __future__ import annotations


METHODS = ("SWD", "ARD", "PRD", "GPD")

DETECTOR_COUNT = {
    "rubis": 1,
    "swat": 1,
    "wadi": 1,
    "bsn": 6,
}

TIME_UNIT_PER_LOOP = {
    "rubis": 60,
    "swat": 1,
    "wadi": 1,
    "bsn": 1,
}

THRESHOLD = 0.0027 / 2

SWD_WINDOW_SIZE = 28
SWD_SAMPLE_RATIO = {
    "rubis": 0.0087981220657277,
    "swat": 0.0027473470929633573,
    "wadi": 0.0027473470929633573,
    "bsn": [0.0027916666666666667, 0.002675, 0.002525, 0.00255, 0.0024416666666666666, 0.002525],
}

ARD_ORDER = 2
ARD_WINDOW_SIZE = 28

GPD_IDENTIFY_P = {
    "rubis": 1e-3,
    "swat": 1e-6,
    "wadi": 1e-6,
    "bsn": 1e-6,
}
GPD_IDENTIFY_RK = 1e-6
GPD_QK = {
    "rubis": 1e-9,
    "swat": 1e-9,
    "wadi": 1e-9,
    "bsn": 1e-10,
}
GPD_RK = {
    "rubis": 1e-6,
    "swat": 1e-6,
    "wadi": 1e-6,
    "bsn": 0.005**2,
}
GPD_HK = {
    "rubis": 0.06340464771218346,
    "swat": 1.0,
    "wadi": 1.0,
    "bsn": 1.0,
}

PRD_N = {
    "rubis": 40,
    "swat": 100,
    "wadi": 100,
    "bsn": 100,
}
PRD_BETA0 = 1.0
PRD_N_USER = 50
PRD_WARNING_NUM = {
    "rubis": 9,
    "swat": 6,
    "wadi": 6,
    "bsn": 3,
}
PRD_FIRST_SCENARIO_GAP = 10

RANDOM_SEED = 42
