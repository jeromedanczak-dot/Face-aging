# AI Module Notes

The runtime AI pipeline is implemented in `backend/app/aging_engine.py` and includes:

1. MTCNN face detection
2. Face-centered alignment/crop to 512x512
3. Optional diffusion age transformation (`timbrooks/instruct-pix2pix`)
4. Identity-preserving blending
5. Resize to 1024x1024

Fallback mode is used automatically if diffusion pipeline is unavailable.
