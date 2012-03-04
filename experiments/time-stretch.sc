s.boot;

(
var sf;
// path to a sound file here
p = "theme-nikolayeva-mono.wav";
// the frame size for the analysis - experiment with other sizes (powers of 2)
f = 1024; 
// the hop size
h = 0.25;
// get some info about the file
sf = SoundFile.new;
sf.openRead(p);
sf.close;
// allocate the FFT buffer
x = Buffer.alloc(s, f);
// allocate memory to store FFT data to... SimpleNumber.calcPVRecSize(frameSize, hop) will return 
// the appropriate number of samples needed for the buffer
y = Buffer.alloc(s, sf.duration.calcPVRecSize(f, h));
// allocate the soundfile you want to analyze
z = Buffer.read(s, p);
)

// this does the analysis and saves it to buffer 1... frees itself when done
SynthDef("pvrec", { arg bufnum=0, recBuf=1, soundBufnum=2;
	var in, chain;
	Line.kr(1, 1, BufDur.kr(soundBufnum), doneAction: 2);
	in = PlayBuf.ar(1, soundBufnum, BufRateScale.kr(soundBufnum), loop: 0);
	// note the window type and overlaps... this is important for resynth parameters
	chain = FFT(bufnum, in, 0.25, 1); 
	chain = PV_RecordBuf(chain, recBuf, 0, 1, 0, 0.25, 1);
	// no ouput ... simply save the analysis to recBuf
	}).send(s);
a = Synth("pvrec", [\bufnum, x, \recBuf, y, \soundBufnum, z]);

// play your analysis back ... see the playback UGens listed above for more examples.
SynthDef("pvplay", { arg out=0, bufnum=0, recBuf=1;
	var in, chain;
	chain = PV_BufRd(bufnum, recBuf, MouseX.kr(0.0, 1.0));
	Out.ar(out, IFFT(chain, 1).dup);
	}).send(s);
b = Synth("pvplay", [\out, 0, \bufnum, x, \recBuf, y]);
