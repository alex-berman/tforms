SynthDef(\warp, {arg buffer = 0, segment_id, begin, end, duration, channel, pan;
	var output_front, output_rear, pointer, filelength, pitch, env_front, env_rear, dir, content;
	var front_content, rear_content;
	var amp;
	pointer = Line.kr(begin, end, duration);
	pitch = 1.0;
	content = Warp1.ar(1, buffer, pointer, pitch, 0.1, -1, 8, 0.1, 2);

	env_front = EnvGen.kr(Env([0.001, 1.0, 0.001],
		[0.996*duration, 0.004*duration], 'sine'), doneAction: 2);
	front_content = env_front * content;
	output_front = Pan2.ar(front_content, pan);
	Out.ar(0, output_front);

	env_rear = EnvGen.kr(Env([0.001, 1.0, 0.001],
		[0.5*duration, 0.5*duration], 'sine'), doneAction: 2);
	rear_content = env_rear * content;
	output_rear = Pan2.ar(rear_content, pan);
	Out.ar(2, output_rear);

	Out.ar(~reverb_bus, output_front + output_rear);

	amp = LPF.kr(Amplitude.kr(front_content), 5);
	SendReply.kr(Impulse.kr(50), "/amp_private", amp, segment_id);

	SendReply.ar(Impulse.ar(500), "/waveform_private", front_content, segment_id);
}).send(s);

SynthDef(\add_reverb, {
	arg mix = 0.25, room = 0.85, damp = 1.0;
	var signal_left, signal_right, silent_noise, reverb_left, reverb_right;
	silent_noise = WhiteNoise.ar(0.00001); // see http://new-supercollider-mailing-lists-forums-use-these.2681727.n2.nabble.com/cpu-problems-with-PV-MagFreeze-and-Freeverb-tp5998599p6013552.html
	# signal_left, signal_right = In.ar(~reverb_bus, 2);
	reverb_left = FreeVerb.ar(signal_left + silent_noise, mix, room, damp);
	reverb_right = FreeVerb.ar(signal_right + silent_noise, mix, room, damp);
	Out.ar(0, reverb_left);
	Out.ar(1, reverb_right);
	Out.ar(2, reverb_left);
	Out.ar(3, reverb_right);
}).send(s);

SystemClock.sched(1.0, {
	~reverb = Synth(\add_reverb);
});
