# ClapControlledLighting

_This project was made in the summer, I wanted to put it on my GitHub for people to see but realized that un-privating my repo would expose some things I don't want to expose...so here's a new repository!_

Watching movies as a kid, I always wanted to have super cool lights that turn on and off when I clapped my hands, but my parents always said those lights were super expensive...

Fast forward 10 years later, I realized, "Wait, I know how to code! I'll just do it myself!"

I used the RaspberryPi 4B I got froma attending HackThe6ix over the summer (shoutout QNX) and bought some cheap Wi-Fi bulbs meant to be controlled with your phone.

These bulbs are from a brand called LifX, and they juse so happen to have a very developer friendly GitHub repo on how to control them using Python scripts! (https://github.com/mclarkk/lifxlan)

I bought a cheap USB microphone and CSI camera off Amazon, hooked 'em up to the Pi and got this sick looking thing:
<img width="4032" height="3024" alt="image" src="https://github.com/user-attachments/assets/d85f71c5-9f29-4409-bedf-2e727791b63a" />

Time for the fun stuff! I spent a weekend coding this, mostly trying to figure out why the hell the CSI camera wouldn't connect (I plugged the strip thingy in the wrong way)

I used a Python module I found called PyClap for clap detection, and even used Mediapipe to track my hand movements to control the brightness with hand gestures! 12-year old me would be so proud...

Anyways here's the finished thing:

I can turn them on with claps:

https://github.com/user-attachments/assets/253d6a09-1d2c-4beb-aeb3-7d466f4767e4

And even control the brighness with gestures!

https://github.com/user-attachments/assets/fce13843-81da-47ec-b273-306f05a521f6

_It's kinda subtle on the video, but works great IRL!_
