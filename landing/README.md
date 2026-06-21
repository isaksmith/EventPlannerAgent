# Marquee — landing page

A standalone marketing landing for Marquee. It does **not** depend on `../app` —
the only connection is the "Try the Demo" button.

## View it
It's a static page. Serve the folder and open it:

```bash
python -m http.server 8750   # then open http://localhost:8750/
```

## Point the button at the app
Edit `PLATFORM_URL` near the top of the `<script>` in `index.html`
(currently `http://localhost:5173`) to wherever the app is deployed.

## The hero animation
The scroll hero plays `frames/frame_000.jpg … frame_144.jpg` — a Seedance
"marquee coming to life" clip split into 145 frames (committed, so the page just
works). To rebuild from a new clip:

```bash
npm i ffmpeg-static
node -e "const f=require('ffmpeg-static'),{execFileSync}=require('child_process');execFileSync(f,['-i','clip.mp4','-vf','fps=16,scale=768:768','-q:v','3','-start_number','0','frames/frame_%03d.jpg'],{stdio:'inherit'})"
```

Then set `const N` in `index.html` to the new frame count.
