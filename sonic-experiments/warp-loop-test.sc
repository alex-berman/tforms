s.boot;

(
~b1 = Buffer.read(s, "theme-nikolayeva-mono.wav");
~b2 = Buffer.read(s, "theme-acad-st-martin-mono.wav");
~b3 = Buffer.read(s, "/home/alex/Downloads/This Developer's Life - 2_0_4 Taste/Content/204-Taste.wav");

SynthDef(\loop, {arg buffer = 0, envbuf = -1, pan = 0, begin=0, end=1, period, duration;
	var out, pointer, filelength, pitch, env, dir;
	var period_line = Line.kr(period, period*5, duration);
	pointer = begin + ((end - begin) * LFSaw.ar(freq:1.0/period_line, iphase:1));
	pitch = 1.0;
	env = EnvGen.kr(Env([0.001, 1, 0.001],
		[0.005*duration, 0.995*duration], 'exp'), doneAction: 2);
	out = Warp1.ar(1, buffer, pointer, pitch, 0.1, envbuf, 8, 0.1, 2);
	Out.ar(0, Pan2.ar(out * env, pan));
}).send(s);

)

Synth(\loop, [\buffer, ~b1, \envbuf, -1, \begin, 0.4, \end, 0.6, \period, 5, \duration, 20]);
Synth(\loop, [\buffer, ~b3, \envbuf, -1, \begin, 0.5, \end, 0.50022554486349691, \period, 9.7600002288818, \duration, 10]);

s.freeAll;
