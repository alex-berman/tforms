Server.local.options.memSize = 131072;
s.boot;

"langPort=".post; NetAddr.langPort.postln;

s.doWhenBooted({

~sounds = Dictionary[];

SynthDef(\warp, {arg buffer = 0, begin, end, duration, pan;
	var out, pointer, filelength, pitch, env, dir;
	pointer = Line.kr(begin, end, duration);
	pitch = 1.0;
	env = EnvGen.kr(Env([0.001, 1, 1, 0.001],
		[0.005*duration, 0.9*duration, 0.06*duration], 'exp'), doneAction: 2);
	out = Warp1.ar(1, buffer, pointer, pitch, 0.1, -1, 8, 0.1, 2);
	Out.ar(0, Pan2.ar(out * env, pan));
}).send(s);

OSCresponder.new(nil, "/load",
  { arg t, r, msg;
	  var sound_id = msg[1];
	  var filename = msg[2];
	  var buffer = Buffer.read(s, filename);
	  ~sounds[sound_id] = buffer;
	  "loaded ".post; filename.postln;
  }).add;

OSCresponder.new(nil, "/play",
  { arg t, r, msg;
	  var sound_id = msg[1];
	  var begin = msg[2];
	  var end = msg[3];
	  var duration = msg[4];
	  var pan = msg[5] * 2 - 1;
	  //"numSynths=".post; s.numSynths.postln;
	  Synth(\warp, [\buffer, ~sounds[sound_id],
		  \begin, begin, \end, end, \duration, duration,
		  \pan, pan]);
  }).add;

});
