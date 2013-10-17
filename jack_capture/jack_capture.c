/*
    Copyright (C) 2001 Paul Davis
    Copyright (C) 2003 Jack O'Quin
    Copyright (C) 2013 Alex Berman

    This program is free software; you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation; either version 2 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program; if not, write to the Free Software
    Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
*/

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <unistd.h>
#include <sndfile.h>
#include <signal.h>
#include <getopt.h>
#include <inttypes.h>
#include <sys/time.h>
#include <jack/jack.h>

SNDFILE *sf;
jack_nframes_t duration;
jack_nframes_t rb_size;
jack_client_t *client;
unsigned int channels;
int bitdepth;
char *path;
volatile int can_process;
int logged_timestamp;

unsigned int nports;
jack_port_t **ports;
jack_default_audio_sample_t **in;
jack_nframes_t nframes;
const size_t sample_size = sizeof(jack_default_audio_sample_t);

jack_client_t *client;
float *sndfile_buffer;

static void signal_handler(int sig)
{
	jack_client_close(client);
	fprintf(stderr, "signal received, exiting ...\n");
	exit(0);
}

void log_timestamp() {
  struct timeval tp;
  gettimeofday(&tp, NULL);
  float secs = tp.tv_sec + (float) tp.tv_usec / 1000000;
  printf("audio capture started at %.3f\n", secs);
  logged_timestamp = 1;
}

static int
process (jack_nframes_t nframes, void *arg)
{
  int chn;
  size_t i;
  float *sndfile_buffer_ptr;

  if (!can_process)
    return 0;

  if (!logged_timestamp)
    log_timestamp();

  for (chn = 0; chn < nports; chn++)
    in[chn] = jack_port_get_buffer (ports[chn], nframes);

  sndfile_buffer_ptr = sndfile_buffer;
  for (i = 0; i < nframes; i++) {
    for (chn = 0; chn < nports; chn++) {
      *sndfile_buffer_ptr++ = in[chn][i];
    }
  }
  sf_writef_float(sf, sndfile_buffer, nframes);

  return 0;
}

static void
jack_shutdown (void *arg)
{
	fprintf(stderr, "JACK shut down, exiting ...\n");
	exit(1);
}

static void
open_wav_file ()
{
	SF_INFO sf_info;
	int short_mask;

	sf_info.samplerate = jack_get_sample_rate (client);
	sf_info.channels = nports;

	switch (bitdepth) {
		case 8: short_mask = SF_FORMAT_PCM_U8;
		  	break;
		case 16: short_mask = SF_FORMAT_PCM_16;
			 break;
		case 24: short_mask = SF_FORMAT_PCM_24;
			 break;
		case 32: short_mask = SF_FORMAT_PCM_32;
			 break;
		default: short_mask = SF_FORMAT_PCM_16;
			 break;
	}
	sf_info.format = SF_FORMAT_WAV|short_mask;

	if ((sf = sf_open (path, SFM_WRITE, &sf_info)) == NULL) {
		char errstr[256];
		sf_error_str (0, errstr, sizeof (errstr) - 1);
		fprintf (stderr, "cannot open sndfile \"%s\" for output (%s)\n", path, errstr);
		jack_client_close (client);
		exit (1);
	}

	duration *= sf_info.samplerate;
}

static void
setup_ports (char *source_names[])
{
	unsigned int i;
	size_t in_size;

	/* Allocate data structures that depend on the number of ports. */
	ports = (jack_port_t **) malloc (sizeof (jack_port_t *) * nports);
	in_size =  nports * sizeof (jack_default_audio_sample_t *);
	in = (jack_default_audio_sample_t **) malloc (in_size);

	memset(in, 0, in_size);

	for (i = 0; i < nports; i++) {
		char name[64];

		sprintf (name, "input%d", i+1);

		if ((ports[i] = jack_port_register (client, name, JACK_DEFAULT_AUDIO_TYPE, JackPortIsInput, 0)) == 0) {
			fprintf (stderr, "cannot register input port \"%s\"!\n", name);
			jack_client_close (client);
			exit (1);
		}
	}

	for (i = 0; i < nports; i++) {
		if (jack_connect (client, source_names[i], jack_port_name (ports[i]))) {
			fprintf (stderr, "cannot connect input port %s to %s\n", jack_port_name (ports[i]), source_names[i]);
			jack_client_close (client);
			exit (1);
		}
	}

	can_process = 1;		/* process() can start, now */
}

int
main (int argc, char *argv[])
{
	int c;
	int longopt_index = 0;
	extern int optind, opterr;
	int show_usage = 0;
	char *optstring = "d:f:b:B:h";
	struct option long_options[] = {
		{ "help", 0, 0, 'h' },
		{ "duration", 1, 0, 'd' },
		{ "file", 1, 0, 'f' },
		{ "bitdepth", 1, 0, 'b' },
		{ "bufsize", 1, 0, 'B' },
		{ 0, 0, 0, 0 }
	};

	while ((c = getopt_long (argc, argv, optstring, long_options, &longopt_index)) != -1) {
		switch (c) {
		case 1:
			/* getopt signals end of '-' options */
			break;

		case 'h':
			show_usage++;
			break;
		case 'd':
			duration = atoi (optarg);
			break;
		case 'f':
			path = optarg;
			break;
		case 'b':
			bitdepth = atoi (optarg);
			break;
		default:
			fprintf (stderr, "error\n");
			show_usage++;
			break;
		}
	}

	if (show_usage || path == NULL || optind == argc) {
	  fprintf (stderr, "usage: %s -f filename [ -d second ] [ -b bitdepth ] port1 [ port2 ... ]\n", argv[0]);
		exit (1);
	}

	if ((client = jack_client_open ("jack_capture", JackNullOption, NULL)) == 0) {
		fprintf (stderr, "JACK server not running?\n");
		exit (1);
	}

	nports = argc - optind;
	sndfile_buffer = (float *) malloc (nports * sample_size *
					   jack_get_buffer_size(client));
	open_wav_file();
	logged_timestamp = 0;
	jack_set_process_callback (client, process, NULL);
	jack_on_shutdown (client, jack_shutdown, NULL);

	if (jack_activate (client)) {
		fprintf (stderr, "cannot activate client");
	}

	setup_ports (&argv[optind]);

	while (1) {
	  sleep (1);
	}

     /* install a signal handler to properly quits jack client */
#ifndef WIN32
	signal(SIGQUIT, signal_handler);
	signal(SIGHUP, signal_handler);
#endif
	signal(SIGTERM, signal_handler);
	signal(SIGINT, signal_handler);

	jack_client_close (client);

	exit (0);
}
