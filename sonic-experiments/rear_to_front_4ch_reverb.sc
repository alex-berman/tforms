s.boot;

(
~b1 = Buffer.read(s, "theme-nikolayeva-mono.wav");
~b3 = Buffer.read(s, "/home/alex/Downloads/This Developer's Life - 2_0_4 Taste/Content/204-Taste.wav");

SynthDef(\warp, {arg buffer = 0, envbuf = -1, pan = 0, begin=0, end=1, period, duration;
	var output_front, output_rear, pointer, filelength, pitch, env_front, env_rear, dir, pan_env, content;
	pointer = Line.kr(0, 1, duration);
	pitch = 1.0;
	content = Warp1.ar(1, buffer, pointer, pitch, 0.1, -1, 8, 0.1, 2);
	pan_env = EnvGen.kr(Env([pan, 0], [duration], 'linear'), doneAction: 2);

	env_front = EnvGen.kr(Env([0.001, 1.0, 0.001],
		[0.996*duration, 0.004*duration], 'sine'), doneAction: 2);
	output_front = Pan2.ar(env_front * content, pan_env);
	Out.ar(0, output_front);

	env_rear = EnvGen.kr(Env([0.001, 1.0, 0.001],
		[0.5*duration, 0.5*duration], 'sine'), doneAction: 2);
	output_rear = Pan2.ar(env_rear * content, pan_env);
	Out.ar(2, output_rear);
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

)

Synth(\add_reverb, [\outbus, 0, \mix, 0.5, \room, 0.8, \damp, 0.1]);
Synth(\add_reverb, [\outbus, 2, \mix, 0.5, \room, 0.8, \damp, 0.1]);
Synth(\warp, [\buffer, ~b3, \envbuf, -1, \begin, 0.5, \end, 0.50022554486349691, \period, 9.7600002288818, \duration, 10]);
Synth(\warp, [\buffer, ~b1, \envbuf, -1, \begin, 0.4, \end, 0.6, \period, 5, \duration, 10, \pan, 1.0]);

s.freeAll;
