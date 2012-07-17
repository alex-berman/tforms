#include "GlWindow.hpp"
#include "Stopwatch.hpp"
#include <vector>
#include <math.h>
#include <lo/lo.h>
#include <stdio.h>

#define PORT "51234"

using namespace std;

float centerX, centerY;
float screenRadius;

class Chunk {
public:
  Chunk(float _angle, float _size, float _duration) {
    angle = _angle;
    duration = _duration;
    size = _size;
    t = 0;
  }

  void draw() {
    float relativeTime = (float) t / duration;
    float x1 = centerX + cos(angle) * (1-relativeTime) * (screenRadius+size);
    float x2 = x1 + cos(angle) * size;
    float y1 = centerY + sin(angle) * (1-relativeTime) * (screenRadius+size);
    float y2 = y1 + sin(angle) * size;

    glLineWidth(2);
    glBegin(GL_LINES);
    glColor3f(1, 1, 1);
    glVertex2f(x1, y1);
    glColor3f(0, 0, 0);
    glVertex2f(x2, y2);
    glEnd();
  }

  void update(float timeIncrement) {
    t += timeIncrement;
  }

  bool arrived() {
    return t >= duration;
  }

  float angle;
  float duration;
  float size;

private:
  float t;
};

class Visualizer : public GlWindow {
public:
  Visualizer(int argc, char **argv) : GlWindow(argc, argv, 500, 500) {
    frameCount = 0;
    glClearColor (0.0, 0.0, 0.0, 0.0);
    glShadeModel (GL_SMOOTH);

    centerX = windowWidth / 2;
    centerY = windowHeight / 2;
    screenRadius = windowWidth / 2;
  }

  void display() {
    if(frameCount == 0) {
      stopwatch.start();
      timeIncrement = 0;
    }
    else {
      float timeOfThisDisplay = stopwatch.getElapsedMilliseconds();
      timeIncrement = timeOfThisDisplay - timeOfPreviousDisplay;
      timeOfPreviousDisplay = timeOfThisDisplay;
    }

    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);

    vector< vector<Chunk>::iterator > chunksToDelete;
    for(vector<Chunk>::iterator i = chunks.begin(); i != chunks.end(); i++) {
      i->draw();
      i->update(timeIncrement);
      if(i->arrived())
	chunksToDelete.push_back(i);
    }

    for(vector< vector<Chunk>::iterator >::reverse_iterator i = chunksToDelete.rbegin();
	i != chunksToDelete.rend(); i++) {
      chunks.erase(*i);
    }

    glutSwapBuffers();
    frameCount++;
  }

  void addChunk(float angle, float size, float durationSecs) {
    float duration = durationSecs * 1000;
    Chunk chunk(angle, size, duration);
    chunks.push_back(chunk);
  }

private:
  vector<Chunk> chunks;
  Stopwatch stopwatch;
  unsigned long frameCount;
  float timeOfPreviousDisplay;
  float timeIncrement;
};


Visualizer *visualizer;

int chunkHandler(const char *path, const char *types,
		 lo_arg **argv, int argc,
		 void *data, void *user_data) {
  int begin = argv[0]->i;
  int end = argv[1]->i;
  float duration = argv[2]->f;
  float pan = argv[3]->f;
  float angle = pan * 360;
  int size = end - begin;
  visualizer->addChunk(angle, size/50, duration);
  return 0;
}

void error(int num, const char *msg, const char *path) {
  printf("liblo server error %d in path %s: %s\n", num, path, msg);
}

int main(int argc, char **argv) {
  visualizer = new Visualizer(argc, argv);

  lo_server_thread st = lo_server_thread_new(PORT, error);
  lo_server_thread_add_method(st, "/chunk", "ifff", chunkHandler, NULL);
  lo_server_thread_start(st);

  glutMainLoop();
}
