s.boot;

s.doWhenBooted({

~sounds = [
	Buffer.read(s, "theme-nikolayeva-mono.wav"),
	Buffer.read(s, "theme-acad-st-martin-mono.wav")
];

SynthDef(\warp, {arg buffer = 0, begin, end, duration;
        var out, pointer, filelength, pitch, env, dir;
        pointer = Line.kr(begin, end, duration);
        pitch = 1.0;
        env = EnvGen.kr(Env([0.001, 1, 1, 0.001], [0.1, 14, 0.9], 'exp'), doneAction: 2);
        out = Warp1.ar(1, buffer, pointer, pitch, 0.1, -1, 8, 0.1, 2);
        Out.ar(0, out * env);
}).send(s);

OSCresponder.new(nil, "/play",
  { arg t, r, msg;
	  var sound_id = msg[1];
	  var begin = msg[2];
	  var end = msg[3];
	  var duration = msg[4];
	  "play sound_id=".post; sound_id.postln;
	  Synth(\warp, [\buffer, ~sounds[sound_id],
		  \begin, begin, \end, end, \duration, duration]);
  }).add;

});
