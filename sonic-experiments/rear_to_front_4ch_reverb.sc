s.boot;

(
~b1 = Buffer.read(s, "theme-nikolayeva-mono.wav");
~b3 = Buffer.read(s, "/home/alex/Downloads/This Developer's Life - 2_0_4 Taste/Content/204-Taste.wav");

~reverb_bus = Bus.audio(s, 1);

SynthDef(\warp, {arg buffer = 0, envbuf = -1, pan = 0, begin=0, end=1, period, duration;
	var output_front, output_rear, pointer, filelength, pitch, env_front, env_rear, dir, pan_env, content;
	var front_content, rear_content;
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
}).send(s);

SynthDef(\add_reverb, {|out=0, in=0, mix = 0.25, room = 0.15, damp = 0.5, amp = 1.0|
	var signal, silent_noise, reverb;
	silent_noise = WhiteNoise.ar(0.00001); // see http://new-supercollider-mailing-lists-forums-use-these.2681727.n2.nabble.com/cpu-problems-with-PV-MagFreeze-and-Freeverb-tp5998599p6013552.html
	signal = In.ar(~reverb_bus, 1);
	reverb = FreeVerb.ar(signal + silent_noise,	mix, room, damp, amp);
	Out.ar(0, reverb);
	Out.ar(1, reverb);
	Out.ar(2, reverb);
	Out.ar(3, reverb);
}).send(s);

)

~reverb = Synth(\add_reverb, [\in, ~reverb_bus.index]);
~reverb.set(\room, 0.9);
Synth(\warp, [\buffer, ~b3, \envbuf, -1, \begin, 0.5, \end, 0.50022554486349691, \period, 9.7600002288818, \duration, 10]);
Synth(\warp, [\buffer, ~b1, \envbuf, -1, \begin, 0.4, \end, 0.6, \period, 5, \duration, 10, \pan, 1.0]);

s.freeAll;
