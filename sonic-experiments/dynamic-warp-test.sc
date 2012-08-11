s.boot;

(
~b1 = Buffer.read(s, "theme-nikolayeva-mono.wav");
~b2 = Buffer.read(s, "theme-acad-st-martin-mono.wav");

SynthDef(\warp, {arg buffer = 0, envbuf = -1, pan = 0, pointer=0;
	var out, filelength, pitch, env, dir;
	pitch = 1.0;
	out = Warp1.ar(1, buffer, pointer, pitch, 0.1, envbuf, 8, 0.1, 2);
	Out.ar(0, Pan2.ar(out, pan));
}).send(s);

)

x=Synth(\warp, [\buffer, ~b1, \envbuf, -1]);
x.set(\pointer, 0.1);
x.set(\pointer, 0.2);
x.set(\pointer, 0.3);
x.set(\pointer, 0.4);
x.set(\pointer, 0.5);
x.set(\pointer, 0.6);
x.free();
