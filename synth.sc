Server.local.options.memSize = 131072;
s.boot;

"langPort=".post; NetAddr.langPort.postln;

s.doWhenBooted({

~sounds = Dictionary[];
~filenames = Dictionary[];


SynthDef(\limiter,
{ arg gain=1.0, threshold=0.2;
  var input, effect;
  var sig;
  input=In.ar(0,5);
  sig = gain*input;
  effect = Compander.ar(
    sig, sig,
    thresh: threshold,
    slopeBelow: 1.0,
    slopeAbove: 0.1,
    clampTime: 0.001,
    relaxTime: 0.01
  );
  ReplaceOut.ar(0,effect);
}).send(s);
SystemClock.sched(1.0, { Synth(\limiter, []); });

SynthDef(\FreeVerb2x2, {|outbus, mix = 0.4, room = 0.6, damp = 0.1, amp = 1.0|
	var signal;
	signal = In.ar(outbus, 2);
	ReplaceOut.ar(outbus,
		signal + FreeVerb2.ar(
			signal[0],
			signal[1],
			mix, room, damp, amp));
}).send(s);
//WARNING: CPU usage freaks out after a while on my Linux with reverb enabled:
	//SystemClock.sched(1.0, { Synth(\FreeVerb2x2, [\outbus, 0]) });

SynthDef(\warp, {arg buffer = 0, begin, end, duration, pan;
	var out, pointer, filelength, pitch, env, dir;
	pointer = Line.kr(begin, end, duration);
	pitch = 1.0;
	env = EnvGen.kr(Env([0.001, 1, 1, 0.001],
		[0.005*duration, 0.9*duration, 0.06*duration], 'exp'), doneAction: 2);
	out = Warp1.ar(1, buffer, pointer, pitch, 0.1, -1, 8, 0.1, 2);
	Out.ar(0, Pan2.ar(env * out, pan));
}).send(s);

OSCresponder.new(nil, "/load",
  { arg t, r, msg;
	  var sound_id = msg[1];
	  var filename = msg[2];
	  if(~filenames[sound_id] != filename, {
		  ~sounds[sound_id] = Buffer.read(s, filename, 0, -1, {"loaded ".post; filename.postln;});
		  ~filenames[sound_id] = filename;
	  }, {});
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
