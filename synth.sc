"SC_JACK_DEFAULT_OUTPUTS".setenv("");
"SC_JACK_DEFAULT_INPUTS".setenv("");

Server.local.options.memSize = 1100000;
Server.local.options.numOutputBusChannels = 16;
s.boot;

"langPort=".post; NetAddr.langPort.postln;

s.doWhenBooted({

~sounds = Dictionary[];
~filenames = Dictionary[];
~synths = Dictionary[];


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

~info_subscriber = nil;
~amp_subscriber = nil;
~waveform_subscriber = nil;

OSCresponder.new(nil, "/info_subscribe",
  { arg t, r, msg;
	  var port = msg[1];
	  ~info_subscriber = NetAddr.new("127.0.0.1", port);
  }).add;

OSCresponder.new(nil, "/amp_subscribe",
  { arg t, r, msg;
	  var port = msg[1];
	  ~amp_subscriber = NetAddr.new("127.0.0.1", port);
  }).add;

OSCresponder.new(nil, "/waveform_subscribe",
  { arg t, r, msg;
	  var port = msg[1];
	  ~waveform_subscriber = NetAddr.new("127.0.0.1", port);
  }).add;

SynthDef(\warp, {arg buffer = 0, segment_id, begin, end, duration, channel, pan;
	var out, pointer, filelength, pitch, env, dir, amp, pan_env;
	pointer = Line.kr(begin, end, duration);
	pitch = 1.0;
	//env = EnvGen.kr(Env([0.001, 1, 0.001], [0.005*duration, 0.995*duration], 'exp'), doneAction: 2);
	env = EnvGen.kr(Env([0.001, 1, 0.001], [0.995*duration, 0.005*duration], 'exp'), doneAction: 2);
	out = env * Warp1.ar(1, buffer, pointer, pitch, 0.1, -1, 8, 0.1, 2);
	if(pan != nil, {
		pan_env = EnvGen.kr(Env([pan, 0], [duration], 'linear'), doneAction: 2);
		out = Pan2.ar(out, pan_env);
	}, {});
	Out.ar(channel, out);

	amp = LPF.kr(Amplitude.kr(out), 5);
	SendReply.kr(Impulse.kr(50), "/amp_private", amp, segment_id);

	SendReply.ar(Impulse.ar(500), "/waveform_private", out, segment_id);
}).send(s);

SynthDef(\loop, {arg buffer = 0, segment_id, begin, end, period, duration, channel, pan;
	var out, pointer, filelength, pitch, env, dir, amp, pan_env;
	var period_line = Line.kr(period, period*5, duration);
	//pan = SinOsc.ar(freq: 2 + 0.5.rand, phase: 3.rand) * Line.kr(0.45, 0, duration); // panning designed for waves visuals
	pointer = begin + ((end - begin) * LFSaw.ar(freq:1.0/period_line, iphase:1));
	pitch = 1.0;
	//env = EnvGen.kr(Env([0.001, 1, 0.001], [0.005*duration, 0.995*duration], 'exp'), doneAction: 2);
	env = EnvGen.kr(Env([0.001, 1], [duration], 'sine'), doneAction: 2);
	out = env * Warp1.ar(1, buffer, pointer, pitch, 0.1, -1, 8, 0.1, 2);
	if(pan != nil, {
		pan_env = EnvGen.kr(Env([pan, 0], [duration], 'linear'), doneAction: 2);
		out = Pan2.ar(out, pan_env);
	}, {});
	Out.ar(channel, out);

	amp = LPF.kr(Amplitude.kr(out), 5);
	SendReply.kr(Impulse.kr(50), "/amp_private", amp, segment_id);

	SendReply.ar(Impulse.ar(500), "/waveform_private", out, segment_id);
}).send(s);

OSCresponderNode(nil,"/amp_private",{|t,r,msg|
	var segment_id = msg[2];
	var amp = msg[3];
	if(~amp_subscriber != nil,
		{ ~amp_subscriber.sendMsg("/amp", segment_id, amp) }, {});
}).add;

OSCresponderNode(nil,"/waveform_private",{|t,r,msg|
	var segment_id = msg[2];
	var sample_value = msg[3];
	if(~waveform_subscriber != nil,
		{ ~waveform_subscriber.sendMsg("/waveform", segment_id, sample_value); }, {});
}).add; 

OSCresponder.new(nil, "/load",
  { arg t, r, msg;
	  var sound_id = msg[1];
	  var filename = msg[2];
	  if(~filenames[sound_id] == filename,
		  { ~info_subscriber.sendMsg("/loaded", sound_id, ~sounds[sound_id].numFrames); },
		  {
			  ~sounds[sound_id] = Buffer.read(s, filename, 0, -1, {
				  "loaded ".post; filename.postln;
				  if(~info_subscriber != nil,
					  { ~info_subscriber.sendMsg("/loaded", sound_id, ~sounds[sound_id].numFrames) }, {});
				  ~filenames[sound_id] = filename;
			  });
		  });
  }).add;

OSCresponder.new(nil, "/free",
  { arg t, r, msg;
	  var sound_id = msg[1];
	  ~sounds[sound_id].free;
	  ~filenames[sound_id] = nil;
  }).add;

OSCresponder.new(nil, "/play",
  { arg t, r, msg;
	  var segment_id = msg[1];
	  var sound_id = msg[2];
	  var begin = msg[3];
	  var end = msg[4];
	  var duration = msg[5];
	  var channel = msg[6];
	  var pan = msg[7];
	  //"numSynths=".post; s.numSynths.postln;
	  ~synths[segment_id] = Synth(\warp, [\buffer, ~sounds[sound_id],
		  \segment_id, segment_id,
		  \begin, begin, \end, end,
		  \duration, duration,
		  \channel, channel, \pan, pan]);
  }).add;

OSCresponder.new(nil, "/loop",
  { arg t, r, msg;
	  var segment_id = msg[1];
	  var sound_id = msg[2];
	  var begin = msg[3];
	  var end = msg[4];
	  var period = msg[5];
	  var duration = msg[6];
	  var channel = msg[7];
	  var pan = msg[8];
	  //"numSynths=".post; s.numSynths.postln;
	  ~synths[segment_id] = Synth(\loop, [\buffer, ~sounds[sound_id],
		  \segment_id, segment_id,
		  \begin, begin, \end, end,
		  \period, period,
		  \duration, duration,
		  \channel, channel, \pan, pan]);
  }).add;

OSCresponder.new(nil, "/pan",
  { arg t, r, msg;
	  var segment_id = msg[1];
	  var pan = msg[2] * 2 - 1;
	  var synth = ~synths[segment_id];
	  //synth.set(\pan, pan); // TEMP!
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


OSCresponder.new(nil, "/stop_all",
	{ arg t, r, msg;
		s.freeAll;
	}).add;

});
