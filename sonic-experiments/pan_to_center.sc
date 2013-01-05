s.boot;

(
~b1 = Buffer.read(s, "theme-nikolayeva-mono.wav");

SynthDef(\loop, {arg buffer = 0, envbuf = -1, pan = 0, begin=0, end=1, period, duration;
	var out, pointer, filelength, pitch, env, dir, pan_env;
	pointer = Line.kr(0, 1, duration);
	pitch = 1.0;
	env = EnvGen.kr(Env([0.001, 1], [duration], 'sine'), doneAction: 2);
	pan_env = EnvGen.kr(Env([pan, 0], [duration], 'linear'), doneAction: 2);
	out = Warp1.ar(1, buffer, pointer, pitch, 0.1, envbuf, 8, 0.1, 2);
	Out.ar(0, Pan2.ar(out * env, pan_env));
}).send(s);

)

Synth(\loop, [\buffer, ~b1, \envbuf, -1, \begin, 0.4, \end, 0.6, \period, 5, \duration, 5, \pan, 1.0]);

s.freeAll;
