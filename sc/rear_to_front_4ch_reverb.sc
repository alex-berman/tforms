
SynthDef(\warp, {arg buffer = 0, segment_id, begin, end, duration, channel, pan;
	var output_front, output_rear, pointer, filelength, pitch, env_front, env_rear, dir, amp, pan_env, content, front_mono;
	pointer = Line.kr(begin, end, duration);
	pitch = 1.0;
	content = Warp1.ar(1, buffer, pointer, pitch, 0.1, -1, 8, 0.1, 2);
	pan_env = EnvGen.kr(Env([pan, 0], [duration], 'linear'), doneAction: 2);

	env_front = EnvGen.kr(Env([0.001, 1.0, 0.001],
		[0.996*duration, 0.004*duration], 'sine'), doneAction: 2);
	front_mono = env_front * content;
	output_front = Pan2.ar(front_mono, pan_env);
	Out.ar(0, output_front);

	env_rear = EnvGen.kr(Env([0.001, 1.0, 0.001],
		[0.5*duration, 0.5*duration], 'sine'), doneAction: 2);
	output_rear = Pan2.ar(env_rear * content, pan_env);
	Out.ar(2, output_rear);

	amp = LPF.kr(Amplitude.kr(front_mono), 5);
	SendReply.kr(Impulse.kr(50), "/amp_private", amp, segment_id);

	SendReply.ar(Impulse.ar(500), "/waveform_private", front_mono, segment_id);
}).send(s);

SynthDef(\add_reverb, {|outbus, mix = 0.25, room = 0.15, damp = 0.5, amp = 1.0|
	var signal, silent_noise;
	silent_noise = WhiteNoise.ar(0.00001);
	signal = In.ar(outbus, 2);
	ReplaceOut.ar(outbus,
		signal + FreeVerb2.ar(
			signal[0] + silent_noise,
			signal[1] + silent_noise,
			mix, room, damp, amp));
}).send(s);

SystemClock.sched(1.0, {
	Synth(\add_reverb, [\outbus, 0, \mix, 0.5, \room, 0.8, \damp, 0.1]);
	Synth(\add_reverb, [\outbus, 2, \mix, 0.5, \room, 0.8, \damp, 0.1]);
});
