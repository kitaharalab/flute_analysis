import pretty_midi
import numpy as np
import librosa.display
import scipy.io.wavfile as wav
import scipy.signal as sig
import scipy.signal.windows as win
from scipy.io import wavfile
import pyworld as pw
import scipy.fft as fft
import statistics
import glob
from scipy.io.wavfile import write

def searchStart(rms,rangeJudge,baseCut):
  dataStart = 0
  tmpStart = dataStart+rangeJudge
 
  while rms[dataStart] < baseCut or rms[tmpStart] < baseCut:
    if rms[tmpStart] >= baseCut:
      for i in range(dataStart+1,tmpStart+rangeJudge):
        if rms[i] < baseCut:
          dataStart = i
          tmpStart = dataStart
          break
    dataStart += 1
    tmpStart = dataStart+rangeJudge

  return dataStart

def searchEnd(rms,rangeJudge,baseCut):
  dataEnd = len(rms)-1
  tmpEnd = dataEnd-rangeJudge
 
  while rms[dataEnd] < baseCut or rms[tmpEnd] < baseCut:
    if rms[tmpEnd] >= baseCut:
      if tmpEnd+rangeJudge < len(rms)-1:
        for i in range(tmpEnd-rangeJudge,dataEnd-1):
          if rms[i] < baseCut:
            dataEnd = i
            tmpEnd = dataEnd
            break
    else:
      for i in range(tmpEnd-rangeJudge,len(rms[0])-1):
        if rms[0][i] < baseCut:
          dataEnd = i
          tmpStart = dataEnd
          break

    dataEnd -= 1
    tmpEnd = dataEnd-rangeJudge

  return dataEnd

def createData(file,y):
  rms = librosa.feature.rms(y=y,hop_length = 512)
  baseCut = max(rms[0])/10
  rangeJudge = int(len(rms[0])/19)
  dataStart = searchStart(rms[0],rangeJudge,baseCut)
  dataEnd = searchEnd(rms[0],rangeJudge,baseCut)
  dataStart = dataStart*int(len(y)/len(rms[0]))
  dataEnd = dataEnd*int(len(y)/len(rms[0]))
  rangeAdjust = int((dataEnd-dataStart)/50)

  return [y[dataStart+int(rangeAdjust):dataEnd+int(rangeAdjust)],dataStart,dataEnd,rangeAdjust]

def rangeVol(data):
  rms = librosa.feature.rms(y = data,hop_length = 512)
  return max(rms[0])/min(rms[0])

def divAvgVol(data):
  rms = librosa.feature.rms(y = data,hop_length = 512*4)
  divsum = 0
  array = rms[0]
  cnt = 0
  for i in range(1,len(array)):
    cnt += 1
    if array[i-1] != 0:
      divsum += abs((array[i]/array[i-1]))
  return divsum/cnt

def createFundData(data,sr):
  base=440.0                                                              
  fixData = data.astype(np.float)
 
  _f0, _time = pw.dio(fixData, sr,f0_floor=70,f0_ceil=16000,frame_period=10.625) 
  f0 = pw.stonemask(fixData, _f0, _time, sr)
  fundData = 1200 * np.log2(f0/base) + 5700

  return fundData

def rangeFund(data):
  q75, q25 = np.percentile(data, [75 ,25])
  if q75 != q75 or q25 != q25 or q75 < 0 or q25 < 0:
    mx = max(data)
    mn = min(data)
    data = sorted(data)
    if mn < 0 or mn != mn:
      i = 0
      while mn < 0 or mn != mn:
        i += 1
        mn = data[i]     
    if (q75 != q75 and q25 != q25) or q25 < 0: iqr = mx-mn
    elif q75 != q75: iqr = mx-q25
    else: iqr = q75-mn
  else: iqr = q75 - q25
  return iqr

def divAvgFund(data):
  divsum = 0
  array = data
  cnt = 0

  for i in range(1,len(array)):
    if array[i] == array[i] and array[i-1] == array[i-1] and array[i] >= 0 and array[i-1] >= 0:
      cnt += 1
      divsum += abs(array[i]-array[i-1])
    else:
      divsum += 0
  return divsum/cnt

def overtoneFeature(data,sr,isStart):
  y = data[0]
  dataStart = data[1]
  dataEnd = data[2]
  rangeAjust = data[3]
  
  if isStart == 0:
    y1 = y[0*sr : 1*sr]
  else:
    time = (dataEnd-dataStart-2*rangeAjust)/sr
    center = int(time/2)
    y1 = y[center*sr : (center+1)*sr]

  if np.all(y1 == 0):
    cntOvertone = 0
    ratioOvertone = 0
    ratioNoise = 0
  else:
    Y1 = fft.fft(y1)
    Y1_half = Y1[0 : int(len(Y1)/2)]
    spec = np.log(np.abs(Y1_half)+1)

    baseFreq = int(220+220*(2**(3/12)))
    margin = int(baseFreq/5)
    overtone = []
    rangeSearchCurrent = spec[baseFreq-margin:baseFreq+margin]
    overtone.append(max(rangeSearchCurrent))
    baseFreq = baseFreq-margin+np.argmax(rangeSearchCurrent)
    currentOvertone = overtone[0]
    k = 2
    while currentOvertone > max(spec)/100:
      margin = int(baseFreq/5)
      rangeSearchCurrent = spec[(k*baseFreq)-margin:(k*baseFreq)+margin]
      if len(rangeSearchCurrent)==0: currentOvertone = 0
      else: currentOvertone = max(rangeSearchCurrent)
      l = k+1
      center = spec[int(((k*baseFreq-margin)+(l*baseFreq+margin))/2)-margin:int(((k*baseFreq-margin)+(l*baseFreq+margin))/2)+margin]
      rangeSearchNext = spec[l*baseFreq-margin:l*baseFreq+margin]
      nextOvertone = max(rangeSearchNext)
      if max(center) > (currentOvertone+nextOvertone)/4: break
      if currentOvertone >= max(spec)/100:
        overtone.append(currentOvertone)
        k += 1

    sumOvertone = 0
    for i in range(len(overtone)): sumOvertone += overtone[i]

    rangeAll = spec[0:k*baseFreq+margin]
    ratioOvertone = sum(overtone[1:len(overtone)])/overtone[0]
    ratioNoise = sumOvertone/sum(rangeAll)
    cntOvertone = len(overtone)

    return [cntOvertone,ratioOvertone,ratioNoise]

def inputFeature(array,data,sr):

  array[0].append(rangeVol(data[0]))
  array[1].append(divAvgVol(data[0]))

  fundData = createFundData(data[0],sr)
  array[2].append(rangeFund(fundData))
  array[3].append(divAvgFund(fundData))

  for i in range(0,3): array[i+4].append(overtoneFeature(data,sr,0)[i])

  for i in range(0,3): array[i+7].append(overtoneFeature(data,sr,1)[i])



path = "???????????????"
files = glob.glob(path+"*.wav")

arrayFeature = [[] for i in range(10)]

for file in files:
  y,sr = librosa.load(file,sr=None)
  cutData = createData(file,y)

  inputFeature(arrayFeature,cutData,sr)
