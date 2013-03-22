
SynthDef(\warp, {arg buffer = 0, segment_id, begin, end, duration, channel, pan;
	var output_front, output_rear, pointer, filelength, pitch, env_front, env_rear, dir, amp, content, front_mono;
	pointer = Line.kr(begin, end, duration);
	pitch = 1.0;
	content = Warp1.ar(1, buffer, pointer, pitch, 0.1, -1, 8, 0.1, 2);

	env_front = EnvGen.kr(Env([0.001, 1.0, 0.001],
		[0.996*duration, 0.004*duration], 'sine'), doneAction: 2);
	front_mono = env_front * content;
	output_front = Pan2.ar(front_mono, pan);
	Out.ar(0, output_front);

	env_rear = EnvGen.kr(Env([0.001, 1.0, 0.001],
		[0.5*duration, 0.5*duration], 'sine'), doneAction: 2);
	output_rear = Pan2.ar(env_rear * content, pan);
	Out.ar(2, output_rear);

	amp = LPF.kr(Amplitude.kr(front_mono), 5);
	SendReply.kr(Impulse.kr(50), "/amp_private", amp, segment_id);

	SendReply.ar(Impulse.ar(500), "/waveform_private", front_mono, segment_id);
}).send(s);
