s.boot;

(
var sf;
~soundFilename = "theme-nikolayeva-mono.wav";
~frameSize = 1024; 
~hopSize = 0.25;
// get some info about the file
sf = SoundFile.new;
sf.openRead(~soundFilename);
sf.close;
~fftBuffer = Buffer.alloc(s, ~frameSize);
~fftData = Buffer.alloc(s, sf.duration.calcPVRecSize(~frameSize, ~hopSize));
~soundFileBuffer = Buffer.read(s, ~soundFilename);
)

// this does the analysis and saves it to buffer 1... frees itself when done
SynthDef("pvrec", { arg bufnum=0, recBuf=1, soundBufnum=2;
	var in, chain;
	Line.kr(1, 1, BufDur.kr(soundBufnum), doneAction: 2);
	in = PlayBuf.ar(1, soundBufnum, BufRateScale.kr(soundBufnum), loop: 0);
	// note the window type and overlaps... this is important for resynth parameters
	chain = FFT(bufnum, in, ~hopSize, 1); 
	chain = PV_RecordBuf(chain, recBuf, 0, 1, 0, ~hopSize, 1);
	// no ouput ... simply save the analysis to recBuf
	}).send(s);
a = Synth("pvrec", [\bufnum, ~fftBuffer, \recBuf, ~fftData, \soundBufnum, ~soundFileBuffer]);

// play your analysis back ... see the playback UGens listed above for more examples.
SynthDef("pvplay", { arg out=0, bufnum=0, recBuf=1;
	var in, chain;
	chain = PV_BufRd(bufnum, recBuf, MouseX.kr(0.0, 1.0));
	Out.ar(out, IFFT(chain, 1).dup);
	}).send(s);
b = Synth("pvplay", [\out, 0, \bufnum, ~fftBuffer, \recBuf, ~fftData]);
