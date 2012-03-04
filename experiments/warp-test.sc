s.boot;

(
~b1 = Buffer.read(s, "theme-nikolayeva-mono.wav");
~b2 = Buffer.read(s, "theme-acad-st-martin-mono.wav");

SynthDef(\warp, {arg buffer = 0, envbuf = -1;
        var out, pointer, filelength, pitch, env, dir;
        // pointer - move from beginning to end of soundfile over 15 seconds
        pointer = Line.kr(0, 1, 15);
        pitch = 1.0;
        env = EnvGen.kr(Env([0.001, 1, 1, 0.001], [0.1, 14, 0.9], 'exp'), doneAction: 2);
        out = Warp1.ar(1, buffer, pointer, pitch, 0.1, envbuf, 8, 0.1, 2);
        Out.ar(0, out * env);
}).send(s);

)

Synth(\warp, [\buffer, ~b1, \envbuf, -1]);
Synth(\warp, [\buffer, ~b2, \envbuf, -1]);
