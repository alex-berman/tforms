
SynthDef(\warp, {arg buffer = 0, segment_id, begin, end, duration, channel, pan;
	var output_front, output_center, output_rear, pointer, filelength, pitch;
	var env_front, env_center, env_rear, dir, amp, content;
	var front_content, center_content, rear_content;
	pointer = Line.kr(begin, end, duration);
	pitch = 1.0;
	content = Warp1.ar(1, buffer, pointer, pitch, 0.1, -1, 8, 0.1, 2);

	env_front = EnvGen.kr(Env([0.001, 0.001, 1.0, 0.001],
		[0.3*duration, 0.696*duration, 0.004*duration], 'sine'), doneAction: 2);
	front_content = env_front * content;
	output_front = Pan2.ar(front_content, pan);
	Out.ar(0, output_front);

	env_center = EnvGen.kr(Env([0.001, 0.001, 1.0, 0.001],
		[0.2*duration, 0.4*duration, 0.4*duration], 'sine'), doneAction: 2);
	output_center = Pan2.ar(env_center * content, pan);
	Out.ar(4, output_center);

	env_rear = EnvGen.kr(Env([0.001, 1.0, 0.001, 0.001],
		[0.4*duration, 0.4*duration, 0.2*duration], 'sine'), doneAction: 2);
	output_rear = Pan2.ar(env_rear * content, pan);
	Out.ar(2, output_rear);

	amp = LPF.kr(Amplitude.kr(front_content), 5);
	SendReply.kr(Impulse.kr(50), "/amp_private", amp, segment_id);

	SendReply.ar(Impulse.ar(500), "/waveform_private", front_content, segment_id);
}).send(s);
