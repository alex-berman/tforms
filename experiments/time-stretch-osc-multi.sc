s.boot;

(
~frameSize = 1024; 
~hopSize = 0.25;

/// this does the analysis and saves it to buffer 1... frees itself when done
SynthDef("pvrec", { arg fftBuffer=0, fftData=1, soundBufnum=2;
	var in, chain;
	Line.kr(1, 1, BufDur.kr(soundBufnum), doneAction: 2);
	in = PlayBuf.ar(1, soundBufnum, BufRateScale.kr(soundBufnum), loop: 0);
	// note the window type and overlaps... this is important for resynth parameters
	chain = FFT(fftBuffer, in, ~hopSize, 1); 
	chain = PV_RecordBuf(chain, fftData, 0, 1, 0, ~hopSize, 1);
	// no ouput ... simply save the analysis to fftData
	}).send(s);

// play your analysis back ... see the playback UGens listed above for more examples.
SynthDef("pvplay", { arg out=0, bufnum=0, fftData=1, cursor=0.0;
	var in, chain;
	chain = PV_BufRd(bufnum, fftData, cursor);
	Out.ar(out, IFFT(chain, 1).dup);
	}).send(s);
)

(
var sf;
~soundFilename = "theme-nikolayeva-mono.wav";
sf = SoundFile.new;
sf.openRead(~soundFilename);
sf.close;
~fftBuffer = Buffer.alloc(s, ~frameSize);
~fftData = Buffer.alloc(s, sf.duration.calcPVRecSize(~frameSize, ~hopSize));
~soundFileBuffer = Buffer.read(s, ~soundFilename);
)
Synth("pvrec", [\fftBuffer, ~fftBuffer, \fftData, ~fftData, \soundBufnum, ~soundFileBuffer]);
~player = Synth("pvplay", [\out, 0, \fftBuffer, ~fftBuffer, \fftData, ~fftData]);

OSCresponder.new(nil, "/cursor",
  { arg t, r, msg;
    var cursor = msg[1];
	  "cursor:".post;
	  cursor.postln;
	~player.set("cursor", cursor);
}).add; 

NetAddr.langPort;

~player.free;
