import glob
from scipy.io.wavfile import write
import librosa.display

label = "パスを記入"
files = glob.glob(label+"*.wav*")#wavファイルを取り出す

for file in files:
  y,sr = librosa.load(file,sr=None)
  newData = file+"修正後の音ファイルの名前を記入"
  write(newData,sr,y*0.5/max(y))
