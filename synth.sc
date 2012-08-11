Server.local.options.memSize = 131072;
s.boot;

"langPort=".post; NetAddr.langPort.postln;

s.doWhenBooted({

~sounds = Dictionary[];
~filenames = Dictionary[];
~players = Dictionary[];

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

SynthDef(\warp, {arg buffer = 0, envbuf = -1, pan = 0, pointer=0;
	var out, filelength, pitch, env, dir;
	pitch = 1.0;
	out = Warp1.ar(1, buffer, pointer, pitch, 0.1, envbuf, 8, 0.1, 2);
	Out.ar(0, Pan2.ar(out, pan));
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

OSCresponder.new(nil, "/start",
  { arg t, r, msg;
	  var player_id = msg[1];
	  var sound_id = msg[2];
	  var position = msg[3];
	  var pan = msg[4] * 2 - 1;
	  //"numSynths=".post; s.numSynths.postln;
	  ~players[player_id] = Synth(\warp, [
		  \buffer, ~sounds[sound_id],
		  \pointer, position,
		  \pan, pan]);
  }).add;

OSCresponder.new(nil, "/stop",
  { arg t, r, msg;
	  var player_id = msg[1];
	  ~players[player_id].free;
  }).add;

OSCresponder.new(nil, "/cursor",
  { arg t, r, msg;
	  var player_id = msg[1];
	  var position = msg[2];
	  ~players[player_id].set(\pointer, position);
  }).add;


SynthDef(\sync_beep, {
    arg freq = 440;
    var sig;
    sig = SinOsc.ar(freq, mul:0.9);
    sig = sig * EnvGen.kr(Env.perc(0, 0.5), doneAction:2);
    Out.ar(0, sig);
}).send(s);

OSCresponder.new(nil, "/sync_beep",
  { arg t, r, msg;
	  Synth(\sync_beep);
  }).add;


});
