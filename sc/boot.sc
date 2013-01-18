"SC_JACK_DEFAULT_OUTPUTS".setenv("");
"SC_JACK_DEFAULT_INPUTS".setenv("");

Server.local.options.memSize = 1100000;
Server.local.options.numOutputBusChannels = 16;
s.boot;

s.doWhenBooted({

//$ENGINE

"langPort=".post; NetAddr.langPort.postln;

});
