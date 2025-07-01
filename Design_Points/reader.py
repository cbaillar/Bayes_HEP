'''
Read data according to the JetScape 1.0 stat specification
'''

import numpy as np

import os
#from pathlib import Path

data_list = []
observables = []
systems = []
labels = []
keys = []
ranges = []
design_array = []
exp_data_list = []
exp_cov = []


def ReadDesign(FileName):
    Result = {}
    Version = ''
    Result["FileName"] = FileName

    has_data = False

    with open(FileName) as f:
        lines = f.readlines()

    for Line in lines:
        Items = Line.strip().split()
        if len(Items) < 2:
            continue

        if Items[0] == '#':
            if Items[1] == 'Version':
                Version = Items[2]
            elif Items[1] == 'Parameter':
                Result["Parameter"] = Items[2:]
            elif Items[1] == '-':
                param = Items[3]
                Result[param] = Items[4:]
        else:
            has_data = True

    if has_data:
        Result["Design"] = np.loadtxt(FileName)
    else:
        Result["Design"] = None  

    return Result

def ReadData(FileName):
    # Initialize objects
    Result = {}
    Version = ''

    Result["FileName"] = FileName
    filename = os.path.basename(FileName).replace('.dat', '')
    parts = filename.split('__')

    Result["Energy"] = parts[1] 
    Result["System"] = parts[2] 
    Result["Observable"] = parts[3] 
    Result["Subobservable"] = parts[4]
    Result["Experiment"] = parts[4].split('_')[-1]
    Result["Histogram"] = parts[5]

    # First read all the header information
    for Line in open(FileName):
        Items = Line.split()
        if (len(Items) < 2): continue
        if Items[0] != '#': continue

        if(Items[1] == 'Version'):
            Version = Items[2]
        elif(Items[1] == 'Label'):
            Result["Label"] = Items[2:]

    XMode = ''
    if(Result["Label"][0:4] == ['xmin', 'xmax', 'y', 'y_err']):
        XMode = 'xminmax'
    else:
        raise AssertionError('Invalid list of initial columns!  Should be (xmin, xmax, y, y_err)')
    
    # Then read the actual data
    RawData = np.loadtxt(FileName)

    Result["Data"] = {}
    if(XMode == 'xminmax'):
        Result["Data"]["x"] = (RawData[:, 0] + RawData[:, 1]) / 2
        Result["Data"]["xerr"] = (RawData[:, 1] - RawData[:, 0]) / 2
        Result["Data"]["y"] = RawData[:, 2]
        Result["Data"]["yerr"] = RawData[:, 3]

    return Result


def ReadPrediction(FileName):
    # Initialize objects
    Result = {}
    Version = ''

    Result["FileName"] = FileName
    filename = os.path.basename(FileName).replace('.dat', '')
    parts = filename.split('__')

    Result["Model"] = parts[1]
    Result["Energy"] = parts[2] 
    Result["System"] = parts[3] 
    Result["Observable"] = parts[4] 
    Result["Subobservable"] = parts[5]
    Result["Experiment"] = parts[5].split('_')[-1]
    Result["Histogram"] = parts[6]

    # First read all the header information
    for Line in open(FileName):
        Items = Line.split()
        if (len(Items) < 2): continue
        if Items[0] != '#': continue

        if(Items[1] == 'Version'):
            Version = Items[2]
        elif(Items[1] == 'Data'):
            Result["Data"] = Items[2]
        elif(Items[1] == 'Design'):
            Result["Design"] = Items[2]

    # Then read the actual model predictions
    Result["Prediction"] = np.loadtxt(FileName).T

    ErrorFileName = FileName.replace('values.dat', 'errors.dat')
    
    for Line in open(ErrorFileName):
        Items = Line.split()
        if (len(Items) < 2): continue
        if Items[0] != '#': continue

        if(Items[1] == 'Version'):
            Version = Items[2]
        elif(Items[1] == 'Data'):
            Result["Data"] = Items[2]
        elif(Items[1] == 'Design'):
            Result["Design"] = Items[2]

    
    Result["PredictionErrors"] = np.loadtxt(ErrorFileName).T

    return Result
