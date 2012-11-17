s.boot;

(
~b1 = Buffer.read(s, "theme-nikolayeva-mono.wav");
~b2 = Buffer.read(s, "theme-acad-st-martin-mono.wav");

SynthDef(\loop, {arg buffer = 0, envbuf = -1, pan = 0, period, duration;
	var out, pointer, filelength, pitch, env, dir;
	pointer = LFSaw.ar(freq:1.0/period, iphase:1);
	pitch = 1.0;
	env = EnvGen.kr(Env([0.001, 1, 0.001],
		[0.005*duration, 0.995*duration], 'exp'), doneAction: 2);
	out = Warp1.ar(1, buffer, pointer, pitch, 0.1, envbuf, 8, 0.1, 2);
	Out.ar(0, Pan2.ar(out * env, pan));
}).send(s);

)

Synth(\loop, [\buffer, ~b1, \envbuf, -1, \period, 4, \duration, 10]);

s.freeAll;
