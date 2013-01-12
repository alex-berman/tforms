
~reverb_bus = Bus.audio(s, 1);

SynthDef(\warp, {arg buffer = 0, segment_id, begin, end, duration, channel, pan;
	var output_front, output_rear, pointer, filelength, pitch, env_front, env_rear, dir, pan_env, content;
	var front_content, rear_content;
	var amp;
	pointer = Line.kr(0, 1, duration);
	pitch = 1.0;
	content = Warp1.ar(1, buffer, pointer, pitch, 0.1, -1, 8, 0.1, 2);
	pan_env = EnvGen.kr(Env([pan, 0], [duration], 'linear'), doneAction: 2);

	env_front = EnvGen.kr(Env([0.001, 1.0, 0.001],
		[0.996*duration, 0.004*duration], 'sine'), doneAction: 2);
	front_content = env_front * content;
	output_front = Pan2.ar(front_content, pan_env);
	Out.ar(0, output_front);

	env_rear = EnvGen.kr(Env([0.001, 1.0, 0.001],
		[0.5*duration, 0.5*duration], 'sine'), doneAction: 2);
	rear_content = env_rear * content;
	output_rear = Pan2.ar(rear_content, pan_env);
	Out.ar(2, output_rear);

	Out.ar(~reverb_bus, front_content + rear_content);

	amp = LPF.kr(Amplitude.kr(front_content), 5);
	SendReply.kr(Impulse.kr(50), "/amp_private", amp, segment_id);

	SendReply.ar(Impulse.ar(500), "/waveform_private", front_content, segment_id);
}).send(s);

SynthDef(\add_reverb, {|out=0, in=0, mix = 0.25, room = 0.15, damp = 0.5|
	var signal, silent_noise, reverb;
	silent_noise = WhiteNoise.ar(0.00001); // see http://new-supercollider-mailing-lists-forums-use-these.2681727.n2.nabble.com/cpu-problems-with-PV-MagFreeze-and-Freeverb-tp5998599p6013552.html
	signal = In.ar(~reverb_bus, 1);
	reverb = FreeVerb.ar(signal + silent_noise,	mix, room, damp);
	Out.ar(0, reverb);
	Out.ar(1, reverb);
	Out.ar(2, reverb);
	Out.ar(3, reverb);
}).send(s);

OSCresponder.new(nil, "/set_reverb_mix",
  { arg t, r, msg;
	  var value = msg[1];
	  ~reverb.set(\mix, value);
  }).add;

OSCresponder.new(nil, "/set_reverb_room",
  { arg t, r, msg;
	  var value = msg[1];
	  ~reverb.set(\room, value);
  }).add;

OSCresponder.new(nil, "/set_reverb_damp",
  { arg t, r, msg;
	  var value = msg[1];
	  ~reverb.set(\damp, value);
  }).add;

SystemClock.sched(1.0, {
	~reverb = Synth(\add_reverb, [\in, ~reverb_bus.index]);
});