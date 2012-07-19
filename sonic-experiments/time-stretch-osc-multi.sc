(
~frameSize = 1024; 
~hopSize = 0.25;
~fftBuffers=[];
~fftDatas=[];
~waveforms=[];
~players=[];

s.boot;
s.doWhenBooted({

SynthDef("pvrec", { arg fftBuffer, fftData, waveform;
	var in, chain;
	in = PlayBuf.ar(1, waveform, BufRateScale.kr(waveform), loop: 0);
	chain = FFT(fftBuffer, in, ~hopSize, 1); 
	chain = PV_RecordBuf(chain, fftData, 0, 1, 0, ~hopSize, 1);
	}).add;

SynthDef("pvplay", { arg out=0, fftBuffer, fftData, cursor=0.0;
	var in, chain;
	chain = PV_BufRd(fftBuffer, fftData, cursor);
	Out.ar(out, IFFT(chain, 1).dup);
	}).add;

l = { arg soundFilename;
	var sf;
	sf = SoundFile.new;
	sf.openRead(soundFilename);
	sf.close;
	~fftBuffers.add(Buffer.alloc(s, ~frameSize));
	~fftDatas.add(Buffer.alloc(s, sf.duration.calcPVRecSize(~frameSize, ~hopSize)));
	~waveforms.add(Buffer.read(s, soundFilename));
}

});

)

~sound1 = l.value("theme-nikolayeva-mono.wav");
Synth("pvrec", [\fftBuffer, ~fftBuffers[0], \fftData, ~fftDatas[0], \waveform, ~waveforms[0]]);
~players.add(Synth("pvplay", [\out, 0, \fftBuffer, ~fftBuffers[0], \fftData, ~fftDatas[0]]));

OSCresponder.new(nil, "/cursor",
  { arg t, r, msg;
	var player_id = msg[1];
    var cursor = msg[2];
	  "cursor:".post;
	  cursor.postln;
	~players[player_id].set("cursor", cursor);
}).add; 

NetAddr.langPort;

~player.free;
