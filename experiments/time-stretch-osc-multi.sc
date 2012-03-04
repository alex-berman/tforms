(
~frameSize = 1024; 
~hopSize = 0.25;

s.boot;
s.doWhenBooted({

SynthDef("pvrec", { arg fftBuffer=0, fftData=1, soundBuffer=2;
	var in, chain;
	Line.kr(1, 1, BufDur.kr(soundBuffer), doneAction: 2);
	in = PlayBuf.ar(1, soundBuffer, BufRateScale.kr(soundBuffer), loop: 0);
	chain = FFT(fftBuffer, in, ~hopSize, 1); 
	chain = PV_RecordBuf(chain, fftData, 0, 1, 0, ~hopSize, 1);
	}).send(s);

SynthDef("pvplay", { arg out=0, fftBuffer=0, fftData=1, cursor=0.0;
	var in, chain;
	chain = PV_BufRd(fftBuffer, fftData, cursor);
	Out.ar(out, IFFT(chain, 1).dup);
	}).send(s);

~soundFilename = "theme-nikolayeva-mono.wav";
~sf = SoundFile.new;
~sf.openRead(~soundFilename);
~sf.close;
~fftBuffer = Buffer.alloc(s, ~frameSize);
~fftData = Buffer.alloc(s, ~sf.duration.calcPVRecSize(~frameSize, ~hopSize));
~soundFileBuffer = Buffer.read(s, ~soundFilename);

});

)


Synth("pvrec", [\fftBuffer, ~fftBuffer, \fftData, ~fftData, \soundBuffer, ~soundFileBuffer]);
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
