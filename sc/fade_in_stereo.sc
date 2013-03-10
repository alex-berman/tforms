SynthDef(\warp, {arg buffer = 0, segment_id, begin, end, duration, channel, pan;
	var out, pointer, filelength, pitch, env, dir, amp, pan_env;
	pointer = Line.kr(begin, end, duration);
	pitch = 1.0;
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
	pointer = begin + ((end - begin) * LFSaw.ar(freq:1.0/period_line, iphase:1));
	pitch = 1.0;
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
